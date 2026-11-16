"""Build a team's code with -g and trace one call of its entry function under gdb.

    trace(ex_dir, sources, entry, args, student_main="main.c") -> dict

`sources` are file names inside ex_dir; `student_main` (if present) is compiled
with its main renamed, so helper functions living in main.c still link, and a
tiny harness main (compiled without -g, so never stepped) calls entry(args...).
The result is gdbtrace.py's timeline plus what the viewer needs to explain it:
the sources, function ranges, and the kind of every control-flow line.
"""

import json
import os
import shutil
import subprocess
import tempfile

import codemap as cm

HERE = os.path.dirname(os.path.realpath(__file__))
GDBTRACE = os.path.join(HERE, "gdbtrace.py")
CC = os.environ.get("CC", "cc")


def _run(cmd, cwd=None, timeout=60, env=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env=env, errors="replace")
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return None, "timed out"
    except OSError as e:
        return None, str(e)


def control_lines(parsed):
    """{ "file:line": {"kind": if|elif|else|while, "cond": text, "fn": name} }"""
    out = {}
    for P in parsed:
        for fn in P.funcs:
            for node in cm.walk(fn.outline):
                if node["k"] == "loop":
                    out[f"{P.name}:{node['line']}"] = {"kind": node["kw"], "cond": node["cond"],
                                                       "fn": fn.name}
                elif node["k"] == "if":
                    for label, cond, _, line in node["branches"]:
                        kind = {"if": "if", "else if": "elif", "else": "else"}[label]
                        out[f"{P.name}:{line}"] = {"kind": kind, "cond": cond, "fn": fn.name}
    return out


def contexts(parsed):
    """{ "file:line": [enclosing control, outermost first] } for every statement line.
    Each control is {kind: if|elif|else|while, cond, line, prev: [conds of earlier branches]}.
    This is what turns "line 54 printed 'C'" into "because xi == x (and not xi == 1)"."""
    out = {}

    def walk(nodes, chain, fname):
        for node in nodes:
            if node["k"] == "loop":
                out[f"{fname}:{node['line']}"] = chain
                walk(node["kids"], chain + [{"kind": node["kw"], "cond": node["cond"],
                                             "line": node["line"], "prev": []}], fname)
            elif node["k"] == "if":
                conds = [cond for _, cond, _, _ in node["branches"]]
                for k, (label, cond, kids, line) in enumerate(node["branches"]):
                    kind = {"if": "if", "else if": "elif", "else": "else"}[label]
                    out[f"{fname}:{line}"] = chain
                    walk(kids, chain + [{"kind": kind, "cond": cond, "line": line,
                                         "prev": [c for c in conds[:k] if c],
                                         "rest": [c for c in conds[k + 1:] if c],
                                         "has_else": node["branches"][-1][0] == "else"}], fname)
            elif node.get("line"):
                out[f"{fname}:{node['line']}"] = chain

    for P in parsed:
        for fn in P.funcs:
            walk(fn.outline, [], P.name)
    return out


def trace(ex_dir, sources, entry, args, student_main="main.c", max_steps=20000,
          max_seconds=25):
    if not shutil.which("gdb"):
        return {"error": "gdb is not installed"}
    work = tempfile.mkdtemp(prefix="rushtrace-")
    try:
        srcs = list(dict.fromkeys(sources))
        mainc = student_main if student_main and os.path.exists(os.path.join(ex_dir, student_main)) \
            and student_main not in srcs else None
        parsed = [cm.parse_file(os.path.join(ex_dir, s)) for s in srcs + ([mainc] if mainc else [])]
        objs = []
        flags = ["-c", "-g", "-O0", "-w", "-fno-omit-frame-pointer",
                 "-ffunction-sections", "-fdata-sections"]
        for s in srcs + ([mainc] if mainc else []):
            o = os.path.join(work, s + ".o")
            extra = ["-Dmain=__rush_student_main"] if s == mainc else []
            rc, log = _run([CC] + flags + extra + [os.path.join(ex_dir, s), "-o", o])
            if rc != 0:
                rc, log = _run([CC] + flags + ["-fpermissive"] + extra
                               + [os.path.join(ex_dir, s), "-o", o])
            if rc != 0:
                if s == mainc:
                    continue
                return {"error": f"cannot compile {s}:\n{log}"}
            objs.append(o)
        nargs = len(args)
        hc = os.path.join(work, "__harness.c")
        with open(hc, "w") as f:
            params = ", ".join("int" for _ in args)
            call = ", ".join(f"atoi(av[{i + 1}])" for i in range(nargs))
            f.write(f"#include <stdlib.h>\nvoid {entry}({params});\n"
                    f"int main(int ac, char **av)\n{{\n\tif (ac < {nargs + 1})\n\t\treturn (2);\n"
                    f"\t{entry}({call});\n\treturn (0);\n}}\n")
        ho = os.path.join(work, "__harness.o")
        _run([CC, "-c", "-w", "-O0", hc, "-o", ho])
        exe = os.path.join(work, "exe")
        rc, log = _run([CC, "-Wl,--gc-sections", ho] + objs + ["-o", exe])
        if rc != 0 and mainc:
            objs = [o for o in objs if not o.endswith(mainc + ".o")]
            parsed = [P for P in parsed if P.name != mainc]
            rc, log = _run([CC, "-Wl,--gc-sections", ho] + objs + ["-o", exe])
        if rc != 0:
            return {"error": f"cannot link:\n{log}"}
        ctl = control_lines(parsed)
        cfg = {"exe": exe, "args": list(args), "entry": entry,
               "files": [P.name for P in parsed], "out": os.path.join(work, "out.json"),
               "paths": {P.name: P.path for P in parsed},
               "conds": {k: v["cond"] for k, v in ctl.items() if v["kind"] != "else"},
               "max_steps": max_steps, "max_seconds": max_seconds}
        cfgp = os.path.join(work, "cfg.json")
        with open(cfgp, "w") as f:
            json.dump(cfg, f)
        env = dict(os.environ, RUSHTRACE_CFG=cfgp)
        rc, log = _run(["gdb", "-q", "-nx", "-batch", "-x", GDBTRACE], cwd=work,
                       timeout=max_seconds + 15, env=env)
        try:
            with open(cfg["out"]) as f:
                res = json.load(f)
        except (OSError, ValueError):
            return {"error": "gdb produced no trace:\n" + log[-2000:]}
        res["files"] = {P.name: P.src.split("\n") for P in parsed}
        res["funcs"] = [{"name": fn.name, "file": P.name, "line": fn.line, "end": fn.close_line,
                         "params": fn.params} for P in parsed for fn in P.funcs]
        res["control"] = ctl
        res["ctx"] = contexts(parsed)
        res["entry"] = entry
        res["args"] = list(args)
        res["output"] = "".join(w["d"] for s in res.get("steps", []) for w in s.get("w", [])
                                if w.get("fd") == 1)
        return res
    finally:
        shutil.rmtree(work, ignore_errors=True)
