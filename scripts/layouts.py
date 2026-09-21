"""Additional reusable layout grammars. Pure local geometry, no remote requests."""
import math,datetime as dt

def need(ok,msg):
 if not ok:raise ValueError(msg)
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
TONES=['accent','teal','amber','red','muted']
def items(d,key='items',lo=1,hi=12):
 a=d[key];need(isinstance(a,list) and lo<=len(a)<=hi,f'{key}: expected {lo}–{hi} entries');return a

def poly(s,pts,fill='tint',stroke='accent',**kw):
 xs,ys=zip(*pts);return s.add(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys),kind='polygon',points=pts,fill=fill,stroke=stroke,check=False,**kw)
def straight(s,a,b,**kw):
 na,nb=s.get(a),s.get(b);ax,ay=na['x']+na['w']/2,na['y']+na['h']/2;bx,by=nb['x']+nb['w']/2,nb['y']+nb['h']/2;dx,dy=bx-ax,by-ay
 def point(n,cx,cy,vx,vy):
  k=min(n['w']/2/abs(vx) if vx else math.inf,n['h']/2/abs(vy) if vy else math.inf)
  return [cx+k*vx,cy+k*vy]
 s.edge(a,b,points=[point(na,ax,ay,dx,dy),point(nb,bx,by,-dx,-dy)],**kw)

def radial(s,d):
 a=items(d,lo=3,hi=8);cx,cy=s.w/2,505;ids=[]
 root=s.add(cx-130,cy-55,260,110,d['center'],d.get('detail',''),kind='ellipse',id='hub',check=True)
 for i,v in enumerate(a):
  ang=-math.pi/2+i*math.tau/len(a);x=cx+480*math.cos(ang)-128;y=cy+235*math.sin(ang)-42
  id=s.add(x,y,256,84,v['label'],v.get('detail',''),id=v.get('id',f'item{i}'),tone='teal',check=True);ids.append(id)
  straight(s,id,root,arrow=d.get('arrows',False),tone='muted')
 s.meta['relation']='hub-and-spoke';s.meta['items']=ids

def cycle(s,d):
 a=items(d,lo=3,hi=6);cx,cy=s.w/2,500;rx,ry=470,240;ids=[];angles=[]
 for i,v in enumerate(a):
  ang=-math.pi/2+i*math.tau/len(a);angles.append(ang);x=cx+rx*math.cos(ang)-125;y=cy+ry*math.sin(ang)-44
  ids.append(s.add(x,y,250,88,f'{i+1:02d}  '+v['label'],v.get('detail',''),id=f'cycle{i}',tone='accent' if i==0 else 'teal',check=True))
 for i in range(len(a)):straight(s,ids[i],ids[(i+1)%len(a)],tone='muted')
 s.text(cx-160,cy-36,320,72,d.get('center','持续循环'),28,'ink',align='center')
 s.meta['cycle_edges']=[[ids[i],ids[(i+1)%len(a)]] for i in range(len(a))]

def tapered(s,d):
 a=items(d,lo=2,hi=6);mode=d.get('mode','pyramid');need(mode in ('pyramid','funnel'),'unknown tapered mode');cx=650;y0=220
 # Measure mixed CJK/Latin copy before deciding the vertical rhythm.  This
 # keeps an English stage from being squeezed into the Chinese one-line box.
 from render import wrap_words
 label_w=420;label_size=24;detail_size=17
 ratio_label=d.get('ratio_label','首阶段占比');unit=d.get('unit','')
 vals=None
 if mode=='funnel':
  vals=[x.get('value') for x in a];need(all(finite(x) and x>0 for x in vals),'funnel values must be positive');need(all(x>=y for x,y in zip(vals,vals[1:])),'funnel stages must be nonincreasing')
 measured=[]
 for v in a:
  label_lines=wrap_words(v['label'],label_w,label_size)
  if mode=='funnel':
   detail=f'{v["value"]:g}{unit}  ·  {ratio_label} {v["value"]/vals[0]:.0%}'
  else:
   detail=v.get('detail','')
  detail_lines=wrap_words(detail,label_w,detail_size) if detail else []
  measured.append((label_lines,detail,detail_lines))
 stage_h=max(120,520/len(a),max((len(labels)*label_size*1.35+len(details)*detail_size*1.35+30 for labels,_,details in measured),default=120))
 if mode=='funnel':
  widths=[680*v/vals[0] for v in vals];s.meta['width_values']=vals
 else:widths=[720*(i+1)/len(a) for i in range(len(a))]
 for i,v in enumerate(a):
  y=y0+i*stage_h;w=widths[i];bottom=widths[i+1] if mode=='funnel' and i+1<len(a) else w if mode=='funnel' else w+600/len(a)
  if mode=='pyramid':top=w-720/len(a);bottom=w
  else:top=w
  poly(s,[(cx-top/2,y),(cx+top/2,y),(cx+bottom/2,y+stage_h-10),(cx-bottom/2,y+stage_h-10)],fill='tint' if i%2==0 else 'tint2',stroke='line')
  labels,detail,detail_lines=measured[i]
  label_h=max(36,len(labels)*label_size*1.35+4);detail_y=y+14+label_h;detail_h=max(28,len(detail_lines)*detail_size*1.35+4)
  s.text(1030,y+10,420,label_h,v['label'],label_size,'accent' if i==0 else 'ink',word_wrap=True)
  s.text(1030,detail_y,420,detail_h,detail,detail_size,'muted',word_wrap=True)
  s.edge(points=[(cx+max(top,bottom)/2+12,y+stage_h/2),(1005,y+stage_h/2)],arrow=False,tone='line')
 s.meta['semantic']=mode;s.meta['ratio_label']=ratio_label if mode=='funnel' else None;s.h=max(s.h,y0+len(a)*stage_h+100)

