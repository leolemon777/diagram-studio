"""Evidence-aware user-path storyboard builder.

This is intentionally different from a user story map: it follows one path
through visible states, keeps explicit next-step/branch/exception semantics,
and marks unverified branches as proposals.  Every source object becomes an
editable draw.io/SVG node with its stable id.
"""
from __future__ import annotations

import re

from adaptive_layout import METRICS


ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value, field):
    _need(isinstance(value, str) and value.strip(), field + " must be non-empty text")
    return value.strip()


def _id(value, field):
    _need(isinstance(value, str) and ID_RE.fullmatch(value), field + " must be a stable ASCII id")
    return value


def _bool(value, field):
    _need(isinstance(value, bool), field + " must be boolean")
    return value


def _lines(value, width, size):
    return max(1, len(METRICS.wrap(str(value), width, size)))


def _card(scene, x, y, width, height, label, detail, ident, tone="accent", *, kind="panel", check=True):
    lines = [(line, 20, True, "ink") for line in METRICS.wrap(str(label), width - 30, 20)]
    if str(detail).strip():
        lines += [(line, 15, False, "muted") for line in METRICS.wrap(str(detail), width - 30, 15)]
    return scene.add(x, y, width, height, label, detail, id=ident, kind=kind, tone=tone, check=check, text_margin=14, _lines=lines)


def validate(data):
    _text(data.get("persona"), "persona")
    _text(data.get("goal"), "goal")
    preconditions = data.get("preconditions")
    _need(isinstance(preconditions, list) and 1 <= len(preconditions) <= 6, "user-path storyboard needs 1–6 preconditions")
    pre_ids = set()
    for row in preconditions:
        ident = _id(row.get("id"), "precondition.id")
        _need(ident not in pre_ids, "duplicate precondition id: " + ident)
        pre_ids.add(ident)
        _text(row.get("text"), "precondition.text")
        if "status" in row:
            _text(row.get("status"), "precondition.status")

    states = data.get("states")
    _need(isinstance(states, list) and 2 <= len(states) <= 8, "user-path storyboard needs 2–8 states")
    state_ids = set()
    for row in states:
        ident = _id(row.get("id"), "state.id")
        _need(ident not in state_ids, "duplicate state id: " + ident)
        state_ids.add(ident)
        _text(row.get("label"), "state.label")
        _text(row.get("detail", row.get("label")), "state.detail")

    steps = data.get("steps")
    _need(isinstance(steps, list) and 4 <= len(steps) <= 12, "user-path storyboard needs 4–12 steps")
    step_ids = set(); step_numbers = set()
    for index, row in enumerate(steps, 1):
        ident = _id(row.get("id"), "step.id")
        _need(ident not in step_ids, "duplicate step id: " + ident)
        step_ids.add(ident)
        _need(row.get("number") == index, "step numbers must be contiguous")
        step_numbers.add(row["number"])
        _need(row.get("state") in state_ids, "step references unknown state")
        _text(row.get("actor"), "step.actor")
        _text(row.get("action"), "step.action")
        _text(row.get("result"), "step.result")
        next_id = row.get("next")
        _need(next_id is None or next_id in step_ids or next_id in {s.get("id") for s in steps}, "step.next references unknown step")
        _bool(row.get("proposal", False), "step.proposal")

    branches = data.get("branches", [])
    exceptions = data.get("exceptions", [])
    _need(isinstance(branches, list) and len(branches) <= 16, "branches must contain at most 16 items")
    _need(isinstance(exceptions, list) and len(exceptions) <= 16, "exceptions must contain at most 16 items")
    path_ids = set(step_ids)
    relation_ids = set()
    for kind, rows in (("branch", branches), ("exception", exceptions)):
        for row in rows:
            ident = _id(row.get("id"), f"{kind}.id")
            _need(ident not in relation_ids, "duplicate path relation id: " + ident)
            relation_ids.add(ident)
            _need(row.get("from") in step_ids and row.get("to") in step_ids, f"{kind} endpoints must reference steps")
            _text(row.get("label"), f"{kind}.label")
            _text(row.get("condition"), f"{kind}.condition")
            if kind == "exception":
                _text(row.get("recovery", row.get("to")), "exception.recovery")
            _bool(row.get("proposal", False), f"{kind}.proposal")
            path_ids.add(ident)
    _need(not (pre_ids & state_ids or pre_ids & step_ids or state_ids & step_ids or (pre_ids | state_ids | step_ids) & relation_ids), "all storyboard ids must be globally unique")
    outgoing = {row["id"]: 0 for row in steps}
    for row in steps:
        if row.get("next"):
            outgoing[row["id"]] += 1
    for row in branches + exceptions:
        outgoing[row["from"]] += 1
    for row in steps[:-1]:
        _need(outgoing[row["id"]] > 0, "every non-final step needs a next step, branch, or exception")
    _need(steps[-1].get("next") in (None, ""), "final step must not have a next step")
    _need(all(state_id in {row["state"] for row in steps} for state_id in state_ids), "every state must be used by a step")
    return {"pre_ids": pre_ids, "state_ids": state_ids, "step_ids": step_ids, "relation_ids": relation_ids}


