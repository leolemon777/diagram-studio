"""High-frequency user-path storyboard and Lean Canvas regressions."""
import copy
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render
from delivery_contract import content_integrity


class HighFrequencyFormTests(unittest.TestCase):
    def read(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_bilingual_forms_keep_ids_text_and_editable_cells(self):
        for name in ("37-user-path-storyboard-cn.json", "37-user-path-storyboard-en.json", "38-lean-canvas-cn.json", "38-lean-canvas-en.json"):
            with self.subTest(name=name):
                data = self.read(name)
                scene = render.build(data, "light")
                qa = render.audit(scene)
                self.assertEqual(qa["errors"], [])
                self.assertEqual(content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta})["status"], "passed")
                ids = {cell.get("id") for cell in ET.fromstring(render.drawio(scene)).iter("mxCell")}
                if data["type"] == "lean-canvas":
                    self.assertIn("problem", ids)
                    self.assertIn("metric-1", ids)
                    self.assertEqual(scene.meta["lean_canvas"]["distinct_from"], "business-model-canvas")
                else:
                    self.assertIn("step-review", ids)
                    self.assertIn("exception-no-slot", ids)
                    self.assertGreater(scene.meta["user_path_storyboard"]["proposal_count"], 0)

    def test_long_lean_entry_expands_without_overflow(self):
        data = self.read("38-lean-canvas-en.json")
        data["items"][0]["entries"][0]["text"] = "A very long problem statement that must remain legible while the canvas keeps the problem block distinct from the value proposition and solution blocks"
        scene = render.build(data, "light")
        self.assertEqual(render.audit(scene)["errors"], [])
        self.assertTrue(any(node.get("id") == "problem-1" and len(render.label_lines(node)) > 2 for node in scene.nodes))

    def test_long_storyboard_exception_expands_without_overflow(self):
        data = self.read("37-user-path-storyboard-en.json")
        data["exceptions"][0]["condition"] = "A very long exception condition that must remain visible while the path still shows its recovery action and the concrete step endpoints"
        data["exceptions"][0]["recovery"] = "Keep the entered request, explain the constraint, and offer a human transfer or another time"
        scene = render.build(data, "light")
        self.assertEqual(render.audit(scene)["errors"], [])
        self.assertGreater(scene.get("exception-no-slot")["h"], 112)

    def test_storyboard_rejects_untracked_next_step_and_missing_evidence(self):
        storyboard = self.read("37-user-path-storyboard-en.json")
        bad = copy.deepcopy(storyboard)
        bad["steps"][1]["next"] = "missing-step"
        with self.assertRaises(ValueError):
            render.build(bad, "light")
        canvas = self.read("38-lean-canvas-en.json")
        bad = copy.deepcopy(canvas)
        bad["items"][0]["entries"][0]["evidence"] = ""
        with self.assertRaises(ValueError):
            render.build(bad, "light")


if __name__ == "__main__":
    unittest.main()
