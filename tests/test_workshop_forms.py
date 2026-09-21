"""Semantic and layout checks for the bilingual workshop examples."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_contract
import organization_relations
import render


class WorkshopFormTests(unittest.TestCase):
    def _load(self, directory, name):
        return json.loads((ROOT / "assets" / directory / name).read_text(encoding="utf-8"))

    def test_affinity_bilingual_examples_retain_observations(self):
        for name in ("education-affinity.json", "education-affinity-en.json"):
            data = self._load("workshop-examples", name)
            result = organization_relations.analyze(data)
            self.assertEqual(result["observation_retention"], "passed")
            self.assertEqual(result["single_assignment"], "passed")
            with tempfile.TemporaryDirectory() as directory:
                organization_relations.render(data, directory, Path(name).stem)
                qa = json.loads((Path(directory) / f"{Path(name).stem}.qa.json").read_text())
                self.assertEqual(qa["errors"], [])
                svg = (Path(directory) / f"{Path(name).stem}.svg").read_text()
                self.assertIn(data["title"], svg)

    def test_affinity_rejects_duplicate_assignment(self):
        data = self._load("workshop-examples", "education-affinity.json")
        bad = copy.deepcopy(data)
        bad["themes"][1]["observation_ids"].append("O1")
        with self.assertRaisesRegex(ValueError, "only one theme"):
            organization_relations.analyze(bad)

    def test_retrospective_bilingual_examples_keep_text_and_word_boundaries(self):
        for name in ("marketing-retrospective.json", "marketing-retrospective-en.json"):
            data = self._load("workshop-examples", name)
            scene = render.build(data, "light")
            self.assertEqual(render.audit(scene)["errors"], [])
            integrity = delivery_contract.content_integrity(
                data, {"nodes": scene.nodes, "edges": scene.edges, "meta": scene.meta}
            )
            self.assertEqual(integrity["status"], "passed", integrity)
            action = next(node for node in scene.nodes if node.get("label", "").startswith(("A1:", "A1：")))
            lines = [line[0] for line in render.label_lines(action)]
            if data.get("language", "zh") == "en":
                self.assertEqual(lines[-1], "first")
                self.assertNotIn("fr", lines)
            else:
                self.assertTrue(lines)


if __name__ == "__main__":
    unittest.main()
