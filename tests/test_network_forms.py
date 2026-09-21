import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render
from adaptive_layout import normalize


class NetworkFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cn = json.loads((ROOT / 'assets/examples/network-cn.json').read_text())
        cls.en = json.loads((ROOT / 'assets/examples/network-en.json').read_text())

    def test_bilingual_network_keeps_ids_links_and_layout(self):
        cn_nodes, cn_edges, _ = normalize(self.cn)
        en_nodes, en_edges, _ = normalize(self.en)
        self.assertEqual([n['id'] for n in cn_nodes], [n['id'] for n in en_nodes])
        self.assertEqual([(e['from'], e['to']) for e in cn_edges], [(e['from'], e['to']) for e in en_edges])
        for data in (self.cn, self.en):
            before = copy.deepcopy(data)
            scene = render.build(data, 'light')
            self.assertEqual(data, before)
            self.assertEqual(render.audit(scene)['errors'], [])
            self.assertEqual(len(scene.nodes), len(data['nodes']) + 5)  # eyebrow, title, subtitle, rule and footer
            self.assertEqual(len(scene.edges), len(data['edges']))
            self.assertEqual(scene.meta['adaptive_layout']['readability']['status'], 'within-target')

    def test_edge_endpoints_and_labels_are_explicit(self):
        scene = render.build(self.en, 'light')
        ids = {n['id'] for n in scene.nodes if n.get('check')}
        self.assertEqual({e['source'] for e in scene.edges} | {e['target'] for e in scene.edges}, ids)
        self.assertTrue(all(e['label'] and e['source'] in ids and e['target'] in ids for e in scene.edges))
        self.assertGreaterEqual(sum(e.get('dashed', False) for e in scene.edges), 1)
        self.assertEqual(scene.meta['adaptive_layout']['crossings'], 0)

    def test_cn_fixture_uses_cross_industry_service_semantics(self):
        serialized = json.dumps(self.cn, ensure_ascii=False)
        self.assertNotIn('工单', serialized)
        self.assertIn('预约', serialized)
        self.assertIn('反馈', serialized)

    def test_invalid_endpoint_fails_before_render(self):
        bad = copy.deepcopy(self.en)
        bad['edges'][0]['to'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'unknown node'):
            render.build(bad, 'light')


if __name__ == '__main__':
    unittest.main()
