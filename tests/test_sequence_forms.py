import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render


class SequenceFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cn = json.loads((ROOT / 'assets/examples/sequence-cn.json').read_text())
        cls.en = json.loads((ROOT / 'assets/examples/sequence-en.json').read_text())

    def test_bilingual_sequence_preserves_actor_and_message_order(self):
        for data in (self.cn, self.en):
            before = copy.deepcopy(data)
            scene = render.build(data, 'light')
            self.assertEqual(data, before)
            qa = render.audit(scene)
            self.assertEqual(qa['errors'], [])
            self.assertEqual(qa['warnings'], [])
            self.assertEqual([e['label'] for e in scene.edges[4:]], [f'{i:02d}  {m["label"]}' for i, m in enumerate(data['messages'], 1)])

    def test_bilingual_topology_and_return_direction_match(self):
        self.assertEqual([a['id'] for a in self.cn['actors']], [a['id'] for a in self.en['actors']])
        self.assertEqual([(m['from'], m['to'], m.get('return', False)) for m in self.cn['messages']], [(m['from'], m['to'], m.get('return', False)) for m in self.en['messages']])
        for data in (self.cn, self.en):
            scene = render.build(data, 'light')
            message_edges = scene.edges[4:]
            self.assertEqual(sum(edge.get('dashed', False) for edge in message_edges), 3)
            self.assertEqual([edge['label'].split('  ', 1)[1] for edge in message_edges], [m['label'] for m in data['messages']])
            actor_x = {actor['id']: 120 + i * ((1600 - 240) / len(data['actors'])) + ((1600 - 240) / len(data['actors'])) / 2 for i, actor in enumerate(data['actors'])}
            for edge, message in zip(message_edges, data['messages']):
                self.assertEqual(edge['points'][0][0], actor_x[message['from']])
                self.assertEqual(edge['points'][-1][0], actor_x[message['to']])

    def test_unknown_actor_fails_before_render(self):
        bad = copy.deepcopy(self.en)
        bad['messages'][0]['to'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'unknown sequence actor'):
            render.build(bad, 'light')


if __name__ == '__main__':
    unittest.main()
