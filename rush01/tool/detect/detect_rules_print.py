"""Print rules (PLAN.md §7.3 Printing): how the digits reach write().
"""

import re

from .detect_hits import ev, ev_file, hit, where
from .detect_read import read_int
from .detect_roles import DIGIT_OUT, roles_reach
from .detect_shapes import ID


def rules_print_walk(cx):
    """The printer that walks the grid (has a loop), else any printer."""
    prints = cx["roles"]["print"]
    looped = [f for f in prints if any(n["k"] == "loop" for n in f["nodes"])]
    return (looped or prints or [None])[0]


def rules_print_buffer(cx):
    """A char buffer filled with digits, and what happens to it:
    (fn, assign, call, kind) with kind 'line' | 'board' | 'putstr'."""
    team = cx["team"]
    for fn in cx["roles"]["print"]:
        for a in fn["assigns"]:
            if "[" not in a["lhs"] or not DIGIT_OUT.search(a["rhs"]):
                continue
            buf = a["lhs"].split("[")[0].strip()
            used = rules_buffer_use(team, fn, buf)
            if used:
                return (fn, a) + used
            # built here, printed by a caller: `s = build(g); ft_putstr(s);`
            for caller in team["funcs"]:
                for b in caller["assigns"]:
                    if re.search(r"\b%s\s*\(" % re.escape(fn["name"]),
                                 b["rhs"]) and re.fullmatch(ID, b["lhs"]):
                        used = rules_buffer_use(team, caller, b["lhs"])
                        if used:
                            return (fn, a) + used
            return (fn, a, None, None)
    return None


def rules_buffer_use(team, fn, buf):
    pat = re.compile(r"&?\s*\(?\s*%s\s*(\+\s*\w+)?\s*\)?" % re.escape(buf))
    for call in fn["calls"]:
        if not any(pat.fullmatch(arg) for arg in call["args"]):
            continue
        if call["name"] == "write":
            in_loop = any(s["k"] == "loop" for s in call["stack"])
            return call, "line" if in_loop else "board"
        if any("write" in team["ext"].get(g, set())
               for t in team["by_name"].get(call["name"], [])
               for g in roles_reach(team, t, 2)):
            return call, "putstr"
    return None


def rules_write1(cx):
    """write(fd, &c, 1) reachable from the printer (through wrappers)."""
    team = cx["team"]
    gids = set()
    for fn in cx["roles"]["print"]:
        gids |= roles_reach(team, fn, 2)
    for gid in sorted(gids):
        fn = team["by_gid"][gid]
        for call in fn["calls"]:
            if call["name"] == "write" and len(call["args"]) == 3 \
                    and read_int(call["args"][2], cx["defines"]) == 1:
                return fn, call
    return None


def rules_convert_ev(cx):
    for fn in cx["roles"]["print"]:
        for call in fn["calls"]:
            if any(DIGIT_OUT.search(a) for a in call["args"]):
                return ev(fn, call["line"], "turns the cell value into its "
                          "digit char (v + '0')")
        for a in fn["assigns"]:
            if DIGIT_OUT.search(a["rhs"]):
                return ev(fn, a["line"], "turns the cell value into its "
                          "digit char (v + '0')")
    return None


def rule_print_char(cx):
    w1 = rules_write1(cx)
    if not w1 or not cx["roles"]["print"]:
        return None
    buf = rules_print_buffer(cx)
    if buf and buf[3]:
        return None
    fn, call = w1
    walk = rules_print_walk(cx)
    req = [ev(fn, call["line"], "writes one char at a time")]
    conv = rules_convert_ev(cx)
    if conv:
        req.append(conv)
    sup = []
    if walk and fn is not walk:
        sup.append(ev(walk, walk["line"], f"the grid walk calls a wrapper "
                      f"that ends in {fn['name']}()"))
    # one output call per cell, inside the row and column loops
    team = cx["team"]
    writers = {f["gid"] for f in cx["roles"]["writers"]}
    for c in (walk or fn)["calls"]:
        nested = sum(1 for s in c["stack"] if s["k"] == "loop") >= 2
        out = c["name"] == "write" or any(
            t["gid"] in writers for t in team["by_name"].get(c["name"], []))
        if nested and out and c["line"] != call["line"]:
            if re.search(r"\" \"|' '", c["text"]):
                sup.append(ev(walk or fn, c["line"], "writes the space "
                              "between two digits"))
                break
    return hit("print.char", req, sup, [where(walk or fn)])


def rules_buffer_hit(cx, kind, rule_id, why):
    buf = rules_print_buffer(cx)
    if not buf or buf[3] != kind:
        return None
    fn, a, call, _ = buf
    req = [ev(fn, a["line"], "fills a char buffer with the digits"),
           ev_file(cx["team"], call_file(cx, call), call["line"], why)]
    return hit(rule_id, req, [], [where(fn)])


def call_file(cx, call):
    for fn in cx["team"]["funcs"]:
        if call in fn["calls"]:
            return fn["file"]
    return ""


def rule_print_line(cx):
    return rules_buffer_hit(cx, "line", "print.line",
                            "one write per row, of the whole line buffer")


def rule_print_board(cx):
    return rules_buffer_hit(cx, "board", "print.board",
                            "one write for the whole board")


def rule_print_putstr(cx):
    return rules_buffer_hit(cx, "putstr", "print.putstr",
                            "hands the built string to a putstr function")
