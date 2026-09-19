#!/usr/bin/env python3
"""Re-render an existing style_family Plate scene with a named share palette.

Keeps semantic data, geometry and numerical results; changes visual tokens and
the palette footer plus any known color-name legend wording. Does not recolor raster screenshots.
"""
import argparse,copy,hashlib,json
from pathlib import Path
from style_family import Plate,wrap

ROOT=Path(__file__).resolve().parents[1]
PALETTES={p['id']:p for p in json.loads((ROOT/'assets/share-palettes.json').read_text())['palettes']}

def luminance(c):
 rgb=[int(c[i:i+2],16)/255 for i in (1,3,5)]
 v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
 return sum(a*b for a,b in zip(v,[.2126,.7152,.0722]))

def contrast(a,b):
 a,b=sorted([luminance(a),luminance(b)])
 return (b+.05)/(a+.05)

def color_report(p):
 return {f'{role}_on_{surface}':round(contrast(p[role],p[surface]),3)
         for role in ('ink','muted','accent','cool') for surface in ('bg','tint')}

def semantic_hash(d):return hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def recolor(stem,palette,out,raster=True):
 stem=Path(stem);scene=json.loads(Path(str(stem)+'.scene.json').read_text())
 data=json.loads(Path(str(stem)+'.input.json').read_text())
 analysis_path=Path(str(stem)+'.analysis.json')
 metrics=json.loads(analysis_path.read_text()) if analysis_path.exists() else {}
 original=copy.deepcopy(scene['items']);p=PALETTES[palette]
 obj=Plate.__new__(Plate);obj.data=data;obj.metrics=metrics;obj.w=scene['width'];obj.h=scene['height'];obj.dpi=240
 obj.name=palette;obj.items=copy.deepcopy(original);obj.ids={n['id'] for n in obj.items}
 obj.f=copy.deepcopy(scene['palette']);oldname=obj.f['name']
 obj.f.update({k:p[k] for k in ('name','bg','ink','muted','line','accent','tint','cool')})
 obj.f.update(relation_ink=p['accent'],secondary_ink=p['muted'])
 if 'border' in p:obj.f['border']=p['border']
 for n in obj.items:
  if n['kind']=='text' and n.get('text','').startswith(oldname+'   /'):
   n['text']=n['text'].replace(oldname,p['name'],1);n['lines']=wrap(n['text'],n['w'],n['fs'])
  if n['kind']=='text' and '蓝墨为正相关，陶土为负相关。' in n.get('text','') and not p.get('original'):
   n['text']=n['text'].replace('蓝墨为正相关，陶土为负相关。','正负相关以两种墨色区分。');n['lines']=wrap(n['text'],n['w'],n['fs'])
  if n['kind'] in ('rect','diamond','ellipse') and n.get('stroke')=='line' and 'border' in p:n['stroke']='border'
 # Geometry, data and encoding (including all signs/dashes) are invariant.
 keys=('id','kind','x','y','w','h','points','fs','lw','arrow','dash','source','target','align','font','weight')
 assert [{k:n[k] for k in keys if k in n} for n in original]==[{k:n[k] for k in keys if k in n} for n in obj.items]
 qa=obj.audit();assert not qa['errors'],qa
 qa.update(palette=palette,semantic_sha256=semantic_hash(data),analysis_sha256=semantic_hash(metrics),geometry_unchanged=True,text_changes='palette footer and known color-name legend wording; numerical values unchanged',contrast=color_report(p))
 out=Path(out);out.mkdir(parents=True,exist_ok=True);dest=out/stem.name
 Path(str(dest)+'.svg').write_text(obj.svg())
 Path(str(dest)+'.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
 if raster:obj.raster(dest)
 return qa

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('source',help='Path stem without .scene.json suffix')
 parser.add_argument('--palette',required=True,choices=PALETTES)
 parser.add_argument('--out',required=True)
 parser.add_argument('--vector-only',action='store_true')
 args=parser.parse_args();print(json.dumps(recolor(args.source,args.palette,args.out,not args.vector_only),ensure_ascii=False))
