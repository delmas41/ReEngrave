"""HYPOTHESIS A: are the stemless heads CHORD MEMBERS whose partner took the stem?

Sean, 2026-09-17: *"Can you look at the stem issue and see if it is related to
multiple notes sharing stems or the sharps and flats issue"*

A chord or double stop is several noteheads on ONE physical stem, and
`_stems_on` attaches by BOX OVERLAP with no tolerance. If a chord's stem box
fails to reach the inner members, those members abstain `no_stem` while the
outer one is decided -- which would make the 793 a WIRING fault rather than a
reading one, and a much cheaper repair than anything in the handoff.

⚠️ THE PREDICTION IS A MIXED COLUMN. Heads sharing a stem stand at one x. So
if A holds, x-columns of size >= 2 should be MIXED (some stemmed, some not)
far more often than chance; if A is refuted, columns are all-or-nothing --
a stem either was read, and serves the whole column, or was not, and serves
none of it.

This also carries the CORRELATIONAL half of hypothesis B (the accidental pair
rule), because both need the same 60-second load: is `no_stem` enriched among
heads standing just right of an accidental? That is evidence ABOUT B and is
not a test OF B -- only re-running `detect_stems` with the rule off is that.

POSITIVE CONTROL: the probe reproduces the committed `is-the-ink-there.json`
head-kind table and band counts before it reports anything of its own. A join
error in this file looks exactly like a clean negative.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators.rhythm import _xywh_head, _boxes_overlap  # noqa: E402
from tools.omr.staged.record import Kind, Subject                            # noqa: E402


def cell_of(k):
    return Subject.from_key(k).at(Kind.CELL).to_key()


def box4(v):
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        return tuple(float(t) for t in v)
    except (TypeError, ValueError):
        return None


def axis_gaps(head, stem):
    """(dx, dy): separation on each axis independently, 0 where they overlap."""
    hx0, hy0, hx1, hy1 = head[0], head[1], head[0] + head[2], head[1] + head[3]
    sx0, sy0, sx1, sy1 = stem[0], stem[1], stem[0] + stem[2], stem[1] + stem[3]
    return (max(sx0 - hx1, hx0 - sx1, 0.0), max(sy0 - hy1, hy0 - sy1, 0.0))


def pct(n, d):
    return f"{100.0 * n / d:5.1f}%" if d else "    --"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "shared-stems.json"))
    #: x-tolerance for calling two heads one COLUMN, in notehead widths. A
    #: chord's heads are set at one x; a SECOND is offset by a full head width,
    #: which is why the sweep below is printed rather than one value chosen.
    ap.add_argument("--column-tol", type=float, default=0.35)
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    box_of, cls_of, space_of = {}, {}, {}
    glyphs_in = collections.defaultdict(list)   # cell -> [(name, box)]
    stems = collections.defaultdict(list)
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "glyph_box":
            v = o.get("value")
            b = _xywh_head(v)
            if b is not None:
                box_of[o["subject"]] = b
                name = str(v[0])
                glyphs_in[cell_of(o["subject"])].append((name, b))
        elif q == "notehead_class":
            cls_of[o["subject"]] = str(o["value"])
        elif q == "stem":
            b = box4(o.get("value"))
            if b is not None:
                stems[cell_of(o["subject"])].append(b)
        elif q == "cell_staff_space":
            try:
                space_of[cell_of(o["subject"])] = float(o["value"])
            except (TypeError, ValueError):
                pass

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    no_stem = {v["subject"] for v in verdicts if v["reason"] == "no_stem"}
    decided = {v["subject"] for v in verdicts if v["outcome"] == "decided"}
    every = no_stem | decided

    # ══ REACH, and the POSITIVE CONTROL, before anything of this probe's own ══
    print("== REACH")
    print(f"   stem_direction verdicts        {len(verdicts):6d}")
    print(f"   no_stem                        {len(no_stem):6d}")
    print(f"   decided                        {len(decided):6d}")
    print(f"   heads with a readable box      {sum(1 for s in every if s in box_of):6d}")
    print(f"   cells carrying stem ink        {len(stems):6d}")
    if not no_stem or not decided:
        print("DEAD: no population to speak about.")
        return 2

    def head_kind(sub):
        c = cls_of.get(sub, "")
        return ("whole" if "Whole" in c else "half" if "Half" in c
                else "black" if "Black" in c else "other")

    control = {"by_head_kind": {}, "no_ink_in_bar": 0}
    for kind in ("whole", "half", "black", "other"):
        d = sum(1 for s in decided if head_kind(s) == kind)
        n = sum(1 for s in no_stem if head_kind(s) == kind)
        if d + n:
            control["by_head_kind"][kind] = {"stem_found": d, "no_stem": n}
    control["no_ink_in_bar"] = sum(1 for s in no_stem
                                   if not stems.get(cell_of(s)))
    print("\n== POSITIVE CONTROL -- must reproduce the committed "
          "is-the-ink-there.json")
    for kind, t in control["by_head_kind"].items():
        print(f"   {kind:<6} stem {t['stem_found']:5d}   no_stem {t['no_stem']:5d}")
    print(f"   no stem ink ANYWHERE in the bar  {control['no_ink_in_bar']}")
    print("   (expected: no_stem 793, half 309/103, whole 8/9, "
          "no-ink-in-bar 211)")

    # ══ A1: the gap, decomposed by AXIS ══════════════════════════════════════
    # A pure-x miss (the stem stands beside the head at the right height) is a
    # different fault from a pure-y miss (the stem is above or below it).
    axis = collections.Counter()
    dxs, dys = [], []
    for sub in no_stem:
        head = box_of.get(sub)
        c = cell_of(sub)
        near = stems.get(c)
        sp = space_of.get(c)
        if head is None or not near or not sp:
            continue
        dx, dy = min((axis_gaps(head, s) for s in near),
                     key=lambda t: t[0] * t[0] + t[1] * t[1])
        dx, dy = dx / sp, dy / sp
        dxs.append(dx)
        dys.append(dy)
        if dx <= 0.01 and dy <= 0.01:
            axis["overlap on both axes (should not happen)"] += 1
        elif dx <= 0.01:
            axis["beside it in x, MISSED in y"] += 1
        elif dy <= 0.01:
            axis["level in y, MISSED in x"] += 1
        else:
            axis["missed on BOTH axes"] += 1
    print(f"\n== A1: the nearest stem in the bar, by which AXIS misses "
          f"(n={len(dxs)})")
    for k, v in axis.most_common():
        print(f"   {v:6d}  ({pct(v, len(dxs))})  {k}")
    if dxs:
        print(f"   median dx {statistics.median(dxs):.2f} spaces, "
              f"median dy {statistics.median(dys):.2f} spaces")

    # ══ A2: COLUMNS -- heads sharing an x, and whether they share an outcome ══
    def columns(cell_heads, tol_widths):
        """Greedy single-linkage on x-centre, in notehead widths."""
        items = sorted(cell_heads, key=lambda t: t[1][0] + t[1][2] / 2.0)
        out, cur = [], []
        for sub, b in items:
            cx = b[0] + b[2] / 2.0
            if cur:
                pcx, pw = cur[-1][2], cur[-1][3]
                if abs(cx - pcx) > tol_widths * max(pw, b[2], 1.0):
                    out.append(cur)
                    cur = []
            cur.append((sub, b, cx, b[2]))
        if cur:
            out.append(cur)
        return out

    by_cell = collections.defaultdict(list)
    for sub in every:
        b = box_of.get(sub)
        if b is not None:
            by_cell[cell_of(sub)].append((sub, b))

    print("\n== A2: x-COLUMNS of >=2 heads -- are they MIXED?")
    print("   (A predicts MIXED; a reading fault predicts all-or-nothing)")
    print(f"   {'tol':>5} {'columns>=2':>11} {'all stemmed':>12} "
          f"{'all stemless':>13} {'MIXED':>8} {'mixed share':>12}")
    sweep = {}
    for tol in (0.20, 0.35, 0.50, 0.75, 1.00):
        allv = allw = mixed = 0
        mixed_cols = []
        for c, heads in by_cell.items():
            for col in columns(heads, tol):
                if len(col) < 2:
                    continue
                subs = [s for s, _, _, _ in col]
                d = sum(1 for s in subs if s in decided)
                if d == len(subs):
                    allv += 1
                elif d == 0:
                    allw += 1
                else:
                    mixed += 1
                    mixed_cols.append((c, col, subs))
        tot = allv + allw + mixed
        sweep[tol] = {"columns": tot, "all_stemmed": allv,
                      "all_stemless": allw, "mixed": mixed,
                      "mixed_share": round(mixed / tot, 3) if tot else None}
        print(f"   {tol:>5.2f} {tot:>11d} {allv:>12d} {allw:>13d} "
              f"{mixed:>8d} {pct(mixed, tot):>12}")
        if abs(tol - a.column_tol) < 1e-9:
            keep = mixed_cols

    # ══ A3: the SHARP question -- does a stemless head have a stemmed partner
    # at its own x? That is the whole of hypothesis A stated as one number.
    print("\n== A3: of the stemless heads, how many stand in a column with a "
          "head that DID get a stem?")
    with_partner = 0
    partner_dx = []
    for c, heads in by_cell.items():
        for col in columns(heads, a.column_tol):
            subs = [s for s, _, _, _ in col]
            if not any(s in decided for s in subs):
                continue
            for s, b, cx, w in col:
                if s in no_stem:
                    with_partner += 1
                    sp = space_of.get(c) or 0.0
                    near = stems.get(c) or []
                    if near and sp:
                        dx, dy = min((axis_gaps(b, st) for st in near),
                                     key=lambda t: t[0] ** 2 + t[1] ** 2)
                        partner_dx.append((dx / sp, dy / sp))
    print(f"   stemless heads with a stemmed column partner   "
          f"{with_partner:5d}  ({pct(with_partner, len(no_stem))} of 793)")
    if partner_dx:
        print(f"   their median dx {statistics.median(p[0] for p in partner_dx):.2f}"
              f"  dy {statistics.median(p[1] for p in partner_dx):.2f} spaces")

    # ══ B (CORRELATIONAL ONLY): accidentals ══════════════════════════════════
    # The pair rule drops two parallel verticals within 0.9 staff spaces that
    # overlap vertically. A FLAT is ONE vertical stroke; its nearest partner is
    # whatever else stands near it -- and a stem-DOWN stem sits at the head's
    # LEFT edge, which is exactly where the accidental is. So: is `no_stem`
    # enriched among heads with an accidental just to their left?
    ACC = ("accidentalFlat", "accidentalSharp", "accidentalNatural",
           "keyFlat", "keySharp", "accidentalDoubleSharp",
           "accidentalDoubleFlat")

    def acc_gap(sub):
        """Distance from the head's LEFT edge to the nearest accidental's
        RIGHT edge, in staff spaces, requiring vertical overlap. None if there
        is no accidental to the left in this bar."""
        b = box_of.get(sub)
        c = cell_of(sub)
        sp = space_of.get(c)
        if b is None or not sp:
            return None, None
        best, bestname = None, None
        for name, ab in glyphs_in.get(c, ()):
            if not any(name.startswith(p) for p in ACC):
                continue
            ar = ab[0] + ab[2]
            if ar > b[0] + b[2]:          # not to the left of this head
                continue
            if not (ab[1] <= b[1] + b[3] and ab[1] + ab[3] >= b[1]):
                continue                  # no vertical overlap with the head
            g = (b[0] - ar) / sp
            if best is None or g < best:
                best, bestname = g, name
        return best, bestname

    print("\n== B (correlational): stemless rate vs the gap to the nearest "
          "ACCIDENTAL on the left")
    bands = [(-99.0, 0.0), (0.0, 0.5), (0.5, 0.9), (0.9, 1.5),
             (1.5, 3.0), (3.0, 99.0)]
    rows = {}
    counted = 0
    for lo, hi in bands:
        n = w = 0
        for s in every:
            g, _ = acc_gap(s)
            if g is None or not (lo <= g < hi):
                continue
            n += 1
            if s in no_stem:
                w += 1
        rows[f"{lo:g}..{hi:g}"] = {"heads": n, "stemless": w,
                                   "rate": round(w / n, 3) if n else None}
        counted += n
        print(f"   gap {lo:>6.1f}..{hi:<5.1f}  heads {n:5d}  stemless {w:5d}"
              f"  rate {(w / n if n else 0):.3f}")
    none_n = sum(1 for s in every if acc_gap(s)[0] is None)
    none_w = sum(1 for s in every if acc_gap(s)[0] is None and s in no_stem)
    print(f"   NO accidental left of it   heads {none_n:5d}  "
          f"stemless {none_w:5d}  rate {(none_w / none_n if none_n else 0):.3f}")
    rows["none"] = {"heads": none_n, "stemless": none_w,
                    "rate": round(none_w / none_n, 3) if none_n else None}
    if counted == 0:
        print("   ⚠️ DEAD ARM: no head has an accidental to its left. Either "
              "the plate prints none (it does not) or the glyph join failed.")

    print("\n== B (correlational): by accidental CLASS, gap < 0.9 spaces")
    bycls = collections.defaultdict(lambda: [0, 0])
    for s in every:
        g, name = acc_gap(s)
        if g is None or g >= 0.9 or g < 0.0:
            continue
        bycls[name][0] += 1
        if s in no_stem:
            bycls[name][1] += 1
    for name, (n, w) in sorted(bycls.items(), key=lambda t: -t[1][0]):
        print(f"   {name:<26} heads {n:5d}  stemless {w:5d}  "
              f"rate {(w / n if n else 0):.3f}")

    out = {"reach": {"verdicts": len(verdicts), "no_stem": len(no_stem),
                     "decided": len(decided)},
           "positive_control": control,
           "axis_of_miss": dict(axis),
           "median_dx_spaces": round(statistics.median(dxs), 3) if dxs else None,
           "median_dy_spaces": round(statistics.median(dys), 3) if dys else None,
           "column_sweep": {str(k): v for k, v in sweep.items()},
           "stemless_with_stemmed_column_partner": with_partner,
           "accidental_gap_bands": rows,
           "accidental_by_class": {k: {"heads": v[0], "stemless": v[1]}
                                   for k, v in bycls.items()}}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
