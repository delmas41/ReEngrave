"""Replay a saved record's GATHER rows through ADJUDICATE..EXPORT in the tree at WORKTREE, metered (ROADMAP 2.249).

usage: replay.py WORKTREE RECORD OUT_PREFIX

The deterministic half of the pipeline (no OCR, no detector): the identity control for a change below GATHER, and its
cost. Writes OUT_PREFIX.record.json (the replayed record, `record_io.dump_to_file`), OUT_PREFIX.musicxml, and
OUT_PREFIX.meter.json: per-stage seconds, RSS and live memory (libmalloc in use + pymalloc) after each stage.
Two trees replayed on one record must write byte-identical records and MusicXML when the change reads nothing.
"""
import sys, os, time, json, gc, ctypes, functools

wt, rec_path, out = sys.argv[1:4]
os.chdir(wt); sys.path.insert(0, wt)
import psutil
P = psutil.Process()


class MS(ctypes.Structure):
    _fields_ = [("blocks_in_use", ctypes.c_uint), ("size_in_use", ctypes.c_size_t),
                ("max_size_in_use", ctypes.c_size_t), ("size_allocated", ctypes.c_size_t)]


def live():
    st = MS(); ctypes.CDLL("/usr/lib/libSystem.B.dylib").malloc_zone_statistics(None, ctypes.byref(st))
    return {"rss_gb": round(P.memory_info().rss / 1e9, 3), "malloc_in_use_gb": round(st.size_in_use / 1e9, 3)}


import tools.omr.staged as pkg
assert pkg.__file__.startswith(wt), pkg.__file__
from tools.omr.staged import adjudicate, groups, evaluate, infer, record, export, record_io
from tools.omr.staged.review import rerun as RR
M = {"stages": []}


def meter(mod, name, label):
    f = getattr(mod, name)

    @functools.wraps(f)
    def w(*x, **k):
        t = time.time(); g0 = GCT["s"]; c0 = dict(CL)
        prof = None
        if label in os.environ.get("REPLAY_PROFILE", "").split(","):     # cProfile one stage (a measurement)
            import cProfile
            prof = cProfile.Profile(); prof.enable()
        try:
            return f(*x, **k)
        finally:
            if prof is not None:
                import pstats, io
                prof.disable()
                sio = io.StringIO()
                pstats.Stats(prof, stream=sio).sort_stats("cumulative").print_stats(45)
                open(out + f".{label}.prof.txt", "w").write(sio.getvalue())
            M["stages"].append({"stage": label, "s": round(time.time() - t, 1), "gc_s": round(GCT["s"] - g0, 1),
                                "closure_calls": CL["calls"] - c0["calls"], "closure_s": round(CL["s"] - c0["s"], 1),
                                "closure_ids_m": round((CL["ids"] - c0["ids"]) / 1e6, 1), **live()})
    setattr(mod, name, w)


for mod, name, label in ((adjudicate, "run", "adjudicate"), (groups, "run", "groups"), (evaluate, "run", "evaluate"),
                         (infer, "run", "infer"), (evaluate, "run_over", "evaluate_bounded")):
    meter(mod, name, label)
if os.environ.get("REPLAY_CLOSURE_CAP") and hasattr(record, "CLOSURE_MEMO_MAX_IDS"):
    # a smaller closure-memo bound on a few pages stands in for the whole movement's pressure (a measurement knob)
    record.CLOSURE_MEMO_MAX_IDS = int(os.environ["REPLAY_CLOSURE_CAP"])
CL = {"calls": 0, "s": 0.0, "ids": 0}
_closure = record.Log.closure


def _closure_metered(self, row_id):      # calls / seconds / ids returned by Log.closure (a measurement; same answer)
    t = time.perf_counter()
    r = _closure(self, row_id)
    CL["calls"] += 1; CL["s"] += time.perf_counter() - t; CL["ids"] += len(r)
    return r


record.Log.closure = _closure_metered
M["closure"] = CL
GCT = {"s": 0.0, "n": [0, 0, 0], "gen2_s": 0.0}
_gcs = [0.0]


def _gc_cb(phase, info):     # seconds the cyclic collector runs, per generation (a measurement; changes nothing)
    if phase == "start":
        _gcs[0] = time.perf_counter()
    else:
        d = time.perf_counter() - _gcs[0]
        GCT["s"] += d; GCT["n"][info["generation"]] += 1
        if info["generation"] == 2:
            GCT["gen2_s"] += d


gc.callbacks.append(_gc_cb)
M["gc"] = GCT
t0 = time.time()
rec = record_io.load_record(rec_path)
rec = rec.get("record", rec)
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
del rec; gc.collect()
M["loaded"] = {"s": round(time.time() - t0, 1), **live()}
RR.run_stages(log)
t = time.time()
try:      # the CLI's form (ROADMAP 2.249 m5): ADJUDICATE bases unspelled; an older tree spells them
    result = {"record": log.to_json(lazy_basis=True), "summary": log.summary()}
except TypeError:
    result = {"record": log.to_json(), "summary": log.summary()}
M["to_json"] = {"s": round(time.time() - t, 1), **live()}
del log; gc.collect()
t = time.time()
n = record_io.dump_to_file(result, out + ".record.json")
M["dump"] = {"s": round(time.time() - t, 1), "bytes": n, **live()}
t = time.time()
xml, _report = export.to_musicxml(result)
open(out + ".musicxml", "w").write(xml)
M["export"] = {"s": round(time.time() - t, 1), **live()}
import resource
M["maxrss_gb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 3)
M["wall_s"] = round(time.time() - t0, 1)
json.dump(M, open(out + ".meter.json", "w"), indent=1)
print("REPLAY", out, json.dumps({k: M[k] for k in ("wall_s", "maxrss_gb")}), [(s["stage"], s["s"], s["malloc_in_use_gb"]) for s in M["stages"]], flush=True)
