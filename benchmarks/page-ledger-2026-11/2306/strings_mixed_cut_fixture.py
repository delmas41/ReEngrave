"""2.306 strings-mixed: cut `tools/omr/tests/fixtures/strings_mixed_2_306.json` from replay inspect files (saved gathers re-adjudicated with
`OMR_STRING_STOPS_OWN_VALUE` ON; read-only inputs: the 2026-11-21 lr-r7-frozen gathers on this tree, and the 2.306 r16 page-stem gathers on
this lane merged with lane-2.306-twovoice for the two chords Sean named, whose heads only that reader joins to their stem).

Usage: strings_mixed_cut_fixture.py OUT.json NAME=INSPECT.json:CELL[:STEM] ... -- PLATE=INSPECT.json ...
Each chord: every head joined (decided `Q.HEAD_STEM`) to the stem: its OWN `Q.DURATION` (the ADJUDICATE verdict) as (base, levels, dots),
the head's own-ink fill (`head_ink`), the join's flush word, its box, and what the ON arm's `Q.STEM_VALUE` said (reason, status, value)."""
import json
import sys

from tools.omr.staged.adjudicators import stem_value as SV
from tools.omr.staged.record import Candidate, Outcome

TYPE = {4.0: "whole", 2.0: "half", 1.0: "quarter", 0.5: "eighth", 0.25: "16th"}
_cache = {}


def load(p):
    if p not in _cache:
        _cache[p] = json.load(open(p))["on"]
    return _cache[p]


class V:
    def __init__(self, v):
        self.outcome = Outcome(v["outcome"])
        self.value = v.get("value")
        self.candidates = [Candidate(value=c.get("value"), support=c.get("support") or 1.0) for c in v.get("candidates") or ()]


def chord(path, cell, stem=None):
    d = load(path)
    rows = d["cells"][cell]
    boxes = {o["subject"]: o for o in d["cell_boxes"][cell]}
    by = {}
    for v in rows:
        by.setdefault(v["subject"], {}).setdefault(v["quantity"], []).append(v)
    stems = {}
    for g, q in by.items():
        hs = [v for v in q.get("head_stem", ()) if v["outcome"] == "decided"]
        if hs:
            stems.setdefault(hs[-1]["value"], []).append(g)
    sid = stem or max(stems.items(), key=lambda kv: len(kv[1]))[0]
    heads = []
    for g in sorted(stems[sid], key=lambda k: int(k.split("/")[-1])):
        q = by[g]
        own = next(v for v in q["duration"] if v.get("decider") == "adjudicate_duration")
        opts = SV._options(V(own))
        hs = [v for v in q["head_stem"] if v["outcome"] == "decided"][-1]
        sv = (q.get("stem_value") or [{}])[-1]
        svd = sv.get("detail") or {}
        od = own.get("detail") or {}
        val = own["value"] if isinstance(own.get("value"), dict) else {}
        pitch = (q.get("pitch") or [{}])[-1].get("value")
        ev = (svd.get("own_values") or {}).get(g) or (list(opts[0]) if len(opts) == 1 else None)
        beats = SV._written(*ev) if ev else float(val.get("beats") or 0)
        base = ev[0] / (2 ** ev[1]) if ev else 1.0
        heads.append(dict(key=g, outcome=own["outcome"], options=[list(o) for o in opts], flush=(hs.get("detail") or {}).get("flush"),
                          box=list(boxes[g]["value"][1:5]), head_ink=od.get("head_ink"), head_ink_guess=od.get("head_ink_guess"),
                          whole_class=SV._stands_on_a_stem_so_not_whole(str(boxes[g]["value"][0])),
                          on_reason=sv.get("reason"), expect_status=(svd.get("status") or {}).get(g), expect_value=ev,
                          candidates=svd.get("candidates"),
                          det=dict(glyph=g, pitch=pitch if isinstance(pitch, str) else "C4", bbox=list(boxes[g]["detail"]["bbox_page_px"]),
                                   duration_beats=beats, duration_type=TYPE.get(base, "quarter"), dots=int(ev[2]) if ev else 0,
                                   stem_id=sid, stem_direction=None)))
    fam = d["families"]["staff/" + "/".join(cell.split("/")[:3])]
    return dict(cell=cell, stem=sid, family=fam["family"], family_source=fam["source"], heads=heads)


out = sys.argv[1]
args = sys.argv[2:]
cut = args.index("--")
fx = {"chords": {}, "staves": {}}
for spec in args[:cut]:
    name, rest = spec.split("=", 1)
    parts = rest.split(":")
    fx["chords"][name] = chord(parts[0], parts[1], ":".join(parts[2:]) or None)
for spec in args[cut + 1:]:
    plate, p = spec.split("=", 1)
    d = load(p)
    fx["staves"][plate] = {s: dict(instrument=r["instrument"] and {k: r["instrument"].get(k) for k in ("outcome", "value")},
                                   slot_index=r["slot_index"] and {k: r["slot_index"].get(k) for k in ("outcome", "value")},
                                   clef=r["clef"] and {k: r["clef"].get(k) for k in ("outcome", "value")},
                                   expect_family=d["families"][s]["family"]) for s, r in d["staff_rows"].items()}
json.dump(fx, open(out, "w"), indent=0, default=str)
for k, c in fx["chords"].items():
    print(k, c["family"], [(h["key"].split("/")[-1], h["options"], h["flush"], (h["head_ink"] or {}).get("value"), h["on_reason"], h["expect_status"])
                          for h in c["heads"]])
