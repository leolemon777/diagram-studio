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
        examples = [self._load(name) for name in ("11-fishbone.json", "11-fishbone-en.json")]
        self.assertEqual(len({len(data["categories"]) for data in examples}), 1)
        self.assertEqual(len({len(data["categories"][0]["causes"]) for data in examples}), 1)
        for name, data in zip(("11-fishbone.json", "11-fishbone-en.json"), examples):
            scene = render.build(data, "light")
            self.assertEqual(render.audit(scene)["errors"], [])
            integrity = delivery_contract.content_integrity(
                data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
            )
            self.assertEqual(integrity["status"], "passed", integrity)
            self.assertEqual(len(data["categories"]), 6)
            effect = next(node for node in scene.nodes if node["label"] == data["effect"])
            self.assertTrue(effect.get("word_wrap"))
        self.assertEqual(examples[0]["effect_detail"].count("确认"), 1)
        self.assertIn("frequency", examples[1]["effect_detail"])

    def test_fishbone_examples_share_a_cross_industry_service_context(self):
        zh, en = [self._load(name) for name in ("11-fishbone.json", "11-fishbone-en.json")]
        self.assertIn("服务", zh["effect"])
        self.assertIn("Service", en["effect"])
        self.assertEqual(
            [item["label"] for item in zh["categories"]],
            ["人员", "流程", "工具", "内容", "触达", "测量"],
        )
        self.assertEqual(
            [item["label"] for item in en["categories"]],
            ["People", "Process", "Tools", "Content", "Access", "Measurement"],
        )

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
