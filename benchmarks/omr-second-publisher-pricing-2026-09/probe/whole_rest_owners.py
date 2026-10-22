"""DOES THE RULE REACH INK THAT WOULD OTHERWISE HAVE BEEN WRITTEN?

⚠️ THE QUESTION A CROP CANNOT ANSWER. A crop says what the ink IS; it does not
say whether the exporter would have written a note for it. `export._place_notes`
already refuses a glyph whose `Q.GLYPH_OWNER` names another staff
(`owned_by_another_staff`, the 2026-09-11 contest repair), so a fire on ink that
was going to be dropped anyway costs NOTHING — and a fire on ink that survives
ownership is a note deleted from the file.

The distinction is load-bearing on a second publisher specifically, because
Breitkopf's fires sit at staff steps the Litolff population never reached
(−7.6, +15.6), i.e. OUTSIDE their own staff, which is the signature of a
neighbouring staff's ink landing in this cell's padding.

⚠️ THIS IS A LOWER BOUND ON THE COST AND NOT THE COST. It reads the record's
SAVED ownership verdicts; the A/B arm is what measures the file. Where the two
disagree, the arm wins.

    python3 whole_rest_owners.py --record R --fires out/fires.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--fires", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()

    blob = json.load(open(a.record))
    rec = blob["record"]
    owner, pitch, dur = {}, {}, {}
    for v in rec["verdicts"]:
        q = v["quantity"]
        if q == "glyph_owner":
            owner[v["subject"]] = v
        elif q == "pitch":
            pitch[v["subject"]] = v
        elif q == "duration":
            dur[v["subject"]] = v

    fires = json.load(open(a.fires))
    if not fires:
        print("NO FIRES — nothing to attribute.", file=sys.stderr)
        return 2
    if not owner:
        print("NO `glyph_owner` VERDICTS IN THIS RECORD — the projection or "
              "the schema is not what this expects, and a clean 'nothing is "
              "relocated' would be indistinguishable from a dead read.",
              file=sys.stderr)
        return 2
    print(f"positive control: {len(owner)} glyph_owner verdicts, "
          f"{len(pitch)} pitch, {len(dur)} duration in the record")

    rows, tally = [], collections.Counter()
    for f in fires:
        s = f["subject"]
        own = owner.get(s)
        st_own = None
        if own is not None:
            val = own.get("value")
            st_own = val if isinstance(val, str) else None
        my_staff = "/".join(s.split("/")[:4]).replace("glyph", "staff")
        relocated = bool(st_own and st_own != my_staff)
        p, d = pitch.get(s), dur.get(s)
        writable = (p is not None and p.get("outcome") == "decided"
                    and d is not None and d.get("outcome") == "decided")
        state = ("owned_by_another_staff" if relocated
                 else ("writable" if writable else "not_writable"))
        tally[state] += 1
        rows.append({"subject": s, "witness": f.get("witness"),
                     "staff_step": f.get("staff_step"),
                     "my_staff": my_staff, "owner": st_own,
                     "relocated": relocated,
                     "pitch": None if p is None else p.get("value"),
                     "pitch_outcome": None if p is None else p.get("outcome"),
                     "duration": None if d is None else d.get("value"),
                     "duration_outcome": None if d is None else d.get("outcome"),
                     "state": state})

    print()
    print(f"{'subject':<26} {'step':>7} {'witness':<17} {'owner':<16} "
          f"{'pitch':>7} {'dur':>6}  state")
    for r in rows:
        print(f"{r['subject']:<26} {r['staff_step']:>+7.2f} "
              f"{str(r['witness']):<17} "
              f"{(r['owner'] or '-').replace('staff/', ''):<16} "
              f"{str(r['pitch']):>7} {str(r['duration']):>6}  {r['state']}")
    print()
    print("SUMMARY:", dict(tally))
    print()
    print("  `owned_by_another_staff`  the exporter ALREADY refuses it; a fire "
          "here costs nothing")
    print("  `writable`                the exporter WOULD have written a note; "
          "a fire here DELETES it")
    if a.json:
        json.dump({"tally": dict(tally), "rows": rows}, open(a.json, "w"),
                  indent=1)
        print(f"\nwrote -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
