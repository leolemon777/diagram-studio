# Delivery format matrix

The capability registry is the current source of truth for format scope; backends do not promise the same formats. The table lists representative files that exist and can be checked in v71. Byte and page checks cover the named artifacts only.

| Backend / form | Registered formats | Representative real check | Editable source |
| --- | --- | --- | --- |
| `scripts/render.py` · architecture/flow/network/planning | SVG, draw.io, scene JSON, QA JSON, HTML | English network SVG is 1800×792; draw.io parses as XML; HTML includes the offline reader and viewport | JSON brief, draw.io; regenerate from JSON when data changes |
| `scripts/data_art.py` · dumbbell/waterfall | SVG, draw.io, PNG, PDF, HTML, input JSON, scene JSON, analysis JSON, QA JSON, CSV | English dumbbell PNG is 1600×1000, PDF is one page, CSV is readable; waterfall emits the same set | input JSON, draw.io; regenerate from JSON when values change |
| `scripts/kanban_render.py` · Kanban | SVG, draw.io, input JSON, model JSON, QA JSON | Input, model, and XML source exist; a static snapshot is not live collaboration | input JSON, draw.io |
| `scripts/organization_relations.py` · affinity | SVG, PNG, input JSON, calculation JSON, QA JSON | Chinese and English examples exist; calculation record is separate from input | input JSON |
| `scripts/render.py` · storymap | SVG, draw.io, scene JSON, brief JSON, QA JSON, HTML | English story-map SVG, draw.io, and reader exist; activity/slice/story IDs remain traceable | JSON brief, draw.io |

For every output, first check non-empty bytes, parsability, key text, and an empty QA error list; then perform browser or native-editor review. An SVG or HTML opening does not approve domain facts or aesthetics. PNG/PDF are promised only by the specialist backends that register them. The delivery contract tests that a failed generation preserves the previous good delivery; see [delivery contract](delivery-contract.en.md).
