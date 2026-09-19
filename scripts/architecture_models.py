#!/usr/bin/env python3
"""Validate and render curated application, cloud, enterprise, C4 and Kubernetes models.

The renderer intentionally uses neutral service badges rather than redistributing vendor
icon packs.  Service names, boundaries and directed flows remain explicit in the model.
"""
from __future__ import annotations

import argparse
import json
import math
import textwrap
from collections import Counter, defaultdict, deque
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
    _need(isinstance(rows, list) and (rows or allow_empty), f'{key} required')
    ids = [row.get('id') for row in rows]
    _need(all(isinstance(value, str) and value.strip() for value in ids), f'{key} ids required')
    _unique(ids, f'{key} ids must be unique')
    return rows


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')
    _need(data.get('data_status') in {'simulated', 'observed', 'mixed'}, 'data_status required')


def _position(row):
    value = row.get('position')
    _need(isinstance(value, list) and len(value) == 2, 'normalized position required')
    _need(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) and 0 <= item <= 1 for item in value), 'positions must be finite within 0..1')


def _rectangle(row):
    value = row.get('rect')
    _need(isinstance(value, list) and len(value) == 4, 'normalized boundary rect required')
    _need(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in value), 'boundary rect values must be finite')
    x, y, w, h = value
    _need(0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x + w <= 1 and y + h <= 1, 'boundary rect must stay within canvas')


def _application_landscape(data):
    _base(data, 'application-landscape')
    capabilities = _rows(data, 'capabilities')
    applications = _rows(data, 'applications')
    integrations = _rows(data, 'integrations')
    domains = _rows(data, 'data_domains')
    links = data.get('capability_links')
    _need(isinstance(links, list) and links, 'capability_links required')
    capability_ids = {row['id'] for row in capabilities}
    app_ids = {row['id'] for row in applications}
    for row in capabilities:
        _need(row.get('label') and row.get('owner'), 'capability label and owner required')
        _position(row)
    for row in applications:
        _need(row.get('label') and row.get('owner') and row.get('lifecycle') in {'invest', 'maintain', 'migrate', 'retire'}, 'application label, owner and lifecycle required')
        _position(row)
    seen = []
    mapped = set()
    for row in links:
        _need(row.get('capability_id') in capability_ids and row.get('application_id') in app_ids, 'capability link references unknown item')
        _need(row.get('coverage') in {'primary', 'supporting'} and row.get('evidence'), 'capability link needs coverage and evidence')
        seen.append((row['capability_id'], row['application_id']))
        mapped.add(row['application_id'])
    _unique(seen, 'duplicate capability-to-application links are not allowed')
    for row in integrations:
        _need(row.get('source') in app_ids and row.get('target') in app_ids and row['source'] != row['target'], 'integration endpoints must reference different applications')
        _need(row.get('pattern') in {'sync', 'event', 'batch'}, 'integration pattern must be sync, event or batch')
        _need(row.get('payload') and row.get('evidence'), 'integration payload and evidence required')
    for row in domains:
        _need(row.get('label') and row.get('system_of_record') in app_ids and row.get('classification'), 'data domain label, system of record and classification required')
        _position(row)
    _need(mapped == app_ids, 'every application must map to at least one capability')
    return {
        'mode': 'application-landscape', 'capabilities': len(capabilities), 'applications': len(applications),
        'integrations': len(integrations), 'data_domains': len(domains),
        'integration_patterns': dict(sorted(Counter(row['pattern'] for row in integrations).items())),
        'capability_coverage': 'passed', 'system_of_record_coverage': 'passed',
    }


PROVIDER_BOUNDARY_KINDS = {
    'AWS': {'account', 'region', 'vpc', 'availability-zone', 'subnet'},
    'Azure': {'tenant', 'subscription', 'resource-group', 'region', 'virtual-network', 'subnet'},
    'GCP': {'organization', 'folder', 'project', 'region', 'vpc', 'subnet'},
}


