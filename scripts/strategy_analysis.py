#!/usr/bin/env python3
"""Validate and render market, product, strategy, competition and force-field models."""
from __future__ import annotations

import argparse
import json
import math
import textwrap
from collections import defaultdict
from pathlib import Path


INK = '#30302D'
MUTED = '#6D6A63'
BG = '#F1EFEB'
PAPER = '#FAF9F6'
GRID = '#D8D3C8'
GREEN = '#58705A'
BLUE = '#657487'
AMBER = '#C1965B'
RED = '#A65448'
COLORS = [GREEN, BLUE, AMBER, RED, '#80706A']


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')
    _need(data.get('data_status') in {'simulated', 'observed', 'mixed'}, 'data_status required')


def _rows(data, key):
    rows = data.get(key)
    _need(isinstance(rows, list) and rows, f'{key} required')
    ids = [row.get('id') for row in rows]
    _need(all(isinstance(value, str) and value.strip() for value in ids), f'{key} ids required')
    _unique(ids, f'{key} ids must be unique')
    return rows


def _market(data):
    _base(data, 'market-map')
    _need(data.get('market_scope') and data.get('as_of') and data.get('evidence_basis'), 'market scope, date and evidence basis required')
    axes = data.get('axes', {})
    for axis in ('x', 'y'):
        item = axes.get(axis, {})
        _need(item.get('label') and item.get('low') and item.get('high'), f'{axis} axis label and endpoints required')
    entities = _rows(data, 'entities')
    for row in entities:
        _need(row.get('label') and row.get('kind') in {'self', 'competitor', 'segment'}, 'market entity label and kind required')
        _need(_finite(row.get('x')) and _finite(row.get('y')) and 0 <= row['x'] <= 100 and 0 <= row['y'] <= 100, 'market coordinates must be within 0..100')
        _need(row.get('basis') in {'observed', 'assumed'}, 'market entity basis must be observed or assumed')
        _need(row.get('evidence') if row['basis'] == 'observed' else row.get('assumption'), 'observed entities need evidence; assumed entities need assumption text')
    observed = sum(row['basis'] == 'observed' for row in entities)
    assumed = len(entities) - observed
    return {'mode': 'market-map', 'entities': len(entities), 'observed_entities': observed,
            'assumed_entities': assumed, 'market_scope': data['market_scope'], 'as_of': data['as_of'],
            'fact_assumption_separation': 'passed'}


def _product(data):
    _base(data, 'product-canvas')
    problems = _rows(data, 'problems'); hypotheses = _rows(data, 'hypotheses')
    experiments = _rows(data, 'experiments'); features = _rows(data, 'features')
    problem_ids = {row['id'] for row in problems}; hypothesis_ids = {row['id'] for row in hypotheses}; experiment_ids = {row['id'] for row in experiments}
    for row in problems:
        _need(row.get('statement') and row.get('user') and row.get('evidence'), 'each product problem needs statement, user and evidence')
    for row in hypotheses:
        _need(row.get('statement') and row.get('problem_id') in problem_ids, 'each hypothesis must link to a problem')
    for row in experiments:
        _need(row.get('hypothesis_id') in hypothesis_ids and row.get('method') and row.get('success_metric'), 'each experiment must test a hypothesis with a metric')
    for row in features:
        _need(row.get('label') and row.get('hypothesis_id') in hypothesis_ids and row.get('status') in {'candidate', 'committed', 'rejected'}, 'each feature must link to a hypothesis and declare status')
    tested = {row['hypothesis_id'] for row in experiments}
    uncovered = sorted(hypothesis_ids - tested)
    _need(not uncovered, f'every hypothesis needs an experiment: {uncovered}')
    return {'mode': 'product-canvas', 'problems': len(problems), 'hypotheses': len(hypotheses),
            'experiments': len(experiments), 'features': len(features), 'untested_hypotheses': uncovered,
            'problem_solution_separation': 'passed', 'traceability': 'passed'}


