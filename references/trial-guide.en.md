# Bilingual trial pack · Diagram Studio

Use this pack to start with six common industry questions. Every case uses simulated data. Open the demo first to understand the reading order, then edit the JSON or give the bilingual brief to Codex. After changing input, regenerate and inspect text, relationships, values, units, and delivered files.

## Six starting scenarios

| Industry question | Reading path | Entry and editable source | Meaningful revision |
| --- | --- | --- | --- |
| Software product: module boundaries and service links | Layered overview → relationship detail | [architecture demo](../demos/architecture/index.html), [network demo](../demos/network/index.html) | Add an explicit user-feedback module and one declared return link |
| Retail/e-commerce: fulfillment exceptions | Main process → exception loop | [flow demo](../demos/flow/index.html), [Kanban demo](../demos/strategy-execution/index.html) | Change “out of stock” to “store confirmation failed”; recheck endpoint and branch labels |
| Education/training: course launch and learning path | Date order → task dependencies | [Gantt demo](../demos/gantt/index.html), [route and mind-map demo](../demos/route-mindmap/index.html) | Move one activity and add a prerequisite; confirm dates, progress, and dependencies update together |
| Marketing: campaign results and change | Zero-baseline comparison → trend | [data-story demo](../demos/data-story/index.html), [waterfall demo](../demos/waterfall/index.html) | Change one channel value and confirm units, totals, and legends contain no stale value |
| HR/administration: handoffs and prioritisation | Ownership swimlane → SWOT/Kanban | [swimlane demo](../demos/swimlane/index.html), [analysis forms](../demos/analysis-forms/index.html) | Add one handoff and confirm role, direction, and exception loop remain explicit |
| Travel/store service: on-site experience and backstage fulfilment | Journey evidence → service blueprint | [experience-map demo](../demos/experience-maps/index.html), [story-map demo](../demos/storymap/index.html) | Change one touchpoint to “reschedule request”; confirm evidence, opportunity, and action remain traceable |

Two additional high-frequency entries are available: [Lean Canvas](../demos/lean-canvas/index.html) keeps problems, solutions, metrics, and evidence on one validation board; [user-path storyboard](../demos/user-path-storyboard/index.html) reviews preconditions, visible states, next steps, branches, and exceptions. Both provide bilingual JSON, SVG, draw.io, and QA, and neither turns a proposal into a fact automatically.

## Minimum workflow

1. Open an entry and read the question it answers and its scope note.
2. Open the linked JSON or draw.io source and make one revision from the table.
3. From the repository root, run for example:

   ```bash
   python3 scripts/render.py assets/examples/02-workflow.json --out /tmp/diagram-trial-flow --theme light
   python3 scripts/render.py assets/examples/61-gantt-delivery.json --out /tmp/diagram-trial-gantt --theme light
   python3 scripts/render.py assets/examples/09-line-chart-en.json --out /tmp/diagram-trial-trend --theme light
   ```

4. Open the generated SVG, HTML, and draw.io files. Record what can be edited directly and which data changes require regenerating from JSON.
5. Use the bilingual chooser to generate a second expression for the same question and compare the reading order. Style cards use the selected form's real miniature; the final output still needs a visual check.

## Feedback record

```text
Scenario / input language:
Audience and question:
Was form selection easy? Yes / no; where did it stop:
Were key labels and relationships readable? Yes / no; which one:
Did the visual direction help reading? Yes / no; which one:
Could SVG / draw.io / JSON be revised:
Export or opening failure:
High-frequency form you would add:
```

This template is not a substitute for real user research. Domain facts, data sources, statistical significance, and native-editor behavior need their own review. Live collaboration, voting, and a complete whiteboard product are outside this trial pack.
