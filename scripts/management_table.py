#!/usr/bin/env python3
"""Validate and render decision, status, checklist and quality tables from JSON."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import textwrap
from pathlib import Path


INK = '#30302D'
MUTED = '#6D6A63'
BG = '#F1EFEB'
PAPER = '#FAF9F6'
GRID = '#D8D3C8'
ACCENT = '#AC6046'
GREEN = '#58705A'
BLUE = '#657487'
AMBER = '#C1965B'
RED = '#A65448'


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _ids(rows, label):
    _need(isinstance(rows, list) and rows, f'{label} required')
    values = [row.get('id') for row in rows]
    _need(all(values), f'each {label} row needs id')
    _unique(values, f'{label} ids must be unique')
    return values


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')


def _checklist(data):
    _base(data, 'checklist')
    rows = data.get('rows')
    _ids(rows, 'checklist')
    allowed = {'passed', 'failed', 'pending', 'not-applicable'}
    for row in rows:
        _need(all(isinstance(row.get(k), str) and row[k].strip() for k in ('item', 'criterion', 'owner')), 'checklist item, criterion and owner required')
        _need(row.get('result') in allowed, 'checklist result must be explicit')
        _need('evidence' in row and isinstance(row['evidence'], str), 'checklist evidence field required')
        if row['result'] in {'passed', 'failed'}:
            _need(row['evidence'].strip(), 'completed checklist result requires evidence')
    counts = {status: sum(row['result'] == status for row in rows) for status in sorted(allowed)}
    return {'mode': 'checklist', 'rows': len(rows), 'result_counts': counts, 'explicit_results': 'passed'}


def _status(data):
    _base(data, 'status')
    definitions = data.get('status_definitions')
    definition_ids = _ids(definitions, 'status definition')
    for row in definitions:
        _need(row.get('label') and row.get('meaning'), 'status definition needs label and meaning')
    rows = data.get('rows')
    _ids(rows, 'status')
    as_of = dt.date.fromisoformat(data.get('as_of', ''))
    stale_after = data.get('stale_after_days')
    _need(isinstance(stale_after, int) and stale_after >= 0, 'stale_after_days must be a nonnegative integer')
    enriched = []
    for row in rows:
        _need(all(isinstance(row.get(k), str) and row[k].strip() for k in ('object', 'owner', 'updated_at')), 'status object, owner and updated_at required')
        _need(row.get('status') in definition_ids, 'row references unknown status')
        updated = dt.date.fromisoformat(row['updated_at'])
        _need(updated <= as_of, 'updated_at cannot be later than as_of')
        age = (as_of - updated).days
        enriched.append({**row, 'age_days': age, 'stale': age > stale_after})
    return {'mode': 'status', 'as_of': as_of.isoformat(), 'stale_after_days': stale_after,
            'rows': enriched, 'stale_count': sum(row['stale'] for row in enriched)}


def _decision_scores(criteria, alternatives):
    weights = {row['id']: float(row['weight']) for row in criteria}
    return {alternative['id']: sum(weights[criterion['id']] * float(alternative['scores'][criterion['id']]['score']) for criterion in criteria)
            for alternative in alternatives}


def _decision(data):
    _base(data, 'decision')
    criteria = data.get('criteria')
    criterion_ids = _ids(criteria, 'criterion')
    _need(all(row.get('label') and _finite(row.get('weight')) and row['weight'] >= 0 for row in criteria), 'criterion label and nonnegative finite weight required')
    weight_sum = sum(float(row['weight']) for row in criteria)
    _need(math.isclose(weight_sum, 1.0, rel_tol=1e-9, abs_tol=1e-9), 'decision weights must sum to 1')
    scale = data.get('score_scale')
    _need(isinstance(scale, dict) and _finite(scale.get('min')) and _finite(scale.get('max')) and scale['min'] < scale['max'], 'valid score_scale required')
    alternatives = data.get('alternatives')
    alternative_ids = _ids(alternatives, 'alternative')
    for alternative in alternatives:
        _need(alternative.get('label'), 'alternative label required')
        scores = alternative.get('scores')
        _need(isinstance(scores, dict) and set(scores) == set(criterion_ids), 'every alternative needs every criterion exactly once')
        for score in scores.values():
            _need(_finite(score.get('score')) and scale['min'] <= score['score'] <= scale['max'], 'score outside declared scale')
            _need(isinstance(score.get('evidence'), str) and score['evidence'].strip(), 'each decision score needs evidence')
    totals = _decision_scores(criteria, alternatives)
    ranking = sorted(alternative_ids, key=lambda item: (-totals[item], item))
    _need(len(ranking) < 2 or not math.isclose(totals[ranking[0]], totals[ranking[1]], rel_tol=1e-12, abs_tol=1e-12), 'top decision scores are tied; add an explicit tie rule')
    sensitivity = []
    for criterion in criteria:
        for factor in (0.9, 1.1):
            adjusted = copy.deepcopy(criteria)
            target = next(row for row in adjusted if row['id'] == criterion['id'])
            target['weight'] *= factor
            total_weight = sum(row['weight'] for row in adjusted)
            for row in adjusted:
                row['weight'] /= total_weight
            scores = _decision_scores(adjusted, alternatives)
            winner = max(alternative_ids, key=lambda item: (scores[item], item))
            sensitivity.append({'criterion': criterion['id'], 'factor': factor, 'winner': winner, 'scores': scores})
    return {'mode': 'decision', 'weight_sum': weight_sum, 'weighted_scores': totals,
            'ranking': ranking, 'winner': ranking[0], 'sensitivity': sensitivity,
            'sensitivity_winners': sorted(set(row['winner'] for row in sensitivity))}


def _target_matrix(data):
    _base(data, 'target-matrix')
    objectives = data.get('objectives'); objective_ids = _ids(objectives, 'objective')
    initiatives = data.get('initiatives'); initiative_ids = _ids(initiatives, 'initiative')
    metrics = data.get('metrics'); metric_ids = _ids(metrics, 'metric')
    _need(all(row.get('label') for row in objectives), 'objective label required')
    _need(all(row.get('label') and row.get('owner') and row.get('cadence') and row.get('priority') in {'high', 'medium', 'low'} for row in initiatives), 'initiative label, owner, cadence and priority required')
    _need(all(row.get('label') and row.get('target') not in (None, '') and row.get('unit') and row.get('operator') in {'<=', '>=', '=', '<', '>'} for row in metrics), 'metric label, target, unit and comparison operator required')
    links = data.get('links')
    _need(isinstance(links, list) and links, 'target matrix links required')
    seen = set()
    for link in links:
        key = (link.get('initiative'), link.get('objective'), link.get('metric'))
        _need(key[0] in initiative_ids and key[1] in objective_ids and key[2] in metric_ids, 'target matrix link references unknown id')
        _need(key not in seen, 'duplicate target matrix link')
        seen.add(key)
        _need(link.get('strength') in {'primary', 'supporting'}, 'link strength must be primary or supporting')
    _need(set(initiative_ids) <= {row['initiative'] for row in links}, 'every initiative must be linked')
    _need(set(objective_ids) <= {row['objective'] for row in links}, 'every objective must be linked')
    _need(set(metric_ids) <= {row['metric'] for row in links}, 'every metric must be linked')
    return {'mode': 'target-matrix', 'objectives': len(objectives), 'initiatives': len(initiatives),
            'metrics': len(metrics), 'links': len(links), 'traceability': 'passed',
            'primary_links': sum(row['strength'] == 'primary' for row in links)}


def _checksheet(data):
    _base(data, 'checksheet')
    categories = data.get('categories'); category_ids = _ids(categories, 'defect category')
    _need(all(row.get('label') for row in categories), 'defect category label required')
    periods = data.get('periods')
    _need(isinstance(periods, list) and periods and all(isinstance(value, str) and value.strip() for value in periods), 'checksheet periods required')
    _unique(periods, 'checksheet periods must be unique')
    _need(data.get('count_unit') and data.get('counting_rule'), 'count unit and counting rule required')
    counts = data.get('counts')
    _need(isinstance(counts, dict) and set(counts) == set(category_ids), 'counts must cover every category exactly once')
    for values in counts.values():
        _need(isinstance(values, list) and len(values) == len(periods), 'each checksheet row must match periods')
        _need(all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values), 'checksheet counts must be nonnegative integers')
    row_totals = {category: sum(counts[category]) for category in category_ids}
    column_totals = [sum(counts[category][index] for category in category_ids) for index in range(len(periods))]
    return {'mode': 'checksheet', 'row_totals': row_totals, 'column_totals': column_totals,
            'grand_total': sum(row_totals.values()), 'integer_counts': 'passed'}


ANALYZERS = {'checklist': _checklist, 'status': _status, 'decision': _decision,
             'target-matrix': _target_matrix, 'checksheet': _checksheet}


def analyze(data):
    mode = data.get('mode')
    _need(mode in ANALYZERS, 'mode must be checklist, status, decision, target-matrix or checksheet')
    result = ANALYZERS[mode](data)
    result['data_status'] = data.get('data_status', 'unspecified')
    result['assumptions'] = data.get('assumptions', [])
    return result


def _font():
    from matplotlib import font_manager
    path = Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists():
        font_manager.fontManager.addfont(path)
        return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def _figure(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family': _font(), 'font.size': 10.5, 'text.color': INK,
                                 'svg.fonttype': 'none', 'svg.hashsalt': 'diagram-studio-management-v1'})
    fig = plt.figure(figsize=(12.8, 7.2), facecolor=BG)
    ax = fig.add_axes([0.055, 0.14, 0.89, 0.66])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    fig.text(0.055, 0.92, data['title'], fontsize=23, weight='medium')
    fig.text(0.055, 0.862, data.get('subtitle', ''), fontsize=10.5, color=MUTED)
    fig.text(0.055, 0.045, data.get('footer', '模拟数据 · 可编辑输入与计算摘要随图保留'), fontsize=9.5, color=MUTED)
    return fig, ax


def _wrap(value, width):
    text = str(value)
    chunks = []
    for line in text.split('\n'):
        chunks.extend(textwrap.wrap(line, width=max(4, width), break_long_words=True, break_on_hyphens=False) or [''])
    return '\n'.join(chunks)


def _table(ax, headers, rows, widths, aligns=None, cell_colors=None, font_size=9.2):
    from matplotlib.patches import Rectangle
    _need(math.isclose(sum(widths), 1.0, abs_tol=1e-9), 'table widths must sum to 1')
    aligns = aligns or ['left'] * len(headers)
    total_rows = len(rows) + 1
    row_height = min(0.125, 0.90 / total_rows)
    total_height = row_height * total_rows
    top = 0.96
    xs = [0]
    for width in widths:
        xs.append(xs[-1] + width)
    ax.add_patch(Rectangle((0, top - row_height), 1, row_height, facecolor='#E7E1D8', edgecolor=GRID, linewidth=1))
    for index, header in enumerate(headers):
        x = (xs[index] + xs[index + 1]) / 2 if aligns[index] == 'center' else xs[index] + 0.012
        ax.text(x, top - row_height / 2, header, ha='center' if aligns[index] == 'center' else 'left', va='center', fontsize=9.3, weight='medium')
    for row_index, row in enumerate(rows):
        bottom = top - row_height * (row_index + 2)
        face = PAPER if row_index % 2 == 0 else '#F4F1EC'
        ax.add_patch(Rectangle((0, bottom), 1, row_height, facecolor=face, edgecolor=GRID, linewidth=0.8))
        for column_index, value in enumerate(row):
            if cell_colors and (row_index, column_index) in cell_colors:
                ax.add_patch(Rectangle((xs[column_index], bottom), widths[column_index], row_height,
                                       facecolor=cell_colors[(row_index, column_index)], edgecolor='none', alpha=0.24))
            center = aligns[column_index] == 'center'
            x = (xs[column_index] + xs[column_index + 1]) / 2 if center else xs[column_index] + 0.012
            wrap_width = max(5, int(widths[column_index] * 78))
            ax.text(x, bottom + row_height / 2, _wrap(value, wrap_width), ha='center' if center else 'left', va='center', fontsize=font_size)
    for x in xs:
        ax.plot([x, x], [top - total_height, top], color=GRID, linewidth=0.8)
    return top - total_height


def _render_checklist(data, meta):
    labels = {'passed': '通过', 'failed': '不通过', 'pending': '待检查', 'not-applicable': '不适用'}
    colors = {'passed': GREEN, 'failed': RED, 'pending': AMBER, 'not-applicable': BLUE}
    fig, ax = _figure(data)
    rows = [[str(i + 1), row['item'], row['criterion'], labels[row['result']], row['owner'], row['evidence'] or '—'] for i, row in enumerate(data['rows'])]
    cell_colors = {(i, 3): colors[row['result']] for i, row in enumerate(data['rows'])}
    bottom = _table(ax, ['#', '检查项', '可观察验收准则', '结果', '责任', '证据'], rows,
                    [0.05, 0.17, 0.30, 0.12, 0.12, 0.24], ['center', 'left', 'left', 'center', 'center', 'left'], cell_colors)
    counts = meta['result_counts']
    ax.text(0, max(0.02, bottom - 0.055), f"通过 {counts['passed']} · 不通过 {counts['failed']} · 待检查 {counts['pending']} · 不适用 {counts['not-applicable']}", fontsize=9.5, color=MUTED)
    return fig


def _render_status(data, meta):
    definitions = {row['id']: row for row in data['status_definitions']}
    color_map = {'green': GREEN, 'amber': AMBER, 'red': RED, 'blue': BLUE}
    fig, ax = _figure(data)
    rows = []
    cell_colors = {}
    for index, row in enumerate(meta['rows']):
        definition = definitions[row['status']]
        rows.append([row['object'], definition['label'], definition['meaning'], row['updated_at'], f"{row['age_days']}天" + (' · 已过期' if row['stale'] else ''), row['owner']])
        cell_colors[(index, 1)] = color_map.get(definition.get('color'), BLUE)
        if row['stale']:
            cell_colors[(index, 4)] = RED
    bottom = _table(ax, ['对象', '状态', '状态含义', '更新时间', '数据时效', '责任'], rows,
                    [0.18, 0.12, 0.25, 0.14, 0.18, 0.13], ['left', 'center', 'left', 'center', 'center', 'center'], cell_colors)
    ax.text(0, max(0.02, bottom - 0.055), f"截至 {meta['as_of']} · 超过 {meta['stale_after_days']} 天视为过期 · 过期 {meta['stale_count']} 项", fontsize=9.5, color=MUTED)
    return fig


def _render_decision(data, meta):
    fig, ax = _figure(data)
    criterion_ids = [row['id'] for row in data['criteria']]
    alternative_by_id = {row['id']: row for row in data['alternatives']}
    headers = ['方案'] + [f"{row['label']}\n{row['weight']:.0%}" for row in data['criteria']] + ['加权总分', '排序']
    rows = []
    cell_colors = {}
    rank = {item: index + 1 for index, item in enumerate(meta['ranking'])}
    for row_index, alternative in enumerate(data['alternatives']):
        values = [alternative['label']]
        for column_index, criterion_id in enumerate(criterion_ids, 1):
            score = alternative['scores'][criterion_id]
            values.append(f"{score['score']:g}\n{score['evidence']}")
            cell_colors[(row_index, column_index)] = GREEN if score['score'] >= 4 else AMBER if score['score'] >= 3 else RED
        values += [f"{meta['weighted_scores'][alternative['id']]:.2f}", str(rank[alternative['id']])]
        rows.append(values)
        if alternative['id'] == meta['winner']:
            cell_colors[(row_index, len(headers) - 2)] = GREEN
    bottom = _table(ax, headers, rows, [0.16, 0.16, 0.16, 0.16, 0.16, 0.13, 0.07],
                    ['left', 'center', 'center', 'center', 'center', 'center', 'center'], cell_colors, 8.8)
    winner = alternative_by_id[meta['winner']]['label']
    stable = len(meta['sensitivity_winners']) == 1
    ax.text(0, max(0.02, bottom - 0.055), f"当前首选：{winner} · 权重合计 {meta['weight_sum']:.0%} · 单项权重 ±10% 敏感性：{'首选不变' if stable else '首选会变化'}", fontsize=9.5, color=MUTED)
    return fig


def _render_target(data, meta):
    fig, ax = _figure(data)
    objective_ids = [row['id'] for row in data['objectives']]
    objective_names = {row['id']: row['label'] for row in data['objectives']}
    metrics = {row['id']: row for row in data['metrics']}
    links_by_initiative = {row['id']: [] for row in data['initiatives']}
    for link in data['links']:
        links_by_initiative[link['initiative']].append(link)
    headers = ['行动'] + [objective_names[item] for item in objective_ids] + ['指标与目标', '责任 / 节奏', '优先级']
    widths = [0.20] + [0.10] * len(objective_ids) + [0.25, 0.17, 0.08]
    rows = []
    cell_colors = {}
    priority_label = {'high': '高', 'medium': '中', 'low': '低'}
    for row_index, initiative in enumerate(data['initiatives']):
        links = links_by_initiative[initiative['id']]
        relation = []
        for column_index, objective_id in enumerate(objective_ids, 1):
            matching = [row for row in links if row['objective'] == objective_id]
            value = '● 主责' if any(row['strength'] == 'primary' for row in matching) else '○ 支持' if matching else '—'
            relation.append(value)
            if matching:
                cell_colors[(row_index, column_index)] = GREEN if value.startswith('●') else BLUE
        metric_ids = list(dict.fromkeys(row['metric'] for row in links))
        symbols = {'<=': '≤', '>=': '≥', '=': '=', '<': '<', '>': '>'}
        metric_text = '\n'.join(f"{metrics[metric_id]['label']} {symbols[metrics[metric_id]['operator']]} {metrics[metric_id]['target']}{metrics[metric_id]['unit']}" for metric_id in metric_ids)
        rows.append([initiative['label']] + relation + [metric_text, f"{initiative['owner']}\n{initiative['cadence']}", priority_label[initiative['priority']]])
        cell_colors[(row_index, len(headers) - 1)] = RED if initiative['priority'] == 'high' else AMBER if initiative['priority'] == 'medium' else BLUE
    bottom = _table(ax, headers, rows, widths, ['left'] + ['center'] * len(objective_ids) + ['left', 'center', 'center'], cell_colors, 8.7)
    ax.text(0, max(0.02, bottom - 0.055), f"{meta['objectives']} 个目标 · {meta['initiatives']} 项行动 · {meta['metrics']} 个指标 · {meta['links']} 条可追踪关系", fontsize=9.5, color=MUTED)
    return fig


def _render_checksheet(data, meta):
    fig, ax = _figure(data)
    rows = []
    category_names = {row['id']: row['label'] for row in data['categories']}
    for category in data['categories']:
        values = data['counts'][category['id']]
        rows.append([category['label']] + [str(value) for value in values] + [str(meta['row_totals'][category['id']])])
    rows.append(['期间合计'] + [str(value) for value in meta['column_totals']] + [str(meta['grand_total'])])
    widths = [0.24] + [0.11] * len(data['periods']) + [0.10]
    bottom = _table(ax, ['缺陷类别'] + data['periods'] + ['合计'], rows, widths,
                    ['left'] + ['center'] * (len(data['periods']) + 1), {(len(rows) - 1, index): BLUE for index in range(len(widths))})
    ax.text(0, max(0.02, bottom - 0.055), f"计数单位：{data['count_unit']} · 规则：{data['counting_rule']} · 总计 {meta['grand_total']}", fontsize=9.5, color=MUTED)
    return fig


RENDERERS = {'checklist': _render_checklist, 'status': _render_status, 'decision': _render_decision,
             'target-matrix': _render_target, 'checksheet': _render_checksheet}


def render(data, output, stem=None):
    import matplotlib
    import matplotlib.pyplot as plt
    meta = analyze(data)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    stem = stem or data.get('id') or data['mode']
    fig = RENDERERS[data['mode']](data, meta)
    fig.savefig(output / f'{stem}.svg', facecolor=BG, metadata={'Date': None})
    fig.savefig(output / f'{stem}.png', facecolor=BG, dpi=150, metadata={'Software': 'diagram-studio management_table.py'})
    plt.close(fig)
    (output / f'{stem}.input.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    meta['matplotlib_version'] = matplotlib.__version__
    meta['scope'] = '验证输入结构、显式状态、计算与追踪关系；不把模拟记录或主观权重冒充现场事实'
    (output / f'{stem}.calculation.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    qa = {'mode': data['mode'], 'errors': [], 'warnings': [], 'layout_issues': [],
          'checks': ['input schema', 'mode-specific invariants', 'finite calculations', 'SVG and PNG generated'],
          'visual_review': 'pending; open the actual SVG/PNG before acceptance'}
    (output / f'{stem}.qa.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2) + '\n')
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input'); parser.add_argument('--out', required=True); parser.add_argument('--stem')
    args = parser.parse_args(); source = Path(args.input)
    try:
        print(json.dumps(render(json.loads(source.read_text()), args.out, args.stem or source.stem), ensure_ascii=False))
    except (KeyError, ValueError, ImportError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
