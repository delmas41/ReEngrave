"""Outside-the-code memory probe (ROADMAP 2.249; measures, edits nothing under tools/).

usage: mem_run.py WORKTREE OUTDIR LABEL PDF PAGES [--holders] [--cache DIR]

Runs the staged CLI of the tree at WORKTREE (through infer, --musicxml) with
an RSS sampler thread (0.25 s) labelled by the segment the run is in: each
page of GATHER (marked by `gather.gather_external`, the first reader of a
page), each later stage, `Log.to_json`, the file write, the export. Writes
OUTDIR/LABEL.mem.json: per-segment peak / end RSS, RSS at each page start,
the log's row counts, and (--holders) at the end of GATHER the ndarray bytes
reachable from the prepared pages and from every gc-tracked container,
grouped by the container's type -- the names of what holds memory.
"""
import sys, os, time, json, functools, threading, gc, argparse

ap = argparse.ArgumentParser()
ap.add_argument("wt"); ap.add_argument("outdir"); ap.add_argument("label")
ap.add_argument("pdf"); ap.add_argument("pages")
ap.add_argument("--holders", action="store_true")
ap.add_argument("--cache", default=None)
ap.add_argument("--through", default="infer")
ap.add_argument("--trace", default="", help="tracemalloc: snapshot at the start of these pages (1-based, comma list) and at gather end; diff by line")
ap.add_argument("--who", type=int, default=0, help="at the start of this page: who still refers to the EARLIER pages' PageImage objects (frames included)")
ap.add_argument("--mid", type=int, default=0, help="snapshot ndarray holders + live memory at the start of this page (1-based)")
ap.add_argument("--teardown", action="store_true", help="after the run: RSS freed by dropping each log cache, then each row store")
a = ap.parse_args()
os.chdir(a.wt); sys.path.insert(0, a.wt)
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
os.environ.setdefault("OMRNED_PYTHON", "/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python")
import psutil
P = psutil.Process()
SEG = ["start"]; PEAK = {}; END = {}; ORDER = []; T0 = time.time(); TL = []
PAGES = []; EXTRA = {}


def rss():
    return P.memory_info().rss


def mark(seg):
    r = rss()
    END[SEG[0]] = r
    SEG[0] = seg
    if seg not in ORDER:
        ORDER.append(seg)
    PEAK[seg] = max(PEAK.get(seg, 0), r)
    TL.append((round(time.time() - T0, 1), seg, round(r / 1e9, 3)))


def sampler():
    while True:
        r = rss(); s = SEG[0]
        PEAK[s] = max(PEAK.get(s, 0), r)
        time.sleep(0.25)


threading.Thread(target=sampler, daemon=True).start()

import tools.omr.staged as pkg
assert pkg.__file__.startswith(a.wt), pkg.__file__
from tools.omr.staged import gather, adjudicate, groups, evaluate, infer, pipeline, record, record_io, export


def seg_wrap(mod, name, seg, after=None):
    f = getattr(mod, name)

    @functools.wraps(f)
    def w(*x, **k):
        prev = SEG[0]
        mark(seg)
        try:
            return f(*x, **k)
        finally:
            mark(after or (seg + ":done"))
    setattr(mod, name, w)


_seen_pws = []      # ids only: holding the page objects here would keep every page alive (the probe's own leak, found 11-01)
_ge = gather.gather_external


def ge(log, pws, *x, **k):
    if not _seen_pws or _seen_pws[-1] != id(pws):
        _seen_pws.append(id(pws))
        n = len(_seen_pws)
        PAGES.append({"page_n": n, "t": round(time.time() - T0, 1), "rss_gb": round(rss() / 1e9, 3), "live": live_mem(),
                      "rows": [len(log._obs), len(log._abs), len(log._vrd)]})
        mark(f"gather.page{n}")
        if a.mid and n == a.mid:
            EXTRA["holders_mid"] = mid_holders()
        if a.who and n == a.who:
            EXTRA["who"] = who_holds(pws)
        if a.trace and str(n) in a.trace.split(","):
            trace_snap(f"page{n}")
    return _ge(log, pws, *x, **k)


def _desc(o):
    import types
    if isinstance(o, types.FrameType):
        return f"frame:{o.f_code.co_name}@{o.f_code.co_filename.split('/tools/')[-1]}:{o.f_lineno}"
    if isinstance(o, dict):
        if "__name__" in o and "__builtins__" in o:
            return "module:" + str(o["__name__"])
        return "dict{" + ",".join(sorted(map(str, o.keys()))[:6]) + "}"
    if isinstance(o, (list, tuple)):
        return f"{type(o).__name__}[{len(o)}]"
    return type(o).__name__ + (":" + o.__qualname__ if hasattr(o, "__qualname__") else "")


