"""Public delivery protocol checks for hashes, content identity and versions."""
import html
import json
import re
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
            input_path = ROOT / case["input"]
            preview_path = ROOT / case["preview"]
            receipt_path = ROOT / case["delivery_receipt"]
            self.assertTrue(input_path.is_file(), f"missing input: {case['input']}")
            self.assertTrue(preview_path.is_file(), f"missing preview: {case['preview']}")
            self.assertTrue(receipt_path.is_file(), f"missing delivery_receipt: {case['delivery_receipt']}")
            for key in ("input", "preview", "editable_source", "delivery_receipt"):
                self.assertTrue((ROOT / case[key]).is_file(), f"missing {key}: {case[key]}")

            receipt_status = delivery_contract.verify_receipt(receipt_path)
            self.assertEqual(receipt_status["status"], "passed")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["input_sha256"], delivery_contract.sha256_bytes(input_path.read_bytes()))
            manifest = receipt["files"]
            preview_name = preview_path.name
            output_dir = preview_path.parent
            qa_path = output_dir / f"{preview_path.stem}.qa.json"
            scene_path = output_dir / f"{preview_path.stem}.scene.json"
            brief_path = output_dir / f"{preview_path.stem}.brief.json"
            for required in (preview_name, Path(case["editable_source"]).name, qa_path.name, scene_path.name, brief_path.name):
                self.assertIn(required, manifest, f"receipt does not cover {required}")
            self.assertTrue(qa_path.is_file())
            self.assertTrue(scene_path.is_file())
            self.assertTrue(brief_path.is_file())
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            self.assertEqual(qa["errors"], [], case["id"])
            self.assertEqual(qa["content_integrity"]["status"], "passed", case["id"])
            self.assertIsInstance(scene.get("nodes"), list)
            self.assertIsInstance(scene.get("edges"), list)
            self.assertEqual(case.get("render_exit_code"), 0)

            source_text = input_path.read_text(encoding="utf-8")
            preview_text = _svg_visible_text(preview_path.read_text(encoding="utf-8"))
            marker = case["mutation"]
            source_has_marker = _source_contains_marker(source_text, marker)
            preview_has_marker = marker in preview_text
            self.assertTrue(source_has_marker, f"mutation is not traceable to input: {case['id']} / {marker}")
            self.assertTrue(preview_has_marker, f"mutation is not visible in preview text: {case['id']} / {marker}")
            self.assertTrue(case["mutation_visible"])
            self.assertEqual(case["mutation_visible"], preview_has_marker)
            self.assertTrue(case.get("mutation_source_traceable"))
            self.assertTrue(case.get("mutation_in_preview"))
            self.assertTrue(case.get("receipt_verified"))
            self.assertTrue(case.get("scene_verified"))
            self.assertTrue(case.get("qa_verified"))
            self.assertEqual(case["qa_errors"], qa["errors"])

    def test_v74_roles_and_industry_trials_are_semantically_aligned(self):
        for relative in (
            "assets/examples/swimlane-cn.json",
            "assets/examples/swimlane-en.json",
            "assets/v74-trials/hr-handoff/hr-handoff.json",
        ):
            data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            groups = {group["id"]: group for group in data["groups"]}
            nodes = {node["id"]: node for node in data["nodes"]}

            def in_group(node_id, group_id):
                node = nodes[node_id]
                group = groups[group_id]
                center_y = node["y"] + node["h"] / 2
                return group["y"] <= center_y <= group["y"] + group["h"]

            self.assertTrue(in_group("deliver", "lane3"), relative)
            self.assertTrue(in_group("review", "lane2"), relative)
            self.assertTrue(in_group("close", "lane2"), relative)
            self.assertTrue("coord" in nodes["review"].get("detail", "").lower() or "协调" in nodes["review"].get("detail", ""), relative)

        retail = json.loads((ROOT / "assets/v74-trials/retail-fulfillment/retail-fulfillment.json").read_text(encoding="utf-8"))
        retail_nodes = {node["id"]: node for node in retail["nodes"]}
        self.assertIn("门店", retail["title"])
        self.assertEqual(retail_nodes["complete"]["label"], "门店确认？")
        self.assertEqual(retail_nodes["add"]["label"], "门店确认失败")
        self.assertTrue(any("门店确认失败" in edge.get("label", "") for edge in retail["edges"]))

        marketing = json.loads((ROOT / "assets/v74-trials/marketing-trend/marketing-trend.json").read_text(encoding="utf-8"))
        self.assertIn("Campaign", marketing["title"])
        self.assertIn("qualified-lead", marketing["title"])
        self.assertEqual(marketing["unit"], " leads")


def _svg_visible_text(svg_text):
    """Return rendered SVG text nodes as one stream so wrapped labels remain testable."""
    text_nodes = re.findall(r"<text\b[^>]*>(.*?)</text>", svg_text, flags=re.DOTALL)
    return html.unescape("".join(re.sub(r"<[^>]+>", "", node) for node in text_nodes))


def _source_contains_marker(source_text, marker):
    if marker in source_text:
        return True
    if re.fullmatch(r"\d{2}/\d{2}", marker):
        month, day = marker.split("/")
        return f"-{month}-{day}" in source_text or f"/{month}/{day}" in source_text
    return "".join(marker.split()) in "".join(source_text.split())


if __name__ == "__main__":
    unittest.main()
