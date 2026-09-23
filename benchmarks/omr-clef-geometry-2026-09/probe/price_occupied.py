#!/usr/bin/env python3
"""ROADMAP 2.11, step 1 — price the `occupied` clef abstention OFF THE RECORDS.

Read-only. No gather, no crop, no `tools/` edit. It answers, per acceptance
document:

  * what height (in staff spaces) a SUCCESSFULLY located clef actually has,
    per family — the MEASURED band, so the change's gate is not the roadmap's
    prose guess (`alto ~= 4-4.5`, `bass ~= 3.5-4`, `treble ~= 7-8`);
  * how many `clef_located` abstentions ended on the `occupied` branch;
  * of those, how many carry a cluster INSIDE the measured band;
  * which detector class occupied the cluster (see the ⚠️ below — the answer
    is structurally "notehead", and the probe proves it rather than asserting
    it);
  * what the same SYSTEM's other staves read for a clef, and the spread of
    their `x_center` against the cluster's own x — Sean's x-consistency check;
  * whether the staff's `clef` verdict ended DECIDED (some other rung carried
    it) or ABSTAINED (2.11 is the only thing that could).

⚠️ "WHICH CLASS OCCUPIED" IS NOT AN OPEN QUESTION IN THE CODE, AND THE PROBE
SAYS SO RATHER THAN PRETENDING TO DISCOVER IT. `gather._occupied_boxes` keeps
ONLY `d.smufl_name.startswith("notehead")` (`gather.py:2180`), so every box
that can ever veto is already notehead-class. The probe still reports the
class of the overlapping boxes, because that is the fact the CHANGE is allowed
to act on and it must come from the record, not from reading the filter.

⚠️ THE OVERLAP HERE IS AN APPROXIMATION AND THE REAL TEST IS NOT.
`locate_clef` compares cluster and occupied box in ANALYSIS space, having
scaled the boxes by that crop's own canonical spacing. The record keeps the
cluster in staff spaces (`detail.clusters`) and the boxes in cell-0 CANONICAL
pixels (`Q.GLYPH_BOX`), and it does NOT keep the header crop's canonical
spacing. So this probe divides the boxes by `Q.CELL_STAFF_SPACE` of cell 0 —
exact for the `cell:0` arm, approximate for the `header_window` arm (the two
crops of one staff share a staff, so their canonical spacings differ only by
the crops' own upscale). The change itself is made INSIDE `locate_clef`, where
both quantities are already in one space, so nothing downstream inherits this
approximation. It is here only to size the reach.

Usage:
    python3 benchmarks/omr-clef-geometry-2026-09/probe/price_occupied.py \
        --manifest benchmarks/acceptance/manifest.json \
        --out-json benchmarks/omr-clef-geometry-2026-09/out/occupied-reach.json
    # one document only, while iterating:
    ... --only beethoven5-litolff
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.omr.staged.record_io import load_record          # noqa: E402
from tools.library.score_library import library_root        # noqa: E402

_NOTEHEAD_PREFIX = "notehead"


# ─────────────────────────────────────────────────────────────────────────────
# Subject keys. `staff/<page>/<system>/<staff>`, `cell/<p>/<s>/<st>/<c>`,
# `glyph/<p>/<s>/<st>/<c>/<g>` — parsed here rather than imported so the probe
# reads a FILE, not a live Subject class that could change under it.
# ─────────────────────────────────────────────────────────────────────────────


def _parts(subject: str) -> List[str]:
    return subject.split("/")


def _staff_of(subject: str) -> Optional[str]:
    p = _parts(subject)
    if p[0] in ("staff", "cell", "glyph") and len(p) >= 4:
        return "staff/%s/%s/%s" % (p[1], p[2], p[3])
    return None


def _system_of(subject: str) -> Optional[str]:
    p = _parts(subject)
    if p[0] in ("staff", "cell", "glyph") and len(p) >= 3:
        return "system/%s/%s" % (p[1], p[2])
    if p[0] == "system" and len(p) >= 3:
        return subject
    return None


def _cell_of(subject: str) -> Optional[str]:
    p = _parts(subject)
    if p[0] in ("cell", "glyph") and len(p) >= 5:
        return "cell/%s/%s/%s/%s" % (p[1], p[2], p[3], p[4])
    return None


def _overlaps(a: Tuple[float, float, float, float],
              b: Tuple[float, float, float, float]) -> bool:
    """The SAME predicate as `clef_locator._overlaps_any`, in spaces."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _band(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"n": 0}
    out = {
        "n": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "median": round(statistics.median(values), 2),
    }
    if len(values) >= 2:
        out["p05"] = round(sorted(values)[int(0.05 * (len(values) - 1))], 2)
        out["p95"] = round(sorted(values)[int(0.95 * (len(values) - 1))], 2)
    return out


