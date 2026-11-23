"""Evidence lines and rule hits: the plain dicts every rule returns
(PLAN.md §7.2 steps 4-5).
"""

from .detect_read import read_line


def ev(fn_or_ctx, line, why):
    ctx = fn_or_ctx["ctx"] if "ctx" in fn_or_ctx else fn_or_ctx
    return {"file": ctx["rel"], "line": line, "text": read_line(ctx, line),
            "why": why}


def ev_file(team, rel, line, why):
    for f in team["files"]:
        if f["rel"] == rel:
            return ev(f["ctx"], line, why)
    return {"file": rel, "line": line, "text": "", "why": why}


def where(fn):
    return {"file": fn["file"], "func": fn["name"], "line": fn["line"]}


def hit(rule_id, req, sup, wheres, facts=()):
    return {"id": rule_id, "score": 2 * len(req) + len(sup),
            "support": len(sup), "evidence": req + sup,
            "where": [w for w in wheres if w], "facts": list(facts)}


def rules_find(fns, regex):
    """(fn, node) pairs whose text (or an else-if condition) matches; the
    node's line is the matching line."""
    out = []
    for fn in fns:
        for node in fn["nodes"]:
            if regex.search(node["text"]):
                out.append((fn, node))
            elif node["k"] == "if":
                for br in node["branches"][1:]:
                    if br["cond"] and regex.search(br["cond"]):
                        out.append((fn, {"k": "if", "text": br["cond"],
                                         "line": br["line"]}))
                        break
    return out
