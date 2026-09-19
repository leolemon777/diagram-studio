#!/usr/bin/env python3
"""Static coherent AND/OR fault trees: explicit shared IDs and exact cut sets.

No probabilities or dynamic-gate semantics are inferred. Duplicate visual
occurrences retain one underlying event ID in the analytical model.
"""
import argparse,json,math,re
from pathlib import Path
from render import Scene,need,audit,svg,drawio

def minimal(sets):
    ordered=sorted(set(sets),key=lambda s:(len(s),tuple(sorted(s))))
    result=[]
    for s in ordered:
        if not any(t<=s for t in result):result.append(s)
    return result

def analyze(d):
    for key in ('title','scope','data_status','top'):
        need(isinstance(d.get(key),str) and d[key].strip(),key+' required')
    rows=d.get('events');need(isinstance(rows,list) and 1<=len(rows)<=80,'1..80 event definitions required')
    nodes={}
    for row in rows:
        need(isinstance(row,dict),'event must be an object');id=row.get('id')
        need(isinstance(id,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',id),'stable ASCII event ID required')
        need(id not in nodes,'duplicate event definition: '+id)
        need(isinstance(row.get('label'),str) and row['label'].strip(),'event label required')
        need(row.get('kind') in ('basic','AND','OR'),'only basic/AND/OR supported')
        need('probability' not in row or d.get('probability_model')=='independent_bernoulli','probability needs explicit independent_bernoulli model')
        if row['kind']=='basic':need(not row.get('inputs'),'basic event cannot have inputs')
        else:
            ins=row.get('inputs');need(isinstance(ins,list) and 2<=len(ins)<=10 and all(isinstance(x,str) for x in ins),'gate needs 2..10 input IDs')
            need(len(ins)==len(set(ins)),'duplicate gate input: reference an event once per gate')
        nodes[id]=row
    need(d['top'] in nodes,'unknown top event')
    visited=set();active=set();cuts={};refs={id:0 for id in nodes}
    def solve(id):
        need(id in nodes,'undefined event: '+id)
        need(id not in active,'cycle in fault tree: '+id)
        if id in cuts:return cuts[id]
        active.add(id);visited.add(id);r=nodes[id]
        if r['kind']=='basic':res=[frozenset([id])]
        else:
            children=[]
            for child in r['inputs']:
                need(child in nodes,'undefined event: '+child);refs[child]+=1;children.append(solve(child))
            if r['kind']=='OR':res=minimal([s for child in children for s in child])
            else:
                res=[frozenset()]
                for child in children:
                    need(len(res)*len(child)<=50000,'cut-set expansion too large; use a BDD solver')
                    res=minimal([a|b for a in res for b in child])
            need(len(res)<=2000,'too many minimal cut sets for this backend')
        active.remove(id);cuts[id]=res;return res
    top=solve(d['top']);need(visited==set(nodes),'unreachable definitions: '+','.join(sorted(set(nodes)-visited)))
    result=dict(top=d['top'],minimal_cut_sets=[sorted(s) for s in top],
                event_cut_sets={k:[sorted(s) for s in v] for k,v in cuts.items()},
                repeated_event_ids=sorted(k for k,v in refs.items() if v>1),
                scope=d['scope'],data_status=d['data_status'],
                interpretation='Each set is sufficient under the stated static Boolean model; no proper subset suffices. No likelihood, sequence, or causality proof is implied.')
    if 'probability_model' in d:
        from fault_probability import quantify
        result['quantification']=quantify(d,nodes,top)
    return result

def gate_points(kind,cx,y,w=60,h=58):
    x=cx-w/2
    if kind=='AND':
        return [(x,y+h),(x,y+h*.5)]+[(cx+w/2*math.cos(a),y+h*.5-h*.5*math.sin(a)) for a in [math.pi-i*math.pi/24 for i in range(25)]]+[(x+w,y+h)]
    # Three quadratic arcs: pointed top, convex sides, concave input boundary.
    def q(a,b,c):
        return [((1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0],(1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1]) for t in [i/24 for i in range(25)]]
    return q((cx,y),(x+w,y+h*.25),(x+w,y+h))+q((x+w,y+h),(cx,y+h*.58),(x,y+h))+q((x,y+h),(x,y+h*.25),(cx,y))

def build(d,theme='editorial-warm'):
    a=analyze(d);nodes={r['id']:r for r in d['events']};occ=[]
    def expand(id,depth):
        need(depth<=8,'more than 8 levels: split into linked subtrees')
        need(len(occ)<100,'more than 100 visual occurrences: split into subtrees')
        o=dict(id=id,depth=depth,index=len(occ),children=[]);occ.append(o)
        o['children']=[expand(c,depth+1) for c in nodes[id].get('inputs',[])]
        o['slots']=sum(c['slots'] for c in o['children']) if o['children'] else 1
        return o
    root=expand(d['top'],0);width=max(1200,root['slots']*250+128);need(width<=8000,'tree too wide: split subtrees')
    maxdepth=max(o['depth'] for o in occ);bottom=210+(maxdepth+1)*235
    cutlines=[', '.join(c) for c in a['minimal_cut_sets']]
    need(len(cutlines)<=30,'more than 30 cut sets: use separate analytical report')
    quantitative='quantification' in a
    spec=dict(width=width,height=bottom+240+len(cutlines)*27+(160 if quantitative else 0),title=d['title'],subtitle=d['scope'],eyebrow='FAULT TREE / 静态故障树',footer=d['data_status']+(' · 独立基本事件概率模型；不含动态时序' if quantitative else ' · AND/OR静态逻辑示例；不含发生概率或时序判断'))
    s=Scene(spec,theme)
    def place(o,left):
        span=o['slots']*250;o['cx']=left+span/2;o['y']=205+o['depth']*235
        pos=left
        for c in o['children']:place(c,pos);pos+=c['slots']*250
    place(root,(width-root['slots']*250)/2)
    repeats={id:sum(o['id']==id for o in occ) for id in nodes}
    for o in occ:
        r=nodes[o['id']];cx=o['cx'];y=o['y'];uid=f"occ-{o['index']}"
        name=r['label'];detail=r['id']+(' · 同一事件重复出现' if repeats[r['id']]>1 else '')
        s.add(cx-108,y,216,83,name,detail,id=uid,fs=19,radius=0,check=True)
        gy=y+103
        if r['kind']=='basic':s.add(cx-22,gy,44,44,'',kind='ellipse',tone='ink',id=uid+'-symbol',fill='panel',check=True)
        else:
            pts=gate_points(r['kind'],cx,gy)
            s.add(cx-30,gy,60,58,'',kind='polygon',points=pts,tone='ink',fill='panel',id=uid+'-symbol',check=True)
            s.text(cx+39,gy+15,82,30,r['kind'],size=16,tone='muted')
    for o in occ:
        r=nodes[o['id']];cx=o['cx'];y=o['y'];uid=f"occ-{o['index']}";gy=y+103
        s.edge(uid,uid+'-symbol',source_port='bottom',target_port='top',arrow=False,tone='ink',width=1.4)
        if o['children']:
            # OR's input edge is concave; connect at its central boundary.
            entry=gy+(58 if r['kind']=='AND' else 58*.79)
            junction=y+188
            s.edge(points=[(cx,entry),(cx,junction)],arrow=False,tone='ink',width=1.4,internal_to=uid+'-symbol')
            for c in o['children']:
                s.edge(b=f"occ-{c['index']}",target_port='top',points=[(cx,junction),(c['cx'],junction),(c['cx'],c['y'])],arrow=False,tone='ink',width=1.4)
    s.text(64,bottom,width-128,32,'最小割集 · 每一组均足以触发顶事件',size=23)
    for i,line in enumerate(cutlines):s.text(64,bottom+44+i*27,width-128,27,f'{i+1:02}   {{ {line} }}',size=18)
    s.text(64,bottom+68+len(cutlines)*27,width-128,46,'图例：矩形为事件描述；圆为基本事件；AND要求全部输入，OR要求至少一个输入。相同ID始终是同一事件。',size=16,tone='muted')
    if quantitative:
        q=a['quantification'];qy=bottom+133+len(cutlines)*27
        s.text(64,qy,width-128,35,f"顶事件概率 = {q['top_probability']:.8g} · 完整布尔分解",size=23)
        s.text(64,qy+42,width-128,42,'概率口径：'+q['probability_basis'],size=16,tone='muted')
        s.text(64,qy+84,width-128,42,'前提：基本事件独立；重复ID只计一次。割集可能重叠，不能直接相加。',size=16,tone='muted')
    s.meta.update(analysis=a,occurrences=[dict(event_id=o['id'],object_id=f"occ-{o['index']}") for o in occ]);s.finish()
    return s,a

def render_file(source,out,theme='editorial-warm'):
    d=json.loads(Path(source).read_text());s,a=build(d,theme);qa=audit(s)
    need(not qa['errors'] and not qa['warnings'],'layout failure: '+repr(qa))
    out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=Path(source).stem
    for ext,text in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('analysis.json',json.dumps(a,ensure_ascii=False,indent=2)),('qa.json',json.dumps(qa,ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))]:
        (out/f'{stem}.{ext}').write_text(text)
    return a
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--theme',default='editorial-warm');args=p.parse_args();print(json.dumps(render_file(args.input,args.out,args.theme),ensure_ascii=False))
