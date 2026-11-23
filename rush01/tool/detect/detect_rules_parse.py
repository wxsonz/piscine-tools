"""Parse rules (PLAN.md §7.3 Parsing): how argv[1] becomes the clues.
One function per catalog id; see detect_rules.py for the hit shape.
"""

import re

from .detect_hits import ev, hit, rules_find, where
from .detect_read import read_walk
from .detect_roles import roles_reach
from .detect_shapes import ID

SIGNAL = {
    "step2": re.compile(r"\+=\s*2\b|=\s*(\w+)\s*\+\s*2$|\[\s*\w+\s*\*\s*2\s*"
                        r"(\+\s*1\s*)?\]|\[\s*2\s*\*\s*\w+\s*(\+\s*1\s*)?\]|"
                        r"%\s*2\s*(==|!=)"),
    "len31": re.compile(r"(==|!=|<|>|<=|>=)\s*31\b|\b31\s*(==|!=|<|>)|"
                        r"\[\s*31\s*\]|8\s*\*\s*\w+\s*-\s*1|\w+\s*\*\s*8\s*-"
                        r"\s*1"),
    "space": re.compile(r"(==|!=)\s*' '|' '\s*(==|!=)|(==|!=)\s*32\b"),
    "range": re.compile(r"(<=|>=|<|>)\s*'[0-9]'|'[0-9]'\s*(<=|>=|<|>)"),
    "minus0": re.compile(r"-\s*'0'|-\s*48\b"),
    "atoi": re.compile(r"\*\s*10\s*\+|\b10\s*\*\s*\w+\s*\+"),
    "count16": re.compile(r"(==|!=|<|>|<=|>=)\s*16\b|\b16\s*(==|!=)|"
                          r"(==|!=)\s*4\s*\*\s*\w+|%\s*4\s*(!=|==)"),
}


def rules_parse_signals(cx):
    fns = cx["roles"]["parse"]
    return {k: rules_find(fns, rx) for k, rx in SIGNAL.items()}


def rules_rejects(cx):
    """Ways the parser says no: an `if` that returns a constant / NULL or
    reaches the error text, or `return (count == 16)`."""
    roles = cx["roles"]
    team = cx["team"]
    error_gids = {f["gid"] for f in roles["error"]}
    parse_gids = {f["gid"] for f in roles["parse"]}
    out = []
    for fn in roles["parse"]:
        for node in fn["nodes"]:
            if node["k"] == "return" and re.search(r"(==|!=|<=|>=|<|>)",
                                                   node["text"]):
                out.append((fn, node))
            if node["k"] != "if":
                continue
            if fn is roles["main"] and not rules_main_cond_on_input(
                    cx, fn, node):
                continue
            if rules_branch_says_no(team, fn, node, error_gids):
                out.append((fn, node))
    main = roles["main"]
    if main and main["gid"] not in parse_gids:
        for node in main["nodes"]:
            if node["k"] == "if" and rules_main_cond_on_input(cx, main, node) \
                    and rules_branch_says_no(team, main, node, error_gids):
                out.append((main, node))
    return out


def rules_main_cond_on_input(cx, main, node):
    """A condition in main about argv's text or a parser's result (an argc
    check alone is not validation)."""
    roles = cx["roles"]
    cond = node["text"]
    if roles["argv"] and re.search(r"\b%s\s*\[" % re.escape(roles["argv"]),
                                   cond):
        return True
    names = {f["name"] for f in roles["parse"] if f is not main}
    return any(re.search(r"\b%s\s*\(" % re.escape(n), cond) for n in names)


def rules_branch_says_no(team, fn, node, error_gids):
    for br in node["branches"]:
        for kid in read_walk(br["kids"]):
            if kid["k"] == "return" and re.fullmatch(
                    r"return\s*\(?\s*(-?\d+|NULL|0|\w+\s*\(.*\))\s*\)?",
                    kid["text"]):
                return True
            for call in fn["calls"]:
                if call["node"] is kid and any(
                        roles_reach(team, t, 2) & error_gids
                        for t in team["by_name"].get(call["name"], [])):
                    return True
                if call["node"] is kid and call["name"] == "exit":
                    return True
    return False


def rules_parse_where(cx, keys):
    """The parser function holding the most of these signals."""
    count = {}
    for k in keys:
        for fn, _ in cx["parse_sig"].get(k, []):
            count[fn["gid"]] = count.get(fn["gid"], 0) + 1
    if count:
        gid = max(count, key=lambda g: count[g])
        return where(cx["team"]["by_gid"][gid])
    parse = cx["roles"]["parse"]
    return where(parse[0]) if parse else None


def rules_first(cx, key, why):
    got = cx["parse_sig"].get(key) or []
    if not got:
        return None
    fn, node = got[0]
    return ev(fn, node["line"], why)


def rules_reject_ev(cx):
    if not cx["rejects"]:
        return None
    fn, node = cx["rejects"][0]
    return ev(fn, node["line"], "rejects bad input here")


def rules_split_fn(cx):
    team = cx["team"]
    for fn in cx["roles"]["parse"]:
        if "**" in fn["ret"].replace(" ", "") and any(
                "malloc" in team["ext"].get(g, set())
                for g in roles_reach(team, fn, 1)):
            return fn
    return None


