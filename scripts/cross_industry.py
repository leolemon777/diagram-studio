#!/usr/bin/env python3
"""Validate and render common cross-industry diagram and document models."""
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

INK='#30302D'; MUTED='#6D6A63'; BG='#F1EFEB'; PAPER='#FAF9F6'; GRID='#D8D3C8'
COLORS=['#657487','#58705A','#C1965B','#A65448','#80706A','#527877']

GRAPH_MODES={'family-tree','uml-overview','uml-package','genogram'}
WIREFRAME_MODES={'desktop-wireframe','tablet-wireframe','website-concept'}
SPATIAL_MODES={'home-plan','garden-plan','ceiling-plan','elevation','wardrobe-plan'}
ROUTE_MODES={'direction-map'}
SCIENCE_MODES={'molecular-model','human-anatomy','biology-diagram','astronomy-diagram'}
DOCUMENT_MODES={'invoice','resume','expense-report','quotation','certificate','thank-you-card','postcard','birthday-card','christmas-card','new-year-card'}
INFOGRAPHIC_MODES={f'{x}-infographic' for x in ('architecture','business','education','environment','food','medical','music','technology','news','travel','transport')}
ORGANIZER_MODES={'graphic-organizer','main-idea-organizer','vocabulary-organizer','compare-organizer','sequence-organizer','grid-organizer','writing-organizer','reading-organizer'}
ALL_MODES=GRAPH_MODES|WIREFRAME_MODES|SPATIAL_MODES|ROUTE_MODES|SCIENCE_MODES|DOCUMENT_MODES|INFOGRAPHIC_MODES|ORGANIZER_MODES
FINANCIAL_MODES={'invoice','expense-report','quotation'}


def need(value,message):
    if not value: raise ValueError(message)


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def money(value):
    value=round(float(value),2)
    return f'{value:,.0f}' if value.is_integer() else f'{value:,.2f}'


def financial_summary(data):
    """Calculate the only values used by financial document rendering."""
    items=data.get('line_items',[]); ids(items,'line_items'); subtotal=0
    rows=[]
    for row in items:
        need(row.get('label') and finite(row.get('quantity')) and finite(row.get('unit_price')),'line item invalid')
        amount=round(row['quantity']*row['unit_price'],2)
        subtotal+=amount
        rows.append({**row,'amount':amount})
    tax=data.get('tax_rate',0)
    need(finite(tax) and 0<=tax<=1,'tax rate invalid')
    total=round(subtotal*(1+tax),2)
    need(math.isclose(total,data.get('declared_total'),abs_tol=.01),'declared total mismatch')
    return {
        'items':rows,
        'subtotal':round(subtotal,2),
        'tax_rate':tax,
        'total':total,
        'items_content':'\n'.join(f"{row['label']} ×{row['quantity']:g} · ¥{money(row['amount'])}" for row in rows),
        'total_content':f"小计 ¥{money(subtotal)}\n税率 {tax * 100:g}%；合计 ¥{money(total)}",
    }


def ids(rows,label):
    need(isinstance(rows,list),f'{label} must be list')
    out=[r.get('id') for r in rows]
    need(all(isinstance(x,str) and x.strip() for x in out),f'{label} ids required')
    need(len(out)==len(set(out)),f'{label} ids unique')
    return set(out)


def point(value):
    need(isinstance(value,list) and len(value)==2 and all(finite(x) and 0<=x<=1 for x in value),'normalized point required')


def rect(value):
    need(isinstance(value,list) and len(value)==4 and all(finite(x) for x in value),'normalized rectangle required')
    x,y,w,h=value; need(0<=x<1 and 0<=y<1 and w>0 and h>0 and x+w<=1 and y+h<=1,'rectangle outside canvas')


def base(data):
    mode=data.get('mode'); need(mode in ALL_MODES,'unsupported cross-industry mode')
    need(data.get('title') and data.get('sector') and data.get('use_case'),'title, sector and use_case required')
    need(data.get('data_status') in {'simulated','observed','mixed'},'data_status required')
    need(isinstance(data.get('assumptions'),list),'assumptions required')
    expected=('graph' if mode in GRAPH_MODES else 'wireframe' if mode in WIREFRAME_MODES else 'spatial' if mode in SPATIAL_MODES else 'route' if mode in ROUTE_MODES else 'science' if mode in SCIENCE_MODES else 'publication' if mode in DOCUMENT_MODES|INFOGRAPHIC_MODES else 'organizer')
    need(data.get('template')==expected,f'template must be {expected}')
    return mode,expected


