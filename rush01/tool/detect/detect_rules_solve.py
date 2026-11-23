"""Solve rules (PLAN.md §7.3 Solving, tiers 0-3):
where the search checks duplicates, clues, bitmasks, MRV, propagation, line
intersection, or dancing links, relative to the recursion.
"""

import re

from .detect_hits import ev, ev_file, hit, where
from .detect_read import read_int, read_walk
from .detect_roles import roles_reach
from .detect_rules_data import (MASK, MASK_TEST, rule_data_bits,
                                rule_data_cand, rules_write_ev)
from .detect_shapes import (ID, shapes_atoms, shapes_call_kinds,
                            shapes_early_kinds, shapes_index_roles,
                            shapes_is_const, shapes_nest)

INPUT_LIT = re.compile(r"[1-9]( [1-9]){15}")
GRID_LIT = re.compile(r"([1-9] ?){3}[1-9]\n")
BIG_COUNT = re.compile(r"\b(65536|4294967296|1048576|16777216)\b|<<\s*32\b")
BASE4 = re.compile(r"/\s*\w+\s*\)?\s*%\s*4\b|%\s*4\s*\)?\s*\+\s*1\b")
DLX_LINK = re.compile(r"->\s*\w+\s*->\s*\w+\s*=")


def rules_sites(cx):
    """Every call reachable from the search, with the conditions it runs
    under. Conditions and index roles (row / col / pos) are inherited down
    the calls, up to 3 hops: `ft_lines_ok(g, row, col)` tests `col == 3`
    with the caller's meaning of col."""
    # 1. start from every function of the search
    team = cx["team"]
    roles = cx["roles"]
    rec = {f["gid"] for f in roles["rec"]}
    out = []
    queue = [(f, frozenset(), False, {}, 0) for f in roles["rec"]]
    seen = set()
    while queue:
        fn, inherited, guard_in, passed, hop = queue.pop(0)
        key = (fn["gid"], inherited, guard_in,
               tuple(sorted((k, tuple(sorted(v))) for k, v in passed.items())))
        if key in seen:
            continue
        seen.add(key)
        # 2. this function's index roles, plus the ones its caller passed
        iroles = shapes_index_roles(fn)
        for role, names in passed.items():
            iroles[role] = set(iroles.get(role, set())) | names
        # 3. each call, with the conditions around it; go down one hop
        for call in fn["calls"]:
            own, guarded = shapes_call_kinds(call, iroles, cx["defines"])
            kinds = inherited | own | shapes_early_kinds(fn, call, iroles,
                                                         cx["defines"])
            guarded = guarded or guard_in
            out.append({"fn": fn, "call": call, "kinds": kinds,
                        "guarded": guarded})
            for t in team["by_name"].get(call["name"], []):
                if t["gid"] in rec or hop >= 3:
                    continue
                give = rules_pass_roles(call, t, iroles)
                queue.append((t, frozenset(kinds), guarded, give, hop + 1))
    return out


def rules_pass_roles(call, target, iroles):
    """Index roles of the caller's arguments, renamed to the callee's params."""
    give = {}
    for k, arg in enumerate(call["args"]):
        if k >= len(target["params"]) or not target["params"][k]["name"]:
            continue
        for role in ("row", "col", "pos"):
            if arg in iroles.get(role, set()):
                give.setdefault(role, set()).add(target["params"][k]["name"])
    return give


def rules_checks(cx):
    """Where duplicates and clues are checked, relative to the search."""
    counter_gids = {c["fn"]["gid"] for c in cx["counters"]}
    dup_gids = {d["fn"]["gid"] for d in cx["dups"]}
    rec = {f["gid"] for f in cx["roles"]["rec"]}
    team = cx["team"]
    out = {"dup_place": [], "clue_full": [], "clue_line": [],
           "clue_every": [], "line_kinds": set(), "dup_full": []}
    # 1. calls to a counter (clues) or a duplicate check, by condition
    for s in cx["sites"]:
        # the recursive call is the search itself, not a check
        targets = [t["gid"] for t in team["by_name"].get(s["call"]["name"],
                                                         [])
                   if t["gid"] not in rec]
        if any(t in counter_gids for t in targets):
            line = s["kinds"] & {"row_end", "col_end", "line_end"}
            if "full" in s["kinds"]:
                out["clue_full"].append(s)
            elif line:
                out["clue_line"].append(s)
                out["line_kinds"] |= line
            elif not s["guarded"]:
                out["clue_every"].append(s)
        if any(t in dup_gids for t in targets):
            if "full" in s["kinds"]:
                out["dup_full"].append(s)
            else:
                out["dup_place"].append(s)
    # 2. a duplicate check written inline in the search itself
    for d in cx["dups"]:
        if d["fn"]["gid"] in rec:
            out["dup_place"].append({"fn": d["fn"], "call": None,
                                     "kinds": frozenset(), "line": d["line"]})
    return out


