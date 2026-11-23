"""Read a team's .c / .h files into plain facts per function and per project.

Lexing comes from common/codemap.py (read-only); its gaps are worked around
here, never fixed there (PLAN.md §7.1): literals from P.src where
kinds == 's', depth-0 globals and structs, defines from raw lines, compound
operators from token pairs, and our own statement tree with code text.
"""

import ast
import bisect
import os
import re
from collections import namedtuple

import codemap

FILES_CAP = 64                 # a rush turn-in has ~10 files: read the first 64
FILE_CAP_BYTES = 512 * 1024    # bigger than this is not hand-written C
FIND_DEPTH_CAP = 2             # ex00/ is searched like judge does (depth <= 2)
TEXT_CAP = 160                 # evidence lines are cut to this many chars

IDENT = re.compile(r"[A-Za-z_]\w*\Z")
CTRL = codemap.CTRL
TYPES = codemap.TYPES
QUALIFIERS = {"const", "static", "unsigned", "signed", "register",
              "volatile", "extern", "struct", "long", "short", "enum",
              "union"}
# token pairs codemap leaves split: (first, second) -> merged operator
MERGE = {("+", "="): "+=", ("-", "="): "-=", ("*", "="): "*=",
         ("/", "="): "/=", ("%", "="): "%=", ("|", "="): "|=",
         ("&", "="): "&=", ("^", "="): "^=", ("<", "<"): "<<",
         (">", ">"): ">>", ("<", "<="): "<<=", (">", ">="): ">>="}
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "|=", "&=", "^=", "<<=",
              ">>="}
DEFINE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(\w+)(\([^)]*\))?[ \t]*(.*)$")

Tok = namedtuple("Tok", "v s e line")


def read_find_ex_dir(team_dir_abs):
    """The turn-in dir the way judge finds it: a folder with .c files at
    depth <= 2, `ex00` first, then the shallowest. '' is the team root;
    None means no .c file at all."""
    cands = []
    for dirpath, dirnames, filenames in os.walk(team_dir_abs):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        rel = os.path.relpath(dirpath, team_dir_abs)
        rel = "" if rel == "." else rel
        depth = 0 if rel == "" else rel.count(os.sep) + 1
        if depth >= FIND_DEPTH_CAP:
            dirnames[:] = []
        if any(f.endswith(".c") for f in filenames):
            cands.append((os.path.basename(rel) != "ex00", depth, rel))
    if not cands:
        return None
    return sorted(cands)[0][2]


def read_team(team_dir_abs, ex_dir):
    """Read every .c / .h of the turn-in dir. Returns (team, problems):
    problems are files that are not C (binary, unbalanced braces)."""
    team = {"dir": team_dir_abs, "ex_dir": "", "files": [], "funcs": [],
            "globals": [], "structs": [], "defines": {}, "define_list": [],
            "callees": {}, "ext": {}, "by_gid": {}, "by_name": {}}
    problems = []

    # 1. the turn-in dir and its files (top level only: `cc *.c` builds those)
    if ex_dir is None:
        ex_dir = read_find_ex_dir(team_dir_abs) or ""
    team["ex_dir"] = ex_dir
    folder = os.path.join(team_dir_abs, ex_dir)
    names = []
    if os.path.isdir(folder):
        names = sorted(n for n in os.listdir(folder)
                       if n.endswith((".c", ".h"))
                       and os.path.isfile(os.path.join(folder, n)))
    names = names[:FILES_CAP]

    # 2. lex each file; files that are not C are reported, not read
    parsed = []
    root = os.path.realpath(team_dir_abs)
    for name in names:
        rel = os.path.join(ex_dir, name) if ex_dir else name
        path = os.path.join(folder, name)
        real = os.path.realpath(path)
        if real != root and not real.startswith(root + os.sep):
            problems.append(f"{rel}: points outside the team folder, not read")
            continue
        with open(path, "rb") as fh:
            data = fh.read(FILE_CAP_BYTES + 1)
        if b"\0" in data:
            problems.append(f"{rel}: binary file, not C source")
            continue
        if len(data) > FILE_CAP_BYTES:
            problems.append(f"{rel}: over {FILE_CAP_BYTES // 1024} KB, not read")
            continue
        P = codemap.Parsed(path, data.decode("utf-8", errors="replace"))
        ctx = read_context(rel, P)
        if not read_is_balanced(ctx):
            problems.append(f"{rel}: unbalanced braces")
            continue
        parsed.append(P)
        read_file(team, ctx)

    # 3. call graph across files (codemap, externals kept)
    nodes, edges, _ = codemap.build_graph(parsed, externals="*")
    for fn in team["funcs"]:
        team["callees"].setdefault(fn["gid"], set())
        team["ext"].setdefault(fn["gid"], set())
    for (a, b) in edges:
        if a not in team["by_gid"]:
            continue
        if b.startswith("ext::"):
            team["ext"][a].add(b[5:])
        elif b in team["by_gid"]:
            team["callees"][a].add(b)
    team["parsed"] = parsed
    return team, problems