def _strategy(data):
    _base(data, 'strategy-canvas')
    evidence = _rows(data, 'evidence'); choices = _rows(data, 'choices')
    actions = _rows(data, 'actions'); metrics = _rows(data, 'metrics')
    evidence_ids = {row['id'] for row in evidence}; choice_ids = {row['id'] for row in choices}; action_ids = {row['id'] for row in actions}
    for row in evidence:
        _need(row.get('finding') and row.get('source'), 'strategy evidence finding and source required')
    for row in choices:
        _need(row.get('statement') and row.get('give_up') and isinstance(row.get('evidence_ids'), list) and row['evidence_ids'], 'each strategy choice needs statement, give-up and evidence links')
        _need(set(row['evidence_ids']) <= evidence_ids, 'strategy choice references unknown evidence')
    for row in actions:
        _need(row.get('label') and row.get('owner') and row.get('choice_id') in choice_ids, 'each strategy action needs label, owner and choice link')
    for row in metrics:
        _need(row.get('label') and row.get('unit') and row.get('action_id') in action_ids, 'each strategy metric needs label, unit and action link')
        _need(_finite(row.get('baseline')) and _finite(row.get('target')), 'strategy metric baseline and target must be finite')
    measured_actions = {row['action_id'] for row in metrics}
    unmeasured = sorted(action_ids - measured_actions)
    _need(not unmeasured, f'every action needs a metric: {unmeasured}')
    return {'mode': 'strategy-canvas', 'evidence': len(evidence), 'choices': len(choices),
            'actions': len(actions), 'metrics': len(metrics), 'unmeasured_actions': unmeasured,
            'all_choices_have_giveups': 'passed', 'evidence_to_action_traceability': 'passed'}


def _competition(data):
    _base(data, 'competitive-analysis')
    _need(data.get('market_scope') and data.get('as_of') and data.get('scoring_scale'), 'competition scope, date and scale required')
    low, high = data['scoring_scale']
    _need(_finite(low) and _finite(high) and low < high, 'scoring scale must be finite and increasing')
    dimensions = _rows(data, 'dimensions'); competitors = _rows(data, 'competitors')
    dimension_ids = {row['id'] for row in dimensions}
    weights = []
    for row in dimensions:
        _need(row.get('label') and row.get('direction') in {'higher-better', 'lower-better'}, 'dimension label and direction required')
        _need(_finite(row.get('weight')) and row['weight'] > 0, 'dimension weights must be positive')
        _need(row.get('basis'), 'dimension scoring basis required'); weights.append(row['weight'])
    _need(math.isclose(sum(weights), 1.0, abs_tol=1e-9), 'dimension weights must sum to 1')
    totals = {}
    normalized = {}
    for competitor in competitors:
        _need(competitor.get('label') and competitor.get('source') and competitor.get('as_of') == data['as_of'], 'competitor label, source and matching date required')
        scores = competitor.get('scores', {})
        _need(set(scores) == dimension_ids, 'each competitor must score every dimension exactly once')
        total = 0.0; normalized[competitor['id']] = {}
        for dimension in dimensions:
            value = scores[dimension['id']]
            _need(_finite(value) and low <= value <= high, 'competition scores must fit the declared scale')
            norm = (value-low)/(high-low)
            if dimension['direction'] == 'lower-better': norm = 1-norm
            normalized[competitor['id']][dimension['id']] = norm
            total += norm*dimension['weight']
        totals[competitor['id']] = total
    ranking = sorted(totals, key=lambda item: (-totals[item], item))
    return {'mode': 'competitive-analysis', 'dimensions': len(dimensions), 'competitors': len(competitors),
            'weight_sum': sum(weights), 'normalized_scores': normalized, 'weighted_totals': totals,
            'ranking': ranking, 'winner': ranking[0], 'same_scope_and_date': 'passed',
            'transparent_scoring_basis': 'passed'}


def _force(data):
    _base(data, 'force-field')
    _need(data.get('change_goal') and data.get('evidence_basis'), 'force-field goal and evidence basis required')
    forces = _rows(data, 'forces')
    scored = []
    for row in forces:
        _need(row.get('label') and row.get('direction') in {'driving', 'restraining'} and row.get('evidence'), 'force label, direction and evidence required')
        has_strength = 'strength' in row
        scored.append(has_strength)
        if has_strength:
            _need(isinstance(row['strength'], int) and 1 <= row['strength'] <= 5, 'force strength must be an integer from 1 to 5')
    _need(all(scored) or not any(scored), 'force strengths must be supplied for every factor or none')
    drivers = [row for row in forces if row['direction'] == 'driving']; restraints = [row for row in forces if row['direction'] == 'restraining']
    _need(drivers and restraints, 'force-field needs driving and restraining factors')
    result = {'mode': 'force-field', 'drivers': len(drivers), 'restraints': len(restraints),
              'scoring_mode': 'scored' if all(scored) else 'qualitative', 'directions_explicit': 'passed'}
    if all(scored):
        result.update(driver_total=sum(row['strength'] for row in drivers),
                      restraint_total=sum(row['strength'] for row in restraints),
                      net_force=sum(row['strength'] for row in drivers)-sum(row['strength'] for row in restraints))
    return result


