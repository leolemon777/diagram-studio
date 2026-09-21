"""Bilingual before/after dumbbell regressions."""
import copy
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from data_art import DataPlate, validate


class DumbbellFormTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "assets" / "data-art-examples" / name).read_text(encoding="utf-8"))

    def test_bilingual_dumbbells_keep_pairs_and_localize_the_plate(self):
        for name in ("dumbbell-cn.json", "dumbbell-en.json"):
            with self.subTest(name=name):
                data = self.load(name)
                plate = DataPlate(data, "detail", "warm").build()
                self.assertEqual(plate.metrics["changes"]["support"]["delta"], -11)
                self.assertEqual(len(plate.tags), len(data["rows"]))
                qa = plate.audit()
                self.assertEqual(qa["errors"], [])
                xml = ET.fromstring(plate.svg())
                visible = " ".join(node.text or "" for node in xml.iter() if node.tag.endswith("text"))
                self.assertIn(data["title"], visible)
                if data["language"] == "en":
                    self.assertIn("Reading guide", plate.svg())
                    self.assertNotIn("读图约定", plate.svg())
                    self.assertNotIn("暖灰纸感", plate.svg())
                else:
                    self.assertIn("读图约定", plate.svg())

    def test_dumbbell_rejects_negative_values_and_unknown_language(self):
        data = self.load("dumbbell-en.json")
        invalid = copy.deepcopy(data)
        invalid["rows"][0]["after"] = -1
        with self.assertRaises(ValueError):
            validate(invalid)
        invalid = copy.deepcopy(data)
        invalid["language"] = "fr"
        with self.assertRaises(ValueError):
            validate(invalid)

    def test_long_labels_wrap_without_leaving_canvas(self):
        data = self.load("dumbbell-en.json")
        data["rows"][0]["label"] = "Customer support / high priority cases and escalation review"
        plate = DataPlate(data, "detail", "warm").build()
        self.assertEqual(plate.audit()["errors"], [])
        labels = [item for item in plate.items if item["kind"] == "text" and "Customer support" in item["text"]]
        self.assertEqual(len(labels), 1)
        self.assertGreater(len(labels[0]["lines"]), 1)


if __name__ == "__main__":
    unittest.main()
