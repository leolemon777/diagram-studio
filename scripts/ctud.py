"""Explicit edge-sampled signed INT16 CTUD teaching model, not a PLC emulator."""

def integer(v):
    if type(v) is not int or not -32768 <= v <= 32767:
        raise ValueError('INT16 required')

def boolean(v):
    if type(v) is not bool:
        raise ValueError('Boolean required')

def initialize(cv=0, previous_cu=False, previous_cd=False):
    integer(cv); boolean(previous_cu); boolean(previous_cd)
    return dict(cv=cv, previous_cu=previous_cu, previous_cd=previous_cd)

def step(state, *, cu, cd, reset, load, pv):
    if not isinstance(state,dict) or set(state)!= {'cv','previous_cu','previous_cd'}:
        raise ValueError('explicit CTUD state required')
    integer(state['cv']); integer(pv)
    for v in (cu,cd,reset,load,state['previous_cu'],state['previous_cd']):boolean(v)
    up=cu and not state['previous_cu']; down=cd and not state['previous_cd']
    cv=state['cv']; reason='hold'
    if reset:cv=0;reason='reset'
    elif load:cv=pv;reason='load'
    elif up and down:reason='simultaneous_edges'
    elif up:cv=min(32767,cv+1);reason='up' if cv!=state['cv'] else 'upper_limit'
    elif down:cv=max(-32768,cv-1);reason='down' if cv!=state['cv'] else 'lower_limit'
    # Every call samples both inputs, including reset/load scans.
    after=initialize(cv,cu,cd)
    return dict(before=dict(state),after=after,cu_rising=up,cd_rising=down,
                cv=cv,qu=cv>=pv,qd=cv<=0,pv=pv,reason=reason)

def analyze(d):
    required={'title','profile','assumptions','initial','scans'}
    if not isinstance(d,dict) or set(d)!=required:raise ValueError('invalid document fields')
    if d['profile']!='edge_int16_sample_every_call':raise ValueError('explicit profile required')
    if not isinstance(d['title'],str) or not d['title'].strip():raise ValueError('title required')
    if not isinstance(d['assumptions'],list) or not d['assumptions'] or any(not isinstance(x,str) or not x.strip() for x in d['assumptions']):raise ValueError('assumptions required')
    initial=d['initial']
    if not isinstance(initial,dict) or set(initial)!={'cv','previous_cu','previous_cd'}:raise ValueError('explicit initial state required')
    state=initialize(**initial)
    if not isinstance(d['scans'],list) or not 1<=len(d['scans'])<=10000:raise ValueError('1..10000 scans required')
    result=[];last=-1;ids=set()
    for row in d['scans']:
        if not isinstance(row,dict) or set(row)!={'id','time_ms','cu','cd','reset','load','pv'}:raise ValueError('invalid scan fields')
        ident=row['id'];time=row['time_ms']
        if not isinstance(ident,str) or not ident.strip() or ident in ids:raise ValueError('unique nonempty scan id required')
        if type(time) is not int or time<0 or time<=last:raise ValueError('strictly increasing unsigned scan times required')
        args={k:row[k] for k in ('cu','cd','reset','load','pv')}
        value=step(state,**args);state=value['after']
        result.append(dict(id=ident,time_ms=time,inputs=args,**value));ids.add(ident);last=time
    return dict(profile=d['profile'],initial=dict(initial),scans=result,final=state)

def export(source,out):
    import json,csv
    from pathlib import Path
    source=Path(source);d=json.loads(source.read_text());a=analyze(d)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for suffix,value in [('input.json',d),('trace.json',a)]:
        (out/(source.stem+'.'+suffix)).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    keys=['id','time_ms','cu','cd','reset','load','pv','cu_rising','cd_rising','cv','qu','qd','reason']
    with (out/(source.stem+'.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for scan in a['scans']:
            merged=dict(scan,**{k:v for k,v in scan['inputs'].items() if k!='pv'})
            writer.writerow({k:merged[k] for k in keys})
    return a

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);args=p.parse_args()
    print('scans:',len(export(args.input,args.out)['scans']))