def rules_site_ev(site, why):
    line = site["call"]["line"] if site["call"] else site["line"]
    return ev(site["fn"], line, why)


def rules_recursion_ev(cx):
    """The recursive call of the search, and the function holding it."""
    team = cx["team"]
    rec = {f["gid"] for f in cx["roles"]["rec"]}
    for lp in cx["loops"]:
        for c in lp["calls"]:
            if any(t["gid"] in rec for t in team["by_name"].get(c["name"],
                                                                [])):
                return lp["fn"], ev(lp["fn"], c["line"], "tries each value "
                                    "and goes on with the next cell "
                                    "(recursion)")
    for fn in cx["roles"]["rec"]:
        for c in fn["calls"]:
            if any(t["gid"] in rec for t in team["by_name"].get(c["name"],
                                                                [])):
                return fn, ev(fn, c["line"], "calls itself for the next cell "
                              "(recursion)")
    return None, None


def rules_reset_ev(cx):
    g = cx["grid"]
    for lp in cx["loops"]:
        for x in lp["writes"]:
            if read_int(x["assign"]["rhs"], cx["defines"]) == 0:
                return ev(lp["fn"], x["line"], "puts the cell back to 0 when "
                          "the try failed (backtrack)")
    if g:
        for fn in cx["roles"]["rec"]:
            for x in fn["accesses"]:
                if x["write"] and x["name"] == g["name"] \
                        and read_int(x["assign"]["rhs"], cx["defines"]) == 0:
                    return ev(fn, x["line"], "puts the cell back to 0 when "
                              "the try failed (backtrack)")
    return None


def rules_trial_ev(cx):
    for lp in cx["loops"]:
        if lp["trial"]:
            return ev(lp["fn"], lp["node"]["line"], "tries the values one "
                      "after another in each cell")
    return None


def rules_perm_ev(cx):
    """A table (or a loop bound) of 24 row orders."""
    if cx["tables"]:
        t = cx["tables"][0]
        if t["fn"]:
            return ev(t["fn"], t["decl"]["line"], "a table of the 24 orders "
                      "of a row (4! permutations)")
        for g in cx["team"]["globals"]:
            if g["decl"] is t["decl"]:
                return ev_file(cx["team"], g["file"], g["line"],
                               "a table of the 24 orders of a row")
        for st in cx["team"]["structs"]:
            if t["decl"] in st["fields"]:
                return ev_file(cx["team"], st["file"], st["line"],
                               "a table of the 24 orders of a row")
    for fn in cx["solve_fns"]:
        for node in fn["nodes"]:
            if node["k"] == "loop" and re.search(r"<\s*24\b|<=\s*23\b",
                                                 node["text"]):
                return ev(fn, node["line"], "loops over the 24 orders of a "
                          "row")
    return None


def rules_is_swap(fn):
    """`t = a; a = b; b = t;` somewhere in fn."""
    plain = [a for a in fn["assigns"] if a["op"] == "="]
    for k in range(len(plain) - 2):
        a, b, c = plain[k:k + 3]
        if a["rhs"] == b["lhs"] and b["rhs"] == c["lhs"] \
                and c["rhs"] == a["lhs"]:
            return True
    return False


def rules_perm_gen_ev(cx):
    """Row orders generated either by swapping (swap, recurse, swap back) or
    by a `used[]` array (mark 1, write perm[k], recurse, unmark 0)."""
    team = cx["team"]
    # 1. swap-based permutation generator
    for lp in cx["loops"]:
        fn = lp["fn"]
        swaps = [c for c in lp["calls"] if any(
            rules_is_swap(t) for t in team["by_name"].get(c["name"], []))]
        if len(swaps) >= 2 or (rules_is_swap(fn) and lp["calls"]):
            line = swaps[0]["line"] if swaps else lp["node"]["line"]
            return ev(fn, line, "generates the orders of a row by swapping "
                      "(a permutation generator)")
    # 2. used[]-array permutation generator (separate from writing the 2D grid)
    gname = cx["grid"]["name"] if cx["grid"] else None
    rec = {f["gid"] for f in cx["roles"]["rec"]}
    for fn in cx["roles"]["rec"]:
        if gname and any(x["write"] and x["name"] == gname
                         for x in fn["accesses"]):
            continue
        for loop in [n for n in fn["nodes"] if n["k"] == "loop"]:
            kids = list(read_walk(loop["kids"]))
            has_rec = any(any(t["gid"] in rec
                              for t in team["by_name"].get(c["name"], []))
                          and any(s["node"] is loop for s in c["stack"])
                          for c in fn["calls"])
            if not has_rec:
                continue
            writes1d = [x for x in fn["accesses"]
                        if x["write"] and len(x["idx"]) == 1
                        and any(x["assign"]["node"] is k for k in kids)]
            by_arr = {}
            for x in writes1d:
                by_arr.setdefault(x["name"], []).append(x)
            used_arr = None
            used_line = None
            for name, xs in by_arr.items():
                vals = {read_int(x["assign"]["rhs"], cx["defines"])
                        for x in xs}
                if 0 in vals and 1 in vals:
                    used_arr = name
                    used_line = xs[0]["line"]
                    break
            if used_arr and any(n != used_arr for n in by_arr):
                return ev(fn, used_line, "generates row orders with a used[] "
                          "array (a permutation generator)")
    return None