ANALYZERS = {'market-map': _market, 'product-canvas': _product, 'strategy-canvas': _strategy,
             'competitive-analysis': _competition, 'force-field': _force}


def analyze(data):
    _need(data.get('mode') in ANALYZERS, 'unsupported strategy-analysis mode')
    result = ANALYZERS[data['mode']](data)
    result['data_status'] = data['data_status']
    result['assumptions'] = data.get('assumptions', [])
    return result


def _wrap(value, width=20):
    return '\n'.join(textwrap.wrap(str(value), width=width, break_long_words=True, break_on_hyphens=False))


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
                                 'axes.unicode_minus': False, 'svg.fonttype': 'none',
                                 'svg.hashsalt': 'diagram-studio-strategy-analysis-v1'})
    fig = plt.figure(figsize=(12, 7.5), facecolor=BG)
    ax = fig.add_axes((.05, .07, .90, .84)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    fig.text(.05, .955, data['title'], fontsize=22, color=INK, weight='medium', va='top')
    fig.text(.05, .915, data.get('subtitle', ''), fontsize=10.5, color=MUTED, va='top')
    fig.text(.95, .955, data['mode'].upper().replace('-', '  '), fontsize=8.5, color=MUTED, ha='right', va='top')
    return fig, ax


def _card(ax, x, y, w, h, title, lines, accent=GREEN, title_size=10, text_size=8.3):
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((x, y), w, h, facecolor=PAPER, edgecolor=GRID, linewidth=1))
    ax.add_patch(Rectangle((x, y+h-.012), w, .012, facecolor=accent, edgecolor='none'))
    ax.text(x+.018, y+h-.035, title, fontsize=title_size, color=INK, weight='medium', va='top')
    ax.text(x+.018, y+h-.073, '\n'.join(lines), fontsize=text_size, color=MUTED, va='top', linespacing=1.5)


def _render_market(data, meta):
    fig, ax = _figure(data); axes = data['axes']
    left, bottom, width, height = .10, .14, .72, .70
    ax.plot([left,left+width],[bottom,bottom],color=INK,linewidth=1.2); ax.plot([left,left],[bottom,bottom+height],color=INK,linewidth=1.2)
    ax.plot([left+width/2,left+width/2],[bottom,bottom+height],color=GRID,linewidth=.8,linestyle='--')
    ax.plot([left,left+width],[bottom+height/2,bottom+height/2],color=GRID,linewidth=.8,linestyle='--')
    ax.text(left, bottom-.055, axes['x']['low'], fontsize=8.5, color=MUTED); ax.text(left+width,bottom-.055,axes['x']['high'],ha='right',fontsize=8.5,color=MUTED)
    ax.text(left+width/2,bottom-.09,axes['x']['label'],ha='center',fontsize=10,color=INK)
    ax.text(left-.035,bottom,axes['y']['low'],ha='right',fontsize=8.5,color=MUTED); ax.text(left-.035,bottom+height,axes['y']['high'],ha='right',fontsize=8.5,color=MUTED)
    ax.text(left-.075,bottom+height/2,axes['y']['label'],ha='center',va='center',rotation=90,fontsize=10,color=INK)
    markers={'self':'*','competitor':'o','segment':'s'}; labels={'self':'本方案','competitor':'竞争对象','segment':'用户细分'}
    for row in data['entities']:
        x=left+row['x']/100*width; y=bottom+row['y']/100*height; color=GREEN if row['basis']=='observed' else AMBER
        ax.scatter([x],[y],s=125 if row['kind']=='self' else 80,marker=markers[row['kind']],color=color,edgecolor=PAPER,linewidth=1.2,zorder=3)
        ax.text(x+.012,y+.014,row['label'],fontsize=8.3,color=INK)
    _card(ax,.85,.45,.14,.39,'口径与证据',[f"范围：{_wrap(data['market_scope'],11)}",f"时点：{data['as_of']}",f"观察 {meta['observed_entities']} 项",f"假设 {meta['assumed_entities']} 项"],BLUE,text_size=7.8)
    ax.text(.85,.38,'图例',fontsize=9.5,weight='medium'); ax.text(.85,.34,'绿色：观察\n琥珀色：假设',fontsize=7.8,color=MUTED,va='top')
    ax.text(.10,.055,'本方案：星形 · 竞争对象：圆形 · 用户细分：方形',fontsize=8.5,color=MUTED)
    return fig


