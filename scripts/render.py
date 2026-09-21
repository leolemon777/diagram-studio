#!/usr/bin/env python3
"""Original, offline diagram renderer. Python standard library only."""
import argparse, copy, datetime as dt, hashlib, html, json, math, os, re, sys, tempfile, unicodedata
from pathlib import Path
import xml.etree.ElementTree as ET
from editorial_style import vector_themes
from delivery_contract import content_integrity, make_receipt, snapshot, verify_receipt

THEMES = {
 'light':dict(bg='#F1EFEB',panel='#FEFDF9',ink='#30302D',muted='#6D6A63',line='#D8D3C8',accent='#AC6046',teal='#67685E',amber='#8C7964',red='#554C46',tint='#F0E4DA',tint2='#ECECE5'),
 'dark':dict(bg='#252522',panel='#302F2B',ink='#ECE8DE',muted='#B6B1A7',line='#57534B',accent='#D39577',teal='#B6B6A4',amber='#B5A088',red='#CCC2B7',tint='#44372F',tint2='#3B3D34'),
 'mono':dict(bg='#FFFFFF',panel='#FFFFFF',ink='#242424',muted='#626262',line='#CECECE',accent='#353535',teal='#707070',amber='#919191',red='#515151',tint='#EEEEEE',tint2='#F5F5F5')
}
THEMES.update(vector_themes())
FONT='PingFang SC, Microsoft YaHei, Noto Sans CJK SC, Arial, sans-serif'
def need(condition,message):
    if not condition: raise ValueError(message)
def measure(s,size):
    return sum(1.0 if unicodedata.east_asian_width(c) in 'WF' else (.3 if c==' ' else .57) for c in str(s))*size
def wrap(s,width,size):
    lines=[]
    for para in str(s).split('\n'):
        line=''
        for c in para:
            if line and measure(line+c,size)>width: lines.append(line.rstrip());line=''
            line+=c
        lines.append(line)
    return lines

def wrap_words(s,width,size):
    """Wrap mixed CJK/Latin copy without splitting ordinary Latin words."""
    lines=[]
    for para in str(s).split('\n'):
        units=[];i=0
        while i<len(para):
            c=para[i]
            if c.isspace():
                j=i+1
                while j<len(para) and para[j].isspace():j+=1
                units.append(('space',para[i:j]));i=j;continue
            if unicodedata.east_asian_width(c) in 'WF':
                units.append(('word',c));i+=1;continue
            j=i+1
            while j<len(para) and not para[j].isspace() and unicodedata.east_asian_width(para[j]) not in 'WF':j+=1
            units.append(('word',para[i:j]));i=j
        line='';pending_space=False
        for kind,unit in units:
            if kind=='space':pending_space=bool(line);continue
            candidate=line+(' ' if pending_space and line else '')+unit
            if line and measure(candidate,size)>width:
                lines.append(line.rstrip());line='';pending_space=False;candidate=unit
            if measure(candidate,size)<=width:
                line=candidate;pending_space=False;continue
            # A single token can be wider than its cell; split only then.
            for char in unit:
                if line and measure(line+char,size)>width:
                    lines.append(line.rstrip());line=''
                line+=char
            pending_space=False
        lines.append(line.rstrip())
    return lines

def color(t,value): return t.get(value,value)
def finite(v): return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

