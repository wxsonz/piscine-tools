"""judge_team: build one team's turn-in in the work dir and judge it against
the puzzle bank (PLAN.md §6 steps 1-9, judge/CONTRACT.md, SHAPES "judge
result"). Never raises for the team's fault: failures are in the result.
"""

import os

from puzzle import puzzle_diagnose

from .judge_build import build_binary
from .judge_files import copy_team, find_ex_dir, list_files
from .judge_forbidden import check_forbidden
from .judge_malloc import run_malloc_fail
from .judge_norm import run_norm
from .judge_probe import probe_tools
from .judge_process import run_capped, run_many
from .judge_sanitize import run_sanitizer
from .judge_sheet import sheet_bonus, sheet_stops
from .judge_verdict import (count_groups, diagnosis_cases, judge_run,
                            sum_timing)


def judge_team(team_dir_abs, subject, bank, work_dir_abs):
    """-> judge result (SHAPES). The team folder is only read; everything is
    built and run in a copy under work_dir_abs."""
    cc = subject["build"][0]
    result = {"ex_dir": ".", "built": False, "build_log": "", "files": None,
              "forbidden": None, "norm": None, "sanitizer": None, "runs": [],
              "groups": {}, "timing": sum_timing([]), "diagnosis": None,
              "malloc_fail": {"ran": False, "mallocs": None, "tries": [],
                              "crashes": [], "note": "build failed: skipped"},
              "stops": [], "bonus": None, "tools": probe_tools(cc)}
    # 1. find ex00/, list and flag the files
    ex_dir, no_ex_dir = find_ex_dir(team_dir_abs, subject["turn_in_dir"])
    result["ex_dir"] = ex_dir
    result["files"] = list_files(team_dir_abs, ex_dir, subject["turn_in_dir"])
    result["files"]["no_ex_dir"] = no_ex_dir
    sources = [os.path.basename(rel) for rel in result["files"]["sources"]]
    # 2. copy the team and build the copy with the official command
    try:
        copy_abs = copy_team(team_dir_abs, work_dir_abs)
    except OSError as e:
        copy_abs = None
        result["build_log"] = f"could not copy the team to the work dir: {e}"
    ex_abs = os.path.join(copy_abs or team_dir_abs, ex_dir)
    if copy_abs is not None:
        result["built"], result["build_log"] = build_binary(
            ex_abs, list(subject["build"]), sources, subject["binary"])
    binary_abs = os.path.join(ex_abs, subject["binary"]) if result["built"] else None
    # 3. forbidden functions: the linked binary and the source
    result["forbidden"] = check_forbidden(copy_abs or team_dir_abs, result["files"],
                                          binary_abs, subject["allowed"])
    # 4. norminette
    result["norm"] = run_norm(ex_abs, ex_dir, result["files"], subject["norm_flags"])
    if not result["built"]:
        result["sanitizer"] = {"ran": False, "findings": [],
                               "note": "build failed: skipped"}
        result["stops"] = sheet_stops(result, subject)
        result["bonus"] = sheet_bonus(result, bank, subject, result["stops"])
        return result
    # 5. run the bank and 7. judge every run
    raws = run_many(bank, lambda entry: run_capped(
        [binary_abs] + entry["argv"], ex_abs, entry["timeout_ms"]))
    result["runs"] = [judge_run(entry, raw, subject) for entry, raw in zip(bank, raws)]
    # 6. sanitizer build on three paths
    result["sanitizer"] = run_sanitizer(ex_abs, copy_abs, cc, sources, bank,
                                        result["tools"], binary_abs)
    # 6b. make the team's mallocs fail, one at a time
    result["malloc_fail"] = run_malloc_fail(ex_abs, work_dir_abs, cc, sources,
                                            _mentions(ex_abs, sources, "malloc"))
    # 8. diagnosis and 9. the sums
    result["diagnosis"] = puzzle_diagnose(
        diagnosis_cases(result["runs"], bank, subject["error_text"]))
    result["groups"] = count_groups(result["runs"])
    result["timing"] = sum_timing(result["runs"])
    # 10. what the eval sheet makes of it
    result["stops"] = sheet_stops(result, subject)
    result["bonus"] = sheet_bonus(result, bank, subject, result["stops"])
    return result


def _mentions(ex_abs, sources, word):
    for name in sources:
        try:
            with open(os.path.join(ex_abs, name), encoding="utf-8",
                      errors="replace") as fh:
                if word in fh.read():
                    return True
        except OSError:
            pass
    return False
