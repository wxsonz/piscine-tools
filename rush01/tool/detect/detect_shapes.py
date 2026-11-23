"""Code shapes several rules share: the grid, the visibility counter, the
duplicate check, the search loop, and what a condition around a call means
(grid full, row end, column end). PLAN.md §7.2 step 3.
"""

import re

from .detect_read import read_int, read_walk

ID = r"[A-Za-z_]\w*"
NAME = r"[A-Za-z_]\w*(?:(?:->|\.)[A-Za-z_]\w*)*"     # n, b->n, s.size
TABLE_ROWS = 24                # 4! row orders
USES_CAP = 10                  # uses of a name that still add to its score
CONST = re.compile(r"-?\d+|'(?:\\.|[^'])'")


def shapes_is_const(text, defines):
    t = text.strip().strip("()").strip()
    return bool(CONST.fullmatch(t)) or (t in defines)


def shapes_grid(team, roles):
    """The array the search fills, with its declaration. None if no array
    is written outside the parser and printer."""
    pool = list(roles["solve"])
    if roles["main"]:
        pool.append(roles["main"])
    cands = {}
    # 1. plain `X[..] = rhs` writes; trial values count more than constants
    for fn in pool:
        for x in fn["accesses"]:
            if not x["write"] or x["decl"] or len(x["idx"]) > 2:
                continue
            a = x["assign"]
            if a["op"] != "=" or re.search(r"<<|\||&", a["rhs"]):
                continue           # bit masks are not the grid
            c = cands.setdefault(x["base"], {"base": x["base"],
                                             "name": x["name"], "writes": [],
                                             "score": 0, "dims2": 0})
            c["writes"].append((fn, x))
            c["score"] += 1 if shapes_is_const(a["rhs"], team["defines"]) else 3
            c["dims2"] += len(x["idx"]) == 2
    # 2. the grid is used everywhere: count its uses (same name, same
    #    number of indexes) across the project, capped
    for c in cands.values():
        nidx = len(c["writes"][0][1]["idx"])
        uses = sum(1 for fn in team["funcs"] for x in fn["accesses"]
                   if x["name"] == c["name"] and len(x["idx"]) == nidx
                   and not x["decl"])
        c["score"] += min(uses, USES_CAP)
    # 3. a 24-row table is a list of row orders, not the grid
    best = None
    for c in cands.values():
        fn, x = c["writes"][0]
        c["decl"] = shapes_decl(team, fn, x)
        origin = shapes_origin(team, fn, c["decl"])
        dims = origin["decl"]["dims"] if origin else []
        if not shapes_grid_sized(dims, team["defines"]):
            continue
        key = (c["score"], c["dims2"])
        if best is None or key > (best["score"], best["dims2"]):
            best = c
    if best is None:
        return None
    # 4. writes of the search first, trial values before constants
    rec = {f["gid"] for f in roles["rec"]}
    best["writes"].sort(key=lambda w: (
        w[0]["gid"] not in rec,
        shapes_is_const(w[1]["assign"]["rhs"], team["defines"])))
    fn, x = best["writes"][0]
    best["decl"] = shapes_decl(team, fn, x)
    # 5. how it is indexed, everywhere it is written
    best["ndim"] = 2 if best["dims2"] * 2 >= len(best["writes"]) else 1
    best["origin"] = shapes_origin(team, best["writes"][0][0], best["decl"])
    return best


def shapes_grid_sized(dims, defines):
    """A grid has a square shape: [k][k] (k = N or N + 2), or N * N >= 16
    cells in one row. Unknown sizes (pointers, `[]`) pass; a 24-row table,
    a [4][5] or a 4-cell helper array does not."""
    vals = [read_int(d, defines) for d in dims]
    if len(dims) == 2:
        a, b = vals
        return a is None or b is None or a == b
    if len(dims) == 1 and vals[0] is not None:
        root = int(vals[0] ** 0.5)
        return vals[0] >= 16 and root * root == vals[0]
    return len(dims) <= 2


