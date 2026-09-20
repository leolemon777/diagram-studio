#!/usr/bin/env python3
"""Validate and inspect the Diagram Studio capability registry.

The JSON file is the source of truth for the chooser's form labels, input model,
backend, formats, limits, languages, examples and acceptance evidence.  This
module deliberately validates references without importing rendering backends,
so a clean install can check the registry before optional plotting dependencies.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "assets" / "capability-registry.json"
LANGUAGES = {"zh", "en"}
EVIDENCE_LEVELS = {
    "manual_visual_review",
    "rendered_visual_check",
    "generated_with_semantic_validation",
    "example_available",
    "planned",
}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _pair(value, field, path):
    _need(isinstance(value, dict) and set(value) == LANGUAGES, f"{path}.{field} must have zh and en")
    _need(all(isinstance(v, str) and v.strip() for v in value.values()), f"{path}.{field} labels must be non-empty")


def validate(data, root=ROOT):
    _need(isinstance(data, dict), "registry must be an object")
    _need(data.get("schema_version") == "1.0", "unsupported capability registry schema")
    _need(isinstance(data.get("version"), str) and data["version"], "registry version required")
    groups = data.get("groups")
    _need(isinstance(groups, list) and groups, "registry groups must be non-empty")
    group_ids = set()
    type_ids = set()
    for gi, group in enumerate(groups):
        gp = f"groups[{gi}]"
        _need(isinstance(group, dict), f"{gp} must be an object")
        gid = group.get("id")
        _need(isinstance(gid, str) and gid, f"{gp}.id required")
        _need(gid not in group_ids, f"duplicate group id: {gid}")
        group_ids.add(gid)
        _pair(group.get("label"), "label", gp)
        _pair(group.get("sub"), "sub", gp)
        types = group.get("types")
        _need(isinstance(types, list) and types, f"{gp}.types must be non-empty")
        for ti, capability in enumerate(types):
            path = f"{gp}.types[{ti}]"
            _need(isinstance(capability, dict), f"{path} must be an object")
            cid = capability.get("id")
            _need(isinstance(cid, str) and cid, f"{path}.id required")
            _need(cid not in type_ids, f"duplicate capability id: {cid}")
            type_ids.add(cid)
            for field in ("label", "why", "minimum_input", "layout_limits", "scope"):
                _pair(capability.get(field), field, path)
            model = capability.get("input_model")
            _need(isinstance(model, dict) and isinstance(model.get("kind"), str), f"{path}.input_model is incomplete")
            _need(isinstance(capability.get("backend"), dict), f"{path}.backend is required")
            backend = capability["backend"]
            _need(all(isinstance(backend.get(k), str) and backend[k] for k in ("kind", "module", "entry")), f"{path}.backend is incomplete")
            module = root / backend["module"]
            _need(module.is_file(), f"{path}.backend.module does not exist: {backend['module']}")
            formats = capability.get("formats")
            _need(isinstance(formats, list) and formats and all(isinstance(v, str) and v for v in formats), f"{path}.formats is incomplete")
            languages = capability.get("languages")
            _need(isinstance(languages, list) and set(languages) <= LANGUAGES and languages, f"{path}.languages is invalid")
            examples = capability.get("examples")
            _need(isinstance(examples, list) and examples, f"{path}.examples is empty")
            for example in examples:
                _need(isinstance(example, str) and (root / example).is_file(), f"{path} example does not exist: {example}")
            evidence = capability.get("evidence")
            _need(isinstance(evidence, dict) and evidence.get("level") in EVIDENCE_LEVELS, f"{path}.evidence.level is invalid")
            reference = evidence.get("reference")
            _need(isinstance(reference, str) and (root / reference).is_file(), f"{path} evidence reference does not exist: {reference}")
            _pair(evidence.get("detail"), "evidence.detail", path)
    aliases = data.get("aliases", {})
    _need(isinstance(aliases, dict), "aliases must be an object")
    for alias, target in aliases.items():
        _need(isinstance(alias, str) and isinstance(target, str) and target in type_ids, f"alias points to unknown capability: {alias}")
    return data


def load(path=DEFAULT_PATH):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate(data, path.parents[1] if path.parent.name == "assets" else ROOT)


def capabilities(data):
    return [capability for group in data["groups"] for capability in group["types"]]


def find(data, identifier):
    target = data.get("aliases", {}).get(identifier, identifier)
    for capability in capabilities(data):
        if capability["id"] == target:
            return capability
    raise KeyError(identifier)


def markdown(data):
    lines = [
        "# 能力登记与交付范围",
        "",
        f"机器可读源：`assets/capability-registry.json`（{data['version']}）。运行 `python3 scripts/capability_registry.py --check` 校验引用。",
        "",
        "选图向导从同一份登记读取结构、后端、格式和验收状态；本表只列当前可追查的高频入口，不把入口数量当作完成率。",
        "",
        "| ID | 图型 | 后端 | 格式 | 证据级别 |",
        "|---|---|---|---|---|",
    ]
    for group in data["groups"]:
        for capability in group["types"]:
            lines.append(
                "| `{id}` | {label} | `{module}#{entry}` | {formats} | `{level}` |".format(
                    id=capability["id"],
                    label=capability["label"]["zh"],
                    module=capability["backend"]["module"],
                    entry=capability["backend"]["entry"],
                    formats=", ".join(capability["formats"]),
                    level=capability["evidence"]["level"],
                )
            )
    lines += [
        "",
        "证据级别只说明已执行的检查：`manual_visual_review` 仍不等于领域或用户批准；`planned` 入口不能直接宣称已实现。格式列表是该后端登记的交付协议，生成后仍需按项目实际检查。",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--check", action="store_true", help="validate the registry and referenced files")
    parser.add_argument("--id", help="print one capability as JSON")
    parser.add_argument("--markdown", action="store_true", help="print the concise capability table")
    args = parser.parse_args(argv)
    data = load(args.path)
    if args.id:
        print(json.dumps(find(data, args.id), ensure_ascii=False, indent=2))
    elif args.markdown:
        print(markdown(data), end="")
    else:
        print(json.dumps({"version": data["version"], "groups": len(data["groups"]), "capabilities": len(capabilities(data))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