def rules_row_place(cx):
    """The search places a whole line per step: in the recursion's loop, a
    copy of a row order into the grid (`g[x][y] = perm[x]` in a loop),
    inline or one call deep. Returns (rec fn, line) or None."""
    g = cx["grid"]
    if not g:
        return None
    team = cx["team"]
    copiers = set()
    for fn, x in g["writes"]:
        loops = [s for s in x["assign"]["node"]["stack"] if s["k"] == "loop"]
        if loops and re.search(r"\w+\s*\[[^\]]+\]", x["assign"]["rhs"]) \
                and not shapes_is_const(x["assign"]["rhs"], cx["defines"]):
            copiers.add(fn["gid"])
    rec = {f["gid"] for f in cx["roles"]["rec"]}
    for lp in cx["loops"]:
        fn = lp["fn"]
        for c in lp["calls"]:
            if any(t["gid"] in copiers and t["gid"] not in rec
                   for t in team["by_name"].get(c["name"], [])):
                return fn, c["line"]
        if fn["gid"] in copiers:
            for w_fn, x in g["writes"]:
                if w_fn is fn and any(s["node"] is lp["node"]
                                      for s in x["assign"]["node"]["stack"]):
                    return fn, x["line"]
    return None


def rules_search_core(cx):
    """Required for every backtracking entry: recursion that writes the
    grid. Returns (fn, evidence) or (None, None)."""
    fn, rec_ev = rules_recursion_ev(cx)
    if not fn or not cx["grid"]:
        return None, None
    rec = {f["gid"] for f in cx["roles"]["rec"]}
    writes = [w for w in cx["grid"]["writes"] if w[0]["gid"] in rec]
    if not writes and not any(lp["writes"] for lp in cx["loops"]):
        return None, None
    return fn, rec_ev


def rules_no_bt(cx):
    """Shapes that make a recursion something else than cell backtracking."""
    return bool(rules_perm_ev(cx)) or bool(rule_solve_cands(cx)) \
        or bool(rules_perm_gen_ev(cx) and rules_row_place(cx)) \
        or bool(rule_solve_dlx(cx)) or bool(rule_solve_line_solver(cx)) \
        or bool(rule_solve_propagate(cx)) or bool(rule_solve_mrv(cx)) \
        or bool(rule_solve_bits(cx))


def rules_clue_fact(ch):
    kinds = ch["line_kinds"]
    if "row_end" in kinds and "col_end" in kinds:
        text = "row-end and col-end: a line's clues are checked as soon as "\
               "the line is full"
    elif "row_end" in kinds:
        text = "row-end: row clues when a row is full"
        text += "; column clues at the end" if ch["clue_full"] else ""
    elif "col_end" in kinds:
        text = "col-end: column clues when a column is full"
        text += "; row clues at the end" if ch["clue_full"] else ""
    elif "line_end" in kinds:
        text = "line-end: a line's clues are checked when its last cell is "\
               "placed (which line, row or column, is not clear from the code)"
    elif ch["clue_every"]:
        text = "clues checked on every placement (partial lines)"
    elif ch["clue_full"]:
        text = "clues checked only when the grid is full"
    else:
        return None
    return {"key": "clue_check", "text": text}


def rule_solve_bt_end(cx):
    fn, rec_ev = rules_search_core(cx)
    if not fn or rules_no_bt(cx):
        return None
    ch = rules_checks(cx)
    if ch["dup_place"] or ch["clue_line"] or ch["clue_every"]:
        return None
    end = (ch["clue_full"] or ch["dup_full"])
    if not end:
        return None
    req = [rec_ev, rules_site_ev(end[0], "every check waits until the grid "
                                 "is full")]
    sup = [e for e in (rules_trial_ev(cx), rules_reset_ev(cx)) if e]
    return hit("solve.bt_end", req, sup, [where(fn)],
               [f for f in (rules_clue_fact(ch),) if f])


def rule_solve_bt_unique(cx):
    fn, rec_ev = rules_search_core(cx)
    if not fn or rules_no_bt(cx):
        return None
    ch = rules_checks(cx)
    if not ch["dup_place"] or ch["clue_line"] or ch["clue_every"]:
        return None
    req = [rec_ev, rules_site_ev(ch["dup_place"][0], "checks the row and "
                                 "column for the value before placing it")]
    sup = [e for e in (
        rules_site_ev(ch["clue_full"][0], "clues are checked when the grid "
                      "is full") if ch["clue_full"] else None,
        rules_reset_ev(cx), rules_trial_ev(cx)) if e]
    return hit("solve.bt_unique", req, sup, [where(fn)],
               [f for f in (rules_clue_fact(ch),) if f])


