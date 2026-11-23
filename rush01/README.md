# rush01

Evaluator tool for the C Piscine rush01 (4x4 skyscraper): builds and judges a
team's turn-in against a puzzle bank and names the approach of each part of
their code (parse, data, solve, print), with evidence.

Run: `./rush01/tool/rush01 serve --open` (dashboard, port 4243) or
`./rush01/tool/rush01 <team dir | git URL>`.
Check everything: `python3 rush01/tests/run.py` (`--quick`, `--no-browser`).

Layout:
- `tool/rush01_wiring.py`: the wiring file + CLI (`tool/rush01` launches it)
- `tool/puzzle/`: solve, make and diagnose puzzles; `bank/` the test puzzles
- `tool/judge/`: build a team and judge it against the bank
- `tool/detect/`: name the approach of each part
- `tool/web/`: dashboard, team page, approach library (`/library`), and preset demos
- `tests/`: `run.py` (the check), one folder of tests per tool folder, `corpus/` fake teams

Rules: `AGENTS.md`. Plan: `PLAN.md`. Shapes between folders: `tool/SHAPES.md`.
Needs python3 (3.10+), cc; optional norminette, valgrind, ASan runtime, node + chromium.
Team code runs on your machine with timeouts, no sandbox.

The eval sheet (intra, 2026-11-22, `eval_sheet/`) is followed: its six
eliminatory inputs are the bank group `evalsheet`; each team page starts with
an "Eval sheet" card: what stops the evaluation, the eliminatory tests,
malloc made to fail (the team rebuilt with `-Wl,--wrap=malloc`), the bonus
size, and lines to ask about (bit shifts, complex lines, recursion, unchecked
malloc). The sheet runs `./rush-01`; the subject's `rush01` is built.

Known limits (true, not hidden):
- Some misreadings (`bottom_no_reverse`, `count_plus1`, ...) make every valid
  puzzle unsolvable: such a team can't be told apart from "always Error",
  so they are listed in `extra`, never named as `best`.
- ASan can't see reads past argv's `'\0'`, only past a malloc'd copy.
- malloc-fail runs need GNU ld (`--wrap`): Linux only.
