# 五类常用图精修 / Five refined forms

适用普通流程、分层架构、执行甘特、单系列对比和趋势。优先用内容确定结构，再用统一的文字、留白与细线规则打磨。风格可以变，数值、单位、关系与方向不变。无需把专业记法改成普通节点图。

For ordinary workflows, layered architecture, delivery Gantt, single-series comparisons and trends, set `"layout":{"profile":"refined"}` in the input to `scripts/render.py`. This is a bounded layout profile, not a separate natural-language model or approval of every diagram type. Chinese and English briefs share the same schema; use `language: "en"` for generated English UI/annotations. User text is preserved, not automatically translated.

## 选择与输入

| 输入 / Input | 精修内容 / Behavior | 范围 / Limit |
|---|---|---|
| `type: graph`, no fixed positions | 主线突出、分支与回流分开；Measured nodes, branch/return routing | 可选 `layout.primary_path` 为已有有向路径的 ID 列表；不会添加关系。Use adaptive mode, not fixed/legacy. |
| `type: architecture`, `layers` | 职责侧栏、模块列对齐、内容扩展分区；Aligned responsibility bands | 只画明确的 `edges`；同层或上下层不自动代表调用。Only explicit calls. |
| `type: gantt`, `gantt_variant: delivery` | 任务、负责人、日期按内容增高；依赖线避开任务条 | 自然日含结束日、完成后开始依赖、进度与里程碑；不算资源或关键路径。Executive/print use the existing backend. |
| `type: chart`, `mode: bar` | 正负值共用零点；条形或 `comparison_style: dot` | `data: [{label,value}]`，有限数字、相同单位；保留输入顺序。Single series, exact values, no inferred ranking. |
| `type: chart`, `mode: line` | 真实日期间隔、缺测断线、完整数值清单 | `data: [{date,value}]`，ISO 日期严格递增；`null` 缺测；无日期则按 `label` 等距。No interpolation or smoothing. |

保留 `unit`、`subtitle`、`footer` 和 `assumptions`。不要用模拟数据替换用户事实。示例数据在 [refinement-cases.json](../assets/refinement-cases.json)，包含客服、电商系统、教育、营销和零售。

Preserve every source value. A missing trend observation is `null`, not zero; date gaps affect horizontal distance. Comparison bars and dots use the same linear scale. Gantt progress remains attached to its task in draw.io. Long text expands rows and canvas rather than being silently truncated. For very large inputs, split into linked views; this profile does not guarantee that all content fits a small screen.

## 复现与验收 / Reproduce and inspect

```bash
python3 scripts/refinement_suite.py --out /tmp/diagram-refinement
python3 -m http.server 8772 --bind 127.0.0.1 --directory /tmp/diagram-refinement
```

Open `http://127.0.0.1:8772/`. The bilingual gallery compares five originals, five content mutations, and one alternate comparison expression (11 outputs). Each has SVG, draw.io, brief JSON, reading HTML, QA and hashed delivery records. Graph/architecture also have adaptive detail pages; refined data charts use a single reading page. Pillow is recommended for measured font widths; actual browser checks remain necessary.

验收顺序：

1. 对照输入确认对象、分支、依赖、日期、缺失值与数值。
2. 打开 SVG 看构图和文字细节，再查看变更后的图；不能只看脚本通过。
3. 检查浏览器文字边界、菱形文字、跨对象文字相交及当前实际字号。过小则切换清晰阅读；大图允许画布内部滚动。
4. 核对交付哈希，针对需要的编辑器执行修改、保存、重开；XML 结构通过不能冒充编辑器实测。
5. 记录具体文件、窗口、检查范围与尚未验证的部分；审美签收由用户完成。

Check content first, then actual browser geometry and visual hierarchy, then a meaningful content change, and finally editing in the target application. The negative browser fixture in the v40 evidence deliberately overlaps two labels to confirm that cross-group checking detects collisions. Successful geometry is not automatic aesthetic approval.

已测范围见 [verification-status.md](verification-status.md)、[v40 evidence](../assets/v40-browser-evidence.json) 与 [v43 story-map evidence](../assets/v43-storymap-evidence.json)。原生编辑实测已覆盖流程图节点文字修改，以及故事地图在 draw.io 中的文字修改、浏览器保存、最近文件重开和结构保留；仍未验证全部图型、拖动路由和全部编辑器。移动端 390px 尺寸尝试未生效，不能把桌面结果记为移动端通过。