def rule_solve_bt_clue_line(cx):
    fn, rec_ev = rules_search_core(cx)
    if not fn or rules_no_bt(cx):
        return None
    ch = rules_checks(cx)
    if not ch["clue_line"]:
        return None
    req = [rec_ev, rules_site_ev(ch["clue_line"][0], "checks a line's clues "
                                 "as soon as the line is full")]
    sup = [e for e in (
        rules_site_ev(ch["dup_place"][0], "checks the row and column for "
                      "the value before placing it")
        if ch["dup_place"] else None,
        rules_site_ev(ch["clue_full"][0], "the other lines are checked when "
                      "the grid is full") if ch["clue_full"] else None,
        rules_reset_ev(cx)) if e]
    return hit("solve.bt_clue_line", req, sup, [where(fn)],
               [f for f in (rules_clue_fact(ch),) if f])


def rule_solve_partial_prune(cx):
    fn, rec_ev = rules_search_core(cx)
    if not fn or rules_no_bt(cx):
        return None
    ch = rules_checks(cx)
    if not ch["clue_every"] or ch["clue_line"]:
        return None
    req = [rec_ev, rules_site_ev(ch["clue_every"][0], "checks the clues on "
                                 "every placement, with the line still "
                                 "partly empty")]
    sup = [e for e in (
        rules_site_ev(ch["dup_place"][0], "checks the row and column for "
                      "the value") if ch["dup_place"] else None,
        rules_reset_ev(cx)) if e]
    return hit("solve.partial_prune", req, sup, [where(fn)],
               [f for f in (rules_clue_fact(ch),) if f])


def rule_solve_bt_iter(cx):
    """No recursion; one loop drives a position that moves forward when a
    value fits and back when none does, and the grid cell gets the values."""
    if cx["roles"]["rec"] or not cx["grid"]:
        return None
    g = cx["grid"]
    for fn in cx["solve_fns"]:
        iroles = shapes_index_roles(fn)
        index_vars = iroles["row"] | iroles["col"] | iroles["pos"]
        for x in fn["accesses"]:
            if x["name"] == g["name"]:
                index_vars |= set(i for i in x["idx"] if re.fullmatch(ID, i))
        for loop in [n for n in fn["nodes"] if n["k"] == "loop"]:
            # 1. a position that goes forward and back in this loop: the
            #    loop's own variable, or the cell index (`while (1)` loops)
            kids = list(read_walk(loop["kids"]))
            inside = [a for a in fn["assigns"]
                      if any(a["node"] is k for k in kids)]
            fwd = {a["lhs"] for a in inside if a["op"] in ("++", "+=")
                   or re.fullmatch(r"%s\s*\+\s*1" % re.escape(a["lhs"]),
                                   a["rhs"])}
            back = [a for a in inside if a["lhs"] in fwd and (
                a["op"] in ("--", "-=") or re.fullmatch(
                    r"%s\s*-\s*1" % re.escape(a["lhs"]), a["rhs"]))
                and (re.search(r"\b%s\b" % re.escape(a["lhs"]), loop["text"])
                     or a["lhs"] in index_vars)]
            # 2. the cell gets values in the loop
            cells = [x for x in fn["accesses"] if x["name"] == g["name"]
                     and any(x["a"] >= k["a"] and x["b"] <= k["b"]
                             for k in kids)
                     and (x["write"] or (x["assign"] and x["assign"]["op"]
                                         in ("++", "+=")))]
            # or one call deep: the loop asks a helper to fill the cell
            writers = {w[0]["gid"] for w in g["writes"]}
            for c in fn["calls"]:
                if any(s["node"] is loop for s in c["stack"]) and any(
                        t["gid"] in writers and t is not fn
                        for t in cx["team"]["by_name"].get(c["name"], [])):
                    cells.append({"line": c["line"]})
            if not back or not cells:
                continue
            cells.sort(key=lambda x: bool(x.get("assign")) and x["write"]
                       and shapes_is_const(x["assign"]["rhs"], cx["defines"]))
            req = [ev(fn, back[0]["line"], "steps back to the previous cell "
                      "(no recursion: a position counter going back)"),
                   ev(fn, cells[0]["line"], "tries the next value in the "
                      "cell")]
            sup = [ev(fn, loop["line"], "one loop drives the position over "
                      "the grid")]
            return hit("solve.bt_iter", req, sup, [where(fn)])
    return None


