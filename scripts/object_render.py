"""Small UML object snapshots with external link lanes and editable cells."""
import argparse,json,xml.etree.ElementTree as E
from pathlib import Path
from object_notation import notation
from render import Scene,svg,drawio,audit,wrap

def build(d):
 model=notation(d);n=len(model['objects']);counts={o['id']:0 for o in model['objects']}
 for link in model['links']:
  for end in link['ends']:counts[end['object']]+=1
 w=max(390,160*(max(counts.values())+1));gap=90;heights=[];used={k:0 for k in counts}
 for o in model['objects']:
  heading=30*len(wrap(o['heading'],w-32,18))+24
  body=sum(max(36,26*len(wrap(v['text'],w-32,17))) for v in o['slots'])+24
  heights.append((heading,max(60,body)))
 # An interior port may only have about half of its port cell available on
 # either side. Reserve height against that conservative width so a role never
 # has to cross its own connector merely to remain readable.
 role_height=max([28]+[21*len(wrap(end['role'],60,14)) for link in model['links'] for end in link['ends']])
 label_heights=[max(28,24*len(wrap(link['association'],120,16))) for link in model['links']]
 bottom=230+max(a+b for a,b in heights);height=bottom+role_height+180+sum(h+60 for h in label_heights)
 s=Scene(dict(width=max(1100,128+n*w+(n-1)*gap),height=height,title=d['title'],subtitle=d['snapshot'],eyebrow='UML / INSTANCE SNAPSHOT',footer='教学快照；仅校验引用完整性。{ } = 显式空值列表；null = 输入空值；未校验类型和多重性。'),'editorial-warm')
 boxes={};heads=[]
 for i,(o,(hh,bh)) in enumerate(zip(model['objects'],heights)):
  x=64+i*(w+gap);y=230;ident='object_'+o['id'];boxes[o['id']]=(x,y,w,hh+bh)
  s.add(x,y,w,hh+bh,id=ident,fill='panel',radius=0,tone='ink',check=True)
  hid='heading_'+o['id'];s.text(x+16,y+12,w-32,hh-24,o['heading'],size=18,align='center',id=hid);heads.append(hid)
  s.add(x,y+hh,w,1,id='divider_'+o['id'],fill='ink',stroke='none',radius=0,tone='ink',check=False)
  yy=y+hh+12
  for j,slot in enumerate(o['slots']):
   sh=max(36,26*len(wrap(slot['text'],w-32,17)));s.text(x+16,yy,w-32,sh,slot['text'],size=17,id='slot_'+o['id']+'_'+str(j));yy+=sh
 routes=[]
 for i,link in enumerate(model['links']):
  a,b=link['ends'];ax,ay,aw,ah=boxes[a['object']];bx,by,bw,bh=boxes[b['object']]
  lane=bottom+role_height+32+sum(h+60 for h in label_heights[:i+1])
  # Different endpoint offsets preserve self-links; one independent lane per link.
  def endpoint(end,x,width,fallback):
   ident=end['object'];used[ident]+=1
   return x+width*(fallback if counts[ident]==1 else used[ident]/(counts[ident]+1))
  sx=endpoint(a,ax,aw,.35);tx=endpoint(b,bx,bw,.65)
  routes.append((link,a,b,sx,tx,ay+ah,by+bh,lane))
 for i,(link,a,b,sx,tx,source_y,target_y,lane) in enumerate(routes):
  s.edge(a='object_'+a['object'],b='object_'+b['object'],points=[(sx,source_y),(sx,lane),(tx,lane),(tx,target_y)],arrow=False,tone='ink',width=1.5)
  if link['association']:
   left,right=sorted((sx,tx));cuts=sorted(set([left,right]+[x for route in routes for x in (route[3],route[4]) if left<x<right]))
   start,end=max(zip(cuts,cuts[1:]),key=lambda pair:pair[1]-pair[0]);available=end-start-24
   lh=max(28,24*len(wrap(link['association'],available,16)))
   s.text(start+12,lane-lh-8,available,lh,link['association'],size=16,id='link_label_'+str(i))
  for j,(end,x,y) in enumerate([(a,sx,source_y),(b,tx,target_y)]):
   if end['role']:
    ox,oy,ow,oh=boxes[end['object']]
    ports=sorted({p for route in routes for e,p in ((route[1],route[3]),(route[2],route[4])) if e['object']==end['object']})
    index=ports.index(x);left=ox if index==0 else (ports[index-1]+x)/2;right=ox+ow if index==len(ports)-1 else (x+ports[index+1])/2
    candidates=[(left+6,x-left-12),(x+6,right-x-12)];rx,rw=max(candidates,key=lambda item:item[1])
    s.text(rx,y+8,rw,role_height,end['role'],size=14,id='role_'+str(i)+'_'+str(j))
 s.meta=dict(model=model,underlined_headings=heads);s.finish();q=audit(s)
 if q['errors'] or q['warnings']:raise ValueError(str(q))
 return s,q

