"""The chooser registry is a validated, single source for delivery claims."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import capability_registry


class CapabilityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = capability_registry.load()

    def test_registry_references_real_backends_examples_and_evidence(self):
        capabilities = capability_registry.capabilities(self.data)
        self.assertGreaterEqual(len(capabilities), 19)
        self.assertEqual(len({item["id"] for item in capabilities}), len(capabilities))
        for item in capabilities:
            self.assertEqual(set(item["languages"]), {"zh", "en"})
            self.assertTrue(item["formats"])
            self.assertTrue(item["examples"])
            self.assertIn(item["evidence"]["level"], capability_registry.EVIDENCE_LEVELS)

    def test_aliases_resolve_without_changing_stable_ids(self):
        self.assertEqual(capability_registry.find(self.data, "workflow")["id"], "flow")
        self.assertEqual(capability_registry.find(self.data, "story-map")["id"], "storymap")
        self.assertNotEqual(capability_registry.find(self.data, "workflow")["id"], "workflow")

    def test_markdown_is_derived_from_registry(self):
        rendered = capability_registry.markdown(self.data)
        self.assertIn("assets/capability-registry.json", rendered)
        self.assertIn("`storymap`", rendered)
        self.assertIn("scripts/render.py#storymap", rendered)

    def test_invalid_backend_reference_is_rejected(self):
        broken = json.loads(json.dumps(self.data))
        broken["groups"][0]["types"][0]["backend"]["module"] = "scripts/does-not-exist.py"
        with self.assertRaisesRegex(ValueError, "backend.module does not exist"):
            capability_registry.validate(broken, ROOT)


if __name__ == "__main__":
    unittest.main()
