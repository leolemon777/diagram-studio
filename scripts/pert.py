"""Exact AON finish-to-start CPM, optionally using PERT three-point means."""
import argparse,json,re
from fractions import Fraction as F
from pathlib import Path

def need(value,msg):
 if not value:raise ValueError(msg)
def fields(d,keys):need(type(d) is dict and set(d)==set(keys),'unexpected or missing fields')
def duration(x):
 need(type(x) in (str,int) and re.fullmatch(r'\d+(\.\d+)?',str(x)) is not None,'nonnegative integer or decimal string required')
 need(len(str(x))<=30,'duration too long');return F(str(x))
def analyze(d):
 fields(d,('title','unit','mode','assumptions','tasks'))
 need(all(isinstance(d[k],str) and d[k].strip() for k in ('title','unit')),'title and unit required')
 need(d['mode'] in ('deterministic','pert'),'unknown mode')
 need(type(d['assumptions']) is list and bool(d['assumptions']) and all(isinstance(s,str) and s.strip() for s in d['assumptions']),'assumptions required')
 need(type(d['tasks']) is list and 1<=len(d['tasks'])<=200,'1..200 tasks required')
 tasks={};ds={};vs={};succ={}
 for t in d['tasks']:
  fields(t,('id','label','predecessors','duration') if d['mode']=='deterministic' else ('id','label','predecessors','optimistic','likely','pessimistic'))
  i=t['id'];need(isinstance(i,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}',i) and i not in tasks,'invalid or duplicate task id')
  need(isinstance(t['label'],str) and t['label'].strip(),'label required')
  p=t['predecessors'];need(type(p) is list and all(isinstance(x,str) for x in p) and len(set(p))==len(p),'invalid predecessors')
  tasks[i]=t;succ[i]=[]
  if d['mode']=='pert':
   a,m,b=[duration(t[k]) for k in ('optimistic','likely','pessimistic')];need(a<=m<=b,'require optimistic <= likely <= pessimistic');ds[i]=(a+4*m+b)/6;vs[i]=((b-a)/6)**2
  else:ds[i]=duration(t['duration']);vs[i]=None
 for i,t in tasks.items():
  for p in t['predecessors']:need(p in tasks and p!=i,'unknown or self predecessor');succ[p].append(i)
 degrees={i:len(t['predecessors']) for i,t in tasks.items()};ready=[i for i in tasks if not degrees[i]];order=[]
 while ready:
  i=ready.pop(0);order.append(i)
  for j in succ[i]:
   degrees[j]-=1
   if not degrees[j]:ready.append(j)
 need(len(order)==len(tasks),'dependency cycle')
 es={};ef={};ls={};lf={}
 for i in order:es[i]=max([ef[p] for p in tasks[i]['predecessors']]+[F(0)]);ef[i]=es[i]+ds[i]
 finish=max(ef.values())
 for i in reversed(order):lf[i]=min([ls[j] for j in succ[i]] or [finish]);ls[i]=lf[i]-ds[i]
 critical={i for i in order if ls[i]==es[i]};edges=[(i,j) for i in order for j in succ[i] if i in critical and j in critical and ef[i]==es[j]]
 counts={i:0 for i in order}
 for i in order:
  if i in critical and not tasks[i]['predecessors']:counts[i]=1
  for a,b in edges:
   if a==i:counts[b]+=counts[i]
 count=sum(counts[i] for i in order if not succ[i])
 rows=[]
 for i in order:
  free=min([es[j] for j in succ[i]] or [finish])-ef[i]
  rows.append(dict(id=i,label=tasks[i]['label'],duration=str(ds[i]),variance=None if vs[i] is None else str(vs[i]),ES=str(es[i]),EF=str(ef[i]),LS=str(ls[i]),LF=str(lf[i]),total_float=str(ls[i]-es[i]),free_float=str(free),critical=i in critical))
 return dict(mode=d['mode'],unit=d['unit'],duration=str(finish),tasks=rows,critical_edges=[list(e) for e in edges],critical_path_count=count,arithmetic='exact rational strings',scope='AON, zero-lag finish-to-start, common zero start and common completion; no calendars/resources/deadlines or project completion probability')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();s=json.dumps(analyze(json.loads(a.input.read_text())),ensure_ascii=False,indent=2)+'\n'
 if a.out:a.out.write_text(s)
 else:print(s,end='')