def read_context(rel, P):
    """Per-file reading context: code text (comments blanked, literals kept),
    merged tokens, bracket matches, literals, newline offsets."""
    code = "".join(" " if k == "c" and ch != "\n" else ch
                   for ch, k in zip(P.src, P.kinds))
    toks = read_merge_tokens(P)
    ctx = {"rel": rel, "P": P, "code": code, "toks": toks,
           "match": read_match(toks),
           "nl": [i for i, ch in enumerate(P.src) if ch == "\n"],
           "lines": P.src.split("\n")}
    ctx["literals"] = read_literals(ctx)
    return ctx


def read_merge_tokens(P):
    """codemap's tokens with `+=`, `<<`, `|=` ... merged back (PLAN §7.1)."""
    out = []
    for t in P.toks:
        if out:
            last = out[-1]
            merged = MERGE.get((last.v, t.v))
            if merged and last.e == t.s:
                out[-1] = Tok(merged, last.s, t.e, last.line)
                continue
        out.append(Tok(t.v, t.s, t.e, t.line))
    return out


def read_match(toks):
    m, st = {}, []
    for i, t in enumerate(toks):
        if t.v in ("(", "{", "["):
            st.append(i)
        elif t.v in (")", "}", "]") and st:
            j = st.pop()
            m[i], m[j] = j, i
    return m


def read_is_balanced(ctx):
    depth = 0
    for t in ctx["toks"]:
        if t.v == "{":
            depth += 1
        elif t.v == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def read_literals(ctx):
    """String and char literals with their real text (codemap blanks them)."""
    P = ctx["P"]
    out = []
    kinds = P.kinds
    i = 0
    n = len(kinds)
    while i < n:
        if kinds[i] != "s":
            i += 1
            continue
        j = i
        while j < n and kinds[j] == "s":
            j += 1
        text = P.src[i:j].rstrip("\n")
        out.append({"s": i, "e": j, "text": text, "value": read_unescape(text),
                    "line": bisect.bisect_right(ctx["nl"], i) + 1})
        i = j
    return out


def read_unescape(text):
    """'\\n' -> newline, '1' -> 1, "Error\\n" -> Error + newline."""
    if not text:
        return ""
    q = text[0]
    inner = text[1:-1] if len(text) >= 2 and text[-1] == q else text[1:]
    table = {"n": "\n", "t": "\t", "0": "\0", "v": "\v", "r": "\r",
             "\\": "\\", "'": "'", '"': '"', "f": "\f"}
    out = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner):
            out.append(table.get(inner[i + 1], inner[i + 1]))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def read_text(ctx, a, b):
    """Code text of tokens a..b (comments blanked), whitespace collapsed."""
    T = ctx["toks"]
    if a > b or a >= len(T):
        return ""
    b = min(b, len(T) - 1)
    s = T[a].s
    e = T[b].e
    kinds = ctx["P"].kinds
    # a char literal is one '0' token in codemap: take the whole literal
    if kinds[T[b].s] == "s":
        while e < len(kinds) and kinds[e] == "s":
            e += 1
    return " ".join(ctx["code"][s:e].split())


