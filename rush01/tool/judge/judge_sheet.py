"""What the eval sheet (intra, 2026-11-22) makes of the judge result: the
stops ("evaluation is over / stops", "no points") and the bonus size. Pure:
reads the result, returns values.
"""

EXTRA_GROUPS = ("small", "bonusN")      # not mandatory
ELIMINATORY = "evalsheet"


def sheet_stops(result, subject):
    """-> [{"key", "level", "text", "sheet"}] in the sheet's order.
    level "stop": the sheet ends the evaluation or gives no points;
    "check": the evaluator decides (the sheet asks to check, or only the
    subject says it)."""
    stops = []
    files = result["files"] or {}
    want = subject["turn_in_dir"]
    # 1. preliminaries: nothing submitted / wrong directory
    if files.get("no_ex_dir"):
        stops.append(_stop("no_ex_dir", "stop", f"no {want}/ folder",
                           "Nothing submitted (or wrong file or directory): "
                           "0, evaluation is over."))
    if not files.get("sources"):
        stops.append(_stop("no_sources", "stop", "no .c file to build",
                           "Nothing submitted: 0, evaluation is over."))
    # 2. preliminaries: norm
    norm = result["norm"] or {}
    if norm.get("ran") and not norm.get("ok"):
        text = f"{len(norm['errors'])} norm error(s)"
        if norm.get("note"):
            text = f"norm errors: {norm['note']}"
        stops.append(_stop("norm", "stop", text,
                           "Norm error: evaluation stops."))
    # 3. preliminaries: extraneous files
    flagged = files.get("flagged") or []
    if flagged:
        names = ", ".join(f"{f['path']} ({f['why']})" for f in flagged[:6])
        more = f" and {len(flagged) - 6} more" if len(flagged) > 6 else ""
        stops.append(_stop("files", "check", names + more,
                           "No extraneous files in the repository, such as "
                           "unused, hidden, or temporary files."))
    # 4. it must build to be tested at all
    if files.get("sources") and not result["built"]:
        first = (result["build_log"].strip().splitlines() or ["?"])[0]
        stops.append(_stop("build", "stop", "does not build: " + first[:160],
                           "Nothing to test: no binary."))
    # 5. forbidden functions: the subject's rule, not the sheet's
    names = sorted({x["name"] for x in (result["forbidden"] or {}).get("names", [])})
    if names:
        stops.append(_stop("forbidden", "check",
                           "calls " + ", ".join(names),
                           "Subject: allowed functions are "
                           + ", ".join(subject["allowed"]) + "."))
    # 6. eliminatory tests
    failed = [r["id"] for r in result["runs"]
              if r["group"] == ELIMINATORY and r["verdict"] == "fail"]
    if failed:
        stops.append(_stop("eliminatory", "stop",
                           f"{len(failed)} eliminatory test(s) failed: "
                           + ", ".join(failed),
                           "If you encounter any problem, discuss it with the "
                           "students, but don't give them any points."))
    return stops


def sheet_mandatory_ok(result, stops):
    """True when nothing stops and every mandatory run passes."""
    if any(s["level"] == "stop" for s in stops) or not result["runs"]:
        return False
    return all(r["verdict"] != "fail" for r in result["runs"]
               if r["group"] not in EXTRA_GROUPS)


def sheet_bonus(result, bank, subject, stops):
    """-> {"sizes": {"5": "pass"|"fail"}, "largest_n", "counted", "note"}.
    Sizes are the subject's bonus_sizes. largest_n: the biggest N such
    that every bonus puzzle of size 5..N
    passes (null when 5 already fails). counted: only when everything
    mandatory passed (the sheet: "ONLY for those who validated all the
    previous questions")."""
    sizes = {}
    by_id = {e["id"]: e for e in bank}
    for run in result["runs"]:
        entry = by_id.get(run["id"])
        if run["group"] != "bonusN" or not entry \
                or entry.get("n") not in subject["bonus_sizes"]:
            continue
        key = str(entry["n"])
        ok = run["verdict"] == "pass"
        sizes[key] = "pass" if ok and sizes.get(key, "pass") == "pass" else "fail"
    largest = None
    for n in sorted(int(k) for k in sizes):
        if sizes[str(n)] != "pass":
            break
        largest = n
    counted = sheet_mandatory_ok(result, stops)
    stopped = [s["key"] for s in stops if s["level"] == "stop"]
    if not sizes:
        note = "no bonus runs"
    elif counted:
        note = ""
    elif stopped:
        note = "not counted: the evaluation stops (" + ", ".join(stopped) + ")"
    else:
        note = "not counted: the mandatory part does not fully pass"
    return {"sizes": sizes, "largest_n": largest, "counted": counted,
            "note": note}


def _stop(key, level, text, sheet):
    return {"key": key, "level": level, "text": text, "sheet": sheet}
