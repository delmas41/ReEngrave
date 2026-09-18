"""THE ATTACHMENT CONVENTION, PER HEAD -- so it can be INTERSECTED.

`omr-stem-ink-2026-09/probe_stem_convention.py` answers *how many* heads the
convention can speak for (472 Litolff, 653 Breitkopf) and writes only
aggregates. The question this directory exists for is *WHICH* heads, because
the beam-mate tier shipped on 2026-09-17 already serves 152 of the same
population and a reach figure that double-counts them overstates the job.

⚠️ EVERY CONSTANT AND THE RUN MEASUREMENT ARE **IMPORTED** FROM THAT PROBE,
never restated. Two copies of a number this project paid to measure once is how
they drift, and a re-implementation that quietly disagreed with its source
would make the intersection a measurement of my own arithmetic.

⚠️ AND THE CONTROL IS THAT IT REPRODUCES THE COMMITTED AGGREGATE. `--expect`
compares this run's group counts against the sibling's own committed JSON and
exits non-zero on any disagreement. A per-head table that does not add up to
the published totals is not a finer view of them; it is a different probe.

⚠️ WHAT IT CANNOT SAY. Agreement here is with our own `stem_direction`, which
is a READING (`stem_projection` off the CV stem rung). No note in any stem arm
has ever been checked against the print. So "95.9%" is two of our own readings
agreeing, and this probe inherits that limit whole.

    python3 convention_rows.py --record R --pdf P --label L \
        --out out/L-rows.json --expect ../omr-stem-ink-2026-09/out/L-convention.json
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
SIB = HERE.parents[0] / "omr-stem-ink-2026-09"
sys.path.insert(0, str(SIB))
sys.path.insert(0, str(HERE.parents[0] / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                       # noqa: E402
# ⚠️ IMPORTED, NOT RESTATED -- see the docstring.
from probe_stem_convention import (                         # noqa: E402
    COL_W, DPI, INK, MIN_ARM, REACH, SWEEP, TOUCH, arm)


def read_record(path: str):
    """`staff_lines`, `notehead_class`, `glyph_box` and the stem verdicts."""
    lines_of, pbox, klass = {}, {}, {}
    for o in stream_array(path, "observations"):
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
    for v in stream_array(path, "verdicts"):
        if v.get("quantity") == "stem_direction":
            dec = v.get("outcome") == "decided"
            verdict[v["subject"]] = "DECIDED" if dec else str(v.get("reason"))
            if dec:
                value[v["subject"]] = str(v.get("value"))
    return lines_of, pbox, klass, verdict, value


def measure(record: str, pdf: str):
    """One row per non-whole-note head: the best legal arm on each side."""
    lines_of, pbox, klass, verdict, value = read_record(record)
    doc = fitz.open(pdf)
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
        best = {("R", "up"): 0.0, ("R", "down"): 0.0,
                ("L", "up"): 0.0, ("L", "down"): 0.0}
        step = max(1, w // 2)
        for side, edge in (("L", x0), ("R", x1)):
            lo = (int(edge - TOUCH * space) if side == "R"
                  else int(edge - SWEEP * space))
            hi = (int(edge + SWEEP * space) if side == "R"
                  else int(edge + TOUCH * space))
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
        r_up, l_dn = best[("R", "up")], best[("L", "down")]
        says = None
        if (r_up >= MIN_ARM) != (l_dn >= MIN_ARM):
            says = "up" if r_up >= MIN_ARM else "down"
        rows.append({"subject": s, "reason": reason, "read": value.get(s),
                     "R_up": round(r_up, 2), "L_down": round(l_dn, 2),
                     "illegal": round(max(best[("R", "down")],
                                          best[("L", "up")]), 2),
                     "says": says,
                     "state": ("speaks" if says else
                               "both" if r_up >= MIN_ARM else "neither")})
    return rows


def groups(rows):
    out = {}
    for reason in sorted({r["reason"] for r in rows}):
        v = [r for r in rows if r["reason"] == reason]
        out[reason] = {
            "n": len(v),
            "exactly_one": sum(1 for r in v if r["state"] == "speaks"),
            "both": sum(1 for r in v if r["state"] == "both"),
            "neither": sum(1 for r in v if r["state"] == "neither"),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", help="the sibling's committed aggregate JSON")
    a = ap.parse_args()

    rows = measure(a.record, a.pdf)
    if not rows:
        print("DEAD: no head produced a row -- the record, the pdf or the "
              "subject-key join is wrong.", file=sys.stderr)
        return 2
    g = groups(rows)
    print(f"{a.label}: {len(rows)} heads (whole notes excluded)\n")
    print(f"{'stem_direction says':<20} {'n':>6} {'speaks':>8} {'both':>7} "
          f"{'neither':>9}")
    for reason, d in sorted(g.items(), key=lambda kv: -kv[1]["n"]):
        print(f"{reason:<20} {d['n']:>6} {d['exactly_one']:>8} "
              f"{d['both']:>7} {d['neither']:>9}")

    agree = collections.Counter()
    for r in rows:
        if r["reason"] != "DECIDED" or r["read"] is None or not r["says"]:
            continue
        agree["AGREES" if r["says"] == r["read"] else "disagrees"] += 1
    tot = agree["AGREES"] + agree["disagrees"]
    rate = (agree["AGREES"] / tot) if tot else 0.0
    print(f"\ncontrol agreement with the stems we already read: "
          f"{rate:.4f} over {tot}")

    Path(a.out).write_text(json.dumps(
        {"label": a.label, "min_arm": MIN_ARM, "groups": g,
         "control_agreement": round(rate, 4), "rows": rows}, indent=1))
    print(f"wrote {a.out}")

    if a.expect:
        want = json.loads(Path(a.expect).read_text())
        bad = []
        if abs(want.get("control_agreement", -1) - round(rate, 4)) > 1e-9:
            bad.append(f"control_agreement {want.get('control_agreement')} "
                       f"!= {round(rate, 4)}")
        for reason, d in (want.get("groups") or {}).items():
            mine = g.get(reason)
            if mine is None:
                bad.append(f"{reason}: absent from this run")
                continue
            for k in ("n", "exactly_one", "both", "neither"):
                if k in d and d[k] != mine[k]:
                    bad.append(f"{reason}.{k} {d[k]} != {mine[k]}")
        if bad:
            print("\nFAILED to reproduce the committed aggregate:",
                  file=sys.stderr)
            for b in bad:
                print(f"   {b}", file=sys.stderr)
            return 1
        print(f"CONTROL: reproduces {Path(a.expect).name} exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