def _cloud_architecture(data):
    _base(data, 'cloud-architecture')
    provider = data.get('provider')
    _need(provider in PROVIDER_BOUNDARY_KINDS, 'provider must be AWS, Azure or GCP')
    boundaries = _rows(data, 'boundaries')
    services = _rows(data, 'services')
    flows = _rows(data, 'flows')
    boundary_ids = {row['id'] for row in boundaries}
    service_ids = {row['id'] for row in services}
    for row in boundaries:
        _need(row.get('label') and row.get('kind') in PROVIDER_BOUNDARY_KINDS[provider], 'boundary kind is invalid for provider')
        _need(row.get('parent_id') is None or row.get('parent_id') in boundary_ids, 'boundary parent is unknown')
        _need(row.get('parent_id') != row['id'], 'boundary may not contain itself')
        _rectangle(row)
        if provider == 'Azure' and row['kind'] == 'resource-group':
            _need(row.get('is_network_boundary') is False, 'Azure resource group must not be marked as network isolation')
        if provider == 'GCP' and row['kind'] == 'project':
            _need(row.get('is_identity_boundary') is True, 'GCP project must be explicit as an identity/resource boundary')
    for row in services:
        _need(row.get('label') and row.get('official_name') and row.get('category'), 'cloud service needs label, official name and category')
        _need(row.get('boundary_id') in boundary_ids or row.get('scope') == 'external', 'cloud service boundary is unknown')
        _need(row.get('scope') in {'global', 'regional', 'zonal', 'external'}, 'cloud service scope invalid')
        _position(row)
    for row in flows:
        _need(row.get('source') in service_ids and row.get('target') in service_ids and row['source'] != row['target'], 'cloud flow endpoints invalid')
        _need(row.get('label') and row.get('protocol') and row.get('classification'), 'cloud flow needs label, protocol and classification')
        _need(row.get('security_control'), 'cloud flow needs an explicit security control')
    parent_map = {row['id']: row.get('parent_id') for row in boundaries}
    for start in boundary_ids:
        seen = set()
        cursor = start
        while cursor is not None:
            _need(cursor not in seen, 'boundary containment cycle detected')
            seen.add(cursor)
            cursor = parent_map[cursor]
    return {
        'mode': 'cloud-architecture', 'provider': provider, 'boundaries': len(boundaries),
        'services': len(services), 'flows': len(flows),
        'service_categories': dict(sorted(Counter(row['category'] for row in services).items())),
        'directed_labeled_flows': 'passed', 'boundary_semantics': 'passed',
        'icon_policy': 'official names retained; neutral badges rendered; official icon packs not bundled',
    }


def _reachable(starts, edges):
    adjacency = defaultdict(list)
    for source, target in edges:
        adjacency[source].append(target)
    seen = set(starts)
    queue = deque(starts)
    while queue:
        for target in adjacency[queue.popleft()]:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def _enterprise_layered(data):
    _base(data, 'enterprise-layered')
    layers = _rows(data, 'layers')
    elements = _rows(data, 'elements')
    traces = _rows(data, 'traces')
    orders = [row.get('order') for row in layers]
    _need(sorted(orders) == list(range(1, len(layers) + 1)), 'enterprise layer order must be contiguous from 1')
    allowed_layers = {'strategy', 'business', 'application', 'data', 'technology'}
    layer_ids = {row['id'] for row in layers}
    for row in layers:
        _need(row.get('label') and row.get('kind') in allowed_layers, 'enterprise layer label and kind required')
    element_ids = {row['id'] for row in elements}
    for row in elements:
        _need(row.get('label') and row.get('responsibility') and row.get('layer_id') in layer_ids, 'enterprise element label, responsibility and layer required')
        _position(row)
    allowed_relations = {'supports', 'uses', 'realizes', 'hosts', 'governs'}
    pairs = []
    for row in traces:
        _need(row.get('source') in element_ids and row.get('target') in element_ids and row['source'] != row['target'], 'enterprise trace endpoints invalid')
        _need(row.get('relationship') in allowed_relations and row.get('evidence'), 'enterprise trace relationship and evidence required')
        pairs.append((row['source'], row['target']))
    starts = [row['id'] for row in elements if next(layer['kind'] for layer in layers if layer['id'] == row['layer_id']) in {'strategy', 'business'}]
    reached = _reachable(starts, pairs)
    _need(reached == element_ids, 'every enterprise element must be traceable from strategy or business')
    return {
        'mode': 'enterprise-layered', 'layers': len(layers), 'elements': len(elements), 'traces': len(traces),
        'layer_order': [row['kind'] for row in sorted(layers, key=lambda item: item['order'])],
        'strategy_to_technology_traceability': 'passed',
    }


