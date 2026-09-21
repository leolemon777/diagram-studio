# Funnel and business model canvas

These are high-frequency strategy and delivery forms, but they answer different questions: a funnel shows how one process narrows by stage, while a business model canvas organises hypotheses across nine fixed blocks.

## Funnel

Use `type: "tapered"` with `mode: "funnel"`. Provide 2–6 ordered `items`; each item needs a `label` and a positive `value`, and counts must stay flat or decrease. `unit` and `ratio_label` are shown beside each stage for one shared counting scope such as people, orders, or applications.

```bash
python3 scripts/render.py assets/examples/25-funnel-en.json --out output/funnel-en
```

Funnel width encodes the declared count ratio only. It does not explain drop-off causes, calculate significance, or turn simulated input into a real conversion rate.

## Business model canvas

Use `type: "bmc"` with nine items in this order: Key Partnerships, Key Activities, Key Resources, Value Propositions, Customer Relationships, Channels, Customer Segments, Cost Structure, Revenue Streams. Each item has a `label` and `detail`; keep entries short and split long research into a validation page.

```bash
python3 scripts/render.py assets/examples/33-business-model-canvas-en.json --out output/bmc-en
```

The canvas organises hypotheses to validate. It does not calculate market size, pricing, revenue forecasts, or strategic priority. Include evidence status, sources, and owners before domain review.
