import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_contract
import kanban_model
import kanban_render
import render


class StrategyExecutionTests(unittest.TestCase):
    def test_bilingual_swot_retains_cells_and_passes_geometry(self):
        examples = [json.loads((ROOT / "assets/examples" / name).read_text()) for name in ("07-swot.json", "07-swot-en.json")]
        for name, data in zip(("07-swot.json", "07-swot-en.json"), examples):
            source = ROOT / "assets/examples" / name
            scene = render.build(data, "light")
            self.assertEqual(render.audit(scene)["errors"], [], name)
            payload = {"nodes": scene.nodes, "edges": scene.edges}
            integrity = delivery_contract.content_integrity(data, payload)
            self.assertEqual(integrity["status"], "passed", name)
            source_text = "\n".join(
                [cell["label"] for cell in data["cells"]]
                + [item for cell in data["cells"] for item in cell["items"]]
            )
            rendered_text = "\n".join(node["label"] for node in scene.nodes)
            for value in source_text.split("\n"):
                self.assertIn(value, rendered_text, name)
        self.assertIn("服务", examples[0]["title"])
        self.assertIn("service", examples[1]["title"].lower())

    def test_bilingual_kanban_localizes_ui_and_preserves_limits(self):
        cases = (
            ("cross-industry-kanban.json", ("快照", "阻塞", "显式策略")),
            ("cross-industry-kanban-en.json", ("Snapshot", "Blocked", "Explicit policies")),
        )
        for name, markers in cases:
            source = ROOT / "assets/kanban-models" / name
            data = json.loads(source.read_text())
            model = kanban_model.validate(data)
            geometry = kanban_render.layout(model)
            self.assertLessEqual(model["column_wip"]["ready"], 3, name)
            self.assertEqual(model["counts"]["blocked"], 1, name)
            svg = kanban_render.render_svg(model, geometry)
            drawio = kanban_render.render_drawio(model, geometry)
            for marker in markers:
                self.assertIn(marker, svg, name)
            self.assertIn("mxfile", drawio, name)
            with tempfile.TemporaryDirectory() as tmp:
                result = kanban_render.render(source, Path(tmp))
                self.assertEqual(result["errors"], [], name)
                self.assertTrue((Path(tmp) / f"{source.stem}.qa.json").is_file(), name)

    def test_legacy_catalog_entries_match_current_form_titles(self):
        catalog = json.loads((ROOT / "assets/catalog.json").read_text())
        by_id = {row["id"]: row for row in catalog}
        expected = {
            "07-swot": "社区服务平台 · SWOT 扫描",
            "11-fishbone": "服务请求反复未完成 · 原因假说整理",
            "36-quadrant": "服务改进 · 影响与实施难度",
        }
        for identifier, title in expected.items():
            self.assertEqual(by_id[identifier]["title"], title, identifier)

    def test_v49_demo_svgs_are_well_formed_xml(self):
        files = sorted((ROOT / "demos/strategy-execution").rglob("*.svg"))
        self.assertEqual(len(files), 4)
        for path in files:
            ET.fromstring(path.read_text())


if __name__ == "__main__":
    unittest.main()
