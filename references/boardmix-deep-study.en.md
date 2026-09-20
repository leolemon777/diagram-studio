# Deeper whiteboard study and X leads

Date: 2026-09-20. Focus: common cross-industry diagram composition and UX. This is a bounded research batch, not full-library coverage or a completed product benchmark. See the [Chinese observation matrix and original post links](boardmix-deep-study.md).

## Direct Boardmix observations

Eight additional templates were inserted into the existing research board and visually inspected, bringing the cumulative total to **12 distinct templates**. The new directory page asked for login, while the existing authenticated editor's template center remained usable. The research copy was renamed clearly; existing business boards were not changed. No commercial assets or private board URLs are distributed.

| Template | Visible composition | Independent design implication |
|---|---|---|
| Architecture | Horizontal layers, nested zones, cross-cutting side rails, inter-layer arrows | Distinguish containment from calls; require evidence for both directions of a two-way edge |
| Service blueprint | Aligned stages, front/backstage lanes, interaction and visibility boundaries | Boundary lines carry meaning; retain handoffs rather than reskinning a journey table |
| User journey | Stage-by-dimension grid with notes and qualitative emotion icons | Pair emotion with text; use measured curves only with measurements; trace opportunities to observations |
| Roadmap | Time headings, colored work tracks and multi-period bars | Distinguish directional plans from dated commitments and computed dependency schedules |
| Fashion planning | Image clusters, palettes, garment line drawings and classification matrices | Organize reference → design attributes → candidates; use supplied/licensed assets only |
| Research methods roadmap | Stage rail plus branching/rejoining logic | Represent methodological reasoning, not calendar duration; align stage and method semantics |
| Event storming | Successive event timelines, role/action additions, groups and boundary views | Preserve mapping between passes; visual grouping does not validate domain boundaries |
| Lean canvas | Unequal numbered regions and split subregions | Preserve business questions and reading order; do not conflate lean and business-model canvases |

Observation depth varies: full composition was seen, with closer service-blueprint and journey views; this is not exhaustive text inspection or native editing round-trip validation.

## Interaction evidence

Template preview/use was exercised. Selecting a journey note exposed a floating toolbar; double-clicking exposed font controls. A v43 follow-up added three paragraphs to a separate synthetic research sticky at 100% view: its width remained while height grew, and undo restored the earlier text and height. This one sample does not establish all text styles, container behavior or exported-file round trips. Reading mode was entered and exited: editing tools hid, pin navigation remained, and Escape was documented in the UI. This does not guarantee readable overview text.

An independent simulated board was created for the export trial: three long-text sticky notes and two arrow connectors. The image dialog was exported with SVG, all-area, and no watermark and showed a success toast. PDF was exported with 16:9, no margin, all-area, and no watermark and showed a success toast. The Markdown dialog listed all three notes, showed `Export (3)`, and showed a success toast. The JSON dialog reported no exportable mind-map content and kept its export button disabled, which is a mind-map-only boundary rather than a generic freeform-board export. Boardmix local backup was invoked. Browser automation did not expose downloaded file bytes, so these are UI-success observations rather than byte-level file validation; see [the export trial evidence](../assets/boardmix-export-trial-evidence.json). Reloading the editor preserved all five objects, both connectors and the reported 72 board words. The dialog still showed two original pin pages after additional templates were added: pagination count alone cannot prove export coverage. The research board rename succeeded.

## Grok CLI and X evidence

Grok CLI ran native X keyword, semantic, user and thread tools. Logged calls include repeated searches; they are not independent sample counts. Its supplementary web fetches were cancelled before reading; a resumed session produced the final report from prior X results. It returned eight candidates, **without visually inspecting any attached images**:

- Honghao Peng: post independently read in v43; X media still login-gated. The linked public Boardmix work was opened read-only and visually inspected, as described below.
- Carl Vellotti: customer journey ending in actionable opportunities — method lead, image not inspected.
- Steve / Builder.io: whole-user-flow storyboard — official repository independently confirms visual-plan/visual-recap purposes; tools were not installed or run.
- Sahn Lam: cache hit/miss sequence diagram — post and author reply independently read in browser; media opened a login prompt, image not inspected.
- Matt Pocock: icons in a custom tldraw diagram — author preference, insufficient visual evidence for a style rule.
- Moksh: Mem0 architecture learning sketch — composition unknown.
- Figma: recommended CJM community template — official recommendation, not independent user testing.
- Ona: fintech user flow and information architecture — personal workflow lead, composition unknown.

All eight source links and verification levels are in the [linked matrix](boardmix-deep-study.md#xgrok-cli-调研结果与复核). No engagement metrics or unverified dates are used to rank quality. Sparse Boardmix results in this batch do not prove a lack of good work on X. Ads and tool lists were excluded from visual conclusions.

## Public work follow-up (v43)

The Boardmix work linked publicly from Honghao Peng’s post opened read-only. It is a user work, not an additional template in the 12-template count. Inspection covered the long-board overview, one error/solution detail, and the overall-process area reached via a named pin. Steps combine text with screenshots marked by arrows and rectangles. Seven named pins cover prerequisites, overview, environment, execution, useful links and configuration. Not every section was read in full, and no commands in the work were executed. X-attached images remain unviewed.

Independent implications: connect steps with evidence and explanations; name navigation for reader tasks. v43 now implements a [dedicated story map](story-map.en.md) with measured card/row expansion, unique assignments, sources, complete bilingual content and explicit download scope. Affinity choices no longer offer unsupported draw.io output.

## Implementation priorities

These are rules and proposals, not claims of completed new renderers.

1. Preserve semantic differences: blueprint boundaries/handoffs, journey evidence→opportunity→action, separate static architecture and dynamic sequences with stable cross-references.
2. Use low-fidelity whole-path storyboards for flow review: preconditions, visible states, branches, next steps and errors; mark unverified paths as proposals.
3. Make controls contextual. Reading mode should preserve location and named navigation, then restore editing context; tools should not cover the text being edited.
4. Make export scope explicit before format/background and preview. List included sections and omissions; verify actual output before claiming completeness.
5. Support mixed reference boards across industries; each asset type should answer a question and retain source/assumption status.

Remaining: systematic community/style sampling; additional text styles and long text inside containers, connector binding and routing, container move/resize and undo (one separate sticky’s growth and undo tested); byte-level validation and independent re-opening of downloaded SVG/PDF/Markdown/backup files; collaboration/voting/presentation flows; visual inspection of X media. Cloud-editor reload passed for the trial board, but it does not substitute for downloaded-file round trips. Prioritize common behaviors and novel structure, not niche duplicates or recolors. No full-product percentage is reported because the sampling universe is not fixed.
