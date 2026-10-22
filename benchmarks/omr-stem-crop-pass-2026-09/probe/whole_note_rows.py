"""A WHOLE NOTE HAS NO STEM — and the record gives some of them one.

⚠️ ADDED MID-PASS at the coordinator's direction. A CENSUS of a named
population, reported apart from `SAMPLE.json` and never pooled with it.

`docs/engraving-conventions.md` `[C9 + L10]` excludes whole notes throughout: a
semibreve carries no stem, so a stem direction for one is not a reading, it is
a confident wrong answer fed on to `Q.EVENT` and `Q.VOICES`. The registry files
it ASSERTED WITH NO FIGURE, and `omr-stem-attachment-2026-09/whole_notes.py`
found the contradiction without looking for it.

⚠️ THE HAZARD IS NAMED BY THAT PROBE AND IS WHY THE PRINT IS THE ONLY WAY TO
SETTLE IT: `notehead_class` can misread a HALF note as a whole one, and a half
note DOES have a stem. So a contradiction has two readings and only the crop
separates them:

  * the head is really a WHOLE note -> the DIRECTION is the false one, and the
    convention holds;
  * the head is really a HALF note -> the CLASS is the false one, the direction
    may be right, and the convention is not what failed.

Two paths reach a direction and both are enumerated, reported apart:

  * PROJECTION — the record's own `stem_direction` verdict on a head whose
    `notehead_class` is `noteheadWhole*`;
  * BORROW — the beam-mate tier lending a direction to such a head.

    python3 probe/whole_note_rows.py --decided out/X-decided.json \
        --rows out/X-rows.json --beammate <attach>/out/X-beammate.json \
        --label X --json out/X-wholenotes.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decided", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--beammate")
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    dec = json.loads(Path(a.decided).read_text())["rows"]
    stemless = {r["subject"]: r
                for r in json.loads(Path(a.rows).read_text())["rows"]}
    out = []
    for r in dec:
        if r.get("cls") and "Whole" in r["cls"]:
            out.append({**r, "path": "projection",
                        "direction": r["read_direction"]})
    n_proj = len(out)
    n_borrow = 0
    if a.beammate:
        fired = json.loads(Path(a.beammate).read_text())["fired"]
        for s, d in fired.items():
            r = stemless.get(s)
            # ⚠️ the BORROW path reaches heads whose own reading ABSTAINED, so
            # they live in the stemless rows and not in the decided ones.
            if r and r.get("cls") and "Whole" in r["cls"]:
                out.append({**r, "path": "borrow", "direction": d,
                            "read_direction": None})
                n_borrow += 1
    print(f"{a.label}: whole-class heads given a stem direction — "
          f"projection {n_proj}, borrow {n_borrow}, total {len(out)}")
    if not out:
        print("DEAD: no whole-class head carries a direction here",
              file=sys.stderr)
        return 2
    keep = [r for r in out if r.get("bbox_page_px")]
    print(f"croppable: {len(keep)} of {len(out)}")
    Path(a.json).write_text(json.dumps(
        {"label": a.label,
         "what": "heads whose notehead_class is a WHOLE note and which the "
                 "pipeline nevertheless gives a stem direction. Either the "
                 "direction is wrong or the class is - the print says which.",
         "added_mid_pass": True,
         "not_part_of_the_preregistered_sample": True,
         "projection": n_proj, "borrow": n_borrow,
         "n": len(keep), "rows": keep}, indent=1))
    print(f"wrote {a.json}")
    return 0 if keep else 2


if __name__ == "__main__":
    raise SystemExit(main())