def read_line(ctx, line):
    """The source line, stripped and cut, for evidence."""
    if 1 <= line <= len(ctx["lines"]):
        return ctx["lines"][line - 1].strip()[:TEXT_CAP]
    return ""


def read_file(team, ctx):
    """Functions, globals, structs and defines of one file into team."""
    T, M = ctx["toks"], ctx["match"]
    rel = ctx["rel"]
    entry = {"rel": rel, "is_header": rel.endswith(".h"), "ctx": ctx,
             "funcs": []}
    team["files"].append(entry)

    # 1. function spans: same rule as codemap's _scan, on merged tokens
    spans = []
    i, depth = 0, 0
    while i < len(T):
        t = T[i]
        if t.v == "{" and depth == 0 and i > 0 and T[i - 1].v == ")" \
                and (i - 1) in M:
            p = M[i - 1]
            if p > 0 and IDENT.match(T[p - 1].v) and T[p - 1].v not in CTRL:
                close = M.get(i, len(T) - 1)
                spans.append((p - 1, p, i, close))
                i = close + 1
                continue
        if t.v == "{":
            depth += 1
        elif t.v == "}":
            depth -= 1
        i += 1

    # 2. one fact dict per function
    for span in spans:
        fn = read_func(ctx, span)
        entry["funcs"].append(fn)
        team["funcs"].append(fn)
        team["by_gid"][fn["gid"]] = fn
        team["by_name"].setdefault(fn["name"], []).append(fn)

    # 3. depth-0 statements: globals and structs
    read_top_level(team, ctx, spans)

    # 4. defines, from the raw lines codemap blanks
    P = ctx["P"]
    offset = 0
    for no, raw in enumerate(P.src.split("\n"), 1):
        m = DEFINE.match(raw)
        hash_at = offset + raw.find("#")
        if m and P.kinds[hash_at] == "p":
            value = re.sub(r"/\*.*?\*/|//.*$", "", m.group(3)).strip()
            if not m.group(2):
                team["defines"][m.group(1)] = value
            team["define_list"].append({"file": rel, "line": no,
                                        "name": m.group(1), "value": value,
                                        "text": raw.strip()[:TEXT_CAP]})
        offset += len(raw) + 1


def read_func(ctx, span):
    """Facts for one function: params, statement tree, calls, accesses,
    assignments, literals."""
    T, M = ctx["toks"], ctx["match"]
    name_i, lp, lb, rb = span
    P = ctx["P"]
    fn = {"name": T[name_i].v, "file": ctx["rel"], "ctx": ctx,
          "gid": f"{P.name}::{T[name_i].v}", "line": T[name_i].line,
          "end": T[rb].line, "lb": lb, "rb": rb}
    fn["nlines"] = max(T[rb].line - T[lb].line - 1, 0)

    # 1. return type and params
    k = name_i - 1
    while k >= 0 and T[k].v not in (";", "}", "{"):
        k -= 1
    fn["ret"] = read_text(ctx, k + 1, name_i - 1)
    fn["params"] = []
    rp = M.get(lp, lp)
    for text in read_split_args(ctx, lp + 1, rp - 1):
        if text in ("", "void"):
            continue
        d = read_decl(text)
        fn["params"].append(d or {"text": text, "name": "", "base": "",
                                  "ptr": 0, "dims": []})

    # 2. the statement tree; every node knows the conditions around it
    heads = []
    fn["tree"] = read_block(ctx, lb + 1, rb, [], heads)
    fn["nodes"] = list(read_walk(fn["tree"]))

    # 3. calls with their arguments and the conditions around them
    fn["calls"] = []
    for j in range(lb + 1, rb):
        v = T[j].v
        if IDENT.match(v) and v not in CTRL and v not in TYPES \
                and j + 1 < rb and T[j + 1].v == "(" and (j + 1) in M:
            close = M[j + 1]
            head = read_owner(heads, j)
            fn["calls"].append({
                "name": v, "line": T[j].line, "tok": j,
                "args": read_split_args(ctx, j + 2, close - 1),
                "text": read_text(ctx, j, close),
                "stack": head["stack"] if head else [],
                "node": head["node"] if head else None})

    # 4. declarations and assignments
    fn["decls"] = []
    fn["assigns"] = []
    for node in fn["nodes"]:
        if node["k"] == "decl":
            d = read_decl(node["text"])
            if d:
                d["line"] = node["line"]
                fn["decls"].append(d)
        if node["k"] in ("stmt", "decl"):
            a = read_assign(ctx, node)
            if a:
                if node["k"] == "decl" and fn["decls"] \
                        and fn["decls"][-1]["line"] == node["line"]:
                    a["lhs"] = fn["decls"][-1]["name"]   # `int top = 0;`
                fn["assigns"].append(a)

    # 5. array accesses: base, indexes, and whether it is written
    fn["accesses"] = read_accesses(ctx, fn)

    # 6. literals inside the body (comments never hold one: PLAN §7.1)
    body_s, body_e = T[lb].e, T[rb].s
    fn["literals"] = [x for x in ctx["literals"]
                      if body_s <= x["s"] < body_e]
    fn["code"] = " ".join(ctx["code"][body_s:body_e].split())
    return fn


