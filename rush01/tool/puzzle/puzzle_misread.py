"""The misreadings of PLAN.md §5: rules for how a buggy team reads or checks
the clues, each turned into the constraints its solver really works with
(cells in viewing order, want, shift; see puzzle_solve.solve_constraints)."""

from .puzzle_solve import line_cells

ALL_SIDES = ("top", "bottom", "left", "right")

# One row per misreading (FLOW-4), in the contract's order.
#   order:   how the 4N input numbers become the team's top/bottom/left/right
#   reverse: the side the team indexes backwards (N - 1 - i), or None
#   view:    "bottom_down" / "right_rightward": that side seen the wrong way
#   sides:   the sides the team checks
#   counter: the visibility counter the team wrote
#   weak:    checks fewer clues, so it fits whatever a fuller rule fits
#   same_as: another misreading that always gives the same constraints
MISREADINGS = [
    {"id": "transpose", "order": "transpose",
     "text": "rows and columns swapped (transposed)"},
    {"id": "swap_top_bottom", "order": "swap_top_bottom",
     "text": "top and bottom clues swapped"},
    {"id": "swap_left_right", "order": "swap_left_right",
     "text": "left and right clues swapped"},
    {"id": "rows_first", "order": "transpose", "same_as": "transpose",
     "text": "input read rows first (left, right, top, bottom): "
             "same effect as transposed"},
    {"id": "clockwise", "order": "clockwise",
     "text": "input read clockwise (top, right, bottom, left)"},
    {"id": "interleaved", "order": "interleaved",
     "text": "input read in pairs (col1top, col1bottom, ...)"},
    {"id": "reverse_top", "reverse": "top",
     "text": "top clues indexed backwards (N - 1 - i)"},
    {"id": "reverse_bottom", "reverse": "bottom",
     "text": "bottom clues indexed backwards (N - 1 - i)"},
    {"id": "reverse_left", "reverse": "left",
     "text": "left clues indexed backwards (N - 1 - i)"},
    {"id": "reverse_right", "reverse": "right",
     "text": "right clues indexed backwards (N - 1 - i)"},
    {"id": "bottom_no_reverse", "view": "bottom_down",
     "text": "bottom clues read top-down"},
    {"id": "right_no_reverse", "view": "right_rightward",
     "text": "right clues read left-to-right"},
    {"id": "only_top_left", "sides": ("top", "left"), "weak": True,
     "text": "only the top and left clues checked"},
    {"id": "only_rows", "sides": ("left", "right"), "weak": True,
     "text": "only the row clues (left, right) checked"},
    {"id": "only_cols", "sides": ("top", "bottom"), "weak": True,
     "text": "only the column clues (top, bottom) checked"},
    {"id": "count_plus1", "counter": "plus1",
     "text": "counter starts at 1 (count = 1, max = 0): +1 everywhere"},
    {"id": "count_minus1", "counter": "minus1",
     "text": "first box not counted (count = 0, or max = line[0]): "
             "-1 everywhere"},
    {"id": "max_one", "counter": "max_one",
     "text": "max starts at 1 with >: one less when a line starts with 1"},
    {"id": "ge_not_gt", "counter": "ge",
     "text": ">= instead of > in the counter (on a Latin line this "
             "counts the same as >)"},
]


def misread_list():
    """[{"id", "text"}] in the contract's order."""
    return [{"id": row["id"], "text": row["text"]} for row in MISREADINGS]


def misread_constraints(rule, n, clues):
    """The constraints a team with misreading `rule` checks, for real
    `clues` (SHAPES order). A side's want may fall outside 1..n (a +1/-1
    counter): no line can then meet it."""
    sides = _team_sides(rule.get("order", "subject"), n, clues)
    reverse = rule.get("reverse")
    view = rule.get("view")
    counter = rule.get("counter", "subject")
    constraints = []
    # 1. the side the team indexes backwards
    if reverse:
        sides[reverse] = sides[reverse][::-1]
    # 2. every checked side, seen the way the team looks at it
    for side in rule.get("sides", ALL_SIDES):
        kind = "col" if side in ("top", "bottom") else "row"
        from_start = side in ("top", "left")
        if side == "bottom" and view == "bottom_down":
            from_start = True
        if side == "right" and view == "right_rightward":
            from_start = True
        for i in range(n):
            want = sides[side][i]
            # 3. the counter: what the team's count == clue means for the
            #    real number of boxes seen
            shift = False
            if counter == "plus1":
                want -= 1
            elif counter == "minus1":
                want += 1
            elif counter == "max_one":
                shift = True
            constraints.append((line_cells(n, kind, i, from_start), want, shift))
    return constraints


def _team_sides(order, n, clues):
    """The 4N numbers split into the team's sides, as its parser reads them."""
    real = {"top": clues[0:n], "bottom": clues[n:2 * n],
            "left": clues[2 * n:3 * n], "right": clues[3 * n:4 * n]}
    if order == "transpose":
        return {"top": real["left"], "bottom": real["right"],
                "left": real["top"], "right": real["bottom"]}
    if order == "swap_top_bottom":
        return {"top": real["bottom"], "bottom": real["top"],
                "left": real["left"], "right": real["right"]}
    if order == "swap_left_right":
        return {"top": real["top"], "bottom": real["bottom"],
                "left": real["right"], "right": real["left"]}
    if order == "clockwise":
        # the input's 2nd block taken as right, 3rd as bottom, 4th as left
        return {"top": real["top"], "right": real["bottom"],
                "bottom": real["left"], "left": real["right"]}
    if order == "interleaved":
        return {"top": clues[0:2 * n:2], "bottom": clues[1:2 * n:2],
                "left": clues[2 * n:4 * n:2], "right": clues[2 * n + 1:4 * n:2]}
    assert order == "subject", "unknown order " + order
    return real
