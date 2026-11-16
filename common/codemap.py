"""codemap: a small, dependency-free reader for Norm-style C, plus the visuals.

It does not try to be a C compiler. Norm C is regular enough (one function per
`type name(params)` + `{` at file scope, no for/switch/ternary, <= 25 lines)
that a tokenizer with bracket matching recovers what an evaluator needs:

  * every function: return type, params, body length, locals, calls,
    char literals it uses, and an outline of its control flow
  * the call graph across files
  * per-line git authorship (when the folder is a git repo)

and turns them into HTML/SVG fragments the rush tools drop into a report.
Shared by rush00/01/02 tools.
"""

import bisect
import html
import os
import re
import subprocess
from collections import Counter, namedtuple

TOKEN = re.compile(r"[A-Za-z_]\w*|\d[\w.]*|->|\+\+|--|<=|>=|==|!=|&&|\|\||[^\s\w]")
IDENT = re.compile(r"[A-Za-z_]\w*\Z")
CHAR_LIT = re.compile(r"'(?:\\.|[^'\\\n])+'")
CTRL = {"if", "while", "for", "else", "return", "do", "switch", "sizeof",
        "case", "break", "continue", "goto", "default"}
TYPES = {"int", "char", "void", "unsigned", "signed", "long", "short", "const",
         "static", "float", "double", "struct", "enum", "union", "size_t",
         "register", "volatile", "extern", "bool"}
C_KEYWORDS = CTRL | TYPES | {"typedef", "NULL"}

PALETTE = ["#4c8df6", "#e39b2d", "#3fb67e", "#c45fd0", "#e0584d",
           "#2fb3b3", "#9a7ff0", "#b8a83a"]

Tok = namedtuple("Tok", "v s e line")


def esc(s):
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------
#  Lexing
# --------------------------------------------------------------------------