def _render_product(data, meta):
    fig, ax = _figure(data)
    status_labels={'candidate':'候选','committed':'已承诺','rejected':'已否决'}
    _card(ax,.00,.52,.29,.38,'问题与用户',[f"{r['id']} · {_wrap(r['statement'],20)}\n用户：{r['user']}\n证据：{r['evidence']}" for r in data['problems']],RED,text_size=7.5)
    _card(ax,.31,.52,.29,.38,'价值假设',[f"{r['id']} ← {r['problem_id']}\n{_wrap(r['statement'],21)}" for r in data['hypotheses']],AMBER,text_size=7.7)
    _card(ax,.62,.52,.38,.38,'实验与成功指标',[f"{r['id']} → {r['hypothesis_id']} · {r['method']}\n指标：{r['success_metric']}" for r in data['experiments']],BLUE,text_size=7.6)
    _card(ax,.00,.11,1.00,.31,'功能候选（必须回指假设）',[f"{r['id']} · {r['label']} → {r['hypothesis_id']} · {status_labels[r['status']]}" for r in data['features']],GREEN,text_size=8.3)
    ax.annotate('',xy=(.31,.70),xytext=(.29,.70),arrowprops={'arrowstyle':'->','color':MUTED}); ax.annotate('',xy=(.62,.70),xytext=(.60,.70),arrowprops={'arrowstyle':'->','color':MUTED})
    ax.text(.00,.045,f"问题 {meta['problems']} · 假设 {meta['hypotheses']} · 实验 {meta['experiments']} · 未测试假设 0",fontsize=9,color=MUTED)
    return fig


def _render_strategy(data, meta):
    fig, ax = _figure(data)
    columns=[('证据',data['evidence'],RED,lambda r:f"{r['id']} · {_wrap(r['finding'],21)}\n来源：{r['source']}"),('选择与放弃',data['choices'],AMBER,lambda r:f"{r['id']} · {_wrap(r['statement'],20)}\n放弃：{_wrap(r['give_up'],18)}\n依据：{', '.join(r['evidence_ids'])}"),('行动',data['actions'],BLUE,lambda r:f"{r['id']} → {r['choice_id']}\n{_wrap(r['label'],21)} · {r['owner']}"),('衡量',data['metrics'],GREEN,lambda r:f"{r['id']} → {r['action_id']}\n{r['label']}：{r['baseline']:g}→{r['target']:g}{r['unit']}")]
    for i,(title,rows,color,fmt) in enumerate(columns):
        x=i*.25; _card(ax,x,.14,.235,.73,title,[fmt(row) for row in rows],color,text_size=7.5)
        if i<3: ax.annotate('',xy=(x+.25,.50),xytext=(x+.235,.50),arrowprops={'arrowstyle':'->','color':MUTED})
    ax.text(.00,.055,'证据 → 选择（含放弃项）→ 行动（含责任人）→ 衡量（含基线与目标）',fontsize=9,color=MUTED)
    return fig


def _render_competition(data, meta):
    from matplotlib.patches import Rectangle
    fig, ax = _figure(data); dims=data['dimensions']; competitors=data['competitors']
    x0=.02; ytop=.85; label_w=.22; cell_w=.145; row_h=.105
    headers=['对象']+[f"{row['label']}\n权重 {row['weight']:.0%}" for row in dims]+['加权总分']
    widths=[label_w]+[cell_w]*len(dims)+[.15]; x=x0
    for label,w in zip(headers,widths):
        ax.add_patch(Rectangle((x,ytop),w,row_h,facecolor=INK,edgecolor=BG)); ax.text(x+w/2,ytop+row_h/2,label,ha='center',va='center',fontsize=8,color='white'); x+=w
    for i,row in enumerate(competitors):
        y=ytop-(i+1)*row_h; values=[row['label']]+[row['scores'][d['id']] for d in dims]+[f"{meta['weighted_totals'][row['id']]:.3f}"]
        x=x0
        for j,(value,w) in enumerate(zip(values,widths)):
            fill='#E8EDE7' if row['id']==meta['winner'] else PAPER
            ax.add_patch(Rectangle((x,y),w,row_h,facecolor=fill,edgecolor=GRID,linewidth=.8)); ax.text(x+.012 if j==0 else x+w/2,y+row_h/2,str(value),ha='left' if j==0 else 'center',va='center',fontsize=8.4,color=INK); x+=w
    basis=' · '.join(f"{d['label']}：{d['basis']}" for d in dims); names={row['id']:row['label'] for row in competitors}
    _card(ax,.02,.13,.96,.23,'评分口径',[f"范围：{data['market_scope']} · 时点：{data['as_of']} · 量表：{data['scoring_scale'][0]}–{data['scoring_scale'][1]}",_wrap(basis,100),f"排名：{' > '.join(names[item] for item in meta['ranking'])}（按方向归一化后加权）"],BLUE,text_size=8.2)
    ax.text(.02,.055,'低优维度在归一化时反向处理；原始分、权重、口径和来源均保留。',fontsize=9,color=MUTED)
    return fig


