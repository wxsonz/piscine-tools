# Critique: Making Rush01 Feel Like a Game, Not a Boring Board

> **Author:** Antigravity (Gemini)  
> **Date:** 2026-11-23  
> **Scope:** Layout & interaction design of `/`, `/team/<name>`, and `/library` (`tool/web/www/`)  
> **Interactive mockup:** `critiques/GAME_LAYOUT_MOCKUP_ANTIGRAVITY.html` (standalone, plain HTML/CSS/JS — open directly in a browser; includes all 3 screens, rotatable 3D boards, paper/night toggle, and a live VS Arena race)  
> **Constraints:** `AGENTS.md` rule 1 (*Truth first* — no fake scores/grades/XP), rule 2 (*Stdlib only / plain JS+CSS*), rule 4 (*notebook-game look: teal = good, orange = attention, ink = neutral*)

---

## 1. Diagnosis: Why It Still Feels Like a Boring Board

Right now the **skin** says *"video game drawn in the margins of a school notebook"*, but the **information architecture** is a classic admin dashboard / report board:

1. **Dashboard (`/`)** is either a dense spreadsheet (`list`) or a grid of 24 identical tall cards (`cards`). You scan rows, click a link, and leave the page.
2. **Team page (`/team/<name>`)** is a **4,000px vertical document** (`Eval Sheet → Project → 4 Part cards → Run tables → 3D → Source`). The most interactive, game-like object in the whole app — **their live 3D skyscraper output** — is buried three screens down.
3. **Approach Library (`/library`)** Compare mode puts two solvers side-by-side in two static panes instead of framing them as an actual head-to-head race.

---

## 2. The Core Tension (What We Must Balance)

| Game-Feel Camp | Live-Evaluator Tool Camp |
|---|---|
| A 42 defense *is* an encounter: inspect the team's build, watch their towers stand or collapse, walk the eval-sheet gates, ask the boss questions. | During a 15–30 minute defense, hiding real facts behind multi-step reveals or decorative animations slows down the tutor. |
| Spatial screens (fighter select, stage + tabs, checkpoint map, VS race) keep nervous students visually engaged when you turn the screen toward them. | Never invent fake RPG metrics (`S-Rank`, `XP`, `HP: 73%`, leaderboards) — `AGENTS.md` rule 1 forbids anything that looks like a score or guess. |

**Thesis:** Keep 100% of the exact same factual data, and change the **spatial arrangement** from *vertical document / spreadsheet* to *game screens*.

---

## 3. Concrete Arrangement Proposals (With Tradeoffs)

### Proposal A — Team Page (`/team/<name>`): Eval Sheet as a **Checkpoint / Gate Track**
The 42 Rush01 eval sheet is *literally* a sequential dungeon run:

```text
[1. Norm] ──▶ [2. Build] ──▶ [3. Allowed Calls] ──▶ [4. 6 Elim] ──▶ [5. Malloc] ──▶ [6. Bonus]
   ✓ OK          ✓ OK             ✓ OK                 ✗ STOP            —               —
```

- **Arrangement:** Replace the top text-paragraph block of `#sheet` with a single horizontal **gate track** pinned directly below the team header.
  - Cleared gates = teal chip; first `STOP` gate = orange barrier stamp; `CHECK` items hang directly off their gate; unreached/skipped gates = dashed neutral.
  - Clicking any gate jumps directly to its underlying detail (norm list, build log, eliminatory run table, malloc test).
- **For:** 100% truthful to the real eval sheet order, zero fake gamification, and communicates *"how far did this team get?"* in 0.5 seconds.
- **Against:** Must stay one compact horizontal strip (wrapping cleanly on narrow viewports) so it doesn't push the main stage down the page.

### Proposal B — Team Page (`/team/<name>`): **Hero 3D Stage + Character Build Loadout + Notebook Tabs**
Stop burying the 3D board at the bottom of a 4,000px scroll. Arrange `/team/<name>` like a **game inspection screen**:

```text
┌─────────────────────────────────────────────────────────────┐
│ [1. Norm] ─▶ [2. Build] ─▶ [3. Calls] ─▶ [4. Elim] ─▶ ...  │  ← Checkpoint Track
├──────────────────────────────────┬──────────────────────────┤
│  THEIR OUTPUT IN 3D (Hero Stage) │  TEAM BUILD (Loadout)    │
│  [puzzle ▼] [top][front][iso][2D]│  ♥ builds  ♥ calls  💔 norm│
│                                  │  ┌─────────────────────┐ │
│        [ rotatable 3D            │  │ PARSE  Scan & count │ │
│          skyscrapers ]           │  │ DATA   2D array     │ │
│                                  │  │ SOLVE  T1 Line BT ▶ │ │
│  diagnosis: 8/8 fit transposed   │  │ PRINT  1 write/char │ │
│                                  │  └─────────────────────┘ │
├──────────────────────────────────┴──────────────────────────┤
│ [ Defense & Ask ]  [ Bank Runs (11/22) ]  [ Blueprints ]    │  ← Physical Notebook Tabs
│  (active tab content here — plus an "All" scroll toggle)    │
└─────────────────────────────────────────────────────────────┘
```