def validate_graph(data):
    nodes=data.get('nodes',[]); edges=data.get('edges',[]); node_ids=ids(nodes,'nodes'); ids(edges,'edges')
    kinds=set()
    for row in nodes:
        need(row.get('label') and row.get('kind'),'node label and kind required'); point(row.get('position')); kinds.add(row['kind'])
    relations=Counter(); graph=defaultdict(list)
    for row in edges:
        need(row.get('source') in node_ids and row.get('target') in node_ids and row['source']!=row['target'],'edge endpoint invalid')
        need(row.get('relation') and row.get('label'),'edge relation and label required'); relations[row['relation']]+=1; graph[row['source']].append(row['target'])
        if row.get('label_position') is not None: point(row['label_position'])
    mode=data['mode']
    if mode=='family-tree': need({'person'}<=kinds and {'parent','partner'}<=set(relations),'family tree relations incomplete')
    elif mode=='genogram': need({'person','health-note'}<=kinds and {'parent','partner','clinical'}<=set(relations),'genogram semantics incomplete')
    elif mode=='uml-overview': need({'structural','behavioral'}<=kinds and len(nodes)>=8,'UML overview must cover structural and behavioral views')
    else: need({'package'}<=kinds and {'dependency','containment'}<=set(relations),'UML package semantics incomplete')
    return {'nodes':len(nodes),'edges':len(edges),'node_kinds':sorted(kinds),'relations':dict(sorted(relations.items())),'reference_check':'passed'}


def validate_wireframe(data):
    screens=data.get('screens',[]); screen_ids=ids(screens,'screens'); regions=0
    for screen in screens:
        need(screen.get('label') and screen.get('viewport'),'screen label and viewport required'); rect(screen.get('rect')); regs=screen.get('regions',[]); ids(regs,f"regions-{screen['id']}")
        for row in regs: need(row.get('role') and row.get('label'),'region role and label required'); rect(row.get('rect')); regions+=1
    interactions=data.get('interactions',[]); ids(interactions,'interactions')
    for row in interactions: need(row.get('source_screen') in screen_ids and row.get('target_screen') in screen_ids and row.get('trigger'),'interaction reference invalid')
    need(data.get('responsive_rule') and regions>=6,'responsive rule and six regions required')
    return {'screens':len(screens),'regions':regions,'interactions':len(interactions),'screen_references':'passed','responsive_rule':data['responsive_rule']}


def validate_spatial(data):
    zones=data.get('zones',[]); zone_ids=ids(zones,'zones')
    for row in zones:
        need(row.get('label') and row.get('kind'),'zone label and kind required'); rect(row.get('rect'))
        if row.get('label_position') is not None: point(row['label_position'])
    measurements=data.get('measurements',[]); ids(measurements,'measurements')
    for row in measurements:
        need(row.get('zone') in zone_ids and finite(row.get('value')) and row['value']>0 and row.get('unit'),'measurement invalid')
    need(data.get('scale_note') and data.get('view'),'scale note and view required')
    if data['mode']=='ceiling-plan': need({'lighting','ceiling'}<=set(r['kind'] for r in zones),'ceiling plan needs lighting and ceiling zones')
    if data['mode']=='elevation': need(data['view'] in {'front','interior-front'},'elevation view invalid')
    return {'zones':len(zones),'measurements':len(measurements),'view':data['view'],'scale_note':data['scale_note'],'bounds_check':'passed'}


def validate_route(data):
    waypoints=data.get('waypoints',[]); waypoint_ids=ids(waypoints,'waypoints')
    for row in waypoints: need(row.get('label') and row.get('kind'),'waypoint label and kind required'); point(row.get('position'))
    routes=data.get('routes',[]); ids(routes,'routes')
    for row in routes:
        path=row.get('waypoint_ids',[]); need(len(path)>=2 and set(path)<=waypoint_ids and row.get('label'),'route references invalid')
    need(any(r['kind']=='destination' for r in waypoints) and data.get('distance_claim') in {'schematic','measured'},'destination and distance claim required')
    return {'waypoints':len(waypoints),'routes':len(routes),'route_references':'passed','distance_claim':data['distance_claim']}