def _archimate(data):
    _base(data, 'archimate-layered')
    _need(data.get('specification_version') == '3.2', 'ArchiMate example is scoped to specification version 3.2')
    _need(data.get('viewpoint') == 'layered', 'current ArchiMate subset supports the layered viewpoint')
    elements = _rows(data, 'elements')
    relations = _rows(data, 'relations')
    allowed_layers = {'business', 'application', 'technology'}
    allowed_aspects = {'active-structure', 'behavior', 'passive-structure'}
    element_ids = {row['id'] for row in elements}
    by_id = {row['id']: row for row in elements}
    for row in elements:
        _need(row.get('label') and row.get('layer') in allowed_layers and row.get('aspect') in allowed_aspects and row.get('element_type'), 'ArchiMate element needs label, layer, aspect and element type')
        _position(row)
    allowed_relations = {'composition', 'assignment', 'realization', 'serving', 'access', 'triggering', 'flow'}
    for row in relations:
        _need(row.get('source') in element_ids and row.get('target') in element_ids and row['source'] != row['target'], 'ArchiMate relation endpoints invalid')
        relation = row.get('relationship')
        _need(relation in allowed_relations, 'unsupported ArchiMate relation in curated subset')
        source = by_id[row['source']]
        target = by_id[row['target']]
        if relation == 'assignment':
            _need(source['aspect'] == 'active-structure' and target['aspect'] == 'behavior', 'assignment must connect active structure to behavior in this subset')
        elif relation == 'access':
            _need(source['aspect'] == 'behavior' and target['aspect'] == 'passive-structure', 'access must connect behavior to passive structure in this subset')
        elif relation == 'triggering':
            _need(source['aspect'] == target['aspect'] == 'behavior', 'triggering must connect behavior elements in this subset')
        _need(row.get('evidence'), 'ArchiMate relation evidence required')
    return {
        'mode': 'archimate-layered', 'specification_version': '3.2', 'viewpoint': 'layered',
        'elements': len(elements), 'relations': len(relations),
        'layers': dict(sorted(Counter(row['layer'] for row in elements).items())),
        'aspects': dict(sorted(Counter(row['aspect'] for row in elements).items())),
        'curated_relationship_subset': 'passed',
    }


def _selector_matches(selector, labels):
    return all(labels.get(key) == value for key, value in selector.items())


