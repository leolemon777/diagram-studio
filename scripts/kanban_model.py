"""Strict model for a practical swimlane Kanban subset."""
from collections import Counter, defaultdict
import re


STAGES = {"queue", "wip", "done"}
SERVICE_CLASSES = {"standard", "fixed_date", "expedite", "intangible"}


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


def whole(value, label, minimum=0):
    need(isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
         f"{label} must be an integer >= {minimum}")


def validate(document):
    exact(document, (
        "title", "service", "snapshot", "assumptions", "columns", "lanes",
        "cards", "policies", "flow_metrics",
    ), ("language",))
    language = document.get("language", "zh")
    need(language in {"zh", "en"}, "language must be zh or en")
    for key in ("title", "service", "snapshot"):
        text(document[key], key)
    need(isinstance(document["assumptions"], list) and document["assumptions"],
         "assumptions must be a non-empty list")
    for item in document["assumptions"]:
        text(item, "assumption")

    need(isinstance(document["columns"], list) and 3 <= len(document["columns"]) <= 7,
         "columns must contain three to seven states")
    columns = {}
    column_orders = set()
    for column in document["columns"]:
        exact(column, ("id", "name", "order", "stage"), ("wip_limit", "pull_criteria"))
        identifier(column["id"], "column id")
        text(column["name"], "column name")
        whole(column["order"], "column order")
        need(column["stage"] in STAGES, "unknown column stage: " + str(column["stage"]))
        need(column["id"] not in columns, "duplicate column id: " + column["id"])
        need(column["order"] not in column_orders, "duplicate column order")
        if column["stage"] == "wip":
            need("wip_limit" in column and "pull_criteria" in column,
                 "WIP columns require wip_limit and pull_criteria")
            whole(column["wip_limit"], "column WIP limit", 1)
            text(column["pull_criteria"], "pull criteria")
        else:
            need("wip_limit" not in column, "queue/done columns cannot declare a WIP limit in this subset")
            need("pull_criteria" not in column, "queue/done columns cannot declare pull criteria in this subset")
        columns[column["id"]] = dict(column)
        column_orders.add(column["order"])
    need(column_orders == set(range(len(columns))), "column order must be contiguous from zero")
    ordered_columns = sorted(columns.values(), key=lambda item: item["order"])
    stages = [column["stage"] for column in ordered_columns]
    need("queue" in stages and "wip" in stages and "done" in stages,
         "workflow requires queue, WIP and done states")
    first_wip = stages.index("wip")
    first_done = stages.index("done")
    need(all(stage == "queue" for stage in stages[:first_wip]), "queue states must precede WIP")
    need(all(stage == "wip" for stage in stages[first_wip:first_done]), "WIP states must be contiguous")
    need(all(stage == "done" for stage in stages[first_done:]), "done states must follow WIP")

    need(isinstance(document["lanes"], list) and 2 <= len(document["lanes"]) <= 5,
         "lanes must contain two to five work classes")
    lanes = {}
    lane_orders = set()
    for lane in document["lanes"]:
        exact(lane, ("id", "name", "order", "wip_limit"))
        identifier(lane["id"], "lane id")
        text(lane["name"], "lane name")
        whole(lane["order"], "lane order")
        whole(lane["wip_limit"], "lane WIP limit", 1)
        need(lane["id"] not in lanes, "duplicate lane id: " + lane["id"])
        need(lane["order"] not in lane_orders, "duplicate lane order")
        lanes[lane["id"]] = dict(lane)
        lane_orders.add(lane["order"])
    need(lane_orders == set(range(len(lanes))), "lane order must be contiguous from zero")

    need(isinstance(document["cards"], list) and document["cards"], "cards must be a non-empty list")
    cards = []
    card_ids = set()
    cell_counts = Counter()
    column_counts = Counter()
    lane_wip = Counter()
    service_counts = Counter()
    blocked = []
    expedite = []
    wip_column_ids = {column["id"] for column in ordered_columns if column["stage"] == "wip"}
    for card in document["cards"]:
        exact(card, ("id", "title", "lane", "column", "owner", "service_class", "blocked"),
              ("age_days", "blocked_reason", "due"))
        identifier(card["id"], "card id")
        text(card["title"], "card title")
        text(card["owner"], "card owner")
        need(card["id"] not in card_ids, "duplicate card id: " + card["id"])
        need(card["lane"] in lanes, "unknown card lane: " + str(card["lane"]))
        need(card["column"] in columns, "unknown card column: " + str(card["column"]))
        need(card["service_class"] in SERVICE_CLASSES,
             "unknown service class: " + str(card["service_class"]))
        need(isinstance(card["blocked"], bool), "blocked must be boolean")
        is_wip = card["column"] in wip_column_ids
        if is_wip:
            need("age_days" in card, "WIP cards require age_days")
            whole(card["age_days"], "card age_days")
            lane_wip[card["lane"]] += 1
        else:
            need("age_days" not in card, "queue/done cards cannot use age_days in this subset")
        if card["blocked"]:
            need(is_wip, "blocked cards must remain inside WIP")
            need("blocked_reason" in card, "blocked cards require blocked_reason")
            text(card["blocked_reason"], "blocked reason")
            blocked.append(card["id"])
        else:
            need("blocked_reason" not in card, "unblocked cards cannot declare blocked_reason")
        if card["service_class"] == "fixed_date":
            need("due" in card, "fixed-date cards require due")
            text(card["due"], "fixed-date due")
        elif "due" in card:
            text(card["due"], "card due")
        if card["service_class"] == "expedite":
            expedite.append(card["id"])
        card_ids.add(card["id"])
        cards.append(dict(card))
        cell_counts[(card["lane"], card["column"])] += 1
        column_counts[card["column"]] += 1
        service_counts[card["service_class"]] += 1
    need(len(expedite) <= 1, "current subset permits at most one expedite card")
    need(max(cell_counts.values()) <= 4, "current layout supports at most four cards per lane/column cell")
    for column in ordered_columns:
        if column["stage"] == "wip":
            need(column_counts[column["id"]] <= column["wip_limit"],
                 f"column {column['id']} exceeds WIP limit")
    for lane in lanes.values():
        need(lane_wip[lane["id"]] <= lane["wip_limit"], f"lane {lane['id']} exceeds WIP limit")

    need(isinstance(document["policies"], list) and len(document["policies"]) >= 3,
         "at least three explicit policies are required")
    policies = []
    policy_ids = set()
    for policy in document["policies"]:
        exact(policy, ("id", "title", "rule"))
        identifier(policy["id"], "policy id")
        text(policy["title"], "policy title")
        text(policy["rule"], "policy rule")
        need(policy["id"] not in policy_ids, "duplicate policy id: " + policy["id"])
        policy_ids.add(policy["id"])
        policies.append(dict(policy))

    metrics = document["flow_metrics"]
    exact(metrics, ("throughput_period", "throughput", "throughput_unit", "sle_days", "sle_probability"))
    text(metrics["throughput_period"], "throughput period")
    whole(metrics["throughput"], "throughput")
    text(metrics["throughput_unit"], "throughput unit")
    whole(metrics["sle_days"], "SLE days", 1)
    need(isinstance(metrics["sle_probability"], (int, float)) and not isinstance(metrics["sle_probability"], bool)
         and 0 < metrics["sle_probability"] <= 1, "SLE probability must be within (0, 1]")

    wip_counts = {column["id"]: column_counts[column["id"]]
                  for column in ordered_columns if column["stage"] == "wip"}
    pull_capacity = {column["id"]: column["wip_limit"] - wip_counts[column["id"]]
                     for column in ordered_columns if column["stage"] == "wip"}
    return {
        "language": language,
        "title": document["title"],
        "service": document["service"],
        "snapshot": document["snapshot"],
        "assumptions": list(document["assumptions"]),
        "columns": ordered_columns,
        "lanes": sorted(lanes.values(), key=lambda item: item["order"]),
        "cards": cards,
        "policies": policies,
        "flow_metrics": dict(metrics),
        "counts": {
            "columns": len(columns), "lanes": len(lanes), "cards": len(cards),
            "wip": sum(wip_counts.values()), "blocked": len(blocked),
        },
        "column_counts": dict(column_counts),
        "column_wip": wip_counts,
        "lane_wip": {lane["id"]: lane_wip[lane["id"]] for lane in lanes.values()},
        "pull_capacity": pull_capacity,
        "service_class_counts": dict(service_counts),
        "blocked_cards": blocked,
        "expedite_cards": expedite,
        "commitment_column": ordered_columns[first_wip]["id"],
        "delivery_column": ordered_columns[first_done]["id"],
    }
