"""Render a validated UML activity subset as SVG and grouped draw.io source."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as E

from activity_model import validate
from render import Scene, audit, drawio, port, svg


NS = "http://www.w3.org/2000/svg"
CANVAS_W = 1600
CANVAS_H = 1220
LANE_X = 70
LANE_Y = 195
LANE_GAP = 12
LANE_H = 940
ROW_Y = 255
ROW_GAP = 56


def geometry_for(node, lane):
    center_x = lane["x"] + lane["w"] / 2
    center_y = ROW_Y + node["row"] * ROW_GAP
    kind = node["kind"]
    if kind == "action":
        w, h = 260, 44
    elif kind == "object":
        w, h = 210, 42
    elif kind in ("fork", "join"):
        w, h = 150, 10
    elif kind in ("decision", "merge"):
        w = h = 36
    else:
        w = h = 28
    return center_x - w / 2, center_y - h / 2, w, h


def route(source, target, source_node, target_node):
    source_lane = source_node["partition_order"]
    target_lane = target_node["partition_order"]
    if target_node["row"] < source_node["row"]:
        start = port(source, "right")
        end = port(target, "right")
        outside = CANVAS_W - 40
        return [start, (outside, start[1]), (outside, end[1]), end], "right", "right", [CANVAS_W - 92, (start[1] + end[1]) / 2]
    if source_lane == target_lane:
        return [port(source, "bottom"), port(target, "top")], "bottom", "top", None
    if target_lane > source_lane:
        start = port(source, "right")
        end = port(target, "left")
    else:
        start = port(source, "left")
        end = port(target, "right")
    middle = (start[0] + end[0]) / 2
    return [start, (middle, start[1]), (middle, end[1]), end], ("right" if target_lane > source_lane else "left"), ("left" if target_lane > source_lane else "right"), None


def build(document):
    model = validate(document)
    lane_w = (CANVAS_W - 2 * LANE_X - (len(model["partitions"]) - 1) * LANE_GAP) / len(model["partitions"])
    scene = Scene(
        {
            "width": CANVAS_W,
            "height": CANVAS_H,
            "title": model["title"],
            "subtitle": model["scope"],
            "eyebrow": "UML / ACTIVITY",
            "footer": "教学子集；泳道不改变令牌流。符号与关系按UML 2.5.1第15章核对。",
        },
        "editorial-warm",
    )

    lanes = {}
    lane_ids = {}
    for partition in model["partitions"]:
        x = LANE_X + partition["order"] * (lane_w + LANE_GAP)
        lane_id = "partition_" + partition["id"]
        scene.add(x, LANE_Y, lane_w, LANE_H, partition["name"], kind="panel", tone="muted", fill="bg", id=lane_id, check=False)
        lanes[partition["id"]] = {"x": x, "y": LANE_Y, "w": lane_w, "h": LANE_H, "order": partition["order"]}
        lane_ids[partition["id"]] = lane_id

    node_ids = {}
    semantic_nodes = {}
    child_owner = {}
    object_nodes = set()
    activity_finals = set()
    open_labels = {}
    for node in model["nodes"]:
        lane = lanes[node["partition"]]
        x, y, w, h = geometry_for(node, lane)
        node_id = "node_" + node["id"]
        kind = node["kind"]
        label = node["name"] if kind in ("action", "object") else "×" if kind == "flow_final" else ""
        shape = "rect"
        tone = "ink"
        options = {"check": True}
        if kind == "action":
            options.update(radius=11, fill="panel", stroke="ink")
        elif kind == "object":
            options.update(radius=0, fill="panel", stroke="teal")
            object_nodes.add(node_id)
        elif kind in ("decision", "merge"):
            shape = "diamond"
            options.update(fill="bg", stroke="ink")
        elif kind in ("fork", "join"):
            options.update(radius=0, fill="ink", stroke="ink")
        elif kind == "initial":
            shape = "ellipse"
            options.update(fill="ink", stroke="ink")
        elif kind == "activity_final":
            shape = "ellipse"
            options.update(fill="bg", stroke="ink", stroke_width=2)
            activity_finals.add(node_id)
        else:
            shape = "ellipse"
            options.update(fill="bg", stroke="ink", stroke_width=2, fs=22)
        scene.add(x, y, w, h, label, kind=shape, tone=tone, id=node_id, **options)
        node_ids[node["id"]] = node_id
        semantic_nodes[node["id"]] = {**scene.get(node_id), **node, "partition_order": lane["order"]}
        child_owner[node_id] = lane_ids[node["partition"]]
        if kind == "activity_final":
            inner_id = "glyph_" + node["id"] + "_inner"
            scene.add(x + 7, y + 7, w - 14, h - 14, kind="ellipse", tone="ink", fill="ink", stroke="ink", id=inner_id, check=False)
            child_owner[inner_id] = node_id
        if kind in ("initial", "activity_final", "flow_final"):
            label_x = x + w + 9
            label_y = y + h / 2 - 11
            label_w = min(125, lane["x"] + lane["w"] - label_x - 8)
            if label_w < 52:
                label_x = x - 126
                label_w = 118
            label_id = "label_" + node["id"]
            scene.text(label_x, label_y, label_w, 22, node["name"], 13, "muted", id=label_id)
            child_owner[label_id] = lane_ids[node["partition"]]
            open_labels[node_id] = label_id

    for edge in model["edges"]:
        source_id = node_ids[edge["source"]]
        target_id = node_ids[edge["target"]]
        source = scene.get(source_id)
        target = scene.get(target_id)
        points, source_port, target_port, label_at = route(source, target, semantic_nodes[edge["source"]], semantic_nodes[edge["target"]])
        label = "[" + edge["guard"] + "]" if "guard" in edge else edge.get("label", "")
        tone = "teal" if edge["kind"] == "object" else "muted"
        scene.edge(
            source_id,
            target_id,
            label,
            points=points,
            source_port=source_port,
            target_port=target_port,
            tone=tone,
            arrow="open",
            width=2.2 if edge["kind"] == "object" else 2,
            label_at=label_at,
        )

    scene.meta = {
        "model": model,
        "lane_ids": lane_ids,
        "node_ids": node_ids,
        "child_owner": child_owner,
        "object_nodes": sorted(object_nodes),
        "activity_finals": sorted(activity_finals),
        "open_labels": open_labels,
    }
    scene.finish()
    qa = audit(scene)
    if qa["errors"] or qa["warnings"]:
        raise ValueError(str(qa))
    return scene, qa


def exports(scene):
    svg_root = E.fromstring(svg(scene))
    ns = "{" + NS + "}"
    defs = svg_root.find(ns + "defs")
    for tone in ("muted", "teal"):
        marker = E.SubElement(
            defs,
            ns + "marker",
            id="arrow-open-" + tone,
            viewBox="0 0 10 10",
            refX="9",
            refY="5",
            markerWidth="7",
            markerHeight="7",
            orient="auto-start-reverse",
        )
        E.SubElement(marker, ns + "path", d="M 0 0 L 10 5 L 0 10", fill="none", stroke=scene.palette[tone], **{"stroke-width": "1.5"})
    drawing_group = svg_root.find(ns + "g")
    edge_paths = [child for child in list(drawing_group) if child.tag == ns + "path" and child.get("fill") == "none"]
    if len(edge_paths) != len(scene.edges):
        raise ValueError("could not map SVG activity edges")
    for edge, path in zip(scene.edges, edge_paths):
        path.set("marker-end", "url(#arrow-open-" + edge.get("tone", "muted") + ")")
    for node_id in scene.meta["object_nodes"]:
        group = svg_root.find(".//" + ns + "g[@id='" + node_id + "']")
        text_element = group.find(ns + "text")
        if text_element is not None:
            text_element.set("text-decoration", "underline")
    E.register_namespace("", NS)
    svg_text = E.tostring(svg_root, encoding="unicode")

    drawio_root = E.fromstring(drawio(scene))
    cells = {cell.get("id"): cell for cell in drawio_root.iter("mxCell")}
    for lane_id in scene.meta["lane_ids"].values():
        cell = cells[lane_id]
        cell.set("style", cell.get("style", "") + "shape=swimlane;horizontal=1;startSize=42;container=1;collapsible=0;recursiveResize=0;")
    # Nest the bullseye before moving the semantic node into its lane.
    for final_id in scene.meta["activity_finals"]:
        inner_id = "glyph_" + final_id.removeprefix("node_") + "_inner"
        inner = cells[inner_id]
        outer_geometry = cells[final_id].find("mxGeometry")
        geometry = inner.find("mxGeometry")
        inner.set("parent", final_id)
        geometry.set("x", str(float(geometry.get("x")) - float(outer_geometry.get("x"))))
        geometry.set("y", str(float(geometry.get("y")) - float(outer_geometry.get("y"))))
    for child_id, owner_id in scene.meta["child_owner"].items():
        if child_id.startswith("glyph_"):
            continue
        child = cells[child_id]
        owner_geometry = cells[owner_id].find("mxGeometry")
        geometry = child.find("mxGeometry")
        child.set("parent", owner_id)
        geometry.set("x", str(float(geometry.get("x")) - float(owner_geometry.get("x"))))
        geometry.set("y", str(float(geometry.get("y")) - float(owner_geometry.get("y"))))
    for node_id in scene.meta["object_nodes"]:
        cell = cells[node_id]
        cell.set("value", "<u>" + cell.get("value", "") + "</u>")
        cell.set("style", cell.get("style", "") + "fontStyle=4;")
    for final_id in scene.meta["activity_finals"]:
        cells[final_id].set("style", cells[final_id].get("style", "") + "shape=ellipse;")
    edge_cells = [cell for cell in drawio_root.iter("mxCell") if cell.get("edge") == "1"]
    if len(edge_cells) != len(scene.edges):
        raise ValueError("could not map draw.io activity edges")
    for cell in edge_cells:
        cell.set("style", cell.get("style", "").replace("endArrow=block;", "endArrow=open;endFill=0;"))
    return svg_text, E.tostring(drawio_root, encoding="unicode")


def render_file(source, output):
    source = Path(source)
    document = json.loads(source.read_text())
    scene, qa = build(document)
    svg_text, drawio_text = exports(scene)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stem = source.stem
    artifacts = {
        "svg": svg_text,
        "drawio": drawio_text,
        "input.json": json.dumps(document, ensure_ascii=False, indent=2),
        "model.json": json.dumps(scene.meta["model"], ensure_ascii=False, indent=2),
        "qa.json": json.dumps(qa, ensure_ascii=False, indent=2),
    }
    for suffix, content in artifacts.items():
        (output / (stem + "." + suffix)).write_text(content)
    return qa


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    print(json.dumps(render_file(arguments.input, arguments.out), ensure_ascii=False))
