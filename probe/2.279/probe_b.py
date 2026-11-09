"""2.279 probe B: the chords EXPORT refuses (`_chords_whose_value_would_be_voted`), group by group: how do the disagreeing
heads split by DECIDED stem? READ-ONLY (wraps the guard, changes nothing).

usage: python3 probe/2.279/probe_b.py RECORD OUT.json [slim]
"""
import collections
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT          # noqa: E402
from tools.omr.staged.record_io import load_record, expand_result  # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402

rec_path, out_path = sys.argv[1], sys.argv[2]
t = time.time()
if len(sys.argv) > 3 and sys.argv[3] == "slim":
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None)
            o.pop("correlated", None)
        return o
    d = expand_result(json.loads(Path(rec_path).read_text(), object_hook=_hook))
else:
    d = load_record(rec_path)
print("loaded", round(time.time() - t), flush=True)
GROUPS = []
orig_guard = EXPORT._chords_whose_value_would_be_voted
orig_group = EXPORT.group_chords_in_measure


def guard(runs):
    for run in runs.values():
        for ck, cell in run.cells.items():
            for ev in orig_group(cell.detections):
                heads = ev.get("noteheads") or ()
                if len(heads) < 2:
                    continue
                vals = {(h.get("duration_beats"), h.get("duration_type"), h.get("dots")) for h in heads}
                if len(vals) > 1:
                    GROUPS.append({"cell": [run.page, run.system, run.staff, ck],
                                   "heads": [{"glyph": h.get("glyph"), "beats": h.get("duration_beats"),
                                              "type": h.get("duration_type"), "dots": h.get("dots"),
                                              "stem": h.get("stem_id"), "dir": h.get("stem_direction"),
                                              "pitch": h.get("pitch") or h.get("step"),
                                              "keys": sorted(k for k in h.keys())[:0]} for h in heads]})
    return orig_guard(runs)


EXPORT._chords_whose_value_would_be_voted = guard
xml, report = EXPORT.to_musicxml(d)
print("exported", round(time.time() - t), flush=True)
cls = collections.Counter()
for g in GROUPS:
    hs = g["heads"]
    by_stem = collections.defaultdict(set)
    for h in hs:
        by_stem[h["stem"] or ("none:" + str(h["glyph"]))].add((h["beats"], h["type"], h["dots"]))
    n_stems = len({h["stem"] for h in hs if h["stem"]})
    nostem = sum(1 for h in hs if not h["stem"])
    uniform_within = all(len(v) == 1 for v in by_stem.values())
    if uniform_within and n_stems >= 2 and nostem == 0:
        k = "distinct_stems_each_uniform"
    elif uniform_within:
        k = "each_head_or_stem_uniform_but_some_without_stem"
    else:
        k = "values_disagree_within_one_stem"
    g["class"] = k
    cls[k] += 1
    g["n_heads"] = len(hs)
print(dict(cls), "groups", len(GROUPS), "heads", sum(g["n_heads"] for g in GROUPS))
c2 = collections.Counter()
for g in GROUPS:
    c2[g["class"]] += g["n_heads"]
print("heads by class", dict(c2))
json.dump(GROUPS, open(out_path, "w"), indent=0, default=str)
