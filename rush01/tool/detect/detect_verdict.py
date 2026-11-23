"""detect_team: read a team, find the roles, run the rules, and build the
detect result of tool/SHAPES.md (PLAN.md §7.2 step 5). Never raises (B13).
"""

import os

import codemap

from .detect_ask import ask_lines
from .detect_catalog import catalog_by_id, catalog_part_questions
from .detect_facts import facts_data, facts_parse, facts_print, facts_solve
from .detect_hits import ev_file
from .detect_read import read_int, read_team
from .detect_roles import roles_find
from .detect_rules import RULES, rules_context
from .detect_rules_print import rules_print_walk
from .detect_shapes import shapes_nest

PARTS = ["parse", "data", "solve", "print"]
EVIDENCE_CAP = 5
BONUS_DIMS = {9, 36, 81}       # a 9x9 grid, its 36 clues, its 81 cells


def detect_team(team_dir_abs, ex_dir):
    """Name the approach of each part of a team's code (SHAPES "detect
    result"). A crash becomes `error` with every part unrecognized."""
    try:
        return verdict_team(team_dir_abs, ex_dir)
    except Exception as e:     # B13: never raise, whatever the input
        return verdict_failed(f"detection crashed: {type(e).__name__}: {e}",
                              verdict_first_file(team_dir_abs, ex_dir))


def verdict_first_file(team_dir_abs, ex_dir):
    """`where` after a crash: the first .c file, if one can be listed."""
    try:
        folder = os.path.join(team_dir_abs, ex_dir or "")
        names = sorted(n for n in os.listdir(folder) if n.endswith(".c"))
    except (OSError, TypeError):
        return []
    if not names:
        return []
    rel = os.path.join(ex_dir, names[0]) if ex_dir else names[0]
    return [{"file": rel, "func": None, "line": 1}]


def verdict_team(team_dir_abs, ex_dir):
    # 1. read; files that are not C stop the detection with a message
    team, problems = read_team(team_dir_abs, ex_dir)
    if problems:
        first = problems[0].split(":", 1)[0]
        return verdict_failed("; ".join(problems),
                              [{"file": first, "func": None, "line": 1}])
    if not any(f["rel"].endswith(".c") for f in team["files"]):
        folder = team["ex_dir"] or "the team folder"
        return verdict_failed(f"no .c file in {folder}", [])

    # 2. roles, shared shapes, then every rule of every part
    roles = roles_find(team)
    cx = rules_context(team, roles)
    facts = {"parse": facts_parse(cx), "data": facts_data(cx),
             "solve": facts_solve(cx), "print": facts_print(cx)}
    parts = {}
    for part in PARTS:
        hits = [h for h in (rule(cx) for rule in RULES[part]) if h]
        also = [h for h in (rule(cx) for rule in RULES.get(part + "_also",
                                                           [])) if h]
        parts[part] = verdict_part(cx, part, hits, also, facts[part],
                                   verdict_fallback(cx, part))
    return {"parts": parts, "project": verdict_project(team, cx, facts),
            "error": None}


def verdict_part(cx, part, hits, also, facts, fallback):
    """Pick the best hit; add the 'also' entries (prefill + its search,
    a grid + its candidate lists) as a mix."""
    # 1. the main entry and the ones reported with it
    ordered = sorted(hits, key=lambda h: -h["score"])
    if part == "solve" and also:
        main, others = also[0], ordered[:1]
    elif ordered:
        main, others = ordered[0], also
    elif also:
        main, others = also[0], also[1:]
    else:
        return verdict_unrecognized(part, fallback, facts)
    # 2. evidence: 2-5 lines, main first, no line twice
    evidence = []
    seen = set()
    for h in [main] + others:
        for e in h["evidence"]:
            key = (e["file"], e["line"])
            if key not in seen and len(evidence) < EVIDENCE_CAP:
                seen.add(key)
                evidence.append(e)
    wheres = []
    for h in [main] + others:
        for w in h["where"]:
            if w not in wheres:
                wheres.append(w)
    wheres = wheres or fallback
    if len(evidence) < 2 and wheres:
        w = wheres[0]
        evidence.append(ev_file(cx["team"], w["file"], w["line"],
                                "the function where this happens"))
    # 3. the verdict, with the catalog's text
    cat = catalog_by_id()
    entry = cat[main["id"]]
    questions = list(entry["questions"])
    for h in others:
        questions.append(cat[h["id"]]["questions"][0])
    hit_facts = [f for h in [main] + others for f in h["facts"]]
    keys = {f["key"] for f in hit_facts}
    if others:
        confidence = "mix"
    elif main["support"] >= 1:
        confidence = "clear"
    else:
        confidence = "likely"
    explain = entry["explain"]
    if others:
        explain += " Then: " + " / ".join(cat[h["id"]]["name"]
                                           for h in others) + "."
    return {"id": main["id"], "name": entry["name"],
            "tier": entry["tier"] if part == "solve" else None,
            "confidence": confidence, "also": [h["id"] for h in others],
            "where": wheres, "evidence": evidence,
            "facts": hit_facts + [f for f in facts if f["key"] not in keys],
            "explain": explain, "questions": questions}


