"""Bilingual ownership swimlane regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render
from delivery_contract import content_integrity


class SwimlaneFormTests(unittest.TestCase):
    def load(self, lang):
        return json.loads((ROOT / "assets" / "examples" / f"swimlane-{lang}.json").read_text(encoding="utf-8"))

    def test_bilingual_lanes_and_handoffs_keep_roles_and_content(self):
        expected_ids = {"submit", "clarify", "triage", "check", "deliver", "review", "close"}
        expected_edges = {("submit", "triage"), ("triage", "check"), ("check", "deliver"),
                          ("check", "clarify"), ("clarify", "triage"), ("deliver", "review"),
                          ("review", "close"), ("review", "deliver")}
        for lang in ("cn", "en"):
            with self.subTest(lang=lang):
                data = self.load(lang)
                self.assertEqual({node["id"] for node in data["nodes"]}, expected_ids)
                self.assertEqual({(edge["from"], edge["to"]) for edge in data["edges"]}, expected_edges)
                self.assertEqual(len(data["groups"]), 3)
                self.assertEqual(render.audit(render.build(data, "light"))["errors"], [])
                self.assertEqual(render.audit(render.build(data, "light"))["warnings"], [])
                scene = render.build(data, "light")
                payload = {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
                self.assertEqual(content_integrity(data, payload)["status"], "passed")
                for node in data["nodes"]:
                    owners = [group for group in data["groups"]
                              if group["x"] <= node["x"] and node["x"] + node["w"] <= group["x"] + group["w"]
                              and group["y"] <= node["y"] and node["y"] + node["h"] <= group["y"] + group["h"]]
                    self.assertEqual(len(owners), 1, node["id"])
                visible = "\n".join(node["label"] for node in scene.nodes)
                for text in [node["label"] for node in data["nodes"]] + [group["label"] for group in data["groups"]]:
                    self.assertIn(text, visible)

    def test_return_handoff_is_explicit_and_dashed(self):
        for lang in ("cn", "en"):
            data = self.load(lang)
            revision = next(edge for edge in data["edges"] if edge["from"] == "review" and edge["to"] == "deliver")
            self.assertTrue(revision["dashed"])
            self.assertEqual(revision["tone"], "amber")
            self.assertTrue(revision["label"])
            self.assertTrue(next(edge for edge in data["edges"] if edge["from"] == "check" and edge["to"] == "clarify")["label"])

    def test_unknown_handoff_endpoint_is_rejected(self):
        invalid = copy.deepcopy(self.load("en"))
        invalid["edges"][0]["to"] = "missing-node"
        with self.assertRaisesRegex(ValueError, "unknown node"):
            render.build(invalid, "light")


if __name__ == "__main__":
    unittest.main()
