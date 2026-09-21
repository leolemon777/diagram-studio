"""Cross-industry content checks for common software-system diagram examples."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render


EXAMPLES = {
    "12-data-model.json": "服务预约 · 逻辑数据关系",
    "13-c4-context.json": "社区服务平台 · 系统上下文",
    "15-network-topology.json": "服务生态 · 中心连接",
    "16-data-flow.json": "反馈数据流 · 输入、处理与存储",
    "17-state-machine.json": "状态机 · 服务申请生命周期",
    "19-use-case.json": "服务平台 · 用例关系",
}


class SystemLibraryExampleTests(unittest.TestCase):
    def read(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_common_system_examples_use_cross_industry_titles_and_terms(self):
        banned = ("设备", "运维", "工单", "维护", "物料", "停机")
        for name, title in EXAMPLES.items():
            with self.subTest(name=name):
                data = self.read(name)
                serialized = json.dumps(data, ensure_ascii=False)
                self.assertEqual(data["title"], title)
                self.assertFalse(any(term in serialized for term in banned))

    def test_common_system_examples_render_cleanly(self):
        for name in EXAMPLES:
            with self.subTest(name=name):
                scene = render.build(self.read(name), "light")
                qa = render.audit(scene)
                self.assertEqual(qa["errors"], [])
                self.assertEqual(qa["warnings"], [])

    def test_data_model_and_context_keep_explicit_relationships(self):
        model = self.read("12-data-model.json")
        self.assertEqual({node["id"] for node in model["nodes"]}, {"service", "booking", "team"})
        self.assertEqual({(edge["from"], edge["to"]) for edge in model["edges"]}, {("service", "booking"), ("team", "booking")})
        context = self.read("13-c4-context.json")
        self.assertEqual({(edge["from"], edge["to"]) for edge in context["edges"]}, {("person", "system"), ("system", "sso"), ("system", "erp")})

    def test_state_machine_and_use_case_keep_semantic_boundaries(self):
        state = self.read("17-state-machine.json")
        self.assertEqual({(edge["from"], edge["to"]) for edge in state["edges"]}, {("new", "work"), ("work", "verify"), ("verify", "done"), ("verify", "work"), ("new", "cancel")})
        use_case = self.read("19-use-case.json")
        self.assertEqual(use_case["groups"][0]["label"], "社区服务平台")
        self.assertEqual(len(use_case["nodes"]), 5)


if __name__ == "__main__":
    unittest.main()
