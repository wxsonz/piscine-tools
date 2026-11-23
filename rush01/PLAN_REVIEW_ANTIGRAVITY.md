# Review & Useful Additions for `PLAN.md` (rush01 Tutor Tool)

> **Reviewed by:** Antigravity (Gemini)  
> **Date:** 2026-11-22  
> **Inputs verified:** `rush01/PLAN.md`, `rush01/rush01.pdf` (v8.0), `common/codemap.py`, `HANDOFF.md`

Overall, `PLAN.md` is a strong, well-scoped architecture that fits the `rush00` ecosystem cleanly (stdlib-only Python, truth-first verdicts, rule-based judging instead of golden diffs, and `subject.txt` configurability).

Below are the **concrete technical gotchas**, **missing evaluation edge cases**, and **Monday-deadline priority cuts** found by cross-checking `PLAN.md` against `common/codemap.py` and `rush01.pdf`.

---

## 1. Monday Timeline & Budget Strategy (Keep Preset Demos, Save Budget Elsewhere)

The **preset animations (`demos.js`) + library page** are a core feature (for other tutors and future batches), so **keep them in scope**! To stay within Monday's deadline and the tight usage budget, save tokens on the *expensive low-ROI parts* (writing Norm-clean C corpus fixtures for rare Tier 3 algorithms) while making `demos.js` super modular and cheap to write:

| Keep / Pull Forward for Monday | Smart Cost-Saving Adjustments |
|---|---|
| **M1:** `ref.py`, puzzle bank, `runner.py`, CLI summary | — |
| **Lean M2:** Parse + Data + Print + **Tier 0–2** solving detectors + bug flags | **Skip synthetic Norm-C corpus teams for rare Tier 3 solvers** (`dlx`, `line_solver`, `propagate`, `mrv`) in `gen_corpus.py` — writing valid 42-Norm C for them burns lots of tokens for little Monday payoff (keep lightweight detectors/JS library demos if desired) |
| **Pull up from M5 → M2/M3:** **Defense questions** per verdict (cheap static text in `catalog.py`, huge live-defense value) | — |
| **M3:** `team.html` + run table + **3D skyscraper view** (clickable clue sightlines + their real output) + source/call graph | — |
| **M4 (Keep!):** **Preset animations (`demos.js`) + library page** — design ONE shared step player + tiny parameterized JS generators (~15–30 lines each), shipping Parse/Data/Print + Tier 0–2 demos first so it's tutor-ready before Monday, then adding Tier 3 / compare mode cleanly | Avoid duplicate rendering code across demos; reuse the exact same 3D/grid canvas + step tape (`place`, `reject`, `backtrack`, `prune`, `prefill`) for every solving demo |
| **Free win from `codemap.py`:** `attach_authors()` git blame + commit distribution per function | — |

---

## 2. Concrete Gotchas in `common/codemap.py` (`detect.py` Must Handle These)

Verified directly in `common/codemap.py` (809 lines):

1. **Headers (`*.h`), `typedef struct`, and file-scope globals are NOT parsed by `codemap.Parsed`.**
   - `Parsed._scan()` only collects `self.funcs` and `self.protos` (lines 148–168).
   - `PLAN.md` §7 relies on detecting `typedef struct`, `#define`, and global arrays (`int g_grid[4][4]`).
   - **Fix:** Also read `*.h` in `ex00/` and scan `depth == 0` tokens outside function bodies in `detect.py` for globals, `typedef struct`, and `#define`.
2. **String and char literals are blanked out in `P.clean` / `P.toks`.**
   - `clean_source()` replaces `"Error\n"` with `"      "` and `'1'` with `0  ` (lines 102–108).
   - `Func.chars` runs `CHAR_LIT` over raw `P.src[body_s:body_e]` (line 188), which **includes comments** (e.g., `/* '1' to '4' */` will pollute `fn.chars`), and `Func` does not extract string literals at all.
   - **Fix:** Extract string and char literals using `P.src` filtered by `P.kinds == 's'` (never `P.toks` or unfiltered `P.src`).
