#!/usr/bin/env python3
"""REACH FIRST: where along a stem does the head that claims it actually sit?

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

⚠️ `docs/ask-first-conventions.md` governs, and this job cannot ask — so the
assumption is written down instead of being left in the code.

**HOW A HUMAN GETS IT.** An editor with the plate in front of them does not
measure anything: they see that the stem *starts at the notehead* and runs
away from it. The head sits at the stem's **END** — at its bottom for a
stem-up note, at its top for a stem-down one. A vertical line that passes
*through the middle* of a head, with the head part-way along it, is not that
head's stem; it is a neighbour's stem, a barline, or a bracket.

**THE CONVENTION.** A stem is attached to its notehead at the side of the head
and terminates there. It extends away for about 3.5 staff spaces, or to a beam.
So the head's vertical centre is at one of the stroke's two ends, within about
half a notehead's height — that is not a statistic, it is what attachment IS.

**WHAT WOULD FALSIFY IT.** A print-adjudicated head whose own stem genuinely
passes through it — which happens for real: a head in the MIDDLE of a chord
shares one stem with the heads above and below it, and then it is mid-stroke by
construction. That case is the reason this probe reports the chord-mate column
apart, and the reason the eventual rule must not be a filter.

**NOT CONFIRMED WITH SEAN.**

## WHY THIS PROBE EXISTS

`adjudicate_stem_direction` attributes a stroke by `_stems_on` — **box overlap,
no tolerance** — so every head a stroke crosses claims it. Two independent
lanes on 2026-09-18 reached the same conclusion from different instruments: the
stroke lane's Breitkopf DISAGREE stratum is **6 of 6 one fault — the record's
notehead box stands part-way ALONG a NEIGHBOURING note's stem** — and the
beam-mate standoff put its own error in GROUPING rather than convention.
`docs/handoff-2026-09-18-three-lanes-and-the-print.md` §5 ranks the repair
first, and records that it **cannot** be done in `detect_stems`, which emits
STROKES and not (stroke, head) pairs: an end-at-the-head constraint there moved
disagreements 40 -> 40 and 14 -> 14, the fifth dead hypothesis on the thread.

**This measures the population before anything is built.** It reads committed
records only — no weights, no re-gather, no detector.

    python3 benchmarks/omr-stem-attribution-2026-09/probe_where_along_the_stem.py \
        --record /path/to/beethoven5-p1-p4.record.json --label Litolff \
        --json out/litolff.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def boxes_overlap(a, b) -> bool:
    """`[x, y, w, h]` overlap — the SHIPPED test, restated nowhere else.

    ⚠️ Imported rather than copied would be better, and is not possible: the
    shipped `_boxes_overlap` takes the same convention but lives behind a
    decision-module import chain that drags in the whole adjudicator registry.
    It is asserted equal to the shipped one by the unit test beside this lane.
    """
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
                or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    print(f"{a.label}: reading {a.record}", flush=True)
    doc = json.load(open(a.record))
    obs = doc["record"]["observations"]

    # subject -> rows, restricted to the two quantities this asks about
    heads: dict[str, list] = collections.defaultdict(list)
    stems: dict[str, list] = collections.defaultdict(list)
    spacing: dict[str, float] = {}
    for o in obs:
        q = o.get("quantity")
        v = o.get("value")
        if q == "glyph_box" and isinstance(v, list) and len(v) >= 5:
            if str(v[0]).startswith("notehead"):
                cell = "/".join(o["subject"].split("/")[1:5])
                # ⚠️⚠️ TWO FRAMES, AND THE SECOND IS NOT OPTIONAL. The value's
                # box is CANONICAL-CELL (a cell rescaled so the staff span is
                # constant); `detail.bbox_page_px` is PAGE pixels and is the
                # only one a crop can be placed with. Carrying only the first
                # is how this lane's own crop pass put every mark outside its
                # bar -- the frame fault CLAUDE.md records four instances of.
                bp = (o.get("detail") or {}).get("bbox_page_px")
                heads["cell/" + cell].append(
                    (o["subject"], str(v[0]),
                     [float(v[1]), float(v[2]), float(v[3]), float(v[4])],
                     [float(x) for x in bp] if bp and len(bp) == 4 else None))
        elif q == "stem" and isinstance(v, list) and len(v) == 4:
            stems[o["subject"]].append((o["id"], [float(x) for x in v]))
        elif q == "staff_spacing":
            try:
                spacing[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass

    n_heads = sum(len(v) for v in heads.values())
    n_stems = sum(len(v) for v in stems.values())
    print(f"  {n_heads} notehead boxes, {n_stems} stem rows, "
          f"{len(heads)} cells with a head", flush=True)

    out: dict = {"label": a.label, "record": a.record,
                 "heads": n_heads, "stems": n_stems}
    if not n_heads or not n_stems:
        print("⚠️ DEAD: this record carries no head/stem pair to measure.",
              file=sys.stderr)
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(a.json, "w"), indent=1)
        return 2

    # ── where along the stroke does each claiming head sit? ─────────────────
    #
    # ⚠️ `t` is the head's vertical CENTRE as a fraction of the stroke's own
    # height: 0.0 = at its top end, 1.0 = at its bottom end, 0.5 = halfway
    # along. The convention says a stem's head is at an END, so the mass
    # should be at the extremes and anything near 0.5 is the fault — EXCEPT
    # for an interior chord member, which is mid-stroke legitimately and is
    # counted apart.
    rows = []
    for cell, hs in heads.items():
        cell_stems = stems.get(cell, [])
        if not cell_stems:
            continue
        for subj, name, hb, hpage in hs:
            hcy = hb[1] + hb[3] / 2.0
            for sid, sb in cell_stems:
                if not boxes_overlap(hb, sb):
                    continue
                t = (hcy - sb[1]) / sb[3] if sb[3] > 0 else None
                if t is None:
                    continue
                # is another head of this cell ALSO on this stroke, and
                # further out? then this head can be an interior chord member
                mates = [o for o in hs
                         if o[0] != subj and boxes_overlap(o[2], sb)]
                above = any(o[2][1] + o[2][3] / 2.0 < hcy for o in mates)
                below = any(o[2][1] + o[2][3] / 2.0 > hcy for o in mates)
                rows.append({
                    "subject": subj, "stem": sid, "t": round(t, 3),
                    "stem_h": sb[3], "head_h": hb[3],
                    # ⚠️ THE DISTANCE TO THE NEARER END, IN NOTEHEAD HEIGHTS —
                    # the unit the convention is stated in, and scale-free, so
                    # it transfers between two plates whose staff spacing
                    # differs by 2x.
                    "end_gap_heads": round(
                        min(abs(hcy - sb[1]), abs(hcy - (sb[1] + sb[3])))
                        / max(1.0, hb[3]), 3),
                    "interior_chord_member": bool(above and below),
                    "n_mates": len(mates),
                    # ⚠️ The boxes travel with the row so a rule can be priced
                    # off this file without re-reading a 443 MB record.
                    "head_box": hb, "stem_box": sb,
                    # ⚠️ PAGE pixels, `[x0, y0, x1, y1]` CORNERS -- a different
                    # spelling from `head_box`'s `[x, y, w, h]`, and the two
                    # are never mixed. None where the row carried no page box.
                    "head_page_box": hpage,
                })

    out["pairs"] = len(rows)
    print(f"  {len(rows)} (head, stroke) overlapping pairs", flush=True)
    if not rows:
        print("⚠️ DEAD: no overlapping pair.", file=sys.stderr)
        json.dump(out, open(a.json, "w"), indent=1)
        return 2

    interior = [r for r in rows if r["interior_chord_member"]]
    plain = [r for r in rows if not r["interior_chord_member"]]
    out["interior_chord_members"] = len(interior)

    def band(rs):
        b = collections.Counter()
        for r in rs:
            g = r["end_gap_heads"]
            b["0.0-0.5" if g <= 0.5 else
              "0.5-1.0" if g <= 1.0 else
              "1.0-2.0" if g <= 2.0 else "over 2.0"] += 1
        return dict(b)

    out["end_gap_bands"] = {"all": band(rows), "plain": band(plain),
                            "interior_chord": band(interior)}
    print(f"\n== distance from the head's centre to the NEARER END of the "
          f"stroke, in notehead heights")
    print(f"  {'population':<22} {'n':>6} {'0-0.5':>7} {'0.5-1':>7} "
          f"{'1-2':>7} {'>2':>7}")
    for name, rs in (("all pairs", rows),
                     ("not a chord interior", plain),
                     ("chord interior", interior)):
        b = band(rs)
        print(f"  {name:<22} {len(rs):>6} "
              + " ".join(f"{b.get(k, 0):>7}"
                         for k in ("0.0-0.5", "0.5-1.0", "1.0-2.0",
                                   "over 2.0")))

    # ── the population the repair would actually reach ──────────────────────
    #
    # ⚠️ A head with ONE overlapping stroke and that stroke not ending at it is
    # where a wrong direction comes from. A head with SEVERAL is already
    # handled — the decision abstains `stems_disagree` when they point
    # different ways — so the two are reported apart: the first is a WRONG
    # ANSWER and the second an abstention, and conflating them would overstate
    # what the repair can recover.
    by_head: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        by_head[r["subject"]].append(r)
    one, many = 0, 0
    one_far, many_all_far = 0, 0
    for subj, rs in by_head.items():
        far = [r for r in rs
               if r["end_gap_heads"] > 1.0 and not r["interior_chord_member"]]
        if len(rs) == 1:
            one += 1
            one_far += 1 if far else 0
        else:
            many += 1
            many_all_far += 1 if len(far) == len(rs) else 0
    out["heads_with_a_stroke"] = {"one": one, "several": many,
                                  "one_and_it_is_far": one_far,
                                  "several_and_all_far": many_all_far}
    print(f"\n== heads claiming a stroke: {one} claim ONE, {many} claim several")
    print(f"   of the ONE group, {one_far} sit more than 1.0 notehead height "
          f"from either end — a wrong answer, not an abstention")
    print(f"   of the SEVERAL group, {many_all_far} have EVERY stroke far")

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    out["rows"] = rows
    json.dump(out, open(a.json, "w"), indent=1)
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
