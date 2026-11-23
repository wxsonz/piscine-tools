"""The rules, wired together (PLAN.md §7.2 step 4, §7.3): the context
every rule shares, computed once per team, and the table of rules per part.

A rule returns None when a required signal is missing or a ruling-out
signal is present; else a hit (detect_hits.py): score = 2 per required
signal + 1 per supporting one, with one evidence line per signal and a plain
"why". Rules read structure (shapes, data flow, the call graph), never names
(B8). Each part's rules live in detect_rules_<part>.py.
"""

import re

from .detect_hits import where
from .detect_read import read_int
from .detect_rules_data import (rule_data_bits, rule_data_cand,
                                rule_data_char, rule_data_flat,
                                rule_data_grid2d, rule_data_malloc2d,
                                rule_data_padded, rule_data_struct)
from .detect_rules_parse import (rule_parse_atoi, rule_parse_fixed,
                                 rule_parse_fsm, rule_parse_none,
                                 rule_parse_scan, rule_parse_split,
                                 rules_parse_signals, rules_rejects)
from .detect_rules_print import (rule_print_board, rule_print_char,
                                 rule_print_line, rule_print_putstr)
from .detect_rules_solve import (rule_solve_bits, rule_solve_brute16,
                                 rule_solve_brute_perm_loops,
                                 rule_solve_bt_clue_line, rule_solve_bt_end,
                                 rule_solve_bt_iter, rule_solve_bt_unique,
                                 rule_solve_cands, rule_solve_dlx,
                                 rule_solve_hardcode, rule_solve_line_solver,
                                 rule_solve_mrv, rule_solve_partial_prune,
                                 rule_solve_prefill, rule_solve_propagate,
                                 rule_solve_row_perm, rules_sites)
from .detect_shapes import (ID, shapes_counters, shapes_dups, shapes_grid,
                            shapes_search_loops, shapes_tables)


def rules_context(team, roles):
    """Everything the rules share, computed once per team."""
    cx = {"team": team, "roles": roles, "defines": team["defines"]}
    solve_fns = roles["solve"] + ([roles["main"]] if roles["main"] else [])
    cx["solve_fns"] = solve_fns
    cx["grid"] = shapes_grid(team, roles)
    cx["counters"] = shapes_counters(team["funcs"])
    cx["dups"] = shapes_dups([f for f in solve_fns], team["defines"])
    cx["tables"] = shapes_tables(team)
    cx["loops"] = shapes_search_loops(team, roles, cx["grid"])
    cx["n"] = rules_n(team)
    cx["n_computed"] = rules_n_computed(roles)
    cx["sites"] = rules_sites(cx)
    cx["parse_sig"] = rules_parse_signals(cx)
    cx["rejects"] = rules_rejects(cx)
    return cx


def rules_n(team):
    """N as a number when fixed (a define, else 4)."""
    for name in ("N", "SIZE", "n", "size", "GRID_SIZE"):
        v = read_int(team["defines"].get(name), team["defines"])
        if v:
            return v
    return 4


def rules_n_computed(roles):
    """(fn, line, text) where the parser derives N from the count
    (`n = count / 4`, `return (count / 4)`, `(len + 1) / 8`), or None."""
    size = re.compile(r"\w+\s*/\s*4\b|\)\s*/\s*8\b|/\s*2\s*/\s*4")
    for fn in roles["parse"]:
        for a in fn["assigns"]:
            if a["op"] == "=" and re.fullmatch(ID, a["lhs"]) \
                    and size.search(a["rhs"]):
                return fn, a["line"], f"{a['lhs']} = {a['rhs']}"
        for node in fn["nodes"]:
            if node["k"] == "return" and size.search(node["text"]):
                return fn, node["line"], node["text"]
    return None


RULES = {
    "parse": [rule_parse_split, rule_parse_atoi, rule_parse_fsm,
              rule_parse_fixed, rule_parse_scan, rule_parse_none],
    "data": [rule_data_struct, rule_data_padded, rule_data_malloc2d,
             rule_data_char, rule_data_grid2d, rule_data_flat],
    "data_also": [rule_data_cand, rule_data_bits],
    "solve": [rule_solve_hardcode, rule_solve_brute16,
              rule_solve_brute_perm_loops, rule_solve_bt_end,
              rule_solve_bt_unique, rule_solve_bt_clue_line,
              rule_solve_bt_iter, rule_solve_row_perm, rule_solve_cands,
              rule_solve_bits, rule_solve_partial_prune, rule_solve_mrv,
              rule_solve_propagate, rule_solve_line_solver, rule_solve_dlx],
    "solve_also": [rule_solve_prefill],
    "print": [rule_print_char, rule_print_line, rule_print_board,
              rule_print_putstr],
}