def shapes_decl(team, fn, x):
    """Where name in access x is declared: struct field, param, local,
    global. {"kind", "decl", "fn", "file", "line"} or None."""
    name = x["name"]
    if "->" in x["base"] or "." in x["base"]:
        for st in team["structs"]:
            for f in st["fields"]:
                if f["name"] == name:
                    return {"kind": "field", "decl": f, "fn": None,
                            "struct": st, "file": st["file"],
                            "line": f.get("line", st["line"])}
    for p in fn["params"]:
        if p["name"] == name:
            return {"kind": "param", "decl": p, "fn": fn, "file": fn["file"],
                    "line": fn["line"]}
    for d in fn["decls"]:
        if d["name"] == name:
            return {"kind": "local", "decl": d, "fn": fn, "file": fn["file"],
                    "line": d["line"]}
    for g in team["globals"]:
        if g["decl"]["name"] == name:
            return {"kind": "global", "decl": g["decl"], "fn": None,
                    "file": g["file"], "line": g["line"]}
    return None


def shapes_origin(team, fn, found):
    """For a param, follow callers up to 3 hops to the real declaration."""
    hops = 0
    while found and found["kind"] == "param" and hops < 3:
        hops += 1
        index = next((k for k, p in enumerate(fn["params"])
                      if p is found["decl"]), None)
        nxt = None
        for caller in team["funcs"]:
            for call in caller["calls"]:
                if call["name"] != fn["name"] or index is None \
                        or index >= len(call["args"]):
                    continue
                m = re.fullmatch(r"&?\s*(%s)" % ID, call["args"][index])
                if not m:
                    continue
                probe = {"name": m.group(1), "base": m.group(1)}
                got = shapes_decl(team, caller, probe)
                if got:
                    nxt = (caller, got)
                    break
            if nxt:
                break
        if not nxt:
            break
        fn, found = nxt
    return found


def shapes_index_roles(fn, skip=()):
    """Variable names used as row / col / pos index in 2D or flat accesses.
    `pos / 4` and `pos % 4` give pos; `[r * 4 + c]` gives row and col.
    A name used both ways (a loop runner) is dropped."""
    # 1. from the accesses: [r][c], [pos / n][pos % n], [r * n + c]
    rows, cols, poss = set(), set(), set()
    lead = re.compile(r"\(?\s*(%s)\s*(?:[+-]\s*\d+)?\s*\)?" % ID)
    for x in fn["accesses"]:
        if x["name"] in skip or x["decl"]:
            continue
        if len(x["idx"]) == 2:
            a, b = x["idx"]
            m = re.fullmatch(r"\(?\s*(%s)\s*[/%%]\s*\w+\s*\)?" % ID, a)
            if m:
                poss.add(m.group(1))
                continue
            ma, mb = lead.fullmatch(a), lead.fullmatch(b)
            if ma and mb:
                rows.add(ma.group(1))
                cols.add(mb.group(1))
        elif len(x["idx"]) == 1:
            i = x["idx"][0]
            m = re.fullmatch(r"\(?\s*(%s)\s*\*\s*\w+\s*\)?\s*\+\s*(%s)"
                             % (ID, ID), i)
            if m:
                rows.add(m.group(1))
                cols.add(m.group(2))
    # 2. `r = pos / n` and `c = pos % n` name the row and column of pos
    for a in fn["assigns"]:
        m = re.fullmatch(r"\(?\s*(%s)\s*([/%%])\s*\w+\s*\)?(\s*\+\s*1)?"
                         % ID, a["rhs"])
        if a["op"] == "=" and re.fullmatch(ID, a["lhs"]) and m:
            poss.add(m.group(1))
            (rows if m.group(2) == "/" else cols).add(a["lhs"])
    both = rows & cols
    # 3. the step of the recursion: `f(.., X + 1)` calls of fn to itself
    steps = set()
    for c in fn["calls"]:
        if c["name"] == fn["name"]:
            for a in c["args"]:
                m = re.fullmatch(r"(%s)\s*\+\s*1" % ID, a)
                if m:
                    steps.add(m.group(1))
    return {"row": rows - both, "col": cols - both, "pos": poss,
            "step": steps - (cols - both)}


