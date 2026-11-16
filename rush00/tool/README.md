# rush00 — evaluate and visualize

```
rush/
  common/            shared by every rush tool: C reader (codemap), gdb tracer
  rush00/
    repo/            drop team folders here (or from the browser)
    tool/            this tool: rush00 (CLI), web.py + www/ (visualizer), subject.txt
    reports/         generated: <team>.html report, <team>.json summary
    tests/           checks the tool itself against the 40-team corpus (see below)
  rush01/  rush02/   same layout, tools to come
```

## The visualizer

```sh
./rush00/tool/rush00 serve --open        # http://localhost:4242
```

- **Dashboard**: drop team folders on the page, pick a folder, or paste a
  git/vogsphere URL. Anything copied into `rush00/repo/` by hand shows up as
  well. Every team gets evaluated automatically, and again whenever its files,
  the subject or its leader/rush setting change. The assigned rush and the
  leader can be set right on the card.
- **Visualize ▶** opens the algorithm view of one team. Its code is compiled
  with `-g` and actually run under gdb, so what you see is what their code
  does, not a guess from reading it:
  - **The idea**: every printed cell grouped by the chain of decisions that
    produced it. With a row-then-column design this is a table: row rule ×
    column rule = char. With per-cell `if`s it's a list of rules, one per
    branch. It also shows where each char literal is written.
  - **Same code, other sizes**: 1×1, 5×1, 1×5, 2×2, 5×3 and 6×5 in the same
    colors. ⚑ marks a decision path that the general case never takes,
    i.e. a special case or hardcoding.
  - **Questions that test the idea**, with their answers, taken from the run:
    which check wins when x = 1 (the first column is also the last), what
    values a loop variable takes, which conditions hold at a given corner, how
    many writes happen.
  - **Watch it run**: step by char, row or line. The current line lights up,
    conditions show true/false with their values filled in, the stack shows
    the variables (changed values flash, unassigned locals read
    "not set yet"), and the rectangle fills in. Click any cell anywhere to
    jump to the moment it was printed.
- **Full report**: the evaluation sheet (see below).

## The CLI

```sh
./rush00/tool/rush00 git@vogsphere…:…/intra-uuid-…   # clone into repo/ and evaluate
./rush00/tool/rush00 rush00/repo/some-team           # one folder
./rush00/tool/rush00                                 # every team in repo/
./rush00/tool/rush00 some-team --rush 3 --open       # assigned rush known, open the report
```

The report checks the turn-in files, runs norminette
(`-R CheckForbiddenSourceHeader`), looks for forbidden functions (in both the
objects and the source), and runs the official
`cc -Wall -Wextra -Werror main.c ft_putchar.c rushNN.c` build. It then draws
every test case as a char grid (expected vs got, with the wrong cells
marked), shows a call graph with a card per function, runs their own main.c,
and lists defense questions next to the line-numbered source.

## The subject: `subject.txt`

Only the core is built in: `rush(x, y)` draws a rectangle from 9 chars
(corners, edges and fill). When x == 1 it prints the left column, and when
y == 1 the top row. Everything that can change on the day goes in
`rush00/tool/subject.txt`:

```sh
./rush00/tool/rush00 subject today.pdf   # pull the examples out of the real PDF
./rush00/tool/rush00 subject             # show what it understood (always check!)
./rush00/tool/rush00 init                # or start from a blank template and paste
```

The tool works out each rush's 3×3 pattern from the examples, checks that the
pattern reproduces every one of them, and then generates the full test set. If
an example doesn't fit, it warns you and tests only the examples, exactly as
written. With no subject, a team's own `rush(6, 5)` is taken as its pattern,
everything else is checked against that, and the verdict reads
`PASS? (check pattern vs PDF)`.

## Assigned rush

Set it on the dashboard card, or pass `--rush N`, or `--leader LOGIN` together
with `assign = leader-mod-5` in subject.txt. It's stored in
`rush00/repo/teams.txt`:

```
some-team   leader=jdoe   rush=3
```

## Testing the tool: the corpus

`repo/` holds 40 generated teams. Each one draws a correct (or deliberately
wrong) rectangle with a different algorithm, and `tests/expect/<team>.txt`
says what it does:

| prefix  | what                                                                  |
| ------- | --------------------------------------------------------------------- |
| `math-` | brute force every cell with math: class sums, flat index, bitmask, ASCII arithmetic, boolean multiply… |
| `weird-`| recursion, one buffer + one write, countdown loops, function-pointer table, struct, state machine… |
| `bad-`  | works but badly designed: special cases, copy-paste, deep nesting, globals, magic numbers… |
| `bug-`  | one realistic bug each: off by one, x == 1, y == 1, swapped corners, newlines, sizes ≤ 0, trailing space |
| `shape-`| odd projects: five rush files, helpers in main.c, entry not named rush, header, extra .c file… |

```sh
python3 rush00/tests/run.py               # everything (≈4 min)
python3 rush00/tests/run.py math- weird-  # some of them
python3 rush00/tests/run.py --no-browser
```

For each team it checks that:
- the evaluator passes the correct teams and catches the buggy ones
- the gdb trace prints exactly what the real binary prints, at 5 sizes
- the visualizer page loads without JS errors and maps every printed char

It also prints the one-line explanation the visualizer gives of each
algorithm. Any other team in `repo/` (a real one) gets only the tracer and
visualizer checks. The corpus uses `tests/subject.txt` (patterns taken from
your own rush00), never `tool/subject.txt`. `tests/ref.py N X Y` prints the
reference output, and `tests/ref.py check DIR N` checks a folder.
The browser part needs node and chromium, and borrows playwright-core from
`~/42me/ft_blueprint/node_modules` (set `PLAYWRIGHT_CORE` to use another).

Delete the generated teams before the real evaluation if you don't want
them on the dashboard: `rm -r rush00/repo/{math,weird,bad,bug,shape}-*`.

## Needs

python3 (stdlib only), cc, gdb, norminette (optional), pdftotext (only for
`subject x.pdf`). The tool runs the teams' code on your machine, with
timeouts but without a sandbox.
