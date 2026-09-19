#!/usr/bin/env python3
"""Explicit classic House of Quality; no inferred VOC or roof-adjusted scores."""
import argparse,csv,json,math,re
from pathlib import Path
from render import Scene,need,finite,wrap,audit,svg,drawio


def text(value,name):
    need(isinstance(value,str) and value.strip(),name+' must be nonempty text')
    return value


def analyze(d):
    for key in ('title','scope','data_status','weight_basis','relationship_basis','roof_basis'):
        text(d.get(key),key)
    need(d.get('method')=='classic_weighted_sum_0139','explicit method classic_weighted_sum_0139 required')
    req=d.get('requirements');tech=d.get('technical')
    need(isinstance(req,list) and 1<=len(req)<=20,'1..20 requirements required')
    need(isinstance(tech,list) and 2<=len(tech)<=12,'2..12 technical characteristics required')
    seen=set()
    for kind,rows in [('requirement',req),('technical',tech)]:
        for row in rows:
            need(isinstance(row,dict),kind+' must be an object')
            ident=row.get('id');need(isinstance(ident,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,19}',ident),'stable ASCII ID required')
            need(ident not in seen,'duplicate ID: '+ident);seen.add(ident)
            text(row.get('label'),kind+' label');text(row.get('source'),kind+' source')
            if kind=='requirement':
                need(finite(row.get('weight')) and row['weight']>=0,'weight must be finite and nonnegative')
            else:
                need(row.get('direction') in ('min','max','target'),'technical direction must be min/max/target')
                need(finite(row.get('target')),'numeric target required');text(row.get('unit'),'unit')
    weights=[r['weight'] for r in req];total=math.fsum(weights)
    need(math.isfinite(total) and total>0,'positive finite total weight required')
    matrix=d.get('relationships')
    need(isinstance(matrix,list) and len(matrix)==len(req),'relationship row count mismatch')
    for row in matrix:
        need(isinstance(row,list) and len(row)==len(tech),'relationship column count mismatch')
        need(all(finite(v) and v in (0,1,3,9) for v in row),'every relationship must explicitly be 0,1,3,9; unknown is not zero')
    # Normalize first to avoid overflowing scores when raw elicited weights are large.
    norm=[w/total for w in weights]
    score=[math.fsum(norm[i]*matrix[i][j] for i in range(len(req))) for j in range(len(tech))]
    score_total=math.fsum(score);need(score_total>0,'no weighted relationships; priorities undefined')
    relative=[v/score_total for v in score]
    roof=d.get('roof');need(isinstance(roof,list),'roof must list every unordered technical pair; null means unassessed')
    tid=[t['id'] for t in tech];roofmap={}
    for pair in roof:
        need(isinstance(pair,dict),'roof pair must be an object')
        left,right=pair.get('a'),pair.get('b')
        need(left in tid and right in tid and left!=right,'invalid roof endpoints')
        key=tuple(sorted((left,right)));need(key not in roofmap,'duplicate roof pair')
        value=pair.get('value');need('value' in pair and (value is None or (finite(value) and value in (-2,-1,0,1,2))),'roof value must be -2,-1,0,1,2,null')
        roofmap[key]=value
    need(len(roofmap)==len(tech)*(len(tech)-1)//2,'roof must explicitly cover every technical pair')
    benchmark=d.get('benchmark')
    if benchmark is not None:
        need(isinstance(benchmark,dict),'benchmark must be an object')
        text(benchmark.get('basis'),'benchmark basis')
        need(benchmark.get('direction')=='higher_is_better','customer benchmark direction must be higher_is_better')
        scale=benchmark.get('scale');need(isinstance(scale,list) and len(scale)==2 and all(finite(v) for v in scale) and scale[0]<scale[1],'valid benchmark scale required')
        columns=benchmark.get('alternatives');need(isinstance(columns,list) and 1<=len(columns)<=4,'1..4 benchmark alternatives')
        names=set()
        for col in columns:
            label=text(col.get('label'),'benchmark label');need(label not in names,'duplicate benchmark alternative');names.add(label)
            values=col.get('scores');need(isinstance(values,list) and len(values)==len(req),'benchmark row count mismatch')
            need(all(v is None or (finite(v) and scale[0]<=v<=scale[1]) for v in values),'benchmark outside stated scale')
    warnings=[]
    for i,r in enumerate(req):
        if not any(matrix[i]):warnings.append('unmapped requirement: '+r['id'])
    for j,t in enumerate(tech):
        if not any(row[j] for row in matrix):warnings.append('unmapped technical characteristic: '+t['id'])
    if any(v is None for v in roofmap.values()):warnings.append('roof contains unassessed pairs; priorities do not incorporate roof')
    return dict(method=d['method'],requirement_ids=[r['id'] for r in req],technical_ids=tid,
        normalized_requirement_weights=norm,technical_scores=score,technical_shares=relative,
        ranks=[1+sum(v>x and not math.isclose(v,x,rel_tol=1e-12,abs_tol=1e-12) for v in score) for x in score],
        contributions=[[norm[i]*v for v in row] for i,row in enumerate(matrix)],
        roof=[dict(a=key[0],b=key[1],value=value) for key,value in sorted(roofmap.items())],warnings=warnings,
        interpretation='Scores are a declared decision heuristic, not causal effects, statistical correlations, or measured customer satisfaction. Roof and benchmark do not alter weighted scores.')


def build(d,theme='editorial-warm'):
    a=analyze(d);req=d['requirements'];tech=d['technical'];m=len(req);n=len(tech)
    cw=154;left=64;labelw=290;weightw=90;x0=left+labelw+weightw;mw=n*cw
    bench=d.get('benchmark');bw=116;extra=(len(bench['alternatives'])*bw if bench else 0)
    width=x0+mw+extra+64;roofbottom=max(480,220+mw/2)
    headh=max(132,max(50+len(wrap(t['label'],cw-28,18))*25 for t in tech))
    rowh=max(62,max(24+len(wrap(r['id']+' '+r['label'],labelw-28,18))*25 for r in req))
    y0=roofbottom+headh;bottom=y0+m*rowh
    s=Scene(dict(width=width,height=bottom+475,title=d['title'],subtitle=d['scope'],eyebrow='HOUSE OF QUALITY / 需求到技术',footer=d['data_status']+' · 关系与权重为明确输入；非因果验证或完整QFD认证'),theme)
    # Roof is an upper triangular pairwise map. Numeric symbols retain meaning in monochrome.
    s.add(x0,roofbottom-mw/2,mw,mw/2,kind='polygon',points=[(x0,roofbottom),(x0+mw/2,roofbottom-mw/2),(x0+mw,roofbottom)],fill='panel',tone='ink',check=False,id='roof-frame')
    roof={frozenset((p['a'],p['b'])):p['value'] for p in a['roof']}
    for i in range(n):
        for j in range(i+1,n):
            cx=x0+(i+j+1)*cw/2;cy=roofbottom-(j-i)*cw/2;r=cw/2
            val=roof[frozenset((tech[i]['id'],tech[j]['id']))]
            s.add(cx-r,cy-r,2*r,2*r,kind='polygon',points=[(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy)],fill='panel',tone='ink',check=False,id=f'roof-{i}-{j}')
            s.text(cx-r*.65,cy-27,r*1.3,29,'?' if val is None else f'{val:+g}' if val else '0',size=22,align='center',tone='accent' if val and val<0 else 'ink',id=f'roof-value-{i}-{j}')
            # Pair identity lives in scene metadata and a separate pair table to avoid tiny IDs.
    s.text(left,240,labelw+weightw-26,44,'屋顶：改进方向之间的协同／冲突',size=22)
    s.text(left,300,labelw+weightw-26,142,'+2 强协同  +1 协同\n−1 冲突  −2 强冲突\n0 已评估无关联  ? 尚未评估\n不是原始测量值的相关系数',size=17,tone='muted')
    def cell(x,y,w,h,label,id,fs=18,fill='panel',tone='ink'):
        s.add(x,y,w,h,label,id=id,fs=fs,kind='rect',fill=fill,tone=tone,radius=0,check=True)
    cell(left,roofbottom,labelw,headh,'客户／内部使用者需求','requirements-heading',20)
    cell(left+labelw,roofbottom,weightw,headh,'权重\n占比','weights-heading',18)
    directions={'min':'越小越好','max':'越大越好','target':'趋近目标'}
    for j,t in enumerate(tech):cell(x0+j*cw,roofbottom,cw,headh,t['id']+'\n'+t['label']+'\n'+directions[t['direction']],f'tech-{j}',18)
    if bench:
        for k,b in enumerate(bench['alternatives']):cell(x0+mw+k*bw,roofbottom,bw,headh,b['label']+'\n需求评分',f'bench-head-{k}',17)
    for i,r in enumerate(req):
        y=y0+i*rowh;cell(left,y,labelw,rowh,r['id']+' '+r['label'],f'req-{i}',18)
        cell(left+labelw,y,weightw,rowh,f"{a['normalized_requirement_weights'][i]*100:.1f}%",f'weight-{i}',18)
        for j,v in enumerate(d['relationships'][i]):cell(x0+j*cw,y,cw,rowh,str(v),f'rel-{i}-{j}',23,fill='tint' if v==9 else 'panel',tone='accent' if v==9 else 'ink')
        if bench:
            for k,b in enumerate(bench['alternatives']):cell(x0+mw+k*bw,y,bw,rowh,'?' if b['scores'][i] is None else str(b['scores'][i]),f'bench-{i}-{k}',19)
    labels=['技术目标','加权得分','技术占比','优先序号']
    for k,label in enumerate(labels):
        y=bottom+k*55;cell(left,y,labelw+weightw,55,label,f'result-label-{k}',18)
        for j,t in enumerate(tech):
            values=[f"{t['target']:g} {t['unit']}",f"{a['technical_scores'][j]:.4g}",f"{a['technical_shares'][j]*100:.1f}%",str(a['ranks'][j])]
            cell(x0+j*cw,y,cw,55,values[k],f'result-{k}-{j}',18)
    note_y=bottom+240
    notes=['关系：0 无关联 · 1 弱 · 3 中 · 9 强。空缺必须补评，不能自动当作0。',
           '得分 = Σ(需求权重占比 × 关系分值)；技术占比按得分归一化。屋顶与对标不加入计算。',
           '输入依据：'+d['weight_basis']+'；'+d['relationship_basis']]
    if bench:notes.append('需求对标：'+str(bench['scale'])+'，越高越好；'+bench['basis'])
    if a['warnings']:notes.append('待核对：'+'；'.join(a['warnings']))
    for note in notes:
        h=max(30,len(wrap(note,width-128,16))*23);s.text(left,note_y,width-128,h,note,size=16,tone='muted');note_y+=h+8
    s.meta.update(analysis=a,roof_pairs=a['roof'],technical_targets=tech,source_input=d);s.finish();return s,a


def render_file(source,out,theme='editorial-warm'):
    d=json.loads(Path(source).read_text());s,a=build(d,theme);qa=audit(s)
    need(not qa['errors'] and not qa['warnings'],'layout failure: '+repr(qa))
    out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=Path(source).stem
    for suffix,content in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('analysis.json',json.dumps(a,ensure_ascii=False,indent=2)),('qa.json',json.dumps(qa,ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))]:
        (out/f'{stem}.{suffix}').write_text(content)
    with (out/f'{stem}.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['technical_id','label','target','unit','direction','weighted_score','share','rank'])
        for j,t in enumerate(d['technical']):w.writerow([t['id'],t['label'],t['target'],t['unit'],t['direction'],a['technical_scores'][j],a['technical_shares'][j],a['ranks'][j]])
    return a

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--theme',default='editorial-warm');args=p.parse_args();print(json.dumps(render_file(args.input,args.out,args.theme),ensure_ascii=False))
