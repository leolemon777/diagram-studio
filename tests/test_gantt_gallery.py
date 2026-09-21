"""Regression checks for the bilingual Gantt gallery."""
from __future__ import annotations

import copy
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
    spec = importlib.util.spec_from_file_location('diagram_studio_render_gantt', ROOT / 'scripts/render.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RENDER = load_render()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


class GanttGalleryTests(unittest.TestCase):
    def setUp(self):
        self.cn = read_json(ROOT / 'assets/examples/gantt-cn.json')
        self.en = read_json(ROOT / 'assets/examples/gantt-en.json')

    def test_bilingual_inputs_share_task_truth(self):
        self.assertEqual(self.cn['language'], 'zh')
        self.assertEqual(self.en['language'], 'en')
        fields = ('id', 'start', 'end', 'progress', 'milestone', 'depends')
        cn = [{key: task.get(key) for key in fields} for task in self.cn['tasks']]
        en = [{key: task.get(key) for key in fields} for task in self.en['tasks']]
        self.assertEqual(cn, en)
        self.assertEqual([task['id'] for task in self.cn['tasks']], ['scope', 'content', 'partners', 'outreach', 'logistics', 'rehearsal', 'event'])

    def test_all_three_variants_keep_clean_qa_and_localized_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            for base, language, header in ((self.cn, 'zh', '任务 / 责任人'), (self.en, 'en', 'Task / owner')):
                for variant in ('executive', 'delivery', 'print'):
                    model = copy.deepcopy(base)
                    model['gantt_variant'] = variant
                    source = Path(tmp) / f'gantt-{language}-{variant}.json'
                    source.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
                    result = RENDER.render_file(source, Path(tmp) / f'out-{language}-{variant}')
                    self.assertEqual(result['qa']['errors'], [])
                    self.assertEqual(result['qa']['warnings'], [])
                    scene = read_json(Path(tmp) / f'out-{language}-{variant}' / f'gantt-{language}-{variant}.scene.json')
                    self.assertEqual(scene['meta']['gantt_variant'], variant)
                    self.assertEqual(scene['meta']['gantt_language'], language)
                    self.assertEqual(scene['meta']['critical_path'], 'not-calculated')
                    svg = ET.parse(result['svg']).getroot()
                    text = '\n'.join(''.join(node.itertext()) for node in svg.iter('{http://www.w3.org/2000/svg}text'))
                    if variant == 'delivery':
                        self.assertIn(header, text)
                    if variant == 'executive':
                        self.assertIn('◆', text)
                    else:
                        self.assertIn('Milestone' if language == 'en' else '里程碑', text)

    def test_unknown_gantt_language_is_rejected(self):
        model = copy.deepcopy(self.en)
        model['language'] = 'fr'
        with self.assertRaisesRegex(ValueError, 'language must be zh or en'):
            RENDER.build(model, 'light')

    def test_committed_gallery_receipts_and_xml_are_clean(self):
        for language in ('cn', 'en'):
            for variant in ('executive', 'delivery', 'print'):
                base = ROOT / 'demos/gantt' / language / variant
                stem = f'gantt-{language}-{variant}'
                qa = read_json(base / f'{stem}.qa.json')
                self.assertEqual(qa['errors'], [])
                self.assertEqual(qa['warnings'], [])
                self.assertEqual(qa['content_integrity']['status'], 'passed')
                ET.parse(base / f'{stem}.svg')
                ET.parse(base / f'{stem}.drawio')
                receipt = read_json(base / f'{stem}.delivery.json')
                self.assertEqual(receipt['checks']['geometry']['status'], 'passed')
                self.assertEqual(receipt['checks']['content_integrity']['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
