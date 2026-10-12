#!/usr/bin/env python3
"""l283_why_unattached: for given heads, WHY `flags_attached` is 0 where the detector boxed a flag in the head's cell: the head's
CV stems and which the verdict used, every flag box in the cell with its refusal verdict (`Q.FLAG_IS_NOT_A_FLAG`) and its gap to
each stem against the join tolerance (`rhythm._attached_flags`'s own test, 0.8 spaces). Re-adjudicates ONE page from a
`l281_miss_rows.py` extract (the rebuild is the 2.81 lane's, its control reproduces every saved duration verdict). ROADMAP 2.83 probe.

    python3 l283_why_unattached.py --rows rows.json --page 24 --keys glyph/24/1/12/7/3
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_miss_rebuild import rebuild  # noqa: E402
from tools.omr.staged import adjudicate  # noqa: E402
from tools.omr.staged import adjudicators, consequences  # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH  # noqa: E402
from tools.omr.staged.record import Kind, Q, Subject  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--keys", required=True)
    a = ap.parse_args()
    data = json.loads(Path(a.rows).read_text())

    def pg(s):
        p = s.split("/")
        return int(p[1]) if len(p) >= 2 and p[0] != "document" else None
    data = {"observations": [o for o in data["observations"] if pg(o["subject"]) in (None, a.page)],
            "abstentions": [o for o in data["abstentions"] if pg(o["subject"]) in (None, a.page)],
            "saved_duration": {}}
    log, _id_map, _stats = rebuild(data)
    adjudicate._ensure_decisions()
    adjudicate.run(log)
    for key in a.keys.split(","):
        g = Subject.from_key(key)
        cell = g.at(Kind.CELL)
        v = log.verdict(Q.DURATION, g)
        print("==", key, "duration:", v.outcome.value if v else None, v.reason if v else None,
              "flags_attached", (v.detail or {}).get("flags_attached") if v else None,
              "stems_attached", (v.detail or {}).get("stems_attached") if v else None)
        hs = log.verdict(Q.HEAD_STEM, g)
        print("   head_stem:", hs.outcome.value if hs else None, hs.reason if hs else None, hs.value if hs else None)
        sd = log.verdict(Q.STEM_DIRECTION, g)
        print("   stem_direction:", sd.outcome.value if sd else None, sd.reason if sd else None, sd.value if sd else None)
        space = None
        for r in log.rows(Q.CELL_STAFF_SPACE, cell):
            space = float(r.value)
        tol = RH.STEM_JOIN_TOLERANCE_SPACES * space if space else 0.0
        box = [r for r in log.rows(Q.GLYPH_BOX, g)]
        hb = RH._xywh_head(box[-1].value) if box else None
        print("   head box", hb, "space", space, "tol", round(tol, 1))
        stems = [(r.id, RH._xywh(r)) for r in log.rows(Q.STEM, cell)]
        near = [(i, b) for i, b in stems if hb and RH._box_gap(b, hb) <= tol]
        print("   CV stems within tol of the head:", near)
        for fr in log.rows(Q.FLAG, cell, scope=__import__("tools.omr.staged.record", fromlist=["Scope"]).Scope.SELF_AND_DESCENDANTS):
            fb = log.rows(Q.GLYPH_BOX, fr.subject)
            fbox = RH._xywh_head(fb[-1].value) if fb else None
            ref = log.verdict(Q.FLAG_IS_NOT_A_FLAG, fr.subject)
            gaps = [(i, round(RH._box_gap(b, fbox), 1)) for i, b in stems if fbox] if fbox else None
            if fbox and hb and abs(fbox[0] - hb[0]) < 6 * (space or 100):
                print("   flag", fr.value, fr.subject.to_key(), "box", [round(x, 1) for x in fbox], "refusal:",
                      (ref.outcome.value, ref.value, ref.reason) if ref else None, "gap to each CV stem:", gaps)


if __name__ == "__main__":
    main()