def venn(s,d):
 a=items(d,lo=2,hi=2);s.add(310,245,550,440,kind='ellipse',fill='none',stroke='accent',stroke_width=2,check=False);s.add(720,245,550,440,kind='ellipse',fill='none',stroke='teal',stroke_width=2,check=False)
 s.text(355,404,300,100,a[0]['label']+'\n'+a[0].get('detail',''),24,'ink',align='center')
 s.text(925,404,300,100,a[1]['label']+'\n'+a[1].get('detail',''),24,'ink',align='center')
 s.text(705,412,170,110,d['intersection'],20,'accent',align='center');s.meta['area_scaled']=False

def concentric(s,d):
 a=items(d,lo=2,hi=5);cx,cy=650,493;r=270
 for i,v in enumerate(a):
  rr=r-i*46;s.add(cx-rr,cy-rr,rr*2,rr*2,kind='ellipse',fill='panel' if i%2 else 'tint2',stroke='line',check=False)
 for i,v in enumerate(a):
  rr=r-i*46;yy=cy-rr+4;s.text(cx-190,yy,380,40,v['label'],18,'accent' if i==0 else 'ink',align='center')
  s.text(1010,260+i*86,430,70,v.get('detail',''),20,'muted')
 s.text(cx-130,cy-13,260,55,d.get('center','核心'),28,'accent',align='center')

def timeline(s,d):
 a=items(d,lo=2,hi=7);dates=[dt.date.fromisoformat(v['date']) for v in a];need(dates==sorted(dates) and len(set(dates))==len(dates),'timeline requires unique increasing dates');span=(dates[-1]-dates[0]).days;xs=[130+((v-dates[0]).days/span)*(s.w-260) for v in dates];cy=500
 label_h=72;detail_h=96;card_top=250;down_top=cy+64
 s.h=max(s.h,down_top+43+label_h+8+detail_h+100)
 s.edge(points=[(100,cy),(s.w-100,cy)],tone='muted')
 for i,(v,x) in enumerate(zip(a,xs)):
  up=i%2==0;y=card_top if up else down_top;w=250;xx=max(64,min(s.w-64-w,x-w/2));s.add(x-7,cy-7,14,14,kind='ellipse',fill='accent',stroke='panel',check=False)
  s.text(xx,y,w,34,v['date'],17,'accent',align='center',word_wrap=True);s.text(xx,y+43,w,label_h,v['label'],22,align='center',word_wrap=True);s.text(xx,y+43+label_h+8,w,detail_h,v.get('detail',''),16,'muted',align='center',word_wrap=True)
  s.edge(points=[(x,cy),(x,cy-38 if up else cy+45)],arrow=False,tone='line')
 s.meta['day_offsets']=[(v-dates[0]).days for v in dates]

def table(s,d):
 columns=items(d,'columns',2,8);rows=items(d,'rows',1,12);first=d.get('first_width',225);cw=(s.w-128-first)/(len(columns)-1);widths=[first]+[cw]*(len(columns)-1);rh=d.get('row_height',110);y0=204
 def cell(x,y,w,h,value,head=False,tone='ink'):
  s.add(x,y,w,h,kind='rect',fill='tint2' if head else 'panel',stroke='line',check=False)
  s.text(x+16,y+12,w-32,h-24,str(value),19 if head else 17,tone,align='left',word_wrap=True)
 x=64
 for i,label in enumerate(columns):cell(x,y0,widths[i],58,label,True);x+=widths[i]
 for j,row in enumerate(rows):
  vals=row.get('cells',row) if isinstance(row,dict) else row;need(len(vals)==len(columns),'table row length mismatch');x=64
  for i,v in enumerate(vals):cell(x,y0+58+j*rh,widths[i],rh,v,i==0,'accent' if i==0 else 'ink');x+=widths[i]
 s.h=max(s.h,y0+58+len(rows)*rh+100)

