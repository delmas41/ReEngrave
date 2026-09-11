"""Detector confidence, split by whether the arc ends up binding two heads.

⚠️ CONFIDENCE IS A PROXY FOR INK QUALITY AND NOT A MEASUREMENT OF TRUTH, and
this repo says so in two places already (`ARC_KIND.md`: the arcs the grammar
cannot speak about sit at median 0.408 against 0.563). It is used here for one
thing only -- to ask whether the REFUSED population looks like the same ink as
the bound one, or like a weaker one.

⚠️ It cannot say an arc is FALSE. A confident detector is confidently wrong on
this corpus regularly. Read the two distributions, not either number alone.

It also prints `arc_kind`'s own `grammar.flanked_heads`, which is the
ADJUDICATE stage's count of heads under the same arc -- so the two stages can
be compared without re-deriving either.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q


def main(path: str) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)

    score_of = {}
    flanked_of = {}
    for o in rec.obs_of(Q.ARC_BOX):
        score_of[o["subject"]] = o.get("score")
        v = rec.verdict(Q.ARC_KIND, o["subject"])
        if v:
            g = (v.get("detail") or {}).get("grammar") or {}
            flanked_of[o["subject"]] = g.get("flanked_heads")

    # Map each placed arc box back to its subject, by identity of the list the
    # exporter stored -- `_place_arcs` keeps the converted box, so re-derive
    # the association here from the same record rather than guessing.
    box_subject = {}
    for o in rec.obs_of(Q.ARC_BOX):
        pb = E._corners_to_wh(E._page_box_of(o))
        if pb is not None:
            box_subject[tuple(round(v, 3) for v in pb)] = o["subject"]

    bound_scores, refused_scores = [], []
    bound_flanked, refused_flanked = [], []
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            for _m, b in segments:
                sub = box_subject.get(tuple(round(v, 3) for v in b))
                if sub is None:
                    continue
                s, f = score_of.get(sub), flanked_of.get(sub)
                (bound_scores if len(covered) >= 2 else refused_scores).append(s)
                if f is not None:
                    (bound_flanked if len(covered) >= 2
                     else refused_flanked).append(f)

    def q(xs, label):
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            print(f"  {label}: n/a")
            return
        print(f"  {label}: n={len(xs)} p10={xs[len(xs)//10]:.3f} "
              f"med={statistics.median(xs):.3f} p90={xs[len(xs)*9//10]:.3f}")

    print("DETECTOR CONFIDENCE of the arc detections in each group")
    q(bound_scores, "in a group that binds 2+ heads")
    q(refused_scores, "in a group that binds < 2   ")
    print("\n`arc_kind`'s OWN grammar.flanked_heads (the ADJUDICATE view)")
    print("  bound 2+ :", collections.Counter(bound_flanked).most_common(6))
    print("  refused  :", collections.Counter(refused_flanked).most_common(6))


if __name__ == "__main__":
    main(sys.argv[1])
