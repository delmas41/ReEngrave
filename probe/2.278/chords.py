"""2.278: the chord_value_undecided groups: per group, each head's value, its stem, voice; do the heads share ONE stem?
usage: python3 probe/2.278/chords.py RECORD OUT.jsonl [slim]"""
import sys, json, collections, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT
from tools.omr.staged.record_io import load_record, expand_result
from tools.omr.staged.record import Q
from tools.omr.voicing import group_chords_in_measure  # may differ; fixed below if import fails

GROUPS = []
orig_c = EXPORT._chords_whose_value_would_be_voted
def wrap(runs):
    for run in runs.values():
        for ck, cell in run.cells.items():
            if not cell.detections:
                continue
            for ev in group_chords_in_measure(cell.detections):
                heads = ev.get("noteheads") or ()
                if len(heads) < 2:
                    continue
                vals = {(h.get("duration_beats"), h.get("duration_type"), h.get("dots")) for h in heads}
                if len(vals) > 1:
                    GROUPS.append({"cell": str(ck), "heads": [{k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v)[:80])
                                                               for k, v in h.items()} for h in heads]})
    return orig_c(runs)
EXPORT._chords_whose_value_would_be_voted = wrap

path, out = sys.argv[1], sys.argv[2]
if len(sys.argv) > 3 and sys.argv[3] == "slim":
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None); o.pop("correlated", None)
        return o
    d = expand_result(json.loads(Path(path).read_text(), object_hook=_hook))
else:
    d = load_record(path)
EXPORT.to_musicxml(d)
json.dump(GROUPS, open(out, "w"), default=str)
print(len(GROUPS), "groups;", sum(len(g["heads"]) for g in GROUPS), "heads")
print(sorted(GROUPS[0]["heads"][0].keys()) if GROUPS else None)
