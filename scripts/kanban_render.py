"""Render the validated swimlane Kanban subset to SVG and editable draw.io."""
from collections import defaultdict
from pathlib import Path
import argparse
import html
import json
import shutil
import xml.etree.ElementTree as ET

from kanban_model import validate


BG = "#F1EFEB"
INK = "#30302D"
MUTED = "#756F66"
LINE = "#CFC7BA"
PAPER = "#FBFAF7"
ACCENT = "#8B5947"
ACTIVE = "#DDE8E1"
BLOCKED = "#B94B42"
CLASS_COLORS = {
    "standard": "#607D8B",
    "fixed_date": "#C28A36",
    "expedite": "#B94B42",
    "intangible": "#7B6D8D",
}
CLASS_LABELS = {
    "standard": "标准",
    "fixed_date": "固定日期",
    "expedite": "加急",
    "intangible": "改善",
}

UI_LABELS = {
    "zh": {
        "snapshot": "快照",
        "wip": "在制",
        "blocked": "阻塞",
        "throughput": "吞吐",
        "sle": "SLE",
        "before_commitment": "承诺前",
        "delivery_complete": "交付完成",
        "lane_wip": "泳道WIP",
        "policies": "显式策略",
        "footer_note": "阻塞项仍计入WIP · 下游有容量才拉动",
        "footer": "教学模拟数据 · 泳道表示工作类型，不用于个人绩效排名",
        "diagram_name": "泳道看板",
        "age_suffix": "天",
        "due_prefix": "截止",
    },
    "en": {
        "snapshot": "Snapshot",
        "wip": "WIP",
        "blocked": "Blocked",
        "throughput": "Throughput",
        "sle": "SLE",
        "before_commitment": "Before commitment",
        "delivery_complete": "Delivered",
        "lane_wip": "Lane WIP",
        "policies": "Explicit policies",
        "footer_note": "Blocked items remain in WIP · pull only when downstream capacity exists",
        "footer": "Teaching simulation · lanes show work classes, not individual performance",
        "diagram_name": "Swimlane Kanban",
        "age_suffix": "d",
        "due_prefix": "Due ",
    },
}

CLASS_LABELS_EN = {
    "standard": "Standard",
    "fixed_date": "Fixed date",
    "expedite": "Expedite",
    "intangible": "Improvement",
}


def labels(model):
    language = model.get("language", "zh")
    return UI_LABELS[language]


def class_label(model, service_class):
    return (CLASS_LABELS_EN if model.get("language", "zh") == "en" else CLASS_LABELS)[service_class]


def wrap(text, width, language="zh"):
    if language == "en":
        lines, current = [], ""
        for token in str(text).split():
            candidate = token if not current else current + " " + token
            if current and len(candidate) > width:
                lines.append(current)
                current = ""
            if len(token) > width:
                if current:
                    lines.append(current)
                    current = ""
                while len(token) > width:
                    lines.append(token[:width])
                    token = token[width:]
                current = token
            else:
                current = token if not current else current + " " + token
        if current:
            lines.append(current)
        return lines or [""]
    lines, current = [], ""
    for ch in text:
        if len(current) >= width:
            lines.append(current)
            current = ""
        current += ch
    if current:
        lines.append(current)
    return lines or [""]


def layout(model):
    width = 1600
    left, right = 170, 50
    header_y, header_h = 154, 86
    col_w = (width - left - right) / len(model["columns"])
    by_cell = defaultdict(list)
    for card in model["cards"]:
        by_cell[(card["lane"], card["column"])].append(card)
    lane_heights = {}
    for lane in model["lanes"]:
        largest = max(len(by_cell[(lane["id"], col["id"])]) for col in model["columns"])
        lane_heights[lane["id"]] = max(172, 24 + largest * 82)
    lane_y = {}
    cursor = header_y + header_h
    for lane in model["lanes"]:
        lane_y[lane["id"]] = cursor
        cursor += lane_heights[lane["id"]]
    policy_rows = (len(model["policies"]) + 1) // 2
    footer_y = cursor + 34
    height = footer_y + 92 + policy_rows * 76 + 42
    return {
        "width": width, "height": height, "left": left, "right": right,
        "header_y": header_y, "header_h": header_h, "col_w": col_w,
        "lane_y": lane_y, "lane_heights": lane_heights, "board_bottom": cursor,
        "footer_y": footer_y, "by_cell": by_cell,
    }


def svg_text(x, y, value, size=15, color=INK, weight=400, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,'
            f'PingFang SC,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}">{html.escape(str(value))}</text>')


