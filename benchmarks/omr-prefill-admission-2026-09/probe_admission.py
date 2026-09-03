"""Per-box admission analysis for the MXL pre-fill, on human-scored cells.

Turns the single --score precision into a precision/coverage table over
candidate ADMISSION policies, using per-box signals the pre-fill already
computes (or can derive from what it holds):

  - `near`           the alignment paired this box one step off (weight-1 LCS)
  - `strength_exact` the cell's share of exactly-positioned matches
  - `small`          box is < 0.85x the cell's own median notehead in BOTH
                     dimensions (the grace-note geometry from the measured
                     handoff: 41x38 / 44x45 vs 51-83 x 47-68 neighbours)
  - parity           whether the cell's exact-correct boxes agree on ONE
                     mapping between the reference note's diatonic parity and
                     the printed on-line/in-space variant; a cell that cannot
                     agree is a cell whose pairing is suspect

It recomputes the pre-fill LIVE through mxl_verdicts' own functions and
replicates score_cell's greedy IoU matching per box, so the pooled numbers
must match a live --score run of the same cells.  Read-only.

Run from the repo root:
    python3 benchmarks/omr-prefill-admission-2026-09/probe_admission.py
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.training import mxl_verdicts as mv  # noqa: E402

DEFAULT_BENCH = REPO / "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1"
# The six cells Sean labeled COMPLETELY (every symbol) on 2026-09-03 — the
# only cells a widened --score may honestly compare against.
COMPLETION_CELLS = [
    "brahms1-p2-sys0-s3-m4", "brahms1-p2-sys0-s9-m0", "brahms1-p3-sys0-s5-m5",
    "brahms1-p3-sys0-s9-m1", "brahms1-p4-sys0-s0-m3", "brahms1-p4-sys0-s10-m5",
]
SMALL_RATIO = 0.85


def diatonic_parity(pitch: str | None) -> int | None:
    m = re.match(r"^([A-G])[#b\-]*(-?\d+)$", pitch or "")
    if not m:
        return None
    return ("CDEFGAB".index(m.group(1)) + 7 * int(m.group(2))) % 2


def variant(cls: str | None) -> int | None:
    if not cls:
        return None
    if "OnLine" in cls:
        return 0
    if "InSpace" in cls:
        return 1
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bench-dir", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--cells", nargs="*", default=COMPLETION_CELLS)
    ap.add_argument("--transcription", type=Path, default=None,
                    help="the reading to score (default: the batch's own). Which "
                         "boxes exist to be scored moves with the weights — see "
                         "FINDINGS.md 'Phase B' — so score against the same "
                         "reading a sample was registered against.")
    ap.add_argument("--inspected-for", default=None, metavar="PASS",
                    help="skip cells whose verdict does not record this pass in "
                         "inspected_passes. ⚠️ Use it whenever the cell list may "
                         "contain cells that were only swept for a NARROWER pass: "
                         "their verdicts hold that pass's boxes and nothing else, "
                         "so scoring every class against them charges each "
                         "correctly pre-filled box of another kind as a false "
                         "positive — the same trap mxl_verdicts refuses outright.")
    args = ap.parse_args()
    bench = args.bench_dir

    tpath = args.transcription or (bench / "transcription.json")
    transcription = json.loads(tpath.read_text())
    truth = mv.load_truth(bench / "reference.mxl")
    windows = mv.load_windows(bench / "windows.json")
    manifest = {e["cell_id"]: e for e in json.loads((bench / "cells.json").read_text())}
    ctx_by_key = mv.index_transcription(transcription)

    rows: list[dict] = []
    skipped: list[str] = []
    for cid in args.cells:
        if args.inspected_for:
            vp = bench / "verdicts" / f"{cid}.verdict.json"
            state = json.loads(vp.read_text()) if vp.exists() else {}
            if args.inspected_for not in (state.get("inspected_passes") or []):
                skipped.append(cid)
                continue
        entry = manifest[cid]
        key = (entry.get("page"), entry.get("system_index"),
               entry.get("staff_index"), entry.get("measure_index"))
        ctx = ctx_by_key.get(key)
        wrow = windows.get(int(entry.get("page", -1)))
        dp = bench / "detections" / f"{cid}.json"
        dets = json.loads(dp.read_text()).get("detections", []) if dp.exists() else []
        cp = mv.prefill_cell(entry, ctx, wrow, truth, dets)
        existing = json.loads((bench / "verdicts" / f"{cid}.verdict.json").read_text())

        human = mv._human_boxes(existing)
        pre = mv._prefill_boxes(cp)
        salign = cp.alignment or {}
        med_w = statistics.median([d["bbox"]["w"] for d in cp.decisions]) if cp.decisions else 0
        med_h = statistics.median([d["bbox"]["h"] for d in cp.decisions]) if cp.decisions else 0

        cell_rows: list[dict] = []
        used: set[int] = set()
        for j, p in enumerate(pre):
            best, best_i = 0.0, None
            for i, h in enumerate(human):
                if i in used:
                    continue
                v = mv.iou(p["bbox"], h["bbox"])
                if v >= mv.DEFAULT_MIN_IOU and v > best:
                    best, best_i = v, i
            matched = best_i is not None
            if matched:
                used.add(best_i)
            d = cp.decisions[j]
            hcls = human[best_i]["class"] if matched else None
            cell_rows.append({
                "cell": cid, "i": j, "verdict": d.get("verdict"),
                "class": d.get("class"), "near": bool(d.get("near")),
                "truth_pitch": (d.get("truth") or {}).get("pitch"),
                "small": bool(med_w and d["bbox"]["w"] < SMALL_RATIO * med_w
                              and d["bbox"]["h"] < SMALL_RATIO * med_h),
                "strength_exact": salign.get("strength_exact"),
                "matched": matched, "iou": round(best, 2), "human_class": hcls,
                "exact": matched and hcls == p["class"],
                "kind": matched and mv._kind(hcls) == mv._kind(p["class"]),
            })

        # Parity calibration on this cell's exact-correct boxes: does ONE
        # offset map reference diatonic parity onto the printed variant?
        offsets = set()
        for r in cell_rows:
            if r["exact"] and variant(r["human_class"]) is not None:
                dp_ = diatonic_parity(r["truth_pitch"])
                if dp_ is not None:
                    offsets.add(dp_ ^ variant(r["human_class"]))
        consistent = len(offsets) == 1
        off = next(iter(offsets)) if consistent else None
        for r in cell_rows:
            r["parity_consistent"] = consistent
            dp_ = diatonic_parity(r["truth_pitch"])
            fixed = False
            if consistent and not r["exact"] and r["matched"] and dp_ is not None:
                want_var = "OnLine" if (dp_ ^ off) == 0 else "InSpace"
                have_var = "OnLine" if variant(r["class"]) == 0 else "InSpace"
                rederived = (r["class"] or "").replace(have_var, want_var)
                # Only a fix if the variant was the WHOLE difference — a grace
                # head stays wrong (the Small qualifier is not the variant's).
                fixed = rederived == r["human_class"]
            r["ref_variant_fixes"] = fixed
        rows.extend(cell_rows)

    n = len(rows)
    ex = sum(1 for r in rows if r["exact"])
    kd = sum(1 for r in rows if r["kind"])
    if skipped:
        print(f"skipped {len(skipped)} cell(s) not swept for {args.inspected_for!r}: "
              + ", ".join(skipped))
    if not rows:
        print("no cells to score — every cell given was skipped or holds no pre-fill.")
        return 0
    print(f"reproduction: prefill={n} exact={ex} kind={kd} "
          f"(recorded 2026-09-03 BEFORE the reference-variant fix: 50 / 42 / 47; "
          f"44 exact once it landed)")
    print()
    print("errors (not exact):")
    for r in rows:
        if not r["exact"]:
            tag = ("UNMATCHED" if not r["matched"]
                   else "kind-ok " + ("REF-VARIANT-FIXES" if r["ref_variant_fixes"] else ""))
            print(f"  {r['cell']:28} #{r['i']:>2} near={int(r['near'])} small={int(r['small'])} "
                  f"strX={r['strength_exact']} parity_ok={int(r['parity_consistent'])} "
                  f"iou={r['iou']:.2f} {r['class']} vs {r['human_class']}  {tag}")
    print()

    def policy(name, keep, fix_variant=False):
        sel = [r for r in rows if keep(r)]
        if not sel:
            print(f"  {name:58} n=0")
            return
        good = sum(1 for r in sel if r["exact"] or (fix_variant and r["ref_variant_fixes"]))
        print(f"  {name:58} n={len(sel):>3} cov={len(sel)/n:.2f}  "
              f"exact={good}/{len(sel)}={good/len(sel):.3f}")

    print("admission policies (precision/coverage over the same boxes):")
    policy("P0 admit everything (the recorded 0.84)", lambda r: True)
    policy("P1 exact-position matches only (near=False)", lambda r: not r["near"])
    policy("P4 cell strength_exact >= 0.75", lambda r: (r["strength_exact"] or 0) >= 0.75)
    policy("P5 cell strength_exact >= 0.9", lambda r: (r["strength_exact"] or 0) >= 0.9)
    policy("S  size veto only (defer small heads)", lambda r: not r["small"])
    policy("C  parity-consistent cells only", lambda r: r["parity_consistent"])
    policy("V  everything, variant re-derived from the reference",
           lambda r: True, fix_variant=True)
    policy("P7 composite: matched + parity-consistent + not small + ref-variant",
           lambda r: r["matched"] and r["parity_consistent"] and not r["small"],
           fix_variant=True)
    print()
    print("size-veto cost (small but exact-correct):",
          sum(1 for r in rows if r["small"] and r["exact"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
