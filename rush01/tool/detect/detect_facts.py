"""Facts per part (PLAN.md §7.3): argc check, N, the '\\0' check, the clue
layout with the team's index mapping, where the grid lives, malloc / free,
the visibility counter, the recursion idiom, what happens with no solution,
and where Error is written. Each fact is {"key", "text"}; a fact the code
does not show is left out, never guessed.
"""

import re

from .detect_read import read_int, read_walk
from .detect_roles import roles_reach
from .detect_rules_data import rules_is_padded
from .detect_shapes import shapes_index_roles

SIDES = ["top", "bottom", "left", "right"]


def facts_parse(cx):
    roles = cx["roles"]
    main = roles["main"]
    out = []
    # 1. argc
    if main and roles["argc"]:
        argc = re.escape(roles["argc"])
        checks = [n for n in main["nodes"] if n["k"] == "if"
                  and re.search(r"\b%s\s*(!=|==|<|>|<=|>=)\s*\d" % argc,
                                n["text"])]
        if checks:
            out.append({"key": "argc", "text": "checks the argument count: "
                        f"`{checks[0]['text']}` ({main['file']}:"
                        f"{checks[0]['line']})"})
        else:
            out.append({"key": "argc", "text": "no argc check: argv[1] is "
                        "read even when it is missing"})
    # 2. N fixed or computed
    computed = cx["n_computed"]
    if computed:
        fn, line, text = computed
        out.append({"key": "n", "text": "N computed from the input: "
                    f"`{text}` ({fn['file']}:{line})"})
    elif roles["parse"]:
        out.append({"key": "n", "text": f"N fixed at {cx['n']}"})
    # 3. the end of the string
    ends = []
    for fn in roles["parse"]:
        names = roles["taint"].get(fn["gid"], set())
        for node in fn["nodes"]:
            if node["k"] not in ("if", "loop", "return") or not any(
                    re.search(r"\b%s\s*\[" % re.escape(n), node["text"])
                    for n in names):
                continue
            if re.search(r"'\\0'", node["text"]) or (
                    node["k"] == "loop" and re.fullmatch(
                        r"\w+\s*\[[^\]]+\](\s*&&.*)?", node["text"])):
                ends.append((fn, node))
    if ends:
        fn, node = ends[0]
        out.append({"key": "null_check", "text": "stops at the end of the "
                    f"string ('\\0'): `{node['text']}` ({fn['file']}:"
                    f"{node['line']})"})
    elif roles["parse"]:
        out.append({"key": "null_check", "text": "no explicit '\\0' test in "
                    "the parser (the sanitizer runs tell if it reads past "
                    "the end)"})
    return out


def facts_data(cx):
    out = []
    g = cx["grid"]
    team = cx["team"]
    # 1. the clue layout and the team's index mapping
    layout = facts_clue_layout(cx)
    if layout:
        out.append({"key": "clue_layout", "text": layout})
    # 2. where the grid lives
    if g:
        found = g["origin"] or g["decl"]
        if found and found["kind"] == "global":
            out.append({"key": "grid_where", "text": "the grid is a global: "
                        f"`{found['decl']['text']}` ({found['file']}:"
                        f"{found['line']})"})
        elif found and found["kind"] == "field":
            out.append({"key": "grid_where", "text": "the grid is a field of "
                        f"struct {found['struct']['name']}"})
        elif found:
            out.append({"key": "grid_where", "text": "the grid is passed as "
                        f"a parameter (declared `{found['decl']['text']}` in "
                        f"{found['file']}:{found['line']})"})
    # 3. malloc and free
    mallocs = [(fn, c) for fn in team["funcs"] for c in fn["calls"]
               if c["name"] == "malloc"]
    frees = [(fn, c) for fn in team["funcs"] for c in fn["calls"]
             if c["name"] == "free"]
    if mallocs and not frees:
        fn, c = mallocs[0]
        out.append({"key": "malloc", "text": f"{len(mallocs)} malloc, never "
                    f"freed (first: {fn['file']}:{c['line']})"})
    elif mallocs:
        out.append({"key": "malloc", "text": f"{len(mallocs)} malloc, "
                    f"{len(frees)} free"})
    return out