def price(record_path: Path) -> Dict[str, Any]:
    data = load_record(str(record_path))
    rec = data["record"]
    obs = rec["observations"]
    abst = rec["abstentions"]
    verd = rec["verdicts"]

    # ── indices ──────────────────────────────────────────────────────────────
    cell_space: Dict[str, float] = {}
    cell_box: Dict[str, List[float]] = {}
    staff_lines: Dict[str, List[float]] = {}
    clef_located_obs: Dict[str, List[dict]] = {}
    glyph_boxes_by_cell: Dict[str, List[dict]] = {}
    clef_glyph_obs: Dict[str, List[dict]] = {}

    for o in obs:
        q = o["quantity"]
        if q == "cell_staff_space":
            try:
                cell_space[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "cell_box":
            v = o["value"]
            if isinstance(v, (list, tuple)) and len(v) == 4:
                cell_box[o["subject"]] = [float(x) for x in v]
        elif q == "staff_lines":
            v = o["value"]
            if isinstance(v, (list, tuple)):
                staff_lines[o["subject"]] = [float(x) for x in v]
        elif q == "clef_located":
            clef_located_obs.setdefault(o["subject"], []).append(o)
        elif q == "clef_glyph":
            clef_glyph_obs.setdefault(o["subject"], []).append(o)
        elif q == "glyph_box":
            c = _cell_of(o["subject"])
            if c is not None and c.endswith("/0"):
                glyph_boxes_by_cell.setdefault(c, []).append(o)

    clef_verdict: Dict[str, dict] = {}
    for v in verd:
        if v["quantity"] == "clef":
            clef_verdict[v["subject"]] = v

    # ── A. the MEASURED height band per family, from successful reads ────────
    by_family: Dict[str, List[float]] = {}
    by_family_width: Dict[str, List[float]] = {}
    located_rows: List[dict] = []
    for staff_sub, rows in clef_located_obs.items():
        p = _parts(staff_sub)
        cell0 = "cell/%s/%s/%s/0" % (p[1], p[2], p[3])
        sp = cell_space.get(cell0)
        for r in rows:
            d = r.get("detail") or {}
            bbox = d.get("bbox")
            if not sp or not bbox or len(bbox) != 4:
                continue
            h_sp = float(bbox[3]) / sp
            w_sp = float(bbox[2]) / sp
            fam = str(r.get("value"))
            # ⚠️ THE DIVISOR IS EXACT ONLY FOR THE `cell:0` ARM. The bbox is
            # in ITS OWN crop's canonical pixels and the record does not carry
            # the HEADER crop's canonical spacing, so a header-frame row
            # divided by cell 0's spacing is off by the two crops' upscale
            # ratio — visibly so: it produces heights ABOVE the locator's own
            # `max_height_spaces` (5.0), which is arithmetically impossible for
            # a cluster the locator accepted. The band that gates anything is
            # therefore taken from the `cell:0` arm alone; the header arm is
            # reported beside it, labelled, and used for nothing.
            key = fam if r.get("frame") == "cell:0" else fam + " (header*)"
            by_family.setdefault(key, []).append(h_sp)
            by_family_width.setdefault(key, []).append(w_sp)
            located_rows.append({
                "staff": staff_sub, "frame": r.get("frame"),
                "read": fam, "family": d.get("family"),
                "x_center": d.get("x_center"),
                "h_spaces": round(h_sp, 3), "w_spaces": round(w_sp, 3),
                "symmetry": r.get("score"),
            })

    bands = {fam: {"height": _band(v),
                   "width": _band(by_family_width.get(fam, []))}
             for fam, v in sorted(by_family.items())}
    bands["ALL_LOCATED_cell0_only"] = {
        "height": _band([h for k, v in by_family.items()
                         if "header*" not in k for h in v]),
        "width": _band([w for k, v in by_family_width.items()
                        if "header*" not in k for w in v]),
    }

    # ── A2. the band the DETECTOR's own clef boxes occupy, per class ─────────
    # ⚠️ THE CV LOCATOR IS A C-CLEF LOCATOR AND ONLY EVER NAMES ONE, so
    # `bands` above can never hold a treble or a bass row and the roadmap's
    # "treble ~= 7-8 / bass ~= 3.5-4" cannot be measured from it. `Q.GLYPH_BOX`
    # on a clef-class box can, on the same plate, in the same unit — a second,
    # independent reading of the same convention ("a clef's size is consistent
    # with the staff"). It is reported and NOT used as a gate: these are boxes
    # the detector drew, not clusters the locator would see.
    det_h: Dict[str, List[float]] = {}
    det_w: Dict[str, List[float]] = {}
    for cell, rows_ in glyph_boxes_by_cell.items():
        sp = cell_space.get(cell)
        if not sp:
            continue
        for g in rows_:
            v = g["value"]
            if not isinstance(v, (list, tuple)) or len(v) != 5:
                continue
            name = str(v[0])
            if not name.lower().startswith("clef"):
                continue
            det_h.setdefault(name, []).append(float(v[4]) / sp)
            det_w.setdefault(name, []).append(float(v[3]) / sp)
    detector_clef_bands = {
        k: {"height": _band(v), "width": _band(det_w.get(k, []))}
        for k, v in sorted(det_h.items())
    }

    # the locator only ever names a C-clef family, so the band it enforces is
    # its own config; record that too so FINDINGS can compare the two.
    from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG as _CFG
    config_band = {
        "min_height_spaces": _CFG.min_height_spaces,
        "max_height_spaces": _CFG.max_height_spaces,
        "min_width_spaces": _CFG.min_width_spaces,
        "max_width_spaces": _CFG.max_width_spaces,
        "max_start_spaces": _CFG.max_start_spaces,
    }

    # ── B/C/D/E. every `occupied` abstention ────────────────────────────────
    lo = bands["ALL_LOCATED_cell0_only"]["height"].get("min")
    hi = bands["ALL_LOCATED_cell0_only"]["height"].get("max")
    rows: List[dict] = []
    n_occ = 0
    for a in abst:
        if a["quantity"] != "clef_located":
            continue
        d = a.get("detail") or {}
        if str(d.get("locator_branch")) != "occupied":
            continue
        n_occ += 1
        staff_sub = a["subject"]
        p = _parts(staff_sub)
        cell0 = "cell/%s/%s/%s/0" % (p[1], p[2], p[3])
        sp = cell_space.get(cell0)
        w_sp = d.get("w_spaces")
        h_sp = d.get("h_spaces")
        clusters = d.get("clusters") or []
        # the cluster that ENDED the call is the one whose (w, h) the branch
        # note carries; find it so its x comes with it.
        ender = None
        for c in clusters:
            if (w_sp is not None and h_sp is not None
                    and abs(float(c.get("w", -1)) - float(w_sp)) < 0.011
                    and abs(float(c.get("h", -1)) - float(h_sp)) < 0.011):
                ender = c
                break
        cx = None if ender is None else float(ender.get("x", 0.0))
        cy = None if ender is None else float(ender.get("y", 0.0))

        # ⚠️ NOTEHEAD-CLASS ONLY, because that is the population that can veto:
        # `gather._occupied_boxes` filters to `startswith("notehead")` before
        # `locate_clef` ever sees a box. Everything else overlapping the same
        # ink is reported apart, as `bystanders` — it is context for the
        # crop, never a veto, and conflating the two would overstate the
        # "which class occupied" answer.
        occupiers: List[dict] = []
        bystanders: List[dict] = []
        if sp and ender is not None:
            cl = (cx, cy, float(w_sp), float(h_sp))
            for g in glyph_boxes_by_cell.get(cell0, ()):
                v = g["value"]
                if not isinstance(v, (list, tuple)) or len(v) != 5:
                    continue
                name = str(v[0])
                box = (float(v[1]) / sp, float(v[2]) / sp,
                       float(v[3]) / sp, float(v[4]) / sp)
                if not _overlaps(cl, box):
                    continue
                entry = {
                    "subject": g["subject"], "class": name,
                    "conf": g.get("score"),
                    "x_spaces": round(box[0], 3), "y_spaces": round(box[1], 3),
                    "w_spaces": round(box[2], 3), "h_spaces": round(box[3], 3),
                }
                if name.lower().startswith(_NOTEHEAD_PREFIX):
                    occupiers.append(entry)
                else:
                    bystanders.append(entry)

        # ── "the clef box is too small" (Sean), made a number ────────────────
        # How much of the CLUSTER the vetoing notehead boxes actually account
        # for, in y. A stacked chord — the object the veto was built for
        # (commit a481398c) — is MADE of its notehead boxes and covers itself;
        # a clef the plate merged into the lines is boxed as one or two
        # noteheads on a much taller piece of ink.
        cov = None
        if occupiers and h_sp:
            segs = sorted((o["y_spaces"], o["y_spaces"] + o["h_spaces"])
                          for o in occupiers)
            merged: List[List[float]] = []
            for s, e in segs:
                s = max(s, float(cy))
                e = min(e, float(cy) + float(h_sp))
                if e <= s:
                    continue
                if merged and s <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], e)
                else:
                    merged.append([s, e])
            cov = round(sum(e - s for s, e in merged) / float(h_sp), 3)

        # the same SYSTEM's other staves — what they read and where.
        # ⚠️ TWO SOURCES, because on Litolff p3 system 0 NOT ONE staff has a
        # `clef_located` row (they all read their clef from the detector), so
        # a sibling x taken only from the locator is empty exactly where 2.11
        # needs it. `Q.GLYPH_BOX` on a clef-class box carries `x_center_page`
        # in PAGE pixels, which is the one frame comparable across staves.
        sys_sub = _system_of(staff_sub)
        siblings: List[dict] = []
        for other, orows in clef_located_obs.items():
            if other == staff_sub or _system_of(other) != sys_sub:
                continue
            op = _parts(other)
            ocell0 = "cell/%s/%s/%s/0" % (op[1], op[2], op[3])
            osp = cell_space.get(ocell0)
            for r in orows:
                od = r.get("detail") or {}
                bbox = od.get("bbox")
                siblings.append({
                    "staff": other, "frame": r.get("frame"),
                    "read": r.get("value"), "family": od.get("family"),
                    "x_center": od.get("x_center"),
                    "x_center_spaces": (None if not osp or od.get("x_center") is None
                                        else round(float(od["x_center"]) / osp, 3)),
                    "h_spaces": (None if not osp or not bbox or len(bbox) != 4
                                 else round(float(bbox[3]) / osp, 3)),
                })
        sib_x = [s["x_center_spaces"] for s in siblings
                 if s["x_center_spaces"] is not None]

        sib_det: List[dict] = []
        for other_cell, rows_ in glyph_boxes_by_cell.items():
            ocp = _parts(other_cell)
            if "system/%s/%s" % (ocp[1], ocp[2]) != sys_sub:
                continue
            if _staff_of(other_cell) == staff_sub:
                continue
            for g in rows_:
                v = g["value"]
                if not isinstance(v, (list, tuple)) or len(v) != 5:
                    continue
                if not str(v[0]).lower().startswith("clef"):
                    continue
                gd = g.get("detail") or {}
                if gd.get("x_center_page") is None:
                    continue
                sib_det.append({"staff": _staff_of(other_cell),
                                "class": str(v[0]), "conf": g.get("score"),
                                "x_center_page": round(
                                    float(gd["x_center_page"]), 1)})
        sib_det_x = [s["x_center_page"] for s in sib_det]

        # the cluster's own x in PAGE px, so it can be compared with the above.
        # Exact for the `cell:0` arm (the cluster's x is measured from that
        # crop's left edge, which IS `Q.CELL_BOX`'s x0); the `header_window`
        # arm uses the same origin and is reported with that caveat.
        cluster_x_page = None
        lines = staff_lines.get(staff_sub)
        cb = cell_box.get(cell0)
        if cx is not None and lines and len(lines) >= 2 and cb:
            sp_page = (lines[-1] - lines[0]) / (len(lines) - 1)
            cluster_x_page = round(float(cb[0]) + cx * sp_page, 1)

        v = clef_verdict.get(staff_sub)
        rows.append({
            "staff": staff_sub,
            "frame": a.get("frame"),
            "cluster": {"x_spaces": cx, "y_spaces": cy,
                        "w_spaces": w_sp, "h_spaces": h_sp,
                        "found_in_cluster_list": ender is not None,
                        "n_clusters": len(clusters)},
            "spacing_px_analysis": d.get("spacing_px"),
            "cell_staff_space_canonical": sp,
            "staff_lines": staff_lines.get(staff_sub),
            "in_measured_band": (None if h_sp is None or lo is None
                                 else bool(lo <= float(h_sp) <= hi)),
            "in_config_band": (None if h_sp is None else bool(
                _CFG.min_height_spaces <= float(h_sp) <= _CFG.max_height_spaces)),
            "occupiers": occupiers,
            "n_occupiers": len(occupiers),
            "bystanders": bystanders,
            "notehead_y_coverage_of_cluster": cov,
            "cluster_x_page_px": cluster_x_page,
            "siblings_located": siblings,
            "sibling_x_centre_spaces": sib_x,
            "sibling_x_spread_spaces": (None if len(sib_x) < 2
                                        else round(max(sib_x) - min(sib_x), 3)),
            "cluster_x_vs_sibling_median_spaces": (
                None if (not sib_x or cx is None)
                else round(cx - statistics.median(sib_x), 3)),
            "siblings_detector_clef": sib_det,
            "sibling_detector_x_page_spread": (
                None if len(sib_det_x) < 2
                else round(max(sib_det_x) - min(sib_det_x), 1)),
            "cluster_x_vs_sibling_detector_median_page_px": (
                None if (not sib_det_x or cluster_x_page is None)
                else round(cluster_x_page - statistics.median(sib_det_x), 1)),
            "clef_verdict": (None if v is None else
                             {"outcome": v["outcome"], "value": v.get("value"),
                              "reason": v.get("reason")}),
        })

    # per-staff roll-up (a staff has up to TWO occupied abstentions, one per
    # crop; the reach is counted in STAVES, because a staff has one clef).
    staves: Dict[str, List[dict]] = {}
    for r in rows:
        staves.setdefault(r["staff"], []).append(r)
    reach = {
        "occupied_abstentions": n_occ,
        "staves_with_an_occupied_abstention": len(staves),
        "staves_with_a_cluster_in_the_measured_band": sum(
            1 for v in staves.values() if any(x["in_measured_band"] for x in v)),
        "staves_in_band_with_a_notehead_occupier_found": sum(
            1 for v in staves.values()
            if any(x["in_measured_band"] and x["n_occupiers"] > 0 for x in v)),
        "staves_in_config_band": sum(
            1 for v in staves.values() if any(x["in_config_band"] for x in v)),
        "staves_in_band_clef_ABSTAINED": sum(
            1 for k, v in staves.items()
            if any(x["in_measured_band"] for x in v)
            and (clef_verdict.get(k) or {}).get("outcome") == "abstained"),
        "staves_in_band_clef_DECIDED": sum(
            1 for k, v in staves.items()
            if any(x["in_measured_band"] for x in v)
            and (clef_verdict.get(k) or {}).get("outcome") == "decided"),
        "staves_in_band_no_clef_verdict": sum(
            1 for k, v in staves.items()
            if any(x["in_measured_band"] for x in v)
            and k not in clef_verdict),
    }

    return {
        "record": str(record_path),
        "provenance": data.get("provenance"),
        "clef_located_observations": len(located_rows),
        "measured_bands": bands,
        "detector_clef_box_bands": detector_clef_bands,
        "locator_config_band": config_band,
        "located_rows": located_rows,
        "reach": reach,
        "occupied_rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest",
                    default="benchmarks/acceptance/manifest.json")
    ap.add_argument("--only", default=None,
                    help="one document id from the manifest")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    man = json.loads((_REPO / args.manifest).read_text())
    roots = {"library": library_root(), "repo": _REPO}
    out: Dict[str, Any] = {"documents": {}}
    for doc in man["documents"]:
        if args.only and doc["id"] != args.only:
            continue
        p = Path(roots[doc["record"]["root"]]) / doc["record"]["path"]
        if not p.exists():
            out["documents"][doc["id"]] = {"error": "record not present",
                                           "path": str(p)}
            print("MISSING %s -> %s" % (doc["id"], p))
            continue
        print("pricing %s (%s)" % (doc["id"], p), flush=True)
        r = price(p)
        r["label"] = doc["label"]
        r["kind"] = doc["kind"]
        out["documents"][doc["id"]] = r
        print("  %s" % json.dumps(r["reach"]), flush=True)
        print("  bands %s" % json.dumps(r["measured_bands"]), flush=True)

    if args.out_json:
        op = Path(args.out_json)
        if not op.is_absolute():
            op = _REPO / op
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(out, indent=1))
        print("wrote %s" % op)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
