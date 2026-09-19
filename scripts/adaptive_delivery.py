"""Reading-size detail pages and a local, offline reader for adaptive scenes."""
from __future__ import annotations

import copy
import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from adaptive_layout import METRICS, normalize


def detail_scenes(scene, data):
    from render import Scene, build, audit
    nodes,edges,bands=normalize(data)
    node_pages={n['id']:[] for n in nodes}
    pages=[]
    band_names={nid:b['label'] for b in bands for nid in b['ids']}
    by_id={n['id']:n for n in nodes}
    local_views=[]
    if scene.meta['adaptive_layout'].get('detail_pages_recommended'):
        # True diagram details accompany the complete text/relationship index.
        # Only labels are shown here; full descriptions remain on object pages.
        groups=([by_id[v] for v in b['ids'][i:i+3]] for b in bands for i in range(0,len(b['ids']),3)) if bands else (nodes[i:i+3] for i in range(0,len(nodes),3))
        groups=list(groups)
        for i,group in enumerate(groups):
            ids={n['id'] for n in group}
            outside=[j+1 for j,e in enumerate(edges) if (e['from'] in ids)!=(e['to'] in ids)]
            neighbors=[]
            for e in edges:
                if (e['from'] in ids)!=(e['to'] in ids):
                    v=e['to'] if e['from'] in ids else e['from']
                    if v not in neighbors:neighbors.append(v)
            context=neighbors[:3]
            shown=ids|set(context)
            inside=[e for e in edges if e['from'] in shown and e['to'] in shown]
            visible_nodes=[{k:v for k,v in n.items() if k in ('id','label','kind','tone')} for n in group]
            visible_nodes += [{**{k:v for k,v in by_id[nid].items() if k in ('id','label','kind')},'tone':'muted','detail':'跨页参照'} for nid in context]
            refs='、'.join(f'R{j:02d}' for j in outside)
            local={'type':'graph','title':f'局部关系 · {i+1}/{len(groups)}','subtitle':data['title'],
                   'eyebrow':'DIAGRAM STUDIO / 阅读详图','footer':('跨页关系 '+refs+'：见完整关系索引。' if refs else '本页对象的完整说明见对象详解。'),
                   'style':data.get('style',{}),'layout':{'direction':'auto'},
                   'nodes':visible_nodes, 'edges':inside}
            try:view=build(local,scene.theme)
            except ValueError:continue
            if view.w>1600 or view.h>900:
                # Keep the core diagram if adding neighbor context overfills a page.
                context=[]
                local['nodes']=visible_nodes[:len(group)]
                local['edges']=[e for e in edges if e['from'] in ids and e['to'] in ids]
                try:view=build(local,scene.theme)
                except ValueError:continue
            if view.w<=1600 and view.h<=900 and not audit(view)['errors']:
                view.meta['reading_finished']=True
                pages.append(view)
                local_views.append({'page':len(pages),'nodes':[n['id'] for n in group],'context_nodes':context,'cross_page_relations':outside})

    def new_page(section):
        p=Scene({'title':section,'subtitle':data['title'],'eyebrow':'DIAGRAM STUDIO / 阅读详图','width':1600,'height':900,'footer':'完整内容保留 · 对象编号对应总览与关系索引','style':data.get('style',{})},scene.theme)
        p.meta['adaptive_layout']={'page_kind':section}
        pages.append(p)
        return p

    p=None;column=0;y=230
    for n in nodes:
        width=684
        lines=[(t,22,True,'ink') for t in METRICS.wrap(n['label'],width-40,22)]
        if n.get('detail'):
            lines += [(t,18,False,'muted') for t in METRICS.wrap(n['detail'],width-40,18)]
        chunks=[];chunk=[];height=0
        for line in lines:
            if height+line[1]*1.35>430 and chunk:
                chunks.append(chunk);chunk=[];height=0
            chunk.append(line);height+=line[1]*1.35
        if chunk:chunks.append(chunk)
        for i,chunk in enumerate(chunks):
            head=n['id']+(' · '+band_names[n['id']] if n['id'] in band_names else '')
            if len(chunks)>1:head+=f' · 续 {i+1}/{len(chunks)}'
            head_lines=[(t,14,False,'accent') for t in METRICS.wrap(head,width-40,14)]
            combined=head_lines+chunk
            height=sum(z[1]*1.35 for z in combined)+44
            if p is None or y+height>786:
                if p is not None and column==0:
                    column=1;y=230
                else:
                    p=new_page('对象详解');column=0;y=230
            x=64+column*788
            p.add(x,y,width,height,n['label'],n.get('detail',''),id=n['id']+f'-part-{i}',check=True,_lines=combined,font_family=METRICS.family,text_margin=20)
            node_pages[n['id']].append(len(pages))
            y+=height+24
    edge_pages=[]
    p=None;y=230
    # All edges appear once in this index, including cross-page relations.
    for index,e in enumerate(edges):
        source=by_id[e['from']]['label'];target=by_id[e['to']]['label']
        relation=e.get('label','') or ('关系' if e.get('arrow',True) else '关联')
        lines=[(t,20,True,'ink') for t in METRICS.wrap(f'{source} → {target}' if e.get('arrow',True) else f'{source} — {target}',1380,20)]
        lines += [(t,17,False,'muted') for t in METRICS.wrap(relation,1380,17)]
        locator=f'R{index+1:02d} · {e["from"]} · P{node_pages[e["from"]][0]:02d}  →  {e["to"]} · P{node_pages[e["to"]][0]:02d}'
        lines += [(locator,14,False,'accent')]
        chunks=[];chunk=[];height=0
        for line in lines:
            if height+line[1]*1.35>460 and chunk:
                chunks.append(chunk);chunk=[];height=0
            chunk.append(line);height+=line[1]*1.35
        if chunk:chunks.append(chunk)
        placements=[]
        for part,chunk in enumerate(chunks):
            height=sum(z[1]*1.35 for z in chunk)+36
            if p is None or y+height>786:
                p=new_page('完整关系索引');y=230
            p.add(64,y,1472,height,relation,id=f'relation-{index}-{part}',check=True,_lines=chunk,font_family=METRICS.family,text_margin=20)
            placements.append(len(pages));y+=height+16
        edge_pages.append({'index':index,'from':e['from'],'to':e['to'],'label':e.get('label',''),'pages':placements})
    for i,p in enumerate(pages):
        if p.meta.get('reading_finished'):continue
        p.spec['eyebrow']+=f' / P{i+1:02d}'
        p.finish()
    return pages,{'nodes':node_pages,'edges':edge_pages,'local_views':local_views,'source_node_count':len(nodes),'source_edge_count':len(edges)}


