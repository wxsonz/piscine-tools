# SHAPES: the data that crosses folders

Every dict passed between folders, in one place (SHAPE-4, FLOW-9). All of
them dump to JSON as they are (FLOW-6). Writer = the only folder that builds
it (FLOW-1). Changing a shape: change this file first (AGENTS.md rule 10).

## Conventions

- **N**: the grid size (4 for the mandatory part, 1..9 in general).
- **clues**: a list of 4N ints, **in the input order of the subject**:
  `clues[0:N]` top (col 0..N-1, looking down) · `clues[N:2N]` bottom (col
  0..N-1, looking up) · `clues[2N:3N]` left (row 0..N-1, looking right) ·
  `clues[3N:4N]` right (row 0..N-1, looking left).
- **grid**: a list of N rows, each a list of N ints; `grid[r][c]`, row 0 at
  the top, col 0 on the left.
- **side** names: `"top" "bottom" "left" "right"`.
- Times are ints in ms (`_ms`, FLOW-5). Paths in shapes are relative to the
  team folder unless named `*_abs`.

## subject (writer: `tool/rush01`, from `tool/subject.txt`)
```json
{"name": "rush01", "turn_in_dir": "ex00", "binary": "rush01",
 "build": ["cc", "-Wall", "-Wextra", "-Werror", "-o", "rush01"],
 "sizes": [4], "bonus_sizes": [5, 6, 7, 8, 9],
 "allowed": ["write", "malloc", "free"],
 "error_text": "Error\n", "error_on_stderr": "note",
 "norm_flags": ["-R", "CheckForbiddenSourceHeader"],
 "sheet_binary": "rush-01"}
```
`sheet_binary`: the name the eval sheet runs (`./rush-01`); the tool builds
`binary` as the subject says and shows a note when they differ.
`build` is completed by judge with the sorted `*.c` of the turn-in dir.
`error_on_stderr`: `"note"` (pass + note) or `"fail"`.

## puzzle entry (writer: `puzzle/`; one JSON object per line in `bank/<group>.jsonl`)
```json
{"id": "ok4-03", "group": "ok4", "n": 4,
 "argv": ["4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2"],
 "clues": [4, 3, 2, 1, 1, 2, 2, 2, 4, 3, 2, 1, 1, 2, 2, 2],
 "expect": "grid", "timeout_ms": 2000, "note": "PDF example (symmetric)"}
```
- `argv`: the arguments after the program name (`[]` = no argument, two
  items = two arguments).
- `n`: the size, or `null` when the input is no valid size (e.g. 18
  numbers).
- `clues`: the real clues, or `null` when the input is malformed (`fmt`) or
  isn't a valid size.
- `expect`: `"grid"` (any correct grid passes), `"error"` (`Error`), or
  `"info"` (recorded, never pass/fail: group `small`).
- Groups: `evalsheet ok4 multi4 nosol4-easy nosol4-deep slow4 fmt bonusN small`
  (PLAN.md §5). Ids are `<group>-NN`, stable across regenerations with the
  same seed.

## diagnosis case (writer: `judge/`, input of `puzzle_diagnose`)
```json
{"id": "ok4-03", "n": 4, "clues": [4, 3, "..."],
 "outcome": "grid", "grid": [[1, 2, 3, 4], "..."], "correct": false}
```
`outcome`: `"grid"` (stdout parsed as a Latin square of size N) or
`"error"` (printed `Error`). Cases with other outcomes (crash, timeout,
garbage) are not passed in. `correct`: the grid satisfies the real clues.

## diagnosis (writer: `puzzle/`)
```json
{"best": {"id": "bottom_no_reverse", "text": "bottom clues read top-down",
          "explains": 8, "failures": 9, "contradicted": 0},
 "all": [{"id": "...", "text": "...", "explains": 0, "failures": 9, "contradicted": 2}],
 "extra": ["heights 0..3 printed (forgot + 1)"]}
```
`best` is `null` unless a misreading explains ≥ 2 failures and is
contradicted by none (PLAN.md §5). `all` is sorted by `explains`, highest
first.

## run (writer: `judge/`)
```json
{"id": "ok4-03", "group": "ok4", "argv": ["..."], "expect": "grid",
 "stdout": "1 2 3 4\n...", "stderr": "", "exit": 0, "signal": null,
 "timed_out": false, "time_ms": 3,
 "verdict": "pass", "reasons": [], "notes": [],
 "grid": [[1, 2, 3, 4], "..."],
 "broken": [{"side": "top", "index": 0, "want": 4, "seen": 3}]}
```
- `stdout` / `stderr` are capped (1 MB) and decoded with
  `errors="replace"`; `exit` is null when killed; `signal` is a name
  (`"SIGSEGV"`) or null.
- `verdict`: `"pass" | "fail" | "info"`. `reasons`: why it failed, plain
  words. `notes`: pass-with-note items (e.g. `Error` on stderr).
- `grid`: the parsed output when it parses as N rows of N ints, else null.
  `broken`: the clues the grid breaks (empty when correct or no grid).

