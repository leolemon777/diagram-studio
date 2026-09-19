"""Content-aware layouts for ordinary graphs, trees and layer architectures.

No remote service. Text measurements, candidate selection and routing are kept
separate from the input model. Geometry is evidence, not an aesthetic verdict.
"""
from __future__ import annotations

import copy
import functools
import heapq
import math
import os
import re
from pathlib import Path

FONT_PATHS = [
    '/System/Library/Fonts/STHeiti Light.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    'C:/Windows/Fonts/msyh.ttc',
]


class Metrics:
    def __init__(self):
        self.path = next((p for p in [os.environ.get('DIAGRAM_FONT', '')] + FONT_PATHS if p and Path(p).is_file()), None)
        self.family = 'Heiti SC' if self.path and 'STHeiti' in self.path else 'Noto Sans CJK SC'
        self.mode = 'conservative-estimate'
        self.loader = None
        try:
            from PIL import ImageFont
            if self.path:
                self.loader = ImageFont.truetype
                self.family = self.font(20).getname()[0]
                self.mode = 'font-glyph-metrics'
        except (ImportError, OSError):
            self.loader = None

    @functools.lru_cache(maxsize=64)
    def font(self, size):
        return self.loader(self.path, round(size))

    @functools.lru_cache(maxsize=32768)
    def width(self, text, size):
        if self.loader:
            # Reserve 4 percent for weight/rendering differences.
            return float(self.font(size).getlength(str(text))) * 1.04
        return sum(size * (1.04 if ord(c) > 255 else .66) for c in str(text))

    def wrap(self, text, width, size):
        if width < size * 2:
            raise ValueError('text column too narrow')
        lines = []
        closing = '，。！？；：、）》】」』,.!?;:)]}'
        opening = '（《【「『([{'
        for para in str(text).split('\n'):
            paragraph_start=len(lines)
            # Latin words stay together when they fit; long identifiers split.
            tokens = re.findall(r'[A-Za-z0-9_./:@+\-]+|[^A-Za-z0-9_./:@+\-]', para)
            row = ''
            for token in tokens:
                pieces = list(token) if self.width(token, size) > width else [token]
                for piece in pieces:
                    if row and self.width(row + piece, size) > width:
                        carry = ''
                        if row[-1] in opening or piece[0] in closing:
                            carry, row = row[-1], row[:-1]
                        if row:
                            lines.append(row.rstrip())
                        row = carry
                    row += piece
            # Balance a short CJK last line rather than leaving a lone character.
            if len(lines)>paragraph_start and row and self.width(row,size)<width*.32 and not re.search(r'[A-Za-z0-9]',row):
                while len(lines[-1])>2 and self.width(row,size)<width*.42 and ord(lines[-1][-1])>255:
                    c=lines[-1][-1]
                    if c in closing or c in opening:break
                    lines[-1]=lines[-1][:-1];row=c+row
            lines.append(row.rstrip())
        return lines or ['']


METRICS = Metrics()


def selected(d):
    mode = d.get('layout', {}).get('mode', 'auto')
    if mode in ('legacy', 'fixed'):
        return False
    if d['type'] in ('tree', 'architecture'):
        return True
    if d['type'] == 'graph':
        positioned = d.get('groups') or any(any(k in n for k in ('x', 'y', 'row', 'col')) for n in d.get('nodes', []))
        return mode == 'adaptive' or not positioned
    return False


