# Boardmix study: diverse expressions and whiteboard UX

Use for research synthesis, workshops, journey maps, retrospectives, user story maps, moodboards and purpose-based diagram selection. Public research dated 2026-09-20; [sources and comparison](boardmix-study.md). The initial public phase stopped at a login overlay. After the user signed in, four template boards were opened in the editor and visually inspected. Voting, AI generation, export, collaboration and version recovery were not tested. No commercial templates or proprietary algorithms were copied.

Follow-up: [eight additional templates, editor interactions and Grok X research](boardmix-deep-study.en.md). Cumulative visual sample: 12 templates; remaining gaps are explicit.

## Authenticated template inspection

On 2026-09-20, four separate template boards were opened using the application UI. Guided brainstorming and sailboat retrospective were labeled member-free at their entry points. Moodboard and user story map were also inspected. Private board URLs, account details and template assets are not distributed.

| Observed template | Visible composition | Independently adopted rule |
|---|---|---|
| Guided brainstorming | Numbered stages, participant groups, synthesis area, example beside blank workspace | Separate divergence, organization and convergence; explain inputs and outputs; participant colors do not imply priority |
| Design moodboard | Image/color/keyword clusters connected by associative curves, instructions and blank skeleton | Organize licensed or supplied references by proposition, label what each contributes and what connections mean |
| Sailboat retrospective | Sun, wind and lighthouse above water; obstacles separated into internal, external and organizational levels | Pair metaphors with plain labels for goals, drivers, barriers and risks; offer plain grouping when imagery impedes reading |
| User story map | Horizontal card sequences, vertical layers and separators, example beside blank structure | Clearly label both dimensions and preserve column alignment; absence is not zero, and release assignments require real input |

Zoom controls, fit-all and the pin list were inspected. Fit-all made text small; the observed pin entries were unnamed. Our rule therefore requires named persistent navigation plus readable detail. Reading and presentation modes were visible as entries but their complete behavior was not tested.

Choose staged workspaces for facilitated sessions, thematic clusters for visual directions, labeled metaphors for retrospectives and two-dimensional structures for experience/delivery planning. Include a small original example and corresponding input guidance, clearly separated from real data. Every zone needs a task title, input and expected output. Check starting point, reading order, category meaning, exceptions and static/small-screen readability; report any unchecked scope.

The existing example reader now applies persistent named navigation, current-section state, return-to-overview and keyboard-focusable diagram scroll regions. This does not add four dedicated renderers or reproduce commercial templates. Keep each diagram's reading state when navigating between sections.

## Reuse and extend

Mind maps, flowcharts, Gantt, timelines, Kanban, affinity maps, journeys, service blueprints, SWOT and business canvases already have related rules or examples. Reuse their semantics instead of counting synonyms as new capabilities. This round adds education feedback, retail journey and marketing retrospective examples, a workshop route in the chooser, and the following method recipes.

- **Affinity synthesis:** retain each observation's ID, original wording and source. Group each observation once; mark inferred groupings. Keep minority and unassigned feedback visible. Group sizes are not prevalence estimates.
- **Journey analysis:** define persona, goal, scenario and stages. Separate behavior, touchpoints, observations, hypotheses and validation. Do not invent emotion scores. Use a service blueprint when backstage delivery is the question.
- **Retrospective action board:** distinguish stop/start/continue decisions, unresolved disagreements and proposed follow-up. Trace actions to observations; include owner, review date and a way to check the result. Unknown commitments remain unassigned.
- **User story map:** organize activities horizontally and stories into explicit release slices vertically. Each slice should support a usable experience. Preserve IDs and avoid double-counting referenced work. A release slice is not a scaled calendar interval. A dedicated measured renderer was added in v43; see [inputs, examples and verified scope](story-map.en.md).
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
