"""Scan-sampled CTUD timing diagram. No interpolation between calls."""
import argparse,json
from pathlib import Path
from ctud import export
from render import Scene,svg,drawio,audit

def build(d,a,numeric_range=None):
 rows=a['scans'];n=len(rows)
 if n>40:raise ValueError('timing sheet supports at most 40 scans; split explicitly')
 s=Scene(dict(width=max(1500,260+n*80),height=1180,title=d['title'],eyebrow='CTUD / SCAN TRACE',subtitle='假设输入 · INT16 · 每次调用采样 · QU 与 QD 独立输出',footer='仅显示调用时刻结果；末次采样后不推定延续。图形编辑不会自动重算。'),'editorial-warm')
 left=210;right=s.w-65;t0=rows[0]['time_ms'];span=max(1,rows[-1]['time_ms']-t0)
 xs=[left+(r['time_ms']-t0)/span*(right-left) for r in rows]
 # Keep physical time spacing; thin annotation only, never samples or values.
 visible=[]
 for i,x in enumerate(xs):
  if not visible or x-xs[visible[-1]]>=72:visible.append(i)
 if n>1 and n-1 not in visible:
  if len(visible)>1 and xs[-1]-xs[visible[-1]]<72:visible.pop()
  if xs[-1]-xs[visible[-1]]>=72:visible.append(n-1)
 for i,(x,r) in enumerate(zip(xs,rows)):
  s.edge(points=[(x,245),(x,1050)],arrow=False,tone='line',dashed=True)
  if i in visible:
   s.text(x-24,205,48,28,r['id'],size=13,align='center')
   s.text(x-30,1060,60,28,str(r['time_ms']),size=13,align='center')
 for k,key in enumerate(('cu','cd','reset','load','qu','qd')):
  y=260+k*85;values=[r['inputs'][key] if key in r['inputs'] else r[key] for r in rows]
  s.text(64,y-8,130,32,key.upper(),size=20)
  pts=[]
  for i,(x,v) in enumerate(zip(xs,values)):
   yy=y+36-30*int(v)
   if i:pts.append((x,y+36-30*int(values[i-1])))
   pts.append((x,yy));s.add(x-3,yy-3,6,6,kind='ellipse',fill='accent',check=False)
  if len(pts)>1:s.edge(points=pts,arrow=False,tone='accent',width=2)
 lo=min(0,*[r['cv'] for r in rows],*[r['pv'] for r in rows]);hi=max(1,*[r['cv'] for r in rows],*[r['pv'] for r in rows])
 if numeric_range is not None:
  low,high=numeric_range
  if low>lo or high<hi or low>=high:raise ValueError('range must contain all CV/PV values')
  lo,hi=low,high
 def yy(v):return 1010-(v-lo)/(hi-lo)*190
 s.text(64,790,130,60,'CV / PV',size=20)
 for value in sorted(set((lo,0,hi))):
  s.text(150,yy(value)-13,45,26,str(value),size=14,align='right')
  s.edge(points=[(left,yy(value)),(right,yy(value))],arrow=False,tone='line')
 for key,tone in [('pv','muted'),('cv','accent')]:
  pts=[]
  for i,(x,r) in enumerate(zip(xs,rows)):
   if i:pts.append((x,yy(rows[i-1][key])))
   pts.append((x,yy(r[key])))
   if key=='cv' and i in visible:s.text(x-22,yy(r[key])-28,44,23,str(r[key]),size=13,align='center')
  if len(pts)>1:s.edge(points=pts,arrow=False,tone=tone,width=2.5 if key=='cv' else 1.5,dashed=key=='pv')
 s.text(210,760,900,32,'实线 CV 当前计数 · 虚线 PV 当次预置值 · 横轴为时间 ms',size=16)
 if len(visible)<n:s.text(210,1100,s.w-275,28,'密集采样仅稀疏标注；全部采样点和跳变保留，精确值见CSV。',size=15,tone='muted')
 s.meta=dict(trace=a,numeric_range=[lo,hi],sample_x=xs,annotated_indices=visible);s.finish();q=audit(s)
 if q['errors']:raise ValueError(str(q))
 return s,q

def render_file(source,out):
 source=Path(source);d=json.loads(source.read_text());a=export(source,out);s,q=build(d,a);out=Path(out)
 for ext,value in [('svg',svg(s)),('drawio',drawio(s)),('qa.json',json.dumps(q,ensure_ascii=False,indent=2))]:
  (out/(source.stem+'.'+ext)).write_text(value)
 return q
def paginate(d,page_size=24):
 from ctud import analyze
 if type(page_size) is not int or not 1<=page_size<=40:raise ValueError('page_size must be 1..40')
 full=analyze(d);pages=[]
 for start in range(0,len(d['scans']),page_size):
  scans=d['scans'][start:start+page_size]
  page=dict(d,title=d['title']+' / '+str(len(pages)+1),initial=dict(full['scans'][start]['before']),scans=scans)
  actual=analyze(page)
  if actual['scans']!=full['scans'][start:start+page_size]:raise ValueError('pagination changed scan state')
  pages.append(page)
 return pages

def render_pages(source,out,page_size=24):
 import xml.etree.ElementTree as ET
 source=Path(source);out=Path(out);d=json.loads(source.read_text());full=export(source,out)
 shared_range=[min(0,*[r['cv'] for r in full['scans']],*[r['pv'] for r in full['scans']]),max(1,*[r['cv'] for r in full['scans']],*[r['pv'] for r in full['scans']])]
 pages=paginate(d,page_size);root=ET.Element('mxfile',host='diagram-studio');index=[]
 for i,page in enumerate(pages,1):
  a=__import__('ctud').analyze(page);s,q=build(page,a,shared_range);stem=source.stem+'-page-'+str(i)
  (out/(stem+'.svg')).write_text(svg(s))
  (out/(stem+'.input.json')).write_text(json.dumps(page,ensure_ascii=False,indent=2)+'\n')
  diagram=ET.fromstring(drawio(s)).find('diagram');diagram.set('id','page-'+str(i));diagram.set('name',str(i)+' '+page['scans'][0]['id']+'–'+page['scans'][-1]['id']);root.append(diagram)
  index.append(dict(numeric_range=shared_range,page=i,first=page['scans'][0]['id'],last=page['scans'][-1]['id'],initial=page['initial'],scans=len(page['scans']),svg=stem+'.svg',qa=q))
 (out/(source.stem+'.pages.drawio')).write_text(ET.tostring(root,encoding='unicode'))
 (out/(source.stem+'.pages.json')).write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
 return index

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--page-size',type=int);args=p.parse_args();print(render_pages(args.input,args.out,args.page_size) if args.page_size else render_file(args.input,args.out))