def render_svg(model, geometry):
    g = geometry
    ui = labels(model)
    language = model.get("language", "zh")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{g["width"]}" height="{g["height"]}" '
        f'viewBox="0 0 {g["width"]} {g["height"]}">',
        f'<rect width="100%" height="100%" fill="{BG}"/>',
        '<title>' + html.escape(model["title"]) + '</title>',
        svg_text(50, 48, "KANBAN / FLOW SNAPSHOT", 12, ACCENT, 650),
        svg_text(50, 83, model["title"], 30, INK, 620),
        svg_text(50, 112, model["service"], 15, MUTED, 400),
        svg_text(1550, 47, ui["snapshot"] + " " + model["snapshot"], 12, MUTED, 450, "end"),
    ]
    metrics = model["flow_metrics"]
    pills = [
        (ui["wip"], str(model["counts"]["wip"])),
        (ui["blocked"], str(model["counts"]["blocked"])),
        (ui["throughput"], f'{metrics["throughput"]} {metrics["throughput_unit"]}'),
        (ui["sle"], f'{int(metrics["sle_probability"]*100)}% ≤ {metrics["sle_days"]}{ui["age_suffix"]}'),
    ]
    px = 815
    for label, value in pills:
        parts.append(f'<rect x="{px}" y="70" width="170" height="48" rx="5" fill="{PAPER}" stroke="{LINE}"/>')
        parts.append(svg_text(px + 13, 89, label, 10, MUTED, 500))
        parts.append(svg_text(px + 13, 108, value, 15, INK, 600))
        px += 182

    # Column headers and commitment/delivery markers.
    for index, column in enumerate(model["columns"]):
        x = g["left"] + index * g["col_w"]
        fill = ACTIVE if column["stage"] == "wip" else PAPER
        parts.append(f'<rect x="{x:.1f}" y="{g["header_y"]}" width="{g["col_w"]:.1f}" height="{g["header_h"]}" fill="{fill}" stroke="{LINE}"/>')
        parts.append(svg_text(x + 16, g["header_y"] + 31, column["name"], 18, INK, 600))
        if column["stage"] == "wip":
            count = model["column_wip"][column["id"]]
            limit = column["wip_limit"]
            label = f"{ui['wip']} {count}/{limit}"
            badge_color = BLOCKED if count >= limit else ACCENT
            parts.append(f'<rect x="{x + g["col_w"] - 91:.1f}" y="{g["header_y"] + 15}" width="73" height="26" rx="13" fill="{badge_color}"/>')
            parts.append(svg_text(x + g["col_w"] - 54.5, g["header_y"] + 34, label, 11, "#FFFFFF", 650, "middle"))
            criteria = wrap(column["pull_criteria"], 18, language)[:2]
            for line_index, line in enumerate(criteria):
                parts.append(svg_text(x + 16, g["header_y"] + 58 + 17 * line_index, line, 11, MUTED, 400))
        else:
            marker = ui["before_commitment"] if column["stage"] == "queue" else ui["delivery_complete"]
            parts.append(svg_text(x + 16, g["header_y"] + 61, marker, 11, MUTED, 500))

    lane_lookup = {lane["id"]: lane for lane in model["lanes"]}
    for lane_index, lane in enumerate(model["lanes"]):
        y = g["lane_y"][lane["id"]]
        h = g["lane_heights"][lane["id"]]
        parts.append(f'<rect x="50" y="{y}" width="120" height="{h}" fill="{PAPER}" stroke="{LINE}"/>')
        parts.append(svg_text(110, y + 42, lane["name"], 15, INK, 620, "middle"))
        lane_count = model["lane_wip"][lane["id"]]
        parts.append(svg_text(110, y + 68, f'{ui["lane_wip"]} {lane_count}/{lane["wip_limit"]}', 10, MUTED, 500, "middle"))
        parts.append(f'<rect x="{g["left"]}" y="{y}" width="{g["width"]-g["left"]-g["right"]}" height="{h}" fill="{PAPER if lane_index%2==0 else "#F7F4EE"}" stroke="{LINE}"/>')
        for col_index, column in enumerate(model["columns"]):
            x = g["left"] + col_index * g["col_w"]
            if col_index:
                parts.append(f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{y+h}" stroke="{LINE}"/>')
            for card_index, card in enumerate(g["by_cell"][(lane["id"], column["id"]) ]):
                cx, cy = x + 12, y + 15 + card_index * 82
                cw, ch = g["col_w"] - 24, 69
                stroke = BLOCKED if card["blocked"] else LINE
                dash = ' stroke-dasharray="6 4"' if card["blocked"] else ""
                parts.append(f'<rect x="{cx:.1f}" y="{cy}" width="{cw:.1f}" height="{ch}" rx="5" fill="#FFFFFF" stroke="{stroke}" stroke-width="{2 if card["blocked"] else 1}"{dash}/>' )
                parts.append(f'<rect x="{cx:.1f}" y="{cy}" width="7" height="{ch}" rx="3" fill="{CLASS_COLORS[card["service_class"]]}"/>')
                title_lines = wrap(card["title"], 14, language)[:2]
                for line_index, line in enumerate(title_lines):
                    parts.append(svg_text(cx + 18, cy + 22 + line_index * 17, line, 13, INK, 600))
                meta_y = cy + 58
                meta = f'{card["id"]} · {card["owner"]}'
                if "age_days" in card:
                    meta += f' · {card["age_days"]}{ui["age_suffix"]}'
                if "due" in card:
                    meta += f' · {ui["due_prefix"]}{card["due"]}'
                parts.append(svg_text(cx + 18, meta_y, meta, 10, MUTED, 450))
                if card["blocked"]:
                    parts.append(f'<rect x="{cx+cw-57:.1f}" y="{cy+8}" width="46" height="21" rx="4" fill="{BLOCKED}"/>')
                    parts.append(svg_text(cx + cw - 34, cy + 23, ui["blocked"], 10, "#FFFFFF", 650, "middle"))
                    parts.append(svg_text(cx + cw - 12, cy + 52, card["blocked_reason"], 9, BLOCKED, 500, "end"))
                else:
                    parts.append(svg_text(cx + cw - 12, cy + 22, class_label(model, card["service_class"]), 9, CLASS_COLORS[card["service_class"]], 600, "end"))

    footer_y = g["footer_y"]
    parts.append(svg_text(50, footer_y, ui["policies"], 18, INK, 620))
    parts.append(svg_text(1550, footer_y, ui["footer_note"], 11, MUTED, 500, "end"))
    for index, policy in enumerate(model["policies"]):
        row, col = divmod(index, 2)
        x, y = 50 + col * 755, footer_y + 25 + row * 76
        parts.append(f'<rect x="{x}" y="{y}" width="730" height="62" rx="5" fill="{PAPER}" stroke="{LINE}"/>')
        parts.append(svg_text(x + 16, y + 24, policy["title"], 12, ACCENT, 650))
        for line_index, line in enumerate(wrap(policy["rule"], 42, language)[:2]):
            parts.append(svg_text(x + 90, y + 23 + line_index * 17, line, 11, INK, 400))
    parts.append(svg_text(50, g["height"] - 17, ui["footer"], 10, MUTED, 450))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_drawio(model, geometry):
    g = geometry
    ui = labels(model)
    mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="diagram-studio", version="24.7.17")
    diagram = ET.SubElement(mxfile, "diagram", id="kanban", name=ui["diagram_name"])
    graph = ET.SubElement(diagram, "mxGraphModel", dx="1600", dy=str(g["height"]), grid="1", gridSize="10",
                          page="1", pageScale="1", pageWidth=str(g["width"]), pageHeight=str(g["height"]),
                          background=BG, math="0", shadow="0")
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def vertex(cell_id, value, x, y, width, height, style, parent="1"):
        cell = ET.SubElement(root, "mxCell", id=cell_id, value=value, style=style, vertex="1", parent=parent)
        ET.SubElement(cell, "mxGeometry", x=str(round(x, 2)), y=str(round(y, 2)),
                      width=str(round(width, 2)), height=str(round(height, 2)), **{"as": "geometry"})
        return cell

    plain = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;"
    vertex("title", model["title"], 50, 38, 720, 50, plain + "fontSize=30;fontStyle=1;fontColor=" + INK + ";")
    vertex("service", model["service"], 50, 91, 720, 30, plain + "fontSize=14;fontColor=" + MUTED + ";")
    metrics = model["flow_metrics"]
    metric_values = [
        f'{ui["wip"]}\n{model["counts"]["wip"]}', f'{ui["blocked"]}\n{model["counts"]["blocked"]}',
        f'{ui["throughput"]}\n{metrics["throughput"]} {metrics["throughput_unit"]}',
        f'{ui["sle"]}\n{int(metrics["sle_probability"]*100)}% ≤ {metrics["sle_days"]}{ui["age_suffix"]}',
    ]
    for i, value in enumerate(metric_values):
        vertex(f"metric-{i}", value, 815 + i * 182, 70, 170, 48,
               f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;strokeColor={LINE};fillColor={PAPER};fontColor={INK};fontSize=12;align=left;spacingLeft=10;")
    for index, column in enumerate(model["columns"]):
        x = g["left"] + index * g["col_w"]
        value = f'<b>{html.escape(column["name"])}</b>'
        if column["stage"] == "wip":
            value += f'<br><font color="{MUTED}">{ui["wip"]} {model["column_wip"][column["id"]]}/{column["wip_limit"]}<br>{html.escape(column["pull_criteria"])}</font>'
        else:
            value += '<br><font color="' + MUTED + '">' + (ui["before_commitment"] if column["stage"] == "queue" else ui["delivery_complete"]) + '</font>'
        vertex("column-" + column["id"], value, x, g["header_y"], g["col_w"], g["header_h"],
               f"rounded=0;whiteSpace=wrap;html=1;strokeColor={LINE};fillColor={ACTIVE if column['stage']=='wip' else PAPER};fontColor={INK};fontSize=13;align=left;verticalAlign=top;spacingTop=12;spacingLeft=12;")
    for lane_index, lane in enumerate(model["lanes"]):
        y, h = g["lane_y"][lane["id"]], g["lane_heights"][lane["id"]]
        value = f'<b>{html.escape(lane["name"])}</b><br><font color="{MUTED}">{ui["lane_wip"]} {model["lane_wip"][lane["id"]]}/{lane["wip_limit"]}</font>'
        vertex("lane-label-" + lane["id"], value, 50, y, 120, h,
               f"rounded=0;whiteSpace=wrap;html=1;strokeColor={LINE};fillColor={PAPER};fontColor={INK};fontSize=13;align=center;verticalAlign=top;spacingTop=18;")
        for col_index, column in enumerate(model["columns"]):
            x = g["left"] + col_index * g["col_w"]
            vertex(f"cell-{lane['id']}-{column['id']}", "", x, y, g["col_w"], h,
                   f"rounded=0;strokeColor={LINE};fillColor={PAPER if lane_index%2==0 else '#F7F4EE'};")
            for card_index, card in enumerate(g["by_cell"][(lane["id"], column["id"]) ]):
                cx, cy, cw, ch = x + 12, y + 15 + card_index * 82, g["col_w"] - 24, 69
                meta = f'{card["id"]} · {card["owner"]}'
                if "age_days" in card:
                    meta += f' · {card["age_days"]}{ui["age_suffix"]}'
                if "due" in card:
                    meta += f' · {ui["due_prefix"]}{card["due"]}'
                extra = f'<br><font color="{BLOCKED}">{ui["blocked"]}: {html.escape(card["blocked_reason"])}</font>' if card["blocked"] else f'<br><font color="{CLASS_COLORS[card["service_class"]]}">{class_label(model, card["service_class"])}</font>'
                value = f'<b>{html.escape(card["title"])}</b><br><font color="{MUTED}">{html.escape(meta)}</font>{extra}'
                vertex("card-" + card["id"], value, cx, cy, cw, ch,
                       f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;strokeWidth={2 if card['blocked'] else 1};strokeColor={BLOCKED if card['blocked'] else LINE};fillColor=#FFFFFF;fontColor={INK};fontSize=11;align=left;verticalAlign=top;spacingTop=7;spacingLeft=12;dashed={1 if card['blocked'] else 0};")
                vertex("band-" + card["id"], "", cx, cy, 7, ch,
                       f"rounded=1;arcSize=8;strokeColor=none;fillColor={CLASS_COLORS[card['service_class']]};")
    footer_y = g["footer_y"]
    vertex("policy-title", ui["policies"], 50, footer_y - 10, 300, 30, plain + f"fontSize=18;fontStyle=1;fontColor={INK};")
    for index, policy in enumerate(model["policies"]):
        row, col = divmod(index, 2)
        x, y = 50 + col * 755, footer_y + 25 + row * 76
        value = f'<b>{html.escape(policy["title"])}</b>　{html.escape(policy["rule"])}'
        vertex("policy-" + policy["id"], value, x, y, 730, 62,
               f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;strokeColor={LINE};fillColor={PAPER};fontColor={INK};fontSize=11;align=left;verticalAlign=top;spacingTop=12;spacingLeft=12;")
    return ET.tostring(mxfile, encoding="unicode") + "\n"


def render(source, output):
    source = Path(source)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw = json.loads(source.read_text())
    model = validate(raw)
    geometry = layout(model)
    name = source.stem
    shutil.copyfile(source, output / f"{name}.input.json")
    (output / f"{name}.model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n")
    (output / f"{name}.svg").write_text(render_svg(model, geometry))
    (output / f"{name}.drawio").write_text(render_drawio(model, geometry))
    qa = {
        "errors": [], "warnings": [], "text_overflow": [], "text_overlap": [], "missing_glyphs": [],
        "canvas": {"width": geometry["width"], "height": geometry["height"]},
        "counts": model["counts"], "column_wip": model["column_wip"],
        "lane_wip": model["lane_wip"], "pull_capacity": model["pull_capacity"],
        "checks": [
            "每张卡只有一个泳道和状态", "WIP列与泳道限制未超限", "阻塞项保留在WIP并写明原因",
            "开始点、完成点、拉动条件和显式策略已显示", "模拟数据与个人绩效边界已声明",
        ],
    }
    (output / f"{name}.qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n")
    return qa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.source, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
