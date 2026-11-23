"""Lines to ask about, as the eval sheet's "Explanation" asks: bit shifts,
complex lines, recursion (and what it returns), and malloc results never
compared with NULL. Each item is a fact about the code text, with its line;
the evaluator asks the question.
"""

import re

from .detect_read import IDENT, TEXT_CAP, read_line

SHIFTS = {"<<", ">>", "<<=", ">>="}
OPERATORS = {"&&", "||", "==", "!=", "<=", ">=", "<", ">", "+", "-", "*",
             "/", "%", "!", "?", "&", "|", "^", "<<", ">>"}
NOT_CALLS = {"if", "while", "for", "return", "sizeof"}
COMPLEX_SCORE = 7      # operators + 2 per call nested in a call's arguments
COMPLEX_CAP = 6         # the most complex lines only
SHIFT_CAP = 8
RETURNS_CAP = 4


def ask_lines(team):
    """-> [{"kind", "file", "line", "text", "why"}]; kinds in this order:
    shift, complex, recursion, malloc."""
    out = []
    for fn in team["funcs"]:
        out += ask_shifts(fn)
    out = out[:SHIFT_CAP]
    complex_lines = []
    for fn in team["funcs"]:
        complex_lines += ask_complex(fn)
    complex_lines.sort(key=lambda x: -x.pop("score"))
    out += complex_lines[:COMPLEX_CAP]
    out += ask_recursion(team)
    for fn in team["funcs"]:
        out += ask_malloc(fn)
    return out


def ask_item(kind, fn, line, why):
    return {"kind": kind, "file": fn["file"], "line": line,
            "text": read_line(fn["ctx"], line), "why": why}


def ask_body_tokens(fn):
    T = fn["ctx"]["toks"]
    return [T[j] for j in range(fn["lb"] + 1, fn["rb"])]


def ask_shifts(fn):
    """Every line in a function body with << or >> (one item per line)."""
    seen = {}
    for t in ask_body_tokens(fn):
        if t.v in SHIFTS:
            seen.setdefault(t.line, set()).add(t.v)
    return [ask_item("shift", fn, line,
                     "bit shift " + " ".join(sorted(ops)) + ": ask what it is")
            for line, ops in sorted(seen.items())]


def ask_complex(fn):
    """Statements and conditions (whole, even over several lines) with many
    operators, or a call inside a call's arguments."""
    T = fn["ctx"]["toks"]
    out, seen = [], set()
    for node in fn["nodes"]:
        if node["k"] not in ("stmt", "decl", "return", "if", "loop") \
                or "a" not in node or node["line"] in seen:
            continue
        toks = T[node["a"]:node["b"] + 1]
        ops = sum(1 for t in toks if t.v in OPERATORS)
        nested, parens = 0, []          # parens: is each open '(' a call?
        for k, t in enumerate(toks):
            if t.v == "(":
                is_call = k > 0 and bool(IDENT.match(toks[k - 1].v)) \
                    and toks[k - 1].v not in NOT_CALLS
                if is_call and any(parens):
                    nested += 1
                parens.append(is_call)
            elif t.v == ")" and parens:
                parens.pop()
        score = ops + 2 * nested
        if score < COMPLEX_SCORE:
            continue
        seen.add(node["line"])
        parts = [f"{ops} operators"] if ops else []
        if nested:
            parts.append(f"{nested} call(s) inside a call")
        span = toks[-1].line - node["line"]
        if span:
            parts.append(f"{span + 1} lines")
        item = ask_item("complex", fn, node["line"],
                        ", ".join(parts) + ": ask what this does")
        item["score"] = score
        out.append(item)
    return out


def ask_recursion(team):
    """Functions that call themselves (or each other in a pair), with their
    return lines: the sheet asks what they return when the grid is full and
    when it is impossible."""
    out = []
    by_gid = team["by_gid"]
    for fn in team["funcs"]:
        callees = team["callees"].get(fn["gid"], set())
        if fn["gid"] in callees:
            how = "calls itself"
        else:
            pair = [g for g in callees if g in by_gid
                    and fn["gid"] in team["callees"].get(g, set())]
            if not pair:
                continue
            how = f"calls {by_gid[pair[0]]['name']}(), which calls it back"
        rets = [n for n in fn["nodes"] if n["k"] == "return"]
        valued = [n for n in rets if n["text"].strip() != "return"]
        if valued:
            said = "; ".join(f"`{n['text'][:40]}` (line {n['line']})"
                             for n in valued[:RETURNS_CAP])
            ask = (f"Returns: {said}. Ask what it returns when the grid is "
                   "full, and when the grid is impossible")
        else:
            ask = ("Returns no value: ask how it stops, and how the result "
                   "gets back to the caller")
        out.append(ask_item("recursion", fn, fn["line"],
                            f"recursive: {fn['name']}() {how}. {ask}"))
    return out


def ask_malloc(fn):
    """Each malloc whose result this function never compares with NULL."""
    out = []
    conds = [n for n in fn["nodes"] if n["k"] in ("if", "loop")]
    cond_texts = []
    for n in conds:
        cond_texts.append((n["line"], n["text"]))
        for br in n.get("branches", []):
            if br["cond"]:
                cond_texts.append((br["line"], br["cond"]))
    for call in fn["calls"]:
        if call["name"] != "malloc":
            continue
        node = call["node"]
        if node is not None and node["k"] in ("if", "loop"):
            continue                    # malloc inside a condition: tested
        text = read_line(fn["ctx"], call["line"])
        if node is not None and node["k"] == "return":
            out.append(ask_item("malloc", fn, call["line"],
                                f"{fn['name']}() returns the malloc result: "
                                "check that its callers test it for NULL"))
            continue
        m = re.search(r"([A-Za-z_][\w.\[\]>-]*?)\s*=\s*(?:\([^()]*\)\s*)?"
                      r"malloc\s*\(", text)
        if not m:
            out.append(ask_item("malloc", fn, call["line"],
                                "malloc result used directly, never tested "
                                "for NULL"))
            continue
        lhs = m.group(1)
        if not any(ask_tests_null(lhs, c) for line, c in cond_texts
                   if line >= call["line"]):
            out.append(ask_item("malloc", fn, call["line"],
                                f"`{lhs}` (from malloc) is never compared with "
                                "NULL here: make malloc fail and ask"))
    return out


def ask_tests_null(lhs, cond):
    """True when the condition text tests lhs: `!x`, `x == NULL`, `x == 0`,
    `x != NULL`, `NULL == x`, or just `x`."""
    x = re.escape(lhs)
    cond = cond.strip()[:TEXT_CAP * 4]
    patterns = [rf"!\s*\(?\s*{x}(?![\w\[])", rf"{x}\s*[!=]=\s*(NULL|0)\b",
                rf"\b(NULL|0)\s*[!=]=\s*{x}(?![\w\[])", rf"^\(?\s*{x}\s*\)?$"]
    return any(re.search(p, cond) for p in patterns)
