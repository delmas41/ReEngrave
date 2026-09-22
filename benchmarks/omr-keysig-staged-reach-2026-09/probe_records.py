"""What the staged path can and cannot say about a key signature — asked of
the committed records with NO pipeline code at all.

Three questions, and the first two are the finding:

1. **Can a mid-staff key change exist here?** Every `key_signature` verdict's
   SCOPE, and every `keysig_marker` row's FRAME. If all of them are staff and
   `cell:0`, the third `checked_by` statement — *"a key CHANGE is printed on
   every staff at the same bar (key_signature_corroboration — CONSUMED,
   default-ON)"* — has no domain, and wiring the import would produce a pass
   over an empty set.

2. **What is out of reach?** Key-accidental detections standing in cells other
   than cell 0. The detector fires on them; GATHER never looks. That count is
   what a mid-staff key reader would be worth, and it belongs in front of
   anyone who proposes building one.

3. **What would the unread markers have said?** `Q.KEYSIG_MARKER` is declared
   in `wants` AND `composed_from` and was read by nothing. ⚠️ The answer is
   NOT a proposed value: on the staves this path DECIDES, the marker count
   agrees with the settled `|fifths|` about half the time. It is evidence that
   INK WAS THERE, which is what separates *nothing was printed* from *we could
   not fit what was printed*.

⚠️ NO PIPELINE CODE. This reads the record's JSON and re-derives everything by
hand, so it cannot agree with the shipped decision by construction. The arm
that proves the SHIPPED code says the same thing is `check_arm.py`.

    python3 probe_records.py <record.json> [<record.json> ...]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: `gather._KEYSIG_CLASSES`, restated here ON PURPOSE — this probe must not
#: import the tree it is measuring. ⚠️ If they ever drift, the drift is the
#: finding: `check_arm.py` imports the real tuple and the two are compared.
KEYSIG_CLASSES = ("keySharp", "keyFlat", "keyNatural")


def run(path: str) -> dict:
    rec = json.load(open(path))["record"]
    obs, vs = rec["observations"], rec["verdicts"]
    name = Path(path).name
    print(f"RECORD  {name}")

    keys = [v for v in vs if v["quantity"] == "key_signature"]
    if not keys:
        print("DEAD: this record holds no key_signature verdict at all")
        return {"record": name, "dead": True}

    scopes = collections.Counter(v["subject"].split("/")[0] for v in keys)
    marks = collections.defaultdict(list)
    frames = collections.Counter()
    for o in obs:
        if o["quantity"] == "keysig_marker":
            marks[o["subject"]].append(o["value"])
            frames[o.get("frame")] += 1

    print(f"  Q1 CAN A CHANGE EXIST? key verdicts {len(keys)} scopes={dict(scopes)}"
          f"; marker rows {sum(frames.values())} frames={dict(frames)}")
    mid_staff = sum(n for k, n in scopes.items() if k != "staff")
    later_frames = sum(n for f, n in frames.items() if f != "cell:0")
    print(f"     -> mid-staff key verdicts: {mid_staff};  "
          f"marker rows outside cell 0: {later_frames}")

    cells = collections.Counter()
    for o in obs:
        if o["quantity"] != "glyph_box":
            continue
        v = o.get("value")
        cls = v[0] if isinstance(v, list) and v else None
        if cls in KEYSIG_CLASSES:
            parts = o["subject"].split("/")
            if parts[0] == "glyph" and len(parts) >= 5:
                cells[int(parts[4])] += 1
    later = sum(n for c, n in cells.items() if c != 0)
    print(f"  Q2 OUT OF REACH: key-accidental detections in cells != 0: "
          f"{later}  (cell 0 holds {cells.get(0, 0)})")

    agree = collections.Counter()
    for v in keys:
        if v["outcome"] != "decided" or not isinstance(v["value"], int):
            continue
        n = len(marks.get(v["subject"], []))
        f = abs(v["value"])
        agree["equal" if n == f else ("more" if n > f else "fewer")] += 1
    total = sum(agree.values())
    eq = agree.get("equal", 0)
    print(f"  Q3 WHAT THE MARKERS WOULD SAY: on {total} decided staves the "
          f"marker COUNT equals |fifths| {eq} times "
          f"({eq / total:.0%})" if total else "  Q3: no decided staves")
    print("     -> so the count is NOT a reading; it is evidence ink was there")

    by_reason = collections.defaultdict(lambda: [0, 0])
    for v in keys:
        if v["outcome"] == "decided":
            continue
        by_reason[v["reason"]][0] += 1
        if marks.get(v["subject"]):
            by_reason[v["reason"]][1] += 1
    print("  ABSTENTIONS, and how many carry marker ink:")
    for r, (t, w) in sorted(by_reason.items()):
        flag = "  <- reported as 'no evidence' on ink" if (
            r == "no_evidence" and w) else ""
        print(f"     {r:26s} {w}/{t}{flag}")

    return {"record": name, "key_verdicts": len(keys), "scopes": dict(scopes),
            "marker_frames": dict(frames), "mid_staff_key_verdicts": mid_staff,
            "marker_rows_outside_cell0": later_frames,
            "keysig_detections_in_later_cells": later,
            "keysig_detections_cell0": cells.get(0, 0),
            "decided_marker_count_agreement": dict(agree),
            "abstentions": {r: {"total": t, "with_marker_ink": w}
                            for r, (t, w) in by_reason.items()}}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    out = []
    for p in sys.argv[1:]:
        out.append(run(p))
        print()
    (HERE / "out" / "probe-records.json").write_text(json.dumps(out, indent=1))
    return 2 if all(r.get("dead") for r in out) else 0


if __name__ == "__main__":
    raise SystemExit(main())
