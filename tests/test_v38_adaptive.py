"""Observable content preservation, routing, pagination and compatibility."""
import copy
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render
from adaptive_layout import METRICS, normalize, rect, segment_hits
from adaptive_delivery import detail_scenes
from adaptive_examples import examples


def compact(text):return re.sub(r'\s+','',text)


class AdaptiveTests(unittest.TestCase):
    def test_stress_outputs_preserve_all_objects_and_relations(self):
        for key,d in examples().items():
            with self.subTest(case=key):
                before=copy.deepcopy(d);scene=render.build(d,'light');qa=render.audit(scene)
                self.assertEqual(d,before)
                self.assertEqual(qa['errors'],[]);self.assertEqual(qa['warnings'],[])
                nodes,edges,_=normalize(d)
                self.assertEqual([(e['source'],e['target'],e['label']) for e in scene.edges],[(e['from'],e['to'],e.get('label','')) for e in edges])
                for n in nodes:
                    actual=scene.get(n['id']);self.assertEqual(actual['label'],n['label'])
                    visible=''.join(line[0] for line in render.label_lines(actual))
                    self.assertEqual(compact(visible),compact(n['label']+n.get('detail','')))
                    self.assertTrue(all(line[1]>=17 for line in render.label_lines(actual)))
                for edge in scene.edges:
                    for n in scene.nodes:
                        if n.get('check') and n['id'] not in (edge['source'],edge['target']):
                            self.assertFalse(any(segment_hits(a,b,rect(n,1)) for a,b in zip(edge['points'],edge['points'][1:])))

    def test_reading_pages_have_every_node_and_edge_at_readable_size(self):
        for key,d in examples().items():
            scene=render.build(d,'light');pages,index=detail_scenes(scene,d)
            nodes,edges,_=normalize(d)
            self.assertEqual(set(index['nodes']),{n['id'] for n in nodes})
            self.assertEqual(len(index['edges']),len(edges))
            for p in pages:
                self.assertEqual((p.w,p.h),(1600,900))
                self.assertEqual(render.audit(p)['errors'],[])
            for n in nodes:
                chunks=[v for p in pages for v in p.nodes if v['id'].startswith(n['id']+'-part-')]
                text=compact(''.join(line[0] for v in chunks for line in v['_lines']))
                self.assertIn(compact(n['label']),text)
                self.assertIn(compact(n.get('detail','')),text)

    def test_extreme_long_content_continues_without_truncation(self):
        d={'type':'graph','title':'完整文字保留','nodes':[{'id':'long','label':'长期客户服务记录','detail':'每次处理保留时间、原因和后续责任。'*160}]}
        scene=render.build(d,'light');pages,index=detail_scenes(scene,d)
        self.assertGreater(len(index['nodes']['long']),1)
        all_lines=[]
        for p in pages:
            self.assertEqual((p.w,p.h),(1600,900));self.assertEqual(render.audit(p)['errors'],[])
            for n in p.nodes:
                if n['id'].startswith('long-part-'):
                    all_lines.extend(line[0] for line in n['_lines'] if line[1]==18)
        self.assertEqual(compact(''.join(all_lines)),compact(d['nodes'][0]['detail']))

    def test_label_changes_reflow_and_not_just_scale(self):
        d=examples()['product-feedback'];a=render.build(d,'light')
        d['nodes'][0]['detail']='补充完整的客户反馈、验证方法以及需要进一步跟进的处理结果。'*12
        b=render.build(d,'light')
        self.assertGreater(b.get('request')['h'],a.get('request')['h'])
        self.assertEqual(render.audit(b)['errors'],[])
        self.assertEqual([(e['source'],e['target']) for e in a.edges],[(e['source'],e['target']) for e in b.edges])

    def test_fixed_coordinates_and_theme_semantics_remain_stable(self):
        d={'type':'graph','title':'固定坐标','nodes':[{'id':'x','x':100,'y':250,'label':'位置保持'}]}
        self.assertEqual(render.build(d,'light').get('x')['x'],100)
        self.assertNotIn('adaptive_layout',render.build(d,'light').meta)
        d=examples()['product-feedback'];a=render.build(d,'light');b=render.build(d,'dark')
        self.assertEqual(a.nodes,b.nodes);self.assertEqual(a.edges,b.edges)

    def test_real_glyph_widths_and_cjk_last_line(self):
        lines=METRICS.wrap('收集用户反馈与业务问题',240,22)
        self.assertTrue(all(METRICS.width(x,22)<=241 for x in lines))
        self.assertGreater(len(lines[-1]),1)
        self.assertEqual(METRICS.wrap('前一段落\n短',240,22),['前一段落','短'])

    def test_mixed_font_sizes_do_not_overlap(self):
        scene=render.Scene({'title':'混合字号'},'light')
        scene.add(100,250,500,180,id='card',_lines=[('对象编号',14,False,'accent'),('完整中文标题',22,True,'ink'),('保留原始说明',18,False,'muted')])
        root=ET.fromstring(render.svg(scene))
        texts=list(root.iter('{http://www.w3.org/2000/svg}text'))
        previous_bottom=None
        for text in texts:
            size=int(text.get('font-size'));baseline=float(text.get('y'))
            bounds=METRICS.font(size).getbbox(text.text,anchor='ls') if METRICS.loader else (0,-size,0,0)
            top,bottom=baseline+bounds[1],baseline+bounds[3]
            if previous_bottom is not None:self.assertGreater(top,previous_bottom)
            previous_bottom=bottom

    def test_drawio_endpoints_and_multi_page_exports(self):
        d=examples()['product-feedback']
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json';source.write_text(json.dumps(d))
            render.render_file(source,Path(tmp)/'out')
            root=ET.parse(Path(tmp)/'out/input-reading.drawio').getroot()
            self.assertGreater(len(root.findall('diagram')),1)
            cells={c.get('id'):c for c in root.find('diagram').iter('mxCell')}
            for e in d['edges']:
                matches=[c for c in cells.values() if c.get('source')==e['from'] and c.get('target')==e['to']]
                self.assertEqual(len(matches),1)
                self.assertIsNotNone(matches[0].find('mxGeometry/mxPoint[@as="offset"]'))
            self.assertTrue((Path(tmp)/'out/input.html').is_file())

    def test_existing_examples_still_build(self):
        for path in (ROOT/'assets/examples').glob('*.json'):
            with self.subTest(source=path.name):
                scene=render.build(json.loads(path.read_text()),'light')
                self.assertEqual(render.audit(scene)['errors'],[])

    def test_unknown_nodes_and_duplicate_ids_fail(self):
        d=examples()['product-feedback'];d['edges'][0]['to']='missing'
        with self.assertRaises(ValueError):render.build(d,'light')
        d=examples()['education-tree'];d['root']['children'][0]['id']=d['root']['id']
        with self.assertRaises(ValueError):render.build(d,'light')


if __name__=='__main__':unittest.main(verbosity=2)
