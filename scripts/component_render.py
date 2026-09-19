"""Render a validated UML component subset as SVG and grouped draw.io source."""
from pathlib import Path
from urllib.parse import quote
import argparse
import base64
import json
import zlib
import xml.etree.ElementTree as E

from component_model import validate
from render import Scene, audit, drawio, svg


NS = "http://www.w3.org/2000/svg"


def port_geometry(component, side, index, count):
    x, y, w, h = (component[key] for key in ("x", "y", "w", "h"))
    fraction = (index + 1) / (count + 1)
    if side == "left":
        center = (x, y + h * fraction)
        symbol = (x - 40, center[1])
    elif side == "right":
        center = (x + w, y + h * fraction)
        symbol = (x + w + 40, center[1])
    elif side == "top":
        center = (x + w * fraction, y)
        symbol = (center[0], y - 40)
    else:
        center = (x + w * fraction, y + h)
        symbol = (center[0], y + h + 40)
    return center, symbol


def build(document):
    model = validate(document)
    max_column = max(item["column"] for item in model["components"])
    max_row = max(item["row"] for item in model["components"])
    component_w, component_h = 260, 140
    x0, y0, column_gap, row_gap = 70, 250, 365, 270
    canvas_w = max(1600, x0 + max_column * column_gap + component_w + 100)
    canvas_h = max(900, y0 + max_row * row_gap + component_h + 120)
    scene = Scene(
        {
            "width": canvas_w,
            "height": canvas_h,
            "title": model["title"],
            "subtitle": model["scope"],
            "eyebrow": "UML / COMPONENT",
            "footer": "教学子集；组件协作不是部署拓扑。符号与关系按UML 2.5.1第11.6节核对。",
        },
        "editorial-warm",
    )

    components = {}
    component_nodes = {}
    child_owner = {}
    for item in model["components"]:
        x = x0 + item["column"] * column_gap
        y = y0 + item["row"] * row_gap
        node_id = "component_" + item["id"]
        stereotype = item.get("stereotype", "component")
        scene.add(
            x,
            y,
            component_w,
            component_h,
            "«" + stereotype + "»\n" + item["name"],
            item.get("kind", "logical component"),
            kind="rect",
            tone="teal",
            id=node_id,
            check=True,
        )
        components[item["id"]] = scene.get(node_id)
        component_nodes[item["id"]] = node_id
        # The UML component icon: one body and two tabs protruding from its left.
        for suffix, geometry in (
            ("body", (x + component_w - 42, y + 13, 25, 29)),
            ("tab1", (x + component_w - 47, y + 18, 10, 7)),
            ("tab2", (x + component_w - 47, y + 30, 10, 7)),
        ):
            icon_id = "icon_" + item["id"] + "_" + suffix
            scene.add(*geometry, kind="rect", tone="teal", fill="bg", id=icon_id, check=False, radius=0)
            child_owner[icon_id] = node_id

    ports = {item["id"]: item for item in model["ports"]}
    interfaces = {item["id"]: item for item in model["interfaces"]}
    grouped = {}
    for port in model["ports"]:
        grouped.setdefault((port["component"], port["side"]), []).append(port)
    for values in grouped.values():
        values.sort(key=lambda item: item["order"])

    symbol_centers = {}
    required_symbols = {}
    for (component_id, side), values in grouped.items():
        component = components[component_id]
        for index, port in enumerate(values):
            center, symbol_center = port_geometry(component, side, index, len(values))
            port_id = "port_" + port["id"]
            symbol_id = "symbol_" + port["id"]
            scene.add(center[0] - 8, center[1] - 8, 16, 16, kind="rect", tone="accent", fill="bg", id=port_id, check=False, radius=0)
            scene.add(symbol_center[0] - 12, symbol_center[1] - 12, 24, 24, kind="ellipse", tone="accent", fill="bg", id=symbol_id, check=False)
            scene.edge(
                port_id,
                symbol_id,
                points=[center, symbol_center],
                arrow=False,
                tone="accent",
                width=2,
                internal_to=component_nodes[component_id],
            )
            child_owner[port_id] = component_nodes[component_id]
            child_owner[symbol_id] = component_nodes[component_id]
            symbol_centers[port["id"]] = symbol_center
            if port["direction"] == "required":
                required_symbols[symbol_id] = side

    relation_meta = []
    for relation in model["relations"]:
        if relation["kind"] == "assembly":
            source = ports[relation["source"]]
            interface = interfaces[source["interface"]]
            a, b = symbol_centers[relation["source"]], symbol_centers[relation["target"]]
            if abs(a[1] - b[1]) < 1 or abs(a[0] - b[0]) < 1:
                points = [a, b]
            else:
                middle = (a[0] + b[0]) / 2
                points = [a, (middle, a[1]), (middle, b[1]), b]
            scene.edge(
                "symbol_" + relation["source"],
                "symbol_" + relation["target"],
                relation.get("label", interface["name"]),
                points=points,
                arrow=False,
                tone="accent",
                width=2.2,
            )
        else:
            source_id = component_nodes[relation["source"]]
            target_id = component_nodes[relation["target"]]
            source, target = components[relation["source"]], components[relation["target"]]
            start = (source["x"] + source["w"] / 2, source["y"] + source["h"])
            end = (target["x"] + target["w"] / 2, target["y"])
            middle_y = (start[1] + end[1]) / 2
            scene.edge(
                source_id,
                target_id,
                relation.get("label", "dependency"),
                points=[start, (start[0], middle_y), (end[0], middle_y), end],
                dashed=True,
                arrow="open",
                tone="muted",
            )
        relation_meta.append(dict(relation))

    scene.meta = {
        "model": model,
        "component_nodes": component_nodes,
        "child_owner": child_owner,
        "required_symbols": required_symbols,
        "relations": relation_meta,
    }
    scene.finish()
    qa = audit(scene)
    if qa["errors"] or qa["warnings"]:
        raise ValueError(str(qa))
    return scene, qa


