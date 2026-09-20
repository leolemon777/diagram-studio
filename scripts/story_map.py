"""Measured user-story maps: ordered activities × explicit release slices.

No calendar inference, priority scoring, vote generation or dependency scheduling.
"""
from collections import defaultdict
import math
import re
from adaptive_layout import METRICS
from refined_layout import text, top


def validate(data):
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    def words(value, field):
        require(isinstance(value, str) and bool(value.strip()), field + ' must be non-empty text')
    words(data.get('persona'), 'persona')
    words(data.get('goal'), 'goal')
    collections = {}
    for key in ('activities', 'releases', 'stories'):
        values = data.get(key)
        require(isinstance(values, list) and bool(values), key + ' must be a non-empty list')
        ids = set()
        for item in values:
            require(isinstance(item, dict), key + ' items must be objects')
            ident = item.get('id')
            require(isinstance(ident, str) and bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', ident)), key + ' requires a stable ASCII id')
            require(ident not in ids, 'duplicate ' + key + ' id: ' + ident)
            ids.add(ident)
            words(item.get('label'), key + '.' + ident + '.label')
            if key == 'releases':
                words(item.get('goal'), 'release goal')
            if key == 'stories':
                for field in ('activity', 'release'):
                    words(item.get(field), 'story ' + field)
                for field in ('detail', 'source'):
                    if field in item:
                        words(item[field], 'story ' + field)
        collections[key] = ids
    for story in data['stories']:
        require(story['activity'] in collections['activities'], 'unknown activity: ' + story['activity'])
        require(story['release'] in collections['releases'], 'unknown release: ' + story['release'])
    # Reject unsupported relation/date fields rather than silently omitting their meaning.
    for field in ('edges', 'dependencies', 'votes', 'dates'):
        require(field not in data, field + ' is unsupported in a story map; use a linked diagram')
    for story in data['stories']:
        for field in ('depends', 'depends_on', 'votes', 'start', 'end'):
            require(field not in story, 'story field ' + field + ' is unsupported; use a linked diagram')
    return data


def build(scene, data):
    validate(data)
    en = str(data.get('language', 'zh')).startswith('en')
    t = lambda zh, english: english if en else zh
    scene.meta['refined_layout'] = {'version': 43, 'profile': 'story-map', 'manual_visual_review': 'not-run'}
    count = len(data['activities'])
    # Width may grow; body text never shrinks to force a large map into one slide.
    scene.w = max(scene.w, 128 + 218 + count * 306)
    left, rail, gap = 64, 218, 16
    start = left + rail
    colw = (scene.w - 128 - rail) / count
    cardw = colw - gap
    def height(value, width, size):
        return math.ceil(len(METRICS.wrap(value, width, size)) * size * 1.35) + 4
    def fields(story):
        parts = [(story['id'], 14, 'accent', False), (story['label'], 20, 'ink', True)]
        if story.get('detail'):
            parts.append((story['detail'], 17, 'ink', False))
        if story.get('source'):
            parts.append((t('来源：', 'Source: ') + story['source'], 14, 'muted', False))
        return parts
    def card_height(story):
        return 32 + sum(height(v, cardw - 32, fs) + 7 for v, fs, _, _ in fields(story))
    cells = defaultdict(list)
    for story in data['stories']:
        cells[story['release'], story['activity']].append(story)
    y = top(scene)
    h = text(scene, left, y, scene.w - 128, t('用户 / ', 'User / ') + data['persona'] + '  ·  ' + data['goal'], 19)
    y += h + 24
    h = text(scene, left, y, scene.w - 128, t('从左向右：用户活动  /  从上向下：交付切片  /  空位表示未安排，不是零', 'Left to right: user activities  /  Top to bottom: release slices  /  Empty means not scheduled, not zero'), 15, 'muted')
    y += h + 24
    activity_ids = [f'{i+1:02d} / {a["id"]}' for i, a in enumerate(data['activities'])]
    headerh = max(height(ident, cardw - 24, 14) + 8 + height(a['label'], cardw - 24, 23)
                  for ident, a in zip(activity_ids, data['activities'])) + 20
    text(scene, left, y + 20, rail - 32, t('交付目标', 'Release outcome'), 17, 'muted')
    for i, activity in enumerate(data['activities']):
        x = start + i * colw
        idh = text(scene, x + 12, y, cardw - 24, activity_ids[i], 14, 'accent')
        text(scene, x + 12, y + idh + 8, cardw - 24, activity['label'], 23, bold=True)
    y += headerh
    rows, assignments = [], []
    for row, release in enumerate(data['releases']):
        contenth = max([sum(card_height(story) + 14 for story in cells[release['id'], a['id']]) for a in data['activities']] + [96])
        railh = height(release['label'], rail - 42, 23) + height(release['goal'], rail - 42, 17) + 80
        rowh = max(contenth + 42, railh + 30)
        scene.edge(points=[(left, y), (scene.w - 64, y)], arrow=False, tone='line', width=1)
        scene.add(left, y + 26, 3, rowh - 52, fill='accent' if row == 0 else 'line', stroke='none', radius=0, check=False)
        ry = y + 24
        ry += text(scene, left + 18, ry, rail - 42, release['id'], 14, 'accent') + 10
        ry += text(scene, left + 18, ry, rail - 42, release['label'], 23, bold=True) + 12
        text(scene, left + 18, ry, rail - 42, release['goal'], 17, 'muted')
        for i, activity in enumerate(data['activities']):
            x, cy = start + i * colw, y + 24
            stories = cells[release['id'], activity['id']]
            if not stories:
                text(scene, x + 16, cy + 18, cardw - 32, t('— 未安排', '— Not scheduled'), 16, 'muted')
            for story in stories:
                ch = card_height(story)
                scene.add(x, cy, cardw, ch, id='story-' + story['id'], kind='panel', fill='panel', stroke='line', radius=3, check=False)
                ty = cy + 16
                for j, (value, fs, tone, bold) in enumerate(fields(story)):
                    ty += text(scene, x + 16, ty, cardw - 32, value, fs, tone, bold=bold, id=f'storytext-{story["id"]}-{j}') + 7
                assignments.append({'story': story['id'], 'activity': activity['id'], 'release': release['id'], 'box': [x, cy, cardw, ch]})
                cy += ch + 14
        rows.append({'release': release['id'], 'y': y, 'height': rowh})
        y += rowh
    text(scene, left, y + 16, scene.w - 128, t('每个故事只安排一次；切片目标需由团队确认。此图不推断日期、工期或优先级分数。', 'Each story is assigned once. Confirm slice outcomes with the team. Dates, durations and priority scores are not inferred.'), 15, 'muted')
    scene.meta['story_map'] = {'activities': [a['id'] for a in data['activities']], 'releases': rows, 'assignments': assignments, 'calendar_scale': False}
