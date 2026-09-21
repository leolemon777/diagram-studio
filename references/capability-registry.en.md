# Capability registry and delivery scope

The machine-readable source is [`assets/capability-registry.json`](../assets/capability-registry.json) (v69). The chooser reads structure, backend, formats and evidence from this file. Run `python3 scripts/capability_registry.py --check` to validate every backend, example and evidence reference. The compact table below is a human index; the JSON carries the complete fields.

| ID | Form | Backend | Formats | Evidence |
|---|---|---|---|---|
| `tree` | Tree / work breakdown | `scripts/render.py#tree` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `architecture` | Layered architecture | `scripts/render.py#architecture` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `network` | Relationship network | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `flow` | Flowchart | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `swimlane` | Swimlane workflow | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `sequence` | Sequence diagram | `scripts/render.py#sequence` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `timeline` | Timeline | `scripts/render.py#timeline` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `gantt` | Gantt chart | `scripts/render.py#gantt` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `dependency` | Dependency graph | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `bar` | Bar chart | `scripts/render.py#chart:bar` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `line` | Trend chart | `scripts/render.py#chart:line` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `dumbbell` | Before/after dumbbell | `scripts/data_art.py#dumbbell` | SVG, draw.io, PNG, PDF, HTML, source/analysis/QA, CSV | `manual_visual_review` |
| `waterfall` | Waterfall chart | `scripts/data_art.py#waterfall` | SVG, draw.io, PNG, PDF, HTML, source/analysis/QA, CSV | `manual_visual_review` |
| `donut` | Donut chart | `scripts/render.py#chart:donut` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `heatmap` | Heatmap | `scripts/render.py#plot:heatmap` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `histogram` | Histogram | `scripts/render.py#plot:histogram` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `scatter` | Scatter plot | `scripts/render.py#plot:scatter` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `fishbone` | Fishbone diagram | `scripts/render.py#fishbone` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `quadrant` | Quadrant priority matrix | `scripts/render.py#quadrant` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `swot` | SWOT analysis | `scripts/render.py#matrix` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `kanban` | Swimlane Kanban | `scripts/kanban_render.py#render` | SVG, draw.io, input/model/QA | `manual_visual_review` |
| `funnel` | Funnel chart | `scripts/layouts.py#tapered:funnel` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `business-model-canvas` | Business model canvas | `scripts/layouts.py#bmc` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `affinity` | Affinity map | `scripts/organization_relations.py#affinity-map` | SVG, PNG, input/calculation/QA JSON | `manual_visual_review` |
| `journey` | Journey map | `scripts/render.py#journey` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `service-blueprint` | Service blueprint | `scripts/render.py#service-blueprint` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `retro` | Retrospective board | `scripts/render.py#table` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `storymap` | User story map | `scripts/render.py#storymap` | SVG, draw.io, scene/brief/QA, HTML | `manual_visual_review` |

Evidence levels describe checks that were actually run; manual review is not domain or user approval. Registered formats are delivery contracts and still require project-level inspection. The number of entries is not a completion percentage.
