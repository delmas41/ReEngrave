"""REACH: how much of the page could the misread-whole-rest fault be, and does
anything separate it from real music WITHOUT deleting real music?

⚠️ REACH BEFORE ACCURACY. The lone-quarter-in-2/4 window is one view of the
fault and not its size: a whole rest misnamed a notehead can also land in a bar
that holds other ink, and can be exported as a HALF note (which in 2/4 fills the
bar and so never shows up as underfull at all).

Three candidate witnesses are scored against the 26-bar HAND-ADJUDICATED set
(`--truth`), because a cut read off the suspects alone is a cut fitted to them:

  SHAPE     the ink's own height and aspect in staff spaces
  SLOT      its staff step against 5.5, where an engraver must hang a whole rest
  NEIGHBOUR whether the SAME STAFF holds a detected `restWhole` in a nearby bar
            at nearly the same height -- a tacet part prints one in EVERY bar,
            so this is a different bar's ink rather than a second opinion about
            the same ink

⚠️ NEIGHBOUR is not independent of the detector; it is independent of THIS
GLYPH. That is a weaker claim than CLAUDE.md's "must not come off the same
raster" and it is the strongest available here, so it is stated rather than
dressed up.

    python3 .../reach.py --cache cache.json --trace trace.json --truth T.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def _k(subject, n):
    return tuple(int(x) for x in subject.split("/")[1:1 + n])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--neighbour-bars", type=int, default=2)
    ap.add_argument("--neighbour-steps", type=float, default=1.5)
    ap.add_argument("--json")
    a = ap.parse_args()

    c = json.load(open(a.cache))
    box, cls, rest, conf, lines, spacing = {}, {}, {}, {}, {}, {}
    for o in c["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                box[s] = pb
        elif q == "notehead_class":
            cls[s] = o["value"]
        elif q == "rest":
            rest[s] = o["value"]
        elif q == "glyph_conf":
            conf[s] = o.get("score")
        elif q == "staff_lines":
            lines[_k(s, 3)] = o["value"]
        elif q == "staff_spacing":
            spacing[_k(s, 3)] = o["value"]

    def geom(sub):
        pb, k = box.get(sub), _k(sub, 3)
        ly, sp = lines.get(k), spacing.get(k)
        if not pb or not ly or not sp:
            return None
        h, w = (pb[3] - pb[1]) / sp, (pb[2] - pb[0]) / sp
        if h <= 0:
            return None
        return h, w / h, (max(ly) - (pb[1] + pb[3]) / 2.0) / (sp / 2.0)

    heads = [s for s in cls if s in box]
    wr = [s for s in rest if s in box
          and str(rest[s]).lower().startswith("restwhole")]
    print("=== POSITIVE CONTROL ===")
    print(f"  noteheads with a page box   {len(heads)}")
    print(f"  restWhole with a page box   {len(wr)}")
    if not heads or not wr:
        print("DEAD INSTRUMENT", file=sys.stderr)
        return 2

    # the document's own whole rests, as the shape band
    rg = [g for s in wr if (g := geom(s))]
    hs = sorted(g[0] for g in rg)
    asps = sorted(g[1] for g in rg)
    q = lambda v, f: v[min(len(v) - 1, int(f * len(v)))]
    print(f"  restWhole height  p05 {q(hs, .05):.3f}  p95 {q(hs, .95):.3f}")
    print(f"  restWhole aspect  p05 {q(asps, .05):.3f}  p95 {q(asps, .95):.3f}")
    print()

    # NEIGHBOUR index: per staff, the whole rests by cell and step
    by_staff = collections.defaultdict(list)
    for s in wr:
        g = geom(s)
        if g:
            by_staff[_k(s, 3)].append((int(s.split("/")[4]), g[2]))

    def neighbour(sub):
        g = geom(sub)
        if not g:
            return None
        cell = int(sub.split("/")[4])
        for c2, step2 in by_staff.get(_k(sub, 3), ()):
            if (abs(c2 - cell) <= a.neighbour_bars
                    and abs(step2 - g[2]) <= a.neighbour_steps):
                return (c2, round(step2, 2))
        return None

    # cells that hold exactly one notehead and no rest at all
    per_cell_heads = collections.Counter(_k(s, 5) for s in heads)
    per_cell_rest = collections.Counter(_k(s, 5) for s in rest if s in box)

    truth = json.load(open(a.truth))
    label = {t["subject"]: t["verdict"] for t in truth}
    print(f"=== the hand-adjudicated set ({len(label)} crops looked at) ===")
    print("  ", dict(collections.Counter(label.values())))
    print()

    rows = []
    for s in heads:
        g = geom(s)
        if not g:
            continue
        h, asp, step = g
        rows.append({
            "subject": s, "height": round(h, 3), "aspect": round(asp, 3),
            "step": round(step, 2), "conf": conf.get(s),
            # ⚠️ The aspect band is TWO-SIDED and both edges are the same
            # percentile of the document's OWN whole rests, not a number
            # chosen to fit the suspects. A one-sided band admitted a 5.49
            # sliver of line residue, which is not a whole rest either -- and
            # a decision may only claim what it can support.
            "shape": bool(h <= q(hs, .95)
                          and q(asps, .05) <= asp <= q(asps, .95)),
            "slot": abs(step - 5.5) <= 1.0,
            "neighbour": neighbour(s),
            "alone_in_bar": (per_cell_heads[_k(s, 5)] == 1
                             and per_cell_rest[_k(s, 5)] == 0),
            "truth": label.get(s),
        })

    def rule(r, want):
        return all(bool(r[k]) for k in want)

    print("=== WITNESSES over ALL noteheads, and on the adjudicated set ===")
    print(f"  {'rule':<34} {'fires':>6}  {'rest':>5} {'note':>5} {'junk':>5}  "
          f"{'precision on the 26':>20}")
    combos = [("shape",), ("slot",), ("neighbour",), ("alone_in_bar",),
              ("shape", "slot"), ("shape", "neighbour"),
              ("shape", "alone_in_bar"),
              ("shape", "slot", "neighbour"),
              ("shape", "neighbour", "alone_in_bar"),
              ("shape", "slot", "alone_in_bar")]
    for want in combos:
        fires = [r for r in rows if rule(r, want)]
        adj = [r for r in fires if r["truth"]]
        n = collections.Counter(r["truth"] for r in adj)
        prec = (f"{n['whole_rest']}/{len(adj)}" if adj else "-")
        print(f"  {'+'.join(want):<34} {len(fires):>6}  "
              f"{n['whole_rest']:>5} {n['notehead']:>5} {n['junk']:>5}  "
              f"{prec:>20}")
    print()
    print("  (rest/note/junk are the hand verdicts among the ones it fires on;")
    print("   a rule firing on a 'notehead' row would DELETE A REAL NOTE.)")
    print()

    print("=== the adjudicated rows, with every witness ===")
    for r in sorted((r for r in rows if r["truth"]),
                    key=lambda r: (r["truth"], r["subject"])):
        print(f"  {r['truth']:<11} h={r['height']:5.2f} asp={r['aspect']:6.2f} "
              f"step={r['step']:+6.2f} conf={r['conf']:.2f} "
              f"shape={int(r['shape'])} slot={int(r['slot'])} "
              f"alone={int(r['alone_in_bar'])} "
              f"nb={r['neighbour']}  {r['subject']}")

    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print(f"\nwrote {len(rows)} rows -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
