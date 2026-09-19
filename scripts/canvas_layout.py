"""Canvas size, aspect-aware layout and resolution for editorial chart plates."""
from dataclasses import dataclass
import copy, math

@dataclass(frozen=True)
class Canvas:
 width: int
 height: int
 dpi: int = 144
 layout: str = 'adaptive'
 def __post_init__(self):
  if any(isinstance(v,bool) or not isinstance(v,int) for v in (self.width,self.height,self.dpi)):
   raise ValueError('Width, height and DPI must be integers.')
  if min(self.width,self.height)<128 or max(self.width,self.height)>16000:
   raise ValueError('Each edge must be 128–16000 px.')
  if self.width*self.height>40_000_000:raise ValueError('Use at most 40 million pixels per export.')
  if not 36<=self.dpi<=1200:raise ValueError('DPI must be 36–1200.')
  if self.layout not in ('adaptive','fit'):raise ValueError('Layout must be adaptive or fit.')
 @classmethod
 def resolve(cls,width=None,height=None,ratio=None,long_edge=1920,dpi=144,layout='adaptive'):
  if ratio:
   if width is not None or height is not None:raise ValueError('Choose ratio + long edge OR width + height.')
   try:
    a,b=map(float,ratio.replace('/',':').split(':'));r=a/b
   except (ValueError,ZeroDivisionError):raise ValueError('Ratio must be positive, such as 16:9 or 9:16.')
   if not math.isfinite(r) or r<=0 or a<=0 or b<=0:raise ValueError('Ratio must be positive.')
   width,height=(long_edge,round(long_edge/r)) if r>=1 else (round(long_edge*r),long_edge)
  elif width is None or height is None:raise ValueError('Provide both width and height, or a ratio.')
  return cls(width,height,dpi,layout)
 def metadata(self):
  g=math.gcd(self.width,self.height)
  return dict(width=self.width,height=self.height,ratio=f'{self.width//g}:{self.height//g}',dpi=self.dpi,
   layout=self.layout,physical_mm=[round(self.width/self.dpi*25.4,2),round(self.height/self.dpi*25.4,2)])

def arguments(parser):
 parser.add_argument('--width',type=int,help='Export width in pixels; requires --height')
 parser.add_argument('--height',type=int,help='Export height in pixels; requires --width')
 parser.add_argument('--ratio',help='Canvas ratio, e.g. 16:9, 9:16, 1:1 or 4:5')
 parser.add_argument('--long-edge',type=int,default=1920,help='Longest pixel edge when --ratio is used')
 parser.add_argument('--dpi',type=int,help='Print density; does not alter pixel dimensions (144 with explicit canvas)')
 parser.add_argument('--layout',choices=('adaptive','fit'),default='adaptive')

def from_args(args):
 if args.ratio or args.width is not None or args.height is not None:
  return Canvas.resolve(args.width,args.height,args.ratio,args.long_edge,144 if args.dpi is None else args.dpi,args.layout)
 if args.dpi is not None:return Canvas(1600,1000,args.dpi,'fit')
 return None

def bounds(items):
 points=[]
 for n in items:
  if n['kind']=='line':points.extend(n['points'])
  else:points.extend([(n['x'],n['y']),(n['x']+n['w'],n['y']+n['h'])])
 xs,ys=zip(*points);return min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)

def move(items,source,target,uniform=False,center=True):
 """Map chart coordinates; preserve circular marks and undistorted text glyphs."""
 x,y,w,h=source;tx,ty,tw,th=target;sx,sy=tw/w,th/h
 if uniform:
  sx=sy=min(sx,sy)
  if center:tx+=(tw-w*sx)/2;ty+=(th-h*sy)/2
 font_scale=min(sx,sy)
 for n in items:
  if n['kind']=='line':
   n['points']=[(tx+(px-x)*sx,ty+(py-y)*sy) for px,py in n['points']]
   n['lw']*=font_scale
   if 'dash_pattern' in n:n['dash_pattern']=[v*font_scale for v in n['dash_pattern']]
  else:
   nx,ny=tx+(n['x']-x)*sx,ty+(n['y']-y)*sy
   if n['kind']=='ellipse':
    cx,cy=nx+n['w']*sx/2,ny+n['h']*sy/2;n['w']*=font_scale;n['h']*=font_scale
    n['x'],n['y']=cx-n['w']/2,cy-n['h']/2
   else:
    n['x'],n['y']=nx,ny;n['w']*=sx;n['h']*=sy
   if n['kind']=='text':
    n['fs']*=font_scale;n['h']=len(n['lines'])*n['fs']*1.38
   else:n['lw']*=font_scale
 return items

class Frame:
 def __init__(self,p):self.p=p;self.count=0
 def key(self):self.count+=1;return 'canvas-frame-'+str(self.count)
 def text(self,x,y,w,text,fs=20,tone='ink',font='sans',weight=400,align='left'):
  ident=self.p.text(x,y,w,text,fs,tone,font,weight,align,id=self.key());return next(n for n in self.p.items if n['id']==ident)['h']
 def line(self,pts,tone='line',lw=.8):return self.p.line(pts,tone,lw,id=self.key())
 def rect(self,x,y,w,h,fill='none',stroke='line',lw=1):return self.p.rect(x,y,w,h,fill,stroke,lw,id=self.key())