def normalize(d):
    """Return the exact source objects/relations, without summarizing labels."""
    nodes, edges, bands = [], [], []
    if d['type'] == 'tree':
        seen = set()
        def visit(n, parent=None, depth=0):
            if n['id'] in seen:
                raise ValueError('tree cycle or duplicate id: ' + n['id'])
            seen.add(n['id'])
            nodes.append({k: copy.deepcopy(v) for k, v in n.items() if k != 'children'})
            nodes[-1]['_rank'] = depth
            if parent is not None:
                edges.append({'from': parent, 'to': n['id'], 'arrow': False})
            for child in n.get('children', []):
                visit(child, n['id'], depth + 1)
        visit(d['root'])
    elif d['type'] == 'architecture':
        for i, layer in enumerate(d['layers']):
            ids = []
            for j, item in enumerate(layer['items']):
                n = {'label': item} if isinstance(item, str) else copy.deepcopy(item)
                n.setdefault('id', f'layer-{i}-item-{j}')
                n.setdefault('tone',layer.get('tone','accent'))
                n['_rank'] = i
                nodes.append(n)
                ids.append(n['id'])
            if not ids:
                raise ValueError('empty architecture layer')
            bands.append({**layer, 'ids': ids})
        if d.get('crosscut'):
            ids = []
            for i, item in enumerate(d['crosscut']):
                n = {'label': item} if isinstance(item, str) else copy.deepcopy(item)
                n.setdefault('id', f'crosscut-{i}')
                n['_rank'] = len(bands)
                nodes.append(n)
                ids.append(n['id'])
            bands.append({'label': d.get('crosscut_title', '横向支撑'), 'ids': ids, 'crosscut': True})
        edges = copy.deepcopy(d.get('edges', []))
    else:
        nodes, edges = copy.deepcopy(d['nodes']), copy.deepcopy(d.get('edges', []))
        if d.get('groups'):
            raise ValueError('adaptive graph requires semantic nodes/edges; preserve coordinate groups with layout.mode=fixed or model the layers explicitly')
    ids = [n['id'] for n in nodes]
    if not nodes or len(set(ids)) != len(ids):
        raise ValueError('empty graph or duplicate node IDs')
    if any(e['from'] not in ids or e['to'] not in ids for e in edges):
        raise ValueError('edge references an unknown node')
    if len(nodes) > 160:
        raise ValueError('more than 160 objects: first organize into linked overview and detail models; do not remove facts')
    return nodes, edges, bands


def dimensions(n, width):
    kind = n.get('kind', 'rect')
    if kind not in ('rect', 'diamond', 'pill', 'ellipse', 'cylinder'):
        raise ValueError('adaptive layout does not support shape ' + kind)
    # A centered text rectangle must fit inside the diamond/ellipse silhouette.
    inset = width * .5 if kind == 'diamond' else width * .25 if kind == 'ellipse' else 40
    lines = [(t, 22, True, 'ink') for t in METRICS.wrap(n['label'], width - inset, 22)]
    if n.get('detail'):
        lines.extend((t, 17, False, 'muted') for t in METRICS.wrap(n['detail'], width - inset, 17))
    text_h = sum(x[1] * 1.35 for x in lines)
    height = math.ceil((text_h * (2 if kind == 'diamond' else 1.45 if kind == 'ellipse' else 1) + 40) / 8) * 8
    return width, max(88, height), lines


def ranks(nodes, edges):
    """Condense strongly connected components, then rank the acyclic graph."""
    ids = [n['id'] for n in nodes]
    adj = {i: [] for i in ids}
    for e in edges:
        adj[e['from']].append(e['to'])
    index, low, stack, active, components = {}, {}, [], set(), []
    def visit(v):
        index[v] = low[v] = len(index)
        stack.append(v); active.add(v)
        for w in adj[v]:
            if w not in index:
                visit(w); low[v] = min(low[v], low[w])
            elif w in active:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); active.remove(w); comp.append(w)
                if w == v:
                    break
            components.append(comp)
    for v in ids:
        if v not in index:
            visit(v)
    owner = {v: i for i, c in enumerate(components) for v in c}
    outgoing = {i: set() for i in range(len(components))}
    incoming = {i: set() for i in outgoing}
    for e in edges:
        a, b = owner[e['from']], owner[e['to']]
        if a != b:
            outgoing[a].add(b); incoming[b].add(a)
    queue = sorted(i for i in incoming if not incoming[i])
    levels = dict.fromkeys(queue, 0)
    while queue:
        a = queue.pop(0)
        for b in sorted(outgoing[a]):
            levels[b] = max(levels.get(b, 0), levels[a] + len(components[a]))
            incoming[b].remove(a)
            if not incoming[b]:
                queue.append(b)
    offsets={v:j for c in components for j,v in enumerate(sorted(c,key=ids.index))}
    return {v: levels[owner[v]] + offsets[v] for v in ids}


