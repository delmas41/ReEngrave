#!/usr/bin/env python3
"""RE-DERIVE, then MEASURE: is a flagged vertical run two stems fused?

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

⚠️ `docs/ask-first-conventions.md` governs and this job cannot ask Sean, so
the assumption is written down rather than left in the code.

**THE CONVENTION (Sean's own words, 2026-09-20).** *"there are two separate
stems that are being measured as one stem"* — two voices stemming toward each
other, the upper UP to its beam and the lower DOWN to its beam, at nearly the
same x, touch and are detected as ONE connected component.

**HOW A HUMAN GETS IT.** A stem STARTS at its notehead and runs away from it.
So a single stem can extend past its OUTERMOST notehead at **one end only** —
the far end, toward the beam. A run that extends past the outermost head at
BOTH ends has two attachment points and is therefore two strokes.

**WHAT WOULD FALSIFY IT.** A run overshooting at both ends that the print
shows to be ONE stem — e.g. a stem fused end-on with a barline, a bracket, a
ledger line or a slur, or a stem whose own notehead was never DETECTED (so the
"outermost head" is the wrong head). Those are ink-merge faults with the same
signature and a different repair.

**NOT CONFIRMED WITH SEAN.** He adjudicated three crops, not this population.

## WHAT THIS DOES

§0(d) of `benchmarks/omr-stem-attribution-2026-09/FINDINGS.md` states four
measurements. The probe that produced them was **never committed** (`git log
--all -S overshoot` returns only the FINDINGS commit, which touches two
markdown files). This re-derives all four from the records, independently, per
publisher, and then measures the REACH and the SHAPE of a split.

⚠️ THE UNIT IS THE CELL'S OWN STAFF SPACE (`Q.CELL_STAFF_SPACE`), never a flat
100 px — `_upscale_to_canonical` scales a too-wide cell by WIDTH, and
`record.py` records 13 of 1,180 Litolff cells not at 100.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def boxes_overlap(a, b) -> bool:
    """`[x, y, w, h]` overlap — the SHIPPED test (`_boxes_overlap`)."""
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
                or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def cell_of(subject: str) -> str:
    return "cell/" + "/".join(subject.split("/")[1:5])


def read_record(path: str):
    doc = json.load(open(path))
    obs = doc["record"]["observations"]
    heads = collections.defaultdict(list)
    stems = collections.defaultdict(list)
    space: dict[str, float] = {}
    for o in obs:
        q = o.get("quantity")
        v = o.get("value")
        if q == "glyph_box" and isinstance(v, list) and len(v) >= 5:
            if str(v[0]).startswith("notehead"):
                heads[cell_of(o["subject"])].append(
                    (o["subject"], str(v[0]),
                     [float(v[1]), float(v[2]), float(v[3]), float(v[4])]))
        elif q == "stem" and isinstance(v, list) and len(v) == 4:
            stems[o["subject"]].append((o["id"], [float(x) for x in v]))
        elif q == "cell_staff_space":
            try:
                space[o["subject"]] = float(v)
            except (TypeError, ValueError):
                pass
    return heads, stems, space


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    print(f"{a.label}: reading {a.record}", flush=True)
    heads, stems, space = read_record(a.record)
    n_heads = sum(len(v) for v in heads.values())
    n_stems = sum(len(v) for v in stems.values())
    print(f"  {n_heads} notehead boxes, {n_stems} stem rows, "
          f"{len(space)} cells carry Q.CELL_STAFF_SPACE", flush=True)

    out = {"label": a.label, "record": a.record,
           "heads": n_heads, "stems": n_stems,
           "cells_with_staff_space": len(space)}

    # ⚠️ REACH FIRST. A probe that found nothing and a record with nothing in
    # it must not print the same table.
    if not n_heads or not n_stems:
        print("⚠️ DEAD: this record carries no head/stem pair.", file=sys.stderr)
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(a.json, "w"), indent=1)
        return 2

    # ── every (head, stroke) overlapping pair, with the STROKE as the key ───
    #
    # ⚠️ The stroke is the subject of this lane's question, not the head. §0's
    # table is per-HEAD; a split rule is per-RUN. Both are built here so the
    # re-derivation and the reach are read off ONE population.
    per_stroke: dict[str, dict] = {}
    pairs = 0
    no_space = 0
    for cell, hs in heads.items():
        for sid, sb in stems.get(cell, []):
            claimants = [h for h in hs if boxes_overlap(h[2], sb)]
            sp = space.get(cell)
            if sp is None or sp <= 0:
                no_space += 1
            per_stroke[sid] = {
                "cell": cell, "stem_box": sb, "staff_space": sp,
                "claimants": [
                    {"subject": h[0], "name": h[1], "box": h[2]}
                    for h in sorted(claimants, key=lambda h: h[2][1])],
            }
            pairs += len(claimants)

    out["pairs"] = pairs
    out["strokes_without_a_staff_space"] = no_space
    print(f"  {pairs} (head, stroke) overlapping pairs; "
          f"{no_space} strokes lack a staff space", flush=True)

    # ── §0(b) re-derivation: the per-HEAD classification ────────────────────
    #
    # A head is FINE if its centre is at an END of the stroke it claims
    # (within 1.0 notehead height, the band §2 of the prior lane used). Else
    # it is looked at again: does another claimant of the SAME stroke stand at
    # essentially the same x? That is a chord. The residue is the flagged set.
    band = collections.Counter()
    flagged_heads = []
    for sid, s in per_stroke.items():
        sb = s["stem_box"]
        for c in s["claimants"]:
            hb = c["box"]
            hcy = hb[1] + hb[3] / 2.0
            gap = min(abs(hcy - sb[1]), abs(hcy - (sb[1] + sb[3]))) \
                / max(1.0, hb[3])
            if gap <= 1.0:
                band["at_an_end"] += 1
                continue
            # the nearest companion's x offset, in notehead WIDTHS
            offs = [abs(o["box"][0] - hb[0]) / max(1.0, hb[2])
                    for o in s["claimants"] if o["subject"] != c["subject"]]
            if not offs:
                band["no_companion"] += 1
                flagged_heads.append((sid, c["subject"], "no_companion"))
            else:
                d = min(offs)
                if d < 0.1:
                    band["companion_same_x"] += 1
                elif d <= 0.5:
                    band["companion_0.1_0.5"] += 1
                    flagged_heads.append((sid, c["subject"], "0.1-0.5"))
                else:
                    band["companion_over_0.5"] += 1
                    flagged_heads.append((sid, c["subject"], "over_0.5"))
    out["head_bands"] = dict(band)
    out["flagged_heads"] = len(flagged_heads)
    print(f"\n== §0(b) per-HEAD classification (re-derived)")
    for k in ("at_an_end", "companion_same_x", "companion_0.1_0.5",
              "companion_over_0.5", "no_companion"):
        print(f"  {k:<22} {band.get(k, 0):>6}")
    print(f"  {'FLAGGED (sum of last 3)':<22} {len(flagged_heads):>6}")

    # ── §0(d): the both-ends overshoot, and the three corroborators ─────────
    #
    # ⚠️ OVERSHOOT is measured past the OUTERMOST claimant's own box EDGE, not
    # its centre — a stem attaches at the head's side and the head has height,
    # so measuring from the centre charges half a notehead of overshoot to
    # every correct stem. Reported in notehead HEIGHTS, the scale-free unit.
    flagged_strokes = {sid for sid, _, _ in flagged_heads}
    rows = []
    for sid, s in per_stroke.items():
        sb, cl = s["stem_box"], s["claimants"]
        if not cl:
            continue
        sp = s["staff_space"]
        top, bot = cl[0]["box"], cl[-1]["box"]
        hh = max(1.0, statistics.median(c["box"][3] for c in cl))
        over_top = (top[1] - sb[1]) / hh
        over_bot = ((sb[1] + sb[3]) - (bot[1] + bot[3])) / hh
        rows.append({
            "stem": sid, "cell": s["cell"],
            "flagged": sid in flagged_strokes,
            "n_claimants": len(cl),
            "len_spaces": (sb[3] / sp) if sp else None,
            "width_spaces": (sb[2] / sp) if sp else None,
            "over_top_heads": round(over_top, 3),
            "over_bot_heads": round(over_bot, 3),
            "both_ends": over_top > 0.5 and over_bot > 0.5,
        })

    fl = [r for r in rows if r["flagged"]]
    un = [r for r in rows if not r["flagged"]]
    out["strokes_with_a_claimant"] = len(rows)
    out["flagged_strokes"] = len(fl)

    def med(rs, k):
        vs = [r[k] for r in rs if r.get(k) is not None]
        return round(statistics.median(vs), 3) if vs else None

    both = sum(1 for r in fl if r["both_ends"])
    both_un = sum(1 for r in un if r["both_ends"])
    out["both_ends"] = {
        "flagged": both, "flagged_n": len(fl),
        "unflagged": both_un, "unflagged_n": len(un)}
    out["medians"] = {
        "len_spaces": {"flagged": med(fl, "len_spaces"),
                       "unflagged": med(un, "len_spaces")},
        "width_spaces": {"flagged": med(fl, "width_spaces"),
                         "unflagged": med(un, "width_spaces")},
    }
    print(f"\n== §0(d) re-derivation")
    print(f"  flagged strokes            {len(fl):>6}   "
          f"unflagged {len(un):>6}")
    print(f"  overshoot at BOTH ends     {both:>6} "
          f"({both / len(fl) * 100:.0f}%)" if fl else "  no flagged stroke")
    print(f"  …same test on UNFLAGGED    {both_un:>6} "
          f"({both_un / len(un) * 100:.1f}%)" if un else "")
    print(f"  median length, spaces      flagged "
          f"{out['medians']['len_spaces']['flagged']}   unflagged "
          f"{out['medians']['len_spaces']['unflagged']}")
    print(f"  median width, spaces       flagged "
          f"{out['medians']['width_spaces']['flagged']}   unflagged "
          f"{out['medians']['width_spaces']['unflagged']}")

    # ── REACH of a both-ends split over EVERY stroke, not just the flagged ──
    #
    # ⚠️ The flagged set is a per-HEAD residue and is NOT the population a
    # split rule would act on: the rule asks a question about the STROKE. So
    # the reach is reported over every stroke carrying a claimant.
    out["reach"] = {
        "strokes_total": n_stems,
        "strokes_with_a_claimant": len(rows),
        "both_ends_any": sum(1 for r in rows if r["both_ends"]),
        "both_ends_and_2plus_claimants":
            sum(1 for r in rows if r["both_ends"] and r["n_claimants"] >= 2),
    }
    print(f"\n== REACH of a both-ends split over ALL strokes")
    for k, v in out["reach"].items():
        print(f"  {k:<32} {v:>6}")

    out["rows"] = rows
    out["flagged_head_list"] = flagged_heads
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.json, "w"), indent=1)
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
