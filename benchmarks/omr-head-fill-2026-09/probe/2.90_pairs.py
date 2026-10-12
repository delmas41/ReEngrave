"""2.90: every bar the exporter sees a divisi PAIR in (an up-stem and a down-stem
event at one onset), classified. EXPORT only, one record.

    python3 .../2.90_pairs.py RECORD.json [OUT.json]
"""
import json
import sys
from collections import Counter

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

res = load_record(sys.argv[1])
rows = []
real = E._voice_split


def spy(rec, run, ci, events, why=None):
    pairs = E._divisi_pairs(events)
    out = real(rec, run, ci, events, why)
    if pairs:
        chords = [e for e in events if e.get("kind") == "chord"]
        unknown = [e for e in chords if e.get("stem_direction") not in ("up", "down")]
        pair_val_agree = all(
            (u["duration_beats"], u["duration_type"], u["dots"]) == (d["duration_beats"], d["duration_type"], d["dots"])
            for u, d in pairs)
        rec_v = rec.verdict("voices", E.R_cell_key(run, ci)) if False else None
        rows.append({"page": run.page, "system": run.system, "staff": run.staff, "cell": ci,
                     "pairs": len(pairs), "chords": len(chords), "unknown_chords": len(unknown),
                     "pair_values_agree": pair_val_agree, "split": out is not None,
                     "why": list(why or [])})
    return out


E._voice_split = spy
xml, rep = E.to_musicxml(res)
c = Counter()
for r in rows:
    c[("unknown" if r["unknown_chords"] else "all_decided", "agree" if r["pair_values_agree"] else "disagree")] += 1
print(json.dumps({"bars_with_a_pair": len(rows), "by": {"%s/%s" % k: v for k, v in c.items()}}, indent=1))
if len(sys.argv) > 2:
    json.dump(rows, open(sys.argv[2], "w"), indent=1)