def rect(n, pad=0):
    return n['x'] - pad, n['y'] - pad, n['x'] + n['w'] + pad, n['y'] + n['h'] + pad


def intersects(a, b, gap=0):
    return a[0] < b[2] + gap and a[2] > b[0] - gap and a[1] < b[3] + gap and a[3] > b[1] - gap


def segment_hits(a, b, r):
    if abs(a[0] - b[0]) < .001:
        return r[0] < a[0] < r[2] and max(min(a[1], b[1]), r[1]) < min(max(a[1], b[1]), r[3])
    return r[1] < a[1] < r[3] and max(min(a[0], b[0]), r[0]) < min(max(a[0], b[0]), r[2])


def point(n, side):
    x, y, w, h = n['x'], n['y'], n['w'], n['h']
    return {'left': (x, y+h/2), 'right': (x+w, y+h/2), 'top': (x+w/2, y), 'bottom': (x+w/2, y+h)}[side]


def simplify(points):
    result = []
    for p in points:
        if result and p == result[-1]:
            continue
        while len(result) >= 2 and ((result[-2][0] == result[-1][0] == p[0]) or (result[-2][1] == result[-1][1] == p[1])):
            result.pop()
        result.append(p)
    return result


def route(a, b, obstacles, orientation, serial=0):
    """Orthogonal A* over free channels. Never return a path through a node."""
    if a['id']!=b['id'] and abs(a['y']-b['y'])<1:
        sa,sb=('right','left') if b['x']>a['x'] else ('left','right')
    elif orientation == 'snake':
        if abs(a['y']-b['y'])<max(a['h'],b['h']):
            sa,sb=('right','left') if b['x']>a['x'] else ('left','right')
        else:sa,sb=('bottom','top') if b['y']>a['y'] else ('right','right')
    elif orientation in ('down','outline'):
        sa, sb = ('bottom', 'top') if b['y'] > a['y'] else ('right', 'right')
    else:
        sa, sb = ('right', 'left') if b['x'] > a['x'] else ('bottom', 'bottom')
    p, q = point(a, sa), point(b, sb)
    vectors = {'right': (1,0), 'left':(-1,0), 'bottom':(0,1), 'top':(0,-1)}
    av, bv = vectors[sa], vectors[sb]
    clearance = 22 + (serial % 4) * 6
    start = (p[0] + av[0]*clearance, p[1] + av[1]*clearance)
    end = (q[0] + bv[0]*clearance, q[1] + bv[1]*clearance)
    boxes = [rect(n, 12) for n in obstacles]
    xs = sorted(set([start[0], end[0]] + [r[0]-clearance for r in boxes] + [r[2]+clearance for r in boxes]))
    ys = sorted(set([start[1], end[1]] + [r[1]-clearance for r in boxes] + [r[3]+clearance for r in boxes]))
    initial, goal = (xs.index(start[0]), ys.index(start[1]), 0), (xs.index(end[0]), ys.index(end[1]))
    costs, previous = {initial: 0}, {}
    heap = [(0, 0, initial)]
    @functools.lru_cache(maxsize=None)
    def clear(ix, iy, jx, jy):
        return not any(segment_hits((xs[ix],ys[iy]), (xs[jx],ys[jy]), r) for r in boxes)
    found = None
    while heap:
        _, cost, state = heapq.heappop(heap)
        if cost != costs[state]:
            continue
        ix, iy, direction = state
        if (ix,iy) == goal:
            found = state; break
        for jx,jy,axis in ((ix-1,iy,1),(ix+1,iy,1),(ix,iy-1,2),(ix,iy+1,2)):
            if not (0 <= jx < len(xs) and 0 <= jy < len(ys)) or not clear(ix,iy,jx,jy):
                continue
            new = (jx,jy,axis)
            nc = cost + abs(xs[jx]-xs[ix]) + abs(ys[jy]-ys[iy]) + (28 if direction and axis != direction else 0)
            if nc < costs.get(new, math.inf):
                costs[new] = nc; previous[new] = state
                heuristic = abs(xs[jx]-end[0]) + abs(ys[jy]-end[1])
                heapq.heappush(heap, (nc+heuristic,nc,new))
    if found is None:
        raise ValueError('no clear route for ' + a['id'] + ' -> ' + b['id'])
    path = []
    while True:
        path.append((xs[found[0]],ys[found[1]]))
        if found == initial:
            break
        found = previous[found]
    path.reverse()
    if a['id'] == b['id']:
        # Distinct ports make a visible loop, not a zero-length relation.
        sa, sb = 'right', 'bottom'
        p,q = point(a,sa),point(b,sb)
        path = [p,(a['x']+a['w']+clearance,p[1]),(a['x']+a['w']+clearance,a['y']+a['h']+clearance),(q[0],a['y']+a['h']+clearance),q]
        if any(segment_hits(u,v,rect(n,6)) for u,v in zip(path,path[1:]) for n in obstacles if n['id'] != a['id']):
            raise ValueError('self-loop channel blocked')
    else:
        path = [p] + path + [q]
    return simplify(path), sa, sb


