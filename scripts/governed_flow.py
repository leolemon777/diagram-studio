#!/usr/bin/env python3
"""Validate and render EPC, audit, program and sitemap models with editable DOT."""
from __future__ import annotations

import argparse
import json
import math
import textwrap
from collections import defaultdict, deque
from pathlib import Path


BG = '#F1EFEB'
PAPER = '#FAF9F6'
INK = '#30302D'
MUTED = '#6D6A63'
GRID = '#CFC8BD'
ACCENT = '#AC6046'
GREEN = '#58705A'
BLUE = '#657487'
AMBER = '#C1965B'
RED = '#A65448'


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _node_index(data):
    nodes = data.get('nodes')
    _need(isinstance(nodes, list) and nodes, 'nodes required')
    ids = [node.get('id') for node in nodes]
    _need(all(ids), 'every node needs id')
    _unique(ids, 'node ids must be unique')
    _need(all(isinstance(node.get('label'), str) and node['label'].strip() for node in nodes), 'every node needs label')
    return {node['id']: node for node in nodes}


def _edges(data, nodes):
    edges = data.get('edges')
    _need(isinstance(edges, list) and edges, 'edges required')
    pairs = []
    for edge in edges:
        source, target = edge.get('source'), edge.get('target')
        _need(source in nodes and target in nodes, 'edge references unknown node')
        _need(source != target, 'self edges are not allowed')
        pairs.append((source, target, edge.get('label', '')))
    _unique([(source, target, label) for source, target, label in pairs], 'duplicate edges are not allowed')
    return edges


def _adjacency(nodes, edges):
    forward = {node: [] for node in nodes}; reverse = {node: [] for node in nodes}
    for edge in edges:
        forward[edge['source']].append(edge['target']); reverse[edge['target']].append(edge['source'])
    return forward, reverse


def _reachable(start, graph):
    seen = set(); queue = deque([start])
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node); queue.extend(graph[node])
    return seen


def _strong_components(nodes, forward, reverse):
    seen = set(); order = []
    def visit(node):
        if node in seen: return
        seen.add(node)
        for target in forward[node]: visit(target)
        order.append(node)
    for node in nodes: visit(node)
    seen.clear(); result = []
    def collect(node, part):
        if node in seen: return
        seen.add(node); part.add(node)
        for source in reverse[node]: collect(source, part)
    for node in reversed(order):
        if node not in seen:
            part = set(); collect(node, part); result.append(part)
    return result


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')


def _epc(data):
    _base(data, 'epc')
    nodes = _node_index(data); edges = _edges(data, nodes)
    allowed = {'event', 'function', 'gateway'}
    _need(all(node.get('type') in allowed for node in nodes.values()), 'unknown EPC node type')
    for node in nodes.values():
        if node['type'] == 'gateway':
            _need(node.get('operator') in {'AND', 'XOR', 'OR'}, 'EPC gateway needs AND, XOR or OR operator')
    forward, reverse = _adjacency(nodes, edges)
    starts = [node for node in nodes if not reverse[node]]; ends = [node for node in nodes if not forward[node]]
    _need(starts and ends and all(nodes[node]['type'] == 'event' for node in starts + ends), 'EPC starts and ends must be events')
    for edge in edges:
        source, target = nodes[edge['source']], nodes[edge['target']]
        if source['type'] != 'gateway' and target['type'] != 'gateway':
            _need({source['type'], target['type']} == {'event', 'function'}, 'EPC events and functions must alternate')
        _need(not (source['type'] == target['type'] == 'gateway'), 'EPC gateways cannot connect directly')
    for node_id, node in nodes.items():
        if node['type'] == 'gateway':
            _need(len(forward[node_id]) > 1 or len(reverse[node_id]) > 1, 'EPC gateway must split or join')
    reached = set().union(*(_reachable(start, forward) for start in starts))
    _need(reached == set(nodes), 'all EPC nodes must be reachable from a start event')
    return {'mode': 'epc', 'nodes': len(nodes), 'edges': len(edges), 'start_events': starts,
            'end_events': ends, 'gateways': {node: nodes[node]['operator'] for node in nodes if nodes[node]['type'] == 'gateway'},
            'alternation': 'passed'}


