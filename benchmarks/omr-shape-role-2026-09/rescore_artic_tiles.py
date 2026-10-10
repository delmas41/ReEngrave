"""ROADMAP 2.12f ROUND 2 -- re-score the 12 round-1 tiles against SEAN'S answers,
one line each.

    python3 benchmarks/omr-shape-role-2026-09/rescore_artic_tiles.py \
        --selection out/artic-side-r1-tiles-selection.json \
        --answers ../../out/print/2.12f-review/answers.json \
        --base-brahms <base.json> --r2-brahms <r2.json> --round1-brahms <arm.json> \
        --base-litolff <base.json> --r2-litolff <r2.json> --round1-litolff <arm.json>

Sean's answers are the evidence (CLAUDE.md rule 7: who says it is right -- the
print, and the man who reads it). The EXPECTED outcome per tile is DERIVED from
what he said, not from what this lane reads:

  7, 9, 10   the mark belongs to the head it TOUCHES  -> r2's owner must be the
             nearest declared-side head round 1 recorded (0.1-0.4 heads away),
             not the head ~3 away the x-only pick took.
  1, 2, 5, 11, 6   the mark belongs to a note in the NEIGHBOUR staff -> in this
             cell the honest outcome is NOT a decision on an in-cell head
             (`no_notehead`), and the mark is owned via the neighbour's cell: a
             same-ink twin there is DECIDED, with its owner on Sean's side of it.
  3, 12      right as decided -> the SAME head as before.
  4, 8       NOT articulations (a piece of a tie; part of a `p` dynamic) -> out of
             scope; reported as a candidate for a family-precision refusal.
"""
from __future__ import annotations

import argparse
import json

EXPECT = {1: "neighbour", 2: "neighbour", 5: "neighbour", 11: "neighbour",
          6: "neighbour", 3: "same", 12: "same", 7: "touching", 9: "touching",
          10: "touching", 4: "not_articulation", 8: "not_articulation"}


def _by(path):
    return {r["subject"]: r for r in json.load(open(path))["articulations"]}


def _centre_y(box):
    return (box[1] + box[3]) / 2.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True)
    ap.add_argument("--answers", required=True)
    for d in ("brahms", "litolff"):
        for k in ("base", "r2", "round1"):
            ap.add_argument("--%s-%s" % (k, d), required=True)
    a = ap.parse_args(argv)
    sel = json.load(open(a.selection))
    ans = json.load(open(a.answers))
    data = {d: {k: _by(getattr(a, "%s_%s" % (k, d))) for k in ("base", "r2", "round1")}
            for d in ("brahms", "litolff")}
    ok_n = 0
    lines = []
    for t in sel:
        n, doc, s = t["n"], t["doc"], t["subject"]
        base, r2, r1 = (data[doc][k][s] for k in ("base", "r2", "round1"))
        bo, ro, r1o = base["owner"], r2["owner"], r1["owner"]
        what = EXPECT[n]
        detail = ro["detail"] or {}
        twins = detail.get("same_ink_twins") or []
        dec_twin = None
        for tw in twins:
            tr = data[doc]["r2"].get(tw)
            if tr and tr["owner"]["outcome"] == "decided":
                dec_twin = tr
                break
        verdict = None
        note = ""
        if what == "touching":
            want = (r1o["detail"] or {}).get("nearest_declared_side_head")
            verdict = (ro["outcome"] == "decided" and ro["value"] == want)
            note = "owner %s; touching head %s (gap %.2f heads); was %s" % (
                ro["value"], want, detail.get("gap_head_heights", float("nan")),
                bo["value"])
        elif what == "same":
            verdict = (ro["outcome"] == "decided" and ro["value"] == bo["value"])
            note = "owner %s (was %s)" % (ro["value"], bo["value"])
        elif what == "neighbour":
            verdict = (ro["outcome"] != "decided")
            if dec_twin is not None and dec_twin.get("owner_bbox_page") \
                    and r2.get("mark_bbox_page"):
                my = _centre_y(r2["mark_bbox_page"])
                oy = _centre_y(dec_twin["owner_bbox_page"])
                rel = "BELOW" if oy > my else "ABOVE"
                note = ("%s/%s here; twin %s DECIDED, its owner %s stands %s the "
                        "mark" % (ro["outcome"], ro["reason"], dec_twin["subject"],
                                  dec_twin["owner"]["value"], rel))
            else:
                note = "%s/%s here; %s" % (
                    ro["outcome"], ro["reason"],
                    "twins %s, none decided" % twins if twins else "no twin recorded")
        else:
            verdict = None
            note = "%s/%s -- not an articulation (candidate refusal)" % (
                ro["outcome"], ro["reason"])
        if verdict:
            ok_n += 1
        lines.append("tile %2d %-11s Sean: %s\n        %s  %s" % (
            n, t["category"], ans[str(n)][:96],
            "OK " if verdict else ("-- " if verdict is None else "NOT"), note))
    scored = sum(1 for t in sel if EXPECT[t["n"]] != "not_articulation")
    print("\n".join(lines))
    print("\nscored against Sean's answers: %d of %d articulation tiles as "
          "expected (tiles 4 and 8 are not articulations)" % (ok_n, scored))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
