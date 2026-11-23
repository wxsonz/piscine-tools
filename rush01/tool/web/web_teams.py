"""The teams: every folder in repo_dir_abs, its evaluation state, the queue
and worker that evaluate it, and the mtime scan (CONTRACT.md B1, B2, B5).
Shape copied from rush00/tool/web.py (App), adapted to the rush01 app dict.
"""

import base64
import json
import os
import queue
import re
import shutil
import threading
import time
import traceback

TEAM_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,80}$")
GIT_URL = re.compile(r"^(https?://|ssh://|git@)[^\s'\"]+$")
BUSY = ("queued", "running", "cloning")
PARTS = ("parse", "data", "solve", "print")
SETTLE_NS = 1_500_000_000       # a folder still being copied in waits this long
SCAN_EVERY_S = 2
WALK_CAP = 5000                 # files looked at per team by the scan (FLOW-3)
UPLOAD_FILES_CAP = 2000
ERROR_CAP = 4000                # chars of a traceback kept for the page
STATE_FILE = ".web_state.json"  # web's own: team -> signature last evaluated


class Teams:
    """One per server. Every field below is written only by these methods."""

    def __init__(self, app):
        self.app = app
        self.repo = app["repo_dir_abs"]
        self.reports = app["report_dir_abs"]
        self.status = {}        # team -> queued | running | done | error
        self.errors = {}        # team -> text
        self.clones = {}        # url name -> {"url", "status", "error"}
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.state_path = os.path.join(self.reports, STATE_FILE)
        self.sigs = {}
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                self.sigs = json.load(fh)
        except (OSError, ValueError):
            self.sigs = {}

    # ------------------------------------------------------------ names

    def teams_names(self):
        if not os.path.isdir(self.repo):
            return []
        return [d for d in sorted(os.listdir(self.repo))
                if not d.startswith(".")
                and os.path.isdir(os.path.join(self.repo, d))]

    def teams_path(self, name):
        """The team's folder. LookupError when the name is bad or unknown,
        so a path can never leave repo_dir_abs (B5)."""
        if not TEAM_NAME.match(name or ""):
            raise LookupError("bad team name")
        path = os.path.join(self.repo, name)
        if not os.path.isdir(path):
            raise LookupError("no such team: " + name)
        return path

    def teams_report(self, name):
        """reports/<team>.json as written by app["evaluate"], or None."""
        path = os.path.join(self.reports, name + ".json")
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------ queue

    def teams_set(self, name, status, error=None):
        with self.lock:
            self.status[name] = status
            if error:
                self.errors[name] = error[-ERROR_CAP:]
            else:
                self.errors.pop(name, None)

    def teams_enqueue(self, name):
        with self.lock:
            if self.status.get(name) in BUSY:
                return
            self.status[name] = "queued"
        self.queue.put(name)

    def teams_work(self):
        """The one worker thread: evaluate is slow and may not be
        thread-safe, so teams go through it one at a time."""
        while True:
            name = self.queue.get()
            path = os.path.join(self.repo, name)
            # 1. the folder may have gone while it waited
            if not os.path.isdir(path):
                with self.lock:
                    self.status.pop(name, None)
                continue
            # 2. evaluate; the signature is taken first, so a change made
            #    during the run is seen by the next scan
            self.teams_set(name, "running")
            sig = teams_signature(path)
            try:
                self.app["evaluate"](path)
                if os.path.isfile(os.path.join(self.reports, name + ".json")):
                    self.teams_set(name, "done")
                else:
                    self.teams_set(name, "error", "evaluate finished but "
                                   "wrote no reports/" + name + ".json")
            except Exception:  # noqa: BLE001  (team code is untrusted)
                self.teams_set(name, "error", traceback.format_exc())
            # 3. remember what was evaluated, across restarts
            with self.lock:
                self.sigs[name] = sig
                sigs = dict(self.sigs)
            self.teams_save_sigs(sigs)

    def teams_save_sigs(self, sigs):
        try:
            os.makedirs(self.reports, exist_ok=True)
            tmp = self.state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(sigs, fh)
            os.replace(tmp, self.state_path)
        except OSError:
            pass  # only costs a re-evaluation after a restart

    def teams_scan(self):
        """Every SCAN_EVERY_S: a team whose files changed is queued (B2)."""
        while True:
            try:
                self.teams_scan_once(time.time_ns())
            except Exception:  # noqa: BLE001  (keep scanning)
                traceback.print_exc()
            time.sleep(SCAN_EVERY_S)

    def teams_scan_once(self, now_ns):
        for name in self.teams_names():
            with self.lock:
                busy = self.status.get(name) in BUSY
                old = self.sigs.get(name)
            if busy:
                continue
            path = os.path.join(self.repo, name)
            sig = teams_signature(path)
            if now_ns - sig < SETTLE_NS:
                continue  # still being copied in: wait until it settles
            if old != sig:
                self.teams_enqueue(name)

    # ------------------------------------------------------------ api

    def teams_state(self):
        """GET /api/state: every folder with its state and summary (B1)."""
        teams = []
        for name in self.teams_names():
            report = self.teams_report(name)
            with self.lock:
                status = self.status.get(name)
                error = self.errors.get(name)
            if status is None:
                status = "done" if report is not None else "new"
            summary = None
            if report is not None:
                summary, bad = teams_summary(report)
                if bad:
                    error = (error + "\n" if error else "") + bad
            teams.append({"name": name, "status": status, "error": error,
                          "summary": summary})
        with self.lock:
            for key, c in sorted(self.clones.items()):
                teams.append({"name": key, "status": c["status"],
                              "error": c["error"], "summary": None,
                              "url": c["url"]})
        return {"repo_dir_abs": self.repo, "teams": teams}

    def teams_team(self, name):
        """GET /api/team/<name>: the full report + state (B3)."""
        self.teams_path(name)
        report = self.teams_report(name)
        with self.lock:
            status = self.status.get(name)
            error = self.errors.get(name)
        if status is None:
            status = "done" if report is not None else "new"
        return {"name": name, "status": status, "error": error,
                "report": report}

    def teams_upload(self, body):
        """POST /api/upload {team, files: [{path, b64}], replace} (B2)."""
        # 1. check the name and the files at the edge
        name = str(body.get("team") or "").strip()
        if not TEAM_NAME.match(name):
            raise ValueError("bad team name")
        files = body.get("files") or []
        if not files:
            raise ValueError("no files")
        if len(files) > UPLOAD_FILES_CAP:
            raise ValueError("too many files (cap %d)" % UPLOAD_FILES_CAP)
        rels = []
        for item in files:
            rel = os.path.normpath(str(item.get("path") or ""))
            if os.path.isabs(rel) or rel in ("", ".") \
                    or rel.split(os.sep)[0] == "..":
                raise ValueError("bad file path: " + str(item.get("path")))
            rels.append((rel, base64.b64decode(item.get("b64") or "")))
        # 2. an existing team is replaced only when asked; the old copy goes
        #    to repo/.trash
        dest = os.path.join(self.repo, name)
        if os.path.exists(dest):
            if not body.get("replace"):
                return 409, {"error": "exists", "team": name}
            self.teams_trash(name)
        # 3. write, then queue
        for rel, data in rels:
            path = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(data)
        self.teams_enqueue(name)
        return 200, {"team": name, "files": len(rels)}

    def teams_trash(self, name):
        trash = os.path.join(self.repo, ".trash")
        os.makedirs(trash, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        shutil.move(os.path.join(self.repo, name),
                    os.path.join(trash, name + "-" + stamp))
        with self.lock:
            self.sigs.pop(name, None)

    def teams_add(self, body):
        """POST /api/add {url}: app["clone"] in a thread, then evaluate (B2)."""
        url = str(body.get("url") or "").strip()
        if not GIT_URL.match(url):
            raise ValueError("that does not look like a git URL")
        key = re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1]
                     .split(":")[-1])
        if not TEAM_NAME.match(key):
            key = "clone"
        with self.lock:
            self.clones[key] = {"url": url, "status": "cloning",
                                "error": None}
        threading.Thread(target=self.teams_clone, args=(key, url),
                         daemon=True).start()
        return 200, {"team": key}

    def teams_clone(self, key, url):
        try:
            path = self.app["clone"](url)
            name = os.path.basename(os.path.normpath(path))
            inside = os.path.realpath(os.path.dirname(os.path.normpath(path)))
            if inside != os.path.realpath(self.repo) \
                    or not TEAM_NAME.match(name):
                raise ValueError("clone wrote outside repo/: " + str(path))
        except Exception as e:  # noqa: BLE001  (shown on the dashboard)
            with self.lock:
                self.clones[key] = {"url": url, "status": "error",
                                    "error": f"{type(e).__name__}: {e}"}
            return
        with self.lock:
            self.clones.pop(key, None)
            self.sigs.pop(name, None)
        self.teams_enqueue(name)

    def teams_rerun(self, body):
        """POST /api/rerun {team} or {all: true}."""
        if body.get("all"):
            names = self.teams_names()
        else:
            names = [str(body.get("team") or "")]
        for name in names:
            self.teams_path(name)
            with self.lock:
                self.sigs.pop(name, None)
            self.teams_enqueue(name)
        return 200, {"queued": names}