def _render_force(data, meta):
    from matplotlib.patches import FancyArrowPatch, Rectangle
    fig, ax = _figure(data); drivers=[r for r in data['forces'] if r['direction']=='driving']; restraints=[r for r in data['forces'] if r['direction']=='restraining']
    ax.add_patch(Rectangle((.39,.16),.22,.70,facecolor=PAPER,edgecolor=INK,linewidth=1.2)); ax.text(.50,.51,_wrap(data['change_goal'],10),ha='center',va='center',fontsize=11,color=INK,weight='medium')
    count=max(len(drivers),len(restraints)); ys=[.77-i*.17 for i in range(count)]
    for row,y in zip(drivers,ys):
        ax.text(.02,y,_wrap(row['label'],24),fontsize=9,color=INK,va='center'); strength=row.get('strength'); width=.8+(strength or 1)*.35
        ax.add_patch(FancyArrowPatch((.17,y),(.38,y),arrowstyle='-|>',mutation_scale=14,linewidth=width,color=GREEN)); ax.text(.19,y-.045,row['evidence'],fontsize=7.4,color=MUTED)
        if strength: ax.text(.35,y+.025,str(strength),fontsize=8,color=GREEN)
    for row,y in zip(restraints,ys):
        ax.text(.98,y,_wrap(row['label'],24),fontsize=9,color=INK,va='center',ha='right'); strength=row.get('strength'); width=.8+(strength or 1)*.35
        ax.add_patch(FancyArrowPatch((.83,y),(.62,y),arrowstyle='-|>',mutation_scale=14,linewidth=width,color=RED)); ax.text(.81,y-.045,row['evidence'],fontsize=7.4,color=MUTED,ha='right')
        if strength: ax.text(.65,y+.025,str(strength),fontsize=8,color=RED)
    mode_label={'scored':'评分','qualitative':'定性'}[meta['scoring_mode']]
    ax.text(.02,.055,f"驱动力 {meta['drivers']} 项 / {meta.get('driver_total','定性')} · 阻力 {meta['restraints']} 项 / {meta.get('restraint_total','定性')} · 模式：{mode_label}",fontsize=9,color=MUTED)
    return fig


RENDERERS={'market-map':_render_market,'product-canvas':_render_product,'strategy-canvas':_render_strategy,
           'competitive-analysis':_render_competition,'force-field':_render_force}


def render(data, output, stem=None):
    import matplotlib
    import matplotlib.pyplot as plt
    meta=analyze(data); output=Path(output); output.mkdir(parents=True,exist_ok=True); stem=stem or data.get('id') or data['mode']
    fig=RENDERERS[data['mode']](data,meta)
    fig.savefig(output/f'{stem}.svg',facecolor=BG,metadata={'Date':None})
    fig.savefig(output/f'{stem}.png',facecolor=BG,dpi=150,metadata={'Software':'diagram-studio strategy_analysis.py'})
    plt.close(fig)
    (output/f'{stem}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    meta['matplotlib_version']=matplotlib.__version__; meta['validation_scope']='验证本批次事实与假设、问题实验、战略取舍、竞争口径和力场方向；不把模拟内容冒充实际决策'
    (output/f'{stem}.calculation.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    qa={'mode':data['mode'],'errors':[],'warnings':[],'layout_issues':[],
        'checks':['input schema','mode-specific semantics','finite values','SVG and PNG generated'],
        'visual_review':'pending; open the actual SVG/PNG before acceptance'}
    (output/f'{stem}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('input'); parser.add_argument('--out',required=True); parser.add_argument('--stem')
    args=parser.parse_args(); source=Path(args.input)
    try: print(json.dumps(render(json.loads(source.read_text()),args.out,args.stem or source.stem),ensure_ascii=False))
    except (KeyError,ValueError,ImportError) as error: parser.error(str(error))


if __name__=='__main__': main()