def who_holds(cur_pws, depth=6):
    """Breadth-first referrer paths from each earlier page's PageImage up to a frame or a module (or `depth`)."""
    import types
    gc.collect()
    cur_page = getattr(cur_pws, "page", None)
    olds = [o for o in gc.get_objects() if type(o).__name__ == "PageImage" and o is not cur_page]
    out = []
    skip = {id(olds)}
    for o in olds[:3]:
        paths = []
        frontier = [(o, [type(o).__name__])]
        for _ in range(depth):
            nxt = []
            for obj, path in frontier:
                refs = [r for r in gc.get_referrers(obj) if id(r) not in skip and r is not frontier and r is not nxt
                        and not (isinstance(r, list) and r is olds)]
                for r in refs[:4]:
                    d = _desc(r)
                    if d.startswith("frame:") or d.startswith("module:"):
                        paths.append(" <- ".join(path + [d]))
                    else:
                        nxt.append((r, path + [d]))
            frontier = nxt[:12]
            if not frontier:
                break
        paths += [" <- ".join(pth) + " <- ..." for _o, pth in frontier[:6]]
        out.append(paths[:16])
    return {"old_page_images": len(olds), "paths": out}


SNAPS = {}


def trace_snap(name):
    import tracemalloc
    if not tracemalloc.is_tracing():
        return
    gc.collect()
    SNAPS[name] = tracemalloc.take_snapshot()
    cur, peak = tracemalloc.get_traced_memory()
    TRACE.setdefault("traced", {})[name] = {"current_gb": round(cur / 1e9, 3), "peak_gb": round(peak / 1e9, 3), "live": live_mem()}
    names = list(SNAPS)
    if len(names) >= 2:
        a0, a1 = SNAPS[names[-2]], SNAPS[names[-1]]
        st = a1.compare_to(a0, "traceback")
        TRACE[f"grew {names[-2]}->{names[-1]}"] = [
            {"mb": round(x.size_diff / 1e6, 1), "n": x.count_diff, "where": [f"{f.filename.split('/tools/')[-1]}:{f.lineno}" for f in x.traceback][:6]}
            for x in st[:25]]
        top = a1.statistics("traceback")
        TRACE[f"held at {names[-1]}"] = [
            {"mb": round(x.size / 1e6, 1), "n": x.count, "where": [f"{f.filename.split('/tools/')[-1]}:{f.lineno}" for f in x.traceback][:6]}
            for x in top[:25]]
        del SNAPS[names[-2]]


TRACE = {}


def mid_holders():
    """ndarrays alive at a page's start, grouped by a 5-level referrer chain (type / dict keys / module) -- who keeps them."""
    import numpy as np
    gc.collect()
    groups = {}; seen = set()
    for o in gc.get_objects():
        for r in gc.get_referents(o):
            if not isinstance(r, np.ndarray):
                continue
            b = r
            while isinstance(b.base, np.ndarray):
                b = b.base
            if id(b) in seen or b.nbytes < (1 << 16):
                continue
            seen.add(id(b))
            chain = []; cur = o
            for _ in range(5):
                d = type(cur).__name__
                if isinstance(cur, dict):
                    if "__name__" in cur and "__builtins__" in cur:
                        chain.append("module:" + str(cur["__name__"])); break
                    d += "{" + ",".join(sorted(map(str, cur.keys()))[:5]) + "}"
                elif hasattr(cur, "__qualname__"):
                    d += ":" + str(cur.__qualname__)
                chain.append(d)
                refs = [x for x in gc.get_referrers(cur) if type(x).__name__ != "frame" and x is not groups and x is not seen]
                if not refs:
                    break
                cur = refs[0]
            k = " <- ".join(chain)
            g = groups.setdefault(k, [0, 0]); g[0] += b.nbytes; g[1] += 1
    top = sorted(groups.items(), key=lambda kv: -kv[1][0])[:30]
    return {"live": live_mem(), "nd_gb": round(sum(v[0] for v in groups.values()) / 1e9, 3),
            "by_chain": [(k, round(v[0] / 1e9, 3), v[1]) for k, v in top]}


gather.gather_external = ge

# per-page seconds of every gather_* reader (the page is the one `ge` last marked)
RT = {}


def _rt_wrap(name):
    f = getattr(gather, name)

    @functools.wraps(f)
    def w(*x, **k):
        t = time.perf_counter()
        try:
            return f(*x, **k)
        finally:
            key = (len(_seen_pws), name)
            RT[key] = RT.get(key, 0.0) + time.perf_counter() - t
    setattr(gather, name, w)


