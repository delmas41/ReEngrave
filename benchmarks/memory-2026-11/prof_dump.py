"""cProfile `record_io.dump_to_file` on a loaded record (ROADMAP 2.249; reads only, writes OUT).

usage: prof_dump.py WORKTREE RECORD OUT
"""
import sys, os, time, cProfile, pstats, io
wt, rec, out = sys.argv[1:4]
os.chdir(wt); sys.path.insert(0, wt)
from tools.omr.staged import record_io
res = record_io.load_record(rec)
if "record" not in res:
    res = {"record": res}
pr = cProfile.Profile(); t = time.time(); pr.enable()
n = record_io.dump_to_file(res, out)
pr.disable()
print("dump", n, "bytes", round(time.time() - t, 1), "s")
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(25); print(s.getvalue()[:6000])