class Scene:
    def __init__(self, spec,theme):
        self.spec=spec;self.theme=theme;self.w=spec.get('width',1600);self.h=spec.get('height',900)
        need(theme in THEMES,'unknown theme')
        overrides=spec.get('style',{})
        need(isinstance(overrides,dict),'style must be a color-token object')
        need(all(k in THEMES[theme] and isinstance(v,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',v) for k,v in overrides.items()),'style supports known tokens with #RRGGBB colors')
        self.palette={**THEMES[theme],**overrides}
        self.nodes=[];self.edges=[];self.count=0;self.ids=set();self.meta={}
    def add(self,x,y,w,h,label='',detail='',kind='rect',tone='accent',id=None,**kw):
        self.count+=1;id=id or f'_v{self.count}'
        need(isinstance(id,str) and id not in ('0','1') and not id.startswith('_edge_'),'invalid or reserved node id')
        need(kind in ('rect','panel','text','diamond','pill','cylinder','ellipse','polygon'),'unsupported shape: '+kind)
        need(tone in THEMES[self.theme],'unknown tone: '+tone)
        need(id not in self.ids,f'duplicate node id: {id}');self.ids.add(id)
        n=dict(id=id,x=x,y=y,w=w,h=h,label=str(label),detail=str(detail),kind=kind,tone=tone,**kw)
        self.nodes.append(n);return id
    def text(self,x,y,w,h,label,size=18,tone='ink',align='left',**kw):
        return self.add(x,y,w,h,label,kind='text',tone=tone,fs=size,align=align,check=False,**kw)
    def get(self,id):
        for n in self.nodes:
            if n['id']==id:return n
        raise ValueError(f'unknown node id: {id}')
    def edge(self,a=None,b=None,label='',points=None,source_port=None,target_port=None,**kw):
        if a:self.get(a)
        if b:self.get(b)
        if points is None:
            need(a and b,'edge needs endpoints or points')
            na,nb=self.get(a),self.get(b)
            ax,ay=na['x']+na['w']/2,na['y']+na['h']/2
            bx,by=nb['x']+nb['w']/2,nb['y']+nb['h']/2
            if a==b:
                source_port,target_port='right','bottom'
                p=port(na,source_port);q=port(nb,target_port)
                points=[p,(p[0]+52,p[1]),(p[0]+52,q[1]+40),(q[0],q[1]+40),q]
            else:
                if not source_port: source_port=('right' if bx>ax else 'left') if abs(bx-ax)>abs(by-ay)*1.35 else ('bottom' if by>ay else 'top')
                if not target_port: target_port={'right':'left','left':'right','top':'bottom','bottom':'top'}[source_port]
                p,q=port(na,source_port),port(nb,target_port)
                if source_port in ('left','right'):
                    mx=(p[0]+q[0])/2;points=[p,(mx,p[1]),(mx,q[1]),q]
                else:
                    my=(p[1]+q[1])/2;points=[p,(p[0],my),(q[0],my),q]
        clean=[]
        for p in points:
            p=list(p)
            if not clean or p!=clean[-1]:clean.append(p)
        self.edges.append(dict(source=a,target=b,label=label,points=clean,source_port=source_port,target_port=target_port,**kw))
    def finish(self):
        if self.meta.get('adaptive_layout'):
            from adaptive_layout import finish_adaptive
            return finish_adaptive(self)
        if self.meta.get('refined_layout'):
            from refined_layout import finish
            return finish(self)
        content_bottom=max([n['y']+n['h'] for n in self.nodes]+[180])
        self.h=max(self.h,content_bottom+100)
        self.text(64,34,self.w-128,22,self.spec.get('eyebrow','DIAGRAM STUDIO  /  专业图示'),14,'accent')
        self.text(64,69,self.w-128,56,self.spec.get('title','未命名图示'),36)
        self.text(64,130,self.w-128,38,self.spec.get('subtitle',''),17,'muted')
        self.add(64,self.h-63,self.w-128,1,kind='rect',fill='line',stroke='none',check=False)
        footer=self.spec.get('footer','示例方案 · 非实际部署 / 业务事实')
        self.text(64,self.h-50,self.w-128,36,footer,14,'muted')
        return self

def port(n,p):
    x,y,w,h=n['x'],n['y'],n['w'],n['h']
    return {'left':(x,y+h/2),'right':(x+w,y+h/2),'top':(x+w/2,y),'bottom':(x+w/2,y+h)}[p]

def architecture(s,d):
    layers=d['layers'];need(1<=len(layers)<=10,'layers: expected 1–10')
    rail=d.get('crosscut',[]);mainw=s.w-128-(252 if rail else 0);y=190
    layer_ids=[]
    for i,layer in enumerate(layers):
        items=layer['items'];need(items,'empty layer');need(len(items)<=6,'more than six modules: split the layer')
        lh=max(118,layer.get('height',126));tone=layer.get('tone','accent' if i%2==0 else 'teal')
        s.add(64,y,mainw,lh,kind='panel',check=False)
        s.add(64,y,6,lh,kind='rect',fill=tone,stroke='none',check=False)
        s.text(90,y+20,124,36,layer['label'],23,tone)
        s.text(90,y+57,124,45,layer.get('description',''),15,'muted')
        x0=240;gap=18;w=(mainw-200-(len(items)-1)*gap)/len(items)
        ids=[]
        for j,item in enumerate(items):
            if isinstance(item,str):item={'label':item}
            nid=s.add(x0+j*(w+gap),y+21,w,lh-42,item['label'],item.get('detail',''),tone=tone,id=item.get('id'),check=True)
            ids.append(nid)
        layer_ids.append(ids)
        if i<len(layers)-1 and layer.get('flow'):
            direction=layer.get('flow_direction','down');cx=64+mainw/2
            pts=[(cx,y+lh+4),(cx,y+lh+42)]
            if direction=='up':pts.reverse()
            s.edge(label=layer['flow'],points=pts,label_at=[cx+20,y+lh+24],label_align='left',tone=tone)
        y+=lh+48
    if rail:
        x=64+mainw+28;h=y-238;s.add(x,190,224,h,kind='panel',check=False)
        s.text(x+24,210,176,36,d.get('crosscut_title','横向支撑'),22,'teal')
        for j,item in enumerate(rail):
            if isinstance(item,str):item={'label':item}
            s.add(x+20,270+j*105,184,82,item['label'],item.get('detail',''),tone='teal',check=True)
        need(270+(len(rail)-1)*105+82<=190+h,'crosscut items exceed rail; increase layer height or shorten list')
    for e in d.get('edges',[]):s.edge(e['from'],e['to'],e.get('label',''),points=e.get('points'),tone=e.get('tone','accent'),dashed=e.get('dashed',False))
    s.meta['layer_nodes']=layer_ids

def graph(s,d):
    for g in d.get('groups',[]):
        s.add(g['x'],g['y'],g['w'],g['h'],g.get('label',''),kind='panel',id=g.get('id'),check=False)
    for n in d['nodes']:
        x=n.get('x',80+n.get('col',0)*310);y=n.get('y',215+n.get('row',0)*155)
        s.add(x,y,n.get('w',235),n.get('h',84),n['label'],n.get('detail',''),kind=n.get('kind','rect'),tone=n.get('tone','accent'),id=n['id'],check=True)
    for e in d.get('edges',[]):
        s.edge(e['from'],e['to'],e.get('label',''),points=e.get('points'),source_port=e.get('source_port'),target_port=e.get('target_port'),tone=e.get('tone','accent'),dashed=e.get('dashed',False),arrow=e.get('arrow',True),label_at=e.get('label_at'))

def tree(s,d):
    root=d['root'];direction=d.get('direction','right');need(direction in ('right','down'),'tree direction must be right/down')
    seen=set();depths={};sizes={};order=[]
    def visit(n,depth,trail):
        need(isinstance(n,dict) and 'id' in n,'each tree node needs id')
        need(n['id'] not in seen,'tree cycle or duplicate id: '+n['id']);seen.add(n['id']);depths[n['id']]=depth
        children=n.get('children',[]);sizes[n['id']]=sum(visit(c,depth+1,trail+[n['id']]) for c in children) if children else 1
        order.append(n);return sizes[n['id']]
    leaves=visit(root,0,[]);maxdepth=max(depths.values());need(maxdepth<=6,'tree deeper than six levels: split views')
    if direction=='right':
        s.w=max(s.w,128+(maxdepth+1)*300);s.h=max(s.h,290+leaves*104)
        nw,nh=230,72
    else:s.w=max(s.w,128+leaves*250);s.h=max(s.h,340+(maxdepth+1)*160);nw,nh=212,78
    def place(n,start,tone='accent'):
        span=sizes[n['id']];center=start+span/2;dep=depths[n['id']]
        if direction=='right':x,y=64+dep*300,200+center*104-nh/2
        else:x,y=64+center*250-nw/2,205+dep*160
        s.add(x,y,nw,nh,n['label'],n.get('detail',''),id=n['id'],tone=n.get('tone',tone),check=True)
        cursor=start
        for i,c in enumerate(n.get('children',[])):
            ctone=('accent','teal','amber','red')[i%4] if dep==0 else tone
            place(c,cursor,ctone);cursor+=sizes[c['id']]
            s.edge(n['id'],c['id'],tone=ctone,arrow=False,source_port='right' if direction=='right' else 'bottom')
    place(root,0)

def sequence(s,d):
    actors=d['actors'];messages=d['messages'];need(2<=len(actors)<=8,'sequence: 2–8 actors')
    gap=(s.w-240)/len(actors);ids=[];xs={};bottom=300+len(messages)*70
    for i,a in enumerate(actors):
        a={'id':a,'label':a} if isinstance(a,str) else a
        need(a['id'] not in xs,'duplicate actor')
        x=120+i*gap+gap/2;xs[a['id']]=x;ids.append(a['id'])
        s.add(x-94,202,188,66,a['label'],a.get('detail',''),id=a['id'],check=True)
        s.edge(points=[(x,272),(x,bottom)],dashed=True,arrow=False,tone='line')
    for i,m in enumerate(messages):
        need(m['from'] in xs and m['to'] in xs,'unknown sequence actor')
        x1,x2=xs[m['from']],xs[m['to']];y=320+i*70
        points=[(x1,y),(x2,y)]
        if x1==x2:points=[(x1,y),(x1+55,y),(x1+55,y+30),(x1,y+30)]
        s.edge(label=f"{i+1:02d}  {m['label']}",points=points,dashed=m.get('return',False),tone='teal' if m.get('return') else 'accent',label_at=[(x1+x2)/2+(80 if x1==x2 else 0),y-17])
    s.h=max(s.h,bottom+100)

def gantt_parse(d):
    tasks=d['tasks'];need(tasks,'empty tasks');parsed=[];ids={}
    for task in tasks:
        a,b=dt.date.fromisoformat(task['start']),dt.date.fromisoformat(task['end']);need(a<=b,'end precedes start: '+task['id'])
        need(task['id'] not in ids,'duplicate task id');need(0<=task.get('progress',0)<=100,'progress outside 0–100')
        ids[task['id']]=len(parsed);parsed.append((task,a,b))
    return parsed,ids,min(x[1] for x in parsed),max(x[2] for x in parsed)

def gantt_grid(s,start,days,x0,usable,y0,y1,ticks=7):
    for j in range(ticks):
        day=round(j*days/(ticks-1));x=x0+day*usable/days
        s.edge(points=[(x,y0),(x,y1)],tone='line',arrow=False)
        if j<ticks-1:s.text(x,y0-34,112,22,(start+dt.timedelta(days=day)).strftime('%m/%d'),14,'muted')

def gantt_dependencies(s,parsed,ids,bars):
    for task,a,b in parsed:
        for dep in task.get('depends',[]):
            need(dep in ids,'missing dependency: '+dep)
            prior=parsed[ids[dep]];need(a>prior[2],f'finish-to-start dependency conflict: {dep} -> {task["id"]}')
            x1,y1,w1=bars[dep];x2,y2,w2=bars[task['id']]
            s.edge(dep,task['id'],points=[(x1+w1,y1),(x1+w1+12,y1),(x1+w1+12,y2),(x2,y2)],source_port='right',target_port='left',tone='muted',width=1.3)

def gantt_bar(s,task,a,b,period_start,x0,unit,y,bars,bar_height=24,tone='accent'):
    x=x0+(a-period_start).days*unit;w=((b-a).days+1)*unit;kind='diamond' if task.get('milestone') else 'rect'
    if task.get('milestone'):
        need(a==b,'milestone must have same start/end');w=24;x-=12
    s.add(x,y-bar_height/2,w,bar_height,kind=kind,id=task['id'],fill='tint',stroke=tone,check=False)
    progress=task.get('progress',0)
    if progress and not task.get('milestone'):
        s.add(x,y-bar_height/2,w*progress/100,bar_height,kind='rect',fill=tone,stroke='none',check=False,parent_task=task['id'])
    bars[task['id']]=(x,y,w)

def gantt_delivery(s,parsed,ids,start,end):
    days=(end-start).days+1;x0=500;usable=s.w-x0-100;unit=usable/days;rowh=76;y0=282
    s.text(82,208,300,40,'任务 / 责任人',18,'muted');s.text(402,208,74,40,'进度',16,'muted',align='right');s.text(x0,208,usable,40,f'{start.isoformat()} — {end.isoformat()} · 自然日',18,'muted')
    gantt_grid(s,start,days,x0,usable,y0-20,y0+len(parsed)*rowh)
    bars={}
    for i,(task,a,b) in enumerate(parsed):
        y=y0+i*rowh;s.text(82,y,300,30,task['label'],20);s.text(82,y+32,300,22,task.get('owner','')+'  ·  '+a.strftime('%m/%d')+' — '+b.strftime('%m/%d'),14,'muted')
        gantt_bar(s,task,a,b,start,x0,unit,y+21,bars)
        s.text(392,y+7,84,30,'里程碑' if task.get('milestone') else f"{task.get('progress',0)}%",14,'muted',align='right')
    gantt_dependencies(s,parsed,ids,bars);s.h=max(s.h,y0+len(parsed)*rowh+100)

def gantt_executive(s,parsed,ids,start,end):
    need(all(task.get('phase') for task,_,_ in parsed),'executive gantt requires a phase for every task')
    days=(end-start).days+1;x0=450;usable=s.w-x0-100;unit=usable/days;y=265;bars={};last_phase=None
    s.text(82,208,300,40,'阶段 / 关键事项',18,'muted');s.text(x0,208,usable,40,f'{start.isoformat()} — {end.isoformat()} · 自然日',18,'muted')
    for i,(task,a,b) in enumerate(parsed):
        if task['phase']!=last_phase:
            if last_phase is not None:y+=18
            s.add(72,y,340,34,kind='panel',fill='tint2',stroke='none',check=False)
            s.text(92,y+6,292,24,task['phase'],15,'accent');y+=44;last_phase=task['phase']
        row_y=y;s.text(96,row_y,296,26,task['label'],18);gantt_bar(s,task,a,b,start,x0,unit,row_y+13,bars,bar_height=18)
        if task.get('milestone'):s.text(392,row_y,42,24,'◆',14,'accent',align='right')
        y+=50
    gantt_grid(s,start,days,x0,usable,245,y-8)
    gantt_dependencies(s,parsed,ids,bars);s.h=max(s.h,y+90)

def gantt_print(s,parsed,ids,start,end):
    days=(end-start).days+1;x0=700;usable=s.w-x0-72;unit=usable/days;rowh=64;y0=282;bars={}
    s.text(72,208,270,32,'任务',17,'ink');s.text(350,208,150,32,'责任人',16,'muted');s.text(510,208,154,32,'起止日期',16,'muted');s.text(x0,208,usable,32,f'{start.isoformat()} — {end.isoformat()} · 自然日',16,'muted')
    s.edge(points=[(72,255),(s.w-72,255)],tone='ink',arrow=False,width=1.2)
    gantt_grid(s,start,days,x0,usable,y0-20,y0+len(parsed)*rowh)
    for i,(task,a,b) in enumerate(parsed):
        y=y0+i*rowh;s.edge(points=[(72,y+53),(s.w-72,y+53)],tone='line',arrow=False,width=.8)
        s.text(72,y,260,28,task['label'],17);s.text(350,y,142,28,task.get('owner',''),14,'muted');s.text(510,y,154,28,a.strftime('%m/%d')+' — '+b.strftime('%m/%d'),14,'muted')
        gantt_bar(s,task,a,b,start,x0,unit,y+22,bars,bar_height=16,tone='ink')
        s.text(510,y+26,154,20,'里程碑' if task.get('milestone') else f"进度 {task.get('progress',0)}%",12,'muted')
    gantt_dependencies(s,parsed,ids,bars);s.h=max(s.h,y0+len(parsed)*rowh+100)

def gantt(s,d):
    parsed,ids,start,end=gantt_parse(d);variant=d.get('gantt_variant','delivery')
    need(variant in {'executive','delivery','print'},'gantt_variant must be executive, delivery, or print')
    if variant=='executive':gantt_executive(s,parsed,ids,start,end)
    elif variant=='print':gantt_print(s,parsed,ids,start,end)
    else:gantt_delivery(s,parsed,ids,start,end)
    s.meta.update({'gantt_variant':variant,'calendar':'natural-days-inclusive','start':start.isoformat(),'end':end.isoformat(),'critical_path':'not-calculated'})

def matrix(s,d):
    cells=d['cells'];cols=d.get('columns',2);need(1<=cols<=4,'matrix columns: 1–4');need(cells,'empty matrix')
    rows=math.ceil(len(cells)/cols);gap=24;w=(s.w-128-gap*(cols-1))/cols;h=d.get('cell_height',235)
    for i,c in enumerate(cells):
        x=64+(i%cols)*(w+gap);y=198+(i//cols)*(h+gap);tone=c.get('tone',('accent','teal','amber','red')[i%4])
        s.add(x,y,w,h,kind='panel',check=False);s.add(x,y,5,h,kind='rect',fill=tone,stroke='none',check=False)
        s.text(x+28,y+24,w-56,36,c['label'],24,tone)
        lines=c.get('items',[]);need(len(lines)<=5,'matrix cell more than five items: split')
        for j,line in enumerate(lines):s.text(x+30,y+83+j*32,w-60,30,'•  '+line,18)
    s.h=max(s.h,198+rows*(h+gap)+76)

def chart(s,d):
    series=d['data'];mode=d.get('mode','bar');need(series,'empty chart data')
    vals=[v['value'] for v in series];need(all(finite(v) for v in vals),'all chart values must be finite numbers')
    need(all(v>=0 for v in vals),'negative values require a signed-axis plotting backend')
    maximum=max(vals);need(maximum>0,'chart needs a positive value')
    unit=d.get('unit','');s.meta['data_values']=vals
    if mode=='bar':
        left=320;plotw=s.w-460;y0=240;rh=76
        for i,item in enumerate(series):
            y=y0+i*rh;s.text(72,y,222,38,item['label'],20,align='right')
            s.add(left,y+4,plotw,30,kind='rect',fill='tint',stroke='none',check=False)
            s.add(left,y+4,plotw*item['value']/maximum,30,kind='rect',fill='accent' if i==d.get('highlight',0) else 'teal',stroke='none',check=False)
            s.text(left+plotw+12,y,120,38,f'{item["value"]:g}{unit}',18)
        s.text(left,y0+len(series)*rh+20,plotw,28,'0 起点 · 长度按数值比例计算',15,'muted');s.h=max(s.h,y0+(len(series)+1)*rh+100)
    elif mode=='line':
        need(len(series)>=2,'line chart needs two or more points');x0=130;y0=250;pw=s.w-260;ph=440
        for i in range(5):
            value=maximum*i/4;y=y0+ph-ph*i/4;s.edge(points=[(x0,y),(x0+pw,y)],arrow=False,tone='line');s.text(64,y-14,54,28,f'{value:g}',14,'muted',align='right')
        points=[]
        for i,item in enumerate(series):
            x=x0+pw*i/(len(series)-1);y=y0+ph-ph*item['value']/maximum;points.append([x,y])
            s.add(x-5,y-5,10,10,kind='ellipse',fill='accent',stroke='panel',check=False)
            s.text(x-80,y0+ph+18,160,40,item['label'],16,'muted',align='center');s.text(x-70,y-36,140,28,f'{item["value"]:g}{unit}',16,align='center')
        s.edge(points=points,arrow=False,tone='accent',width=3);s.h=max(s.h,y0+ph+140)
    elif mode=='donut':
        total=sum(vals);cx=530;cy=475;r=200;inner=132;angle=-math.pi/2;tones=['accent','teal','amber','red','muted'];need(len(series)<=5,'donut supports up to five categories')
        for i,item in enumerate(series):
            share=item['value']/total;end=angle+share*math.tau
            count=max(2,math.ceil(share*120));pts=[]
            for j in range(count+1):a=angle+(end-angle)*j/count;pts.append([cx+r*math.cos(a),cy+r*math.sin(a)])
            for j in range(count,-1,-1):a=angle+(end-angle)*j/count;pts.append([cx+inner*math.cos(a),cy+inner*math.sin(a)])
            if item['value']>0:s.add(cx-r,cy-r,2*r,2*r,kind='polygon',points=pts,fill=tones[i],stroke='bg',check=False)
            y=280+i*84;s.add(850,y+8,16,16,kind='rect',fill=tones[i],stroke='none',check=False)
            s.text(885,y,360,36,item['label'],22);s.text(885,y+35,420,28,f'{item["value"]:g}{unit}  /  {share:.1%}',17,'muted')
            angle=end
        s.text(cx-130,cy-42,260,58,f'{total:g}',40,align='center');s.text(cx-130,cy+20,260,32,d.get('total_label','总计')+' '+unit,17,'muted',align='center')
    else:raise ValueError('chart mode supported: bar, line, donut')

def fishbone(s,d):
    groups=d['categories'];need(2<=len(groups)<=6,'fishbone expects 2–6 categories')
    cause_width=250;cause_size=15;line_height=20;stack_gap=8
    def cause_height(cause):
        return max(32,len(wrap('• '+cause,cause_width,cause_size))*line_height+6)
    stacks=[sum(cause_height(cause)+stack_gap for cause in group.get('causes',[])) for group in groups]
    max_stack=max(stacks or [32])-stack_gap
    up_start=300;mainy=max(480,up_start+max_stack+18);down_start=mainy+30;down_label_y=down_start+max_stack+18
    s.h=max(s.h,down_label_y+100);endx=s.w-330;s.edge(points=[(100,mainy),(endx,mainy)],tone='accent',width=3)
    effect_width=240;effect_inner=effect_width-30
    effect_label_lines=wrap_words(d['effect'],effect_inner,22)
    effect_detail_lines=wrap_words(d.get('effect_detail',''),effect_inner,16) if d.get('effect_detail','') else []
    effect_h=max(92,sum(size*1.35 for size in [22]*len(effect_label_lines)+[16]*len(effect_detail_lines))+24)
    s.add(endx+12,mainy-effect_h/2,effect_width,effect_h,d['effect'],d.get('effect_detail',''),tone='accent',check=True,word_wrap=True)
    pairs=math.ceil(len(groups)/2);step=(endx-150)/pairs
    for i,g in enumerate(groups):
        col=i//2;up=i%2==0;tipx=170+col*step;base=tipx+265;ty=up_start-64 if up else down_label_y
        tone=('accent','teal','amber')[col%3]
        rib_start=(tipx+150,up_start-18 if up else down_start+max_stack+10)
        s.edge(points=[rib_start,(base,mainy)],arrow=False,tone=tone)
        s.text(tipx-70,ty,260,36,g['label'],22,tone)
        text_y=up_start if up else down_start
        for j,cause in enumerate(g.get('causes',[])):
            need(j<3,'fishbone: split categories exceeding 3 causes')
            box_h=cause_height(cause);s.text(tipx-95,text_y,cause_width,box_h,'• '+cause,cause_size,word_wrap=True)
            line_y=text_y+box_h/2
            join_x=rib_start[0]+(base-rib_start[0])*(line_y-rib_start[1])/(mainy-rib_start[1])
            s.edge(points=[(tipx+137,line_y),(join_x,line_y)],arrow=False,tone=tone,width=1.3);text_y+=box_h+stack_gap

def build(d,theme):
    need(d.get('type') in BUILDERS,'unsupported type: '+str(d.get('type')))
    need(isinstance(d.get('title'),str) and d['title'].strip(),'title is required')
    s=Scene(d,theme);need(finite(s.w) and finite(s.h) and s.w>=800 and s.h>=500,'invalid page size')
    from adaptive_layout import selected, build_adaptive
    refined=d.get('layout',{}).get('profile')=='refined'
    if selected(d):
        build_adaptive(s,d)
        if refined:s.meta['refined_layout']={'version':40,'profile':'refined','manual_visual_review':'not-run'}
    elif d['type']=='storymap':
        BUILDERS['storymap'](s,d)
    elif refined:
        from refined_layout import build as refined_build
        refined_build(s,d)
    else:BUILDERS[d['type']](s,d)
    return s.finish()
BUILDERS={'architecture':architecture,'graph':graph,'tree':tree,'sequence':sequence,'gantt':gantt,'matrix':matrix,'chart':chart,'fishbone':fishbone}

from layouts import BUILDERS as EXTRA_BUILDERS
BUILDERS.update(EXTRA_BUILDERS)
from story_map import build as story_map_build
BUILDERS['storymap']=story_map_build
from experience_maps import BUILDERS as EXPERIENCE_BUILDERS
BUILDERS.update(EXPERIENCE_BUILDERS)

def label_lines(n):
    if '_lines' in n:return n['_lines']
    if not n['label'] and not n['detail']:return []
    wrapper=wrap_words if n.get('word_wrap') else wrap
    if n['kind']=='text':
        fs=n.get('fs',18);return [(line,fs,n.get('bold',False),n['tone']) for line in wrapper(n['label'],n['w'],fs)]
    if n['kind']=='panel':return [(n['label'],20,True,'muted')] if n['label'] else []
    fs=n.get('fs',22);width=n['w']-(80 if n['kind']=='diamond' else 30)
    lines=[(line,fs,True,'ink') for line in wrapper(n['label'],width,fs)]
    if n['detail']:lines +=[(line,16,False,'muted') for line in wrapper(n['detail'],width,16)]
    return lines

def svg(s):
    t=s.palette;out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w}" height="{s.h}" viewBox="0 0 {s.w} {s.h}" role="img" aria-labelledby="diagram-title diagram-desc">',f'<title id="diagram-title">{html.escape(s.spec["title"])}</title>',f'<desc id="diagram-desc">{html.escape(s.spec.get("subtitle",""))}</desc>',f'<rect width="100%" height="100%" fill="{t["bg"]}"/>','<defs>']
    for key in ['accent','teal','amber','red','muted','line','ink']:
        out.append(f'<marker id="arrow-{key}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{t[key]}"/></marker>')
    out+=['</defs>',f'<g font-family="{FONT}">']
    # Background panels first; connectors then foreground objects.
    def shape(n):
        x,y,w,h=[n[k] for k in ('x','y','w','h')];kind=n['kind'];tone=n['tone']
        fill=color(t,n.get('fill','panel' if kind in ('panel','rect','diamond','pill','cylinder','ellipse') else 'none'))
        stroke=color(t,n.get('stroke','line' if kind=='panel' else tone))
        attrs=f'fill="{fill}" stroke="{stroke}" stroke-width="{n.get("stroke_width",1.5)}"'
        if kind=='text':return ''
        if kind=='diamond':return f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" {attrs}/>'
        if kind=='polygon':return f'<polygon points="'+ ' '.join(f'{px},{py}' for px,py in n['points'])+f'" {attrs}/>'
        if kind=='ellipse':return f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" {attrs}/>'
        if kind=='cylinder':
            ry=min(15,h/5);return f'<path d="M{x},{y+ry} A{w/2},{ry} 0 0 1 {x+w},{y+ry} L{x+w},{y+h-ry} A{w/2},{ry} 0 0 1 {x},{y+h-ry} Z" {attrs}/><ellipse cx="{x+w/2}" cy="{y+ry}" rx="{w/2}" ry="{ry}" {attrs}/>'
        rx=n.get('radius',0 if n.get('stroke')=='none' else (h/2 if kind=='pill' else 10))
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {attrs}/>'
    def node(n):
        x,y,w,h=[n[k] for k in ('x','y','w','h')];family=f' font-family="{html.escape(n["font_family"],quote=True)}"' if n.get('font_family') else '';out.append(f'<g id="{html.escape(n["id"],quote=True)}" data-kind="{n["kind"]}" data-content-text="{str(n.get("content_text",False)).lower()}" data-box="{x},{y},{w},{h}"{family}>');out.append(shape(n))
        lines=label_lines(n);total=sum(z[1]*1.35 for z in lines);align=n.get('align','center');istext=n['kind']=='text';ispanel=n['kind']=='panel'
        if ispanel:align='left';cx=x+24;cursor=y+9
        else:
            cx=x if align=='left' else x+w if align=='right' else x+w/2
            cursor=y+(h-total)/2
        anchor={'left':'start','center':'middle','right':'end'}[align]
        for line,size,bold,tone in lines:
            editorial_font=' font-family="Songti SC, Noto Serif CJK SC, serif"' if s.theme.startswith('editorial-') and size>=36 else ''
            out.append(f'<text x="{cx}" y="{cursor+size}" text-anchor="{anchor}" font-size="{size}" font-weight="{600 if bold else 400}" fill="{color(t,tone)}"{editorial_font}>{html.escape(line)}</text>');cursor+=size*1.35
        out.append('</g>')
    for n in s.nodes:
        if n['kind']=='panel':node(n)
    for e in s.edges:
        tone=e.get('tone','accent');pts=e['points'];p='M'+' L'.join(f'{x},{y}' for x,y in pts)
        marker=f' marker-end="url(#arrow-{tone})"' if e.get('arrow',True) else ''
        dash=' stroke-dasharray="7 6"' if e.get('dashed') else ''
        out.append(f'<path d="{p}" fill="none" stroke="{color(t,tone)}" stroke-width="{e.get("width",2)}" stroke-linejoin="round"{dash}{marker}/>')
    for n in s.nodes:
        if n['kind']!='panel':node(n)
    for e in s.edges:
        if not e.get('label'):continue
        if e.get('_label_box'):
            x,y,x1,y1=e['_label_box']
            from adaptive_layout import METRICS
            out.append(f'<g data-edge-label="true" data-box="{x},{y},{x1-x},{y1-y}" font-family="{html.escape(METRICS.family,quote=True)}"><rect x="{x}" y="{y}" width="{x1-x}" height="{y1-y}" rx="4" fill="{t["bg"]}"/>')
            for j,line in enumerate(e['_label_lines']):
                size=e.get('_label_font',15)
                out.append(f'<text x="{(x+x1)/2}" y="{y+size+5+j*math.ceil(size*1.4)}" font-size="{size}" text-anchor="middle" fill="{color(t,e.get("tone","muted"))}">{html.escape(line)}</text>')
            out.append('</g>');continue
        pts=e['points'];pos=e.get('label_at');align=e.get('label_align','center')
        if not pos:
            segments=list(zip(pts,pts[1:]));a,b=max(segments,key=lambda ab:abs(ab[0][0]-ab[1][0])+abs(ab[0][1]-ab[1][1]));pos=[(a[0]+b[0])/2,(a[1]+b[1])/2-13]
        x,y=pos;lw=measure(e['label'],15)+16;rx=x-8 if align=='left' else x-lw/2
        out.append(f'<rect x="{rx}" y="{y-17}" width="{lw}" height="25" rx="4" fill="{t["bg"]}"/>')
        out.append(f'<text x="{x}" y="{y}" font-size="15" text-anchor="{"start" if align=="left" else "middle"}" fill="{color(t,e.get("tone","muted"))}">{html.escape(e["label"])}</text>')
    out+=['</g></svg>']
    result='\n'.join(out)
    if s.meta.get('refined_layout'):result=result.replace('<svg ','<svg data-quality="refined" ',1)
    return result

def drawio(s):
    t=s.palette;mxfile=ET.Element('mxfile',host='diagram-studio',version='1.0');diagram=ET.SubElement(mxfile,'diagram',id='diagram',name=s.spec['title'])
    model=ET.SubElement(diagram,'mxGraphModel',dx=str(s.w),dy=str(s.h),grid='1',gridSize='8',page='1',pageScale='1',pageWidth=str(s.w),pageHeight=str(s.h),background=t['bg'])
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    for n in s.nodes:
        x,y,w,h=[n[k] for k in ('x','y','w','h')];k=n['kind'];tone=n['tone'];shape={'diamond':'rhombus','ellipse':'ellipse','cylinder':'cylinder','text':'text'}.get(k,'rectangle')
        fill=color(t,n.get('fill','panel' if k!='text' else 'none'));stroke=color(t,n.get('stroke','line' if k=='panel' else tone))
        if k=='text':fill='none';stroke='none'
        style=f'shape={shape};rounded={0 if n.get("radius")==0 else 1};arcSize={50 if k=="pill" else 10};whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor={color(t,tone) if k=="text" else t["ink"]};fontFamily=PingFang SC;fontSize={n.get("fs",22)};align={n.get("align","center")};verticalAlign=middle;spacing=12;'
        if k=='panel':style+='verticalAlign=top;align=left;fontSize=20;'
        if s.theme.startswith('editorial-'):
            if n.get('fs',22)>=36:style=style.replace('fontFamily=PingFang SC;','fontFamily=Songti SC;')
            if k=='text':style=style.replace('spacing=12;','spacing=0;')
        if k=='polygon':
            # Editable vector wedges use an mxGraph custom stencil.
            import base64,zlib
            from urllib.parse import quote
            sh=ET.Element('shape',name='polygon',w=str(w),h=str(h),aspect='variable',strokewidth='inherit');fg=ET.SubElement(sh,'foreground');path=ET.SubElement(fg,'path')
            for i,(px,py) in enumerate(n['points']):ET.SubElement(path,'move' if i==0 else 'line',x=str(px-x),y=str(py-y))
            ET.SubElement(path,'close');ET.SubElement(fg,'fillstroke')
            compressor=zlib.compressobj(wbits=-15)
            raw=quote(ET.tostring(sh,encoding='unicode'),safe="~()*!.'-").encode()
            encoded=base64.b64encode(compressor.compress(raw)+compressor.flush()).decode()
            style=style.replace('shape=rectangle;',f'shape=stencil({encoded});')
        value=html.escape(n['label'])
        if n.get('detail'):value='<b>'+value+'</b><br><span style="font-size:16px;color:'+t['muted']+'">'+html.escape(n['detail'])+'</span>'
        value=value.replace('\n','<br>')
        if '_lines' in n:
            value='<br>'.join(f'<span style="font-size:{size}px;color:{color(t,tone)};font-weight:{600 if bold else 400}">{html.escape(line)}</span>' for line,size,bold,tone in n['_lines'])
        if n.get('font_family'):
            style=style.replace('fontFamily=PingFang SC;',f'fontFamily={n["font_family"]};')
        parent=n.get('parent_task','1')
        if parent!='1':
            owner=s.get(parent);x-=owner['x'];y-=owner['y']
            style+='movable=0;resizable=0;selectable=0;'
        c=ET.SubElement(root,'mxCell',id=n['id'],value=value,style=style,vertex='1',parent=parent);ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    ports={'left':(0,.5),'right':(1,.5),'top':(.5,0),'bottom':(.5,1)}
    for i,e in enumerate(s.edges):
        tone=e.get('tone','accent');pts=e['points']
        orthogonal=all(abs(a[0]-b[0])<.1 or abs(a[1]-b[1])<.1 for a,b in zip(pts,pts[1:]))
        edge_style='orthogonalEdgeStyle' if orthogonal and (e.get('source') or e.get('target')) else 'none'
        style=f'edgeStyle={edge_style};rounded=0;html=1;strokeColor={color(t,tone)};strokeWidth={e.get("width",2)};fontColor={color(t,tone)};fontSize=15;labelBackgroundColor={t["bg"]};endArrow={"block" if e.get("arrow",True) else "none"};'
        if e.get('dashed'):style+='dashed=1;'
        if e.get('_label_font'):style=style.replace('fontSize=15;',f'fontSize={e["_label_font"]};')
        for key,prefix in [('source_port','exit'),('target_port','entry')]:
            selected=e.get(key)
            endpoint=e.get('source' if prefix=='exit' else 'target')
            if not selected and endpoint:
                n=s.get(endpoint);point=pts[0] if prefix=='exit' else pts[-1]
                nearest=min(ports,key=lambda p:sum((a-b)**2 for a,b in zip(port(n,p),point)))
                if sum((a-b)**2 for a,b in zip(port(n,nearest),point))<1:selected=nearest
            if selected:px,py=ports[selected];style+=f'{prefix}X={px};{prefix}Y={py};{prefix}Dx=0;{prefix}Dy=0;'
        attrs=dict(id=f'_edge_{i}',value=e.get('label',''),style=style,edge='1',parent='1')
        if e.get('source'):attrs['source']=e['source']
        if e.get('target'):attrs['target']=e['target']
        c=ET.SubElement(root,'mxCell',attrs);geo=ET.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});pts=e['points']
        if e.get('_label_box'):
            lengths=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])]
            remaining=sum(lengths)/2;middle=pts[0]
            for a,b,length in zip(pts,pts[1:],lengths):
                if remaining<=length:
                    fraction=remaining/length if length else 0;middle=(a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1]));break
                remaining-=length
            x0,y0,x1,y1=e['_label_box'];geo.set('x','0');geo.set('y','0')
            ET.SubElement(geo,'mxPoint',x=str((x0+x1)/2-middle[0]),y=str((y0+y1)/2-middle[1]),attrib={'as':'offset'})
            c.set('style',c.get('style')+f'whiteSpace=wrap;labelWidth={x1-x0};')
        if not e.get('source'):ET.SubElement(geo,'mxPoint',x=str(pts[0][0]),y=str(pts[0][1]),attrib={'as':'sourcePoint'})
        if not e.get('target'):ET.SubElement(geo,'mxPoint',x=str(pts[-1][0]),y=str(pts[-1][1]),attrib={'as':'targetPoint'})
        if len(pts)>2:
            arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
            for x,y in pts[1:-1]:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    return ET.tostring(mxfile,encoding='unicode',xml_declaration=True)

