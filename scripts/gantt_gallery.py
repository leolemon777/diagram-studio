#!/usr/bin/env python3
"""Render the bilingual Gantt gallery from two shared task truths.

Each language keeps the same IDs, dates, progress and dependencies.  The
three outputs change only the reading mode: executive, delivery or print.
"""
from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path

from render import render_file


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("executive", "delivery", "print")


def build_gallery(out: Path) -> list[dict]:
    records = []
    with tempfile.TemporaryDirectory(prefix="diagram-gantt-") as staging:
        staging = Path(staging)
        for language in ("cn", "en"):
            base = json.loads((ROOT / f"assets/examples/gantt-{language}.json").read_text(encoding="utf-8"))
            for variant in VARIANTS:
                model = copy.deepcopy(base)
                model["gantt_variant"] = variant
                source = staging / f"gantt-{language}-{variant}.json"
                source.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
                target = out / language / variant
                result = render_file(source, target, theme="light")
                records.append({"language": language, "variant": variant, **result})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    records = build_gallery(args.out)
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
