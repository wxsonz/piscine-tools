"""Which functions parse, solve, print, or write the error (PLAN.md §7.2 step 2).

Roles come from structure, never from names (B8): argv flows into the
parser, a call cycle is the search, digits reaching write() are the printer,
the "Error" literal is the error path. Signals follow the call graph 1-2 hops
because the Norm splits every idea into 25-line functions.
"""

import re

TAINT_HOPS = 3                 # argv is followed this many calls deep
DIGIT_OUT = re.compile(r"\+\s*'0'|'0'\s*\+|\+\s*48\b|\b48\s*\+")


def roles_find(team):
    """Role sets (lists of function fact dicts) for one team."""
    funcs = team["funcs"]
    roles = {"main": None, "argv": None, "argc": None, "parse": [],
             "parse_only": [], "error": [], "print": [], "writers": [],
             "solve": [], "rec": []}

    # 1. the entry point and its argument names
    mains = team["by_name"].get("main") or []
    main = mains[0] if mains else None
    roles["main"] = main
    if main and len(main["params"]) >= 2:
        roles["argc"] = main["params"][0]["name"] or None
        roles["argv"] = main["params"][1]["name"] or None

    # 2. parser: every function argv's text flows into (data flow on calls)
    tainted = roles_taint(team, main, roles["argv"]) if roles["argv"] else {}
    parse = [team["by_gid"][g] for g in tainted if g != main["gid"]]
    if main and roles_main_reads_argv(main, roles["argv"]):
        parse.append(main)
    roles["parse"] = parse
    roles["taint"] = tainted
    parse_gids = {f["gid"] for f in parse}
    roles["parse_only"] = [f for f in parse if f is not main and all(
        c in parse_gids for c in team["callees"][f["gid"]])]

    # 3. the error path: functions holding the "Error" text
    roles["error"] = [f for f in funcs
                      if any("Error" in x["value"] for x in f["literals"])]

    # 4. printer: digits converted and written (through 1-2 wrapper hops)
    roles["writers"] = [f for f in funcs
                        if roles_reaches_ext(team, f, "write", 2)]
    roles["print"] = roles_printers(team, roles)

    # 5. the search: functions on a call cycle
    roles["rec"] = [f for f in funcs if roles_on_cycle(team, f["gid"])
                    and not roles_is_putnbr(f)]

    # 6. solver side: what is left once parse-only, print and wrappers go
    skip = {f["gid"] for f in roles["parse_only"] + roles["print"]}
    for f in funcs:
        if f["gid"] in skip or f is main:
            continue
        if roles_is_wrapper(team, f):
            continue
        roles["solve"].append(f)
    return roles


def roles_taint(team, main, argv):
    """{gid: names} of functions that receive argv's text, from main."""
    tainted = {main["gid"]: {argv}}
    queue = [(main, {argv}, 0)]
    while queue:
        fn, names, hop = queue.pop(0)
        # 1. aliases inside the function: `str = argv[1];`, `p = s + i;`
        #    (a call's result, `n = ft_args(argv[1])`, is not the text)
        for a in fn["assigns"]:
            if a["op"] == "=" and re.fullmatch(r"[A-Za-z_]\w*", a["lhs"]) \
                    and roles_is_alias(a["rhs"], names):
                names.add(a["lhs"])
        if hop >= TAINT_HOPS:
            continue
        # 2. calls that pass it on: the callee's param at that position
        for call in fn["calls"]:
            for target in team["by_name"].get(call["name"], []):
                for k, arg in enumerate(call["args"]):
                    if k >= len(target["params"]) \
                            or not roles_mentions(arg, names):
                        continue
                    pname = target["params"][k]["name"]
                    if not pname:
                        continue
                    seen = tainted.setdefault(target["gid"], set())
                    if pname not in seen:
                        seen.add(pname)
                        queue.append((target, {pname}, hop + 1))
    return tainted


def roles_is_alias(rhs, names):
    m = re.fullmatch(r"[&*(\s]*([A-Za-z_]\w*)\s*(\[[^\]]*\]\s*)*"
                     r"(\+\s*\w+\s*)?\)?", rhs)
    return bool(m) and m.group(1) in names


def roles_mentions(text, names):
    return any(re.search(r"(?<![\w>.])%s\b" % re.escape(n), text)
               for n in names if n)


def roles_main_reads_argv(main, argv):
    """main itself looks inside argv's text (argv[1][i], *argv[1])."""
    if not argv:
        return False
    for x in main["accesses"]:
        if x["name"] == argv and len(x["idx"]) >= 2:
            return True
    return bool(re.search(r"\*\s*\(?\s*%s\s*\[" % re.escape(argv),
                          main["code"]))


def roles_reach(team, fn, hops):
    """gids reachable from fn in at most `hops` calls (fn included)."""
    seen = {fn["gid"]}
    frontier = {fn["gid"]}
    for _ in range(hops):
        nxt = set()
        for g in frontier:
            nxt |= team["callees"].get(g, set())
        frontier = nxt - seen
        seen |= nxt
    return seen


