"""Project actual ladder CTUD call traces into the common timing renderer."""
import argparse,json
from pathlib import Path
from ladder import analyze
from ctud_render import render_file,render_pages
from ctud import analyze as analyze_counter

def project(d,trace,rung):
    scans=[]
    for scan in trace['scans']:
        call=next(r for r in scan['rungs'] if r['rung']==rung['id'])
        scans.append(dict(id=scan['id'],time_ms=scan['time_ms'],pv=call['block']['pv'],**call['inputs']))
    model=dict(title=d['title']+' / '+rung['id'],profile=rung['profile'],assumptions=[d['data_status'],d['scope'],'Derived from actual ordered ladder calls; includes reads of earlier rung writes.'],initial=rung['initial'],scans=scans)
    reproduced=analyze_counter(model)
    for scan,calc in zip(trace['scans'],reproduced['scans']):
        original=next(r for r in scan['rungs'] if r['rung']==rung['id'])['block']
        for key in ('before','after','cv','qu','qd','cu_rising','cd_rising','reason','pv'):
            if original[key]!=calc[key]:raise ValueError('trace projection mismatch: '+key)
    return model

def render(source,out):
    source=Path(source);d=json.loads(source.read_text());trace=analyze(d)
    rungs=[r for r in d['rungs'] if r.get('type')=='CTUD']
    if not rungs:raise ValueError('no CTUD rungs')
    out=Path(out);out.mkdir(parents=True,exist_ok=True);records=[]
    for rung in rungs:
        model=project(d,trace,rung);stem=source.stem+'-'+rung['id']
        src=out/(stem+'.model.json');src.write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n')
        qa=render_pages(src,out) if len(model['scans'])>40 else render_file(src,out)
        records.append(dict(rung=rung['id'],source=str(src.name),qa=qa,outputs=rung['outputs'],scans=len(model['scans'])))
    (out/(source.stem+'.timing-index.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    return records
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);args=p.parse_args();print(json.dumps(render(args.input,args.out)))
