#!/usr/bin/env python3
"""l283_head_dump: everything ADJUDICATE's duration verdict read at given heads of a record -- the standing verdict (outcome, reason,
levels), the head's own stem and direction, EVERY `Q.STEM_TIP_INK` row and abstention at the stem's two ends (with the measures), every
`Q.NOTEHEAD_INK` row (the three fill readings' `center` / `ring` windows), the detector's class, any attached flag box. ROADMAP 2.83 fix
round (Sean's tiles 4, 8, 10): why a head's reading moved. Read-only.

    python3 l283_head_dump.py rec.json key [key ...]
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def short(d, keys):
    return {k: d.get(k) for k in keys if d.get(k) is not None}


def main():
    run = RD.load_run(sys.argv[1])
    for key in sys.argv[2:]:
        g = run.glyphs.get(key)
        print("=" * 100)
        if g is None:
            print(key, "not in the record")
            continue
        du = run.standing(key, Q.DURATION, "ADJUDICATE")
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        print(key, "class", g.cls, "box_canon", g.box_canon)
        print("  DURATION", du and {k: du.get(k) for k in ("outcome", "reason", "value")})
        print("  HEAD_STEM", hs and {k: hs.get(k) for k in ("outcome", "value", "reason")}, "| DIRECTION", sd and sd.get("value"))
        for o in run.observations:
            if o["quantity"] == Q.NOTEHEAD_INK and o["subject"] == key:
                d = o.get("detail") or {}
                print("  NOTEHEAD_INK", o["value"], {k: (v.get("windows") if isinstance(v, dict) else v) for k, v in d.items() if k.startswith("ink_")})
        stem_id = hs and hs.get("value")
        end = "top" if sd and sd.get("value") == "up" else "bottom"
        for o in list(run.observations) + list(run.abstentions):
            if o["quantity"] == Q.STEM_TIP_INK and o["subject"] == g.cell_key:
                d = o.get("detail") or {}
                if d.get("stem_row_id") != stem_id:
                    continue
                kind = "OBS" if "value" in o and o.get("state") != "DECLINED" and o.get("reason") is None else "ABST"
                mark = "  <== true tip" if d.get("end") == end else ""
                print(f"  TIP[{d.get('end')}] {kind} value={o.get('value')} reason={o.get('reason')} reader={o.get('reader')}",
                      short(d, ("why", "out", "arm", "t_first", "area", "left_area", "covered_area", "right", "left", "hooks", "hooks_reason")), mark)
        for o in run.observations:
            if o["quantity"] == Q.FLAG and o["subject"] != key and o["subject"].startswith("glyph/") and False:
                pass


if __name__ == "__main__":
    main()