for _n in [n for n in dir(gather) if n.startswith("gather_") and n != "gather_external" and callable(getattr(gather, n))]:
    _rt_wrap(_n)


def live_mem():
    """what is LIVE, as against RSS: libmalloc zone bytes in use, and pymalloc's own count (sys._debugmallocstats)."""
    import ctypes, io, contextlib, re, tempfile
    class MS(ctypes.Structure):
        _fields_ = [("blocks_in_use", ctypes.c_uint), ("size_in_use", ctypes.c_size_t),
                    ("max_size_in_use", ctypes.c_size_t), ("size_allocated", ctypes.c_size_t)]
    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    st = MS(); libc.malloc_zone_statistics(None, ctypes.byref(st))
    out = {"malloc_in_use_gb": round(st.size_in_use / 1e9, 3), "malloc_allocated_gb": round(st.size_allocated / 1e9, 3)}
    with tempfile.TemporaryFile("w+") as tf:
        fd = os.dup(2); os.dup2(tf.fileno(), 2)
        try:
            sys._debugmallocstats()
        finally:
            os.dup2(fd, 2); os.close(fd)
        tf.seek(0); txt = tf.read()
    m = re.search(r"# bytes in allocated blocks\s*=\s*([\d,]+)", txt)
    m2 = re.search(r"# arenas allocated current\s*=\s*([\d,]+)", txt)
    if m:
        out["pymalloc_live_gb"] = round(int(m.group(1).replace(",", "")) / 1e9, 3)
    if m2:
        out["pymalloc_arenas_gb"] = round(int(m2.group(1).replace(",", "")) * 256 * 1024 / 1e9, 3)
    out["rss_gb"] = round(rss() / 1e9, 3)
    return out


def nd_bytes_from(roots, maxdepth=6):
    import numpy as np
    seen = set(); bufs = {}
    stack = [(r, 0) for r in roots]
    while stack:
        o, d = stack.pop()
        if id(o) in seen:
            continue
        seen.add(id(o))
        if isinstance(o, np.ndarray):
            b = o
            while isinstance(b.base, np.ndarray):
                b = b.base
            bufs[id(b)] = b.nbytes
            continue
        if d >= maxdepth:
            continue
        if isinstance(o, dict):
            stack.extend((v, d + 1) for v in o.values())
        elif isinstance(o, (list, tuple, set, frozenset)):
            stack.extend((v, d + 1) for v in o)
        elif hasattr(o, "__dict__") and not isinstance(o, type):
            stack.extend((v, d + 1) for v in vars(o).values())
        elif hasattr(o, "__slots__"):
            for s in o.__slots__:
                if hasattr(o, s):
                    stack.append((getattr(o, s), d + 1))
    return sum(bufs.values())


def deep(o, seen, d=0):
    if id(o) in seen or d > 8:
        return 0
    seen.add(id(o))
    n = sys.getsizeof(o)
    if isinstance(o, dict):
        n += sum(deep(k, seen, d + 1) + deep(v, seen, d + 1) for k, v in o.items())
    elif isinstance(o, (list, tuple, set, frozenset)):
        n += sum(deep(v, seen, d + 1) for v in o)
    elif hasattr(o, "__dataclass_fields__"):
        n += sum(deep(getattr(o, f), seen, d + 1) for f in o.__dataclass_fields__)
    elif hasattr(o, "__dict__") and not isinstance(o, type):
        n += deep(vars(o), seen, d + 1)
    return n


def row_sizes(log, per_q=200):
    """deep bytes per (store, quantity), from a sample of up to `per_q` rows each, scaled to the count (strings counted per row,
    so an id shared by many rows is over-counted: an upper bound)."""
    import random
    out = {}
    for store in ("_obs", "_abs", "_vrd"):
        by_q = {}
        for r in getattr(log, store).values():
            by_q.setdefault(r.quantity, []).append(r)
        for q, rows in by_q.items():
            smp = rows if len(rows) <= per_q else random.Random(0).sample(rows, per_q)
            b = sum(deep(r, set()) for r in smp) / len(smp) * len(rows)
            out[f"{store[1:]}|{q}"] = (len(rows), round(b / 1e9, 3))
    return dict(sorted(out.items(), key=lambda kv: -kv[1][1])[:40])


