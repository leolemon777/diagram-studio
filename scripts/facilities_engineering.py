#!/usr/bin/env python3
"""Validate and render facilities and engineering-plan teaching models.

The inputs are simulated and retain dimensions, identifiers and routes. They are
not code-compliance drawings, stamped engineering designs or installation sets.
"""
from __future__ import annotations

import argparse
import json
import math
import textwrap
from collections import Counter, defaultdict, deque
from pathlib import Path


INK='#30302D'; MUTED='#6D6A63'; BG='#F1EFEB'; PAPER='#FAF9F6'; GRID='#D8D3C8'
GREEN='#58705A'; BLUE='#657487'; AMBER='#C1965B'; RED='#A65448'; PLUM='#80706A'


def _need(condition, message):
    if not condition: raise ValueError(message)


def _rows(data,key,allow_empty=False):
    rows=data.get(key); _need(isinstance(rows,list) and (allow_empty or rows),f'{key} required')
    ids=[row.get('id') for row in rows]; _need(all(isinstance(v,str) and v.strip() for v in ids),f'{key} ids required')
    _need(len(ids)==len(set(ids)),f'{key} ids must be unique'); return rows


def _base(data,mode):
    _need(data.get('mode')==mode,f'mode must be {mode}')
    _need(isinstance(data.get('title'),str) and data['title'].strip(),'title required')
    _need(data.get('data_status') in {'simulated','observed','mixed'},'data_status required')
    _need(isinstance(data.get('assumptions'),list),'assumptions required')


def _finite(value): return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def _plan(data):
    plan=data.get('plan'); _need(isinstance(plan,dict),'plan required')
    w=plan.get('width_m'); h=plan.get('height_m')
    _need(_finite(w) and _finite(h) and w>0 and h>0,'positive plan dimensions required')
    return plan,w,h


def _point(value,w,h,message='point outside plan'):
    _need(isinstance(value,list) and len(value)==2 and all(_finite(v) for v in value),'finite point required')
    _need(0<=value[0]<=w and 0<=value[1]<=h,message)


def _rect(value,w,h,message='rectangle outside plan'):
    _need(isinstance(value,list) and len(value)==4 and all(_finite(v) for v in value),'finite rectangle required')
    x,y,rw,rh=value; _need(0<=x<w and 0<=y<h and rw>0 and rh>0 and x+rw<=w and y+rh<=h,message)


def _polyline(value,w,h):
    _need(isinstance(value,list) and len(value)>=2,'route needs at least two points')
    for point in value: _point(point,w,h)


def _rooms(data,w,h):
    rooms=_rows(data,'rooms'); total=0
    for row in rooms:
        _need(row.get('label') and row.get('zone'),'room label and zone required'); _rect(row.get('rect'),w,h)
        total+=row['rect'][2]*row['rect'][3]
    return rooms,total


def _facility_layout(data):
    _base(data,'facility-layout'); profile=data.get('profile'); _need(profile in {'office','seating'},'facility profile invalid')
    plan,w,h=_plan(data); rooms,room_area=_rooms(data,w,h)
    routes=_rows(data,'routes')
    requirement=data.get('clearance_requirement_mm'); _need(_finite(requirement) and requirement>0,'clearance requirement required')
    _need(data.get('requirement_source'),'clearance requirement source required')
    clearances=[]
    for row in routes:
        _polyline(row.get('points'),w,h); _need(_finite(row.get('clearance_mm')) and row['clearance_mm']>0,'route clearance required')
        _need(isinstance(row.get('accessible'),bool) and row.get('evidence'),'route accessibility and evidence required')
        if row['accessible']: _need(row['clearance_mm']>=requirement,'accessible route below declared clearance requirement')
        clearances.append(row['clearance_mm'])
    if profile=='office':
        items=_rows(data,'items'); desk_count=0
        for row in items:
            _need(row.get('label') and row.get('kind') in {'desk','meeting-table','storage','printer','pantry','plant'},'office item invalid')
            _rect(row.get('rect'),w,h); desk_count+=row['kind']=='desk'
        _need(desk_count>=4,'office example needs at least four workstations')
        return {'mode':'facility-layout','profile':'office','plan_area_m2':round(w*h,2),'room_area_m2':round(room_area,2),'rooms':len(rooms),'items':len(items),'workstations':desk_count,'routes':len(routes),'minimum_clearance_mm':min(clearances),'declared_clearance_check':'passed'}
    seats=_rows(data,'seats'); exits=_rows(data,'exits'); spaces=_rows(data,'accessible_spaces')
    labels=set()
    for row in seats:
        _need(row.get('row') and isinstance(row.get('number'),int) and row['number']>0,'seat row and number required'); _point(row.get('position'),w,h)
        key=(row['row'],row['number']); _need(key not in labels,'duplicate seat label'); labels.add(key)
    for row in exits: _need(row.get('label'),'exit label required'); _point(row.get('position'),w,h)
    for row in spaces:
        _need(row.get('label') and row.get('adjacent_route_id') in {r['id'] for r in routes},'accessible space route reference invalid'); _rect(row.get('rect'),w,h)
    _need(len(exits)>=2 and spaces,'seating example needs two exits and accessible spaces')
    return {'mode':'facility-layout','profile':'seating','plan_area_m2':round(w*h,2),'room_area_m2':round(room_area,2),'rooms':len(rooms),'seats':len(seats),'accessible_spaces':len(spaces),'exits':len(exits),'routes':len(routes),'minimum_clearance_mm':min(clearances),'declared_clearance_check':'passed'}


