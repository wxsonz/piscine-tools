#!/usr/bin/env python3
"""Reference output for the test corpus.   ref.py N X Y  -> prints what rush0N(X, Y) must print.
   ref.py check DIR N [ENTRY] -> builds DIR's .c files (only rush0N.c of the rush files; main.c with its main
                           renamed) with a harness calling ENTRY(x, y) (default rush), compares many sizes.
                           Exit 0 if all match."""
import os, subprocess, sys, tempfile
P = {0: ["o-o", "| |", "o-o"], 1: ["/*\\", "* *", "\\*/"], 2: ["ABA", "B B", "CBC"],
     3: ["ABC", "B B", "ABC"], 4: ["ABC", "B B", "CBA"]}
def render(n, x, y):
    if x <= 0 or y <= 0:
        return ""
    p = P[n]
    rows = []
    for r in range(y):
        R = p[0] if r == 0 else (p[2] if r == y - 1 else p[1])
        rows.append("".join(R[0] if c == 0 else (R[2] if c == x - 1 else R[1]) for c in range(x)))
    return "\n".join(rows) + "\n"
SIZES = [(5, 3), (5, 1), (1, 1), (1, 5), (4, 4), (2, 2), (2, 1), (1, 2), (3, 3), (10, 6), (123, 42), (0, 0), (0, 3), (3, 0), (-2, 4)]
if sys.argv[1] == "check":
    d, n = sys.argv[2], int(sys.argv[3])
    entry = sys.argv[4] if len(sys.argv) > 4 else "rush"
    w = tempfile.mkdtemp()
    h = os.path.join(w, "h.c")
    open(h, "w").write(f"#include <stdlib.h>\nvoid {entry}(int x, int y);\nint main(int c, char **v) {{ (void)c; {entry}(atoi(v[1]), atoi(v[2])); return 0; }}\n")
    srcs = [f for f in os.listdir(d) if f.endswith(".c")
            and (not f.startswith("rush") or f == f"rush{n:02d}.c")]
    objs = []
    for f in srcs + ["h.c"]:
        src = h if f == "h.c" else os.path.join(d, f)
        extra = ["-Dmain=__student_main"] if f == "main.c" else []
        o = os.path.join(w, f + ".o")
        r = subprocess.run(["cc", "-c", "-Wall", "-Wextra", "-Werror", "-ffunction-sections"] + extra + [src, "-o", o], capture_output=True, text=True)
        if r.returncode:
            print(f"BUILD FAILED ({f})\n" + r.stderr); sys.exit(1)
        objs.append(o)
    r = subprocess.run(["cc", "-Wl,--gc-sections"] + objs + ["-o", os.path.join(w, "a")], capture_output=True, text=True)
    if r.returncode:
        print("LINK FAILED\n" + r.stderr); sys.exit(1)
    bad = 0
    for x, y in SIZES:
        try:
            out = subprocess.run([os.path.join(w, "a"), str(x), str(y)], capture_output=True, timeout=3).stdout.decode("latin-1")
        except subprocess.TimeoutExpired:
            out = "<TIMEOUT>"
        ok = out == render(n, x, y)
        bad += not ok
        print(f"rush({x}, {y}): {'ok' if ok else 'DIFFERS'}" + ("" if ok else f"\n  want {render(n, x, y)[:80]!r}\n  got  {out[:80]!r}"))
    print("ALL MATCH" if not bad else f"{bad} size(s) differ"); sys.exit(1 if bad else 0)
print(render(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])), end="")
