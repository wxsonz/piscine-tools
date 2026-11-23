"""Data rules (PLAN.md §7.3 Data structure): how the grid is stored,
plus the add-on structures (bit masks, candidate lists).
"""

import re

from .detect_hits import ev, ev_file, hit, where
from .detect_read import read_int
from .detect_shapes import ID

MASK = re.compile(r"(%s)((?:\[[^\]]+\]){1,3})\s*(\|=|&=|\^=)\s*~?\s*\(?\s*"
                  r"1\s*<<" % ID)
MASK_TEST = re.compile(r"(%s)((?:\[[^\]]+\]){1,3})\s*&\s*\(?\s*1\s*<<" % ID)


def rules_grid_decl(cx):
    g = cx["grid"]
    if not g:
        return None, None
    found = g["origin"] or g["decl"]
    return g, found


def rules_decl_ev(cx, found, why):
    if not found:
        return None
    return ev_file(cx["team"], found["file"], found["line"], why)


def rules_write_ev(cx, g, why, pred=None):
    for fn, x in g["writes"]:
        if pred is None or pred(x):
            return ev(fn, x["line"], why)
    return None


def rules_grid_where(cx, g, found):
    if found and found["fn"]:
        return {"file": found["file"], "func": found["fn"]["name"],
                "line": found["line"]}
    if found:
        return {"file": found["file"], "func": None, "line": found["line"]}
    fn = g["writes"][0][0]
    return where(fn)


def rules_is_padded(cx, found):
    if not found:
        return False
    dims = found["decl"]["dims"]
    if len(dims) != 2:
        return False
    n = cx["n"]
    vals = [read_int(d, cx["defines"]) for d in dims]
    if vals[0] == vals[1] == n + 2:
        return True
    return all(re.fullmatch(r"%s\s*\+\s*2" % ID, d) for d in dims)


def rule_data_struct(cx):
    g, found = rules_grid_decl(cx)
    if not g or not found or found["kind"] != "field":
        return None
    st = found["struct"]
    req = [ev_file(cx["team"], st["file"], st["line"], "a struct holds the "
                   "board"),
           rules_write_ev(cx, g, f"the search writes `{g['base']}[..]` inside "
                          "the struct")]
    sup = []
    if st["file"].endswith(".h"):
        sup.append(ev_file(cx["team"], st["file"], found["line"],
                           "declared in a header, shared by every file"))
    others = [f for f in st["fields"] if f is not found["decl"]]
    if others:
        sup.append(ev_file(cx["team"], st["file"], others[0].get("line",
                                                                 st["line"]),
                           "the struct also carries other data (size, "
                           "clues)"))
    return hit("data.struct", [e for e in req if e], sup,
               [{"file": st["file"], "func": None, "line": st["line"]}],
               [{"key": "grid_field",
                 "text": f"board field: {found['decl']['text']}"}])


def rule_data_padded(cx):
    g, found = rules_grid_decl(cx)
    if not g or g["ndim"] != 2 or (found and found["kind"] == "field"):
        return None
    if not rules_is_padded(cx, found):
        return None
    n = cx["n"]
    req = [rules_decl_ev(cx, found, f"board is {n + 2}x{n + 2}: the puzzle "
                         "plus a border for the clues")]
    border = None
    for fn in cx["team"]["funcs"]:
        for x in fn["accesses"]:
            if x["name"] == g["name"] and len(x["idx"]) == 2 and any(
                    read_int(i, cx["defines"]) in (0, n + 1) for i in x["idx"]):
                border = ev(fn, x["line"], "reads a clue from the border row "
                            "or column")
                break
        if border:
            break
    sup = [e for e in (border,) if e]
    return hit("data.padded", req, sup, [rules_grid_where(cx, g, found)])


def rules_malloc_rows(cx):
    """malloc of N pointers, then a malloc per row."""
    ptr_alloc = None
    row_alloc = None
    for fn in cx["team"]["funcs"]:
        for call in fn["calls"]:
            if call["name"] != "malloc":
                continue
            text = " ".join(call["args"])
            if re.search(r"sizeof\s*\(\s*\w+\s*\*+\s*\)", text):
                ptr_alloc = ptr_alloc or (fn, call)
            elif any(s["k"] == "loop" for s in call["stack"]):
                row_alloc = row_alloc or (fn, call)
    return ptr_alloc, row_alloc


def rule_data_malloc2d(cx):
    g, found = rules_grid_decl(cx)
    if not g or not found or found["decl"]["ptr"] < 2 \
            or found["kind"] == "field":
        return None
    ptr_alloc, row_alloc = rules_malloc_rows(cx)
    if not ptr_alloc and not row_alloc:
        return None
    req = [rules_decl_ev(cx, found, "the board is an `int **`")]
    first = ptr_alloc or row_alloc
    req.append(ev(first[0], first[1]["line"], "malloc of the row pointers"
                  if ptr_alloc else "malloc of each row"))
    sup = []
    if ptr_alloc and row_alloc:
        sup.append(ev(row_alloc[0], row_alloc[1]["line"],
                      "then one malloc per row, in a loop"))
    return hit("data.malloc2d", req, sup, [rules_grid_where(cx, g, found)])


