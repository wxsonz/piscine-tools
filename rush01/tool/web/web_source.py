"""The source + call graph panel of the team page (CONTRACT.md B3), drawn by
common/codemap.py (read-only). Reads only files inside the team folder (B5).
"""

import os
import re

import codemap  # rush/common/codemap.py, on sys.path via the wiring file

FILE_CAP_BYTES = 512 * 1024
# decoration only (notebook.css: blue and gold never carry meaning); teal and
# orange are kept for good / attention, so files never use them
FILE_COLORS = ["#3B5BA9", "#8A6A2F", "#5B6B7F", "#7A4E8C", "#2F5D7C",
               "#6B5B3E", "#4A5A8A", "#7D6A55"]


def source_panel(team_dir_abs, report):
    """{"files": [{"path", "id", "html"}], "graph": svg, "notes": [...]}"""
    files = []
    notes = []
    parsed = []
    root = os.path.realpath(team_dir_abs)
    judge = report["judge"]
    # 1. the lines to mark: norm errors and forbidden calls, per file
    marks = {}
    for err in judge["norm"]["errors"]:
        if err.get("line"):
            marks.setdefault(err["file"], {})[err["line"]] = \
                "norm: " + err["text"]
    for bad in judge["forbidden"]["names"]:
        if bad["where"] == "source" and bad.get("line"):
            marks.setdefault(bad["file"], {})[bad["line"]] = \
                "forbidden: " + bad["name"]
    # 2. each source and header, only from inside the team folder
    for rel in judge["files"]["sources"] + judge["files"]["headers"]:
        path = os.path.realpath(os.path.join(root, rel))
        if not path.startswith(root + os.sep):
            notes.append(f"skipped {rel}: outside the team folder")
            continue
        if not os.path.isfile(path):
            notes.append(f"skipped {rel}: not found")
            continue
        if os.path.getsize(path) > FILE_CAP_BYTES:
            notes.append(f"skipped {rel}: bigger than "
                         f"{FILE_CAP_BYTES // 1024} KB")
            continue
        p = codemap.parse_file(path)
        file_id = "f-" + re.sub(r"[^A-Za-z0-9_-]+", "-", rel)
        fn_lines = {fn.line: codemap.fn_anchor(fn) for fn in p.funcs}
        files.append({"path": rel, "id": file_id,
                      "html": codemap.source_html(p, file_id, fn_lines,
                                                  marks.get(rel))})
        if rel.endswith(".c"):
            parsed.append(p)
    # 3. the call graph, every external call shown, forbidden ones flagged
    nodes, edges, ambiguous = codemap.build_graph(parsed, externals="*")
    names = {bad["name"] for bad in judge["forbidden"]["names"]}
    flags = {}
    for node_id, node in nodes.items():
        if node["fn"] is None and node["name"] in names:
            flags[node_id] = {"forbidden"}
        elif node["name"] == "main":
            flags[node_id] = {"entry"}
    colors = {}
    for i, p in enumerate(parsed):
        colors[p.name] = FILE_COLORS[i % len(FILE_COLORS)]
    graph = codemap.svg_graph(nodes, edges, ambiguous, colors,
                              roots=[n for n in flags if "entry" in flags[n]],
                              flags=flags)
    return {"files": files, "graph": graph, "notes": notes}
