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


_seen_pws = []
_ge = gather.gather_external


def ge(log, pws, *x, **k):
    if not _seen_pws or _seen_pws[-1] is not pws:
        _seen_pws.append(pws)
        n = len(_seen_pws)
        PAGES.append({"page_n": n, "t": round(time.time() - T0, 1), "rss_gb": round(rss() / 1e9, 3),
                      "rows": [len(log._obs), len(log._abs), len(log._vrd)]})
        mark(f"gather.page{n}")
    return _ge(log, pws, *x, **k)


gather.gather_external = ge


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


def holders(prepared, log):
    import numpy as np
    out = {}
    out["prepared_nd_gb"] = round(nd_bytes_from([prepared]) / 1e9, 3)
    per_page = []
    for pws, cells in prepared:
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
                by_type[t] = by_type.get(t, 0) + b.nbytes
    out["nd_by_holder_type_gb"] = {k: round(v / 1e9, 3) for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])[:25]}
    out["nd_total_gb"] = round(sum(by_type.values()) / 1e9, 3)
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
        if a.holders:
            EXTRA["holders_after_gather"] = holders(prepared, log)
        return log
    gather.gather = g
    return _rso(prepared, *x, **k)


pipeline.run_staged_on = rso
seg_wrap(pipeline, "prepare_pages", "prepare")
seg_wrap(adjudicate, "run", "adjudicate")
_adj = adjudicate.run


def adj(log, *x, **k):
    r = _adj(log, *x, **k)
    EXTRA["after_adjudicate_rss_gb"] = round(rss() / 1e9, 3)
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
argv = [a.pdf, "--pages", a.pages, "--weights", "auto", "--through", "infer", "--out", out,
        "--musicxml", f"{a.outdir}/{a.label}.musicxml"]
if a.cache:
    argv += ["--detector-cache", a.cache]
t0 = time.time()
rc = m.main(argv)
mark("end")
import resource
res = {"label": a.label, "pages": a.pages, "rc": rc, "wall_s": round(time.time() - t0, 1),
       "out_bytes": os.path.getsize(out) if os.path.exists(out) else None,
       "maxrss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 3),
       "segments": [{"seg": s, "peak_gb": round(PEAK.get(s, 0) / 1e9, 3), "end_gb": round(END.get(s, 0) / 1e9, 3)} for s in ORDER],
       "pages_start": PAGES, **EXTRA, "timeline": TL}
json.dump(res, open(f"{a.outdir}/{a.label}.mem.json", "w"), indent=1)
print("MEM", a.label, "rc", rc, "wall", res["wall_s"], "maxrss", res["maxrss_gb"], "bytes", res["out_bytes"], flush=True)