def validate_science(data):
    concepts=data.get('concepts',[]); concept_ids=ids(concepts,'concepts')
    for row in concepts: need(row.get('label') and row.get('kind') and row.get('source'),'concept label, kind and source required'); point(row.get('position'))
    relations=data.get('relations',[]); ids(relations,'relations')
    for row in relations: need(row.get('source') in concept_ids and row.get('target') in concept_ids and row.get('relation'),'science relation invalid')
    need(data.get('claim_scope') and len(concepts)>=4,'claim scope and four concepts required')
    mode=data['mode']; kinds={x['kind'] for x in concepts}
    if mode=='molecular-model': need({'atom','bond'}<=kinds,'molecular model requires atoms and bond concept')
    elif mode=='human-anatomy': need({'organ','system'}<=kinds,'anatomy model requires organs and system')
    elif mode=='biology-diagram': need({'structure','process'}<=kinds,'biology model requires structure and process')
    else: need({'body','orbit'}<=kinds,'astronomy model requires bodies and orbit')
    return {
        'concepts':len(concepts),'relations':len(relations),'concept_kinds':sorted(kinds),
        'source_fields_check':'passed','claim_scope':data['claim_scope'],
        'representation':'concept relationship diagram; not an anatomical or molecular illustration',
    }


def validate_publication(data):
    blocks=data.get('blocks',[]); ids(blocks,'blocks'); roles=set()
    for row in blocks:
        need(row.get('role') and row.get('label'),'block role and label required'); rect(row.get('rect')); roles.add(row['role'])
        need(isinstance(row.get('content',''),str),'content must be text')
    sheet=data.get('sheet',{}); need(finite(sheet.get('width')) and finite(sheet.get('height')) and sheet.get('unit') in {'mm','px'},'sheet invalid')
    need(data.get('audience') and data.get('primary_action'),'audience and action required')
    order=[r['id'] for r in sorted(blocks,key=lambda x:x.get('order',999))]; need(data.get('reading_order')==order,'reading order mismatch')
    result={'blocks':len(blocks),'roles':sorted(roles),'sheet':f"{sheet['width']}×{sheet['height']} {sheet['unit']}",'reading_order_check':'passed','audience_action_check':'passed'}
    mode=data['mode']
    if mode in FINANCIAL_MODES:
        source_by_role={row['role']:row.get('content_source') for row in blocks}
        need(source_by_role.get('items')=='line_items','financial items block must use line_items')
        need(source_by_role.get('total')=='financial_summary','financial total block must use financial_summary')
        summary=financial_summary(data)
        result.update({'line_items':len(summary['items']),'subtotal':summary['subtotal'],'tax_rate':summary['tax_rate'],'total':summary['total'],'arithmetic_check':'passed','rendered_financial_values':'derived from line_items and tax_rate'})
    elif mode=='resume': need({'identity','summary','experience','skills','education'}<=roles,'resume sections incomplete')
    elif mode=='certificate': need({'recipient','award','issuer','date'}<=roles,'certificate fields incomplete')
    elif mode in {'thank-you-card','postcard','birthday-card','christmas-card','new-year-card'}: need({'recipient','message','sender'}<=roles,'card message fields incomplete')
    elif mode in INFOGRAPHIC_MODES:
        need({'headline','context','evidence','action'}<=roles,'infographic roles incomplete'); need(data.get('source_note'),'infographic source note required'); result['source_check']='passed'
    return result


def validate_organizer(data):
    slots=data.get('slots',[]); slot_ids=ids(slots,'slots')
    for row in slots: need(row.get('label') and row.get('prompt'),'slot label and prompt required'); rect(row.get('rect'))
    links=data.get('links',[]); ids(links,'links')
    for row in links: need(row.get('source') in slot_ids and row.get('target') in slot_ids and row.get('relation'),'organizer link invalid')
    need(len(slots)>=3 and data.get('learning_goal') and data.get('completion_rule'),'organizer goal and completion rule required')
    if data['mode']=='graphic-organizer': need(len(data.get('recommended_variants',[]))>=4,'graphic organizer overview requires four variants')
    return {'slots':len(slots),'links':len(links),'learning_goal':data['learning_goal'],'reference_check':'passed','completion_rule':data['completion_rule']}


