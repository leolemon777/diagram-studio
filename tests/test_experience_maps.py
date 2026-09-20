"""Semantic coverage for journey maps and service blueprints."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_contract
import render
from experience_maps import _blueprint_validate, _journey_validate


class ExperienceMapTests(unittest.TestCase):
    def _brief(self, name):
        return json.loads((ROOT / "assets" / "experience-models" / name).read_text(encoding="utf-8"))

    def test_journey_bilingual_examples_keep_traceable_content(self):
        for name in ("education-journey.json", "education-journey-en.json"):
            data = self._brief(name)
            scene = render.build(data, "light")
            self.assertEqual(scene.meta["experience_map"], "journey")
            self.assertEqual(render.audit(scene)["errors"], [])
            result = delivery_contract.content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta})
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual(result["source_ids"], 16)

    def test_blueprint_bilingual_examples_keep_boundaries_and_handoffs(self):
        for name in ("retail-service-blueprint.json", "retail-service-blueprint-en.json"):
            data = self._brief(name)
            scene = render.build(data, "light")
            self.assertEqual(scene.meta["experience_map"], "service-blueprint")
            self.assertEqual(render.audit(scene)["errors"], [])
            self.assertEqual(len(scene.edges), 5)  # two boundaries + three declared handoffs
            result = delivery_contract.content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta})
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual(result["source_relations"], 3)
            self.assertEqual(result["source_ids"], 4 + 5 + 15)

    def test_journey_rejects_unknown_trace_reference(self):
        data = self._brief("education-journey.json")
        bad = copy.deepcopy(data)
        bad["stages"][0]["opportunities"][0]["evidence"] = ["missing-evidence"]
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            _journey_validate(bad)

    def test_blueprint_rejects_handoff_to_empty_cell(self):
        data = self._brief("retail-service-blueprint.json")
        bad = copy.deepcopy(data)
        bad["handoffs"][0]["to"] = {"lane": "support", "stage": "order"}
        with self.assertRaisesRegex(ValueError, "has no item"):
            _blueprint_validate(bad)


if __name__ == "__main__":
    unittest.main()