def deliver(scene,data,out,stem):
    from render import svg,drawio,audit
    out=Path(out)
    pages,index=detail_scenes(scene,data)
    combined=ET.fromstring(drawio(scene))
    combined.find('diagram').set('name','结构总览')
    records=[]
    for i,p in enumerate(pages):
        qa=audit(p)
        if qa['errors'] or qa['warnings']:
            raise ValueError('detail page failed: '+str(qa))
        name=f'{stem}-p{i+1:02d}'
        (out/(name+'.svg')).write_text(svg(p),encoding='utf-8')
        (out/(name+'.qa.json')).write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
        page=ET.fromstring(drawio(p)).find('diagram')
        page.set('id',f'page-{i+1}');page.set('name',f'P{i+1:02d} '+p.spec['title'])
        combined.append(page)
        records.append({'file':name+'.svg','title':f'P{i+1:02d} '+p.spec['title'],'width':p.w,'height':p.h})
    (out/(stem+'-reading.drawio')).write_text(ET.tostring(combined,encoding='unicode',xml_declaration=True),encoding='utf-8')
    index['pages']=records
    (out/(stem+'-reading.json')).write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    items=[{'file':stem+'.svg','title':'结构总览','width':scene.w,'height':scene.h}]+records
    options=''.join(f'<option value="{html.escape(x["file"],quote=True)}">{html.escape(x["title"])}</option>' for x in items)
    title=html.escape(data['title'])
    page_json=json.dumps(items,ensure_ascii=False).replace('<','\\u003c')
    (out/'browser_quality.js').write_text(Path(__file__).with_name('browser_quality.js').read_text(),encoding='utf-8')
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#e7e5e0;color:#30302d;font:15px/1.6 system-ui,sans-serif}}header{{padding:18px 28px;background:#fefdf9;border-bottom:1px solid #d8d3c8;display:flex;gap:18px;align-items:center;flex-wrap:wrap}}h1{{font-size:18px;margin:0;flex:1}}select,button,a{{font:inherit}}select,button{{padding:8px 12px;border:1px solid #c7c4bd;background:#fff;border-radius:6px}}a{{color:#86503f}}main{{height:calc(100vh - 132px);overflow:auto;padding:24px;text-align:center}}object{{background:#f1efeb;box-shadow:0 8px 32px #0001;display:block;margin:auto}}footer{{padding:9px 28px;background:#fefdf9;font-size:13px}}button{{cursor:pointer}}</style>
<header><h1>{title}</h1><select aria-label="阅读页面">{options}</select><button id="fit">适合窗口</button><button id="width">阅读宽度</button><button id="actual">原始尺寸</button><a href="{html.escape(stem,quote=True)}-reading.drawio">可编辑多页源</a><a href="{html.escape(stem,quote=True)}.brief.json">内容数据</a></header>
<main><object type="image/svg+xml" aria-label="图示"></object></main><footer>总览用于看关系；对象详解保留长文字，关系索引标明跨页去向。<span id="quality" aria-live="polite"></span></footer>
<script src="browser_quality.js"></script><script>const pages={page_json};let mode='auto';const pick=document.querySelector('select'),obj=document.querySelector('object'),main=document.querySelector('main');obj.addEventListener('load',async()=>{{await obj.contentDocument.fonts.ready;const report=diagramQuality(obj.contentDocument);document.querySelector('#quality').textContent=report.status==='passed'?'本页文字边界检查通过。':'本页文字边界需要复核。';document.querySelector('#quality').dataset.report=JSON.stringify(report);}});function show(){{const p=pages.find(x=>x.file===pick.value);if(obj.getAttribute('data')!==p.file){{obj.data=p.file;main.scrollTop=0;}}const m=mode==='auto'?(p.height/p.width>1.2?'width':'fit'):mode;const scale=m==='actual'?1:Math.min((main.clientWidth-48)/p.width,m==='width'?1:(main.clientHeight-48)/p.height,1);obj.style.width=p.width*scale+'px';obj.style.height=p.height*scale+'px';}}pick.addEventListener('change',()=>{{mode='auto';show()}});document.querySelector('#fit').onclick=()=>{{mode='fit';show()}};document.querySelector('#width').onclick=()=>{{mode='width';show()}};document.querySelector('#actual').onclick=()=>{{mode='actual';show()}};window.addEventListener('resize',show);show();</script></html>'''
    target=out/(stem+'.html');target.write_text(page,encoding='utf-8')
    return {'html':str(target),'detail_pages':len(pages),'index':str(out/(stem+'-reading.json'))}
