"""Measured, editable layouts for common comparison, trend and delivery charts.

Selected by layout.profile=refined. Geometry is checked separately from appearance.
"""
from __future__ import annotations

import datetime as dt
import math
from adaptive_layout import METRICS


def text(s,x,y,w,value,size=18,tone='ink',align='left',bold=False,content=True,id=None):
    lines=[(v,size,bold,tone) for v in METRICS.wrap(str(value),w,size)]
    height=math.ceil(len(lines)*size*1.35)+4
    s.text(x,y,w,height,str(value),size,tone,align=align,_lines=lines,
           font_family=METRICS.family,content_text=content,**({'id':id} if id else {}))
    return height


def english(d):
    from adaptive_delivery import language
    return language(d)=='en'


def top(s):
    return 92+len(METRICS.wrap(s.spec['title'],s.w-128,36))*49+len(METRICS.wrap(s.spec.get('subtitle',''),s.w-128,18))*25+44


def finish(s):
    bottom=max([n['y']+n['h'] for n in s.nodes]+[p[1] for e in s.edges for p in e['points']]+[top(s)])
    footer=s.spec.get('footer','Illustrative data' if english(s.spec) else '模拟数据 · 用于展示图形表达')
    footer_h=len(METRICS.wrap(footer,s.w-128,15))*21+4
    s.h=max(s.h,bottom+footer_h+64) if 'height' in s.spec else math.ceil(max(560,bottom+footer_h+64)/8)*8
    text(s,64,34,s.w-128,s.spec.get('eyebrow','DIAGRAM STUDIO / REFINED'),14,'accent',content=False)
    h=text(s,64,78,s.w-128,s.spec['title'],36,bold=True,content=False)
    text(s,64,86+h,s.w-128,s.spec.get('subtitle',''),18,'muted',content=False)
    s.edge(points=[(64,s.h-footer_h-32),(s.w-64,s.h-footer_h-32)],arrow=False,tone='line',width=1)
    text(s,64,s.h-footer_h-20,s.w-128,footer,15,'muted',content=False)
    s.meta['refined_layout']['font_measurement']=METRICS.mode
    return s


def numeric_range(values,include_zero=True):
    low=min(values);high=max(values)
    if include_zero:low=min(0,low);high=max(0,high)
    if low==high:return (0,1,0.25) if low==0 else (low-1,high+1,.5)
    raw=(high-low)/4;power=10**math.floor(math.log10(raw))
    step=next(v*power for v in (1,2,2.5,5,10) if v*power>=raw)
    return math.floor(low/step)*step,math.ceil(high/step)*step,step


def ticks(low,high,step):
    return [low+i*step for i in range(round((high-low)/step)+1)]


def comparison(s,d):
    from render import need,finite
    data=d['data'];need(data,'empty comparison data')
    values=[v['value'] for v in data];need(all(finite(v) for v in values),'comparison values must be finite')
    variant=d.get('comparison_style','bar');need(variant in ('bar','dot'),'comparison_style must be bar or dot')
    unit=d.get('unit','');low,high,step=numeric_range(values)
    left=64;labelw=min(340,max(200,s.w*.20));x0=left+labelw+40;end=s.w-188
    need(end-x0>=280,'comparison needs a wider canvas')
    position=lambda v:x0+(v-low)/(high-low)*(end-x0)
    y=top(s);rows=[]
    for i,item in enumerate(data):
        labelh=len(METRICS.wrap(item['label'],labelw,21))*29+4
        rowh=max(68,labelh+24);rows.append((item,y,rowh));y+=rowh
    bottom=y+16
    for value in ticks(low,high,step):
        x=position(value)
        s.edge(points=[(x,top(s)-12),(x,bottom)],tone='muted' if value==0 else 'line',width=1.3 if value==0 else .7,arrow=False)
        text(s,x-46,bottom+12,92,f'{value:g}',16,'muted','center')
    marks=[]
    for i,(item,y,rowh) in enumerate(rows):
        center=y+rowh/2
        text(s,left,y+(rowh-(len(METRICS.wrap(item['label'],labelw,21))*29+4))/2,labelw,item['label'],21)
        value=item['value'];x=position(value);zero=position(0)
        tone='accent' if i==d.get('highlight',0) else 'teal'
        if variant=='dot':
            if value:s.edge(points=[(zero,center),(x,center)],arrow=False,tone=tone,width=2)
            s.add(x-7,center-7,14,14,id=f'value-{i}',kind='ellipse',fill=tone,stroke='bg',stroke_width=2,check=False)
        elif value:
            s.add(min(x,zero),center-10,abs(x-zero),20,id=f'value-{i}',kind='rect',fill=tone,stroke='none',radius=0,check=False)
        else:s.add(zero-3,center-3,6,6,id=f'value-{i}',kind='ellipse',fill=tone,stroke='none',check=False)
        text(s,end+28,center-17,132,f'{value:g}',23,tone,'right',bold=True)
        marks.append({'index':i,'value':value,'zero_x':zero,'value_x':x})
    text(s,x0,bottom+54,s.w-x0-64,('Unit: ' if english(d) else '单位：')+(unit or ('not specified' if english(d) else '未指定')),16,'muted')
    s.meta.update(data_values=values,chart_encoding={'mode':'bar','variant':variant,'domain':[low,high],'zero_included':True,'marks':marks,'unit':unit})


