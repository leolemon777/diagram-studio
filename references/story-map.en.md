# User story maps: from experience to release

[中文说明](story-map.md). A dedicated renderer now supports product, education, retail and service planning. The team must still confirm whether each slice provides a usable experience.

Activities run horizontally in user order; explicit release slices run vertically. Each story belongs to exactly one activity and one release. Empty means not scheduled, not zero or automatically missing. This is not a scaled calendar or dependency schedule.

## Input and generation

Use `scripts/render.py` with `type: "storymap"`. Required: non-empty `persona`, `goal`, `activities`, `releases` and `stories`. Start from [the complete English input](../assets/storymap-examples/education-storymap-en.json).

| Collection | Required fields | Optional fields |
|---|---|---|
| activities | id, label | — |
| releases | id, label, goal | — |
| stories | id, activity, release, label | detail, source |

IDs must be unique within each collection, start with an ASCII letter, contain only letters/digits/underscores/hyphens, and have at most 64 characters. Labels support Chinese and English. Story references must resolve. Optional text fields must be non-empty when supplied. A source label does not verify the source itself.

Array order determines activity columns, release rows and story order within a cell. `language: "en"` changes structural labels; supply translated content separately. The renderer does not translate user text. `width` is a minimum, and additional columns may expand it. Arbitrary full text cannot be guaranteed to fit a fixed slide at readable size.

Top-level `edges/dependencies/votes/dates` and story fields `depends/depends_on/votes/start/end` are rejected rather than silently dropping their meaning. Other undocumented fields have no display or processing guarantee.

```bash
python3 scripts/render.py assets/storymap-examples/education-storymap-en.json --out output/storymap
```

Text is measured before card and row sizing. Long content increases height; additional activities increase width. Body font sizes stay fixed. Stable IDs are retained in native draw.io objects and scene metadata (`meta.story_map`).

Outputs include complete SVG, draw.io, original brief JSON, scene, geometric QA, delivery receipt and standalone reading HTML. The [bilingual demo](../demos/storymap/index.html) changes complete diagram content and explicitly lists download scope: both releases, all three activities and six stories, independent of scroll position.

Readable size allows internal scrolling. Overview is for structure; text below the current 12px review threshold triggers advice to switch back. Text bounds, displayed font size and human visual review remain separate checks.

## Verified scope

Six new regression tests cover assignments, long Chinese content, reordered activities, invalid references/duplicate IDs, preserving prior delivery on failure, and an English long heading. All 40 tests passed. Both SVGs passed browser text checks at 1280×720 and actual 390×844 viewports; readable mode had 14px minimum content text. See [v43 evidence](../assets/v43-storymap-evidence.json).

The diagram was edited, saved and reopened in the draw.io browser editor; the edited text, 58 XML cells, 3 edges and story IDs remained intact. Extreme-content unit fixtures were not individually reviewed in the browser. Inspect every new real-content output. Live collaboration, voting, dependency scheduling and automatic validation of a minimum usable release are not implemented.
