# Runs inside gdb:  gdb -q -nx -batch -x gdbtrace.py   (config in $RUSHTRACE_CFG)
#
# Steps the student's code line by line from the entry function and writes a
# JSON timeline. Each step has the line about to run, the user call stack
# (newest first) with every visible variable, the result of the condition
# when the line is an if / else if / while, and the write() calls that
# happened while that line ran, each with the stack that made it.
#
# Only frames whose source file is in cfg["files"] count as user code; the
# harness main (compiled without -g) and libc are stepped over.
import json
import os
import re
import time

import gdb

CFG = json.load(open(os.environ["RUSHTRACE_CFG"]))
FILES = set(CFG["files"])
CONDS = CFG.get("conds", {})
MAX_STEPS = CFG.get("max_steps", 20000)
DEADLINE = time.monotonic() + CFG.get("max_seconds", 25)
UNSAFE = re.compile(r"[A-Za-z_]\w*\s*\(|\+\+|--|(?<![=!<>])=(?!=)")

for cmd in ("set pagination off", "set confirm off", "set width 0", "set height 0",
            "set breakpoint pending on", "set debuginfod enabled off",
            "set disable-randomization on", "set print elements 40",
            "set startup-with-shell off"):
    try:
        gdb.execute(cmd, to_string=True)
    except gdb.error:
        pass

state = {"exit": None, "signal": None}
pending = []
steps = []
stores = {}      # address -> index of the step whose line stored a byte there
SRC = {}         # basename -> source lines (to spot `buf[i] = c` style stores)
for _name, _path in CFG.get("paths", {}).items():
    try:
        SRC[_name] = open(_path, encoding="utf-8", errors="replace").read().split("\n")
    except OSError:
        pass
STORE = re.compile(r"^\s*([^=;]*?(?:\[|\*)[^=;]*?)\s*(?<![=!<>+\-*/%&|^])=(?!=)")


def on_exit(ev):
    state["exit"] = getattr(ev, "exit_code", 0)


def on_stop(ev):
    if isinstance(ev, gdb.SignalEvent) and ev.stop_signal not in ("SIGTRAP", "0"):
        state["signal"] = ev.stop_signal


gdb.events.exited.connect(on_exit)
gdb.events.stop.connect(on_stop)


def alive():
    try:
        return gdb.selected_inferior().pid != 0 and state["exit"] is None \
            and state["signal"] is None
    except gdb.error:
        return False


def base(symtab):
    return os.path.basename(symtab.filename) if symtab else None


def val(v):
    try:
        t = v.type.strip_typedefs()
        code = t.code
        if code in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_CHAR, gdb.TYPE_CODE_BOOL,
                    gdb.TYPE_CODE_ENUM):
            n = int(v)
            if t.sizeof == 1 and code != gdb.TYPE_CODE_BOOL:
                return {"c": n & 0xFF}
            return n
        if code == gdb.TYPE_CODE_PTR:
            tt = t.target().strip_typedefs()
            addr = int(v)
            if addr == 0:
                return {"p": "NULL"}
            if tt.sizeof == 1:
                try:
                    return {"s": v.string(length=40, errors="replace")}
                except (gdb.error, gdb.MemoryError, UnicodeDecodeError):
                    pass
            return {"p": hex(addr)}
        return {"t": str(v)[:60]}
    except (gdb.error, gdb.MemoryError, RuntimeError, ValueError):
        return {"t": "?"}


def frame_vars(f):
    try:
        b = f.block()
    except RuntimeError:
        return {}
    res = {}
    while b is not None:
        for sym in b:
            if (sym.is_argument or sym.is_variable) and sym.name not in res:
                try:
                    res[sym.name] = val(sym.value(f))
                except (gdb.error, RuntimeError):
                    res[sym.name] = {"t": "?"}
        if b.function:
            break
        b = b.superblock
    return res


def user_stack(with_vars=True):
    st = []
    f = gdb.newest_frame()
    while f is not None:
        try:
            sal = f.find_sal()
        except gdb.error:
            sal = None
        if sal and sal.symtab and base(sal.symtab) in FILES:
            rec = {"fn": f.name(), "f": base(sal.symtab), "l": sal.line}
            if with_vars:
                rec["vars"] = frame_vars(f)
            st.append(rec)
        f = f.older()
    return st


