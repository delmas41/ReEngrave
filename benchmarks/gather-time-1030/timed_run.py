"""Outside-the-code stage timer (lane gather-time-1030; diagnosis only).

usage: timed_run.py WORKTREE OUTDIR LABEL PAGES [prof]

Runs the staged CLI of the tree at WORKTREE on Brahms pages PAGES (through
infer) with wall-clock wrappers monkeypatched onto the stage entry points and
every gather_* function. Edits nothing under tools/.
"""
import sys, os, time, json, functools, cProfile, pathlib

wt, outdir, label, pages = sys.argv[1:5]
prof = len(sys.argv) > 5 and sys.argv[5] == "prof"
os.chdir(wt); sys.path.insert(0, wt)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
os.environ.setdefault("OMR_DIRECTION_TEXT_SCAN_GATE", "1")
os.environ.setdefault("OMRNED_PYTHON", "/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python")
T = {}; N = {}; L = {}


def wrap(mod, name, key=None):
    f = getattr(mod, name)
    key = key or f"{mod.__name__.split('.')[-1]}.{name}"

    @functools.wraps(f)
    def w(*a, **k):
        t = time.perf_counter()
        try:
            return f(*a, **k)
        finally:
            T[key] = T.get(key, 0) + time.perf_counter() - t
            N[key] = N.get(key, 0) + 1
            L.setdefault(key, []).append(round(time.perf_counter() - t, 2))
    setattr(mod, name, w)


import tools.omr.staged as pkg
assert pkg.__file__.startswith(wt), pkg.__file__
from tools.omr.staged import gather, adjudicate, groups, evaluate, infer, pipeline, record, record_io
for n in [n for n in dir(gather) if n.startswith("gather_") and callable(getattr(gather, n))]:
    wrap(gather, n)
wrap(gather, "gather", "STAGE gather"); wrap(adjudicate, "run", "STAGE adjudicate"); wrap(groups, "run", "STAGE groups")
wrap(evaluate, "run", "STAGE evaluate"); wrap(evaluate, "run_over", "STAGE evaluate_bounded"); wrap(infer, "run", "STAGE infer")
wrap(record.Log, "to_json", "to_json(log)"); wrap(record_io, "dumps_for_file", "STAGE dumps_for_file")
_a1 = adjudicate.adjudicate_one
def _a1w(log, spec, subject):
    t = time.perf_counter()
    try: return _a1(log, spec, subject)
    finally:
        k = "ADJ " + str(spec.quantity); T[k] = T.get(k, 0) + time.perf_counter() - t; N[k] = N.get(k, 0) + 1
adjudicate.adjudicate_one = _a1w
_sf = adjudicate.subjects_for
def _sfw(log, spec):
    t = time.perf_counter()
    try: return _sf(log, spec)
    finally:
        k = "SUBJ " + str(spec.quantity); T[k] = T.get(k, 0) + time.perf_counter() - t; N[k] = N.get(k, 0) + 1
adjudicate.subjects_for = _sfw
wrap(pipeline, "_adjudication_report", "_adjudication_report")
_wt = pathlib.Path.write_text


def wtxt(self, *a, **k):
    t = time.perf_counter(); r = _wt(self, *a, **k)
    T["STAGE write_text"] = T.get("STAGE write_text", 0) + time.perf_counter() - t
    return r


pathlib.Path.write_text = wtxt
from tools.omr.staged import __main__ as m
pdf = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
os.makedirs(outdir, exist_ok=True)
out = f"{outdir}/{label}.record.json"
argv = [pdf, "--pages", pages, "--weights", "auto", "--through", "infer", "--out", out,
        "--detector-cache", "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/detector-cache-gt1030"]
t0 = time.perf_counter(); pr = cProfile.Profile() if prof else None
if pr:
    pr.enable()
rc = m.main(argv)
if pr:
    pr.disable()
tot = time.perf_counter() - t0
res = {"label": label, "pages": pages, "rc": rc, "total_s": tot, "timers": T, "calls": N, "per_call_s": {k: v for k, v in L.items() if k.startswith("STAGE") or k.startswith("gather.")},
       "out_bytes": os.path.getsize(out) if os.path.exists(out) else None,
       "maxrss_mb": __import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss / 1e6}
json.dump(res, open(f"{outdir}/{label}.timers.json", "w"), indent=1)
if pr:
    pr.dump_stats(f"{outdir}/{label}.prof")
print("TOTAL", round(tot, 1), {k: round(v, 1) for k, v in T.items() if k.startswith("STAGE") or k.startswith("to_json")})
