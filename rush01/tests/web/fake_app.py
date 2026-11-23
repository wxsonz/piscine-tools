"""The fake app dict the web tests (and serve_fixture.py) give web_serve:
evaluate writes a fixture report (tool/SHAPES.md "report") for the team,
clone makes a folder. Everything lives in a temp dir (PROOF-9).

Team names pick the behaviour: d* -> the build-failure fixture, boom* ->
evaluate raises, slow* -> evaluate waits for fake["gate"], else the main one.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RUSH01 = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(RUSH01, "tool"),
           os.path.join(os.path.dirname(RUSH01), "common")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from web import web_serve  # noqa: E402  (after the path set-up above)

FIXTURE = os.path.join(HERE, "fixture_report.json")
FIXTURE_NOBUILD = os.path.join(HERE, "fixture_report_nobuild.json")
CATALOG = [
    {"id": "parse.scan", "part": "parse", "tier": None,
     "name": "Scan and count", "explain": "Walks the string once.",
     "questions": ["How do you count 16?"], "demo": "parse_scan"},
    {"id": "data.grid2d", "part": "data", "tier": None,
     "name": "2D array", "explain": "int grid[4][4] on stack.",
     "questions": ["Why fixed size?"], "demo": "data_grid2d"},
    {"id": "solve.bt_end", "part": "solve", "tier": 1,
     "name": "Backtracking, check at the end",
     "explain": "Checks only when full.",
     "questions": ["When do you reject?"], "demo": "solve_bt_end"},
    {"id": "solve.bt_unique", "part": "solve", "tier": 1,
     "name": "Backtracking + row/col check per placement",
     "explain": "Checks duplicates per cell.",
     "questions": ["Where do you undo?"], "demo": "solve_bt_unique"},
    {"id": "solve.bt_clue_line", "part": "solve", "tier": 1,
     "name": "Backtracking + clue check when a line is full",
     "explain": "Checks row/col clues at line end.",
     "questions": ["When do you check a row?"], "demo": "solve_bt_clue_line"},
    {"id": "solve.prefill", "part": "solve", "tier": 2,
     "name": "Pre-fill rules, then search",
     "explain": "Fills forced cells first.",
     "questions": ["Which rules apply?"], "demo": "solve_prefill"},
    {"id": "print.char", "part": "print", "tier": None,
     "name": "One write per char", "explain": "write(1, &c, 1) per char.",
     "questions": ["How many writes?"], "demo": "print_char"},
]


def fake_make(root):
    """A repo with c01 (main fixture) and d3 (does not build)."""
    repo = os.path.join(root, "repo")
    reports = os.path.join(root, "reports")
    os.makedirs(repo)
    shutil.copytree(os.path.join(HERE, "fixture_team"),
                    os.path.join(repo, "c01"))
    shutil.copytree(os.path.join(HERE, "fixture_nobuild"),
                    os.path.join(repo, "d3"))
    fake = {"calls": [], "gate": threading.Event(), "repo": repo,
            "reports": reports}

    def evaluate(team_dir_abs):
        name = os.path.basename(team_dir_abs)
        fake["calls"].append(name)
        if name.startswith("boom"):
            raise RuntimeError("evaluate failed on purpose")
        if name.startswith("slow"):
            fake["gate"].wait(30)
        src = FIXTURE_NOBUILD if name.startswith("d") else FIXTURE
        with open(src, encoding="utf-8") as fh:
            report = json.load(fh)
        report["team"] = name
        report["team_dir_abs"] = team_dir_abs
        report["made_at"] = time.strftime("%Y-%m-%dT%H:%M:%S") + \
            ".%d" % len(fake["calls"])
        os.makedirs(reports, exist_ok=True)
        with open(os.path.join(reports, name + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(report, fh)
        return report

    def clone(url):
        name = url.rstrip("/").split("/")[-1].replace(".git", "")
        path = os.path.join(repo, name)
        shutil.copytree(os.path.join(HERE, "fixture_team"), path)
        return path

    fake["app"] = {"repo_dir_abs": repo, "report_dir_abs": reports,
                   "evaluate": evaluate, "clone": clone, "catalog": CATALOG}
    return fake


def fake_serve(app):
    """web_serve on a free port in a daemon thread; returns the base URL."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    threading.Thread(target=web_serve, args=(app, port), daemon=True).start()
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return f"http://127.0.0.1:{port}"
        except OSError:
            time.sleep(0.05)
    raise AssertionError("web_serve did not start")


def fake_get(url, headers=None):
    """(status, body bytes); errors are statuses, not exceptions."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fake_post(url, obj, ctype="application/json"):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def fake_state(base):
    code, body = fake_get(base + "/api/state")
    assert code == 200, code
    return {t["name"]: t for t in json.loads(body)["teams"]}


def fake_wait(fn, timeout_s=15, what="condition"):
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        got = fn()
        if got:
            return got
        time.sleep(0.1)
    raise AssertionError("timed out waiting for " + what)


def fake_wait_status(base, name, statuses, timeout_s=15):
    return fake_wait(lambda: name in fake_state(base)
                     and fake_state(base)[name]["status"] in statuses,
                     timeout_s, f"{name} to be {statuses}")


def fake_browser_tools():
    """(node, playwright-core dir, chromium) or a reason to skip (str)."""
    if os.environ.get("RUSH01_NO_BROWSER"):
        return "RUSH01_NO_BROWSER is set"
    pw = os.environ.get("PLAYWRIGHT_CORE", os.path.expanduser(
        "~/42me/ft_blueprint/node_modules/playwright-core"))
    chrome = (shutil.which("chromium") or shutil.which("google-chrome")
              or shutil.which("chromium-browser"))
    node = shutil.which("node")
    if not (node and os.path.isdir(pw) and chrome):
        return "needs node, playwright-core (PLAYWRIGHT_CORE) and chromium"
    return node, pw, chrome


def fake_browser(tools, base, mode):
    """Run browser_check.cjs; returns its JSON result."""
    node, pw, chrome = tools
    script = os.path.join(HERE, "browser_check.cjs")
    p = subprocess.run([node, script, pw, chrome, base, mode],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(p.stdout.strip().split("\n")[-1])
    except (ValueError, IndexError):
        raise AssertionError("browser check crashed:\n" + p.stdout[-1500:]
                             + p.stderr[-1500:])
