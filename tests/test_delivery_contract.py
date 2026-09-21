"""Public delivery protocol checks for hashes, content identity and versions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_contract
import render


class DeliveryContractTests(unittest.TestCase):
    def test_story_map_content_integrity_keeps_ids_text_and_assignments(self):
        source = ROOT / "assets/storymap-examples/education-storymap.json"
        data = json.loads(source.read_text())
        scene = render.build(data, "light")
        result = delivery_contract.content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges})
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["source_ids"], len(data["stories"]))

    def test_receipt_verifies_and_can_be_snapshotted(self):
        source = ROOT / "assets/examples/02-workflow.json"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "delivery"
            versions = Path(tmp) / "versions"
            result = render.render_file(source, output, version_root=versions)
            self.assertEqual(delivery_contract.verify_receipt(result["receipt"])["status"], "passed")
            receipt = json.loads(Path(result["receipt"]).read_text())
            version = Path(receipt["version_dir"])
            self.assertTrue((version / "version.json").is_file())
            self.assertTrue((version / "02-workflow.svg").is_file())
            self.assertEqual(json.loads((version / "version.json").read_text())["version_id"], receipt["version_id"])

    def test_receipt_detects_changed_artifact(self):
        source = ROOT / "assets/examples/03-organization.json"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "delivery"
            result = render.render_file(source, output)
            svg = output / "03-organization.svg"
            svg.write_text(svg.read_text() + "\nchanged\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                delivery_contract.verify_receipt(result["receipt"])

    def test_v74_trial_pack_has_six_reproducible_mutations(self):
        evidence = json.loads((ROOT / "assets/v74-trials/evidence.json").read_text())
        self.assertEqual(len(evidence["cases"]), 6)
        for case in evidence["cases"]:
            self.assertTrue(case["mutation_visible"])
            self.assertEqual(case["qa_errors"], [])
            for key in ("input", "preview", "editable_source", "delivery_receipt"):
                self.assertTrue((ROOT / case[key]).is_file(), f"missing {key}: {case[key]}")


if __name__ == "__main__":
    unittest.main()