VALIDATORS={'graph':validate_graph,'wireframe':validate_wireframe,'spatial':validate_spatial,'route':validate_route,'science':validate_science,'publication':validate_publication,'organizer':validate_organizer}


def analyze(data):
    mode,template=base(data); calc=VALIDATORS[template](data)
    metrics=data.get('metrics',[]); ids(metrics,'metrics')
    for row in metrics: need(row.get('label') and row.get('evidence') and isinstance(row.get('value'),(str,int,float)),'metric invalid')
    if mode in FINANCIAL_MODES:
        sources={row['id']:row.get('value_source') for row in metrics}
        need(sources.get('total')=='financial_total','financial total metric must use financial_total')
        for row in metrics:
            if row.get('value_source')=='financial_total':
                need(row['id']=='total','financial_total is reserved for the total metric')
            if row.get('value_source')=='line_items_count':
                need(row['id'] in {'items','deliverables'},'line_items_count metric id is invalid')
        calc['metric_sources']=sources
    return {'mode':mode,'template':template,'sector':data['sector'],'data_status':data['data_status'],'assumptions':data['assumptions'],'metric_count':len(metrics),**calc}


def font_name():
    from matplotlib import font_manager
    path=Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists(): font_manager.fontManager.addfont(path); return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def wrap(value,width=18):
    """Wrap CJK and Latin text by display width instead of whitespace alone."""
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


def figure(data):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family':font_name(),'font.size':10,'text.color':INK,'axes.unicode_minus':False,'svg.fonttype':'none','svg.hashsalt':'diagram-studio-cross-industry-v1'})
    publication=data['template']=='publication'
    if publication:
        sheet=data['sheet']
        if sheet['unit']=='mm': size=(sheet['width']/25.4,sheet['height']/25.4)
        else: size=(sheet['width']/150,sheet['height']/150)
    else: size=(12.8,7.6)
    fig=plt.figure(figsize=size,dpi=150,facecolor=PAPER if publication else BG)
    if publication:
        # A document's declared sheet is the actual drawing surface.  The old
        # layout put a second, smaller sheet inside an A4 image, leaving titles
        # and totals outside the document that a user would print or hand over.
        ax=fig.add_axes((.07,.075,.86,.79))
        scale=min(1.05,max(.48,min(min(size)/8.27,max(size)/11.69)))
        fig.text(.07,.962,data['title'],fontsize=max(10,18*scale),color=INK,weight='medium',va='top')
        fig.text(.07,.905,data.get('subtitle',''),fontsize=max(5.6,8.2*scale),color=MUTED,va='top')
        fig.text(.93,.962,data['sector'],fontsize=max(5.2,7*scale),color=MUTED,ha='right',va='top')
    else:
        ax=fig.add_axes((.055,.11,.89,.73)); scale=1.0
        fig.text(.055,.965,data['title'],fontsize=21,color=INK,weight='medium',va='top')
        fig.text(.055,.895,data.get('subtitle',''),fontsize=9.5,color=MUTED,va='top')
        fig.text(.945,.96,data['sector'],fontsize=8,color=MUTED,ha='right',va='top')
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off'); return fig,ax


def draw_graph(ax,data):
    from matplotlib.patches import FancyBboxPatch
    by={x['id']:x for x in data['nodes']}
    for i,row in enumerate(data['edges']):
        a=by[row['source']]['position']; b=by[row['target']]['position']; c=COLORS[i%len(COLORS)]
        x,y=row.get('label_position',((a[0]+b[0])/2,(a[1]+b[1])/2+.018))
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='-|>',color=c,lw=1.2,shrinkA=23,shrinkB=23)); ax.text(x,y,row['label'],fontsize=5.5,color=c,ha='center',bbox=dict(fc=BG,ec='none',pad=.1))
    for i,row in enumerate(data['nodes']):
        x,y=row['position']; c=COLORS[i%len(COLORS)]; ax.add_patch(FancyBboxPatch((x-.075,y-.045),.15,.09,boxstyle='round,pad=.008,rounding_size=.012',fc=PAPER,ec=c,lw=1.35))
        mark_container(ax.text(x,y,wrap(row['label'],18),fontsize=6.3,ha='center',va='center'),ax,(x-.075,y-.045,.15,.09),f"node:{row['id']}")