def shapes_atoms(cond):
    """`a == 3 && !f(x)` -> [(lhs, op, rhs)] for each comparison."""
    out = []
    # `->`, `<<` and `>>` are not comparisons: hide them while splitting
    hidden = cond.replace("->", "\x01").replace("<<", "\x02").replace(
        ">>", "\x03")
    for part in re.split(r"&&|\|\|", hidden):
        p = part.strip()
        m = re.fullmatch(r"[!(\s]*(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+?)[)\s]*",
                         p)
        if m:
            out.append(tuple(shapes_unhide(x) for x in (
                m.group(1).strip("( "), m.group(2), m.group(3).strip("() "))))
    return out


def shapes_unhide(text):
    return text.replace("\x01", "->").replace("\x02", "<<").replace(
        "\x03", ">>")


def shapes_value(text, defines):
    """Classify a bound: 3 / 4 / 11 / 12 / 15 / 16, or 'N-1', 'N', 'NN'."""
    v = read_int(text, defines)
    if v is not None:
        return v
    t = " ".join(text.split())
    if re.fullmatch(r"%s\s*-\s*1" % NAME, t):
        return "N-1"
    if re.fullmatch(r"(%s)\s*\*\s*\1" % NAME, t):
        return "NN"
    if re.fullmatch(r"(%s)\s*\*\s*\1\s*-\s*1" % NAME, t):
        return "NN-1"
    if re.fullmatch(NAME, t):
        return "N"
    return None


def shapes_atom_kind(atom, iroles, defines):
    """What one comparison tells about the search position:
    'full' (grid done), 'row_end', 'col_end', or None."""
    lhs, op, rhs = atom
    val = shapes_value(rhs, defines)
    if op in ("<", "<="):
        return None
    # 1. pos-based: pos == 16, pos % 4 == 3, pos / 4 == 3, pos >= 12
    m = re.fullmatch(r"\(?\s*(%s)\s*(\+\s*1\s*)?\)?\s*([%%/])\s*\w+" % ID, lhs)
    if m:
        plus1 = bool(m.group(2))
        if m.group(3) == "%":
            if (not plus1 and val in (3, "N-1")) or (plus1 and val == 0):
                return "row_end"
            return None
        if val in (3, "N-1"):
            return "col_end"
        return None
    if not re.fullmatch(ID, lhs):
        return None
    if lhs in iroles["pos"] or val in (16, 15, "NN", "NN-1"):
        if val in (16, 15, "NN", "NN-1"):
            return "full"
        if val in (12, 11) and op in (">=", ">"):
            return "col_end"
        return None
    # 2. (row, col): last col -> the row is complete; last row -> columns
    if lhs in iroles.get("step", ()) and lhs not in iroles["row"] \
            and val in (4, "N") and op in ("==", ">="):
        return "full"              # one row per call, past the last row
    if lhs in iroles["col"] and val in (3, "N-1"):
        return "row_end"
    if lhs in iroles["row"]:
        if val in (3, "N-1"):
            return "col_end"
        if val in (4, "N"):
            return "full"
    if val in (3, "N-1") and op in ("==", "!=", ">="):
        return "line_end"          # the last cell of some line
    return None


