"""Make malloc fail (the eval sheet: "Check malloc returns and break their
program if possible; if it breaks, select 'Crash'"). The team is built again
with `-Wl,--wrap=malloc` and a small shim: only the team's own malloc calls
go through it, libc's don't. The shim counts the calls and returns NULL on
the Nth. Every N from 1 to the count is run on the PDF example.
"""

import os

from .judge_build import build_binary, first_error
from .judge_process import run_capped, run_many

MFAIL_BINARY = "rush01_mfail"
SHIM_NAME = "rush01_malloc_shim.c"
MALLOC_TRIES_CAP = 24
RUN_MS = 2000
PDF_ARGV = ["4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2"]
SHIM = r"""
#include <stdlib.h>
#include <unistd.h>

void	*__real_malloc(size_t size);

static int	g_rush01_count;
static int	g_rush01_fail_at = -1;

void	*__wrap_malloc(size_t size)
{
	char	*s;

	if (g_rush01_fail_at < 0)
	{
		s = getenv("RUSH01_FAIL_AT");
		g_rush01_fail_at = s ? atoi(s) : 0;
	}
	g_rush01_count++;
	if (g_rush01_count == g_rush01_fail_at)
		return (NULL);
	return (__real_malloc(size));
}

__attribute__((destructor)) static void	rush01_count(void)
{
	char	buf[24];
	int		n;
	int		i;

	if (!getenv("RUSH01_COUNT"))
		return ;
	n = g_rush01_count;
	i = 23;
	buf[i] = '\n';
	do
	{
		buf[--i] = '0' + n % 10;
		n /= 10;
	} while (n);
	write(2, "RUSH01_MALLOCS=", 15);
	write(2, buf + i, 24 - i);
}
"""


def run_malloc_fail(ex_abs, work_abs, cc, sources, uses_malloc):
    """-> {"ran", "mallocs", "tries": [{"nth", "outcome", "signal",
    "stdout"}], "crashes": [nth...], "note"}. outcome: "crash" (a signal),
    "timeout", or "exit N"."""
    result = {"ran": False, "mallocs": None, "tries": [], "crashes": [],
              "note": ""}
    if not uses_malloc:
        result["note"] = "the source never calls malloc: nothing to break"
        return result
    # 1. the shim build
    shim_abs = os.path.join(work_abs, SHIM_NAME)
    with open(shim_abs, "w", encoding="utf-8") as fh:
        fh.write(SHIM)
    built, log = build_binary(ex_abs, [cc, "-Wl,--wrap=malloc", "-o", MFAIL_BINARY],
                              list(sources) + [shim_abs], MFAIL_BINARY)
    if not built:
        result["note"] = "malloc-fail build failed: " + first_error(log)
        return result
    bin_abs = os.path.join(ex_abs, MFAIL_BINARY)
    # 2. count the mallocs of a normal run
    env = dict(os.environ, RUSH01_COUNT="1", RUSH01_FAIL_AT="0")
    raw = run_capped([bin_abs] + PDF_ARGV, ex_abs, RUN_MS, env=env)
    count = _count(raw["stderr"])
    result["ran"] = True
    result["mallocs"] = count
    if count is None:
        result["note"] = "the normal run did not end cleanly: malloc count unknown"
        return result
    if count == 0:
        result["note"] = "no malloc call at run time on the PDF example"
        return result
    # 3. fail the Nth malloc, N = 1..count
    nths = list(range(1, min(count, MALLOC_TRIES_CAP) + 1))
    if count > MALLOC_TRIES_CAP:
        result["note"] = (f"{count} mallocs: only the first "
                          f"{MALLOC_TRIES_CAP} were made to fail")
    raws = run_many(nths, lambda n: run_capped(
        [bin_abs] + PDF_ARGV, ex_abs, RUN_MS,
        env=dict(os.environ, RUSH01_FAIL_AT=str(n))))
    for n, r in zip(nths, raws):
        if r["signal"]:
            outcome = "crash"
        elif r["timed_out"]:
            outcome = "timeout"
        else:
            outcome = f"exit {r['exit']}"
        result["tries"].append({"nth": n, "outcome": outcome,
                                "signal": r["signal"],
                                "stdout": r["stdout"][:200].decode("utf-8", "replace")})
        if outcome in ("crash", "timeout"):
            result["crashes"].append(n)
    return result


def _count(stderr):
    text = stderr.decode("utf-8", "replace")
    for line in reversed(text.splitlines()):
        if line.startswith("RUSH01_MALLOCS="):
            try:
                return int(line.split("=", 1)[1])
            except ValueError:
                return None
    return None