def rule_solve_row_perm(cx):
    """Row orders (a 24-row table, or generated), placed one per row by a
    recursion over the rows."""
    if rule_solve_line_solver(cx):
        return None
    # 1. where the row orders come from
    perm = rules_perm_ev(cx)
    place = rules_row_place(cx)
    if not perm and place:
        perm = rules_perm_gen_ev(cx)
    if not perm or not cx["roles"]["rec"]:
        return None
    # 2. the search that places them, a whole row at a time
    if place:
        fn, line = place
    else:
        fn, rec_ev = rules_recursion_ev(cx)
        if not fn:
            return None
        line = rec_ev["line"]
    req = [perm, ev(fn, line, "places one row order per row, then goes on "
                    "with the next row")]
    ch = rules_checks(cx)
    sup = [e for e in (
        rules_site_ev(ch["dup_place"][0], "checks the columns for "
                      "duplicates") if ch["dup_place"] else None,
        rules_row_clue_ev(cx, ch, fn))
        if e]
    return hit("solve.row_perm", req, sup, [where(fn)])


def rules_row_clue_ev(cx, ch, search_fn):
    """Where the row-order search meets the clues: inside the generator
    (row orders filtered by the row's own clues) or in the search."""
    sites = ch["clue_full"] + ch["clue_line"] + ch["clue_every"]
    if not sites:
        return None
    inside = roles_reach(cx["team"], search_fn, 3)
    for s in sites:
        if s["fn"]["gid"] not in inside:
            return rules_site_ev(s, "keeps only the row orders that fit the "
                                 "row's own clues")
    return rules_site_ev(sites[0], "checks the clues")


def rule_solve_brute_perm_loops(cx):
    perm = rules_perm_ev(cx)
    if not perm or cx["roles"]["rec"]:
        return None
    deep = None
    for fn in cx["solve_fns"]:
        if shapes_nest(cx["team"], fn) >= 4:
            deep = fn
            break
    if not deep:
        return None
    req = [perm, ev(deep, deep["line"], "nested loops pick a row order for "
                    "each of the 4 rows, every combination")]
    sup = []
    counter_gids = {c["fn"]["gid"] for c in cx["counters"]}
    for c in deep["calls"]:
        if sum(1 for s in c["stack"] if s["k"] == "loop") >= 3 and any(
                roles_reach(cx["team"], t, 2) & counter_gids
                for t in cx["team"]["by_name"].get(c["name"], [])):
            sup.append(ev(deep, c["line"], "checks only once all rows are "
                          "chosen"))
            break
    return hit("solve.brute_perm_loops", req, sup, [where(deep)])


def rules_odometer(cx):
    """The grid as an odometer: a loop bumps a cell (`g[..]++` or `g[..]--`),
    and when it rolls over sets it back to its starting value and carries into
    the next cell in one direction only (never moving the same position var
    both forward and back). Returns (fn, bump line, carry line) or None."""
    g = cx["grid"]
    n = cx["n"]
    for fn in cx["solve_fns"]:
        for loop in [n for n in fn["nodes"] if n["k"] == "loop"]:
            kids = list(read_walk(loop["kids"]))
            inside = [a for a in fn["assigns"]
                      if any(a["node"] is k for k in kids)]
            cell = [a for a in inside if a["lhs"].startswith(g["name"] + "[")]
            # 1. count-up cell or count-down cell with matching rollover reset
            up_b = [a for a in cell if a["op"] in ("++", "+=")
                    or re.search(r"\+\s*1$", a["rhs"])]
            up_r = [a for a in cell if a["op"] == "="
                    and read_int(a["rhs"], cx["defines"]) in (0, 1)]
            dn_b = [a for a in cell if a["op"] in ("--", "-=")
                    or re.search(r"-\s*1$", a["rhs"])]
            dn_r = [a for a in cell if a["op"] == "=" and (
                read_int(a["rhs"], cx["defines"]) == n
                or re.fullmatch(ID, a["rhs"]))]
            bumps, resets = (up_b, up_r) if (up_b and up_r) else (dn_b, dn_r)
            # 2. carry index moves monotonically (never both ++ and -- on same var)
            moves = [a for a in inside if a["op"] in ("++", "--", "+=", "-=")
                     and not a["lhs"].startswith(g["name"] + "[")]
            if not bumps or not resets or not moves:
                continue
            up_vars = {a["lhs"] for a in moves if a["op"] in ("++", "+=")}
            dn_vars = {a["lhs"] for a in moves if a["op"] in ("--", "-=")}
            if up_vars & dn_vars:
                continue           # going back is backtracking, not counting
            return fn, bumps[0]["line"], resets[0]["line"]
    return None


def rules_full_check_loop(cx, odo_fn):
    """A loop that alternates: check the whole grid, then the next grid."""
    counter_gids = {c["fn"]["gid"] for c in cx["counters"]}
    team = cx["team"]
    for fn in cx["solve_fns"]:
        for c in fn["calls"]:
            if c["name"] != odo_fn["name"] or not any(
                    s["k"] == "loop" for s in c["stack"]):
                continue
            loop = [s["node"] for s in c["stack"] if s["k"] == "loop"][-1]
            for d in fn["calls"]:
                if any(s["node"] is loop for s in d["stack"]) and any(
                        roles_reach(team, t, 2) & counter_gids
                        for t in team["by_name"].get(d["name"], [])):
                    return [ev(fn, d["line"], "checks the whole grid before "
                               "moving to the next one")]
    return []


