#!/usr/bin/env python3
"""Data-first editorial chart plates, independently authored for Diagram Studio.

python data_art.py input.json --out output --mode detail --theme warm
SVG/draw.io/JSON/CSV use the standard library; PNG/PDF use Matplotlib/fontTools.
"""
import argparse, copy, csv, datetime as dt, html, io, json, math, re, statistics
from pathlib import Path
import xml.etree.ElementTree as ET
from style_family import Plate, ROOT, width, wrap

PALETTES={x['id']:x for x in json.loads((ROOT/'assets/editorial-palettes.json').read_text())}
RECIPES={
 'rungs':('刻度柱','RUNG STUDY'), 'barcode':('日序条码','DAILY REGISTER'),
 'area':('细线面积','LOAD ENVELOPE'), 'ring':('计量环','MEASURED CIRCLE'),
 'field':('百点构成','COUNTED FIELD'), 'dumbbell':('前后哑铃','PAIRED CHANGE'),
 'scatter':('垂线散点','PAIRED OBSERVATIONS'), 'matrix':('面积点阵','SHIFT MATRIX'),
 'distribution':('样本与箱线','SAMPLE DISTRIBUTION'), 'waterfall':('增减分解','CHANGE ACCOUNT'),
 'multiples':('指数小多图','COMMON BASELINE'), 'parallel':('多维剖面','OPERATING PROFILES')}

DATA_ART_UI={
 'zh':{
  'recipe_label':{'dumbbell':'前后哑铃','waterfall':'增减分解'},
  'mode_detail':'细读 · 逐项看数据','mode_clear':'快读 · 先看整体',
  'reading_guide':'读图约定','observation':'01  观察','boundary':'02  边界',
  'synthetic':'模拟数据','source':'来源数据',
 },
 'en':{
  'recipe_label':{'dumbbell':'Before / after dumbbell','waterfall':'Change waterfall'},
  'mode_detail':'Detail · read each value','mode_clear':'Clear · compare at a glance',
  'reading_guide':'Reading guide','observation':'01  Observation','boundary':'02  Boundary',
  'synthetic':'Synthetic data','source':'Source data',
 },
}

def number(v, nonnegative=False):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('expected a finite number')
 if nonnegative and v<0:raise ValueError('this encoding requires nonnegative values')
 return v

def fmt(v):
 if v is None:return '缺测'
 return f'{v:,.0f}' if abs(v-round(v))<1e-8 else f'{v:,.2f}'.rstrip('0').rstrip('.')

def quantile(values,p):
 s=sorted(values);q=(len(s)-1)*p;i=math.floor(q);j=math.ceil(q)
 return s[i]+(s[j]-s[i])*(q-i)

def box_stats(values):
 q1,med,q3=[quantile(values,p) for p in (.25,.5,.75)];iqr=q3-q1
 inside=[v for v in values if q1-1.5*iqr<=v<=q3+1.5*iqr]
 return dict(n=len(values),q1=q1,median=med,q3=q3,low=min(inside),high=max(inside),outliers=[v for v in values if v<q1-1.5*iqr or v>q3+1.5*iqr])

def validate(d):
 recipe=d.get('recipe');rows=d.get('rows')
 if recipe not in RECIPES:raise ValueError('unknown recipe')
 if d.get('language','zh') not in DATA_ART_UI:raise ValueError('language must be zh or en')
 for k in ('title','subtitle','source','period','unit'):
  if not isinstance(d.get(k),str) or not d[k].strip():raise ValueError('missing '+k)
 if not isinstance(d.get('synthetic'),bool):raise ValueError('synthetic must be explicit')
 if not isinstance(rows,list) or not rows:raise ValueError('rows must be a nonempty list')
 ids=[r.get('id') for r in rows]
 if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):raise ValueError('unique string row IDs required')
 for r in rows:
  if not isinstance(r.get('label'),str) or not r['label']:raise ValueError('every row needs a label')
 limits={'rungs':8,'barcode':180,'area':120,'ring':6,'field':6,'dumbbell':7,'scatter':100,'matrix':80,'distribution':5,'waterfall':7,'multiples':4,'parallel':6}
 if len(rows)>limits[recipe]:raise ValueError('split this chart into readable panels')
 if recipe in ('rungs','barcode','area','ring','field','matrix','waterfall'):
  for r in rows:
   if r.get('value') is None and recipe in ('barcode','area','matrix'):continue
   number(r.get('value'),recipe!='waterfall')
 if recipe in ('rungs','ring','waterfall'):
  number(d.get('quantum'),True)
  if not d['quantum']>0:raise ValueError('quantum must be positive')
 if recipe in ('ring','field'):
  if sum(r['value'] for r in rows)<=0:raise ValueError('composition total must be positive')
  if recipe=='field' and (len(rows)>3 or any(int(r['value'])!=r['value'] for r in rows) or sum(r['value'] for r in rows)>200):raise ValueError('counted field needs at most three classes and 200 integer observations')
 if recipe in ('barcode','area'):
  dates=[dt.datetime.fromisoformat(r['date']) for r in rows]
  if len(dates)<2 or any(b<=a for a,b in zip(dates,dates[1:])):raise ValueError('strictly increasing ISO dates required')
  if not any(r['value'] is not None for r in rows):raise ValueError('no measured observations')
 if recipe=='dumbbell':
  for r in rows:number(r.get('before'),True);number(r.get('after'),True)
 if recipe=='scatter':
  for k in ('x_unit','y_unit','x_label','y_label'):
   if not d.get(k):raise ValueError('missing '+k)
  for r in rows:number(r.get('x'));number(r.get('y'))
  if len(rows)<2:raise ValueError('scatter requires two paired observations')
 if recipe=='matrix':
  xs=d.get('columns',[]);ys=d.get('groups',[])
  if not 1<=len(xs)<=12 or not 1<=len(ys)<=6 or len(set(xs))!=len(xs) or len(set(ys))!=len(ys):raise ValueError('invalid matrix categories')
  cells=[(r.get('column'),r.get('group')) for r in rows]
  if len(cells)!=len(set(cells)) or set(cells)!={(x,y) for x in xs for y in ys}:raise ValueError('matrix needs each cell exactly once; use null for missing')
 if recipe=='distribution':
  for r in rows:
   if not isinstance(r.get('values'),list) or not 2<=len(r['values'])<=150:raise ValueError('distribution needs 2–150 observations per group')
   for v in r['values']:number(v)
 if recipe=='waterfall':
  number(d.get('start'),True)
 if recipe=='multiples':
  dates=[dt.datetime.fromisoformat(t) for t in d.get('dates',[])]
  if not 2<=len(dates)<=48 or any(b<=a for a,b in zip(dates,dates[1:])):raise ValueError('strict dates required')
  for r in rows:
   if not r.get('unit') or len(r.get('values',[]))!=len(dates):raise ValueError('aligned series with original units required')
   for v in r['values']:
    if v is not None:number(v,True)
   if r['values'][0] is None or r['values'][0]<=0:raise ValueError('first baseline must be positive')
 if recipe=='parallel':
  dims=d.get('dimensions',[])
  if not 3<=len(dims)<=6:raise ValueError('parallel requires 3–6 dimensions')
  keys=[a['id'] for a in dims]
  if len(keys)!=len(set(keys)):raise ValueError('duplicate dimension')
  for a in dims:
   number(a.get('min'));number(a.get('max'))
   if a['max']<=a['min'] or not a.get('unit'):raise ValueError('fixed dimension ranges and units required')
  for r in rows:
   if set(r.get('values',{}))!=set(keys):raise ValueError('dimension keys must match')
   for a in dims:
    v=number(r['values'][a['id']])
    if not a['min']<=v<=a['max']:raise ValueError('value outside declared scale')
 return d

