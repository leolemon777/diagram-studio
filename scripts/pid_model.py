"""Validate explicit teaching P&ID topology; not a DEXPI serializer or hydraulic solver."""
import json,re,argparse
from pathlib import Path

def need(ok,message):
    if not ok:raise ValueError(message)
def fields(obj,keys,where):
    need(type(obj) is dict and set(obj)==set(keys),where+': unexpected or missing fields')
def validate(d):
    fields(d,('schema','title','assumptions','items','connections'),'model')
    need(d['schema']=='pid-topology-1','unsupported schema')
    need(isinstance(d['title'],str) and d['title'].strip(),'title required')
    need(type(d['assumptions']) is list and bool(d['assumptions']) and all(isinstance(x,str) and x.strip() for x in d['assumptions']),'explicit assumptions required')
    need(type(d['items']) is list and 1<=len(d['items'])<=200,'1..200 items required')
    need(type(d['connections']) is list and len(d['connections'])<=500,'at most 500 connections')
    ids=set();tags=set();ports={};items={};used={};warnings=[]
    def reserve(value):
        need(isinstance(value,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,47}',value) and value not in ids,'invalid or duplicate id');ids.add(value)
    for item in d['items']:
        fields(item,('id','tag','kind','label','ports'),'item');reserve(item['id'])
        need(item['kind'] in ('tank','pump','valve','instrument','junction','boundary'),'unknown item kind')
        need(isinstance(item['tag'],str) and item['tag'].strip() and item['tag'] not in tags,'duplicate or empty tag');tags.add(item['tag'])
        need(isinstance(item['label'],str) and item['label'].strip(),'label required')
        need(type(item['ports']) is list and len(item['ports'])>0,'ports required');items[item['id']]=item
        for p in item['ports']:
            fields(p,('id','domain','direction'),'port');reserve(p['id'])
            need(p['domain'] in ('process','signal'),'unknown port domain')
            need(p['direction'] in ('in','out','bidirectional'),'unknown direction')
            ports[p['id']]=(item['id'],p);used[p['id']]=0
        if item['kind']=='junction':
            need(len(item['ports'])>=3 and all(p['domain']=='process' for p in item['ports']),'junction requires at least 3 process ports')
    edges=[]
    for c in d['connections']:
        fields(c,('id','from','to','domain','label','flow'),'connection');reserve(c['id'])
        need(c['from'] in ports and c['to'] in ports,'unknown endpoint')
        a,ap=ports[c['from']];b,bp=ports[c['to']]
        need(a!=b,'self connection unsupported')
        need(c['domain'] in ('process','signal') and ap['domain']==bp['domain']==c['domain'],'domain mismatch')
        need(isinstance(c['label'],str) and c['label'].strip(),'connection label required')
        need(c['flow'] in ('forward','bidirectional','unknown'),'unknown flow declaration')
        if c['flow']=='forward':need(ap['direction']!='in' and bp['direction']!='out','direction conflict')
        else:need(ap['direction']==bp['direction']=='bidirectional','non-forward flow requires bidirectional ports')
        for pid in (c['from'],c['to']):
            used[pid]+=1;need(used[pid]==1,'port reused; represent branch with explicit junction')
        edges.append(dict(id=c['id'],source_item=a,target_item=b,domain=c['domain'],flow=c['flow']))
    for pid,count in used.items():
        if not count:warnings.append('Unconnected port: '+pid)
    return dict(schema=d['schema'],items=len(items),ports=len(ports),connections=len(edges),edges=edges,warnings=warnings,scope='Declared connectivity only; geometry, instrument semantics, physical feasibility and standards compliance unverified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();r=validate(json.loads(a.input.read_text()));s=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.out:a.out.write_text(s)
    else:print(s,end='')