def _audit(data):
    _base(data, 'audit')
    nodes = _node_index(data); edges = _edges(data, nodes)
    allowed = {'start', 'action', 'decision', 'remediation', 'review', 'end'}
    _need(all(node.get('type') in allowed for node in nodes.values()), 'unknown audit node type')
    starts = [node for node in nodes if nodes[node]['type'] == 'start']; ends = [node for node in nodes if nodes[node]['type'] == 'end']
    _need(len(starts) == 1 and ends, 'audit needs exactly one start and at least one end')
    evidence = []
    for node in nodes.values():
        if node['type'] in {'action', 'decision', 'remediation', 'review'}:
            _need(node.get('owner'), 'audit work nodes need an owner')
        if node['type'] == 'decision':
            _need(node.get('evidence_id') and node.get('basis'), 'audit decisions need evidence_id and basis')
            evidence.append(node['evidence_id'])
    _unique(evidence, 'audit evidence ids must be unique')
    forward, reverse = _adjacency(nodes, edges)
    _need(_reachable(starts[0], forward) == set(nodes), 'all audit nodes must be reachable')
    for node_id, node in nodes.items():
        if node['type'] != 'decision': continue
        outgoing = [edge for edge in edges if edge['source'] == node_id]
        _need({edge.get('label') for edge in outgoing} == {'通过', '不通过'}, 'each audit decision needs 通过 and 不通过 branches')
        failed = next(edge for edge in outgoing if edge['label'] == '不通过')
        _need(nodes[failed['target']]['type'] == 'remediation', 'audit 不通过 branch must enter remediation')
        remedies = _reachable(failed['target'], forward)
        _need(any(nodes[item]['type'] == 'review' for item in remedies), 'audit remediation must reach review')
        _need(node_id in remedies, 'audit review path must return to the decision')
    reachable_to_end = set().union(*(_reachable(end, reverse) for end in ends))
    _need(reachable_to_end == set(nodes), 'every audit node must be able to reach an end')
    return {'mode': 'audit', 'nodes': len(nodes), 'edges': len(edges), 'decisions': len(evidence),
            'evidence_ids': evidence, 'remediation_review_loops': 'passed'}


def _program(data):
    _base(data, 'program')
    nodes = _node_index(data); edges = _edges(data, nodes)
    allowed = {'start', 'input', 'process', 'decision', 'output', 'end'}
    _need(all(node.get('type') in allowed for node in nodes.values()), 'unknown program node type')
    starts = [node for node in nodes if nodes[node]['type'] == 'start']; ends = [node for node in nodes if nodes[node]['type'] == 'end']
    _need(len(starts) == 1 and ends, 'program flow needs exactly one start and at least one end')
    forward, reverse = _adjacency(nodes, edges)
    _need(_reachable(starts[0], forward) == set(nodes), 'all program nodes must be reachable')
    reachable_to_end = set().union(*(_reachable(end, reverse) for end in ends))
    _need(reachable_to_end == set(nodes), 'every program node must be able to reach an end')
    for node_id, node in nodes.items():
        if node['type'] == 'decision':
            outgoing = [edge for edge in edges if edge['source'] == node_id]
            _need({edge.get('label') for edge in outgoing} == {'是', '否'}, 'program decisions need 是 and 否 branches')
            _need(node.get('condition'), 'program decision needs a testable condition')
    loops = []
    for part in _strong_components(nodes, forward, reverse):
        if len(part) <= 1: continue
        exits = [(source, target) for source in part for target in forward[source] if target not in part]
        _need(exits, 'every program loop must have an exit edge')
        loops.append({'nodes': sorted(part), 'exits': exits})
    return {'mode': 'program', 'nodes': len(nodes), 'edges': len(edges), 'decisions': sum(node['type'] == 'decision' for node in nodes.values()),
            'loops': loops, 'all_paths_can_reach_end': 'passed'}


