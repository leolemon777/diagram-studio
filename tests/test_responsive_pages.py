"""Guard the demo-shell responsive contract and recorded viewport evidence."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POPULAR_SHELLS = (
    "demos/flow/index.html",
    "demos/architecture/index.html",
    "demos/swimlane/index.html",
    "demos/gantt/index.html",
    "demos/network/index.html",
    "demos/data-story/index.html",
)


class ResponsiveDemoTests(unittest.TestCase):
    def test_viewport_evidence_covers_all_declared_sizes_and_pages(self):
        evidence = json.loads((ROOT / "assets/v72-viewport-evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["runs"], 92)
        self.assertEqual(len(evidence["viewports"]), 4)
        self.assertEqual(len(evidence["pages_checked"]), 23)
        self.assertEqual(evidence["checks"]["document_scroll_width_equals_viewport"]["failed"], 0)
        self.assertEqual(evidence["checks"]["uncontained_visible_horizontal_overflow"]["failed"], 0)

    def test_experience_map_wide_images_stay_inside_a_narrow_shell(self):
        html = (ROOT / "demos/experience-maps/index.html").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns:minmax(0,1fr)", html)
        self.assertIn(".card{background:#fefdf9;border:1px solid #d8d3c8;min-width:0}", html)
        self.assertIn(".frame{overflow:auto", html)
        self.assertIn("min-width:0;max-width:100%", html)

    def test_v74_popular_embedded_viewport_evidence_has_no_uncontained_overflow(self):
        evidence = json.loads((ROOT / "assets/v74-popular-viewport-evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(set(evidence["viewports"] and [tuple(v.values()) for v in evidence["viewports"]]), {(390, 844), (768, 1024)})
        self.assertEqual(len(evidence["pages"]), 9)
        self.assertEqual(evidence["checks"]["page_level_document_scroll_width"]["failed"], 0)
        self.assertEqual(evidence["checks"]["uncontained_visible_horizontal_overflow"]["failed"], 0)
        self.assertTrue(all(item["runs"] == 2 for item in evidence["pages"].values()))
        self.assertTrue(all(item["default_mode"] in {"readable-natural", "fit-overview"} for item in evidence["pages"].values()))
        for item in evidence["pages"].values():
            self.assertEqual(len(item["viewport_runs"]), 2)
            for run in item["viewport_runs"]:
                self.assertTrue(run["document_scroll_width_equals_viewport"])
                self.assertEqual(run["uncontained_visible_horizontal_overflow"], 0)
                self.assertGreaterEqual(run["minimum_displayed_font_px"], 12)

    def test_popular_shells_default_to_readable_natural_mode_on_narrow_viewports(self):
        for relative in POPULAR_SHELLS:
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("let reading=window.matchMedia('(max-width:1000px)').matches", html, relative)
            self.assertIn("button.textContent=reading?", html, relative)
            self.assertIn("obj.style.width=width+'px'", html, relative)


if __name__ == "__main__":
    unittest.main()