def required_path(node, side):
    x, y, w, h = (node[key] for key in ("x", "y", "w", "h"))
    if side == "right":
        return f"M {x+w},{y} Q {x},{y+h/2} {x+w},{y+h}"
    if side == "left":
        return f"M {x},{y} Q {x+w},{y+h/2} {x},{y+h}"
    if side == "top":
        return f"M {x},{y} Q {x+w/2},{y+h} {x+w},{y}"
    return f"M {x},{y+h} Q {x+w/2},{y} {x+w},{y+h}"


def socket_stencil(side):
    shape = E.Element("shape", name="required-interface", w="24", h="24", aspect="fixed", strokewidth="inherit")
    E.SubElement(shape, "background")
    foreground = E.SubElement(shape, "foreground")
    path = E.SubElement(foreground, "path")
    if side == "right":
        E.SubElement(path, "move", x="24", y="0")
        E.SubElement(path, "curve", x1="0", y1="3", x2="0", y2="21", x3="24", y3="24")
    elif side == "left":
        E.SubElement(path, "move", x="0", y="0")
        E.SubElement(path, "curve", x1="24", y1="3", x2="24", y2="21", x3="0", y3="24")
    elif side == "top":
        E.SubElement(path, "move", x="0", y="0")
        E.SubElement(path, "curve", x1="3", y1="24", x2="21", y2="24", x3="24", y3="0")
    else:
        E.SubElement(path, "move", x="0", y="24")
        E.SubElement(path, "curve", x1="3", y1="0", x2="21", y2="0", x3="24", y3="24")
    E.SubElement(foreground, "stroke")
    compressor = zlib.compressobj(wbits=-15)
    raw = quote(E.tostring(shape, encoding="unicode"), safe="~()*!.'-").encode()
    return base64.b64encode(compressor.compress(raw) + compressor.flush()).decode()


def exports(scene):
    svg_root = E.fromstring(svg(scene))
    ns = "{" + NS + "}"
    defs = svg_root.find(ns + "defs")
    marker = E.SubElement(
        defs,
        ns + "marker",
        id="arrow-open-muted",
        viewBox="0 0 10 10",
        refX="9",
        refY="5",
        markerWidth="7",
        markerHeight="7",
        orient="auto-start-reverse",
    )
    E.SubElement(marker, ns + "path", d="M 0 0 L 10 5 L 0 10", fill="none", stroke=scene.palette["muted"], **{"stroke-width": "1.5"})
    for symbol_id, side in scene.meta["required_symbols"].items():
        group = svg_root.find(".//" + ns + "g[@id='" + symbol_id + "']")
        ellipse = group.find(ns + "ellipse")
        group.remove(ellipse)
        node = scene.get(symbol_id)
        group.insert(0, E.Element(ns + "path", d=required_path(node, side), fill="none", stroke=scene.palette["accent"], **{"stroke-width": "2"}))
    drawing_group = svg_root.find(ns + "g")
    edge_paths = [child for child in list(drawing_group) if child.tag == ns + "path" and child.get("fill") == "none"]
    if len(edge_paths) != len(scene.edges):
        raise ValueError("could not map SVG edge paths")
    for edge, path in zip(scene.edges, edge_paths):
        if edge.get("arrow") == "open":
            path.set("marker-end", "url(#arrow-open-muted)")
    E.register_namespace("", NS)
    svg_text = E.tostring(svg_root, encoding="unicode")

    drawio_root = E.fromstring(drawio(scene))
    cells = {cell.get("id"): cell for cell in drawio_root.iter("mxCell")}
    for component_id, node_id in scene.meta["component_nodes"].items():
        cell = cells[node_id]
        cell.set("style", cell.get("style", "") + "container=1;collapsible=0;recursiveResize=0;")
    for child_id, owner_id in scene.meta["child_owner"].items():
        child = cells[child_id]
        owner_geometry = cells[owner_id].find("mxGeometry")
        geometry = child.find("mxGeometry")
        child.set("parent", owner_id)
        geometry.set("x", str(float(geometry.get("x")) - float(owner_geometry.get("x"))))
        geometry.set("y", str(float(geometry.get("y")) - float(owner_geometry.get("y"))))
    for symbol_id, side in scene.meta["required_symbols"].items():
        cell = cells[symbol_id]
        style = cell.get("style", "").replace("shape=ellipse;", "shape=stencil(" + socket_stencil(side) + ");")
        style = style.replace("fillColor=" + scene.palette["bg"] + ";", "fillColor=none;")
        cell.set("style", style)
    edge_cells = [cell for cell in drawio_root.iter("mxCell") if cell.get("edge") == "1"]
    if len(edge_cells) != len(scene.edges):
        raise ValueError("could not map draw.io edges")
    for edge, cell in zip(scene.edges, edge_cells):
        if edge.get("arrow") == "open":
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