- **Arrangement:**
  - **Left Hero:** The rotatable **3D skyscraper board** + puzzle picker + diagnosis banner right at the top of the page (or, when the team did not build, the build-error terminal well in that hero slot — honest, never empty chrome).
  - **Right Sidecar:** **Lives (3 hearts)** + **4-Part Loadout** (`Parse / Data / Solve / Print` as compact RPG equipment slots showing approach name, confidence, tier, and `▶ Demo`; clicking a slot expands its evidence & defense questions or scrolls to its detail).
  - **Bottom Deck (Notebook Divider Tabs):**
    1. `Defense` (lines to ask about + defense questions per detected part + project facts)
    2. `Runs` (bank groups & tables — clicking `3D` on any row updates the Hero Stage right above/beside it without losing your scroll position!)
    3. `Blueprints` (call graph + source code — clicking any `file:line` link auto-switches to `Blueprints` and highlights the line)
    4. Optional `All` toggle for tutors who want `Ctrl+F` across the entire page at once.
- **For:** Turns `/team/<name>` from a static wall of text into a live playable defense cockpit; eliminates scrolling 3,000px between `Runs`, `3D`, and `Source`.
- **Against:** Tabbed views break naive `Ctrl+F` unless we provide an `All` mode (easy to include) or keep `Defense` + `Loadout` visible.

### Proposal C — Dashboard (`/`): **Arcade "Fighter Select" Split Screen**
Right now `list` feels like a spreadsheet and `cards` is 24 giant cards in a wall.

```text
┌────────────────────────────────────────────────────────────────┐
│ find a team ( / )   [All] [Stopped] [Failing] [Pass]  [+ Add] │
├──────────────────────────┬─────────────────────────────────────┤
│ ROSTER (↑ / ↓ / Enter)   │  SELECTED TEAM PREVIEW              │
│ ▶ c01   11 fail   T1     │  c01          [ 11 FAIL / 22 ]      │
│   c02   all pass  T2     │  [Norm ✗]─[Build ✓]─[Elim ✗]...     │
│   d3    no build  T2     │  Loadout: Scan · 2D · T1 BT · Char  │
│   ...                    │  ♥ builds   ♥ calls   💔 norm        │
│                          │  8/8 failures fit: transposed       │
│                          │            [ ▶ START DEFENSE ]      │
└──────────────────────────┴─────────────────────────────────────┘
```

- **Arrangement:** Keep the fast searchable/filterable roster on the left (`↑`/`↓` moves the `▶` cursor, `Enter` opens `/team/<name>`); pin **one focused Hero Preview card** on the right (reusing `rush00`'s original `.stage` two-column concept from `notebook.css`!). Keep the full-width `list` table as a secondary view toggle for bulk comparison.
- **For:** Feels unmistakably like Smash Bros / Pokémon party select / arcade fighter select; lets a tutor flip through 20+ teams with arrow keys without opening 20 tabs.
- **Against:** Slightly less horizontal space for scanning all 4 approach names across every team at once (mitigated by keeping the `table` view button right next to `select`).

### Proposal D — Library (`/library`) Compare Mode: **"VS Arena" Solver Race**
- **Arrangement:** Frame Compare mode as a live matchup:
  - `P1` vs `P2` header with a hand-drawn **`VS`** emblem in the middle.
  - A **live twin race bar** at the top tracking each solver's step progress in real time as both 3D boards animate side-by-side.
  - When the faster solver finishes (e.g. `T1 Line-Check` at 88 steps while `T0 Check-at-End` is still thrashing toward 416), stamp **`SOLVED · 88 steps`** in teal on the winner's pane while the other keeps running!
- **For:** Visually proves *why* pruning matters in 3 seconds flat — students and other tutors remember it instantly, and every count is exact truth.
- **Against:** Very small implementation cost (~40 lines of JS + CSS); low risk.

---

## 4. Non-Negotiable Guardrails (What We Must Reject)

1. **No fake scores, grades, letter ranks (`S/A/B`), XP bars, or "code quality %"**: violates `AGENTS.md` rule 1 and misleads students about real 42 evaluation.
2. **No blocking intro animations or sound effects**: a tutor runs 6–10 defenses back-to-back; every click and keypress must be instant.
3. **No hiding `STOP` conditions behind clicks/tabs**: norm failure, build failure, forbidden calls, and eliminatory failure must always be visible at first glance.
4. **No external frameworks or assets**: stay 100% plain HTML/CSS/JS (`AGENTS.md` rule 2) and keep dark mode variable-driven (`rush01.css`).

---

## 5. My Recommended Priority Order

If we don't redesign everything at once, here is the highest payoff-to-effort order:

1. **Team Page Hero + Checkpoint Track + Notebook Tabs** (Proposals A + B) — biggest single transformation because tutors spend 90% of a defense on `/team/<name>`, and right now the 3D board is buried at the bottom.
2. **VS Arena Race Bar in `/library` Compare** (Proposal D) — tiny change, huge "wow" factor for teaching algorithms.
3. **Dashboard Fighter Select Split Screen** (Proposal C) — great polish once `/team/<name>` feels right, while preserving the compact `list` view toggle.

---

*Signed,*  
**Antigravity (Gemini)** · 2026-11-23
