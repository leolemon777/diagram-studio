#!/usr/bin/env python3
"""Boolean ladder diagrams and explicit sequential scans; not a PLC compiler."""
import argparse, csv, json, math, re
from pathlib import Path
from render import Scene, need, wrap, audit, svg, drawio
import ladder_blocks as fb
import ctud


def obj(x, required, optional=()):
    need(isinstance(x, dict), 'object required')
    need(set(required) <= set(x), 'missing fields: '+str(set(required)-set(x)))
    need(set(x) <= set(required)|set(optional), 'unsupported fields: '+str(set(x)-set(required)-set(optional)))


def txt(x):
    need(isinstance(x,str) and x.strip(), 'nonempty text required'); return x


def ident(x):
    need(isinstance(x,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,23}',x), 'ASCII identifier up to 24 characters required'); return x


def validate(d):
    obj(d, ('title','scope','data_status','semantics','write_policy','variables','rungs','scans'))
    for k in ('title','scope','data_status'): txt(d[k])
    need(d['semantics'] in ('sequential_boolean_scan','sequential_timed_scan'), 'explicit Boolean or timed scan semantics required')
    timed=d['semantics']=='sequential_timed_scan'
    need(d['write_policy'] in ('single_writer','ordered_last_write'), 'explicit write_policy required')
    need(isinstance(d['variables'],list) and 1<=len(d['variables'])<=64, '1..64 variables required')
    variables={}
    for v in d['variables']:
        obj(v,('id','label','role','source'),('initial',))
        ident(v['id']);txt(v['label']);txt(v['source'])
        need(v['id'] not in variables, 'duplicate variable')
        need(v['role'] in ('input','memory','output'), 'invalid role')
        if v['role']=='input': need('initial' not in v,'input values belong to complete scan snapshots')
        else: need(type(v.get('initial')) is bool,'explicit Boolean initial value required')
        variables[v['id']]=v
    need(isinstance(d['rungs'],list) and 1<=len(d['rungs'])<=32, '1..32 ordered rungs required')
    ids=set();contacts=[];writers={}
    def unique(x):
        ident(x);need(x not in ids,'duplicate element/rung ID');ids.add(x)
    def walk(e,depth=0):
        need(isinstance(e,dict), 'expression object required')
        need(depth<=8, 'expression nesting exceeds 8')
        kind=e.get('kind')
        if kind=='contact':
            obj(e,('id','kind','var','sense'));unique(e['id'])
            need(e['var'] in variables,'undeclared contact variable')
            need(e['sense'] in ('true','false'),'contact sense must be true or false')
            contacts.append(e);need(len(contacts)<=120,'more than 120 contacts')
        else:
            obj(e,('id','kind','children'));unique(e['id'])
            need(kind in ('series','parallel'),'unsupported logic element')
            need(isinstance(e['children'],list) and 2<=len(e['children'])<=8,'series/parallel requires 2..8 children')
            for c in e['children']:walk(c,depth+1)
    for r in d['rungs']:
        if r.get('type')=='CTUD':
            obj(r,('id','label','type','profile','cu','cd','reset','load','pv','initial','outputs'))
            unique(r['id']);txt(r['label']);need(timed,'CTUD requires timed scans')
            need(r['profile']=='edge_int16_sample_every_call','explicit CTUD profile required')
            for k in ('cu','cd','reset','load'):walk(r[k])
            ctud.integer(r['pv'])
            need(isinstance(r['initial'],dict) and set(r['initial'])=={'cv','previous_cu','previous_cd'},'CTUD initial state required')
            ctud.initialize(**r['initial'])
            obj(r['outputs'],('qu','qd'));need(r['outputs']['qu']!=r['outputs']['qd'],'CTUD outputs must target distinct variables')
            for target in r['outputs'].values():
                need(target in variables and variables[target]['role']!='input','CTUD output must be writable')
                writers.setdefault(target,[]).append(r['id'])
            continue
        obj(r,('id','label','logic','coil'),('block',));unique(r['id']);txt(r['label']);walk(r['logic'])
        if 'block' in r:
            need(timed,'stateful block requires sequential_timed_scan')
            fb.validate_block(r['block'],variables);unique(r['block']['id'])
        c=r['coil'];obj(c,('id','var','kind'));unique(c['id'])
        need(c['var'] in variables and variables[c['var']]['role']!='input','coil must target writable declared variable')
        need(c['kind'] in ('assign','negated','set','reset'),'unsupported coil type')
        writers.setdefault(c['var'],[]).append(r['id'])
    if d['write_policy']=='single_writer':need(all(len(x)==1 for x in writers.values()),'duplicate coil writes require ordered_last_write')
    need(all(v['role']=='input' or v['id'] in writers for v in variables.values()),'declared writable variable has no coil')
    need(isinstance(d['scans'],list) and 1<=len(d['scans'])<=1000,'1..1000 scans required')
    inputs={v['id'] for v in variables.values() if v['role']=='input'};stepids=set()
    previous_time=-1
    for step in d['scans']:
        obj(step,('id','label','inputs','time_ms') if timed else ('id','label','inputs'));ident(step['id']);txt(step['label'])
        need(step['id'] not in stepids,'duplicate scan ID');stepids.add(step['id'])
        if timed:
            fb.integer(step['time_ms'],2**53-1,'time_ms')
            need(step['time_ms']>previous_time,'scan time_ms must increase strictly');previous_time=step['time_ms']
        need(isinstance(step['inputs'],dict) and set(step['inputs'])==inputs,'every scan requires all input bits, no extra bits')
        need(all(type(x) is bool for x in step['inputs'].values()),'input bits must be Boolean; no coercion')
    return variables, writers


def evaluate(e, values, observed):
    if e['kind']=='contact':
        bit=values[e['var']];result=bit if e['sense']=='true' else not bit
        observed[e['id']]=dict(variable=e['var'],read_value=bit,condition=result)
        return result
    results=[evaluate(c,values,observed) for c in e['children']]
    return all(results) if e['kind']=='series' else any(results)


def analyze(d):
    variables,writers=validate(d)
    state={k:v['initial'] for k,v in variables.items() if v['role']!='input'};scans=[]
    blocks={r['block']['id']:fb.initialize(r['block']) for r in d['rungs'] if 'block' in r}
    blocks.update({r['id']:ctud.initialize(**r['initial']) for r in d['rungs'] if r.get('type')=='CTUD'})
    for step in d['scans']:
        state.update(step['inputs']);before=dict(state);trace=[]
        for r in d['rungs']:
            if r.get('type')=='CTUD':
                reads={};args={k:evaluate(r[k],state,reads) for k in ('cu','cd','reset','load')}
                result=ctud.step(blocks[r['id']],pv=r['pv'],**args);blocks[r['id']]=result['after']
                writes=[]
                for port,target in r['outputs'].items():
                    writes.append(dict(port=port,target=target,before=state[target],after=result[port]));state[target]=result[port]
                trace.append(dict(rung=r['id'],type='CTUD',contacts=reads,inputs=args,block=result,writes=writes))
                continue
            reads={};logic_power=evaluate(r['logic'],state,reads);power=logic_power;block_trace=None
            if 'block' in r:
                b=r['block'];block_trace=fb.call(b,blocks[b['id']],logic_power,state,step['time_ms']);power=block_trace['q']
            c=r['coil'];var=c['var'];old=state[var]
            if c['kind']=='assign':state[var]=power
            elif c['kind']=='negated':state[var]=not power
            elif power:state[var]=c['kind']=='set'
            trace.append(dict(rung=r['id'],power=power,contacts=reads,coil=c['id'],target=var,kind=c['kind'],before=old,after=state[var],write_performed=c['kind'] in ('assign','negated') or power))
            if block_trace is not None:trace[-1].update(logic_power=logic_power,block=block_trace)
        scans.append(dict(id=step['id'],label=step['label'],inputs=step['inputs'],before=before,rungs=trace,after=dict(state),outputs={k:state[k] for k,v in variables.items() if v['role']=='output'}))
        if d['semantics']=='sequential_timed_scan':scans[-1].update(time_ms=step['time_ms'],blocks={k:dict(v) for k,v in blocks.items()})
    return dict(semantics=d['semantics'],write_policy=d['write_policy'],writers=writers,scans=scans,
                notes=['Inputs sampled once per scan; rung writes immediately visible to later rungs; output image published after last rung.',
                       'Initial values apply only at model start; retained state between scans is not a claim of power-cycle retention.',
                       'Boolean contact negation is not a physical wiring or safety property.'])


def build(d,theme='editorial-warm'):
    a=analyze(d);variables={v['id']:v for v in d['variables']};sizes={}
    def measure(e):
        if e['kind']=='contact':
            label=variables[e['var']]['label'];w=230;h=max(140,2*(38+len(wrap(label,w-24,16))*23))
        else:
            wh=[measure(c) for c in e['children']]
            if e['kind']=='series':w=sum(x[0] for x in wh);h=max(x[1] for x in wh)
            else:w=max(x[0] for x in wh)+80;h=sum(x[1] for x in wh)+24*(len(wh)-1)
        sizes[e['id']]=(w,h);return w,h
    dimensions=[]
    for r in d['rungs']:
        if r.get('type')=='CTUD':
            wh=[measure(r[k]) for k in ('cu','cd','reset','load')]
            dimensions.append((max(w for w,h in wh),sum(h for w,h in wh)+90))
        else:dimensions.append(measure(r['logic']))
    width=max(1320,max(w+(500 if r.get('type')=='CTUD' else 360 if 'block' in r else 0) for r,(w,h) in zip(d['rungs'],dimensions))+570);right=width-100;coilx=right-170;y=240
    s=Scene(dict(width=width,height=900,title=d['title'],subtitle=d['scope'],eyebrow='LADDER / 布尔逻辑与逐扫描解释',footer=d['data_status']+' · 教学模型；非厂商编译程序、现场接线或安全回路'),theme)
    def line(points,width=2):s.edge(points=points,arrow=False,tone='ink',width=width)
    def text(x,y,w,h,value,id,size=16,tone='ink',align='center'):
        nid=s.text(x,y,w,h,value,size,tone,align=align,id=id);s.get(nid)['check']=True
    def junction(x,y):s.add(x-3,y-3,6,6,'',kind='ellipse',fill='ink',stroke='none',tone='ink',check=False)
    def draw(e,x,top,available=None):
        w,h=sizes[e['id']];w=available or w;cy=top+h/2
        if e['kind']=='contact':
            cx=x+w/2
            line([(x,cy),(cx-12,cy)]);line([(cx+12,cy),(x+w,cy)])
            line([(cx-12,cy-20),(cx-12,cy+20)]);line([(cx+12,cy-20),(cx+12,cy+20)])
            if e['sense']=='false':line([(cx-19,cy+23),(cx+19,cy-23)])
            text(x+8,cy-58,w-16,30,e['var'],e['id']+'-tag',18)
            text(x+12,cy+28,w-24,h/2-28,variables[e['var']]['label'],e['id']+'-label')
        elif e['kind']=='series':
            xx=x
            for c in e['children']:
                cw,ch=sizes[c['id']];draw(c,xx,top+(h-ch)/2);xx+=cw
            if xx<x+w:line([(xx,cy),(x+w,cy)])
        else:
            xx=x+32;end=x+w-32;ys=[];yy=top
            for c in e['children']:
                cw,ch=sizes[c['id']];childy=yy+ch/2;ys.append(childy)
                draw(c,xx,yy);line([(xx+cw,childy),(end,childy)]);yy+=ch+24
            line([(x,cy),(xx,cy)]);line([(end,cy),(x+w,cy)])
            line([(xx,min(ys+[cy])),(xx,max(ys+[cy]))]);line([(end,min(ys+[cy])),(end,max(ys+[cy]))])
            for yy in set(ys+[cy]):junction(xx,yy);junction(end,yy)
        return cy
    for i,(r,(w,h)) in enumerate(zip(d['rungs'],dimensions)):
        if r.get('type')=='CTUD':
            text(100,y,width-200,38,r['id']+' · '+r['label'],r['id']+'-title',20,'accent','left')
            top=y+65;bx=160+w+85;bw=280;yy=top;ports=[]
            for key in ('cu','cd','reset','load'):
                ew,eh=sizes[r[key]['id']];cy=draw(r[key],160,yy)
                line([(120,cy),(160,cy)]);line([(160+ew,cy),(bx,cy)])
                ports.append(cy)
                s.text(bx+12,cy-15,80,30,{'reset':'R','load':'LD'}.get(key,key.upper()),size=18)
                yy+=eh+30
            bottom=yy-30
            line([(120,top),(120,bottom)],3)
            s.add(bx,top-8,bw,bottom-top+16,id=r['id']+'-box',kind='rect',fill='none',tone='ink',check=False)
            s.text(bx+95,top+12,170,36,'CTUD',size=24)
            s.text(bx+95,top+55,170,80,'INT16\nPV = '+str(r['pv']),size=18)
            s.text(bx+95,bottom-95,170,75,'CV 初值 '+str(r['initial']['cv'])+'\n每扫描调用',size=16)
            for key,cy in zip(('qu','qd'),ports[:2]):
                s.text(bx+bw-62,cy-15,52,30,key.upper(),size=18)
                line([(bx+bw,cy),(coilx-24,cy)])
                for side in (-1,1):line([(coilx+side*(13+11*math.sin(math.pi*t/20)),cy-23+46*t/20) for t in range(21)])
                line([(coilx+24,cy),(right,cy)])
                text(coilx-85,cy-58,170,30,r['outputs'][key],r['id']+'-'+key+'-target',18)
            line([(right,ports[0]-35),(right,ports[1]+35)],3)
            y=bottom+65
            continue
        logic_h=h;h=max(h,230 if 'block' in r else h)
        heading=r['id']+' · '+r['label'];hh=max(38,len(wrap(heading,width-200,20))*29)
        text(100,y,width-200,hh,heading,r['id']+'-title',20,'accent','left');top=y+hh+18;cy=top+h/2
        line([(120,top-5),(120,top+h+5)],3);line([(right,top-5),(right,top+h+5)],3)
        line([(120,cy),(160,cy)]);draw(r['logic'],160,top+(h-logic_h)/2)
        if 'block' in r:
            b=r['block'];bx=160+w+40;bw=280
            s.add(bx,cy-84,bw,168,b['id']+' · '+b['type'],fb.label(b),id=b['id']+'-box',fs=21,fill='panel',tone='ink',radius=0,check=True)
            line([(160+w,cy),(bx,cy)]);line([(bx+bw,cy),(coilx-24,cy)])
        else:line([(160+w,cy),(coilx-24,cy)])
        line([(coilx+24,cy),(right,cy)])
        for side in (-1,1):
            line([(coilx+side*(13+11*math.sin(math.pi*t/20)),cy-23+46*t/20) for t in range(21)])
        c=r['coil'];marker={'assign':'','negated':'/','set':'S','reset':'R'}[c['kind']]
        if marker:text(coilx-10,cy-17,20,34,marker,c['id']+'-mode',20)
        text(coilx-122,cy-58,244,30,c['var'],c['id']+'-tag',18)
        label=variables[c['var']]['label'];lh=max(40,len(wrap(label,244,16))*23)
        text(coilx-122,cy+28,244,lh,label,c['id']+'-label')
        y=max(top+h,cy+28+lh)+42
    legend=['触点：| | 检查 TRUE；|/| 检查 FALSE。串联 = 与，并联 = 或；圆点表示连接。',
            '线圈：( ) 赋值；(/) 取反赋值；(S) 真时置位；(R) 真时复位。S/R 条件为假时保持原值。',
            '按图中梯级顺序执行，同一扫描内后级可读取前级写入值；全部输入在扫描开始时一次采样。',
            '写入策略：'+d['write_policy']+'；'+('每个变量仅一个线圈。' if d['write_policy']=='single_writer' else '允许多处写入，后执行且实际写入的线圈决定最终值。')]
    if d['semantics']=='sequential_timed_scan':legend.append('功能块每扫描调用一次，包括输入为假时；线圈接块的Q，不能把IN/CU当作跳过调用的使能。时刻单位ms。')
    if any(r.get('type')=='CTUD' for r in d['rungs']):legend[-1]=legend[-1].replace('线圈接块的Q','单输出块接Q；CTUD分别接QU/QD')
    for i,note in enumerate(legend):
        nh=max(30,len(wrap(note,width-128,16))*23);text(64,y,width-128,nh,note,'legend-'+str(i),16,'muted','left');y+=nh+8
    y+=22;text(64,y,width-128,34,'扫描验算 / 1 = TRUE，0 = FALSE；完整逐梯级读写见 trace.json 与 CSV','trace-title',22,'ink','left');y+=48
    writable=[v['id'] for v in d['variables'] if v['role']!='input']
    # Summaries stay readable; complete scans are never truncated in trace outputs.
    for i,step in enumerate(a['scans'][:12]):
        value=step['id']+(' @'+str(step['time_ms'])+'ms' if 'time_ms' in step else '')+' · '+step['label']+'    '+', '.join(k+'='+str(int(step['after'][k])) for k in writable)
        if 'blocks' in step:value+='    '+', '.join(k+'.ET='+str(v['et_ms'])+'ms' if 'et_ms' in v else k+'.CV='+str(v['cv']) if 'cv' in v else k+'.Q='+str(int(v['q'])) for k,v in step['blocks'].items())
        nh=max(32,len(wrap(value,width-128,17))*24);text(64,y,width-128,nh,value,'scan-'+str(i),17,'ink','left');y+=nh+6
    if len(a['scans'])>12:text(64,y,width-128,32,'图上显示前12次扫描，全部 '+str(len(a['scans']))+' 次见 trace.json。','scan-more',16,'muted','left')
    s.meta.update(source_input=d,analysis=a,expression_sizes=sizes);s.finish();return s,a


def render_file(source,out,theme='editorial-warm'):
    source=Path(source);d=json.loads(source.read_text());s,a=build(d,theme);qa=audit(s)
    need(not qa['errors'] and not qa['warnings'],'layout audit failed: '+repr(qa))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for suffix,content in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('trace.json',json.dumps(a,ensure_ascii=False,indent=2)),('qa.json',json.dumps(qa,ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))]:
        (out/(source.stem+'.'+suffix)).write_text(content)
    if any(r.get('type')=='CTUD' for r in d['rungs']):
        export_analysis(source,out)
        from ctud_ladder_timing import render as render_ctud_timing
        render_ctud_timing(source,out/'ctud-timing')
        from ladder_timing import write_timing
        write_timing(d,a,out,source.stem,theme)
        return dict(scans=len(a['scans']),rungs=len(d['rungs']),width=s.w,height=s.h,qa=qa)
    with (out/(source.stem+'.csv')).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['scan','rung','power','coil','target','kind','before','after','write_performed'])
        for step in a['scans']:
            for r in step['rungs']:w.writerow([step['id']]+[r[k] for k in ('rung','power','coil','target','kind','before','after','write_performed')])
    if d['semantics']=='sequential_timed_scan':
        from ladder_timing import write_timing
        write_timing(d,a,out,source.stem,theme)
    return dict(scans=len(a['scans']),rungs=len(d['rungs']),width=s.w,height=s.h,qa=qa)