def read_split_args(ctx, a, b):
    """Split tokens a..b at depth-0 commas into code texts."""
    T = ctx["toks"]
    out = []
    if a > b:
        return out
    start, depth = a, 0
    for j in range(a, b + 1):
        v = T[j].v
        if v in ("(", "[", "{"):
            depth += 1
        elif v in (")", "]", "}"):
            depth -= 1
        elif v == "," and depth == 0:
            out.append(read_text(ctx, start, j - 1))
            start = j + 1
    out.append(read_text(ctx, start, b))
    return out


def read_decl(text):
    """`int grid[4][4]` -> name grid, base int, ptr 0, dims ['4', '4']."""
    t = text.split("=", 1)[0].split(",", 1)[0].strip().rstrip(";")
    dims = [d.strip() for d in re.findall(r"\[([^\]]*)\]", t)]
    head = re.sub(r"\[[^\]]*\]", " ", t).replace("(", " ").replace(")", " ")
    words = re.findall(r"\*|[A-Za-z_]\w*", head)
    names = [w for w in words if w != "*"]
    if len(names) < 2:
        return None
    base_words = [w for w in names[:-1] if w not in QUALIFIERS]
    return {"text": text, "name": names[-1],
            "base": base_words[-1] if base_words else names[0],
            "ptr": words.count("*"), "dims": dims}


def read_block(ctx, a, b, stack, heads):
    nodes, i = [], a
    while i < b:
        node, i = read_stmt(ctx, i, b, stack, heads)
        if node is None:
            continue
        nodes.extend(node["kids"] if node["k"] == "block" else [node])
    return nodes


