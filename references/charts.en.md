# Charts, distributions and relationships

Keep raw values, units, time window, source, missingness and denominator. When no real data is supplied, label simulated values clearly.

| Question | Form | Guardrail |
|---|---|---|
| Rank and compare categories | Bar | Start the value axis at zero; use a signed axis for negative values |
| Show a distribution | Histogram | Keep equal-width or explicitly declared bins and the boundary rule |
| Inspect two variables | Scatter | Keep paired observations and units; correlation is not causation |
| Show a shared composition | Donut | Parts must share one meaningful whole |
| Compare ordered change | Line | Preserve order and missingness; do not smooth invented peaks |

Generate the v53 bilingual distribution examples with the shared vector renderer:

```bash
python3 scripts/render.py assets/examples/50-histogram-en.json --out output/histogram-en
python3 scripts/render.py assets/examples/46-scatter-en.json --out output/scatter-en
```

The renderer checks finite observations, equal histogram bins, point bounds, content retention and measured labels. It does not fit a distribution, calculate regression significance, forecast, establish causality, or validate data provenance.