def rule_solve_brute16(cx):
    if cx["roles"]["rec"] or rules_perm_ev(cx) or not cx["grid"]:
        return None
    for fn in cx["solve_fns"]:
        # 1. a 4^16 counter, base-4 digits, or 8+ nested loops
        big = [n for n in fn["nodes"] if BIG_COUNT.search(n["text"])]
        # a counter cut into base-4 digits: `k % 4` and `k = k / 4`
        shifts = {a["lhs"] for a in fn["assigns"] if re.fullmatch(
            r"%s\s*/\s*4" % re.escape(a["lhs"]), a["rhs"])
            or (a["op"] == "/=" and a["rhs"] == "4")}
        base4 = [n for n in fn["nodes"] if BASE4.search(n["text"])
                 and any(re.search(r"\b%s\s*%%\s*4" % re.escape(k),
                                   n["text"]) for k in shifts)]
        nest = shapes_nest(cx["team"], fn)
        odo = rules_odometer(cx)
        if odo and odo[0] is fn:
            req = [ev(fn, odo[1], "bumps one cell to its next value, like an "
                      "odometer digit"),
                   ev(fn, odo[2], "when it rolls over: back to the start and "
                      "carry into the next cell (every grid, in order)")]
            sup = rules_full_check_loop(cx, fn)
            return hit("solve.brute16", req, sup, [where(fn)])
        if not (big or base4 or nest >= 8):
            continue
        # 2. evidence, and the check of each full grid
        req = []
        if big:
            req.append(ev(fn, big[0]["line"], "counts through all 4^16 "
                          "fillings of the grid"))
        if base4:
            req.append(ev(fn, base4[0]["line"], "turns the counter into one "
                          "value per cell (base 4 digits)"))
        if nest >= 8 and not req:
            req.append(ev(fn, fn["line"], f"{nest} loops nested: one per "
                          "cell, every combination"))
        req.append(rules_write_ev(cx, cx["grid"], "fills the cells") or
                   ev(fn, fn["line"], "fills the cells"))
        counter_gids = {c["fn"]["gid"] for c in cx["counters"]}
        sup = [ev(fn, c["line"], "checks each full grid")
               for c in fn["calls"][:20] if any(
                   roles_reach(cx["team"], t, 2) & counter_gids
                   for t in cx["team"]["by_name"].get(c["name"], []))][:1]
        return hit("solve.brute16", req, sup, [where(fn)])
    return None


def rules_hardcode_lits(cx):
    out = []
    for fn in cx["team"]["funcs"]:
        for lit in fn["literals"]:
            if INPUT_LIT.fullmatch(lit["value"]):
                out.append((fn, lit, "compares the input with a fixed "
                            "puzzle string"))
            elif len(GRID_LIT.findall(lit["value"])) >= 2:
                out.append((fn, lit, "prints a fixed grid written in the "
                            "code"))
    return out


def rule_solve_hardcode(cx):
    if cx["roles"]["rec"] or cx["loops"] or rule_solve_bt_iter(cx) \
            or rule_solve_brute16(cx) or rule_solve_brute_perm_loops(cx):
        return None
    lits = rules_hardcode_lits(cx)
    consts = []
    if cx["grid"]:
        consts = [(fn, x) for fn, x in cx["grid"]["writes"]
                  if all(read_int(i, cx["defines"]) is not None
                         for i in x["idx"])
                  and shapes_is_const(x["assign"]["rhs"], cx["defines"])]
    if not lits and len(consts) < 16:
        return None
    req = []
    if lits:
        fn, lit, why = lits[0]
        req.append(ev(fn, lit["line"], why))
    else:
        fn, x = consts[0]
        req.append(ev(fn, x["line"], f"{len(consts)} cells set to fixed "
                      "values, no search"))
    req.append(ev(fn, fn["line"], "no search anywhere: no recursion, no "
                  "loop that tries values"))
    sup = [ev(f, lit["line"], why) for f, lit, why in lits[1:3]]
    return hit("solve.hardcode", req, sup, [where(fn)])


