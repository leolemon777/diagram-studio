"""Nested Nassi-Shneiderman layout, editable geometry without jump arrows."""
import argparse,json
from pathlib import Path
from structured_program import validate
from render import Scene,svg,drawio,audit,wrap

def build(d):
 inventory=validate(d);sizes={};headers={}
 def measure_seq(body):
  sizes_=[measure(n) for n in body]
  return max([w for w,h in sizes_] or [260]),sum(h for w,h in sizes_) or 64
 def measure(n):
  k=n['kind']
  if k=='action':wh=(300,max(70,28*len(wrap(n['text'],268,18))+28))
  elif k in ('while','repeat'):
   w,h=measure_seq(n['body']);w+=38
   value=('WHILE  '+n['condition']) if k=='while' else ('UNTIL  '+n['until'])
   headers[n['id']]=(max(76,28*len(wrap(value,w-24,18))+24),0)
   wh=(w,h+headers[n['id']][0])
  else:
   children=[n['then'],n['else']] if k=='if' else [b['body'] for b in n['branches']]+[n['default']]
   dims=[measure_seq(c) for c in children];w=sum(cw for cw,ch in dims)
   heading=n['condition'] if k=='if' else n['expression']
   labels=['真','假'] if k=='if' else [b['label'] for b in n['branches']]+['否则']
   head=max(68,4*(6+28*len(wrap(heading,w*.5,18))))
   label_h=max(48,max(24*len(wrap(label,cw-24,16))+16 for label,(cw,ch) in zip(labels,dims)))
   headers[n['id']]=(head,label_h)
   wh=(w,max(ch for cw,ch in dims)+head+label_h)
  sizes[n['id']]=wh;return wh
 width,height=measure_seq(d['body']);s=Scene(dict(width=max(1050,width+128),height=height+330,title=d['title'],eyebrow='NASSI–SHNEIDERMAN / STRUCTURED PROGRAM',subtitle='教学结构 · 自上而下读取 · 分支区域嵌套，不使用任意跳转箭头',footer='假设程序；仅核验结构，未执行表达式。空分支以 ∅ 标注。'), 'editorial-warm')
 def rect(x,y,w,h,ident=None):s.add(x,y,w,h,id=ident,kind='rect',fill='none',radius=0,tone='ink',check=False)
 def text(x,y,w,h,value,size=18):s.text(x+12,y+8,w-24,h-16,value,size=size)
 def line(points):s.edge(points=points,arrow=False,tone='ink',width=1.5)
 def seq(body,x,y,w,fill_height=None):
  start=y
  if not body:rect(x,y,w,64);text(x,y,w,64,'∅');y+=64
  for n in body:
   node(n,x,y,w);y+=sizes[n['id']][1]
  if fill_height and y<start+fill_height:rect(x,y,w,start+fill_height-y)
 def node(n,x,y,w):
  k=n['kind'];h=sizes[n['id']][1];rect(x,y,w,h,'node_'+n['id'])
  if k=='action':text(x,y,w,h,n['text']);return
  if k in ('while','repeat'):
   head=headers[n['id']][0]
   if k=='while':
    text(x,y,w,head,'WHILE  '+n['condition']);seq(n['body'],x+38,y+head,w-38)
   else:
    seq(n['body'],x+38,y,w-38);text(x,y+h-head,w,head,'UNTIL  '+n['until'])
   return
  children=[n['then'],n['else']] if k=='if' else [b['body'] for b in n['branches']]+[n['default']]
  labels=['真','假'] if k=='if' else [b['label'] for b in n['branches']]+['否则']
  heading=n['condition'] if k=='if' else n['expression']
  head,label_h=headers[n['id']]
  s.text(x+w*.25,y+6,w*.5,head/4-6,heading,size=18,align='center')
  weights=[measure_seq(c)[0] for c in children];total=sum(weights);xx=x
  pivot=x+w*weights[0]/total if k=='if' else x+w-w*weights[-1]/total
  line([(x,y),(pivot,y+head),(x+w,y)])
  for child,label,weight in zip(children,labels,weights):
   cw=w*weight/total
   text(xx,y+head,cw,label_h,label,16)
   boundary_y=y+head*((xx-x)/(pivot-x) if xx<=pivot else (x+w-xx)/(x+w-pivot))
   line([(xx,boundary_y),(xx,y+h)])
   seq(child,xx,y+head+label_h,cw,h-head-label_h);xx+=cw
 seq(d['body'],64,220,s.w-128)
 s.meta=dict(inventory=inventory,node_sizes=sizes,header_sizes=headers);s.finish();q=audit(s)
 if q['errors'] or q['warnings']:raise ValueError(str(q))
 return s,q

def render_file(source,out):
 source=Path(source);d=json.loads(source.read_text());s,q=build(d);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for suffix,value in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('qa.json',json.dumps(q,indent=2)),('structure.json',json.dumps(s.meta,ensure_ascii=False,indent=2))]:
  (out/(source.stem+'.'+suffix)).write_text(value)
 return q
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);args=p.parse_args();print(render_file(args.input,args.out))
