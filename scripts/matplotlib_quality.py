"""Rendered-output checks shared by Matplotlib diagram backends.

Semantic validators know whether a model is internally consistent.  This module
checks what Matplotlib actually placed on the page after font selection and
layout.  It deliberately reports inspection results; it does not claim a human
has approved visual design or domain-specific facts.
"""
from __future__ import annotations

from itertools import combinations


def mark_container(text, ax, bounds, label):
    """Associate a Text artist with an axes-data rectangle for overflow checks."""
    text._diagram_quality_container = (ax, tuple(bounds), str(label))
    return text


def _box(box):
    return {
        'x0': round(float(box.x0), 2),
        'y0': round(float(box.y0), 2),
        'x1': round(float(box.x1), 2),
        'y1': round(float(box.y1), 2),
    }


def _outside(inner, outer, tolerance=0.75):
    return (
        inner.x0 < outer.x0 - tolerance or inner.y0 < outer.y0 - tolerance
        or inner.x1 > outer.x1 + tolerance or inner.y1 > outer.y1 + tolerance
    )


def _summary(text, limit=72):
    compact = ' '.join(text.split())
    return compact if len(compact) <= limit else compact[:limit - 1] + '…'


def inspect_figure(fig, captured_warnings=()):
    """Return concrete page/text/glyph findings from an already-rendered figure."""
    from matplotlib.text import Text
    from matplotlib.transforms import Bbox

    renderer = fig.canvas.get_renderer()
    page = fig.bbox
    text_rows = []
    overflow = []
    for index, artist in enumerate(fig.findobj(Text)):
        value = artist.get_text()
        if not artist.get_visible() or not value or not value.strip():
            continue
        box = artist.get_window_extent(renderer)
        row = {'id': index, 'text': _summary(value), 'bbox_px': _box(box)}
        text_rows.append((artist, box, row))
        if _outside(box, page):
            overflow.append({**row, 'scope': 'page', 'page_bbox_px': _box(page)})
        container = getattr(artist, '_diagram_quality_container', None)
        if container:
            ax, bounds, label = container
            x, y, width, height = bounds
            parent = ax.transData.transform_bbox(Bbox.from_bounds(x, y, width, height))
            if _outside(box, parent):
                overflow.append({**row, 'scope': 'container', 'container': label, 'container_bbox_px': _box(parent)})

    overlaps = []
    for (artist_a, box_a, row_a), (artist_b, box_b, row_b) in combinations(text_rows, 2):
        x = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
        y = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
        if x > 1 and y > 1:
            overlaps.append({
                'first': row_a,
                'second': row_b,
                'overlap_px': {'width': round(float(x), 2), 'height': round(float(y), 2)},
            })

    glyphs = []
    for warning in captured_warnings:
        message = str(getattr(warning, 'message', warning))
        if 'Glyph' in message and ('missing' in message or 'not found' in message):
            glyphs.append(message)

    return {
        'page_bbox_px': _box(page),
        'rendered_texts': len(text_rows),
        'text_overflow': overflow,
        'text_overlap': overlaps,
        'missing_glyphs': sorted(set(glyphs)),
        'inspection': 'actual Matplotlib text bounding boxes after draw',
    }


def quality_payload(semantic_validation, visual, claim_boundary):
    """Use stable QA fields while making unrun/manual checks explicit."""
    overflow = visual['text_overflow']
    glyphs = visual['missing_glyphs']
    overlaps = visual['text_overlap']
    errors = [f"text overflow: {row['text']} ({row['scope']})" for row in overflow]
    errors.extend(f'missing glyph: {message}' for message in glyphs)
    warnings = [
        f"text overlap: {row['first']['text']} / {row['second']['text']}"
        for row in overlaps
    ]
    return {
        'errors': errors,
        'warnings': warnings,
        'layout_issues': overflow + overlaps,
        'text_overflow': overflow,
        'text_overlap': overlaps,
        'missing_glyphs': glyphs,
        'semantic_validation': semantic_validation,
        'rendered_visual_check': 'passed' if not errors and not warnings else 'issues-found',
        'manual_visual_review': 'not-run',
        'inspection': visual['inspection'],
        'rendered_texts': visual['rendered_texts'],
        'page_bbox_px': visual['page_bbox_px'],
        'claim_boundary': claim_boundary,
    }