def _sitemap(data):
    _base(data, 'sitemap')
    pages = data.get('pages')
    _need(isinstance(pages, list) and pages, 'sitemap pages required')
    ids = [page.get('id') for page in pages]; _need(all(ids), 'every page needs id'); _unique(ids, 'page ids must be unique')
    by_id = {page['id']: page for page in pages}
    urls = [page.get('url') for page in pages]
    _need(all(isinstance(url, str) and url.startswith('/') for url in urls), 'every sitemap page needs a root-relative URL')
    _unique(urls, 'sitemap URLs must be unique')
    _need(all(page.get('label') and page.get('access') in {'public', 'internal', 'admin'} for page in pages), 'every page needs label and access')
    roots = [page['id'] for page in pages if page.get('parent') is None]
    _need(len(roots) == 1, 'sitemap needs exactly one root page')
    children = defaultdict(list)
    for page in pages:
        parent = page.get('parent')
        if parent is not None:
            _need(parent in by_id and parent != page['id'], 'sitemap parent references unknown page')
            children[parent].append(page['id'])
    hierarchy = {page_id: children[page_id] for page_id in ids}
    _need(_reachable(roots[0], hierarchy) == set(ids), 'sitemap hierarchy must be one connected tree')
    cross_links = data.get('cross_links', [])
    seen = set()
    for link in cross_links:
        pair = (link.get('source'), link.get('target'))
        _need(pair[0] in by_id and pair[1] in by_id and pair[0] != pair[1], 'cross-link references unknown page')
        _need(by_id[pair[1]].get('parent') != pair[0], 'hierarchy edges must not be repeated as cross-links')
        _need(pair not in seen, 'duplicate cross-link'); seen.add(pair)
    return {'mode': 'sitemap', 'pages': len(pages), 'root': roots[0], 'hierarchy_edges': len(pages) - 1,
            'cross_links': len(cross_links), 'unique_urls': 'passed', 'access_counts': {access: sum(page['access'] == access for page in pages) for access in ('public','internal','admin')}}


ANALYZERS = {'epc': _epc, 'audit': _audit, 'program': _program, 'sitemap': _sitemap}


def analyze(data):
    mode = data.get('mode'); _need(mode in ANALYZERS, 'mode must be epc, audit, program or sitemap')
    result = ANALYZERS[mode](data); result['data_status'] = data.get('data_status', 'unspecified'); result['assumptions'] = data.get('assumptions', [])
    return result


def _q(value):
    return json.dumps(str(value), ensure_ascii=False)


def _node_style(mode, node):
    node_type = node.get('type', 'page')
    if mode == 'epc':
        return {'event': ('ellipse', '#E7E1D8', ACCENT), 'function': ('box', PAPER, GREEN), 'gateway': ('diamond', '#ECE7DF', BLUE)}[node_type]
    if mode == 'audit':
        return {'start': ('circle', GREEN, GREEN), 'end': ('doublecircle', INK, INK), 'action': ('box', PAPER, GREEN),
                'decision': ('diamond', '#ECE7DF', ACCENT), 'remediation': ('box', '#EFE0DB', RED), 'review': ('box', '#E3E8E1', GREEN)}[node_type]
    if mode == 'program':
        return {'start': ('circle', GREEN, GREEN), 'end': ('doublecircle', INK, INK), 'input': ('parallelogram', '#E2E7EB', BLUE),
                'output': ('parallelogram', '#E2E7EB', BLUE), 'process': ('box', PAPER, GREEN), 'decision': ('diamond', '#ECE7DF', ACCENT)}[node_type]
    access = node.get('access')
    return ('box', {'public': PAPER, 'internal': '#E2E7EB', 'admin': '#EFE0DB'}[access], {'public': GREEN, 'internal': BLUE, 'admin': RED}[access])


