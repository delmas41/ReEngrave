"""ROADMAP 2.305 r5 (MEASUREMENT): re-adjudicate a saved slice with both arc flags ON, export it, and for named cross-system pairs print what the join saw --
each half's note (pitch, voice, x), the part's run boundaries, and every note of the same voice AFTER the first note in its run / BEFORE the second in its own (the
adjacency test that makes a same-pitch join a slur). Also every edge half offered to that part.

    python3 cross_debug_2305.py SLICEDIR PLATE START STOP [START STOP ...]
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["OMR_PAGE_ARC_WRITE"] = "1"
os.environ["OMR_ARC_MEETING_AT_HEAD"] = "1"
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

slicedir, plate = sys.argv[1], sys.argv[2]
pairs = list(zip(sys.argv[3::2], sys.argv[4::2]))
rec = LR.load_slices(pathlib.Path(slicedir) / plate)
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
calls = []
orig = E._across_system_spans


def spy(rec_, part, measures, breaks, voice_of, edges, positions, taken, counters):
    out = orig(rec_, part, measures, breaks, voice_of, edges, positions, taken, counters)
    calls.append((measures, breaks, voice_of, edges, positions, out))
    return out


E._across_system_spans = spy
E.to_musicxml(result)
for a, b in pairs:
    print("=" * 10, a, "->", b)
    for measures, breaks, voice_of, edges, positions, out in calls:
        idx = {}
        for mi, m in enumerate(measures):
            for d in m["detections"] or ():
                if d.get("glyph") and d.get("category") == "notehead":
                    idx.setdefault(str(d["glyph"]), (mi, d))
        if a not in idx and b not in idx:
            continue
        starts = sorted(set(breaks))
        run_of = lambda m: sum(1 for s in starts if s <= m)  # noqa: E731
        print("  part: measures %d, run starts %s" % (len(measures), starts))
        mine = [c for c in edges if c["head"] in idx]
        for c in mine:
            print("   edge half", c["side"], c["head"], "curve", c["curve"], "run", run_of(idx[c["head"]][0]), "x_end", c["x_end"], "pos", positions.get(c["head"]))
        for k in (a, b):
            if k in idx:
                mi, d = idx[k]
                print("   note", k, "measure", mi, "run", run_of(mi), "pitch", d.get("pitch"), "voice", voice_of.get(id(d)), "x", E._head_x_centre(d))
        for kind_, spans_ in zip(("slur", "tie"), out):
            for sp_ in spans_:
                ks = (str(sp_[2].get("glyph")), str(sp_[3].get("glyph")))
                if a in ks or b in ks:
                    print("   JOIN WROTE", kind_, ks)
        if a in idx and b in idx:
            (ma, da), (mb, db) = idx[a], idx[b]
            v = voice_of.get(id(da), 0)
            ra, rb = run_of(ma), run_of(mb)
            fa = [m for m in range(len(measures)) if run_of(m) == ra]
            fb = [m for m in range(len(measures)) if run_of(m) == rb]
            xa, xz = E._head_x_centre(da), E._head_x_centre(db)
            after = [(d.get("glyph"), d.get("pitch"), m) for m in fa for d in (measures[m]["detections"] or ())
                     if d.get("category") == "notehead" and d is not da and voice_of.get(id(d), 0) == v and (E._head_x_centre(d) or -1e9) > xa + 1.0]
            before = [(d.get("glyph"), d.get("pitch"), m) for m in fb for d in (measures[m]["detections"] or ())
                      if d.get("category") == "notehead" and d is not db and voice_of.get(id(d), 0) == v and (E._head_x_centre(d) or 1e9) < xz - 1.0]
            print("   notes of voice %s AFTER the first in its run: %s" % (v, after[:6]))
            print("   notes of voice %s BEFORE the second in its run: %s" % (v, before[:6]))