def holders(prepared, log):
    import numpy as np
    out = {}
    lazy = hasattr(prepared, "page_indices")
    out["prepared_nd_gb"] = None if lazy else round(nd_bytes_from([prepared]) / 1e9, 3)
    per_page = []
    for pws, cells in ([] if lazy else prepared):
        per_page.append({"pws_gb": round(nd_bytes_from([vars(pws)], 3) / 1e9, 3),
                         "cells_gb": round(nd_bytes_from([cells], 4) / 1e9, 3),
                         "n_cells": len(cells),
                         "cell_attrs": sorted(set().union(*[set(vars(c)) for c in cells])) if cells else []})
    out["per_page"] = per_page
    gc.collect()
    by_type = {}; seen = set()
    for o in gc.get_objects():
        for r in gc.get_referents(o):
            if isinstance(r, np.ndarray):
                b = r
                while isinstance(b.base, np.ndarray):
                    b = b.base
                if id(b) in seen:
                    continue
                seen.add(id(b))
                t = type(o).__name__
                if b.nbytes < (2 << 20):
                    pass
                elif isinstance(o, dict):        # name the dict's owner: an instance's __dict__, a module's globals, or a container
                    owners = [type(x).__name__ + ("" if not hasattr(x, "__name__") else ":" + str(getattr(x, "__name__", ""))[:40])
                              for x in gc.get_referrers(o) if x is not by_type and x is not seen][:2]
                    t = "dict<-" + "|".join(owners)
                elif isinstance(o, (list, tuple)):
                    owners = [type(x).__name__ for x in gc.get_referrers(o)][:3]
                    t = type(o).__name__ + "<-" + "|".join(owners)
                by_type[t] = by_type.get(t, 0) + b.nbytes
    out["nd_by_holder_type_gb"] = {k: round(v / 1e9, 3) for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])[:25]}
    out["nd_total_gb"] = round(sum(by_type.values()) / 1e9, 3)
    # who keeps a MeasureCell / PageImage alive after GATHER: three referrer levels, by type and module name
    chains = []
    for o in gc.get_objects():
        tn = type(o).__name__
        if tn in ("MeasureCell", "PageImage") and len(chains) < 6:
            lvl = [o]; desc = [tn]
            for _ in range(4):
                refs = [r for r in gc.get_referrers(lvl[-1]) if r is not lvl and r is not chains and type(r).__name__ != "frame"]
                if not refs:
                    break
                r = refs[0]
                d = type(r).__name__
                if isinstance(r, dict) and "__name__" in r:
                    d = "module-globals:" + str(r["__name__"])
                elif hasattr(r, "__qualname__"):
                    d += ":" + r.__qualname__
                elif isinstance(r, dict):
                    d += "{" + ",".join(list(map(str, r.keys()))[:4]) + "}"
                desc.append(d); lvl.append(r)
            chains.append(" <- ".join(desc))
    out["cell_holders"] = chains
    out["row_gb_by_quantity"] = row_sizes(log)
    out["log_rows"] = [len(log._obs), len(log._abs), len(log._vrd)]
    out["log_caches"] = {s: len(getattr(log, s)) for s in ("_closure_cache", "_qic_cache", "_desc_result_cache", "_desc_index_cache", "_desc_prefix_cache", "_subjects_cache")}
    out["rss_gb"] = round(rss() / 1e9, 3)
    return out


_rso = pipeline.run_staged_on


def rso(prepared, *x, **k):
    mark("prepared")
    EXTRA["after_prepare_rss_gb"] = round(rss() / 1e9, 3)
    if a.holders:
        EXTRA["prepared_nd_gb_at_prepare"] = round(nd_bytes_from([prepared]) / 1e9, 3)
    _g = gather.gather

    def g(*gx, **gk):
        log = _g(*gx, **gk)
        mark("gather:done")
        EXTRA["after_gather_rss_gb"] = round(rss() / 1e9, 3)
        EXTRA["after_gather_live"] = live_mem()
        if a.trace:
            trace_snap("gather_end")
        if a.holders:
            EXTRA["holders_after_gather"] = holders(prepared, log)
        return log
    gather.gather = g
    return _rso(prepared, *x, **k)


pipeline.run_staged_on = rso
seg_wrap(pipeline, "prepare_pages", "prepare")
seg_wrap(adjudicate, "run", "adjudicate")
_adj = adjudicate.run


LOGREF = []