3. **Compound & shift operators are split into 2 tokens in `codemap.TOKEN`.**
   - `TOKEN` (line 23) does **not** include `+=`, `-=`, `*=`, `|=`, `&=`, `<<`, `>>` — they tokenize as `+` `=`, `<` `<`, `|` `=`, etc.
   - **Fix:** Match these patterns on outline statement text (`node["text"]` / `P.text()`) or token bigrams, not single tokens.
4. **Pass `externals` explicitly to `codemap.build_graph()`.**
   - Default is `externals=("write",)` (line 380).
   - **Fix:** Pass `externals="*"` (or `("write", "malloc", "free")`) so `malloc`, `free`, and any forbidden calls (`printf`, `atoi`, `exit`, `calloc`) appear on the SVG call graph with the `FORBIDDEN` tag.
5. **Reuse `codemap.attach_authors()` — it's already implemented!**
   - `codemap.py` lines 315–373 already compute per-function `git blame` percentages and `git log` commit counts.
   - `rush01.pdf` Chapter II explicitly requires every teammate to understand all parts of a split workload, and Chapter III highlights AI/copy-paste risks. Showing per-function authorship + single-commit paste warnings is almost free to wire in.

---

## 3. Runner & Judging Edge Cases to Add (`runner.py` + `ref.py`)

### 3.1 Build, Files, & Forbidden Functions
- **Allowed files in `ex00/`:** Subject says `All the necessary files (*.c)` and *"must contain all files required to compile your program"*. Allow `*.c` and `*.h` without warning; flag `*.o`, binaries (`rush01`, `a.out`), `.DS_Store`, stray test files, extra directories, or files outside `ex00/`.
- **Compiler-generated symbols in `nm -u` (IMPORTANT!):**
  - On GCC/Linux, completely valid Piscine C like `int grid[4][4] = {0};` or struct copies can emit implicit `memset`, `memcpy`, or `__stack_chk_fail` in `nm -u`.
  - **Fix:** Cross-reference `nm -u` against source-level calls (`codemap`):
    - In `nm -u` **and** called in source → **FORBIDDEN**.
    - In `nm -u` **only** (not called in source, e.g. `memset`/`memcpy`/`__stack_chk_fail`) → **Note: compiler-generated** (do not falsely mark as forbidden!).