def rule_solve_prefill(cx):
    """`if (clue == 4)` / `== 1` / `a + b == 5` outside the recursion, with
    the grid written in its branch."""
    g = cx["grid"]
    if not g:
        return None
    team = cx["team"]
    rec = {f["gid"] for f in cx["roles"]["rec"]}
    writers = {fn["gid"] for fn, _ in g["writes"]}
    n = cx["n"]
    found = []
    # 1. clue tests outside the search whose branch writes the grid
    for fn in cx["solve_fns"]:
        if fn["gid"] in rec:
            continue
        for node in fn["nodes"]:
            if node["k"] != "if":
                continue
            rule = rules_prefill_rule(node["text"], g["name"], cx["defines"],
                                      n)
            if not rule:
                continue
            kids = [k for br in node["branches"][:1]
                    for k in read_walk(br["kids"])]
            writes = any(x["write"] and x["name"] == g["name"] and any(
                x["assign"]["node"] is k for k in kids)
                for x in fn["accesses"])
            calls = any(c["node"] is k and any(
                t["gid"] in writers and t["gid"] not in rec
                for t in team["by_name"].get(c["name"], []))
                for c in fn["calls"] for k in kids)
            if writes or calls:
                found.append((fn, node, rule))
    if not found:
        return None
    # 2. one evidence line per kind of rule (4, 1, pair)
    rules_seen = {}
    for fn, node, rule in found:
        rules_seen.setdefault(rule, (fn, node))
    first_rule = next(iter(rules_seen))
    fn, node = rules_seen[first_rule]
    why = {"four": "a clue of 4 fills the line 1..N before the search",
           "one": "a clue of 1 puts N next to it before the search",
           "pair": "two opposite clues summing to N + 1 fix where N goes"}
    req = [ev(fn, node["line"], why[first_rule])]
    sup = [ev(f, nd["line"], why[r]) for r, (f, nd) in rules_seen.items()
           if r != first_rule]
    return hit("solve.prefill", req, sup, [where(fn)])


def rules_prefill_rule(cond, grid_name, defines, n):
    for lhs, op, rhs in shapes_atoms(cond):
        if op != "==" or "[" not in lhs or lhs.startswith(grid_name + "["):
            continue
        v = read_int(rhs, defines)
        if "+" in lhs and v == n + 1:
            return "pair"
        if v == n or (v is None and re.fullmatch(ID, rhs)):
            return "four"
        if v == 1:
            return "one"
    return None


def rule_solve_cands(cx):
    """Candidate lists used by the search: crossed out as cells are placed,
    read when picking a value."""
    rec = cx["roles"]["rec"]
    if not rec or rule_solve_propagate(cx) or rule_solve_mrv(cx):
        return None
    cand = rule_data_cand(cx)
    if not cand:
        return None
    reads = []
    for fn in rec:
        for node in fn["nodes"]:
            if node["k"] in ("if", "loop") and (re.search(
                    r"\w+\[[^\]]+\]\[[^\]]+\]\[[^\]]+\]", node["text"])
                    or MASK_TEST.search(node["text"])):
                reads.append(ev(fn, node["line"], "picks only values still "
                                "in the cell's candidate list"))
                break
    if not reads:
        return None
    fn, _ = rules_recursion_ev(cx)
    return hit("solve.cands", [cand["evidence"][0], reads[0]],
               cand["evidence"][1:2], [where(fn or rec[0])])


def rule_solve_bits(cx):
    """Tier 3: bitmask used-sets tested and updated inside the search."""
    fn, rec_ev = rules_search_core(cx)
    if not fn or rule_solve_mrv(cx) or rule_solve_propagate(cx) \
            or rule_solve_line_solver(cx) or rule_solve_dlx(cx):
        return None
    if not rule_data_bits(cx):
        return None
    # 1. look for both a bit test and a bit set/clear in the search
    reach = roles_reach(cx["team"], fn, 2)
    tested = None
    mutated = None
    for f in cx["team"]["funcs"]:
        if f["gid"] not in reach:
            continue
        for node in f["nodes"]:
            if not tested and MASK_TEST.search(node["text"]):
                tested = ev(f, node["line"], "tests a row/col bitmask "
                            "(1 << v) instead of scanning the line")
            if not mutated and MASK.search(node["text"]):
                mutated = ev(f, node["line"], "sets and clears the bitmask "
                             "on placement and backtrack")
    if not (tested and mutated):
        return None
    return hit("solve.bits", [rec_ev, tested, mutated],
               [e for e in (rules_reset_ev(cx),) if e], [where(fn)])


def rule_solve_mrv(cx):
    """Tier 3: picks the empty cell with the fewest legal candidates next
    (scans the grid, counts choices per empty cell, tracks the minimum)."""
    fn, rec_ev = rules_search_core(cx)
    if not fn or not cx["grid"] or rule_solve_propagate(cx):
        return None
    gname = cx["grid"]["name"]
    reach = roles_reach(cx["team"], fn, 2)
    # 1. a function reachable from the recursion that picks a min-count cell
    for f in cx["team"]["funcs"]:
        if f["gid"] not in reach:
            continue
        has_empty = any(node["k"] == "if"
                        and re.search(r"\b%s\[.*==\s*0\b|!\s*%s\["
                                      % (re.escape(gname), re.escape(gname)),
                                      node["text"])
                        for node in f["nodes"])
        if not has_empty:
            continue
        for node in f["nodes"]:
            if node["k"] != "if":
                continue
            lt = [a for a in shapes_atoms(node["text"]) if a[1] == "<"
                  and re.fullmatch(ID, a[0]) and re.fullmatch(ID, a[2])]
            if not lt:
                continue
            kids = list(read_walk(node["branches"][0]["kids"]))
            assigns = [a for a in f["assigns"]
                       if any(a["node"] is k for k in kids)]
            # updates the min tracker AND saves at least one cell coordinate
            for lhs, _, rhs in lt:
                if any(a["lhs"] == rhs and a["rhs"] == lhs for a in assigns) \
                        and len(assigns) >= 2:
                    return hit("solve.mrv",
                               [rec_ev,
                                ev(f, node["line"], "picks the empty cell "
                                   "with the fewest possible values (MRV)")],
                               [e for e in (rules_reset_ev(cx),) if e],
                               [where(fn), where(f)])
    return None