def analyse(d):
 validate(d);rows=d['rows'];r=d['recipe'];a={'recipe':r,'row_count':len(rows),'unit':d['unit'],'synthetic':d['synthetic']}
 if r in ('rungs','barcode','area','ring','field','matrix'):
  good=[v for v in rows if v['value'] is not None];vals=[v['value'] for v in good]
  a.update(total=sum(vals),mean=statistics.mean(vals),minimum=min(vals),maximum=max(vals),missing=len(rows)-len(good),peak_ids=[v['id'] for v in good if v['value']==max(vals)])
  if r in ('ring','field'):a['shares']={v['id']:v['value']/sum(vals)*100 for v in rows}
 elif r=='dumbbell':
  a['changes']={v['id']:{'before':v['before'],'after':v['after'],'delta':v['after']-v['before'],'percent':(v['after']/v['before']-1)*100 if v['before'] else None} for v in rows}
 elif r=='scatter':
  xs=[v['x'] for v in rows];ys=[v['y'] for v in rows];xm=statistics.mean(xs);ym=statistics.mean(ys)
  den=math.sqrt(sum((x-xm)**2 for x in xs)*sum((y-ym)**2 for y in ys))
  a['pearson_r']=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/den if den else None
 elif r=='distribution':a['groups']={v['id']:box_stats(v['values']) for v in rows}
 elif r=='waterfall':
  running=d['start'];steps=[]
  for v in rows:steps.append(dict(id=v['id'],start=running,end=running+v['value'],delta=v['value']));running+=v['value']
  a.update(start=d['start'],end=running,net=running-d['start'],steps=steps)
 elif r=='multiples':a['indexed']={v['id']:[x/v['values'][0]*100 if x is not None else None for x in v['values']] for v in rows}
 else:a['normalized']={v['id']:[(v['values'][a['id']]-a['min'])/(a['max']-a['min']) for a in d['dimensions']] for v in rows}
 return a

def scale(vals,zero=False):
 vals=[v for v in vals if v is not None];lo=min(vals);hi=max(vals)
 if zero:lo=min(0,lo)
 gap=(hi-lo)*.1 or max(abs(hi)*.1,1)
 if not zero:lo-=gap
 hi+=gap
 step=nice_step((hi-lo)/4)
 return math.floor(lo/step)*step,math.ceil(hi/step)*step

def nice_step(raw):
 power=10**math.floor(math.log10(raw));ratio=raw/power
 return next(k for k in (1,2,2.5,5,10) if k>=ratio-1e-10)*power

def ticks(lo,hi,n=4):
 step=nice_step((hi-lo)/n);first=math.ceil(lo/step-1e-10)*step
 return [first+i*step for i in range(math.floor((hi-first)/step+1e-10)+1)]