def audit(s):
    errors=[];warnings=[];nodes=s.nodes
    for n in nodes:
        if not all(finite(n[k]) for k in ('x','y','w','h')) or min(n['w'],n['h'])<=0:errors.append('invalid geometry: '+n['id']);continue
        if n['x']<0 or n['y']<0 or n['x']+n['w']>s.w+.1 or n['y']+n['h']>s.h+.1:errors.append('outside page: '+n['id'])
        lines=label_lines(n)
        if sum(z[1]*1.35 for z in lines)>n['h']+2:errors.append('text estimate overflows: '+n['id'])
    check=[n for n in nodes if n.get('check')]
    for i,a in enumerate(check):
        for b in check[i+1:]:
            ox=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']);oy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
            if ox>1 and oy>1:errors.append(f'node overlap: {a["id"]} / {b["id"]}')
    for i,e in enumerate(s.edges):
        for x,y in e['points']:
            if not finite(x) or not finite(y) or not (0<=x<=s.w and 0<=y<=s.h):errors.append(f'edge {i} outside page')
        for n in check:
            if n['id'] in (e.get('source'),e.get('target'),e.get('internal_to')):continue
            for a,b in zip(e['points'],e['points'][1:]):
                x0,y0=n['x']+2,n['y']+2;x1,y1=n['x']+n['w']-2,n['y']+n['h']-2
                cross=(abs(a[0]-b[0])<.1 and x0<a[0]<x1 and max(min(a[1],b[1]),y0)<min(max(a[1],b[1]),y1)) or (abs(a[1]-b[1])<.1 and y0<a[1]<y1 and max(min(a[0],b[0]),x0)<min(max(a[0],b[0]),x1))
                if cross:warnings.append(f'edge {i} may cross node {n["id"]}');break
    result=dict(errors=sorted(set(errors)),warnings=sorted(set(warnings)),nodes=len(nodes),edges=len(s.edges),scope='geometry, text estimate, axis-aligned edge/node crossings; not semantic or visual acceptance')
    if s.meta.get('adaptive_layout') or s.meta.get('refined_layout'):
        from adaptive_layout import METRICS,rect,intersects,segment_hits
        for n in nodes:
            for line,size,_,_ in label_lines(n):
                if METRICS.width(line,size)>n['w']-n.get('text_margin',0)*2+1:
                    result['errors'].append('measured text width overflows: '+n['id'])
        boxes=[]
        for i,e in enumerate(s.edges):
            box=e.get('_label_box')
            if not box:continue
            if box[0]<0 or box[1]<0 or box[2]>s.w or box[3]>s.h:result['errors'].append(f'edge label outside page: {i}')
            if any(intersects(box,rect(n)) for n in check):result['errors'].append(f'edge label overlaps node: {i}')
            if any(intersects(box,b) for b in boxes):result['errors'].append(f'edge labels overlap: {i}')
            boxes.append(box)
        result.update(font_measurement=METRICS.mode,rendered_visual_check='not-run',manual_visual_review='not-run')
        if s.meta.get('adaptive_layout'):result['adaptive_layout']=s.meta['adaptive_layout']
        if s.meta.get('refined_layout'):result['refined_layout']=s.meta['refined_layout']
    return result