def verdict_unrecognized(part, wheres, facts):
    w = wheres[0] if wheres else None
    if w and w.get("func"):
        look = f"look at {w['func']}() in {w['file']}"
    elif w:
        look = f"look at {w['file']}"
    else:
        look = "no function to point at"
    return {"id": None, "name": "unrecognized", "tier": None,
            "confidence": "unrecognized", "also": [], "where": wheres,
            "evidence": [], "facts": facts,
            "explain": f"No catalog entry matches this code: {look}.",
            "questions": catalog_part_questions(part)}


def verdict_fallback(cx, part):
    """The most likely function for a part, for `where`."""
    roles = cx["roles"]
    team = cx["team"]
    pick = None
    if part == "parse":
        pick = (roles["parse"] or [None])[0] or roles["main"]
    elif part == "data":
        if cx["grid"]:
            pick = cx["grid"]["writes"][0][0]
        else:
            pick = (roles["rec"] or roles["solve"] or [None])[0]
    elif part == "solve":
        if roles["rec"]:
            pick = roles["rec"][0]
        elif roles["solve"]:
            pick = max(roles["solve"], key=lambda f: (shapes_nest(team, f),
                                                      f["nlines"]))
    elif part == "print":
        pick = rules_print_walk(cx) or (roles["writers"] or [None])[0]
    pick = pick or roles["main"] or (team["funcs"] or [None])[0]
    if pick:
        return [{"file": pick["file"], "func": pick["name"],
                 "line": pick["line"]}]
    first = next(f for f in team["files"] if f["rel"].endswith(".c"))
    return [{"file": first["rel"], "func": None, "line": 1}]


def verdict_failed(message, wheres):
    parts = {p: verdict_unrecognized(p, wheres, []) for p in PARTS}
    project = {"globals": [], "structs": [], "defines": [], "functions": 0,
               "longest": None, "never_freed": False, "bonus": False,
               "authors": None, "commits": None, "ask": []}
    return {"parts": parts, "project": project, "error": message}


def verdict_project(team, cx, facts):
    """The project strip: globals, structs, defines, sizes, memory, bonus,
    authorship (PLAN.md §7.3), and the lines to ask about (eval sheet)."""
    funcs = team["funcs"]
    # 1. sizes
    longest = None
    if funcs:
        f = max(funcs, key=lambda x: x["nlines"])
        longest = {"name": f["name"], "file": f["file"], "lines": f["nlines"]}
    # 2. memory: malloc with no free anywhere
    calls = {c["name"] for f in funcs for c in f["calls"]}
    never_freed = "malloc" in calls and "free" not in calls
    # 3. bonus: N from the input, or arrays sized for 9x9
    bonus = cx["n_computed"] is not None
    decls = [d for f in funcs for d in f["decls"]]
    decls += [g["decl"] for g in team["globals"]]
    for d in decls:
        if any(read_int(x, team["defines"]) in BONUS_DIMS for x in d["dims"]):
            bonus = True
    # 4. authorship from git, when the team folder is its own repo
    authors, commits = verdict_authors(team)
    return {"globals": [{"file": g["file"], "line": g["line"],
                         "text": g["text"]} for g in team["globals"]],
            "structs": [{"file": s["file"], "line": s["line"],
                         "name": s["name"]} for s in team["structs"]],
            "defines": [{"file": d["file"], "line": d["line"],
                         "name": d["name"], "value": d["value"]}
                        for d in team["define_list"]],
            "functions": len(funcs), "longest": longest,
            "never_freed": never_freed, "bonus": bonus,
            "authors": authors, "commits": commits,
            "ask": ask_lines(team)}


def verdict_authors(team):
    """% of function lines per author (git blame) and the commit count."""
    parsed = team.get("parsed") or []
    if not parsed or not os.path.isdir(os.path.join(team["dir"])):
        return None, None
    log = codemap.attach_authors(parsed, team["dir"])
    if log is None:
        return None, None
    lines = {}
    for P in parsed:
        for fn in P.funcs:
            for name, count in fn.authors.items():
                lines[name] = lines.get(name, 0) + count
    total = sum(lines.values())
    authors = {k: round(100 * v / total) for k, v in sorted(lines.items())} \
        if total else {}
    return authors, sum(log.values())
