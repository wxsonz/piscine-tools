# CONTRACT: tool/puzzle/

## Job
Know the skyscraper puzzle: solve it, make the test bank, explain wrong
answers.

## Owns
`tool/puzzle/*.py`, `tool/puzzle/bank/*.jsonl`, `tests/puzzle/`.

## Publishes (from `__init__.py`, and only these)
- `puzzle_visible(line) -> int`: boxes seen from the start of the list.
- `puzzle_clues(grid) -> clues`: the 4N clues of a full grid (SHAPES order).
- `puzzle_check(n, clues, grid) -> {"latin": bool, "broken": [...]}`:
  `broken` items are `{"side", "index", "want", "seen"}` (SHAPES run).
- `puzzle_solve(n, clues, limit=2) -> {"solutions": [grid...], "nodes": int}`:
  exact solver, N = 1..9, stops after `limit` solutions.
- `puzzle_make_bank(seed=2026) -> {group: [puzzle entry...]}` (pure).
- `puzzle_save_bank(bank_dir_abs, bank)` / `puzzle_load_bank(bank_dir_abs)
  -> [puzzle entry...]` (the only file I/O here; group order as in SHAPES,
  then id).
- `puzzle_misreadings() -> [{"id", "text"}]`
- `puzzle_diagnose(cases) -> diagnosis` (SHAPES "diagnosis case" in,
  "diagnosis" out).

## Uses
Nothing (stdlib only).

## Misreading ids (PLAN.md §5)
`transpose swap_top_bottom swap_left_right rows_first clockwise interleaved
reverse_top reverse_bottom reverse_left reverse_right bottom_no_reverse
right_no_reverse only_top_left only_rows only_cols count_plus1 count_minus1
max_one ge_not_gt`. A misreading is a rule for how a buggy team reads or
checks the clues; `puzzle_diagnose` solves the puzzle **under** that rule
(exact solver with the rule's clue mapping, sides and counter).

## Behaviours (one test each)
- **B1** The PDF example (`4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2`) has exactly one
  solution: `1 2 3 4 / 2 3 4 1 / 3 4 1 2 / 4 1 2 3`.
- **B2** `puzzle_clues` of that grid gives back the PDF clues.
- **B3** There are exactly 576 4x4 Latin squares; every `ok4`, `slow4`
  entry has 1 solution, every `multi4` ≥ 2, every `nosol4-*` 0.
- **B4** At least 2/3 of `ok4` are asymmetric (top ≠ left or bottom ≠ right),
  all four sides different in at least half.
- **B5** Every `nosol4-deep` entry has all opposite pairs with sum 3..5 and no
  `1 1` pair.
- **B6** `fmt` entries have `clues: null` and `expect: "error"`; all the
  inputs in PLAN.md §5 are present.
- **B7** Same seed → byte-identical bank files; ids stable.
- **B8** `puzzle_solve` finds a correct grid for a 9x9 bank puzzle in < 2 s.
- **B9** Diagnose: grids from a transposed-reading solver on 5 asymmetric
  puzzles → `best.id == "transpose"`.
- **B10** `Error` on valid puzzles where M has no solution, plus M's wrong
  grids elsewhere → `best.id == M` (e.g. `reverse_bottom`). A team printing
  `Error` on every valid puzzle → `best` null, and `extra` lists the
  misreadings that fit (e.g. `bottom_no_reverse`, `count_plus1`): they make
  every valid puzzle unsolvable, so they can't be told apart from "always
  Error" (found by W1, 2026-11-22).
- **B11** Diagnose: only correct grids → `best` null.
- **B12** Diagnose: a grid with values 0..N-1 → `extra` names it.
- **B13** `puzzle_check` on a non-Latin grid → `latin` false; broken clues
  still listed.

## Rules here
Pure: no printing, no clock, no randomness except `random.Random(seed)`.
Bank files are small (< 200 KB total).

## Done when
`python3 rush01/tests/run.py puzzle` passes.
