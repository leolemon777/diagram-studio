"""Bilingual high-frequency flowchart regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render
from delivery_contract import content_integrity


class FlowFormTests(unittest.TestCase):
    def load(self, lang):
        return json.loads((ROOT / "assets" / "examples" / f"flow-{lang}.json").read_text(encoding="utf-8"))

    def test_bilingual_steps_decision_and_return_keep_content(self):
        expected_ids = {"request", "check", "complete", "add", "schedule", "notify"}
        expected_edges = {("request", "check"), ("check", "complete"), ("complete", "schedule"),
                          ("complete", "add"), ("add", "check"), ("schedule", "notify")}
        for lang in ("cn", "en"):
            with self.subTest(lang=lang):
                data = self.load(lang)
                self.assertEqual({n["id"] for n in data["nodes"]}, expected_ids)
                self.assertEqual({(e["from"], e["to"]) for e in data["edges"]}, expected_edges)
                scene = render.build(data, "light")
                qa = render.audit(scene)
                self.assertEqual(qa["errors"], [])
                self.assertEqual(qa["warnings"], [])
                self.assertEqual(content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta})["status"], "passed")
                labels = "\n".join(n["label"] for n in scene.nodes)
                edge_labels = "\n".join(e["label"] for e in scene.edges if e.get("label"))
                for text in [n["label"] for n in data["nodes"]]:
                    self.assertIn(text, labels)
                for text in [e["label"] for e in data["edges"] if e.get("label")]:
                    self.assertIn(text, edge_labels)

    def test_branch_and_feedback_conditions_are_explicit(self):
        for lang in ("cn", "en"):
            data = self.load(lang)
            for edge in data["edges"]:
                if edge["from"] == "complete":
                    self.assertIn(edge.get("label"), {"是", "否", "Yes", "No"})
            feedback = next(e for e in data["edges"] if e["from"] == "add")
            self.assertTrue(feedback["dashed"])
            self.assertEqual(feedback["tone"], "amber")

    def test_unknown_endpoint_is_rejected(self):
        invalid = copy.deepcopy(self.load("en"))
        invalid["edges"][0]["to"] = "missing-node"
        with self.assertRaisesRegex(ValueError, "unknown node"):
            render.build(invalid, "light")


if __name__ == "__main__":
    unittest.main()
