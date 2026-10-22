"""What the marks did, and the contradictions they leave — no truth file.

⚠️ THE CONTRADICTION COLUMN IS THE FALSE-POSITIVE PROBE, and it needs nothing
external: **a note under a beam carries no flag.** An engraver draws one or the
other, so a notehead that both has a beam level READ over it AND a flag
attached to its stem is a contradiction — one of the two readings is wrong. It
does not say WHICH, so it is a rate to compare between arms and between
printings, never a count of errors.

    python3 .../mark_census.py <staged.json> [more.json ...]
"""
import json
import sys
from collections import Counter


def one(path):
    rec = json.load(open(path))["record"]
    d = [v for v in rec["verdicts"] if v["quantity"] == "duration"]
    det = [(v.get("detail") or {}) for v in d]
    o = rec["observations"]
    avail = Counter(x["quantity"] for x in o)
    heads = [x for x in det if x.get("head")]
    contradiction = sum(1 for x in heads
                        if (x.get("flags_attached") or 0)
                        and (x.get("levels_certain") or 0))
    beamed = sum(1 for x in heads if (x.get("levels_certain") or 0))
    flagged = sum(1 for x in heads if (x.get("flags_attached") or 0))
    print(f"{path}")
    print(f"   duration verdicts   {dict(Counter(v['outcome'] for v in d))}")
    print(f"   beam_evidence       {dict(Counter(x.get('beam_evidence') for x in det))}")
    print(f"   rows available      flag {avail['flag']}  aug_dot {avail['aug_dot']}"
          f"  stem {avail['stem']}  beam_stroke {avail['beam_stroke']}"
          f"  cell_staff_space {avail['cell_staff_space']}")
    print(f"   attached            stems {sum(x.get('stems_attached') or 0 for x in det)}"
          f"  beams-by-stem {sum(x.get('beams_by_stem') or 0 for x in det)}"
          f"  flags {sum(x.get('flags_attached') or 0 for x in det)}"
          f"  dots {sum(x.get('dots_attached') or 0 for x in det)}")
    print(f"   noteheads           {len(heads)}   with a beam level {beamed}"
          f"   with a flag {flagged}")
    rate = contradiction / flagged if flagged else 0.0
    print(f"   ⚠️ CONTRADICTIONS   {contradiction}  "
          f"({rate:.1%} of flagged notes also carry a beam level)")


for p in sys.argv[1:]:
    one(p)