def build_dot(data, meta):
    mode = data['mode']; rankdir = 'TB' if mode == 'sitemap' else 'LR'
    title_label = data['title'] + '\n' + data.get('subtitle', '')
    lines = [
        'digraph G {',
        f'graph [rankdir={rankdir}, bgcolor={_q(BG)}, pad="0.35", nodesep="0.42", ranksep="0.65", splines=polyline, fontname="Heiti SC", labelloc=t, label={_q(title_label)}, fontsize=22, fontcolor={_q(INK)}];',
        f'node [fontname="Heiti SC", fontsize=11, fontcolor={_q(INK)}, style="rounded,filled", penwidth=1.4, margin="0.13,0.08"];',
        f'edge [fontname="Heiti SC", fontsize=9.5, color={_q(MUTED)}, fontcolor={_q(MUTED)}, arrowsize=0.72, penwidth=1.15];',
    ]
    source_nodes = data['pages'] if mode == 'sitemap' else data['nodes']
    for node in source_nodes:
        shape, fill, stroke = _node_style(mode, node)
        label = node['label']
        if mode == 'epc' and node['type'] == 'gateway': label = node['operator']
        elif mode == 'audit' and node['type'] == 'decision': label += f"\n[{node['evidence_id']}]\n{node['basis']}"
        elif mode == 'program' and node['type'] == 'decision': label += f"\n{node['condition']}"
        elif mode == 'sitemap': label += f"\n{node['url']}\n{node['access']}"
        extra = ', width=0.28, height=0.28, fixedsize=true, label=""' if node.get('type') in {'start','end'} else ''
        lines.append(f'{_q(node["id"])} [label={_q(label)}, shape={shape}, fillcolor={_q(fill)}, color={_q(stroke)}{extra}];')
    if mode == 'sitemap':
        for page in data['pages']:
            if page.get('parent') is not None:
                lines.append(f'{_q(page["parent"])} -> {_q(page["id"])} [color={_q(GREEN)}];')
        for link in data.get('cross_links', []):
            lines.append(f'{_q(link["source"])} -> {_q(link["target"])} [style=dashed, color={_q(BLUE)}, constraint=false, label={_q(link.get("label","跨页"))}];')
    else:
        nodes = {node['id']: node for node in data['nodes']}
        for edge in data['edges']:
            attrs = []
            if edge.get('label'): attrs.append('label='+_q(edge['label']))
            if mode == 'audit' and edge.get('label') == '不通过': attrs += ['color='+_q(RED), 'fontcolor='+_q(RED)]
            if mode == 'program' and edge.get('loop'): attrs += ['color='+_q(BLUE), 'fontcolor='+_q(BLUE)]
            lines.append(f'{_q(edge["source"])} -> {_q(edge["target"])}' + (' ['+', '.join(attrs)+']' if attrs else '') + ';')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def _flow_positions(data):
    nodes = {node['id']: node for node in data['nodes']}
    forward, reverse = _adjacency(nodes, data['edges'])
    starts = [node for node in nodes if not reverse[node]]
    distance = {node: 0 for node in starts}; queue = deque(starts)
    while queue:
        source = queue.popleft()
        for target in forward[source]:
            proposal = distance[source] + 1
            if target not in distance or proposal < distance[target]:
                distance[target] = proposal; queue.append(target)
    ranks = defaultdict(list)
    for node in nodes: ranks[distance[node]].append(node)
    last = max(ranks); positions = {}
    for rank in sorted(ranks):
        members = ranks[rank]
        ys = [0.5] if len(members) == 1 else [0.78 - index * 0.56 / (len(members) - 1) for index in range(len(members))]
        x = 0.08 + rank * 0.83 / max(1, last)
        for node, y in zip(members, ys): positions[node] = (x, y)
    return positions


def _sitemap_positions(data):
    children = defaultdict(list)
    root = next(page['id'] for page in data['pages'] if page.get('parent') is None)
    for page in data['pages']:
        if page.get('parent') is not None: children[page['parent']].append(page['id'])
    slots = {}; counter = [0]
    def assign(node, depth):
        if not children[node]:
            slots[node] = (counter[0], depth); counter[0] += 1; return slots[node][0]
        values = [assign(child, depth + 1) for child in children[node]]
        slots[node] = (sum(values) / len(values), depth); return slots[node][0]
    assign(root, 0); max_slot = max(1, counter[0] - 1); max_depth = max(depth for _, depth in slots.values())
    return {node: (0.09 + slot * 0.82 / max_slot, 0.84 - depth * 0.64 / max(1, max_depth)) for node, (slot, depth) in slots.items()}


