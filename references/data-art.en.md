# Data-art delivery notes

Use these recipes when the brief needs measured marks, fine ticks, clear text hierarchy and editorial annotations. They complement the structural families: data-art stays in this document, while fishbone, architecture and workflow remain in `style-families.md`. Texture cannot stand in for a missing relationship.

From v54, the before/after dumbbell recipe has bilingual cross-industry examples (`dumbbell-cn.json` and `dumbbell-en.json`). The optional `language` field accepts `zh` or `en`. The English plate localises the reading guide, observation, boundary, source marker and recipe label, and wraps long entity names at word boundaries. v55 adds the same bilingual treatment to the waterfall examples (`waterfall-cn.json` and `waterfall-en.json`), preserving the opening, closing, signed changes and declared quantum. Other recipes still need a language-specific review; bilingual coverage of these two forms is not evidence for every data-art form.

```bash
python3 scripts/data_art.py assets/data-art-examples/dumbbell-en.json \
  --out demos/dumbbell/en --mode detail --theme warm
```

The before/after form keeps paired entities, original units and absolute positions. A segment shows change; it does not establish causality. Keep the observation window and case mix visible before interpreting a difference.
