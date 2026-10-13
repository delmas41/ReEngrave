"""2.90 REACH: of the chords 2.89 refuses (heads that disagree on value), how many
are two voices by DECIDED stems? Reads the same record twice, EXPORT only.

    python3 .../2.90_reach.py RECORD.json [OUT.json]

Classes of a 2.89-refused chord (its heads' decided `Q.STEM_DIRECTION` / `Q.HEAD_STEM`):
  opposite_directions   both an up and a down head -> the guard now splits it
  distinct_decided_stems no opposite pair, but >=2 different decided stem ids
  one_stem_or_unknown   everything else (stays refused)
"""
import json
import sys
from collections import Counter

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

res = load_record(sys.argv[1])
captured = []
orig = E._chords_whose_value_would_be_voted
real_facts = E._stem_facts_of


def spy(runs):
    # group in the BASE way (no facts), remember each chord's heads
    out = []
    from tools.omr.voicing import group_chords_in_measure
    for run in runs.values():
        for ci, cell in run.cells.items():
            for ev in group_chords_in_measure(cell.detections):
                heads = ev.get("noteheads") or ()
                if len(heads) < 2:
                    continue
                if len({(h.get("duration_beats"), h.get("duration_type"), h.get("dots")) for h in heads}) > 1:
                    captured.append((run.page, run.system, run.staff, ci, [dict(h) for h in heads]))
    return orig(runs)


E._chords_whose_value_would_be_voted = spy
# base grouping: facts off, so what is captured is exactly 2.89's refused set
E._stem_facts_of = lambda rec, sub: {"stem_direction": None, "stem_id": None}
xml, rep = E.to_musicxml(res)
E._stem_facts_of = real_facts
E._chords_whose_value_would_be_voted = orig

rec = res["record"] if isinstance(res, dict) and "record" in res else res
from tools.omr.staged.record import Q  # noqa: E402
import tools.omr.staged.export as _e  # noqa: E402
# facts need the exporter's own Record wrapper
from tools.omr.staged.export import Record  # noqa: E402
r = Record(res) if not hasattr(res, "verdict") else res

cls = Counter()
rows = []
for page, system, staff, ci, heads in captured:
    facts = [real_facts(r, h["glyph"]) for h in heads]
    dirs = {f["stem_direction"] for f in facts if f["stem_direction"]}
    stems = {f["stem_id"] for f in facts if f["stem_id"]}
    if {"up", "down"} <= dirs:
        c = "opposite_directions"
    elif len(stems) >= 2:
        c = "distinct_decided_stems"
    else:
        c = "one_stem_or_unknown"
    cls[c] += 1
    rows.append({"page": page, "system": system, "staff": staff, "cell": ci, "class": c,
                 "dirs": sorted(dirs), "stems": sorted(stems), "n_heads": len(heads),
                 "heads": [{"glyph": h["glyph"], "pitch": h.get("pitch"), "beats": h["duration_beats"],
                            "type": h["duration_type"], "dots": h["dots"], "bbox_page": h.get("bbox_page"),
                            "dir": f["stem_direction"], "stem": f["stem_id"]}
                           for h, f in zip(heads, facts)]})
print(json.dumps({"refused_chords": len(captured), "classes": dict(cls)}, indent=1))
if len(sys.argv) > 2:
    json.dump(rows, open(sys.argv[2], "w"), default=str, indent=1)