def _display_label(mode, node):
    if mode == 'epc' and node['type'] == 'gateway': return node['operator']
    if mode == 'audit' and node['type'] == 'decision': return node['label'] + f"\n[{node['evidence_id']}]\n" + node['basis']
    if mode == 'program' and node['type'] == 'decision': return node['label'] + '\n' + node['condition']
    if mode == 'sitemap': return node['label'] + '\n' + node['url'] + '\n' + node['access']
    return node['label']


def _wrapped(text, width=11):
    lines = []
    for raw in text.split('\n'):
        lines.extend(textwrap.wrap(raw, width=width, break_long_words=True, break_on_hyphens=False) or [''])
    return '\n'.join(lines)


def _draw_node(ax, mode, node, x, y):
    from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon
    shape, fill, stroke = _node_style(mode, node); label = _display_label(mode, node)
    if node.get('type') in {'start', 'end'}:
        ax.add_patch(Circle((x, y), 0.020, facecolor=stroke, edgecolor=stroke, linewidth=1.4, zorder=3))
        if node.get('type') == 'end': ax.add_patch(Circle((x, y), 0.027, fill=False, edgecolor=stroke, linewidth=1.3, zorder=3))
        return
    if shape == 'ellipse':
        patch = Ellipse((x, y), 0.145, 0.105, facecolor=fill, edgecolor=stroke, linewidth=1.4, zorder=3)
    elif shape == 'diamond':
        width, height = (0.105, 0.075) if node.get('type') == 'gateway' else (0.155, 0.145)
        patch = Polygon([(x, y + height / 2), (x + width / 2, y), (x, y - height / 2), (x - width / 2, y)], closed=True, facecolor=fill, edgecolor=stroke, linewidth=1.4, zorder=3)
    elif shape == 'parallelogram':
        width, height, skew = 0.15, 0.09, 0.025
        patch = Polygon([(x - width/2 + skew, y + height/2), (x + width/2, y + height/2), (x + width/2 - skew, y - height/2), (x - width/2, y - height/2)], closed=True, facecolor=fill, edgecolor=stroke, linewidth=1.4, zorder=3)
    else:
        patch = FancyBboxPatch((x - 0.075, y - 0.047), 0.15, 0.094, boxstyle='round,pad=0.008,rounding_size=0.012', facecolor=fill, edgecolor=stroke, linewidth=1.4, zorder=3)
    ax.add_patch(patch)
    wrap_width = 24 if mode == 'sitemap' else 18 if mode == 'program' and node.get('type') == 'decision' else 12 if mode == 'program' else 10
    fontsize = 7.7 if mode == 'sitemap' and any(len(line) > 18 for line in label.split('\n')) else 8.1 if '\n' in label else 9.1
    ax.text(x, y, _wrapped(label, wrap_width), ha='center', va='center', fontsize=fontsize, color=INK, zorder=4)


