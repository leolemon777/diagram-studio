"""Keep common business, UX and data examples cross-industry and structurally valid."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render


EXAMPLES = (
    "22-concept-map.json",
    "23-hub-spoke.json",
    "32-decision-tree.json",
    "33-business-model-canvas.json",
    "34-pest.json",
    "37-raci.json",
    "38-customer-journey.json",
    "39-service-blueprint.json",
    "41-comparison.json",
    "45-stacked-bar.json",
    "48-heatmap.json",
    "53-pie.json",
)


class BusinessLibraryExampleTests(unittest.TestCase):
    def read(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_common_examples_drop_maintenance_fixture_terms(self):
        banned = ("设备", "运维", "工单", "维护", "停机", "物料")
        for name in EXAMPLES:
            with self.subTest(name=name):
                serialized = json.dumps(self.read(name), ensure_ascii=False)
                self.assertFalse(any(term in serialized for term in banned))

    def test_common_examples_render_without_quality_errors(self):
        for name in EXAMPLES:
            with self.subTest(name=name):
                qa = render.audit(render.build(self.read(name), "light"))
                self.assertEqual(qa["errors"], [])
                self.assertEqual(qa["warnings"], [])

    def test_graph_and_matrix_semantics_remain_explicit(self):
        concept = self.read("22-concept-map.json")
        self.assertEqual(len(concept["nodes"]), 6)
        self.assertEqual(len(concept["edges"]), 7)
        decision = self.read("32-decision-tree.json")
        self.assertEqual({(edge["from"], edge["to"]) for edge in decision["edges"]}, {("risk", "fix"), ("risk", "plan"), ("fix", "stop"), ("fix", "support")})
        pest = self.read("34-pest.json")
        self.assertEqual([cell["label"][0] for cell in pest["cells"]], ["P", "E", "S", "T"])

    def test_tables_and_charts_keep_shared_dimensions_and_values(self):
        journey = self.read("38-customer-journey.json")
        self.assertEqual(len(journey["columns"]), 6)
        self.assertTrue(all(len(row) == len(journey["columns"]) for row in journey["rows"]))
        blueprint = self.read("39-service-blueprint.json")
        self.assertTrue(all(len(row) == len(blueprint["columns"]) for row in blueprint["rows"]))
        heatmap = self.read("48-heatmap.json")
        self.assertEqual(len(heatmap["row_labels"]), len(heatmap["values"]))
        self.assertTrue(all(len(row) == len(heatmap["column_labels"]) for row in heatmap["values"]))
        pie = self.read("53-pie.json")
        self.assertEqual(sum(item["value"] for item in pie["data"]), 100)


if __name__ == "__main__":
    unittest.main()