def store_addr(fname, line, f):
    """Address a `lhs = ...;` line is about to store to, when lhs is memory (a[i], *p)."""
    text = SRC.get(fname, [])
    if not (0 < line <= len(text)):
        return None
    m = STORE.match(text[line - 1])
    if not m:
        return None
    lhs = m.group(1).strip()
    lhs = re.sub(r"(\w+)\s*(\+\+|--)", r"\1", lhs)          # buf[i++] -> buf[i]
    lhs = re.sub(r"\+\+\s*(\w+)", r"(\1 + 1)", lhs)          # buf[++i] -> buf[(i + 1)]
    lhs = re.sub(r"--\s*(\w+)", r"(\1 - 1)", lhs)
    if UNSAFE.search(lhs):
        return None
    try:
        f.select()
        v = gdb.parse_and_eval(f"&({lhs})")
        return int(v), int(v.dereference().type.sizeof)
    except (gdb.error, RuntimeError, ValueError):
        return None


def eval_cond(cond, f):
    if UNSAFE.search(cond):
        return None
    try:
        f.select()
        return bool(int(gdb.parse_and_eval(cond)))
    except (gdb.error, RuntimeError, ValueError):
        return None


ARCH = ""
REGS = ("$rdi", "$rsi", "$rdx")


class Write(gdb.Breakpoint):
    def stop(self):
        try:
            fd = int(gdb.parse_and_eval(REGS[0]))
            buf = int(gdb.parse_and_eval(REGS[1]))
            n = int(gdb.parse_and_eval(REGS[2]))
            if fd in (1, 2) and 0 < n <= 65536:
                data = bytes(gdb.selected_inferior().read_memory(buf, n)).decode("latin-1")
                rec = {"fd": fd, "d": data, "stack": user_stack(False)}
                prov = [stores.get(buf + k) for k in range(n)]
                if any(p is not None for p in prov):
                    rec["prov"] = prov  # step index that stored each byte
                pending.append(rec)
        except (gdb.error, gdb.MemoryError, RuntimeError):
            pass
        return False  # record and keep going: never disturbs the stepping


def main():
    global ARCH, REGS
    gdb.execute(f"file {CFG['exe']}", to_string=True)
    gdb.execute(f"set args {' '.join(str(a) for a in CFG['args'])}", to_string=True)
    try:
        gdb.execute("set inferior-tty /dev/null", to_string=True)
    except gdb.error:
        pass
    gdb.Breakpoint(CFG["entry"], internal=True)
    gdb.execute("starti", to_string=True)
    ARCH = gdb.selected_inferior().architecture().name()
    if "aarch64" in ARCH:
        REGS = ("$x0", "$x1", "$x2")
    Write("write", internal=True)
    gdb.execute("continue", to_string=True)

    truncated = False
    while alive():
        if len(steps) >= MAX_STEPS or time.monotonic() > DEADLINE:
            truncated = True
            break
        f = gdb.selected_frame()
        sal = f.find_sal()
        if sal.symtab and base(sal.symtab) in FILES:
            stack = user_stack()
            rec = {"f": base(sal.symtab), "l": sal.line, "stack": stack}
            cond = CONDS.get(f"{rec['f']}:{sal.line}")
            if cond is not None:
                rec["cond"] = eval_cond(cond, f)
            prev = steps[-1] if steps else None
            if prev and prev["f"] == rec["f"] and prev["l"] == rec["l"] \
                    and len(prev["stack"]) == len(stack) and not prev.get("w"):
                steps[-1] = rec  # same line reported twice in a row (is_stmt split)
            else:
                steps.append(rec)
            st = store_addr(rec["f"], sal.line, f)
            gdb.execute("step", to_string=True)
            if st:
                addr, size = st
                for k in range(min(size, 64)):
                    stores[addr + k] = len(steps) - 1
            if pending and steps:
                steps[-1].setdefault("w", []).extend(pending)
                pending.clear()
        else:
            gdb.execute("continue", to_string=True)
            if pending:
                tail = steps[-1] if steps else None
                if tail is not None:
                    tail.setdefault("w", []).extend(pending)
                pending.clear()
    if truncated:
        try:
            gdb.execute("kill", to_string=True)
        except gdb.error:
            pass
    out = {"steps": steps, "exit": state["exit"], "signal": state["signal"],
           "truncated": truncated, "arch": ARCH}
    with open(CFG["out"], "w") as fh:
        json.dump(out, fh)


try:
    main()
except Exception as e:  # noqa: BLE001 — report anything to the caller
    with open(CFG["out"], "w") as fh:
        json.dump({"error": f"{type(e).__name__}: {e}", "steps": steps}, fh)
