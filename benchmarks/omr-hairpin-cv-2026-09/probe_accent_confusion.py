#!/usr/bin/env python3
"""Does the CV hairpin reader mistake accent marks for small diminuendo hairpins?

Sean's hypothesis: an accent (`>`) and a diminuendo hairpin (`>`) are the same
shape at different scales. The CV reader (`tools/omr/hairpin_detection.py`)
finds hairpins by isolation + straight-outline shape and calls direction by
which end is wider — an accent glyph would pass both tests and read as a small
diminuendo. The prompting evidence: the reader's damage on the 20-row scan gate
concentrates on `dvorak-sym9-mvt1-405834-p7` (+11 edits, +8 of them
`wrong diminuendo`), on a row that otherwise recovered 70% of its truth
hairpins (FINDINGS.md §8).

This probe reads the ALREADY-COMMITTED `-hpon.omr.json` transcriptions (no
pipeline run) and asks, per row:

  1. does every CV-added hairpin (`detector: "cv"` on the detection) coincide
     in page-pixel space with an `articAccentAbove`/`Below` detection on the
     SAME staff?
  2. is that coincidence concentrated in the diminuendo-classed hairpins?
  3. do the coinciding ("false") hairpins measure smaller (in staff spaces)
     than the non-coinciding ("plausibly real") ones -- i.e. is there a width
     gap a threshold could sit in?

Exits non-zero if it cannot read a fixture, if a row set turns up empty, or if
zero CV hairpins / zero accent detections are found ACROSS THE WHOLE 20-ROW
GATE (a class read as always-zero is this project's most common silent-probe
failure, per CLAUDE.md's "six cases this week"). A single row legitimately
carrying zero of either is reported, not treated as failure.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr import class_aliases  # noqa: E402

FIXTURES_DIR = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/fix-hairpin-wire/"
    "benchmarks/omr-scan-e2e-2026-09/fixtures"
)
RESULTS_ON = Path(__file__).resolve().parent / "results-scan-arm-hpon.json"

ACCENT_CLASSES = {"articAccentAbove", "articAccentBelow", "articulationAccent"}
HAIRPIN_CLASSES = {"dynamicCrescendoHairpin", "dynamicDiminuendoHairpin"}

#: How close a CV hairpin's center must sit to an accent's center to count as
#: "coincides", in staff spaces of the hairpin's own staff. An accent glyph and
#: a genuine short hairpin both run roughly one staff space wide, so this is
#: deliberately tight -- true coincidence, not merely "nearby".
COINCIDE_MAX_SPACES = 1.25


def staff_spacings(page: dict) -> dict[int, float]:
    out = {}
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            g = staff.get("staff_geometry") or {}
            sp = g.get("line_spacing_px")
            if sp:
                out[staff.get("staff_index")] = float(sp)
    return out


def all_detections(page: dict):
    """Yield (staff_index, measure_index, detection_dict) for every detection."""
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            si = staff.get("staff_index")
            for meas in staff.get("measures", []):
                mi = meas.get("measure_index")
                for det in meas.get("detections", []):
                    yield si, mi, det


def center(bbox_page) -> tuple[float, float]:
    x, y, w, h = bbox_page
    return x + w / 2.0, y + h / 2.0


def load_row(row_id: str) -> dict:
    path = FIXTURES_DIR / f"{row_id}.omr.json"
    if not path.is_file():
        raise SystemExit(f"FATAL: fixture missing, cannot measure anything: {path}")
    with path.open() as f:
        data = json.load(f)
    pages = data.get("pages")
    if not pages:
        raise SystemExit(f"FATAL: {path} has no pages -- reads nothing")
    return data


def canon(cls: str | None) -> str:
    return class_aliases.canonical(cls or "")


def measure_row(row_id: str) -> dict:
    data = load_row(row_id)
    page = data["pages"][0]
    spacings = staff_spacings(page)

    cv_hairpins = []
    accents = []
    for si, mi, det in all_detections(page):
        cls = canon(det.get("class"))
        bbox_page = det.get("bbox_page")
        if not bbox_page or len(bbox_page) != 4:
            continue
        if det.get("detector") == "cv" and cls in HAIRPIN_CLASSES:
            cv_hairpins.append({
                "staff": si, "measure": mi, "kind": cls,
                "bbox_page": bbox_page, "confidence": det.get("confidence"),
            })
        elif cls in ACCENT_CLASSES:
            accents.append({
                "staff": si, "measure": mi, "class": cls,
                "bbox_page": bbox_page, "confidence": det.get("confidence"),
            })

    # Cross-check route 2: the top-level counter the exporter itself wrote,
    # against route 1 (filtering detector=="cv" out of the built page dict).
    # They should agree exactly -- attach_to_page's own `added` counter is
    # exactly the detections it appended, and nothing removes a "cv" tag
    # afterwards.
    top_level_added = data.get("n_cv_hairpins_added")

    results = []
    for hp in cv_hairpins:
        sp = spacings.get(hp["staff"])
        cx, cy = center(hp["bbox_page"])
        best = None
        best_dist_sp = None
        for ac in accents:
            if ac["staff"] != hp["staff"]:
                continue
            ac_sp = spacings.get(ac["staff"]) or sp
            if not ac_sp:
                continue
            acx, acy = center(ac["bbox_page"])
            dist_px = math.hypot(cx - acx, cy - acy)
            dist_sp = dist_px / ac_sp
            if best_dist_sp is None or dist_sp < best_dist_sp:
                best_dist_sp = dist_sp
                best = ac
        width_sp = hp["bbox_page"][2] / sp if sp else None
        height_sp = hp["bbox_page"][3] / sp if sp else None
        coincides = best_dist_sp is not None and best_dist_sp <= COINCIDE_MAX_SPACES
        results.append({
            "staff": hp["staff"], "measure": hp["measure"], "kind": hp["kind"],
            "width_sp": width_sp, "height_sp": height_sp,
            "nearest_accent_dist_sp": best_dist_sp,
            "coincides_with_accent": coincides,
            "nearest_accent_class": (best or {}).get("class"),
        })

    return {
        "row_id": row_id,
        "n_cv_hairpins": len(cv_hairpins),
        "n_cv_hairpins_top_level": top_level_added,
        "n_accents": len(accents),
        "n_accents_above": sum(1 for a in accents if a["class"] == "articAccentAbove"),
        "n_accents_below": sum(1 for a in accents if a["class"] == "articAccentBelow"),
        "hairpins": results,
    }


def row_ids_from_results() -> list[str]:
    if not RESULTS_ON.is_file():
        raise SystemExit(f"FATAL: {RESULTS_ON} missing -- cannot enumerate rows")
    with RESULTS_ON.open() as f:
        d = json.load(f)
    rows = d.get("rows") or []
    if not rows:
        raise SystemExit("FATAL: results-scan-arm-hpon.json has an empty row set")
    return [r["row_id"] for r in rows]


def main() -> int:
    row_ids = row_ids_from_results()
    if len(row_ids) != 20:
        raise SystemExit(f"FATAL: expected the 20-row scan gate, got {len(row_ids)}")

    per_row = [measure_row(rid) for rid in row_ids]

    total_cv = sum(r["n_cv_hairpins"] for r in per_row)
    total_accents = sum(r["n_accents"] for r in per_row)
    if total_cv == 0:
        raise SystemExit("FATAL: zero CV hairpins found across all 20 rows -- probe reads nothing")
    if total_accents == 0:
        raise SystemExit("FATAL: zero accent detections found across all 20 rows -- probe reads nothing")

    # Cross-check route 1 vs route 2 (the exporter's own counter).
    mismatches = [
        (r["row_id"], r["n_cv_hairpins"], r["n_cv_hairpins_top_level"])
        for r in per_row
        if r["n_cv_hairpins_top_level"] is not None
        and r["n_cv_hairpins"] != r["n_cv_hairpins_top_level"]
    ]

    out = {
        "coincide_threshold_staff_spaces": COINCIDE_MAX_SPACES,
        "total_cv_hairpins": total_cv,
        "total_accents": total_accents,
        "cross_check_mismatches": mismatches,
        "rows": per_row,
    }
    out_path = Path(__file__).resolve().parent / "accent_confusion_result.json"
    out_path.write_text(json.dumps(out, indent=2))

    # ---- console summary ----
    print(f"{'row':45s} {'cv_hp':>6} {'accents':>8} {'coincide':>9} {'dim':>5} {'dim_coin':>9}")
    for r in per_row:
        hp = r["hairpins"]
        dim = [h for h in hp if h["kind"] == "dynamicDiminuendoHairpin"]
        dim_coin = [h for h in dim if h["coincides_with_accent"]]
        coin = [h for h in hp if h["coincides_with_accent"]]
        print(f"{r['row_id']:45s} {r['n_cv_hairpins']:6d} {r['n_accents']:8d} "
              f"{len(coin):9d} {len(dim):5d} {len(dim_coin):9d}")

    print()
    print(f"total CV hairpins: {total_cv}, total accent detections: {total_accents}")
    print(f"cross-check (route1 vs top-level counter) mismatches: {len(mismatches)}")
    for m in mismatches:
        print(f"  MISMATCH {m[0]}: filtered={m[1]} top_level={m[2]}")

    all_hp = [h for r in per_row for h in r["hairpins"]]
    coincide = [h for h in all_hp if h["coincides_with_accent"]]
    non_coincide = [h for h in all_hp if not h["coincides_with_accent"]]
    print()
    print(f"ALL ROWS: {len(all_hp)} CV hairpins, {len(coincide)} coincide with an accent "
          f"({len(coincide)/len(all_hp)*100:.1f}%)")
    dim = [h for h in all_hp if h["kind"] == "dynamicDiminuendoHairpin"]
    dim_coin = [h for h in dim if h["coincides_with_accent"]]
    cre = [h for h in all_hp if h["kind"] == "dynamicCrescendoHairpin"]
    cre_coin = [h for h in cre if h["coincides_with_accent"]]
    if dim:
        print(f"  diminuendo: {len(dim)} total, {len(dim_coin)} coincide "
              f"({len(dim_coin)/len(dim)*100:.1f}%)")
    if cre:
        print(f"  crescendo:  {len(cre)} total, {len(cre_coin)} coincide "
              f"({len(cre_coin)/len(cre)*100:.1f}%)")

    def stats(vals):
        vals = sorted(v for v in vals if v is not None)
        if not vals:
            return "n=0"
        n = len(vals)
        p50 = vals[n // 2]
        return f"n={n} min={vals[0]:.2f} p50={p50:.2f} max={vals[-1]:.2f}"

    print()
    print("width_sp (coincide-with-accent, i.e. 'false'):",
          stats([h["width_sp"] for h in coincide]))
    print("width_sp (no accent nearby, i.e. 'plausibly real'):",
          stats([h["width_sp"] for h in non_coincide]))

    print()
    print("=== dvorak-sym9-mvt1-405834-p7 detail ===")
    p7 = next(r for r in per_row if r["row_id"] == "dvorak-sym9-mvt1-405834-p7.-hpon")
    print(f"n_cv_hairpins={p7['n_cv_hairpins']} n_accents={p7['n_accents']} "
          f"(above={p7['n_accents_above']}, below={p7['n_accents_below']})")
    for h in p7["hairpins"]:
        print(f"  staff={h['staff']} meas={h['measure']} kind={h['kind']:26s} "
              f"width_sp={h['width_sp']:.2f} nearest_accent_dist_sp="
              f"{h['nearest_accent_dist_sp']!r} coincides={h['coincides_with_accent']} "
              f"nearest_class={h['nearest_accent_class']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