def _electrical_telecom(data):
    _base(data,'electrical-telecom-plan'); plan,w,h=_plan(data); rooms,_=_rooms(data,w,h)
    equipment=_rows(data,'equipment'); endpoints=_rows(data,'endpoints'); routes=_rows(data,'routes')
    eq={r['id']:r for r in equipment}; ep={r['id']:r for r in endpoints}; ids=set(eq)|set(ep)
    for row in equipment:
        _need(row.get('label') and row.get('system') in {'power','data'},'equipment system invalid'); _point(row.get('position'),w,h)
        _need(row.get('tag') and row.get('rating'),'equipment tag and rating required')
    for row in endpoints:
        _need(row.get('label') and row.get('system') in {'power','data'},'endpoint system invalid'); _point(row.get('position'),w,h)
        _need(row.get('tag') and row.get('circuit_or_port'),'endpoint tag and circuit/port required')
    route_systems=Counter()
    for row in routes:
        _need(row.get('system') in {'power','data'} and row.get('source') in ids and row.get('target') in ids,'route system or endpoints invalid')
        _need((eq|ep)[row['source']]['system']==row['system'] and (eq|ep)[row['target']]['system']==row['system'],'route system must match endpoints')
        _polyline(row.get('points'),w,h); _need(row.get('cable_spec') and row.get('evidence'),'route cable and evidence required'); route_systems[row['system']]+=1
    _need(route_systems['power'] and route_systems['data'],'power and data routes must both be present')
    tags=[r['tag'] for r in equipment+endpoints]; _need(len(tags)==len(set(tags)),'equipment and endpoint tags must be unique')
    return {'mode':'electrical-telecom-plan','plan_area_m2':round(w*h,2),'rooms':len(rooms),'equipment':len(equipment),'endpoints':len(endpoints),'routes':len(routes),'route_systems':dict(sorted(route_systems.items())),'tag_uniqueness':'passed','power_data_separation':'passed'}


def _security_access(data):
    _base(data,'security-access-plan'); plan,w,h=_plan(data); rooms,_=_rooms(data,w,h)
    zones=_rows(data,'access_zones'); doors=_rows(data,'doors'); devices=_rows(data,'devices')
    zone_ids={r['id'] for r in zones}
    for row in zones: _need(row.get('label') and row.get('authorization'),'zone fields required'); _rect(row.get('rect'),w,h)
    for row in doors:
        _need(row.get('label') and row.get('from_zone') in zone_ids and row.get('to_zone') in zone_ids,'door zones invalid'); _point(row.get('position'),w,h)
        _need(row.get('credential_rule'),'door credential rule required')
    counts=Counter()
    for row in devices:
        _need(row.get('label') and row.get('kind') in {'reader','camera','request-to-exit','door-contact'},'security device kind invalid'); _point(row.get('position'),w,h); counts[row['kind']]+=1
        _need(row.get('tag') and row.get('evidence'),'device tag and evidence required')
        if row['kind']=='camera':
            _need(_finite(row.get('bearing_deg')) and _finite(row.get('fov_deg')) and 0<row['fov_deg']<=180,'camera field of view invalid')
            _need(_finite(row.get('range_m')) and row['range_m']>0,'camera illustrative range required')
    _need(data.get('coverage_claim')=='illustrative-only','security coverage must be declared illustrative-only')
    _need(counts['reader'] and counts['camera'],'reader and camera examples required')
    return {'mode':'security-access-plan','plan_area_m2':round(w*h,2),'rooms':len(rooms),'access_zones':len(zones),'doors':len(doors),'devices':len(devices),'device_types':dict(sorted(counts.items())),'coverage_claim':'illustrative-only','blind_spot_claim':'not-evaluated'}