def facts_clue_layout(cx):
    """How the clues are stored, with the offsets the team reads them at."""
    g = cx["grid"]
    gname = g["name"] if g else None
    found = (g["origin"] or g["decl"]) if g else None
    if g and rules_is_padded(cx, found):
        return "in the border of the padded board (row 0, row n+1, col 0, "\
               "col n+1)"
    # 1. padded: the clues are in the board itself
    n = cx["n"]
    maps = {}
    kind = None
    fns = cx["solve_fns"] + [c["fn"] for c in cx["counters"]]
    # 2. reads at a side's offset: clue[8 + r], views[2][r]
    for fn in fns:
        for x in fn["accesses"]:
            if x["name"] == gname or x["decl"] or x["write"]:
                continue
            if len(x["idx"]) == 1:
                side = facts_side_of_offset(x["idx"][0], n, cx["defines"])
                if side is not None:
                    kind = kind or "flat"
                    maps.setdefault(SIDES[side],
                                    f"{x['base']}[{x['idx'][0]}]")
            elif len(x["idx"]) == 2:
                k = read_int(x["idx"][0], cx["defines"])
                if k is not None and 0 <= k <= 3 \
                        and read_int(x["idx"][1], cx["defines"]) is None:
                    kind = kind or "views"
                    maps.setdefault(SIDES[k], f"{x['base']}[{k}][..]")
    # 3. the text: shape, then each side's read
    if maps and kind == "flat" and "top" not in maps:
        # the top clues sit at offset 0: `clues[i]` on the same array
        bases = {v.split("[")[0] for v in maps.values()}
        for fn in fns:
            for x in fn["accesses"]:
                if x["base"] in bases and len(x["idx"]) == 1 \
                        and re.fullmatch(r"[A-Za-z_]\w*", x["idx"][0]) \
                        and not x["write"] and not x["decl"]:
                    maps["top"] = f"{x['base']}[{x['idx'][0]}]"
                    break
            if "top" in maps:
                break
    if maps:
        where = "in the struct, " if any("->" in v or "." in v
                                         for v in maps.values()) else ""
        count = "4N" if cx["n_computed"] else str(4 * n)
        shape = f"one flat array of {count}" if kind == "flat" \
            else "a [4][n] array (side, index)"
        pairs = "; ".join(f"{v} = {s}" for s, v in
                          sorted(maps.items(), key=lambda kv:
                                 SIDES.index(kv[0])))
        return f"{where}{shape}, read as {pairs} (subject order)"
    # 4. else: four separate arrays filled by the parser
    bases = []
    for fn in cx["roles"]["parse"]:
        for x in fn["accesses"]:
            if x["write"] and x["base"] not in bases \
                    and re.search(r"-\s*'0'|-\s*48\b", x["assign"]["rhs"]):
                bases.append(x["base"])
    if len(bases) == 4:
        return "four arrays, filled in this order: " + ", ".join(bases)
    return None


def facts_side_of_offset(idx, n, defines):
    """`8 + r` -> 2 (left): a constant offset of n, 2n or 3n (also written
    `2 * size + r`). `n + r` alone is left out: either name could be n."""
    t = " ".join(idx.split())
    m = re.fullmatch(r"(.+?)\s*\+\s*(.+)", t)
    if not m:
        return None
    for part in (m.group(1), m.group(2)):
        v = read_int(part, defines)
        if v in (n, 2 * n, 3 * n):
            return v // n
        k = re.fullmatch(r"([23])\s*\*\s*[A-Za-z_]\w*|[A-Za-z_]\w*\s*\*\s*"
                         r"([23])", part)
        if k:
            return int(k.group(1) or k.group(2))
    return None


