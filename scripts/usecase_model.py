"""Small UML use-case content model; structural checks, not metamodel conformance."""
import math
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


def multiplicity(value, label):
    if value is None:
        return
    need(isinstance(value, str), label + " must be text")
    need(re.fullmatch(r"(?:\d+|\*)(?:\.\.(?:\d+|\*))?", value) is not None, label + " is invalid")
    if ".." in value:
        lower, upper = value.split("..")
        if upper != "*":
            need(int(lower) <= int(upper), label + " lower bound exceeds upper bound")


def validate(document):
    exact(document, ("title", "scope", "assumptions", "subjects", "actors", "use_cases", "relations"))
    text(document["title"], "title")
    text(document["scope"], "scope")
    need(isinstance(document["assumptions"], list) and document["assumptions"], "assumptions must be a non-empty list")
    for item in document["assumptions"]:
        text(item, "assumption")
    need(isinstance(document["subjects"], list) and document["subjects"], "subjects must be non-empty")
    need(isinstance(document["actors"], list) and document["actors"], "actors must be non-empty")
    need(isinstance(document["use_cases"], list) and document["use_cases"], "use_cases must be non-empty")
    need(isinstance(document["relations"], list), "relations must be a list")

    identifiers = set()
    subjects = {}
    for subject in document["subjects"]:
        exact(subject, ("id", "name"), ("stereotype",))
        identifier(subject["id"], "subject id")
        text(subject["name"], "subject name")
        need(subject["id"] not in identifiers, "duplicate id: " + subject["id"])
        identifiers.add(subject["id"])
        if "stereotype" in subject:
            text(subject["stereotype"], "subject stereotype")
        subjects[subject["id"]] = subject

    actors = {}
    for actor in document["actors"]:
        exact(actor, ("id", "name"), ("side", "kind"))
        identifier(actor["id"], "actor id")
        text(actor["name"], "actor name")
        need(actor["id"] not in identifiers, "duplicate id: " + actor["id"])
        identifiers.add(actor["id"])
        need(actor.get("side", "left") in ("left", "right"), "actor side must be left or right")
        if "kind" in actor:
            text(actor["kind"], "actor kind")
        actors[actor["id"]] = actor

    use_cases = {}
    extension_points = {}
    for use_case in document["use_cases"]:
        exact(use_case, ("id", "name", "subject"), ("extension_points", "stereotype"))
        identifier(use_case["id"], "use case id")
        text(use_case["name"], "use case name")
        need(use_case["id"] not in identifiers, "duplicate id: " + use_case["id"])
        identifiers.add(use_case["id"])
        need(use_case["subject"] in subjects, "unknown use case subject: " + use_case["subject"])
        points = use_case.get("extension_points", [])
        need(isinstance(points, list), "extension_points must be a list")
        for point in points:
            text(point, "extension point")
        need(len(points) == len(set(points)), "duplicate extension point in " + use_case["id"])
        if "stereotype" in use_case:
            text(use_case["stereotype"], "use case stereotype")
        extension_points[use_case["id"]] = set(points)
        use_cases[use_case["id"]] = use_case

    relation_ids = set()
    include_graph = {key: [] for key in use_cases}
    normalized = []
    for relation in document["relations"]:
        exact(
            relation,
            ("id", "kind", "source", "target"),
            ("source_multiplicity", "target_multiplicity", "condition", "extension_points", "label"),
        )
        identifier(relation["id"], "relation id")
        need(relation["id"] not in relation_ids, "duplicate relation id: " + relation["id"])
        relation_ids.add(relation["id"])
        kind = relation["kind"]
        need(kind in ("association", "include", "extend", "generalization"), "unknown relation kind: " + str(kind))
        source, target = relation["source"], relation["target"]
        need(source in identifiers and target in identifiers, "unknown relation endpoint: " + relation["id"])
        need(source != target, "self relation is not allowed: " + relation["id"])
        if kind == "association":
            need((source in actors and target in use_cases) or (target in actors and source in use_cases), "association must connect one actor and one use case")
            multiplicity(relation.get("source_multiplicity"), "source multiplicity")
            multiplicity(relation.get("target_multiplicity"), "target multiplicity")
        elif kind == "include":
            need(source in use_cases and target in use_cases, "include must connect use cases")
            include_graph[source].append(target)
            need("condition" not in relation and "extension_points" not in relation, "include cannot carry extend fields")
        elif kind == "extend":
            need(source in use_cases and target in use_cases, "extend must connect use cases")
            points = relation.get("extension_points")
            need(isinstance(points, list) and points, "extend requires extension_points")
            need(all(point in extension_points[target] for point in points), "extend points must belong to the extended use case")
            if "condition" in relation:
                text(relation["condition"], "extend condition")
        else:
            same_kind = (source in actors and target in actors) or (source in use_cases and target in use_cases)
            need(same_kind, "generalization endpoints must be the same metaclass")
        if "label" in relation:
            text(relation["label"], "relation label")
        normalized.append(dict(relation))

    visiting = set()
    visited = set()

    def walk(node):
        need(node not in visiting, "include cycle detected at " + node)
        if node in visited:
            return
        visiting.add(node)
        for target in include_graph[node]:
            walk(target)
        visiting.remove(node)
        visited.add(node)

    for node in include_graph:
        walk(node)

    return {
        "title": document["title"],
        "scope": document["scope"],
        "subjects": list(document["subjects"]),
        "actors": list(document["actors"]),
        "use_cases": list(document["use_cases"]),
        "relations": normalized,
        "counts": {
            "subjects": len(subjects),
            "actors": len(actors),
            "use_cases": len(use_cases),
            "relations": len(normalized),
        },
        "scope_note": "binary actor associations, include/extend/generalization structure and reference integrity; not full UML metamodel conformance",
    }
