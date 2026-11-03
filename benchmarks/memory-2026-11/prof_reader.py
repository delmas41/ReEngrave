"""cProfile ONE gather reader across a staged run (ROADMAP 2.249; measures, edits nothing under tools/).

usage: prof_reader.py WORKTREE OUT_PREFIX PDF PAGES READER [--cache DIR]

Runs the staged CLI of WORKTREE `--through gather` with `gather.<READER>` wrapped in a cProfile that is enabled only
inside the reader's calls; writes OUT_PREFIX.prof and OUT_PREFIX.txt (top 40 by cumulative and by own time, per page
seconds).
"""
import sys, os, time, argparse, cProfile, pstats, io, functools

ap = argparse.ArgumentParser()
ap.add_argument("wt"); ap.add_argument("out"); ap.add_argument("pdf"); ap.add_argument("pages"); ap.add_argument("reader")
ap.add_argument("--cache", default=None)
a = ap.parse_args()
os.chdir(a.wt); sys.path.insert(0, a.wt)
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
import tools.omr.staged as pkg
assert pkg.__file__.startswith(a.wt), pkg.__file__
from tools.omr.staged import gather
PR = cProfile.Profile(); SECS = []
_f = getattr(gather, a.reader)


@functools.wraps(_f)
def w(*x, **k):
    t = time.perf_counter(); PR.enable()
    try:
        return _f(*x, **k)
    finally:
        PR.disable(); SECS.append(round(time.perf_counter() - t, 1))


setattr(gather, a.reader, w)
from tools.omr.staged import __main__ as m
argv = [a.pdf, "--pages", a.pages, "--weights", "auto", "--through", "gather", "--out", a.out + ".record.json"]
if a.cache:
    argv += ["--detector-cache", a.cache]
rc = m.main(argv)
PR.dump_stats(a.out + ".prof")
s = io.StringIO()
st = pstats.Stats(PR, stream=s)
s.write(f"rc {rc} reader {a.reader} seconds per call {SECS}\n")
st.sort_stats("cumulative").print_stats(40)
st.sort_stats("tottime").print_stats(25)
open(a.out + ".txt", "w").write(s.getvalue())
print("PROF done", SECS, flush=True)
