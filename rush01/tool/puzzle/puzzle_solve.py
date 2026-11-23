"""Skyscraper basics: visibility, clues of a grid, checking a grid, and the
exact solver (bitmasks + clue pruning, N = 1..9). See tool/puzzle/CONTRACT.md
and tool/SHAPES.md (clue order, grid shape)."""

SIDES = ("top", "bottom", "left", "right")


def puzzle_visible(line):
    """Boxes seen from the start of `line` (strictly taller than all before)."""
    seen = 0
    tallest = 0
    # 1. count every box taller than the tallest so far
    for height in line:
        if height > tallest:
            tallest = height
            seen += 1
    return seen


def puzzle_clues(grid):
    """The 4N clues of a full grid, in the subject's input order."""
    n = len(grid)
    columns = [[grid[r][c] for r in range(n)] for c in range(n)]
    clues = []
    # 1. top (looking down), bottom (looking up), left, right
    clues += [puzzle_visible(col) for col in columns]
    clues += [puzzle_visible(col[::-1]) for col in columns]
    clues += [puzzle_visible(row) for row in grid]
    clues += [puzzle_visible(row[::-1]) for row in grid]
    return clues


def puzzle_check(n, clues, grid):
    """Is `grid` a Latin square of 1..n, and which clues does it break."""
    want_values = set(range(1, n + 1))
    latin = len(grid) == n and all(len(row) == n for row in grid)
    broken = []
    # 1. Latin: every row and every column holds 1..n once
    if latin:
        for i in range(n):
            if set(grid[i]) != want_values:
                latin = False
            if {grid[r][i] for r in range(n)} != want_values:
                latin = False
    # 2. every clue, compared with what the grid shows (only when the shape fits)
    if len(grid) == n and all(len(row) == n for row in grid):
        seen = puzzle_clues(grid)
        for k, want in enumerate(clues):
            if seen[k] != want:
                broken.append({"side": SIDES[k // n], "index": k % n,
                               "want": want, "seen": seen[k]})
    return {"latin": latin, "broken": broken}


def puzzle_solve(n, clues, limit=2):
    """Exact solver: up to `limit` solutions and the number of nodes tried."""
    found = solve_constraints(n, subject_constraints(n, clues), limit, None)
    return {"solutions": found["solutions"], "nodes": found["nodes"]}


def subject_constraints(n, clues):
    """The 4N clues as constraints (cells in viewing order, want, shift)."""
    constraints = []
    # 1. top, bottom, left, right, each line in the order its clue sees it
    for c in range(n):
        constraints.append((line_cells(n, "col", c, True), clues[c], False))
    for c in range(n):
        constraints.append((line_cells(n, "col", c, False), clues[n + c], False))
    for r in range(n):
        constraints.append((line_cells(n, "row", r, True), clues[2 * n + r], False))
    for r in range(n):
        constraints.append((line_cells(n, "row", r, False), clues[3 * n + r], False))
    return constraints


def line_cells(n, kind, index, from_start):
    """Flat cell indexes (r * n + c) of a row or column, in viewing order."""
    if kind == "row":
        cells = [index * n + c for c in range(n)]
    else:
        cells = [r * n + index for r in range(n)]
    if not from_start:
        cells.reverse()
    return tuple(cells)


def solve_constraints(n, constraints, limit, node_cap):
    """Latin squares of 1..n meeting every constraint, by backtracking.

    A constraint is (cells, want, shift): the boxes seen along `cells` must be
    `want`; with `shift`, a line whose first box is 1 must show want + 1
    (the `max = 1` counter bug). Returns {"solutions", "nodes", "complete"};
    `complete` is false when `node_cap` nodes ran out first (FLOW-3).
    """
    full = (1 << (n + 1)) - 2
    domain = [full] * (n * n)
    by_cell = [[] for _ in range(n * n)]
    state = {"grid": [0] * (n * n), "rows": [0] * n, "cols": [0] * n,
             "nodes": 0, "solutions": [], "complete": True}
    # 1. clue bounds: a box d steps from a clue c is at most n - c + 1 + d
    for k, (cells, want, shift) in enumerate(constraints):
        low = max(want, 1)
        high = want + 1 if shift else want
        if high < 1 or low > n:
            return {"solutions": [], "nodes": 0, "complete": True}
        for d, cell in enumerate(cells):
            cap = n - low + 1 + d
            if cap < n:
                domain[cell] &= (1 << (cap + 1)) - 2
            by_cell[cell].append(k)
        if high == 1:
            domain[cells[0]] &= 1 << n
    # 2. search
    _search(n, constraints, domain, by_cell, state, limit, node_cap)
    return {"solutions": state["solutions"], "nodes": state["nodes"],
            "complete": state["complete"]}


def _search(n, constraints, domain, by_cell, state, limit, node_cap):
    """One level of the search; True when the search must stop."""
    grid = state["grid"]
    rows = state["rows"]
    cols = state["cols"]
    # 1. where to branch next (a dead end returns None)
    picked = _pick(n, domain, state)
    if picked is None:
        return False
    best_cell, best_mask = picked
    # 2. no empty cell: a solution
    if best_cell < 0:
        state["solutions"].append([grid[r * n:(r + 1) * n] for r in range(n)])
        return len(state["solutions"]) >= limit
    # 3. try each candidate, smallest first
    r = best_cell // n
    c = best_cell % n
    for value in range(1, n + 1):
        bit = 1 << value
        if not best_mask & bit:
            continue
        state["nodes"] += 1
        if node_cap is not None and state["nodes"] > node_cap:
            state["complete"] = False
            return True
        grid[best_cell] = value
        rows[r] |= bit
        cols[c] |= bit
        if all(_line_fits(n, grid, constraints[k]) for k in by_cell[best_cell]):
            if _search(n, constraints, domain, by_cell, state, limit, node_cap):
                return True
        grid[best_cell] = 0
        rows[r] &= ~bit
        cols[c] &= ~bit
    return False


def _pick(n, domain, state):
    """(cell, candidate mask) to branch on, (-1, 0) when the grid is full,
    None at a dead end. Picks the cell with the fewest candidates, unless a
    value has a single place left in a row or column (measured: 7x7 nodes
    94k -> 13k)."""
    grid = state["grid"]
    rows = state["rows"]
    cols = state["cols"]
    candidates = [0] * (n * n)
    best_cell = -1
    best_mask = 0
    best_count = n + 1
    # 1. the empty cell with the fewest candidates
    for cell in range(n * n):
        if grid[cell]:
            continue
        mask = domain[cell] & ~(rows[cell // n] | cols[cell % n])
        count = mask.bit_count()
        if count == 0:
            return None
        candidates[cell] = mask
        if count < best_count:
            best_cell, best_mask, best_count = cell, mask, count
    if best_count <= 1:
        return best_cell, best_mask
    # 2. a value with no place (dead) or one place (forced) in a line
    for line in range(2 * n):
        if line < n:
            used = rows[line]
            cells = range(line * n, line * n + n)
        else:
            used = cols[line - n]
            cells = range(line - n, n * n, n)
        for value in range(1, n + 1):
            bit = 1 << value
            if used & bit:
                continue
            places = [cell for cell in cells if candidates[cell] & bit]
            if not places:
                return None
            if len(places) == 1:
                return places[0], bit
    return best_cell, best_mask


def _line_fits(n, grid, constraint):
    """Can this (maybe partly filled) line still meet its constraint."""
    cells, want, shift = constraint
    size = len(cells)
    seen = 0
    tallest = 0
    i = 0
    # 1. the filled run from the viewing start
    while i < size and grid[cells[i]]:
        if grid[cells[i]] > tallest:
            tallest = grid[cells[i]]
            seen += 1
        i += 1
    # 2. which seen counts the constraint accepts
    low = want
    high = want
    first = grid[cells[0]]
    if shift and first == 1:
        low = want + 1
        high = want + 1
    elif shift and first == 0:
        high = want + 1
    # 3. the run is final when it is the whole line or holds n
    if i == size or tallest == n:
        return low <= seen <= high
    # 4. bounds: n is still to come and always seen; nothing after n is,
    #    nor a filled box lower than the run's tallest
    tall_at = size
    hidden = 0
    for j in range(i, size):
        value = grid[cells[j]]
        if value == n:
            tall_at = j
            break
        if value and value < tallest:
            hidden += 1
    least = seen + 1
    if tall_at < size:
        most = seen + 1 + min(tall_at - i - hidden, n - 1 - tallest)
    else:
        most = seen + min(n - tallest, size - i - hidden)
    return not (high < least or low > most)
