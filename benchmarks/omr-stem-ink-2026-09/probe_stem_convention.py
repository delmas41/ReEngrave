"""THE ENGRAVING CONVENTION AS A TEST: which SIDE, and which WAY.

Sean, 2026-09-17: *"Does the direction as well as the side of the note head
it is connected to -- right-up and left-down -- help us at all?"*

It does, and it is the tightest test available, because it is a rule the
engraver has no freedom about. **A stem is attached on the RIGHT and goes UP,
or on the LEFT and goes DOWN.** Right-and-down does not exist; left-and-up
does not exist. So of the four (side, direction) cells, two are music and two
are something else -- a barline, a neighbouring stem, a bar of a beam, the
edge of a slur.

That makes it a discriminator AND a reader: a head whose ink fills exactly
one of the two legal cells has had its stem direction told to us.

⚠️ THE CONVENTION HAS KNOWN EXCEPTIONS AND THEY ARE NOT RARE. In two-voice
writing the upper voice takes stems up and the lower down REGARDLESS of where
the heads sit, and in a chord one stem serves every head. Neither breaks the
side/direction pairing -- both break the *position* convention (`stem up if
below the middle line`), which is the one PR #54 measured at 0.787. This test
does not touch that one.

⚠️ THE REFERENCE IS NOT A GUESS. The heads that already have a decided stem
direction set the bar: whatever share of THEM satisfies the convention is
what a head we read correctly looks like, and the `no_stem` heads are held to
that and to nothing else.

The reach is deliberately large (10 staff spaces) so the run length can also
be read against `line_detection.STEM_MAX_HEIGHT_LINES`, which is 8.0 and has
already been raised once for exactly this population.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

import fitz
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmarks"
                       / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI, INK = 600, 128
COL_W = 0.12        # a hairline
REACH = 10.0        # staff spaces each way -- past the 8.0 cap on purpose
SWEEP = 0.85
MIN_ARM = 1.25      # a stem's arm must reach this far from the head
TOUCH = 0.35        # and must start this close to the head's edge


def arm(mask: np.ndarray, mid: int, up: bool) -> int:
    """How far the unbroken run through `mid` reaches in one direction."""
    n = 0
    i = mid
    while 0 <= i < len(mask) and mask[i]:
        n += 1
        i += -1 if up else 1
    return max(0, n - 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    lines_of, pbox, klass = {}, {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                pbox[o["subject"]] = [float(x) for x in bp]
    verdict, value = {}, {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            dec = v.get("outcome") == "decided"
            verdict[v["subject"]] = "DECIDED" if dec else str(v.get("reason"))
            if dec:
                value[v["subject"]] = str(v.get("value"))

    doc = fitz.open(a.pdf)
    pages: dict[int, np.ndarray] = {}
    rows = []
    for s, reason in verdict.items():
        if s not in pbox or "Whole" in klass.get(s, ""):
            continue                      # a whole note correctly has none
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        if not L or len(L) < 5:
            continue
        pg = int(p[1])
        if pg not in pages:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pages[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pages[pg]
        space = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
        x0, y0, x1, y1 = pbox[s]
        cy = (y0 + y1) / 2
        w = max(2, int(COL_W * space))
        ya = max(0, int(cy - REACH * space))
        yb = min(img.shape[0], int(cy + REACH * space))
        if yb - ya < 8:
            continue
        mid = int(cy) - ya
        # best arm on each (side, direction), in staff spaces
        best = {("R", "up"): 0.0, ("R", "down"): 0.0,
                ("L", "up"): 0.0, ("L", "down"): 0.0}
        step = max(1, w // 2)
        for side, edge in (("L", x0), ("R", x1)):
            lo = int(edge - TOUCH * space) if side == "R" else int(edge - SWEEP * space)
            hi = int(edge + SWEEP * space) if side == "R" else int(edge + TOUCH * space)
            for cx in range(lo, hi + 1, step):
                xa, xb = max(0, cx), min(img.shape[1], cx + w)
                if xb - xa < 1 or not (0 <= mid < yb - ya):
                    continue
                mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                if not mask[mid]:
                    continue              # not attached at the head's centre
                u = arm(mask, mid, True) / space
                d = arm(mask, mid, False) / space
                best[(side, "up")] = max(best[(side, "up")], u)
                best[(side, "down")] = max(best[(side, "down")], d)
        legal_up = best[("R", "up")]
        legal_dn = best[("L", "down")]
        illegal = max(best[("R", "down")], best[("L", "up")])
        rows.append({"subject": s, "reason": reason, "read": value.get(s),
                     "R_up": round(legal_up, 2), "L_down": round(legal_dn, 2),
                     "illegal": round(illegal, 2)})

    print(f"{a.label}: {len(rows)} heads (whole notes excluded)")
    out = {"label": a.label, "min_arm": MIN_ARM, "groups": {}}
    print(f"\n== does the ink satisfy the convention -- RIGHT-and-UP, or "
          f"LEFT-and-DOWN, reaching >= {MIN_ARM} spaces?")
    print(f"{'stem_direction says':<20} {'n':>6} {'exactly ONE':>12} "
          f"{'both':>7} {'neither':>9}")
    for reason in sorted({r["reason"] for r in rows},
                         key=lambda x: -sum(1 for r in rows if r["reason"] == x)):
        v = [r for r in rows if r["reason"] == reason]
        one = [r for r in v if (r["R_up"] >= MIN_ARM) != (r["L_down"] >= MIN_ARM)]
        both = [r for r in v if r["R_up"] >= MIN_ARM and r["L_down"] >= MIN_ARM]
        nei = [r for r in v if r["R_up"] < MIN_ARM and r["L_down"] < MIN_ARM]
        out["groups"][reason] = {"n": len(v), "exactly_one": len(one),
                                 "both": len(both), "neither": len(nei),
                                 "share_one": round(len(one) / len(v), 4)}
        print(f"{reason:<20} {len(v):>6} {len(one):>7} {len(one)/len(v):>5.0%} "
              f"{len(both):>7} {len(nei):>9}")

    # ── does it AGREE with what we read, where we read one? (the control) ──
    agree = collections.Counter()
    for r in rows:
        if r["reason"] != "DECIDED" or r["read"] is None:
            continue
        if (r["R_up"] >= MIN_ARM) == (r["L_down"] >= MIN_ARM):
            agree["convention is silent or says both"] += 1
            continue
        says = "up" if r["R_up"] >= MIN_ARM else "down"
        agree["AGREES" if says == r["read"] else "disagrees"] += 1
    tot = agree["AGREES"] + agree["disagrees"]
    print(f"\n== POSITIVE CONTROL: where the convention speaks AND we already "
          f"read a stem, do they agree?")
    for k, n in agree.most_common():
        print(f"   {k:<34} {n:>6}")
    if tot:
        print(f"   -> agreement {agree['AGREES'] / tot:.1%} over {tot}")
        out["control_agreement"] = round(agree["AGREES"] / tot, 4)
    if not tot or agree["AGREES"] / tot < 0.8:
        print("\nDEAD: the convention does not reproduce the stems we already "
              "read, so it cannot be trusted on the ones we did not.",
              file=sys.stderr)
        Path(a.json).write_text(json.dumps(out, indent=1))
        return 2

    # ── the run lengths, against STEM_MAX_HEIGHT_LINES = 8.0 ──────────────
    print(f"\n== arm length where the convention speaks, in staff spaces "
          f"(line_detection.STEM_MAX_HEIGHT_LINES = 8.0)")
    for reason in ("DECIDED", "no_stem"):
        v = [max(r["R_up"], r["L_down"]) for r in rows
             if r["reason"] == reason
             and (r["R_up"] >= MIN_ARM) != (r["L_down"] >= MIN_ARM)]
        if not v:
            continue
        v.sort()
        over = sum(1 for x in v if x > 8.0)
        out["groups"].setdefault(reason, {})["arm_median"] = round(
            statistics.median(v), 2)
        out["groups"][reason]["arm_over_8"] = over
        print(f"   {reason:<10} n={len(v):>5}  median {statistics.median(v):>5.2f}"
              f"  p90 {v[9*len(v)//10]:>5.2f}  over 8.0: {over} ({over/len(v):.1%})")

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