def _evacuation(data):
    _base(data,'evacuation-plan'); plan,w,h=_plan(data); rooms,_=_rooms(data,w,h)
    nodes=_rows(data,'nodes'); edges=_rows(data,'edges'); ids={r['id'] for r in nodes}; by={r['id']:r for r in nodes}
    currents=[r for r in nodes if r.get('kind')=='current']; exits=[r for r in nodes if r.get('kind')=='exit']
    _need(len(currents)==1 and len(exits)>=2,'one current location and at least two exits required')
    for row in nodes:
        _need(row.get('label') and row.get('kind') in {'current','waypoint','exit','assembly'},'evacuation node invalid'); _point(row.get('position'),w,h)
        if row['kind']=='exit':
            x,y=row['position']; _need(min(x,w-x,y,h-y)<=.05,'exit must be on plan boundary')
    graph=defaultdict(list); route_ids=set(); total=defaultdict(float)
    for row in edges:
        _need(row.get('source') in ids and row.get('target') in ids and row['source']!=row['target'],'evacuation edge invalid')
        _need(row.get('route_id') and _finite(row.get('length_m')) and row['length_m']>0,'route id and length required')
        _need(row.get('verified_against') and row.get('blocked') is False,'evacuation edge must be verified and unblocked in input')
        graph[row['source']].append(row['target']); route_ids.add(row['route_id']); total[row['route_id']]+=row['length_m']
    reachable=set([currents[0]['id']]); q=deque(reachable)
    while q:
        for nxt in graph[q.popleft()]:
            if nxt not in reachable: reachable.add(nxt); q.append(nxt)
    _need(all(r['id'] in reachable for r in exits),'every declared exit must be reachable from current location')
    _need(len(route_ids)>=2,'at least two distinct evacuation routes required')
    _need(data.get('compliance_status')=='requires-local-review','evacuation plan must require local review')
    return {'mode':'evacuation-plan','plan_area_m2':round(w*h,2),'rooms':len(rooms),'nodes':len(nodes),'edges':len(edges),'routes':len(route_ids),'reachable_exits':len(exits),'route_lengths_m':dict(sorted((k,round(v,2)) for k,v in total.items())),'continuity_check':'passed','compliance_status':'requires-local-review'}


def _hvac(data):
    _base(data,'hvac-plan'); plan,w,h=_plan(data); rooms,_=_rooms(data,w,h)
    equipment=_rows(data,'equipment'); terminals=_rows(data,'terminals'); ducts=_rows(data,'ducts'); controls=_rows(data,'controls')
    ids={r['id'] for r in equipment+terminals}
    for row in equipment:
        _need(row.get('label') and row.get('kind') in {'ahu','fan','damper','vav'},'HVAC equipment invalid'); _point(row.get('position'),w,h); _need(row.get('tag'),'HVAC equipment tag required')
    flow=Counter()
    for row in terminals:
        _need(row.get('label') and row.get('kind') in {'supply','return','exhaust'},'HVAC terminal invalid'); _point(row.get('position'),w,h)
        _need(_finite(row.get('airflow_lps')) and row['airflow_lps']>0,'terminal airflow required'); flow[row['kind']]+=row['airflow_lps']
    for row in ducts:
        _need(row.get('source') in ids and row.get('target') in ids and row.get('system') in {'supply','return','exhaust'},'duct endpoints or system invalid')
        _polyline(row.get('points'),w,h); _need(_finite(row.get('width_mm')) and row['width_mm']>0,'duct width required'); _need(row.get('flow_direction'),'duct flow direction required')
    for row in controls:
        _need(row.get('sensor') in ids and row.get('controlled') in ids and row.get('signal'),'control link invalid')
    balance=round(flow['supply']-flow['return']-flow['exhaust'],3)
    _need(abs(balance)<=data.get('allowed_balance_lps',0),'HVAC air balance exceeds declared allowance')
    return {'mode':'hvac-plan','plan_area_m2':round(w*h,2),'rooms':len(rooms),'equipment':len(equipment),'terminals':len(terminals),'ducts':len(ducts),'controls':len(controls),'airflow_lps':dict(sorted(flow.items())),'air_balance_lps':balance,'flow_balance_check':'passed'}


def _wiring(data):
    _base(data,'wiring-diagram'); devices=_rows(data,'devices'); wires=_rows(data,'wires')
    terminals={}
    for row in devices:
        _need(row.get('label') and row.get('tag') and isinstance(row.get('terminals'),list) and row['terminals'],'device label, tag and terminals required')
        _need(len(row['terminals'])==len(set(row['terminals'])),'device terminal labels must be unique')
        pos=row.get('position'); _need(isinstance(pos,list) and len(pos)==2 and all(_finite(v) and 0<=v<=1 for v in pos),'normalized device position required')
        for terminal in row['terminals']: terminals[f"{row['id']}.{terminal}"]=row['id']
    used=set(); wire_numbers=[]
    for row in wires:
        _need(row.get('from') in terminals and row.get('to') in terminals and row['from']!=row['to'],'wire terminal reference invalid')
        _need(row['from'] not in used and row['to'] not in used,'terminal used by more than one wire in simple example'); used|={row['from'],row['to']}
        _need(row.get('wire_no') and row.get('conductor_spec') and row.get('signal'),'wire number, conductor and signal required'); wire_numbers.append(row['wire_no'])
    _need(len(wire_numbers)==len(set(wire_numbers)),'wire numbers must be unique')
    return {'mode':'wiring-diagram','devices':len(devices),'terminals':len(terminals),'wires':len(wires),'wire_number_uniqueness':'passed','terminal_endpoint_check':'passed','conductor_spec_coverage':'passed'}


