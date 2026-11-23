"""Explain a team's wrong answers with a misreading (PLAN.md §5, "Diagnosis:
both directions"): every case votes for the misreadings that explain it
and against those it contradicts. Shapes: tool/SHAPES.md "diagnosis"."""

from .puzzle_misread import MISREADINGS, misread_constraints
from .puzzle_solve import puzzle_check, puzzle_visible, solve_constraints
from .puzzle_solve import subject_constraints

# Solves stop after this many nodes (FLOW-3); an unsettled one neither
# explains nor contradicts. 4x4 needs a few hundred at most. REAL_CAP
# matches the bank's (every bonus bank puzzle settles within it).
MISREAD_CAP = 5000
REAL_CAP = 20000


def puzzle_diagnose(cases):
    """SHAPES "diagnosis case" list in, "diagnosis" out.

    Votes: a wrong grid explains M when it meets M's checks, else
    contradicts it; Error on a solvable puzzle explains M when M's puzzle
    has no solution, else contradicts it; a correct grid contradicts M when
    it breaks M's checks (a team with M can't print it), else no vote.
    """
    extra = []
    # 1. the evidence: failures and correct grids
    evidence = _evidence(cases, extra)
    failures = [item for item in evidence if item["failed"]]
    # 2. every misreading: how many failures it explains, how many cases
    #    contradict it
    scored = []
    for order, rule in enumerate(MISREADINGS):
        explains = 0
        contradicted = 0
        for item in evidence:
            fit = _fits(rule, item)
            if fit is True and item["failed"]:
                explains += 1
            elif fit is False:
                contradicted += 1
        scored.append(({"id": rule["id"], "text": rule["text"],
                        "explains": explains, "failures": len(failures),
                        "contradicted": contradicted}, rule, order))
    # 3. most explained first; among equals the fuller rule, then the list
    scored.sort(key=lambda item: (-item[0]["explains"],
                                  item[0]["contradicted"],
                                  bool(item[1].get("weak")), item[2]))
    # 4. the best: explains >= 2, contradicted by none, and no other rule of
    #    the same strength fits as well (a tie is not a finding)
    best = None
    fitting = [item for item in scored
               if item[0]["explains"] >= 2 and item[0]["contradicted"] == 0]
    if fitting:
        top = fitting[0]
        fitting = [item for item in fitting
                   if item[0]["explains"] == top[0]["explains"]
                   and bool(item[1].get("weak")) == bool(top[1].get("weak"))
                   and item[1].get("same_as") is None]
        if len(fitting) == 1:
            best = dict(fitting[0][0])
        else:
            extra.append("tie, no single misreading: "
                         + " / ".join(item[0]["text"] for item in fitting)
                         + " (each explains %d)" % top[0]["explains"])
    return {"best": best, "all": [item[0] for item in scored], "extra": extra}


def _evidence(cases, extra):
    """The cases that can vote, as {"n", "clues", "grid" or None, "failed"}.
    Notes go to `extra`. Error at a size where the team printed no grid is
    left out: a size it doesn't handle, or a program that always prints
    Error, can't be told from a misreading."""
    evidence = []
    errors_by_n = {}
    grids_by_n = {}
    zero_based = 0
    # 1. grids; heights 0..N-1 are read as 1..N
    for case in cases:
        if case.get("clues") is None:
            continue
        n = case["n"]
        if case["outcome"] == "error":
            errors_by_n.setdefault(n, []).append(case)
            continue
        grids_by_n[n] = grids_by_n.get(n, 0) + 1
        grid = case["grid"]
        correct = case["correct"]
        if _is_zero_based(n, grid):
            zero_based += 1
            grid = [[value + 1 for value in row] for row in grid]
            check = puzzle_check(n, case["clues"], grid)
            correct = check["latin"] and not check["broken"]
        evidence.append({"n": n, "clues": case["clues"], "grid": grid,
                         "failed": not correct})
    if zero_based:
        extra.append("heights 0..N-1 printed (forgot + 1) in %d grid(s); "
                     "read as 1..N for the misreadings" % zero_based)
    # 2. Error: a failure when the real puzzle has a solution
    for n in sorted(errors_by_n):
        if not grids_by_n.get(n):
            extra.append(_no_grid_note(n, errors_by_n[n]))
            continue
        for case in errors_by_n[n]:
            if _has_solution(n, subject_constraints(n, case["clues"]),
                             REAL_CAP):
                evidence.append({"n": n, "clues": case["clues"],
                                 "grid": None, "failed": True})
    return evidence


def _no_grid_note(n, cases):
    """Why a size's Errors don't vote; for 4x4 (cheap to solve) also which
    misreadings make every solvable one of them unsolvable."""
    note = ("Error on all %d %dx%d puzzle(s), no grid printed at that size: "
            "left out of the misreadings" % (len(cases), n, n))
    if n != 4:
        return note
    # 1. the solvable ones, and the misreadings that refuse all of them
    solvable = [case for case in cases
                if _has_solution(n, subject_constraints(n, case["clues"]),
                                 REAL_CAP)]
    if not solvable:
        return note
    refusing = []
    for rule in MISREADINGS:
        if all(_has_solution(n, misread_constraints(rule, n, case["clues"]),
                             MISREAD_CAP) is False for case in solvable):
            refusing.append(rule["text"])
    if refusing:
        note += ("; %d were solvable, and these misreadings make every one "
                 "unsolvable, so they can't be told apart (nor from a "
                 "program that always prints Error): %s"
                 % (len(solvable), " / ".join(refusing)))
    return note


def _is_zero_based(n, grid):
    """Every row holds 0..n-1."""
    want = set(range(n))
    return len(grid) == n and all(set(row) == want for row in grid)


def _fits(rule, item):
    """True: the case is what a team with this misreading prints; False:
    it isn't; None: unknown (the solve ran out of nodes)."""
    n = item["n"]
    constraints = misread_constraints(rule, n, item["clues"])
    # 1. a grid: does it meet every check the team makes
    if item["grid"] is not None:
        flat = [value for row in item["grid"] for value in row]
        return all(_meets(flat, constraint) for constraint in constraints)
    # 2. Error: the misread puzzle has no solution
    solved = _has_solution(n, constraints, MISREAD_CAP)
    if solved is None:
        return None
    return not solved


def _has_solution(n, constraints, node_cap):
    """True / False, or None when the cap ran out first."""
    found = solve_constraints(n, constraints, 1, node_cap)
    if found["solutions"]:
        return True
    if not found["complete"]:
        return None
    return False


def _meets(flat, constraint):
    """A full line meets its constraint (shift: the max = 1 counter)."""
    cells, want, shift = constraint
    line = [flat[cell] for cell in cells]
    seen = puzzle_visible(line)
    if shift and line[0] == 1:
        seen -= 1
    return seen == want
