"""AON task cards driven by exact CPM values; layout is not a timescale."""
import argparse,csv,json,copy
from pathlib import Path
from pert import analyze
from render import Scene,svg,drawio,audit,need

def build(d,theme='editorial-warm'):
 a=analyze(d);tasks={t['id']:t for t in d['tasks']};ranks={};layers={}
 for row in a['tasks']:
  i=row['id'];ranks[i]=max([ranks[p]+1 for p in tasks[i]['predecessors']] or [0]);layers.setdefault(ranks[i],[]).append(i)
 step=280 if d['mode']=='pert' else 250;card_height=238 if d['mode']=='pert' else 208
 width=max(1400,128+len(layers)*390);rows=max(map(len,layers.values()));height=max(900,420+rows*step)
 s=Scene(dict(width=width,height=height,title=d['title'],eyebrow='PERT / CPM · ACTIVITY ON NODE',subtitle='零时滞完成到开始 · 排列按依赖层级，不是时间比例；单位：'+d['unit'],footer='假设输入 · 无资源/日历约束；三点均值网络不是项目完成概率'),theme)
 s.text(64,190,width-128,44,'网络工期 '+a['duration']+' '+d['unit']+'   ·   并列关键路径 '+str(a['critical_path_count'])+' 条',size=23)
 s.text(64,238,width-128,34,'粗线＋“关键”标记＝零总浮动；ES/EF 最早开始/结束，LS/LF 最迟开始/结束，TF/FF 总/自由浮动。',size=16,tone='muted')
 rowmap={r['id']:r for r in a['tasks']}
 for rank,ids in layers.items():
  for n,i in enumerate(ids):
   r=rowmap[i];x=64+rank*390;y=300+((rows-len(ids))/2+n)*step;critical=r['critical'];tone='accent' if critical else 'muted'
   s.add(x,y,280,card_height,id='task_'+i,kind='rect',tone=tone,fill='bg',check=False)
   s.text(x+16,y+10,248,52,i+' · '+r['label'],size=21)
   s.text(x+16,y+66,248,30,('关键' if critical else '非关键')+' · 工期 '+r['duration'],size=18,tone=tone)
   s.text(x+16,y+101,248,28,'ES '+r['ES']+'    EF '+r['EF'],size=16)
   s.text(x+16,y+132,248,28,'LS '+r['LS']+'    LF '+r['LF'],size=16)
   s.text(x+16,y+163,248,30,'TF '+r['total_float']+'    FF '+r['free_float'],size=16,tone=tone)
   if d['mode']=='pert':
    t=tasks[i];s.text(x+16,y+196,248,30,'a/m/b  '+str(t['optimistic'])+' / '+str(t['likely'])+' / '+str(t['pessimistic']),size=15,tone='muted')
 critical={tuple(e) for e in a['critical_edges']}
 cards={n['id']:n for n in s.nodes if n['id'].startswith('task_')}
 skips=[(p,t['id']) for t in d['tasks'] for p in t['predecessors'] if ranks[t['id']]-ranks[p]>1]
 bottom=max(n['y']+n['h'] for n in cards.values())
 lanes={edge:bottom+48+24*k for k,edge in enumerate(skips)}
 if skips:s.h=max(s.h,bottom+48+24*len(skips)+100)
 for t in d['tasks']:
  for p in t['predecessors']:
   yes=(p,t['id']) in critical
   points=None
   if (p,t['id']) in lanes:
    src=cards['task_'+p];dst=cards['task_'+t['id']];lane=lanes[p,t['id']]
    x0=src['x']+src['w'];y0=src['y']+src['h']/2;x1=dst['x'];y1=dst['y']+dst['h']/2
    points=[(x0,y0),(x0+36,y0),(x0+36,lane),(x1-36,lane),(x1-36,y1),(x1,y1)]
   s.edge('task_'+p,'task_'+t['id'],source_port='right',target_port='left',points=points,tone='accent' if yes else 'muted',width=3 if yes else 1.5,arrow=True)
 # Card backgrounds are excluded from the generic nested-text overlap audit.
 # Audit them separately so dependencies cannot silently pass through a card.
 route_scene=copy.copy(s);route_scene.nodes=[dict(n,check=True) for n in cards.values()]
 route_qa=audit(route_scene)
 need(not route_qa['errors'] and not route_qa['warnings'],'PERT card routing: '+str(route_qa))
 s.meta.update(routing={'skip_edges':len(skips),'strategy':'bottom lanes outside task columns','card_clearance_checked':True},analysis=a,ranks=ranks,assumptions=d['assumptions'],layout='dependency ranks; not time-scaled');s.finish();q=audit(s);need(not q['errors'] and not q['warnings'],'PERT layout: '+str(q));return s,q

def render_file(source,out,theme='editorial-warm'):
 source=Path(source);d=json.loads(source.read_text());s,q=build(d,theme);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for ext,value in [('svg',svg(s)),('drawio',drawio(s)),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('analysis.json',json.dumps(s.meta['analysis'],ensure_ascii=False,indent=2)),('scene.json',json.dumps(dict(width=s.w,height=s.h,nodes=s.nodes,edges=s.edges,meta=s.meta),ensure_ascii=False,indent=2)),('qa.json',json.dumps(q,ensure_ascii=False,indent=2))]:(out/(source.stem+'.'+ext)).write_text(value)
 with (out/(source.stem+'.csv')).open('w',newline='') as f:
  rows=s.meta['analysis']['tasks'];w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return q
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);args=p.parse_args();print(render_file(args.input,args.out))
