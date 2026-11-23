# CONTRACT: tool/detect/

## Job
Read a team's C source and name the approach of each part (parse, data,
solve, print), with evidence.

## Owns
`tool/detect/*.py`, `tests/detect/`.

## Publishes
- `detect_team(team_dir_abs, ex_dir) -> detect result` (SHAPES). `ex_dir`
  is the turn-in dir relative to the team ("ex00", "" for the root, or
  None to find it the same way judge does). Never raises: a crash becomes
  `error` + `unrecognized` parts.
- `detect_catalog() -> [catalog entry]` (SHAPES; ids of PLAN.md §7.3, all
  of them, tier 3 included as text).

## Uses
`common/codemap.py` (read-only): `parse_file`, `Parsed`, `Func`,
`build_graph(..., externals="*")`, `attach_authors`. Its gaps are worked
around here (PLAN.md §7.1), never fixed in `common/`.

## Behaviours (one test each; tests use small C snippets written in the test)
- **B1** Each parse / data / print entry and each tier 0–3 solve entry is
  recognised on a minimal sample (one test per id), including `used[]`
  permutation generators (`solve.row_perm`) and count-down odometers
  (`solve.brute16`).
- **B2** `grid[pos / 4][pos % 4]` on `int grid[4][4]` → `data.grid2d`, never
  `data.flat`.
- **B3** `int b[6][6]` with clues on the border → `data.padded`.
- **B4** Digits written through `ft_putnbr` / `ft_putchar` → `print.char`
  (follows calls 1–2 hops).
- **B5** Pre-fill + backtracking → `confidence: "mix"`, `id: solve.prefill`,
  `also` has the search entry.
- **B6** Row clues checked at `col == 3`, column clues only when full →
  `solve.bt_clue_line` with fact `row-end`.
- **B7** A 24-row permutation table → `solve.row_perm`, not `solve.hardcode`.
- **B8** Same solver with functions renamed `f1`, `f2` → same verdict.
- **B9** Unrelated C (a hello world) → all parts `unrecognized`, with `where`.
- **B10** A struct in a `.h`, a global array, `#define N 4` → found in
  `project`.
- **B11** `'1'` inside a comment is not a signal.
- **B12** Every verdict has 2–5 evidence lines (or `where` when
  unrecognized), and the catalog's questions.
- **B13** Garbage input (unbalanced braces, a binary file named `.c`) →
  `error` set, no exception.
- **B14** `project.ask`: `<<` / `>>` lines, complex lines, recursive
  functions with their returns, and `malloc` results never compared with
  NULL (a malloc inside a condition counts as tested).

## Rules here
No printing; no running code; read files only under the team dir.
Signals use structure (shapes, data flow, call graph), names only as
support (B8).

## Done when
`python3 rush01/tests/run.py detect` passes.