def facts_solve(cx):
    out = []
    team = cx["team"]
    roles = cx["roles"]
    # 1. the visibility counter
    if cx["counters"]:
        c = cx["counters"][0]
        text = (f"visibility counter in {c['fn']['name']}(): "
                f"`{c['count']}` starts at {c['init_count'] or '(set by the caller)'}"
                f", `{c['max']}` at {c['init_max'] or '(set by the caller)'}; "
                f"counts when a cell is taller (`{c['big']} {c['op']} "
                f"{c['max']}`)")
        if c["op"] in (">=", "<="):
            text += "; equal heights count too (>=)"
        out.append({"key": "counter", "text": text})
    # 2. the recursion idiom, read on the search that fills the grid first
    rec = {f["gid"] for f in roles["rec"]}
    writers = {w[0]["gid"] for w in cx["grid"]["writes"]} if cx["grid"] \
        else set()
    fills = [f for f in roles["rec"] if f["gid"] in writers or any(
        t["gid"] in writers for c in f["calls"]
        for t in team["by_name"].get(c["name"], []))]
    for fn in fills + [f for f in roles["rec"] if f not in fills]:
        for call in fn["calls"]:
            if not any(t["gid"] in rec
                       for t in team["by_name"].get(call["name"], [])):
                continue
            args = " ".join(call["args"])
            plus = re.findall(r"\b(\w+)\s*\+\s*1\b", args)
            iroles = shapes_index_roles(fn)
            if len(plus) == 1 and re.search(r"\b0\b", args) is None:
                if plus[0] in iroles["pos"] or re.search(
                        r"\b%s\s*[/%%]\s*\w+" % re.escape(plus[0]),
                        fn["code"]):
                    last = "N * N - 1" if cx["n_computed"] \
                        else str(cx["n"] ** 2 - 1)
                    text = (f"cell number idiom: `{plus[0]}` 0..{last} "
                            "(/ n and % n give row and column), recursion "
                            f"on `{plus[0]} + 1`")
                else:
                    text = f"one step per call: recursion on `{plus[0]} + 1`"
                out.append({"key": "idiom", "text": text +
                            f" ({fn['file']}:{call['line']})"})
                break
            if plus and re.search(r"\b0\b", args):
                out.append({"key": "idiom", "text": "(row, col) idiom: "
                            f"`{call['text']}` ({fn['file']}:{call['line']})"})
                break
        if any(f["key"] == "idiom" for f in out):
            break
    # 3. what happens with no solution: a call from main that reaches the
    #    search, tested in a condition (or by the function it is passed
    #    to) that leads to Error. "Not tested" is only said for a
    #    recursive search, where the call is surely the search.
    main = roles["main"]
    error_gids = {f["gid"] for f in roles["error"]}
    search = set(rec) | {w[0]["gid"] for w in cx["grid"]["writes"]
                         if main is None or w[0] is not main} \
        if cx["grid"] else set(rec)
    found = None
    untested = None
    for call in (main["calls"] if main and search else []):
        targets = team["by_name"].get(call["name"], [])
        if not any(roles_reach(team, t, 3) & search for t in targets):
            continue
        guarded = [s for s in call["stack"] if s["k"] != "loop"]
        in_cond = call["node"] and call["node"]["k"] == "if"
        outer = facts_outer_call(main, call)
        if outer and not (guarded or in_cond):
            if facts_branches_to_error(team, outer, error_gids):
                found = (f"no solution → Error (decided in {outer['name']}"
                         f"(), {main['file']}:{call['line']})")
                break
            continue
        if not (guarded or in_cond):
            if untested is None and any(roles_reach(team, t, 3) & rec
                                        for t in targets):
                untested = ("main does not test the search result "
                            f"({main['file']}:{call['line']})")
            continue
        node = call["node"] if in_cond else guarded[-1]["node"]
        kids = [k for br in node["branches"] for k in read_walk(br["kids"])]
        if any('"Error' in k["text"] for k in kids) or any(
                c["node"] is k and any(
                    roles_reach(team, t, 2) & error_gids
                    for t in team["by_name"].get(c["name"], []))
                for k in kids for c in main["calls"]):
            found = f"no solution → Error ({main['file']}:{node['line']})"
            break
    if found or untested:
        out.append({"key": "no_solution", "text": found or untested})
    return out


def facts_outer_call(main, call):
    """The call whose arguments hold this call (`f(g())` -> f), or None."""
    for c in main["calls"]:
        if c is not call and c["line"] == call["line"] \
                and any(call["text"] in a for a in c["args"]):
            return c
    return None


def facts_branches_to_error(team, outer, error_gids):
    """The called function tests its first param and one branch reaches
    the Error text."""
    for t in team["by_name"].get(outer["name"], []):
        if not t["params"]:
            continue
        name = t["params"][0]["name"]
        for node in t["nodes"]:
            if node["k"] != "if" or not re.search(
                    r"\b%s\b" % re.escape(name), node["text"]):
                continue
            for br in node["branches"]:
                for k in read_walk(br["kids"]):
                    for c in t["calls"]:
                        if c["node"] is k and (t["gid"] in error_gids or any(
                                roles_reach(team, x, 2) & error_gids
                                for x in team["by_name"].get(c["name"], []))):
                            return True
                    if k["k"] in ("stmt", "return") and t["gid"] in \
                            error_gids and "Error" in k["text"]:
                        return True
    return False


def facts_print(cx):
    out = []
    team = cx["team"]
    for fn in cx["roles"]["error"]:
        lit = next(x for x in fn["literals"] if "Error" in x["value"])
        fd = facts_error_fd(team, fn, lit)
        out.append({"key": "error_text", "text": "Error text: "
                    f"{lit['text']} ({fn['file']}:{lit['line']})"})
        if fd is not None:
            name = {"1": "stdout", "2": "stderr"}.get(fd, "fd " + fd)
            out.append({"key": "error_fd", "text": f"Error goes to fd {fd} "
                        f"({name})"})
        break
    return out


def facts_error_fd(team, fn, lit):
    """The fd of the write that prints the Error literal (direct or one
    wrapper deep, with the fd passed as an argument or fixed inside)."""
    for call in fn["calls"]:
        if lit["text"] not in call["text"]:
            continue
        if call["name"] == "write":
            return call["args"][0] if call["args"] else None
        for t in team["by_name"].get(call["name"], []):
            for w in t["calls"]:
                if w["name"] != "write" or not w["args"]:
                    continue
                fd = w["args"][0]
                if re.fullmatch(r"\d", fd):
                    return fd
                for k, p in enumerate(t["params"]):
                    if p["name"] == fd and k < len(call["args"]):
                        return call["args"][k]
    return None