def clean_source(src):
    """Blank out comments, string/char contents and preprocessor lines,
    keeping every offset and newline in place. Returns (clean, kinds) where
    kinds[i] is '' (code), 'c' (comment), 's' (literal) or 'p' (preproc)."""
    out = []
    kinds = []
    i, n = 0, len(src)
    line_start = True

    def emit(ch, k):
        out.append(ch)
        kinds.append(k)

    while i < n:
        c = src[i]
        if c == "\n":
            emit(c, "")
            i += 1
            line_start = True
            continue
        if line_start and c in " \t":
            emit(c, "")
            i += 1
            continue
        if line_start and c == "#":
            while i < n and src[i] != "\n":
                if src[i] == "\\" and i + 1 < n and src[i + 1] == "\n":
                    emit(" ", "p")
                    emit("\n", "p")
                    i += 2
                    continue
                emit(" ", "p")
                i += 1
            continue
        line_start = False
        if src.startswith("//", i):
            while i < n and src[i] != "\n":
                emit(" ", "c")
                i += 1
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for ch in src[i:j]:
                emit("\n" if ch == "\n" else " ", "c")
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                if src[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            seg = src[i:j]
            if c == '"':
                rep = '"' + " " * max(len(seg) - 2, 0) + ('"' if len(seg) >= 2 else "")
            else:
                rep = "0" + " " * (len(seg) - 1)
            for ch in rep:
                emit(ch, "s")
            i = j
            continue
        emit(c, "")
        i += 1
    return "".join(out), kinds


class Parsed:
    def __init__(self, path, src):
        self.path = path
        self.name = os.path.basename(path)
        self.src = src
        self.clean, self.kinds = clean_source(src)
        nl = [i for i, ch in enumerate(self.clean) if ch == "\n"]
        self.toks = [Tok(m.group(), m.start(), m.end(),
                         bisect.bisect_right(nl, m.start()) + 1)
                     for m in TOKEN.finditer(self.clean)]
        self.match = self._match()
        self.includes = re.findall(r'^\s*#\s*include\s*([<"][^>"]+[>"])', src, re.M)
        self.funcs = []
        self.protos = []
        self._scan()

    def _match(self):
        m, st = {}, []
        for i, t in enumerate(self.toks):
            if t.v in ("(", "{", "["):
                st.append(i)
            elif t.v in (")", "}", "]") and st:
                j = st.pop()
                m[i], m[j] = j, i
        return m

    def text(self, a, b):
        """Original source spanning tokens a..b inclusive, whitespace collapsed."""
        if a > b or a >= len(self.toks):
            return ""
        b = min(b, len(self.toks) - 1)
        return " ".join(self.src[self.toks[a].s:self.toks[b].e].split())

    def _scan(self):
        T, i, depth = self.toks, 0, 0
        while i < len(T):
            t = T[i]
            if t.v == "{" and depth == 0 and i > 0 and T[i - 1].v == ")" \
                    and (i - 1) in self.match:
                p = self.match[i - 1]
                if p > 0 and IDENT.match(T[p - 1].v) and T[p - 1].v not in CTRL:
                    close = self.match.get(i, len(T) - 1)
                    self.funcs.append(Func(self, p - 1, p, i, close))
                    i = close + 1
                    continue
            if depth == 0 and IDENT.match(t.v) and i + 1 < len(T) and T[i + 1].v == "(":
                q = self.match.get(i + 1)
                if q is not None and q + 1 < len(T) and T[q + 1].v == ";":
                    self.protos.append(t.v)
            if t.v == "{":
                depth += 1
            elif t.v == "}":
                depth -= 1
            i += 1


class Func:
    def __init__(self, P, name_i, lp, lb, rb):
        T = P.toks
        self.file = P.name
        self.name = T[name_i].v
        k = name_i - 1
        while k >= 0 and T[k].v not in (";", "}", "{"):
            k -= 1
        self.ret = P.text(k + 1, name_i - 1)
        ptxt = P.text(lp + 1, self.match_close(P, lp) - 1)
        self.params = [] if ptxt in ("", "void") else [x.strip() for x in ptxt.split(",")]
        self.line = T[name_i].line
        self.open_line = T[lb].line
        self.close_line = T[rb].line
        self.nlines = max(self.close_line - self.open_line - 1, 0)
        body_s, body_e = T[lb].e, T[rb].s
        self.chars = []
        for m in CHAR_LIT.finditer(P.src[body_s:body_e]):
            if m.group() not in self.chars:
                self.chars.append(m.group())
        self.calls = []          # (name, line)
        for j in range(lb + 1, rb):
            if IDENT.match(T[j].v) and T[j].v not in CTRL and T[j].v not in TYPES \
                    and j + 1 < rb and T[j + 1].v == "(":
                self.calls.append((T[j].v, T[j].line))
        self.outline = _block(P, lb + 1, rb)
        self.locals = [n["text"] for n in self.outline if n["k"] == "decl"]
        self.loops = _count(self.outline, "loop")
        self.branches = _count(self.outline, "if")
        self.id = f"{self.file}::{self.name}"
        self.authors = Counter()

    @staticmethod
    def match_close(P, lp):
        return P.match.get(lp, lp)

    def callees(self):
        return [c for c, _ in self.calls]


def _kids(node):
    if node is None:
        return []
    return node["kids"] if node["k"] == "block" else [node]


def _block(P, a, b):
    nodes, i = [], a
    while i < b:
        node, i = _stmt(P, i, b)
        if node is None:
            continue
        nodes.extend(_kids(node))
    return nodes


def _stmt(P, i, b):
    T = P.toks
    v = T[i].v
    if v == ";":
        return None, i + 1
    if v == "{":
        j = P.match.get(i, b - 1)
        return {"k": "block", "kids": _block(P, i + 1, j)}, j + 1
    if v in ("if", "while", "for") and i + 1 < b and T[i + 1].v == "(" and (i + 1) in P.match:
        q = P.match[i + 1]
        cond = P.text(i + 2, q - 1)
        body, k = _stmt(P, q + 1, b) if q + 1 < b else (None, q + 1)
        if v != "if":
            return {"k": "loop", "kw": v, "cond": cond, "kids": _kids(body),
                    "line": T[i].line}, k
        node = {"k": "if", "line": T[i].line,
                "branches": [("if", cond, _kids(body), T[i].line)]}
        while k < b and T[k].v == "else":
            line = T[k].line
            if k + 2 < b and T[k + 1].v == "if" and T[k + 2].v == "(" and (k + 2) in P.match:
                q2 = P.match[k + 2]
                cond2 = P.text(k + 3, q2 - 1)
                body2, k = _stmt(P, q2 + 1, b)
                node["branches"].append(("else if", cond2, _kids(body2), line))
            else:
                body2, k = _stmt(P, k + 1, b)
                node["branches"].append(("else", "", _kids(body2), line))
                break
        return node, k
    if v == "else":
        return None, i + 1
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
    text = P.text(i, j - 1)
    calls = [T[x].v for x in range(i, j) if IDENT.match(T[x].v) and T[x].v not in CTRL
             and T[x].v not in TYPES and x + 1 < j and T[x + 1].v == "("]
    if v == "return":
        kind = "return"
    elif v in TYPES or (v.startswith("t_") and i + 1 < j and IDENT.match(T[i + 1].v)):
        kind = "decl"
    elif calls:
        kind = "call"
    else:
        kind = "stmt"
    return {"k": kind, "text": text, "calls": calls, "line": T[i].line}, j + 1


def _count(nodes, kind):
    n = 0
    for node in nodes:
        if node["k"] == kind:
            n += 1
        if node["k"] == "if":
            for _, _, kids, _ in node["branches"]:
                n += _count(kids, kind)
        elif "kids" in node:
            n += _count(node["kids"], kind)
    return n


def walk(nodes):
    """Yield every outline node, depth first."""
    for node in nodes:
        yield node
        if node["k"] == "if":
            for _, _, kids, _ in node["branches"]:
                yield from walk(kids)
        elif "kids" in node:
            yield from walk(node["kids"])


def parse_file(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return Parsed(path, f.read())


# --------------------------------------------------------------------------
#  Git authorship
# --------------------------------------------------------------------------

def git_root(path):
    try:
        r = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return os.path.realpath(r.stdout.strip())


def blame_lines(file_path):
    """Return {line_no: author} or {} when not available."""
    try:
        r = subprocess.run(["git", "-C", os.path.dirname(file_path) or ".", "blame",
                            "--line-porcelain", "--", os.path.basename(file_path)],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if r.returncode != 0:
        return {}
    out, cur_line, author = {}, None, None
    for ln in r.stdout.splitlines():
        m = re.match(r"^[0-9a-f]{40} \d+ (\d+)", ln)
        if m:
            cur_line = int(m.group(1))
        elif ln.startswith("author "):
            author = ln[7:].strip()
        elif ln.startswith("\t") and cur_line is not None:
            if author == "Not Committed Yet":
                author = "(uncommitted)"
            out[cur_line] = author
    return out


def git_log_authors(root):
    try:
        r = subprocess.run(["git", "-C", root, "log", "--format=%an"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return Counter()
    return Counter(x for x in r.stdout.splitlines() if x.strip())


def attach_authors(parsed_files, team_root):
    """Fill Func.authors from git blame when team_root is (inside) a git repo
    whose top level is not above the team folder."""
    root = git_root(team_root)
    team = os.path.realpath(team_root)
    # only trust a repo that belongs to the team (not e.g. the evaluator's own folder)
    if not root or not (root == team or root.startswith(team + os.sep)):
        return None
    for P in parsed_files:
        lines = blame_lines(P.path)
        for fn in P.funcs:
            for ln in range(fn.line, fn.close_line + 1):
                if ln in lines:
                    fn.authors[lines[ln]] += 1
    return git_log_authors(root)


# --------------------------------------------------------------------------
#  Graph
# --------------------------------------------------------------------------

def build_graph(parsed_files, externals=("write",)):
    """Nodes for every function (+ external sinks it calls), edges caller->callee.
    A call to a name defined in several files links to all of them (ambiguous)."""
    funcs = [fn for P in parsed_files for fn in P.funcs]
    by_name = {}
    for fn in funcs:
        by_name.setdefault(fn.name, []).append(fn)
    nodes = {fn.id: {"id": fn.id, "name": fn.name, "file": fn.file, "fn": fn}
             for fn in funcs}
    edges = Counter()
    ambiguous = set()
    for fn in funcs:
        for callee, _ in fn.calls:
            targets = by_name.get(callee)
            if targets:
                same = [t for t in targets if t.file == fn.file]
                tg = same or targets
                for t in tg:
                    edges[(fn.id, t.id)] += 1
                    if len(tg) > 1:
                        ambiguous.add((fn.id, t.id))
            elif callee in externals or externals == "*":
                eid = "ext::" + callee
                nodes.setdefault(eid, {"id": eid, "name": callee, "file": None, "fn": None})
                edges[(fn.id, eid)] += 1
    return nodes, edges, ambiguous


def svg_graph(nodes, edges, ambiguous, file_colors, roots=(), flags=None):
    """Layered left-to-right call graph. flags: {node_id: set('dead','over','entry')}."""
    flags = flags or {}
    ids = list(nodes)
    if not ids:
        return '<p class="dim">no functions found</p>'
    indeg = Counter(b for (a, b) in edges if a != b)
    layer = {n: 0 for n in ids if indeg[n] == 0 or n in roots}
    for n in ids:
        layer.setdefault(n, 0)
    for _ in range(len(ids)):
        changed = False
        for (a, b) in edges:
            if a != b and layer[a] + 1 > layer[b] and layer[a] + 1 < len(ids) \
                    and not _reaches(edges, b, a):
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    cols = {}
    for n in ids:
        cols.setdefault(layer[n], []).append(n)

    def sort_key(n):
        fn = nodes[n]["fn"]
        return (nodes[n]["file"] is None, nodes[n]["file"] or "", fn.line if fn else 0)

    W, H, CG, RG, PAD = 190, 52, 86, 20, 24
    pos = {}
    ncol = max(cols) + 1
    for c in range(ncol):
        col = cols.get(c, [])
        if c == 0:
            col.sort(key=sort_key)
        else:
            def bary(n):
                ps = [pos[a][1] for (a, b) in edges if b == n and a in pos]
                return (sum(ps) / len(ps)) if ps else 1e9
            col.sort(key=lambda n: (bary(n), sort_key(n)))
        cols[c] = col
        for r, n in enumerate(col):
            pos[n] = (c, r)
    maxrows = max(len(v) for v in cols.values())
    height = PAD * 2 + maxrows * H + (maxrows - 1) * RG + 30
    width = PAD * 2 + ncol * W + (ncol - 1) * CG

    def xy(n):
        c, r = pos[n]
        colh = len(cols[c]) * H + (len(cols[c]) - 1) * RG
        top = PAD + (maxrows * H + (maxrows - 1) * RG - colh) / 2
        return PAD + c * (W + CG), top + r * (H + RG)

    out = [f'<svg class="graph" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" xmlns="http://www.w3.org/2000/svg">',
           '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" '
           'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           '<path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>']
    for (a, b), cnt in edges.items():
        ax, ay = xy(a)
        bx, by = xy(b)
        color = file_colors.get(nodes[a]["file"], "#888")
        dash = ' stroke-dasharray="5 4"' if (a, b) in ambiguous else ""
        if a == b:
            x0, y0 = ax + W - 30, ay
            d = f"M{x0},{y0} C{x0},{y0-34} {x0+40},{y0-34} {x0+24},{y0}"
            lx, ly = x0 + 20, y0 - 30
        elif pos[b][0] > pos[a][0]:
            x0, y0 = ax + W, ay + H / 2
            x1, y1 = bx - 2, by + H / 2
            mx = (x0 + x1) / 2
            d = f"M{x0},{y0} C{mx},{y0} {mx},{y1} {x1},{y1}"
            lx, ly = mx, (y0 + y1) / 2 - 4
        else:
            x0, y0 = ax + W / 2, ay + H
            x1, y1 = bx + W / 2, by + H + 2
            dip = max(y0, y1) + 34
            d = f"M{x0},{y0} C{x0},{dip} {x1},{dip} {x1},{y1}"
            lx, ly = (x0 + x1) / 2, dip - 6
        out.append(f'<g class="edge" data-from="{esc(a)}" data-to="{esc(b)}" '
                   f'style="color:{color}"><path d="{d}" fill="none" stroke="currentColor" '
                   f'stroke-width="1.8" marker-end="url(#arr)"{dash}/>')
        if cnt > 1:
            out.append(f'<text x="{lx:.0f}" y="{ly:.0f}" class="ecount" '
                       f'text-anchor="middle">×{cnt}</text>')
        out.append("</g>")
    for n in ids:
        x, y = xy(n)
        node = nodes[n]
        fn = node["fn"]
        fl = flags.get(n, set())
        color = file_colors.get(node["file"], "#8a8f98")
        cls = "node" + (" ext" if fn is None else "") + "".join(" " + f for f in sorted(fl))
        stroke = "#e0584d" if "over" in fl else color
        dash = ' stroke-dasharray="6 4"' if "dead" in fl else ""
        sub = f"{node['file']} · {fn.nlines} lines" if fn else "external"
        anchor = f"fn-{_slug(n)}" if fn else ""
        out.append(f'<g class="{cls}" data-id="{esc(n)}" data-anchor="{anchor}" '
                   f'transform="translate({x:.0f},{y:.0f})">'
                   f'<rect width="{W}" height="{H}" rx="9" fill="{color}" fill-opacity="0.13" '
                   f'stroke="{stroke}" stroke-width="{2.4 if "entry" in fl else 1.5}"{dash}/>'
                   f'<text x="12" y="21" class="nname">{esc(node["name"])}'
                   f'{"()" if fn else ""}</text>'
                   f'<text x="12" y="39" class="nsub">{esc(sub)}</text>')
        if "forbidden" in fl:
            stroke = "#e0584d"
            out[-1] = out[-1].replace(f'stroke="{color}"', 'stroke="#e0584d"')
            out.append(f'<text x="{W-10}" y="21" class="ntag bad" text-anchor="end">FORBIDDEN</text>')
        elif "entry" in fl:
            out.append(f'<text x="{W-10}" y="21" class="ntag" text-anchor="end">ENTRY</text>')
        elif "dead" in fl:
            out.append(f'<text x="{W-10}" y="21" class="ntag bad" text-anchor="end">UNUSED</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def _reaches(edges, src, dst):
    """True if dst is reachable from src (used to avoid layering cycles)."""
    adj = {}
    for (a, b) in edges:
        adj.setdefault(a, []).append(b)
    seen, st = set(), [src]
    while st:
        n = st.pop()
        if n == dst:
            return True
        if n in seen:
            continue
        seen.add(n)
        st.extend(adj.get(n, []))
    return False


def _slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s)


def fn_anchor(fn):
    return "fn-" + _slug(fn.id)


# --------------------------------------------------------------------------
#  Outline / cards / source
# --------------------------------------------------------------------------

def _code_inline(text, known):
    """Escape a code snippet, highlighting calls to known functions + char literals."""
    parts = re.split(r"('(?:\\.|[^'\\])+'|[A-Za-z_]\w*(?=\s*\())", text)
    res = []
    for p in parts:
        if not p:
            continue
        if p.startswith("'"):
            res.append(f'<span class="lit">{esc(p)}</span>')
        elif IDENT.match(p) and p in known:
            res.append(f'<a class="call" href="#{known[p]}">{esc(p)}</a>')
        elif IDENT.match(p) and p not in CTRL:
            res.append(f'<span class="ext">{esc(p)}</span>')
        else:
            res.append(esc(p))
    return "".join(res)


def outline_html(nodes, known, line_href=None):
    out = []
    for n in nodes:
        k = n["k"]
        ln = n.get("line")
        lnk = (f'<a class="ln" href="{line_href(ln)}">L{ln}</a>' if line_href and ln
               else f'<span class="ln">L{ln}</span>' if ln else "")
        if k == "decl":
            continue
        if k == "loop":
            out.append(f'<div class="ol loop"><div class="olh"><span class="kw">⟳ {esc(n["kw"])}</span> '
                       f'<code>{_code_inline(n["cond"], known)}</code>{lnk}</div>'
                       f'<div class="olk">{outline_html(n["kids"], known, line_href)}</div></div>')
        elif k == "if":
            for label, cond, kids, bl in n["branches"]:
                blnk = (f'<a class="ln" href="{line_href(bl)}">L{bl}</a>' if line_href else "")
                c = f' <code>{_code_inline(cond, known)}</code>' if cond else ""
                out.append(f'<div class="ol branch"><div class="olh"><span class="kw">◇ {esc(label)}</span>'
                           f'{c}{blnk}</div><div class="olk">{outline_html(kids, known, line_href)}</div></div>')
        elif k == "return":
            out.append(f'<div class="ol ret"><span class="kw">↩</span> <code>{_code_inline(n["text"], known)}</code>{lnk}</div>')
        elif k == "call":
            out.append(f'<div class="ol callst"><span class="kw">→</span> <code>{_code_inline(n["text"], known)}</code>{lnk}</div>')
        else:
            out.append(f'<div class="ol st"><code>{_code_inline(n["text"], known)}</code>{lnk}</div>')
    return "".join(out)


def function_card(fn, known, color, flags=(), line_href=None, max_lines=25):
    over = fn.nlines > max_lines
    pct = min(fn.nlines / max_lines, 1.0) * 100
    badges = []
    if "entry" in flags:
        badges.append('<span class="badge entry">entry</span>')
    if "dead" in flags:
        badges.append('<span class="badge bad">never called</span>')
    if fn.name in fn.callees():
        badges.append('<span class="badge">recursive</span>')
    if over:
        badges.append(f'<span class="badge bad">{fn.nlines} &gt; {max_lines} lines</span>')
    if len(fn.params) > 4:
        badges.append('<span class="badge bad">&gt; 4 params</span>')
    authors = ""
    if fn.authors:
        tot = sum(fn.authors.values())
        authors = '<div class="authors">' + "".join(
            f'<span class="author">{esc(a)} {round(100 * c / tot)}%</span>'
            for a, c in fn.authors.most_common()) + "</div>"
    chars = ""
    if fn.chars:
        chars = '<div class="chips"><span class="lbl">chars</span>' + "".join(
            f'<span class="chip lit">{esc(c)}</span>' for c in fn.chars) + "</div>"
    locs = ""
    if fn.locals:
        locs = '<div class="chips"><span class="lbl">locals</span>' + "".join(
            f'<span class="chip">{esc(l)}</span>' for l in fn.locals) + "</div>"
    head_href = line_href(fn.line) if line_href else "#"
    return (f'<div class="card" id="{fn_anchor(fn)}" style="--fc:{color}">'
            f'<div class="cardh"><a class="fname" href="{head_href}">{esc(fn.name)}</a>'
            f'<span class="sig">({esc(", ".join(fn.params) or "void")}) → {esc(fn.ret)}</span>'
            f'{"".join(badges)}</div>'
            f'<div class="meta"><span class="file" style="color:{color}">{esc(fn.file)}:{fn.line}</span>'
            f'<span class="bar{" over" if over else ""}"><i style="width:{pct:.0f}%"></i></span>'
            f'<span class="dim">{fn.nlines}/{max_lines} lines · {fn.loops} loop · {fn.branches} if</span></div>'
            f'{authors}{chars}{locs}'
            f'<div class="outline">{outline_html(fn.outline, known, line_href) or "<span class=dim>(empty)</span>"}</div>'
            f'</div>')


_HL = re.compile(r"\b(" + "|".join(sorted(C_KEYWORDS)) + r")\b")


def source_html(P, file_id, fn_lines=None, bad_lines=None):
    """Line-numbered source with light highlighting. fn_lines: {line: anchor}."""
    fn_lines = fn_lines or {}
    bad_lines = bad_lines or {}
    lines, cur, kinds = [], [], []
    start = 0
    for i, ch in enumerate(P.src + "\n"):
        if ch == "\n":
            lines.append((P.src[start:i], P.kinds[start:i]))
            start = i + 1
    if lines and lines[-1] == ("", []):
        lines.pop()
    rows = []
    for no, (text, ks) in enumerate(lines, 1):
        segs, buf, bk = [], "", None
        for ch, k in zip(text, ks + [""] * (len(text) - len(ks))):
            if k != bk and buf:
                segs.append((buf, bk))
                buf = ""
            buf += ch
            bk = k
        if buf:
            segs.append((buf, bk))
        h = []
        for s, k in segs:
            if k == "c":
                h.append(f'<span class="cm">{esc(s)}</span>')
            elif k == "s":
                h.append(f'<span class="lit">{esc(s)}</span>')
            elif k == "p":
                h.append(f'<span class="pp">{esc(s)}</span>')
            else:
                h.append(_HL.sub(lambda m: f'<span class="kw">{m.group(1)}</span>', esc(s)))
        cls = "sl"
        title = ""
        if no in bad_lines:
            cls += " badl"
            title = f' title="{esc(bad_lines[no])}"'
        aid = f' id="{fn_lines[no]}-src"' if no in fn_lines else ""
        rows.append(f'<div class="{cls}" id="{file_id}-L{no}"{title}{aid}><span class="no">{no}</span>'
                    f'<span class="tx">{"".join(h) or " "}</span></div>')
    return '<div class="src">' + "".join(rows) + "</div>"


# --------------------------------------------------------------------------
#  Page chrome shared by the reports
# --------------------------------------------------------------------------

BASE_CSS = r"""
/* tokens, fonts, canvas, buttons, pills, panels: common/skin.css (inlined by page()) */
code,.src,.grid,.mono{font-family:var(--mono);font-variant-ligatures:none}
.wrap{max-width:1360px;margin:0 auto;padding:0 28px 96px}
header.top{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:flex-end;padding:34px 0 18px;border-bottom:1px solid var(--line)}
header.top h1{overflow-wrap:anywhere}
.dim{color:var(--dim)}
nav.toc{display:flex;flex-wrap:wrap;gap:6px;margin:16px 0 4px;position:sticky;top:10px;z-index:5;padding:7px;border-radius:999px;
  background:var(--glass);border:1px solid var(--line);box-shadow:inset 0 1px 0 var(--rim),var(--shadow);backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%)}
nav.toc a{padding:4px 13px;border-radius:999px;text-decoration:none;font-size:13px;white-space:nowrap}
nav.toc a:hover{background:var(--chip)}
section{margin-top:38px;scroll-margin-top:70px}
.panel{padding:16px 18px}
table.checks{width:100%;border-collapse:collapse}
table.checks td{padding:9px 10px;border-top:1px solid var(--line);vertical-align:top}
table.checks tr:first-child td{border-top:0}
.st{font:600 12px var(--mono);letter-spacing:.06em;white-space:nowrap}
.st.ok{color:var(--ok)}.st.bad{color:var(--bad)}.st.warn{color:var(--warn)}.st.na{color:var(--dim)}
pre.log{background:var(--code);border-radius:8px;padding:8px 10px;margin:6px 0 0;overflow:auto;font-size:12px;max-height:260px;white-space:pre-wrap}
.graphwrap{overflow:auto;padding:8px}
svg.graph{display:block;color:var(--ink)}
svg.graph .nname{font:600 14px var(--mono);fill:var(--ink)}
svg.graph .nsub{font:11px var(--sans);fill:var(--dim)}
svg.graph .ntag{font:700 9px var(--sans);letter-spacing:.08em;fill:var(--dim)}
svg.graph .ntag.bad{fill:var(--bad)}
svg.graph .ecount{font:600 11px var(--sans);fill:var(--dim)}
svg.graph .node{cursor:pointer}
svg.graph .edge path{opacity:.75}
svg.graph.focus .edge{opacity:.12}svg.graph.focus .node{opacity:.3}
svg.graph.focus .edge.on{opacity:1}svg.graph.focus .node.on{opacity:1}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 2px;font-size:12px;color:var(--dim)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:12px;margin-top:12px}
@media (max-width:520px){.cards{grid-template-columns:1fr}}
.card{background:var(--glass);border:1px solid var(--line);border-left:3px solid var(--fc);border-radius:14px;padding:12px 14px;min-width:0;box-shadow:inset 0 1px 0 var(--rim)}
.card:target{outline:2px solid var(--fc)}
.cardh{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px}
.fname{font:700 15px var(--mono);text-decoration:none}
.sig{font:12px var(--mono);color:var(--dim);overflow-wrap:anywhere}
.badge{font-size:11px;padding:1px 7px;border-radius:999px;background:var(--chip);color:var(--dim);font-weight:600}
.badge.bad{color:var(--bad);background:color-mix(in srgb,var(--bad) 14%,transparent)}
.badge.entry{color:var(--accent);background:color-mix(in srgb,var(--accent) 14%,transparent)}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:12px;margin:4px 0 6px}
.bar{display:inline-block;width:80px;height:6px;border-radius:3px;background:var(--chip);overflow:hidden}
.bar i{display:block;height:100%;background:var(--ok)}.bar.over i{background:var(--bad)}
.chips{display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin:3px 0}
.chips .lbl{font-size:11px;color:var(--dim);margin-right:2px;text-transform:uppercase;letter-spacing:.05em}
.authors{display:flex;flex-wrap:wrap;gap:4px;margin:2px 0}
.author{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:0 7px}
.outline{margin-top:6px;font-size:12.5px}
.ol{margin:2px 0}.ol code{font-size:12.5px;overflow-wrap:anywhere}
.olh{display:flex;gap:6px;align-items:baseline}
.olk{margin-left:9px;padding-left:10px;border-left:2px solid var(--line)}
.ol.loop>.olk{border-left-color:#4c8df6}.ol.branch>.olk{border-left-color:#e39b2d}
.ol .kw{font-weight:700;font-size:12px;white-space:nowrap}
.ol.loop>.olh .kw{color:#4c8df6}.ol.branch>.olh .kw{color:#e39b2d}
.ol.ret .kw{color:#c45fd0}.ol.callst .kw{color:#3fb67e}.ol.st code{color:var(--dim)}
.ln{margin-left:auto;font-size:10.5px;color:var(--dim);text-decoration:none;padding-left:8px;white-space:nowrap}
a.call{color:#3fb67e;font-weight:600;text-decoration:none}
.ext{color:var(--ink)}
.lit{color:#d4683a}
.src{background:var(--glass);border:1px solid var(--line);border-radius:14px;font-size:12.5px;overflow:auto;tab-size:4;padding:6px 0}
.sl{display:flex;white-space:pre}.sl:target,.sl.hl{background:color-mix(in srgb,var(--accent) 16%,transparent)}
.sl.badl{background:color-mix(in srgb,var(--bad) 14%,transparent)}
.sl .no{display:inline-block;min-width:3.2em;text-align:right;padding-right:12px;color:var(--dim);user-select:none}
.src .kw{color:#4c8df6}.src .cm{color:var(--dim)}.src .pp{color:#9a7ff0}
details>summary{cursor:pointer;font-weight:600;padding:4px 0}
.themebtn{margin-left:auto}
"""

BASE_JS = r"""
(function(){
  var root=document.documentElement;
  try{var t=localStorage.getItem('rush-theme');if(t)root.setAttribute('data-theme',t);}catch(e){}
  var b=document.querySelector('.themebtn');
  if(b)b.onclick=function(){var dark=root.getAttribute('data-theme')==='dark'||
    (!root.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme: dark)').matches);
    var t=dark?'light':'dark';root.setAttribute('data-theme',t);try{localStorage.setItem('rush-theme',t);}catch(e){}};
  document.querySelectorAll('svg.graph').forEach(function(svg){
    svg.querySelectorAll('.node').forEach(function(n){
      var id=n.getAttribute('data-id');
      n.addEventListener('mouseenter',function(){svg.classList.add('focus');n.classList.add('on');
        svg.querySelectorAll('.edge').forEach(function(e){
          if(e.getAttribute('data-from')===id||e.getAttribute('data-to')===id){e.classList.add('on');
            var o=e.getAttribute('data-from')===id?e.getAttribute('data-to'):e.getAttribute('data-from');
            var on=svg.querySelector('.node[data-id="'+CSS.escape(o)+'"]');if(on)on.classList.add('on');}});});
      n.addEventListener('mouseleave',function(){svg.classList.remove('focus');
        svg.querySelectorAll('.on').forEach(function(e){e.classList.remove('on');});});
      n.addEventListener('click',function(){var a=n.getAttribute('data-anchor');
        if(a){var el=document.getElementById(a);if(el){location.hash=a;el.scrollIntoView({behavior:'smooth',block:'center'});}}});
    });
  });
  document.querySelectorAll('[data-tabs]').forEach(function(box){
    var btns=box.querySelectorAll('[data-tab]');
    btns.forEach(function(b){b.onclick=function(){
      btns.forEach(function(x){x.classList.toggle('on',x===b);});
      box.querySelectorAll('[data-pane]').forEach(function(p){p.hidden=p.getAttribute('data-pane')!==b.getAttribute('data-tab');});
    };});
  });
})();
"""


SKIN_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skin.css")


def skin_css():
    try:
        with open(SKIN_CSS_PATH, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def page(title, body, extra_css=""):
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{esc(title)}</title><style>{skin_css()}{BASE_CSS}{extra_css}</style></head>"
            f"<body><div class=\"wrap\">{body}</div><script>{BASE_JS}</script></body></html>")