def export_analysis(source,out):
    """Export complete scan evidence for single- and dual-output rungs."""
    source=Path(source);d=json.loads(source.read_text());a=analyze(d)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for suffix,value in [('input.json',d),('trace.json',a)]:
        (out/(source.stem+'.'+suffix)).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    with (out/(source.stem+'.writes.csv')).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['scan','time_ms','rung','port','target','before','after','write_performed'])
        for scan in a['scans']:
            for rung in scan['rungs']:
                if rung.get('type')=='CTUD':
                    for row in rung['writes']:w.writerow([scan['id'],scan.get('time_ms',''),rung['rung'],row['port'],row['target'],row['before'],row['after'],True])
                else:w.writerow([scan['id'],scan.get('time_ms',''),rung['rung'],'coil',rung['target'],rung['before'],rung['after'],rung['write_performed']])
    with (out/(source.stem+'.ctud.csv')).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['scan','time_ms','rung','cu','cd','reset','load','pv','cu_rising','cd_rising','cv','qu','qd','reason'])
        for scan in a['scans']:
            for rung in scan['rungs']:
                if rung.get('type')=='CTUD':
                    b=rung['block'];w.writerow([scan['id'],scan['time_ms'],rung['rung']]+[rung['inputs'][k] for k in ('cu','cd','reset','load')]+[b[k] for k in ('pv','cu_rising','cd_rising','cv','qu','qd','reason')])
    return dict(scans=len(a['scans']),rungs=len(d['rungs']),scope='analysis only; no diagram generated')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--theme',default='editorial-warm');p.add_argument('--analyze-only',action='store_true');args=p.parse_args()
    print(json.dumps(export_analysis(args.input,args.out) if args.analyze_only else render_file(args.input,args.out,args.theme),ensure_ascii=False))
