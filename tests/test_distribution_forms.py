"""Bilingual distribution and relationship plot regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render
from delivery_contract import content_integrity


class DistributionFormTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_bilingual_histogram_and_scatter_keep_content_and_geometry(self):
        names = [
            "50-histogram-cn.json", "50-histogram-en.json",
            "46-scatter-cn.json", "46-scatter-en.json",
        ]
        for name in names:
            with self.subTest(name=name):
                data = self.load(name)
                scene = render.build(data, "light")
                self.assertEqual(render.audit(scene)["errors"], [])
                payload = {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
                self.assertEqual(content_integrity(data, payload)["status"], "passed")
                if data["mode"] == "histogram":
                    self.assertEqual(sum(scene.meta["bin_counts"]), len(data["values"]))
                    self.assertEqual(scene.meta["bin_edges"], data["bin_edges"])
                    self.assertIn(data["frequency_note"], "\n".join(node["label"] for node in scene.nodes))
                else:
                    self.assertEqual(len(scene.meta["points"]), len(data["data"]))
                    self.assertEqual(scene.meta["axis_ranges"], {"x": data["x_range"], "y": data["y_range"]})
                    visible = "\n".join(node["label"] for node in scene.nodes)
                    for point in data["data"]:
                        self.assertIn(point["label"], visible)

    def test_histogram_rejects_unequal_bins_and_scatter_rejects_outside_points(self):
        histogram = self.load("50-histogram-en.json")
        invalid = copy.deepcopy(histogram)
        invalid["bin_edges"] = [0, 10, 25, 40, 50, 60]
        with self.assertRaises(ValueError):
            render.build(invalid, "light")
        scatter = self.load("46-scatter-en.json")
        invalid = copy.deepcopy(scatter)
        invalid["data"][0]["x"] = 12
        with self.assertRaises(ValueError):
            render.build(invalid, "light")

    def test_long_english_axis_copy_wraps_without_overflow(self):
        data = self.load("46-scatter-en.json")
        data["x_label"] = "Weekly study time across community learning sessions"
        data["y_label"] = "Tasks completed during the same observation window"
        scene = render.build(data, "light")
        self.assertEqual(render.audit(scene)["errors"], [])


if __name__ == "__main__":
    unittest.main()
