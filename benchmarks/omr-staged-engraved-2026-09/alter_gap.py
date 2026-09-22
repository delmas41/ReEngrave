"""WHY three printed E-flats came out E natural, on ink that is perfect.

`note_accuracy.py` finds exactly three wrong notes on the whole page and all
three are one fault: our `E4` where the score prints `E-4`, in the two violin
parts, in the two bars that hold the symphony's answering half note. The key is
C minor — three flats — so the alteration is the key signature's, and
`consequences.respell_accidental` is the rule that applies it.

This asks the record which link failed, rather than guessing:

    key signature read?  -> Q.KEY_SIGNATURE verdict per staff
    alteration applied?  -> Q.ACCIDENTAL verdict per glyph
    which glyph is it?   -> the note's own subject, via Q.PITCH

    python3 benchmarks/omr-staged-engraved-2026-09/alter_gap.py \
        --record out/engraved-p0.record.json

⚠️ EVERY FACT HERE IS READ OFF THE RECORD. Nothing is recomputed from the
raster, so this says what the pipeline DECIDED and not what it should have.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


def _v(rec, quantity: str) -> List[dict]:
    return [v for v in rec["verdicts"] if v.get("quantity") == quantity]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    rec = json.loads(args.record.read_text())["record"]

    ks = _v(rec, "key_signature")
    print(f"Q.KEY_SIGNATURE: {len(ks)} verdicts")
    print(f"   outcomes {dict(Counter(v['outcome'] for v in ks))}")
    print(f"   values   {dict(Counter(str(v.get('value')) for v in ks))}")
    print(f"   reasons  {dict(Counter(v.get('reason') for v in ks))}")
    per_staff = {v["subject"]: v for v in ks}
    for sub in sorted(per_staff):
        v = per_staff[sub]
        print(f"   {sub:18s} {v['outcome']:9s} {str(v.get('value')):>6s}  "
              f"{v.get('reason')}")

    acc = _v(rec, "accidental")
    print(f"\nQ.ACCIDENTAL: {len(acc)} verdicts  "
          f"{dict(Counter(v['outcome'] for v in acc))}  "
          f"{dict(Counter(v.get('reason') for v in acc))}")
    by_staff: Dict[str, List[str]] = defaultdict(list)
    for v in acc:
        p = v["subject"].split("/")
        by_staff["/".join(["staff", p[1], p[2], p[3]])].append(
            f"{v['subject'].split('/')[-1]}:{v.get('value')}")
    for k in sorted(by_staff):
        print(f"   {k:18s} {by_staff[k]}")

    pitch = _v(rec, "pitch")
    print(f"\nQ.PITCH: {len(pitch)} verdicts")
    got: Dict[str, List[str]] = defaultdict(list)
    for v in pitch:
        if v["outcome"] != "decided":
            continue
        p = v["subject"].split("/")
        got["/".join(["staff", p[1], p[2], p[3]])].append(str(v.get("value")))
    for k in sorted(got, key=lambda s: int(s.split("/")[-1])):
        print(f"   {k:18s} {got[k]}")

    print("\nQ.NOTEHEAD_STAFF_POSITION for the staves that disagree "
          "(13, 14 = Violin 1, Violin 2):")
    pos = [o for o in rec["observations"]
           if o.get("quantity") == "notehead_staff_position"]
    for o in pos:
        p = o["subject"].split("/")
        if p[3] in ("13", "14"):
            print(f"   {o['subject']:24s} pos {o.get('value')}  "
                  f"reader {o.get('reader')}")

    out = {
        "key_signature": {v["subject"]: {"outcome": v["outcome"],
                                         "value": v.get("value"),
                                         "reason": v.get("reason")}
                          for v in ks},
        "accidental": [{"subject": v["subject"], "value": v.get("value"),
                        "reason": v.get("reason")} for v in acc],
    }
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
