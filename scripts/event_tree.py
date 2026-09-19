#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ordered event trees with path-conditional branches and explicit terminal outcomes."""
import argparse,csv,json,math,re
from collections import defaultdict
from decimal import Decimal,localcontext
from pathlib import Path
from render import Scene,need,finite,wrap,audit,svg,drawio


def txt(value,name):
    need(isinstance(value,str) and value.strip(),name+' required');return value

def uid(value):
    need(isinstance(value,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,23}',value),'stable ASCII ID required');return value

def probability(value):
    need(finite(value) and 0<=value<=1,'branch probability must be a finite number in [0,1]')
    return Decimal(str(value))

def analyze(d):
    with localcontext() as ctx:
        ctx.prec=80
        return _analyze(d)

def _analyze(d):
    for key in ('title','scope','data_status'):txt(d.get(key),key)
    mode=d.get('mode');need(mode in ('qualitative','conditional_probability','frequency'),'explicit mode required')
    quantitative=mode!='qualitative';init=d.get('initiator');need(isinstance(init,dict),'initiator object required')
    uid(init.get('id'));txt(init.get('label'),'initiator label');txt(init.get('source'),'initiator source')
    need('probability' not in init,'initiator probability unsupported; use conditional mode or explicit event frequency')
    rate=None;unit=None
    if mode=='frequency':
        f=init.get('frequency');need(isinstance(f,dict),'initiator frequency object required')
        need(finite(f.get('value')) and f['value']>=0,'nonnegative finite event frequency required')
        rate=Decimal(str(f['value']));unit=txt(f.get('unit'),'frequency unit');txt(f.get('source'),'frequency source')
    else:need('frequency' not in init,'frequency supplied outside frequency mode')
    stages=d.get('stages');need(isinstance(stages,list) and 1<=len(stages)<=8,'1..8 ordered barrier stages required')
    stage_index={}
    for i,r in enumerate(stages):
        need(isinstance(r,dict),'stage object required');id=uid(r.get('id'));need(id not in stage_index,'duplicate stage ID');stage_index[id]=i;txt(r.get('label'),'stage label')
    outcomes=d.get('outcomes');need(isinstance(outcomes,list) and 1<=len(outcomes)<=64,'outcome definitions required')
    omap={}
    for r in outcomes:
        need(isinstance(r,dict),'outcome object required');id=uid(r.get('id'));need(id not in omap,'duplicate outcome ID');omap[id]=r;txt(r.get('label'),'outcome label');txt(r.get('description'),'outcome description')
    definitions=d.get('nodes');need(isinstance(definitions,list) and 1<=len(definitions)<=255,'1..255 nodes required')
    nodes={}
    for row in definitions:
        need(isinstance(row,dict),'node object required');id=uid(row.get('id'));need(id not in nodes,'duplicate node ID');nodes[id]=row
    root=d.get('root');need(root in nodes,'root not defined');need(nodes[root].get('kind')=='decision','root must be first barrier decision')
    seen=set();active=set();used_outcomes=set();sequences=[];checks=[];parents={};layout=[]
    def visit(id,depth,path,mass,parent=None):
        need(id in nodes,'undefined destination: '+str(id));need(id not in active,'cycle in event tree')
        need(id not in seen,'shared child is not a tree; define a separate path-context node')
        seen.add(id);active.add(id);parents[id]=parent;r=nodes[id];kind=r.get('kind')
        need(kind in ('decision','terminal'),'node kind decision/terminal required')
        if kind=='terminal':
            need('branches' not in r and 'stage' not in r,'terminal cannot contain branches or stage')
            oid=r.get('outcome');need(oid in omap,'unknown outcome');used_outcomes.add(oid)
            reason=txt(r.get('termination_reason'),'explicit termination reason required')
            need(len(sequences)<64,'more than 64 terminal sequences; split into documented subtrees')
            item=dict(id=id,outcome_id=oid,outcome=omap[oid]['label'],path=path,termination_reason=reason,skipped_stages=[s['id'] for s in stages[depth:]])
            if quantitative:
                item['conditional_probability']=str(mass)
                if rate is not None:item['frequency']=str(rate*mass);item['frequency_unit']=unit
            sequences.append(item);layout.append(dict(id=id,depth=depth,terminal_index=len(sequences)-1))
        else:
            need(depth<len(stages),'decision exceeds declared stages');need(r.get('stage')==stages[depth]['id'],'decision must use next declared stage, without silent skips')
            txt(r.get('context'),'decision context');txt(r.get('partition_basis'),'mutually exclusive and exhaustive partition basis')
            branches=r.get('branches');need(isinstance(branches,list) and 2<=len(branches)<=5,'decision needs 2..5 explicit branches')
            bids=set();values=[]
            for b in branches:
                need(isinstance(b,dict),'branch object required');bid=uid(b.get('id'));need(bid not in bids,'duplicate branch ID within decision');bids.add(bid)
                txt(b.get('label'),'branch label');need(isinstance(b.get('to'),str),'branch destination ID required')
                if quantitative:
                    values.append(probability(b.get('probability')));txt(b.get('source'),'conditional probability source')
                else:need('probability' not in b,'qualitative mode cannot silently ignore probabilities')
            if quantitative:
                total=sum(values,Decimal(0));need(abs(total-1)<=Decimal('1e-12'),'conditional branch probabilities must sum to 1; no automatic normalization')
                checks.append(dict(node_id=id,sum=str(total),residual=str(total-1)))
            layout.append(dict(id=id,depth=depth,children=[b['to'] for b in branches]))
            for i,b in enumerate(branches):
                step=dict(node_id=id,stage_id=r['stage'],branch_id=b['id'],label=b['label'],context=r['context'])
                if quantitative:step.update(probability=str(values[i]),source=b['source'])
                visit(b['to'],depth+1,path+[step],mass*values[i] if quantitative else None,id)
        active.remove(id)
    visit(root,0,[],Decimal(1) if quantitative else None)
    need(seen==set(nodes),'unreachable node definitions: '+','.join(sorted(set(nodes)-seen)))
    need(used_outcomes==set(omap),'unused outcome definitions: '+','.join(sorted(set(omap)-used_outcomes)))
    aggregates=[]
    for r in outcomes:
        selected=[s for s in sequences if s['outcome_id']==r['id']];item=dict(id=r['id'],label=r['label'],sequence_ids=[s['id'] for s in selected])
        if quantitative:
            p=sum((Decimal(s['conditional_probability']) for s in selected),Decimal(0));item['conditional_probability']=str(p)
            if rate is not None:item['frequency']=str(p*rate);item['frequency_unit']=unit
        aggregates.append(item)
    result=dict(mode=mode,sequences=sequences,outcomes=aggregates,branch_sum_checks=checks,layout=layout,
        interpretation='Branches are conditional on the initiating event and entire preceding path. Multiplication uses the chain rule, not an independence assumption. Outcome aggregation assumes the declared branches form disjoint exhaustive partitions.')
    if quantitative:
        total=sum((Decimal(s['conditional_probability']) for s in sequences),Decimal(0));need(abs(total-1)<=Decimal('1e-10'),'terminal probability mass not conserved')
        result['terminal_probability_sum']=str(total)
        if rate is not None:result['total_frequency']=str(total*rate);result['frequency_unit']=unit
    return result


def fmt(value):return format(Decimal(value),'.5g')

def build(d,theme='editorial-warm'):
    a=analyze(d);nodes={r['id']:r for r in d['nodes']};n=len(d['stages']);quant=d['mode']!='qualitative'
    pitch=336;xfirst=340;outx=xfirst+n*pitch+34;outw=370;width=outx+outw+64;rowh=116;y0=340
    leaves={s['id']:i for i,s in enumerate(a['sequences'])};positions={}
    def place(id,depth):
        r=nodes[id]
        if r['kind']=='terminal':cy=y0+leaves[id]*rowh;positions[id]=(outx,cy);return cy
        yy=[place(b['to'],depth+1) for b in r['branches']];cy=(yy[0]+yy[-1])/2;positions[id]=(xfirst+depth*pitch,cy);return cy
    rooty=place(d['root'],0);bottom=y0+len(leaves)*rowh
    s=Scene(dict(width=width,height=bottom+270+len(a['outcomes'])*44,title=d['title'],subtitle=d['scope'],eyebrow='EVENT TREE / 从初始事件前推结果',footer=d['data_status']+' · 条件分支与互斥完备性为输入前提；不构成现场风险认定'),theme)
    for i,st in enumerate(d['stages']):
        s.add(xfirst+i*pitch-55,205,pitch-36,74,f"{i+1:02}  {st['label']}",id='stage-'+st['id'],fs=20,fill='panel',tone='ink',radius=0,check=True)
    s.text(outx,223,outw,43,'路径终点 / 结果',size=23)
    initial=d['initiator']['label']
    if d['mode']=='frequency':initial+='\n'+str(d['initiator']['frequency']['value'])+' '+d['initiator']['frequency']['unit']
    s.add(64,rooty-54,208,108,initial,id='initiator',fs=19,fill='tint',tone='ink',radius=0,check=True)
    for id,(x,y) in positions.items():
        r=nodes[id]
        if r['kind']=='decision':
            s.add(x-5,y-5,10,10,'',kind='ellipse',id='node-'+id,fill='ink',tone='ink',check=True)
            s.text(x-30,y+14,90,26,id,size=13,tone='muted')
        else:
            item=a['sequences'][leaves[id]];label=id+' · '+item['outcome']
            detail=('P(路径 | 初始事件) = '+fmt(item['conditional_probability'])) if quant else '定性路径 · 未输入概率'
            if 'frequency' in item:detail+='\n频度 '+fmt(item['frequency'])+' '+item['frequency_unit']
            s.add(x,y-47,outw,94,label,detail,id='terminal-'+id,fs=18,dfs=15,fill='panel',tone='ink',radius=0,check=True)
    s.edge('initiator','node-'+d['root'],points=[(272,rooty),(xfirst-5,rooty)],source_port='right',target_port='left',arrow=False,tone='ink')
    for id,(x,y) in positions.items():
        r=nodes[id]
        if r['kind']=='terminal':continue
        for b in r['branches']:
            tx,ty=positions[b['to']];target='terminal-'+b['to'] if nodes[b['to']]['kind']=='terminal' else 'node-'+b['to']
            s.edge('node-'+id,target,points=[(x+5,y),(x+65,y),(x+65,ty),(tx if nodes[b['to']]['kind']=='terminal' else tx-5,ty)],source_port='right',target_port='left',arrow=False,tone='ink')
            label=b['label']+('  p='+fmt(str(b['probability'])) if quant else '')
            s.text(x+80,ty-42,pitch-100,37,label,size=16,tone='accent')
    sy=bottom+20;s.text(64,sy,width-128,36,'结果归并 · 同类结果的互斥路径相加',size=23);sy+=47
    for o in a['outcomes']:
        value='P = '+fmt(o['conditional_probability']) if quant else str(len(o['sequence_ids']))+' 条定性路径'
        if 'frequency' in o:value+='；频度 '+fmt(o['frequency'])+' '+o['frequency_unit']
        s.text(64,sy,width-128,35,o['id']+'  '+o['label']+'  ·  '+value,size=18);sy+=43
    s.text(64,sy+8,width-128,42,'分支概率均以初始事件及之前全部路径为条件；相乘不要求无条件独立。提前终止的理由与跳过阶段保存在分析JSON。' if quant else '定性模式保留路径与终止理由，不生成概率或频度。提前终止不表示后续屏障一定成功。',size=16,tone='muted')
    s.meta.update(analysis=a,source_input=d);s.finish();return s,a


def render_file(source,out,theme='editorial-warm'):
    d=json.loads(Path(source).read_text());s,a=build(d,theme);qa=audit(s);need(not qa['errors'] and not qa['warnings'],'layout failure: '+repr(qa))
    out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=Path(source).stem
    for ext,value in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('analysis.json',json.dumps(a,ensure_ascii=False,indent=2)),('qa.json',json.dumps(qa,ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))]:(out/(stem+'.'+ext)).write_text(value)
    with (out/(stem+'.csv')).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['sequence_id','outcome_id','path','conditional_probability','frequency','frequency_unit','termination_reason','skipped_stages'])
        for seq in a['sequences']:w.writerow([seq['id'],seq['outcome_id'],' / '.join(t['stage_id']+':'+t['branch_id'] for t in seq['path']),seq.get('conditional_probability',''),seq.get('frequency',''),seq.get('frequency_unit',''),seq['termination_reason'],' / '.join(seq['skipped_stages'])])
    return a

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--theme',default='editorial-warm');args=p.parse_args();print(json.dumps(render_file(args.input,args.out,args.theme),ensure_ascii=False))
