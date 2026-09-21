# User-path storyboard: review the complete path

The user-path storyboard is for interface, service, and workflow review. It answers: under which preconditions does a person move through visible states and steps, what is next, and where can a branch or failure occur? It differs from a user story map, which organises activities and delivery slices.

## Input

Use `type: "user-path-storyboard"` with:

- `preconditions`: 1–6 stable-ID prerequisites;
- `states`: 2–8 visible states with stable `id`, `label`, and `detail`;
- `steps`: 4–12 contiguous numbered steps with `id`, `state`, `actor`, `action`, `result`, and `next`; the final step must have an empty `next`;
- optional `branches` and `exceptions`, each with stable ID, `from`, `to`, `label`, `condition`, and `proposal`. Exceptions also carry `recovery`.

Every non-final step must declare a next step, branch, or exception. `proposal: true` marks an unverified option; the renderer shows it with dashed lines and a proposal label rather than presenting it as fact. All source IDs are preserved in SVG, draw.io, and scene JSON for item-level editing and review.

```bash
python3 scripts/render.py assets/examples/37-user-path-storyboard-cn.json --out output/user-path-cn
python3 scripts/render.py assets/examples/37-user-path-storyboard-en.json --out output/user-path-en
```

The main path runs horizontally, while returns, branches, and exceptions use separate tracks connected to concrete steps. Long copy grows cards; split very long paths into an overview and local exception pages. This is a low-fidelity review and proposal tool, not an executable workflow engine, service promise, or domain approval.