def read_stmt(ctx, i, b, stack, heads):
    """One statement from token i (a port of codemap's _stmt that keeps
    token ranges, code text and the stack of enclosing conditions)."""
    T, M = ctx["toks"], ctx["match"]
    v = T[i].v
    # 1. empty statements and blocks
    if v == ";":
        return None, i + 1
    if v == "{":
        j = M.get(i)
        if j is None or j >= b:
            j = b - 1
        return {"k": "block",
                "kids": read_block(ctx, i + 1, j, stack, heads)}, j + 1
    if v == "else":
        return None, i + 1

    # 2. loops and ifs: the head, then the body with one more stack entry
    if v in ("if", "while", "for") and i + 1 < b and T[i + 1].v == "(" \
            and M.get(i + 1, b) < b:
        q = M[i + 1]
        cond = read_text(ctx, i + 2, q - 1)
        if v == "for":
            return read_for(ctx, i, q, b, stack, heads)
        if v != "if":
            node = {"k": "loop", "kw": v, "text": cond, "line": T[i].line,
                    "a": i, "b": q, "stack": stack}
            inner = stack + [{"k": "loop", "cond": cond, "node": node}]
            heads.append({"a": i, "b": q, "node": node, "stack": inner})
            body, k = (read_stmt(ctx, q + 1, b, inner, heads)
                       if q + 1 < b else (None, q + 1))
            node["kids"] = read_kids(body)
            return node, k
        node = {"k": "if", "text": cond, "line": T[i].line, "a": i, "b": q,
                "stack": stack, "branches": []}
        inner = stack + [{"k": "if", "cond": cond, "node": node}]
        heads.append({"a": i, "b": q, "node": node, "stack": inner})
        body, k = (read_stmt(ctx, q + 1, b, inner, heads)
                   if q + 1 < b else (None, q + 1))
        node["branches"].append({"kw": "if", "cond": cond,
                                 "kids": read_kids(body), "line": T[i].line})
        while k < b and T[k].v == "else":
            line = T[k].line
            if k + 2 < b and T[k + 1].v == "if" and T[k + 2].v == "(" \
                    and M.get(k + 2, b) < b:
                q2 = M[k + 2]
                cond2 = read_text(ctx, k + 3, q2 - 1)
                inner = stack + [{"k": "else if", "cond": cond2,
                                  "node": node}]
                heads.append({"a": k, "b": q2, "node": node, "stack": inner})
                body2, k = (read_stmt(ctx, q2 + 1, b, inner, heads)
                            if q2 + 1 < b else (None, q2 + 1))
                node["branches"].append({"kw": "else if", "cond": cond2,
                                         "kids": read_kids(body2),
                                         "line": line})
            else:
                inner = stack + [{"k": "else", "cond": "", "node": node}]
                body2, k = (read_stmt(ctx, k + 1, b, inner, heads)
                            if k + 1 < b else (None, k + 1))
                node["branches"].append({"kw": "else", "cond": "",
                                         "kids": read_kids(body2),
                                         "line": line})
                break
        return node, k

    # 3. a plain statement, up to the ';' at depth 0
    j, d = i, 0
    while j < b:
        tv = T[j].v
        if tv in ("(", "[", "{"):
            d += 1
        elif tv in (")", "]", "}"):
            d -= 1
        elif tv == ";" and d <= 0:
            break
        j += 1
    if v == "return":
        kind = "return"
    elif v in TYPES or (v.startswith("t_") and i + 1 < j
                        and IDENT.match(T[i + 1].v)):
        kind = "decl"
    else:
        kind = "stmt"
    node = {"k": kind, "text": read_text(ctx, i, j - 1), "line": T[i].line,
            "a": i, "b": j - 1, "stack": stack}
    heads.append({"a": i, "b": j - 1, "node": node, "stack": stack})
    return node, j + 1


def read_for(ctx, i, q, b, stack, heads):
    """`for (init; cond; step) body` read as `init; while (cond) { body
    step; }`, so every rule sees the same shape as in Norm code."""
    T = ctx["toks"]
    # 1. the three parts of the head, cut at its depth-0 ';'
    cuts = []
    depth = 0
    for j in range(i + 2, q):
        if T[j].v in ("(", "["):
            depth += 1
        elif T[j].v in (")", "]"):
            depth -= 1
        elif T[j].v == ";" and depth == 0:
            cuts.append(j)
    if len(cuts) != 2:
        cuts = [i + 1, q]          # not a 3-part head: all of it is the cond
    init_a, init_b = i + 2, cuts[0] - 1
    cond_a, cond_b = cuts[0] + 1, cuts[1] - 1
    step_a, step_b = cuts[1] + 1, q - 1
    # 2. init before the loop, then the loop, its body, the step last
    out = []
    if init_a <= init_b:
        out.append(read_plain(ctx, init_a, init_b, stack, heads))
    cond = read_text(ctx, cond_a, cond_b) if cond_a <= cond_b else "1"
    node = {"k": "loop", "kw": "for", "text": cond, "line": T[i].line,
            "a": cond_a if cond_a <= cond_b else i, "b": max(cond_b, i),
            "stack": stack}
    inner = stack + [{"k": "loop", "cond": cond, "node": node}]
    heads.append({"a": node["a"], "b": node["b"], "node": node,
                  "stack": inner})
    body, k = (read_stmt(ctx, q + 1, b, inner, heads)
               if q + 1 < b else (None, q + 1))
    node["kids"] = read_kids(body)
    if step_a <= step_b:
        node["kids"].append(read_plain(ctx, step_a, step_b, inner, heads))
    out.append(node)
    return {"k": "block", "kids": out}, k


