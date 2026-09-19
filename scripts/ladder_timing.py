"""Plot scan observations on a true millisecond axis; do not infer hidden events."""
from render import Scene, need, audit, svg, drawio


def build_timing(d,a,theme='editorial-warm'):
    scans=a['scans'];times=[s['time_ms'] for s in scans];first=times[0];span=max(1,times[-1]-first)
    rows=[]
    for v in d['variables']:
        rows.append(dict(id=v['id'],label=v['label'],unit='BOOL',maximum=1,values=[int(s['after'][v['id']]) for s in scans]))
    for r in d['rungs']:
        if r.get('type')=='CTUD':
            values=[scan['blocks'][r['id']]['cv'] for scan in scans]
            rows.append(dict(id=r['id']+'.CV',label='双向计数',unit='count',minimum=min(0,*values),maximum=max(1,*values),values=values))
        if 'block' not in r:continue
        b=r['block'];bid=b['id']
        if b['type'] in ('TON','TOF','TP'):rows.append(dict(id=bid+'.ET',label='已过时间',unit='ms',maximum=b['pt_ms'],values=[s['blocks'][bid]['et_ms'] for s in scans]))
        if b['type'] in ('CTU','CTD'):rows.append(dict(id=bid+'.CV',label='当前计数',unit='count',maximum=max(b['pv'],b['initial_cv']),values=[s['blocks'][bid]['cv'] for s in scans]))
    s=Scene(dict(width=1680,height=420+len(rows)*122,title=d['title']+' · 扫描时序',subtitle='点为实际模拟扫描结果；阶梯仅作采样保持显示，不表示扫描间信号已被观测。',eyebrow='SCAN TIMELINE / 横轴为真实输入时刻 ms',footer=d['data_status']+' · 仅模拟输入扫描；扫描间窄脉冲、硬件时钟与调度未建模'),theme)
    x0=370;pw=1200;y0=260;rh=122
    def xpos(t):return x0+(t-first)/span*pw
    tickids=[0]
    for i in range(1,len(times)-1):
        if xpos(times[i])-xpos(times[tickids[-1]])>=130:tickids.append(i)
    if len(times)>1:
        if len(tickids)>1 and xpos(times[-1])-xpos(times[tickids[-1]])<130:tickids.pop()
        tickids.append(len(times)-1)
    for i in tickids:
        x=xpos(times[i]);s.edge(points=[(x,y0-12),(x,y0+rh*len(rows)-20)],arrow=False,tone='line',width=1)
        s.text(x-65,y0-56,130,28,str(times[i]),size=16,tone='muted',align='center')
    for j,row in enumerate(rows):
        top=y0+j*rh;baseline=top+60;minimum=row.get('minimum',0);ceiling=max(1,row['maximum']-minimum)
        s.text(64,top-10,245,56,row['id'],size=18)
        # Short diagram labels; full source labels retained in the input and trace.
        s.text(64,top+48,245,36,row['unit']+' · '+('0 / 1' if row['unit']=='BOOL' else str(minimum)+' … '+str(row['maximum'])),size=16,tone='muted')
        s.edge(points=[(x0,baseline),(x0+pw,baseline)],arrow=False,tone='line',width=1)
        s.text(x0-48,baseline-11,34,24,str(minimum),size=13,tone='muted',align='right')
        if row['maximum']:s.text(x0-64,top-12,50,24,str(row['maximum']),size=13,tone='muted',align='right')
        points=[]
        for i,(t,value) in enumerate(zip(times,row['values'])):
            x=xpos(t);y=baseline-(value-minimum)/ceiling*60
            if i:points.append((x,points[-1][1]))
            points.append((x,y));s.add(x-3,y-3,6,6,kind='ellipse',fill='accent',tone='accent',stroke='none',check=False)
        if len(points)>1:s.edge(points=points,arrow=False,tone='accent',width=2)
    bottom=y0+len(rows)*rh+12
    s.text(64,bottom,1550,42,'时间轴按毫秒比例绘制，扫描间隔可以不相等；小间隔点可能靠近，精确值以 samples.csv 和 trace.json 为准。',size=17,tone='muted')
    s.meta.update(sample_times_ms=times,rows=rows,interpretation='scan samples with zero-order-hold display; no inference of interscan transitions');s.finish()
    qa=audit(s);need(not qa['errors'] and not qa['warnings'],'timing plot layout: '+repr(qa))
    return s,qa


def write_timing(d,a,out,stem,theme):
    import csv,json
    s,qa=build_timing(d,a,theme)
    for suffix,content in [('svg',svg(s)),('drawio',drawio(s)),('qa.json',json.dumps(qa,ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2))]:
        (out/(stem+'.timing.'+suffix)).write_text(content)
    with (out/(stem+'.samples.csv')).open('w',newline='') as f:
        writer=csv.writer(f);rows=s.meta['rows'];writer.writerow(['scan','time_ms']+[r['id'] for r in rows])
        for i,scan in enumerate(a['scans']):writer.writerow([scan['id'],scan['time_ms']]+[r['values'][i] for r in rows])
    with (out/(stem+'.blocks.csv')).open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['scan','time_ms','rung','block','type','input','q','et_ms','cv','reset','rising','previous_input_before'])
        for step in a['scans']:
            for r in step['rungs']:
                if 'block' not in r or r.get('type')=='CTUD':continue
                b=r['block'];writer.writerow([step['id'],step['time_ms'],r['rung'],b['id'],b['type'],b['input'],b['q'],b['after'].get('et_ms',''),b['after'].get('cv',''),b.get('reset',''),b.get('rising',''),b['before'].get('previous_input','')])

    if any(r.get('block',{}).get('type')=='CTD' for r in d['rungs']):
        with (out/(stem+'.counter-controls.csv')).open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['scan','time_ms','rung','block','load_variable','load','rising','cv_before','cv_after','q'])
            for step in a['scans']:
                for r in step['rungs']:
                    b=r.get('block',{})
                    if b.get('type')=='CTD':writer.writerow([step['id'],step['time_ms'],r['rung'],b['id'],b['load_variable'],b['load'],b['rising'],b['before']['cv'],b['after']['cv'],b['q']])
