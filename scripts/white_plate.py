#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the pure-white editorial grammar to the twelve share-atlas Plate scenes.

Retains source data, statistics, node IDs, edge endpoints and quantitative geometry.
Font roles and mark treatments are refined; this is not color-only recoloring.
"""
import argparse,copy,json,re
from pathlib import Path
from style_family import Plate,wrap,FONTS
from recolor_plate import semantic_hash,color_report,contrast

ROOT=Path(__file__).resolve().parents[1]
WHITE=json.loads((ROOT/'assets/white-precision.json').read_text())
SUPPORTED={'sales-review','sales-funnel','sales-waterfall','software-architecture',
 'data-architecture','delivery-workflow','capacity-fishbone','project-gantt',
 'research-distribution','correlation-matrix','ablation-table','neural-network'}

def reshape_text(n,**changes):
 n.update(changes);n['lines']=wrap(n['text'],n['w'],n['fs']);n['h']=len(n['lines'])*n['fs']*1.38

def refine(stem,out,raster=True):
 stem=Path(stem)
 source=json.loads(Path(str(stem)+'.scene.json').read_text())
 data=json.loads(Path(str(stem)+'.input.json').read_text())
 ap=Path(str(stem)+'.analysis.json');analysis=json.loads(ap.read_text()) if ap.exists() else {}
 recipe=re.sub(r'^\d+-','',data['form'])
 if recipe not in SUPPORTED:raise ValueError('White refinements require one of the twelve explicit share-atlas recipes; map a new scene deliberately.')
 if [source['width'],source['height']]!=[3840,2160]:raise ValueError('Current reference refinements expect a 3840 x 2160 source. Re-layout other ratios before adopting these rules.')
 p=Plate.__new__(Plate);p.data=copy.deepcopy(data);p.metrics=copy.deepcopy(analysis)
 p.name='white-precision';p.f=copy.deepcopy(WHITE);p.f.update(relation_ink=WHITE['accent'],secondary_ink=WHITE['muted'])
 p.w=source['width'];p.h=source['height'];p.dpi=240
 p.items=copy.deepcopy(source['items']);p.ids={n['id'] for n in p.items}
 # Use the same locally registered CJK faces in SVG and PNG, with portable fallbacks.
 FONTS['sans']='Heiti SC, PingFang SC, Noto Sans CJK SC, sans-serif'
 original={n['id']:copy.deepcopy(n) for n in p.items};text_exceptions=set();removed=[]
 for n in p.items:
  if n['kind']=='text':
   n['role']='body'
   if n['text']==data['title']:
    reshape_text(n,fs=104,font='serif',weight=400,tone='ink');n['role']='heading'
   elif n['text']==data['subtitle']:
    reshape_text(n,fs=40,tone='muted');n['role']='subtitle'
   elif n['fs']>=112:
    reshape_text(n,weight=500,tone='ink',font='grotesk');n['role']='metric'
   elif n['y']<180 or n['y']>1950:n['role']='metadata'
   elif n['font']=='grotesk':n['role']='numeric'
   elif n['font']=='mono':n['role']='label'
   elif n['tone']=='ink' and n['fs']>=42:
    reshape_text(n,weight=500);n['role']='section'
   if n['text'].startswith(source['palette']['name']+'   /'):
    text_exceptions.add(n['id']);reshape_text(n,text=n['text'].replace(source['palette']['name'],WHITE['name'],1))
   if '蓝墨为正相关，陶土为负相关。' in n['text']:
    text_exceptions.add(n['id']);reshape_text(n,text=n['text'].replace('蓝墨为正相关，陶土为负相关。','正负相关以两种墨色区分。'))
  elif n['kind']=='line':
   n['role']='grid' if n['tone']=='line' else 'mark'
   if n.get('source') or n.get('target'):
    n['role']='relationship';n['lw']=max(2.6,n['lw']);n['cap']='round'
   elif n['tone']=='line':n['lw']=min(n['lw'],1.5)
  elif n['stroke']=='line':n['stroke']='border';n['lw']=max(n['lw'],2.2)

 if recipe=='sales-review':
  for n in p.items:
   if n['kind']=='line' and len(n['points'])==6:
    n['lw']=3.0 if n['dash'] else 5.0;n['role']='target' if n['dash'] else 'actual'
   if n['kind']=='text' and n['role']=='numeric' and n['fs']<=46:reshape_text(n,weight=500)
  for x in (950,1900):p.line([(x,585),(x,865)],'line',1.4,id=f'white-metric-divider-{x}')

 elif recipe=='sales-funnel':
  # Replace decorative hatching by quiet solid bars; count remains encoded by width.
  for n in list(p.items):
   if n['kind']=='line' and n['tone']=='accent' and len(n['points'])==2 and n['points'][0][0]==n['points'][1][0] and abs(n['points'][1][1]-n['points'][0][1])==74:
    p.items.remove(n);removed.append(n['id'])
   elif n['kind']=='rect' and n['h']==74:
    n.update(fill='tint',stroke='accent',lw=2.3,role='count-bar')
    if n['y']==1588:n.update(fill='accent')
   elif n['kind']=='text' and n['font']=='grotesk' and n['y']<1700 and n['fs']<100:
    reshape_text(n,font='mono',fs=44,weight=500 if n['tone']=='ink' else 400)
  for n in p.items:
   if n['kind']=='text' and '细杆为纹理' in n['text']:
    text_exceptions.add(n['id']);reshape_text(n,text='横条从 0 起按人数等比例编码；最后一行深墨对应签约成交，不代表另一种口径。')

 elif recipe=='sales-waterfall':
  for n in list(p.items):
   if n['kind']=='line' and len(n['points'])==2 and n['tone'] in ('accent','cool') and abs(n['points'][1][0]-n['points'][0][0])==144:
    p.items.remove(n);removed.append(n['id'])
   elif n['kind']=='rect' and n['w']==156:
    n['fill']='cool_tint' if n['stroke']=='cool' else 'tint';n['lw']=2.5;n['role']='contribution'
    if n['x'] in (350,2398):n.update(fill='accent',role='total')

 elif recipe in ('software-architecture','data-architecture','delivery-workflow'):
  boxes=[n for n in p.items if n['kind'] in ('rect','diamond')]
  for n in boxes:
   n['role']='decision' if n['kind']=='diamond' else 'node';n['lw']=3 if n['kind']=='diamond' else 2.4
   # A keyline inside every regular node is a common visual convention, not a data encoding.
   if n['kind']=='rect':p.line([(n['x']+1.4,n['y']-1.0),(n['x']+n['w']-1.4,n['y']-1.0)],'accent',3.0,id='white-keyline-'+n['id'])
  for n in p.items:
   if n['kind']=='text' and any(n['x']>=b['x'] and n['x']+n['w']<=b['x']+b['w'] and b['y']<=n['y']<b['y']+b['h'] for b in boxes):
    n['role']='node-title' if n['fs']>=42 else 'node-detail'
    if n['role']=='node-title':reshape_text(n,weight=500,tone='ink')

 elif recipe=='capacity-fishbone':
  for n in p.items:
   if n['kind']=='text' and n['font']=='serif' and n['text']!=data['title']:
    reshape_text(n,font='sans',weight=500,fs=48,tone='ink');n['role']='cause-category'
   elif n['kind']=='line' and n['tone']=='muted':n['lw']=1.8
   elif n['kind']=='text' and n['fs']==36:reshape_text(n,tone='ink')

 elif recipe=='project-gantt':
  for n in p.items:
   if n['id'].startswith('task-'):n.update(fill='tint',stroke='accent',lw=2,role='duration')
   elif n['kind']=='text' and n['text'].endswith(' 天'):reshape_text(n,font='sans',weight=500,fs=36)

 elif recipe=='research-distribution':
  for n in list(p.items):
   if n['kind']=='line' and n['tone']=='line' and len(n['points'])==2 and abs(n['points'][1][0]-n['points'][0][0])<=452 and 700<n['points'][0][1]<1700:
    p.items.remove(n);removed.append(n['id'])
   elif n['kind']=='line' and len(n['points'])>10:n['lw']=2.9;n['role']='density-contour'
   elif n['kind']=='ellipse':n['role']='observation'

 elif recipe=='correlation-matrix':
  for n in p.items:
   if n['kind']=='ellipse' and n['stroke'] in ('accent','cool'):
    n.update(fill='cool_tint' if n['stroke']=='cool' else 'tint',lw=2.2,role='correlation-area')
   elif n['kind']=='text' and n['font']=='grotesk':reshape_text(n,weight=500)

 elif recipe=='ablation-table':
  best=max(range(len(analysis['rows'])),key=lambda i:analysis['rows'][i]['metrics']['f1']['mean'])
  columns={1130:(1000,400),1740:(1590,690),2380:(2540,910)}
  for n in p.items:
   if n['kind']=='text' and 890<n['y']<1640:
    if n['font']=='grotesk':
     oldx=n['x'];nx,nw=columns[oldx];reshape_text(n,x=nx,w=nw,font='mono',fs=44,align='right',tone='ink')
    elif n['fs']>=44:reshape_text(n,weight=500,tone='ink')
    if n['x']==1590 and n['y']==2*(471+best*92):reshape_text(n,weight=700,tone='accent');n['role']='highest-observed-f1'
   elif n['kind']=='text' and n['y']==750 and n['x'] in columns:
    nx,nw=columns[n['x']];reshape_text(n,x=nx,w=nw,align='right',weight=500)

 elif recipe=='neural-network':
  for n in p.items:
   if n['kind']=='line' and len(n['points'])==40:
    if n['tone']=='line':n.update(tone='network_faint',lw=.9,role='context-connection')
    else:n.update(lw=n['lw']*1.15,role='focus-connection')
   if n['kind']=='text' and n['fs']==24:reshape_text(n,fs=26)

 # Protect semantic structure: only non-semantic hatch lines may disappear.
 current={n['id']:n for n in p.items}
 for ident,n in original.items():
  if ident not in current:
   assert n['kind']=='line' and not n.get('source') and not n.get('target') and ident in removed
   continue
  v=current[ident]
  if n['kind']=='line':
   for k in ('points','source','target','arrow','dash'):assert n.get(k)==v.get(k),(ident,k)
  elif n['kind']!='text':
   for k in ('kind','x','y','w','h'):assert n[k]==v[k],(ident,k)
  elif ident not in text_exceptions:assert n['text']==v['text'],ident
 assert p.data==data and p.metrics==analysis
 qa=p.save(out,raster)
 qa.update(recipe=recipe,visual_preset='white-precision',data_sha256=semantic_hash(data),analysis_sha256=semantic_hash(analysis),quantitative_geometry_unchanged=True,relationships_unchanged=True,typography_refined=True,removed_decorative_hatch_lines=len(removed),contrast=color_report(WHITE),border_contrast=round(contrast(WHITE['border'],WHITE['bg']),3),min_text_px=min(n['fs'] for n in p.items if n['kind']=='text'))
 assert min(qa['contrast'].values())>=4.5
 Path(out,f'{data["form"]}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
 return qa

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source');ap.add_argument('--out',required=True);ap.add_argument('--vector-only',action='store_true');args=ap.parse_args()
 print(json.dumps(refine(args.source,args.out,not args.vector_only),ensure_ascii=False))
