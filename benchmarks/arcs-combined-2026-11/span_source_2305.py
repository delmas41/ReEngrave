"""ROADMAP 2.305 r5 (MEASUREMENT): which export path writes the arc span on named heads -- re-adjudicates a saved slice with both arc flags ON,
spies every span producer in `_pair_arcs` and prints each span that touches a named head, with its producer and the drop counters.

    python3 span_source_2305.py SLICEDIR PLATE HEAD [HEAD ...]
"""
import collections
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_PAGE_ARC_WRITE", "1")
os.environ.setdefault("OMR_ARC_MEETING_AT_HEAD", "1")
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

slicedir, plate = sys.argv[1], sys.argv[2]
heads = set(sys.argv[3:])
rec = LR.load_slices(pathlib.Path(slicedir) / plate)
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}


def show(name, spans):
    for s in spans or ():
        try:
            ks = (str(s[2].get("glyph")), str(s[3].get("glyph")))
        except Exception:  # noqa: BLE001
            continue
        if heads & set(ks):
            print("  %-28s %s -> %s" % (name, ks[0], ks[1]))


def wrap(mod, fname, label, pick=lambda out: out):
    orig = getattr(mod, fname)

    def f(*a, **k):
        out = orig(*a, **k)
        try:
            for nm, sp in pick(out):
                show(label + nm, sp)
        except Exception as e:  # noqa: BLE001
            print("  spy failed", label, e)
        return out
    setattr(mod, fname, f)


wrap(E, "_across_system_spans", "join:", lambda o: (("slur", o[0]), ("tie", o[1])))
wrap(E, "_page_bound_slur_spans", "2.223 page-bound slur", lambda o: (("", o),))
wrap(E, "_anchored_slur_spans", "anchored slur", lambda o: (("", o),))
wrap(E, "_record_tie_spans", "record tie", lambda o: (("", o),))
wrap(E, "_drop_unison_same_pitch_slurs", "slurs after drop", lambda o: (("", o),))
wrap(E._legacy, "_paired_spans", "legacy paired", lambda o: (("", o),))
counters = collections.Counter()
E.to_musicxml(result)
print("done")