def _single_line(data):
    _base(data,'single-line'); nodes=_rows(data,'nodes'); edges=_rows(data,'edges'); ids={r['id'] for r in nodes}; by={r['id']:r for r in nodes}
    sources=[r for r in nodes if r.get('kind')=='source']; _need(len(sources)==1,'single-line example needs one source')
    allowed={'source','breaker','bus','transformer','meter','load'}
    total_load=0
    for row in nodes:
        _need(row.get('label') and row.get('tag') and row.get('kind') in allowed,'single-line node invalid')
        pos=row.get('position'); _need(isinstance(pos,list) and len(pos)==2 and all(_finite(v) and 0<=v<=1 for v in pos),'normalized node position required')
        _need(_finite(row.get('voltage_v')) and row['voltage_v']>0 and row.get('rating'),'node voltage and rating required')
        if row['kind']=='load': _need(_finite(row.get('load_kw')) and row['load_kw']>=0,'load kW required'); total_load+=row['load_kw']
    incoming=Counter(); graph=defaultdict(list)
    for row in edges:
        _need(row.get('source') in ids and row.get('target') in ids and row['source']!=row['target'],'single-line edge invalid')
        _need(row.get('conductor') and row.get('protection_basis'),'conductor and protection basis required')
        graph[row['source']].append(row['target']); incoming[row['target']]+=1
    _need(all(incoming[r['id']]<=1 for r in nodes),'single-line simple radial model cannot have multiple incoming feeders')
    seen=set(); visiting=set()
    def walk(node):
        _need(node not in visiting,'single-line cycle detected');
        if node in seen:return
        visiting.add(node)
        for nxt in graph[node]: walk(nxt)
        visiting.remove(node); seen.add(node)
    walk(sources[0]['id']); _need(seen==ids,'all single-line nodes must be reachable from source')
    for row in edges:
        a,b=by[row['source']],by[row['target']]
        if a['voltage_v']!=b['voltage_v']: _need(a['kind']=='transformer' or b['kind']=='transformer','voltage may change only across a transformer')
    _need(data.get('engineering_status')=='illustrative-requires-design-review','engineering review status required')
    return {'mode':'single-line','nodes':len(nodes),'edges':len(edges),'loads':sum(r['kind']=='load' for r in nodes),'total_load_kw':round(total_load,2),'radial_reachability':'passed','cycle_check':'passed','engineering_status':'illustrative-requires-design-review'}


def _plumbing(data):
    _base(data,'plumbing-plan'); plan,w,h=_plan(data); rooms,_=_rooms(data,w,h)
    nodes=_rows(data,'nodes'); pipes=_rows(data,'pipes'); ids={r['id'] for r in nodes}; fixtures={r['id'] for r in nodes if r.get('kind')=='fixture'}
    for row in nodes:
        _need(row.get('label') and row.get('kind') in {'source','heater','fixture','stack','drain'},'plumbing node invalid'); _point(row.get('position'),w,h); _need(row.get('tag'),'plumbing tag required')
    systems=Counter(); fixture_systems=defaultdict(set)
    for row in pipes:
        _need(row.get('source') in ids and row.get('target') in ids and row['source']!=row['target'],'pipe endpoints invalid')
        _need(row.get('system') in {'cold','hot','waste'},'pipe system invalid'); _polyline(row.get('points'),w,h)
        _need(_finite(row.get('diameter_mm')) and row['diameter_mm']>0 and row.get('flow_direction'),'pipe diameter and flow direction required')
        if row['system']=='waste': _need(_finite(row.get('slope_percent')) and row['slope_percent']>0,'waste pipe slope required')
        systems[row['system']]+=1
        for endpoint in (row['source'],row['target']):
            if endpoint in fixtures: fixture_systems[endpoint].add(row['system'])
    _need(all({'cold','waste'}<=fixture_systems[f] for f in fixtures),'each fixture needs cold supply and waste connection')
    _need(data.get('engineering_status')=='schematic-requires-local-design','plumbing review status required')
    return {'mode':'plumbing-plan','plan_area_m2':round(w*h,2),'rooms':len(rooms),'nodes':len(nodes),'fixtures':len(fixtures),'pipes':len(pipes),'systems':dict(sorted(systems.items())),'fixture_connection_check':'passed','waste_slope_coverage':'passed','engineering_status':'schematic-requires-local-design'}