## judge result (writer: `judge/`)
```json
{"ex_dir": "ex00", "built": true, "build_log": "",
 "files": {"sources": ["ex00/main.c"], "headers": ["ex00/rush.h"],
           "flagged": [{"path": "a.out", "why": "binary in the turn-in"}],
           "no_ex_dir": false},
 "forbidden": {"names": [{"name": "printf", "where": "source", "file": "ex00/main.c", "line": 12}],
               "notes": ["compiler-generated: memset (e.g. = {0})", "defines own strlen"]},
 "norm": {"ran": true, "ok": false, "errors": [{"file": "ex00/main.c", "line": 3, "text": "..."}], "note": ""},
 "sanitizer": {"ran": true, "findings": [{"case": "fmt-01", "kind": "heap-buffer-overflow", "text": "..."}], "note": ""},
 "runs": ["<run>", "..."],
 "groups": {"ok4": {"pass": 10, "fail": 1, "info": 0}},
 "timing": {"slowest_id": "slow4-02", "slowest_ms": 840, "slow4_over_ok4": 31.5},
 "diagnosis": "<diagnosis>",
 "malloc_fail": {"ran": true, "mallocs": 3, "crashes": [1],
                 "tries": [{"nth": 1, "outcome": "crash", "signal": "SIGSEGV", "stdout": ""}],
                 "note": ""},
 "stops": [{"key": "norm", "level": "stop", "text": "6 norm error(s)",
            "sheet": "Norm error: evaluation stops."}],
 "bonus": {"sizes": {"5": "pass", "6": "fail"}, "largest_n": 5,
           "counted": false, "note": "not counted: ..."},
 "tools": {"cc": true, "norminette": true, "valgrind": false, "asan": true}}
```
When the build fails: `built` false, `runs` empty, `diagnosis` null,
`malloc_fail.ran` false; the rest is filled.
- `malloc_fail`: the team's own `malloc` calls fail one at a time (the Nth,
  N = 1..`mallocs`, capped) on the PDF example. `outcome`: `"crash"`,
  `"timeout"` or `"exit N"`; `crashes` lists the N that crashed or hung.
- `stops`: the eval sheet's stops, in its order. `key`: `no_ex_dir
  no_sources norm files build forbidden eliminatory`. `level`: `"stop"`
  (the sheet ends the evaluation or gives no points) or `"check"` (the
  evaluator decides). `sheet`: the rule's words.
- `bonus`: `sizes` per bonus N (keys are strings: JSON); `largest_n` is the
  biggest N with every bonus puzzle of 5..N passing; `counted` only when
  no stop and every mandatory run passes. `where` is `"binary"` (found by `nm -u`) or `"source"`.

## detect result (writer: `detect/`)
```json
{"parts": {"parse": "<verdict>", "data": "<verdict>",
           "solve": "<verdict>", "print": "<verdict>"},
 "project": {"globals": [{"file": "ex00/g.c", "line": 3, "text": "int g_grid[4][4];"}],
             "structs": [{"file": "ex00/rush.h", "line": 5, "name": "t_board"}],
             "defines": [{"file": "ex00/rush.h", "line": 3, "name": "N", "value": "4"}],
             "functions": 14, "longest": {"name": "solve", "file": "ex00/solve.c", "lines": 24},
             "never_freed": false, "bonus": false,
             "authors": {"alice": 62, "bob": 38}, "commits": 7,
             "ask": [{"kind": "shift", "file": "ex00/check.c", "line": 12,
                      "text": "used |= 1 << v;", "why": "bit shift <<: ask what it is"}]},
 "error": null}
```
verdict:
```json
{"id": "solve.bt_unique", "name": "Backtracking + row/col check per placement",
 "tier": 1, "confidence": "clear", "also": [],
 "where": [{"file": "ex00/solve.c", "func": "solve", "line": 10}],
 "evidence": [{"file": "ex00/solve.c", "line": 18, "text": "if (is_valid(g, pos, v))",
               "why": "checks the row and column before placing"}],
 "facts": [{"key": "clue_check", "text": "clues checked only when the grid is full"}],
 "explain": "Tries 1..4 in each cell in order ...",
 "questions": ["What happens when no value fits a cell?"]}
```
- `confidence`: `"clear" | "likely" | "mix" | "unrecognized"`. With `mix`,
  `id` is the main entry and `also` lists the others. With
  `unrecognized`, `id` is null, `name` is "unrecognized", and `where` points
  at the function to look at.
- `project.ask`: lines to ask about (the sheet's "Explanation"); `kind`
  in this order: `shift` (`<<` `>>`), `complex` (many operators or a call
  in a call), `recursion` (with its return lines), `malloc` (a result never
  compared with NULL in its function, or returned to the caller).
- `tier` is only set for `solve.*`. `authors` / `commits` are null when the
  folder is not a git repo. `error`: a message when detection crashed (the
  parts are then `unrecognized`); never raises.

## catalog entry (writer: `detect/`)
```json
{"id": "parse.scan", "part": "parse", "tier": null, "name": "Scan and count",
 "explain": "...", "questions": ["..."], "demo": "parse_scan"}
```
Ids are exactly those of PLAN.md §7.3.

## report (writer: `tool/rush01`; `reports/<team>.json`)
```json
{"team": "c01", "team_dir_abs": "/.../rush01/repo/c01",
 "made_at": "2026-11-23T09:12:00", "subject": "<subject>",
 "judge": "<judge result>", "detect": "<detect result>",
 "cross_check": ["solving reads as tier 1 but slow4 is 40x ok4: check"]}
```

## corpus expect (writer: `tests/corpus/`; `expect/<team>.txt`)
Plain `key = value` lines; `#` comments. Only the keys present are checked.
```
parse = parse.scan
data = data.grid2d
solve = solve.bt_unique          # main id; "mix" teams: solve = solve.prefill + solve.bt_unique
print = print.char
built = yes                      # yes | no
ex_dir = yes                     # yes | no
forbidden = none                 # none | space-separated names
group.ok4 = pass                 # pass (all pass) | fail (at least one fails)
diagnosis = none                 # none | a misreading id
sanitizer = clean                # clean | finding
```
