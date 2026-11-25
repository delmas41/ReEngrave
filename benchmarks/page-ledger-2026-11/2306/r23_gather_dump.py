"""Run one staged gather with `page_stems.read`'s exact inputs pickled per page (for real-row fixtures).
Usage (from the worktree): python3 gather_dump.py DUMPDIR -- <tools.omr.staged args>"""
import os, pickle, runpy, sys

dump = sys.argv[1]
args = sys.argv[sys.argv.index("--") + 1:]
os.makedirs(dump, exist_ok=True)
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS  # noqa: E402

_read = PS.read


def read(heads, verticals, held=None, crossers=None, strokes=None):
    page = None
    for h in heads:
        for m in h.get("members") or ():
            page = int(str(m).split("/")[1])
            break
        if page is not None:
            break
    D = dict(page=page, heads=[dict(h) for h in heads], verticals=[dict(v) for v in verticals], held=dict(held or {}),
             crossers=[dict(c) for c in (crossers or ())], strokes={int(o): dict(s) for o, s in (strokes or {}).items()})
    pickle.dump(D, open(os.path.join(dump, "p%s.pkl" % page), "wb"))
    return _read(heads, verticals, held, crossers=crossers, strokes=strokes)


PS.read = read
sys.argv = ["tools.omr.staged"] + args
runpy.run_module("tools.omr.staged", run_name="__main__", alter_sys=True)