def rule_data_char(cx):
    g, found = rules_grid_decl(cx)
    if not g or not found or found["decl"]["base"] != "char" \
            or found["kind"] == "field":
        return None
    chars = rules_write_ev(cx, g, "the search writes chars ('1'..'4')",
                           lambda x: re.search(r"'[1-9]'",
                                               x["assign"]["rhs"]))
    trial = None
    for lp in cx["loops"]:
        if lp["trial"] and re.search(r"'[0-9]'", lp["node"]["text"]):
            trial = ev(lp["fn"], lp["node"]["line"], "tries the chars '1'.."
                       "'4' directly")
    req = [rules_decl_ev(cx, found, "the board is a char array")]
    if not chars and not trial:
        return None
    sup = [e for e in (chars, trial) if e]
    return hit("data.char", req, sup[:1] + sup[1:],
               [rules_grid_where(cx, g, found)])


def rule_data_grid2d(cx):
    g, found = rules_grid_decl(cx)
    if not g or g["ndim"] != 2:
        return None
    if found and (found["kind"] == "field" or rules_is_padded(cx, found)
                  or found["decl"]["base"] == "char"):
        return None
    if found and found["decl"]["ptr"] >= 2 and any(rules_malloc_rows(cx)):
        return None
    req = [rules_write_ev(cx, g, "the grid is written as `[row][col]`",
                          lambda x: len(x["idx"]) == 2)]
    sup = []
    if found and len(found["decl"]["dims"]) == 2:
        sup.append(rules_decl_ev(cx, found, "declared as a 2D array"))
    pos = rules_write_ev(cx, g, "a cell number is split into row and column "
                         "(pos / n, pos % n)",
                         lambda x: len(x["idx"]) == 2 and "/" in x["idx"][0])
    if pos:
        sup.append(pos)
    return hit("data.grid2d", [e for e in req if e], [e for e in sup if e],
               [rules_grid_where(cx, g, found)])


def rule_data_flat(cx):
    g, found = rules_grid_decl(cx)
    if not g or g["ndim"] != 1:
        return None
    if found and (found["kind"] == "field" or found["decl"]["base"] == "char"
                  or len(found["decl"]["dims"]) > 1
                  or found["decl"]["ptr"] > 1):
        return None
    req = [rules_write_ev(cx, g, "the grid is written with one index per "
                          "cell", lambda x: len(x["idx"]) == 1)]
    sup = []
    if found:
        sup.append(rules_decl_ev(cx, found, "declared as a 1D array / "
                                 "pointer"))
    rc = rules_write_ev(cx, g, "row and column folded into one index "
                        "(r * n + c)",
                        lambda x: "*" in x["idx"][0] and "+" in x["idx"][0])
    if rc:
        sup.append(rc)
    return hit("data.flat", [e for e in req if e], [e for e in sup if e],
               [rules_grid_where(cx, g, found)])


def rules_masks(cx, ndims):
    """Bit-mask writes / tests on arrays with this many indexes."""
    out = []
    for fn in cx["team"]["funcs"]:
        for node in fn["nodes"]:
            for rx in (MASK, MASK_TEST):
                for m in rx.finditer(node["text"]):
                    if m.group(2).count("[") in ndims:
                        out.append((fn, node, m.group(1)))
    return out


def rule_data_cand(cx):
    team = cx["team"]
    n = cx["n"]
    req = None
    for fn in team["funcs"]:
        for d in fn["decls"]:
            vals = [read_int(x, cx["defines"]) for x in d["dims"]]
            if len(vals) == 3 and vals[0] == vals[1] == n \
                    and vals[2] in (n, n + 1):
                req = ev(fn, d["line"], "one list of possible values per "
                         "cell (3D array)")
    masks = rules_masks(cx, (2,))
    if not req and masks:
        fn, node, name = masks[0]
        req = ev(fn, node["line"], f"`{name}[r][c]` is a bit mask of the "
                 "values still possible in a cell")
    if not req:
        return None
    sup = []
    for fn in cx["solve_fns"]:
        for x in fn["accesses"]:
            if x["write"] and len(x["idx"]) == 3 \
                    and read_int(x["assign"]["rhs"], cx["defines"]) != 1:
                sup.append(ev(fn, x["line"], "values are crossed out (and "
                              "put back)"))
                break
        if sup:
            break
    return hit("data.cand", [req], sup, [])


def rule_data_bits(cx):
    masks = rules_masks(cx, (1,))
    if not masks:
        return None
    fn, node, name = masks[0]
    req = [ev(fn, node["line"], f"`{name}[i]` keeps the used values of a "
              "row or column as bits (1 << v)")]
    sup = [ev(f, nd["line"], "tests a bit before placing")
           for f, nd, _ in masks[1:2]]
    return hit("data.bits", req, sup, [where(fn)])
