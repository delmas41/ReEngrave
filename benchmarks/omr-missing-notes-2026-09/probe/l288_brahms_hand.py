#!/usr/bin/env python3
"""l288_brahms_hand: Sean's hand-truth page (Brahms 317803 pdf 0, `data/hand-truth/pages/imslp317803/0.json`) against records, for the
2.88 question. Each truth head (`noteheadHalf*` = a half; `noteheadBlack*` = filled) is matched to the record notehead of best box overlap
(IoU >= 0.3); the standing ADJUDICATE duration is classed:  half(decided 2.0 or 3.0)  /  narrowed-with-half  /  other-decided  / none.
THE GUARD: a truth FILLED head must never be a decided half (the count printed per record), a truth HALF should be.

    python3 l288_brahms_hand.py rec.json [rec2.json]
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

from l288_population import build  # noqa: E402
from l288_score import iou  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402

PAGE = HERE.parents[2] / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json"


def main():
    boxes = [b for b in json.loads(PAGE.read_text())["boxes"] if (b["cls"] or "").startswith(("noteheadHalf", "noteheadBlack"))]
    for path in sys.argv[1:]:
        rows = [r for r in build(RD.load_run(path)) if r["page"] == 0 and r["box_page"]]
        c = collections.Counter()
        bad = []
        for b in boxes:
            kind = "half" if b["cls"].startswith("noteheadHalf") else "black"
            best, bi = None, 0.3
            for r in rows:
                v = iou(r["box_page"], b["rect"])
                if v > bi:
                    best, bi = r, v
            if best is None:
                c[(kind, "nohead")] += 1
                continue
            if best["outcome"] == "decided":
                k = "decided_half" if best["reason"] == "hollow_head_bare_stem" or (best["beats"] or 0) >= 2.0 else "decided_other"
            elif best["outcome"] == "narrowed":
                k = "narrowed_with_half" if 2.0 in (best["cands"] or []) or 3.0 in (best["cands"] or []) else "narrowed_without"
            else:
                k = "abstained"
            c[(kind, k)] += 1
            if kind == "black" and best["outcome"] == "decided" and (best["reason"] == "hollow_head_bare_stem"):
                bad.append((b["id"], best["key"]))
        print(path)
        for k, n in sorted(c.items()):
            print(f"   {k[0]:6s} {k[1]:20s} {n}")
        print("   FILLED truth heads decided as a 2.70 half:", len(bad), bad[:5])


if __name__ == "__main__":
    main()
