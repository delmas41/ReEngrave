"""Squeeze the 132 MB shared record down to the few quantities this job reads.

Everything downstream reads THIS, so the expensive load happens once and every
probe sees the same bytes. Nothing is derived here -- it is a projection, not a
reading.

⚠️ PAGE PIXELS, NEVER CANONICAL. `Q.GLYPH_BOX`'s `value` is the CANONICAL box
(one cell rescaled so the staff span is constant) and its `detail.bbox_page_px`
is the page one. A question about where a glyph sits against ITS STAFF'S LINES
can only be asked in the page frame -- `Q.STAFF_LINES` and `Q.STAFF_SPACING` are
filed there -- and two staves' canonical frames coincide by construction, which
is the fault `Q.ONSET_COLUMN` paid for.

    python3 .../cache.py --record R --out cache.json
"""
from __future__ import annotations

import argparse
import json
import sys

WANT_OBS = {"glyph_box", "glyph_conf", "notehead_class", "rest",
            "notehead_staff_position", "staff_lines", "staff_spacing",
            "cell_box", "cell_staff_space", "stem", "aug_dot", "flag"}
WANT_VERDICT = {"pitch", "duration", "glyph_owner", "meter", "clef", "event"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    blob = json.load(open(a.record))
    rec = blob["record"]
    obs = [o for o in rec["observations"] if o["quantity"] in WANT_OBS]
    vrd = [v for v in rec["verdicts"] if v["quantity"] in WANT_VERDICT]
    if not obs or not vrd:
        print("EMPTY PROJECTION -- the schema is not what this expects",
              file=sys.stderr)
        return 2
    print(f"observations {len(rec['observations'])} -> {len(obs)}")
    print(f"verdicts     {len(rec['verdicts'])} -> {len(vrd)}")
    json.dump({"provenance": blob.get("provenance"),
               "observations": obs, "verdicts": vrd},
              open(a.out, "w"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