def read_plain(ctx, a, b, stack, heads):
    """A statement node for tokens a..b (no ';' inside)."""
    T = ctx["toks"]
    v = T[a].v
    kind = "decl" if v in TYPES else "stmt"
    node = {"k": kind, "text": read_text(ctx, a, b), "line": T[a].line,
            "a": a, "b": b, "stack": stack}
    heads.append({"a": a, "b": b, "node": node, "stack": stack})
    return node


def read_kids(node):
    if node is None:
        return []
    return node["kids"] if node["k"] == "block" else [node]


def read_walk(nodes):
    """Every node, depth first."""
    for node in nodes:
        yield node
        if node["k"] == "if":
            for br in node["branches"]:
                yield from read_walk(br["kids"])
        elif node["k"] == "loop":
            yield from read_walk(node["kids"])


def read_owner(heads, j):
    """The innermost statement head holding token j."""
    best = None
    for h in heads:
        if h["a"] <= j <= h["b"]:
            if best is None or h["a"] >= best["a"]:
                best = h
    return best


def read_assign(ctx, node):
    """`lhs op rhs` of a statement, or `x++` as op '++'."""
    T = ctx["toks"]
    a, b = node["a"], node["b"]
    depth = 0
    for j in range(a, b + 1):
        v = T[j].v
        if v in ("(", "["):
            depth += 1
        elif v in (")", "]"):
            depth -= 1
        elif v in ASSIGN_OPS and depth == 0:
            return {"lhs": read_text(ctx, a, j - 1), "op": v,
                    "rhs": read_text(ctx, j + 1, b), "line": node["line"],
                    "a": a, "lhs_b": j - 1, "node": node}
    if b > a and T[b].v in ("++", "--"):
        return {"lhs": read_text(ctx, a, b - 1), "op": T[b].v, "rhs": "",
                "line": node["line"], "a": a, "lhs_b": b - 1, "node": node}
    if b > a and T[a].v in ("++", "--"):
        return {"lhs": read_text(ctx, a + 1, b), "op": T[a].v, "rhs": "",
                "line": node["line"], "a": a + 1, "lhs_b": b, "node": node}
    return None


def read_accesses(ctx, fn):
    """Every `base[i][j]...` in the body. base keeps `->` / `.` chains."""
    T, M = ctx["toks"], ctx["match"]
    lb, rb = fn["lb"], fn["rb"]
    writes = {(x["a"], x["lhs_b"]): x for x in fn["assigns"]}
    decl_ranges = [(n["a"], n["b"]) for n in fn["nodes"] if n["k"] == "decl"]
    out = []
    seen = set()
    for j in range(lb + 2, rb):
        if T[j].v != "[" or j in seen or not IDENT.match(T[j - 1].v) \
                or T[j - 1].v in TYPES or T[j - 1].v in CTRL:
            continue
        # 1. walk back over a -> b . c chains
        k = j - 1
        while k - 2 > lb and T[k - 1].v in ("->", ".") \
                and IDENT.match(T[k - 2].v):
            k -= 2
        # 2. every [..] that follows
        idx = []
        m = j
        last = j
        while m < rb and T[m].v == "[" and m in M:
            seen.add(m)
            idx.append(read_text(ctx, m + 1, M[m] - 1))
            last = M[m]
            m = M[m] + 1
        in_decl = any(a <= j <= b for a, b in decl_ranges)
        assign = writes.get((k, last))
        out.append({"base": "".join(T[x].v for x in range(k, j)),
                    "name": T[j - 1].v, "idx": idx, "line": T[j].line,
                    "a": k, "b": last, "decl": in_decl,
                    "write": assign is not None and assign["op"] not in
                    ("++", "--"),
                    "assign": assign})
    return out


