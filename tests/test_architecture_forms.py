"""Regression checks for the bilingual cross-industry architecture forms."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def load_render():
    spec = importlib.util.spec_from_file_location('diagram_studio_render_architecture', ROOT / 'scripts/render.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RENDER = load_render()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def item_truth(model):
    return [
        (item['id'], item['label'], item.get('detail', ''))
        for layer in model['layers']
        for item in layer['items']
    ]


class ArchitectureFormTests(unittest.TestCase):
    def setUp(self):
        self.cn = read_json(ROOT / 'assets/examples/architecture-cn.json')
        self.en = read_json(ROOT / 'assets/examples/architecture-en.json')

    def test_bilingual_architectures_share_stable_module_slots(self):
        self.assertEqual([item[0] for item in item_truth(self.cn)], [item[0] for item in item_truth(self.en)])
        self.assertEqual(len(self.cn['layers']), 4)
        self.assertEqual([len(layer['items']) for layer in self.cn['layers']], [3, 3, 3, 3])
        self.assertEqual(len(self.cn['crosscut']), len(self.en['crosscut']))

    def test_bilingual_architectures_render_cleanly_and_keep_all_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            for model, language, title in ((self.cn, 'cn', '社区服务平台 · 分层架构'), (self.en, 'en', 'Community service platform · layered architecture')):
                source = Path(tmp) / f'architecture-{language}.json'
                source.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
                result = RENDER.render_file(source, Path(tmp) / language)
                self.assertEqual(result['qa']['errors'], [])
                self.assertEqual(result['qa']['warnings'], [])
                self.assertEqual(result['qa']['content_integrity']['status'], 'passed')
                scene = read_json(Path(tmp) / language / f'architecture-{language}.scene.json')
                visible = '\n'.join(node['label'] + '\n' + node.get('detail', '') for node in scene['nodes'])
                self.assertIn(title, visible)
                for _, label, detail in item_truth(model):
                    self.assertIn(label, visible)
                    self.assertIn(detail, visible)
                ET.parse(result['svg'])
                ET.parse(result['drawio'])
                self.assertTrue((Path(tmp) / language / f'architecture-{language}.html').is_file())

    def test_committed_architecture_outputs_have_clean_receipts(self):
        for language in ('cn', 'en'):
            base = ROOT / 'demos/architecture' / language
            stem = f'architecture-{language}'
            qa = read_json(base / f'{stem}.qa.json')
            self.assertEqual(qa['errors'], [])
            self.assertEqual(qa['warnings'], [])
            self.assertEqual(qa['content_integrity']['status'], 'passed')
            receipt = read_json(base / f'{stem}.delivery.json')
            self.assertEqual(receipt['checks']['geometry']['status'], 'passed')
            self.assertEqual(receipt['checks']['content_integrity']['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