def teams_signature(path):
    """Newest mtime (ns) of the team's files and folders, .git left out.
    Folders count too: deleting a file changes its folder's mtime."""
    newest = 0
    seen = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for entry in [dirpath] + [os.path.join(dirpath, f) for f in filenames]:
            try:
                newest = max(newest, os.lstat(entry).st_mtime_ns)
            except OSError:
                pass
            seen += 1
        if seen > WALK_CAP:
            break
    return newest


def teams_summary(report):
    """The few report fields a dashboard card shows (SHAPES "report").
    Returns (summary, None), or (None, why) when the report doesn't match
    the shape: an old or broken file is named, never guessed at."""
    try:
        judge = report["judge"]
        detect = report["detect"]
        parts = {}
        for part in PARTS:
            v = detect["parts"][part]
            parts[part] = {"id": v["id"], "name": v["name"],
                           "confidence": v["confidence"], "tier": v["tier"],
                           "also": v.get("also") or []}
        runs = {"pass": 0, "fail": 0, "info": 0}
        for run in judge["runs"]:
            runs[run["verdict"]] += 1
        forbidden = sorted({x["name"] for x in judge["forbidden"]["names"]})
        summary = {"made_at": report.get("made_at"),
                   "built": judge["built"],
                   "forbidden": forbidden,
                   "norm": {"ran": judge["norm"]["ran"],
                            "ok": judge["norm"]["ok"]},
                   "parts": parts, "groups": judge["groups"], "runs": runs,
                   "diagnosis": judge["diagnosis"],
                   "stops": judge.get("stops", []),
                   "bonus": judge.get("bonus"),
                   "detect_error": detect.get("error")}
        return summary, None
    except (KeyError, TypeError) as e:
        return None, f"report does not match tool/SHAPES.md: {e!r}"
