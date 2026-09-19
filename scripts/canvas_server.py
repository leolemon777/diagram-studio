#!/usr/bin/env python3
"""Local-only canvas preview. python canvas_server.py --out output/canvas --port 8767"""
import argparse, hashlib, importlib, json, logging, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.Lock()
def catalog():
 from style_family import FAMILIES,FORMS
 from data_art import RECIPES,PALETTES
 return dict(styles=list(FAMILIES.values()),forms=FORMS,recipes={k:v[0] for k,v in RECIPES.items()},themes=list(PALETTES.values()))

def render(payload,out,raster=False):
 # Reload local authoring modules so a running preview reflects saved changes.
 import style_family,data_art,canvas_layout
 with LOCK:
  importlib.reload(style_family);importlib.reload(data_art);importlib.reload(canvas_layout)
  kind=payload.get('kind','style');name=payload.get('name','workflow');variant=payload.get('variant','ledger' if kind=='style' else 'warm');mode=payload.get('mode','detail')
  spec=canvas_layout.Canvas(int(payload['width']),int(payload['height']),int(payload.get('dpi',144)),payload.get('layout','adaptive'))
  valid=style_family.FORMS if kind=='style' else data_art.RECIPES
  if kind not in ('style','data') or name not in valid:raise ValueError('Unknown chart.')
  asset=ROOT/'assets'/('style-family-examples' if kind=='style' else 'data-art-examples')/(name+'.json')
  data=json.loads(asset.read_text())
  engine=''.join(hashlib.sha256((ROOT/'scripts'/f).read_bytes()).hexdigest() for f in ('style_family.py','data_art.py','canvas_layout.py'))
  key=hashlib.sha256(json.dumps([payload,data,engine],sort_keys=True).encode()).hexdigest()[:20]
  dest=out/'renders'/key;stem=dest/name
  p=style_family.Plate(data,variant).build() if kind=='style' else data_art.DataPlate(data,mode,variant).build()
  canvas_layout.apply_canvas(p,spec)
  if not stem.with_suffix('.svg').exists() or (raster and not stem.with_suffix('.png').exists()):p.save(dest,raster)
  extensions=['svg','drawio','input.json','canvas.json','scene.json','analysis.json','qa.json']+(['html','csv'] if kind=='data' else [])
  if raster:extensions+=['png','pdf']
  return dict(canvas=spec.metadata(),files={e:f'/renders/{key}/{name}.{e}' for e in extensions},qa=p.audit(),title=data['title'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--port',type=int,default=8767);a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 logging.getLogger('fontTools').setLevel(logging.ERROR)
 class Handler(SimpleHTTPRequestHandler):
  def __init__(self,*args,**kw):super().__init__(*args,directory=str(out),**kw)
  def send_json(self,value,status=200):
   body=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
  def do_GET(self):
   path=self.path.split('?')[0]
   if path=='/api/catalog':return self.send_json(catalog())
   if path in ('/','/index.html'):
    body=(ROOT/'assets/canvas-studio.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
   if path.startswith('/renders/'):return super().do_GET()
   self.send_error(404)
  def do_POST(self):
   if self.path not in ('/api/preview','/api/export'):return self.send_error(404)
   # The UI is local. Cross-origin pages cannot drive file creation.
   origin=self.headers.get('Origin')
   if origin and origin not in (f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}'):return self.send_error(403)
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<8192:raise ValueError('Invalid request size.')
    payload=json.loads(self.rfile.read(size));result=render(payload,out,self.path=='/api/export');self.send_json(result)
   except (ValueError,KeyError,TypeError) as e:self.send_json(dict(error=str(e)),400)
   except Exception:
    logging.exception('Canvas export failed');self.send_json(dict(error='导出失败，请查看本地服务日志。'),500)
 print(f'Canvas Studio: http://127.0.0.1:{a.port}',flush=True)
 ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()
