"""rush00 web visualizer:  `rush00 serve [--port N] [--open]`

  /                  dashboard: drop team folders / paste a git URL, every team as a card
  /team/<name>       the algorithm visualizer for that team (trace of its real code)
  /report/<name>     the static evaluation report (checklist, tests, structure)

Teams live in rush00/repo/. Anything that appears or changes there (dropped in
the browser, cloned, or copied in with a file manager) is re-evaluated in the
background. Binds to 127.0.0.1 only.
"""

import base64
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import ctrace as rtrace  # rush/common/ctrace.py (on sys.path via rush00)

WWW = os.path.join(os.path.dirname(os.path.realpath(__file__)), "www")
MAX_BODY = 60 * 1024 * 1024
TEAM_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,80}$")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
         ".ttf": "font/ttf", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}


class App:
    def __init__(self, R, port):
        self.R = R
        self.port = port
        self.status = {}        # team -> queued|running|cloning|done|skipped|error
        self.errors = {}
        self.sigs = {}
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.trace_cache = {}
        self.trace_lock = threading.Lock()
        self.state_file = os.path.join(R.REPORT_DIR, ".state.json")
        try:
            with open(self.state_file) as f:
                self.sigs = json.load(f)
        except (OSError, ValueError):
            self.sigs = {}

    # ---------------------------------------------------------------- teams
    def team_names(self):
        if not os.path.isdir(self.R.REPO_DIR):
            return []
        return [d for d in sorted(os.listdir(self.R.REPO_DIR))
                if not d.startswith(".") and os.path.isdir(os.path.join(self.R.REPO_DIR, d))]

    def team_path(self, name):
        if not TEAM_NAME.match(name or ""):
            raise ValueError("bad team name")
        return os.path.join(self.R.REPO_DIR, name)

    def newest_mtime(self, name):
        m = 0
        for dp, dns, fns in os.walk(self.team_path(name)):
            dns[:] = [d for d in dns if d != ".git"]
            for f in fns:
                try:
                    m = max(m, os.stat(os.path.join(dp, f)).st_mtime_ns)
                except OSError:
                    pass
        return m

    def sig(self, name, meta):
        def mt(p):
            try:
                return os.stat(p).st_mtime_ns
            except OSError:
                return 0
        tool = max(mt(self.R.__file__), mt(os.path.join(self.R.ROOT_DIR, "common", "codemap.py")))
        return (f"{self.newest_mtime(name)}|{mt(self.R.SUBJECT)}|{tool}|"
                f"{json.dumps(meta.get(name, {}), sort_keys=True)}")

    def set(self, name, st, err=None):
        with self.lock:
            self.status[name] = st
            if err:
                self.errors[name] = err
            else:
                self.errors.pop(name, None)

    def enqueue(self, name):
        with self.lock:
            if self.status.get(name) in ("queued", "running", "cloning"):
                return
            self.status[name] = "queued"
        self.q.put(name)

    def worker(self):
        while True:
            name = self.q.get()
            self.set(name, "running")
            meta = self.R.load_teams_file()
            s = None
            try:
                path = self.team_path(name)
                if not os.path.isdir(path):
                    with self.lock:
                        self.status.pop(name, None)
                    continue
                s = self.sig(name, meta)
                S = self.R.Subject.load()
                if not self.R.find_ex_dir(path, S.cfg["dir"]):
                    self.drop_reports(name)
                    self.set(name, "skipped", "no rushNN.c anywhere in this folder")
                else:
                    self.R.evaluate(path, S, None, None, True, meta)
                    self.R.write_index(S)
                    self.set(name, "done")
            except Exception:  # noqa: BLE001
                self.set(name, "error", traceback.format_exc())
            if s:
                self.sigs[name] = s
                try:
                    os.makedirs(self.R.REPORT_DIR, exist_ok=True)
                    with open(self.state_file, "w") as f:
                        json.dump(self.sigs, f)
                except OSError:
                    pass

    def scanner(self):
        while True:
            try:
                meta = self.R.load_teams_file()
                now = time.time_ns()
                for name in self.team_names():
                    if self.status.get(name) in ("queued", "running", "cloning"):
                        continue
                    if now - self.newest_mtime(name) < 1_500_000_000:
                        continue  # still being copied in: wait until it settles
                    if self.sigs.get(name) != self.sig(name, meta):
                        self.enqueue(name)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            time.sleep(2)

    def drop_reports(self, name):
        for ext in (".html", ".json"):
            try:
                os.remove(os.path.join(self.R.REPORT_DIR, name + ext))
            except OSError:
                pass

    def summary(self, name):
        try:
            with open(os.path.join(self.R.REPORT_DIR, name + ".json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    # ---------------------------------------------------------------- api
    def api_state(self):
        S = self.R.Subject.load()
        meta = self.R.load_teams_file()
        teams = []
        for name in self.team_names():
            with self.lock:
                st = self.status.get(name, "done" if self.summary(name) else "new")
                err = self.errors.get(name)
            teams.append({"name": name, "status": st, "error": err, "summary": self.summary(name),
                          "meta": meta.get(name, {})})
        rushes = {}
        for n, d in S.derived.items():
            rushes[n] = {"pattern": ["".join(r) for r in d["pattern"]] if d["pattern"] else None,
                         "notes": d["notes"], "examples": len(d["valid_examples"]),
                         "generate": d["generate"]}
        return {"teams": teams, "repo": self.R.REPO_DIR,
                "subject": {"loaded": S.loaded, "cfg": S.cfg, "rushes": rushes, "notes": S.notes}}

    def api_upload(self, body):
        name = (body.get("team") or "").strip()
        self.team_path(name)
        files = body.get("files") or []
        if not files:
            raise ValueError("no files")
        dest = self.team_path(name)
        if os.path.exists(dest):
            if not body.get("replace"):
                return 409, {"error": "exists", "team": name}
            self.trash(name)
        written = 0
        for item in files:
            rel = os.path.normpath(item.get("path", "")).lstrip(os.sep)
            if rel.startswith("..") or os.path.isabs(rel) or rel in ("", "."):
                continue
            p = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(base64.b64decode(item.get("b64", "")))
            written += 1
        self.save_meta(name, body)
        self.enqueue(name)
        return 200, {"team": name, "files": written}

    def save_meta(self, name, body):
        leader = body.get("leader")
        rush = body.get("rush")
        if leader is not None or rush is not None:
            if rush not in (None, "") and not str(rush).isdigit():
                raise ValueError("rush must be a number")
            self.R.save_team_meta(name, leader, rush)

    def api_add(self, body):
        url = (body.get("url") or "").strip()
        if not self.R.is_url(url):
            raise ValueError("that does not look like a git URL")
        name = (body.get("team") or "").strip() or \
            re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1].split(":")[-1])
        dest = self.team_path(name)
        self.set(name, "cloning")
        self.save_meta(name, body)

        def job():
            if os.path.exists(dest):
                rc = subprocess.run(["git", "-C", dest, "pull", "--ff-only", "-q"],
                                    capture_output=True, text=True, timeout=120)
            else:
                os.makedirs(self.R.REPO_DIR, exist_ok=True)
                rc = subprocess.run(["git", "clone", "-q", url, dest], capture_output=True,
                                    text=True, timeout=300,
                                    env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
            if rc.returncode != 0:
                self.set(name, "error", "git: " + (rc.stderr or rc.stdout).strip())
            else:
                self.set(name, "new")
                self.enqueue(name)
        threading.Thread(target=job, daemon=True).start()
        return 200, {"team": name}

    def trash(self, name):
        src = self.team_path(name)
        if os.path.exists(src):
            tdir = os.path.join(self.R.REPO_DIR, ".trash")
            os.makedirs(tdir, exist_ok=True)
            shutil.move(src, os.path.join(tdir, f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"))
        self.drop_reports(name)
        with self.lock:
            self.status.pop(name, None)
        self.sigs.pop(name, None)

    def api_trace(self, qs):
        name = qs.get("team", [""])[0]
        path = self.team_path(name)
        n = int(qs.get("rush", ["-1"])[0])
        x = max(-5, min(int(qs.get("x", ["5"])[0]), 40))
        y = max(-5, min(int(qs.get("y", ["3"])[0]), 30))
        R = self.R
        S = R.Subject.load()
        ex = R.find_ex_dir(path, S.cfg["dir"])
        if not ex:
            raise ValueError("no rushNN.c in this team")
        files = sorted(os.listdir(ex))
        rfs = [f for f in files if R.RUSH_FILE.match(f)]
        rf = f"rush{n:02d}.c" if n >= 0 else rfs[0]
        if rf not in rfs:
            raise ValueError(f"{rf} not turned in")
        key = (name, rf, x, y, self.newest_mtime(name))
        with self.trace_lock:
            if key in self.trace_cache:
                return self.trace_cache[key]
        t = R.Team(path, S)
        try:
            t.ex = ex
            t.parsed = [R.cm.parse_file(os.path.join(ex, f)) for f in files if f.endswith(".c")]
            entry = t._entry(rf)
        finally:
            t.cleanup()
        if not entry:
            raise ValueError(f"no rush(int x, int y)-shaped function in {rf}")
        helpers = [f for f in files if f.endswith(".c") and not R.RUSH_FILE.match(f)
                   and f not in ("main.c", "ft_putchar.c") and not t._has_main(f)]
        srcs = [f for f in ("ft_putchar.c",) if f in files] + [rf] + helpers
        res = rtrace.trace(ex, srcs, entry.name, [x, y])
        res["team"], res["rush"], res["rush_file"] = name, int(rf[4:6]), rf
        res["rush_files"] = rfs
        spec = S.expected_for(int(rf[4:6]))
        res["expected"] = R.render(spec["pattern"], x, y) if spec and spec["pattern"] else None
        with self.trace_lock:
            if len(self.trace_cache) > 200:
                self.trace_cache.clear()
            self.trace_cache[key] = res
        return res


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        server_version = "rush00"

        def log_message(self, fmt, *args):
            pass

        def send(self, code, body, ctype):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def json(self, obj, code=200):
            self.send(code, json.dumps(obj), "application/json")

        def host_ok(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("localhost", "127.0.0.1", "[::1]", "")

        def do_GET(self):
            if not self.host_ok():
                return self.send(403, "forbidden", "text/plain")
            u = urlparse(self.path)
            p = unquote(u.path)
            try:
                if p == "/":
                    return self.static("dash.html")
                if p.startswith("/team/"):
                    return self.static("viz.html")
                if p.startswith("/www/"):
                    return self.static(p[5:])
                if p.startswith("/report/"):
                    name = p[8:]
                    app.team_path(name)
                    rp = os.path.join(app.R.REPORT_DIR, name + ".html")
                    if not os.path.exists(rp):
                        return self.send(404, "<p>not evaluated yet — <a href='/'>back</a></p>",
                                         "text/html")
                    with open(rp, encoding="utf-8") as f:
                        html = f.read()
                    html = html.replace('href="index.html">← all teams', 'href="/">← dashboard')
                    html = html.replace('<a href="#checks">Checklist</a>',
                                        f'<a href="/team/{name}">▶ Algorithm</a><a href="#checks">Checklist</a>', 1)
                    return self.send(200, html, "text/html; charset=utf-8")
                if p == "/api/state":
                    return self.json(app.api_state())
                if p == "/api/trace":
                    return self.json(app.api_trace(parse_qs(u.query)))
                if p == "/favicon.ico":
                    return self.send(204, b"", "text/plain")
                return self.send(404, "not found", "text/plain")
            except ValueError as e:
                return self.json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                return self.json({"error": f"{type(e).__name__}: {e}"}, 500)

        def static(self, rel):
            p = os.path.normpath(os.path.join(WWW, rel))
            if not p.startswith(WWW + os.sep) or not os.path.isfile(p):
                return self.send(404, "not found", "text/plain")
            with open(p, "rb") as f:
                return self.send(200, f.read(), TYPES.get(os.path.splitext(p)[1], "text/plain"))

        def do_POST(self):
            if not self.host_ok():
                return self.send(403, "forbidden", "text/plain")
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                return self.json({"error": "json only"}, 415)
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self.json({"error": "too big"}, 413)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                p = urlparse(self.path).path
                if p == "/api/upload":
                    code, res = app.api_upload(body)
                    return self.json(res, code)
                if p == "/api/add":
                    code, res = app.api_add(body)
                    return self.json(res, code)
                if p == "/api/meta":
                    name = body.get("team", "")
                    app.team_path(name)
                    app.save_meta(name, body)
                    app.enqueue(name)
                    return self.json({"ok": True})
                if p == "/api/rerun":
                    names = app.team_names() if body.get("all") else [body.get("team", "")]
                    for name in names:
                        app.team_path(name)
                        app.sigs.pop(name, None)
                        app.enqueue(name)
                    return self.json({"ok": True})
                if p == "/api/remove":
                    app.trash(body.get("team", ""))
                    return self.json({"ok": True})
                return self.json({"error": "unknown endpoint"}, 404)
            except ValueError as e:
                return self.json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                return self.json({"error": f"{type(e).__name__}: {e}"}, 500)

    return H


def serve(R, port=6969, open_browser=False):
    os.makedirs(R.REPO_DIR, exist_ok=True)
    os.makedirs(R.REPORT_DIR, exist_ok=True)
    app = App(R, port)
    threading.Thread(target=app.worker, daemon=True).start()
    threading.Thread(target=app.scanner, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    url = f"http://localhost:{port}/"
    print(f"rush00 visualizer → {url}\n  teams folder: {R.REPO_DIR}\n  Ctrl-C to stop")
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
