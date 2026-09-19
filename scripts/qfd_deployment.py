#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Explicit ordered QFD matrices with ID-based carry and original-need traceability."""
import argparse,copy,csv,html,json,math,re
from pathlib import Path
import xml.etree.ElementTree as ET
from render import Scene,need,finite,wrap,audit,svg,drawio


def nonempty(v,name):
    need(isinstance(v,str) and v.strip(),name+' required')
    return v


def ident(v):
    need(isinstance(v,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',v),'stable ASCII ID required')
    return v


def normalize(values,context):
    need(values and all(finite(v) and v>=0 for v in values),context+': nonnegative finite weights required')
    maximum=max(values);need(maximum>0,context+': positive total required')
    scaled=[v/maximum for v in values];total=math.fsum(scaled)
    return [v/total for v in scaled]


def analyze(d):
    need(isinstance(d,dict),'input must be an object')
    for k in ('title','scope','data_status','method_basis'):nonempty(d.get(k),k)
    need(d.get('method')=='classic_weighted_sum_0139','explicit classic_weighted_sum_0139 method required')
    stages=d.get('stages');need(isinstance(stages,list) and 2<=len(stages)<=8,'2..8 ordered stages required')
    result=[];seen=set();stageids=set();roots=[];previous=None
    for index,stage in enumerate(stages):
        need(isinstance(stage,dict),'stage must be an object');sid=ident(stage.get('id'))
        need(sid not in stageids,'duplicate stage ID');need(sid not in ('overview','deployment','priorities','origin-trace'),'reserved output filename: '+sid);stageids.add(sid)
        for k in ('title','input_kind','output_kind','relationship_basis'):nonempty(stage.get(k),k)
        discarded=[];retained=1.0
        if index==0:
            for k in ('input_ids','carry_mode','excluded'):need(k not in stage,'first stage cannot carry upstream outputs')
            nonempty(stage.get('weight_basis'),'first-stage weight_basis')
            inputs=stage.get('inputs');need(isinstance(inputs,list) and 1<=len(inputs)<=20,'1..20 initial inputs required')
            for r in inputs:
                need(isinstance(r,dict),'initial input must be an object');rid=ident(r.get('id'))
                need(rid not in seen,'duplicate item ID');seen.add(rid)
                nonempty(r.get('label'),'initial input label');nonempty(r.get('source'),'initial input source')
            weights=normalize([r.get('weight') for r in inputs],'initial inputs');roots=[r['id'] for r in inputs]
            origins=[[weights[i] if k==i else 0.0 for i in range(len(inputs))] for k in range(len(roots))]
            basis=stage['weight_basis']
        else:
            need('inputs' not in stage and 'weight_basis' not in stage,'downstream weights and labels are inherited; do not override with inputs/weight_basis')
            ids=stage.get('input_ids');need(isinstance(ids,list) and 1<=len(ids)<=20 and all(isinstance(v,str) for v in ids),'explicit input_ids required')
            need(len(ids)==len(set(ids)),'duplicate carried input ID')
            old={r['id']:j for j,r in enumerate(previous['outputs'])}
            need(set(ids)<=set(old),'carried ID not found in immediately previous stage')
            excluded=stage.get('excluded',[]);need(isinstance(excluded,list),'excluded must be a list')
            excluded_ids=[]
            for row in excluded:
                need(isinstance(row,dict),'excluded entry must be an object');eid=row.get('id')
                need(eid in old,'unknown excluded ID');nonempty(row.get('reason'),'exclusion reason');excluded_ids.append(eid)
                discarded.append(dict(id=eid,reason=row['reason'],share=previous['shares'][old[eid]]))
            need(len(excluded_ids)==len(set(excluded_ids)),'duplicate excluded ID')
            need(not set(ids)&set(excluded_ids),'carried and excluded IDs overlap')
            need(set(ids)|set(excluded_ids)==set(old),'every upstream output must be carried or explicitly excluded')
            mode=stage.get('carry_mode');need(mode in ('full','subset_renormalize'),'explicit carry_mode full/subset_renormalize required')
            need((mode=='full' and not excluded) or (mode=='subset_renormalize' and bool(excluded)),'carry_mode and exclusions disagree')
            inputs=[copy.deepcopy(previous['outputs'][old[rid]]) for rid in ids]
            retained=math.fsum(previous['shares'][old[rid]] for rid in ids);need(retained>0,'selected upstream outputs carry zero priority')
            weights=[previous['shares'][old[rid]]/retained for rid in ids]
            origins=[[previous['origin_shares'][k][old[rid]]/retained for rid in ids] for k in range(len(roots))]
            basis='Inherited from '+previous['id']+' by stable ID; retained share '+format(retained,'.12g')+'; '+mode
        outputs=stage.get('outputs');need(isinstance(outputs,list) and 1<=len(outputs)<=20,'1..20 outputs required')
        for r in outputs:
            need(isinstance(r,dict),'output must be an object');rid=ident(r.get('id'))
            need(rid not in seen,'output ID must be globally unique: '+rid);seen.add(rid)
            for k in ('label','source','unit','owner'):nonempty(r.get(k),'output '+k)
            need(r.get('direction') in ('min','max','target'),'output direction min/max/target required')
            need(finite(r.get('target')),'finite numeric output target required')
        matrix=stage.get('relationships')
        need(isinstance(matrix,list) and len(matrix)==len(inputs),'matrix row count must match explicit input order')
        for row in matrix:
            need(isinstance(row,list) and len(row)==len(outputs),'matrix column count must match output order')
            need(all(finite(v) and v in (0,1,3,9) for v in row),'relationship cells must explicitly be 0,1,3,9; missing is not zero')
        contributions=[[weights[i]*v for v in row] for i,row in enumerate(matrix)]
        scores=[math.fsum(row[j] for row in contributions) for j in range(len(outputs))]
        total=math.fsum(scores);need(total>0,'stage has no weighted relationships: '+sid)
        shares=[v/total for v in scores]
        origin_shares=[[math.fsum(origins[k][i]*matrix[i][j] for i in range(len(inputs)))/total for j in range(len(outputs))] for k in range(len(roots))]
        warnings=[]
        for i,row in enumerate(matrix):
            if not any(row):warnings.append('Unmapped input '+inputs[i]['id'])
        for j,r in enumerate(outputs):
            if not any(row[j] for row in matrix):warnings.append('Unmapped output '+r['id'])
        ranks=[1+sum(v>x and not math.isclose(v,x,rel_tol=1e-12,abs_tol=1e-12) for v in scores) for x in scores]
        previous=dict(id=sid,title=stage['title'],input_kind=stage['input_kind'],output_kind=stage['output_kind'],
            inputs=copy.deepcopy(inputs),outputs=copy.deepcopy(outputs),input_weights=weights,relationships=copy.deepcopy(matrix),
            contributions=contributions,scores=scores,shares=shares,ranks=ranks,original_input_ids=roots,origin_shares=origin_shares,
            retained_upstream_share=retained,excluded=discarded,weight_basis=basis,relationship_basis=stage['relationship_basis'],warnings=warnings)
        result.append(previous)
    return dict(method=d['method'],stages=result,original_input_ids=roots,
        interpretation='Chained classic decision-priority matrices, not causal probabilities or proof of engineering feasibility. Each normalization and explicit exclusion is recorded. More linked outputs can amplify a need under this method.')


def build_stage(d,a,index,theme='editorial-warm'):
    rows=a['inputs'];cols=a['outputs'];n=len(cols);left=64;labelw=330;ww=106;cw=164;x0=left+labelw+ww
    width=x0+n*cw+64;y0=300
    hh=max(132,max(55+25*len(wrap(t['label'],cw-26,18)) for t in cols))
    rh=max(66,max(24+25*len(wrap(t['id']+' '+t['label'],labelw-26,18)) for t in rows))
    bottom=y0+hh+rh*len(rows)
    s=Scene(dict(width=width,height=bottom+430,title=f"{index+1:02} · {a['title']}",subtitle=a['input_kind']+' → '+a['output_kind'],eyebrow='QFD DEPLOYMENT / 阶段 '+a['id'],footer=d['data_status']+' · 输入与目标为声明数据；非工程可行性证明'),theme)
    message=('首次输入权重归一化' if index==0 else '按上一阶段输出ID继承权重；保留 '+f"{a['retained_upstream_share']*100:.2f}%"+' 的优先级份额')
    s.text(left,195,width-128,40,message,size=20,tone='accent')
    s.text(left,242,width-128,35,'0 无关联 · 1 弱 · 3 中 · 9 强；未知关系须补评。各阶段均采用经典加权和。',size=17,tone='muted')
    def cell(x,y,w,h,label,id,fs=18,fill='panel'):
        s.add(x,y,w,h,label,id=id,fs=fs,fill=fill,tone='ink',radius=0,check=True)
    cell(left,y0,labelw,hh,a['input_kind'],'input-heading',20);cell(left+labelw,y0,ww,hh,'输入权重','weight-heading',18)
    directions={'min':'越小越好','max':'越大越好','target':'趋近目标'}
    for j,r in enumerate(cols):cell(x0+j*cw,y0,cw,hh,r['id']+'\n'+r['label']+'\n'+directions[r['direction']],f'output-{j}',18)
    for i,r in enumerate(rows):
        y=y0+hh+i*rh;cell(left,y,labelw,rh,r['id']+' '+r['label'],f'input-{i}')
        cell(left+labelw,y,ww,rh,f"{a['input_weights'][i]*100:.2f}%",f'weight-{i}')
        for j,v in enumerate(a['relationships'][i]):cell(x0+j*cw,y,cw,rh,str(v),f'rel-{i}-{j}',22,'tint' if v==9 else 'panel')
    for k,label in enumerate(['目标与单位','加权得分','输出优先级','优先序号','责任角色']):
        y=bottom+k*56;cell(left,y,labelw+ww,56,label,f'result-label-{k}')
        for j,r in enumerate(cols):
            values=[f"{r['target']:g} {r['unit']}",f"{a['scores'][j]:.5g}",f"{a['shares'][j]*100:.2f}%",str(a['ranks'][j]),r['owner']]
            cell(x0+j*cw,y,cw,56,values[k],f'result-{k}-{j}',17)
    y=bottom+300
    notes=['下一阶段按ID传递未舍入优先级；排除项需说明原因，保留项重新归一化。', '关系依据：'+a['relationship_basis']]
    if a['excluded']:notes.append('已排除：'+'；'.join(r['id']+' ('+f"{r['share']*100:.2f}%"+') '+r['reason'] for r in a['excluded']))
    if a['warnings']:notes.append('待评审：'+'；'.join(a['warnings']))
    for note in notes:
        h=max(32,len(wrap(note,width-128,16))*24);s.text(left,y,width-128,h,note,size=16,tone='muted');y+=h+9
    s.meta.update(stage_analysis=a,source_input=d);s.finish();return s


def build_overview(d,a,theme='editorial-warm'):
    width=1560;s=Scene(dict(width=width,height=300+len(a['stages'])*245,title=d['title'],subtitle=d['scope'],eyebrow='QFD / 多阶段优先级追踪',footer=d['data_status']+' · 阶段矩阵与原始需求贡献可独立复算'),theme)
    y=200
    for i,r in enumerate(a['stages']):
        h=190;s.add(64,y,width-128,h,kind='panel',check=False)
        s.text(88,y+20,340,70,f"{i+1:02}  {r['title']}",size=25)
        s.text(88,y+100,340,55,r['input_kind']+' → '+r['output_kind'],size=17,tone='muted')
        order=sorted(range(len(r['outputs'])),key=lambda j:-r['shares'][j])[:3]
        s.text(460,y+16,960,32,'本阶段前三项优先级（完整结果见阶段矩阵）',size=18,tone='muted')
        for k,j in enumerate(order):s.text(460,y+56+k*35,960,32,f"{r['outputs'][j]['id']}  {r['outputs'][j]['label']}    {r['shares'][j]*100:.2f}%",size=20)
        if i<len(a['stages'])-1:
            nxt=a['stages'][i+1];s.edge(points=[(236,y+h),(236,y+h+49)],arrow=True,tone='accent')
            s.text(275,y+h+8,1100,33,'按ID继承 · 下阶段保留 '+f"{nxt['retained_upstream_share']*100:.2f}%"+' · 排除 '+str(len(nxt['excluded']))+' 项',size=16,tone='muted')
        y+=245
    s.meta.update(analysis=a);s.finish();return s


def write_scene(s,path):
    qa=audit(s);need(not qa['errors'] and not qa['warnings'],'layout audit failed: '+repr(qa))
    path.with_suffix('.svg').write_text(svg(s));path.with_suffix('.drawio').write_text(drawio(s))
    path.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    path.with_suffix('.scene.json').write_text(json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))


def render_file(source,out,theme='editorial-warm'):
    d=json.loads(Path(source).read_text());a=analyze(d);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    combined=ET.Element('mxfile',host='diagram-studio',version='1.0')
    overview=build_overview(d,a,theme);write_scene(overview,out/'overview')
    scenes=[('overview',overview)]+[(r['id'],build_stage(d,r,i,theme)) for i,r in enumerate(a['stages'])]
    for name,s in scenes:
        if name!='overview':write_scene(s,out/name)
        diagram=ET.fromstring(drawio(s)).find('diagram');diagram.set('id',name);diagram.set('name',s.spec['title']);combined.append(diagram)
    (out/'deployment.drawio').write_text(ET.tostring(combined,encoding='unicode',xml_declaration=True))
    (out/'deployment.input.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(out/'deployment.analysis.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
    with (out/'priorities.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['stage_id','output_id','label','score','share','rank','target','unit','owner'])
        for r in a['stages']:
            for j,t in enumerate(r['outputs']):w.writerow([r['id'],t['id'],t['label'],r['scores'][j],r['shares'][j],r['ranks'][j],t['target'],t['unit'],t['owner']])
    with (out/'origin-trace.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['stage_id','original_input_id','output_id','priority_contribution'])
        for r in a['stages']:
            for k,root in enumerate(a['original_input_ids']):
                for j,t in enumerate(r['outputs']):w.writerow([r['id'],root,t['id'],r['origin_shares'][k][j]])
    return a

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--theme',default='editorial-warm');args=p.parse_args();print(json.dumps(render_file(args.input,args.out,args.theme),ensure_ascii=False))
