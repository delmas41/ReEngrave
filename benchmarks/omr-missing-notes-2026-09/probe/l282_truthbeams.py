#!/usr/bin/env python3
"""l282_truthbeams: every `Q.BEAM_STROKE` stroke in Sean's FULLY LABELED cells of Brahms 317803
pdf page 0, set against his boxes -- is it a beam (a truth `beam` box), or what else (a slur,
a tie, a ledger line, a stem, a head, nothing he boxed) -- with its `Q.BEAM_STROKE_INK`
reading. ROADMAP 2.82. A reading probe: it decides nothing and changes no product code.

SOURCE. `data/hand-truth/pages/imslp317803/0.json` read through `tools.omr.hand_truth.store.load`
(never written) and the strokes of a record, extracted by `l282_extract.py`.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (rule 3):
  * a stroke is a REAL BEAM where a truth `beam` box of Sean's is covered by it by half or more
    (its own area may be larger: a detector box draws a stack) -- falsified by a crop showing the
    stroke is something else; `--crops` cuts them;
  * a stroke in a fully labeled cell that covers NO truth beam is NOT a beam by his page (every
    ink in an `all-ink` cell is boxed or deliberately left): classified by the truth class it
    covers most of (slur, tie, ledgerLine, stem, notehead, ...), else `unboxed ink`;
  * a stroke is judged in the cell it was FILED in (centre inside that cell's own rectangle), so
    a beam seen again in a neighbour's padding is not counted twice.

    python3 l282_truthbeams.py --ext ext.json [--json out.json] [--ratio-min 1.75]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_truth import Truth  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402

PAGE = 0
CLASSES = ("slur", "tie", "ledger_line", "stem", "notehead", "flag", "tremolo", "beam",
           "augmentation_dot", "rest", "accidental", "dynamic")


def area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def inter(a, b):
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def build_rows(ext, T):
    bands = S.staff_bands(T.page)
    by_cell = {}
    for c in T.page.cells:
        if c.kind == "measure" and c.system is not None:
            by_cell[(c.system, c.staff, c.measure or 0)] = c
    full_ids = {c.id for c in T.full}
    band_of = {}
    for b in bands:
        band_of[b.cell_id] = b
    rows = []
    for ck, strokes in ext["strokes"].items():
        p = ck.split("/")
        if int(p[1]) != PAGE:
            continue
        sys_, st, m = int(p[2]), int(p[3]), int(p[4])
        cell = by_cell.get((sys_, st, m))
        calib = ext["calib"].get(ck)
        if cell is None or calib is None or cell.id not in full_ids:
            continue
        x0, y0, up = calib[0], calib[1], calib[2]
        for sid, s in strokes.items():
            bx, by, bw, bh = s["box"][:4]
            pb = (x0 + bx / up, y0 + by / up, x0 + (bx + bw) / up, y0 + (by + bh) / up)
            cx, cy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
            if not (cell.rect[0] <= cx < cell.rect[2] and cell.rect[1] <= cy < cell.rect[3]):
                continue
            ink = ext["ink"].get(sid)
            ab = ext["ink_abs"].get(sid)
            row = {"id": sid, "cell": ck, "truth_cell": cell.id, "reader": s["reader"],
                   "page_box": [round(v, 1) for v in pb],
                   "w_px": round(pb[2] - pb[0], 1), "h_px": round(pb[3] - pb[1], 1)}
            if ink:
                row.update(ratio=ink["thickness_ratio"], thick_px=ink["thickness_px"],
                           line_px=ink["line_px"], thick_sp=ink["thickness_spaces"],
                           sag=ink["sagitta_spaces"], cover=ink["cover"],
                           ends=[bool(e.get("found")) for e in (ink["end_stems"] or [])],
                           band=ink["band"], core=ink.get("core"))
                from tools.omr.staged.adjudicators import rhythm as _rh
                row["thin_old"] = ink["thickness_ratio"] is not None and ink["thickness_ratio"] < 1.75
                sp_c = float(ext.get("space", {}).get(ck) or 100.0)
                heads_c = [tuple(h) for h in ext.get("heads", {}).get(ck, [])
                           if h[2] <= _rh.BEAM_HEAD_BOX_MAX_SPACES * sp_c]
                # the rule as built: the core must stand on a stem at each end that leads to a detector-boxed head
                # (canonical frame, the unit the record's own `Q.CELL_STAFF_SPACE` gives)
                row["thin_new"] = _rh.stroke_thin_by_ink({"thickness_ratio": ink["thickness_ratio"],
                                                          "core": ink.get("core")}, heads_c, sp_c)
            else:
                row.update(ratio=None, ink_abs=(ab or {}).get("reason", "no row"))
            band = band_of.get(cell.id)
            # staff-line contact: page lines of THIS cell's staff that pass through the stroke's
            # measured band (else its box)
            if band and ink and ink.get("band"):
                t, b = y0 + ink["band"][0] / up, y0 + ink["band"][1] / up
            else:
                t, b = pb[1], pb[3]
            row["lines_through"] = (sum(1 for ly in band.lines if t - 1 <= ly <= b + 1)
                                    if band else None)
            row["space_px"] = round(band.space, 2) if band else None
            # truth overlaps
            cov = {}
            for it in T.items:
                if it.family not in CLASSES and it.cls not in CLASSES:
                    continue
                fam = it.family if it.family in CLASSES else it.cls
                a = inter(pb, it.rect)
                if a <= 0:
                    continue
                v = (a / max(1e-6, area(pb)), a / max(1e-6, area(it.rect)), it.id)
                if fam not in cov or v[0] > cov[fam][0]:
                    cov[fam] = v
            row["cov"] = {k: [round(v[0], 2), round(v[1], 2), v[2]] for k, v in cov.items()}
            tb = cov.get("beam")
            row["is_beam"] = bool(tb and (tb[1] >= 0.5))
            if row["is_beam"]:
                row["label"] = "beam"
            else:
                best = max(((v[0], k) for k, v in cov.items() if k != "beam"), default=(0, None))
                row["label"] = best[1] if best[0] >= 0.3 else "unboxed ink / none"
            rows.append(row)
    return rows


BUCKETS = [0, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 99]


def hist(vals):
    c = collections.Counter()
    for v in vals:
        for lo, hi in zip(BUCKETS, BUCKETS[1:]):
            if lo <= v < hi:
                c[(lo, hi)] += 1
                break
    return c


def fmt_hist(vals):
    c = hist(vals)
    return "  ".join(f"[{lo:g},{hi:g}):{c.get((lo, hi), 0)}" for lo, hi in zip(BUCKETS, BUCKETS[1:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--ratio-min", type=float, default=1.75)
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    T = Truth()
    rows = build_rows(ext, T)
    print(f"strokes filed in fully labeled cells of page {PAGE}: {len(rows)}")
    print("by reader:", dict(collections.Counter(r["reader"] for r in rows)))
    print("by label:", dict(collections.Counter(r["label"] for r in rows)))
    unmeasured = [r for r in rows if r["ratio"] is None]
    print(f"ink reading missing: {len(unmeasured)}", dict(collections.Counter(
        (r["label"], r.get("ink_abs")) for r in unmeasured)))
    print()
    for reader in ("cv_beam", "detector", None):
        sel = [r for r in rows if r["ratio"] is not None and (reader is None or r["reader"] == reader)]
        if not sel:
            continue
        print(f"== thickness_ratio histogram, reader={reader or 'ALL'} ==")
        print("  REAL BEAM  (n=%d): %s" % (sum(r["is_beam"] for r in sel),
                                          fmt_hist([r["ratio"] for r in sel if r["is_beam"]])))
        for lab in sorted({r["label"] for r in sel if not r["is_beam"]}):
            v = [r["ratio"] for r in sel if not r["is_beam"] and r["label"] == lab]
            print(f"  not-beam {lab:20s}(n={len(v)}): {fmt_hist(v)}")
        v = [r["ratio"] for r in sel if not r["is_beam"]]
        print(f"  NOT A BEAM (n={len(v)}): {fmt_hist(v)}")
        print()
    # raw thickness in spaces too, since the ratio's denominator is the suspect
    print("== thickness in staff SPACES (denominator-free) ==")
    for lab, sel in (("REAL BEAM", [r for r in rows if r["is_beam"] and r["ratio"] is not None]),
                     ("NOT A BEAM", [r for r in rows if not r["is_beam"] and r["ratio"] is not None])):
        v = sorted(r["thick_sp"] for r in sel)
        if v:
            q = lambda f: v[min(len(v) - 1, int(f * (len(v) - 1)))]
            print(f"  {lab:11s} n={len(v)} min {v[0]:.2f} p10 {q(.1):.2f} p25 {q(.25):.2f} med {q(.5):.2f} "
                  f"p75 {q(.75):.2f} p90 {q(.9):.2f} max {v[-1]:.2f}")
    print("== line_px / space_px (the denominator, in spaces) ==")
    v = sorted(r["line_px"] / r["space_px"] for r in rows if r.get("line_px") and r.get("space_px"))
    print(f"  all measured strokes n={len(v)} min {v[0]:.3f} med {v[len(v)//2]:.3f} max {v[-1]:.3f}")
    print()
    # truth beams one by one
    print("== every truth beam in the scored cells: the strokes that cover it ==")
    tb = [i for i in T.beams if S.Scope(T.full).holds(i.rect)]
    print(f"  truth beams in fully labeled cells: {len(tb)}")
    out_tb = []
    for it in sorted(tb, key=lambda i: (i.rect[1], i.rect[0])):
        cand = []
        for r in rows:
            c = r["cov"].get("beam")
            if c and c[2] == it.id:
                cand.append(r)
        # also strokes whose beam cover points at another truth beam but overlap this one
        cand.sort(key=lambda r: -r["cov"]["beam"][1])
        best = cand[0] if cand else None
        rec = {"truth_id": it.id, "rect": [round(v, 1) for v in it.rect],
               "w_px": round(it.rect[2] - it.rect[0], 1), "h_px": round(it.rect[3] - it.rect[1], 1),
               "n_strokes": len(cand),
               "strokes": [{k: r.get(k) for k in ("id", "reader", "ratio", "thick_px", "line_px", "thick_sp",
                                                  "sag", "ends", "lines_through", "w_px", "h_px")}
                           | {"cover_of_truth": r["cov"]["beam"][1]} for r in cand]}
        out_tb.append(rec)
        if best is None:
            print(f"  {it.id} {rec['w_px']:.0f}x{rec['h_px']:.0f}: NO STROKE COVERS IT")
            continue
        refused_all = all((s["ratio"] is not None and s["ratio"] < a.ratio_min) for s in rec["strokes"]
                          if s["ratio"] is not None) and any(s["ratio"] is not None for s in rec["strokes"])
        for s in rec["strokes"][:4]:
            print(f"  {it.id} {rec['w_px']:.0f}x{rec['h_px']:.0f}  {s['reader']:8s} ratio={s['ratio']} "
                  f"thick={s['thick_px']}px line={s['line_px']}px ({s['thick_sp']} sp) sag={s['sag']} "
                  f"ends={s['ends']} lines_through={s['lines_through']} cover_of_truth={s['cover_of_truth']}"
                  + ("   <- REFUSED too_thin" if s["ratio"] is not None and s["ratio"] < a.ratio_min else ""))
    n_lost = 0
    n_none = 0
    n_kept = 0
    for rec in out_tb:
        ratios = [s["ratio"] for s in rec["strokes"] if s["ratio"] is not None]
        if not rec["strokes"]:
            n_none += 1
        elif any(r >= a.ratio_min for r in ratios) or not ratios:
            n_kept += 1
        else:
            n_lost += 1
    print(f"\n  truth beams: {len(out_tb)}; kept by >= 1 stroke at ratio >= {a.ratio_min} (or unmeasured): {n_kept}; "
          f"EVERY covering stroke refused too_thin: {n_lost}; no stroke covers: {n_none}")
    # ---- the beam-level table: kept / refused by the THICKNESS test, before (2.74) and after (2.82) ----
    rowby = {r["id"]: r for r in rows}
    st = collections.Counter()
    print("\n== per truth beam: is a covering stroke KEPT by the thickness test? (a stroke 'covers' a truth beam "
          "when it covers >= 0.5 of it) ==")
    print("   truth beam   covering strokes (reader ratio core)                          before(2.74)  after(2.82)")
    for rec in out_tb:
        cov = [rowby[s["id"]] for s in rec["strokes"] if s["cover_of_truth"] >= 0.5 and rowby[s["id"]].get("ratio") is not None]
        if not cov:
            old = new = "no stroke"
        else:
            old = "KEPT" if any(not r["thin_old"] for r in cov) else "refused too_thin"
            new = "KEPT" if any(not r["thin_new"] for r in cov) else "refused too_thin"
        st[(old, new)] += 1
        desc = "; ".join(f"{r['reader'][:3]} {r['ratio']}" + (f" core {r['core']['spaces']:.1f}sp "
                         f"{[(e['found'], e.get('through')) for e in r['core']['end_stems']]}" if r.get("core") else "")
                         for r in cov) or "-"
        print(f"   {rec['truth_id']:8s} {rec['w_px']:.0f}x{rec['h_px']:.0f}  {desc[:78]:78s} {old:16s} {new}")
    print("   before -> after:", dict(st))
    if a.json:
        Path(a.json).write_text(json.dumps({"rows": rows, "truth_beams": out_tb}, separators=(",", ":"),
                                           default=str))


if __name__ == "__main__":
    main()
