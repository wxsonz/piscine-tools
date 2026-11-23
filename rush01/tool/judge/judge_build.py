"""Build the copied turn-in (PLAN.md §6 step 2; the sanitizer build of step 6
uses the same function). first_error is copied from rush00.
"""

import os
import re

from .judge_process import run_capped

BUILD_MS = 120_000
BUILD_LOG_CAP = 8000
ANSI = re.compile(r"\x1b\[[0-9;]*[mK]")


def build_binary(ex_abs, cmd_head, sources, binary):
    """cmd_head + sources, in ex_abs; -> (built, build_log). The log starts
    with the first error line, then the whole compiler output (capped)."""
    # 1. never run a binary the team handed in
    out_abs = os.path.join(ex_abs, binary)
    if os.path.lexists(out_abs):
        os.remove(out_abs)
    if not sources:
        return False, "no .c files to build"
    # 2. compile
    r = run_capped(cmd_head + sources, ex_abs, BUILD_MS)
    log = ANSI.sub("", (r["stdout"] + r["stderr"]).decode("utf-8", "replace"))
    if r["error"]:
        return False, f"could not start the compiler: {r['error']}"
    if r["timed_out"]:
        return False, f"the build timed out after {BUILD_MS // 1000} s\n" + log[:BUILD_LOG_CAP]
    built = r["exit"] == 0 and os.path.isfile(out_abs)
    if built:
        return True, log[:BUILD_LOG_CAP]
    head = first_error(log) or f"the compiler exited with {r['exit']} and no message"
    return False, head + "\n\n" + log[:BUILD_LOG_CAP]


def first_error(log):
    lines = [line for line in log.split("\n") if line.strip()]
    for line in sorted(lines, key=lambda line: (
            line.startswith("collect2"),
            not re.search(r"undefined reference|multiple definition", line))):
        if re.search(r"error|undefined reference|multiple definition", line, re.I):
            return re.sub(r"^/usr/bin/ld: (/tmp/\S+: )?", "", line).strip()[:200]
    return (lines[0] if lines else "")[:200]
