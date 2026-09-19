"""Validated UML activity-diagram subset; not full UML metamodel conformance."""
from collections import Counter, defaultdict, deque
import re


NODE_KINDS = {
    "action",
    "object",
    "initial",
    "activity_final",
    "flow_final",
    "decision",
    "merge",
    "fork",
    "join",
}
CONTROL_KINDS = {"initial", "activity_final", "flow_final", "decision", "merge", "fork", "join"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, required, optional=()):
    need(isinstance(value, dict), "expected object")
    keys = set(value)
    required = set(required)
    allowed = required | set(optional)
    need(required <= keys, "missing fields: " + ", ".join(sorted(required - keys)))
    need(keys <= allowed, "unknown fields: " + ", ".join(sorted(keys - allowed)))


def text(value, label):
    need(isinstance(value, str) and value.strip(), label + " must be non-empty text")


def identifier(value, label):
    text(value, label)
    need(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value) is not None, label + " has invalid characters")


def whole(value, label):
    need(isinstance(value, int) and not isinstance(value, bool) and value >= 0, label + " must be a non-negative integer")


def reachable(start, adjacency):
    seen = set(start)
    queue = deque(start)
    while queue:
        current = queue.popleft()
        for other in adjacency[current]:
            if other not in seen:
                seen.add(other)
                queue.append(other)
    return seen


