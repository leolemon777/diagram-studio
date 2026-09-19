"""Validated UML component-diagram subset; not full UML metamodel conformance."""
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


def validate(document):
    exact(document, ("title", "scope", "assumptions", "components", "interfaces", "ports", "relations"))
    text(document["title"], "title")
    text(document["scope"], "scope")
    need(isinstance(document["assumptions"], list) and document["assumptions"], "assumptions must be a non-empty list")
    for item in document["assumptions"]:
        text(item, "assumption")
    need(isinstance(document["components"], list) and document["components"], "components must be non-empty")
    need(isinstance(document["interfaces"], list) and document["interfaces"], "interfaces must be non-empty")
    need(isinstance(document["ports"], list) and document["ports"], "ports must be non-empty")
    need(isinstance(document["relations"], list), "relations must be a list")

    ids = set()
    components = {}
    positions = set()
    for component in document["components"]:
        exact(component, ("id", "name", "column", "row"), ("stereotype", "kind"))
        identifier(component["id"], "component id")
        text(component["name"], "component name")
        whole(component["column"], "component column")
        whole(component["row"], "component row")
        need(component["id"] not in ids, "duplicate id: " + component["id"])
        slot = (component["column"], component["row"])
        need(slot not in positions, "duplicate component grid position: " + str(slot))
        positions.add(slot)
        ids.add(component["id"])
        for key in ("stereotype", "kind"):
            if key in component:
                text(component[key], "component " + key)
        components[component["id"]] = component

    interfaces = {}
    for interface in document["interfaces"]:
        exact(interface, ("id", "name"), ("description",))
        identifier(interface["id"], "interface id")
        text(interface["name"], "interface name")
        need(interface["id"] not in ids, "duplicate id: " + interface["id"])
        ids.add(interface["id"])
        if "description" in interface:
            text(interface["description"], "interface description")
        interfaces[interface["id"]] = interface

    ports = {}
    port_slots = set()
    for port in document["ports"]:
        exact(port, ("id", "name", "component", "interface", "direction", "side", "order"))
        identifier(port["id"], "port id")
        text(port["name"], "port name")
        need(port["id"] not in ids, "duplicate id: " + port["id"])
        ids.add(port["id"])
        need(port["component"] in components, "unknown port component: " + port["component"])
        need(port["interface"] in interfaces, "unknown port interface: " + port["interface"])
        need(port["direction"] in ("provided", "required"), "port direction must be provided or required")
        need(port["side"] in ("left", "right", "top", "bottom"), "port side is invalid")
        whole(port["order"], "port order")
        slot = (port["component"], port["side"], port["order"])
        need(slot not in port_slots, "duplicate port slot: " + str(slot))
        port_slots.add(slot)
        ports[port["id"]] = port

    relation_ids = set()
    assemblies = []
    dependencies = []
    used_assembly_ports = set()
    for relation in document["relations"]:
        exact(relation, ("id", "kind", "source", "target"), ("label",))
        identifier(relation["id"], "relation id")
        need(relation["id"] not in relation_ids, "duplicate relation id: " + relation["id"])
        relation_ids.add(relation["id"])
        if "label" in relation:
            text(relation["label"], "relation label")
        source, target = relation["source"], relation["target"]
        need(source != target, "self relation is not allowed: " + relation["id"])
        if relation["kind"] == "assembly":
            need(source in ports and target in ports, "assembly must connect ports")
            need(ports[source]["direction"] == "required", "assembly source must be a required port")
            need(ports[target]["direction"] == "provided", "assembly target must be a provided port")
            need(ports[source]["interface"] == ports[target]["interface"], "assembly ports must share one interface")
            need(source not in used_assembly_ports and target not in used_assembly_ports, "current subset allows one assembly per port")
            used_assembly_ports.update((source, target))
            assemblies.append(dict(relation))
        elif relation["kind"] == "dependency":
            need(source in components and target in components, "dependency must connect components")
            dependencies.append(dict(relation))
        else:
            raise ValueError("unknown relation kind: " + str(relation["kind"]))

    need(assemblies, "at least one assembly is required")
    return {
        "title": document["title"],
        "scope": document["scope"],
        "components": list(document["components"]),
        "interfaces": list(document["interfaces"]),
        "ports": list(document["ports"]),
        "relations": [*assemblies, *dependencies],
        "counts": {
            "components": len(components),
            "interfaces": len(interfaces),
            "ports": len(ports),
            "assemblies": len(assemblies),
            "dependencies": len(dependencies),
        },
        "scope_note": "component rectangles, simple ports, provided/required interface symbols, binary assembly connectors and component dependencies; not full UML metamodel conformance",
    }
