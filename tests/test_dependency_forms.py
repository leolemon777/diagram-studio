import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render
from adaptive_layout import normalize


class DependencyFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cn = json.loads((ROOT / 'assets/examples/dependency-cn.json').read_text())
        cls.en = json.loads((ROOT / 'assets/examples/dependency-en.json').read_text())

    def test_bilingual_dependency_keeps_dag_topology_and_readability(self):
        cn_nodes, cn_edges, _ = normalize(self.cn)
        en_nodes, en_edges, _ = normalize(self.en)
        self.assertEqual([n['id'] for n in cn_nodes], [n['id'] for n in en_nodes])
        self.assertEqual([(e['from'], e['to']) for e in cn_edges], [(e['from'], e['to']) for e in en_edges])
        for data in (self.cn, self.en):
            before = copy.deepcopy(data)
            scene = render.build(data, 'light')
            self.assertEqual(data, before)
            qa = render.audit(scene)
            self.assertEqual(qa['errors'], [])
            self.assertEqual(qa['warnings'], [])
            self.assertEqual(scene.meta['adaptive_layout']['crossings'], 0)
            self.assertEqual(scene.meta['adaptive_layout']['readability']['status'], 'within-target')

    def test_dependency_edges_are_explicit_and_acyclic(self):
        data = self.en
        ids = {node['id'] for node in data['nodes']}
        edges = [(edge['from'], edge['to']) for edge in data['edges']]
        self.assertTrue(all(source in ids and target in ids and source != target for source, target in edges))
        outgoing = {node: [] for node in ids}
        for source, target in edges:
            outgoing[source].append(target)
        seen, active = set(), set()
        def visit(node):
            if node in active:
                return False
            if node in seen:
                return True
            active.add(node)
            if not all(visit(child) for child in outgoing[node]):
                return False
            active.remove(node); seen.add(node); return True
        self.assertTrue(all(visit(node) for node in ids))

    def test_unknown_dependency_endpoint_fails(self):
        bad = copy.deepcopy(self.en)
        bad['edges'][0]['to'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'unknown node'):
            render.build(bad, 'light')


if __name__ == '__main__':
    unittest.main()
