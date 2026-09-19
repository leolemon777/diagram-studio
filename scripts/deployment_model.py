"""Validated UML deployment-diagram subset; not full UML metamodel conformance."""
import re


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


def contiguous(values, label):
    values = sorted(values)
    need(values == list(range(len(values))), label + " must be contiguous from zero")


def validate(document):
    exact(
        document,
        (
            "title",
            "scope",
            "assumptions",
            "devices",
            "environments",
            "artifacts",
            "components",
            "manifestations",
            "communication_paths",
        ),
    )
    text(document["title"], "title")
    text(document["scope"], "scope")
    need(isinstance(document["assumptions"], list) and document["assumptions"], "assumptions must be a non-empty list")
    for item in document["assumptions"]:
        text(item, "assumption")
    for field in ("devices", "environments", "artifacts", "components", "manifestations", "communication_paths"):
        need(isinstance(document[field], list) and document[field], field + " must be a non-empty list")

    ids = set()
    positions = set()
    devices = {}
    for item in document["devices"]:
        exact(item, ("id", "name", "instance", "type", "column", "row"))
        identifier(item["id"], "device id")
        for key in ("name", "instance", "type"):
            text(item[key], "device " + key)
        whole(item["column"], "device column")
        whole(item["row"], "device row")
        need(item["id"] not in ids, "duplicate id: " + item["id"])
        slot = (item["column"], item["row"])
        need(slot not in positions, "duplicate device grid position: " + str(slot))
        positions.add(slot)
        ids.add(item["id"])
        devices[item["id"]] = dict(item)
    contiguous({item["column"] for item in devices.values()}, "device columns")
    need({item["row"] for item in devices.values()} == {0}, "current subset supports one device row")

    environments = {}
    environment_orders = {}
    for item in document["environments"]:
        exact(item, ("id", "name", "instance", "type", "device", "order"))
        identifier(item["id"], "environment id")
        for key in ("name", "instance", "type"):
            text(item[key], "environment " + key)
        need(item["id"] not in ids, "duplicate id: " + item["id"])
        need(item["device"] in devices, "unknown environment device: " + item["device"])
        whole(item["order"], "environment order")
        ids.add(item["id"])
        environments[item["id"]] = dict(item)
        environment_orders.setdefault(item["device"], []).append(item["order"])
    for device_id in devices:
        need(device_id in environment_orders, "every device requires an execution environment in this subset: " + device_id)
        contiguous(environment_orders[device_id], "environment order for " + device_id)
        need(len(environment_orders[device_id]) == 1, "current subset supports one execution environment per device")

    targets = {**devices, **environments}
    artifacts = {}
    artifact_orders = {}
    for item in document["artifacts"]:
        exact(item, ("id", "name", "target", "order"), ("kind",))
        identifier(item["id"], "artifact id")
        text(item["name"], "artifact name")
        need(item["id"] not in ids, "duplicate id: " + item["id"])
        need(item["target"] in targets, "unknown artifact deployment target: " + item["target"])
        whole(item["order"], "artifact order")
        if "kind" in item:
            text(item["kind"], "artifact kind")
        ids.add(item["id"])
        artifacts[item["id"]] = dict(item)
        artifact_orders.setdefault(item["target"], []).append(item["order"])
    for target, orders in artifact_orders.items():
        contiguous(orders, "artifact order for " + target)
        need(len(orders) <= 4, "current subset allows at most four artifacts per target")

    components = {}
    component_slots = set()
    for item in document["components"]:
        exact(item, ("id", "name", "column"))
        identifier(item["id"], "component id")
        text(item["name"], "component name")
        whole(item["column"], "component column")
        need(item["id"] not in ids, "duplicate id: " + item["id"])
        need(item["column"] not in component_slots, "duplicate component column: " + str(item["column"]))
        component_slots.add(item["column"])
        ids.add(item["id"])
        components[item["id"]] = dict(item)
    contiguous(component_slots, "component columns")

    relation_ids = set()
    manifestations = []
    used_artifacts = set()
    used_components = set()
    for item in document["manifestations"]:
        exact(item, ("id", "artifact", "component"))
        identifier(item["id"], "manifestation id")
        need(item["id"] not in relation_ids and item["id"] not in ids, "duplicate id: " + item["id"])
        relation_ids.add(item["id"])
        need(item["artifact"] in artifacts, "unknown manifestation artifact: " + item["artifact"])
        need(item["component"] in components, "unknown manifestation component: " + item["component"])
        need(item["artifact"] not in used_artifacts, "current subset allows one manifestation per artifact")
        need(item["component"] not in used_components, "current subset allows one artifact per component")
        used_artifacts.add(item["artifact"])
        used_components.add(item["component"])
        manifestations.append(dict(item))
    need(used_artifacts == set(artifacts), "every artifact must manifest one logical component in this subset")
    need(used_components == set(components), "every logical component must have one manifesting artifact in this subset")

    paths = []
    device_pairs = set()
    adjacency = {item: set() for item in devices}
    for item in document["communication_paths"]:
        exact(item, ("id", "source", "target", "label"))
        identifier(item["id"], "communication path id")
        text(item["label"], "communication path label")
        need(item["id"] not in relation_ids and item["id"] not in ids, "duplicate id: " + item["id"])
        relation_ids.add(item["id"])
        need(item["source"] in devices and item["target"] in devices, "current communication paths must connect devices")
        need(item["source"] != item["target"], "communication path cannot be self-connected")
        pair = frozenset((item["source"], item["target"]))
        need(pair not in device_pairs, "duplicate communication path between devices")
        device_pairs.add(pair)
        adjacency[item["source"]].add(item["target"])
        adjacency[item["target"]].add(item["source"])
        paths.append(dict(item))
    seen = set()
    pending = [next(iter(devices))]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency[current] - seen)
    need(seen == set(devices), "communication path graph must connect every device")

    return {
        "title": document["title"],
        "scope": document["scope"],
        "devices": list(document["devices"]),
        "environments": list(document["environments"]),
        "artifacts": list(document["artifacts"]),
        "components": list(document["components"]),
        "manifestations": manifestations,
        "communication_paths": paths,
        "counts": {
            "devices": len(devices),
            "execution_environments": len(environments),
            "artifacts": len(artifacts),
            "logical_components": len(components),
            "manifestations": len(manifestations),
            "communication_paths": len(paths),
        },
        "scope_note": "device instances, one execution-environment instance per device, nested artifacts, one-to-one manifestations and a connected device communication topology; not full UML metamodel conformance",
    }
