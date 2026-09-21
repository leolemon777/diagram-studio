"""High-frequency bilingual chart regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render
from delivery_contract import content_integrity


class ChartFormTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_bilingual_data_story_examples_keep_content_and_geometry(self):
        names = [
            "08-bar-chart-cn.json", "08-bar-chart-en.json",
            "09-line-chart-cn.json", "09-line-chart-en.json",
            "10-donut-chart-cn.json", "10-donut-chart-en.json",
            "48-heatmap-cn.json", "48-heatmap-en.json",
        ]
        for name in names:
            with self.subTest(name=name):
                data = self.load(name)
                scene = render.build(data, "light")
                qa = render.audit(scene)
                self.assertEqual(qa["errors"], [])
                self.assertEqual(qa["warnings"], [])
                payload = {
                    "nodes": scene.nodes,
                    "edges": scene.edges,
                    "meta": scene.meta,
                }
                self.assertEqual(content_integrity(data, payload)["status"], "passed")
                visible = "\n".join(node["label"] for node in scene.nodes)
                if data["type"] == "chart":
                    labels = [row["label"] for row in data["data"]]
                else:
                    labels = data["row_labels"] + data["column_labels"]
                for label in labels:
                    self.assertIn(label, visible)

    def test_chart_wraps_long_latin_labels_at_word_boundaries(self):
        data = self.load("08-bar-chart-en.json")
        data["data"][0]["label"] = "Community learning sessions and partner orientation"
        scene = render.build(data, "light")
        self.assertEqual(render.audit(scene)["errors"], [])
        label = next(node for node in scene.nodes if node["kind"] == "text" and node["label"] == data["data"][0]["label"])
        lines = render.label_lines(label)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(not line[0].isspace() and not line[-1].isspace() for line, *_ in lines))
        self.assertTrue(all("Community learning" not in line or line == "Community learning" for line, *_ in lines))

    def test_donut_keeps_total_label_and_rejects_invalid_values(self):
        data = self.load("10-donut-chart-en.json")
        scene = render.build(data, "light")
        visible = "\n".join(node["label"] for node in scene.nodes)
        self.assertIn(data["total_label"] + " " + data["unit"], visible)
        invalid = copy.deepcopy(data)
        invalid["data"][0]["value"] = -1
        with self.assertRaises(ValueError):
            render.build(invalid, "light")

    def test_heatmap_keeps_one_shared_scale_and_rejects_shape_mismatch(self):
        data = self.load("48-heatmap-en.json")
        scene = render.build(data, "light")
        self.assertEqual(render.audit(scene)["errors"], [])
        visible = "\n".join(node["label"] for node in scene.nodes)
        for label in data["row_labels"] + data["column_labels"]:
            self.assertIn(label, visible)
        invalid = copy.deepcopy(data)
        invalid["values"][-1] = invalid["values"][-1][:-1]
        with self.assertRaises(ValueError):
            render.build(invalid, "light")


if __name__ == "__main__":
    unittest.main()
