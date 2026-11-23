"""Which tools this machine has (judge/CONTRACT.md judge_tools). ASan counts
only when a tiny program really builds with -fsanitize=address,undefined and
runs (the 42 iMac may lack the runtime; PLAN.md §2).
"""

import os
import shutil
import tempfile

from .judge_process import run_capped

SANITIZE_FLAGS = ["-g", "-fsanitize=address,undefined"]
PROBE_SOURCE = "int\tmain(void)\n{\n\treturn (0);\n}\n"
PROBE_BUILD_MS = 60_000
PROBE_RUN_MS = 10_000


def judge_tools():
    """-> {"cc", "norminette", "valgrind", "asan": bool} for the default cc."""
    return probe_tools("cc")


def probe_tools(cc):
    """The same, for the compiler the subject builds with."""
    tools = {"cc": shutil.which(cc) is not None,
             "norminette": shutil.which("norminette") is not None,
             "valgrind": shutil.which("valgrind") is not None,
             "asan": False}
    if tools["cc"]:
        tools["asan"] = probe_asan(cc)
    return tools


def probe_asan(cc):
    """True when cc links and runs a sanitizer build of an empty main."""
    with tempfile.TemporaryDirectory(prefix="rush01-asan-probe-") as tmp:
        # 1. build the probe
        with open(os.path.join(tmp, "probe.c"), "w", encoding="utf-8") as fh:
            fh.write(PROBE_SOURCE)
        built = run_capped([cc] + SANITIZE_FLAGS + ["-o", "probe", "probe.c"],
                           tmp, PROBE_BUILD_MS)
        if built["exit"] != 0:
            return False
        # 2. run it: a missing runtime library fails here, not at link time
        ran = run_capped([os.path.join(tmp, "probe")], tmp, PROBE_RUN_MS)
        return ran["exit"] == 0
