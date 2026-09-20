# Capability registry and delivery scope

The machine-readable source is [`assets/capability-registry.json`](../assets/capability-registry.json). The chooser reads structure, backend, formats and evidence from this file. Run `python3 scripts/capability_registry.py --check` to validate every backend, example and evidence reference. The compact table below is a human index; the JSON carries the complete fields.

| ID | Form | Backend | Formats | Evidence |
|---|---|---|---|---|
| `tree` | Tree / work breakdown | `scripts/render.py#tree` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `architecture` | Layered architecture | `scripts/render.py#architecture` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `network` | Relationship network | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `flow` | Flowchart | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `swimlane` | Swimlane workflow | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `sequence` | Sequence diagram | `scripts/render.py#sequence` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `timeline` | Timeline | `scripts/render.py#timeline` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `gantt` | Gantt chart | `scripts/render.py#gantt` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `dependency` | Dependency graph | `scripts/render.py#graph` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `bar` / `line` | Bar / trend chart | `scripts/render.py#chart` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` / `manual_visual_review` |
| `dumbbell` | Before/after dumbbell | `scripts/data_art.py#dumbbell` | SVG, draw.io, PNG, PDF, HTML, source/analysis/QA, CSV | `rendered_visual_check` |
| `donut` | Donut chart | `scripts/render.py#chart:donut` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `histogram` / `scatter` | Histogram / scatter | `scripts/render.py#plot` | SVG, draw.io, scene/QA, HTML | `generated_with_semantic_validation` |
| `affinity` | Affinity map | `scripts/organization_relations.py#affinity-map` | SVG, PNG, input/calculation/QA JSON | `manual_visual_review` |
| `journey` / `retro` | Journey / retrospective board | `scripts/render.py#table` | SVG, draw.io, scene/QA, HTML | `manual_visual_review` |
| `storymap` | User story map | `scripts/render.py#storymap` | SVG, draw.io, scene/brief/QA, HTML | `manual_visual_review` |

Evidence levels describe checks that were actually run; manual review is not domain or user approval. Registered formats are delivery contracts and still require project-level inspection. The number of entries is not a completion percentage.
