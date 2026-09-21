"""Bilingual high-frequency funnel and canvas regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render
from delivery_contract import content_integrity


class StrategyFormTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_bilingual_funnel_and_canvas_keep_content_and_geometry(self):
        names = [
            "25-funnel-cn.json", "25-funnel-en.json",
            "33-business-model-canvas-cn.json", "33-business-model-canvas-en.json",
        ]
        for name in names:
            with self.subTest(name=name):
                data = self.load(name)
                scene = render.build(data, "light")
                self.assertEqual(render.audit(scene)["errors"], [])
                payload = {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
                self.assertEqual(content_integrity(data, payload)["status"], "passed")
                visible = "\n".join(node["label"] + "\n" + node.get("detail", "") for node in scene.nodes)
                for item in data["items"]:
                    self.assertIn(item["label"], visible)
                    if item.get("detail"):
                        self.assertIn(item["detail"], visible)

    def test_funnel_requires_positive_nonincreasing_counts(self):
        data = self.load("25-funnel-en.json")
        invalid = copy.deepcopy(data)
        invalid["items"][1]["value"] = 1100
        with self.assertRaises(ValueError):
            render.build(invalid, "light")
        invalid = copy.deepcopy(data)
        invalid["items"][0]["value"] = 0
        with self.assertRaises(ValueError):
            render.build(invalid, "light")

    def test_canvas_wraps_long_english_detail_without_overflow(self):
        data = self.load("33-business-model-canvas-en.json")
        data["items"][3]["detail"] = "A clear next step for complex community care coordination\nFewer repeated calls across service partners"
        scene = render.build(data, "light")
        qa = render.audit(scene)
        self.assertEqual(qa["errors"], [])
        detail_node = next(node for node in scene.nodes if node["label"] == data["items"][3]["detail"])
        self.assertGreater(len(render.label_lines(detail_node)), 2)


if __name__ == "__main__":
    unittest.main()