def read_top_level(team, ctx, spans):
    """Globals and structs: depth-0 statements outside function bodies."""
    T = ctx["toks"]
    bodies = {lb: rb for (_, _, lb, rb) in spans}
    stmts = []
    start, depth, i = 0, 0, 0
    # 1. cut the file into depth-0 statements, skipping function bodies
    while i < len(T):
        if depth == 0 and i in bodies:
            i = bodies[i] + 1
            start = i
            continue
        v = T[i].v
        if v == "{":
            depth += 1
        elif v == "}":
            depth -= 1
        elif v == ";" and depth == 0:
            if i > start:
                stmts.append((start, i - 1))
            start = i + 1
        i += 1
    # 2. classify each one
    for a, b in stmts:
        vals = [T[x].v for x in range(a, b + 1)]
        line = T[a].line
        if "{" in vals and ("struct" in vals[:3]):
            team["structs"].append(read_struct(ctx, a, b, line))
            continue
        if vals[0] in ("typedef", "extern", "enum") or "{" in vals[:1]:
            continue
        if any(IDENT.match(vals[x]) and vals[x + 1] == "("
               for x in range(len(vals) - 1)):
            continue                   # a prototype
        if not (vals[0] in TYPES or vals[0].startswith("t_")):
            continue
        text = read_text(ctx, a, b) + ";"
        d = read_decl(text)
        if d:
            team["globals"].append({"file": ctx["rel"], "line": line,
                                    "text": text[:TEXT_CAP], "decl": d})


def read_struct(ctx, a, b, line):
    T, M = ctx["toks"], ctx["match"]
    lb = next(x for x in range(a, b + 1) if T[x].v == "{")
    rb = M.get(lb, b)
    name = ""
    for x in range(b, rb, -1):
        if IDENT.match(T[x].v):
            name = T[x].v
            break
    if not name:
        name = next((T[x].v for x in range(a, lb)
                     if IDENT.match(T[x].v) and T[x].v not in QUALIFIERS
                     and T[x].v != "typedef"), "")
    fields = []
    start = lb + 1
    for x in range(lb + 1, rb):
        if T[x].v == ";":
            d = read_decl(read_text(ctx, start, x - 1))
            if d:
                d["line"] = T[start].line
                fields.append(d)
            start = x + 1
    return {"file": ctx["rel"], "line": line, "name": name, "fields": fields}


def read_int(text, defines, depth=0):
    """Value of a small constant expression (`4`, `N + 2`, `N * N`), with
    defines substituted; None when it is not constant."""
    if depth > 4 or text is None:
        return None
    t = text.strip()
    names = set(re.findall(r"[A-Za-z_]\w*", t))
    for name in names:
        if name not in defines:
            return None
        sub = read_int(defines[name], defines, depth + 1)
        if sub is None:
            return None
        t = re.sub(r"\b%s\b" % re.escape(name), str(sub), t)
    if not t or not re.fullmatch(r"[\d\s+\-*/()]+", t):
        return None
    try:
        tree = ast.parse(t, mode="eval")
    except (SyntaxError, ValueError):
        return None
    return read_eval(tree.body)


def read_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = read_eval(node.operand)
        return None if v is None else -v
    if isinstance(node, ast.BinOp):
        x, y = read_eval(node.left), read_eval(node.right)
        if x is None or y is None:
            return None
        if isinstance(node.op, ast.Add):
            return x + y
        if isinstance(node.op, ast.Sub):
            return x - y
        if isinstance(node.op, ast.Mult):
            return x * y
        if isinstance(node.op, (ast.Div, ast.FloorDiv)) and y != 0:
            return x // y
    return None
