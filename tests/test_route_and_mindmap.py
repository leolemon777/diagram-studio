import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_contract
import render


class RouteAndMindmapTests(unittest.TestCase):
    def test_bilingual_mindmaps_keep_tree_content_and_readable_overview(self):
        for name in ("04-mindmap-cn.json", "04-mindmap-en.json"):
            data = json.loads((ROOT / "assets/examples" / name).read_text())
            scene = render.build(data, "light")
            qa = render.audit(scene)
            self.assertEqual(qa["errors"], [], name)
            self.assertEqual(scene.meta["adaptive_layout"]["strategy"], "down", name)
            self.assertEqual(scene.meta["adaptive_layout"]["readability"]["status"], "within-target", name)
            result = delivery_contract.content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges})
            self.assertEqual(result["status"], "passed", name)

    def test_bilingual_timelines_keep_dates_and_actual_day_spacing(self):
        for name in ("29-timeline-cn.json", "29-timeline-en.json"):
            data = json.loads((ROOT / "assets/examples" / name).read_text())
            scene = render.build(data, "light")
            self.assertEqual(render.audit(scene)["errors"], [], name)
            self.assertEqual(scene.meta["day_offsets"], [0, 8, 23, 42], name)
            result = delivery_contract.content_integrity(data, {"nodes": scene.nodes, "edges": scene.edges})
            self.assertEqual(result["status"], "passed", name)


if __name__ == "__main__":
    unittest.main()
