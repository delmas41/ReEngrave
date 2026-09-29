"""ROADMAP 2.17 -- Step 1, from SAVED records, no re-gather.

Measures `Q.STEM`'s GATHER yield on BEAMED cells specifically, Litolff vs.
Breitkopf, and asks -- for every `Q.DURATION` verdict whose own `detail`
shows `stems_attached == 0` (the population `duration_narrowed:
beams_ambiguous` names, CLAUDE.md SS4a/SS10) -- whether that glyph's own
CELL holds ANY accepted `Q.STEM` row at all.

That last split is the whole point (roadmap 2.17's own gate, FINDINGS SS6):

  * cell has ZERO accepted `Q.STEM` rows -> nothing was accepted ANYWHERE in
    the cell for `_stem_joined` to try -- a GATHER-reach question (is the
    ink there and refused, or genuinely absent -- needs Step 1b / a crop).
  * cell has >=1 accepted `Q.STEM` row, but NONE overlaps THIS head's own
    box -- the cell's own stems exist, so this is a join-TOLERANCE question
    (`_stem_joined`'s `_boxes_overlap` test), not a GATHER-reach one.

Reads each record EXACTLY ONCE via `record_io.load_record`
(CLAUDE.md SS4b), through `export.Record` (SS5b's own sanctioned index --
no opinions, just lookups; the same class `notehead_funnel.py` already
uses). No re-gather, no re-adjudicate, no code change under
`tools/omr/staged/`.

Usage (nohup -- Breitkopf's record is ~1 GB):

    python3 benchmarks/omr-missing-notes-2026-09/probe/stem_yield.py \\
        --record <path> --label breitkopf --out <out.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def _boxes_overlap(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (min(ax + aw, bx + bw) - max(ax, bx) > 0
            and min(ay + ah, by + bh) - max(ay, by) > 0)


def _xywh_head(v):
    # `Q.GLYPH_BOX` value is `[smufl_name, x, y, w, h]` -- see
    # `notehead_funnel.py`'s own `bbox` field and `rhythm._xywh_head`.
    if not (isinstance(v, (list, tuple)) and len(v) >= 5):
        return None
    return (float(v[1]), float(v[2]), float(v[3]), float(v[4]))


def _cell_key(glyph_subject: str) -> str:
    parts = glyph_subject.split("/")
    # glyph/page/system/staff/cell/idx -> cell/page/system/staff/cell
    return "/".join(["cell"] + parts[1:5])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from tools.omr.staged import export as E
    from tools.omr.staged import record_io
    from tools.omr.staged.record import Q

    log(f"[{a.label}] loading {a.record} via record_io.load_record (ONE read) ...")
    t0 = time.time()
    doc = record_io.load_record(a.record)
    log(f"[{a.label}] loaded in {time.time() - t0:.1f}s")
    provenance = doc.get("provenance")
    log(f"[{a.label}] provenance: commit={provenance.get('commit') if provenance else None} "
        f"dirty={provenance.get('dirty') if provenance else None}")

    log(f"[{a.label}] building Record() index ...")
    t0 = time.time()
    rec = E.Record(doc)
    log(f"[{a.label}] Record() built in {time.time() - t0:.1f}s "
        f"({len(rec.observations)} observations, {len(rec.verdicts)} verdicts)")

    # ── per-CELL Q.STEM / Q.BEAM_STROKE row counts ──────────────────────────
    log(f"[{a.label}] indexing Q.STEM and Q.BEAM_STROKE rows by cell ...")
    stem_rows_by_cell: dict = collections.defaultdict(list)
    for o in rec.obs_of(Q.STEM):
        stem_rows_by_cell[o["subject"]].append(o)
    beam_rows_by_cell: dict = collections.defaultdict(list)
    for o in rec.obs_of(Q.BEAM_STROKE):
        beam_rows_by_cell[o["subject"]].append(o)
    log(f"[{a.label}] {len(stem_rows_by_cell)} cells carry >=1 Q.STEM row; "
        f"{len(beam_rows_by_cell)} cells carry >=1 Q.BEAM_STROKE row")

    # ── every Q.DURATION verdict on a NOTEHEAD (not a rest), with its own
    # `detail` (adjudicate_duration's `shared` dict -- present on EVERY
    # verdict, decided or narrowed, CLAUDE.md SS4a: EVALUATE/INFER aside,
    # ADJUDICATE's own verdict already carries `stems_attached`) ────────────
    log(f"[{a.label}] walking Q.DURATION verdicts ...")
    t0 = time.time()
    n_duration = 0
    n_notehead_duration = 0
    beamed_cells_total = 0
    beamed_cells_zero_stem = 0
    stems_attached_zero_total = 0
    stems_attached_zero_beamambig = 0
    # of the stems_attached==0 population: cell has 0 stem rows at all vs
    # cell has >=1 stem row that just doesn't overlap THIS head.
    zero_cell_has_no_stems = 0
    zero_cell_has_stems_not_joined = 0
    # restricted to the ACTUAL funnel population -- narrowed AND
    # beams_ambiguous, not every unbeamed note (which legitimately has
    # stems_attached==0 and is DECIDED, not narrowed).
    beamambig_cell_has_no_stems = 0
    beamambig_cell_has_stems_not_joined = 0
    near_by_x_total = [0]
    far_by_x_total = [0]
    stem_rows_per_beamed_cell_hist: collections.Counter = collections.Counter()
    examples_cell_has_stems_not_joined = []
    examples_cell_has_no_stems = []
    seen_cells_for_hist = set()
    # spread crop candidates across PAGES, the same discipline
    # `notehead_funnel.py`'s own `_example` uses -- otherwise a document
    # whose `Q.DURATION` verdicts are walked in page order fills the whole
    # cap from page 0 alone and every later page is invisible to the crop
    # step.
    MAX_GAP_EXAMPLES = 60
    MAX_GAP_PER_PAGE = 2
    _gap_per_page: collections.Counter = collections.Counter()

    for v in rec.verdicts_of(Q.DURATION):
        n_duration += 1
        sub = v["subject"]
        if not sub.startswith("glyph/"):
            continue
        detail = v.get("detail") or {}
        if "stems_attached" not in detail:
            # a rest's Q.DURATION verdict carries no such detail (rhythm.py
            # `_rest_ruling` is a different branch entirely) -- skip, it is
            # not part of this population.
            continue
        n_notehead_duration += 1
        cell = _cell_key(sub)

        is_beamed = bool(beam_rows_by_cell.get(cell))
        if is_beamed and cell not in seen_cells_for_hist:
            seen_cells_for_hist.add(cell)
            beamed_cells_total += 1
            n_stem_rows = len(stem_rows_by_cell.get(cell, ()))
            stem_rows_per_beamed_cell_hist[n_stem_rows] += 1
            if n_stem_rows == 0:
                beamed_cells_zero_stem += 1

        stems_attached = detail.get("stems_attached")
        if stems_attached == 0:
            stems_attached_zero_total += 1
            is_beamambig = (v.get("outcome") == "narrowed"
                             and v.get("reason") == "beams_ambiguous")
            if is_beamambig:
                stems_attached_zero_beamambig += 1
            cell_stem_rows = stem_rows_by_cell.get(cell, ())
            box_rows = rec.obs(Q.GLYPH_BOX, sub)
            head_box = _xywh_head(box_rows[-1]["value"]) if box_rows else None
            head_cx = (head_box[0] + head_box[2] / 2.0) if head_box else None
            head_w = head_box[2] if head_box else None
            # ⚠️ NEAR vs FAR, in NOTEHEAD WIDTHS -- `_stem_joined`'s own
            # `_boxes_overlap` test has ZERO tolerance, so a real stem
            # sitting a few px off the head's box already reads
            # `stems_attached==0`. "NEAR" (<=1 notehead width of x-distance,
            # `BEAM_EDGE_TOLERANCE_WIDTHS`'s own unit) says a plausible
            # candidate exists close by and this is a JOIN-TOLERANCE
            # question; "FAR" (or no stem in the cell at all) says there is
            # no local candidate for THIS note's own stem to be, which is a
            # GATHER-reach question about this note specifically, not the
            # cell as a whole.
            min_dist_widths = None
            if head_cx is not None and cell_stem_rows:
                dists = []
                for r in cell_stem_rows:
                    sv = r["value"]
                    if isinstance(sv, (list, tuple)) and len(sv) >= 3:
                        s_cx = float(sv[0]) + float(sv[2]) / 2.0
                        dists.append(abs(s_cx - head_cx))
                if dists and head_w:
                    min_dist_widths = min(dists) / head_w
            is_near = min_dist_widths is not None and min_dist_widths <= 1.0
            page_no = int(sub.split("/")[1])

            if not cell_stem_rows:
                zero_cell_has_no_stems += 1
                if is_beamambig:
                    beamambig_cell_has_no_stems += 1
                if (is_beamambig
                        and len(examples_cell_has_no_stems) < MAX_GAP_EXAMPLES
                        and _gap_per_page[page_no] < MAX_GAP_PER_PAGE):
                    _gap_per_page[page_no] += 1
                    examples_cell_has_no_stems.append(
                        {"subject": sub, "cell": cell, "detail": detail,
                         "reason": v.get("reason"), "outcome": v.get("outcome"),
                         "is_beamambig": is_beamambig})
            else:
                zero_cell_has_stems_not_joined += 1
                if is_beamambig:
                    beamambig_cell_has_stems_not_joined += 1
                    if is_near:
                        near_by_x_total[0] += 1
                    else:
                        far_by_x_total[0] += 1
                if (is_beamambig and not is_near
                        and len(examples_cell_has_stems_not_joined) < MAX_GAP_EXAMPLES
                        and _gap_per_page[page_no] < MAX_GAP_PER_PAGE):
                    _gap_per_page[page_no] += 1
                    examples_cell_has_stems_not_joined.append(
                        {"subject": sub, "cell": cell, "detail": detail,
                         "reason": v.get("reason"), "outcome": v.get("outcome"),
                         "is_beamambig": is_beamambig,
                         "head_box": head_box,
                         "min_dist_notehead_widths": min_dist_widths,
                         "is_near": is_near,
                         "cell_stem_rows": [
                             {"value": r["value"],
                              "x0": (r.get("detail") or {}).get("x0"),
                              "x1": (r.get("detail") or {}).get("x1")}
                             for r in cell_stem_rows]})
    log(f"[{a.label}] duration walk done in {time.time() - t0:.1f}s: "
        f"{n_duration} Q.DURATION verdicts, {n_notehead_duration} on noteheads")

    # ── crop-ready geometry for the GAP population (beamambig AND stems
    # NOT near this head, whether the cell was empty or merely far) --
    # reuses `notehead_funnel.py`'s own geometry shape so
    # `crop_beams_ambiguous.py`'s reader can be reused with no changes to
    # its geometry-consuming code, only its examples key.
    gap_examples = (
        [e for e in examples_cell_has_no_stems if e.get("is_beamambig")]
        + [e for e in examples_cell_has_stems_not_joined
           if e.get("is_beamambig") and not e.get("is_near")])
    log(f"[{a.label}] {len(gap_examples)} GAP examples "
        f"(beamambig, no near stem) -- collecting crop geometry ...")
    geometry: dict = {}
    for e in gap_examples:
        sub = e["subject"]
        box_rows = rec.obs(Q.GLYPH_BOX, sub)
        bbox_page = (box_rows[-1].get("detail") or {}).get("bbox_page_px") \
            if box_rows else None
        e["bbox_page"] = bbox_page
        s = sub.split("/")
        page, system, staff, cell = int(s[1]), int(s[2]), int(s[3]), int(s[4])
        staff_key = f"staff/{page}/{system}/{staff}"
        cell_key = f"cell/{page}/{system}/{staff}/{cell}"
        if sub in geometry:
            continue
        lines_rows = rec.obs(Q.STAFF_LINES, staff_key)
        sp_rows = rec.obs(Q.STAFF_SPACING, staff_key)
        cell_rows = rec.obs(Q.CELL_BOX, cell_key)
        geometry[sub] = {
            "page": page, "system": system, "staff": staff, "cell": cell,
            "staff_key": staff_key, "cell_key": cell_key,
            "staff_lines": lines_rows[-1]["value"] if lines_rows else None,
            "staff_spacing": sp_rows[-1]["value"] if sp_rows else None,
            "cell_box": cell_rows[-1]["value"] if cell_rows else None,
        }
    log(f"[{a.label}] geometry collected for {len(geometry)} gap examples")

    pdf_path = (((provenance or {}).get("settings") or {}).get("args") or {}).get("pdf")

    out = {
        "label": a.label,
        "record": a.record,
        "provenance": provenance,
        "n_duration_verdicts": n_duration,
        "n_notehead_duration_verdicts": n_notehead_duration,
        "n_cells_with_any_stem_row": len(stem_rows_by_cell),
        "n_cells_with_any_beam_row": len(beam_rows_by_cell),
        "beamed_cells_total": beamed_cells_total,
        "beamed_cells_zero_stem_rows": beamed_cells_zero_stem,
        "beamed_cells_zero_stem_pct": (
            round(100.0 * beamed_cells_zero_stem / beamed_cells_total, 1)
            if beamed_cells_total else None),
        "stem_rows_per_beamed_cell_hist": dict(sorted(
            stem_rows_per_beamed_cell_hist.items())),
        "stems_attached_zero_total": stems_attached_zero_total,
        "stems_attached_zero_beamambig": stems_attached_zero_beamambig,
        "of_stems_attached_zero__cell_has_no_stems_at_all": zero_cell_has_no_stems,
        "of_stems_attached_zero__cell_has_stems_not_joined": zero_cell_has_stems_not_joined,
        "of_BEAMAMBIG_only__cell_has_no_stems_at_all": beamambig_cell_has_no_stems,
        "of_BEAMAMBIG_only__cell_has_stems_not_joined": beamambig_cell_has_stems_not_joined,
        "of_BEAMAMBIG_cell_has_stems__NEAR_within_1_notehead_width": near_by_x_total[0],
        "of_BEAMAMBIG_cell_has_stems__FAR_over_1_notehead_width": far_by_x_total[0],
        "examples_cell_has_no_stems": examples_cell_has_no_stems,
        "examples_cell_has_stems_not_joined": examples_cell_has_stems_not_joined,
        "pdf": pdf_path,
        "examples": {"stem_gap_far_or_empty": gap_examples},
        "geometry": geometry,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    log(f"[{a.label}] wrote {a.out}")
    print(json.dumps({k: v for k, v in out.items()
                       if k not in ("examples_cell_has_no_stems",
                                     "examples_cell_has_stems_not_joined",
                                     "examples", "geometry",
                                     "provenance")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