def bmc(s,d):
 a=items(d,lo=9,hi=9);gap=14;w=(s.w-128-4*gap)/5;x=[64+i*(w+gap) for i in range(5)];y=204
 from render import wrap_words
 inner_w=w-44;label_size=21;detail_size=18
 cell_heights=[]
 for v in a:
  label_lines=wrap_words(v['label'],inner_w,label_size)
  detail_lines=wrap_words(v.get('detail',''),inner_w,detail_size) if v.get('detail','') else []
  required=18+max(42,len(label_lines)*label_size*1.35+4)+8+max(44,len(detail_lines)*detail_size*1.35+4)+18
  cell_heights.append(required)
 h=max(208,max(cell_heights,default=208))
 slots=[(x[0],y,w,h*2+gap),(x[1],y,w,h),(x[1],y+h+gap,w,h),(x[2],y,w,h*2+gap),(x[3],y,w,h),(x[3],y+h+gap,w,h),(x[4],y,w,h*2+gap),(64,y+2*(h+gap),(s.w-128-gap)/2,135),(64+(s.w-128+gap)/2,y+2*(h+gap),(s.w-128-gap)/2,135)]
 for v,(xx,yy,ww,hh) in zip(a,slots):
  label_lines=wrap_words(v['label'],ww-44,label_size);label_h=max(42,len(label_lines)*label_size*1.35+4)
  detail_y=yy+18+label_h+8;detail_h=max(44,hh-(detail_y-yy)-18)
  s.add(xx,yy,ww,hh,kind='panel',check=False)
  s.text(xx+22,yy+18,ww-44,label_h,v['label'],label_size,'accent',word_wrap=True)
  s.text(xx+22,detail_y,ww-44,detail_h,v.get('detail',''),detail_size,'ink',word_wrap=True)
 s.h=max(s.h,900);s.meta['semantic']='business-model-canvas';s.meta['cell_height']=h

