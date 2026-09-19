"""Render a small UML use-case model as SVG and grouped draw.io source."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as E

from render import Scene, audit, drawio, svg
from usecase_model import validate


NS = "http://www.w3.org/2000/svg"


def build(document):
    model = validate(document)
    use_cases = {item["id"]: item for item in model["use_cases"]}
    actors = {item["id"]: item for item in model["actors"]}
    subject_ids = [item["id"] for item in model["subjects"]]
    if len(subject_ids) != 1:
        raise ValueError("current renderer supports exactly one subject")
    subject_id = subject_ids[0]
    if any(item["subject"] != subject_id for item in model["use_cases"]):
        raise ValueError("current renderer requires all use cases to share one subject")

    included = {relation["target"] for relation in model["relations"] if relation["kind"] == "include"}
    extensions = {relation["source"] for relation in model["relations"] if relation["kind"] == "extend"}
    ranks = {key: (0 if key in included else 2 if key in extensions else 1) for key in use_cases}
    rows = {rank: [key for key in use_cases if ranks[key] == rank] for rank in (0, 1, 2)}
    rows = {rank: values for rank, values in rows.items() if values}
    max_columns = max(len(values) for values in rows.values())
    subject_x, subject_y = 350, 214
    subject_w = max(860, max_columns * 250 + 100)
    row_gap = 176
    subject_h = 116 + len(rows) * row_gap
    canvas_w = max(1600, subject_x + subject_w + 350)
    canvas_h = subject_y + subject_h + 110
    subject = model["subjects"][0]
    label = ("«" + subject["stereotype"] + "»\n" if subject.get("stereotype") else "") + subject["name"]
    scene = Scene(
        {
            "width": canvas_w,
            "height": canvas_h,
            "title": model["title"],
            "subtitle": model["scope"],
            "eyebrow": "UML / USE CASE",
            "footer": "教学视图；关系方向按UML 2.5.1第18章校验，行为步骤与完整元模型不在本图中验证。",
        },
        "editorial-warm",
    )
    subject_node = "subject_" + subject_id
    scene.add(subject_x, subject_y, subject_w, subject_h, label, kind="panel", id=subject_node, check=False)

    positions = {}
    for row_index, (rank, values) in enumerate(sorted(rows.items())):
        y = subject_y + 82 + row_index * row_gap
        span = subject_w - 110
        step = span / len(values)
        for column, use_case_id in enumerate(values):
            item = use_cases[use_case_id]
            width, height = 220, 104 if item.get("extension_points") else 86
            x = subject_x + 55 + step * (column + 0.5) - width / 2
            detail = ""
            if item.get("extension_points"):
                detail = "extension points\n" + ", ".join(item["extension_points"])
            name = ("«" + item["stereotype"] + "»\n" if item.get("stereotype") else "") + item["name"]
            node_id = "usecase_" + use_case_id
            scene.add(x, y, width, height, name, detail, kind="ellipse", tone="accent", id=node_id, check=True)
            positions[use_case_id] = scene.get(node_id)

    association_targets = {key: [] for key in actors}
    for relation_index, relation in enumerate(model["relations"]):
        if relation["kind"] != "association":
            continue
        actor_id = relation["source"] if relation["source"] in actors else relation["target"]
        use_case_id = relation["target"] if relation["target"] in use_cases else relation["source"]
        association_targets[actor_id].append(use_case_id)

    actor_nodes = {}
    for side in ("left", "right"):
        side_actors = [item for item in model["actors"] if item.get("side", "left") == side]
        desired = []
        for index, actor in enumerate(side_actors):
            targets = association_targets[actor["id"]]
            average = sum(positions[target]["y"] + positions[target]["h"] / 2 for target in targets) / len(targets) if targets else subject_y + 130 + index * 140
            desired.append([actor, average - 50])
        desired.sort(key=lambda pair: pair[1])
        last = subject_y + 20
        for actor, proposed in desired:
            y = max(last, min(proposed, subject_y + subject_h - 118))
            x = 70 if side == "left" else subject_x + subject_w + 70
            detail = actor.get("kind", "external role")
            node_id = "actor_" + actor["id"]
            scene.add(x, y, 220, 96, "«actor»\n" + actor["name"], detail, kind="rect", tone="teal", id=node_id, check=True)
            actor_nodes[actor["id"]] = scene.get(node_id)
            last = y + 126

    relation_meta = []
    for relation in model["relations"]:
        kind, source, target = relation["kind"], relation["source"], relation["target"]
        if kind == "association":
            actor_id = source if source in actors else target
            use_case_id = target if target in use_cases else source
            actor, use_case = actor_nodes[actor_id], positions[use_case_id]
            left = actors[actor_id].get("side", "left") == "left"
            start = (actor["x"] + actor["w"], actor["y"] + actor["h"] / 2) if left else (actor["x"], actor["y"] + actor["h"] / 2)
            end = (use_case["x"] + use_case["w"] / 2, use_case["y"])
            lane = subject_x - 28 if left else subject_x + subject_w + 28
            approach_y = use_case["y"] - 24 - relation_index * 3
            scene.edge(
                "actor_" + actor_id,
                "usecase_" + use_case_id,
                relation.get("label", ""),
                points=[start, (lane, start[1]), (lane, approach_y), (end[0], approach_y), end],
                arrow=False,
                tone="muted",
            )
        else:
            source_node, target_node = positions[source], positions[target]
            source_center = source_node["y"] + source_node["h"] / 2
            target_center = target_node["y"] + target_node["h"] / 2
            if abs(source_center - target_center) < 20:
                left_to_right = source_node["x"] < target_node["x"]
                start = (source_node["x"] + source_node["w"] if left_to_right else source_node["x"], source_center)
                end = (target_node["x"] if left_to_right else target_node["x"] + target_node["w"], target_center)
                points = [start, end]
            else:
                upward = source_center > target_center
                start = (source_node["x"] + source_node["w"] / 2, source_node["y"] if upward else source_node["y"] + source_node["h"])
                end = (target_node["x"] + target_node["w"] / 2, target_node["y"] + target_node["h"] if upward else target_node["y"])
                middle = (start[1] + end[1]) / 2
                points = [start, (start[0], middle), (end[0], middle), end]
            label = {"include": "«include»", "extend": "«extend»", "generalization": relation.get("label", "")}[kind]
            if kind == "extend" and relation.get("condition"):
                label += " [" + relation["condition"] + "]"
            scene.edge(
                "usecase_" + source,
                "usecase_" + target,
                label,
                points=points,
                dashed=kind in ("include", "extend"),
                arrow="open",
                tone="accent",
            )
        relation_meta.append({"id": relation["id"], "kind": kind})

    scene.meta = {"model": model, "subject_node": subject_node, "relations": relation_meta}
    scene.finish()
    qa = audit(scene)
    if qa["errors"] or qa["warnings"]:
        raise ValueError(str(qa))
    return scene, qa


def exports(scene):
    svg_root = E.fromstring(svg(scene))
    ns = "{" + NS + "}"
    defs = svg_root.find(ns + "defs")
    marker = E.SubElement(
        defs,
        ns + "marker",
        id="arrow-open-accent",
        viewBox="0 0 10 10",
        refX="9",
        refY="5",
        markerWidth="7",
        markerHeight="7",
        orient="auto-start-reverse",
    )
    E.SubElement(marker, ns + "path", d="M 0 0 L 10 5 L 0 10", fill="none", stroke=scene.palette["accent"], **{"stroke-width": "1.5"})
    drawing_group = svg_root.find(ns + "g")
    edge_paths = [child for child in list(drawing_group) if child.tag == ns + "path" and child.get("fill") == "none"]
    if len(edge_paths) != len(scene.edges):
        raise ValueError("could not map SVG edge paths")
    for edge, path in zip(scene.edges, edge_paths):
        if edge.get("arrow") == "open":
            path.set("marker-end", "url(#arrow-open-accent)")
    E.register_namespace("", NS)
    svg_text = E.tostring(svg_root, encoding="unicode")

    drawio_root = E.fromstring(drawio(scene))
    edge_cells = [cell for cell in drawio_root.iter("mxCell") if cell.get("edge") == "1"]
    if len(edge_cells) != len(scene.edges):
        raise ValueError("could not map draw.io edges")
    for edge, cell in zip(scene.edges, edge_cells):
        if edge.get("arrow") == "open":
            style = cell.get("style", "").replace("endArrow=block;", "endArrow=open;endFill=0;")
            cell.set("style", style)
    cells = {cell.get("id"): cell for cell in drawio_root.iter("mxCell")}
    subject = cells[scene.meta["subject_node"]]
    subject.set("style", subject.get("style", "") + "container=1;collapsible=0;recursiveResize=0;")
    subject_geometry = subject.find("mxGeometry")
    subject_x, subject_y = float(subject_geometry.get("x")), float(subject_geometry.get("y"))
    for use_case in scene.meta["model"]["use_cases"]:
        cell = cells["usecase_" + use_case["id"]]
        geometry = cell.find("mxGeometry")
        cell.set("parent", subject.get("id"))
        geometry.set("x", str(float(geometry.get("x")) - subject_x))
        geometry.set("y", str(float(geometry.get("y")) - subject_y))
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
