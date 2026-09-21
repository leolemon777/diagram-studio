"""High-frequency fishbone and quadrant examples stay bilingual and auditable."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_contract
import render


class AnalysisFormTests(unittest.TestCase):
    def _load(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_fishbone_bilingual_examples_fit_and_retain_hypotheses(self):
        for name in ("11-fishbone.json", "11-fishbone-en.json"):
            data = self._load(name)
            scene = render.build(data, "light")
            self.assertEqual(render.audit(scene)["errors"], [])
            integrity = delivery_contract.content_integrity(
                data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
            )
            self.assertEqual(integrity["status"], "passed", integrity)
            self.assertEqual(len(data["categories"]), 6)
            effect = next(node for node in scene.nodes if node["label"] == data["effect"])
            self.assertTrue(effect.get("word_wrap"))

    def test_quadrant_bilingual_examples_keep_axes_and_items(self):
        for name in ("36-quadrant.json", "36-quadrant-en.json"):
            data = self._load(name)
            scene = render.build(data, "light")
            self.assertEqual(render.audit(scene)["errors"], [])
            integrity = delivery_contract.content_integrity(
                data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
            )
            self.assertEqual(integrity["status"], "passed", integrity)
            self.assertEqual(len(data["items"]), 4)
            self.assertEqual(scene.meta["coordinates"], [(item["x"], item["y"]) for item in data["items"]])


if __name__ == "__main__":
    unittest.main()