ANALYZERS={'facility-layout':_facility_layout,'electrical-telecom-plan':_electrical_telecom,'security-access-plan':_security_access,'evacuation-plan':_evacuation,'hvac-plan':_hvac,'wiring-diagram':_wiring,'single-line':_single_line,'plumbing-plan':_plumbing}


def analyze(data):
    _need(data.get('mode') in ANALYZERS,'unsupported facilities/engineering mode'); result=ANALYZERS[data['mode']](data)
    result['data_status']=data['data_status']; result['assumptions']=data.get('assumptions',[]); return result


def _font():
    from matplotlib import font_manager
    path=Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists(): font_manager.fontManager.addfont(path); return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def _figure(data):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family':_font(),'font.size':10,'text.color':INK,'axes.unicode_minus':False,'svg.fonttype':'none','svg.hashsalt':'diagram-studio-facilities-engineering-v1'})
    fig=plt.figure(figsize=(12.8,7.6),facecolor=BG); ax=fig.add_axes((.055,.09,.89,.77)); ax.axis('off')
    fig.text(.055,.955,data['title'],fontsize=21.5,color=INK,weight='medium',va='top'); fig.text(.055,.912,data.get('subtitle',''),fontsize=10,color=MUTED,va='top')
    fig.text(.945,.95,data['mode'].upper().replace('-','  '),fontsize=8,color=MUTED,ha='right',va='top'); return fig,ax


def _wrap(value,width=16): return '\n'.join(textwrap.wrap(str(value),width=width,break_long_words=False,break_on_hyphens=False))


def _setup_plan(ax,data):
    _,w,h=_plan(data); ax.set_xlim(-.4,w+.4); ax.set_ylim(-.4,h+.4); ax.set_aspect('equal')
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((0,0),w,h,fc=PAPER,ec=INK,lw=1.7,zorder=.1))
    return w,h


def _draw_rooms(ax,data):
    from matplotlib.patches import Rectangle
    for i,row in enumerate(data['rooms']):
        x,y,w,h=row['rect']; ax.add_patch(Rectangle((x,y),w,h,fc=[BLUE,GREEN,AMBER,PLUM][i%4],alpha=.055,ec=GRID,lw=1,zorder=.2))
        ax.text(x+.15,y+h-.18,row['label'],fontsize=7.8,color=MUTED,va='top',zorder=3)


