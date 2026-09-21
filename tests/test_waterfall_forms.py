"""Bilingual change waterfall regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from data_art import DataPlate, validate


class WaterfallFormTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "assets" / "data-art-examples" / name).read_text(encoding="utf-8"))

    def test_bilingual_waterfalls_reconcile_and_localize(self):
        for name in ("waterfall-cn.json", "waterfall-en.json"):
            with self.subTest(name=name):
                data = self.load(name)
                plate = DataPlate(data, "detail", "warm").build()
                self.assertEqual(plate.metrics["end"], 12800)
                self.assertEqual(plate.metrics["net"], 2800)
                self.assertEqual(plate.audit()["errors"], [])
                svg = plate.svg()
                self.assertIn(data["title"], svg)
                if data["language"] == "en":
                    self.assertIn("Reading guide", svg)
                    self.assertIn("Opening", svg)
                    self.assertNotIn("读图约定", svg)
                    self.assertNotIn("暖灰纸感", svg)
                else:
                    self.assertIn("读图约定", svg)
                    self.assertIn("基期", svg)

    def test_waterfall_rejects_invalid_start_or_quantum(self):
        data = self.load("waterfall-en.json")
        invalid = copy.deepcopy(data)
        invalid["start"] = -1
        with self.assertRaises(ValueError):
            validate(invalid)
        invalid = copy.deepcopy(data)
        invalid["quantum"] = 0
        with self.assertRaises(ValueError):
            validate(invalid)

    def test_long_change_label_wraps_without_canvas_errors(self):
        data = self.load("waterfall-en.json")
        data["rows"][1]["label"] = "Campaign lift after regional partnership launch"
        plate = DataPlate(data, "detail", "warm").build()
        self.assertEqual(plate.audit()["errors"], [])
        labels = [item for item in plate.items if item["kind"] == "text" and "Campaign lift" in item["text"]]
        self.assertEqual(len(labels), 1)
        self.assertGreater(len(labels[0]["lines"]), 1)


if __name__ == "__main__":
    unittest.main()
