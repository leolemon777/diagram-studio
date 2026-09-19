#!/usr/bin/env python3
"""Validate and render the final common/high-value catalog models.

The renderer is deliberately neutral: vendor names are retained as data labels,
while graphics use local vector primitives instead of proprietary icon packs.
Publication examples are content structures, not print-ready brand artwork.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
import warnings
from collections import Counter, defaultdict, deque
from pathlib import Path

SCRIPT_DIR=str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path: sys.path.insert(0,SCRIPT_DIR)
from matplotlib_quality import inspect_figure, mark_container, quality_payload

INK = '#30302D'; MUTED = '#6D6A63'; BG = '#F1EFEB'; PAPER = '#FAF9F6'; GRID = '#D8D3C8'
BLUE = '#657487'; GREEN = '#58705A'; AMBER = '#C1965B'; RED = '#A65448'; PLUM = '#80706A'; TEAL = '#527877'
PALETTE = [BLUE, GREEN, AMBER, RED, PLUM, TEAL]


SPECS = {
    'circuit-logic': ('graph', {'source', 'sensor', 'gate', 'load'}),
    'system-diagram': ('graph', {'actor', 'system', 'interface'}),
    'transit-map': ('map', set()),
    'geographic-map': ('map', set()),
    'mathematics': ('science', {'statement', 'derivation', 'result'}),
    'mechanics': ('science', {'body', 'force', 'balance'}),
    'optics': ('science', {'object', 'lens', 'image'}),
    'chemical-equation': ('science', {'reactants', 'reaction', 'products'}),
    'lab-equipment': ('science', {'equipment', 'connection', 'safety'}),
    'presentation': ('publication', {'title', 'problem', 'evidence', 'solution', 'result', 'action'}),
    'vision-mission': ('publication', {'vision', 'mission', 'principles', 'measures'}),
    'annual-report': ('publication', {'cover', 'letter', 'performance', 'operations', 'people', 'outlook'}),
    'banner': ('publication', {'brand', 'headline', 'proof', 'action'}),
    'brochure': ('publication', {'cover', 'problem', 'solution', 'proof', 'action', 'contact'}),
    'cover': ('publication', {'series', 'title', 'subtitle', 'issue'}),
    'flyer': ('publication', {'headline', 'benefit', 'details', 'action'}),
    'magazine': ('publication', {'masthead', 'lead', 'features', 'issue'}),
    'press-release': ('publication', {'headline', 'dateline', 'lead', 'quote', 'facts', 'boilerplate'}),
    'poster': ('publication', {'headline', 'visual', 'evidence', 'action'}),
    'newsletter': ('publication', {'masthead', 'lead', 'updates', 'calendar', 'contact'}),
    'business-card': ('publication', {'identity', 'role', 'contact', 'organization'}),
    'invitation': ('publication', {'occasion', 'host', 'datetime', 'venue', 'rsvp'}),
    'knowledge-card': ('publication', {'term', 'definition', 'action', 'source'}),
    'sysml-requirement': ('graph', {'requirement', 'block', 'test'}),
    'sysml-bdd': ('graph', {'block', 'value-type'}),
    'sysml-ibd': ('graph', {'part', 'port'}),
    'sysml-parametric': ('graph', {'constraint', 'value'}),
    'alicloud-architecture': ('graph', {'edge', 'network', 'compute', 'data', 'operations'}),
    'tencentcloud-architecture': ('graph', {'edge', 'network', 'compute', 'data', 'operations'}),
    'huaweicloud-architecture': ('graph', {'edge', 'network', 'compute', 'data', 'operations'}),
    'storyboard': ('storyboard', set()),
    'quality-seven-tools': ('quality', set()),
    'tqm': ('graph', {'customer', 'leadership', 'process', 'people', 'measurement', 'improvement'}),
}

PUBLICATION_MODES = {m for m, (t, _) in SPECS.items() if t == 'publication'}
CLOUD_MODES = {'alicloud-architecture', 'tencentcloud-architecture', 'huaweicloud-architecture'}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _ids(rows, key):
    _need(isinstance(rows, list), f'{key} must be a list')
    values = [r.get('id') for r in rows]
    _need(all(isinstance(v, str) and v.strip() for v in values), f'{key} ids required')
    _need(len(values) == len(set(values)), f'{key} ids must be unique')
    return set(values)


def _point(value):
    _need(isinstance(value, list) and len(value) == 2 and all(_finite(v) and 0 <= v <= 1 for v in value), 'normalized point required')


def _rect(value):
    _need(isinstance(value, list) and len(value) == 4 and all(_finite(v) for v in value), 'normalized rectangle required')
    x, y, w, h = value
    _need(0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x + w <= 1 and y + h <= 1, 'rectangle outside normalized canvas')


def _base(data):
    mode = data.get('mode')
    _need(mode in SPECS, 'unsupported remaining catalog mode')
    template, _ = SPECS[mode]
    _need(data.get('template') == template, f'template must be {template}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')
    _need(data.get('data_status') in {'simulated', 'observed', 'mixed'}, 'data_status required')
    _need(isinstance(data.get('assumptions'), list), 'assumptions required')
    return mode, template


def _validate_metrics(data):
    rows = data.get('metrics', [])
    ids = _ids(rows, 'metrics')
    for row in rows:
        _need(row.get('label') and row.get('evidence'), 'metric label and evidence required')
        _need(isinstance(row.get('value'), (str, int, float)) and not isinstance(row.get('value'), bool), 'metric value required')
    return ids


def _validate_blocks(data, required_roles):
    rows = data.get('blocks', [])
    _ids(rows, 'blocks')
    roles = set()
    for row in rows:
        _need(row.get('label') and row.get('role'), 'block label and role required')
        _rect(row.get('rect')); roles.add(row['role'])
        _need(isinstance(row.get('content', ''), str), 'block content must be text')
    _need(required_roles <= roles, f'missing required roles: {sorted(required_roles - roles)}')
    return rows, roles


def _validate_graph(data, required_kinds):
    nodes = data.get('nodes', []); edges = data.get('edges', []); groups = data.get('groups', [])
    node_ids = _ids(nodes, 'nodes'); _ids(edges, 'edges'); group_ids = _ids(groups, 'groups')
    kinds = set()
    for group in groups:
        _need(group.get('label'), 'group label required'); _rect(group.get('rect'))
    for node in nodes:
        _need(node.get('label') and node.get('kind'), 'node label and kind required'); _point(node.get('position')); kinds.add(node['kind'])
        if node.get('group') is not None: _need(node['group'] in group_ids, 'node group reference invalid')
    _need(required_kinds <= kinds, f'missing required node kinds: {sorted(required_kinds - kinds)}')
    graph = defaultdict(list); incoming = Counter(); relations = Counter()
    for edge in edges:
        _need(edge.get('source') in node_ids and edge.get('target') in node_ids and edge['source'] != edge['target'], 'edge endpoints invalid')
        _need(edge.get('relation') and edge.get('label'), 'edge relation and label required')
        if edge.get('label_position') is not None: _point(edge['label_position'])
        graph[edge['source']].append(edge['target']); incoming[edge['target']] += 1; relations[edge['relation']] += 1
    if data.get('root'):
        _need(data['root'] in node_ids, 'graph root invalid')
        seen = {data['root']}; q = deque(seen)
        while q:
            for nxt in graph[q.popleft()]:
                if nxt not in seen: seen.add(nxt); q.append(nxt)
        _need(set(data.get('must_reach', [])) <= seen, 'declared target is not reachable from graph root')
    return nodes, edges, groups, kinds, relations, incoming


def _publication(data, required_roles):
    blocks, roles = _validate_blocks(data, required_roles)
    sheet = data.get('sheet'); _need(isinstance(sheet, dict), 'sheet required')
    _need(_finite(sheet.get('width')) and _finite(sheet.get('height')) and sheet['width'] > 0 and sheet['height'] > 0, 'positive sheet dimensions required')
    _need(sheet.get('unit') in {'mm', 'px'}, 'sheet unit invalid')
    _need(data.get('audience') and data.get('primary_action'), 'audience and primary action required')
    _need(data.get('reading_order') == [r['id'] for r in sorted(blocks, key=lambda r: r.get('order', 999))], 'reading order must match block order')
    return {'blocks': len(blocks), 'roles': sorted(roles), 'sheet': f"{sheet['width']}×{sheet['height']} {sheet['unit']}", 'reading_order_check': 'passed', 'audience_action_check': 'passed'}


def _graph(data, required_kinds):
    nodes, edges, groups, kinds, relations, incoming = _validate_graph(data, required_kinds)
    result = {'nodes': len(nodes), 'edges': len(edges), 'groups': len(groups), 'node_kinds': sorted(kinds), 'relations': dict(sorted(relations.items())), 'reference_check': 'passed'}
    mode = data['mode']
    if mode == 'circuit-logic':
        rows = data.get('truth_table'); _need(isinstance(rows, list) and len(rows) == 4, 'four-row truth table required')
        for row in rows:
            _need(set(row) == {'pressure_low', 'level_ok', 'pump_run'}, 'truth-table fields invalid')
            _need(row['pump_run'] == (row['pressure_low'] and row['level_ok']), 'truth table does not match AND logic')
        result['truth_rows'] = len(rows); result['true_outputs'] = sum(r['pump_run'] for r in rows); result['logic_check'] = 'passed'
    elif mode == 'system-diagram':
        boundary = data.get('system_boundary'); _need(boundary and boundary in {g['id'] for g in groups}, 'system boundary required')
        _need({'command', 'telemetry', 'work-order'} <= set(relations), 'system interface types incomplete')
        result['system_boundary'] = boundary; result['interface_coverage'] = 'passed'
    elif mode == 'sysml-requirement':
        _need({'satisfy', 'verify', 'deriveReqt'} <= set(relations), 'SysML requirement relations incomplete')
        reqs={n['id'] for n in nodes if n['kind']=='requirement'}
        satisfied={e['target'] for e in edges if e['relation']=='satisfy'}; verified={e['target'] for e in edges if e['relation']=='verify'}
        _need(reqs <= satisfied | verified, 'requirement without satisfy or verify relation')
        result['requirements']=len(reqs); result['traceability_coverage']='passed'; result['specification_version']='SysML 1.6 teaching subset'
    elif mode == 'sysml-bdd':
        _need({'composition', 'generalization', 'typed-by'} <= set(relations), 'BDD relationship subset incomplete')
        result['block_definition_semantics']='passed'; result['specification_version']='SysML 1.6 teaching subset'
    elif mode == 'sysml-ibd':
        ports={n['id']:n for n in nodes if n['kind']=='port'}
        for edge in edges:
            if edge['relation']=='connector':
                _need(edge['source'] in ports and edge['target'] in ports, 'IBD connector must join ports')
                _need(ports[edge['source']].get('interface') == ports[edge['target']].get('interface'), 'IBD connector interfaces differ')
        _need(any(e['relation']=='connector' for e in edges), 'IBD connector required')
        result['ports']=len(ports); result['connector_compatibility']='passed'; result['specification_version']='SysML 1.6 teaching subset'
    elif mode == 'sysml-parametric':
        constraints=data.get('constraints'); _need(isinstance(constraints,list) and constraints,'constraints required')
        residuals=[]
        for row in constraints:
            _need(all(_finite(row.get(k)) for k in ('lhs','rhs','tolerance')), 'finite constraint terms required')
            residual=abs(row['lhs']-row['rhs']); _need(residual <= row['tolerance'], 'constraint residual exceeds tolerance'); residuals.append(residual)
        result['constraints']=len(constraints); result['max_residual']=max(residuals); result['constraint_check']='passed'; result['specification_version']='SysML 1.6 teaching subset'
    elif mode in CLOUD_MODES:
        provider={'alicloud-architecture':'Alibaba Cloud','tencentcloud-architecture':'Tencent Cloud','huaweicloud-architecture':'Huawei Cloud'}[mode]
        _need(data.get('provider')==provider,'cloud provider mismatch')
        zones={n.get('zone') for n in nodes if n.get('zone')}; _need(len(zones)>=2,'multi-zone example requires at least two zones')
        _need(any(n['kind']=='operations' for n in nodes),'operations/observability node required')
        _need(any(n.get('identity_control') for n in nodes),'identity control evidence required')
        result.update({'provider':provider,'availability_zones':len(zones),'multi_zone_check':'passed','identity_observability_coverage':'passed','icon_policy':'neutral-vector-primitives'})
    elif mode == 'tqm':
        _need({'govern', 'measure', 'improve', 'feedback'} <= set(relations), 'TQM closed-loop relations incomplete')
        result['closed_loop']='passed'; result['principles']=len(required_kinds)
    return result


def _map(data):
    mode=data['mode']; routes=data.get('routes',[]); stations=data.get('stations',[]); locations=data.get('locations',[])
    _ids(routes,'routes')
    for route in routes:
        _need(route.get('label') and route.get('color') and isinstance(route.get('points'),list) and len(route['points'])>=2,'map route invalid')
        for p in route['points']:_point(p)
    if mode=='transit-map':
        station_ids=_ids(stations,'stations'); route_ids={r['id'] for r in routes}; interchanges=0
        for row in stations:
            _point(row.get('position')); _need(row.get('label') and set(row.get('route_ids',[]))<=route_ids and row.get('route_ids'),'station route reference invalid')
            interchanges+=len(row['route_ids'])>1
        _need(interchanges>=1 and len(route_ids)>=2,'transit example needs two routes and an interchange')
        return {'routes':len(routes),'stations':len(station_ids),'interchanges':interchanges,'topology_check':'passed','distance_claim':'schematic-not-to-scale'}
    _ids(locations,'locations'); bbox=data.get('bbox'); _need(isinstance(bbox,list) and len(bbox)==4 and all(_finite(v) for v in bbox),'map bbox required')
    minlon,minlat,maxlon,maxlat=bbox; _need(minlon<maxlon and minlat<maxlat,'map bbox invalid')
    sources=set()
    for row in locations:
        _point(row.get('position')); _need(_finite(row.get('lon')) and _finite(row.get('lat')) and minlon<=row['lon']<=maxlon and minlat<=row['lat']<=maxlat,'location outside geographic bbox')
        _need(row.get('label') and row.get('source'),'location label and source required'); sources.add(row['source'])
    _need(data.get('map_accuracy')=='schematic-with-coordinates','geographic map accuracy statement required')
    return {'locations':len(locations),'routes':len(routes),'bbox':bbox,'sources':len(sources),'coordinate_bounds_check':'passed','map_accuracy':'schematic-with-coordinates'}


def _science(data, required_roles):
    blocks, roles=_validate_blocks(data,required_roles); mode=data['mode']; result={'blocks':len(blocks),'roles':sorted(roles)}
    if mode=='mathematics':
        steps=data.get('steps'); _need(isinstance(steps,list) and len(steps)>=3,'mathematical steps required')
        residuals=[]
        for row in steps:
            _need(row.get('expression') and _finite(row.get('lhs')) and _finite(row.get('rhs')),'mathematical step invalid'); residuals.append(abs(row['lhs']-row['rhs']))
        _need(max(residuals)<=data.get('tolerance',1e-9),'mathematical equality check failed')
        result.update({'steps':len(steps),'max_residual':max(residuals),'equivalence_check':'passed'})
    elif mode=='mechanics':
        forces=data.get('forces'); _ids(forces,'forces'); sx=sy=0.0
        for row in forces:
            _need(_finite(row.get('fx_n')) and _finite(row.get('fy_n')) and row.get('evidence'),'force vector invalid'); _point(row.get('origin')); sx+=row['fx_n']; sy+=row['fy_n']
        tol=data.get('balance_tolerance_n'); _need(_finite(tol) and abs(sx)<=tol and abs(sy)<=tol,'force balance exceeds tolerance')
        result.update({'forces':len(forces),'sum_fx_n':round(sx,6),'sum_fy_n':round(sy,6),'force_balance':'passed'})
    elif mode=='optics':
        do=data.get('object_distance_mm'); f=data.get('focal_length_mm'); _need(_finite(do) and _finite(f) and do>f>0,'optical distances invalid')
        di=1/(1/f-1/do); mag=-di/do
        _need(len(data.get('rays',[]))>=2,'at least two construction rays required')
        result.update({'object_distance_mm':do,'focal_length_mm':f,'image_distance_mm':round(di,3),'magnification':round(mag,3),'thin_lens_check':'passed','claim_scope':'paraxial teaching model'})
    elif mode=='chemical-equation':
        reactions=data.get('reactions'); _need(isinstance(reactions,list) and reactions,'reaction required')
        for row in reactions:
            _need(row.get('equation') and isinstance(row.get('atoms_left'),dict) and isinstance(row.get('atoms_right'),dict),'reaction atom inventory required')
            _need(row['atoms_left']==row['atoms_right'],'chemical equation is not atom balanced')
        result.update({'reactions':len(reactions),'atom_balance':'passed','stoichiometry_scope':'mass-balance teaching example'})
    elif mode=='lab-equipment':
        equipment=data.get('equipment'); links=data.get('connections'); _ids(equipment,'equipment'); ids={r['id'] for r in equipment}; _ids(links,'connections')
        for row in equipment:_point(row.get('position')); _need(row.get('label') and row.get('tag'),'equipment label and tag required')
        for row in links:_need(row.get('source') in ids and row.get('target') in ids and row.get('medium') and row.get('direction'),'laboratory connection invalid')
        hazards=set(data.get('hazards',[])); _need({'pressure','chemical','heat'}<=hazards,'lab hazard coverage incomplete')
        result.update({'equipment':len(equipment),'connections':len(links),'hazards':sorted(hazards),'connection_check':'passed','safety_scope':'procedure-and-local-review-required'})
    return result


def _storyboard(data):
    frames=data.get('frames'); _ids(frames,'frames'); total=0; shots=set()
    for i,row in enumerate(frames,1):
        _need(row.get('number')==i and row.get('shot') and row.get('action') and row.get('audio'),'contiguous storyboard frame fields required')
        _need(_finite(row.get('duration_s')) and row['duration_s']>0,'positive frame duration required'); total+=row['duration_s']; shots.add(row['shot'])
    _need(len(frames)>=6 and len(shots)>=3,'storyboard needs at least six frames and three shot types')
    _need(math.isclose(total,data.get('declared_duration_s'),rel_tol=0,abs_tol=1e-9),'storyboard duration mismatch')
    metrics={r['id']:r['value'] for r in data.get('metrics',[])}
    _need(metrics.get('frames')==len(frames) and metrics.get('duration')==total and metrics.get('shots')==len(shots),'storyboard metrics do not match computed values')
    return {'frames':len(frames),'duration_s':total,'shot_types':sorted(shots),'contiguous_numbering':'passed','duration_reconciliation':'passed'}


def _quality(data):
    tools=data.get('tools'); ids=_ids(tools,'tools')
    required={'check-sheet','pareto','fishbone','histogram','control-chart','scatter','stratification'}
    _need(ids==required,'seven quality tools set incomplete')
    total=0
    for row in tools:
        _need(row.get('label') and row.get('question') and row.get('evidence'),'quality tool fields required')
        _need(_finite(row.get('sample_value')) and row['sample_value']>=0,'quality sample value invalid'); total+=row['sample_value']
    _need(data.get('same_dataset') is True,'quality-tool comparison must use one dataset')
    return {'tools':len(tools),'tool_set':sorted(ids),'sample_value_total':round(total,3),'same_dataset':'passed','method_scope':'selection-and-communication-example'}


def analyze(data):
    mode,template=_base(data); _validate_metrics(data); required=SPECS[mode][1]
    if template=='publication': calc=_publication(data,required)
    elif template=='graph': calc=_graph(data,required)
    elif template=='map': calc=_map(data)
    elif template=='science': calc=_science(data,required)
    elif template=='storyboard': calc=_storyboard(data)
    else: calc=_quality(data)
    return {'mode':mode,'template':template,'data_status':data['data_status'],'assumptions':data.get('assumptions',[]),**calc,'metric_count':len(data.get('metrics',[]))}


def _font():
    from matplotlib import font_manager
    path=Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists(): font_manager.fontManager.addfont(path); return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def _figure(data):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family':_font(),'font.size':10,'text.color':INK,'axes.unicode_minus':False,'svg.fonttype':'none','svg.hashsalt':'diagram-studio-remaining-types-v1'})
    if data['template']=='publication':
        sheet=data['sheet']
        if sheet['unit']=='mm': size=(sheet['width']/25.4,sheet['height']/25.4)
        else: size=(sheet['width']/150,sheet['height']/150)
    else: size=(12.8,7.6)
    fig=plt.figure(figsize=size,dpi=150,facecolor=BG); ax=fig.add_axes((.055,.10,.89,.75)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
    scale=1.0
    if data['template']=='publication': scale=min(1.0,max(.45,min(size[0]/8.27,size[1]/7.6)))
    fig.text(.055,.965,data['title'],fontsize=21.5*scale,color=INK,weight='medium',va='top')
    fig.text(.055,.895,data.get('subtitle',''),fontsize=9.5*scale,color=MUTED,va='top')
    fig.text(.945,.96,data['mode'].upper().replace('-','  '),fontsize=8*scale,color=MUTED,ha='right',va='top'); return fig,ax


def _wrap(value,width=16):
    lines=[]
    for paragraph in str(value).splitlines() or ['']:
        line=''; used=0.0
        for char in paragraph:
            char_width=1.0 if unicodedata.east_asian_width(char) in 'WF' else .55
            if line and used+char_width>width:
                lines.append(line.rstrip()); line=''; used=0.0
            line+=char; used+=char_width
        lines.append(line.rstrip())
    return '\n'.join(lines)


def _metrics(fig,data):
    rows=data.get('metrics',[])[:4]
    if not rows:return
    page_height=fig.get_figheight()*fig.dpi
    compact=page_height<600
    metric_font=8.0 if compact else 10.5; label_font=5.3 if compact else 6.6
    metric_y=max(.06,32/page_height); label_y=max(.02,12/page_height)
    x=.055
    for row in rows:
        fig.text(x,metric_y,str(row['value'])+((' '+row.get('unit','')) if row.get('unit') else ''),fontsize=metric_font,color=INK,weight='medium',va='top')
        fig.text(x,label_y,row['label'],fontsize=label_font,color=MUTED,va='top'); x+=.19


def _draw_graph(ax,data):
    from matplotlib.patches import FancyBboxPatch,Rectangle
    for i,g in enumerate(data.get('groups',[])):
        x,y,w,h=g['rect']; c=PALETTE[i%len(PALETTE)]; ax.add_patch(Rectangle((x,y),w,h,fc=c,alpha=.045,ec=c,lw=1.1,linestyle='--',zorder=.1)); ax.text(x+.012,y+h-.014,g['label'],fontsize=7,color=c,va='top')
    by={r['id']:r for r in data.get('nodes',[])}
    for i,e in enumerate(data.get('edges',[])):
        a=by[e['source']]['position']; b=by[e['target']]['position']; c=PALETTE[i%len(PALETTE)]
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='-|>',color=c,lw=1.15,shrinkA=21,shrinkB=21),zorder=1)
        mx,my=e.get('label_position',((a[0]+b[0])/2,(a[1]+b[1])/2))
        ax.text(mx,my+.014,_wrap(e['label'],18),fontsize=5.5,color=c,ha='center',va='center',bbox=dict(fc=BG,ec='none',pad=.08,alpha=.92),zorder=4)
    for i,n in enumerate(data.get('nodes',[])):
        x,y=n['position']; c=PALETTE[i%len(PALETTE)]; w=n.get('width',.145); h=n.get('height',.085)
        ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=.007,rounding_size=.01',fc=PAPER,ec=c,lw=1.4,zorder=3))
        label=n['label']+(('\n'+n.get('detail','')) if n.get('detail') else '')
        mark_container(ax.text(x,y,_wrap(label,20),fontsize=6.2,ha='center',va='center',zorder=4),ax,(x-w/2,y-h/2,w,h),f"node:{n['id']}")


def _draw_publication(ax,data):
    from matplotlib.patches import Rectangle
    sheet=data['sheet']; ratio=sheet['width']/sheet['height']; maxw=.82; maxh=.86
    if ratio>=1: w=maxw; h=min(maxh,w/ratio)
    else: h=maxh; w=min(maxw,h*ratio)
    ox=(1-w)/2; oy=(1-h)/2
    ax.add_patch(Rectangle((ox,oy),w,h,fc=PAPER,ec=INK,lw=1.2,zorder=.1))
    roles={r for _,rs in SPECS.values() for r in rs}; role_colors={r:PALETTE[i%len(PALETTE)] for i,r in enumerate(sorted(roles))}
    for row in data['blocks']:
        x,y,bw,bh=row['rect']; x=ox+x*w; y=oy+y*h; bw*=w; bh*=h; c=role_colors.get(row['role'],BLUE)
        ax.add_patch(Rectangle((x,y),bw,bh,fc=c,alpha=.10,ec=c,lw=.9,zorder=1))
        mark_container(ax.text(x+.012*w,y+bh-.014*h,_wrap(row['label'],24),fontsize=max(5.6,min(9,6.2+bh*3)),color=INK,weight='medium',va='top'),ax,(x,y,bw,bh),f"block:{row['id']}:label")
        if row.get('content'):
            mark_container(ax.text(x+.012*w,y+bh*.40,_wrap(row['content'],28),fontsize=max(4.8,min(7,5.1+bh*2)),color=MUTED,va='top'),ax,(x,y,bw,bh),f"block:{row['id']}:content")
    ax.text(ox,oy-.025,f"{sheet['width']} × {sheet['height']} {sheet['unit']} · 阅读顺序与内容角色已校验",fontsize=6.5,color=MUTED,va='top')


def _draw_map(ax,data):
    from matplotlib.patches import Circle,Polygon
    for i,z in enumerate(data.get('zones',[])):
        ax.add_patch(Polygon(z['points'],closed=True,fc=PALETTE[i%len(PALETTE)],ec=PALETTE[i%len(PALETTE)],alpha=.08,lw=1)); ax.text(*z['label_at'],z['label'],fontsize=6.5,color=PALETTE[i%len(PALETTE)])
    route_colors={r['id']:r.get('color',PALETTE[i%len(PALETTE)]) for i,r in enumerate(data.get('routes',[]))}
    for route in data.get('routes',[]):
        xs=[p[0] for p in route['points']]; ys=[p[1] for p in route['points']]; ax.plot(xs,ys,color=route_colors[route['id']],lw=4,solid_capstyle='round',zorder=1); ax.text(xs[-1],ys[-1]+.03,route['label'],fontsize=6.5,color=route_colors[route['id']],ha='center')
    for row in data.get('stations',[]):
        x,y=row['position']; multi=len(row['route_ids'])>1; ax.add_patch(Circle((x,y),.014 if not multi else .021,fc=PAPER,ec=INK,lw=1.2,zorder=3)); ax.text(x,y-.032,_wrap(row['label'],10),fontsize=5.6,ha='center',va='top')
    for row in data.get('locations',[]):
        x,y=row['position']; ax.scatter([x],[y],s=70,facecolor=PAPER,edgecolor=RED,linewidth=1.5,zorder=3); ax.text(x+.015,y+.012,_wrap(row['label'],12),fontsize=6.2,color=INK,va='bottom')


def _draw_science(ax,data):
    from matplotlib.patches import Rectangle,Circle
    for i,row in enumerate(data.get('blocks',[])):
        x,y,w,h=row['rect']; c=PALETTE[i%len(PALETTE)]; ax.add_patch(Rectangle((x,y),w,h,fc=PAPER,ec=c,lw=1.2,zorder=1)); ax.text(x+.015,y+h-.02,row['label'],fontsize=8.5,color=c,weight='medium',va='top'); ax.text(x+.015,y+.03,_wrap(row.get('content',''),34),fontsize=6.3,color=INK,va='bottom')
    if data['mode']=='mechanics':
        cx,cy=.50,.44; ax.add_patch(Rectangle((cx-.12,cy-.07),.24,.14,fc=AMBER,alpha=.18,ec=AMBER,lw=1.4));
        scale=max(max(abs(f['fx_n']),abs(f['fy_n'])) for f in data['forces'])/.22
        for i,f in enumerate(data['forces']):
            ox,oy=f['origin']; dx=f['fx_n']/scale; dy=f['fy_n']/scale; ax.annotate('',xy=(ox+dx,oy+dy),xytext=(ox,oy),arrowprops=dict(arrowstyle='-|>',lw=2,color=PALETTE[i%len(PALETTE)])); ax.text(ox+dx,oy+dy+(.02 if dy>=0 else -.025),f['label'],fontsize=6,color=PALETTE[i%len(PALETTE)],ha='center',va='bottom' if dy>=0 else 'top')
    elif data['mode']=='optics':
        ax.axhline(.43,color=GRID,lw=1); ax.plot([.5,.5],[.2,.7],color=BLUE,lw=3); ax.text(.5,.73,'薄透镜',ha='center',fontsize=7,color=BLUE)
        for i,ray in enumerate(data['rays']): xs=[p[0] for p in ray['points']]; ys=[p[1] for p in ray['points']]; ax.plot(xs,ys,color=PALETTE[i],lw=1.5)
        ax.arrow(.25,.43,0,.19,width=.005,color=RED,length_includes_head=True); ax.arrow(.75,.43,0,-.285,width=.005,color=GREEN,length_includes_head=True)
    elif data['mode']=='lab-equipment':
        by={r['id']:r for r in data['equipment']}
        for i,e in enumerate(data['connections']): a=by[e['source']]['position']; b=by[e['target']]['position']; ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='-|>',color=PALETTE[i],lw=1.4,shrinkA=16,shrinkB=16)); ax.text((a[0]+b[0])/2,(a[1]+b[1])/2,e['medium'],fontsize=5.5,color=PALETTE[i])
        for i,n in enumerate(data['equipment']): x,y=n['position']; ax.add_patch(Circle((x,y),.04,fc=PAPER,ec=PALETTE[i%len(PALETTE)],lw=1.4)); ax.text(x,y-.065,n['tag']+' '+n['label'],fontsize=6,ha='center',va='top')


def _draw_storyboard(ax,data):
    from matplotlib.patches import Rectangle,Circle
    frames=data['frames']; cols=4; gap=.018; w=(1-gap*(cols-1))/cols; h=.42
    for i,row in enumerate(frames):
        col=i%cols; rr=1-i//cols; x=col*(w+gap); y=.04+rr*(h+.07); c=PALETTE[i%len(PALETTE)]
        ax.add_patch(Rectangle((x,y),w,h,fc=PAPER,ec=c,lw=1.2)); ax.add_patch(Rectangle((x+.012,y+.16),w-.024,h-.19,fc=c,alpha=.08,ec='none'))
        ax.add_patch(Circle((x+w*.28,y+.28),.028,fc=c,alpha=.25,ec=c)); ax.plot([x+w*.42,x+w*.78],[y+.22,y+.34],color=c,lw=3)
        ax.text(x+.012,y+h-.018,f"{row['number']:02d} · {row['shot']} · {row['duration_s']}s",fontsize=6.6,color=c,weight='medium',va='top')
        ax.text(x+.012,y+.125,_wrap(row['action'],24),fontsize=5.6,color=INK,va='top'); ax.text(x+.012,y+.02,_wrap('音频 '+row['audio'],25),fontsize=5.2,color=MUTED,va='bottom')


def _draw_quality(ax,data):
    from matplotlib.patches import Rectangle
    tools=data['tools']; positions=[(0,.53),( .255,.53),(.51,.53),(.765,.53),(.125,.06),(.38,.06),(.635,.06)]
    for i,(row,(x,y)) in enumerate(zip(tools,positions)):
        w=.225; h=.37; c=PALETTE[i%len(PALETTE)]; ax.add_patch(Rectangle((x,y),w,h,fc=PAPER,ec=c,lw=1.1)); ax.text(x+.012,y+h-.02,row['label'],fontsize=7.4,color=c,weight='medium',va='top'); ax.text(x+.012,y+h-.085,_wrap(row['question'],20),fontsize=5.7,color=INK,va='top'); ax.text(x+.012,y+.025,f"样例值 {row['sample_value']}\n证据 {row['evidence']}",fontsize=5.4,color=MUTED,va='bottom')


DRAWERS={'graph':_draw_graph,'publication':_draw_publication,'map':_draw_map,'science':_draw_science,'storyboard':_draw_storyboard,'quality':_draw_quality}


def render(data,out,name=None):
    calc=analyze(data); out=Path(out); out.mkdir(parents=True,exist_ok=True); name=name or data.get('id') or data['mode']
    fig,ax=_figure(data)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        DRAWERS[data['template']](ax,data); _metrics(fig,data)
        fig.canvas.draw()
        fig.savefig(out/f'{name}.svg',format='svg',facecolor=BG,metadata={'Date':None}); fig.savefig(out/f'{name}.png',dpi=150,facecolor=BG)
        visual=inspect_figure(fig,captured)
    import matplotlib.pyplot as plt; plt.close(fig)
    (out/f'{name}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (out/f'{name}.calculation.json').write_text(json.dumps(calc,ensure_ascii=False,indent=2)+'\n')
    qa=quality_payload('passed',visual,'simulated teaching content unless a source is explicitly named')
    (out/f'{name}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n'); return calc


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('--out',required=True); p.add_argument('--name'); args=p.parse_args()
    data=json.loads(Path(args.input).read_text()); print(json.dumps(render(data,args.out,args.name or Path(args.input).stem),ensure_ascii=False))


if __name__=='__main__': main()
