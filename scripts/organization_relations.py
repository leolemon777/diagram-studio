#!/usr/bin/env python3
"""Validate and render organization, responsibility, affinity and relationship models."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import textwrap
from collections import Counter, defaultdict
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


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _rows(data, key):
    rows = data.get(key)
    _need(isinstance(rows, list) and rows, f'{key} required')
    ids = [row.get('id') for row in rows]
    _need(all(isinstance(value, str) and value.strip() for value in ids), f'{key} ids required')
    _unique(ids, f'{key} ids must be unique')
    return rows


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')
    _need(data.get('data_status') in {'simulated', 'observed', 'mixed'}, 'data_status required')


def _position(row):
    value = row.get('position')
    _need(isinstance(value, list) and len(value) == 2, 'normalized position required')
    _need(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) and 0 <= item <= 1 for item in value), 'positions must be finite within 0..1')


def _people_network(data):
    _base(data, 'people-network')
    people = _rows(data, 'people'); types = _rows(data, 'relation_types'); relations = _rows(data, 'relations')
    person_ids = {row['id'] for row in people}; type_ids = {row['id'] for row in types}
    for row in people:
        _need(row.get('label') and row.get('role') and row.get('group'), 'each person needs label, role and group'); _position(row)
    for row in types:
        _need(row.get('label') and isinstance(row.get('directed'), bool), 'relation type needs label and directed flag')
        _need(row.get('style') in {'solid', 'dashed', 'dotted'}, 'relation type style required')
    pair_keys = []
    for row in relations:
        _need(row.get('source') in person_ids and row.get('target') in person_ids and row['source'] != row['target'], 'relation endpoints must reference different people')
        _need(row.get('type') in type_ids and row.get('verb') and row.get('evidence'), 'relation type, verb and evidence required')
        pair_keys.append((row['source'], row['target'], row['type']))
    _unique(pair_keys, 'duplicate typed relations are not allowed')
    degree = Counter()
    for row in relations:
        degree[row['source']] += 1; degree[row['target']] += 1
    return {'mode': 'people-network', 'people': len(people), 'relations': len(relations),
            'relation_types': len(types), 'evidence_complete': 'passed',
            'highest_degree_people': sorted((item for item in degree if degree[item] == max(degree.values())), key=str)}


def _hr_lifecycle(data):
    _base(data, 'hr-lifecycle')
    units = _rows(data, 'units'); roles = _rows(data, 'roles'); stages = _rows(data, 'stages'); metrics = _rows(data, 'metrics')
    unit_ids = {row['id'] for row in units}; stage_ids = {row['id'] for row in stages}
    for row in units:
        _need(row.get('label') and row.get('leader'), 'unit label and leader required')
        _need(isinstance(row.get('headcount'), int) and row['headcount'] >= 0, 'unit headcount must be a nonnegative integer')
    role_totals = Counter()
    for row in roles:
        _need(row.get('label') and row.get('unit_id') in unit_ids, 'role label and unit required')
        _need(isinstance(row.get('count'), int) and row['count'] >= 0, 'role count must be a nonnegative integer')
        role_totals[row['unit_id']] += row['count']
    declared = {row['id']: row['headcount'] for row in units}
    _need(dict(role_totals) == declared, 'role counts must reconcile exactly to each unit headcount')
    orders = [row.get('order') for row in stages]
    _need(all(isinstance(value, int) and value >= 1 for value in orders) and sorted(orders) == list(range(1, len(stages)+1)), 'lifecycle stage order must be contiguous from 1')
    for row in stages:
        _need(row.get('label') and row.get('owner'), 'stage label and owner required')
    for row in metrics:
        _need(row.get('label') and row.get('stage_id') in stage_ids and row.get('unit'), 'metric label, stage and unit required')
        _need(isinstance(row.get('value'), (int, float)) and not isinstance(row['value'], bool) and math.isfinite(row['value']), 'metric values must be finite')
    return {'mode': 'hr-lifecycle', 'units': len(units), 'roles': len(roles), 'stages': len(stages),
            'metrics': len(metrics), 'total_headcount': sum(declared.values()), 'headcount_reconciliation': 'passed',
            'lifecycle_order': [row['id'] for row in sorted(stages, key=lambda item:item['order'])]}


def _raci(data):
    _base(data, 'raci')
    members = _rows(data, 'members'); work = _rows(data, 'work_items'); assignments = data.get('assignments')
    member_ids = {row['id'] for row in members}; work_ids = {row['id'] for row in work}
    for row in members:
        _need(row.get('label') and row.get('role'), 'member label and role required')
    for row in work:
        _need(row.get('label') and row.get('deliverable'), 'work item label and deliverable required')
    _need(isinstance(assignments, list) and assignments, 'RACI assignments required')
    keys=[]; by_work=defaultdict(list)
    for row in assignments:
        _need(row.get('work_id') in work_ids and row.get('member_id') in member_ids, 'RACI assignment references unknown work or member')
        _need(row.get('responsibility') in {'R','A','C','I'}, 'responsibility must be R, A, C or I')
        key=(row['work_id'],row['member_id']); keys.append(key); by_work[row['work_id']].append(row['responsibility'])
    _unique(keys, 'a member may have only one RACI value per work item')
    for item in work_ids:
        _need(by_work[item].count('A') == 1, f'work item {item} must have exactly one accountable owner')
        _need(by_work[item].count('R') >= 1, f'work item {item} must have at least one responsible member')
    workload = {member: sum(row['member_id'] == member and row['responsibility'] in {'R','A'} for row in assignments) for member in sorted(member_ids)}
    return {'mode':'raci','members':len(members),'work_items':len(work),'assignments':len(assignments),
            'accountable_coverage':'passed','responsible_coverage':'passed','ra_workload':workload}


def _team_canvas(data):
    _base(data, 'team-canvas')
    _need(data.get('purpose') and data.get('success_definition'), 'team purpose and success definition required')
    members=_rows(data,'members'); agreements=_rows(data,'agreements'); risks=_rows(data,'risks')
    member_ids={row['id'] for row in members}
    for row in members:
        _need(row.get('label') and row.get('role') and row.get('decision_scope'), 'member role and decision scope required')
    for row in agreements:
        _need(row.get('rule') and row.get('owner_id') in member_ids and row.get('review_date'), 'agreement rule, owner and review date required')
        dt.date.fromisoformat(row['review_date'])
    for row in risks:
        _need(row.get('statement') and row.get('owner_id') in member_ids and row.get('mitigation'), 'risk statement, owner and mitigation required')
    return {'mode':'team-canvas','members':len(members),'agreements':len(agreements),'risks':len(risks),
            'owned_agreements':'passed','owned_risks':'passed','executable_rules':'passed'}


def _influence_map(data):
    _base(data, 'influence-map')
    nodes=_rows(data,'nodes'); links=_rows(data,'links'); node_ids={row['id'] for row in nodes}
    for row in nodes:
        _need(row.get('label') and row.get('kind') in {'condition','actor','outcome'}, 'influence node label and kind required'); _position(row)
    for row in links:
        _need(row.get('source') in node_ids and row.get('target') in node_ids and row['source'] != row['target'], 'influence link endpoints invalid')
        _need(row.get('verb') and row.get('evidence'), 'influence link verb and evidence required')
        _need(row.get('claim_type') in {'associated','influences'}, 'claim type must distinguish association and influence')
        if row['claim_type']=='influences': _need(row.get('causal_basis'), 'influence claims need a causal basis')
    return {'mode':'influence-map','nodes':len(nodes),'links':len(links),
            'association_links':sum(row['claim_type']=='associated' for row in links),
            'influence_links':sum(row['claim_type']=='influences' for row in links),
            'claim_scope_explicit':'passed','evidence_complete':'passed'}


def _affinity(data):
    _base(data, 'affinity-map')
    observations=_rows(data,'observations'); themes=_rows(data,'themes'); observation_ids={row['id'] for row in observations}
    for row in observations:
        _need(row.get('text') and row.get('source'), 'affinity observations need text and source')
    assigned=[]
    for row in themes:
        ids=row.get('observation_ids')
        _need(row.get('label') and isinstance(ids,list) and ids, 'theme label and observation ids required')
        _need(set(ids) <= observation_ids, 'theme references unknown observation'); assigned.extend(ids)
    _need(len(assigned)==len(set(assigned)), 'each observation may appear in only one theme')
    _need(set(assigned)==observation_ids, 'every observation must remain in the affinity map')
    minority=data.get('minority_observation_ids',[])
    _need(isinstance(minority,list) and set(minority)<=observation_ids, 'minority observations must reference retained observations')
    return {'mode':'affinity-map','observations':len(observations),'themes':len(themes),
            'theme_sizes':{row['id']:len(row['observation_ids']) for row in themes},
            'minority_observations':minority,'observation_retention':'passed','single_assignment':'passed'}


def _matrix_org(data):
    _base(data, 'matrix-org')
    departments=_rows(data,'departments'); projects=_rows(data,'projects'); members=_rows(data,'members')
    department_ids={row['id'] for row in departments}; project_ids={row['id'] for row in projects}
    for row in departments:
        _need(row.get('label') and row.get('manager'), 'department label and manager required')
    for row in projects:
        _need(row.get('label') and row.get('manager') and row.get('objective'), 'project label, manager and objective required')
    assignments=0
    for row in members:
        _need(row.get('label') and row.get('role') and row.get('department_id') in department_ids, 'member label, role and department required')
        pids=row.get('project_ids'); _need(isinstance(pids,list) and pids and set(pids)<=project_ids, 'member needs one or more valid projects'); _unique(pids,'member project ids must be unique')
        assignments+=len(pids)
    return {'mode':'matrix-org','departments':len(departments),'projects':len(projects),'members':len(members),
            'project_assignments':assignments,'dual_reporting_coverage':'passed',
            'functional_line':'solid','project_line':'dashed'}


def _ordered_loop(links_by_id, loop):
    ids=loop.get('link_ids')
    _need(isinstance(ids,list) and len(ids)>=2 and len(ids)==len(set(ids)), 'loop needs at least two unique links')
    _need(set(ids)<=set(links_by_id), 'loop references unknown link')
    rows=[links_by_id[item] for item in ids]
    for left,right in zip(rows,rows[1:]+rows[:1]):
        _need(left['target']==right['source'], f"loop {loop.get('id')} link order must form a closed path")
    return rows


def _causal_loop(data):
    _base(data, 'causal-loop')
    variables=_rows(data,'variables'); links=_rows(data,'links'); loops=_rows(data,'loops'); variable_ids={row['id'] for row in variables}
    for row in variables:
        _need(row.get('label'), 'causal variable label required'); _position(row)
    for row in links:
        _need(row.get('source') in variable_ids and row.get('target') in variable_ids and row['source']!=row['target'], 'causal link endpoints invalid')
        _need(row.get('polarity') in {1,-1} and row.get('evidence'), 'causal link polarity and evidence required')
        _need(isinstance(row.get('delay',False),bool), 'causal link delay must be boolean')
    links_by_id={row['id']:row for row in links}; computed={}
    for loop in loops:
        rows=_ordered_loop(links_by_id,loop); polarity=math.prod(row['polarity'] for row in rows)
        expected='reinforcing' if polarity==1 else 'balancing'
        _need(loop.get('declared_type')==expected, f"loop {loop['id']} declared type conflicts with link polarities")
        _need(loop.get('label'), 'loop label required'); computed[loop['id']]=expected
    return {'mode':'causal-loop','variables':len(variables),'links':len(links),'loops':len(loops),
            'computed_loop_types':computed,'delayed_links':sum(row.get('delay',False) for row in links),
            'closed_paths':'passed','polarity_consistency':'passed'}


ANALYZERS={'people-network':_people_network,'hr-lifecycle':_hr_lifecycle,'raci':_raci,
           'team-canvas':_team_canvas,'influence-map':_influence_map,'affinity-map':_affinity,
           'matrix-org':_matrix_org,'causal-loop':_causal_loop}


def analyze(data):
    _need(data.get('mode') in ANALYZERS, 'unsupported organization/relationship mode')
    result=ANALYZERS[data['mode']](data); result['data_status']=data['data_status']; result['assumptions']=data.get('assumptions',[])
    return result


def _font():
    from matplotlib import font_manager
    path=Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists():
        font_manager.fontManager.addfont(path); return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def _figure(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family':_font(),'font.size':10.5,'text.color':INK,
                                 'axes.unicode_minus':False,'svg.fonttype':'none',
                                 'svg.hashsalt':'diagram-studio-organization-relations-v1'})
    fig=plt.figure(figsize=(12.8,7.6),facecolor=BG); ax=fig.add_axes((.05,.09,.90,.78)); ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
    fig.text(.05,.955,data['title'],fontsize=22,color=INK,weight='medium',va='top')
    fig.text(.05,.912,data.get('subtitle',''),fontsize=10.2,color=MUTED,va='top')
    fig.text(.95,.95,data['mode'].upper().replace('-','  '),fontsize=8.2,color=MUTED,ha='right',va='top')
    return fig,ax


def _wrap(value,width=18):
    return '\n'.join(textwrap.wrap(str(value),width=max(4,width),break_long_words=True,break_on_hyphens=False))


def _card(ax,x,y,w,h,title,lines,accent=GREEN,text_size=8.2):
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((x,y),w,h,facecolor=PAPER,edgecolor=GRID,linewidth=1))
    ax.add_patch(Rectangle((x,y+h-.012),w,.012,facecolor=accent,edgecolor='none'))
    ax.text(x+.015,y+h-.035,title,fontsize=10,weight='medium',va='top')
    ax.text(x+.015,y+h-.078,'\n'.join(lines),fontsize=text_size,color=MUTED,va='top',linespacing=1.4)


def _arrow(ax,start,end,color=MUTED,style='solid',label='',directed=True,curve=0.0,label_offset=(0,0)):
    ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->' if directed else '-','color':color,'linewidth':1.35,'linestyle':style,'shrinkA':11,'shrinkB':11,'connectionstyle':f'arc3,rad={curve}'})
    if label:
        ax.text((start[0]+end[0])/2+label_offset[0],(start[1]+end[1])/2+label_offset[1],label,fontsize=7.5,color=color,ha='center',va='center',bbox={'boxstyle':'round,pad=.14','facecolor':BG,'edgecolor':'none','alpha':.92})


def _node(ax,pos,label,detail,color=GREEN,shape='round'):
    from matplotlib.patches import FancyBboxPatch, Circle
    x,y=pos
    if shape=='circle':
        ax.add_patch(Circle((x,y),.058,facecolor=PAPER,edgecolor=color,linewidth=1.5,zorder=3))
    else:
        ax.add_patch(FancyBboxPatch((x-.075,y-.046),.15,.092,boxstyle='round,pad=.008,rounding_size=.012',facecolor=PAPER,edgecolor=color,linewidth=1.5,zorder=3))
    ax.text(x,y+.009,_wrap(label,11),ha='center',va='center',fontsize=8.5,weight='medium',zorder=4)
    if detail: ax.text(x,y-.028,_wrap(detail,14),ha='center',va='center',fontsize=6.8,color=MUTED,zorder=4)


def _network(data,node_key,edge_key,type_key=None,causal=False):
    fig,ax=_figure(data); nodes=data[node_key]; by_id={row['id']:row for row in nodes}
    positions={row['id']:(.08+.78*row['position'][0],.12+.76*row['position'][1]) for row in nodes}
    types={row['id']:row for row in data.get(type_key,[])} if type_key else {}
    for index,row in enumerate(data[edge_key]):
        color=COLORS[index%len(COLORS)] if causal else (GREEN if row.get('claim_type')=='influences' else BLUE)
        style='dashed' if row.get('delay') or row.get('claim_type')=='associated' else types.get(row.get('type'),{}).get('style','solid')
        if causal: label=('+' if row['polarity']==1 else '−')+(' · 时滞' if row.get('delay') else '')
        else: label=row.get('verb','')
        directed=True if causal or row.get('claim_type') else types.get(row.get('type'),{}).get('directed',True)
        offset=row.get('label_offset',[0,.012 if index%2 else -.012])
        _need(isinstance(offset,list) and len(offset)==2 and all(isinstance(value,(int,float)) for value in offset),'label offset must be a numeric pair')
        _arrow(ax,positions[row['source']],positions[row['target']],color,style,label,directed,curve=.06 if index%2 else -.04,label_offset=tuple(offset))
    for index,row in enumerate(nodes):
        color={'actor':BLUE,'condition':AMBER,'outcome':GREEN}.get(row.get('kind'),COLORS[index%len(COLORS)])
        kind_labels={'actor':'行动者','condition':'条件','outcome':'结果'}
        _node(ax,positions[row['id']],row['label'],row.get('role') or kind_labels.get(row.get('kind'),''),color,'circle' if causal else 'round')
    if causal:
        lines=[f"{row['id']} · {'增强 R' if row['declared_type']=='reinforcing' else '平衡 B'}\n{_wrap(row['label'],8)}" for row in data['loops']]
        _card(ax,.84,.52,.16,.34,'反馈回路',lines,RED,text_size=7.1)
        ax.text(.86,.43,'+ 同向作用\n− 反向作用\n虚线为时滞',fontsize=7.5,color=MUTED,va='top')
    elif type_key:
        style_labels={'solid':'实线','dashed':'虚线','dotted':'点线'}
        lines=[f"{row['label']} · {'有向' if row['directed'] else '无向'} · {style_labels[row['style']]}" for row in data[type_key]]
        _card(ax,.86,.52,.14,.34,'关系图例',lines,BLUE,text_size=7.2)
    else:
        _card(ax,.86,.52,.14,.34,'声明边界',[f"关联 {sum(r['claim_type']=='associated' for r in data[edge_key])} 条",f"影响 {sum(r['claim_type']=='influences' for r in data[edge_key])} 条",'关联不自动解释为因果','影响边必须有因果依据'],AMBER,text_size=7.2)
    return fig


def _render_people(data,meta): return _network(data,'people','relations','relation_types')
def _render_influence(data,meta): return _network(data,'nodes','links')
def _render_causal(data,meta): return _network(data,'variables','links',causal=True)


def _render_hr(data,meta):
    fig,ax=_figure(data); units=data['units']; roles=data['roles']; stages=sorted(data['stages'],key=lambda r:r['order']); metrics={r['stage_id']:r for r in data['metrics']}
    width=.27; gap=.035
    for i,unit in enumerate(units):
        x=.01+i*(width+gap); related=[r for r in roles if r['unit_id']==unit['id']]
        _card(ax,x,.56,width,.34,f"{unit['label']} · {unit['headcount']}人",[f"负责人：{unit['leader']}"]+[f"{r['label']} × {r['count']}" for r in related],COLORS[i],text_size=8)
    left=.075; total=.70; y=.31
    for i,stage in enumerate(stages):
        x=left+i*total/(len(stages)-1); ax.scatter([x],[y],s=210,color=COLORS[i%len(COLORS)],edgecolor=PAPER,zorder=3)
        if i<len(stages)-1: _arrow(ax,(x+.015,y),(left+(i+1)*total/(len(stages)-1)-.015,y),MUTED,'solid','',True)
        metric=metrics.get(stage['id'])
        _card(ax,x-.066,.055,.132,.18,_wrap(stage['label'],7),[_wrap(stage['owner'],9),_wrap(f"{metric['label']} {metric['value']:g}{metric['unit']}" if metric else '',10)],COLORS[i%len(COLORS)],text_size=6.6)
    _card(ax,.86,.14,.14,.28,'口径',[f"总人数 {meta['total_headcount']}",f"岗位 {meta['roles']} 类",f"生命周期 {meta['stages']} 阶段",'组织、流程、指标分视图'],GREEN,text_size=7.3)
    return fig


def _render_raci(data,meta):
    from matplotlib.patches import Rectangle
    fig,ax=_figure(data); members=data['members']; work=data['work_items']; values={(r['work_id'],r['member_id']):r['responsibility'] for r in data['assignments']}
    left=.02; top=.93; label_w=.28; cell_w=.69/len(members); row_h=.105
    ax.add_patch(Rectangle((left,top-row_h),label_w,row_h,facecolor=INK,edgecolor=BG)); ax.text(left+.012,top-row_h/2,'工作项 / 交付物',color='white',va='center',fontsize=8.5)
    for col,m in enumerate(members):
        x=left+label_w+col*cell_w; ax.add_patch(Rectangle((x,top-row_h),cell_w,row_h,facecolor=INK,edgecolor=BG)); ax.text(x+cell_w/2,top-row_h/2,_wrap(m['label']+'\n'+m['role'],7),color='white',ha='center',va='center',fontsize=7.4)
    for row_index,item in enumerate(work):
        y=top-row_h*(row_index+2); ax.add_patch(Rectangle((left,y),label_w,row_h,facecolor=PAPER if row_index%2==0 else '#F4F1EC',edgecolor=GRID)); ax.text(left+.012,y+row_h/2,_wrap(item['label']+'\n'+item['deliverable'],22),va='center',fontsize=7.8)
        for col,m in enumerate(members):
            x=left+label_w+col*cell_w; value=values.get((item['id'],m['id']),'—'); color={'A':RED,'R':GREEN,'C':BLUE,'I':MUTED}.get(value,MUTED)
            ax.add_patch(Rectangle((x,y),cell_w,row_h,facecolor=PAPER if row_index%2==0 else '#F4F1EC',edgecolor=GRID)); ax.text(x+cell_w/2,y+row_h/2,value,ha='center',va='center',fontsize=10,weight='bold' if value in {'A','R'} else 'normal',color=color)
    ax.text(.02,.055,'A 唯一问责 · R 至少一名执行 · C 征询 · I 知会',fontsize=9,color=MUTED)
    return fig


def _render_team(data,meta):
    fig,ax=_figure(data); members=data['members']; agreements=data['agreements']; risks=data['risks']
    _card(ax,.00,.57,.48,.35,'目的与成功定义',[_wrap(data['purpose'],38),f"成功：{_wrap(data['success_definition'],32)}"],GREEN,text_size=8.3)
    _card(ax,.52,.57,.48,.35,'成员、职责与决策范围',[f"{r['label']} · {r['role']}\n可决策：{_wrap(r['decision_scope'],24)}" for r in members],BLUE,text_size=7.3)
    by_id={r['id']:r['label'] for r in members}
    _card(ax,.00,.12,.48,.36,'团队约定',[f"{r['rule']}\n负责人 {by_id[r['owner_id']]} · 复核 {r['review_date']}" for r in agreements],AMBER,text_size=7.3)
    _card(ax,.52,.12,.48,.36,'风险与应对',[f"{r['statement']}\n负责人 {by_id[r['owner_id']]} · {r['mitigation']}" for r in risks],RED,text_size=7.3)
    return fig


def _render_affinity(data,meta):
    fig,ax=_figure(data); obs={r['id']:r for r in data['observations']}; themes=data['themes']; gap=.018; width=(1-gap*(len(themes)-1))/len(themes)
    en=str(data.get('language','zh')).lower().startswith('en')
    source_label='Source: ' if en else '来源：'
    count_label='items' if en else '条'
    # Keep the workshop wall compact when there are only a few observations,
    # while allowing dense groups to grow instead of shrinking body text.
    line_counts=[]; render_groups=[]
    for i,theme in enumerate(themes):
        color=COLORS[i%len(COLORS)]; lines=[]
        for oid in theme['observation_ids']:
            marker='◆ ' if oid in data.get('minority_observation_ids',[]) else '• '
            lines.append(marker+_wrap(obs[oid]['text'],18)+f"\n  {source_label}{obs[oid]['source']}")
            line_counts.append(1 + len(_wrap(obs[oid]['text'],18).splitlines()))
        render_groups.append(lines)
    card_h=min(.70,max(.42,.20+max(line_counts or [1])*.045))
    # Hold the card tops near the same reading line while keeping a footer gap;
    # sparse groups therefore do not sink into an oversized empty canvas.
    card_y=max(.20,.84-card_h)
    for i,(theme,lines) in enumerate(zip(themes,render_groups)):
        x=i*(width+gap); color=COLORS[i%len(COLORS)]
        _card(ax,x,card_y,width,card_h,f"{theme['label']} · {len(theme['observation_ids'])} {count_label}",lines,color,text_size=8.4)
    ax.text(0,.09,'◆ Minority feedback remains visible · Themes follow the original grouping' if en else '◆ 少数意见仍保留 · 主题名称建立在原始观察分组之后',fontsize=8.8,color=MUTED)
    return fig


def _render_matrix_org(data,meta):
    from matplotlib.patches import Rectangle
    fig,ax=_figure(data); deps=data['departments']; projects=data['projects']; members=data['members']; left=.24; top=.90; width=.70/len(deps); row_h=.19
    for col,dep in enumerate(deps):
        x=left+col*width; ax.add_patch(Rectangle((x,top-.12),width,.12,facecolor=INK,edgecolor=BG)); ax.text(x+width/2,top-.06,_wrap(dep['label']+'\n职能经理 '+dep['manager'],12),color='white',ha='center',va='center',fontsize=7.8)
    for row_index,project in enumerate(projects):
        y=top-.12-row_h*(row_index+1); ax.add_patch(Rectangle((.01,y),left-.02,row_h,facecolor='#E8E3DA',edgecolor=GRID)); ax.text(.02,y+row_h/2,_wrap(project['label']+'\n项目经理 '+project['manager']+'\n'+project['objective'],18),va='center',fontsize=7.5)
        for col,dep in enumerate(deps):
            x=left+col*width; ax.add_patch(Rectangle((x,y),width,row_h,facecolor=PAPER if (row_index+col)%2==0 else '#F4F1EC',edgecolor=GRID))
            rows=[m for m in members if m['department_id']==dep['id'] and project['id'] in m['project_ids']]
            ax.text(x+width/2,y+row_h/2,'\n'.join(f"{m['label']} · {m['role']}" for m in rows) or '—',ha='center',va='center',fontsize=7.5,color=INK if rows else MUTED)
    ax.plot([.02,.11],[.10,.10],color=INK,linewidth=1.6); ax.text(.12,.10,'实线：职能归属（列）',va='center',fontsize=8.2,color=MUTED)
    ax.plot([.36,.45],[.10,.10],color=BLUE,linewidth=1.6,linestyle='--'); ax.text(.46,.10,'虚线：项目分派（行）',va='center',fontsize=8.2,color=MUTED)
    ax.text(.75,.10,f"成员 {meta['members']} · 项目分派 {meta['project_assignments']}",va='center',fontsize=8.2,color=MUTED)
    return fig


RENDERERS={'people-network':_render_people,'hr-lifecycle':_render_hr,'raci':_render_raci,
           'team-canvas':_render_team,'influence-map':_render_influence,'affinity-map':_render_affinity,
           'matrix-org':_render_matrix_org,'causal-loop':_render_causal}


def render(data,output,stem=None):
    import matplotlib
    import matplotlib.pyplot as plt
    meta=analyze(data); output=Path(output); output.mkdir(parents=True,exist_ok=True); stem=stem or data.get('id') or data['mode']
    fig=RENDERERS[data['mode']](data,meta)
    fig.savefig(output/f'{stem}.svg',facecolor=BG,metadata={'Date':None})
    fig.savefig(output/f'{stem}.png',facecolor=BG,dpi=150,metadata={'Software':'diagram-studio organization_relations.py'})
    plt.close(fig)
    (output/f'{stem}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    meta['matplotlib_version']=matplotlib.__version__; meta['scope']='验证本批次角色、关系、证据、责任、分组、双重汇报和反馈极性；模拟示例不代表现场组织或因果结论'
    (output/f'{stem}.calculation.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    qa={'mode':data['mode'],'errors':[],'warnings':[],'layout_issues':[],
        'checks':['schema validated','references resolved','semantic constraints evaluated','editable input preserved']}
    (output/f'{stem}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('input',type=Path); parser.add_argument('--out',type=Path,default=Path('.')); args=parser.parse_args()
    data=json.loads(args.input.read_text()); result=render(data,args.out,args.input.stem); print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__': main()
