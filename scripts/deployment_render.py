"""Render a validated UML deployment subset as SVG and grouped draw.io source."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as E

from deployment_model import validate
from render import Scene, audit, drawio, port, svg


NS = "http://www.w3.org/2000/svg"
CANVAS_W = 1900
CANVAS_H = 1120
DEVICE_X = 70
DEVICE_Y = 250
DEVICE_W = 380
DEVICE_H = 500
DEVICE_GAP = 75
ENV_INSET_X = 22
ENV_Y = DEVICE_Y + 105
ENV_W = DEVICE_W - 44
ENV_H = 330
ARTIFACT_W = 140
ARTIFACT_H = 94
COMPONENT_X = 70
COMPONENT_Y = 850
COMPONENT_W = 300
COMPONENT_H = 86
COMPONENT_GAP = 60


def build(document):
    model = validate(document)
    scene = Scene(
        {
            "width": CANVAS_W,
            "height": CANVAS_H,
            "title": model["title"],
            "subtitle": model["scope"],
            "eyebrow": "UML / DEPLOYMENT",
            "footer": "模拟教学拓扑；物理设备、执行环境、制品与逻辑组件分开。符号按UML 2.5.1第19章核对。",
        },
        "editorial-warm",
    )

    device_ids = {}
    environment_ids = {}
    artifact_ids = {}
    component_ids = {}
    child_owner = {}
    instance_nodes = set()
    cube_nodes = set()
    component_nodes = set()

    devices = {}
    for item in model["devices"]:
        x = DEVICE_X + item["column"] * (DEVICE_W + DEVICE_GAP)
        y = DEVICE_Y
        node_id = "device_" + item["id"]
        label = "«device»\n" + item["instance"] + " : " + item["type"]
        scene.add(x, y, DEVICE_W, DEVICE_H, label, item["name"], kind="rect", tone="accent", fill="bg", id=node_id, check=False, fs=19)
        device_ids[item["id"]] = node_id
        devices[item["id"]] = scene.get(node_id)
        instance_nodes.add(node_id)
        cube_nodes.add(node_id)

    environments_by_device = {}
    for item in model["environments"]:
        environments_by_device.setdefault(item["device"], []).append(item)
    for values in environments_by_device.values():
        values.sort(key=lambda item: item["order"])

    environments = {}
    for device_id, values in environments_by_device.items():
        device = devices[device_id]
        for item in values:
            x = device["x"] + ENV_INSET_X
            y = ENV_Y
            node_id = "environment_" + item["id"]
            label = "«executionEnvironment»\n" + item["instance"] + " : " + item["type"]
            scene.add(x, y, ENV_W, ENV_H, label, item["name"], kind="rect", tone="teal", fill="bg", id=node_id, check=False, fs=17)
            environment_ids[item["id"]] = node_id
            environments[item["id"]] = scene.get(node_id)
            child_owner[node_id] = device_ids[device_id]
            instance_nodes.add(node_id)
            cube_nodes.add(node_id)

    artifacts_by_target = {}
    for item in model["artifacts"]:
        artifacts_by_target.setdefault(item["target"], []).append(item)
    for values in artifacts_by_target.values():
        values.sort(key=lambda item: item["order"])

    for target_id, values in artifacts_by_target.items():
        target_node_id = environment_ids.get(target_id, device_ids.get(target_id))
        target = scene.get(target_node_id)
        count = len(values)
        for item in values:
            order = item["order"]
            if count == 1:
                x = target["x"] + (target["w"] - ARTIFACT_W) / 2
            else:
                x = target["x"] + 18 + (order % 2) * (ARTIFACT_W + 20)
            y = target["y"] + 112 + (order // 2) * (ARTIFACT_H + 22)
            node_id = "artifact_" + item["id"]
            scene.add(
                x,
                y,
                ARTIFACT_W,
                ARTIFACT_H,
                "«artifact»\n" + item["name"],
                item.get("kind", ""),
                kind="rect",
                tone="amber",
                fill="panel",
                id=node_id,
                check=True,
                fs=16,
                radius=0,
            )
            artifact_ids[item["id"]] = node_id
            child_owner[node_id] = target_node_id

    max_component_column = max(item["column"] for item in model["components"])
    for item in model["components"]:
        x = COMPONENT_X + item["column"] * (COMPONENT_W + COMPONENT_GAP)
        y = COMPONENT_Y
        node_id = "component_" + item["id"]
        scene.add(x, y, COMPONENT_W, COMPONENT_H, "«component»\n" + item["name"], kind="rect", tone="ink", fill="panel", id=node_id, check=True, fs=18)
        component_ids[item["id"]] = node_id
        component_nodes.add(node_id)
        for suffix, geometry in (
            ("body", (x + COMPONENT_W - 40, y + 14, 24, 28)),
            ("tab1", (x + COMPONENT_W - 45, y + 19, 10, 7)),
            ("tab2", (x + COMPONENT_W - 45, y + 31, 10, 7)),
        ):
            icon_id = "icon_" + item["id"] + "_" + suffix
            scene.add(*geometry, kind="rect", tone="ink", fill="bg", id=icon_id, check=False, radius=0)
            child_owner[icon_id] = node_id

    edge_kinds = []
    for item in model["communication_paths"]:
        source_id = device_ids[item["source"]]
        target_id = device_ids[item["target"]]
        source = scene.get(source_id)
        target = scene.get(target_id)
        start = port(source, "right") if source["x"] < target["x"] else port(source, "left")
        end = port(target, "left") if source["x"] < target["x"] else port(target, "right")
        scene.edge(
            source_id,
            target_id,
            item["label"],
            points=[start, end],
            source_port="right" if source["x"] < target["x"] else "left",
            target_port="left" if source["x"] < target["x"] else "right",
            tone="muted",
            arrow=False,
            width=2,
        )
        edge_kinds.append("communication")

    for index, item in enumerate(model["manifestations"]):
        source_id = artifact_ids[item["artifact"]]
        target_id = component_ids[item["component"]]
        source = scene.get(source_id)
        target = scene.get(target_id)
        start = port(source, "bottom")
        end = port(target, "top")
        route_y = DEVICE_Y + DEVICE_H + 28 + index * 11
        points = [start, (start[0], route_y), (end[0], route_y), end]
        scene.edge(
            source_id,
            target_id,
            "«manifest»",
            points=points,
            source_port="bottom",
            target_port="top",
            tone="accent",
            dashed=True,
            arrow="open",
            width=1.8,
            label_at=[end[0], route_y - 10],
        )
        edge_kinds.append("manifestation")

    scene.meta = {
        "model": model,
        "device_ids": device_ids,
        "environment_ids": environment_ids,
        "artifact_ids": artifact_ids,
        "component_ids": component_ids,
        "child_owner": child_owner,
        "instance_nodes": sorted(instance_nodes),
        "cube_nodes": sorted(cube_nodes),
        "component_nodes": sorted(component_nodes),
        "edge_kinds": edge_kinds,
        "component_columns": max_component_column + 1,
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
        raise ValueError("could not map SVG deployment edges")
    for kind, path in zip(scene.meta["edge_kinds"], edge_paths):
        if kind == "manifestation":
            path.set("marker-end", "url(#arrow-open-accent)")
        else:
            path.attrib.pop("marker-end", None)

    for node_id in scene.meta["cube_nodes"]:
        group = svg_root.find(".//" + ns + "g[@id='" + node_id + "']")
        node = scene.get(node_id)
        x, y, w, h = (node[key] for key in ("x", "y", "w", "h"))
        cube_path = E.Element(
            ns + "path",
            d=(
                f"M {x},{y} L {x + 12},{y - 12} L {x + w + 12},{y - 12} L {x + w},{y} "
                f"M {x + w},{y} L {x + w + 12},{y - 12} L {x + w + 12},{y + h - 12} L {x + w},{y + h}"
            ),
            fill="none",
            stroke=scene.palette["accent"] if node_id.startswith("device_") else scene.palette["teal"],
            **{"stroke-width": "1.5"},
        )
        group.insert(1, cube_path)
    for node_id in scene.meta["instance_nodes"]:
        group = svg_root.find(".//" + ns + "g[@id='" + node_id + "']")
        node = scene.get(node_id)
        text_elements = group.findall(ns + "text")
        for index, text_element in enumerate(text_elements):
            text_element.set("x", str(node["x"] + 18))
            text_element.set("y", str(node["y"] + 27 + index * 23))
            text_element.set("text-anchor", "start")
        if len(text_elements) >= 2:
            text_elements[1].set("text-decoration", "underline")

    E.register_namespace("", NS)
    svg_text = E.tostring(svg_root, encoding="unicode")

    drawio_root = E.fromstring(drawio(scene))
    cells = {cell.get("id"): cell for cell in drawio_root.iter("mxCell")}
    absolute = {}
    for cell_id, cell in cells.items():
        geometry = cell.find("mxGeometry")
        if geometry is not None:
            absolute[cell_id] = (
                float(geometry.get("x", "0")),
                float(geometry.get("y", "0")),
            )
    for node_id in scene.meta["cube_nodes"]:
        cell = cells[node_id]
        cell.set("style", cell.get("style", "") + "shape=cube;size=12;direction=south;container=1;collapsible=0;recursiveResize=0;verticalAlign=top;align=left;spacingTop=12;spacingLeft=12;")
    for node_id in scene.meta["component_nodes"]:
        cells[node_id].set("style", cells[node_id].get("style", "") + "container=1;collapsible=0;recursiveResize=0;")
    for child_id, owner_id in scene.meta["child_owner"].items():
        child = cells[child_id]
        geometry = child.find("mxGeometry")
        owner_x, owner_y = absolute[owner_id]
        child_x, child_y = absolute[child_id]
        child.set("parent", owner_id)
        geometry.set("x", str(child_x - owner_x))
        geometry.set("y", str(child_y - owner_y))
    device_records = {"device_" + item["id"]: item for item in scene.meta["model"]["devices"]}
    environment_records = {"environment_" + item["id"]: item for item in scene.meta["model"]["environments"]}
    for node_id, item in {**device_records, **environment_records}.items():
        keyword = "device" if node_id.startswith("device_") else "executionEnvironment"
        color = scene.palette["muted"]
        cells[node_id].set(
            "value",
            "«" + keyword + "»<br><u>" + item["instance"] + " : " + item["type"] + "</u><br>"
            + '<span style="font-size:16px;color:' + color + '">' + item["name"] + "</span>",
        )
    edge_cells = [cell for cell in drawio_root.iter("mxCell") if cell.get("edge") == "1"]
    if len(edge_cells) != len(scene.edges):
        raise ValueError("could not map draw.io deployment edges")
    for kind, cell in zip(scene.meta["edge_kinds"], edge_cells):
        if kind == "manifestation":
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