def roles_reaches_ext(team, fn, name, hops):
    return any(name in team["ext"].get(g, set())
               for g in roles_reach(team, fn, hops))


def roles_on_cycle(team, gid):
    seen = set()
    stack = list(team["callees"].get(gid, set()))
    while stack:
        g = stack.pop()
        if g == gid:
            return True
        if g in seen:
            continue
        seen.add(g)
        stack.extend(team["callees"].get(g, set()))
    return False


def roles_is_wrapper(team, fn):
    """A thin write wrapper (ft_putchar, ft_putstr): calls write, no grid."""
    if "write" not in team["ext"].get(fn["gid"], set()):
        return False
    return not any(x["write"] for x in fn["accesses"]) \
        and not team["callees"][fn["gid"]]


def roles_converts(team, fn):
    """Turns a number into a digit char (v + '0') on its way to write(), or
    writes a cell's char directly. A search function never counts."""
    if roles_on_cycle(team, fn["gid"]) and not roles_is_putnbr(fn):
        return False
    for call in fn["calls"]:
        if call["name"] == "write" and len(call["args"]) == 3 \
                and re.match(r"&\s*\w+(->\w+)?\[", call["args"][1]):
            return True
        if any(DIGIT_OUT.search(a) for a in call["args"]):
            return True
    # a buffer filled with digits, then handed to write or a write wrapper
    for a in fn["assigns"]:
        if not DIGIT_OUT.search(a["rhs"]):
            continue
        buf = a["lhs"].split("[")[0].strip()
        for call in fn["calls"]:
            if not any(re.fullmatch(r"&?\s*%s\b.*" % re.escape(buf), arg)
                       for arg in call["args"]):
                continue
            if call["name"] == "write" or any(
                    roles_reaches_ext(team, t, "write", 2)
                    for t in team["by_name"].get(call["name"], [])):
                return True
    return False


def roles_writes_result(team, caller, name):
    """caller does `x = name(..);` then hands x to write or a wrapper."""
    for a in caller["assigns"]:
        if a["op"] != "=" or not re.fullmatch(r"[A-Za-z_]\w*", a["lhs"]) \
                or not re.match(r"%s\s*\(" % re.escape(name), a["rhs"]):
            continue
        for call in caller["calls"]:
            if a["lhs"] not in call["args"]:
                continue
            if call["name"] == "write" or any(
                    roles_reaches_ext(team, t, "write", 2)
                    for t in team["by_name"].get(call["name"], [])):
                return True
    return False


def roles_is_putnbr(fn):
    """ft_putnbr calls itself with n / 10: recursion that prints, no search."""
    return any(c["name"] == fn["name"]
               and any(re.search(r"/\s*10\b", a) for a in c["args"])
               for c in fn["calls"])


def roles_printers(team, roles):
    """Functions that put the grid's digits on the screen: they convert
    digits and reach write, or pass grid cells to such a function in a
    loop (print_grid -> ft_putnbr -> ft_putchar)."""
    error_gids = {f["gid"] for f in roles["error"]}
    parse_gids = {f["gid"] for f in roles["parse_only"]}
    writers = {f["gid"] for f in roles["writers"]}
    core = {f["gid"] for f in team["funcs"]
            if f["gid"] in writers and roles_converts(team, f)
            and f["gid"] not in parse_gids}
    out = [team["by_gid"][g] for g in core]
    # 0. a helper that builds a digit string and returns it to a caller
    #    who writes it: `s = ft_row_str(b, r); ft_putstr(s);`
    for f in team["funcs"]:
        if f["gid"] in core or f["gid"] in parse_gids:
            continue
        built = {a["lhs"].split("[")[0].strip() for a in f["assigns"]
                 if "[" in a["lhs"] and DIGIT_OUT.search(a["rhs"])}
        if not built or not any(n["k"] == "return" and re.fullmatch(
                r"return\s*\(?\s*(%s)\s*\)?" % "|".join(map(re.escape, built)),
                n["text"]) for n in f["nodes"]):
            continue
        for caller in team["funcs"]:
            if roles_writes_result(team, caller, f["name"]):
                out.extend(x for x in (f, caller) if x not in out)
    # 1. callers that loop over the core (the grid walk), 1-2 hops up
    for f in team["funcs"]:
        if f["gid"] in core or f["gid"] in parse_gids:
            continue
        if f["gid"] in error_gids and not f["accesses"]:
            continue
        for call in f["calls"]:
            if not any(s["k"] == "loop" for s in call["stack"]) \
                    or not any("[" in a for a in call["args"]):
                continue
            hit = False
            for t in team["by_name"].get(call["name"], []):
                if roles_reach(team, t, 1) & core:
                    hit = True
            if hit:
                out.append(f)
                break
    return out
