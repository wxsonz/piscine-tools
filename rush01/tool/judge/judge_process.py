"""Run one untrusted process: stdin /dev/null, its own session, a timeout and
an output cap (AGENTS.md rule 7, judge/CONTRACT.md "Rules here"). Also a small
thread pool for many runs. Copied in spirit from rush00's run_capped.
"""

import os
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

RUN_CAP_BYTES = 1_000_000
POOL_WORKERS = 4
READ_CHUNK_BYTES = 65536
DRAIN_JOIN_S = 2


def run_capped(cmd, cwd, timeout_ms, env=None, cap_bytes=RUN_CAP_BYTES):
    """-> {"stdout", "stderr" (bytes, capped), "exit", "signal", "timed_out",
    "over_cap", "time_ms", "error"}. Never raises for the program's fault."""
    result = {"stdout": b"", "stderr": b"", "exit": None, "signal": None,
              "timed_out": False, "over_cap": False, "time_ms": 0, "error": ""}
    # 1. start it in its own session, so the whole group can be killed.
    # No DEBUGINFOD_URLS (set on the 42 iMacs): ASan/valgrind symbolizing would
    # fetch debug info over the network and stall past the timeout.
    env = dict(os.environ if env is None else env)
    env.pop("DEBUGINFOD_URLS", None)
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError as e:
        result["error"] = str(e)
        return result
    start = time.monotonic()
    # 2. drain both pipes; keep at most cap_bytes each, stop the program past it
    over_cap = threading.Event()
    out_buf = bytearray()
    err_buf = bytearray()
    drains = [threading.Thread(target=_drain, daemon=True,
                               args=(proc, pipe, buf, cap_bytes, over_cap))
              for pipe, buf in ((proc.stdout, out_buf), (proc.stderr, err_buf))]
    for t in drains:
        t.start()
    # 3. wait, kill on timeout
    try:
        rc = proc.wait(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        rc = proc.wait()
        result["timed_out"] = True
    result["time_ms"] = int((time.monotonic() - start) * 1000)
    # 4. children it left behind die too; then collect the output
    _kill_group(proc)
    for t in drains:
        t.join(DRAIN_JOIN_S)
    result["stdout"] = bytes(out_buf)
    result["stderr"] = bytes(err_buf)
    result["over_cap"] = over_cap.is_set()
    # 5. exit code or signal; a kill by us is not the program's own signal
    killed_by_us = result["timed_out"] or result["over_cap"]
    if rc >= 0:
        result["exit"] = rc
    elif not killed_by_us:
        result["signal"] = _signal_name(-rc)
    return result


def run_many(jobs, worker):
    """worker(job) for every job, at most POOL_WORKERS at a time, in order."""
    with ThreadPoolExecutor(max_workers=POOL_WORKERS) as pool:
        return list(pool.map(worker, jobs))


def _drain(proc, pipe, buf, cap_bytes, over_cap):
    while True:
        chunk = pipe.read1(READ_CHUNK_BYTES)
        if not chunk:
            break
        room = cap_bytes - len(buf)
        if room > 0:
            buf += chunk[:room]
        if len(chunk) > room:
            over_cap.set()
            _kill_group(proc)
    pipe.close()


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _signal_name(number):
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"signal {number}"