def exports(s):
 # Underline the entire instance namestring in both actual formats.
 root=E.fromstring(svg(s));ns={'s':'http://www.w3.org/2000/svg'}
 for g in root.findall('s:g/s:g',ns):
  if g.get('id') in s.meta['underlined_headings']:
   for t in g.findall('s:text',ns):t.set('text-decoration','underline')
 E.register_namespace('','http://www.w3.org/2000/svg');sv=E.tostring(root,encoding='unicode')
 root=E.fromstring(drawio(s))
 for c in root.iter('mxCell'):
  if c.get('id') in s.meta['underlined_headings']:c.set('style',c.get('style','')+'fontStyle=4;')
 cells={c.get('id'):c for c in root.iter('mxCell')}
 for o in s.meta['model']['objects']:
  parent=cells['object_'+o['id']];pg=parent.find('mxGeometry');px=float(pg.get('x'));py=float(pg.get('y'))
  parent.set('style',parent.get('style','')+'container=1;collapsible=0;recursiveResize=0;')
  child_ids=['heading_'+o['id'],'divider_'+o['id']]+['slot_'+o['id']+'_'+str(j) for j in range(len(o['slots']))]
  for ident in child_ids:
   c=cells[ident];g=c.find('mxGeometry');c.set('parent',parent.get('id'));c.set('connectable','0')
   c.set('style',c.get('style','')+'part=1;movable=0;resizable=0;')
   g.set('x',str(float(g.get('x'))-px));g.set('y',str(float(g.get('y'))-py))
 for i,link in enumerate(s.meta['model']['links']):
  for j,end in enumerate(link['ends']):
   if not end['role']:continue
   c=cells['role_'+str(i)+'_'+str(j)];parent=cells['object_'+end['object']];pg=parent.find('mxGeometry');g=c.find('mxGeometry');c.set('parent',parent.get('id'));c.set('connectable','0')
   g.set('x',str(float(g.get('x'))-float(pg.get('x'))));g.set('y',str(float(g.get('y'))-float(pg.get('y'))))
  if link['association']:
   c=cells['link_label_'+str(i)];c.set('parent','_edge_'+str(i));c.set('connectable','0');c.set('style',c.get('style','')+'align=center;')
   g=c.find('mxGeometry');g.set('relative','1');g.set('x','0');g.set('y','0');g.set('width','200');g.set('height',str(max(28,24*len(wrap(link['association'],200,16)))));E.SubElement(g,'mxPoint',x='-100',y=str(-float(g.get('height'))-8),attrib={'as':'offset'})
 return sv,E.tostring(root,encoding='unicode')

def render_file(source,out):
 p=Path(source);d=json.loads(p.read_text());s,q=build(d);sv,xml=exports(s);dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
 for ext,content in [('svg',sv),('drawio',xml),('input.json',json.dumps(d,ensure_ascii=False,indent=2)),('notation.json',json.dumps(s.meta,ensure_ascii=False,indent=2)),('qa.json',json.dumps(q,indent=2))]:(dest/(p.stem+'.'+ext)).write_text(content)
 return q
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);a=p.parse_args();print(render_file(a.input,a.out))
