"""Editable teaching symbols with explicit port placement; no standards certification."""
import argparse,csv,json,math
from pathlib import Path
from pid_model import validate,fields,need
from render import Scene,svg,drawio,audit
from pid_geometry import diagnose,crossing_display
SLOTS={'tank':{'left':(-60,0),'right':(60,0),'top':(0,-60),'bottom':(0,60)},'pump':{'left':(-36,0),'right':(36,0)},'valve':{'left':(-32,0),'right':(32,0)},'instrument':{'left':(-36,0),'right':(36,0),'top':(0,-36),'bottom':(0,36)},'junction':{'left':(-6,0),'right':(6,0),'top':(0,-6),'bottom':(0,6)},'boundary':{'left':(-32,0),'right':(32,0)}}

def build(d,layout,theme='editorial-warm'):
    topology=validate(d);fields(layout,('positions','ports','routes','crossings') if 'crossings' in layout else ('positions','ports','routes'),'layout')
    items={x['id']:x for x in d['items']};allports={p['id']:i for i in d['items'] for p in i['ports']}
    need(type(layout['positions']) is dict and set(layout['positions'])==set(items),'positions must cover every item')
    need(type(layout['ports']) is dict and set(layout['ports'])==set(allports),'layout must bind every port')
    need(type(layout['routes']) is dict and set(layout['routes'])=={c['id'] for c in d['connections']},'routes must cover every connection')
    def point(p):
        need(type(p) is list and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in p),'finite point required')
        need(100<=p[0]<=1500 and 220<=p[1]<=620,'point outside supported drawing region')
        return p
    for p in layout['positions'].values():point(p)
    coords={};taken=set()
    for pid,slot in layout['ports'].items():
        i=allports[pid];need(isinstance(slot,str) and slot in SLOTS[i['kind']],'unsupported port slot')
        need((i['id'],slot) not in taken,'two ports share a symbol slot');taken.add((i['id'],slot))
        x,y=layout['positions'][i['id']];dx,dy=SLOTS[i['kind']][slot];coords[pid]=[x+dx,y+dy]
    scene=Scene(dict(width=1600,height=1080,title=d['title'],subtitle='独立教学符号 · 连接来自显式端口模型；未验证为 ISA 标准工程图',eyebrow='PIPING / MEASUREMENT / SIGNAL',footer='假设模型 · 不含管径、压力等级、保护设定或水力计算；JSON 是连接依据'),theme)
    def line(points,**kw):scene.edge(points=points,arrow=False,tone='ink',width=2,**kw)
    for i in d['items']:
        x,y=layout['positions'][i['id']];kind=i['kind'];iid=i['id']
        if kind=='tank':line([(x-60,y-60),(x-60,y+60),(x+60,y+60),(x+60,y-60)])
        elif kind in ('pump','instrument'):
            scene.add(x-36,y-36,72,72,kind='ellipse',fill='none',tone='ink',id=iid,check=False)
            if kind=='pump':line([(x-18,y-18),(x+22,y),(x-18,y+18),(x-18,y-18)])
            else:scene.text(x-33,y-20,66,40,i['tag'].split('-')[0],size=20,align='center')
        elif kind=='valve':line([(x-32,y-24),(x+32,y+24),(x+32,y-24),(x-32,y+24),(x-32,y-24)])
        elif kind=='junction':scene.add(x-6,y-6,12,12,kind='ellipse',fill='ink',stroke='none',id=iid,check=False)
        else:line([(x-32,y-22),(x+14,y-22),(x+32,y),(x+14,y+22),(x-32,y+22),(x-32,y-22)])
        scene.text(x-100,y+(-120 if kind=='instrument' else 78),200,30,i['tag'],size=20,align='center')
        scene.text(x-100,y+(-88 if kind=='instrument' else 110),200,34,i['label'],size=17,tone='muted',align='center')
    connections=[]
    for c in d['connections']:
        via=layout['routes'][c['id']];need(type(via) is list,'route must be list')
        points=[coords[c['from']]]+[point(p) for p in via]+[coords[c['to']]]
        need(all(a[0]==b[0] or a[1]==b[1] for a,b in zip(points,points[1:])),'route must be orthogonal')
        need(all(a!=b for a,b in zip(points,points[1:])),'zero length route segment')
        scene.edge(points=points,arrow=c['flow']=='forward',dashed=c['domain']=='signal',tone='teal' if c['domain']=='signal' else 'ink',width=2)
        # An unknown flow has no arrow. Bidirectional is explicitly listed below.
        connections.append(dict(**c,points=points))
    scene.text(64,760,1470,34,'图例：实线＝过程连接（含测压）；虚线＝测量信号；实心点＝显式分支；箭头＝已声明方向',size=18)
    scene.text(64,802,1470,34,'无箭头表示双向或方向未知，详见连接表；线条交叉不能自动解释为连通。',size=17,tone='muted')
    for n,c in enumerate(connections):
        x=64+(n%2)*760;y=856+(n//2)*42
        scene.text(x,y,720,36,c['id']+'  '+c['from']+' → '+c['to']+'  ['+c['flow']+']',size=14,tone='muted')
    sizes={'tank':(60,60),'pump':(36,36),'valve':(32,24),'instrument':(36,36),'junction':(6,6),'boundary':(32,22)}
    boxes={}
    for iid,i in items.items():
        x,y=layout['positions'][iid];w,h=sizes[i['kind']];boxes[iid]=[x-w,y-h,x+w,y+h]
    geometry=diagnose(connections,boxes)
    display=crossing_display(connections,geometry,layout.get('crossings',[]))
    if layout.get('crossings'):
        del scene.edges[-len(connections):]
        for c in connections:
            parts=display[c['id']]
            for index,points in enumerate(parts):
                scene.edge(points=points,arrow=c['flow']=='forward' and index==len(parts)-1,dashed=c['domain']=='signal',tone='teal' if c['domain']=='signal' else 'ink',width=2)
        scene.text(64,714,1470,34,'交叉图例：局部断口表示跨越且不连通；不是管道断开。完整连接以端口模型为准。',size=17,tone='muted')
        geometry['declared_crossings']=layout['crossings'];geometry['display_parts']=display
    scene.meta.update(geometry=geometry,topology=topology,connections=connections,port_coordinates=coords,assumptions=d['assumptions'],symbol_scope='Original teaching symbols; not ISA certified')
    scene.finish();qa=audit(scene);need(not qa['errors'] and not qa['warnings'],'layout QA: '+str(qa));return scene,qa

def render_file(source,layout_path,out,theme='editorial-warm'):
    d=json.loads(Path(source).read_text());layout=json.loads(Path(layout_path).read_text());s,q=build(d,layout,theme);out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=Path(source).stem
    for suffix,value in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('layout.json',json.dumps(layout,indent=2)),('qa.json',json.dumps(q,ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))]:(out/(stem+'.'+suffix)).write_text(value)
    with (out/(stem+'.connections.csv')).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','from','to','domain','flow','label']);w.writeheader();w.writerows(d['connections'])
    return q
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--layout',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(render_file(a.input,a.layout,a.out))