def _kubernetes(data):
    _base(data, 'kubernetes-architecture')
    clusters = _rows(data, 'clusters')
    namespaces = _rows(data, 'namespaces')
    components = _rows(data, 'control_plane_components')
    nodes = _rows(data, 'worker_nodes')
    workloads = _rows(data, 'workloads')
    services = _rows(data, 'services')
    ingresses = _rows(data, 'ingresses')
    configs = _rows(data, 'configuration')
    claims = _rows(data, 'persistent_volume_claims')
    cluster_ids = {row['id'] for row in clusters}
    namespace_ids = {row['id'] for row in namespaces}
    workload_ids = {row['id'] for row in workloads}
    service_ids = {row['id'] for row in services}
    for row in clusters:
        _need(row.get('label') and row.get('version'), 'cluster label and version required')
    for row in namespaces:
        _need(row.get('label') and row.get('cluster_id') in cluster_ids, 'namespace must belong to a cluster')
    required_components = {'kube-apiserver', 'etcd', 'kube-scheduler', 'kube-controller-manager'}
    component_names = {row.get('component') for row in components}
    _need(required_components <= component_names, 'control plane is missing a required core component')
    for row in components:
        _need(row.get('cluster_id') in cluster_ids and row.get('component') and row.get('responsibility'), 'control-plane component fields required')
        _position(row)
    for row in nodes:
        _need(row.get('cluster_id') in cluster_ids and row.get('label') and row.get('kubelet') and row.get('container_runtime'), 'worker node needs kubelet and container runtime')
        _position(row)
    for row in workloads:
        _need(row.get('namespace_id') in namespace_ids and row.get('kind') in {'Deployment', 'StatefulSet', 'DaemonSet'}, 'workload namespace or kind invalid')
        _need(isinstance(row.get('replicas'), int) and row['replicas'] >= 1, 'workload replicas must be a positive integer')
        _need(isinstance(row.get('pod_labels'), dict) and row['pod_labels'], 'workload pod labels required')
        _need(row.get('image') and row.get('label'), 'workload image and label required')
        _position(row)
    selected = defaultdict(list)
    for row in services:
        _need(row.get('namespace_id') in namespace_ids and row.get('label'), 'Service namespace and label required')
        _need(isinstance(row.get('selector'), dict) and row['selector'], 'Service selector required')
        ports = row.get('ports')
        _need(isinstance(ports, list) and ports, 'Service ports required')
        for port in ports:
            _need(isinstance(port.get('port'), int) and isinstance(port.get('target_port'), int) and port.get('protocol') in {'TCP', 'UDP'}, 'Service port mapping invalid')
        matches = [workload['id'] for workload in workloads if workload['namespace_id'] == row['namespace_id'] and _selector_matches(row['selector'], workload['pod_labels'])]
        _need(matches, f"Service {row['id']} selector matches no workload")
        selected[row['id']] = matches
        _position(row)
    for row in ingresses:
        _need(row.get('namespace_id') in namespace_ids and row.get('host'), 'Ingress namespace and host required')
        routes = row.get('routes')
        _need(isinstance(routes, list) and routes, 'Ingress routes required')
        for route in routes:
            _need(route.get('service_id') in service_ids and route.get('path') and isinstance(route.get('port'), int), 'Ingress route invalid')
            target = next(item for item in services if item['id'] == route['service_id'])
            _need(target['namespace_id'] == row['namespace_id'], 'Ingress may only route to a Service in the same namespace in this example')
        _position(row)
    for row in configs:
        _need(row.get('namespace_id') in namespace_ids and row.get('kind') in {'ConfigMap', 'Secret'}, 'configuration namespace or kind invalid')
        consumers = row.get('consumer_workload_ids')
        _need(isinstance(consumers, list) and consumers and set(consumers) <= workload_ids, 'configuration consumers invalid')
        if row['kind'] == 'Secret':
            _need(row.get('values_redacted') is True, 'Secret values must remain redacted')
        _position(row)
    for row in claims:
        _need(row.get('namespace_id') in namespace_ids and row.get('label') and row.get('storage_class'), 'PVC namespace, label and storage class required')
        _need(isinstance(row.get('size_gib'), (int, float)) and row['size_gib'] > 0, 'PVC size must be positive')
        consumers = row.get('consumer_workload_ids')
        _need(isinstance(consumers, list) and consumers and set(consumers) <= workload_ids, 'PVC consumers invalid')
        _position(row)
    return {
        'mode': 'kubernetes-architecture', 'clusters': len(clusters), 'namespaces': len(namespaces),
        'control_plane_components': len(components), 'worker_nodes': len(nodes), 'workloads': len(workloads),
        'desired_pods': sum(row['replicas'] for row in workloads), 'services': len(services),
        'service_selector_matches': dict(sorted(selected.items())), 'ingress_routes': sum(len(row['routes']) for row in ingresses),
        'config_objects': len(configs), 'persistent_volume_claims': len(claims),
        'selector_resolution': 'passed', 'secret_redaction': 'passed',
    }


def _c4_component(data):
    _base(data, 'c4-component')
    scope = data.get('scope')
    _need(isinstance(scope, dict) and scope.get('software_system') and scope.get('container_id') and scope.get('container_label'), 'C4 component scope requires one software system and one container')
    components = _rows(data, 'components')
    externals = _rows(data, 'externals')
    relationships = _rows(data, 'relationships')
    component_ids = {row['id'] for row in components}
    external_ids = {row['id'] for row in externals}
    for row in components:
        _need(row.get('label') and row.get('responsibility') and row.get('technology'), 'C4 component label, responsibility and technology required')
        _need(row.get('container_id') == scope['container_id'], 'every component must belong to the single in-scope container')
        _position(row)
    for row in externals:
        _need(row.get('label') and row.get('description') and row.get('type') in {'person', 'software-system', 'container'}, 'C4 external element invalid')
        _position(row)
    ids = component_ids | external_ids
    for row in relationships:
        _need(row.get('source') in ids and row.get('target') in ids and row['source'] != row['target'], 'C4 component relationship endpoints invalid')
        _need(row.get('description') and row.get('technology') and row.get('evidence'), 'C4 component relationship needs description, technology and evidence')
    return {
        'mode': 'c4-component', 'software_system': scope['software_system'], 'container_id': scope['container_id'],
        'components': len(components), 'external_elements': len(externals), 'relationships': len(relationships),
        'single_container_scope': 'passed', 'responsibility_coverage': 'passed',
    }


