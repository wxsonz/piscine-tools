# 001 Keep `common/` as it is until after Monday
Status: accepted
Date: 2026-11-22

## Context
The repo root has `common/` (codemap, tracer, skin) shared by rush00 and now
rush01. The Code Book's SHAPE-1 bans pattern names like `common/`, and
codemap has gaps rush01 needs (PLAN.md §7.1).

## Choice
Breaks SHAPE-1 on purpose: `common/` keeps its name and stays read-only for
rush01 until after the Monday 2026-11-23 evaluations. rush01 works around the
gaps inside `tool/detect/`.

## Why
rush00 imports it and works today; renaming or changing it the day before
evaluations risks breaking a working tool. After Monday: fix the gaps in
codemap (with rush00's tests as the pin, PROOF-3) and rename it after its job
(e.g. `creader/`).
