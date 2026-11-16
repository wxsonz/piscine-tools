# Handoff: rush tools → the 42 iMac session

For the Claude session on the 42 Bangkok iMac. The user will fetch the **rush
subject PDF** there and wants you to update the tool to match it. This note is
the context you don't have; the laptop session that built the tool wrote it
(2026-11-16). Talk to the user in plain words.

## What this repo is

A tool for evaluating C-Piscine **rush** projects (Batch #20): it builds each
team's turn-in, runs norminette and a forbidden-function check, tests the
output against the subject, traces the code under gdb, and shows the result
in a web visualizer plus a static HTML report per team.

```
common/           shared by every rush tool
  codemap.py        Norm-C reader + report page chrome (BASE_CSS, page())
  ctrace.py         gdb tracer driver;  gdbtrace.py  runs inside gdb
  skin.css          "editorial" look for the visualizer + reports (see Style)
rush00/
  tool/rush00       the CLI (python3, stdlib only)
  tool/web.py       the visualizer server:  rush00 serve [--port N] [--open]
  tool/www/         dash.html (team select), viz.html (algorithm view),
                    notebook.css, style.css, fonts/
  tool/README.md    full manual: read it before changing anything
  tests/            self-checks; expect/*.txt describe the 40 generated teams
rush01/ rush02/   same layout, tools still to come (only empty folders)
```

**Not in git, on purpose (see `.gitignore`), never commit them:**
- `*/repo/`: team submissions (student code) and the 40 generated test teams.
- `*/reports/`: generated; they embed team source and local paths.

So on a fresh clone `rush00/repo/` is empty: `tests/run.py` has no teams to
check until the user copies the corpus over or real teams are dropped in.

## Your task: match the tool to the PDF

First find out **which rush the PDF is**, then:

### If it is rush00 (the rectangle: `rush(x, y)`, 9 chars)
The tool is built for this. Only `rush00/tool/subject.txt` should change; the
core rule (corners/edges/fill; x == 1 prints the left column, y == 1 the top
row) is built in.

```sh
./rush00/tool/rush00 subject the.pdf   # pulls the examples out (needs pdftotext)
./rush00/tool/rush00 subject           # shows what it understood: ALWAYS check this
./rush00/tool/rush00 init              # or a blank template to fill by hand
```

No `pdftotext`? You can read the PDF yourself and fill `subject.txt` by hand
from `init`'s template. Check every example in the PDF against what
`rush00 subject` prints; the tool warns when an example doesn't fit its 3×3
pattern, and then tests only the examples, as written. Also check the turn-in
rules (file names, `ex00/`, allowed functions) against what the tool expects
(`tool/README.md`); if the PDF differs, change the tool, not the PDF's reading.

### If it is rush01 or rush02 (a different project)
There is no tool yet. Build `rushNN/tool/` on the rush00 layout and reuse
`common/` (codemap, tracer, page chrome). Ask the user what they want first:
the full evaluator + visualizer, or a smaller checker for the day. Don't copy
rush00's rectangle logic into a project it doesn't fit.

## Running on the 42 iMac

Ubuntu 22.04, no sudo, Python 3.10 (the code is 3.10-safe), home has ~3 GB.
Check before starting: `which gdb cc norminette pdftotext node chromium`.
gdb and cc are needed; norminette is optional; pdftotext only for
`subject x.pdf`; node + chromium + playwright-core only for the browser part of
`tests/run.py` (`--no-browser` skips it). The tool runs team code with timeouts
but **no sandbox**.

`rush00 serve` keeps the code it started with: after editing the tool, restart
the server, or it regenerates reports with the old code.

## Style (in case the PDF work touches the UI)

The dashboard (`www/dash.html` + `www/notebook.css`) is in the **"notebook
game"** look of this batch's Coalition Quest deck: ruled paper, taped index
cards (3px ink border, uneven corners, 6px hard shadow, slight rotation),
Permanent Marker titles, Patrick Hand text, a HUD top-right, hearts = the
three basic checks, hatched bars = core cases. Colours: ink `#1E2A3A`, teal
`#0B7A73` = good, orange `#E07A1F` / `#B4560A` = attention or loss, paper
`#FBF8EF`, card `#FFFDF7`. The visualizer and reports still use the older
editorial skin (`common/skin.css`); moving them to the notebook look is the
planned next step, but **only if the user asks**.

Rules the user cares about:
- **Truth first:** a picture or label must say what the code really does.
  Status words and colours carry meaning; style never changes it.
- **No ligatures** in code (`==` must not render as one glyph); both CSS
  files force this.
- Fonts ship as files in `www/fonts/` (with licences); never assume installed.
- Plain Python stdlib + plain JS/CSS; no frameworks or new dependencies.
- The user's usage budget is tight: prefer direct, cheap steps.

## Git

Remote `git@github.com:wxsonz/piscine-tools.git` (private), branch `main`.
Commit small and push when the user says so. Before every commit check
`git status` shows no `repo/` or `reports/` paths. `tests/subject.txt` has a
comment naming the user's 42 login; fine while private.