def _copy(data, key, en):
    if key in data and isinstance(data[key], str):
        return data[key]
    defaults = {
        "preconditions": ("前置条件 / Preconditions", "Preconditions"),
        "path": ("主路径 / Main path", "Main path"),
        "branch": ("分支 / Branch", "Branch"),
        "exception": ("异常 / Exception", "Exception"),
        "proposal": ("拟议 · 待验证", "Proposed · validate"),
        "observed": ("已观察", "Observed"),
    }
    return defaults[key][1 if en else 0]


def build(scene, data):
    refs = validate(data)
    en = str(data.get("language", "zh")).lower().startswith("en")
    t = lambda zh, english: english if en else zh
    steps = data["steps"]; states = {row["id"]: row for row in data["states"]}
    # A horizontal path is intentionally allowed to grow: shrinking step cards
    # would hide action/result text and make the branch semantics ambiguous.
    left, gap, cardw = 64, 26, 250
    scene.w = max(scene.w, left * 2 + len(steps) * cardw + (len(steps) - 1) * gap)
    scene.text(left, 188, scene.w - 128, 32, t("用户：", "Persona: ") + data["persona"] + "  ·  " + t("目标：", "Goal: ") + data["goal"], 18, "muted")
    pre_y = 232
    pre_w = max(230, (scene.w - 128 - (len(data["preconditions"]) - 1) * 14) / len(data["preconditions"]))
    scene.text(left, pre_y - 25, 260, 50, _copy(data, "preconditions", en), 16, "accent")
    for index, row in enumerate(data["preconditions"]):
        x = left + index * (pre_w + 14)
        detail = row.get("status", t("待确认", "To confirm"))
        _card(scene, x, pre_y, pre_w, 68, f"[{row['id']}] {row['text']}", detail, row["id"], "teal", kind="panel", check=False)

    state_y = 316
    state_w = max(210, (scene.w - 128 - (len(states) - 1) * 12) / len(states))
    for index, state in enumerate(data["states"]):
        x = left + index * (state_w + 12)
        _card(scene, x, state_y, state_w, 72, f"[{state['id']}] {state['label']}", state["detail"], state["id"], "muted", kind="panel", check=False)

    # Leave a real reading gap after the state strip.  The state detail is
    # semantic content, so the main-path heading must never sit on top of it.
    main_y = 430
    step_heights=[]
    for row in steps:
        state = states[row["state"]]
        content = [f"{row['number']:02d} · {state['label']}", row["actor"], row["action"], t("结果：", "Result: ") + row["result"]]
        required = 30 + sum(_lines(value, cardw - 30, 15 if i else 18) * (22 if i == 0 else 20) for i, value in enumerate(content)) + 26
        step_heights.append(max(154, required))
    main_h = max(step_heights)
    scene.text(left, main_y - 30, 280, 52, _copy(data, "path", en), 16, "accent")
    positions = {}
    for index, row in enumerate(steps):
        x = left + index * (cardw + gap)
        state = states[row["state"]]
        proposal = t(" · 拟议", " · Proposed") if row.get("proposal") else ""
        label = f"{row['number']:02d} · {state['label']}{proposal}"
        detail = f"[{row['id']}] {row['actor']}\n{row['action']}\n{t('结果：', 'Result: ')}{row['result']}"
        tone = "accent" if index == 0 else ("amber" if row.get("proposal") else "teal")
        _card(scene, x, main_y, cardw, main_h, label, detail, row["id"], tone)
        positions[row["id"]] = (x, main_y, cardw, main_h)
    # Main path edges are always explicit.  A backward link is drawn under the
    # row so the return semantics remain visible instead of being hidden in a
    # generic arrow.
    for index, row in enumerate(steps):
        target = row.get("next")
        if not target:
            continue
        x, y, w, h = positions[row["id"]]; tx, ty, tw, th = positions[target]
        if tx > x:
            scene.edge(row["id"], target, t("下一步", "Next"), tone="accent", width=1.7)
        else:
            low = main_y + main_h + 30 + index * 12
            scene.edge(points=[(x + w / 2, y + h), (x + w / 2, low), (tx + tw / 2, low), (tx + tw / 2, ty + th)], label=t("返回", "Return"), label_at=[(x + tx + w) / 2, low - 16], tone="red", dashed=True, width=1.5)

    branch_rows = []
    for kind, rows in (("branch", data.get("branches", [])), ("exception", data.get("exceptions", []))):
        for row in rows:
            branch_rows.append((kind, row))
    branch_y = main_y + main_h + 105
    if branch_rows:
        scene.text(left, branch_y - 28, 300, 50, t("分支与异常 / Branches & exceptions", "Branches & exceptions"), 16, "accent")
    relation_w = 310
    for index, (kind, row) in enumerate(branch_rows):
        x = left + (index % max(1, int((scene.w - 128) // (relation_w + 20)))) * (relation_w + 20)
        y = branch_y + (index // max(1, int((scene.w - 128) // (relation_w + 20)))) * 150
        proposal = t(" · 拟议", " · Proposed") if row.get("proposal") else ""
        prefix = _copy(data, kind, en)
        label = f"[{row['id']}] {prefix}{proposal}"
        detail = f"{row['label']} · {t('条件：', 'When: ')}{row['condition']}"
        if kind == "exception":
            detail += " · " + t("恢复：", "Recovery: ") + row.get("recovery", row["to"])
        rel_id = row["id"]
        relation_height = max(112, 32 + (_lines(label, relation_w - 30, 20) * 27) + (_lines(detail, relation_w - 30, 15) * 22))
        _card(scene, x, y, relation_w, relation_height, label, detail, rel_id, "red" if kind == "exception" else "amber", check=False)
        source_x, source_y, source_w, source_h = positions[row["from"]]
        target_x, target_y, target_w, target_h = positions[row["to"]]
        scene.edge(row["from"], row["to"], points=[
            (source_x + source_w / 2, source_y + source_h),
            (source_x + source_w / 2, y - 9),
            (x + relation_w / 2, y - 9),
            (x + relation_w / 2, y + relation_height + 16),
            (target_x + target_w / 2, y + relation_height + 16),
            (target_x + target_w / 2, target_y + target_h),
        ], label=prefix, label_at=[source_x + source_w / 2 + 12, y - 28], tone="red" if kind == "exception" else "amber", dashed=bool(row.get("proposal")), width=1.4)
    max_relation_y = branch_y + ((len(branch_rows) - 1) // max(1, int((scene.w - 128) // (relation_w + 20))) + 1) * 150 if branch_rows else branch_y
    scene.text(left, max_relation_y + 8, scene.w - 128, 44, t("虚线与“拟议”只表示待验证路径；状态、分支和异常均来自输入，不从相邻位置推断。", "Dashed and proposed paths are unverified; states, branches and exceptions come from the input and are never inferred from proximity."), 15, "muted")
    scene.h = max(scene.h, max_relation_y + 100)
    scene.meta["user_path_storyboard"] = {
        "preconditions": sorted(refs["pre_ids"]),
        "states": sorted(refs["state_ids"]),
        "steps": [row["id"] for row in steps],
        "branches": [row["id"] for row in data.get("branches", [])],
        "exceptions": [row["id"] for row in data.get("exceptions", [])],
        "stable_ids": sorted(refs["pre_ids"] | refs["state_ids"] | refs["step_ids"] | refs["relation_ids"]),
        "proposal_count": sum(bool(row.get("proposal")) for row in steps + data.get("branches", []) + data.get("exceptions", [])),
    }


BUILDERS = {"user-path-storyboard": build}