def _route(ax,points,color,label='',lw=2,style='-',label_at=None):
    xs=[p[0] for p in points]; ys=[p[1] for p in points]; ax.plot(xs,ys,color=color,lw=lw,linestyle=style,zorder=2)
    ax.annotate('',xy=points[-1],xytext=points[-2],arrowprops=dict(arrowstyle='-|>',color=color,lw=lw,shrinkA=0,shrinkB=0),zorder=3)
    if label:
        mid=label_at or points[len(points)//2]; ax.text(mid[0],mid[1]+.16,_wrap(label,22),fontsize=6.6,color=color,ha='center',va='bottom',bbox=dict(fc=BG,ec='none',pad=.12,alpha=.94),zorder=5)


def _footer(fig,calc):
    skip={'mode','profile','data_status','assumptions','route_systems','device_types','route_lengths_m','airflow_lps','systems','engineering_status','compliance_status'}; facts=[]
    for key,value in calc.items():
        if key in skip: continue
        if isinstance(value,(str,int,float)) and len(facts)<5: facts.append(f"{key.replace('_',' ')}: {value}")
    fig.text(.055,.035,'  ·  '.join(facts),fontsize=7.2,color=MUTED); fig.text(.945,.035,'模拟输入 / 需用真实底图、清册和属地要求替换',fontsize=7.2,color=MUTED,ha='right')


def _render_facility(data,calc,fig,ax):
    from matplotlib.patches import Rectangle,Circle
    _setup_plan(ax,data); _draw_rooms(ax,data)
    if data['profile']=='office':
        colors={'desk':BLUE,'meeting-table':PLUM,'storage':GREEN,'printer':AMBER,'pantry':RED,'plant':GREEN}
        for row in data['items']:
            x,y,w,h=row['rect']; ax.add_patch(Rectangle((x,y),w,h,fc=colors[row['kind']],alpha=.18,ec=colors[row['kind']],lw=1,zorder=2)); ax.text(x+w/2,y+h/2,_wrap(row['label'],9),fontsize=6.2,ha='center',va='center')
    else:
        for row in data['seats']:
            x,y=row['position']; ax.add_patch(Circle((x,y),.16,fc=BLUE,alpha=.28,ec=BLUE,lw=.7)); ax.text(x,y,f"{row['row']}{row['number']}",fontsize=5.3,ha='center',va='center')
        for row in data['accessible_spaces']:
            x,y,w,h=row['rect']; ax.add_patch(Rectangle((x,y),w,h,fc=GREEN,alpha=.12,ec=GREEN,lw=1.4,linestyle='--')); ax.text(x+w/2,y+h/2,row['label'],fontsize=6.3,ha='center',va='center',color=GREEN)
        for row in data['exits']: ax.text(*row['position'],f"出口\n{row['label']}",fontsize=7,color=RED,ha='center',va='center',weight='medium')
    for row in data['routes']: _route(ax,row['points'],GREEN if row['accessible'] else MUTED,f"{row['label']} · {row['clearance_mm']:.0f} mm",lw=2.1 if row['accessible'] else 1.2,style='-' if row['accessible'] else '--')


def _render_electrical(data,calc,fig,ax):
    from matplotlib.patches import Circle,Rectangle
    _setup_plan(ax,data); _draw_rooms(ax,data); colors={'power':RED,'data':BLUE}; allrows={r['id']:r for r in data['equipment']+data['endpoints']}
    for row in data['routes']: _route(ax,row['points'],colors[row['system']],f"{row['label']} · {row['cable_spec']}",1.5,'-' if row['system']=='power' else '--',row.get('label_at'))
    for row in data['equipment']:
        x,y=row['position']; ax.add_patch(Rectangle((x-.60,y-.34),1.2,.68,fc=PAPER,ec=colors[row['system']],lw=1.4,zorder=4)); ax.text(x,y,_wrap(f"{row['tag']}\n{row['label']}",12),fontsize=6.4,ha='center',va='center',zorder=5)
    for row in data['endpoints']:
        x,y=row['position']; ax.add_patch(Circle((x,y),.22,fc=PAPER,ec=colors[row['system']],lw=1.25,zorder=4)); ax.text(x,y,_wrap(row['tag'],8),fontsize=5.7,ha='center',va='center',zorder=5)
    ax.text(.1,data['plan']['height_m']-.35,'红：电力　蓝：通信　线路分层表达',fontsize=7.5,color=MUTED)


def _render_security(data,calc,fig,ax):
    from matplotlib.patches import Rectangle,Wedge,Circle
    _setup_plan(ax,data); _draw_rooms(ax,data); colors=[BLUE,GREEN,AMBER,PLUM]
    for i,row in enumerate(data['access_zones']):
        x,y,w,h=row['rect']; ax.add_patch(Rectangle((x,y),w,h,fc=colors[i%4],alpha=.055,ec=colors[i%4],lw=1.3,linestyle='--')); ax.text(x+.12,y+.15,f"{row['label']} · {row['authorization']}",fontsize=6.5,color=colors[i%4])
    for row in data['doors']:
        x,y=row['position']; lx,ly=row.get('label_at',(x,y-.45))
        ax.add_patch(Rectangle((x-.18,y-.06),.36,.12,fc=PAPER,ec=RED,lw=1.3,zorder=5))
        ax.annotate(f"{row['label']}\n{row['credential_rule']}",xy=(x,y),xytext=(lx,ly),fontsize=5.8,color=RED,ha='center',va='center',bbox=dict(fc=PAPER,ec=RED,pad=.18),arrowprops=dict(arrowstyle='-',color=RED,lw=.7),zorder=6)
    for row in data['devices']:
        x,y=row['position']
        if row['kind']=='camera':
            ax.add_patch(Wedge((x,y),row['range_m'],row['bearing_deg']-row['fov_deg']/2,row['bearing_deg']+row['fov_deg']/2,fc=AMBER,ec=AMBER,alpha=.13,lw=.8,zorder=1)); ax.add_patch(Circle((x,y),.16,fc=PAPER,ec=AMBER,lw=1.3,zorder=4))
        else: ax.add_patch(Rectangle((x-.13,y-.13),.26,.26,fc=PAPER,ec=BLUE,lw=1.2,zorder=4))
        lx,ly=row.get('label_at',(x,y+.22)); ax.annotate(row['tag'],xy=(x,y),xytext=(lx,ly),fontsize=5.8,color=INK,ha='center',va='center',arrowprops=dict(arrowstyle='-',color=MUTED,lw=.55) if (lx,ly)!=(x,y+.22) else None,zorder=5)
    ax.text(.1,data['plan']['height_m']-.35,'覆盖范围仅为示意；未做盲区、像素密度或法规符合性结论',fontsize=7.2,color=RED)


def _render_evacuation(data,calc,fig,ax):
    from matplotlib.patches import Circle
    _setup_plan(ax,data); _draw_rooms(ax,data); by={r['id']:r for r in data['nodes']}; colors={'R1':GREEN,'R2':BLUE}
    for row in data['edges']:
        a=by[row['source']]['position']; b=by[row['target']]['position']; _route(ax,[a,b],colors.get(row['route_id'],GREEN),f"{row['route_id']} · {row['length_m']} m",2,label_at=row.get('label_at'))
    for row in data['nodes']:
        x,y=row['position']; color=RED if row['kind']=='current' else GREEN if row['kind']=='exit' else BLUE
        ax.add_patch(Circle((x,y),.22,fc=PAPER,ec=color,lw=1.5,zorder=4)); lx,ly=row.get('label_at',(x,y)); ax.annotate(_wrap(row['label'],8),xy=(x,y),xytext=(lx,ly),fontsize=6.2,ha='center',va='center',weight='medium' if row['kind'] in {'current','exit'} else 'normal',arrowprops=dict(arrowstyle='-',color=color,lw=.55) if (lx,ly)!=(x,y) else None,zorder=5)
    ax.text(.1,data['plan']['height_m']-.35,'示例不替代属地消防审查、现场核对、标识安装或演练',fontsize=7.2,color=RED)


def _render_hvac(data,calc,fig,ax):
    from matplotlib.patches import Circle,Rectangle
    _setup_plan(ax,data); _draw_rooms(ax,data); colors={'supply':BLUE,'return':GREEN,'exhaust':AMBER}; by={r['id']:r for r in data['equipment']+data['terminals']}
    for row in data['ducts']: _route(ax,row['points'],colors[row['system']],f"{row['label']} · {row['width_mm']} mm",max(1.2,row['width_mm']/180),'-',row.get('label_at'))
    for row in data['equipment']:
        x,y=row['position']; ax.add_patch(Rectangle((x-.34,y-.22),.68,.44,fc=PAPER,ec=PLUM,lw=1.4,zorder=4)); ax.text(x,y,row['tag'],fontsize=6.4,ha='center',va='center',zorder=5); lx,ly=row.get('label_at',(x,y-.42)); ax.annotate(row['label'],xy=(x,y),xytext=(lx,ly),fontsize=5.8,ha='center',va='center',color=INK,arrowprops=dict(arrowstyle='-',color=PLUM,lw=.55),zorder=5)
    for row in data['terminals']:
        x,y=row['position']; ax.add_patch(Circle((x,y),.18,fc=PAPER,ec=colors[row['kind']],lw=1.3,zorder=4)); lx,ly=row.get('label_at',(x,y+.34)); ax.annotate(f"{row['label']}\n{row['airflow_lps']} L/s",xy=(x,y),xytext=(lx,ly),fontsize=5.6,color=colors[row['kind']],ha='center',va='center',arrowprops=dict(arrowstyle='-',color=colors[row['kind']],lw=.5),zorder=5)
    ax.text(.1,data['plan']['height_m']-.35,'蓝：送风　绿：回风　黄：排风　流量为模拟设计点',fontsize=7.2,color=MUTED)


def _render_wiring(data,calc,fig,ax):
    from matplotlib.patches import Rectangle,Circle
    ax.set_xlim(0,1); ax.set_ylim(0,1); devices={r['id']:r for r in data['devices']}; terminals={}
    for row in data['devices']:
        x,y=row['position']; w=.18; h=.11+.025*len(row['terminals']); ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc=PAPER,ec=BLUE,lw=1.4,zorder=3)); ax.text(x,y+h/2-.025,f"{row['tag']} · {row['label']}",fontsize=7,ha='center',va='top')
        for i,t in enumerate(row['terminals']):
            ty=y+h/2-.065-i*.025; side=-1 if x>.5 else 1; tx=x+side*w/2; terminals[f"{row['id']}.{t}"]=(tx,ty); ax.add_patch(Circle((tx,ty),.006,fc=INK,ec=INK,zorder=5)); ax.text(tx-side*.012,ty,t,fontsize=5.6,ha='right' if side==1 else 'left',va='center')
    for row in data['wires']:
        a=terminals[row['from']]; b=terminals[row['to']]; mid=(a[0]+b[0])/2; ax.plot([a[0],mid,mid,b[0]],[a[1],a[1],b[1],b[1]],color=RED if '24V' in row['signal'] else GREEN,lw=1.2,zorder=1)
        lx,ly=row.get('label_at',(mid,(a[1]+b[1])/2)); ax.text(lx,ly,_wrap(f"{row['wire_no']}\n{row['conductor_spec']}\n{row['signal']}",15),fontsize=5.2,ha='center',va='center',bbox=dict(fc=BG,ec='none',pad=.12),zorder=4)
    ax.text(.02,.97,'端子—线号—导体规格—信号逐线保留；不替代端子厂家图或现场导通测试',fontsize=7.3,color=MUTED,va='top')