def shapes_call_kinds(call, iroles, defines):
    """What the conditions around a call say about the search position:
    (kinds, guarded). kinds is a set of 'full' / 'row_end' / 'col_end';
    guarded is True when a position-like condition we can't read is around
    it (then nobody may call it "every placement"). Conditions that are only
    calls (`if (ft_is_free(..))`) say nothing about the position."""
    kinds = set()
    guarded = False
    stack = call["stack"]
    for k, entry in enumerate(stack):
        if entry["k"] == "loop":
            continue
        # 1. the comparisons that hold when the call runs
        in_cond = (k == len(stack) - 1 and call["node"] is entry["node"]
                   and call["node"]["k"] == "if"
                   and call["tok"] <= call["node"]["b"])
        if entry["k"] == "else":
            atoms = [a for a in shapes_atoms(entry["node"]["text"])
                     if a[1] == "!="]
            plain = [a for a in shapes_atoms(entry["node"]["text"])
                     if "(" not in a[0]]
        else:
            atoms = [a for a in shapes_atoms(entry["cond"])
                     if in_cond or a[1] != "!="]
            plain = [a for a in shapes_atoms(entry["cond"])
                     if "(" not in a[0]]
        # 2. what they say about the position; unread ones guard the call
        found = False
        for atom in atoms:
            kind = shapes_atom_kind(atom, iroles, defines)
            if kind:
                kinds.add(kind)
                found = True
        if plain and not found and not in_cond:
            guarded = True
    return kinds, guarded


NEGATE = {"<": ">=", "<=": ">", "!=": "==", ">": "<=", ">=": "<", "==": "!="}


def shapes_early_kinds(fn, call, iroles, defines):
    """Kinds from early exits before the call: `if (col < 3) return (1);`
    means the rest of the function runs only when col >= 3."""
    kinds = set()
    for node in fn["tree"]:
        if node["k"] != "if" or node["line"] >= call["line"] \
                or len(node["branches"]) != 1:
            continue
        kids = node["branches"][0]["kids"]
        if not kids or any(k["k"] != "return" for k in kids):
            continue
        parts = re.split(r"\|\|", node["text"])
        for part in parts:
            for lhs, op, rhs in shapes_atoms(part):
                if NEGATE[op] == "!=":
                    continue           # "not the last cell" says nothing
                kind = shapes_atom_kind((lhs, NEGATE[op], rhs), iroles,
                                        defines)
                if kind:
                    kinds.add(kind)
    return kinds


def shapes_counters(fns):
    """Visibility counters: `if (cell > max) { max = cell; count++; }` in a
    loop, or unrolled cell by cell. One dict per function."""
    out = []
    for fn in fns:
        found = []
        for node in fn["nodes"]:
            if node["k"] != "if":
                continue
            # 1. `cell > max` (or `max < cell`)
            cond = node["branches"][0]["cond"]
            m = re.fullmatch(r"(.+?)\s*(>=|>)\s*(%s)" % ID,
                             cond.replace("->", "\x01"))
            n = re.fullmatch(r"(%s)\s*(<=|<)\s*(.+)" % ID, cond)
            if m:
                big, op, mx = shapes_unhide(m.group(1)), m.group(2), \
                    m.group(3)
            elif n:
                mx, op, big = n.group(1), n.group(2), n.group(3)
            else:
                continue
            # 2. the branch sets max and counts one more
            kids = list(read_walk(node["branches"][0]["kids"]))
            assigns = [a for a in fn["assigns"]
                       if any(a["node"] is k for k in kids)]
            sets_max = any(a["lhs"] == mx and a["op"] == "=" for a in assigns)
            counts = [a["lhs"] for a in assigns if a["lhs"] != mx and (
                a["op"] in ("++",) or (a["op"] == "+=" and a["rhs"] == "1")
                or re.fullmatch(r"%s\s*\+\s*1" % re.escape(a["lhs"]),
                                a["rhs"]))]
            if not sets_max or not counts:
                continue
            found.append({"fn": fn, "line": node["line"], "max": mx,
                          "count": counts[0], "op": op, "big": big,
                          "in_loop": any(s["k"] == "loop"
                                         for s in node["stack"]),
                          "init_count": shapes_init(fn, counts[0],
                                                    node["line"]),
                          "init_max": shapes_init(fn, mx, node["line"])})
        # 3. in a loop, or unrolled (the same test written out 2+ times)
        if any(c["in_loop"] for c in found) or len(found) >= 2:
            out.append(found[0])
    return out


