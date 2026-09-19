"""Regression checks for the v37 release candidate.

These tests assert visible data flow and rendered-output facts rather than a
byte-for-byte snapshot, so intentional layout improvements remain testable.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CROSS = load_module('diagram_studio_cross_v37', 'scripts/cross_industry.py')
REMAINING = load_module('diagram_studio_remaining_v37', 'scripts/remaining_types.py')
GENERIC = load_module('diagram_studio_render_v37', 'scripts/render.py')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def svg_text(path):
    root = ET.parse(path).getroot()
    return '\n'.join(''.join(node.itertext()) for node in root.iter('{http://www.w3.org/2000/svg}text'))


class V37OptimizationTests(unittest.TestCase):
    def test_graph_container_overflow_is_detected(self):
        data=read_json(ROOT/'assets/cross-industry-models/family-tree.json')
        data['nodes'][0]['label']='长中文姓名说明'*16
        with tempfile.TemporaryDirectory() as tmp:
            CROSS.render(data,tmp,'overflow')
            qa=read_json(Path(tmp)/'overflow.qa.json')
            self.assertTrue(any(x['scope']=='container' and x['container']=='node:gp1' for x in qa['text_overflow']))

    def test_gantt_dependencies_and_progress_have_parents(self):
        data=read_json(ROOT/'assets/examples/61-gantt-delivery.json')
        scene=GENERIC.build(data,'light')
        cells={x.get('id'):x for x in ET.fromstring(GENERIC.drawio(scene)).iter('mxCell')}
        actual={(x.get('source'),x.get('target')) for x in cells.values() if x.get('source')}
        expected={(dep,t['id']) for t in data['tasks'] for dep in t.get('depends',[])}
        self.assertEqual(actual,expected)
        for node in scene.nodes:
            if node.get('parent_task'):
                cell=cells[node['id']];self.assertEqual(cell.get('parent'),node['parent_task'])
                self.assertEqual(float(cell.find('mxGeometry').get('x')),0)

    def test_all_cross_and_remaining_models_have_clean_rendered_text_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for directory, renderer in (
                (ROOT / 'assets/cross-industry-models', CROSS),
                (ROOT / 'assets/remaining-type-models', REMAINING),
            ):
                for source in sorted(directory.glob('*.json')):
                    with self.subTest(source=source.name):
                        renderer.render(read_json(source), tmp / source.stem, source.stem)
                        qa = read_json(tmp / source.stem / f'{source.stem}.qa.json')
                        self.assertEqual(qa['errors'], [])
                        self.assertEqual(qa['warnings'], [])
                        self.assertEqual(qa['rendered_visual_check'], 'passed')
                        self.assertEqual(qa['manual_visual_review'], 'not-run')

    def test_financial_mutation_changes_visible_values_and_preserves_a4_ratio(self):
        data = read_json(ROOT / 'assets/acceptance-scenarios/finance-project-quotation.json')
        data['line_items'][1]['quantity'] = 3
        data['declared_total'] = 28196
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            calc = CROSS.render(data, tmp, 'quotation')
            svg = tmp / 'quotation.svg'
            page = ET.parse(svg).getroot()
            width = float(page.attrib['width'].removesuffix('pt'))
            height = float(page.attrib['height'].removesuffix('pt'))
            text = svg_text(svg)
            self.assertEqual(calc['total'], 28196)
            self.assertAlmostEqual(width / height, 210 / 297, places=3)
            self.assertIn('到货质检与交付复核 ×3', text)
            self.assertIn('¥28,196', text)
            self.assertNotIn('到货质检与交付复核 ×2', text)
            self.assertNotIn('¥25,440', text)

    def test_long_financial_line_is_reported_as_a_rendered_overflow(self):
        data = read_json(ROOT / 'assets/acceptance-scenarios/finance-project-quotation.json')
        data['line_items'][0]['label'] = '超长交付说明' * 80
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            CROSS.render(data, tmp, 'quotation')
            qa = read_json(tmp / 'quotation.qa.json')
            self.assertTrue(any(item.startswith('text overflow:') for item in qa['errors']))
            self.assertEqual(qa['rendered_visual_check'], 'issues-found')

    def test_three_gantt_layouts_share_truth_and_generate_clean_outputs(self):
        sources = [
            ROOT / 'assets/examples/60-gantt-executive.json',
            ROOT / 'assets/examples/61-gantt-delivery.json',
            ROOT / 'assets/examples/62-gantt-print.json',
        ]
        models = [read_json(path) for path in sources]
        self.assertTrue(all(model['tasks'] == models[0]['tasks'] for model in models[1:]))
        self.assertEqual([model['gantt_variant'] for model in models], ['executive', 'delivery', 'print'])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for source, model in zip(sources, models):
                with self.subTest(variant=model['gantt_variant']):
                    result = GENERIC.render_file(source, tmp / model['gantt_variant'])
                    self.assertEqual(result['qa']['errors'], [])
                    scene = read_json(tmp / model['gantt_variant'] / f'{source.stem}.scene.json')
                    self.assertEqual(scene['meta']['gantt_variant'], model['gantt_variant'])
                    self.assertEqual(scene['meta']['critical_path'], 'not-calculated')

    def test_acceptance_suite_exercises_eight_cross_industry_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env.setdefault('MPLCONFIGDIR', '/private/tmp/apat-mpl')
            env.setdefault('PYTHONPYCACHEPREFIX', '/private/tmp/apat-pyc')
            result = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/acceptance_suite.py'), '--out', tmp],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = read_json(Path(tmp) / 'acceptance-report.json')
            self.assertEqual(len(report['scenarios']), 8)
            finance = next(row for row in report['scenarios'] if row['id'] == 'finance-project-quotation')
            self.assertEqual(finance['mutation'], {'quantity': 3, 'total': 28196, 'stale_values_visible': False})
            self.assertEqual(report['gantt_variants']['variants'], ['executive', 'delivery', 'print'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
