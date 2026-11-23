"""The turn-in on disk: find ex00/, list and flag its files, copy the team to
the work dir (PLAN.md §3, §6 step 1; judge/CONTRACT.md B1, B2).
"""

import os
import re
import shutil

EX_DIR_MAX_DEPTH = 2
OUTSIDE_LIST_CAP = 30
BINARY_MAGICS = (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe",
                 b"\xca\xfe\xba\xbe")
TEST_NAME = re.compile(r"test", re.I)


def find_ex_dir(team_abs, want):
    """-> (ex_dir relative to the team, no_ex_dir). The shallowest `want`
    directory at depth <= 2 wins, one holding .c files first (rush00's
    find_ex_dir order); none -> (".", True): the root is judged."""
    cands = []
    # 1. every `want` directory, hidden ones skipped
    for dirpath, dirnames, _ in os.walk(team_abs):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        rel = os.path.relpath(dirpath, team_abs)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= EX_DIR_MAX_DEPTH:
            dirnames[:] = []
        if depth >= 1 and os.path.basename(dirpath) == want:
            cands.append((not _has_c_files(dirpath), depth, rel))
    # 2. the best one
    if not cands:
        return ".", True
    cands.sort()
    return cands[0][2], False


def list_files(team_abs, ex_dir, want):
    """-> the "files" part of the judge result (SHAPES), minus no_ex_dir."""
    ex_abs = os.path.join(team_abs, ex_dir)
    sources = []
    headers = []
    flagged = []
    # 1. the top of the turn-in dir: what `cc *.c` sees
    for name in sorted(os.listdir(ex_abs)):
        path = os.path.join(ex_abs, name)
        rel = os.path.normpath(os.path.join(ex_dir, name))
        why = _flag_reason(name, path)
        if os.path.isfile(path) and name.endswith(".c"):
            sources.append(rel)
        elif os.path.isfile(path) and name.endswith(".h"):
            headers.append(rel)
        if why:
            flagged.append({"path": rel + ("/" if os.path.isdir(path) else ""),
                            "why": why})
    # 2. files outside the turn-in dir (only when there is one)
    if ex_dir != ".":
        flagged += _outside_files(team_abs, ex_dir, want)
    return {"sources": sources, "headers": headers, "flagged": flagged}


def copy_team(team_abs, work_abs):
    """Copy the team (without .git) into work_abs/team; -> that path.
    Symlinks stay links, so nothing outside the team is copied."""
    dst = os.path.join(work_abs, "team")
    if os.path.lexists(dst):
        shutil.rmtree(dst)
    shutil.copytree(team_abs, dst, symlinks=True,
                    ignore=shutil.ignore_patterns(".git"))
    return dst


def _has_c_files(dir_abs):
    return any(n.endswith(".c") for n in os.listdir(dir_abs))


def _flag_reason(name, path):
    """Why a top-level entry of the turn-in is flagged (a note, not a fail)."""
    if os.path.isdir(path):
        if name == ".git":
            return ""
        return ("hidden directory" if name.startswith(".")
                else "extra directory in the turn-in")
    if name == ".DS_Store":
        return ".DS_Store (macOS folder file)"
    if name.startswith("."):
        return "hidden file (the sheet: no hidden files)"
    if name.endswith(("~", ".swp", ".swo", ".tmp")) or name.startswith("#"):
        return "temporary file (the sheet: no temporary files)"
    if name.endswith(".o"):
        return "object file in the turn-in"
    if _is_binary(path):
        return "binary in the turn-in"
    if TEST_NAME.search(name):
        return "looks like a test file"
    if not name.endswith((".c", ".h")):
        return "not a .c or .h file"
    return ""


def _is_binary(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(4) in BINARY_MAGICS
    except OSError:
        return False


def _outside_files(team_abs, ex_dir, want):
    """Files of the team that are not in the turn-in dir (hidden ones skipped
    except .DS_Store), at most OUTSIDE_LIST_CAP plus one count line."""
    found = []
    ex_abs = os.path.normpath(os.path.join(team_abs, ex_dir))
    for dirpath, dirnames, filenames in os.walk(team_abs):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".")
                             and os.path.join(dirpath, d) != ex_abs)
        for name in sorted(filenames):
            if name.startswith(".") and name != ".DS_Store":
                continue
            found.append(os.path.relpath(os.path.join(dirpath, name), team_abs))
    flagged = [{"path": p, "why": f"outside {want}/"}
               for p in found[:OUTSIDE_LIST_CAP]]
    if len(found) > OUTSIDE_LIST_CAP:
        flagged.append({"path": "...", "why": f"and {len(found) - OUTSIDE_LIST_CAP}"
                        f" more files outside {want}/"})
    return flagged
