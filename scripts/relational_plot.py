#!/usr/bin/env python3
"""Validate and render four relationship/scientific visuals from editable JSON.

Supported modes: alluvial, sunburst, chord, surface. The renderer never
interpolates missing values and records the numeric structure used to draw.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


INK = "#30302D"
MUTED = "#6D6A63"
BG = "#F1EFEB"
GRID = "#D8D3C8"
COLORS = ["#AC6046", "#58705A", "#657487", "#C1965B", "#8A6F78", "#7A8470"]


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _base(data, mode):
    _need(data.get("mode") == mode, f"mode must be {mode}")
    _need(isinstance(data.get("title"), str) and data["title"].strip(), "title required")


def _alluvial(data):
    _base(data, "alluvial")
    stages = data.get("stages")
    links = data.get("links")
    _need(isinstance(stages, list) and 2 <= len(stages) <= 4, "alluvial requires 2-4 stages")
    _need(isinstance(links, list) and links, "alluvial links required")
    stage_ids = [s.get("id") for s in stages]
    _unique(stage_ids, "stage ids must be unique")
    categories = {}
    for stage in stages:
        _need(stage.get("id") and stage.get("label"), "each stage needs id and label")
        cats = stage.get("categories")
        _need(isinstance(cats, list) and cats, "each stage needs categories")
        ids = [c.get("id") for c in cats]
        _need(all(ids) and all(c.get("label") for c in cats), "each category needs id and label")
        _unique(ids, f"category ids must be unique within {stage['id']}")
        categories[stage["id"]] = ids
    inbound = {(sid, cid): 0.0 for sid in stage_ids for cid in categories[sid]}
    outbound = dict(inbound)
    normalized = []
    for link in links:
        value = link.get("value")
        _need(_finite(value) and value >= 0, "link weights must be finite and nonnegative")
        source_stage = link.get("source_stage")
        target_stage = link.get("target_stage")
        _need(source_stage in stage_ids and target_stage in stage_ids, "link references unknown stage")
        source_index = stage_ids.index(source_stage)
        _need(source_index + 1 < len(stage_ids) and stage_ids[source_index + 1] == target_stage,
              "alluvial links must connect adjacent stages")
        source = link.get("source")
        target = link.get("target")
        _need(source in categories[source_stage] and target in categories[target_stage],
              "link references unknown category")
        outbound[(source_stage, source)] += float(value)
        inbound[(target_stage, target)] += float(value)
        normalized.append({**link, "value": float(value)})
    tolerance = 1e-9
    for stage_index in range(1, len(stages) - 1):
        sid = stage_ids[stage_index]
        for cid in categories[sid]:
            _need(math.isclose(inbound[(sid, cid)], outbound[(sid, cid)], rel_tol=tolerance, abs_tol=tolerance),
                  f"flow is not conserved at {sid}/{cid}")
    totals = []
    node_values = {}
    for stage_index, stage in enumerate(stages):
        sid = stage["id"]
        values = {}
        for cid in categories[sid]:
            values[cid] = outbound[(sid, cid)] if stage_index < len(stages) - 1 else inbound[(sid, cid)]
        total = sum(values.values())
        _need(total > 0, f"stage {sid} has no positive flow")
        totals.append(total)
        node_values[sid] = values
    _need(all(math.isclose(total, totals[0], rel_tol=tolerance, abs_tol=tolerance) for total in totals),
          "all stages must represent the same cohort total")
    return {
        "mode": "alluvial",
        "stage_totals": dict(zip(stage_ids, totals)),
        "node_values": node_values,
        "links": normalized,
        "conservation": "passed",
        "cohort_total": totals[0],
    }


def _sunburst(data):
    _base(data, "sunburst")
    root = data.get("root")
    _need(isinstance(root, dict), "sunburst root required")
    ids = set()
    flat = []

    def visit(node, depth, path):
        node_id = node.get("id")
        label = node.get("label")
        _need(node_id and label, "each hierarchy node needs id and label")
        _need(node_id not in ids, "hierarchy node ids must be unique")
        ids.add(node_id)
        children = node.get("children", [])
        _need(isinstance(children, list), "children must be a list")
        if children:
            subtotal = sum(visit(child, depth + 1, path + [node_id]) for child in children)
            if "value" in node:
                _need(_finite(node["value"]) and math.isclose(float(node["value"]), subtotal, rel_tol=1e-9, abs_tol=1e-9),
                      f"internal value must equal child sum at {node_id}")
            value = subtotal
        else:
            value = node.get("value")
            _need(_finite(value) and value >= 0, f"leaf {node_id} needs a finite nonnegative value")
            value = float(value)
        flat.append({"id": node_id, "label": label, "depth": depth, "path": path + [node_id], "value": value})
        return value

    total = visit(root, 0, [])
    _need(total > 0, "sunburst total must be positive")
    max_depth = max(node["depth"] for node in flat)
    _need(max_depth <= 4, "static sunburst supports at most four hierarchy levels")
    return {"mode": "sunburst", "total": total, "max_depth": max_depth, "nodes": flat, "hierarchy_sum": "passed"}


def _chord(data):
    _base(data, "chord")
    groups = data.get("groups")
    matrix = data.get("matrix")
    _need(isinstance(groups, list) and 2 <= len(groups) <= 10, "chord requires 2-10 groups")
    _need(all(g.get("id") and g.get("label") for g in groups), "each chord group needs id and label")
    ids = [g["id"] for g in groups]
    _unique(ids, "chord group ids must be unique")
    n = len(groups)
    _need(isinstance(matrix, list) and len(matrix) == n and all(isinstance(row, list) and len(row) == n for row in matrix),
          "chord matrix must be square and match groups")
    _need(all(_finite(value) and value >= 0 for row in matrix for value in row),
          "chord matrix values must be finite and nonnegative")
    matrix = [[float(value) for value in row] for row in matrix]
    outbound = [sum(row) for row in matrix]
    inbound = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    _need(sum(outbound) > 0, "chord matrix must contain positive flow")
    _need(all(outbound[i] + inbound[i] > 0 for i in range(n)), "every chord group must participate")
    direction = data.get("direction")
    _need(direction in ("directed", "undirected"), "direction must be directed or undirected")
    if direction == "undirected":
        _need(all(math.isclose(matrix[i][j], matrix[j][i], rel_tol=1e-9, abs_tol=1e-9)
                  for i in range(n) for j in range(n)), "undirected chord matrix must be symmetric")
    return {
        "mode": "chord",
        "direction": direction,
        "groups": ids,
        "outbound": outbound,
        "inbound": inbound,
        "incident": [outbound[i] + inbound[i] for i in range(n)],
        "total": sum(outbound),
        "matrix_shape": [n, n],
    }


def _surface(data):
    _base(data, "surface")
    x = data.get("x")
    y = data.get("y")
    z = data.get("z")
    _need(isinstance(x, list) and len(x) >= 2 and all(_finite(v) for v in x), "surface x must be finite values")
    _need(isinstance(y, list) and len(y) >= 2 and all(_finite(v) for v in y), "surface y must be finite values")
    _need(all(a < b for a, b in zip(x, x[1:])), "surface x must be strictly increasing")
    _need(all(a < b for a, b in zip(y, y[1:])), "surface y must be strictly increasing")
    _need(isinstance(z, list) and len(z) == len(y) and all(isinstance(row, list) and len(row) == len(x) for row in z),
          "surface z shape must be len(y) by len(x)")
    _need(all(_finite(v) for row in z for v in row), "surface z values must be finite")
    values = [float(v) for row in z for v in row]
    return {
        "mode": "surface",
        "grid_shape": [len(y), len(x)],
        "measured_points": len(values),
        "x_range": [float(x[0]), float(x[-1])],
        "y_range": [float(y[0]), float(y[-1])],
        "z_range": [min(values), max(values)],
        "interpolation": "none; only the supplied regular grid is rendered",
    }


ANALYZERS = {"alluvial": _alluvial, "sunburst": _sunburst, "chord": _chord, "surface": _surface}


def analyze(data):
    mode = data.get("mode")
    _need(mode in ANALYZERS, "mode must be alluvial, sunburst, chord or surface")
    result = ANALYZERS[mode](data)
    result["assumptions"] = data.get("assumptions", [])
    result["data_status"] = data.get("data_status", "unspecified")
    return result


def _font():
    from matplotlib import font_manager

    path = Path("/System/Library/Fonts/STHeiti Light.ttc")
    if path.exists():
        font_manager.fontManager.addfont(path)
        return font_manager.FontProperties(fname=path).get_name()
    return "DejaVu Sans"


def _figure(data, projection=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update({
        "font.family": _font(), "font.size": 11, "text.color": INK,
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": GRID, "axes.unicode_minus": False,
        "svg.fonttype": "none", "svg.hashsalt": "diagram-studio-relational-v1",
    })
    fig = plt.figure(figsize=(12.8, 7.2), facecolor=BG)
    ax = fig.add_axes([0.08, 0.13, 0.84, 0.68], projection=projection)
    ax.set_facecolor(BG)
    fig.text(0.08, 0.92, data["title"], fontsize=23, weight="medium", color=INK)
    fig.text(0.08, 0.865, data.get("subtitle", ""), fontsize=10.5, color=MUTED)
    fig.text(0.08, 0.045, data.get("footer", "模拟数据 · 输入与计算摘要随图保留"), fontsize=9.5, color=MUTED)
    return fig, ax


def _render_alluvial(data, meta):
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import PathPatch, Rectangle

    fig, ax = _figure(data)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    stages = data["stages"]
    xs = [0.04 + i * 0.92 / (len(stages) - 1) for i in range(len(stages))]
    gap = 0.018
    low, high = 0.07, 0.90
    available = high - low
    positions = {}
    for stage_index, stage in enumerate(stages):
        values = meta["node_values"][stage["id"]]
        total = sum(values.values())
        usable = available - gap * (len(stage["categories"]) - 1)
        cursor = high
        for category_index, category in enumerate(stage["categories"]):
            height = usable * values[category["id"]] / total
            bottom = cursor - height
            positions[(stage["id"], category["id"])] = [bottom, cursor]
            color = COLORS[category_index % len(COLORS)]
            ax.add_patch(Rectangle((xs[stage_index] - 0.013, bottom), 0.026, height,
                                   facecolor=color, edgecolor=BG, linewidth=1.1, zorder=3))
            side = -1 if stage_index == 0 else 1 if stage_index == len(stages) - 1 else (-1 if stage_index % 2 == 0 else 1)
            ax.text(xs[stage_index] + side * 0.024, (bottom + cursor) / 2,
                    f"{category['label']}  {values[category['id']]:g}",
                    ha="right" if side < 0 else "left", va="center", fontsize=9.5, color=INK)
            cursor = bottom - gap
        ax.text(xs[stage_index], 0.97, stage["label"], ha="center", va="top", fontsize=12, weight="medium")
    source_offsets = {key: value[0] for key, value in positions.items()}
    target_offsets = {key: value[0] for key, value in positions.items()}
    total = meta["cohort_total"]
    usable_by_stage = {
        s["id"]: available - gap * (len(s["categories"]) - 1) for s in stages
    }
    color_by_source = {}
    for stage in stages:
        for index, category in enumerate(stage["categories"]):
            color_by_source[(stage["id"], category["id"])] = COLORS[index % len(COLORS)]
    for link in meta["links"]:
        if link["value"] == 0:
            continue
        source_key = (link["source_stage"], link["source"])
        target_key = (link["target_stage"], link["target"])
        source_index = [s["id"] for s in stages].index(link["source_stage"])
        target_index = source_index + 1
        source_height = link["value"] / total * usable_by_stage[link["source_stage"]]
        target_height = link["value"] / total * usable_by_stage[link["target_stage"]]
        sy0, sy1 = source_offsets[source_key], source_offsets[source_key] + source_height
        ty0, ty1 = target_offsets[target_key], target_offsets[target_key] + target_height
        source_offsets[source_key] = sy1
        target_offsets[target_key] = ty1
        x0, x1 = xs[source_index] + 0.013, xs[target_index] - 0.013
        c0, c1 = x0 + (x1 - x0) * 0.42, x1 - (x1 - x0) * 0.42
        vertices = [(x0, sy0), (c0, sy0), (c1, ty0), (x1, ty0),
                    (x1, ty1), (c1, ty1), (c0, sy1), (x0, sy1), (x0, sy0)]
        codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor=color_by_source[source_key],
                               edgecolor="none", alpha=0.34, zorder=1))
    fig.text(0.92, 0.045, f"同一群体总量 {meta['cohort_total']:g}", ha="right", fontsize=9.5, color=MUTED)
    return fig


def _render_sunburst(data, meta):
    from matplotlib.patches import Circle, Wedge

    fig, ax = _figure(data)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-0.90, 0.90); ax.set_ylim(-0.82, 0.82)
    ring = 0.24
    root = data["root"]
    ax.add_patch(Circle((0, 0), ring * 0.90, facecolor="#E5DFD5", edgecolor=BG, linewidth=1.2))
    ax.text(0, 0.035, root["label"], ha="center", va="center", fontsize=11, weight="medium")
    ax.text(0, -0.075, f"{meta['total']:g}", ha="center", va="center", fontsize=10, color=MUTED)

    def value(node):
        children = node.get("children", [])
        return sum(value(c) for c in children) if children else float(node["value"])

    def draw(node, start, span, depth, color_index):
        cursor = start
        children = node.get("children", [])
        for index, child in enumerate(children):
            child_span = span * value(child) / value(node)
            inner = ring * depth
            color = COLORS[(color_index + index) % len(COLORS)]
            ax.add_patch(Wedge((0, 0), inner + ring, cursor, cursor + child_span,
                               width=ring * 0.94, facecolor=color,
                               alpha=max(0.42, 0.88 - 0.15 * depth), edgecolor=BG, linewidth=1.2))
            mid = math.radians(cursor + child_span / 2)
            if child_span >= 10:
                radius = inner + ring * 0.50
                ax.text(radius * math.cos(mid), radius * math.sin(mid), child["label"],
                        ha="center", va="center", fontsize=8.6, color=INK,
                        rotation=(cursor + child_span / 2 if 90 < (cursor + child_span / 2) % 360 < 270 else cursor + child_span / 2 - 180),
                        rotation_mode="anchor")
            draw(child, cursor, child_span, depth + 1, color_index + index)
            cursor += child_span

    draw(root, 90, 360, 1, 0)
    fig.text(0.92, 0.045, f"层级总量 {meta['total']:g} · {meta['max_depth']} 层", ha="right", fontsize=9.5, color=MUTED)
    return fig


def _polar(radius, degrees):
    angle = math.radians(degrees)
    return radius * math.cos(angle), radius * math.sin(angle)


def _render_chord(data, meta):
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import PathPatch, Wedge

    fig, ax = _figure(data)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-1.34, 1.34); ax.set_ylim(-1.16, 1.16)
    n = len(data["groups"])
    gap = 5.0
    incident = meta["incident"]
    total_incident = sum(incident)
    usable = 360 - n * gap
    group_ranges = []
    cursor = 90.0
    for index, group in enumerate(data["groups"]):
        span = usable * incident[index] / total_incident
        group_ranges.append((cursor, cursor + span))
        ax.add_patch(Wedge((0, 0), 1.0, cursor, cursor + span, width=0.10,
                           facecolor=COLORS[index % len(COLORS)], edgecolor=BG, linewidth=1.2))
        mid = cursor + span / 2
        x, y = _polar(1.13, mid)
        ax.text(x, y, f"{group['label']}\n出 {meta['outbound'][index]:g} / 入 {meta['inbound'][index]:g}",
                ha="left" if x >= 0 else "right", va="center", fontsize=9.2, color=INK)
        cursor += span + gap
    out_cursor = [a for a, _ in group_ranges]
    in_cursor = [a + (b - a) * (meta["outbound"][i] / incident[i]) for i, (a, b) in enumerate(group_ranges)]
    out_scale = [(b - a) / incident[i] for i, (a, b) in enumerate(group_ranges)]
    in_scale = out_scale[:]
    matrix = data["matrix"]
    for i in range(n):
        for j in range(n):
            value = float(matrix[i][j])
            if value <= 0:
                continue
            source_a = out_cursor[i]
            source_b = source_a + value * out_scale[i]
            target_a = in_cursor[j]
            target_b = target_a + value * in_scale[j]
            out_cursor[i] = source_b
            in_cursor[j] = target_b
            s0 = _polar(0.88, source_a); s1 = _polar(0.88, source_b)
            t0 = _polar(0.88, target_a); t1 = _polar(0.88, target_b)
            vertices = [s0, (0, 0), (0, 0), t1, t0, (0, 0), (0, 0), s1, s0]
            codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                     MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor=COLORS[i % len(COLORS)],
                                   edgecolor=BG, linewidth=0.35, alpha=0.42))
            if data["direction"] == "directed":
                mid = (target_a + target_b) / 2
                tx, ty = _polar(0.885, mid)
                ax.plot([tx], [ty], marker=(3, 0, mid - 90), markersize=5.5,
                        color=COLORS[i % len(COLORS)], markeredgecolor=BG, markeredgewidth=0.4)
    fig.text(0.92, 0.045, f"有向流总量 {meta['total']:g} · 箭头位于流入端", ha="right", fontsize=9.5, color=MUTED)
    return fig


def _render_surface(data, meta):
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    fig, ax = _figure(data, projection="3d")
    x = np.asarray(data["x"], float)
    y = np.asarray(data["y"], float)
    z = np.asarray(data["z"], float)
    xx, yy = np.meshgrid(x, y)
    cmap = LinearSegmentedColormap.from_list("warm-scientific", ["#657487", "#E1D6C5", "#AC6046"])
    surface = ax.plot_surface(xx, yy, z, cmap=cmap, edgecolor="#F1EFEB", linewidth=0.7,
                              antialiased=True, alpha=0.91, rstride=1, cstride=1)
    ax.scatter(xx.ravel(), yy.ravel(), z.ravel(), s=17, c=INK, depthshade=False, label="实测网格点")
    ax.set_xlabel(data.get("x_label", "X"), labelpad=9)
    ax.set_ylabel(data.get("y_label", "Y"), labelpad=9)
    ax.set_zlabel(data.get("z_label", "Z"), labelpad=7)
    ax.view_init(elev=float(data.get("view", {}).get("elev", 28)), azim=float(data.get("view", {}).get("azim", -132)))
    ax.xaxis.pane.set_facecolor(BG); ax.yaxis.pane.set_facecolor(BG); ax.zaxis.pane.set_facecolor(BG)
    ax.xaxis.pane.set_edgecolor(GRID); ax.yaxis.pane.set_edgecolor(GRID); ax.zaxis.pane.set_edgecolor(GRID)
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.99), frameon=False)
    cbar = fig.colorbar(surface, ax=ax, shrink=0.62, pad=0.08, aspect=25)
    cbar.set_label(data.get("z_label", "Z"))
    fig.text(0.92, 0.045, f"{meta['measured_points']} 个实测网格点 · 未插值", ha="right", fontsize=9.5, color=MUTED)
    return fig


RENDERERS = {"alluvial": _render_alluvial, "sunburst": _render_sunburst, "chord": _render_chord, "surface": _render_surface}


def render(data, output, stem=None):
    import matplotlib
    import matplotlib.pyplot as plt

    meta = analyze(data)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stem = stem or data.get("id") or data["mode"]
    fig = RENDERERS[data["mode"]](data, meta)
    fig.savefig(output / f"{stem}.svg", facecolor=BG, metadata={"Date": None})
    fig.savefig(output / f"{stem}.png", facecolor=BG, dpi=150,
                metadata={"Software": "diagram-studio relational_plot.py"})
    plt.close(fig)
    (output / f"{stem}.input.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    meta["matplotlib_version"] = matplotlib.__version__
    meta["scope"] = "验证输入结构和绘图计算；不把模拟数据、迁移关系或观察关联解释为现实因果"
    (output / f"{stem}.calculation.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    qa = {
        "mode": data["mode"], "errors": [], "warnings": [], "layout_issues": [],
        "checks": ["input schema", "finite numeric values", "mode-specific invariants", "SVG and PNG generated"],
        "visual_review": "pending; open the actual SVG/PNG before acceptance",
    }
    (output / f"{stem}.qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n")
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    parser.add_argument("--stem")
    args = parser.parse_args()
    source = Path(args.input)
    try:
        result = render(json.loads(source.read_text()), args.out, args.stem or source.stem)
        print(json.dumps(result, ensure_ascii=False))
    except (KeyError, ValueError, ImportError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
