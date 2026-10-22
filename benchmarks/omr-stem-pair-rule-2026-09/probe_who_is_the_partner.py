"""WHO EATS THE STEM? -- naming the partner of every stroke the pair rule drops.

`probe_pair_rule.py` measures that `_drop_paired_strokes` deletes 244 strokes
on Litolff Beethoven 5 pp.1-4 and that 73 of the 793 `no_stem` heads would stop
abstaining without it. That says the rule COSTS something; it does not say
Sean's question, which is WHICH of two mechanisms is doing it:

  ACCIDENTAL   the stroke pairs with a sharp's or a natural's own vertical, or
               with the single vertical of a FLAT -- the rule firing on the
               population it was written for, and taking a stem with it;
  TWO STEMS    the stroke pairs with ANOTHER stroke that itself carries a
               notehead -- which would refute the rule's stated premise, "a
               stem is single ... successive notes are set further apart than
               an accidental's own strokes";
  UNATTRIBUTED neither -- residue, a barline fragment, ink we cannot name.

The partition is re-derived by RESTATING `_drop_paired_strokes`' own pairing
test over the OFF-arm strokes, so a partner here is a partner there. It is
asserted against the shipped function: the set this file computes as dropped
must equal (OFF minus ON) exactly, or the restatement has drifted and every
label below is about a different pairing.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import (detect_stems, _staff_line_spacing)      # noqa: E402
from tools.omr.staged import record as R                                      # noqa: E402
from tools.omr.staged.gather import _system_local                             # noqa: E402
from tools.omr.staged.pipeline import prepare_pages                           # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (                            # noqa: E402
    _boxes_overlap, _xywh_head, _Shim)
from tools.omr import transcribe as _legacy_stems                             # noqa: E402
from tools.omr.staged.record import Kind, Subject                             # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
       "symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")

#: The shipped defaults of `detect_stems`, restated here ONLY so the pairing
#: can be re-derived; they are asserted against the function's own signature.
GAP_LINES = 0.9
MIN_OVERLAP = 0.6

ACC_PREFIX = ("accidental", "keyFlat", "keySharp", "keyNatural")


def cell_of(k):
    return Subject.from_key(k).at(Kind.CELL).to_key()


def box(d):
    return (float(d.x_canonical), float(d.y_canonical),
            float(d.width_canonical), float(d.height_canonical))


def partners(bs, spacing):
    """{i: [j, ...]} -- the pairing `_drop_paired_strokes` would find."""
    max_dx = spacing * GAP_LINES
    cen = [b[0] + b[2] / 2.0 for b in bs]
    top = [b[1] for b in bs]
    bot = [b[1] + b[3] for b in bs]
    out = collections.defaultdict(list)
    for i in range(len(bs)):
        for j in range(len(bs)):
            if i == j or abs(cen[i] - cen[j]) > max_dx:
                continue
            ov = min(bot[i], bot[j]) - max(top[i], top[j])
            if ov <= 0:
                continue
            if ov / max(1.0, min(bot[i] - top[i], bot[j] - top[j])) >= MIN_OVERLAP:
                out[i].append(j)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--pdf", default=PDF)
    ap.add_argument("--pages", default="1,2,3,4")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json", default=str(HERE / "out" / "who-is-the-partner.json"))
    a = ap.parse_args()

    # signature guard -- the restatement must match the shipped defaults
    import inspect
    sig = inspect.signature(detect_stems).parameters
    assert sig["accidental_pair_gap_lines"].default == GAP_LINES, sig
    assert sig["accidental_pair_overlap"].default == MIN_OVERLAP, sig
    print(f"== the shipped pair window: gap {GAP_LINES} staff spaces, "
          f"overlap {MIN_OVERLAP} of the shorter stroke")

    prepared = prepare_pages(a.pdf, [int(t) for t in a.pages.split(",")],
                             dpi=a.dpi)
    per_cell = {}
    n_drop_check = 0
    for pws, cells in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            sub = R.cell(c.page_index, key[0], key[1], c.measure_index).to_key()
            on = [box(d) for d in detect_stems(c)]
            off = [box(d) for d in detect_stems(c, drop_accidental_pairs=False)]
            sp = _staff_line_spacing(c)
            per_cell[sub] = (on, off, sp)
            n_drop_check += len(off) - len(on)
    print(f"== REACH: {len(per_cell)} cells, {n_drop_check} strokes dropped")
    if n_drop_check == 0:
        print("DEAD: nothing dropped.")
        return 2

    # ── the restatement must reproduce the shipped drop set exactly ────────
    mismatch = 0
    dropped_by_cell = {}
    for sub, (on, off, sp) in per_cell.items():
        if len(off) == len(on):
            continue
        pr = partners(off, sp)
        mine = {i for i in range(len(off)) if pr.get(i)}
        rem = list(on)
        shipped = set()
        for i, b in enumerate(off):
            if b in rem:
                rem.remove(b)
            else:
                shipped.add(i)
        if mine != shipped:
            mismatch += 1
        dropped_by_cell[sub] = (off, pr, shipped, sp)
    print(f"== CONTROL: cells where the restated pairing disagrees with the "
          f"shipped function: {mismatch}")
    if mismatch:
        print("   ⚠️ the restatement has DRIFTED -- every label below is about "
              "a different pairing.")

    # ── the record's heads and accidentals ─────────────────────────────────
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    box_of, name_of = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            v = o.get("value")
            b = _xywh_head(v)
            if b is not None:
                box_of[o["subject"]] = b
                name_of[o["subject"]] = str(v[0])
    heads, accs = collections.defaultdict(list), collections.defaultdict(list)
    for o in rec["observations"]:
        if o["quantity"] == "notehead_class":
            b = box_of.get(o["subject"])
            if b is not None:
                heads[cell_of(o["subject"])].append((o["subject"], b))
    for sub, nm in name_of.items():
        if any(nm.startswith(p) for p in ACC_PREFIX):
            accs[cell_of(sub)].append((nm, box_of[sub]))

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    no_stem = {v["subject"] for v in verdicts if v["reason"] == "no_stem"}
    print(f"   accidental glyphs on the record: "
          f"{sum(len(v) for v in accs.values())}")

    # ── classify every dropped stroke by WHO its partner is ───────────────
    kind = collections.Counter()
    kind_head = collections.Counter()     # only strokes that carry a notehead
    acc_class = collections.Counter()
    rescued_by_kind = collections.defaultdict(set)
    for sub, (off, pr, shipped, sp) in dropped_by_cell.items():
        hs = heads.get(sub, [])
        ac = accs.get(sub, [])

        def carries(i):
            return [s for s, b in hs if _boxes_overlap(b, off[i])]

        def acc_on(i):
            return [nm for nm, b in ac if _boxes_overlap(b, off[i])]

        for i in sorted(shipped):
            ps = pr.get(i, [])
            p_heads = any(carries(j) for j in ps)
            p_accs = [nm for j in ps for nm in acc_on(j)]
            if p_heads:
                k = "partner CARRIES A NOTEHEAD (two stems)"
            elif p_accs:
                k = "partner is an ACCIDENTAL glyph"
            else:
                k = "partner is UNATTRIBUTED ink"
            kind[k] += 1
            mine = carries(i)
            if mine:
                kind_head[k] += 1
                if p_accs:
                    acc_class[p_accs[0]] += 1
                for s in mine:
                    if s in no_stem:
                        rescued_by_kind[k].add(s)

    print(f"\n== EVERY dropped stroke, by who its partner is "
          f"(n={sum(kind.values())})")
    for k, v in kind.most_common():
        print(f"   {v:5d}  ({100.0 * v / sum(kind.values()):5.1f}%)  {k}")

    tot_h = sum(kind_head.values())
    print(f"\n== ONLY the dropped strokes that CARRY A NOTEHEAD -- the cost "
          f"(n={tot_h})")
    for k, v in kind_head.most_common():
        print(f"   {v:5d}  ({100.0 * v / max(1, tot_h):5.1f}%)  {k}")
    print(f"\n== heads rescued from `no_stem`, attributed to the mechanism")
    allr = set()
    for k, s in sorted(rescued_by_kind.items(), key=lambda t: -len(t[1])):
        allr |= s
        print(f"   {len(s):5d}  {k}")
    print(f"   {len(allr):5d}  TOTAL distinct heads "
          f"({100.0 * len(allr) / max(1, len(no_stem)):.1f}% of {len(no_stem)})")
    if acc_class:
        print(f"\n== when an ACCIDENTAL ate a stem, which accidental")
        for nm, v in acc_class.most_common():
            print(f"   {v:5d}  {nm}")

    # ── IS THERE A DISCRIMINATOR INSIDE `detect_stems`? ───────────────────
    # The rule runs on the CELL alone -- it has no noteheads and cannot get
    # them, `detect_stems(cell)` taking nothing else -- so any repair has to
    # separate the two populations on the STROKE GEOMETRY. These are the four
    # quantities such a rule could read. Reported as a measurement, with the
    # widest empty interval, because a cut through an overlapping population
    # would be a constant fitted to this plate.
    feats = {"STEM PAIR (both carry a notehead)": collections.defaultdict(list),
             "ACCIDENTAL PAIR (neither carries one)":
                 collections.defaultdict(list)}
    for sub, (off, pr, shipped, sp) in dropped_by_cell.items():
        hs = heads.get(sub, [])
        if not sp:
            continue

        def carries(i):
            return any(_boxes_overlap(b, off[i]) for _s, b in hs)

        seen = set()
        for i in sorted(shipped):
            for j in pr.get(i, []):
                if (min(i, j), max(i, j)) in seen:
                    continue
                seen.add((min(i, j), max(i, j)))
                both, neither = carries(i) and carries(j), not (carries(i) or carries(j))
                lab = ("STEM PAIR (both carry a notehead)" if both else
                       "ACCIDENTAL PAIR (neither carries one)" if neither
                       else None)
                if lab is None:
                    continue
                bi, bj = off[i], off[j]
                f = feats[lab]
                f["shorter_height_spaces"].append(min(bi[3], bj[3]) / sp)
                f["taller_height_spaces"].append(max(bi[3], bj[3]) / sp)
                f["top_offset_spaces"].append(abs(bi[1] - bj[1]) / sp)
                f["bottom_offset_spaces"].append(
                    abs((bi[1] + bi[3]) - (bj[1] + bj[3])) / sp)
                f["centre_dx_spaces"].append(
                    abs((bi[0] + bi[2] / 2) - (bj[0] + bj[2] / 2)) / sp)

    # ── B-q2: DO THE TWO STEMS POINT OPPOSITE WAYS? ──────────────────────
    # Sean, 2026-09-17: notes sounding on one beat in one voice share ONE
    # stem, whatever the interval -- so two genuine stems within the pair
    # window CANNOT be a chord. They are either TWO VOICES on one staff, whose
    # stems point opposite ways by convention, or successive notes set very
    # close. An accidental's two strokes carry no notehead and so point
    # NOWHERE, which is a discriminator the shipped rule does not have.
    dirs = collections.Counter()
    dx_by = collections.defaultdict(list)
    for sub, (off, pr, shipped, sp) in dropped_by_cell.items():
        hs = heads.get(sub, [])
        if not sp:
            continue

        def carried(i):
            return [b for _s, b in hs if _boxes_overlap(b, off[i])]

        def facing(i):
            g = carried(i)
            if not g:
                return None
            return _legacy_stems._stem_direction(_Shim(*off[i]),
                                                 [_Shim(*b) for b in g])

        seen = set()
        for i in sorted(shipped):
            for j in pr.get(i, []):
                k = (min(i, j), max(i, j))
                if k in seen:
                    continue
                seen.add(k)
                di, dj = facing(i), facing(j)
                if di is None and dj is None:
                    lab = "neither carries a head (accidental-shaped)"
                elif di is None or dj is None:
                    lab = "only ONE carries a head"
                elif di != dj:
                    lab = "both carry a head, OPPOSITE ways (two voices)"
                else:
                    lab = f"both carry a head, SAME way ({di})"
                dirs[lab] += 1
                dx_by[lab].append(
                    abs((off[i][0] + off[i][2] / 2)
                        - (off[j][0] + off[j][2] / 2)) / sp)
    print("\n== B-q2: the dropped PAIRS, by where their stems point")
    tp = sum(dirs.values())
    for k, v in dirs.most_common():
        xs = sorted(dx_by[k])
        med = xs[len(xs) // 2] if xs else float("nan")
        print(f"   {v:5d}  ({100.0 * v / max(1, tp):5.1f}%)  {k}"
              f"   median centre dx {med:.2f} spaces")

    print("\n== COULD A GEOMETRY RULE SEPARATE THEM? (medians, p10-p90)")
    keys = ["shorter_height_spaces", "taller_height_spaces",
            "top_offset_spaces", "bottom_offset_spaces", "centre_dx_spaces"]
    geom = {}
    for lab, f in feats.items():
        n = len(f.get("shorter_height_spaces", []))
        print(f"   {lab}  n={n}")
        geom[lab] = {"n": n}
        for k in keys:
            v = sorted(f.get(k, []))
            if not v:
                continue
            med = v[len(v) // 2]
            lo, hi = v[int(0.1 * len(v))], v[int(0.9 * len(v))]
            geom[lab][k] = {"median": round(med, 3), "p10": round(lo, 3),
                            "p90": round(hi, 3)}
            print(f"      {k:<26} {med:6.2f}   [{lo:5.2f} .. {hi:5.2f}]")

    a_lab = "STEM PAIR (both carry a notehead)"
    b_lab = "ACCIDENTAL PAIR (neither carries one)"
    print("\n   overlap of the two populations (a cut can only be as good "
          "as this):")
    for k in keys:
        A = sorted(feats[a_lab].get(k, []))
        B = sorted(feats[b_lab].get(k, []))
        if not A or not B:
            continue
        # how well does the best single threshold on this feature split them?
        cuts = sorted(set(A + B))
        best, bestc = 0.0, None
        for c in cuts:
            acc = max(
                (sum(1 for x in A if x > c) + sum(1 for x in B if x <= c)),
                (sum(1 for x in A if x <= c) + sum(1 for x in B if x > c)))
            if acc > best:
                best, bestc = acc, c
        print(f"      {k:<26} best single cut {bestc:5.2f} separates "
              f"{best}/{len(A) + len(B)} = {best / (len(A) + len(B)):.3f}")
        geom.setdefault("best_single_cut", {})[k] = {
            "cut": round(bestc, 3),
            "accuracy": round(best / (len(A) + len(B)), 3)}

    out = {"dropped_total": sum(kind.values()),
           "by_partner": dict(kind),
           "head_bearing_by_partner": dict(kind_head),
           "rescued_by_partner": {k: len(v) for k, v in rescued_by_kind.items()},
           "rescued_total": len(allr),
           "accidental_class": dict(acc_class),
           "restatement_mismatch_cells": mismatch,
           "pair_geometry": geom,
           "dropped_pairs_by_direction": dict(dirs),
           "no_stem_population": len(no_stem)}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