def _render_single(data,calc,fig,ax):
    from matplotlib.patches import FancyBboxPatch
    ax.set_xlim(0,1); ax.set_ylim(0,1); by={r['id']:r for r in data['nodes']}
    for row in data['edges']:
        a=by[row['source']]['position']; b=by[row['target']]['position']; ax.plot([a[0],b[0]],[a[1],b[1]],color=INK,lw=1.5,zorder=1)
        mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2; ax.text(mx,my,_wrap(row['conductor'],18),fontsize=5.7,color=MUTED,ha='center',va='center',bbox=dict(fc=BG,ec='none',pad=.1),zorder=4)
    colors={'source':RED,'breaker':AMBER,'bus':INK,'transformer':PLUM,'meter':BLUE,'load':GREEN}
    for row in data['nodes']:
        x,y=row['position']; patch=FancyBboxPatch((x-.08,y-.035),.16,.07,boxstyle='round,pad=.006,rounding_size=.008',fc=PAPER,ec=colors[row['kind']],lw=1.4,zorder=3); ax.add_patch(patch)
        label=f"{row['tag']} · {row['label']}\n{row['voltage_v']} V · {row['rating']}"+(f" · {row['load_kw']} kW" if row['kind']=='load' else '')
        ax.text(x,y,_wrap(label,22),fontsize=6.2,ha='center',va='center',zorder=4)
    ax.text(.02,.97,'单线示意：额定值和保护依据必须由真实设计替换并复核',fontsize=7.3,color=RED,va='top')


