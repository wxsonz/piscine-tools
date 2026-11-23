# rush01 tool: plan

Status: **v3** (2026-11-22, Sunday). v1 and v2 were reviewed by Gemini
(`PLAN_REVIEW_ANTIGRAVITY.md`, `PLAN_REVIEW_V2_ANTIGRAVITY.md`); the reply to
round 1 is `PLAN_REPLY_TO_GEMINI.md`. v3 takes round 2 (§13 lists what came
from where) and lays the work out for parallel workers (§10).

How code is written here: **`AGENTS.md`** (the project rules, built on the
user's Code Book). Read it before this plan if you write code.

Subject: `~/Documents/42piscine-2026/rush01.pdf` (v8.0, the 4x4 skyscraper
puzzle; a copy in `rush01/rush01.pdf`, not committed).

**Deadline: Monday 2026-11-23** (the evaluations). §10 "before Monday" must
work by then. Preset demos (animations, 3D presets, library page) come
**after everything else**.

## 1. Goal

A tool for the **evaluator** (a tutor at 42 Bangkok, Batch #20) that reads a
team's rush01 code and says, in plain words, **which common approach the
team used** for each part of the program:

1. **Parsing**: how argv[1] becomes clues
2. **Data structure**: how the grid and clues are stored
3. **Solving**: how the grid gets filled
4. **Printing**: how the answer (or `Error`) gets written

Each part shows the verdict, the lines that prove it, and defense questions.
A **3D skyscraper view** shows the team's real output as blocks. Later, a
**preset animation** per approach shows how that approach works.

It also builds and runs the binary on a puzzle bank (no gdb) to check it
works, to explain failures ("8 of 9 failures fit: bottom clues read
top-down"), and to back up the solving verdict with timings.

### Non-goals
- No gdb / tracing. Presets are labelled "how this approach works (preset),
  not their code".
- No grading score. It reports facts; the evaluator decides.
- No "suspicion" heuristics. Authorship is plain facts only.
- No sandbox (timeouts only, like rush00).

## 2. Constraints

- Python 3.10 stdlib only; plain JS/CSS; no frameworks, no new deps.
- Runs on the 42 iMac (Ubuntu 22.04, no sudo, ~3 GB home) and the laptop.
  Needs `cc`; `norminette`, `valgrind`, the ASan runtime are optional (each
  check is skipped with a note when missing).
- **Truth first**: a label or picture says what the code really does. When
  unsure: "unsure" / "unrecognized", never a guess.
- No ligatures in code fonts; fonts ship in `www/fonts/`.
- Look: the notebook-game style of `rush00/tool/www/notebook.css`.
- `rush01/repo/` and `rush01/reports/` are never committed.
- **Don't break rush00 before Monday**: nothing in `common/` or `rush00/`
  changes. codemap gaps are worked around inside `rush01/tool/detect/`.

## 3. The subject, as the tool understands it

- Turn-in: `ex00/`, all files needed (`*.c`; `*.h` is normal); built with
  `cc -Wall -Wextra -Werror -o rush01 *.c` inside `ex00/`. Flagged (note, not
  fail): `*.o`, binaries, `.DS_Store`, extra directories, stray test files,
  files outside `ex00/`.
- Allowed functions: `write`, `malloc`, `free`.
- Input: one argument, 16 numbers `'1'..'4'`, single spaces, order
  `col1top..col4top col1bottom..col4bottom row1left..row4left
  row1right..row4right`.
- Output: the first solution found, N lines of `d d d d\n`.
- Error (bad input or no solution): `Error\n`.
- Bonus: sizes up to 9x9 (4N numbers, values 1..N).

Open points, reported (the evaluator decides):
- `Error` on stderr → pass + orange note.
- Leading/trailing spaces, tabs, `\n` inside the argument → the bank expects
  `Error`; accepting them is a fail **with the reason shown**.
- Several solutions: any correct grid passes; the tool notes which one.
- Exit code: recorded, never judged.

All of this lives in `rush01/tool/subject.txt`, so it can change on the day
without touching code.

## 4. Layout (one folder, one job: SHAPE-1)

```
rush01/
  AGENTS.md  CLAUDE.md  README.md  PLAN.md  decisions/
  tool/
    rush01            CLI launcher (3 lines)
    rush01_wiring.py  the wiring file + CLI: reads subject.txt, calls the
                      folders in order, writes reports, prints. No rules.
    subject.txt
    puzzle/           CONTRACT.md: solve, make and diagnose puzzles (pure)
      bank/           the generated puzzle bank (committed: ours)
    judge/            CONTRACT.md: build a team and judge it against the bank
    detect/           CONTRACT.md: name the approach of each part (static)
    web/              CONTRACT.md: dashboard + team page server, www/
  tests/
    run.py            THE check command (PROOF-1)
    corpus/           CONTRACT.md: generator of the fake teams + expect/
  repo/  reports/     (not committed)
```

Each folder is a Python package. Others import **only the names its
`__init__.py` exports**, which are exactly the ones its `CONTRACT.md`
publishes (SHAPE-3). Data between folders is plain dicts that dump to JSON;
the shapes are in the contracts (FLOW-6, FLOW-9).

Reused, read-only: `common/codemap.py` (functions, calls, outline, call
graph with `externals="*"`, `source_html`, `function_card`, page chrome,
`attach_authors`). From rush00, small pieces are **copied** (clone, teams
file, `run_capped`, `find_ex_dir`, the server skeleton), never imported.

### CLI
```sh
./rush01/tool/rush01 serve [--port 4243] [--open]   # dashboard (rush00 keeps 4242)
./rush01/tool/rush01 <team dir | git URL>           # evaluate one, write report
./rush01/tool/rush01                                # every team in repo/
./rush01/tool/rush01 explain <team>                 # terminal: 4 verdicts + evidence
./rush01/tool/rush01 puzzles                        # (re)generate the bank
./rush01/tool/rush01 solve "4 3 2 1 ..."            # reference answer(s)
python3 rush01/tests/run.py [--quick] [--no-browser] # check everything
```

## 5. `puzzle/`: solvers, bank, diagnosis

Solvers:
- **exact**: bitmasks + clue pruning, N = 1..9, up to 2 solutions + nodes.
- **naive**: fill everything, check at the end (4x4 only).
- **piscine**: per-cell backtracking, row/col uniqueness per placement, clues
  at the end (the common student solver; ranks how slow a puzzle is for
  real student code).

4x4: enumerate all 576 Latin squares → clues → exact unique / multi sets.
5..9: random Latin square (seeded) → clues; no uniqueness needed for 8, 9.

### The bank (`puzzle/bank/<group>.jsonl`)

| group | what | expect | timeout |
|---|---|---|---|
| `ok4` | the PDF example + ~10 unique 4x4, **most asymmetric** (top ≠ left, bottom ≠ right, all sides differ) | grid | 2 s |
| `multi4` | 2+ solutions | any correct grid | 2 s |
| `nosol4-easy` | impossible on one line: an opposite pair `1 1`, a pair summing > N+1 | `Error` | 2 s |
| `nosol4-deep` | every opposite pair locally fine (sum 3..5, no `1 1`), impossible globally; highest `piscine` nodes | `Error` | 5 s |
| `slow4` | unique, highest `piscine` nodes (mostly 2s and 3s) | grid | 5 s |
| `fmt` | see below | `Error` | 2 s |
| `bonusN` | N = 5..9 valid / multi / impossible; count not 4N (18), value > N, N = 10 (40 numbers) | grid / `Error` | 10 s |
| `small` | N = 1, 2, 3 | info only | 2 s |

The PDF example is symmetric (top == left, bottom == right), so a solver
with rows and columns swapped passes it. That's why `ok4` is mostly
asymmetric.

`fmt`: `""`, `"1"`, `"4 3"`, 15 / 17 numbers, `0`, `5`, `/`, `:`, `12`,
`04`, letters, double space, leading space, trailing space, tab, `\v`, `\n`
inside, trailing `\n`, `-1`, `+1`, no argument, two arguments.

### Diagnosis: both directions

A **misreading** is a rule that turns the real clues into the clues a buggy
team works with. For each misreading M, `puzzle/` rebuilds the misread
puzzle and solves it with the exact solver:
- the team printed a **wrong grid** and it satisfies M's clues → M explains it;
- the team printed **`Error` on a valid puzzle** and M's puzzle has no
  solution → M explains it;
- the team printed a **correct grid** that breaks M's rules → M is
  contradicted (a team with M couldn't have printed it).

Votes add up over the whole bank: **"8 of 9 failures fit: rows and columns
swapped"**. Only a misreading that explains ≥ 2 failures, is contradicted by
none and isn't tied is reported as `best`; otherwise `best` is null and
`extra` lists what fits. Some misreadings (`bottom_no_reverse`,
`right_no_reverse`, `count_plus1`, and on every 4x4 also `swap_top_bottom`,
`swap_left_right`, `clockwise`, `count_minus1`) make **every** valid puzzle
unsolvable: such a team prints `Error` everywhere and can't be told apart
from "always Error", so they are only ever listed as fits, never named as
the cause. `ok4` / `multi4` include puzzles where the other misreadings give
a wrong grid instead of `Error`, so those can be named.

Misreadings:
- transposed (rows ↔ columns) · top ↔ bottom · left ↔ right
- rows before columns in the input order
- clockwise order (top, right, bottom, left) · interleaved pairs
  (`col1top, col1bottom, ...`)
- one side indexed backwards (`3 - i`), for each side
- bottom clues read top-down, right clues read left-to-right (no reversal)
- only some sides checked (top+left only, rows only, columns only)
- counter bugs: `count = 1, max = 0` (+1 everywhere), `max = line[0]`,
  `count = 0` (−1 everywhere), `max = 1` with `>` (−1 when the line starts
  with 1), `>=` instead of `>`

Also reported (not misreadings): heights 0..3 printed (forgot `+ 1`); a
partial grid printed before `Error`; `Error` printed after a grid.

## 6. `judge/`: build, checks, runs

1. Find `ex00/`; list missing / flagged files (§3).
2. Build with the official command in a temp copy. Failure → no runs, but the
   report still has everything static (detect still runs).
3. **Forbidden functions** (on the **linked binary**, `@GLIBC_*` stripped):
   1. every undefined symbol in `nm -u ./rush01`:
      allowed (`write malloc free` from subject.txt) or CRT/runtime
      (`__libc_start_main`, `__cxa_finalize`, `__gmon_start__`, `_ITM_*`,
      `__stack_chk_fail`, `_GLOBAL_OFFSET_TABLE_`) → OK;
      compiler aggregate ops (`memset memcpy memmove bcmp`) **not** called in
      source → note "compiler-generated (e.g. `= {0}`)";
      **anything else → forbidden** (catches `puts` from a folded `printf`,
      `__ctype_b_loc` from `isalpha`, `atoi`, `calloc`, `exit`...).
   2. every call in source to a name the team doesn't define and that isn't
      allowed → forbidden (catches macros and folded builtins by their
      source name).
   3. a team function sharing a libc name (`strlen`) → fine; note "defines
      own `strlen`".
   `#include <stdio.h>` / `<string.h>` → warning; `<stdlib.h>` → note only.
4. Norminette on `*.c` + `*.h`, flags from subject.txt. Skipped if missing.
5. Run the bank: per-group timeout, output cap 1 MB; record stdout, stderr,
   exit code / signal, wall time.
6. **Sanitizer build** (`-g -fsanitize=address,undefined`) on 3 paths: one
   `ok4`, one `nosol4`, and `""`, `"1"`, `"4 3"`. LeakSanitizer runs with it.
   If LSan dies with "LeakSanitizer has encountered a fatal error" (ptrace
   blocked), retry with `ASAN_OPTIONS=detect_leaks=0`, then use `valgrind`
   for leaks if present. ASan runtime missing → skipped with a note.
7. **Judge** each run:
   - valid puzzle: N lines of N digits, single spaces, `\n` at the end, no
     trailing space, nothing else on stdout; Latin square; all 4N clues.
     Show each broken clue (seen vs expected).
   - error puzzle: exactly `Error\n` on stdout → pass; stderr → pass + note;
     anything else → fail. Extra stderr → note; extra stdout → fail.
   - timeout / crash → fail with the reason.
8. Diagnosis over all runs (via `puzzle/`, §5).
9. Summary per group, slowest puzzle, timing ratio `slow4` / `ok4`.

## 7. `detect/`: the approach per part

### 7.1 codemap gaps (verified) and the workarounds

| gap | workaround |
|---|---|
| no `typedef struct`, no globals; `#define` lines blanked | parse `*.h` too; scan depth-0 tokens for globals and structs; read defines from raw lines where `kinds == 'p'` |
| string/char contents blanked in `clean` / `toks` | extract literals from `P.src` where `P.kinds == 's'` |
| `Func.chars` counts literals inside comments | use the filtered extraction, not `fn.chars` |
| no `+= -= *= \|= &= << >>` tokens | match token bigrams or statement text |
| `build_graph` default externals | `externals="*"` |

### 7.2 How it works

1. Read every `.c` / `.h` → functions, call graph, globals, structs,
   defines, literals (with the workarounds).
2. **Roles** first: touches argv → parser; recursive (self call or a cycle)
   or the try-1..N shape → solver; writes digits → printer; `"Error\n"` →
   error path. Signals **follow the call graph** 1–2 hops (Norm splits logic
   into 25-line functions; `ft_putnbr` / `ft_putchar` wrappers).
3. **Features**: index steps (`i += 2`, `i * 2`), compares with `' '` `'1'`
   `'4'` `'0'` `'9'`, `- '0'`, `* 10 +`, length checks (`31`, `16`, `4 * n`),
   declarations, index shapes, recursive-call argument shapes, resets to 0
   after a failed try, bit ops, a 24-row table, running `max` + `count++`,
   write shapes.
4. **Rules**: each catalog entry scores features → (score, evidence), with
   required, supporting and ruling-out signals.
5. **Verdict**: `clear` / `likely` / `mix` (two entries, e.g. prefill + the
   search after it) / `unrecognized` ("look at `fn()` in `file.c`"). Always
   2–5 evidence lines.
6. **Runtime cross-check** (done by the wiring, from judge's timing ratio): a
   clash lowers the confidence, never flips the verdict.

### 7.3 The catalog

Each entry: id, part, tier (solve), name, 2–3 line explanation, signals,
**1–3 defense questions**, demo id (after Monday).

**Parsing**
| id | name | key signals |
|---|---|---|
| `parse.fixed` | Fixed positions | `str[i * 2]` / `i += 2`; length 31 (`8n - 1`); digits even, spaces odd |
| `parse.scan` | Scan and count | one pass: digit → store + count, space → skip; `count == 16` |
| `parse.split` | Split into words | `ft_split`-like (malloc of words), length-1 + range check |
| `parse.atoi` | atoi per token | `res * 10 + (c - '0')`; range check after; often accepts `04` |
| `parse.fsm` | State machine | explicit state variable |
| `parse.none` | No real validation | stores without checking (confirmed by `fmt` runs) |

Facts: `argc != 2` check; N fixed or from the count; a `'\0'` check before
indexing (confirmed by the sanitizer).

**Data structure**
| id | name | key signals |
|---|---|---|
| `data.grid2d` | 2D array | `int grid[4][4]` / `[9][9]`; indexed `[r][c]` **or `[pos / n][pos % n]`** |
| `data.padded` | Board with a clue border | `[6][6]` / `[n + 2][n + 2]`; clues in row 0, row n+1, col 0, col n+1; puzzle in `[1..n][1..n]` (like the PDF's drawing) |
| `data.malloc2d` | malloc'd `int **` | malloc of N pointers then N rows |
| `data.flat` | Flat 1D array | **1D declaration** (`int grid[16]`, `int *grid` + malloc) indexed `[r * n + c]` or `[pos]` |
| `data.char` | char grid | holds `'1'..'4'` |
| `data.struct` | Struct board | `typedef struct` (in a `.h`) with n, grid, clues |
| `data.bits` | Bitmask used-sets | `row_used[r]`, `1 << v` |
| `data.cand` | Candidates per cell | `cand[r][c]` mask / `[n][n][n]` |

Clue layout, with the team's **index mapping** (`clue[8 + r]` = row r
left): flat `[16]` · `views[4][4]` · four arrays · in the struct · in the
padded border. Facts: globals vs passed; malloc freed or not.

**Solving**
| tier | id | name | key signals |
|---|---|---|---|
| 0 | `solve.hardcode` | Hardcoded answers | compares argv with fixed strings / prints a fixed grid. **Not** a 24-perm table |
| 0 | `solve.brute16` | Every combination of all cells | 4^16 counter / deep helper nesting; check at the end |
| 0 | `solve.brute_perm_loops` | Every combination of row orders | 24 perms × 4 rows, check at the end |
| 1 | `solve.bt_end` | Backtracking, check at the end | recursive per cell, checks only when full |
| 1 | `solve.bt_unique` | + row/col check per placement | `is_valid(r, c, v)` before placing; clues at the end |
| 1 | `solve.bt_clue_line` | + clue check when a line is full | **row-end or col-end or both** (fact chip says which) |
| 1 | `solve.bt_iter` | Iterative backtracking | no recursion; position counter going back |
| 2 | `solve.row_perm` | Row permutations | 24 perms (table or generated), one per row, columns checked |
| 2 | `solve.prefill` | Pre-fill rules, then search | clue 4 → 1..N; clue 1 → N at the edge; pair N+1. **Always reported with the search after it** (`mix`) |
| 2 | `solve.cands` | Candidate lists | per-cell values, removed as cells are placed |
| 3 | `solve.bits` `solve.partial_prune` `solve.mrv` `solve.propagate` `solve.line_solver` `solve.dlx` | (catalog text now; rules if cheap; after Monday otherwise) | |

Idioms named explicitly: `pos` 0..15 with `pos / 4`, `pos % 4`, `pos + 1`;
`(row, col)` with `(row, col + 1)` / `(row + 1, 0)`.
Facts: visibility counter shape; what happens with no solution.

**Printing**
| id | name | key signals |
|---|---|---|
| `print.char` | One write per char | `write(1, &c, 1)` with `v + '0'`; also through `ft_putchar` / `ft_putnbr` wrappers |
| `print.line` | Line buffer | `char line[8]` / `2n`, one write per row |
| `print.board` | Whole-board buffer | one buffer, one write |
| `print.putstr` | putstr of a built string | builds a string, `ft_putstr` |

Facts: `Error` fd and text; trailing space / final newline (from runs);
output before solving finished.

**Project strip**: forbidden (with compiler-generated notes) · norm · flagged
files · globals · memory never freed · bonus attempted · sanitizer findings ·
authorship facts (`attach_authors`: % lines per teammate, commit count).

## 8. `web/`: the pages

**Before Monday** (`team.html`): top (name, build, hearts: builds ·
forbidden-free · norm; project strip) → four cards Parse · Data · Solve ·
Print (verdict, tier badge, confidence, where, 2–5 evidence lines, fact
chips, folded defense questions) → run table by group + the diagnosis line →
**3D view of their real output** (`sky3d.js`, CSS 3D, no libs: blocks by
height, clues on the base, drag to rotate, top/front/iso; click a clue →
visible blocks teal, hidden faded, count shown, orange if wrong; puzzle
picker). Built last; fallback is a 2D grid with the same sightlines. →
source + call graph (codemap).

Dashboard (`dash.html`): rush00's, adapted: team cards with the 4 verdict
chips + hearts; drop folders / paste URL; auto-evaluate on change.

**After Monday**: `demos.js` (one step player, one renderer, small
generators per entry), 3D presets, ▶ on each card, `library.html`, compare.

## 9. `tests/`: the check and the corpus

`python3 rush01/tests/run.py` is the one check (PROOF-1). It runs:
1. structure checks: every folder in §4 has `CONTRACT.md`; no folder imports
   another folder's inner module (only `from <folder> import <published>`);
   no `print(` in `puzzle/`, `judge/`, `detect/` (CODE-11).
2. `puzzle/` tests (from its contract behaviours).
3. `judge/` + `detect/` on every corpus team vs `tests/corpus/expect/`.
4. `web/` pages load without JS errors (skipped with `--no-browser`, and by
   default if node/chromium are missing).
`--quick` skips the slow groups.

**Corpus before Monday** (~18 teams, written by `tests/corpus/gen.py` into
`rush01/repo/`; generator committed, teams not). **Composite**: each team
covers one entry per part, so ~13 teams cover the matrix:

| team | parse | data | solve | print |
|---|---|---|---|---|
| `c01` | fixed | grid2d (pos idiom) | bt_unique | char |
| `c02` | scan | grid2d (row/col idiom) | bt_clue_line (both) | line |
| `c03` | split | malloc2d | bt_clue_line (row-end only) | board |
| `c04` | atoi | struct in a `.h` | prefill + bt_unique | putstr |
| `c05` | scan | flat `[16]` | bt_end | char via `ft_putnbr` |
| `c06` | fixed | padded `[6][6]` | bt_iter | line |
| `c07` | scan | grid2d | row_perm (table) | char |
| `c08` | scan | grid2d + cands | cands | board |
| `c09` | none | grid2d | brute_perm_loops | char |
| `c10` | fixed | grid2d | hardcode (PDF example only) | char |
| `c11` | atoi (bonus N) | malloc2d | bt_clue_line | line |
| `c12` | scan | flat | bt_unique, `Error` on fd 2 | char |
| `c13` | odd: `f1`, `f2`, globals | grid2d | bt_unique | char |

Day-one cases: `d1` forbidden (`printf` + `atoi`) · `d2` `= {0}` (must
**not** be flagged) · `d3` build failure · `d4` files at repo root, no `ex00/`
· `d5` malloc before validation, no free on error (leak).
Bugs: `b1` transposed clue order · `b2` bottom read top-down (→ `Error` on
valid puzzles) · `b3` counter `count = 1` · `b4` reads past `'\0'` on short
input · `b5` infinite loop on no solution · `b6` trailing space.

`tests/corpus/expect/<team>.txt`: plain `key = value` lines (format in the
corpus contract).

Real code: `~/backup_42/42piscine/rush01` is run through as soon as judge +
detect exist; its expected verdict is written by hand after reading it.

## 10. Milestones and the work split

**Before Monday**: M1 puzzle + judge + CLI text · M2 detect + corpus + check
· M3 web (3D last). **After Monday**: M4 presets / library / compare · M5
fix the codemap gaps in `common/`, tier 3, bonus polish, tuning on real code.

**Parallel work** (decision 002). The lead writes the top first: this plan,
`AGENTS.md`, every `CONTRACT.md`, `subject.txt`, the wiring file
`tool/rush01_wiring.py`, and `tests/run.py`. Then one worker per folder, each owning
only its folder:

| worker | OWN | uses (published only) |
|---|---|---|
| W1 | `tool/puzzle/` | — |
| W2 | `tool/judge/` | `puzzle` (check + diagnose), `common/codemap.py` |
| W3 | `tool/detect/` | `common/codemap.py` |
| W4 | `tests/corpus/` | `puzzle` (to self-check the teams it writes) |
| W5 | `tool/web/` | the report shape (wiring contract), `common/codemap.py` |

A worker that needs a published thing that isn't built yet codes against the
contract. A contract that looks wrong → stop and tell the lead (PLAN-8);
never change another folder. The lead integrates and runs the check.

## 11. Known risks

- Static detection is heuristic → structure over names, `mix` /
  `unrecognized`, evidence always shown, calibrated on real code.
- The corpus shares its writer's habits → real code is the real test.
- Monday time → M1 is the safety net; the 3D view drops to 2D first; then
  tier 3 rules; then the browser check.
- Parallel workers drift → contracts first, OWN folders, one check.
- codemap is a tokenizer → odd code falls to `unrecognized`, never a crash.
- Timing noise → ratios only. Untrusted code → timeouts, cap, temp dir.
- CSS 3D at 9x9 (81 boxes) → check on the iMac's browser.

## 12. Decisions

1. `Error` on stderr: pass + note. 2. Timeouts 2 / 5 / 10 s. 3. Defense
questions in M2. 4. Port 4243. 5. Calibrate on the real project early.
More in `decisions/`.

## 13. Where v3 came from (round 2)

From Gemini round 2: `data.flat` signal fixed (`[pos / n][pos % n]` is
2D) · `data.padded` · `ft_putnbr`/`ft_putchar` wrappers · `bt_clue_line`
row-end/col-end · prefill reported with its search · forbidden check on the
linked binary + allowlists + source calls · more misreadings · composite
corpus + 5 day-one cases · LSan retry. From Claude: diagnosis in both
directions (most misreadings make `Error` on valid puzzles, not a wrong
grid) with votes across the bank · folder layout per the Code Book.
