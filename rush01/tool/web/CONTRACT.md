# CONTRACT: tool/web/

## Job
Serve the dashboard and the team page on localhost.

## Owns
`tool/web/*.py`, `tool/web/www/`, `tests/web/`.

## Publishes
- `web_serve(app, port=4243, open_browser=False)`: blocks; binds
  127.0.0.1 only. `app` is a dict built by the wiring file:
  `{"repo_dir_abs", "report_dir_abs", "evaluate", "clone", "catalog"}`;
  `evaluate(team_dir_abs) -> report` (and writes `reports/<team>.json`),
  `clone(url) -> team_dir_abs`, `catalog` = `detect_catalog()`.

## Uses
- The report shape (SHAPES) through `app["evaluate"]` and the JSON files in
  `report_dir_abs`; never imports `judge/` or `detect/`.
- `common/codemap.py` (read-only): `parse_file`, `source_html`,
  `build_graph`, `svg_graph` to show source + call graph.
- `rush00/tool/www/notebook.css` and `fonts/` via symlinks in `www/`
  (read-only).

## Behaviours
- **B1** `/` lists every folder in `repo_dir_abs` with its state (queued,
  running, done, error) and, when done, the four verdict names + hearts.
  Three views (list, select = roster + one team's card, cards), a search
  box, filters (stopped / sheet OK / extra fails / not evaluated), keys
  `/` ↑ ↓ Enter.
- **B2** Dropping a folder or pasting a git URL adds the team and evaluates
  it; a team whose files change is re-evaluated (mtime scan, like rush00).
- **B3** `/team/<name>` shows, top to bottom: the eval sheet as 7 gates in
  its order (turn-in, norm, build, allowed calls, eliminatory, malloc
  break, bonus; gates after the first STOP are marked "after stop", never
  hidden); the 3D view beside the loadout (hearts + the four parts); then
  tabs Defense (sheet details, lines to ask, part cards: verdict, tier,
  confidence, where, evidence, facts, folded questions, the strip) / Runs
  (the run table by group with the diagnosis line) / Source (source + call
  graph) / All. A gate, a part slot or a file:line link opens its tab.
- **B4** The 3D view (CSS 3D, no libs) draws a team's output for any bank
  puzzle: blocks by height, clues on the base, drag to rotate, top / front /
  iso; clicking a clue lights the sightline (visible teal, hidden faded,
  count shown, orange if wrong). Fallback: 2D grid, same sightlines.
- **B5** Unknown team / bad path → 404; paths can't leave `repo_dir_abs`.
- **B6** Pages load without JS errors on a report fixture
  (`tests/web/fixture_report.json`, made from SHAPES).
- **B7** Preset demos (`www/demos_gen.js`, `www/demos_ui.js`): every catalog
  entry (`parse.*`, `data.*`, `solve.*`, `print.*`) has a deterministic JS
  step generator played by one shared player (step / back / play / speed /
  reset / jump to end + step counter) and one shared renderer per part
  (reusing the 3D/2D skyscraper view for solving). Always labelled
  "how this approach works (preset), not their code" (AGENTS.md rule 1).
  Huge brute-force spaces stop at a fixed cap and state it plainly (FLOW-3).
- **B8** Each recognized part card on `/team/<name>` has a "show how it
  works" button that opens that approach's preset demo; `/library` lists
  every catalog entry with its demo and offers a side-by-side compare mode
  for any two solving approaches on the same puzzle (a VS race: each
  side's step bar, and its preset step count when it ends).
- **B9** The headline of a team is the eval sheet's outcome (`page_sheet`
  in `www/page.js`): its first STOP, or "sheet OK" when nothing stops and
  the eliminatory tests pass. Our own bank (every group but `evalsheet`)
  is shown apart as "extra checks": facts to ask about, never points.

## Rules here
JS per decision 003 (Allman, tabs, snake_case, no framework, no build).
Status words and colours carry meaning (AGENTS.md rule 1). No ligatures.
Port 4243. No CDN.

## Done when
`python3 rush01/tests/run.py web` passes (the browser part is skipped
without node + chromium).
