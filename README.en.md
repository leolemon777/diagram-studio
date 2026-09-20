# Diagram Studio · diagram-studio

[中文](README.md) · **English**

Diagram Studio is a local Codex skill for turning a natural-language brief into a clear diagram. It helps choose a suitable structure, lay out content, render the result, and inspect the actual output. You can also run its Python generators directly. Common uses include architecture diagrams, workflows, organization and relationship diagrams, project plans, and data charts.

## What can it create?

| Task | Common forms | Current support |
| --- | --- | --- |
| Architecture and systems | Business and system layers, C4 views, application and cloud architecture, network and data relationships | Ordinary layered architecture has adaptive layout. Specialized models follow their own input rules. See [architecture guidance](references/architecture.md). |
| Workflows and collaboration | Flowcharts, decisions, exception loops, swimlanes, basic sequences, a BPMN subset | Ordinary graph workflows have adaptive nodes and routes. Formal notation requires the relevant backend and checks. See [process guidance](references/process.md). |
| Structure and relationships | Organization trees, work breakdown, mind maps, people relationships, responsibility matrices | The skill chooses tree, graph, or matrix semantics as appropriate. |
| Planning and operations | Gantt charts, task dependencies, Kanban, PERT, milestones, operational analysis | Dates, progress, dependencies, and calculations are handled by specific rules. Check the [format and input limits](references/rendering.md). |
| Data and research | Comparisons, trends, distributions, statistical and selected scientific charts | Use real values and units. Specialist charts may need extra Python packages and validation. See [chart guidance](references/charts.md). |
| Engineering and industry examples | Facilities, energy, control, software infrastructure, and common cross-industry diagrams | Each specialist script covers only its documented model subset and may need domain review. |

You can also compare **different visual expressions of the same source data**, changing the reading order and composition while preserving values, units, relationships, and direction. The [four-study, eight-expression demo](demos/expression-lab/index.html) is reproducible. Catalog entries are search terms and rules, not a promise of a separate renderer for every named type. See the [verification record](references/verification-status.md) for tested scope.

## How to use it

If you are unsure which form to use, clone the repository and open the local [bilingual diagram chooser](demos/chooser/index.html) in a browser. Select the reader's question, a diagram form, and a visual direction; then enter your content and copy the resulting `$diagram-studio` prompt. It covers 19 common forms and explains the choice. The chooser itself does not render arbitrary input; Codex uses the skill to make the final diagram. Style thumbnails are directional sketches; see the [validated style scope](references/style-families.md).

### 1. Install it for Codex

On macOS or Linux, run:

```bash
git clone https://github.com/leolemon777/diagram-studio.git ~/.codex/skills/diagram-studio
```

If the directory is already a Git clone, run `git pull` inside it to update. If it was copied manually, back it up before replacing it. On Windows, place the repository at `%USERPROFILE%\.codex\skills\diagram-studio`. Then invoke `$diagram-studio` in a Codex task and describe the diagram you need. The full skill instructions are in [SKILL.md](SKILL.md).

Copy and adapt any of these prompts:

```text
Use $diagram-studio to draw an order fulfillment workflow: order placed → stock check → payment → dispatch → delivery. Out-of-stock loops to replenishment; failed payment ends the process. Label each decision branch and provide SVG plus editable draw.io source.

Use $diagram-studio to draw a software architecture for a product review. Show the web app, API, order service, inventory service, and database. Only draw calls I specify. Provide a presentation overview and readable detail pages.

Use $diagram-studio to compare before-and-after scores for four courses. Show two ways to read change using exactly the same values on a 0–100 scale, and explain which question each view answers best.
```

For a useful result, state **the audience, the question the diagram must answer, required objects and relationships, values and units, output format, and canvas size**. Ask the assistant to label assumptions when facts are missing. One skill accepts both English and Chinese requests.

### 2. Run the examples without Codex

The base renderer requires Python 3.9+ and no API key or remote generation service. From the repository root, run:

```bash
python3 scripts/render.py assets/examples-en/architecture.json --out /tmp/diagram-architecture-en --theme light
python3 scripts/render.py assets/examples-en/workflow.json --out /tmp/diagram-workflow-en --theme light
python3 scripts/render.py assets/examples/01-system-architecture.json --out /tmp/diagram-architecture-zh --theme light
python3 scripts/render.py assets/examples/02-workflow.json --out /tmp/diagram-workflow-zh --theme light
python3 scripts/expression_lab.py --out /tmp/diagram-expression-lab
```

The first four commands generate architecture and workflow examples in English and Chinese. Ordinary `render.py` output includes SVG, editable draw.io, the source brief, a scene file, and a QA record. Adaptive output also includes a reading HTML page and multipage source. The last command creates an offline comparison page for four simulated studies and eight expressions. See the [input and output reference](references/rendering.md). Some specialist charts require Matplotlib; Pillow is optional for more accurate font measurement in adaptive layouts.

## Diverse whiteboard methods and UX

Public Boardmix research informs a new Insights & workshops route: affinity, journey, retrospective and user story mapping. The chooser explains purpose, required content and actual support, links to examples, and preserves input and keyboard focus. Three original simulated studies cover education, retail and marketing. Story mapping is a method recipe requiring a newly checked layout; live collaboration and voting services are not implemented. See [methods and sources](references/boardmix-study.en.md) and [examples](demos/workshop-study/index.html).

## Five refined forms and their checks

A refined profile now covers ordinary workflows, layered architecture, delivery Gantt, single-series comparison and trend charts. It expands long content, separates primary and return paths, preserves signed values and missing observations, and offers a dot comparison alternative. Run `python3 scripts/refinement_suite.py --out /tmp/diagram-refinement`, serve that directory over local HTTP, and open the bilingual gallery of 11 original, changed and alternative outputs. See [inputs and scope](references/refinement.md).

This round passed 34 regression tests and actual desktop-browser text checks on 11 overviews. One workflow was edited, saved and reopened in draw.io. This is not approval of all diagram types, mobile layouts or aesthetics; see the [verification record](references/verification-status.md).

## Workflow and delivery improvements

Ordinary adaptive workflows now rank forward branches separately from feedback loops while preserving every relation label. The bilingual reader offers Overview and Readable size, reports displayed text size, and flags small text. `render.py` completes generation and detail-page checks in a staging directory before replacing outputs. Generation failures preserve the previous files; successful runs include a `delivery.json` record of input and output hashes. Promotion replaces individual files, not an atomic multi-file transaction. See [adaptive layout guidance](references/adaptive-layout.md) for scope. These changes independently implement ideas studied in [Archify](https://github.com/tt-a1i/archify).

## Outputs and limits

The skill helps select an expression and produces modifiable source files. The scripts do not interpret natural language on their own: the assistant using the skill interprets the brief and judges the finished visual. Review the actual output for labels, arrows, branches, units, and data. Passing automated boundary checks does not prove that a reader will understand the diagram.

SVG and draw.io remain editable formats. Dragging, saving, and reopening individual objects in a target editor still need to be verified for the specific file. Engineering, medical, and research diagrams are bounded by their documented inputs and checks and do not replace expert review.

The project draws on public diagram-design references but independently implements its code, layouts, and examples. It contains no commercial templates, image assets, or bundled fonts and is not affiliated with EdrawMax. The repository is currently shared for public testing and feedback; no open-source license has been added yet.
