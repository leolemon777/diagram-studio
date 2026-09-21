# 能力登记与交付范围

机器可读源：`assets/capability-registry.json`（v69）。运行 `python3 scripts/capability_registry.py --check` 校验引用。

选图向导从同一份登记读取结构、后端、格式和验收状态；本表只列当前可追查的高频入口，不把入口数量当作完成率。

| ID | 图型 | 后端 | 格式 | 证据级别 |
|---|---|---|---|---|
| `tree` | 组织树 / 分解结构 | `scripts/render.py#tree` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `architecture` | 分层架构图 | `scripts/render.py#architecture` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `network` | 关系网络图 | `scripts/render.py#graph` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `flow` | 流程图 | `scripts/render.py#graph` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `swimlane` | 泳道流程图 | `scripts/render.py#graph` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `sequence` | 时序图 | `scripts/render.py#sequence` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `timeline` | 时间线 | `scripts/render.py#timeline` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `gantt` | 甘特图 | `scripts/render.py#gantt` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `dependency` | 任务依赖图 | `scripts/render.py#graph` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `bar` | 条形图 | `scripts/render.py#chart:bar` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `line` | 趋势图 | `scripts/render.py#chart:line` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `dumbbell` | 前后对照图 | `scripts/data_art.py#dumbbell` | svg, drawio, png, pdf, html, input.json, scene.json, analysis.json, qa.json, csv | `manual_visual_review` |
| `waterfall` | 瀑布图 | `scripts/data_art.py#waterfall` | svg, drawio, png, pdf, html, input.json, scene.json, analysis.json, qa.json, csv | `manual_visual_review` |
| `donut` | 环形占比图 | `scripts/render.py#chart:donut` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `heatmap` | 热力图 | `scripts/render.py#plot:heatmap` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `histogram` | 直方图 | `scripts/render.py#plot:histogram` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `scatter` | 散点图 | `scripts/render.py#plot:scatter` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `fishbone` | 鱼骨分析图 | `scripts/render.py#fishbone` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `quadrant` | 四象限优先级图 | `scripts/render.py#quadrant` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `swot` | SWOT 分析 | `scripts/render.py#matrix` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `kanban` | 泳道看板 | `scripts/kanban_render.py#render` | svg, drawio, input.json, model.json, qa.json | `manual_visual_review` |
| `funnel` | 漏斗图 | `scripts/layouts.py#tapered:funnel` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `business-model-canvas` | 商业模式画布 | `scripts/layouts.py#bmc` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `affinity` | 亲和图 | `scripts/organization_relations.py#affinity-map` | svg, png, input.json, calculation.json, qa.json | `manual_visual_review` |
| `journey` | 用户旅程图 | `scripts/render.py#journey` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `service-blueprint` | 服务蓝图 | `scripts/render.py#service-blueprint` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `retro` | 复盘行动板 | `scripts/render.py#table` | svg, drawio, scene.json, qa.json, html | `manual_visual_review` |
| `storymap` | 用户故事地图 | `scripts/render.py#storymap` | svg, drawio, scene.json, brief.json, qa.json, html | `manual_visual_review` |

证据级别只说明已执行的检查：`manual_visual_review` 仍不等于领域或用户批准；`planned` 入口不能直接宣称已实现。格式列表是该后端登记的交付协议，生成后仍需按项目实际检查。
