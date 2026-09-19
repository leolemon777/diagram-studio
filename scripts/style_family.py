#!/usr/bin/env python3
"""Original cross-form editorial plates. Offline SVG / draw.io / PNG / PDF renderer.

Usage: python style_family.py input.json --family folio --out output
The model is held constant; family controls composition and visual vocabulary.
"""
import argparse,copy,hashlib,html,json,math,re,unicodedata
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
FAMILIES={v['id']:v for v in json.loads((ROOT/'assets/style-families.json').read_text())}
FORMS={'fishbone':'鱼骨分析','architecture':'系统架构','workflow':'闭环流程','trend':'单耗趋势'}
FONTS={'serif':'Songti SC, Noto Serif CJK SC, serif','sans':'PingFang SC, Noto Sans CJK SC, sans-serif','mono':'Menlo, Consolas, PingFang SC, monospace','booknum':'Baskerville, Songti SC, serif','grotesk':'Helvetica Neue, PingFang SC, sans-serif'}
_SYSTEM_FONTS_LOADED=False
def load_system_fonts():
 """Register real TTC faces; Songti.ttc face 0 is Black, not Regular.

 Only local system fonts are expanded into a temporary cache; no font binary
 is added to this skill or its distributed bundle.
 """
 global _SYSTEM_FONTS_LOADED
 if _SYSTEM_FONTS_LOADED:return
 import tempfile
 from fontTools.ttLib import TTCollection
 from matplotlib import font_manager
 cache=Path(tempfile.gettempdir())/'diagram-studio-system-fonts';cache.mkdir(exist_ok=True)
 for path in ['/System/Library/Fonts/Supplemental/Songti.ttc','/System/Library/Fonts/STHeiti Light.ttc','/System/Library/Fonts/STHeiti Medium.ttc','/System/Library/Fonts/Menlo.ttc','/System/Library/Fonts/HelveticaNeue.ttc','/System/Library/Fonts/Supplemental/Baskerville.ttc']:
  p=Path(path)
  if not p.exists():continue
  collection=TTCollection(p,lazy=True);stamp=hashlib.sha256((path+str(p.stat().st_mtime_ns)).encode()).hexdigest()[:12]
  for i,font in enumerate(collection.fonts):
   family=font['name'].getDebugName(1);style=font['name'].getDebugName(2) or ''
   if family not in ('Songti SC','Heiti SC','Menlo','Helvetica Neue','Baskerville') or 'Italic' in style or 'Oblique' in style:continue
   target=cache/f'{stamp}-{i}.ttf'
   if not target.exists():font.save(target)
   font_manager.fontManager.addfont(str(target))
  collection.close()
 _SYSTEM_FONTS_LOADED=True
def width(text,fs):return sum(1 if unicodedata.east_asian_width(c) in 'WF' else .59 for c in text)*fs

def wrap(text,w,fs):
 lines=[]
 for para in str(text).split('\n'):
  line=''
  for c in para:
   if line and width(line+c,fs)>w:lines.append(line);line=''
   line+=c
  lines.append(line)
 return lines

def validate(d):
 if d.get('form') not in FORMS:raise ValueError('form must be fishbone, architecture, workflow or trend')
 for key in ['title','deck','eyebrow','kicker','summary','footer','notes']:
  if not d.get(key):raise ValueError('missing '+key)
 if not isinstance(d['notes'],list) or len(d['notes'])!=3:raise ValueError('provide exactly three concise notes')
 if d['form']=='fishbone':
  cats=d.get('categories',[])
  if len(cats)!=6 or any(len(c.get('causes',[]))!=3 for c in cats):raise ValueError('this plate supports six categories with three causes each; split larger content')
  ids=[v['id'] for c in cats for v in c['causes']]+[c['id'] for c in cats]
 elif d['form']=='architecture':
  if len(d.get('layers',[]))!=3 or any(len(x.get('items',[]))!=2 for x in d['layers']):raise ValueError('this plate supports three layers with two modules each')
  ids=[v['id'] for l in d['layers'] for v in l['items']]
 elif d['form']=='workflow':
  ids=[v['id'] for v in d.get('nodes',[])]
  if len(ids)!=5 or d['nodes'][3].get('kind')!='diamond':raise ValueError('this plate supports five steps and a fourth-step verification decision')
 else:
  if len(d.get('months',[]))!=12 or len(d.get('series',[]))!=2:raise ValueError('this comparison plate expects 12 periods and two series')
  ids=[x['id'] for x in d['series']]
  for x in d['series']:
   vals=x['values']
   if len(vals)!=12 or any(not isinstance(v,(float,int)) or isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in vals):raise ValueError('intensity values must be 12 finite positive measurements')
 if len(ids)!=len(set(ids)):raise ValueError('duplicate semantic IDs')
 if d['form'] in ('architecture','workflow'):
  edges=d.get('edges',[])+[d.get('feedback',[])]
  if any(len(e)!=2 or not set(e)<=set(ids) for e in edges):raise ValueError('invalid relationship endpoint')
 return d

