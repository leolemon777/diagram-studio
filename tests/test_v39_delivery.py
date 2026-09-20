"""Regression evidence for parallel branches and validated staged delivery."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render
from adaptive_layout import ranks


class DeliveryTests(unittest.TestCase):
    def workflow(self):
        return json.loads((ROOT/'assets/examples-en/workflow.json').read_text())

    def test_branches_remain_parallel_beside_a_return_loop(self):
        data=self.workflow();original=copy.deepcopy(data)
        scene=render.build(data,'light')
        self.assertEqual(data,original)
        self.assertEqual([(e['source'],e['target'],e['label']) for e in scene.edges],
                         [(e['from'],e['to'],e['label']) for e in data['edges']])
        a,b=scene.get('self_help'),scene.get('agent')
        direction=scene.meta['adaptive_layout']['strategy']
        axis='x' if direction=='right' else 'y'
        self.assertEqual(a[axis],b[axis])
        self.assertLess(scene.get('triage')[axis],a[axis])
        self.assertGreater(scene.get('confirm')[axis],a[axis])
        self.assertEqual(scene.meta['adaptive_layout']['crossings'],0)
        self.assertEqual(render.audit(scene)['errors'],[])
        self.assertIn('Resolved?', [line[0] for line in scene.get('confirm')['_lines']])

    def test_explicit_feedback_survives_source_reordering(self):
        data=self.workflow();data['nodes'].reverse()
        data['edges'][-1]['role']='return'
        levels=ranks(data['nodes'],data['edges'])
        self.assertEqual(levels['agent'],levels['self_help'])
        for edge in data['edges'][:-1]:
            self.assertLess(levels[edge['from']],levels[edge['to']])
        scene=render.build(data,'light')
        self.assertTrue(any(e['source']=='confirm' and e['target']=='agent' and e['label']=='No' for e in scene.edges))

    def test_acyclic_relations_do_not_depend_on_node_input_order(self):
        nodes=[{'id':v} for v in ['end','middle','start']]
        edges=[{'from':'start','to':'middle'},{'from':'middle','to':'end'}]
        levels=ranks(nodes,edges)
        self.assertLess(levels['start'],levels['middle']);self.assertLess(levels['middle'],levels['end'])

    def test_receipt_hashes_match_exact_delivered_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'workflow.json';source.write_text(json.dumps(self.workflow()))
            out=Path(tmp)/'out';result=render.render_file(source,out)
            receipt=json.loads(Path(result['receipt']).read_text())
            self.assertEqual(receipt['input_sha256'],hashlib.sha256(source.read_bytes()).hexdigest())
            for name,digest in receipt['files'].items():
                self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),digest)
            self.assertEqual(receipt['checks']['browser_text_bounds']['status'],'not-run')
            self.assertEqual(receipt['checks']['manual_visual_review']['status'],'not-run')
            self.assertTrue(Path(result['reading_view']['html']).exists())

    def test_late_detail_failure_preserves_entire_last_good_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'workflow.json';source.write_text(json.dumps(self.workflow()))
            out=Path(tmp)/'out';render.render_file(source,out)
            before={p.name:p.read_bytes() for p in out.iterdir()}
            changed=self.workflow();changed['title']='Updated title';source.write_text(json.dumps(changed))
            with patch('adaptive_delivery.deliver',side_effect=ValueError('detail page failed')):
                with self.assertRaises(ValueError):render.render_file(source,out)
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})
            self.assertEqual(list(Path(tmp).glob('.diagram-stage-*')),[])

    def test_large_overview_reports_readability_separately_from_geometry(self):
        data=self.workflow();data['width']=6000
        scene=render.build(data,'light');qa=render.audit(scene)
        self.assertEqual(qa['errors'],[])
        readability=qa['adaptive_layout']['readability']
        self.assertEqual(readability['status'],'review-required')
        self.assertLess(readability['projected_minimum_font_px'],12)
        self.assertTrue(qa['adaptive_layout']['detail_pages_recommended'])


if __name__=='__main__':unittest.main()