def adj(log, *x, **k):
    r = _adj(log, *x, **k)
    if a.teardown:
        LOGREF.append(log)
    if a.holders:
        EXTRA["row_gb_after_adjudicate"] = row_sizes(log)
    EXTRA["after_adjudicate_rss_gb"] = round(rss() / 1e9, 3)
    EXTRA["after_adjudicate_live"] = live_mem()
    cc = getattr(log, "_closure_cache", {}) or {}
    EXTRA["after_adjudicate_log"] = {
        "rows": [len(log._obs), len(log._abs), len(log._vrd)],
        "verdict_basis_entries": sum(len(v.basis) for v in log._vrd.values()),
        "verdict_considered_entries": sum(len(v.considered) for v in log._vrd.values()),
        "closure_cache_n": len(cc), "closure_cache_entries": sum(len(s) for s in cc.values()),
        "closure_cache_gb_est": round(sum(sys.getsizeof(s) for s in cc.values()) / 1e9, 3),
        "basis_tuples_gb_est": round(sum(sys.getsizeof(v.basis) for v in log._vrd.values()) / 1e9, 3),
        "qic_cache_n": len(getattr(log, "_qic_cache", {}) or {}),
    }
    return r


adjudicate.run = adj
seg_wrap(groups, "run", "groups")
seg_wrap(evaluate, "run", "evaluate")
seg_wrap(infer, "run", "infer")
seg_wrap(record.Log, "to_json", "to_json")
seg_wrap(record_io, "dumps_for_file", "dumps_for_file")
seg_wrap(export, "to_musicxml", "export")
if hasattr(record_io, "dump_to_file"):
    seg_wrap(record_io, "dump_to_file", "dump_to_file")
import pathlib
_wt = pathlib.Path.write_text


def wtxt(self, *x, **k):
    mark("write_text:" + self.name[-30:])
    r = _wt(self, *x, **k)
    mark("write_text:done")
    return r


pathlib.Path.write_text = wtxt
from tools.omr.staged import __main__ as m
os.makedirs(a.outdir, exist_ok=True)
out = f"{a.outdir}/{a.label}.record.json"
argv = [a.pdf, "--pages", a.pages, "--weights", "auto", "--through", a.through, "--out", out]
if a.through == "infer":
    argv += ["--musicxml", f"{a.outdir}/{a.label}.musicxml"]
if a.cache:
    argv += ["--detector-cache", a.cache]
if a.trace:
    import tracemalloc
    tracemalloc.start(6)
t0 = time.time()
rc = m.main(argv)
mark("end")
TEARDOWN = []
if a.teardown and LOGREF:
    lg = LOGREF[0]; LOGREF.clear()
    import gc as _gc
    _gc.collect(); r0 = rss()
    steps = [("closure_cache", lambda: lg._closure_cache.clear()), ("qic_cache", lambda: lg._qic_cache.clear()),
             ("desc_caches", lambda: (lg._desc_result_cache.clear(), lg._desc_index_cache.clear(), lg._desc_prefix_cache.clear(),
                                      lg._subjects_cache.clear())),
             ("verdict_basis", lambda: [object.__setattr__(v, "basis", ()) for v in lg._vrd.values()]),
             ("verdict_considered_used", lambda: [(object.__setattr__(v, "considered", ()), object.__setattr__(v, "used", ()),
                                                   object.__setattr__(v, "correlated", ())) for v in lg._vrd.values()]),
             ("verdicts", lambda: lg._vrd.clear()), ("by_subject", lambda: lg._by_subject.clear()),
             ("abstentions", lambda: lg._abs.clear()), ("observations", lambda: lg._obs.clear())]
    for name, f in steps:
        f(); _gc.collect(); r1 = rss()
        TEARDOWN.append({"dropped": name, "freed_gb": round((r0 - r1) / 1e9, 3), "rss_gb": round(r1 / 1e9, 3)}); r0 = r1
    del lg; _gc.collect()
    TEARDOWN.append({"dropped": "log", "rss_gb": round(rss() / 1e9, 3)})
import resource
RTP = {}
for (pg, name), v in RT.items():
    RTP.setdefault(name, {})[pg] = round(v, 1)
res = {"trace": TRACE, "teardown": TEARDOWN, "reader_s_by_page": dict(sorted(RTP.items(), key=lambda kv: -sum(kv[1].values()))), "label": a.label, "pages": a.pages, "rc": rc, "wall_s": round(time.time() - t0, 1),
       "out_bytes": os.path.getsize(out) if os.path.exists(out) else None,
       "maxrss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 3),
       "segments": [{"seg": s, "peak_gb": round(PEAK.get(s, 0) / 1e9, 3), "end_gb": round(END.get(s, 0) / 1e9, 3)} for s in ORDER],
       "pages_start": PAGES, **EXTRA, "timeline": TL}
json.dump(res, open(f"{a.outdir}/{a.label}.mem.json", "w"), indent=1)
print("MEM", a.label, "rc", rc, "wall", res["wall_s"], "maxrss", res["maxrss_gb"], "bytes", res["out_bytes"], flush=True)
