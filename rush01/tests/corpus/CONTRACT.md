# CONTRACT: tests/corpus/

## Job
Provide fake rush01 teams with known approaches and known bugs, so the
tool can be checked.

## Owns
`tests/corpus/` (`teams/<team>/...`, `expect/<team>.txt`, `gen.py`), and the
copies `gen.py` writes into `rush01/repo/`.

## Publishes
- `teams/<team>/`: the team's files as a student would push them (normally
  `ex00/*.c`, `*.h`). Committed: it's code we wrote (SHAPE-7).
- `expect/<team>.txt`: the expected labels (SHAPES "corpus expect").
- `python3 rush01/tests/corpus/gen.py [--out DIR]`: copies every team into
  `DIR` (default `rush01/repo/`), each as its own git repo with 2 authors
  (fixed names and dates, so authorship is stable).

## Uses
`puzzle/` (`puzzle_solve`, `puzzle_check`, `puzzle_load_bank`) for the
self-check only.

## The teams (PLAN.md §9)
Composite `c01`–`c13`, day-one `d1`–`d5`, bugs `b1`–`b6`, exactly as in the
PLAN.md §9 table.

## Behaviours
- **B1** Every team except `d3` builds with
  `cc -Wall -Wextra -Werror -o rush01 *.c` in its turn-in dir.
- **B2** Every team except where `expect` says otherwise passes norminette
  (if installed).
- **B3** Correct teams solve every `ok4` bank puzzle and print `Error` on
  every `fmt` and `nosol4-easy` puzzle (self-check, `gen.py --check`).
- **B4** Each `b*` team shows its bug and nothing else (e.g. `b1` fails only
  asymmetric puzzles).
- **B5** The code reads like student code: Norm style, French-42 habits
  (`ft_` names, `t_` types), not like this tool's style.

## Rules here
C follows the 42 Norm (AGENTS.md). Only `write`, `malloc`, `free`, except
in `d1`. No team includes files outside its folder.

## Done when
`python3 rush01/tests/corpus/gen.py --check` passes and
`python3 rush01/tests/run.py corpus` passes.