class Plate:
 def __init__(self,data,family,colors=None):
  self.data=validate(copy.deepcopy(data));self.f=copy.deepcopy(FAMILIES[family]);self.name=family;self.w=1600;self.h=1000;self.items=[];self.ids=set();self.metrics={}
  if colors:
   if any(k not in ('bg','ink','accent','muted','line','tint','title_ink','body_ink','secondary_ink','category_ink','relation_ink') or not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for k,v in colors.items()):raise ValueError('color overrides require known color roles with #RRGGBB')
   self.f.update(colors)
   for source,targets in {'ink':['title_ink','body_ink'],'accent':['category_ink','relation_ink'],'muted':['secondary_ink']}.items():
    if source in colors:
     for target in targets:
      if target not in colors:self.f[target]=colors[source]
 def put(self,kind,**kw):
  ident=kw.pop('id',None) or 'visual-'+str(len(self.items)+1)
  if ident in self.ids:raise ValueError('duplicate primitive '+ident)
  self.ids.add(ident);self.items.append(dict(kind=kind,id=ident,**kw));return ident
 def c(self,key):return self.f.get(key,key)
 def text(self,x,y,w,text,fs=20,tone='ink',font=None,weight=400,align='left',id=None):
  lines=wrap(text,w,fs);return self.put('text',x=x,y=y,w=w,h=len(lines)*fs*1.38,lines=lines,text=str(text),fs=fs,tone=tone,font=font or 'sans',weight=weight,align=align,id=id)
 def rect(self,x,y,w,h,fill='none',stroke='line',lw=1,id=None,kind='rect'):
  return self.put(kind,x=x,y=y,w=w,h=h,fill=fill,stroke=stroke,lw=lw,id=id)
 def line(self,pts,tone='line',lw=1,arrow=False,dash=False,source=None,target=None,id=None):
  return self.put('line',points=pts,tone=tone,lw=lw,arrow=arrow,dash=dash,source=source,target=target,id=id)
 def note(self,x,y,w,number,text):
  self.text(x,y,45,number,15,'accent','mono');self.text(x+45,y-2,w-45,text,17,'muted')
 def frame(self):
  d=self.data;f=self.f;name=self.name;tx=self.text;ln=self.line
  tx(80,40,1260,f['english']+'    /    '+d['eyebrow'],14,'muted','mono')
  tx(1370,40,150,'PLATE '+f['number'],14,'muted','mono',align='right')
  if name=='folio':
   ln([(80,82),(1520,82)],'ink',1.2);ln([(80,87),(1520,87)],'line',.7)
   tx(80,114,1180,d['title'],54,font='serif');tx(82,194,1080,d['deck'],22,'muted','serif')
   tx(82,252,900,'图 '+f['number']+'  /  '+FORMS[d['form']],16,'accent');tx(1120,248,400,d['kicker'],20,align='right')
   box=(95,300,1410,465)
   ln([(80,806),(1520,806)],'ink');tx(82,826,1400,d['summary'],21,font='serif')
   for i,n in enumerate(d['notes']):self.note(82+i*485,885,445,f'{i+1:02}',n)
  elif name=='ledger':
   tx(80,104,1140,d['title'],50,weight=500);tx(83,182,1140,d['deck'],21,'muted')
   ln([(80,247),(1520,247)],'ink',1)
   tx(80,278,240,'现场观测 / NOTES',15,'accent','mono');tx(80,325,236,d['kicker'],20,font='serif')
   for i,n in enumerate(d['notes']):self.note(80,460+i*112,247,f'{i+1:02}',n)
   ln([(344,277),(344,866)],'line');tx(380,268,1130,FORMS[d['form']]+'  ·  '+d['summary'],18,'muted')
   box=(380,330,1130,465);tx(380,854,1130,'读图线索  /  '+f['signature'],16,'muted')
  elif name=='cut':
   tx(78,105,1170,d['title'],58,weight=400);tx(80,190,1140,d['deck'],21,'muted')
   tx(1320,90,200,f['number'],110,'accent','sans',300,'right')
   self.rect(80,253,1440,53,'ink','none');tx(102,265,940,FORMS[d['form']]+'    /    '+d['summary'],19,'bg');tx(1090,265,407,d['kicker'],19,'bg',align='right')
   box=(80,350,1440,435)
   ln([(80,825),(1520,825)],'ink',2)
   for i,n in enumerate(d['notes']):
    if i:ln([(80+i*480,843),(80+i*480,917)],'line')
    self.note(94+i*480,865,432,f'{i+1:02}',n)
  elif name=='archive':
   ln([(125,108),(125,918)],'accent',1);tx(57,117,44,'研\n究\n图\n录',26,'accent','serif');tx(57,800,50,f['number'],28,'accent','mono')
   tx(170,105,1340,d['title'],50,font='serif');tx(172,178,1300,d['deck'],22,'muted','serif')
   self.rect(170,244,1350,570,'none','line');self.rect(188,230,250,32,'bg','none');tx(199,234,235,'案卷 '+f['number']+' / '+FORMS[d['form']],16,'accent')
   tx(202,273,1250,d['kicker']+'    ·    '+d['summary'],19,'muted','serif');box=(195,335,1290,445)
   for i,n in enumerate(d['notes']):self.note(174+i*445,862,421,f'{i+1:02}',n)
  elif name=='dune':
   ln([(80,92),(1520,92)],'ink',.8);tx(80,137,295,FORMS[d['form']],17,'accent','serif')
   tx(78,214,308,d.get('narrow_title',d['title']),48,font='serif');tx(80,419,296,d['deck'],20,'muted','serif')
   ln([(80,527),(204,527)],'accent',1.2)
   tx(80,552,294,d['kicker'],26,'accent','serif')
   for i,n in enumerate(d['notes']):self.note(80,663+i*77,298,f'{i+1:02}',n)
   tx(450,154,1070,d['summary'],28,font='serif');box=(430,282,1090,460)
   ln([(450,808),(1520,808)],'line');tx(450,837,1060,'图版 '+f['number']+'    /    '+f['signature'],17,'muted','serif')
  else:
   ln([(80,87),(1520,87)],'line');tx(80,117,1220,d['title'],52,weight=500);tx(82,190,1210,d['deck'],21,'muted')
   self.rect(80,254,1440,560,'none','line');tx(102,269,810,FORMS[d['form']]+'    /    '+d['summary'],17,'accent','mono');tx(1120,269,378,d['kicker'],17,'accent','mono',align='right')
   box=(105,334,1390,424)
   for x,y,sx,sy in [(80,254,1,1),(1520,254,-1,1),(80,814,1,-1),(1520,814,-1,-1)]:ln([(x,y+sy*15),(x,y),(x+sx*15,y)],'accent',1.7)
   for i,n in enumerate(d['notes']):self.note(82+i*485,870,441,f'{i+1:02}',n)
  ln([(80,945),(1520,945)],'line',.8);tx(80,960,1320,d['footer'],14,'muted');tx(1430,960,90,f"{(int(f['number'])-1)*4+list(FORMS).index(d['form'])+1:02d} / 24",13,'muted','mono',align='right')
  return box
 def boxnode(self,x,y,w,h,item):
  name=self.name;ident=item['id'];kind=item.get('kind','rect')
  self.rect(x,y,w,h,'tint' if name in ('cut','graphite') else 'bg','accent' if kind=='diamond' else 'line',1.1,id=ident,kind=kind)
  if name=='ledger' and kind!='diamond':self.line([(x+12,y),(x+12,y+h)],'accent',2)
  if name=='archive' and kind!='diamond':self.line([(x,y),(x+35,y)],'accent',2.3)
  if name=='graphite':
   for px in (x-3,x+w-3):self.rect(px,y+h/2-3,6,6,'accent','none')
  self.text(x+10,y+16,w-20,item['label'],21,'ink',self.f['font'],500,'center',ident+'-label')
  if item.get('detail'):self.text(x+10,y+51,w-20,item['detail'],15,'muted',align='center',id=ident+'-detail')
  return ident
 def fishbone(self,b):
  x,y,w,h=b;d=self.data;mid=y+h*.50;head=145;usable=w-head-15;slot=usable/3
  self.line([(x+4,mid),(x+w-head+20,mid)],'accent',2.2,True,id='cause-spine')
  self.text(x+w-head+18,mid-42,head-18,d.get('effect','产能提升受限').replace('产能提升受限','产能提升\n受限'),22,'ink',self.f['font'],500)
  for i,cat in enumerate(d['categories']):
   top=i<3;col=i%3;left=x+col*slot;tip=left+slot*.56;base=left+slot*.97
   end=y+58 if top else y+h-55
   self.line([(tip,end),(base,mid)],'accent',1.5,source=None,target=None,id='rib-'+cat['id'])
   self.text(left,y+4 if top else y+h-25,slot-8,cat['label'].replace('｜',' / '),20,'accent',self.f['font'],500,id=cat['id'])
   for j,c in enumerate(cat['causes']):
    yy=y+97+j*44 if top else mid+48+j*44
    cx=tip+(base-tip)*(yy-end)/(mid-end)
    self.line([(left+3,yy+7),(cx,yy+7)],'line',.8)
    self.text(left+3,yy-19,min(slot-10,cx-left-6),c.get('display_label',c['label']),16,'ink',id=c['id'])
    if c.get('priority'):self.rect(left-6,yy-12,3,14,'accent','none')
  self.metrics={'category_count':6,'candidate_causes':18,'claim':'hypotheses, not validated root causes'}
 def architecture(self,b):
  x,y,w,h=b;layers=self.data['layers'];vertical=self.name in ('ledger','archive','dune');positions={}
  if vertical:
   nw=(w-235)/2;nh=84;gap=(h-3*nh)/2
   for i,l in enumerate(layers):
    yy=y+i*(nh+gap);self.text(x,yy+24,151,l['name'],21,'accent',self.f['font'],500)
    for j,n in enumerate(l['items']):positions[n['id']]=(x+175+j*(nw+48),yy,nw,nh);self.boxnode(*positions[n['id']],n)
  else:
   gap=85;colw=(w-2*gap)/3;nw=colw-24;nh=88
   for i,l in enumerate(layers):
    xx=x+i*(colw+gap);self.text(xx,y, colw,l['name'],24,'accent',self.f['font'],500)
    self.line([(xx,y+43),(xx+colw,y+43)],'line')
    for j,n in enumerate(l['items']):positions[n['id']]=(xx+12,y+72+j*160,nw,nh);self.boxnode(*positions[n['id']],n)
  for j,(a,c) in enumerate(self.data['edges']):
   ax,ay,aw,ah=positions[a];bx,by,bw,bh=positions[c]
   if vertical and ay==by:pts=[(ax+aw,ay+ah/2),(bx,by+bh/2)]
   elif vertical:pts=[(ax+aw/2,ay+ah),(ax+aw/2,ay+ah+16),(bx+bw/2,ay+ah+16),(bx+bw/2,by)]
   elif ax==bx:pts=[(ax+aw/2,ay+ah),(bx+bw/2,by)]
   else:pts=[(ax+aw,ay+ah/2),(ax+aw+42,ay+ah/2),(ax+aw+42,by+bh/2),(bx,by+bh/2)]
   self.line(pts,'accent',1.5,True,source=a,target=c,id='flow-'+str(j))
  a,c=self.data['feedback'];ax,ay,aw,ah=positions[a];bx,by,bw,bh=positions[c]
  bottom=y+h-12
  # Outer return path avoids other modules; observed on the completed plate.
  if vertical:pts=[(ax+aw,ay+ah/2),(x+w+7,ay+ah/2),(x+w+7,y-16),(bx+bw/2,y-16),(bx+bw/2,by)]
  else:pts=[(ax+aw/2,ay+ah),(ax+aw/2,bottom),(x-10,bottom),(x-10,by+bh/2),(bx,by+bh/2)]
  self.line(pts,'muted',1,True,True,source=a,target=c,id='feedback')
  self.text(x+10,bottom+10,w-20,'虚线：改善措施回到现场复核',14,'muted')
  self.metrics={'module_count':6,'logical_flows':5,'feedback':self.data['feedback']}
 def workflow(self,b):
  x,y,w,h=b;nodes=self.data['nodes'];pos={}
  if self.name in ('ledger','dune','archive'):
   nw=(w-130)/3;nh=90;xs=[x,x+(w-nw)/2,x+w-nw];yy=y+40
   for i,n in enumerate(nodes):
    xx=xs[i] if i<3 else xs[2 if i==3 else 1];ny=yy if i<3 else yy+240;pos[n['id']]=(xx,ny,nw,nh);self.boxnode(*pos[n['id']],n)
  else:
   nw=(w-160)/5;nh=100
   for i,n in enumerate(nodes):pos[n['id']]=(x+i*(nw+40),y+140,nw,nh);self.boxnode(*pos[n['id']],n)
  for j,(a,c) in enumerate(self.data['edges']):
   ax,ay,aw,ah=pos[a];bx,by,bw,bh=pos[c]
   if ay==by:pts=[(ax+aw if bx>ax else ax,ay+ah/2),(bx if bx>ax else bx+bw,by+bh/2)]
   else:pts=[(ax+aw/2,ay+ah),(bx+bw/2,by)]
   self.line(pts,'accent',1.6,True,source=a,target=c,id='process-'+str(j))
   if a=='verify':
    mx=(pts[0][0]+pts[-1][0])/2;self.text(mx-17,pts[0][1]-32,46,'是',16,'accent')
  a,c=self.data['feedback'];ax,ay,aw,ah=pos[a];bx,by,bw,bh=pos[c]
  if ay==by:
   bottom=ay+ah+96;pts=[(ax+aw/2,ay+ah),(ax+aw/2,bottom),(bx+bw/2,bottom),(bx+bw/2,by+bh)];self.text((ax+bx)/2, bottom+14,330,'否 / 重新处置',17,'muted')
  else:
   right=x+w+10;pts=[(ax+aw,ay+ah/2),(right,ay+ah/2),(right,by+bh/2),(bx+bw,by+bh/2)];self.text(right-47,by+bh+83,42,'否',17,'muted')
  self.line(pts,'muted',1.2,True,True,source=a,target=c,id='rework')
  self.metrics={'steps':5,'verification_outcomes':['yes','no'],'rework':self.data['feedback']}
 def trend(self,b):
  x,y,w,h=b;d=self.data;left=x+54;top=y+44;pw=w-145;ph=h-112
  normalized={s['id']:[v/s['values'][0]*100 for v in s['values']] for s in d['series']};allv=sum(normalized.values(),[])
  lo=5*math.floor((min(allv)-2)/5);hi=5*math.ceil((max(allv)+2)/5)
  self.text(x,y-5,w,'单耗指数 / 1 月 = 100',16,'muted')
  for v in range(lo,hi+1,5):
   yy=top+ph*(hi-v)/(hi-lo);self.line([(left,yy),(left+pw,yy)],'muted' if v==100 else 'line',1 if v==100 else .5,dash=v==100)
   self.text(x,yy-11,42,str(v),15,'muted','mono',align='right')
  for i,m in enumerate(d['months']):
   xx=left+pw*i/11;self.text(xx-24,top+ph+16,48,m,15,'muted',align='center')
  for k,s in enumerate(d['series']):
   tone='accent' if k==0 else 'ink';points=[(left+pw*i/11,top+ph*(hi-v)/(hi-lo)) for i,v in enumerate(normalized[s['id']])]
   self.line(points,tone,2.1 if k==0 else 1.45,False,k==1,id=s['id'])
   for i,(xx,yy) in enumerate(points):
    # Each mark corresponds to one observed period; no invented unit glyphs.
    if self.name=='ledger':self.line([(xx,yy-6),(xx,yy+6)],tone,1.4,id=s['id']+'-'+str(i))
    else:self.rect(xx-3,yy-3,6,6,'bg',tone,1.1,id=s['id']+'-'+str(i),kind='ellipse' if k==0 else 'rect')
   ly=top-30+k*23;self.line([(left+pw-180,ly+10),(left+pw-148,ly+10)],tone,1.6,dash=k==1);self.text(left+pw-137,ly,134,s['label'],15,tone)
   val=normalized[s['id']][-1];other=normalized[d['series'][1-k]['id']][-1];dy=-27 if val>other or (val==other and k==0) else 6;self.text(left+pw+15,points[-1][1]+dy,80,f'{val:.1f}',19,tone,'mono')
  self.metrics={'index_base':d['months'][0],'normalized':normalized,'axis_min':lo,'axis_max':hi,'raw_units':{s['id']:s['unit'] for s in d['series']}}
 def build(self):
  b=self.frame();getattr(self,self.data['form'])(b);self.refine_visual_roles();return self
 def refine_visual_roles(self):
  """Apply family-specific text and line grammar after semantic layout.

  Coordinates, endpoints and measured values are left unchanged. Roles are
  retained in the scene so a future editor can revise them explicitly.
  """
  ty=self.f.get('type');st=self.f.get('stroke')
  if not ty or not st:return
  causes={c['id'] for g in self.data.get('categories',[]) for c in g['causes']}
  groups={g['id'] for g in self.data.get('categories',[])}
  titles={self.data['title'],self.data.get('narrow_title',self.data['title'])}
  for n in self.items:
   if n['kind']=='text':
    tone=n['tone'];role='body'
    if n['text'] in titles:role='heading';n.update(font=ty['heading_font'],weight=ty['heading_weight'],tone='title_ink')
    elif n['id'] in causes:role='cause';n.update(font=ty['body_font'],weight=ty['body_weight'],fs=ty['cause_size'],tone='body_ink')
    elif n['id'] in groups or (tone=='accent' and 20<=n['fs']<=26):role='category';n.update(font=ty['category_font'],weight=ty['category_weight'],tone='category_ink')
    elif n['id'].endswith('-label'):role='node';n.update(font=ty['body_font'],weight=ty['node_weight'],fs=ty['node_size'],tone='body_ink')
    elif n['font']=='mono' or n['text']==self.data['kicker']:role='numeric' if any(c.isdigit() for c in n['text']) else 'meta';n.update(font=ty['numeric_font'] if role=='numeric' else 'mono')
    elif n['fs']>=36:role='display';n.update(font=ty['numeric_font'])
    elif n['fs']<=18:role='annotation';n.update(font=ty['note_font'])
    elif n['font']=='serif':n.update(font=ty['body_font'])
    if tone=='ink' and n['tone']=='ink':n['tone']='body_ink'
    if tone=='muted' and n['tone']=='muted':n['tone']='secondary_ink'
    n['role']=role;n['lines']=wrap(n['text'],n['w'],n['fs']);n['h']=len(n['lines'])*n['fs']*1.38
   elif n['kind']=='line':
    ident=n['id'];role='rule'
    if ident=='cause-spine':role='spine';n['lw']=st['spine']
    elif ident.startswith('rib-'):role='rib';n['lw']=st['rib']
    elif n.get('source') or ident.startswith(('flow-','process-')):role='relation';n['lw']=st['main']
    elif n['tone']=='line':role='hairline';n['lw']=st['hair']
    elif ident in [v['id'] for v in self.data.get('series',[])]:role='series';n['lw']*=st['main']/1.5
    if n['tone']=='accent':n['tone']='relation_ink'
    if n['tone']=='muted':n['tone']='secondary_ink'
    n.update(role=role,cap=st['cap'],arrow_style=st['arrow'],dash_pattern=st['dash'])
   elif n['stroke']!='none':
    n['lw']=st['frame']
 def audit(self):
  errors=[]
  for n in self.items:
   if n['kind']=='line':
    if any(not math.isfinite(float(q)) for p in n['points'] for q in p):errors.append(n['id']+': nonfinite path')
    if any(not (0<=x<=self.w and 0<=y<=self.h) for x,y in n['points']):errors.append(n['id']+': path outside canvas')
   elif n['x']<0 or n['y']<0 or n['x']+n['w']>self.w or n['y']+n['h']>self.h:errors.append(n['id']+': outside canvas')
  return {'errors':errors,'semantic_sha256':hashlib.sha256(json.dumps(self.data,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'scope':'bounds and same-input digest; visual inspection recorded separately'}
 def svg(self):
  esc=lambda v:html.escape(str(v),quote=True);c=self.c
  out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="plate-title"><title id="plate-title">{esc(self.data["title"])} · {esc(self.f["name"])}</title>',f'<rect width="{self.w}" height="{self.h}" fill="{c("bg")}"/>','<defs>']
  arrow_style=self.f.get('stroke',{}).get('arrow','open')
  for t in ('accent','muted','ink','relation_ink','secondary_ink'):
   shape='M0 1 L9 5 L0 9'+(' Z' if arrow_style!='open' else '')
   fill=c(t) if arrow_style=='filled' else c('bg') if arrow_style=='hollow' else 'none'
   out.append(f'<marker id="arrow-{t}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="{shape}" fill="{fill}" stroke="{c(t)}" stroke-width="1.0"/></marker>')
  out.append('</defs>')
  # All relationships are under node fills. Panels precede their text.
  ordered=[n for n in self.items if n['kind']=='line']+[n for n in self.items if n['kind']!='line']
  for n in ordered:
   kind=n['kind'];attrs=f'id="{esc(n["id"])}"'
   if kind=='line':
    points=' '.join(f'{x},{y}' for x,y in n['points']);pattern=' '.join(str(v) for v in n.get('dash_pattern',[6,5]));dash=f' stroke-dasharray="{pattern}"' if n['dash'] else '';arrow=f' marker-end="url(#arrow-{n["tone"]})"' if n['arrow'] else ''
    out.append(f'<polyline {attrs} points="{points}" fill="none" stroke="{c(n["tone"])}" stroke-width="{n["lw"]}" stroke-linecap="{n.get("cap","butt")}" stroke-linejoin="miter"{dash}{arrow}/>');continue
   x,y,w,h=[n[k] for k in ('x','y','w','h')];attrs+=f' data-box="{x},{y},{w},{h}"'
   if kind=='text':
    align=n['align'];anchor={'left':'start','right':'end','center':'middle'}[align];xx=x+(w if align=='right' else w/2 if align=='center' else 0)
    out.append(f'<g {attrs} font-family="{FONTS[n["font"]]}" font-size="{n["fs"]}" font-weight="{n["weight"]}" fill="{c(n["tone"])}" text-anchor="{anchor}">')
    for i,line in enumerate(n['lines']):out.append(f'<text x="{xx}" y="{y+n["fs"]+i*n["fs"]*1.38}">{esc(line)}</text>')
    out.append('</g>');continue
   sty=f'fill="{c(n["fill"])}" stroke="{c(n["stroke"])}" stroke-width="{n["lw"]}"'
   if kind=='ellipse':out.append(f'<ellipse {attrs} cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" {sty}/>')
   elif kind=='diamond':out.append(f'<polygon {attrs} points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" {sty}/>')
   else:out.append(f'<rect {attrs} x="{x}" y="{y}" width="{w}" height="{h}" {sty}/>')
  return '\n'.join(out+['</svg>'])
 def drawio(self):
  mx=ET.Element('mxfile',host='diagram-studio');dg=ET.SubElement(mx,'diagram',name=self.data['title']);model=ET.SubElement(dg,'mxGraphModel',page='1',pageScale='1',pageWidth=str(self.w),pageHeight=str(self.h),background=self.c('bg'));root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
  for n in [v for v in self.items if v['kind']=='line']+[v for v in self.items if v['kind']!='line']:
   k=n['kind'];attrs=dict(id=n['id'],parent='1')
   if k=='line':
    arrow='none' if not n['arrow'] else 'open' if n.get('arrow_style','open')=='open' else 'block'
    pattern=' '.join(str(v/n['lw']) for v in n.get('dash_pattern',[6,5]))
    attrs.update(edge='1',value='',style=f'edgeStyle=none;rounded=0;strokeColor={self.c(n["tone"])};strokeWidth={n["lw"]};dashed={int(n["dash"])};dashPattern={pattern};endArrow={arrow};endFill={int(n.get("arrow_style")=="filled")};lineCap={n.get("cap","butt")};')
    # Native vertices remain separate from captions. Explicit ports keep connectors attached.
    for endpoint,index in [('source',0),('target',-1)]:
     if n.get(endpoint):
      attrs[endpoint]=n[endpoint];node=next(q for q in self.items if q['id']==n[endpoint]);px,py=n['points'][index];pre='exit' if endpoint=='source' else 'entry';attrs['style']+=f'{pre}X={(px-node["x"])/node["w"]};{pre}Y={(py-node["y"])/node["h"]};{pre}Perimeter=0;'
    cell=ET.SubElement(root,'mxCell',**attrs);geo=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
    for endpoint,point in [('source',n['points'][0]),('target',n['points'][-1])]:
     if not n.get(endpoint):ET.SubElement(geo,'mxPoint',x=str(point[0]),y=str(point[1]),attrib={'as':endpoint+'Point'})
    if len(n['points'])>2:
     arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
     for x,y in n['points'][1:-1]:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    continue
   if k=='text':
    style=f'shape=text;html=1;whiteSpace=wrap;overflow=visible;fillColor=none;strokeColor=none;spacing=0;verticalAlign=top;align={n["align"]};fontFamily={FONTS[n["font"]].split(",")[0]};fontSize={n["fs"]};fontColor={self.c(n["tone"])};fontStyle={1 if n["weight"]>=500 else 0};'
    value='<div style="line-height:1.38">'+'<br>'.join(html.escape(v) for v in n['lines'])+'</div>'
   else:
    style=f'shape={"rhombus" if k=="diamond" else "rectangle" if k=="rect" else k};rounded=0;fillColor={self.c(n["fill"])};strokeColor={self.c(n["stroke"])};strokeWidth={n["lw"]};';value=''
   attrs.update(vertex='1',style=style,value=value);cell=ET.SubElement(root,'mxCell',**attrs);ET.SubElement(cell,'mxGeometry',x=str(n['x']),y=str(n['y']),width=str(n['w']),height=str(n['h']),attrib={'as':'geometry'})
  return ET.tostring(mx,encoding='unicode',xml_declaration=True)
 def raster(self,dest):
  import matplotlib;matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  from matplotlib import font_manager
  from matplotlib.patches import Rectangle,Ellipse,Polygon,FancyArrowPatch
  load_system_fonts()
  available={f.name for f in font_manager.fontManager.ttflist};sans=next((f for f in ['Heiti SC','Heiti TC','PingFang SC','Noto Sans CJK SC'] if f in available),'DejaVu Sans');serif=next((f for f in ['Songti SC','Noto Serif CJK SC'] if f in available),sans)
  fonts={'sans':sans,'serif':serif,'mono':'Menlo' if 'Menlo' in available else sans,'booknum':'Baskerville' if 'Baskerville' in available else serif,'grotesk':'Helvetica Neue' if 'Helvetica Neue' in available else sans}
  with plt.rc_context({'pdf.fonttype':42,'axes.unicode_minus':False}):
   dpi=getattr(self,'dpi',100);pt=72/dpi
   fig=plt.figure(figsize=(self.w/dpi,self.h/dpi),dpi=dpi,facecolor=self.c('bg'));ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,self.w),ylim=(self.h,0));ax.axis('off')
   for z,n in enumerate([v for v in self.items if v['kind']=='line']+[v for v in self.items if v['kind']!='line']):
    k=n['kind'];order=z+1
    if k=='line':
     xs,ys=zip(*n['points']);cap='projecting' if n.get('cap')=='square' else n.get('cap','butt');ax.plot(xs,ys,color=self.c(n['tone']),lw=n['lw']*pt,ls=(0,n.get('dash_pattern',[6,5])) if n['dash'] else '-',solid_capstyle=cap,dash_capstyle=cap,zorder=order)
     if n['arrow']:
      mode=n.get('arrow_style','open');ax.add_patch(FancyArrowPatch(n['points'][-2],n['points'][-1],arrowstyle='->' if mode=='open' else '-|>',mutation_scale=11 if not hasattr(self,'canvas') else 7*n['lw']*pt,linewidth=n['lw']*pt,edgecolor=self.c(n['tone']),facecolor=self.c(n['tone']) if mode=='filled' else self.c('bg'),zorder=order))
     continue
    x,y,w,h=[n[q] for q in ('x','y','w','h')]
    if k=='text':
     xx=x+(w if n['align']=='right' else w/2 if n['align']=='center' else 0)
     for i,line in enumerate(n['lines']):ax.text(xx,y+n['fs']+i*n['fs']*1.38,line,fontsize=n['fs']*pt,fontfamily=[fonts[n['font']],serif if n['font']=='booknum' else sans],fontweight=n['weight'],color=self.c(n['tone']),ha=n['align'],va='baseline',zorder=order)
    else:
     kw=dict(facecolor=self.c(n['fill']),edgecolor=self.c(n['stroke']),linewidth=n['lw']*pt,zorder=order)
     patch=Ellipse((x+w/2,y+h/2),w,h,**kw) if k=='ellipse' else Polygon([(x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2)],**kw) if k=='diamond' else Rectangle((x,y),w,h,**kw);ax.add_patch(patch)
   for ext in ('png','pdf'):fig.savefig(str(dest)+'.'+ext,dpi=dpi,facecolor=self.c('bg'))
   plt.close(fig)
 def save(self,out,raster=True):
  out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=out/self.data['form'];qa=self.audit()
  if qa['errors']:raise ValueError(qa['errors'])
  def js(suffix,value):Path(str(stem)+suffix).write_text(json.dumps(value,ensure_ascii=False,indent=2))
  if hasattr(self,'canvas'):
   qa['canvas']=self.canvas;qa['warnings']=['Small exported text: raise pixel dimensions or simplify content.'] if min(n['fs'] for n in self.items if n['kind']=='text')<12 else []
   js('.canvas.json',self.canvas)
  Path(str(stem)+'.svg').write_text(self.svg());Path(str(stem)+'.drawio').write_text(self.drawio());js('.input.json',self.data);js('.scene.json',dict(family=self.name,palette=self.f,width=self.w,height=self.h,canvas=getattr(self,'canvas',None),items=self.items));js('.analysis.json',self.metrics);js('.qa.json',qa)
  if raster:self.raster(stem)
  return qa

def main():
 from canvas_layout import arguments,from_args,apply_canvas
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--family',choices=list(FAMILIES),default='folio');p.add_argument('--out',required=True);p.add_argument('--colors',help='JSON object of six optional color tokens');p.add_argument('--vector-only',action='store_true');arguments(p);a=p.parse_args();d=json.loads(Path(a.input).read_text());plate=Plate(d,a.family,json.loads(a.colors) if a.colors else None).build();apply_canvas(plate,from_args(a));print(json.dumps(plate.save(a.out,not a.vector_only),ensure_ascii=False))
if __name__=='__main__':main()