- **Forbidden include check:** Flag `#include <stdio.h>` or `<string.h>` as a warning even if unused.
- **Norminette:** Run on both `*.c` and `*.h` inside `ex00/`. Make `-R CheckForbiddenSourceHeader` configurable in `subject.txt` (some evaluations check 42 headers, others don't).

### 3.2 Catching Silent Bugs via Better Test Cases
- **Asymmetric puzzles are mandatory in `ok4`:**
  - The PDF example `"4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2"` is **symmetric** (`col_top == row_left`, `col_bottom == row_right`). A transposed or row/col-swapped solver still passes it!
  - Ensure `ok4` includes strictly asymmetric puzzles where all 4 sides differ.
- **Auto-diagnosis on wrong grids (high-value tutor UX!):**
  - When a team outputs a valid Latin square that fails clues, check in Python (takes < 0.1 ms) if it matches the clues under:
    - **Transposed grid** (rows/cols swapped in input or output),
    - **Top ↔ Bottom swapped**,
    - **Left ↔ Right swapped**,
    - **Clue order `row` before `col`**,
    - **Off-by-one visibility** (`>=` instead of `>` — though Latin square values are distinct, `max` initialized to `1` instead of `0` breaks visibility of `1`).
  - Showing *"matches if transposed — likely swapped col/row clue indices"* lets the tutor pinpoint the exact bug in 5 seconds.
- **Extra `fmt` edge cases to add:**
  - `"04 3 2 ..."` (leading zero — catches `ft_atoi`-based parsers accepting multi-digit tokens that evaluate to `1..4`!).
  - ASCII neighbors `'/'` (47) and `':'` (58), plus `'\t'`, `'\v'`, `'\n'` inside `argv[1]` (catches `ft_atoi` / `isspace` parsers).
  - `"4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2\n"` (trailing newline inside the argument).
  - Very short inputs (`""`, `"1"`, `"4 3"`) paired with **ASan (`-fsanitize=address,undefined`)** or **Valgrind** — catches the #1 Rush01 crash/UB bug: indexing `argv[1][i * 2]` without checking `'\0'` first!
- **Unsolvable puzzles (`nosol4`):**
  - Include `(1, 1)` opposite clue pairs (impossible for `N > 1`), pairs with `a + b > N + 1`, and globally impossible puzzles where every opposite pair is locally valid (`3 <= a + b <= 5`, no `(1, 1)`).
- **Valgrind / ASan coverage:**
  - Run leak/UB checks on **3 paths**, not just valid puzzles:
    1. One valid `ok4` puzzle,
    2. One `nosol4` puzzle (catches leaks on solver-failure early returns),
    3. One `fmt` bad-input case (catches leaks when `malloc` happens before validation fails, AND catches out-of-bounds reads on `""`!).
  - Note: Running an auxiliary ASan/UBSan build (`cc -Wall -Wextra -Werror -fsanitize=address,undefined`) catches stack buffer over-reads even for teams that don't use `malloc`.
- **Bonus `N×N` notes:**
  - Include `N = 5..9` in `bonusN`, plus invalid sizes like `N = 10` (40 clues → must `Error`) and non-multiples of 4 (e.g., 18 clues → `Error`).
  - Test `N = 1, 2, 3` separately as **informational** (PDF says *"other map sizes (up to 9x9)"*, so some teams start at 4 and some at 1).
  - For `N = 8, 9` in `ref.py`, don't block puzzle generation trying to prove uniqueness across huge search trees — generating a random Latin square + computing its clues is instant and valid for testing any solver since Rush01 accepts any valid solution.

### 3.3 `ref.py` `slow4` Selection
- The 576 4×4 Latin square enumeration is exact and takes milliseconds.
- When selecting `slow4` and `nosol4-deep`, rank puzzles by node count under **row/col-uniqueness backtracking** (the most common Piscine solver), not *only* check-at-end brute force — puzzles with mostly `2`s and `3`s (no `1`s or `4`s) stress real Piscine backtrackers much better than clues with `4`s.

---

## 4. Detector (`detect.py`) Refinements

- **Distinguish hardcoded 24-permutation tables from `solve.hardcode`:**
  - Clever Pisciners sometimes hardcode the 24 permutations of `{1,2,3,4}` as a lookup table and search over rows. That is **`solve.row_perm`**, NOT `solve.hardcode` (cheating/hardcoded answers).
  - Signal: `solve.hardcode` compares `argv[1]` against specific clue strings or outputs fixed grids without checking clues; `solve.row_perm` stores `24` 4-tuples and checks visibility/columns.
- **Common Piscine backtracking variants to recognize explicitly:**
  - `pos` (`0..15`) with `pos / 4` and `pos % 4` passed as `pos + 1` (the single most widespread 42 Rush01 idiom).
  - `(row, col)` passed as `(row, col + 1)` or `(row + 1, 0)`.
- **Neutral "Defense Signals" strip (aligned with Chapter III AI policy):**
  - Without ever accusing a student, surface objective signals that guide tutor questioning:
    - Git authorship & commit count (e.g., 1 teammate = 100%, or 1 giant commit).
    - Unused helper functions / dead code (`codemap` already flags `dead`).
    - Complexity jump (e.g., bitmasks / dynamic `int **` / structs on a 4×4-only submission) → auto-highlight 2 specific lines to ask *"Walk me through what happens if we change this line?"*.

---

## 5. Suggested Answers to `PLAN.md` §12 Open Questions

1. **`Error` on stderr:** Pass + orange note (PDF only says *"display 'Error' followed by a newline"* without specifying fd; also log exit code and flag unexpected extra stdout/stderr output).
2. **Timeouts:** `2s` for `ok4`/`fmt`/`nosol4-easy`, `5s` for `slow4`/`nosol4-deep` (helps tell "very slow" apart from "infinite loop"), `10s` for bonus `5×5..9×9`.
3. **Defense questions:** Include in **M2/M3**, not M5 — tiny implementation cost, highest payoff during Monday's defense.
4. **Port:** Keep `4243` alongside `rush00` (`4242`).
5. **Real past project (`~/backup_42/42piscine/rush01`):** Definitely run M1/M2 against it early so the detector is calibrated on real Piscine C before scaling up synthetic tests.

---

*Signed: Antigravity (Gemini)*
