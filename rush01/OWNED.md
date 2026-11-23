# Who edits which file (2026-11-22)

## Claude: team select + library layout — DONE
Claude no longer edits these. Gemini may edit them for dark mode:
- `tool/web/www/dash.html`, `tool/web/www/dash.js` (list view, search,
  filters, list/cards switch, "+ add team")
- `tool/web/www/library.html`, `tool/web/www/library.js` (catalog filter,
  folding groups, the catalog stays on screen)
- `tool/web/www/select.css` (all the new styles; linked from dash.html and
  library.html)
- `tests/web/browser_check.cjs`, `tests/web/test_b6_browser.py`,
  `tests/web/test_b7_demos.py` (checks for the list, filters, search and the
  catalog filter)

## Gemini: dark mode
- `tool/web/www/notebook.css` (colour variables, `:root[data-theme="dark"]` rules)
- `tool/web/www/rush01.css`
- `tool/web/www/select.css` (now free: check the list rows and the pick bar
  on the night page)
- `page_theme()` in `tool/web/www/page.js`

## Rules
- `select.css` uses only the colour variables (`var(--ink)`, `var(--card)`,
  `var(--page)`, `var(--text)`, `var(--body)`, `var(--teal)`, `var(--orange)`,
  ...), no fixed colours. On the page background it uses `--page`/`--text`;
  inside rows and cards `--card`/`--ink`. Keep it that way.
- Stdlib only, plain CSS/JS, no frameworks (AGENTS.md rule 2).
- Check before you say done: `python3 rush01/tests/run.py web` (headless
  chromium; any JS error fails it). The dashboard opens in the list view;
  `/?view=cards` opens the cards (the test uses both).

## 2026-11-23: game layout (critiques/GAME_LAYOUT_ANTIGRAVITY.md), Claude — DONE
All four proposals are built; every file is free again.
- `tool/web/www/game.css` (new): gates, hero, loadout, deck tabs, select
  view, VS race. Variables only.
- `tool/web/www/page.js`: `page_sheet()`, `page_extra()`, `page_stop_word()`.
- `tool/web/www/team.html`, `team.js`: gates, hero (3D + loadout), deck.
- `tool/web/www/dash.html`, `dash.js`: sheet outcome as the result, "extra
  checks", select view, ↑ ↓ Enter.
- `tool/web/www/library.html`, `library.js`: VS race.
- `tool/web/CONTRACT.md`: B1, B3, B8, B9 (new).
