"""Observable semantic, layout and editability regressions for five common forms."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render
from adaptive_layout import normalize,rect,segment_hits
from refinement_suite import mutations,run


class RefinedTests(unittest.TestCase):
    def setUp(self):self.models=json.loads((ROOT/'assets/refinement-cases.json').read_text())

    def test_original_and_mutated_content_build_without_geometry_errors(self):
        for version,models in [('base',self.models),('changed',mutations(self.models))]:
            for key,d in models.items():
                with self.subTest(version=version,diagram=key):
                    before=copy.deepcopy(d);scene=render.build(d,'light');qa=render.audit(scene)
                    self.assertEqual(d,before);self.assertEqual(qa['errors'],[]);self.assertEqual(qa['warnings'],[])
                    self.assertIn('refined_layout',scene.meta)

    def test_graph_and_architecture_keep_every_object_relation_and_description(self):
        for models in [self.models,mutations(self.models)]:
            for key in ['workflow','architecture']:
                d=models[key];scene=render.build(d,'light');nodes,edges,_=normalize(d)
                for node in nodes:
                    self.assertEqual(scene.get(node['id'])['label'],node['label'])
                    self.assertEqual(scene.get(node['id'])['detail'],node.get('detail',''))
                self.assertEqual([(e['source'],e['target'],e['label']) for e in scene.edges],[(e['from'],e['to'],e.get('label','')) for e in edges])

    def test_architecture_modules_stay_inside_their_responsibility_band(self):
        for models in [self.models,mutations(self.models)]:
            d=models['architecture'];scene=render.build(d,'light')
            panels=[n for n in scene.nodes if n['kind']=='panel']
            for layer,panel in zip(d['layers'],panels):
                for item in layer['items']:
                    node=scene.get(item['id'])
                    self.assertGreaterEqual(node['x'],panel['x'])
                    self.assertLessEqual(node['x']+node['w'],panel['x']+panel['w']-20)
                    self.assertGreaterEqual(node['y'],panel['y'])
                    self.assertLessEqual(node['y']+node['h'],panel['y']+panel['h'])

    def test_primary_path_cannot_invent_a_relation(self):
        d=self.models['workflow'];d['layout']['primary_path']=['receive','close']
        with self.assertRaisesRegex(ValueError,'existing directed'):render.build(d,'light')

    def test_signed_comparison_uses_one_linear_scale_and_preserves_zero(self):
        d=self.models['comparison'];scene=render.build(d,'light');encoding=scene.meta['chart_encoding'];marks=encoding['marks']
        positive,_,negative,zero=marks
        self.assertGreater(positive['value_x'],positive['zero_x']);self.assertLess(negative['value_x'],negative['zero_x'])
        self.assertEqual(zero['value_x'],zero['zero_x'])
        self.assertAlmostEqual((positive['value_x']-positive['zero_x'])/positive['value'],(negative['value_x']-negative['zero_x'])/negative['value'])
        d['comparison_style']='dot';dot=render.build(d,'light')
        self.assertEqual(marks,dot.meta['chart_encoding']['marks'])

    def test_all_zero_and_invalid_numeric_values(self):
        d=self.models['comparison']
        for item in d['data']:item['value']=0
        scene=render.build(d,'light');self.assertEqual(render.audit(scene)['errors'],[])
        for value in [float('nan'),float('inf'),True,'12']:
            d['data'][0]['value']=value
            with self.assertRaises(ValueError):render.build(d,'light')

    def test_trend_calendar_spacing_and_missing_breaks_are_real(self):
        d=self.models['trend'];scene=render.build(d,'light');e=scene.meta['chart_encoding'];p=e['positions']
        self.assertAlmostEqual((p[2]['x']-p[1]['x'])/(p[1]['x']-p[0]['x']),5/2)
        self.assertEqual([len(segment) for segment in e['segments']],[3,3])
        self.assertIsNone(p[3]['y']);self.assertIsNone(scene.meta['data_values'][3])
        d['data'][1]['date']=d['data'][0]['date']
        with self.assertRaisesRegex(ValueError,'strictly increasing'):render.build(d,'light')

    def test_gantt_calendar_width_progress_and_dependency_avoidance(self):
        d=mutations(self.models)['gantt'];scene=render.build(d,'light');encoding=scene.meta['gantt_encoding']
        byid={t['id']:t for t in d['tasks']};bars=[scene.get(t['id']) for t in d['tasks']]
        for row in encoding['rows']:
            task=byid[row['id']]
            if not task.get('milestone'):
                days=(dt.date.fromisoformat(task['end'])-dt.date.fromisoformat(task['start'])).days+1
                self.assertAlmostEqual(row['bar'][2],days*encoding['day_width'])
        progress=next(n for n in scene.nodes if n.get('parent_task')=='outline')
        self.assertAlmostEqual(progress['w']/scene.get('outline')['w'],.63)
        relations=[e for e in scene.edges if e.get('source')]
        self.assertEqual({(e['source'],e['target']) for e in relations},{(parent,t['id']) for t in d['tasks'] for parent in t.get('depends',[])})
        for edge in relations:
            for bar in bars:
                if bar['id'] not in [edge['source'],edge['target']]:
                    self.assertFalse(any(segment_hits(a,b,rect(bar)) for a,b in zip(edge['points'],edge['points'][1:])))

    def test_long_titles_and_task_metadata_expand_without_truncation(self):
        d=self.models['gantt'];original=render.build(d,'light')
        d['title']='跨团队课程研发、内容上线与学习支持的完整执行计划 '*5
        d['tasks'][0]['label']='完成访谈、需求确认与特殊学习支持需求的联合评审 '*5
        d['tasks'][0]['owner']='课程负责人 / 教学支持 / 内容与质量评审 / 无障碍体验支持 '*3
        scene=render.build(d,'light');self.assertEqual(render.audit(scene)['errors'],[])
        self.assertGreater(scene.get('scope')['y'],original.get('scope')['y'])
        visible=''.join(n['label'] for n in scene.nodes)
        self.assertIn(d['tasks'][0]['label'],visible);self.assertIn(d['tasks'][0]['owner'],visible)

    def test_drawio_keeps_links_and_progress_as_native_objects(self):
        scene=render.build(self.models['gantt'],'light');xml=ET.fromstring(render.drawio(scene))
        cells={c.get('id'):c for c in xml.iter('mxCell')}
        self.assertTrue(any(c.get('parent')=='outline' for c in cells.values()))
        expected={(dep,t['id']) for t in self.models['gantt']['tasks'] for dep in t.get('depends',[])}
        self.assertEqual({(c.get('source'),c.get('target')) for c in cells.values() if c.get('source')},expected)

    def test_suite_delivers_all_views_and_bilingual_gallery(self):
        with tempfile.TemporaryDirectory() as tmp:
            records=run(tmp);self.assertEqual(len(records),11)
            for item in records:
                for field in ['svg','reader','drawio','source','receipt']:self.assertTrue((Path(tmp)/item[field]).is_file())
                self.assertGreaterEqual(item['minimum_font'],15)
            self.assertTrue((Path(tmp)/'index.html').is_file())


if __name__=='__main__':unittest.main()
