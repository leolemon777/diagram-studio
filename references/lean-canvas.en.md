# Lean Canvas: nine validation questions

Lean Canvas is an early product-hypothesis worksheet and answers a different question from the Business Model Canvas. It places problem, customer segments, unique value proposition, solution, channels, revenue, cost, metrics, and unfair advantage in unequal regions. Every entry carries a stable ID, evidence, and status; unknown evidence stays explicitly unknown or a hypothesis.

## Input

Use `type: "lean-canvas"` with exactly these nine item IDs:

`problem`, `customer-segments`, `unique-value-proposition`, `solution`, `channels`, `revenue-streams`, `cost-structure`, `key-metrics`, and `unfair-advantage`.

Each block has 1–6 `entries`. Every entry needs `id`, `text`, `evidence`, and `status`; allowed statuses are `observed`, `validated`, `hypothesis`, `proposed`, and `unknown`. Stable IDs are preserved in SVG, draw.io, and scene JSON, and evidence status remains editable text.

```bash
python3 scripts/render.py assets/examples/38-lean-canvas-cn.json --out output/lean-canvas-cn
python3 scripts/render.py assets/examples/38-lean-canvas-en.json --out output/lean-canvas-en
```

The layout places problem/customer context on the outside, the value proposition in the middle, and a horizontal cost/revenue strip at the bottom. Long copy grows the regions; split dense material into a validation page. The canvas organises hypotheses; it does not calculate market size, revenue forecasts, priority weights, or product-market fit.

## Difference from Business Model Canvas

Business Model Canvas fixes partners, activities, resources, value, customer relationships, channels, customer segments, costs, and revenue. Lean Canvas starts with problems and customers, then puts solution and measurable validation questions at the centre. One must not be substituted for the other by changing a title.
