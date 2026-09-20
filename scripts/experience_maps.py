#!/usr/bin/env python3
"""Semantic journey-map and service-blueprint builders.

These builders share the local Scene/export contract but keep the two forms
distinct: a journey traces evidence to opportunities and actions, while a
blueprint shows visible and backstage handoffs across explicit lanes.
"""
from __future__ import annotations

import re
from adaptive_layout import METRICS


ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
LANE_TONES = {"customer": "accent", "frontstage": "teal", "backstage": "amber", "support": "muted", "system": "red"}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _word(value, field):
    _need(isinstance(value, str) and value.strip(), field + " must be non-empty text")
    return value.strip()


def _id(value, field):
    _need(isinstance(value, str) and ID_RE.fullmatch(value), field + " must be a stable ASCII id")
    return value


def _lines(value, width, size):
    return max(1, len(METRICS.wrap(str(value), width, size)))


def _height(label, detail, width, minimum=92):
    return max(minimum, 30 + _lines(label, width - 30, 20) * 27 + _lines(detail, width - 30, 16) * 22)


def _card(scene, x, y, width, height, label, detail, ident, tone="accent"):
    lines = [(line, 20, True, "muted") for line in METRICS.wrap(str(label), width - 30, 20)]
    if str(detail).strip():
        lines += [(line, 16, False, "muted") for line in METRICS.wrap(str(detail), width - 30, 16)]
    return scene.add(x, y, width, height, label, detail, id=ident, kind="panel", tone=tone, check=True, text_margin=14, _lines=lines)


def _journey_validate(data):
    _word(data.get("persona"), "persona")
    _word(data.get("goal"), "goal")
    stages = data.get("stages")
    _need(isinstance(stages, list) and 2 <= len(stages) <= 8, "journey stages must contain 2–8 items")
    stage_ids = set(); evidence_ids = set(); opportunity_ids = set(); action_ids = set()
    # Collect every identity before checking references.  This lets a brief
    # cite evidence or an opportunity that appears later in the reading order
    # without making the result depend on JSON ordering.
    for stage in stages:
        for field, bucket in (("evidence", evidence_ids), ("opportunities", opportunity_ids), ("actions", action_ids)):
            values = stage.get(field, [])
            _need(isinstance(values, list), f"stage.{field} must be a list")
            for item in values:
                ident = _id(item.get("id"), f"{field}.id")
                _need(ident not in bucket, f"duplicate {field[:-1]} id: {ident}")
                bucket.add(ident)
    for stage in stages:
        sid = _id(stage.get("id"), "stage.id"); _need(sid not in stage_ids, "duplicate stage id: " + sid); stage_ids.add(sid)
        _word(stage.get("label"), "stage.label"); _word(stage.get("behavior"), "stage.behavior"); _word(stage.get("touchpoint"), "stage.touchpoint")
        for item in stage.get("evidence", []):
            _word(item.get("text"), "evidence.text"); _word(item.get("source"), "evidence.source")
        for item in stage.get("opportunities", []):
            _word(item.get("text"), "opportunity.text")
            refs = item.get("evidence", []); _need(isinstance(refs, list) and refs, "opportunity.evidence must name evidence")
            _need(set(refs) <= evidence_ids, "opportunity references unknown evidence")
        for item in stage.get("actions", []):
            _word(item.get("text"), "action.text"); _word(item.get("owner"), "action.owner"); _word(item.get("check"), "action.check")
            refs = item.get("opportunities", []); _need(isinstance(refs, list) and refs, "action.opportunities must name opportunities")
            _need(set(refs) <= opportunity_ids, "action references unknown opportunity")
        if "emotion" in stage:
            emotion = stage["emotion"]; _need(isinstance(emotion, dict), "emotion must be an object")
            _word(emotion.get("label"), "emotion.label"); _word(emotion.get("basis"), "emotion.basis")
    return {"stage_ids": stage_ids, "evidence_ids": evidence_ids, "opportunity_ids": opportunity_ids, "action_ids": action_ids}


def _journey_text(stage, lane, en=False):
    if lane == "behavior": return stage["behavior"], ""
    if lane == "touchpoint": return stage["touchpoint"], ""
    source, basis, owner, check = ("Source: ", "Evidence: ", "Owner: ", "Check: ") if en else ("来源：", "依据：", "负责人：", "验收：")
    empty = {
        "evidence": "— No observation recorded" if en else "— 未记录观察",
        "opportunity": "— No opportunity proposed" if en else "— 未提出机会",
        "action": "— No action assigned" if en else "— 未安排行动",
    }
    if lane == "evidence": return "\n".join(f"[{v['id']}] {v['text']} · {source}{v['source']}" for v in stage.get("evidence", [])) or empty[lane], ""
    if lane == "opportunity": return "\n".join(f"[{v['id']}] {v['text']} · {basis}{', '.join(v['evidence'])}" for v in stage.get("opportunities", [])) or empty[lane], ""
    if lane == "action": return "\n".join(f"[{v['id']}] {v['text']} · {owner}{v['owner']} · {check}{v['check']}" for v in stage.get("actions", [])) or empty[lane], ""
    emotion = stage.get("emotion")
    return (f"{emotion['label']} · {basis}{emotion['basis']}", "") if emotion else (("— No emotion evidence" if en else "— 未提供情绪证据"), "")