def _render_local(data, meta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import FancyArrowPatch
    font = Path('/System/Library/Fonts/STHeiti Light.ttc')
    if font.exists(): font_manager.fontManager.addfont(font); family = font_manager.FontProperties(fname=font).get_name()
    else: family = 'DejaVu Sans'
    matplotlib.rcParams.update({'font.family': family, 'font.size': 10, 'text.color': INK, 'svg.fonttype': 'none', 'svg.hashsalt': 'diagram-studio-governed-flow-v1'})
    fig = plt.figure(figsize=(12.8, 7.2), facecolor=BG); ax = fig.add_axes([0.04, 0.10, 0.92, 0.70]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    fig.text(0.055, 0.92, data['title'], fontsize=23, weight='medium'); fig.text(0.055, 0.862, data.get('subtitle',''), fontsize=10.5, color=MUTED)
    mode = data['mode']; positions = _sitemap_positions(data) if mode == 'sitemap' else _flow_positions(data)
    source_nodes = data['pages'] if mode == 'sitemap' else data['nodes']; nodes = {node['id']: node for node in source_nodes}
    if mode == 'sitemap':
        edges = [{'source': page['parent'], 'target': page['id'], 'label': '', 'kind': 'hierarchy'} for page in data['pages'] if page.get('parent') is not None]
        edges += [{**edge, 'kind': 'cross'} for edge in data.get('cross_links', [])]
    else: edges = [{**edge, 'kind': 'flow'} for edge in data['edges']]
    for edge in edges:
        x1, y1 = positions[edge['source']]; x2, y2 = positions[edge['target']]
        backward = mode != 'sitemap' and x2 <= x1
        bend = 0.82 if mode == 'program' and edge.get('loop') else 0.55
        rad = (bend if y1 <= y2 else -bend) if backward else (0.18 if edge['kind'] == 'cross' else 0)
        color = RED if mode == 'audit' and edge.get('label') == '不通过' else BLUE if edge['kind'] == 'cross' or edge.get('loop') else GREEN if edge['kind'] == 'hierarchy' else MUTED
        style = '--' if edge['kind'] == 'cross' else '-'
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=10, linewidth=1.2, color=color, linestyle=style, connectionstyle=f'arc3,rad={rad}', shrinkA=19, shrinkB=19, zorder=1))
        if edge.get('label'):
            mx, my = (x1+x2)/2, (y1+y2)/2 + (0.05 if rad >= 0 else -0.05 if rad else 0.028)
            ax.text(mx, my, edge['label'], fontsize=8.3, color=color, ha='center', va='center', bbox={'facecolor': BG, 'edgecolor': 'none', 'pad': 1.5}, zorder=2)
    for node_id, node in nodes.items(): _draw_node(ax, mode, node, *positions[node_id])
    footer = {'epc': '事件与功能交替 · 逻辑门明确', 'audit': '证据编号 · 判定依据 · 整改复核闭环', 'program': '分支可判定 · 循环可退出 · 全部路径可结束', 'sitemap': '实线：层级 · 虚线：跨页任务链接 · URL 与权限可追踪'}[mode]
    fig.text(0.055, 0.04, '模拟数据 · ' + footer, fontsize=9.5, color=MUTED)
    return fig


def render(data, output, stem=None, dot_executable='dot'):
    import matplotlib.pyplot as plt
    meta = analyze(data); output = Path(output); output.mkdir(parents=True, exist_ok=True); stem = stem or data.get('id') or data['mode']
    source = build_dot(data, meta); (output / f'{stem}.dot').write_text(source)
    fig = _render_local(data, meta)
    fig.savefig(output / f'{stem}.svg', facecolor=BG, metadata={'Date': None})
    fig.savefig(output / f'{stem}.png', facecolor=BG, dpi=150, metadata={'Software': 'diagram-studio governed_flow.py'})
    plt.close(fig)
    (output / f'{stem}.input.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    meta['renderer'] = 'built-in deterministic matplotlib layout; DOT retained as editable interchange source'
    meta['scope'] = '验证本批次图语法、连接、可达性和模式专用约束；不把模拟过程冒充现场制度或软件实现'
    (output / f'{stem}.analysis.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    qa = {'mode': data['mode'], 'errors': [], 'warnings': [], 'layout_issues': [],
          'checks': ['unique ids', 'valid references', 'mode-specific semantics', 'SVG, PNG and DOT generated'],
          'visual_review': 'pending; open the actual SVG/PNG before acceptance'}
    (output / f'{stem}.qa.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2) + '\n')
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('input'); parser.add_argument('--out', required=True); parser.add_argument('--stem'); parser.add_argument('--dot', default='dot')
    args = parser.parse_args(); source = Path(args.input)
    try: print(json.dumps(render(json.loads(source.read_text()), args.out, args.stem or source.stem, args.dot), ensure_ascii=False))
    except (KeyError, ValueError) as error: parser.error(str(error))


if __name__ == '__main__': main()
