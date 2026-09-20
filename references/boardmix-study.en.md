# Boardmix study: diverse expressions and whiteboard UX

Use for research synthesis, workshops, journey maps, retrospectives, user story maps, moodboards and purpose-based diagram selection. Public research dated 2026-09-20; [sources and comparison](boardmix-study.md). The application showed a login overlay. Its exploration categories were observed, but live editing, voting, AI generation, export and collaboration were not tested. No commercial templates or proprietary algorithms were copied.

## Reuse and extend

Mind maps, flowcharts, Gantt, timelines, Kanban, affinity maps, journeys, service blueprints, SWOT and business canvases already have related rules or examples. Reuse their semantics instead of counting synonyms as new capabilities. This round adds education feedback, retail journey and marketing retrospective examples, a workshop route in the chooser, and the following method recipes.

- **Affinity synthesis:** retain each observation's ID, original wording and source. Group each observation once; mark inferred groupings. Keep minority and unassigned feedback visible. Group sizes are not prevalence estimates.
- **Journey analysis:** define persona, goal, scenario and stages. Separate behavior, touchpoints, observations, hypotheses and validation. Do not invent emotion scores. Use a service blueprint when backstage delivery is the question.
- **Retrospective action board:** distinguish stop/start/continue decisions, unresolved disagreements and proposed follow-up. Trace actions to observations; include owner, review date and a way to check the result. Unknown commitments remain unassigned.
- **User story map:** organize activities horizontally and stories into explicit release slices vertically. Each slice should support a usable experience. Preserve IDs and avoid double-counting referenced work. A release slice is not a scaled calendar interval. This is a recipe requiring a newly composed and inspected layout, not a dedicated renderer.
- **Event storming:** a novel exploration entry observed on the product home. Distinguish business events, commands, actors and open questions. No complete domain-modeling workflow or dedicated renderer was implemented in this study.
- **Moodboard:** another observed entry, useful for brand, learning, space and content proposals. Organize supplied or licensed references around a specific visual proposition; identify what each reference contributes. Without assets, produce a text direction board instead of inventing reference artworks. No dedicated asset workflow was implemented here.

For decisions, draw voting results only from actual votes and rules. Record participant scope and allocation rules; popularity is not measured impact. Use impact/effort coordinates only with defined axes and evidence. Missing evidence calls for a discussion category, not fabricated scores.

## UI/UX application

The [bilingual chooser](../demos/chooser/index.html) now includes an **Insights & workshops** purpose, four distinct diagram sketches, contextual minimum inputs, explicit implementation scope and links to real examples or methods. Switching language or visual direction retains user input. Keyboard focus is restored after controls are rebuilt.

Use progressive disclosure: purpose → suitable form → required content → detailed method. Give the reader a visible starting point and a way to inspect evidence. Provide overview and readable detail where needed; preserve important meaning in static exports. Different purposes may use different visual systems—editorial, analytical, narrative or technical—without changing the underlying facts. Novelty is welcome when it reduces or justifies reading effort.

These are independently applied principles, not a replica of Boardmix's interface. They do not implement live collaboration, chat, voting services, cloud history or BDX export.

## Runnable examples

See the [three original studies](../demos/workshop-study/index.html) and `assets/workshop-examples/`. All values and observations are simulated.

```bash
python3 scripts/organization_relations.py assets/workshop-examples/education-affinity.json --out output/workshop
python3 scripts/render.py assets/workshop-examples/retail-journey.json --out output/workshop
python3 scripts/render.py assets/workshop-examples/marketing-retrospective.json --out output/workshop
```

Affinity rendering needs Matplotlib and retains editable model JSON; it does not export draw.io. The two table examples export SVG, draw.io, JSON and geometric QA. Group completeness and uniqueness were checked for affinity, and geometry passed for the tables. These do not prove aesthetic, native-editor or domain acceptance. Inspect every regenerated output after changing the content.

[Observed checks](../assets/boardmix-study-evidence.json) record desktop choice switching, input retention across languages, keyboard focus and the reading toggle. Representative portions of all three diagrams were viewed; automated browser text-boundary checks and mobile validation were not completed.
