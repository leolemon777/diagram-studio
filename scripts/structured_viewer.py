"""Offline N-S overview and native-size locator; preserves the complete SVG."""
import argparse,json,html
from pathlib import Path
from structured_render import build
from render import svg

def viewer(d):
 s,q=build(d);rows=[]
 def visit(body,path):
  for i,n in enumerate(body):
   label=n.get('text',n.get('condition',n.get('until',n.get('expression',''))))
   here=path+[str(i+1)+'. '+n['kind']+' ['+n['id']+']']
   rows.append(dict(id=n['id'],label=label,path=' → '.join(here)))
   if n['kind'] in ('while','repeat'):visit(n['body'],here+['循环体'])
   elif n['kind']=='if':
    visit(n['then'],here+['真分支']);visit(n['else'],here+['假分支'])
   elif n['kind']=='case':
    for b in n['branches']:visit(b['body'],here+['CASE '+b['label']])
    visit(n['default'],here+['默认分支'])
 visit(d['body'],[])
 data=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')
 return '''<!doctype html><html lang="zh"><meta charset="utf-8"><title>'''+html.escape(d['title'])+''' · 结构定位</title><style>
*{box-sizing:border-box}body{height:100vh;display:flex;flex-direction:column;margin:0;background:#F1EFEB;color:#30302D;font:16px/1.5 sans-serif}header{flex-shrink:0;padding:16px 22px;border-bottom:1px solid #bbb}h1{font-size:20px;margin:0 0 10px}.tools{display:flex;gap:12px;flex-wrap:wrap}select{max-width:65vw}button,select{font:inherit;padding:6px}#context{margin:10px 0 0;overflow-wrap:anywhere}#stage{flex:1;min-height:0;overflow:auto;border-top:1px solid #bbb}#stage svg{display:block;max-width:none}#stage.overview svg{width:100%;height:auto}.selected>rect{stroke:#AC6046;stroke-width:4}p.note{font-size:13px;margin:8px 0}button:focus,select:focus{outline:2px solid #AC6046}
</style><header><h1>'''+html.escape(d['title'])+'''</h1><div class="tools"><button id="overview">整图总览</button><button id="actual">原尺寸阅读</button><label>定位节点 <select id="nodes" aria-label="定位节点"></select></label></div><p id="context" aria-live="polite">请选择节点查看其结构路径。</p><p class="note">原尺寸可横向、纵向滚动。定位只突出显示节点，不折叠或截断分支；表达式未执行。</p></header><main id="stage" class="overview">'''+svg(s)+'''</main><script>
const rows='''+data+''',stage=document.getElementById('stage'),pick=document.getElementById('nodes');
const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='选择节点';pick.append(placeholder);
for(const r of rows){const o=document.createElement('option');o.value=r.id;o.textContent=r.id+' · '+r.label;pick.append(o)}
function native(){stage.classList.remove('overview')}
document.getElementById('overview').onclick=()=>{stage.classList.add('overview');stage.scrollTo(0,0)};
document.getElementById('actual').onclick=native;
pick.onchange=()=>{for(const el of stage.querySelectorAll('.selected'))el.classList.remove('selected');const r=rows.find(r=>r.id===pick.value);if(!r)return;native();const el=document.getElementById('node_'+r.id);el.classList.add('selected');document.getElementById('context').textContent=r.path+' — '+r.label;const box=el.getBoundingClientRect(),outer=stage.getBoundingClientRect();stage.scrollTo({left:stage.scrollLeft+box.left-outer.left-24,top:stage.scrollTop+box.top-outer.top-24,behavior:'instant'})};
</script></html>'''

def render_file(source,out):
 p=Path(source);d=json.loads(p.read_text());dest=Path(out);dest.mkdir(parents=True,exist_ok=True);target=dest/(p.stem+'.viewer.html');target.write_text(viewer(d));return str(target)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);a=p.parse_args();print(render_file(a.input,a.out))
