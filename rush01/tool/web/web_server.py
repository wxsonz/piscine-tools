"""The HTTP server: routes, the JSON API and the static files of www/
(CONTRACT.md). Binds 127.0.0.1 only; skeleton copied from rush00/tool/web.py.

  GET  /                    dashboard (www/dash.html)
  GET  /team/<name>         team page (www/team.html); 404 for unknown teams
  GET  /www/<file>          static files (notebook.css and fonts/ are links)
  GET  /api/state           every team with its state and summary
  GET  /api/team/<name>     state + the full report
  GET  /api/source/<name>   source files + call graph (codemap)
  GET  /api/catalog         app["catalog"]
  POST /api/upload /api/add /api/rerun
"""

import json
import os
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .web_source import source_panel
from .web_teams import Teams

WWW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
MAX_BODY = 60 * 1024 * 1024
LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]", "")
TYPES = {".html": "text/html; charset=utf-8",
         ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
         ".ttf": "font/ttf", ".txt": "text/plain; charset=utf-8"}


def web_serve(app, port=4243, open_browser=False):
    """Serve until Ctrl-C. app: {"repo_dir_abs", "report_dir_abs",
    "evaluate", "clone", "catalog"} (CONTRACT.md)."""
    # 1. folders, the team state, its worker and scanner
    os.makedirs(app["repo_dir_abs"], exist_ok=True)
    os.makedirs(app["report_dir_abs"], exist_ok=True)
    teams = Teams(app)
    threading.Thread(target=teams.teams_work, daemon=True).start()
    threading.Thread(target=teams.teams_scan, daemon=True).start()
    # 2. the server, on localhost only
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 web_make_handler(app, teams))
    url = f"http://localhost:{port}/"
    print(f"rush01 dashboard: {url}\n  teams folder: {app['repo_dir_abs']}"
          "\n  Ctrl-C to stop", flush=True)
    if open_browser:
        webbrowser.open(url)
    # 3. block
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


def web_make_handler(app, teams):
    class Handler(BaseHTTPRequestHandler):
        server_version = "rush01"

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

        def send_json(self, obj, code=200):
            self.send(code, json.dumps(obj), "application/json")

        def is_local(self):
            # a page on another site can't reach us through DNS rebinding
            host = self.headers.get("Host") or ""
            if host.startswith("["):
                host = host.split("]")[0] + "]"
            else:
                host = host.split(":")[0]
            return host in LOCAL_HOSTS

        def do_GET(self):
            if not self.is_local():
                return self.send(403, "forbidden", "text/plain")
            path = unquote(urlparse(self.path).path)
            try:
                return self.route_get(path)
            except LookupError as e:
                return self.send_json({"error": str(e)}, 404)
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001  (shown, server keeps on)
                traceback.print_exc()
                return self.send_json({"error": f"{type(e).__name__}: {e}"},
                                      500)

        def route_get(self, path):
            if path == "/":
                return self.static("dash.html")
            if path == "/library":
                return self.static("library.html")
            if path.startswith("/team/"):
                teams.teams_path(path[len("/team/"):])
                return self.static("team.html")
            if path.startswith("/www/"):
                return self.static(path[len("/www/"):])
            if path == "/api/state":
                return self.send_json(teams.teams_state())
            if path.startswith("/api/team/"):
                return self.send_json(teams.teams_team(path[len("/api/team/"):]))
            if path.startswith("/api/source/"):
                name = path[len("/api/source/"):]
                team_dir = teams.teams_path(name)
                report = teams.teams_report(name)
                if report is None:
                    return self.send_json({"files": [], "graph": "",
                                           "notes": ["not evaluated yet"]})
                return self.send_json(source_panel(team_dir, report))
            if path == "/api/catalog":
                return self.send_json(app["catalog"])
            if path == "/favicon.ico":
                return self.send(204, b"", "text/plain")
            raise LookupError("not found")

        def static(self, rel):
            # normpath, not realpath: notebook.css and fonts/ are symlinks
            # into rush00 on purpose; ".." still can't climb out of www/
            path = os.path.normpath(os.path.join(WWW, rel))
            if not path.startswith(WWW + os.sep) or not os.path.isfile(path):
                raise LookupError("not found")
            with open(path, "rb") as fh:
                ctype = TYPES.get(os.path.splitext(path)[1], "text/plain")
                return self.send(200, fh.read(), ctype)

        def do_POST(self):
            if not self.is_local():
                return self.send(403, "forbidden", "text/plain")
            # json only: a plain form on another site can't post here
            if "application/json" not in (self.headers.get("Content-Type")
                                          or ""):
                return self.send_json({"error": "json only"}, 415)
            size = int(self.headers.get("Content-Length") or 0)
            if size > MAX_BODY:
                return self.send_json({"error": "too big"}, 413)
            try:
                body = json.loads(self.rfile.read(size) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("body must be a JSON object")
                path = urlparse(self.path).path
                if path == "/api/upload":
                    code, res = teams.teams_upload(body)
                elif path == "/api/add":
                    code, res = teams.teams_add(body)
                elif path == "/api/rerun":
                    code, res = teams.teams_rerun(body)
                else:
                    raise LookupError("unknown endpoint")
                return self.send_json(res, code)
            except LookupError as e:
                return self.send_json({"error": str(e)}, 404)
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                return self.send_json({"error": f"{type(e).__name__}: {e}"},
                                      500)

    return Handler