def _c4_dynamic(data):
    _base(data, 'c4-dynamic')
    _need(data.get('scenario') and data.get('static_view_reference'), 'C4 dynamic scenario and static view reference required')
    elements = _rows(data, 'elements')
    registry = _rows(data, 'relationship_registry')
    interactions = data.get('interactions')
    _need(isinstance(interactions, list) and interactions, 'interactions required')
    element_ids = {row['id'] for row in elements}
    for row in elements:
        _need(row.get('label') and row.get('description') and row.get('type') in {'person', 'software-system', 'container', 'component'}, 'C4 dynamic element invalid')
        _position(row)
    registry_by_id = {}
    for row in registry:
        _need(row.get('source') in element_ids and row.get('target') in element_ids and row['source'] != row['target'], 'static relationship endpoints invalid')
        _need(row.get('description'), 'static relationship description required')
        registry_by_id[row['id']] = row
    orders = [row.get('order') for row in interactions]
    _need(orders == list(range(1, len(interactions) + 1)), 'C4 dynamic interaction order must be contiguous and listed from 1')
    for row in interactions:
        _need(row.get('source') in element_ids and row.get('target') in element_ids and row['source'] != row['target'], 'C4 dynamic interaction endpoints invalid')
        _need(row.get('description') and row.get('technology'), 'C4 dynamic interaction description and technology required')
        relationship = registry_by_id.get(row.get('static_relationship_id'))
        _need(relationship and relationship['source'] == row['source'] and relationship['target'] == row['target'], 'dynamic interaction must reference a matching stable relationship')
    return {
        'mode': 'c4-dynamic', 'scenario': data['scenario'], 'elements': len(elements),
        'interactions': len(interactions), 'ordered_steps': orders,
        'stable_relationship_references': 'passed', 'contiguous_order': 'passed',
    }


ANALYZERS = {
    'application-landscape': _application_landscape,
    'cloud-architecture': _cloud_architecture,
    'enterprise-layered': _enterprise_layered,
    'archimate-layered': _archimate,
    'kubernetes-architecture': _kubernetes,
    'c4-component': _c4_component,
    'c4-dynamic': _c4_dynamic,
}


def analyze(data):
    _need(data.get('mode') in ANALYZERS, 'unsupported architecture mode')
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
        'svg.hashsalt': 'diagram-studio-architecture-models-v1',
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


def _node(ax, row, *, w=.17, h=.105, color=BLUE, title=None, detail=None, z=4):
    from matplotlib.patches import FancyBboxPatch
    x, y = row['position']
    patch = FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle='round,pad=.008,rounding_size=.012',
                           fc=PAPER, ec=color, lw=1.35, zorder=z)
    ax.add_patch(patch)
    label = title or row.get('label', row.get('official_name', row['id']))
    ax.text(x, y + .018, _wrap(label, 13), ha='center', va='center', fontsize=9.7, weight='medium', zorder=z+1)
    if detail:
        ax.text(x, y - .032, _wrap(detail, 19), ha='center', va='center', fontsize=7.2, color=MUTED, zorder=z+1)
    return (x - w/2, y - h/2, w, h)