def _render_files(source,out,theme='light'):
    source=Path(source);d=json.loads(source.read_text(encoding='utf-8'));need(theme in THEMES,'unknown theme');s=build(d,theme);qa=audit(s)
    out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=source.stem
    need(not qa['errors'],'layout audit failed: '+'; '.join(qa['errors']))
    (out/(stem+'.svg')).write_text(svg(s),encoding='utf-8');(out/(stem+'.drawio')).write_text(drawio(s),encoding='utf-8')
    scene_payload=dict(width=s.w,height=s.h,theme=theme,palette=s.palette,nodes=s.nodes,edges=s.edges,meta=s.meta,assumptions=d.get('assumptions',[]))
    (out/(stem+'.scene.json')).write_text(json.dumps(scene_payload,ensure_ascii=False,indent=2),encoding='utf-8')
    qa['content_integrity']=content_integrity(d,scene_payload)
    need(qa['content_integrity']['status']!='failed','source content integrity failed: '+json.dumps(qa['content_integrity'],ensure_ascii=False))
    (out/(stem+'.qa.json')).write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/(stem+'.brief.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    result=dict(svg=str(out/(stem+'.svg')),drawio=str(out/(stem+'.drawio')),qa=qa)
    if s.meta.get('adaptive_layout') or s.meta.get('refined_layout'):
        from adaptive_delivery import deliver
        result['reading_view']=deliver(s,d,out,stem)
    return result

def render_file(source,out,theme='light',version_root=None):
    """Validate a complete staged delivery before touching the last good files.

    Promotion uses individual file replacements, not a filesystem transaction;
    an OS failure during promotion can still interrupt a multi-file update.
    """
    source=Path(source);out=Path(out);raw=source.read_bytes();stem=source.stem
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.diagram-stage-',dir=out.parent) as temp:
        root=Path(temp);frozen=root/source.name;frozen.write_bytes(raw)
        stage=root/'artifacts'
        result=_render_files(frozen,stage,theme)
        qa=result['qa'];adaptive=qa.get('adaptive_layout',{})
        findings=[]
        if adaptive.get('crossings',0):findings.append({'kind':'connector-crossings','count':adaptive['crossings']})
        if adaptive.get('readability',{}).get('status')=='review-required':
            findings.append({'kind':'small-overview-text',**adaptive['readability']})
        files=sorted(stage.iterdir())
        receipt=make_receipt(raw,stage,source_name=stem,theme=theme,
                 checks={'geometry':{'status':'passed','warnings':qa['warnings']},
                         'composition':{'status':('review-required' if findings else 'within-target') if adaptive else 'not-run','findings':findings},
                         'content_integrity':qa.get('content_integrity',{'status':'not-run'}),
                         'browser_text_bounds':{'status':'not-run'},'manual_visual_review':{'status':'not-run'},
                         'native_editor':{'status':'not-run'}},
                 delivery_scope='Generation, semantic content checks and QA finish before replacement. Individual files are replaced; promotion is not a multi-file atomic transaction.')
        receipt_path=stage/(stem+'.delivery.json')
        receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        out.mkdir(parents=True,exist_ok=True)
        # Reader entrypoint and receipt are promoted after their dependencies.
        for p in sorted(files,key=lambda p:p.suffix=='.html')+[receipt_path]:
            os.replace(p,out/p.name)
        result['svg']=str(out/(stem+'.svg'));result['drawio']=str(out/(stem+'.drawio'))
        result['receipt']=str(out/receipt_path.name)
        verify_receipt(result['receipt'])
        if 'reading_view' in result:
            result['reading_view']['html']=str(out/(stem+'.html'))
            result['reading_view']['index']=str(out/(stem+'-reading.json'))
        if version_root:
            version_dir=snapshot(out,result['receipt'],version_root)
            receipt['version_dir']=str(version_dir)
            receipt_path=out/receipt_path.name
            receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
            snapshot(out,receipt_path,version_root)
        return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--out',required=True);p.add_argument('--theme',choices=THEMES,default='light');p.add_argument('--version-root',help='copy the completed delivery into <version-root>/<version-id>');args=p.parse_args()
    try:print(json.dumps(render_file(args.source,args.out,args.theme,args.version_root),ensure_ascii=False))
    except (KeyError,ValueError,TypeError) as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