def rules_state_var(cx):
    """An explicit state: one variable set to 2+ constants inside a loop
    and tested in that loop, never counted up."""
    for fn in cx["roles"]["parse"]:
        counted = {a["lhs"] for a in fn["assigns"]
                   if a["op"] in ("++", "--", "+=", "-=")}
        for loop in [n for n in fn["nodes"] if n["k"] == "loop"]:
            kids = list(read_walk(loop["kids"]))
            values = {}
            for a in fn["assigns"]:
                if a["op"] == "=" and any(a["node"] is k for k in kids) \
                        and re.fullmatch(ID, a["lhs"]) \
                        and re.fullmatch(r"\d+", a["rhs"]):
                    values.setdefault(a["lhs"], set()).add(a["rhs"])
            for var, vals in values.items():
                if len(vals) < 2 or var in counted \
                        or re.search(r"\b%s\b" % var, loop["text"]):
                    continue
                tested = [k for k in kids if k["k"] == "if" and re.search(
                    r"\b%s\s*(==|!=)\s*\d|!\s*%s\b|^%s$" % (var, var, var),
                    k["text"])]
                if tested:
                    return fn, tested[0], var
    return None


def rule_parse_split(cx):
    fn = rules_split_fn(cx)
    if not fn:
        return None
    req = [ev(fn, fn["line"], "returns an array of words built with malloc "
              "(a split)")]
    sup = [e for e in (rules_first(cx, "range", "checks each word is a digit "
                                   "in range"),
                       rules_first(cx, "count16", "checks the number of "
                                   "words"),
                       rules_reject_ev(cx)) if e]
    if not cx["rejects"]:
        return None
    return hit("parse.split", req, sup, [where(fn)])


def rule_parse_atoi(cx):
    first = rules_first(cx, "atoi", "builds a number digit by digit "
                        "(res * 10 + c - '0')")
    if not first or rules_split_fn(cx) or not cx["rejects"]:
        return None
    sup = [e for e in (rules_first(cx, "range", "compares with digit chars"),
                       rules_first(cx, "count16", "checks how many numbers"),
                       rules_reject_ev(cx)) if e]
    return hit("parse.atoi", [first], sup, [rules_parse_where(cx, ["atoi"])],
               [{"key": "leading_zero",
                 "text": "an atoi loop usually accepts \"04\" as 4"}])


def rule_parse_fsm(cx):
    got = rules_state_var(cx)
    if not got or rules_split_fn(cx) or not cx["rejects"]:
        return None
    fn, node, var = got
    req = [ev(fn, node["line"], f"`{var}` holds the state (what is expected "
              "next) and is tested in the loop")]
    sup = [e for e in (rules_first(cx, "space", "a space moves the state"),
                       rules_first(cx, "range", "a digit moves the state"))
           if e]
    return hit("parse.fsm", req, sup, [where(fn)])


def rule_parse_fixed(cx):
    first = rules_first(cx, "step2", "reads at fixed positions (every 2nd "
                        "char)")
    if not first or rules_split_fn(cx) or not cx["rejects"] \
            or cx["parse_sig"]["atoi"] or rules_state_var(cx):
        return None
    sup = [e for e in (rules_first(cx, "len31", "the input length must be "
                                   "31 (16 digits + 15 spaces)"),
                       rules_first(cx, "space", "odd positions must be "
                                   "spaces"),
                       rules_first(cx, "range", "even positions must be "
                                   "digits in range")) if e]
    return hit("parse.fixed", [first], sup,
               [rules_parse_where(cx, ["step2", "len31"])])


def rule_parse_scan(cx):
    sig = cx["parse_sig"]
    store = rules_first(cx, "minus0", "stores each digit as a number "
                        "(c - '0')") or rules_first(
        cx, "range", "keeps the chars that are digits")
    count = rules_first(cx, "count16", "counts the numbers (must be 16)") \
        or rules_first(cx, "space", "compares with ' ' (the separator)")
    if not store or not count or not cx["rejects"] or sig["step2"] \
            or sig["atoi"] or rules_split_fn(cx) or rules_state_var(cx):
        return None
    sup = [e for e in (rules_first(cx, "space", "compares with ' ' (the "
                                   "separator)"),
                       rules_first(cx, "range", "checks the digit range"),
                       rules_reject_ev(cx)) if e and e != count and e != store]
    return hit("parse.scan", [store, count], sup,
               [rules_parse_where(cx, ["minus0", "range", "count16"])])


def rule_parse_none(cx):
    """Stores from argv but never says no."""
    roles = cx["roles"]
    if cx["rejects"] or not roles["parse"]:
        return None
    stores = []
    for fn in roles["parse"]:
        names = cx["roles"]["taint"].get(fn["gid"], set())
        for a in fn["assigns"]:
            if "[" in a["lhs"] and (SIGNAL["minus0"].search(a["rhs"]) or any(
                    re.search(r"\b%s\b" % re.escape(n), a["rhs"])
                    for n in names)):
                stores.append((fn, a))
    if not stores:
        return None
    fn, a = stores[0]
    req = [ev(fn, a["line"], "copies the input into the clues"),
           ev(fn, fn["line"], "no branch here or in its callers rejects bad "
              "input (no Error, no early return)")]
    sup = [e for e in (rules_first(cx, "step2", "reads at fixed positions, "
                                   "without checking them"),
                       rules_first(cx, "range", "skips non-digits instead of "
                                   "rejecting them")) if e]
    return hit("parse.none", req, sup, [where(fn)])