def trend(s,d):
    from render import need,finite
    data=d['data'];need(len(data)>=2,'trend needs at least two observations')
    values=[v.get('value') for v in data];observed=[v for v in values if v is not None]
    need(observed and all(finite(v) for v in observed),'trend values must be finite numbers or null')
    dated=any('date' in v for v in data)
    need(not dated or all('date' in v for v in data),'every dated observation needs a date')
    coords=[dt.date.fromisoformat(v['date']).toordinal() for v in data] if dated else list(range(len(data)))
    need(all(a<b for a,b in zip(coords,coords[1:])),'trend dates must be unique and strictly increasing')
    low,high,step=numeric_range(observed);x0=142;right=s.w-142;y0=top(s)+54;ph=330
    xp=lambda v:x0+(v-coords[0])/(coords[-1]-coords[0])*(right-x0)
    yp=lambda v:y0+ph-(v-low)/(high-low)*ph
    for v in ticks(low,high,step):
        y=yp(v);s.edge(points=[(x0,y),(right,y)],tone='line',arrow=False,width=.8)
        text(s,64,y-14,58,f'{v:g}',16,'muted','right')
    unit=d.get('unit','');text(s,x0,y0-45,right-x0,('Unit: ' if english(d) else '单位：')+(unit or '—'),17,'muted')
    segments=[];current=[];positions=[]
    for i,(item,value,xval) in enumerate(zip(data,values,coords)):
        x=xp(xval);positions.append({'index':i,'x':x,'value':value,'y':None if value is None else yp(value)})
        if value is None:
            if current:segments.append(current);current=[]
            continue
        y=yp(value);current.append([x,y])
        s.add(x-5,y-5,10,10,id=f'point-{i}',kind='ellipse',fill='accent',stroke='panel',stroke_width=2,check=False)
    if current:segments.append(current)
    for segment in segments:
        if len(segment)>1:s.edge(points=segment,arrow=False,tone='accent',width=2.4)
    # Sparse axis labels keep close dates readable; the ledger retains every value.
    last=-math.inf
    for i,xval in enumerate(coords):
        x=xp(xval)
        if i not in (0,len(data)-1) and (x-last<130 or right-x<130):continue
        label=data[i]['date'][5:] if dated else data[i]['label']
        text(s,x-60,y0+ph+18,120,label,16,'muted','center');last=x
    note=('Calendar spacing · gaps remain missing' if dated else 'Category spacing · gaps remain missing') if english(d) else ('按真实日期间隔 · 缺测处断线' if dated else '按类别等间距 · 缺测处断线')
    text(s,64,y0+ph+82,s.w-128,note,17,'muted')
    ledger_y=y0+ph+125;cols=max(1,min(4,int((s.w-128)/300)));cw=(s.w-128)/cols
    for start in range(0,len(data),cols):
        heights=[]
        for j,item in enumerate(data[start:start+cols]):
            value=item.get('value');label=item.get('date',item.get('label',''))
            if dated and item.get('label'):label+=' · '+item['label']
            x=64+j*cw
            h=text(s,x,ledger_y,cw-30,label,16,'muted')
            v=('Missing' if english(d) else '缺测') if value is None else f'{value:g} {unit}'.strip()
            h+=text(s,x,ledger_y+h+7,cw-30,v,23,'ink',bold=True)+7;heights.append(h)
        ledger_y+=max(heights)+26
    s.meta.update(data_values=values,chart_encoding={'mode':'line','domain':[low,high],'x_kind':'date' if dated else 'category','x_coordinates':coords,'positions':positions,'segments':segments,'missing':'break','unit':unit})