def build_journey(scene, data):
    refs = _journey_validate(data)
    stages = data["stages"]
    en = str(data.get("language", "zh")).lower().startswith("en")
    t = lambda zh, english: english if en else zh
    scene.w = max(scene.w, 128 + 250 + len(stages) * 270)
    left, rail, gap = 64, 238, 14
    colw = (scene.w - 128 - rail) / len(stages)
    cardw = colw - gap
    scene.text(left, 190, scene.w - 128, 34, f"{t('用户：', 'Persona: ')}{data['persona']}  ·  {t('目标：', 'Goal: ')}{data['goal']}", 18, "muted")
    header_y = 236
    header_h = max(86, max(_height(s["label"], "", cardw, 86) for s in stages))
    scene.text(left, header_y + 25, rail - 28, 36, t("阶段 / Stage", "Stage"), 17, "muted")
    coords = {}
    for index, stage in enumerate(stages):
        x = left + rail + index * colw
        _card(scene, x, header_y, cardw, header_h, f"{index + 1:02d} / {stage['id']}", stage["label"], f"journey-stage-{stage['id']}", "accent" if index == 0 else "teal")
        coords[stage["id"]] = {"x": x, "center": x + cardw / 2}
    lanes = [("behavior", t("用户行为 / Behavior", "Behavior"), "accent"), ("touchpoint", t("触点 / Touchpoint", "Touchpoint"), "teal"), ("evidence", t("观察与来源 / Evidence", "Evidence & source"), "muted"), ("opportunity", t("机会假说 / Opportunity", "Opportunity"), "amber"), ("action", t("拟议行动 / Action", "Action"), "red")]
    if any("emotion" in s for s in stages):
        lanes.append(("emotion", t("体验感受 / Emotion", "Emotion"), "teal"))
    y = header_y + header_h + 18
    placements = []
    for lane_id, lane_label, tone in lanes:
        values = [_journey_text(stage, lane_id, en) for stage in stages]
        row_h = max(100, max(_height(label, detail, cardw) for label, detail in values))
        scene.text(left, y + 20, rail - 28, row_h - 28, lane_label, 17, "muted")
        for index, (label, detail) in enumerate(values):
            stage = stages[index]; x = left + rail + index * colw
            placements.append(_card(scene, x, y, cardw, row_h, label, detail, f"journey-{lane_id}-{stage['id']}", tone))
        y += row_h + 12
    scene.text(left, y + 4, scene.w - 128, 34, t("证据先于机会，机会先于行动；空位表示尚未提出，不表示没有问题。", "Evidence precedes opportunity, and opportunity precedes action; an empty cell means no proposal yet, not no problem."), 15, "muted")
    scene.meta["experience_map"] = "journey"
    scene.meta["journey"] = {"stages": [s["id"] for s in stages], "stable_ids": sorted(refs["stage_ids"] | refs["evidence_ids"] | refs["opportunity_ids"] | refs["action_ids"]), "lanes": [v[0] for v in lanes], "trace_counts": {"evidence": len(refs["evidence_ids"]), "opportunities": len(refs["opportunity_ids"]), "actions": len(refs["action_ids"])}}


def _blueprint_validate(data):
    _word(data.get("customer"), "customer"); _word(data.get("goal"), "goal")
    stages = data.get("stages"); _need(isinstance(stages, list) and 2 <= len(stages) <= 8, "blueprint stages must contain 2–8 items")
    stage_ids = set()
    for stage in stages:
        sid = _id(stage.get("id"), "stage.id"); _need(sid not in stage_ids, "duplicate stage id: " + sid); stage_ids.add(sid); _word(stage.get("label"), "stage.label")
    lanes = data.get("lanes"); _need(isinstance(lanes, list) and 3 <= len(lanes) <= 6, "blueprint lanes must contain 3–6 items")
    lane_ids = set(); item_ids = set(); item_lookup = {}
    for lane in lanes:
        lid = _id(lane.get("id"), "lane.id"); _need(lid not in lane_ids, "duplicate lane id: " + lid); lane_ids.add(lid)
        _word(lane.get("label"), "lane.label"); _need(lane.get("kind") in LANE_TONES, "unsupported lane kind: " + str(lane.get("kind")))
        for item in lane.get("items", []):
            ident = _id(item.get("id"), "item.id"); _need(ident not in item_ids, "duplicate item id: " + ident); item_ids.add(ident)
            _need(item.get("stage") in stage_ids, "item references unknown stage")
            _word(item.get("text"), "item.text")
            if item.get("owner") is not None: _word(item.get("owner"), "item.owner")
            item_lookup[(lid, item["stage"])] = ident
    for boundary in data.get("boundaries", []):
        _need(boundary.get("after") in lane_ids and boundary.get("before") in lane_ids, "boundary references unknown lane")
        _word(boundary.get("label"), "boundary.label")
    for handoff in data.get("handoffs", []):
        for key in ("from", "to"):
            point = handoff.get(key); _need(isinstance(point, dict) and point.get("lane") in lane_ids and point.get("stage") in stage_ids, "handoff point is invalid")
            _need((point.get("lane"), point.get("stage")) in item_lookup, "handoff point has no item")
        _word(handoff.get("label"), "handoff.label")
    return {"stage_ids": stage_ids, "lane_ids": lane_ids, "item_ids": item_ids, "item_lookup": item_lookup}