def heading(p,f,w,h,data_art):
 m=60;wide=w/h>=1.35;name=p.f.get('english',p.f['name'])
 f.text(m,34,w-2*m,'APAT    /    '+name,14,'muted','mono')
 f.line([(m,73),(w-m,73)],'ink',1)
 ty=p.f.get('type',{});fs=46 if wide else 40
 y=99+f.text(m,99,w-2*m,p.data['title'],fs,'title_ink' if 'title_ink' in p.f else 'ink',ty.get('heading_font','serif'),ty.get('heading_weight',400))
 y+=20;y+=f.text(m,y,w-2*m,p.data.get('subtitle',p.data.get('deck','')),20,'muted',ty.get('body_font','sans'))
 y+=22;f.text(m,y,w-2*m,p.data.get('period',p.data.get('kicker','')),15,'accent')
 f.line([(m,h-68),(w-m,h-68)])
 source=(('模拟数据' if p.data.get('synthetic') else '来源数据')+' · '+p.data['source']) if data_art else p.data['footer']
 f.text(m,h-48,w-2*m,source,13,'muted')
 return m,y+48

def responsive_data(p,w,h):
 original=[copy.deepcopy(n) for n in p.items if n['id'] in p.plot_ids]
 p.items=[];p.ids=set(n['id'] for n in original);f=Frame(p);m,top=heading(p,f,w,h,True)
 wide=w/h>=1.35
 if wide:
  side=max(260,min(360,w*.2));px=m;pw=w-2*m-side-65;ph=h-top-150
  sx=w-m-side;f.line([(sx-28,top),(sx-28,h-120)])
  f.text(sx,top,side,p.kpi,56,'accent','grotesk');yy=top+85
  yy+=f.text(sx,yy,side,p.kpi_label,17,'muted')+28
  yy+=f.text(sx,yy,side,'01  观察',13,'accent','mono')+12
  yy+=f.text(sx,yy,side,p.reading,18)+26
  yy+=f.text(sx,yy,side,'02  边界',13,'accent','mono')+12
  f.text(sx,yy,side,p.caveat,16,'muted')
  plot=(px,top,pw,ph)
 else:
  notes_y=h-315;pw=w-2*m;plot=(m,top,pw,notes_y-top-48)
  f.line([(m,notes_y-18),(w-m,notes_y-18)])
  gap=30;cw=(w-2*m-2*gap)/3
  f.text(m,notes_y,cw,p.kpi,50,'accent','grotesk');f.text(m,notes_y+76,cw,p.kpi_label,17,'muted')
  for i,(label,body) in enumerate([('01  观察',p.reading),('02  边界',p.caveat)],1):
   x=m+i*(cw+gap);f.text(x,notes_y,cw,label,13,'accent','mono');f.text(x,notes_y+34,cw,body,17,'ink' if i==1 else 'muted')
 if plot[2]<300 or plot[3]<180:raise ValueError('This content needs more space. Choose fit layout or a less extreme ratio.')
 # Ring and count-field layouts retain isotropic geometry. Axes in other charts
 # use the new plot extent while circle areas and font proportions stay correct.
 if not wide and p.recipe in ('ring','field') and h/w>1.2:
  def legend(n):return min(x for x,_ in n['points'])>=780 if n['kind']=='line' else n['x']>=780
  symbols=[n for n in original if not legend(n)];labels=[n for n in original if legend(n)]
  px,py,pw,ph=plot;lh=min(ph*.38,350);gap=32
  move(symbols,bounds(symbols),(px,py,pw,ph-lh-gap),uniform=True)
  move(labels,bounds(labels),(px+20,py+ph-lh,pw-40,lh))
 else:move(original,bounds(original),plot,uniform=p.recipe in ('ring','field'))
 p.items.extend(original)
 f.text(m,h-119,w-2*m,p.encoding.replace('右侧','标签中') if not wide else p.encoding,16,'muted')

def vertical_workflow(p,b):
 x,y,w,h=b;nodes=p.data['nodes'];nw=min(490,w*.67);nh=90;gap=(h-5*nh)/4;left=x+(w-nw)/2;pos={}
 if gap<38:nh=72;gap=(h-5*nh)/4
 for i,n in enumerate(nodes):
  pos[n['id']]=(left,y+i*(nh+gap),nw,nh);p.boxnode(*pos[n['id']],n)
 for j,(a,c) in enumerate(p.data['edges']):
  ax,ay,aw,ah=pos[a];bx,by,bw,bh=pos[c]
  p.line([(ax+aw/2,ay+ah),(bx+bw/2,by)],'accent',1.6,True,source=a,target=c,id='process-'+str(j))
  if a=='verify':p.text(ax+aw/2+14,ay+ah+8,70,'是',16,'accent')
 a,c=p.data['feedback'];ax,ay,aw,ah=pos[a];bx,by,bw,bh=pos[c];right=x+w-18
 p.line([(ax+aw,ay+ah/2),(right,ay+ah/2),(right,by+bh/2),(bx+bw,by+bh/2)],'muted',1.2,True,True,source=a,target=c,id='rework')
 p.text(right-73,(ay+by)/2,70,'否 /\n重新处置',16,'muted')