def edge_labels(edges, nodes):
    occupied = [rect(n, 8) for n in nodes]
    issues = []
    for i,e in enumerate(edges):
        if not e.get('label'):
            continue
        lines = METRICS.wrap(e['label'], 220, 15)
        width = max(METRICS.width(t,15) for t in lines)+20
        height = len(lines)*21+12
        segments = sorted(zip(e['points'],e['points'][1:]), key=lambda ab:-(abs(ab[1][0]-ab[0][0])+abs(ab[1][1]-ab[0][1])))
        choices = []
        for a,b in segments:
            horizontal = a[1] == b[1]
            for fraction in (.5,.3,.7):
                cx,cy = a[0]+(b[0]-a[0])*fraction,a[1]+(b[1]-a[1])*fraction
                for side in (-1,1):
                    x,y = (cx-width/2, cy+8 if side==1 else cy-height-8) if horizontal else (cx+8 if side==1 else cx-width-8, cy-height/2)
                    box=(x,y,x+width,y+height)
                    if min(x,y) < 16 or any(intersects(box,r) for r in occupied):
                        continue
                    # Labels may sit beside their own line, never on another line.
                    hits=sum(segment_hits(p,q,box) for edge in edges for p,q in zip(edge['points'],edge['points'][1:]))
                    choices.append((hits, abs(fraction-.5), box))
        if not choices:
            issues.append(f'edge label has no free space: {i}'); continue
        hits,_,box = min(choices)
        if hits:
            issues.append(f'edge label overlaps a connector: {i}')
        e['_label_box'] = list(box)
        e['_label_lines'] = lines
        occupied.append(box)
    return issues


def crossing_count(edges):
    count = 0
    for i,e in enumerate(edges):
        for f in edges[i+1:]:
            if set((e.get('source'),e.get('target'))) & set((f.get('source'),f.get('target'))):
                continue
            for a,b in zip(e['points'],e['points'][1:]):
                for c,d in zip(f['points'],f['points'][1:]):
                    if a[0] == b[0] and c[1] == d[1] and min(c[0],d[0]) < a[0] < max(c[0],d[0]) and min(a[1],b[1]) < c[1] < max(a[1],b[1]):
                        count += 1
                    if a[1] == b[1] and c[0] == d[0] and min(a[0],b[0]) < c[0] < max(a[0],b[0]) and min(c[1],d[1]) < a[1] < max(c[1],d[1]):
                        count += 1
    return count


