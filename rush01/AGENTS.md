# rush01: rules for every agent

What this is: a tool for the evaluator of the C Piscine rush01 (4x4
skyscraper). It builds and judges a team's turn-in and names the approach of
each part of their code. The plan is `PLAN.md`; read §1–§4 before any code.

## Code design
Follow the Code Book: `~/_research/software/10_me/14_code-book/14.00-read-me-first.md`
(read it first, then the chapters it names; cite rule IDs in plans and
reports). Kind: **none** (a Python tool with a plain JS/CSS web page).
Check command: `python3 rush01/tests/run.py` (`--quick`, `--no-browser`).
One folder's tests: `python3 rush01/tests/run.py <folder>` (e.g. `puzzle`).

Differences from the book (each has a decision file):
- `common/` (repo root) breaks SHAPE-1 by its name. Kept as is, read-only,
  until after Monday: rush00 depends on it. `decisions/001-keep-common.md`.
- Parallel workers for v0, against PLAN-1 / 11.04: the Monday deadline.
  `decisions/002-workers-for-monday.md`.
- Python and JS formatting: `decisions/003-python-and-js-style.md`.
- C in `tests/corpus/` imitates student code: it follows the **42 Norm**
  (norminette), not the book (the book's rule 1: an outside standard wins).

## Project rules (they win over the book)
1. **Truth first.** A label, colour or picture says what the code really
   does. When a check can't tell, it says "unsure" / "unrecognized" /
   "skipped: <why>". Never a guess shown as a fact. No "suspicion" heuristics.
2. **Stdlib only**: Python 3.10 (the 42 iMac), plain JS/CSS. No pip, no npm,
   no frameworks, no CDN. Fonts ship as files with their licences.
3. **No ligatures** in code fonts (`font-variant-ligatures: none`).
4. **Look**: the notebook-game style of `rush00/tool/www/notebook.css`.
   Teal = good, orange = attention / loss, ink = neutral.
5. **Never commit** `rush01/repo/`, `rush01/reports/`, `rush01/rush01.pdf`,
   or anything generated except `tool/puzzle/bank/` (small, ours). Never run
   git commands that change history; commit only when the user says so.
6. **Don't touch** `common/` or `rush00/` before Monday 2026-11-23.
7. **Team code is untrusted**: build and run it only in a temp dir, always
   with a timeout and an output cap. Never in the repo.
8. **Folders meet through their contract** (SHAPE-3): import only
   `from <folder> import <name>` for names the folder's `CONTRACT.md`
   publishes; data between folders has the shapes in `tool/SHAPES.md`.
9. **The core returns values** (CODE-11): no `print(` in `puzzle/`, `judge/`,
   `detect/`. Only `tool/rush01` and `web/` talk to the user.
10. **Contract first** (PLAN-5): to change a published name or a shape,
    change `tool/SHAPES.md` / the `CONTRACT.md` first, in the same change.

## Workers (decision 002)
- Your task names the folders you **OWN**. Write only there. Read anything.
- Need something another folder publishes that isn't built yet? Code against
  its contract (a stub in your tests is fine). A contract looks wrong → stop
  and tell the lead with the change you propose (PLAN-8). Never edit it.
- Done = your folder's tests pass under `python3 rush01/tests/run.py <folder>`,
  and you end with the PLAN-7 report: CHANGED / DID / DECIDED / CHECKS / UNSURE.
