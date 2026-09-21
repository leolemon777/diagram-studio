# v74 Release Notes

Date: 2026-09-21

v74 closes a reviewable loop around high-frequency, cross-industry and release-confidence work. It does not promise that every complex input will be laid out perfectly; the tested scope, evidence files and limits below define the claim.

## Included in this release

- Eight groups and 30 registered capabilities, with bilingual chooser continuity evidence.
- Embedded-content closure for nine popular pages—flow, architecture, swimlane, Gantt, network, data story, story map, user-path storyboard and Lean Canvas—at 390×844 and 768×1024; wide drawings stay inside explicit scroll regions.
- Six popular demo shells default to readable natural-size mode on narrow viewports; measured embedded text is 14px minimum, with the compact Gantt print variant recorded separately at 12px, and page-level overflow remains 0/18.
- Six cross-industry trial cases—software, retail, education, marketing, HR/administration, and travel/store service—each with one meaningful revision and a traceable input, SVG preview, editable draw.io source, scene, QA record and delivery receipt.
- The trial regression contract now verifies the input SHA-256, receipt manifest hashes, parseable scene/QA files with no errors, and the revised text in the rendered SVG; swimlane roles and retail/marketing semantics have dedicated checks.
- Fresh-directory reproduction of the basic renderer and one valid cross-industry model; artifacts are complete, QA has no errors, and generated output contains no development-machine absolute paths, local service URLs or private-directory dependencies.
- Fifteen representative draw.io files edited, saved and reopened in diagrams.net; this evidence is not generalized to every type or editor.

## Traceable files

- [Bilingual trial guide](trial-guide.en.md)
- [Popular viewport evidence](../assets/v74-popular-viewport-evidence.json)
- [Chooser continuity evidence](../assets/v74-chooser-continuity-evidence.json)
- [Six-industry trial evidence](../assets/v74-trials/evidence.json)
- [Clean-directory evidence](../assets/v74-clean-install-evidence.json)
- [Full release evidence](../assets/v74-release-evidence.json)
- [Verification status and limits](verification-status.md)

## Verification

The source repository and installed copy each pass 130 regression tests; quick validation, JSON parsing, link audit, diff checks and recursive parity are rerun and recorded before release. The basic renderer requires Python 3.9+; specialist cross-industry backends may require Matplotlib/Pillow.

## Limits

Simulated cases are not industry facts and specialist domains still need review. Popular narrow-screen evidence is not generalized to arbitrary high-density inputs. The local EdrawMax/万兴图示 session still rejects a temporary `.drawio` copy, so only the representative diagrams.net round trips are recorded as passed. No real JEV Skill name, path or callable entry is available, so JEV is not claimed as integrated or passed.