class DataPlate(Plate):
 def __init__(self,data,mode='detail',theme='warm'):
  if mode not in ('detail','clear'):raise ValueError('unknown reading mode')
  if theme not in PALETTES:raise ValueError('unknown theme')
  self.data=validate(copy.deepcopy(data));self.data['form']=data['recipe'];self.language=self.data.get('language','zh');self.metrics=analyse(data)
  self.mode=mode;self.name=theme;self.f=copy.deepcopy(PALETTES[theme]);self.f.update(relation_ink=self.f['accent'],secondary_ink=self.f['muted'])
  if self.language=='en':self.f['name']=self.f.get('en',self.f['name'])
  self.items=[];self.ids=set();self.w=1600;self.h=1000;self.tags={};self.detail=mode=='detail';self.box=(150,330,980,440)
  self.rows=self.data['rows'];self.recipe=data['recipe'];self.encoding='';self.reading='';self.caveat='';self.kpi='';self.kpi_label=''
 def ui(self,key):return DATA_ART_UI[self.language].get(key,key)
 def recipe_label(self):return DATA_ART_UI[self.language]['recipe_label'].get(self.recipe,RECIPES[self.recipe][0])
 def text(self,x,y,w,text,fs=20,tone='ink',font=None,weight=400,align='left',id=None):
  # Keep numbers and Latin words intact; never start a line with closing punctuation.
  lines=[]
  for para in str(text).split('\n'):
   tokens=re.findall(r'[A-Za-z0-9]+(?:[.,:/+-][A-Za-z0-9]+)*%?|.',para)
   line=[]
   for token in tokens:
    if line and width(''.join(line)+token,fs)>w:
     carry=[]
     if token in '，。、；：！？）】》％' and len(line)>1:carry=[line.pop()]
     lines.append(''.join(line).rstrip());line=carry
    if line or not token.isspace():line.append(token)
   lines.append(''.join(line).rstrip())
  return self.put('text',x=x,y=y,w=w,h=len(lines)*fs*1.38,lines=lines,text=str(text),fs=fs,tone=tone,font=font or 'sans',weight=weight,align=align,id=id)
 def mark(self,ident,row,tip):self.tags[ident]={'record':row['id'],'tip':tip};return ident
 def dot(self,x,y,r=4,tone='accent',hollow=False,ident=None):return self.rect(x-r,y-r,2*r,2*r,'bg' if hollow else tone,tone,1.4,id=ident,kind='ellipse')
 def seg(self,x1,y1,x2,y2,tone='line',lw=1,dash=False):return self.line([(x1,y1),(x2,y2)],tone,lw,dash=dash)
 def label(self,x,y,w,text,fs=17,tone='muted',align='left'):return self.text(x,y,w,text,fs,tone,'sans',400,align)
 def num(self,x,y,w,value,fs=23,tone='ink',align='left'):return self.text(x,y,w,fmt(value),fs,tone,'grotesk',500,align)
 def axis(self,lo,hi,x=None,y=None,w=None,h=None,unit=None):
  bx,by,bw,bh=self.box;x=bx if x is None else x;y=by if y is None else y;w=bw if w is None else w;h=bh if h is None else h
  for v in ticks(lo,hi):
   yy=y+h*(hi-v)/(hi-lo);self.seg(x,yy,x+w,yy,'line',.6);self.num(x-78,yy-12,63,v,16,'muted','right')
  self.label(x-60,y-43,w,unit or self.data['unit'],17)
  return lambda v:y+h*(hi-v)/(hi-lo)
 def horizontal_axis(self,lo,hi,x,y,w,h,unit):
  for v in ticks(lo,hi):
   xx=x+(v-lo)/(hi-lo)*w;self.seg(xx,y,xx,y+h,'line',.7);self.num(xx-50,y+h+20,100,v,16,'muted','center')
  self.label(x,y+h+60,w,unit,17,align='right')
  return lambda v:x+(v-lo)/(hi-lo)*w
 def frame(self):
  d=self.data;order=list(RECIPES).index(self.recipe)+1
  self.text(80,39,1150,f'APAT    /    DATA STUDIES    /    {RECIPES[self.recipe][1]}',14,'muted','mono')
  self.text(1340,39,180,f'{order:02d} / 12',14,'muted','mono',align='right')
  self.seg(80,82,1520,82,'ink',1.0)
  self.text(78,105,1440,d['title'],49,'ink','serif',400)
  self.label(81,183,1425,d['subtitle'],21)
  self.label(81,247,900,d['period']+'  /  '+self.recipe_label(),16,'accent')
  self.label(1160,247,360,(self.ui('mode_detail') if self.detail else self.ui('mode_clear')),16,'accent','right')
  self.seg(1195,316,1195,809,'line',.8)
 def side(self):
  self.text(1240,316,276,str(self.kpi),60,'accent','grotesk',400)
  self.label(1244,399,269,self.kpi_label,18)
  self.seg(1244,449,1518,449,'line',.8)
  self.text(1244,474,265,self.ui('observation'),14,'accent','mono')
  reading_fs=18 if self.language=='en' else 20
  caveat_fs=16 if self.language=='en' else 18
  reading_height=len(wrap(self.reading,269,reading_fs))*reading_fs*1.38
  boundary_y=max(643,507+reading_height+22)
  self.label(1244,507,269,self.reading,reading_fs,'ink')
  self.text(1244,boundary_y,265,self.ui('boundary'),14,'accent','mono')
  self.label(1244,boundary_y+33,269,self.caveat,caveat_fs)
  self.seg(80,851,1520,851,'ink',.8)
  self.label(80,873,130, self.ui('reading_guide'),16,'accent')
  self.label(220,871,1295,self.encoding,18,'ink')
  flag=self.ui('synthetic') if self.data['synthetic'] else self.ui('source')
  self.label(80,950,1370,flag+' · '+self.data['source'],14)
  self.label(1420,950,100,'APAT',14,'muted','right')
 def build(self):
  self.frame();start=len(self.items);getattr(self,self.recipe)();self.plot_ids={n['id'] for n in self.items[start:]};self.side();return self
 def rungs(self):
  x,y,w,h=self.box;rows=sorted(self.rows,key=lambda r:r['value'],reverse=True);mx=max(r['value'] for r in rows);lo,hi=scale([0,mx],True);Y=self.axis(lo,hi);quant=self.data['quantum'];slot=w/len(rows)
  if mx/quant>180:raise ValueError('too many ticks; choose a larger declared quantum')
  for i,r in enumerate(rows):
   xx=x+(i+.5)*slot;v=r['value'];tip=r['label']+'：'+fmt(v)+' '+self.data['unit'];ww=min(slot*.38,64)
   if self.detail:
    full=math.floor(v/quant)
    for k in range(full):self.mark(self.seg(xx-ww/2,Y((k+.5)*quant),xx+ww/2,Y((k+.5)*quant),'accent' if i==0 else 'ink',1.8),r,tip)
    remainder=v-full*quant
    if remainder>1e-10:self.mark(self.seg(xx-ww/2,Y(full*quant+remainder/2),xx-ww/2+ww*remainder/quant,Y(full*quant+remainder/2),'accent' if i==0 else 'ink',1.8),r,tip)
    self.seg(xx-ww/2-5,Y(v),xx+ww/2+5,Y(v),'accent' if i==0 else 'ink',.9)
   else:self.mark(self.rect(xx-ww/2,Y(v),ww,Y(0)-Y(v),'accent' if i==0 else 'ink','none'),r,tip)
   self.num(xx-slot/2,Y(v)-39,slot,v,25,'ink','center');self.label(xx-slot/2,y+h+22,slot,r['label'],18,'ink','center')
  self.kpi=fmt(mx);self.kpi_label='最高示例产能 / '+self.data['unit'];self.reading=rows[0]['label']+'的示例值最高。按数值排序，比较同一统计口径。';self.caveat='这是产能观测值，不能直接推断停机或效率改善的原因。';self.encoding=f'纵轴从 0 起；'+(f'一条完整短线 = {fmt(quant)} {self.data["unit"]}，不足一单位按线长保留。' if self.detail else '柱高与数值成正比，颜色仅突出最高值。')
 def _time(self,area=False):
  x,y,w,h=self.box;rs=self.rows;ts=[dt.datetime.fromisoformat(r['date']).timestamp() for r in rs];X=lambda t:x+(t-ts[0])/(ts[-1]-ts[0])*w
  lo,hi=scale([r['value'] for r in rs if r['value'] is not None],True);Y=self.axis(lo,hi);peak=max(r['value'] for r in rs if r['value'] is not None);run=[]
  for i,r in enumerate(rs):
   xx=X(ts[i]);v=r['value'];self.seg(xx,y+h+5,xx,y+h+13,'line',.8)
   if v is None:
    if len(run)>1:self.line(run,'accent',1.5 if self.detail else 3)
    run=[];self.label(xx-18,y+h-28,36,'×',17,'muted','center');continue
   yy=Y(v);run.append((xx,yy));tip=r['date']+'：'+fmt(v)+' '+self.data['unit']
   if self.detail or area:self.mark(self.seg(xx,y+h,xx,yy,'line' if not area else 'accent',.8 if self.detail else 4),r,tip)
   if not area or v==peak:self.mark(self.dot(xx,yy,5.5 if v==peak else 3,'accent' if v==peak else 'ink',dt.datetime.fromisoformat(r['date']).weekday()>=5 and self.detail),r,tip)
  if len(run)>1:self.line(run,'accent',1.7 if self.detail else 3.4)
  for i in sorted(set([0,len(rs)//3,2*len(rs)//3,len(rs)-1])):
   self.label(X(ts[i])-55,y+h+28,110,rs[i]['label'],17,'muted','center')
  peakrow=next(r for r in rs if r['value']==peak);px=X(ts[rs.index(peakrow)]);self.num(max(x,min(px-65,x+w-130)),Y(peak)-43,130,peak,24,'accent','center')
  self.kpi=fmt(peak);self.kpi_label=('峰值负荷' if area else '最高单日耗电')+' / '+self.data['unit'];self.reading=peakrow['label']+'达到样例峰值。日期间距按实际时间排列。';self.caveat=f'{self.metrics["missing"]} 个缺测点保留空缺；峰值变化还需结合产量和开机时长。';self.encoding=('每根细线 = 一个实测时刻；轮廓连接相邻有效观测，面积不代替电量积分。' if area else '每个点 = 一天；空心点表示周末，× 表示缺测。' if self.detail else '折线连接相邻有效日期；缺测处断开，纵轴从 0 起。')
 def barcode(self):self._time()
 def area(self):self._time(True)
 def ring(self):
  rows=self.rows;total=self.metrics['total'];cx,cy=500,548;rad=185;unit=self.data['quantum'];tones=['accent','ink','muted'];start=-math.pi/2
  if total/unit>360:raise ValueError('too many ring ticks; increase quantum')
  for i,r in enumerate(rows):
   v=r['value'];tone=tones[i%3];span=v/total*2*math.pi;end=start+span
   if self.detail:
    full=math.floor(v/unit);fractions=[1]*full+([v/unit-full] if v/unit-full>1e-9 else [])
    used=0
    for frac in fractions:
     a=start+(used+unit*frac/2)/total*2*math.pi;length=26*frac
     self.mark(self.seg(cx+(rad-length/2)*math.cos(a),cy+(rad-length/2)*math.sin(a),cx+(rad+length/2)*math.cos(a),cy+(rad+length/2)*math.sin(a),tone,2.1),r,r['label']+'：'+fmt(v)+' '+self.data['unit']);used+=unit*frac
   elif v:
    points=[(cx+rad*math.cos(start+span*j/max(2,math.ceil(span*55))),cy+rad*math.sin(start+span*j/max(2,math.ceil(span*55)))) for j in range(max(2,math.ceil(span*55))+1)]
    self.mark(self.line(points,tone,23),r,r['label']+'：'+fmt(v)+' '+self.data['unit'])
   if v:
    # Boundary ticks show exact sector extents independently of quantized marks.
    self.seg(cx+(rad-34)*math.cos(start),cy+(rad-34)*math.sin(start),cx+(rad+34)*math.cos(start),cy+(rad+34)*math.sin(start),'bg',3)
   yy=358+i*69;self.seg(790,yy+18,811,yy+18,tone,3);self.label(827,yy,173,r['label'],19,'ink');self.num(1000,yy-1,137,self.metrics['shares'][r['id']],22,tone,'right');self.label(1003,yy+29,132,fmt(v)+' '+self.data['unit'],15,'muted','right')
   start=end
  self.num(cx-135,cy-53,270,total,60,'ink','center');self.label(cx-135,cy+32,270,self.data['unit']+' / 合计',18,'muted','center');self.label(980,309,160,'占比 / %',16,'muted','right')
  self.kpi=fmt(max(self.metrics['shares'].values()))+'%';self.kpi_label='最大分项占比';self.reading=max(rows,key=lambda r:r['value'])['label']+'占比最高。分项互斥，合计为同一期间总量。';self.caveat='环用于读构成；需要精确比较接近的分项时优先选横条图。';self.encoding=(f'完整刻度 = {fmt(unit)} {self.data["unit"]}；末段按刻度长度保留余量，边界按精确比例定位。' if self.detail else '弧长按真实占比分配；右侧保留原始用量和占比。')
 def field(self):
  total=int(self.metrics['total']);rows=self.rows;tones=['accent','ink','muted'];ncol=10 if total<=100 else 20;spacing=min(43,620/ncol);x,y=182,351;k=0
  if self.detail:
   for j,r in enumerate(rows):
    for i in range(int(r['value'])):
     xx=x+(k%ncol)*spacing;yy=y+(k//ncol)*spacing;self.mark(self.dot(xx,yy,9.5,tones[j%3],j%3==2),r,r['label']+'：'+fmt(r['value'])+' '+self.data['unit']+' / 计数单位 '+str(i+1)+'（非样本 ID）');k+=1
  else:
   x,y=150,430;w=625
   for j,r in enumerate(rows):
    ww=w*r['value']/total;self.mark(self.rect(x,y,ww,126,tones[j%3],'bg',2),r,r['label']+'：'+fmt(r['value']));x+=ww
   self.label(150,591,625,'样本构成 / 合计 '+fmt(total)+' '+self.data['unit'],20)
  for j,r in enumerate(rows):
   yy=368+j*115;self.dot(805,yy+13,7,tones[j%3],j%3==2);self.label(831,yy-2,295,r['label'],20,'ink');self.num(831,yy+35,130,r['value'],32,tones[j%3]);self.label(974,yy+46,150,fmt(self.metrics['shares'][r['id']])+'%',18)
  self.kpi=str(total);self.kpi_label='样本总量 / '+self.data['unit'];self.reading='所有样本只计入一个类别，数量与原始记录合计一致。';self.caveat='离散点只用于整数计数；不能把百分比点阵冒充逐人观测。';self.encoding=('每个点 = 1 '+self.data['unit']+'，按类别连续排布；颜色和空心形状同时区分类别。' if self.detail else '每段宽度 = 分项数 / 样本总数；保持同一分母。')
 def dumbbell(self):
  # Leave enough room for cross-industry labels while keeping the axis and
  # the right-side reading column visually separate. Long labels wrap at word
  # boundaries and are vertically centred on their row.
  x,y,w,h=360,340,727,405;label_w=248;vals=[r[k] for r in self.rows for k in ('before','after')];lo,hi=scale(vals);X=self.horizontal_axis(lo,hi,x,y,w,h,self.data['unit'])
  for i,r in enumerate(self.rows):
   yy=y+(i+.5)*h/len(self.rows);a,b=r['before'],r['after'];lines=len(wrap(r['label'],label_w,20))*20*1.38
   self.label(78,yy-lines/2,label_w,r['label'],20,'ink')
   self.mark(self.seg(X(a),yy,X(b),yy,'accent',1.3 if self.detail else 6),r,fmt(a)+' → '+fmt(b)+' '+self.data['unit']);self.dot(X(a),yy,6,'ink',True);self.dot(X(b),yy,7,'accent')
   self.num(X(a)-45,yy-36,90,a,17,'muted','center');self.num(X(b)-45,yy+16,90,b,18,'accent','center')
  reductions=sum(r['after']<r['before'] for r in self.rows);self.kpi=f'{reductions}/{len(self.rows)}'
  if self.language=='en':
   self.kpi_label='Entities with a lower after value';self.reading='Each entity is paired before and after. Segment length shows absolute change while position keeps the original values.';self.caveat='A before/after difference is not causal proof; check the mix of cases and the observation window.';self.encoding='Hollow point = before; filled point = after. The axis keeps the original unit, and each segment connects one entity.'
  else:
   self.kpi_label='示例单耗下降的工位';self.reading='同一工位前后成对比较。线段长度表示变化量，位置保留实际数值。';self.caveat='前后差异不是因果证明；需核对产品组合与统计窗口。';self.encoding='空心点 = 改善前；实心点 = 改善后。横轴保留原始单位，连线只连接同一工位。'
 def scatter(self):
  x,y,w,h=self.box;lo,hi=scale([r['y'] for r in self.rows]);xl,xh=scale([r['x'] for r in self.rows]);Y=self.axis(lo,hi,unit=self.data['y_label']+' / '+self.data['y_unit']);X=lambda v:x+w*(v-xl)/(xh-xl)
  for v in ticks(xl,xh):self.num(X(v)-50,y+h+22,100,v,16,'muted','center')
  self.label(x,y+h+64,w,self.data['x_label']+' / '+self.data['x_unit'],17,align='right')
  for r in self.rows:
   xx,yy=X(r['x']),Y(r['y'])
   if self.detail:self.seg(xx,yy,xx,y+h,'line',.65);self.seg(xx,y+h+3,xx,y+h+12,'ink',.8)
   self.mark(self.dot(xx,yy,4.6 if self.detail else 7,'accent'),r,r['label']+'：'+fmt(r['x'])+' '+self.data['x_unit']+' / '+fmt(r['y'])+' '+self.data['y_unit'])
  corr=self.metrics['pearson_r'];self.kpi='—' if corr is None else f'{corr:.2f}';self.kpi_label='Pearson r / 成对样本';self.reading=f'{len(self.rows)} 组同日观测。相关系数由全部有效成对数据计算。';self.caveat='相关不等于因果。没有用回归线暗示未经验证的预测关系。';self.encoding='每个点 = 同一日期的一对观测；'+('垂线帮助回读横轴，线长不表示第三个变量。' if self.detail else '点大小统一，坐标表示两个变量的真实数值。')
 def matrix(self):
  xs,ys=self.data['columns'],self.data['groups'];x,y,w,h=220,354,865,377;mx=max((r['value'] or 0) for r in self.rows);maxr=min(w/len(xs),h/len(ys))*.30
  for i,name in enumerate(xs):self.label(x+i*w/len(xs),y+h+26,w/len(xs),name,18,'muted','center')
  for j,name in enumerate(ys):
   yy=y+(j+.5)*h/len(ys);self.label(89,yy-12,105,name,20,'ink');self.seg(x,yy,x+w,yy,'line',.65)
  for r in self.rows:
   xx=x+(xs.index(r['column'])+.5)*w/len(xs);yy=y+(ys.index(r['group'])+.5)*h/len(ys);v=r['value'];tip=r['column']+' / '+r['group']+'：'+fmt(v)+' '+self.data['unit']
   if v is None:self.label(xx-20,yy-14,40,'×',23,'muted','center')
   elif v==0:self.mark(self.dot(xx,yy,2,'muted',True),r,tip)
   else:
    rad=maxr*math.sqrt(v/mx);self.mark(self.dot(xx,yy,rad,'accent',self.detail),r,tip)
    if not self.detail and rad>12:self.num(xx-40,yy-13,80,v,18,'bg','center')
  self.kpi=fmt(mx);self.kpi_label='最大停机时长 / '+self.data['unit'];self.reading='按班次与星期交叉阅读。面积大的单元值得回看原始停机记录。';self.caveat='圆面积与分钟数成正比；× 是缺测，小空心圆是零值。';self.encoding='圆面积 ∝ 停机分钟数，半径使用平方根；同一张图使用同一尺度。'
 def distribution(self):
  x,y,w,h=self.box;vals=[v for r in self.rows for v in r['values']];lo,hi=scale(vals);Y=self.axis(lo,hi);slot=w/len(self.rows)
  for i,r in enumerate(self.rows):
   xx=x+(i+.5)*slot;b=self.metrics['groups'][r['id']];bx=xx+25 if self.detail else xx
   self.seg(bx,Y(b['low']),bx,Y(b['high']),'muted',1);self.rect(bx-24,Y(b['q3']),48,Y(b['q1'])-Y(b['q3']),'none','accent',1.3 if self.detail else 3)
   for v in (b['low'],b['high']):self.seg(bx-14,Y(v),bx+14,Y(v),'muted',1)
   self.seg(bx-24,Y(b['median']),bx+24,Y(b['median']),'accent',2.4)
   self.num(bx+36,Y(b['median'])-13,90,b['median'],20,'accent')
   if self.detail:
    # Deterministic horizontal offsets only; all vertical positions are measured values.
    for k,v in enumerate(r['values']):
     dx=((k*17)%13-6)*3.5;self.mark(self.dot(xx-60+dx,Y(v),3.6,'ink',v in b['outliers']),r,r['label']+' / 样本 '+str(k+1)+'：'+fmt(v)+' '+self.data['unit'])
   else:
    for v in b['outliers']:self.dot(bx,Y(v),4,'ink',True)
   self.label(xx-slot/2,y+h+25,slot,r['label']+' / n='+str(b['n']),19,'ink','center')
  n=sum(len(r['values']) for r in self.rows);self.kpi=str(n);self.kpi_label='原始测量值 / 总样本数';self.reading='箱体显示中间 50% 的样本，中线为中位数；旁注保留各组样本数。';self.caveat='须线止于 1.5 × IQR 内的实测极值；离群点不删除，也不等同异常原因。';self.encoding=('每个点 = 一次测量，横向错开仅防重叠。' if self.detail else '箱体 = Q1–Q3；空心点 = 1.5 × IQR 以外观测。')+'分位数采用线性插值。'
 def waterfall(self):
  x,y,w,h=self.box;a=self.metrics
  opening,closing=('Opening','Closing') if self.language=='en' else ('基期','期末')
  bars=[dict(id='opening',label=opening,lo=0,hi=a['start'],display=a['start'])]
  for r,s in zip(self.rows,a['steps']):bars.append(dict(id=r['id'],label=r['label'],lo=s['start'],hi=s['end'],display=s['delta']))
  bars.append(dict(id='closing',label=closing,lo=0,hi=a['end'],display=a['end']))
  lo,hi=scale([0]+[v for b in bars for v in (b['lo'],b['hi'])],True);Y=self.axis(lo,hi);slot=w/len(bars);quant=self.data['quantum']
  if (hi-lo)/quant>200:raise ValueError('increase waterfall quantum')
  for i,b in enumerate(bars):
   xx=x+(i+.5)*slot;low,high=sorted([b['lo'],b['hi']]);ww=min(66,slot*.52);tone='accent' if i in (0,len(bars)-1) else 'ink' if b['display']<0 else 'muted';tip=b['label']+(': ' if self.language=='en' else '：')+fmt(b['display'])+' '+self.data['unit']
   if self.detail:
    for k in range(math.floor((high-low)/quant)):
     self.mark(self.seg(xx-ww/2,Y(low+(k+.5)*quant),xx+ww/2,Y(low+(k+.5)*quant),tone,1.7),b,tip)
    rem=(high-low)%quant
    if rem>1e-9:self.mark(self.seg(xx-ww/2,Y(high-rem/2),xx-ww/2+ww*rem/quant,Y(high-rem/2),tone,1.7),b,tip)
    for v in (low,high):self.seg(xx-ww/2,Y(v),xx+ww/2,Y(v),tone,.8)
   else:self.mark(self.rect(xx-ww/2,Y(high),ww,Y(low)-Y(high),tone,'none'),b,tip)
   if i<len(bars)-1:self.seg(xx+ww/2,Y(b['hi']),xx+slot-ww/2,Y(b['hi']),'muted',.7,True)
   self.text(xx-slot/2,Y(high)-39,slot,('+' if b['display']>0 and 0<i<len(bars)-1 else '')+fmt(b['display']),23,tone,'grotesk',500,'center');self.label(xx-slot/2,y+h+22,slot,b['label'],17,'ink','center')
  self.kpi=('+' if a['net']>0 else '')+fmt(a['net'])
  if self.language=='en':
   self.kpi_label='Net change / '+self.data['unit'];self.reading='Closing = opening + every signed change. Each step continues from the previous cumulative value.';self.caveat='This is a simulated reconciliation, not verified savings; check that one measure is not counted twice.';self.encoding=(f'One full tick = {fmt(quant)} {self.data["unit"]}; ' if self.detail else '')+'Floating steps show signed change; opening and closing bars start at zero, with dashed cumulative guides.'
  else:
   self.kpi_label='净变化 / '+self.data['unit'];self.reading='期末 = 基期 + 所有增减项。每一段都从上一段的累计值接续。';self.caveat='分解项是模拟核算，不代表已验证的节能量；避免重复计入同一措施。';self.encoding=(f'完整短线 = {fmt(quant)} {self.data["unit"]}；' if self.detail else '')+'浮动段表示增减，首尾柱从 0 起；虚线追踪累计值。'
 def multiples(self):
  x,y,w,h=150,337,980,426;indexed=self.metrics['indexed'];vals=[v for row in indexed.values() for v in row if v is not None];lo,hi=scale(vals+[100]);n=len(self.rows);slot=w/n;dates=[dt.datetime.fromisoformat(v).timestamp() for v in self.data['dates']]
  for i,r in enumerate(self.rows):
   xx=x+i*slot;ww=slot-45;Y=lambda v:y+h*(hi-v)/(hi-lo);X=lambda t:xx+(t-dates[0])/(dates[-1]-dates[0])*ww
   self.label(xx,y-46,ww,r['label'],22,'ink')
   for v in ticks(lo,hi):
    self.seg(xx,Y(v),xx+ww,Y(v),'line',.6)
    if i==0:self.num(xx-68,Y(v)-12,51,v,16,'muted','right')
   self.seg(xx,Y(100),xx+ww,Y(100),'muted',1,True)
   if i>0:self.num(xx,Y(100)-26,55,100,15,'muted')
   run=[]
   for j,v in enumerate(indexed[r['id']]):
    if v is None:
     if len(run)>1:self.line(run,'accent',1.6 if self.detail else 3)
     run=[];continue
    px,py=X(dates[j]),Y(v);run.append((px,py))
    if self.detail:self.seg(px,y+h,px,py,'line',.65)
    self.mark(self.dot(px,py,3.5,'accent'),r,self.data['dates'][j]+' / '+r['label']+'：'+fmt(r['values'][j])+' '+r['unit']+' / 指数 '+fmt(v))
   if len(run)>1:self.line(run,'accent',1.6 if self.detail else 3)
   last=indexed[r['id']][-1]
   if last is not None:
    previous=next((v for v in reversed(indexed[r['id']][:-1]) if v is not None),last)
    ly=Y(last)-38 if last>=previous else Y(last)+12
    self.num(xx+ww-84,ly,84,last,24,'accent','right')
   self.label(xx,y+h+26,ww,self.data['dates'][0][:7]+' → '+self.data['dates'][-1][:7],16)
  self.kpi='100';self.kpi_label='各系列首期 / 共同基准';self.reading='每项指标除以各自首期再乘 100；所有小图共用同一纵轴范围。';self.caveat='指数可比变化幅度，不能比较水、电、蒸汽的绝对消耗量。';self.encoding='每个点 = 一期指数；原始数值与单位随源数据保存。虚线为首期 100，缺测不补零。'
 def parallel(self):
  dims=self.data['dimensions'];x,y,w,h=190,356,820,385;n=len(dims)
  for i,a in enumerate(dims):
   xx=x+w*i/(n-1);self.seg(xx,y,xx,y+h,'muted',1)
   for t in range(6):self.seg(xx-6,y+h*t/5,xx+6,y+h*t/5,'line',.8)
   self.label(xx-95,y-58,190,a['label'],19,'ink','center');self.num(xx-70,y-28,140,a['max'],16,'muted','center');self.num(xx-70,y+h+13,140,a['min'],16,'muted','center');self.label(xx-100,y+h+42,200,a['unit'],17,'muted','center')
  ends=[]
  for j,r in enumerate(self.rows):
   vals=self.metrics['normalized'][r['id']];pts=[(x+w*i/(n-1),y+h*(1-v)) for i,v in enumerate(vals)];tone='accent' if j==0 else 'muted';self.mark(self.line(pts,tone,2 if j==0 else .9 if self.detail else 1.7,dash=j%2==1),r,r['label']+' / '+'；'.join(a['label']+' '+fmt(r['values'][a['id']])+a['unit'] for a in dims))
   for i,p in enumerate(pts):self.mark(self.dot(*p,4,tone,j%2==1),r,r['label']+' / '+dims[i]['label']+'：'+fmt(r['values'][dims[i]['id']]))
   ends.append([pts[-1][1],r,tone])
  ends.sort(key=lambda v:v[0]);last=y-38;positions=[]
  for ey,r,tone in ends:
   yy=max(last+37,ey);last=yy;positions.append(yy)
  shift=max(0,positions[-1]-(y+h));positions=[v-shift for v in positions]
  for (ey,r,tone),yy in zip(ends,positions):
   self.seg(x+w+7,ey,x+w+30,yy,tone,.8);self.label(x+w+38,yy-13,112,r['label'],19,tone)
  self.kpi=str(len(dims));self.kpi_label='独立维度 / 分轴量纲';self.reading='每条路径连接同一产线。轴上下限固定并标明，逐项比较性能轮廓。';self.caveat='各轴量纲不同，折线面积没有意义；数值越高并不总是越好。';self.encoding='每条线 = 一条产线；每个轴按标明范围线性映射，换型时间越低越好。'
 def svg(self):
  xml=ET.fromstring(super().svg());ns='{http://www.w3.org/2000/svg}';ET.register_namespace('',ns[1:-1])
  xml.set('data-recipe',self.recipe);xml.set('data-mode',self.mode)
  desc=ET.SubElement(xml,ns+'desc');desc.text=self.encoding+' '+self.reading+' '+self.caveat
  for el in xml.iter():
   tag=self.tags.get(el.get('id'))
   if tag:
    el.set('data-record',tag['record']);el.set('data-tip',tag['tip']);title=ET.SubElement(el,ns+'title');title.text=tag['tip']
  return ET.tostring(xml,encoding='unicode')
 def csv_text(self):
  rows=[]
  for r in self.rows:
   if self.recipe in ('distribution','multiples'):
    for i,v in enumerate(r['values']):rows.append(dict(id=r['id'],label=r['label'],observation=i+1,date=self.data.get('dates',['']*len(r['values']))[i],value=v,unit=r.get('unit',self.data['unit'])))
   elif self.recipe=='parallel':
    for a in self.data['dimensions']:rows.append(dict(id=r['id'],label=r['label'],dimension=a['label'],value=r['values'][a['id']],unit=a['unit']))
   else:rows.append({**r,'unit':self.data['unit']})
  out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));writer.writeheader();writer.writerows(rows);return out.getvalue()
 def save(self,out,raster=True):
  qa=super().save(out,raster);stem=Path(out)/self.recipe;stem.with_suffix('.csv').write_text('\ufeff'+self.csv_text())
  csv_rows=list(csv.reader(io.StringIO(self.csv_text())));table='<table>'+''.join('<tr>'+''.join(('<th>' if i==0 else '<td>')+html.escape(v)+('</th>' if i==0 else '</td>') for v in row)+'</tr>' for i,row in enumerate(csv_rows))+'</table>'
  embedded=json.dumps(dict(input=self.data,svg=self.svg(),drawio=self.drawio(),csv='\ufeff'+self.csv_text()),ensure_ascii=False).replace('<','\\u003c')
  viewer=(ROOT/'assets/data-art-viewer.html').read_text()
  tokens={'TITLE':html.escape(self.data['title']),'SVG':self.svg(),'TABLE':table,'EMBEDDED':embedded,'SOURCE':html.escape(('模拟数据' if self.data['synthetic'] else '来源数据')+' · '+self.data['source'])}
  tokens.update({k.upper():self.c(k) for k in ('bg','ink','line','accent','muted')})
  # Replace template tokens in one pass; user text cannot introduce a second template substitution.
  import re
  viewer=re.sub(r'__(TITLE|SVG|TABLE|EMBEDDED|SOURCE|BG|INK|LINE|ACCENT|MUTED)__',lambda m:tokens[m.group(1)],viewer)
  stem.with_suffix('.html').write_text(viewer)
  qa.update(mode=self.mode,theme=self.name,tagged_marks=len(self.tags));Path(str(stem)+'.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));return qa

def main():
 from canvas_layout import arguments,from_args,apply_canvas
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--mode',choices=['detail','clear'],default='detail');p.add_argument('--theme',choices=list(PALETTES),default='warm');p.add_argument('--vector-only',action='store_true');arguments(p);a=p.parse_args()
 data=json.loads(Path(a.input).read_text());plate=apply_canvas(DataPlate(data,a.mode,a.theme).build(),from_args(a));print(json.dumps(plate.save(a.out,not a.vector_only),ensure_ascii=False))
if __name__=='__main__':main()
