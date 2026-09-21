#!/usr/bin/env python3
"""Shared delivery receipt, content-preservation and version snapshot helpers.

The renderers keep their own semantic validators and layout algorithms.  This
module gives them one small hand-off contract: hash the frozen input and every
delivered artifact, record checks separately, verify stable IDs/relationships
when the input exposes them, and optionally copy a completed delivery into an
explicit version directory.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


PROTOCOL_VERSION = "diagram-studio/delivery-1"


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def manifest(directory, names=None):
    directory = Path(directory)
    files = sorted(Path(name) for name in (names or [p.name for p in directory.iterdir() if p.is_file()]))
    return {str(path): sha256_bytes((directory / path).read_bytes()) for path in files}


def _text(value):
    return str(value).strip() if value is not None else ""


def _collect_tree(node, ids, relations, texts):
    if not isinstance(node, dict):
        return
    if node.get("id"):
        ids.add(node["id"])
    for key in ("label", "detail"):
        if _text(node.get(key)):
            texts.add(_text(node[key]))
    for child in node.get("children", []):
        if isinstance(node.get("id"), str) and isinstance(child, dict) and child.get("id"):
            relations.add((node["id"], child["id"]))
        _collect_tree(child, ids, relations, texts)


def expected_content(data):
    """Return stable IDs, relation pairs and required display text from a brief."""
    kind = data.get("type")
    ids, relations, texts = set(), set(), set()
    if kind in {"graph", "architecture"}:
        if kind == "graph":
            for node in data.get("nodes", []):
                if node.get("id"):
                    ids.add(node["id"])
                for key in ("label", "detail"):
                    if _text(node.get(key)):
                        texts.add(_text(node[key]))
            for edge in data.get("edges", []):
                if edge.get("from") and edge.get("to"):
                    relations.add((edge["from"], edge["to"]))
        else:
            for layer in data.get("layers", []):
                for node in layer.get("items", []):
                    if isinstance(node, str):
                        continue
                    if node.get("id"):
                        ids.add(node["id"])
                    for key in ("label", "detail"):
                        if _text(node.get(key)):
                            texts.add(_text(node[key]))
            for edge in data.get("edges", []):
                if edge.get("from") and edge.get("to"):
                    relations.add((edge["from"], edge["to"]))
    elif kind == "tree":
        _collect_tree(data.get("root"), ids, relations, texts)
    elif kind == "sequence":
        for actor in data.get("actors", []):
            actor = {"id": actor, "label": actor} if isinstance(actor, str) else actor
            if actor.get("id"):
                ids.add(actor["id"])
            if _text(actor.get("label")):
                texts.add(_text(actor["label"]))
        for message in data.get("messages", []):
            if message.get("from") and message.get("to"):
                relations.add((message["from"], message["to"]))
            if _text(message.get("label")):
                texts.add(_text(message["label"]))
    elif kind == "gantt":
        for task in data.get("tasks", []):
            if task.get("id"):
                ids.add(task["id"])
            task_text_fields = ("label",) if data.get("gantt_variant") == "executive" else ("label", "owner")
            for key in task_text_fields:
                if _text(task.get(key)):
                    texts.add(_text(task[key]))
            for parent in task.get("depends", []):
                relations.add((parent, task.get("id")))
    elif kind == "storymap":
        for story in data.get("stories", []):
            if story.get("id"):
                ids.add(story["id"])
            for key in ("label", "detail", "source"):
                if _text(story.get(key)):
                    texts.add(_text(story[key]))
    elif kind == "journey":
        for stage in data.get("stages", []):
            if _text(stage.get("id")):
                ids.add(stage["id"])
            for key in ("label", "behavior", "touchpoint"):
                if _text(stage.get(key)):
                    texts.add(_text(stage[key]))
            emotion = stage.get("emotion", {})
            for key in ("label", "basis"):
                if _text(emotion.get(key)):
                    texts.add(_text(emotion[key]))
            for item in stage.get("evidence", []):
                if _text(item.get("id")):
                    ids.add(item["id"])
                for key in ("text", "source"):
                    if _text(item.get(key)):
                        texts.add(_text(item[key]))
            for item in stage.get("opportunities", []):
                if _text(item.get("id")):
                    ids.add(item["id"])
                if _text(item.get("text")):
                    texts.add(_text(item["text"]))
            for item in stage.get("actions", []):
                if _text(item.get("id")):
                    ids.add(item["id"])
                for key in ("text", "owner", "check"):
                    if _text(item.get(key)):
                        texts.add(_text(item[key]))
    elif kind == "service-blueprint":
        item_lookup = {}
        for stage in data.get("stages", []):
            if _text(stage.get("id")):
                ids.add(stage["id"])
            if _text(stage.get("label")):
                texts.add(_text(stage["label"]))
        for lane in data.get("lanes", []):
            if _text(lane.get("id")):
                ids.add(lane["id"])
            if _text(lane.get("label")):
                texts.add(_text(lane["label"]))
            if _text(lane.get("kind")):
                texts.add(_text(lane["kind"]))
            for item in lane.get("items", []):
                if _text(item.get("id")):
                    ids.add(item["id"])
                for key in ("text", "owner"):
                    if _text(item.get(key)):
                        texts.add(_text(item[key]))
                item_lookup[(lane.get("id"), item.get("stage"))] = item.get("id")
        for boundary in data.get("boundaries", []):
            if _text(boundary.get("label")):
                texts.add(_text(boundary["label"]))
        for handoff in data.get("handoffs", []):
            if _text(handoff.get("label")):
                texts.add(_text(handoff["label"]))
            start = handoff.get("from", {})
            end = handoff.get("to", {})
            if item_lookup.get((start.get("lane"), start.get("stage"))) and item_lookup.get((end.get("lane"), end.get("stage"))):
                relations.add(("blueprint-" + item_lookup[(start["lane"], start["stage"])], "blueprint-" + item_lookup[(end["lane"], end["stage"])]))
    elif kind in {"chart", "plot"}:
        rows = data.get("data", [])
        for row in rows:
            if _text(row.get("label")):
                texts.add(_text(row["label"]))
    elif kind == "table":
        for value in data.get("columns", []):
            if _text(value):
                texts.add(_text(value))
        for row in data.get("rows", []):
            values = row.get("cells", row) if isinstance(row, dict) else row
            for value in values:
                if _text(value):
                    texts.add(_text(value))
    elif kind == "fishbone":
        for key in ("title", "subtitle", "effect", "effect_detail", "footer"):
            if _text(data.get(key)):
                texts.add(_text(data[key]))
        for group in data.get("categories", []):
            if _text(group.get("label")):
                texts.add(_text(group["label"]))
            for cause in group.get("causes", []):
                if _text(cause):
                    texts.add(_text(cause))
    elif kind == "quadrant":
        for key in ("title", "subtitle", "x_label", "y_label", "footer"):
            if _text(data.get(key)):
                texts.add(_text(data[key]))
        for label in data.get("quadrants", []):
            if _text(label):
                texts.add(_text(label))
        for item in data.get("items", []):
            if _text(item.get("label")):
                texts.add(_text(item["label"]))
    return {"ids": sorted(ids), "relations": sorted(relations), "texts": sorted(texts)}


def content_integrity(data, scene):
    """Compare source identity/text/relations with a rendered scene manifest."""
    expected = expected_content(data)
    scene_nodes = scene.get("nodes", [])
    scene_ids = {n.get("id") for n in scene_nodes if n.get("id")}
    if data.get("type") == "storymap":
        present_ids = {value[6:] for value in scene_ids if value.startswith("story-")}
    elif data.get("type") == "journey":
        present_ids = {value[len("journey-stage-"):] for value in scene_ids if value.startswith("journey-stage-")}
        scene_blob = "\n".join(_text(n.get("label")) + "\n" + _text(n.get("detail")) for n in scene_nodes)
        present_ids |= set(re.findall(r"\[([A-Za-z][A-Za-z0-9_-]{0,63})\]", scene_blob))
    elif data.get("type") == "service-blueprint":
        present_ids = {value[len("blueprint-stage-"):] for value in scene_ids if value.startswith("blueprint-stage-")}
        present_ids |= {value[len("blueprint-"):] for value in scene_ids if value.startswith("blueprint-") and not value.startswith("blueprint-stage-") and not value.startswith("blueprint-empty-")}
        scene_blob = "\n".join(_text(n.get("label")) + "\n" + _text(n.get("detail")) for n in scene_nodes)
        present_ids |= set(re.findall(r"\[([A-Za-z][A-Za-z0-9_-]{0,63})\]", scene_blob))
    else:
        present_ids = scene_ids
    missing_ids = sorted(set(expected["ids"]) - present_ids)
    scene_relations = {(e.get("source"), e.get("target")) for e in scene.get("edges", []) if e.get("source") and e.get("target")}
    # Sequence messages intentionally use coordinate lifelines rather than node
    # endpoints. Their text remains auditable, while endpoint binding belongs to
    # the sequence-specific backend check.
    missing_relations = [] if data.get("type") == "sequence" else sorted(set(expected["relations"]) - scene_relations)
    scene_text = "\n".join(_text(n.get("label")) + "\n" + _text(n.get("detail")) + "\n" + "\n".join(_text(line[0]) for line in n.get("_lines", [])) for n in scene_nodes)
    scene_text += "\n" + "\n".join(_text(e.get("label")) for e in scene.get("edges", []))
    missing_text = sorted(value for value in expected["texts"] if value not in scene_text)
    applicable = bool(expected["ids"] or expected["relations"] or expected["texts"])
    status = "passed" if not (missing_ids or missing_relations or missing_text) else "failed"
    if not applicable:
        status = "not-applicable"
    return {
        "status": status,
        "source_ids": len(expected["ids"]),
        "source_relations": len(expected["relations"]),
        "source_texts": len(expected["texts"]),
        "missing_ids": missing_ids,
        "missing_relations": [list(pair) for pair in missing_relations],
        "missing_text": missing_text,
        "scope": "stable source IDs, explicit relation endpoints and source display text; not domain correctness",
    }


def make_receipt(raw_input, output_directory, *, source_name, theme, checks, delivery_scope):
    raw = bytes(raw_input)
    input_sha = sha256_bytes(raw)
    return {
        "schema_version": 1,
        "protocol_version": PROTOCOL_VERSION,
        "version_id": "v-" + input_sha[:12],
        "source_name": source_name,
        "input_sha256": input_sha,
        "theme": theme,
        "checks": checks,
        "files": manifest(output_directory),
        "delivery_scope": delivery_scope,
    }


def verify_receipt(receipt_path):
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    root = receipt_path.parent
    missing = []
    changed = []
    for name, digest in receipt.get("files", {}).items():
        path = root / name
        if not path.is_file():
            missing.append(name)
        elif sha256_bytes(path.read_bytes()) != digest:
            changed.append(name)
    if missing or changed:
        raise ValueError(json.dumps({"missing": missing, "changed": changed}, ensure_ascii=False))
    return {"status": "passed", "files": len(receipt.get("files", {})), "version_id": receipt.get("version_id")}


def snapshot(output_directory, receipt_path, version_root):
    """Copy one completed delivery into an explicit, independently reopenable version directory."""
    output_directory = Path(output_directory)
    receipt_path = Path(receipt_path)
    version_root = Path(version_root)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    target = version_root / receipt["version_id"]
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for name in list(receipt.get("files", {})) + [receipt_path.name]:
        source = output_directory / name
        if source.is_file():
            shutil.copy2(source, target / name)
    (target / "version.json").write_text(json.dumps({"version_id": receipt["version_id"], "source_name": receipt.get("source_name"), "input_sha256": receipt.get("input_sha256"), "protocol_version": receipt.get("protocol_version")}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
