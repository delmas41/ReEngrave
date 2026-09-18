"""THE ARM: the column-profile reader end to end, against three bars.

`probe_separability.py` established that the stroke IS separable inside a
rejected component (96.7% / 99.3% of WIDE ones) and that the profile re-finds
98.2% / 98.7% of the strokes `detect_stems` already accepts. That is a
property of components. This runs the reader the way it would SHIP -- over
the whole cell, labelling NO components at all -- and prices it.

FOUR THINGS, and the last two are what decide whether it is worth shipping:

  1  REACH. How many `no_stem` heads does an added stroke cover, and how many
     strokes does that cost. Reported per publisher, never pooled.
  2  ⚠️ IS IT JUST THE WIDTH CAP BY ANOTHER NAME? `filter_sweep_arm.py`
     recovers 217 Litolff heads by relaxing `max_width_lines` 0.6 -> 1.5, and
     `width_cap_check.py` measured those recoveries at 83.6% convention
     agreement against a 95.8% bar -- i.e. roughly a quarter junk, and
     REFUSED. If this reader reaches the same heads it inherits that verdict
     and is not worth having. The overlap is computed head by head.
  3  QUALITY, against the one independent reader on this thread: the engraving
     convention off the raster (right-and-up or left-and-down), which agrees
     with the stems we already read 95.8%. The recovered strokes are held to
     that bar, exactly as `width_cap_check.py` holds the width cap's.
  4  ⚠️ FLAG-OFF IDENTITY. The reader is ADDITIVE: every shipped stroke
     survives and new ones are added only where none overlaps. So arm OFF
     must reproduce the record's own stroke set to the stroke, and the arm
     asserts it against the record BEFORE reading any delta -- because
     `line_detection.py` is the file every sibling arm's control runs
     through, and a flag-off difference here would break their instruments
     and look like their bug.

⚠️ NO OMR-NED FIGURE, deliberately: the metric is symmetric and pays for
emitting FEWER symbols, which is the wrong direction for a recall change.

⚠️ THIS IS A GATHER CHANGE. `readjudicate.py` and `reexport_arm.py` rebuild
from a saved record and are STRUCTURALLY BLIND to it; pricing its effect on a
FILE needs two full re-gathers, which this arm does not take and does not
claim.
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
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI, INK = 600, 128
COL_W, REACH, SWEEP_, TOUCH = 0.12, 10.0, 0.85, 0.35
MIN_ARM = 1.25


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def arm_len(mask, mid, up):
    n, i = 0, mid
    while 0 <= i < len(mask) and mask[i]:
        n += 1
        i += -1 if up else 1
    return max(0, n - 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--agree", type=float, default=0.25)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr import line_detection as ld
    from tools.omr.line_detection import (detect_stems, _binary_ink,
                                          _staff_line_spacing)
    from stroke_columns import read_strokes, anchor_to_heads

    heads, pboxes, lines_of, klass = {}, {}, {}, {}
    rec_strokes: dict[str, list] = collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "stem":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 4:
                p = o["subject"].split("/")
                rec_strokes["cell/" + "/".join(p[1:5])].append(
                    tuple(float(x) for x in v))
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
                heads[o["subject"]] = (float(v[1]), float(v[2]),
                                       float(v[3]), float(v[4]))
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    pboxes[o["subject"]] = [float(x) for x in bp]
    verdict, value = {}, {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            dec = v.get("outcome") == "decided"
            verdict[v["subject"]] = "DECIDED" if dec else str(v.get("reason"))
            if dec:
                value[v["subject"]] = str(v.get("value"))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}
    n_rec = sum(len(v) for v in rec_strokes.values())
    print(f"{a.label}: {len(missing)} heads abstain `no_stem`; "
          f"the record holds {n_rec} stem rows")

    pages = [int(x) for x in a.pages.split(",")]
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))

    # THREE VARIANTS, because the first one measured is not the one to ship:
    #   raw        every banded stroke, the column profile alone
    #   side       only strokes standing at a notehead's LEFT or RIGHT EDGE
    #              (`docs/engraving-conventions.md` [C9 + L10], geometry only)
    #   side+legal plus RIGHT-and-UP / LEFT-and-DOWN
    # ⚠️ The `side+legal` arm's convention score is CIRCULAR by construction
    # and is reported as REACH only.
    VARIANTS = ("raw", "side", "side+end", "side+end+legal")
    END_SWEEP = (0.20, 0.35, 0.50, 0.75)
    VARIANTS = VARIANTS + tuple(f"side+end@{e:.2f}" for e in END_SWEEP
                                if e != 0.35)
    off, wide_arm = {}, {}
    on = {v: {} for v in VARIANTS}
    added = {v: 0 for v in VARIANTS}
    heads_by_cell = collections.defaultdict(list)
    for s, b in heads.items():
        heads_by_cell["cell/" + "/".join(s.split("/")[1:5])].append(b)
    for (pws, cs), pg in prepared:
        local = _system_local(pws.staves)
        for c in cs:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            base = [(float(d.x_canonical), float(d.y_canonical),
                     float(d.width_canonical), float(d.height_canonical))
                    for d in detect_stems(c)]
            off[ck] = base
            wide_arm[ck] = [(float(d.x_canonical), float(d.y_canonical),
                             float(d.width_canonical), float(d.height_canonical))
                            for d in detect_stems(c, max_width_lines=1.5)]
            src = (c.image_no_staff
                   if getattr(c, "image_no_staff", None) is not None
                   else c.image)
            sp = _staff_line_spacing(c)
            if src is None or src.size == 0 or sp <= 1.0:
                for v in VARIANTS:
                    on[v][ck] = base
                continue
            bands = read_strokes(_binary_ink(src), sp, c.width,
                                 agree_spaces=a.agree)
            hs = heads_by_cell.get(ck, [])
            keep = {
                "raw": list(bands),
                "side": [st for st, _h, _s, _d
                         in anchor_to_heads(bands, hs, sp)],
                "side+end": [st for st, _h, _s, _d
                             in anchor_to_heads(bands, hs, sp, end_tol=0.35)],
                "side+end+legal": [
                    st for st, _h, _s, _d
                    in anchor_to_heads(bands, hs, sp, end_tol=0.35,
                                       require_legal=True)],
            }
            for e in END_SWEEP:
                if e == 0.35:
                    continue
                keep[f"side+end@{e:.2f}"] = [
                    st for st, _h, _s, _d
                    in anchor_to_heads(bands, hs, sp, end_tol=e)]
            for v in VARIANTS:
                extra = []
                seen = set()
                for st in keep[v]:
                    k = (st.x_canonical, st.y_canonical, st.width_canonical, st.height_canonical)
                    if k in seen:
                        continue
                    seen.add(k)
                    b = (float(st.x_canonical), float(st.y_canonical), float(st.width_canonical), float(st.height_canonical))
                    if any(overlaps(b, e) for e in base):
                        continue      # the component reader already has it
                    if any(overlaps(b, e) for e in extra):
                        continue
                    extra.append(b)
                added[v] += len(extra)
                on[v][ck] = base + extra

    # ── CONTROL 1: flag OFF must reproduce the RECORD, stroke for stroke ──
    n_off = sum(len(v) for v in off.values())
    same = sum(1 for ck, v in off.items()
               if sorted(v) == sorted(rec_strokes.get(ck, [])))
    cells_with = len({*off} | {*rec_strokes})
    print(f"\n== CONTROL 1 (flag OFF vs the record): {n_off} strokes against "
          f"{n_rec}; cells matching exactly {same} of {cells_with}")
    if n_off != n_rec or same != cells_with:
        print("DEAD: the re-cut does not reproduce the record with the reader "
              "OFF, so no delta below is attributable to the reader.",
              file=sys.stderr)
        return 2

    # ── CONTROL 2: the two sides must DIFFER, or the arm measured nothing ──
    n_on = {v: sum(len(x) for x in on[v].values()) for v in VARIANTS}
    print("== CONTROL 2 (the arm has teeth): strokes held by each arm")
    for v in VARIANTS:
        print(f"   {v:<12} {n_on[v]:>6}  (+{n_on[v] - n_off} added)")
    if all(n_on[v] == n_off for v in VARIANTS):
        print("DEAD: no arm added anything; there is no arm here.",
              file=sys.stderr)
        return 2

    # ── REACH, per variant ──
    got_wide = set()
    for s in missing:
        ck = "cell/" + "/".join(s.split("/")[1:5])
        if any(overlaps(heads[s], st) for st in off.get(ck, [])):
            continue
        if any(overlaps(heads[s], st) for st in wide_arm.get(ck, [])):
            got_wide.add(s)
    got = {v: {} for v in VARIANTS}
    for v in VARIANTS:
        for s in missing:
            ck = "cell/" + "/".join(s.split("/")[1:5])
            if any(overlaps(heads[s], st) for st in off.get(ck, [])):
                continue                      # already had one; not `no_stem`
            hit = [st for st in on[v].get(ck, []) if overlaps(heads[s], st)]
            if hit:
                got[v][s] = max(hit, key=lambda st: st[3])
    print(f"\n== REACH: `no_stem` heads newly covered, of {len(missing)}")
    print(f"{'variant':<12} {'heads':>6} {'share':>7} {'added strokes':>14} "
          f"{'heads per stroke':>17}")
    for v in VARIANTS:
        n = len(got[v])
        print(f"{v:<12} {n:>6} {n/max(1,len(missing)):>6.1%} "
              f"{added[v]:>14} {n/max(1,added[v]):>17.2f}")
    if not any(got[v] for v in VARIANTS):
        print("DEAD: reach is zero on every variant.", file=sys.stderr)
        return 2

    # ── IS IT THE WIDTH CAP BY ANOTHER NAME? ──
    print(f"\n== is this the WIDTH CAP by another name?  "
          f"(`max_width_lines` 0.6 -> 1.5 reaches {len(got_wide)})")
    print(f"{'variant':<12} {'both':>6} {'ONLY column':>12} "
          f"{'ONLY width cap':>15} {'shared':>8}")
    for v in VARIANTS:
        g = set(got[v])
        both = len(g & got_wide)
        print(f"{v:<12} {both:>6} {len(g - got_wide):>12} "
              f"{len(got_wide - g):>15} {both/max(1,len(g)):>7.1%}")

    # ── QUALITY: the engraving convention, off the raster ──
    doc = fitz.open(a.pdf)
    pgimg: dict[int, np.ndarray] = {}

    def convention(s):
        if s not in pboxes:
            return None
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        if not L or len(L) < 5:
            return None
        pg = int(p[1])
        if pg not in pgimg:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pgimg[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pgimg[pg]
        space = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
        x0, y0, x1, y1 = pboxes[s]
        cy = (y0 + y1) / 2
        w = max(2, int(COL_W * space))
        ya, yb = max(0, int(cy - REACH * space)), min(img.shape[0],
                                                      int(cy + REACH * space))
        mid = int(cy) - ya
        if yb - ya < 8 or not (0 <= mid < yb - ya):
            return None
        best = {"up": 0.0, "down": 0.0}
        step = max(1, w // 2)
        for side, edge in (("L", x0), ("R", x1)):
            lo = int(edge - (TOUCH if side == "R" else SWEEP_) * space)
            hi = int(edge + (SWEEP_ if side == "R" else TOUCH) * space)
            for cx in range(lo, hi + 1, step):
                xa, xb = max(0, cx), min(img.shape[1], cx + w)
                if xb - xa < 1:
                    continue
                mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                if not mask[mid]:
                    continue
                if side == "R":
                    best["up"] = max(best["up"], arm_len(mask, mid, True) / space)
                else:
                    best["down"] = max(best["down"],
                                       arm_len(mask, mid, False) / space)
        up, dn = best["up"] >= MIN_ARM, best["down"] >= MIN_ARM
        return ("up" if up else "down") if up != dn else None

    def stroke_dir(s, st):
        hx0, hy0, hw, hh = heads[s]
        return "up" if st[1] + st[3] / 2 < hy0 + hh / 2 else "down"

    ref = collections.Counter()
    for s, r in verdict.items():
        if r != "DECIDED" or s not in heads:
            continue
        c = convention(s)
        ref["convention silent" if c is None else
            ("AGREES" if c == value.get(s) else "disagrees")] += 1
    rr = ref["AGREES"] + ref["disagrees"]
    tallies = {}
    for v in VARIANTS:
        t_ = collections.Counter()
        for s, st in got[v].items():
            c = convention(s)
            t_["convention silent" if c is None else
               ("AGREES" if c == stroke_dir(s, st) else "disagrees")] += 1
        tallies[v] = t_
    print(f"\n== QUALITY: do the recovered strokes agree with the engraving "
          f"convention, read off the ORIGINAL page raster?")
    print(f"{'variant':<12} {'AGREES':>7} {'disagrees':>10} {'silent':>7} "
          f"{'rate':>7}")
    for v in VARIANTS:
        t_ = tallies[v]
        n = t_["AGREES"] + t_["disagrees"]
        note = "   <- CIRCULAR" if v.endswith("legal") else ""
        print(f"{v:<12} {t_['AGREES']:>7} {t_['disagrees']:>10} "
              f"{t_['convention silent']:>7} "
              f"{t_['AGREES']/max(1,n):>6.1%}{note}")
    print(f"\n   REFERENCE (stems we already read): {ref['AGREES']}/{rr} = "
          f"{ref['AGREES']/max(1,rr):.1%}   <- the bar")
    print(f"   (`width_cap_check.py` measured the width cap's recoveries at "
          f"83.6% against this bar and REFUSED them)")
    print(f"   ⚠️ `side+legal` is graded on the rule it was BUILT to satisfy. "
          f"Read its REACH, never its rate.")

    out = {"label": a.label, "agree": a.agree, "no_stem": len(missing),
           "record_strokes": n_rec, "off_strokes": n_off,
           "reference": dict(ref),
           "reference_rate": round(ref["AGREES"] / max(1, rr), 4),
           "width_cap_recovers": len(got_wide), "variants": {}}
    for v in VARIANTS:
        t_ = tallies[v]
        n = t_["AGREES"] + t_["disagrees"]
        g = set(got[v])
        out["variants"][v] = {
            "on_strokes": n_on[v], "added_strokes": added[v],
            "recovered": len(g),
            "shared_with_width_cap": len(g & got_wide),
            "only_column_profile": len(g - got_wide),
            "agreement": dict(t_),
            "agreement_rate": round(t_["AGREES"] / max(1, n), 4),
            "circular": v.endswith("legal")}
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