def rule_solve_propagate(cx):
    """Tier 3: fixpoint constraint-propagation loop (`while (changed)` setting
    forced singletons until nothing changes) over per-cell candidates."""
    cand = rule_data_cand(cx)
    if not cand or not cx["grid"]:
        return None
    gname = cx["grid"]["name"]
    # 1. a fixpoint loop: condition tests a flag reset to 0 and set back to 1
    for fn in cx["solve_fns"]:
        for loop in [n for n in fn["nodes"] if n["k"] == "loop"]:
            m = re.fullmatch(r"(%s)(?:\s*!=\s*0)?" % ID, loop["text"].strip())
            if not m:
                continue
            flag = m.group(1)
            kids = list(read_walk(loop["kids"]))
            inside = [a for a in fn["assigns"]
                      if any(a["node"] is k for k in kids)]
            vals = {read_int(a["rhs"], cx["defines"])
                    for a in inside if a["lhs"] == flag and a["op"] == "="}
            if not ({0, 1} <= vals):
                continue
            # writes the grid or calls a helper inside the propagation loop
            writes_g = any(a["lhs"].startswith(gname + "[") for a in inside)
            has_single = any(node["k"] == "if" and (
                re.search(r"==\s*1\b", node["text"])
                or re.search(r"&\s*\(\s*\w+\s*-\s*1\s*\)", node["text"]))
                for node in kids)
            if not (writes_g or has_single):
                continue
            return hit("solve.propagate",
                       [cand["evidence"][0],
                        ev(fn, loop["line"], "repeats forced deductions "
                           "until nothing changes (constraint propagation)")],
                       cand["evidence"][1:2], [where(fn)])
    return None


def rule_solve_line_solver(cx):
    """Tier 3: keeps candidate line permutations for both rows and columns
    and intersects them via a 2D cell mask / two-axis filtering loop."""
    perm = rules_perm_ev(cx) or rules_perm_gen_ev(cx)
    if not perm:
        return None
    # 1. builds a 2D cell bitmask from line options (`mask[r][c] |= 1 <<`)
    #    and filters line options against it (`mask[r][c] & (1 << ...)`)
    build_ev = None
    filter_ev = None
    for fn in cx["solve_fns"]:
        for node in fn["nodes"]:
            if not build_ev and re.search(
                    r"\w+\[[^\]]+\]\[[^\]]+\]\s*\|=\s*\(?\s*1\s*<<",
                    node["text"]):
                build_ev = ev(fn, node["line"], "collects allowed values per "
                              "cell across valid line orders")
            if not filter_ev and re.search(
                    r"\w+\[[^\]]+\]\[[^\]]+\]\s*&\s*\(?\s*1\s*<<",
                    node["text"]):
                filter_ev = ev(fn, node["line"], "filters line orders against "
                               "the crossed-axis cell mask")
    if not (build_ev and filter_ev):
        return None
    return hit("solve.line_solver", [perm, build_ev, filter_ev], [],
               [where(cx["solve_fns"][0])])


def rule_solve_dlx(cx):
    """Tier 3: Knuth's dancing links — a node struct with 4+ self-links
    (left/right/up/down) and doubly-linked cover/uncover pointer rewrites."""
    # 1. node struct with >= 4 self-referential pointer fields
    node_st = None
    for st in cx["team"]["structs"]:
        self_ptrs = [f for f in st["fields"] if f["ptr"] >= 1
                     and ("struct" in f["text"] or f["base"] == st["name"])]
        if len(self_ptrs) >= 4:
            node_st = st
            break
    if not node_st:
        return None
    # 2. doubly-linked unlink/relink (`x->right->left = x->left`, etc.)
    links = []
    for fn in cx["team"]["funcs"]:
        for node in fn["nodes"]:
            if DLX_LINK.search(node["text"]):
                links.append((fn, node))
                break
    if not links:
        return None
    fn, node = links[0]
    req = [ev_file(cx["team"], node_st["file"], node_st["line"],
                   "a 4-way linked node struct (left/right/up/down)"),
           ev(fn, node["line"], "unlinks / relinks matrix nodes in place "
              "(dancing links cover/uncover)")]
    sup = [ev(f, nd["line"], "second cover / uncover link rewrite")
           for f, nd in links[1:2]]
    return hit("solve.dlx", req, sup, [where(fn)])