def shapes_init(fn, name, before):
    last = None
    for a in fn["assigns"]:
        if a["lhs"] == name and a["op"] == "=" and a["line"] <= before:
            last = a["rhs"]
    return last


def shapes_dups(fns, defines):
    """Duplicate checks: in a loop, `if (cell == value) return ...` (or a
    bit test `mask & (1 << v)`), with an early exit or a flag."""
    out = []
    for fn in fns:
        for node in fn["nodes"]:
            if node["k"] != "if":
                continue
            cond = node["branches"][0]["cond"]
            bits = re.search(r"&\s*\(?\s*1\s*<<", cond)
            in_loop = any(s["k"] == "loop" for s in node["stack"])
            eq = None
            for lhs, op, rhs in shapes_atoms(cond):
                if op != "==" or not ("[" in lhs or "[" in rhs):
                    continue
                other = rhs if "[" in lhs else lhs
                if shapes_is_const(other, defines):
                    continue
                eq = (lhs, rhs)
            if not (bits or (eq and in_loop)):
                continue
            kids = list(read_walk(node["branches"][0]["kids"]))
            if not any(k["k"] in ("return", "stmt") for k in kids):
                continue
            out.append({"fn": fn, "line": node["line"], "cond": cond,
                        "bits": bool(bits)})
    return out


def shapes_search_loops(team, roles, grid):
    """Loops of the recursive functions that hold the recursive call. Each
    tells its trial variable and whether the grid gets the trial value."""
    rec = {f["gid"] for f in roles["rec"]}
    out = []
    for fn in roles["rec"]:
        for node in fn["nodes"]:
            if node["k"] != "loop":
                continue
            inner = [c for c in fn["calls"]
                     if any(s["node"] is node for s in c["stack"])]
            if not any(t["gid"] in rec for c in inner
                       for t in team["by_name"].get(c["name"], [])):
                continue
            m = re.fullmatch(r"\(?\s*(%s)\s*(<=|<)\s*(.+?)\)?" % ID,
                             node["text"])
            var = m.group(1) if m else None
            kids = list(read_walk(node["kids"]))
            writes = []
            if grid:
                writes = [x for x in fn["accesses"] if x["write"]
                          and x["name"] == grid["name"]
                          and any(x["assign"]["node"] is k for k in kids)]
            trial = [x for x in writes if var and re.search(
                r"\b%s\b" % re.escape(var), x["assign"]["rhs"])]
            out.append({"fn": fn, "node": node, "var": var,
                        "bound": m.group(3) if m else None,
                        "trial": trial, "writes": writes, "calls": inner})
    return out


def shapes_tables(team):
    """24-row tables of row orders: declarations whose first dim is 24."""
    out = []
    decls = [(fn, d) for fn in team["funcs"] for d in fn["decls"]]
    decls += [(None, g["decl"]) for g in team["globals"]]
    decls += [(None, f) for st in team["structs"] for f in st["fields"]]
    for fn, d in decls:
        if d["dims"] and read_int(d["dims"][0], team["defines"]) == TABLE_ROWS:
            out.append({"fn": fn, "decl": d})
    return out


def shapes_nest(team, fn, seen=None):
    """Deepest loop nesting, counting loops of functions called in loops."""
    seen = set() if seen is None else seen
    if fn["gid"] in seen:
        return 0
    seen = seen | {fn["gid"]}
    best = 0
    for node in fn["nodes"]:
        if node["k"] == "loop":
            depth = 1 + sum(1 for s in node["stack"] if s["k"] == "loop")
            best = max(best, depth)
    for call in fn["calls"]:
        depth = sum(1 for s in call["stack"] if s["k"] == "loop")
        for t in team["by_name"].get(call["name"], []):
            best = max(best, depth + shapes_nest(team, t, seen))
    return best
