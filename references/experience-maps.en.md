# Journey maps and service blueprints

Both forms use `scripts/render.py` and the shared SVG, draw.io, scene, QA and delivery-receipt contract, but they answer different questions: a journey map follows one person’s experience, while a service blueprint follows visible service actions and backstage collaboration.

## Journey map

Use `type: "journey"`:

- `persona`, `goal`, and 2–8 `stages` are required.
- Each stage has a stable `id`, `label`, `behavior`, and `touchpoint`.
- `evidence` keeps original text and a `source`; `opportunities` must reference evidence; `actions` must reference opportunities and include an `owner` and testable `check`.
- `emotion` is qualitative and requires a `basis`; the renderer never invents a score.

Generate the example with:

```bash
python3 scripts/render.py assets/experience-models/education-journey-en.json --out /tmp/education-journey-en
```

Read stages from left to right, then evidence → opportunity → action from top to bottom. Empty cells are labelled as such and are not interpreted as “no problem”.

## Service blueprint

Use `type: "service-blueprint"`:

- `customer`, `goal`, 2–8 service stages, and 3–6 `lanes` are required.
- Each lane declares a `kind`: `customer`, `frontstage`, `backstage`, `support`, or `system`.
- Each cell has a stable `id`, a `stage`, and `text`, with an optional `owner`.
- `boundaries` are drawn only between adjacent lanes; `handoffs` must point to real cells. Layout never infers collaboration from adjacency.

Examples are `assets/experience-models/retail-service-blueprint.json` and its English version. They place online order, store preparation, pickup and aftercare on one chain while separating frontstage, backstage, support and system records.

Both inputs can be checked with `python3 scripts/capability_registry.py --check`; the shared delivery contract checks stable IDs, display text and the receipt. These forms are reviewable service models, not live collaboration, voting, ticket execution or domain fact validation.