def draw_wireframe(ax,data):
    from matplotlib.patches import FancyBboxPatch,Rectangle
    for si,screen in enumerate(data['screens']):
        x,y,w,h=screen['rect']; c=COLORS[si%len(COLORS)]; ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.006,rounding_size=.016',fc=PAPER,ec=c,lw=1.4)); ax.text(x+w/2,y+h+.018,screen['label'],fontsize=7.2,color=c,ha='center')
        for region in screen['regions']:
            rx,ry,rw,rh=region['rect']; ax.add_patch(Rectangle((x+rx*w,y+ry*h),rw*w,rh*h,fc=c,ec=c,alpha=.08,lw=.8)); ax.text(x+(rx+rw/2)*w,y+(ry+rh/2)*h,wrap(region['label'],15),fontsize=5.3,ha='center',va='center')


def draw_spatial(ax,data):
    from matplotlib.patches import Rectangle
    for i,row in enumerate(data['zones']):
        x,y,w,h=row['rect']; c=COLORS[i%len(COLORS)]; label_x,label_y=row.get('label_position',(x+w/2,y+h/2)); ax.add_patch(Rectangle((x,y),w,h,fc=c,ec=c,alpha=.10,lw=1.25)); ax.text(label_x,label_y,wrap(row['label'],16),fontsize=6.2,ha='center',va='center')
    for row in data['measurements']:
        ax.text(.02,.97-.035*data['measurements'].index(row),f"{row['label']} {row['value']} {row['unit']}",fontsize=5.7,color=MUTED,va='top')


def draw_route(ax,data):
    from matplotlib.patches import Circle
    by={x['id']:x for x in data['waypoints']}
    for i,route in enumerate(data['routes']):
        pts=[by[x]['position'] for x in route['waypoint_ids']]; ax.plot([x[0] for x in pts],[x[1] for x in pts],color=COLORS[i],lw=4,solid_capstyle='round'); ax.text(pts[-1][0],pts[-1][1]+.05,route['label'],fontsize=7,color=COLORS[i],ha='center')
    for i,row in enumerate(data['waypoints']):
        x,y=row['position']; ax.add_patch(Circle((x,y),.018,fc=PAPER,ec=COLORS[i%len(COLORS)],lw=1.4)); ax.text(x,y-.035,wrap(row['label'],12),fontsize=5.8,ha='center',va='top')


def draw_science(ax,data):
    from matplotlib.patches import Circle,FancyBboxPatch
    by={x['id']:x for x in data['concepts']}
    for i,row in enumerate(data['relations']):
        a=by[row['source']]['position']; b=by[row['target']]['position']; ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='-|>',color=COLORS[i%len(COLORS)],lw=1.3,shrinkA=20,shrinkB=20))
    for i,row in enumerate(data['concepts']):
        x,y=row['position']; c=COLORS[i%len(COLORS)]
        if row['kind'] in {'atom','organ','body'}: ax.add_patch(Circle((x,y),.045,fc=c,ec=c,alpha=.16,lw=1.2))
        else: ax.add_patch(FancyBboxPatch((x-.065,y-.038),.13,.076,boxstyle='round,pad=.006',fc=PAPER,ec=c,lw=1.2))
        ax.text(x,y,wrap(row['label'],16),fontsize=5.8,ha='center',va='center')


