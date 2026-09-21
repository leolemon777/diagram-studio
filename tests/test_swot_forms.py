"""Regression checks for the bilingual cross-industry SWOT forms."""
from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def load_render():
    spec = importlib.util.spec_from_file_location('diagram_studio_render_swot', ROOT / 'scripts/render.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RENDER = load_render()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


class SwotFormTests(unittest.TestCase):
    def setUp(self):
        self.cn = read_json(ROOT / 'assets/examples/swot-cn.json')
        self.en = read_json(ROOT / 'assets/examples/swot-en.json')

    def test_bilingual_swot_keeps_same_four_lenses_and_item_counts(self):
        self.assertEqual([cell['tone'] for cell in self.cn['cells']], [cell['tone'] for cell in self.en['cells']])
        self.assertEqual([len(cell['items']) for cell in self.cn['cells']], [3, 3, 3, 3])
        self.assertEqual([len(cell['items']) for cell in self.cn['cells']], [len(cell['items']) for cell in self.en['cells']])

    def test_bilingual_swot_renders_cleanly_and_keeps_every_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            for model, language, title in ((self.cn, 'cn', '社区服务平台 · SWOT 扫描'), (self.en, 'en', 'Community service platform · SWOT scan')):
                source = Path(tmp) / f'swot-{language}.json'
                source.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
                result = RENDER.render_file(source, Path(tmp) / language)
                self.assertEqual(result['qa']['errors'], [])
                self.assertEqual(result['qa']['warnings'], [])
                self.assertEqual(result['qa']['content_integrity']['status'], 'passed')
                scene = read_json(Path(tmp) / language / f'swot-{language}.scene.json')
                visible = '\n'.join(node['label'] + '\n' + node.get('detail', '') for node in scene['nodes'])
                self.assertIn(title, visible)
                for cell in model['cells']:
                    self.assertIn(cell['label'], visible)
                    for item in cell['items']:
                        self.assertIn(item, visible)
                ET.parse(result['svg'])
                ET.parse(result['drawio'])

    def test_committed_swot_outputs_have_clean_receipts(self):
        for language in ('cn', 'en'):
            base = ROOT / 'demos/swot' / language
            stem = f'swot-{language}'
            qa = read_json(base / f'{stem}.qa.json')
            self.assertEqual(qa['errors'], [])
            self.assertEqual(qa['warnings'], [])
            self.assertEqual(qa['content_integrity']['status'], 'passed')
            receipt = read_json(base / f'{stem}.delivery.json')
            self.assertEqual(receipt['checks']['geometry']['status'], 'passed')
            self.assertEqual(receipt['checks']['content_integrity']['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