def quadrant(s,d):
 a=items(d,lo=1,hi=12);x0,y0,pw,ph=250,230,1060,500
 for i,l in enumerate(d.get('quadrants',['低 / 高','高 / 高','低 / 低','高 / 低'])):
  xx=x0+(i%2)*pw/2;yy=y0+(i//2)*ph/2;s.add(xx,yy,pw/2,ph/2,kind='panel',fill='tint2' if i%2 else 'panel',stroke='none',check=False);s.text(xx+18,yy+10,pw/2-36,34,l,16,'muted')
 s.edge(points=[(x0-20,y0+ph/2),(x0+pw+25,y0+ph/2)],tone='muted');s.edge(points=[(x0+pw/2,y0+ph+15),(x0+pw/2,y0-10)],tone='muted')
 for v in a:
  need(all(finite(v[k]) and 0<=v[k]<=100 for k in ('x','y')),'quadrant coordinates must be 0–100');xx=x0+v['x']/100*pw;yy=y0+ph-v['y']/100*ph;s.add(xx-5,yy-5,10,10,kind='ellipse',fill='accent',stroke='none',check=False);s.text(xx+12,yy-17,230,58,v['label'],17,word_wrap=True)
 s.text(x0,y0+ph+32,pw,36,d.get('x_label','横轴 →'),18,'muted',align='center');s.text(64,y0+20,166,76,d.get('y_label','纵轴 ↑'),18,'muted');s.meta['coordinates']=[(v['x'],v['y']) for v in a]

def chevrons(s,d):
 a=items(d,lo=2,hi=6);w=(s.w-148)/len(a);y=336;h=154
 for i,v in enumerate(a):
  x=64+i*w;pts=[(x,y),(x+w-30,y),(x+w,y+h/2),(x+w-30,y+h),(x,y+h),(x+25,y+h/2)]
  if i==0:pts=[(x,y)]+pts[1:5]
  poly(s,pts,fill='tint' if i==0 else 'tint2',stroke='bg');s.text(x+34,y+43,w-78,70,v['label'],23,align='center');s.text(x+16,y+h+35,w-44,115,v.get('detail',''),18,'muted',align='center')

def treemap(s,d):
 a=items(d,lo=2,hi=10);need(all(finite(v['value']) and v['value']>0 for v in a),'treemap values must be positive');rects=[]
 def split(entries,x,y,w,h):
  if len(entries)==1:
   v=entries[0];rects.append((v,x,y,w,h));return
  total=sum(v['value'] for v in entries);acc=0;best=1
  for i,v in enumerate(entries[:-1],1):
   acc+=v['value']
   if abs(acc-total/2)<abs(sum(k['value'] for k in entries[:best])-total/2):best=i
  ratio=sum(v['value'] for v in entries[:best])/total
  if w>=h:split(entries[:best],x,y,w*ratio,h);split(entries[best:],x+w*ratio,y,w*(1-ratio),h)
  else:split(entries[:best],x,y,w,h*ratio);split(entries[best:],x,y+h*ratio,w,h*(1-ratio))
 split(a,100,220,s.w-200,520);total=sum(v['value'] for v in a)
 for i,(v,x,y,w,h) in enumerate(rects):
  s.add(x,y,w,h,kind='rect',fill='tint' if i==0 else 'tint2' if i%2 else 'panel',stroke='bg',stroke_width=4,radius=0,check=False)
  s.text(x+14,y+18,w-28,h-36,f'{v["label"]}\n{v["value"]:g} · {v["value"]/total:.0%}',22,align='center')
 s.meta['rectangles']=[{'label':v['label'],'value':v['value'],'area':w*h} for v,x,y,w,h in rects]

def sankey(s,d):
 sources=items(d,'sources',1,6);targets=items(d,'targets',1,6);links=items(d,'links',1,24);sn={v['id']:v for v in sources};tn={v['id']:v for v in targets};need(len(sn)==len(sources) and len(tn)==len(targets),'duplicate sankey id');sv={k:0 for k in sn};tv={k:0 for k in tn}
 for l in links:
  need(l['from'] in sn and l['to'] in tn and finite(l['value']) and l['value']>0,'invalid sankey link');sv[l['from']]+=l['value'];tv[l['to']]+=l['value']
 need(all(v>0 for v in [*sv.values(),*tv.values()]),'unconnected sankey node');total=sum(sv.values());unit=(480-36*(max(len(sources),len(targets))-1))/total;x1,x2=420,s.w-420;sp={};tp={};ys={};yt={}
 for group,values,pos in ((sources,sv,sp),(targets,tv,tp)):
  yy=246
  for v in group:pos[v['id']]=yy;yy+=values[v['id']]*unit+36
 ys=sp.copy();yt=tp.copy()
 for i,l in enumerate(links):
  h=l['value']*unit;a=ys[l['from']];b=yt[l['to']];upper=[];lower=[]
  for j in range(31):
   t=j/30;q=t*t*(3-2*t);xx=x1+24+(x2-x1-24)*t;upper.append((xx,a+(b-a)*q));lower.append((xx,a+h+(b-a)*q))
  poly(s,upper+list(reversed(lower)),fill='tint' if i%2==0 else 'tint2',stroke='line',stroke_width=.5);ys[l['from']]+=h;yt[l['to']]+=h
 for group,values,pos,x,align in ((sources,sv,sp,x1,'right'),(targets,tv,tp,x2,'left')):
  for v in group:
   y=pos[v['id']];h=values[v['id']]*unit;s.add(x,y,24,h,kind='rect',fill='accent' if align=='right' else 'teal',stroke='none',check=False);xx=x-300 if align=='right' else x+45;s.text(xx,y+h/2-38,280,76,f'{v["label"]}\n{values[v["id"]]:g}',21,align=align)
 s.meta.update(total_flow=total,source_totals=sv,target_totals=tv,flow_scale=unit)

def record(s,d):
 classes=items(d,'classes',1,6)
 for i,c in enumerate(classes):
  x=c.get('x',100+i*480);y=c.get('y',300);w=c.get('w',360);fields=c.get('fields',[]);methods=c.get('methods',[]);h=74+max(1,len(fields))*32+max(1,len(methods))*32+36
  s.add(x,y,w,h,c['label'],kind='rect',id=c['id'],check=True,fs=22,radius=0)
  # Put title and compartments as separate editable text/lines, preserving class connection target.
  s.get(c['id'])['label']='';s.text(x+14,y+12,w-28,42,c['label'],24,'accent',align='center');cut=y+64
  s.add(x,cut,w,1,kind='rect',fill='line',stroke='none',check=False)
  for j,v in enumerate(fields):s.text(x+20,cut+12+j*32,w-40,30,v,18)
  cut+=max(1,len(fields))*32+18;s.add(x,cut,w,1,kind='rect',fill='line',stroke='none',check=False)
  for j,v in enumerate(methods):s.text(x+20,cut+10+j*32,w-40,30,v,18)
 for e in d.get('edges',[]):s.edge(e['from'],e['to'],e.get('label',''),arrow=False,tone='muted')

def nice_top(v):
 need(finite(v) and v>0,'positive finite scale required')
 base=10**math.floor(math.log10(v))
 return next(k*base for k in [1,1.2,1.6,2,2.4,3.2,4,5,6,8,10] if k*base>=v)

def data_range(values):
 low=min(values);high=max(values)
 if low==high==0:return [0,1]
 return [-nice_top(abs(low)*1.1) if low<0 else 0,nice_top(high*1.1) if high>0 else 0]

def plot(s,d):
 mode=d['mode'];x0,y0,pw,ph=170,245,s.w-340,445
 def axis(maximum,minimum=0):
  need(finite(maximum) and finite(minimum) and maximum>minimum,'invalid axis range')
  for j in range(5):
   yy=y0+ph-j*ph/4;vv=minimum+(maximum-minimum)*j/4;s.edge(points=[(x0,yy),(x0+pw,yy)],arrow=False,tone='line');s.text(64,yy-16,88,32,f'{vv:g}',15,'muted',align='right')
  return lambda v:y0+ph-(v-minimum)/(maximum-minimum)*ph
 def bottom(i,n,label):s.text(x0+pw*(i+.5)/n-100,y0+ph+16,200,42,label,17,'muted',align='center')
 if mode in ('grouped','stacked'):
  categories=d['categories'];series=d['series'];need(1<=len(series)<=4 and 1<=len(categories)<=8,'group/stack sizes exceeded')
  for v in series:need(len(v['values'])==len(categories) and all(finite(z) and z>=0 for z in v['values']),'invalid series data')
  maxima=[sum(v['values'][i] for v in series) if mode=='stacked' else max(v['values'][i] for v in series) for i in range(len(categories))];maximum=nice_top(max(maxima)*1.08);Y=axis(maximum);slot=pw/len(categories);segments=[]
  for i,label in enumerate(categories):
   bottom(i,len(categories),label);acc=0
   for j,v in enumerate(series):
    value=v['values'][i];w=slot*.58 if mode=='stacked' else slot*.7/len(series);x=x0+i*slot+slot*.15+(j*w if mode=='grouped' else slot*.06);top=Y(acc+value if mode=='stacked' else value);height=value/maximum*ph
    if value:s.add(x,top,w-2,height,kind='rect',fill=TONES[j],stroke='none',check=False)
    segments.append({'category':label,'series':v['label'],'value':value,'height':height});acc+=value
  for j,v in enumerate(series):s.add(x0+j*250,198,14,14,kind='rect',fill=TONES[j],stroke='none',check=False);s.text(x0+25+j*250,190,220,34,v['label'],16)
  s.meta['segments']=segments
 elif mode in ('scatter','bubble'):
  a=items(d,'data',2,40);need(all(finite(v[k]) for v in a for k in ('x','y')),'invalid points');xmin,xmax=d['x_range'] if 'x_range' in d else data_range([v['x'] for v in a]);ymin,ymax=d['y_range'] if 'y_range' in d else data_range([v['y'] for v in a]);need(xmax>xmin,'invalid x range');need(all(xmin<=v['x']<=xmax and ymin<=v['y']<=ymax for v in a),'point outside specified axis');Y=axis(ymax,ymin);X=lambda v:x0+(v-xmin)/(xmax-xmin)*pw;maxsize=max(v.get('size',1) for v in a);need(maxsize>0,'bubble sizes must be positive');radii=[]
  points=[]
  for j in range(5):xx=x0+pw*j/4;s.text(xx-70,y0+ph+14,140,32,f'{xmin+(xmax-xmin)*j/4:g}',15,'muted',align='center')
  for v in a:
   size=v.get('size',1);need(finite(size) and size>0,'bubble sizes must be positive');r=35*math.sqrt(size/maxsize) if mode=='bubble' else 7;xx,yy=X(v['x']),Y(v['y']);s.add(xx-r,yy-r,2*r,2*r,kind='ellipse',fill='tint' if mode=='bubble' else 'accent',stroke='accent',check=False);s.text(xx+12,yy-38,180,32,v.get('label',''),15);radii.append({'value':size,'radius':r})
   points.append({'x':v['x'],'y':v['y'],'label':v.get('label','')})
  s.meta['bubble_radii']=radii;s.meta['points']=points;s.meta['axis_ranges']={'x':[xmin,xmax],'y':[ymin,ymax]}
  if mode=='bubble':s.text(s.w-630,192,490,36,f'圆面积编码第三个量 · 最大 {maxsize:g}',16,'muted',align='right')
  x_label=d.get('x_label','X')+(' · '+d['x_unit'] if d.get('x_unit') else '')
  y_label=d.get('y_label','Y')+(' · '+d['y_unit'] if d.get('y_unit') else '')
  from render import wrap_words
  x_h=max(34,len(wrap_words(x_label,pw,17))*17*1.35+4);y_h=max(40,len(wrap_words(y_label,350,17))*17*1.35+4)
  s.text(x0,y0+ph+62,pw,x_h,x_label,17,'muted',align='center',word_wrap=True);s.text(64,184,350,y_h,y_label,17,'muted',word_wrap=True);s.h=max(s.h,y0+ph+62+x_h+100)
 elif mode=='heatmap':
  rows=d['row_labels'];cols=d['column_labels'];values=d['values'];need(len(rows)==len(values) and all(len(r)==len(cols) for r in values),'heatmap dimensions');need(all(finite(v) for r in values for v in r),'heatmap needs finite values');low=d.get('minimum',min(v for r in values for v in r));high=d.get('maximum',max(v for r in values for v in r));need(high>low and all(low<=v<=high for r in values for v in r),'invalid heatmap range');cw=pw/len(cols);rh=ph/len(rows)
  def blend(a,b,t):return '#'+''.join(f'{round(int(a[k:k+2],16)*(1-t)+int(b[k:k+2],16)*t):02X}' for k in (1,3,5))
  for j,row in enumerate(values):
   s.text(64,y0+j*rh+rh/2-18,100,36,rows[j],17,'muted',align='right')
   for i,v in enumerate(row):
    t=(v-low)/(high-low);fill=blend(s.palette['panel'],s.palette['accent'],t*.65);s.add(x0+i*cw,y0+j*rh,cw,rh,kind='rect',fill=fill,stroke='bg',stroke_width=3,radius=0,check=False);s.text(x0+i*cw,y0+j*rh+rh/2-20,cw,40,f'{v:g}',20,'ink',align='center')
  for i,c in enumerate(cols):bottom(i,len(cols),c)
  s.text(x0,192,pw,36,f'{d.get("scale_label","明度映射")} {low:g} — {high:g}  ·  '+d.get('unit',''),17,'muted',word_wrap=True)
 elif mode=='radar':
  a=items(d,'data',3,8);maximum=d.get('maximum',100);need(finite(maximum) and maximum>0 and all(finite(v['value']) and 0<=v['value']<=maximum for v in a),'radar requires shared bounded scale');cx,cy,r=s.w/2,492,228;points=[]
  for level in (.25,.5,.75,1):
   pts=[(cx+r*level*math.cos(-math.pi/2+i*math.tau/len(a)),cy+r*level*math.sin(-math.pi/2+i*math.tau/len(a))) for i in range(len(a))];s.edge(points=pts+[pts[0]],arrow=False,tone='line')
  for i,v in enumerate(a):
   ang=-math.pi/2+i*math.tau/len(a);dx,dy=math.cos(ang),math.sin(ang);s.edge(points=[(cx,cy),(cx+r*dx,cy+r*dy)],arrow=False,tone='line');points.append((cx+r*dx*v['value']/maximum,cy+r*dy*v['value']/maximum));s.text(cx+(r+68)*dx-120,cy+(r+48)*dy-24,240,48,f'{v["label"]} {v["value"]:g}',18,align='center')
  s.edge(points=points+[points[0]],arrow=False,tone='accent',width=3);s.meta['normalized_values']=[v['value']/maximum for v in a]
 elif mode=='histogram':
  values=d['values'];edges=d['bin_edges'];need(values,'histogram observations required');need(len(edges)>=3 and all(finite(x) for x in values+edges),'histogram finite values required');widths=[b-a for a,b in zip(edges,edges[1:])];need(min(widths)>0 and max(widths)-min(widths)<1e-8,'histogram requires equal width bins');need(all(edges[0]<=v<=edges[-1] for v in values),'observation outside bins');counts=[0]*(len(edges)-1)
  for v in values:
   i=min(len(counts)-1,int((v-edges[0])/widths[0]));counts[i]+=1
  Y=axis(max(4,math.ceil(max(counts)*1.05/4)*4));cw=pw/len(counts)
  for i,n in enumerate(counts):
   if n:s.add(x0+i*cw,Y(n),cw,y0+ph-Y(n),kind='rect',fill='tint',stroke='accent',radius=0,check=False)
   s.text(x0+i*cw,Y(n)-34,cw,30,str(n),18,align='center');bottom(i,len(counts),f'{edges[i]:g}–{edges[i+1]:g}')
  s.meta.update(bin_counts=counts,sample_count=len(values),bin_edges=edges,unit=d.get('unit',''))
  note=d.get('frequency_note','频数 · 左闭右开，最后一个区间含右端点')+(' · '+d['unit'] if d.get('unit') else '')
  s.text(x0,194,pw,42,note,16,'muted',word_wrap=True)
 elif mode=='waterfall':
  a=items(d,'data',2,10);acc=0;bars=[]
  for v in a:
   value=v['value'];need(finite(value),'waterfall invalid value');before=acc
   if v.get('total') and bars:need(abs(value-acc)<1e-8,'waterfall total does not match cumulative changes')
   acc=value if v.get('total') else acc+value;bars.append((v,0 if v.get('total') else before,acc))
  low=min(0,*[min(a,b) for v,a,b in bars]);high=max(0,*[max(a,b) for v,a,b in bars]);pad=(high-low)*.1 or 1;Y=axis(nice_top(high+pad),-nice_top(abs(low)+pad) if low<0 else 0);cw=pw/len(a)
  for i,(v,before,after) in enumerate(bars):
   top=Y(max(before,after));h=abs(Y(before)-Y(after));x=x0+i*cw+cw*.16
   if h:s.add(x,top,cw*.65,h,kind='rect',fill='accent' if v.get('total') else 'teal' if after>=before else 'amber',stroke='none',check=False)
   s.text(x,top-35,cw*.65,32,f'{after:g}' if v.get('total') else f'{v["value"]:+g}',18,align='center');bottom(i,len(a),v['label'])
   if i<len(a)-1:s.edge(points=[(x+cw*.65,Y(after)),(x0+(i+1)*cw+cw*.16,Y(after))],arrow=False,tone='line',dashed=True)
  s.meta['end_values']=[b for v,a,b in bars]
 elif mode=='area':
  a=items(d,'data',2,12);need(all(finite(v['value']) and v['value']>=0 for v in a),'area needs nonnegative values');maximum=nice_top(max(v['value'] for v in a)*1.1);Y=axis(maximum);pts=[]
  for i,v in enumerate(a):xx=x0+i*pw/(len(a)-1);pts.append((xx,Y(v['value'])));s.text(xx-80,y0+ph+16,160,36,v['label'],17,'muted',align='center')
  poly(s,[(x0,y0+ph)]+pts+[(x0+pw,y0+ph)],fill='tint',stroke='none');s.edge(points=pts,arrow=False,tone='accent',width=3)
  for (xx,yy),v in zip(pts,a):s.text(xx-60,yy-34,120,30,f'{v["value"]:g}',17,align='center')
 elif mode=='pie':
  a=items(d,'data',2,5);need(all(finite(v['value']) and v['value']>=0 for v in a),'pie values nonnegative');total=sum(v['value'] for v in a);need(total>0,'pie total positive');cx,cy,r=535,488,222;ang=-math.pi/2
  for i,v in enumerate(a):
   share=v['value']/total;end=ang+share*math.tau;count=max(2,math.ceil(120*share));pts=[(cx,cy)]+[(cx+r*math.cos(ang+(end-ang)*j/count),cy+r*math.sin(ang+(end-ang)*j/count)) for j in range(count+1)]
   if share:poly(s,pts,fill=TONES[i],stroke='bg')
   s.add(900,290+i*85,16,16,kind='rect',fill=TONES[i],stroke='none',check=False);s.text(935,278+i*85,410,70,f'{v["label"]}\n{v["value"]:g} · {share:.1%}',21);ang=end
  s.meta['shares']=[v['value']/total for v in a]
 elif mode=='bullet':
  a=items(d,'data',1,6);maximum=d['maximum'];need(finite(maximum) and maximum>0,'bullet maximum positive')
  for i,v in enumerate(a):
   need(all(finite(v[k]) and 0<=v[k]<=maximum for k in ('value','target')),'bullet outside scale');y=245+i*90;s.text(70,y,270,40,v['label'],20);xx=400;ww=s.w-620
   s.add(xx,y+7,ww,28,kind='rect',fill='tint2',stroke='none',check=False)
   if v['value']:s.add(xx,y+12,ww*v['value']/maximum,18,kind='rect',fill='accent',stroke='none',check=False)
   tx=xx+ww*v['target']/maximum;s.add(tx-1.5,y,3,42,kind='rect',fill='ink',stroke='none',check=False);s.text(xx+ww+20,y,175,60,f'{v["value"]:g} / {v["target"]:g}',18)
  s.text(400,230+len(a)*90,800,40,'条长 = 实绩；竖线 = 目标；统一量程 '+str(maximum),17,'muted')
 else:raise ValueError('unsupported plot mode: '+mode)

def floorplan(s,d):
 width,height=d['room_size'];need(width>0 and height>0,'invalid plan dimensions');scale=min(1100/width,480/height);x0,y0=240,240
 s.add(x0,y0,width*scale,height*scale,kind='rect',fill='panel',stroke='ink',stroke_width=3,radius=0,check=False)
 for v in d['zones']:
  x,y,w,h=v['rect'];need(min(x,y)>=0 and min(w,h)>0 and x+w<=width and y+h<=height,'zone outside room');s.add(x0+x*scale,y0+y*scale,w*scale,h*scale,v['label'],v.get('detail',''),kind='rect',stroke='line',radius=0,check=True)
 s.text(x0,y0+height*scale+22,width*scale,40,f'{width:g} m  ·  示意平面尺寸',19,'muted',align='center');s.text(65,y0+height*scale/2,150,42,f'{height:g} m',19,'muted');s.meta['units']='metres';s.meta['scale']=scale

def circuit(s,d):
 # A small topological teaching circuit. Component symbols are independently editable paths.
 x0,x1,y0,y1=300,1260,330,650
 s.edge(points=[(x0,y0),(600,y0)],arrow=False,tone='ink');s.edge(points=[(850,y0),(1000,y0)],arrow=False,tone='ink');s.edge(points=[(1110,y0),(x1,y0),(x1,y1),(x0,y1),(x0,510)],arrow=False,tone='ink');s.edge(points=[(x0,470),(x0,y0)],arrow=False,tone='ink')
 s.edge(points=[(250,470),(350,470)],arrow=False,tone='accent',width=4);s.edge(points=[(270,510),(330,510)],arrow=False,tone='ink',width=3);s.text(95,447,135,70,d.get('source','直流源'),22,'accent',align='right')
 s.add(600,y0-26,250,52,d.get('load','电阻 R'),kind='rect',stroke='ink',check=True)
 s.add(992,y0-6,12,12,kind='ellipse',fill='panel',stroke='ink',check=False);s.add(1104,y0-6,12,12,kind='ellipse',fill='panel',stroke='ink',check=False);s.edge(points=[(1004,y0),(1100,y0-68)],arrow=False,tone='ink');s.text(955,y0+30,235,50,d.get('switch','开关 S（断开）'),20,align='center')
 s.text(510,560,530,55,'断开状态：无闭合导电回路',22,'muted',align='center')

def processplant(s,d):
 # PFD functional shapes, deliberately without fabricated pipe classes or design ratings.
 units=items(d,'units',3,5);ids=[];gap=(s.w-240)/len(units)
 for i,v in enumerate(units):
  x=120+i*gap;y=352;kind={'tank':'cylinder','pump':'ellipse','process':'rect'}.get(v.get('kind'),'rect');id=s.add(x,y,220,160,v['label'],v.get('tag',''),kind=kind,id=v['id'],check=True);ids.append(id)
  s.text(x-12,y+188,244,70,v.get('detail',''),18,'muted',align='center')
 for i in range(len(ids)-1):s.edge(ids[i],ids[i+1],d.get('stream','物料流'),tone='accent',source_port='right',target_port='left')
 s.meta['notation']='conceptual PFD; not P&ID'

def infographic(s,d):
 a=items(d,lo=2,hi=6);cols=2;w=(s.w-160)/2;h=170
 for i,v in enumerate(a):
  x=64+i%2*(w+32);y=220+i//2*(h+24);s.add(x,y,w,h,kind='panel',check=False);s.text(x+24,y+20,100,65,f'{i+1:02d}',42,'accent');s.text(x+140,y+20,w-166,46,v['label'],25);s.text(x+140,y+76,w-166,72,v.get('detail',''),18,'muted')
 s.h=max(s.h,220+math.ceil(len(a)/2)*(h+24)+100)

BUILDERS={'radial':radial,'cycle':cycle,'tapered':tapered,'venn':venn,'concentric':concentric,'timeline':timeline,'table':table,'bmc':bmc,'quadrant':quadrant,'chevrons':chevrons,'treemap':treemap,'sankey':sankey,'record':record,'plot':plot,'floorplan':floorplan,'circuit':circuit,'processplant':processplant,'infographic':infographic}
