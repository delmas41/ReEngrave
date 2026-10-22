"""The two key-signature readers, on the SAME header crop, all 18 staves.

`alter_gap.py` reads the RECORD and finds that `Q.KEYSIG_TEMPLATE_FIT` is
right on 18 staves of 18 while the verdict is right on 10 — because
`adjudicate_key_signature` takes the locator's `fitted` answer the moment one
exists and reads the template only into GAPS. That is the record's own account.

This one goes back to the INK and asks what each reader actually saw, so the
failure has a mechanism rather than a name:

    locator  `key_signature_locator.locate_key_signature(crop, clef)` — ink
             components, then `key_signature_geometry.fit_key_signature`
    template `key_signature_template` — Bravura accidental templates slid
             along the same crop

    python3 benchmarks/omr-staged-engraved-2026-09/locator_vs_template.py \
        --pdf out/fixture/<stem>.pdf --page 0 --dpi 300 \
        --truth-xml out/fixture/<stem>.musicxml

⚠️ IT RE-PREPARES THE PAGE. The crops are not on the record — `Q.KEYSIG_*` rows
carry the READINGS, not the pixels — so this rasterises and re-detects staves.
It is therefore a SECOND pass over the same PDF and its staff order must be
checked against the record's, not assumed; the script prints both.

⚠️ THE TRUTH IS THE ENCODING'S `<key><fifths>`, PART BY PART, and the join is
the ordinal one the renderer makes true (every part on every system). The
script REFUSES if the staff count and the part count disagree.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_SLOT_TABLE_CLEFS = ("treble", "bass", "alto", "tenor")


def truth_fifths(xml: Path) -> List[int]:
    root = ET.parse(str(xml)).getroot()
    out = []
    for p in root.findall("{*}part"):
        f = p.find("{*}measure/{*}attributes/{*}key/{*}fifths")
        out.append(int(f.text) if f is not None else None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--truth-xml", type=Path, required=True)
    ap.add_argument("--record", type=Path,
                    help="the staged record, to cross-check the staff order")
    ap.add_argument("--dump-staff", type=int,
                    help="print every cluster of this staff in the x window, "
                         "with the gate that dropped it")
    ap.add_argument("--dump-x", type=int, nargs=2, default=(0, 1200))
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staff_header import header_cells_for_page
    from tools.omr.key_signature_locator import locate_key_signature
    from tools.omr.key_signature_template import read_key_signature

    pages = prepare_pages(str(args.pdf), [args.page], dpi=args.dpi)
    pws, _cells = pages[0]
    crops = header_cells_for_page(pws)
    staves = sorted(pws.staves, key=lambda s: s.staff_index)
    truth = truth_fifths(args.truth_xml)

    print(f"REACH: {len(staves)} staves detected, {len(crops)} header crops, "
          f"{len(truth)} encoded parts")
    if len(staves) != len(truth):
        print("REFUSED: staff count != part count, so the ordinal join is a "
              "guess here and every row below would be unattributable.")
        return 2

    rec_verdict: Dict[int, Any] = {}
    settled_clef: Dict[int, str] = {}
    if args.record:
        rec = json.loads(args.record.read_text())["record"]
        for v in rec["verdicts"]:
            if v.get("outcome") != "decided":
                continue
            if v.get("quantity") == "key_signature":
                rec_verdict[int(v["subject"].split("/")[-1])] = (
                    v.get("value"), v.get("reason"))
            elif v.get("quantity") == "clef":
                settled_clef[int(v["subject"].split("/")[-1])] = str(v.get("value"))

    rows = []
    print(f"\n{'staff':>5s} {'clef':>6s} {'truth':>6s} "
          f"{'locator':>16s} {'template':>12s} {'verdict':>9s}  reason")
    for i, st in enumerate(staves):
        crop = crops.get(st.staff_index)
        loc: Dict[str, Any] = {}
        if crop is not None:
            for cand in _SLOT_TABLE_CLEFS:
                try:
                    found = locate_key_signature(crop, cand)
                except Exception:                              # noqa: BLE001
                    continue
                if found is None:
                    continue
                loc[cand] = {"n": len(found.boxes),
                             "fifths": getattr(found.read, "fifths", None),
                             "accidental": found.accidental}
        tpl = None
        if crop is not None:
            for cand in _SLOT_TABLE_CLEFS:
                try:
                    r = read_key_signature(crop, cand)
                except Exception:                              # noqa: BLE001
                    r = None
                if r is not None:
                    tpl = tpl or {}
                    tpl[cand] = {"n": len(getattr(r, "matched_slots", ()) or ()),
                                 "fifths": getattr(r, "fifths", None)}
        v = rec_verdict.get(i)
        # ⚠️ REPORTED UNDER THE CLEF THE RECORD SETTLED, never under `treble`
        # for everyone. Both readers take the clef as an argument and return a
        # different answer per candidate, so a fixed column compares a bass
        # staff's treble hypothesis with a treble staff's real one — which is
        # what the first version of this table did, printing `-` for every
        # bass and alto staff and reading as "the template found nothing".
        clef = settled_clef.get(i)
        loc_c = loc.get(clef) if clef else None
        tpl_c = (tpl or {}).get(clef) if clef else None
        loc_s = f"{loc_c['fifths']}(n={loc_c['n']})" if loc_c else "-"
        tpl_s = f"{tpl_c['fifths']}(n={tpl_c['n']})" if tpl_c else "-"
        print(f"{i:5d} {str(clef or '?'):>6s} {str(truth[i]):>6s} "
              f"{loc_s:>16s} {tpl_s:>12s} "
              f"{str(v[0]) if v else '-':>9s}  {v[1] if v else ''}")
        rows.append({"staff": i, "clef": clef, "truth": truth[i],
                     "locator": loc, "template": tpl,
                     "locator_at_clef": loc_c, "template_at_clef": tpl_c,
                     "verdict": v[0] if v else None,
                     "verdict_reason": v[1] if v else None})

    print("\nlocator box COUNT per candidate clef, against the flats printed:")
    for r in rows:
        counts = {k: v["n"] for k, v in (r["locator"] or {}).items()}
        print(f"   staff {r['staff']:2d}  truth {str(r['truth']):>3s}  {counts}")

    # ── WHERE the run is lost: ink pass, or the slot fit? ───────────────────
    # ⚠️ The two have DIFFERENT repairs, so a count that does not separate them
    # is not actionable. This re-runs the locator's own pre-fit pass using its
    # OWN helpers (`header_ink_mask`, `cluster_components_2d`) and its own
    # config — nothing is reimplemented — and reports how many
    # accidental-SIZED glyphs stand in the header before any clef, anchor or
    # slot table is applied.
    print("\nthe locator's pre-fit pass — accidental-sized glyphs in the "
          "header, before the anchor and before the slot fit:")
    import numpy as np                                            # noqa: E402
    from tools.omr.key_signature_locator import (                 # noqa: E402
        DEFAULT_LOCATOR_CONFIG as C, DEFAULT_INK_CONFIG as IC)
    from tools.omr.header_ink import (header_ink_mask, cluster_components_2d,
                                      staff_metrics)
    import cv2                                                    # noqa: E402

    for i, st in enumerate(staves):
        crop = crops.get(st.staff_index)
        if crop is None:
            continue
        metrics = staff_metrics(crop)
        if metrics is None:
            continue
        spacing, top_y, bottom_y = metrics
        mask = header_ink_mask(crop, spacing, crop.staff_line_ys_canonical, IC)
        if mask is None:
            continue
        n, _l, stats, _c = cv2.connectedComponentsWithStats(mask, connectivity=8)
        min_area = C.min_component_area_spaces * spacing * spacing
        band = C.staff_band_spaces * spacing
        comps = []
        for j in range(1, n):
            if int(stats[j, cv2.CC_STAT_AREA]) < min_area:
                continue
            y_j, h_j = int(stats[j, cv2.CC_STAT_TOP]), int(stats[j, cv2.CC_STAT_HEIGHT])
            if not (top_y - band <= y_j + h_j / 2.0 <= bottom_y + band):
                continue
            comps.append((int(stats[j, cv2.CC_STAT_LEFT]), y_j,
                          int(stats[j, cv2.CC_STAT_WIDTH]), h_j,
                          int(stats[j, cv2.CC_STAT_AREA])))
        clusters = cluster_components_2d(
            comps, max_gap=C.cluster_gap_spaces * spacing)
        sized = [b for b in clusters
                 if C.min_width_spaces <= b[2] / spacing <= C.max_width_spaces
                 and C.min_height_spaces <= b[3] / spacing <= C.max_height_spaces]
        loc_c = rows[i].get("locator_at_clef")
        print(f"   staff {i:2d} truth {str(truth[i]):>3s}  clusters "
              f"{len(clusters):3d}  accidental-sized {len(sized):2d}  "
              f"run the FIT returned "
              f"{loc_c['n'] if loc_c else '-'}   "
              f"x of sized: {[b[0] for b in sized]}")
        rows[i]["prefit_sized"] = len(sized)
        rows[i]["prefit_clusters"] = len(clusters)
        rows[i]["prefit_sized_x"] = [b[0] for b in sized]
        if args.dump_staff is not None and i == args.dump_staff:
            lo, hi = args.dump_x
            print(f"\n   ── every cluster of staff {i} with x in [{lo}, {hi}] "
                  f"(spacing {spacing:.1f} px) ──")
            print(f"      staff lines (canonical y): "
                  f"{[round(float(v), 1) for v in (crop.staff_line_ys_canonical or [])]}")
            print(f"      {'x':>6s} {'y':>6s} {'w':>6s} {'h':>6s}  "
                  f"{'w_sp':>6s} {'h_sp':>6s}  verdict")
            for b in sorted(clusters):
                if not (lo <= b[0] <= hi):
                    continue
                w_sp, h_sp = b[2] / spacing, b[3] / spacing
                why = []
                if h_sp >= C.clef_min_height_spaces:
                    why.append("clef-tall")
                if w_sp > C.max_width_spaces:
                    why.append(f"w>{C.max_width_spaces}")
                if w_sp < C.min_width_spaces:
                    why.append(f"w<{C.min_width_spaces}")
                if h_sp < C.min_height_spaces:
                    why.append(f"h<{C.min_height_spaces}")
                if h_sp > C.max_height_spaces:
                    why.append(f"h>{C.max_height_spaces}")
                print(f"      {b[0]:6d} {b[1]:6d} {b[2]:6d} {b[3]:6d}  "
                      f"{w_sp:6.2f} {h_sp:6.2f}  "
                      f"{'KEPT' if not why else 'dropped: ' + ','.join(why)}")

    if args.json_out:
        args.json_out.write_text(json.dumps(rows, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