def _arrow(ax, source, target, label, *, color=MUTED, dashed=False, rad=0, offset=(0, 0), z=2):
    sx, sy = source['position']; tx, ty = target['position']
    ax.annotate('', xy=(tx, ty), xytext=(sx, sy),
                arrowprops=dict(arrowstyle='-|>', color=color, lw=1.15, linestyle='--' if dashed else '-',
                                shrinkA=35, shrinkB=35, connectionstyle=f'arc3,rad={rad}'), zorder=z)
    mx, my = (sx + tx)/2 + offset[0], (sy + ty)/2 + offset[1]
    ax.text(mx, my, _wrap(label, 20), fontsize=7.2, color=color, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=.18', fc=BG, ec='none', alpha=.96), zorder=z+3)


def _boundary(ax, row, *, color=BLUE, fill=PAPER, alpha=.45, lw=1.2):
    from matplotlib.patches import FancyBboxPatch
    x, y, w, h = row['rect']
    patch = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=.008,rounding_size=.012', fc=fill, ec=color, lw=lw, alpha=alpha, zorder=.5)
    ax.add_patch(patch)
    kinds = {
        'account':'账号','region':'区域','vpc':'VPC','availability-zone':'可用区','subnet':'子网',
        'tenant':'租户','subscription':'订阅','resource-group':'资源组','virtual-network':'虚拟网络',
        'organization':'组织','folder':'文件夹','project':'项目',
    }
    right = row.get('label_side') == 'right'
    kind_label = kinds.get(row['kind'], row['kind'])
    boundary_label = row['label'] if kind_label.lower() in row['label'].lower() else f"{row['label']}  ·  {kind_label}"
    ax.text(x + w - .012 if right else x + .012, y + h - .018,
            boundary_label, fontsize=7.6, color=color,
            va='top', ha='right' if right else 'left', weight='medium', zorder=1)


def _footer(fig, calc):
    facts = []
    for key, value in calc.items():
        if key in {'mode', 'data_status', 'assumptions', 'service_categories', 'layers', 'aspects', 'service_selector_matches', 'integration_patterns'}:
            continue
        if isinstance(value, (str, int, float)) and len(facts) < 4:
            facts.append(f"{key.replace('_', ' ')}: {value}")
    fig.text(.05, .035, '  ·  '.join(facts), fontsize=7.5, color=MUTED, va='bottom')
    fig.text(.95, .035, '模拟数据 / 关系与边界由输入校验', fontsize=7.5, color=MUTED, va='bottom', ha='right')


def _render_application(data, calc, fig, ax):
    by_id = {row['id']: row for key in ('capabilities', 'applications', 'data_domains') for row in data[key]}
    for row in data['capabilities']:
        _node(ax, row, w=.17, h=.085, color=GREEN, detail='业务能力 · '+row['owner'])
    for row in data['applications']:
        lifecycle = {'invest':'重点投入','maintain':'持续维护','migrate':'迁移整合','retire':'计划退役'}[row['lifecycle']]
        _node(ax, row, w=.17, h=.11, color=BLUE, detail=f"{row['owner']} · {lifecycle}")
    for row in data['data_domains']:
        _node(ax, row, w=.15, h=.09, color=AMBER, detail='数据域 · '+row['classification'])
    for row in data['capability_links']:
        if row.get('render') is False:
            continue
        _arrow(ax, by_id[row['capability_id']], by_id[row['application_id']], {'primary':'主责','supporting':'支撑'}[row['coverage']], color=GREEN, dashed=True, offset=tuple(row.get('label_offset', [0, 0])))
    for row in data['integrations']:
        pattern = {'sync':'同步','event':'事件','batch':'批处理'}[row['pattern']]
        _arrow(ax, by_id[row['source']], by_id[row['target']], f"{pattern} · {row['payload']}", color=BLUE, rad=row.get('rad', 0), offset=tuple(row.get('label_offset', [0, 0])))
    for row in data['data_domains']:
        _arrow(ax, by_id[row['system_of_record']], row, '主记录系统', color=AMBER, dashed=True, offset=tuple(row.get('label_offset', [0, 0])))
    ax.text(.025, .95, '业务能力', color=GREEN, fontsize=8, weight='medium')
    ax.text(.38, .95, '应用组合', color=BLUE, fontsize=8, weight='medium')
    ax.text(.83, .95, '数据责任', color=AMBER, fontsize=8, weight='medium')


def _render_cloud(data, calc, fig, ax):
    for i, row in enumerate(data['boundaries']):
        _boundary(ax, row, color=COLORS[i % len(COLORS)], alpha=.28 + .05 * (i % 2))
    services = {row['id']: row for row in data['services']}
    category_colors = {'edge': RED, 'compute': BLUE, 'integration': PLUM, 'data': AMBER, 'security': GREEN, 'operations': MUTED, 'external': INK}
    categories = {'edge':'边缘','compute':'计算','integration':'集成','data':'数据','security':'安全','operations':'运维','external':'外部'}
    scopes = {'global':'全局','regional':'区域','zonal':'可用区','external':'外部'}
    for row in data['services']:
        _node(ax, row, w=.145, h=.09, color=category_colors.get(row['category'], BLUE), title=row['official_name'], detail=f"{categories[row['category']]} · {scopes[row['scope']]}")
    for row in data['flows']:
        _arrow(ax, services[row['source']], services[row['target']], f"{row['label']}\n{row['protocol']}", color=BLUE, rad=row.get('rad', 0), offset=tuple(row.get('label_offset', [0, 0])))
    fig.text(.95, .885, f"{data['provider']} · 官方服务名 / 中性徽标", fontsize=8.2, color=MUTED, ha='right')


def _render_enterprise(data, calc, fig, ax, archimate=False):
    if archimate:
        order = ['business', 'application', 'technology']
        layer_rows = [{'id': item, 'label': {'business':'业务层','application':'应用层','technology':'技术层'}[item], 'kind': item, 'order': i+1} for i, item in enumerate(order)]
        elements = data['elements']
        relation_key = 'relations'
    else:
        layer_rows = sorted(data['layers'], key=lambda item: item['order'])
        elements = data['elements']
        relation_key = 'traces'
    n = len(layer_rows)
    y_positions = {}
    for i, layer in enumerate(layer_rows):
        y = .84 - i * (.74 / max(1, n-1))
        y_positions[layer['id'] if not archimate else layer['kind']] = y
        ax.axhspan(y-.075, y+.075, xmin=.08, xmax=.98, facecolor=COLORS[i % len(COLORS)], alpha=.065, edgecolor='none', zorder=.1)
        ax.text(.015, y, layer['label'], color=COLORS[i % len(COLORS)], fontsize=8.7, va='center', weight='medium')
    draw_rows = []
    for row in elements:
        copy = dict(row)
        layer_id = row['layer'] if archimate else row['layer_id']
        copy['position'] = [row['position'][0], y_positions[layer_id]]
        draw_rows.append(copy)
    by_id = {row['id']: row for row in draw_rows}
    for i, row in enumerate(draw_rows):
        detail = row.get('element_type') if archimate else row.get('responsibility')
        color = COLORS[list(y_positions).index(row.get('layer', row.get('layer_id'))) % len(COLORS)]
        _node(ax, row, w=.145 if len(elements) > 9 else .17, h=.085, color=color, detail=detail)
    for row in data[relation_key]:
        if row.get('render') is False:
            continue
        rel = row.get('relationship', '')
        labels = {'supports':'支撑','uses':'使用','realizes':'实现','hosts':'承载','governs':'约束',
                  'composition':'组合','assignment':'指派','realization':'实现','serving':'服务','access':'访问','triggering':'触发','flow':'流'}
        default_offset = [0, -.028] if rel == 'hosts' else [0, .018] if rel == 'uses' else [0, 0]
        _arrow(ax, by_id[row['source']], by_id[row['target']], labels.get(rel, rel), color=MUTED, dashed=rel in {'supports', 'serving'}, rad=row.get('rad', 0), offset=tuple(row.get('label_offset', default_offset)))
    if archimate:
        fig.text(.95, .885, 'ArchiMate 3.2 · layered viewpoint · curated subset', fontsize=8.1, color=MUTED, ha='right')


def _render_kubernetes(data, calc, fig, ax):
    from matplotlib.patches import FancyBboxPatch
    control = FancyBboxPatch((.02,.70),.96,.25,boxstyle='round,pad=.008,rounding_size=.012',fc=PAPER,ec=PLUM,lw=1.15,zorder=.4)
    workload = FancyBboxPatch((.02,.05),.96,.59,boxstyle='round,pad=.008,rounding_size=.012',fc=PAPER,ec=BLUE,lw=1.15,zorder=.4)
    ax.add_patch(control); ax.add_patch(workload)
    ax.text(.035,.925,'控制平面 · desired state / reconciliation',fontsize=8,color=PLUM,va='top',weight='medium')
    namespace = data['namespaces'][0]
    ax.text(.035,.615,f"Namespace · {namespace['label']}",fontsize=8,color=BLUE,va='top',weight='medium')
    by_id = {}
    for row in data['control_plane_components']:
        by_id[row['id']] = row
        _node(ax,row,w=.155,h=.085,color=PLUM,title=row['component'],detail=row['responsibility'])
    for row in data['worker_nodes']:
        by_id[row['id']] = row
        _node(ax,row,w=.17,h=.085,color=MUTED,detail=f"kubelet/{row['container_runtime']}")
    for group, color, detail_key in [
        ('ingresses', RED, 'host'), ('services', GREEN, None), ('workloads', BLUE, 'kind'),
        ('configuration', AMBER, 'kind'), ('persistent_volume_claims', PLUM, 'storage_class')]:
        for row in data[group]:
            by_id[row['id']] = row
            detail = row.get(detail_key) if detail_key else 'Service · selector'
            if group == 'workloads': detail += f" · {row['replicas']} replicas"
            if group == 'services': detail = 'Service · 选择器'
            if group == 'configuration' and row['kind'] == 'Secret': detail = 'Secret · 值已脱敏'
            _node(ax,row,w=.145,h=.085,color=color,detail=detail)
    for ingress in data['ingresses']:
        for route in ingress['routes']:
            _arrow(ax, ingress, by_id[route['service_id']], f"{route['path']} :{route['port']}", color=RED)
    for service in data['services']:
        for workload_id in calc['service_selector_matches'][service['id']]:
            _arrow(ax, service, by_id[workload_id], '选择器', color=GREEN)
    for cfg in data['configuration']:
        for index, workload_id in enumerate(cfg['consumer_workload_ids']):
            offset = (-.015, .018) if index == 0 else (.025, -.022)
            _arrow(ax, cfg, by_id[workload_id], '配置引用' if cfg['kind']=='ConfigMap' else '密钥引用', color=AMBER, dashed=True, offset=offset)
    for claim in data['persistent_volume_claims']:
        for workload_id in claim['consumer_workload_ids']:
            _arrow(ax, claim, by_id[workload_id], '挂载', color=PLUM, dashed=True)
    ax.text(.50,.105,'Worker nodes：运行位置示意；Deployment 不固定到单一节点',fontsize=7.1,color=MUTED,ha='center')


def _render_c4_component(data, calc, fig, ax):
    from matplotlib.patches import FancyBboxPatch
    scope = data['scope']
    box = FancyBboxPatch((.19,.10),.62,.79,boxstyle='round,pad=.008,rounding_size=.012',fc=PAPER,ec=BLUE,lw=1.45,zorder=.4)
    ax.add_patch(box)
    ax.text(.21,.86,f"Container · {scope['container_label']}  /  {scope['software_system']}",fontsize=8.3,color=BLUE,weight='medium')
    by_id = {}
    for row in data['components']:
        by_id[row['id']] = row
        _node(ax,row,w=.16,h=.105,color=BLUE,detail=f"{row['technology']} · {row['responsibility']}")
    for row in data['externals']:
        by_id[row['id']] = row
        types = {'person':'人员','software-system':'软件系统','container':'容器'}
        _node(ax,row,w=.15,h=.10,color=AMBER if row['type']=='person' else GREEN,detail=types[row['type']])
    for row in data['relationships']:
        _arrow(ax,by_id[row['source']],by_id[row['target']],f"{row['description']}\n[{row['technology']}]",color=MUTED,rad=row.get('rad',0),offset=tuple(row.get('label_offset',[0,0])))


def _render_c4_dynamic(data, calc, fig, ax):
    by_id = {row['id']: row for row in data['elements']}
    type_colors = {'person': AMBER, 'software-system': GREEN, 'container': BLUE, 'component': PLUM}
    types = {'person':'人员','software-system':'软件系统','container':'容器','component':'组件'}
    for row in data['elements']:
        _node(ax,row,w=.16,h=.105,color=type_colors[row['type']],detail=types[row['type']])
    for row in data['interactions']:
        _arrow(ax,by_id[row['source']],by_id[row['target']],f"{row['order']}. {row['description']}\n[{row['technology']}]",color=COLORS[(row['order']-1)%len(COLORS)],rad=row.get('rad',0),offset=tuple(row.get('label_offset',[0,0])))
    ax.text(.02,.95,'场景：'+data['scenario'],fontsize=8.7,color=INK,weight='medium')
    ax.text(.98,.95,'静态视图：'+data['static_view_reference'],fontsize=7.8,color=MUTED,ha='right')


RENDERERS = {
    'application-landscape': _render_application,
    'cloud-architecture': _render_cloud,
    'enterprise-layered': lambda d,c,f,a: _render_enterprise(d,c,f,a,False),
    'archimate-layered': lambda d,c,f,a: _render_enterprise(d,c,f,a,True),
    'kubernetes-architecture': _render_kubernetes,
    'c4-component': _render_c4_component,
    'c4-dynamic': _render_c4_dynamic,
}


def render(data, out_dir, stem):
    calc = analyze(data)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    fig, ax = _figure(data)
    RENDERERS[data['mode']](data, calc, fig, ax)
    _footer(fig, calc)
    svg = out / f'{stem}.svg'; png = out / f'{stem}.png'
    fig.savefig(svg, format='svg', metadata={'Date': None})
    fig.savefig(png, format='png', dpi=160, metadata={'Software': 'diagram-studio architecture_models.py'})
    import matplotlib.pyplot as plt
    plt.close(fig)
    (out / f'{stem}.input.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (out / f'{stem}.calculation.json').write_text(json.dumps(calc, ensure_ascii=False, indent=2) + '\n')
    qa = {
        'mode': data['mode'], 'errors': [], 'warnings': [], 'layout_issues': [],
        'semantic_validation': 'passed', 'editable_source': f'{stem}.input.json',
        'visual_review': 'pending manual browser review',
    }
    (out / f'{stem}.qa.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2) + '\n')
    return calc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('--out', required=True)
    parser.add_argument('--name')
    args = parser.parse_args()
    source = Path(args.input)
    data = json.loads(source.read_text())
    stem = args.name or source.stem
    result = render(data, args.out, stem)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
