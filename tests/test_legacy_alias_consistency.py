"""Keep numbered high-frequency examples aligned with reviewed cross-industry inputs."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render


PAIRED_ALIASES = {
    "01-system-architecture.json": "architecture-cn.json",
    "02-workflow.json": "swimlane-cn.json",
    "04-mindmap.json": "04-mindmap-cn.json",
    "05-sequence.json": "sequence-cn.json",
    "06-gantt.json": "gantt-cn.json",
    "08-bar-chart.json": "08-bar-chart-cn.json",
    "09-line-chart.json": "09-line-chart-cn.json",
    "10-donut-chart.json": "10-donut-chart-cn.json",
}


class LegacyAliasConsistencyTests(unittest.TestCase):
    def read(self, name):
        return json.loads((ROOT / "assets" / "examples" / name).read_text(encoding="utf-8"))

    def test_high_frequency_aliases_match_reviewed_chinese_inputs(self):
        for alias, canonical in PAIRED_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(self.read(alias), self.read(canonical))

    def test_organization_alias_uses_cross_industry_service_roles(self):
        data = self.read("03-organization.json")
        labels = []
        def collect(node):
            labels.append(node["label"])
            for child in node.get("children", []):
                collect(child)
        collect(data["root"])
        self.assertEqual(data["title"], "服务运营团队 · 职责结构")
        self.assertIn("服务运营负责人", labels)
        self.assertIn("需求受理", labels)
        self.assertNotIn("运维", "".join(labels))

    def test_high_frequency_aliases_drop_specialist_fixture_terms(self):
        banned = ("设备", "物料", "工单", "运维", "停机", "维护")
        for alias in list(PAIRED_ALIASES) + ["03-organization.json"]:
            with self.subTest(alias=alias):
                serialized = json.dumps(self.read(alias), ensure_ascii=False)
                self.assertFalse(any(term in serialized for term in banned))

    def test_alias_inputs_render_without_quality_errors(self):
        names = list(PAIRED_ALIASES) + ["03-organization.json"]
        for name in names:
            with self.subTest(name=name):
                scene = render.build(self.read(name), "light")
                qa = render.audit(scene)
                self.assertEqual(qa["errors"], [])
                self.assertEqual(qa["warnings"], [])

    def test_catalog_titles_match_updated_alias_inputs(self):
        catalog = {row["id"]: row for row in json.loads((ROOT / "assets/catalog.json").read_text(encoding="utf-8"))}
        expected = {
            "01-system-architecture": "社区服务平台 · 分层架构",
            "02-workflow": "服务请求 · 责任交接",
            "03-organization": "服务运营团队 · 职责结构",
            "04-mindmap": "社区学习改进 · 从问题到证据",
            "05-sequence": "服务预约 · 交互时序",
            "06-gantt": "社区服务活动 · 上线计划",
            "08-bar-chart": "社区活动 · 触达渠道比较",
            "09-line-chart": "客户支持 · 首次响应趋势",
            "10-donut-chart": "课程服务 · 参与方式构成",
        }
        for identifier, title in expected.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(catalog[identifier]["title"], title)


if __name__ == "__main__":
    unittest.main()