def validate(document):
    exact(document, ("title", "scope", "assumptions", "partitions", "nodes", "edges"))
    text(document["title"], "title")
    text(document["scope"], "scope")
    need(isinstance(document["assumptions"], list) and document["assumptions"], "assumptions must be a non-empty list")
    for item in document["assumptions"]:
        text(item, "assumption")
    need(isinstance(document["partitions"], list) and 2 <= len(document["partitions"]) <= 5, "partitions must contain two to five lanes")
    need(isinstance(document["nodes"], list) and 5 <= len(document["nodes"]) <= 40, "nodes must contain five to forty items")
    need(isinstance(document["edges"], list) and document["edges"], "edges must be non-empty")

    ids = set()
    partitions = {}
    orders = set()
    for partition in document["partitions"]:
        exact(partition, ("id", "name", "order"))
        identifier(partition["id"], "partition id")
        text(partition["name"], "partition name")
        whole(partition["order"], "partition order")
        need(partition["id"] not in ids, "duplicate id: " + partition["id"])
        need(partition["order"] not in orders, "duplicate partition order")
        ids.add(partition["id"])
        orders.add(partition["order"])
        partitions[partition["id"]] = dict(partition)
    need(orders == set(range(len(partitions))), "partition order must be contiguous from zero")

    nodes = {}
    slots = set()
    kinds = Counter()
    for node in document["nodes"]:
        exact(node, ("id", "name", "kind", "partition", "row"), ("description",))
        identifier(node["id"], "node id")
        text(node["name"], "node name")
        need(node["kind"] in NODE_KINDS, "unknown node kind: " + str(node["kind"]))
        need(node["partition"] in partitions, "unknown node partition: " + str(node["partition"]))
        whole(node["row"], "node row")
        need(node["row"] <= 20, "node row exceeds current layout capacity")
        need(node["id"] not in ids, "duplicate id: " + node["id"])
        slot = (node["partition"], node["row"])
        need(slot not in slots, "duplicate node lane/row position: " + str(slot))
        if "description" in node:
            text(node["description"], "node description")
        ids.add(node["id"])
        slots.add(slot)
        nodes[node["id"]] = dict(node)
        kinds[node["kind"]] += 1
    need(kinds["initial"] == 1, "current subset requires exactly one initial node")
    need(kinds["activity_final"] >= 1, "at least one activity final is required")
    need(kinds["action"] >= 2, "at least two actions are required")

    edges = []
    edge_ids = set()
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    adjacency = defaultdict(list)
    reverse = defaultdict(list)
    for edge in document["edges"]:
        exact(edge, ("id", "kind", "source", "target"), ("guard", "label"))
        identifier(edge["id"], "edge id")
        need(edge["id"] not in edge_ids, "duplicate edge id: " + edge["id"])
        need(edge["kind"] in ("control", "object"), "edge kind must be control or object")
        need(edge["source"] in nodes and edge["target"] in nodes, "edge endpoint is unknown: " + edge["id"])
        need(edge["source"] != edge["target"], "self edge is not allowed: " + edge["id"])
        if "guard" in edge:
            text(edge["guard"], "edge guard")
        if "label" in edge:
            text(edge["label"], "edge label")
        source_kind = nodes[edge["source"]]["kind"]
        target_kind = nodes[edge["target"]]["kind"]
        if edge["kind"] == "object":
            need("object" in (source_kind, target_kind), "current subset requires every object flow to touch an object node")
            need(source_kind not in CONTROL_KINDS and target_kind not in CONTROL_KINDS, "object flow cannot connect a control node in this subset")
        else:
            need(source_kind != "object" and target_kind != "object", "control flow cannot connect an object node")
        edge_ids.add(edge["id"])
        copy = dict(edge)
        edges.append(copy)
        incoming[edge["target"]].append(copy)
        outgoing[edge["source"]].append(copy)
        adjacency[edge["source"]].append(edge["target"])
        reverse[edge["target"]].append(edge["source"])

    for node_id, node in nodes.items():
        before, after = incoming[node_id], outgoing[node_id]
        kind = node["kind"]
        if kind == "initial":
            need(not before, "initial node cannot have incoming edges")
            need(after and all(edge["kind"] == "control" for edge in after), "initial node must emit control flow")
        elif kind in ("activity_final", "flow_final"):
            need(before and not after, kind + " must have incoming edges and no outgoing edges")
            need(all(edge["kind"] == "control" for edge in before), kind + " only accepts control flow in this subset")
        elif kind == "decision":
            need(len(before) == 1 and len(after) >= 2, "decision requires one incoming and at least two outgoing edges")
            need(all("guard" in edge for edge in after), "every decision output requires a guard")
            need(len({edge["guard"] for edge in after}) == len(after), "decision guards must be unique")
            need(all(edge["kind"] == before[0]["kind"] for edge in after), "decision input/output flow kinds must match")
        elif kind == "merge":
            need(len(before) >= 2 and len(after) == 1, "merge requires multiple incoming and one outgoing edge")
            need(len({edge["kind"] for edge in before + after}) == 1, "merge flow kinds must match")
        elif kind == "fork":
            need(len(before) == 1 and len(after) >= 2, "fork requires one incoming and multiple outgoing edges")
            need(len({edge["kind"] for edge in before + after}) == 1, "fork flow kinds must match")
        elif kind == "join":
            need(len(before) >= 2 and len(after) == 1, "join requires multiple incoming and one outgoing edge")
            need(all(edge["kind"] == "control" for edge in before + after), "current subset validates control-flow joins only")
        else:
            need(before or kind == "action", "node has no incoming flow: " + node_id)
            need(after or kind == "action", "node has no outgoing flow: " + node_id)

    start = next(node_id for node_id, node in nodes.items() if node["kind"] == "initial")
    finals = {node_id for node_id, node in nodes.items() if node["kind"] in ("activity_final", "flow_final")}
    need(reachable([start], adjacency) == set(nodes), "all nodes must be reachable from the initial node")
    need(reachable(finals, reverse) == set(nodes), "every node must lead to a final node")

    return {
        "title": document["title"],
        "scope": document["scope"],
        "partitions": sorted((dict(item) for item in document["partitions"]), key=lambda item: item["order"]),
        "nodes": [dict(item) for item in document["nodes"]],
        "edges": edges,
        "counts": {
            "partitions": len(partitions),
            "nodes": len(nodes),
            "actions": kinds["action"],
            "object_nodes": kinds["object"],
            "control_nodes": sum(kinds[kind] for kind in CONTROL_KINDS),
            "control_flows": sum(edge["kind"] == "control" for edge in edges),
            "object_flows": sum(edge["kind"] == "object" for edge in edges),
        },
        "scope_note": "actions, explicit object nodes, activity partitions, initial/activity-final/flow-final, decision/merge/fork/join and explicit control/object flows; not full UML metamodel conformance",
    }
