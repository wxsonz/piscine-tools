# CONTRACT: tool/judge/

## Job
Build a team's turn-in and judge the binary against the puzzle bank.

## Owns
`tool/judge/*.py`, `tests/judge/`, temp dirs it creates (removed after).

## Publishes
- `judge_team(team_dir_abs, subject, bank, work_dir_abs) -> judge result`
  (SHAPES). Never raises for a team's fault: failures are in the result.
- `judge_tools() -> {"cc", "norminette", "valgrind", "asan": bool}`

## Uses
- `puzzle/`: `puzzle_check`, `puzzle_diagnose`
- `common/codemap.py` (read-only): `parse_file`, `Func.calls`, for the
  source-call half of the forbidden check.

## Behaviours (one test each; tests build tiny C programs in a temp dir)
- **B1** Finds `ex00/` (any depth ≤ 2, rush00's `find_ex_dir` logic); none →
  `files.no_ex_dir` true and judges the root.
- **B2** Copies the turn-in to `work_dir_abs`; the team folder is unchanged
  afterwards (no files added).
- **B3** Build failure → `built` false, first error in `build_log`, `runs`
  empty, everything else filled.
- **B4** `printf` → forbidden, `where: "binary"` (shows as `puts` or `printf`
  in `nm -u`) and `"source"` with file and line.
- **B5** `int g[4][4] = {0};` that emits `memset` → not forbidden; note
  "compiler-generated".
- **B6** A team's own `ft_strlen` / `strlen` → not forbidden; own `strlen`
  gets the "defines own" note.
- **B7** Correct grid → pass; trailing space / missing final `\n` / extra
  stdout → fail with the reason.
- **B8** `Error\n` on stdout → pass; on stderr → pass + note (or fail when
  `subject.error_on_stderr == "fail"`).
- **B9** Infinite loop → killed at `timeout_ms`, `timed_out` true, fail.
- **B10** Segfault → `signal: "SIGSEGV"`, fail. Output > 1 MB → capped.
- **B11** Reading past `'\0'` on `""` → sanitizer finding with the case id.
- **B12** LSan "fatal error" → retried with `detect_leaks=0`, note says so.
- **B13** A missing tool (norminette, valgrind, asan) → `ran` false and a
  note; nothing fails because of it.
- **B14** `diagnosis` is built from runs whose output is a grid or `Error`,
  on puzzles with `clues` not null.
- **B15** `timing.slow4_over_ok4` = median slow4 time / median ok4 time
  (null if either is missing).

- **B16** The eval sheet's stops in its order (`stops`): no `ex00/`,
  norm errors, extraneous files (check), build failure, forbidden calls
  (check), a failed `evalsheet` run (no points).
- **B17** Unchecked `malloc` → crashes when the Nth malloc returns NULL
  (`-Wl,--wrap=malloc` shim, team calls only); checked → `exit N`; no
  malloc in the source → `ran` false and a note.
- **B18** `bonus.largest_n` = biggest N with all bonus puzzles 5..N
  passing; `counted` false after a stop or a mandatory failure.

## Rules here
No printing (return values). Every process: timeout, output cap, cwd in the
temp dir, `stdin` from `/dev/null`. Run puzzles in a small thread pool
(≤ 4) to keep a full evaluation under ~30 s.

## Done when
`python3 rush01/tests/run.py judge` passes.
