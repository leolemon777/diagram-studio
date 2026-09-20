# 能力登记与交付范围

机器可读源是 [`assets/capability-registry.json`](../assets/capability-registry.json)。选图向导从同一份登记读取结构、后端、格式和验收状态；运行 `python3 scripts/capability_registry.py --check` 会检查所有后端、示例和证据引用。下面的表由 `--markdown` 生成，不能替代 JSON 的完整字段。

| ID | 图型 | 后端 | 格式 | 证据级别 |
|---|---|---|---|---|
| `tree` | 组织树 / 分解结构 | `scripts/render.py#tree` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `architecture` | 分层架构图 | `scripts/render.py#architecture` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `network` | 关系网络图 | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `flow` | 流程图 | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `swimlane` | 泳道流程图 | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `sequence` | 时序图 | `scripts/render.py#sequence` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `timeline` | 时间线 | `scripts/render.py#timeline` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `gantt` | 甘特图 | `scripts/render.py#gantt` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `dependency` | 任务依赖图 | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `bar` / `line` | 条形图 / 趋势图 | `scripts/render.py#chart` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` / `manual_visual_review` |
| `dumbbell` | 前后对照图 | `scripts/data_art.py#dumbbell` | SVG, draw.io, PNG, PDF, HTML, source/analysis/QA, CSV | `rendered_visual_check` |
| `donut` | 环形占比图 | `scripts/render.py#chart:donut` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `histogram` / `scatter` | 直方图 / 散点图 | `scripts/render.py#plot` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `affinity` | 亲和图 | `scripts/organization_relations.py#affinity-map` | SVG, PNG, input/calculation/QA JSON | `manual_visual_review` |
| `journey` / `retro` | 用户旅程 / 复盘行动板 | `scripts/render.py#table` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `storymap` | 用户故事地图 | `scripts/render.py#storymap` | SVG, draw.io, scene/brief/QA, HTML | `manual_visual_review` |

证据级别只说明已执行的检查；人工查看不等于领域或用户批准。登记格式是交付协议，生成后仍要按项目实际检查。入口数量不代表完成率。