def candidate(source_nodes, source_edges, bands, orientation, width, spacing):
    nodes = []
    for n in source_nodes:
        w,h,lines = dimensions(n,width)
        nodes.append({**n,'w':w,'h':h,'_lines':lines,'font_family':METRICS.family,'text_margin':20,'align':'center'})
    by_id = {n['id']:n for n in nodes}
    levels = {n['id']:n['_rank'] for n in nodes} if all('_rank' in n for n in nodes) else ranks(nodes,source_edges)
    layers = [[n['id'] for n in nodes if levels[n['id']]==r] for r in sorted(set(levels.values()))]
    # Barycentric ordering reduces crossings while preserving source order ties.
    for turn in range(4):
        positions = {v:i for layer in layers for i,v in enumerate(layer)}
        for layer in (layers if turn%2==0 else list(reversed(layers))):
            def score(v):
                adjacent=[e['from'] if e['to']==v else e['to'] for e in source_edges if v in (e['from'],e['to']) and levels[e['from']]!=levels[e['to']]]
                return sum(positions[a] for a in adjacent)/len(adjacent) if adjacent else positions[v]
            layer.sort(key=score)
    panels=[]
    cursor=230.0
    if bands:
        # Semantic layers remain bands; large layers reflow into a grid.
        inner_gap=140 if source_edges else 36
        cols=max(1,min(4,int(1360/(width+inner_gap))))
        for band in bands:
            label_lines=METRICS.wrap(band['label'],1280,20)
            description=METRICS.wrap(band.get('description',''),1280,16) if band.get('description') else []
            head=(100 if source_edges else 36)+len(label_lines)*27+len(description)*22
            top=cursor; y=top+head
            for start in range(0,len(band['ids']),cols):
                row=band['ids'][start:start+cols]
                row_height=max(by_id[v]['h'] for v in row)
                for j,v in enumerate(row):
                    by_id[v].update(x=104+j*(width+inner_gap),y=y)
                y+=row_height+inner_gap
            panels.append({'x':76,'y':top,'w':max(1360,cols*(width+inner_gap)+20),'h':y-top-32,'label':band['label'],'description':band.get('description',''),'label_lines':label_lines,'description_lines':description})
            cursor=y+spacing
    elif orientation=='outline':
        root=layers[0][0]
        children={n['id']:[] for n in nodes}
        for e in source_edges:children[e['from']].append(e['to'])
        branches=children[root]
        cols=min(4,len(branches)) or 1
        lane=width+spacing+64
        by_id[root].update(x=96+(cols*lane-width-spacing-64)/2,y=cursor)
        cursor+=by_id[root]['h']+spacing
        for start in range(0,len(branches),cols):
            bottoms=[]
            for j,branch in enumerate(branches[start:start+cols]):
                y=cursor
                def place(v,depth=0):
                    nonlocal y
                    by_id[v].update(x=96+j*lane+min(depth,2)*24,y=y)
                    y+=by_id[v]['h']+64
                    for child in children[v]:place(child,depth+1)
                place(branch);bottoms.append(y)
            cursor=max(bottoms)+spacing
    elif orientation=='snake':
        ordered=[v for layer in layers for v in layer]
        cols=3
        for start in range(0,len(ordered),cols):
            row=ordered[start:start+cols]
            reverse=(start//cols)%2==1
            row_h=max(by_id[v]['h'] for v in row)
            for j,v in enumerate(row):
                col=cols-1-j if reverse else j
                by_id[v].update(x=96+col*(width+spacing),y=cursor+(row_h-by_id[v]['h'])/2)
            cursor+=row_h+spacing
    elif orientation=='down':
        spans=[sum(by_id[v]['w'] for v in layer)+(len(layer)-1)*40 for layer in layers]
        full=max(spans)
        for layer,span in zip(layers,spans):
            x=96+(full-span)/2
            for v in layer:
                by_id[v].update(x=x,y=cursor);x+=by_id[v]['w']+40
            cursor+=max(by_id[v]['h'] for v in layer)+spacing
    else:
        spans=[sum(by_id[v]['h'] for v in layer)+(len(layer)-1)*40 for layer in layers]
        full=max(spans)
        x=96.0
        for layer,span in zip(layers,spans):
            y=230+(full-span)/2
            for v in layer:
                by_id[v].update(x=x,y=y);y+=by_id[v]['h']+40
            x+=width+spacing
    edges=[]
    header_obstacles=[{'id':f'_band_header_{i}','x':p['x']+20,'y':p['y']+12,'w':p['w']-40,'h':len(p['label_lines'])*27+len(p['description_lines'])*22+16} for i,p in enumerate(panels)]
    for i,e in enumerate(source_edges):
        a,b=by_id[e['from']],by_id[e['to']]
        if orientation=='outline' and len(layers[1] if len(layers)>1 else [])<=4:
            sa='bottom';p=point(a,sa)
            if levels[a['id']]==0:
                sb='top';q=point(b,sb);bus=p[1]+spacing/2
                path=[p,(p[0],bus),(q[0],bus),q]
            else:
                sb='left';q=point(b,sb);spine=a['x']-20
                path=[p,(p[0],p[1]+24),(spine,p[1]+24),(spine,q[1]),q]
        else:
            path,sa,sb=route(a,b,nodes+header_obstacles,orientation,i)
        edges.append({**e,'source':e['from'],'target':e['to'],'points':path,'source_port':sa,'target_port':sb})
    issues=edge_labels(edges,nodes+header_obstacles)
    all_rects=[rect(n) for n in nodes]+[rect(p) for p in panels]+[e['_label_box'] for e in edges if '_label_box' in e]
    max_x=max([r[2] for r in all_rects]+[p[0] for e in edges for p in e['points']])+76
    max_y=max([r[3] for r in all_rects]+[p[1] for e in edges for p in e['points']])+100
    crossings=crossing_count(edges)
    scale=min(1472/max(max_x-128,1),560/max(max_y-260,1),1)
    score=len(issues)*10000+crossings*65+(1-scale)*250+max_x*max_y/100000
    return {'nodes':nodes,'edges':edges,'panels':panels,'width':max_x,'height':max_y,'issues':issues,'score':round(score,2),'crossings':crossings,'orientation':orientation,'node_width':width,'spacing':spacing,'overview_scale':round(scale,3)}


def build_adaptive(s,d):
    nodes,edges,bands=normalize(d)
    preference=d.get('layout',{}).get('direction',d.get('direction','auto'))
    if preference not in ('auto','right','down'):
        raise ValueError('layout direction must be auto/right/down')
    directions=['down'] if bands else [preference] if preference!='auto' else ['right','down']+(['outline'] if d['type']=='tree' else ['snake'])
    attempts=[];best=None
    for spacing in (100,168):
        for direction in directions:
            for width in (280,360):
                try:
                    c=candidate(nodes,edges,bands,direction,width,spacing)
                    attempts.append({k:c[k] for k in ('score','crossings','orientation','node_width','spacing','issues')})
                    if best is None or c['score']<best['score']:
                        best=c
                except ValueError as exc:
                    attempts.append({'orientation':direction,'node_width':width,'spacing':spacing,'error':str(exc)})
        if best and not best['issues'] and not best['crossings']:
            break
    if best is None or best['issues']:
        raise ValueError('adaptive layout needs smaller semantic groups: '+str(attempts[-1]))
    s.w=max(s.w,math.ceil(best['width']/8)*8)
    s.h=max(s.h,math.ceil(best['height']/8)*8)
    for p in best['panels']:
        s.add(p['x'],p['y'],p['w'],p['h'],kind='panel',check=False)
        h=len(p['label_lines'])*27
        s.text(p['x']+24,p['y']+16,p['w']-48,h,'\n'.join(p['label_lines']),20,'accent',font_family=METRICS.family)
        if p['description']:
            s.text(p['x']+24,p['y']+20+h,p['w']-48,len(p['description_lines'])*22,'\n'.join(p['description_lines']),16,'muted',font_family=METRICS.family)
    for n in best['nodes']:
        s.add(n['x'],n['y'],n['w'],n['h'],n['label'],n.get('detail',''),id=n['id'],kind=n.get('kind','rect'),tone=n.get('tone','accent'),check=True,_lines=n['_lines'],font_family=METRICS.family,text_margin=20)
    for e in best['edges']:
        s.edge(e['source'],e['target'],e.get('label',''),points=e['points'],source_port=e['source_port'],target_port=e['target_port'],tone=e.get('tone','muted'),dashed=e.get('dashed',False),arrow=e.get('arrow',True),_label_box=e.get('_label_box'),_label_lines=e.get('_label_lines'))
    if bands:
        s.meta['layer_nodes']=[b['ids'] for b in bands if not b.get('crosscut')]
        s.meta['architecture_bands']=[{k:b.get(k) for k in ('label','description','ids','flow','flow_direction','crosscut')} for b in bands]
        # Flow captions are semantic facts, carried into both overview and details.
        for i,b in enumerate(bands):
            if b.get('flow') and i+1<len(bands):
                p=best['panels'][i]
                caption=('↑ ' if b.get('flow_direction')=='up' else '↓ ')+b['flow']
                lines=METRICS.wrap(caption,p['w']-48,16)
                s.text(p['x']+24,p['y']+p['h']+12,p['w']-48,len(lines)*22,'\n'.join(lines),16,'muted',font_family=METRICS.family)
    s.meta['adaptive_layout']={
        'version':38,'strategy':best['orientation'],'node_width':best['node_width'],
        'candidates':attempts,'selected_score':best['score'],'crossings':best['crossings'],
        'font_measurement':METRICS.mode,'font_family':METRICS.family,
        'source_node_ids':[n['id'] for n in nodes],
        'source_edges':copy.deepcopy(edges),'overview_scale_at_1600':best['overview_scale'],
        'detail_pages_recommended':best['overview_scale']<.8 or len(nodes)>16,
        'rendered_visual_check':'not-run','manual_visual_review':'not-run',
    }


def finish_adaptive(s):
    """Reserve title and footer by their measured line count, moving content."""
    title=METRICS.wrap(s.spec['title'],s.w-128,36)
    subtitle=METRICS.wrap(s.spec.get('subtitle',''),s.w-128,17)
    top=82+len(title)*49+len(subtitle)*24+36
    shift=max(0,top-230)
    for n in s.nodes:
        n['y']+=shift
    for e in s.edges:
        e['points']=[[x,y+shift] for x,y in e['points']]
        if e.get('_label_box'):
            e['_label_box'][1]+=shift;e['_label_box'][3]+=shift
    footer=METRICS.wrap(s.spec.get('footer','模拟内容 · 用于展示排版能力'),s.w-128,14)
    bottom=max([n['y']+n['h'] for n in s.nodes]+[p[1] for e in s.edges for p in e['points']]+[e['_label_box'][3] for e in s.edges if e.get('_label_box')])
    spare=s.h-len(footer)*20-76-bottom
    if spare>120 and not s.meta['adaptive_layout'].get('page_kind'):
        delta=round(spare*.45)
        for n in s.nodes:n['y']+=delta
        for e in s.edges:
            e['points']=[[x,y+delta] for x,y in e['points']]
            if e.get('_label_box'):e['_label_box'][1]+=delta;e['_label_box'][3]+=delta
        bottom+=delta
    s.h=max(s.h,bottom+len(footer)*20+76)
    s.text(64,34,s.w-128,22,s.spec.get('eyebrow','DIAGRAM STUDIO / 内容自适应排版'),14,'accent',font_family=METRICS.family)
    s.text(64,74,s.w-128,len(title)*49,'\n'.join(title),36,font_family=METRICS.family,_lines=[(t,36,True,'ink') for t in title])
    s.text(64,82+len(title)*49,s.w-128,len(subtitle)*24,'\n'.join(subtitle),17,'muted',font_family=METRICS.family,_lines=[(t,17,False,'muted') for t in subtitle])
    s.add(64,s.h-len(footer)*20-40,s.w-128,1,kind='rect',fill='line',stroke='none',check=False)
    s.text(64,s.h-len(footer)*20-24,s.w-128,len(footer)*20,'\n'.join(footer),14,'muted',font_family=METRICS.family,_lines=[(t,14,False,'muted') for t in footer])
    return s
