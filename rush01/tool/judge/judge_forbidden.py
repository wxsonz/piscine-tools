"""Forbidden functions (PLAN.md §6 step 3): undefined symbols of the LINKED
binary (`nm -u`, @GLIBC_* stripped) and calls in the source to names the team
does not define. Facts checked on gcc 16 / clang (PROOF-8): printf("Error\n")
links as `puts` (gcc) or `printf` (clang -O0); a local `int g[4][4] = {0}`
emits no memset, `int g[9][9] = {0}` and struct copies emit memset / memcpy.
"""

import os
import re
import shutil

import codemap

from .judge_process import run_capped

NM_MS = 30_000
CRT_NAMES = {"__libc_start_main", "__cxa_finalize", "__gmon_start__",
             "__stack_chk_fail", "_GLOBAL_OFFSET_TABLE_"}
CRT_PREFIX = "_ITM_"
AGGREGATE_OPS = {"memset", "memcpy", "memmove", "bcmp"}
WARN_HEADERS = {"<stdio.h>", "<string.h>"}
NOTE_HEADERS = {"<stdlib.h>"}
# libc names a team may define itself (3.3: "defines own strlen" is a note)
LIBC_NAMES = {
    "strlen", "strcpy", "strncpy", "strcat", "strncat", "strcmp", "strncmp",
    "strchr", "strrchr", "strstr", "strdup", "strndup", "strlcpy", "strlcat",
    "memset", "memcpy", "memmove", "memcmp", "memchr", "bzero", "bcmp",
    "atoi", "atol", "strtol", "itoa", "calloc", "realloc", "printf", "puts",
    "putchar", "isdigit", "isalpha", "isspace", "isalnum", "isprint",
    "toupper", "tolower", "abs", "exit", "sqrt", "pow", "qsort", "free",
    "malloc", "write", "read"}
DEFINE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)", re.M)
IDENT = re.compile(r"[A-Za-z_]\w*")


def check_forbidden(copy_abs, files, binary_abs, allowed):
    """-> the "forbidden" part of the judge result (SHAPES). binary_abs is
    None when the build failed (then only the source half runs)."""
    names = []
    notes = []
    allowed = set(allowed)
    # 1. read the team's .c and .h: what it defines, calls and includes
    parsed = []
    for rel in files["sources"] + files["headers"]:
        try:
            parsed.append((rel, codemap.parse_file(os.path.join(copy_abs, rel))))
        except Exception as e:  # untrusted code: a tokenizer crash is a note
            notes.append(f"could not read {rel}: {e}")
    defined = set()
    for _, P in parsed:
        defined |= {fn.name for fn in P.funcs}
        defined |= set(DEFINE.findall(P.src))
    called = set()
    for _, P in parsed:
        for fn in P.funcs:
            called |= set(fn.callees())
    # 2. the linked binary: every undefined symbol not allowed or runtime
    if binary_abs is None:
        notes.append("build failed: binary check skipped (source check only)")
    elif shutil.which("nm") is None:
        notes.append("nm not found: binary check skipped (source check only)")
    else:
        for sym in _undefined_symbols(binary_abs, copy_abs):
            if sym in allowed or sym in CRT_NAMES or sym.startswith(CRT_PREFIX):
                continue
            if sym in AGGREGATE_OPS and sym not in called:
                notes.append(f"compiler-generated: {sym} (e.g. = {{0}})")
                continue
            names.append({"name": sym, "where": "binary", "file": None, "line": None})
    # 3. the source: calls to names the team doesn't define, one per name and
    #    file (a call through a parameter or local, a function pointer, is theirs)
    seen = set()
    for rel, P in parsed:
        for fn in P.funcs:
            declared = fn.params + [d.split("=", 1)[0] for d in fn.locals]
            own_vars = set(IDENT.findall(" ".join(declared)))
            for name, line in fn.calls:
                if name in defined or name in allowed or name in own_vars \
                        or (name, rel) in seen:
                    continue
                seen.add((name, rel))
                # no binary: an unknown name may be the team's missing
                # function, not a library call (truth first: say so)
                if binary_abs is None and name not in LIBC_NAMES:
                    notes.append(f"calls {name}() ({rel}:{line}) but no file "
                                 "defines it: missing, or a library function")
                    continue
                names.append({"name": name, "where": "source", "file": rel, "line": line})
    # 4. own libc names and includes: notes, never forbidden
    for name in sorted(defined & LIBC_NAMES):
        notes.append(f"defines own {name}")
    for rel, P in parsed:
        for inc in P.includes:
            if inc in WARN_HEADERS:
                notes.append(f"warning: includes {inc} ({rel})")
            elif inc in NOTE_HEADERS:
                notes.append(f"includes {inc} ({rel}): note only")
    return {"names": names, "notes": notes}


def _undefined_symbols(binary_abs, cwd):
    """Names from `nm -u`, version suffixes (@GLIBC_2.2.5) stripped, in order."""
    r = run_capped(["nm", "-u", binary_abs], cwd, NM_MS)
    syms = []
    for line in r["stdout"].decode("utf-8", "replace").split("\n"):
        parts = line.split()
        if not parts:
            continue
        sym = parts[-1].split("@", 1)[0]
        if sym and sym not in syms:
            syms.append(sym)
    return syms