def gantt(s,d):
    from render import gantt_parse,gantt_bar,need
    need(d.get('gantt_variant','delivery')=='delivery','refined gantt currently supports delivery; use the original backend for executive/print')
    parsed,ids,start,end=gantt_parse(d);days=(end-start).days+1
    x0=max(500,s.w*.34);right=s.w-96;usable=right-x0
    need(usable>=320,'refined gantt needs a wider canvas')
    unit=usable/days;y0=top(s)+88;y=y0;bars={};rowmeta=[]
    labelw=x0-190
    for i,(task,a,b) in enumerate(parsed):
        labelh=len(METRICS.wrap(task['label'],labelw,20))*27+4
        owner=task.get('owner','');dates=a.strftime('%m/%d')+' – '+b.strftime('%m/%d')
        metadata=(owner+' · ' if owner else '')+dates
        metah=len(METRICS.wrap(metadata,labelw,16))*22+4
        rowh=max(88,labelh+metah+30);center=y+rowh/2
        text(s,64,y+10,labelw,task['label'],20,bold=True)
        text(s,64,y+14+labelh,labelw,metadata,16,'muted')
        text(s,x0-112,center-13,84,('Gate' if english(d) else '里程碑') if task.get('milestone') else f"{task.get('progress',0):g}%",16,'muted','right')
        gantt_bar(s,task,a,b,start,x0,unit,center,bars,bar_height=18)
        s.edge(points=[(64,y+rowh),(right,y+rowh)],arrow=False,tone='line',width=.65)
        rowmeta.append({'id':task['id'],'top':y,'height':rowh,'center':center,'start':a.isoformat(),'end':b.isoformat(),'bar':list(bars[task['id']])})
        y+=rowh
    tick_count=max(2,min(8,int(usable/112)))
    offsets=sorted(set(round(i*(days-1)/(tick_count-1)) for i in range(tick_count)))
    for day in offsets:
        x=x0+day*unit
        s.edge(points=[(x,y0-16),(x,y)],arrow=False,tone='line',width=.7)
        text(s,x-38,y0-48,76,(start+dt.timedelta(days=day)).strftime('%m/%d'),16,'muted','center')
    text(s,64,top(s),labelw,'Task / owner / dates' if english(d) else '任务 / 责任人 / 起止日期',17,'muted')
    text(s,x0,top(s),usable,f'{start.isoformat()} — {end.isoformat()}',19,'ink',bold=True)
    dependencies=[]
    from adaptive_layout import route
    obstacles=[s.get(task['id']) for task,_,_ in parsed]
    for task,a,b in parsed:
        for dep in task.get('depends',[]):
            need(dep in ids,'missing dependency: '+dep)
            need(a>parsed[ids[dep]][2],f'finish-to-start dependency conflict: {dep} -> {task["id"]}')
            points,sp,tp=route(s.get(dep),s.get(task['id']),obstacles,'right',len(dependencies))
            s.edge(dep,task['id'],points=points,source_port=sp,target_port=tp,tone='muted',width=1.25)
            dependencies.append([dep,task['id']])
    note='Inclusive calendar days · fill = progress · diamond = milestone · arrows = finish-to-start' if english(d) else '自然日，包含结束日 · 实色为完成比例 · 菱形为里程碑 · 箭头为完成后开始'
    text(s,64,y+28,s.w-128,note,16,'muted')
    s.meta.update(gantt_variant='delivery',calendar='natural-days-inclusive',start=start.isoformat(),end=end.isoformat(),critical_path='not-calculated',gantt_encoding={'rows':rowmeta,'dependencies':dependencies,'day_width':unit,'origin_x':x0})


def build(s,d):
    s.meta['refined_layout']={'version':40,'profile':'refined','manual_visual_review':'not-run'}
    if d['type']=='gantt':gantt(s,d)
    elif d['type']=='chart' and d.get('mode','bar')=='bar':comparison(s,d)
    elif d['type']=='chart' and d.get('mode')=='line':trend(s,d)
    else:raise ValueError('refined profile supports adaptive graph/architecture, delivery gantt, bar and line charts')