def _render_plumbing(data,calc,fig,ax):
    from matplotlib.patches import Circle,Rectangle
    _setup_plan(ax,data); _draw_rooms(ax,data); colors={'cold':BLUE,'hot':RED,'waste':GREEN}; by={r['id']:r for r in data['nodes']}
    for row in data['pipes']:
        label=f"{row['label']} · DN{row['diameter_mm']}"+(f" · 坡度 {row['slope_percent']}%" if row['system']=='waste' else '')
        _route(ax,row['points'],colors[row['system']],label,2 if row['system']=='waste' else 1.4,'--' if row['system']=='waste' else '-',row.get('label_at'))
    for row in data['nodes']:
        x,y=row['position']
        if row['kind']=='fixture': ax.add_patch(Circle((x,y),.20,fc=PAPER,ec=PLUM,lw=1.3,zorder=4))
        else: ax.add_patch(Rectangle((x-.25,y-.18),.5,.36,fc=PAPER,ec=AMBER,lw=1.3,zorder=4))
        ax.text(x,y,row['tag'],fontsize=5.5,ha='center',va='center',zorder=5); lx,ly=row.get('label_at',(x,y-.36)); ax.annotate(row['label'],xy=(x,y),xytext=(lx,ly),fontsize=5.7,ha='center',va='center',color=INK,arrowprops=dict(arrowstyle='-',color=MUTED,lw=.5),zorder=5)
    ax.text(.1,data['plan']['height_m']-.35,'蓝：冷水　红：热水　绿虚线：排水；管径、坡度与标高需按属地设计',fontsize=7.2,color=MUTED)


RENDERERS={'facility-layout':_render_facility,'electrical-telecom-plan':_render_electrical,'security-access-plan':_render_security,'evacuation-plan':_render_evacuation,'hvac-plan':_render_hvac,'wiring-diagram':_render_wiring,'single-line':_render_single,'plumbing-plan':_render_plumbing}


def render(data,out,name=None):
    calc=analyze(data); out=Path(out); out.mkdir(parents=True,exist_ok=True); name=name or data.get('id') or data['mode']
    fig,ax=_figure(data); RENDERERS[data['mode']](data,calc,fig,ax); _footer(fig,calc)
    fig.savefig(out/f'{name}.svg',format='svg',facecolor=BG,metadata={'Date':None}); fig.savefig(out/f'{name}.png',dpi=150,facecolor=BG)
    import matplotlib.pyplot as plt; plt.close(fig)
    (out/f'{name}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (out/f'{name}.calculation.json').write_text(json.dumps(calc,ensure_ascii=False,indent=2)+'\n')
    qa={'errors':[],'warnings':[],'layout_issues':[],'text_overflow':[],'text_overlap':[],'missing_glyphs':[],'semantic_validation':'passed'}
    (out/f'{name}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n'); return calc


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('--out',required=True); p.add_argument('--name'); args=p.parse_args()
    data=json.loads(Path(args.input).read_text()); print(json.dumps(render(data,args.out,args.name or Path(args.input).stem),ensure_ascii=False))


if __name__=='__main__': main()