def build_blueprint(scene, data):
    refs = _blueprint_validate(data)
    stages, lanes = data["stages"], data["lanes"]
    en = str(data.get("language", "zh")).lower().startswith("en")
    t = lambda zh, english: english if en else zh
    scene.w = max(scene.w, 128 + 270 + len(stages) * 248)
    left, rail, gap = 64, 260, 12
    colw = (scene.w - 128 - rail) / len(stages); cardw = colw - gap
    scene.text(left, 190, scene.w - 128, 34, f"{t('用户：', 'Customer: ')}{data['customer']}  ·  {t('目标：', 'Goal: ')}{data['goal']}", 18, "muted")
    header_y, header_h = 234, 76
    scene.text(left, header_y + 22, rail - 26, 36, t("服务阶段 / Stage", "Service stage"), 17, "muted")
    row_tops = []; row_heights = []
    for index, stage in enumerate(stages):
        x = left + rail + index * colw
        _card(scene, x, header_y, cardw, header_h, f"{index + 1:02d} / {stage['id']}", stage["label"], f"blueprint-stage-{stage['id']}", "accent" if index == 0 else "teal")
    y = header_y + header_h + 16; boxes = {}
    lane_order = {lane["id"]: index for index, lane in enumerate(lanes)}
    owner_prefix = "Owner: " if en else "负责人："
    empty_label = "— Not recorded" if en else "— 未记录"
    for lane in lanes:
        by_stage = {(item["stage"]): item for item in lane.get("items", [])}
        values = []
        for stage in stages:
            item = by_stage.get(stage["id"])
            if item:
                detail = (owner_prefix + item["owner"]) if item.get("owner") else ""
                values.append((f"[{item['id']}] {item['text']}", detail))
            else:
                values.append((empty_label, ""))
        row_h = max(112, max(_height(label, detail, cardw) for label, detail in values))
        tone = LANE_TONES[lane["kind"]]
        scene.text(left, y + 20, rail - 26, row_h - 28, f"{lane['label']}\n[{lane['id']}] · {lane['kind']}", 17, "muted")
        row_tops.append(y); row_heights.append(row_h)
        for index, (label, detail) in enumerate(values):
            stage = stages[index]; x = left + rail + index * colw; ident = by_stage.get(stage["id"], {}).get("id", f"empty-{lane['id']}-{stage['id']}")
            cell_id = f"blueprint-{ident}"; _card(scene, x, y, cardw, row_h, label, detail, cell_id, tone); boxes[(lane["id"], stage["id"])] = cell_id
        y += row_h + 10
    for boundary in data.get("boundaries", []):
        before = next(i for i, lane in enumerate(lanes) if lane["id"] == boundary["before"]); after = next(i for i, lane in enumerate(lanes) if lane["id"] == boundary["after"])
        _need(before == after + 1, "boundary lanes must be adjacent in reading order")
        boundary_y = row_tops[before] - 5
        scene.edge(points=[(left, boundary_y - 5), (scene.w - 64, boundary_y - 5)], arrow=False, tone="ink", width=2)
        scene.text(left, boundary_y - 34, rail - 26, 28, boundary["label"], 14, "accent")
    for handoff in data.get("handoffs", []):
        source = boxes[(handoff["from"]["lane"], handoff["from"]["stage"])]
        target = boxes[(handoff["to"]["lane"], handoff["to"]["stage"])]
        same_stage = handoff["from"]["stage"] == handoff["to"]["stage"]
        skipped_lane = abs(lane_order[handoff["from"]["lane"]] - lane_order[handoff["to"]["lane"]]) > 1
        ports = {"source_port": "left", "target_port": "left"} if same_stage and skipped_lane else {}
        scene.edge(source, target, handoff["label"], tone="accent", width=1.5, arrow=True, **ports)
    scene.text(left, y + 4, scene.w - 128, 34, t("分界线承载服务语义；交接箭头只表示输入中声明的协作，不从相邻位置推断。", "Boundaries carry service semantics; handoff arrows show declared collaboration only and are never inferred from adjacency."), 15, "muted")
    scene.meta["experience_map"] = "service-blueprint"
    scene.meta["service_blueprint"] = {"stages": [s["id"] for s in stages], "lanes": [lane["id"] for lane in lanes], "boundaries": [b["label"] for b in data.get("boundaries", [])], "handoffs": len(data.get("handoffs", [])), "stable_ids": sorted(refs["stage_ids"] | refs["lane_ids"] | refs["item_ids"])}


BUILDERS = {"journey": build_journey, "service-blueprint": build_blueprint}
