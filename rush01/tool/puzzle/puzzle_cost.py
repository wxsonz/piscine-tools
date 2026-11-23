"""What a puzzle costs the usual student solvers (PLAN.md §5): the piscine
solver (per-cell backtracking, row/col check per placement, clues only on a
full grid) and the naive one (fill everything, check at the end)."""


def cost_latin_squares(n):
    """Every Latin square of 1..n in the piscine solver's visiting order.

    Returns (squares, total): squares is a list of (grid, tries), `tries`
    being the values the piscine solver has tried when it reaches that grid;
    `total` is what it tries over the whole search (a puzzle with no
    solution). Its clue check only runs on full grids, so the first square
    matching a puzzle's clues is where that solver stops (n <= 4: 576
    squares for n = 4; bigger n are far too many).
    """
    assert 1 <= n <= 4, "only small n can be enumerated"
    grid = [[0] * n for _ in range(n)]
    rows = [0] * n
    cols = [0] * n
    squares = []
    state = {"tries": 0}
    # 1. depth-first, row by row, values 1..n in order
    _fill(n, 0, grid, rows, cols, squares, state)
    return squares, state["tries"]


def _fill(n, cell, grid, rows, cols, squares, state):
    """Place a value in `cell` (row-major) and go on; record full grids."""
    if cell == n * n:
        squares.append(([row[:] for row in grid], state["tries"]))
        return
    r = cell // n
    c = cell % n
    for value in range(1, n + 1):
        bit = 1 << value
        state["tries"] += 1
        if rows[r] & bit or cols[c] & bit:
            continue
        grid[r][c] = value
        rows[r] |= bit
        cols[c] |= bit
        _fill(n, cell + 1, grid, rows, cols, squares, state)
        grid[r][c] = 0
        rows[r] &= ~bit
        cols[c] &= ~bit


def cost_naive_tries(n, grid):
    """Full grids the naive solver fills before it reaches `grid` (or
    n ** (n * n) with grid None: it checks them all). It walks every grid of
    1..n in lexicographic order, so this is the grid's rank plus one; it is
    computed, not run (4x4: 4 ** 16 grids)."""
    if grid is None:
        return n ** (n * n)
    rank = 0
    # 1. the grid read as one base-n number, row by row
    for row in grid:
        for value in row:
            rank = rank * n + (value - 1)
    return rank + 1
