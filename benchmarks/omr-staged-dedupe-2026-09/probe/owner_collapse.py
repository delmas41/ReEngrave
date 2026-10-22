"""Do the two copies of a cross-staff duplicate agree on an OWNER — and then both get written?

⚠️ THE LEGACY RULE DELETES THE LOSER. THE STAGED PATH MOVES THE WINNER.
`_dedupe_cross_staff_detections` removes the losing detection from its cell's
list, so one piece of ink leaves one note. `adjudicate_glyph_owner` decides
whose the ink is and `export._place_notes` writes EVERY decided notehead into
the cell its OWNER names — so when both copies of one contest name the same
owner, both are written, onto the same staff, at the same pitch. That is not a
missing decision; it is a decision honoured in a way that doubles.

This probe asks the record whether that is what happens, by NAME.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from reach import duplicate_pairs  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args(argv)

    d = json.load(open(args.record))
    obs = d["record"]["observations"]
    _subjects, _family, pairs = duplicate_pairs(obs)

    owner, pitch = {}, {}
    dur = {}
    for v in d["record"]["verdicts"]:
        if v["quantity"] == "glyph_owner":
            owner[v["subject"]] = (v["value"], v["reason"], v["outcome"])
        elif v["quantity"] == "duration":
            dur[v["subject"]] = v["outcome"]
    for o in obs:
        if o["quantity"] == "pitch":
            pitch[o["subject"]] = o["value"]
    for c in d["record"].get("verdicts", []):
        if c["quantity"] == "pitch":
            pitch[c["subject"]] = c.get("value")

    cross = [p for p in pairs
             if p["scope"] == "same_system_other_staff"
             and p["family"] == "notehead_class"]
    print(f"cross-staff notehead duplicate pairs: {len(cross)}")

    agree = same = diff = neither = 0
    examples = []
    for p in cross:
        oa, ob = owner.get(p["a"]), owner.get(p["b"])
        if oa is None or ob is None:
            neither += 1
            continue
        agree += 1
        if oa[0] == ob[0]:
            same += 1
            if len(examples) < args.limit:
                examples.append((p, oa, ob))
        else:
            diff += 1

    print(f"  both copies carry a glyph_owner verdict : {agree}")
    print(f"    ... and they name the SAME owner staff: {same}")
    print(f"    ... they disagree                     : {diff}")
    print(f"  one or both carry no owner verdict      : {neither}")
    print("\n⚠️ Every 'SAME owner' pair is two decided noteheads that "
          "`_place_notes` writes into ONE staff's cell.")
    print("\nexamples (subject, owner named, reason):")
    for p, oa, ob in examples:
        print(f"  {p['a']}  -> {oa[0]}  ({oa[1]})  {p['class_a']}")
        print(f"  {p['b']}  -> {ob[0]}  ({ob[1]})  {p['class_b']}"
              f"   IoU={p['iou']}")
        print()

    reasons = collections.Counter(
        owner[p["a"]][1] for p in cross if p["a"] in owner)
    print("glyph_owner reason on the first copy of each cross-staff pair:")
    for k, v in reasons.most_common():
        print(f"  {k:<16} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
