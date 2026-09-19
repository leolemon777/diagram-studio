#!/usr/bin/env python3
"""Validate and render software, network, rack, directory and wireframe models.

The module keeps topology semantics and editable geometry in JSON. Vendor-specific
examples use product names where useful, but render neutral vector badges so the
Skill does not redistribute third-party icon packs or screenshots.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import math
import textwrap
from collections import Counter, defaultdict
from pathlib import Path


INK = '#30302D'
MUTED = '#6D6A63'
BG = '#F1EFEB'
PAPER = '#FAF9F6'
GRID = '#D8D3C8'
GREEN = '#58705A'
BLUE = '#657487'
AMBER = '#C1965B'
RED = '#A65448'
PLUM = '#80706A'
COLORS = [GREEN, BLUE, AMBER, RED, PLUM]


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _rows(data, key, *, allow_empty=False):
    rows = data.get(key)
    _need(isinstance(rows, list) and (allow_empty or rows), f'{key} required')
    ids = [row.get('id') for row in rows]
    _need(all(isinstance(item, str) and item.strip() for item in ids), f'{key} ids required')
    _unique(ids, f'{key} ids must be unique')
    return rows


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')
    _need(data.get('data_status') in {'simulated', 'observed', 'mixed'}, 'data_status required')


def _position(row):
    value = row.get('position')
    _need(isinstance(value, list) and len(value) == 2, 'normalized position required')
    _need(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) and 0 <= item <= 1 for item in value), 'position must be finite within 0..1')


def _point(value, message):
    _need(isinstance(value, list) and len(value) == 2, message)
    _need(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) and 0 <= item <= 1 for item in value), message)


def _rect(row, key='rect'):
    value = row.get(key)
    _need(isinstance(value, list) and len(value) == 4, f'normalized {key} required')
    _need(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in value), f'{key} values must be finite')
    x, y, w, h = value
    _need(0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x + w <= 1 and y + h <= 1, f'{key} must stay within 0..1')


def _inside(position, rect):
    x, y = position
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def _chen_erd(data):
    _base(data, 'chen-erd')
    entities = _rows(data, 'entities')
    attributes = _rows(data, 'attributes')
    relationships = _rows(data, 'relationships')
    entity_ids = {row['id'] for row in entities}
    weak_ids = set()
    for row in entities:
        _need(row.get('label'), 'entity label required')
        _need(isinstance(row.get('weak'), bool), 'entity weak flag required')
        _position(row)
        if row['weak']:
            weak_ids.add(row['id'])
    attribute_kinds = {'simple', 'multivalued', 'derived'}
    key_count = defaultdict(int)
    for row in attributes:
        _need(row.get('label') and row.get('entity_id') in entity_ids, 'attribute label and owner required')
        _need(row.get('kind') in attribute_kinds and isinstance(row.get('key'), bool), 'attribute kind and key flag required')
        _position(row)
        key_count[row['entity_id']] += int(row['key'])
    _need(all(key_count[entity_id] >= 1 for entity_id in entity_ids), 'every entity needs at least one key attribute in this example')
    identifying = 0
    participation = set()
    for row in relationships:
        _need(row.get('label') and isinstance(row.get('identifying'), bool), 'relationship label and identifying flag required')
        _position(row)
        roles = row.get('roles')
        _need(isinstance(roles, list) and len(roles) >= 2, 'relationship requires at least two roles')
        role_entities = [role.get('entity_id') for role in roles]
        _need(set(role_entities) <= entity_ids, 'relationship role references unknown entity')
        _unique(role_entities, 'duplicate entity role in one relationship')
        for role in roles:
            _need(role.get('cardinality') in {'1', 'N', 'M'} and role.get('participation') in {'total', 'partial'}, 'role cardinality and participation required')
            participation.add(role['entity_id'])
        if row['identifying']:
            weak_roles = [role for role in roles if role['entity_id'] in weak_ids]
            _need(weak_roles and all(role['participation'] == 'total' for role in weak_roles), 'identifying relationship must totally include a weak entity')
            identifying += 1
    _need(participation == entity_ids, 'every entity must participate in a relationship')
    return {
        'mode': 'chen-erd', 'entities': len(entities), 'weak_entities': len(weak_ids),
        'attributes': len(attributes), 'key_attributes': sum(key_count.values()),
        'relationships': len(relationships), 'identifying_relationships': identifying,
        'attribute_ownership': 'passed', 'cardinality_coverage': 'passed',
    }


def _network_topology(data):
    _base(data, 'network-topology')
    _need(data.get('profile') in {'cisco-campus', 'detailed'}, 'network profile invalid')
    devices = _rows(data, 'devices')
    segments = _rows(data, 'segments', allow_empty=True)
    links = _rows(data, 'links')
    device_ids = {row['id'] for row in devices}
    segment_ids = {row['id'] for row in segments}
    allowed_roles = {'internet', 'wan-edge', 'firewall', 'core', 'distribution', 'access', 'wireless', 'server', 'endpoint', 'ot-controller'}
    layers = set()
    for row in devices:
        _need(row.get('label') and row.get('role') in allowed_roles, 'device label or role invalid')
        _need(row.get('layer') in {'external', 'edge', 'core', 'distribution', 'access', 'service', 'ot'}, 'device layer invalid')
        _need(row.get('vendor') and row.get('model') and row.get('management_ip'), 'device vendor, model and management IP required')
        ipaddress.ip_address(row['management_ip'])
        _position(row)
        layers.add(row['layer'])
    for row in segments:
        _need(row.get('label') and row.get('kind') in {'vlan', 'subnet', 'security-zone'}, 'segment label or kind invalid')
        if row['kind'] == 'vlan':
            _need(isinstance(row.get('vlan_id'), int) and 1 <= row['vlan_id'] <= 4094, 'VLAN id must be 1..4094')
        if row.get('cidr'):
            ipaddress.ip_network(row['cidr'], strict=False)
    endpoints = set()
    redundancy = defaultdict(list)
    capacities = []
    for row in links:
        _need(row.get('source') in device_ids and row.get('target') in device_ids and row['source'] != row['target'], 'link endpoints invalid')
        _need(row.get('source_interface') and row.get('target_interface'), 'link interfaces required')
        _need(row.get('plane') in {'L2', 'L3'} and row.get('medium') in {'fiber', 'copper', 'wireless', 'virtual'}, 'link plane or medium invalid')
        _need(isinstance(row.get('capacity_mbps'), (int, float)) and row['capacity_mbps'] > 0, 'link capacity must be positive')
        _need(row.get('purpose') and row.get('evidence'), 'link purpose and evidence required')
        _need(row.get('segment_id') is None or row.get('segment_id') in segment_ids, 'link segment is unknown')
        for endpoint in ((row['source'], row['source_interface']), (row['target'], row['target_interface'])):
            _need(endpoint not in endpoints, f'device interface reused: {endpoint}')
            endpoints.add(endpoint)
        capacities.append(row['capacity_mbps'])
        if row.get('redundancy_group'):
            redundancy[row['redundancy_group']].append(row['id'])
    _need(all(len(items) >= 2 for items in redundancy.values()), 'redundancy groups require at least two links')
    if data['profile'] == 'cisco-campus':
        _need({'core', 'distribution', 'access'} <= layers, 'Cisco campus example needs core, distribution and access layers')
    return {
        'mode': 'network-topology', 'profile': data['profile'], 'devices': len(devices),
        'links': len(links), 'segments': len(segments), 'layer_counts': dict(sorted(Counter(row['layer'] for row in devices).items())),
        'l2_links': sum(row['plane'] == 'L2' for row in links), 'l3_links': sum(row['plane'] == 'L3' for row in links),
        'minimum_capacity_mbps': min(capacities), 'maximum_capacity_mbps': max(capacities),
        'redundancy_groups': dict(sorted(redundancy.items())), 'interface_uniqueness': 'passed',
        'icon_policy': 'official or supplied names retained; neutral badges rendered; vendor icon packs not bundled',
    }


def _rack_elevation(data):
    _base(data, 'rack-elevation')
    racks = _rows(data, 'racks')
    equipment = _rows(data, 'equipment')
    rack_ids = {row['id'] for row in racks}
    rack_by_id = {row['id']: row for row in racks}
    occupied = defaultdict(dict)
    power = defaultdict(float)
    for row in racks:
        _need(row.get('label') and row.get('view') in {'front', 'rear'}, 'rack label and view required')
        _need(isinstance(row.get('total_u'), int) and 6 <= row['total_u'] <= 48, 'rack total_u must be 6..48')
    for row in equipment:
        _need(row.get('rack_id') in rack_ids and row.get('label') and row.get('category'), 'equipment rack, label and category required')
        _need(isinstance(row.get('start_u'), int) and isinstance(row.get('height_u'), int) and row['start_u'] >= 1 and row['height_u'] >= 1, 'equipment U placement invalid')
        rack = rack_by_id[row['rack_id']]
        _need(row['start_u'] + row['height_u'] - 1 <= rack['total_u'], 'equipment exceeds rack height')
        _need(isinstance(row.get('power_w'), (int, float)) and row['power_w'] >= 0, 'equipment power_w invalid')
        _need(isinstance(row.get('depth_mm'), (int, float)) and row['depth_mm'] > 0, 'equipment depth_mm invalid')
        for unit in range(row['start_u'], row['start_u'] + row['height_u']):
            _need(unit not in occupied[row['rack_id']], f"rack U overlap at {row['rack_id']} U{unit}")
            occupied[row['rack_id']][unit] = row['id']
        power[row['rack_id']] += row['power_w']
    utilization = {
        rack_id: round(len(occupied[rack_id]) / rack_by_id[rack_id]['total_u'], 4)
        for rack_id in rack_ids
    }
    return {
        'mode': 'rack-elevation', 'racks': len(racks), 'equipment': len(equipment),
        'occupied_u': {key: len(value) for key, value in sorted(occupied.items())},
        'free_u': {key: rack_by_id[key]['total_u'] - len(occupied[key]) for key in sorted(rack_ids)},
        'utilization': dict(sorted(utilization.items())), 'power_w': dict(sorted(power.items())),
        'overlap_check': 'passed', 'rack_unit_mm': 44.45,
    }


def _active_directory(data):
    _base(data, 'active-directory')
    _need(data.get('view') == 'logical', 'this model supports the logical AD view')
    forests = _rows(data, 'forests')
    domains = _rows(data, 'domains')
    ous = _rows(data, 'organizational_units')
    objects = _rows(data, 'objects')
    trusts = _rows(data, 'trusts', allow_empty=True)
    forest_ids = {row['id'] for row in forests}
    domain_ids = {row['id'] for row in domains}
    ou_ids = {row['id'] for row in ous}
    for row in forests:
        _need(row.get('label') and row.get('schema_version'), 'forest label and schema version required')
        _rect(row)
    for row in domains:
        _need(row.get('label') and row.get('dns_name') and row.get('forest_id') in forest_ids, 'domain fields invalid')
        _rect(row)
    by_ou = {row['id']: row for row in ous}
    for row in ous:
        _need(row.get('label') and row.get('domain_id') in domain_ids, 'OU label and domain required')
        _need(row.get('parent_ou_id') is None or row.get('parent_ou_id') in ou_ids, 'OU parent unknown')
        if row.get('parent_ou_id'):
            _need(by_ou[row['parent_ou_id']]['domain_id'] == row['domain_id'], 'OU parent must be in same domain')
        _need(row.get('delegated_to') and isinstance(row.get('gpo_links'), list), 'OU delegation and GPO links required')
        _rect(row)
    for start in ous:
        seen = set(); cursor = start
        while cursor.get('parent_ou_id'):
            _need(cursor['id'] not in seen, 'OU containment cycle detected')
            seen.add(cursor['id']); cursor = by_ou[cursor['parent_ou_id']]
    types = {'user', 'group', 'computer', 'service-account'}
    for row in objects:
        _need(row.get('label') and row.get('ou_id') in ou_ids and row.get('object_type') in types, 'directory object invalid')
        _position(row)
    for row in trusts:
        _need(row.get('source_domain') in domain_ids and row.get('target_domain') in domain_ids and row['source_domain'] != row['target_domain'], 'trust endpoints invalid')
        _need(row.get('direction') in {'one-way', 'two-way'} and row.get('transitivity') in {'transitive', 'non-transitive'}, 'trust direction or transitivity invalid')
        _need(row.get('evidence'), 'trust evidence required')
    _need(all(_inside(row['position'], by_ou[row['ou_id']]['rect']) for row in objects), 'directory object must be positioned inside its OU')
    return {
        'mode': 'active-directory', 'view': 'logical', 'forests': len(forests), 'domains': len(domains),
        'organizational_units': len(ous), 'objects': len(objects), 'trusts': len(trusts),
        'object_types': dict(sorted(Counter(row['object_type'] for row in objects).items())),
        'delegation_coverage': 'passed', 'gpo_scope_explicit': 'passed',
        'physical_site_topology': 'separate view required',
    }


def _network_location(data):
    _base(data, 'network-location')
    _need(data.get('map_accuracy') == 'schematic', 'network location map must declare schematic accuracy')
    sites = _rows(data, 'sites')
    nodes = _rows(data, 'nodes')
    connections = _rows(data, 'connections')
    site_ids = {row['id'] for row in sites}
    site_by_id = {row['id']: row for row in sites}
    for row in sites:
        _need(row.get('label') and row.get('location') and row.get('location_source'), 'site label, location and source required')
        _rect(row)
    for row in nodes:
        _need(row.get('label') and row.get('role') and row.get('site_id') in site_ids, 'location node invalid')
        _position(row)
        _need(_inside(row['position'], site_by_id[row['site_id']]['rect']), 'node must be positioned inside its site')
    pairs = set()
    for row in connections:
        _need(row.get('source_site') in site_ids and row.get('target_site') in site_ids and row['source_site'] != row['target_site'], 'site connection endpoints invalid')
        pair = tuple(sorted((row['source_site'], row['target_site'])))
        _need(pair not in pairs, 'duplicate site connection')
        pairs.add(pair)
        _need(isinstance(row.get('capacity_mbps'), (int, float)) and row['capacity_mbps'] > 0, 'site connection capacity invalid')
        _need(isinstance(row.get('latency_ms'), (int, float)) and row['latency_ms'] >= 0, 'site latency invalid')
        _need(row.get('carrier') and row.get('medium') and row.get('route_source'), 'carrier, medium and route source required')
        if row.get('source_anchor') is not None or row.get('target_anchor') is not None:
            _point(row.get('source_anchor'), 'source_anchor must be a normalized point')
            _point(row.get('target_anchor'), 'target_anchor must be a normalized point')
    return {
        'mode': 'network-location', 'sites': len(sites), 'nodes': len(nodes), 'connections': len(connections),
        'map_accuracy': 'schematic', 'location_sources': 'passed', 'route_sources': 'passed',
        'maximum_latency_ms': max(row['latency_ms'] for row in connections),
        'minimum_capacity_mbps': min(row['capacity_mbps'] for row in connections),
    }


def _ui_wireframe(data):
    _base(data, 'ui-wireframe')
    platform = data.get('platform')
    _need(platform in {'web', 'ios', 'android'}, 'wireframe platform invalid')
    screens = _rows(data, 'screens')
    components = _rows(data, 'components')
    transitions = _rows(data, 'transitions', allow_empty=True)
    screen_ids = {row['id'] for row in screens}
    components_by_screen = defaultdict(list)
    for row in screens:
        _need(row.get('label') and row.get('state'), 'screen label and state required')
        _rect(row)
        _need(isinstance(row.get('viewport_width'), int) and row['viewport_width'] > 0, 'screen viewport width required')
        _need(isinstance(row.get('safe_areas'), list), 'screen safe_areas required')
    allowed_types = {'header', 'nav', 'main', 'footer', 'status-bar', 'navigation-bar', 'tab-bar', 'app-bar', 'list', 'card', 'button', 'field', 'dialog', 'message', 'image', 'filter'}
    for row in components:
        _need(row.get('screen_id') in screen_ids and row.get('label') and row.get('type') in allowed_types, 'wireframe component invalid')
        _rect(row)
        _need(isinstance(row.get('interactive'), bool), 'component interactive flag required')
        if row['interactive']:
            _need(row.get('action') and row.get('accessible_name'), 'interactive component needs action and accessible name')
        components_by_screen[row['screen_id']].append(row)
    for row in transitions:
        _need(row.get('source_screen') in screen_ids and row.get('target_screen') in screen_ids and row['source_screen'] != row['target_screen'], 'wireframe transition endpoints invalid')
        _need(row.get('trigger'), 'wireframe transition trigger required')
        if platform == 'android':
            _need(row.get('back_behavior'), 'Android transition needs back behavior')
    if platform == 'web':
        widths = {row['viewport_width'] for row in screens}
        _need({320, 1440} <= widths, 'web wireframe requires 1440 and 320 responsive views')
        for screen in screens:
            types = {row['type'] for row in components_by_screen[screen['id']]}
            _need({'header', 'nav', 'main', 'footer'} <= types, 'each web view needs header, nav, main and footer landmarks')
        _need(data.get('reflow_policy') == 'single-axis-at-320', 'web reflow policy must cover 320 CSS px')
    else:
        required = {'top', 'bottom'} if platform == 'ios' else {'status-bar', 'navigation-bar'}
        _need(all(required <= set(row['safe_areas']) for row in screens), 'mobile screen safe areas incomplete')
        if platform == 'ios':
            _need(any(row['type'] == 'tab-bar' for row in components), 'iOS wireframe needs a tab bar example')
        else:
            _need(any(row['state'] in {'permission', 'keyboard'} for row in screens), 'Android example needs permission or keyboard state')
    return {
        'mode': 'ui-wireframe', 'platform': platform, 'screens': len(screens), 'components': len(components),
        'interactive_components': sum(row['interactive'] for row in components), 'transitions': len(transitions),
        'viewport_widths': sorted({row['viewport_width'] for row in screens}),
        'component_types': dict(sorted(Counter(row['type'] for row in components).items())),
        'accessible_names': 'passed', 'safe_area_coverage': 'passed',
        'responsive_reflow': 'passed' if platform == 'web' else 'not-applicable',
        'back_stack_coverage': 'passed' if platform == 'android' else 'not-applicable',
    }


ANALYZERS = {
    'chen-erd': _chen_erd,
    'network-topology': _network_topology,
    'rack-elevation': _rack_elevation,
    'active-directory': _active_directory,
    'network-location': _network_location,
    'ui-wireframe': _ui_wireframe,
}


def analyze(data):
    _need(data.get('mode') in ANALYZERS, 'unsupported software/infrastructure mode')
    result = ANALYZERS[data['mode']](data)
    result['data_status'] = data['data_status']
    result['assumptions'] = data.get('assumptions', [])
    return result


def _font():
    from matplotlib import font_manager
    path = Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists():
        font_manager.fontManager.addfont(path)
        return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def _figure(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({
        'font.family': _font(), 'font.size': 10.2, 'text.color': INK,
        'axes.unicode_minus': False, 'svg.fonttype': 'none',
        'svg.hashsalt': 'diagram-studio-software-infrastructure-v1',
    })
    fig = plt.figure(figsize=(12.8, 7.6), facecolor=BG)
    ax = fig.add_axes((.045, .085, .91, .79))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    fig.text(.05, .955, data['title'], fontsize=21.5, color=INK, weight='medium', va='top')
    fig.text(.05, .912, data.get('subtitle', ''), fontsize=10.1, color=MUTED, va='top')
    fig.text(.95, .95, data['mode'].upper().replace('-', '  '), fontsize=8.2, color=MUTED, ha='right', va='top')
    return fig, ax


def _wrap(value, width=18):
    return '\n'.join(textwrap.wrap(str(value), width=width, break_long_words=False, break_on_hyphens=False))


def _node(ax, row, *, w=.15, h=.09, color=BLUE, title=None, detail=None, z=4):
    from matplotlib.patches import FancyBboxPatch
    x, y = row['position']
    patch = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle='round,pad=.008,rounding_size=.012', fc=PAPER, ec=color, lw=1.35, zorder=z)
    ax.add_patch(patch)
    ax.text(x, y + (.014 if detail else 0), _wrap(title or row.get('label', row['id']), 15), ha='center', va='center', fontsize=8.9, weight='medium', zorder=z+1)
    if detail:
        ax.text(x, y-.028, _wrap(detail, 22), ha='center', va='center', fontsize=6.8, color=MUTED, zorder=z+1)


def _arrow(ax, source, target, label, *, color=MUTED, dashed=False, rad=0, offset=(0, 0), shrink=34, z=2):
    sx, sy = source['position']; tx, ty = target['position']
    ax.annotate('', xy=(tx,ty), xytext=(sx,sy), arrowprops=dict(arrowstyle='-|>', color=color, lw=1.1, linestyle='--' if dashed else '-', shrinkA=shrink, shrinkB=shrink, connectionstyle=f'arc3,rad={rad}'), zorder=z)
    mx, my = (sx+tx)/2+offset[0], (sy+ty)/2+offset[1]
    ax.text(mx, my, _wrap(label, 25), fontsize=6.8, color=color, ha='center', va='center', bbox=dict(boxstyle='round,pad=.18', fc=BG, ec='none', alpha=.96), zorder=z+3)


def _draw_rect(ax, rect, *, edge=BLUE, fill=PAPER, alpha=.45, lw=1.2, label=None, z=.4):
    from matplotlib.patches import FancyBboxPatch
    x,y,w,h = rect
    patch = FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.006,rounding_size=.009',fc=fill,ec=edge,lw=lw,alpha=alpha,zorder=z)
    ax.add_patch(patch)
    if label:
        ax.text(x+.012,y+h-.018,label,fontsize=7.4,color=edge,va='top',weight='medium',zorder=z+1)
    return patch


def _footer(fig, calc):
    facts=[]
    for key,value in calc.items():
        if key in {'mode','profile','view','platform','map_accuracy','data_status','assumptions','layer_counts','redundancy_groups','object_types','component_types','occupied_u','free_u','utilization','power_w','viewport_widths','icon_policy'}:
            continue
        if isinstance(value,(str,int,float)) and len(facts)<4:
            facts.append(f"{key.replace('_',' ')}: {value}")
    fig.text(.05,.035,'  ·  '.join(facts),fontsize=7.4,color=MUTED,va='bottom')
    fig.text(.95,.035,'模拟输入 / 语义与几何由后端校验',fontsize=7.4,color=MUTED,ha='right',va='bottom')


def _render_chen(data, calc, fig, ax):
    from matplotlib.patches import Rectangle, Ellipse, Polygon
    by_id={}
    for row in data['entities']:
        x,y=row['position']; w,h=.15,.075
        ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc=PAPER,ec=BLUE,lw=1.5,zorder=4))
        if row['weak']:
            ax.add_patch(Rectangle((x-w/2+.007,y-h/2+.006),w-.014,h-.012,fc='none',ec=BLUE,lw=.9,zorder=5))
        ax.text(x,y,row['label'],ha='center',va='center',fontsize=9,weight='medium',zorder=6)
        by_id[row['id']]=row
    for row in data['relationships']:
        x,y=row['position']; w,h=.13,.075
        points=[(x,y+h/2),(x+w/2,y),(x,y-h/2),(x-w/2,y)]
        ax.add_patch(Polygon(points,closed=True,fc=PAPER,ec=PLUM,lw=1.45,zorder=4))
        if row['identifying']:
            points2=[(x,y+h/2-.007),(x+w/2-.011,y),(x,y-h/2+.007),(x-w/2+.011,y)]
            ax.add_patch(Polygon(points2,closed=True,fc='none',ec=PLUM,lw=.85,zorder=5))
        ax.text(x,y,row['label'],ha='center',va='center',fontsize=8.5,zorder=6)
        by_id[row['id']]=row
    for row in data['attributes']:
        x,y=row['position']; w,h=.115,.052
        style='--' if row['kind']=='derived' else '-'
        ax.add_patch(Ellipse((x,y),w,h,fc=PAPER,ec=AMBER,lw=1.15,linestyle=style,zorder=4))
        if row['kind']=='multivalued':
            ax.add_patch(Ellipse((x,y),w-.012,h-.008,fc='none',ec=AMBER,lw=.75,zorder=5))
        ax.text(x,y,row['label'],ha='center',va='center',fontsize=7.5,weight='medium' if row['key'] else 'normal',zorder=6)
        if row['key']:
            ax.plot([x-w*.28,x+w*.28],[y-.012,y-.012],color=INK,lw=.7,zorder=6)
        ax.plot([x,by_id[row['entity_id']]['position'][0]],[y,by_id[row['entity_id']]['position'][1]],color=GRID,lw=.95,zorder=1)
    for row in data['relationships']:
        for role in row['roles']:
            entity=by_id[role['entity_id']]
            lw=2 if role['participation']=='total' else 1
            ax.plot([row['position'][0],entity['position'][0]],[row['position'][1],entity['position'][1]],color=PLUM,lw=lw,zorder=2)
            mx=(row['position'][0]+entity['position'][0])/2; my=(row['position'][1]+entity['position'][1])/2
            ax.text(mx,my,role['cardinality'],fontsize=8,color=PLUM,bbox=dict(fc=BG,ec='none',pad=.1),zorder=5)
    ax.text(.02,.96,'实体矩形 · 联系菱形 · 属性椭圆 · 双框为弱实体/标识联系',fontsize=8,color=MUTED,va='top')


def _render_network(data, calc, fig, ax):
    devices={row['id']:row for row in data['devices']}
    layer_order=['external','edge','core','distribution','access','service','ot']
    labels={'external':'外部','edge':'边界','core':'核心','distribution':'汇聚','access':'接入','service':'服务','ot':'OT'}
    present=[layer for layer in layer_order if any(row['layer']==layer for row in data['devices'])]
    for index,layer in enumerate(present):
        ys=[row['position'][1] for row in data['devices'] if row['layer']==layer]
        y=sum(ys)/len(ys)
        ax.axhspan(max(0,y-.07),min(1,y+.07),xmin=.015,xmax=.985,facecolor=COLORS[index%len(COLORS)],alpha=.045,zorder=.1)
        ax.text(.012,y,labels[layer],fontsize=7.5,color=COLORS[index%len(COLORS)],va='center',weight='medium')
    role_colors={'internet':INK,'wan-edge':RED,'firewall':RED,'core':PLUM,'distribution':BLUE,'access':GREEN,'wireless':AMBER,'server':BLUE,'endpoint':MUTED,'ot-controller':AMBER}
    for row in data['devices']:
        detail=f"{row['vendor']} {row['model']}\n{row['management_ip']}"
        _node(ax,row,w=.145,h=.09,color=role_colors[row['role']],detail=detail)
    for row in data['links']:
        capacity = f"{row['capacity_mbps']/1000:g} Gb/s" if row['capacity_mbps'] >= 1000 else f"{row['capacity_mbps']:g} Mb/s"
        color=BLUE if row['plane']=='L3' else GREEN
        _arrow(ax,devices[row['source']],devices[row['target']],f"{row['plane']} · {capacity}",color=color,dashed=row['plane']=='L2',rad=row.get('rad',0),offset=tuple(row.get('label_offset',[0,0])))
        sx,sy=devices[row['source']]['position']; tx,ty=devices[row['target']]['position']
        dx,dy=tx-sx,ty-sy; length=max(math.hypot(dx,dy),1e-9)
        ux,uy=dx/length,dy/length; nx,ny=-uy,ux; side=row.get('interface_side',1)
        boundary=min(.0725/max(abs(ux),1e-9),.045/max(abs(uy),1e-9))+.008
        source_at=(sx+ux*boundary+nx*.018*side,sy+uy*boundary+ny*.018*side)
        target_at=(tx-ux*boundary-nx*.018*side,ty-uy*boundary-ny*.018*side)
        ax.text(*source_at,row['source_interface'],fontsize=5.6,color=color,ha='center',va='center',bbox=dict(fc=BG,ec='none',pad=.1),zorder=5)
        ax.text(*target_at,row['target_interface'],fontsize=5.6,color=color,ha='center',va='center',bbox=dict(fc=BG,ec='none',pad=.1),zorder=5)
    fig.text(.95,.884,'官方/输入名称 · 中性徽标 · 未捆绑厂商图标包',fontsize=7.8,color=MUTED,ha='right')


def _render_rack(data, calc, fig, ax):
    from matplotlib.patches import Rectangle
    racks=data['racks']; rack_count=len(racks)
    equipment_by=defaultdict(list)
    for row in data['equipment']:
        equipment_by[row['rack_id']].append(row)
    width=min(.40,.72/rack_count)
    for index,rack in enumerate(racks):
        x=.16+index*(.76/max(1,rack_count)); y=.06; h=.86
        ax.add_patch(Rectangle((x,y),width,h,fc=PAPER,ec=INK,lw=1.5,zorder=1))
        unit_h=h/rack['total_u']
        for unit in range(1,rack['total_u']+1):
            yy=y+(unit-1)*unit_h
            ax.plot([x,x+width],[yy,yy],color=GRID,lw=.55,zorder=2)
            if unit==1 or unit%2==0 or rack['total_u']>30 and unit%5==0:
                ax.text(x-.012,yy+unit_h/2,f'U{unit}',ha='right',va='center',fontsize=5.8,color=MUTED)
        category_colors={'power':RED,'patch':AMBER,'network':GREEN,'server':BLUE,'storage':PLUM,'blank':GRID}
        for row in equipment_by[rack['id']]:
            yy=y+(row['start_u']-1)*unit_h
            hh=row['height_u']*unit_h
            color=category_colors.get(row['category'],BLUE)
            ax.add_patch(Rectangle((x+.006,yy+.002),width-.012,max(.006,hh-.004),fc=color,ec=color,lw=1,alpha=.22,zorder=3))
            ax.text(x+width/2,yy+hh/2,_wrap(f"{row['label']} · {row['height_u']}U",24),ha='center',va='center',fontsize=7 if hh>.045 else 5.6,color=INK,zorder=4)
        ax.text(x+width/2,.955,f"{rack['label']} · {rack['total_u']}U · {rack['view']=='front' and '前视' or '后视'}",ha='center',va='top',fontsize=9,weight='medium')
        ax.text(x+width+.025,.86,f"占用 {calc['occupied_u'][rack['id']]}U\n空余 {calc['free_u'][rack['id']]}U\n{calc['power_w'][rack['id']]:g} W",fontsize=7.2,color=MUTED,va='top')


def _render_ad(data, calc, fig, ax):
    domain_centers={}
    for index,row in enumerate(data['forests']):
        _draw_rect(ax,row['rect'],edge=PLUM,fill=PAPER,alpha=.35,lw=1.45,label='林 · '+row['label'],z=.2)
    for index,row in enumerate(data['domains']):
        _draw_rect(ax,row['rect'],edge=BLUE,fill=PAPER,alpha=.5,lw=1.25,label='域 · '+row['dns_name'],z=.4)
        x,y,w,h=row['rect']; domain_centers[row['id']]={'position':[x+w/2,y+h/2]}
    for index,row in enumerate(data['organizational_units']):
        _draw_rect(ax,row['rect'],edge=COLORS[index%len(COLORS)],fill=BG,alpha=.78,lw=1,label='OU · '+row['label']+' · 委派 '+row['delegated_to'],z=.7)
        x,y,w,h=row['rect']
        if row['gpo_links']:
            ax.text(x+w-.008,y+.01,'GPO: '+','.join(row['gpo_links']),fontsize=5.7,color=MUTED,ha='right',va='bottom',zorder=3)
    object_colors={'user':AMBER,'group':PLUM,'computer':GREEN,'service-account':RED}
    type_labels={'user':'用户','group':'组','computer':'计算机','service-account':'服务账号'}
    for row in data['objects']:
        _node(ax,row,w=.105,h=.055,color=object_colors[row['object_type']],detail=type_labels[row['object_type']])
    for row in data['trusts']:
        direction='双向' if row['direction']=='two-way' else '单向'
        transitivity={'transitive':'传递','non-transitive':'非传递'}[row['transitivity']]
        _arrow(ax,domain_centers[row['source_domain']],domain_centers[row['target_domain']],f"{direction} · {transitivity}",color=RED,rad=.12,shrink=110)
    ax.text(.02,.96,'逻辑视图：林 → 域 → OU → 对象；站点与复制拓扑需另图',fontsize=8,color=MUTED,va='top')


def _render_location(data, calc, fig, ax):
    centers={}
    for index,row in enumerate(data['sites']):
        _draw_rect(ax,row['rect'],edge=COLORS[index%len(COLORS)],fill=PAPER,alpha=.55,lw=1.3,label=row['label']+' · '+row['location'],z=.4)
        x,y,w,h=row['rect']; centers[row['id']]={'position':[x+w/2,y+h/2]}
        ax.text(x+.012,y+.018,'位置来源：'+row['location_source'],fontsize=5.8,color=MUTED,va='bottom')
    for row in data['nodes']:
        _node(ax,row,w=.12,h=.065,color=BLUE,detail=row['role'])
    for row in data['connections']:
        source = {'position': row.get('source_anchor', centers[row['source_site']]['position'])}
        target = {'position': row.get('target_anchor', centers[row['target_site']]['position'])}
        anchored = 'source_anchor' in row
        _arrow(ax,source,target,f"{row['carrier']} · {row['capacity_mbps']:g} Mb/s · {row['latency_ms']:g} ms\n{row['route_source']}",color=RED,rad=row.get('rad',0),offset=tuple(row.get('label_offset',[0,0])),shrink=4 if anchored else 105,z=1)
    ax.text(.02,.96,'示意位置：不使用未核对的经纬度或距离；带宽与时延独立标注',fontsize=8,color=MUTED,va='top')


def _component_box(ax, screen, component, color):
    from matplotlib.patches import Rectangle
    sx,sy,sw,sh=screen['rect']; x,y,w,h=component['rect']
    gx=sx+x*sw; gy=sy+y*sh; gw=w*sw; gh=h*sh
    fill=color if component['type'] in {'button','tab-bar','navigation-bar','app-bar','nav'} else PAPER
    alpha=.18 if fill!=PAPER else .75
    ax.add_patch(Rectangle((gx,gy),gw,gh,fc=fill,ec=color,lw=.85,alpha=alpha,zorder=3))
    ax.text(gx+gw/2,gy+gh/2,_wrap(component['label'],14),ha='center',va='center',fontsize=5.8 if sw<.25 else 6.6,color=INK,zorder=4)


def _render_wireframe(data, calc, fig, ax):
    from matplotlib.patches import FancyBboxPatch
    screens={row['id']:row for row in data['screens']}
    centers={}
    platform_color={'web':BLUE,'ios':PLUM,'android':GREEN}[data['platform']]
    state_labels={'default':'默认','reflow':'重排','selected':'已选择','editing':'编辑','permission':'权限'}
    safe_labels={'top':'顶部','bottom':'底部','status-bar':'状态栏','navigation-bar':'导航栏'}
    for screen in data['screens']:
        x,y,w,h=screen['rect']
        rounding = '.014' if data['platform'] != 'web' else '.006'
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=.004,rounding_size={rounding}',fc=BG,ec=platform_color,lw=1.3,zorder=1))
        centers[screen['id']]={'position':[x+w/2,y+h/2]}
        ax.text(x+w/2,y+h+.018,f"{screen['label']} · {screen['viewport_width']} px · {state_labels.get(screen['state'],screen['state'])}",ha='center',va='bottom',fontsize=7.2,color=platform_color,weight='medium')
        if screen['safe_areas']:
            ax.text(x+w-.006,y+.006,'安全区：'+'、'.join(safe_labels.get(item,item) for item in screen['safe_areas']),ha='right',va='bottom',fontsize=5.2,color=MUTED)
    type_colors={'header':PLUM,'nav':GREEN,'main':BLUE,'footer':MUTED,'status-bar':MUTED,'navigation-bar':GREEN,'tab-bar':PLUM,'app-bar':BLUE,'list':BLUE,'card':AMBER,'button':RED,'field':GREEN,'dialog':RED,'message':AMBER,'image':PLUM,'filter':GREEN}
    for component in data['components']:
        _component_box(ax,screens[component['screen_id']],component,type_colors[component['type']])
    for index,row in enumerate(data['transitions']):
        _arrow(ax,centers[row['source_screen']],centers[row['target_screen']],row['trigger'],color=RED,rad=.18 if index%2==0 else -.18,offset=tuple(row.get('label_offset',[0,0])),shrink=125,z=1)
    note={'web':'1440 与 320 宽度同构；地标和功能不丢失','ios':'安全区、底部导航和触控动作显式','android':'系统栏、返回行为和权限/键盘状态显式'}[data['platform']]
    ax.text(.02,.96,note,fontsize=8,color=MUTED,va='top')


RENDERERS = {
    'chen-erd': _render_chen,
    'network-topology': _render_network,
    'rack-elevation': _render_rack,
    'active-directory': _render_ad,
    'network-location': _render_location,
    'ui-wireframe': _render_wireframe,
}


def render(data, out_dir, stem):
    calc=analyze(data)
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    fig,ax=_figure(data)
    RENDERERS[data['mode']](data,calc,fig,ax)
    _footer(fig,calc)
    svg=out/f'{stem}.svg'; png=out/f'{stem}.png'
    fig.savefig(svg,format='svg',metadata={'Date':None})
    fig.savefig(png,format='png',dpi=160,metadata={'Software':'diagram-studio software_infrastructure.py'})
    import matplotlib.pyplot as plt
    plt.close(fig)
    (out/f'{stem}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (out/f'{stem}.calculation.json').write_text(json.dumps(calc,ensure_ascii=False,indent=2)+'\n')
    qa={'mode':data['mode'],'errors':[],'warnings':[],'layout_issues':[],'semantic_validation':'passed','editable_source':f'{stem}.input.json','visual_review':'pending manual browser review'}
    (out/f'{stem}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    return calc


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('input'); parser.add_argument('--out',required=True); parser.add_argument('--name')
    args=parser.parse_args(); source=Path(args.input); data=json.loads(source.read_text()); stem=args.name or source.stem
    print(json.dumps(render(data,args.out,stem),ensure_ascii=False))


if __name__=='__main__':
    main()