def vertical_architecture(p,b):
 x,y,w,h=b;pos={};band=h/3;nw=(w-72)/2;nh=88
 for i,l in enumerate(p.data['layers']):
  yy=y+i*band;p.text(x,yy,w,l['name'],23,'accent',p.f['font'],500);p.line([(x,yy+39),(x+w,yy+39)])
  for j,n in enumerate(l['items']):
   pos[n['id']]=(x+j*(nw+72),yy+65,nw,nh);p.boxnode(*pos[n['id']],n)
 for j,(a,c) in enumerate(p.data['edges']):
  ax,ay,aw,ah=pos[a];bx,by,bw,bh=pos[c]
  pts=[(ax+aw,ay+ah/2),(bx,by+bh/2)] if ay==by else [(ax+aw/2,ay+ah),(ax+aw/2,ay+ah+24),(bx+bw/2,ay+ah+24),(bx+bw/2,by)]
  p.line(pts,'accent',1.5,True,source=a,target=c,id='flow-'+str(j))
 a,c=p.data['feedback'];ax,ay,aw,ah=pos[a];bx,by,bw,bh=pos[c]
 p.line([(ax+aw,ay+ah/2),(x+w+22,ay+ah/2),(x+w+22,y-15),(bx+bw/2,y-15),(bx+bw/2,by)],'muted',1,True,True,source=a,target=c,id='feedback')

def vertical_fishbone(p,b):
 x,y,w,h=b;cx=x+w/2;bands=(h-86)/3;branchw=w*.38
 p.line([(cx,y+10),(cx,y+h-55)],'accent',2.2,True,id='cause-spine')
 p.text(cx-180,y+h-42,360,p.data.get('effect','产能提升受限'),23,'ink',p.f['font'],500,'center')
 # Pair the original top/bottom categories into three levels, preserving order.
 for row in range(3):
  for side,index in enumerate((row,row+3)):
   cat=p.data['categories'][index];yy=y+row*bands;left=x if side==0 else x+w-branchw;startx=cx-96 if side==0 else cx+96;joiny=yy+bands-10
   p.text(left,yy,branchw,cat['label'].replace('｜',' / '),21,'accent',p.f['font'],500,id=cat['id'])
   p.line([(startx,yy+45),(cx,joiny)],'accent',1.5,id='rib-'+cat['id'])
   for j,c in enumerate(cat['causes']):
    cy=yy+45+j*(bands-60)/3;ix=startx+(cx-startx)*(cy+26-(yy+45))/(joiny-(yy+45))
    p.text(left,cy,branchw,c.get('display_label',c['label']),17,'ink',id=c['id'])
    p.line([(left+2,cy+26),(ix,cy+26)] if side==0 else [(ix,cy+26),(left+branchw-2,cy+26)],'line',.8)
    if c.get('priority'):p.rect(left-9,cy+6,3,13,'accent','none')

def responsive_structure(p,w,h):
 p.items=[];p.ids=set();f=Frame(p);m,top=heading(p,f,w,h,False);vertical=w/h<1.35
 notes_y=h-182;box=(m+10,top+15,w-2*m-30,notes_y-top-73)
 if box[3]<350:raise ValueError('This diagram needs more space. Choose fit layout or a less extreme ratio.')
 if vertical and p.data['form']!='trend':
  {'workflow':vertical_workflow,'architecture':vertical_architecture,'fishbone':vertical_fishbone}[p.data['form']](p,box)
 else:
  # Wide variants retain the family-specific structural composition.
  getattr(p,p.data['form'])(box)
 f.line([(m,notes_y-15),(w-m,notes_y-15)],'accent' if p.name=='archive' else 'line')
 gap=30;cw=(w-2*m-2*gap)/3
 for i,n in enumerate(p.data['notes']):
  xx=m+i*(cw+gap);f.text(xx,notes_y,cw,f'{i+1:02}',13,'accent','mono');f.text(xx,notes_y+25,cw,n,16,'muted')
 p.refine_visual_roles()

def apply_canvas(p,spec):
 if spec is None:return p
 if hasattr(p,'canvas'):raise ValueError('Build a fresh plate before changing the canvas.')
 metrics=copy.deepcopy(p.metrics)
 if spec.layout=='fit':
  move(p.items,(0,0,p.w,p.h),(0,0,spec.width,spec.height),uniform=True)
 else:
  ratio=spec.width/spec.height;base=1200 if 1<=ratio<1.35 else 1000
  w,h=(base*ratio,base) if ratio>=1 else (1000,1000/ratio)
  if hasattr(p,'recipe'):responsive_data(p,w,h)
  else:responsive_structure(p,w,h)
  move(p.items,(0,0,w,h),(0,0,spec.width,spec.height),uniform=True,center=False)
 p.w,p.h=spec.width,spec.height;p.dpi=spec.dpi;p.canvas=spec.metadata()
 p.metrics=metrics  # A presentation change must never change measurements.
 return p
