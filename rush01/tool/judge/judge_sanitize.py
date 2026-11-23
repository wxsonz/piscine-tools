"""Sanitizer build and runs (PLAN.md §6 step 6): -g -fsanitize=address,undefined
on one ok4, one nosol4, and "" "1" "4 3". LeakSanitizer dies where ptrace is
blocked: then retry with detect_leaks=0 and look for leaks with valgrind.
"""

import json
import os
import re

from .judge_build import build_binary, first_error
from .judge_probe import SANITIZE_FLAGS
from .judge_process import run_capped, run_many

SAN_BINARY = "rush01_sanitize"
SAN_SLOWDOWN = 3
VALGRIND_SLOWDOWN = 10
VALGRIND_MIN_MS = 10_000
SHORT_ARGVS = ([""], ["1"], ["4 3"])
SHORT_TIMEOUT_MS = 2000
UB_PER_CASE_CAP = 3
LSAN_FATAL = "LeakSanitizer has encountered a fatal error"
ASAN_ERROR = re.compile(r"ERROR: AddressSanitizer: ([\w-]+)")
LSAN_ERROR = re.compile(r"ERROR: LeakSanitizer: detected memory leaks")
SUMMARY = re.compile(r"SUMMARY: (?:Address|Leak)Sanitizer: (.*)")
UB_ERROR = re.compile(r"\S*runtime error: .*")
VALGRIND_LOST = re.compile(r"definitely lost: ([\d,]+) bytes in ([\d,]+) blocks")


def run_sanitizer(ex_abs, copy_abs, cc, sources, bank, tools, binary_abs):
    """-> the "sanitizer" part of the judge result (SHAPES). binary_abs is
    the normal build (for valgrind)."""
    result = {"ran": False, "findings": [], "note": ""}
    notes = []
    leaks = []
    # 1. a sanitizer build, if this machine can make one
    if not tools["asan"]:
        result["note"] = ("ASan not available here (a test program did not build "
                          "and run with -fsanitize=address,undefined): skipped")
        return result
    built, log = build_binary(ex_abs, [cc] + SANITIZE_FLAGS + ["-o", SAN_BINARY],
                              sources, SAN_BINARY)
    if not built:
        result["note"] = "sanitizer build failed: " + first_error(log)
        return result
    result["ran"] = True
    cases = pick_cases(bank)
    san_abs = os.path.join(ex_abs, SAN_BINARY)
    # 2. run the cases with LeakSanitizer on
    raws = _run_cases(san_abs, ex_abs, cases, "detect_leaks=1")
    # 3. LSan could not run here: again without it, leaks from valgrind
    if any(LSAN_FATAL in raw["stderr"].decode("utf-8", "replace") for raw in raws):
        raws = _run_cases(san_abs, ex_abs, cases, "detect_leaks=0")
        notes.append("LeakSanitizer hit a fatal error (ptrace blocked?): "
                     "re-ran with ASAN_OPTIONS=detect_leaks=0")
        if tools["valgrind"]:
            leaks = _valgrind_leaks(binary_abs, ex_abs, cases)
            notes.append("leaks checked with valgrind")
        else:
            notes.append("valgrind not installed: leaks not checked")
    # 4. what the sanitizers said, case by case
    for case, raw in zip(cases, raws):
        stderr = raw["stderr"].decode("utf-8", "replace")
        result["findings"] += parse_findings(case["id"], stderr, copy_abs)
    result["findings"] += leaks
    result["note"] = "; ".join(notes)
    return result


def pick_cases(bank):
    """One ok4, one nosol4 (easy first), then "" "1" "4 3": the bank's entry
    when it has that argv, else a made-up one named after the argument."""
    ok = [e for e in bank if e["group"] == "ok4"]
    nosol = ([e for e in bank if e["group"] == "nosol4-easy"]
             or [e for e in bank if e["group"] == "nosol4-deep"])
    cases = ok[:1] + nosol[:1]
    for argv in SHORT_ARGVS:
        found = [e for e in bank if e["argv"] == argv]
        cases.append(found[0] if found else {
            "id": "arg " + json.dumps(argv[0]), "group": "", "argv": argv,
            "timeout_ms": SHORT_TIMEOUT_MS})
    return cases


def parse_findings(case_id, stderr, copy_abs):
    """ASan errors (kind = its name), leaks, UBSan runtime errors."""
    findings = []
    lines = stderr.replace(copy_abs + os.sep, "").split("\n")
    ub_count = 0
    for i, line in enumerate(lines):
        asan = ASAN_ERROR.search(line)
        if asan or LSAN_ERROR.search(line):
            kind = asan.group(1) if asan else "memory-leak"
            summary = next((m.group(1) for m in map(SUMMARY.search, lines[i + 1:]) if m),
                           line.strip())
            findings.append({"case": case_id, "kind": kind, "text": summary})
            continue
        ub = UB_ERROR.search(line)
        if ub and ub_count < UB_PER_CASE_CAP:
            ub_count += 1
            findings.append({"case": case_id, "kind": "undefined-behavior",
                             "text": ub.group(0)})
    return findings


def _run_cases(san_abs, ex_abs, cases, leaks_option):
    env = dict(os.environ, ASAN_OPTIONS=leaks_option + ":abort_on_error=0",
               UBSAN_OPTIONS="print_stacktrace=0")
    return run_many(cases, lambda case: run_capped(
        [san_abs] + case["argv"], ex_abs, case["timeout_ms"] * SAN_SLOWDOWN, env))


def _valgrind_leaks(binary_abs, ex_abs, cases):
    def one(case):
        timeout_ms = max(VALGRIND_MIN_MS, case["timeout_ms"] * VALGRIND_SLOWDOWN)
        return run_capped(["valgrind", "--leak-check=full", binary_abs] + case["argv"],
                          ex_abs, timeout_ms)
    findings = []
    for case, raw in zip(cases, run_many(cases, one)):
        m = VALGRIND_LOST.search(raw["stderr"].decode("utf-8", "replace"))
        if m and m.group(1).replace(",", "") != "0":
            findings.append({"case": case["id"], "kind": "memory-leak",
                             "text": f"valgrind: definitely lost: {m.group(1)} bytes "
                                     f"in {m.group(2)} blocks"})
    return findings