def draw_publication(ax,data,calc=None):
    from matplotlib.patches import Rectangle
    sh=data['sheet']
    figure_width,figure_height=ax.figure.get_size_inches()
    scale=min(1.05,max(.48,min(min(figure_width,figure_height)/8.27,max(figure_width,figure_height)/11.69)))
    label_size=max(5.6,8.3*scale); content_size=max(4.8,6.8*scale)
    summary=financial_summary(data) if data['mode'] in FINANCIAL_MODES else None
    for i,row in enumerate(data['blocks']):
        x,y,bw,bh=row['rect']; c=COLORS[i%len(COLORS)]
        ax.add_patch(Rectangle((x,y),bw,bh,fc=c,ec=c,alpha=.10,lw=.8))
        mark_container(ax.text(x+.012*bw,y+bh-.014*bh,wrap(row['label'],22),fontsize=label_size,color=c,weight='medium',va='top'),ax,(x,y,bw,bh),f"block:{row['id']}:label")
        content=row.get('content','')
        if summary and row['role']=='items': content=summary['items_content']
        if summary and row['role']=='total': content=summary['total_content']
        content_width=max(16,int(72*bw))
        # Documents read from each block's heading downward.  Bottom-aligning
        # short text made normal quotations look like empty form fields with
        # stray values at the lower edge.
        content_top=y+bh-max(.05,.20*bh)
        mark_container(ax.text(x+.012*bw,content_top,wrap(content,content_width),fontsize=content_size,color=INK,va='top'),ax,(x,y,bw,bh),f"block:{row['id']}:content")


def metric_value(row, summary):
    if summary and row.get('value_source')=='financial_total': return summary['total']
    if summary and row.get('value_source')=='line_items_count': return len(summary['items'])
    return row['value']


def draw_organizer(ax,data):
    from matplotlib.patches import FancyBboxPatch
    by={x['id']:x for x in data['slots']}
    for i,row in enumerate(data['links']):
        a=by[row['source']]['rect']; b=by[row['target']]['rect']; pa=(a[0]+a[2]/2,a[1]+a[3]/2); pb=(b[0]+b[2]/2,b[1]+b[3]/2); ax.annotate('',xy=pb,xytext=pa,arrowprops=dict(arrowstyle='-|>',color=COLORS[i%len(COLORS)],lw=1.1,shrinkA=28,shrinkB=28))
    for i,row in enumerate(data['slots']):
        x,y,w,h=row['rect']; c=COLORS[i%len(COLORS)]; ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.006,rounding_size=.012',fc=PAPER,ec=c,lw=1.2)); ax.text(x+.012,y+h-.018,row['label'],fontsize=6.8,color=c,weight='medium',va='top'); ax.text(x+.012,y+.018,wrap(row['prompt'],28),fontsize=5.4,color=INK,va='bottom')


DRAW={'graph':draw_graph,'wireframe':draw_wireframe,'spatial':draw_spatial,'route':draw_route,'science':draw_science,'publication':draw_publication,'organizer':draw_organizer}


def render(data,out,name=None):
    calc=analyze(data); out=Path(out); out.mkdir(parents=True,exist_ok=True); name=name or data['mode']; fig,ax=figure(data)
    summary=financial_summary(data) if data['mode'] in FINANCIAL_MODES else None
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        if data['template']=='publication': draw_publication(ax,data,calc)
        else: DRAW[data['template']](ax,data)
        if data['template']!='publication':
            page_height=fig.get_figheight()*fig.dpi
            compact=page_height<600
            metric_font=8.0 if compact else 10.0; label_font=5.3 if compact else 6.4
            metric_y=max(.06,32/page_height); label_y=max(.02,12/page_height)
            x=.055
            for row in data.get('metrics',[])[:4]:
                value=metric_value(row,summary)
                fig.text(x,metric_y,str(value)+((' '+row.get('unit','')) if row.get('unit') else ''),fontsize=metric_font,color=INK,weight='medium',va='top')
                fig.text(x,label_y,row['label'],fontsize=label_font,color=MUTED,va='top'); x+=.20
        fig.canvas.draw()
        fig.savefig(out/f'{name}.svg',format='svg',facecolor=BG,metadata={'Date':None})
        fig.savefig(out/f'{name}.png',dpi=150,facecolor=BG)
        visual=inspect_figure(fig,captured)
    import matplotlib.pyplot as plt; plt.close(fig)
    (out/f'{name}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n'); (out/f'{name}.calculation.json').write_text(json.dumps(calc,ensure_ascii=False,indent=2)+'\n')
    qa=quality_payload('passed',visual,'simulated example; replace names, measurements and claims for real delivery')
    (out/f'{name}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n'); return calc


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('--out',required=True); p.add_argument('--name'); a=p.parse_args(); data=json.loads(Path(a.input).read_text()); print(json.dumps(render(data,a.out,a.name or Path(a.input).stem),ensure_ascii=False))


if __name__=='__main__': main()
