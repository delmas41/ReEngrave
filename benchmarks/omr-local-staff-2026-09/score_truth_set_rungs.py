#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01) -- score `measure_ledger_rungs`
(`tools/omr/annotate/ledger_grid.py`), BEFORE and AFTER the wide-gap /
first-space / stub fixes (DECISIONS 2026-10-01 a/b/c), against 2.44c's
reference-backed far-head truth set (Litolff n=47, Brahms n=11).

MEASUREMENT ONLY — writes nothing back into the pipeline. Reuses
`truth_set_2_44c`'s own doc loading, far-head population and onset-exact
judge UNCHANGED (CLAUDE.md rule 9: derive, don't re-list); the only new
thing here is the METRIC: CLAUDE.md §6b ("Until further notice, EVERY
test is GATHER + ADJUDICATE only ... compare a head's measured STAFF
POSITION with the reference pitch converted through ADJUDICATE's clef --
never Q.PITCH or the exported file") — so this script scores POSITION,
never pitch, for geometry and both rung-reader states.

"Before" is the committed pre-lane reader (`8232c1866`, loaded from a
scratch copy so the committed fix in this working tree is never touched
or reverted) -- a real second implementation, not a flag toggle, so the
comparison cannot be gamed by this lane's own code.
"""
from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import truth_set_2_44c as ts  # noqa: E402
from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.pitch_resolver import _CLEF_ANCHORS, diatonic_index  # noqa: E402
from tools.omr.annotate import ledger_grid as lg_after  # noqa: E402

# The commit immediately before this lane touched `ledger_grid.py` --
# `git log --oneline -- tools/omr/annotate/ledger_grid.py` names it as the
# file's most recent change before this lane's own. Regenerated via `git
# show` each run (not committed) so this script stays reproducible after
# the lane merges, rather than depending on a scratch file.
_BEFORE_COMMIT = "8232c1866"
_BEFORE_PATH = REPO / "out" / "print" / "ledgers" / "_ledger_grid_before.py"


def _load_before_module():
    import subprocess
    content = subprocess.run(
        ["git", "show", f"{_BEFORE_COMMIT}:tools/omr/annotate/ledger_grid.py"],
        cwd=str(REPO), check=True, capture_output=True, text=True,
    ).stdout
    _BEFORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BEFORE_PATH.write_text(content)
    spec = importlib.util.spec_from_file_location("ledger_grid_before", _BEFORE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ─────────────────────────────────────────────────────────────────────────
# pitch <-> staff position, inverse of pitch_resolver._pitch_from_position
# ─────────────────────────────────────────────────────────────────────────

def position_from_letter_octave(letter: str, octave: int, clef: str) -> Optional[int]:
    anchor = _CLEF_ANCHORS.get(clef)
    if anchor is None:
        return None
    return diatonic_index(*anchor) - diatonic_index(letter, octave)


def truth_positions(truth_pitches: Sequence[Tuple[str, int]], clef: str) -> List[int]:
    out = []
    for letter, octave in truth_pitches:
        p = position_from_letter_octave(letter, octave, clef)
        if p is not None:
            out.append(p)
    return out


# ─────────────────────────────────────────────────────────────────────────
# the reader's own absolute-position derivation (Sean's clean-count rule,
# DECISIONS 2026-09-30 / rungs_sheet.classify_far_head's same arithmetic,
# corrected here to an ABSOLUTE position for both sides -- rungs_sheet.py
# only ever draws "above" heads on the 15-head sheet, so its own relative
# step display was never exercised on a "below" head)
# ─────────────────────────────────────────────────────────────────────────

def reader_absolute_position(
    lg_module, gray, global_lines: Sequence[float], cx: float, cy: float,
    pass_target: bool,
) -> Optional[int]:
    ys = sorted(float(v) for v in global_lines)
    if len(ys) < 2:
        return None
    spacing = (ys[-1] - ys[0]) / 4.0
    if spacing <= 0:
        return None
    half_step = spacing / 2.0
    top, bottom = ys[0], ys[-1]
    if cy < top:
        side, edge, sign, edge_pos = "above", top, -1.0, 0
    else:
        side, edge, sign, edge_pos = "below", bottom, 1.0, 8

    kwargs = {}
    if pass_target:
        kwargs["head_y"] = cy
    items = lg_module.measure_ledger_rungs(gray, ys, cx, **kwargs).get(side, [])
    if not items:
        return None

    head_dist_units = sign * (cy - edge) / half_step
    occ_idx = None
    for i, ry in enumerate(items, start=1):
        dist_units = sign * (ry - edge) / half_step
        if abs(dist_units - head_dist_units) <= 1.0:
            occ_idx = i
            break
    if occ_idx is not None:
        offset = 2 * occ_idx
    else:
        clean_before = sum(
            1 for i, ry in enumerate(items, start=1)
            if sign * (ry - edge) / half_step < head_dist_units
        )
        offset = 2 * clean_before + 1
    return edge_pos + int(sign * offset) if side == "above" else edge_pos + offset


# ─────────────────────────────────────────────────────────────────────────

def _far_head_rows(doc_id: str, loaded: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`truth_set_2_44c.build_rows`'s own population + truth-matching,
    reused UNCHANGED (CLAUDE.md rule 9) -- except the far-head GATE, which
    that module reads off `Q.LEDGER_CLEAN_COUNT_POSITION`/`Q.LEDGER_RUNG_
    GRID_POSITION` (a later, unmerged reader's own quantities, not present
    on this record's schema). The gate those quantities apply is the SAME
    one this lane's `is_far` has used throughout (`_ledger_expected > 0`,
    i.e. "outside the staff's own 5 lines, position < 0 or > 8") -- read
    here directly off `Q.NOTEHEAD_STAFF_POSITION` instead, reproducing the
    same population rather than a different one."""
    rec: EXP.Record = loaded["rec"]
    offsets = loaded["offsets"]
    detmap = ts._subject_detections(loaded["parts"])
    ref_root = loaded["ref_root"]
    bad_pages = loaded.get("bad_pages") or {}

    far_subs = []
    for o in rec.observations:
        if o["quantity"] != Q.NOTEHEAD_STAFF_POSITION:
            continue
        pos = int(round(float(o["value"])))
        if pos < 0 or pos > 8:
            far_subs.append(o["subject"])
    far_subs = sorted(set(far_subs))

    rows: List[Dict[str, Any]] = []
    for sub in far_subs:
        parts_of_sub = sub.split("/")
        page, system, staff, cell, glyph_i = (int(x) for x in parts_of_sub[1:6])
        staff_key = f"staff/{page}/{system}/{staff}"
        clef_v = rec.value(Q.CLEF, staff_key)
        pos_obs = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        box_obs = rec.obs(Q.GLYPH_BOX, sub)
        if not pos_obs or not box_obs or clef_v is None:
            continue
        raw_pos = float(pos_obs[-1]["value"])
        bbox_detail = box_obs[-1].get("detail") or {}
        page_box = bbox_detail.get("bbox_page_px")

        det = detmap.get(sub)
        our_part_id = det["our_part_id"] if det else None
        family = ts._family_for_part_id(doc_id, our_part_id) if our_part_id else None
        bar = None
        if det is not None:
            off = offsets.get((det["page"], det["system"]))
            if off is not None:
                bar = off + det["cell"] + 1 + loaded["bar_correction"]

        if page in bad_pages:
            truth_pitches: List[Tuple[str, int]] = []
        else:
            truth_pitches = ts.onset_exact_truth(
                rec, doc_id, family, bar, ref_root, page, system, staff,
                cell, glyph_i) or []

        rows.append(dict(
            subject=sub, staff_key=staff_key, raw_pos=raw_pos,
            page_box=page_box, truth_pitches=truth_pitches,
        ))
    return rows


def score_doc(doc_id: str, lg_before, lg_after_mod) -> Dict[str, Any]:
    loaded = ts.load_doc(doc_id)
    rows = _far_head_rows(doc_id, loaded)
    rec = loaded["rec"]
    gray = loaded["gray"]

    tally: Dict[str, "collections.Counter[str]"] = collections.defaultdict(
        collections.Counter
    )
    per_head: List[Dict[str, Any]] = []

    for row in rows:
        truth_p = row["truth_pitches"]
        if not truth_p:
            continue  # unscored bar -- same exclusion truth_set_2_44c uses
        staff_key = row["staff_key"]
        clef_v = rec.value(Q.CLEF, staff_key)
        if clef_v is None:
            continue
        truth_pos = set(truth_positions(truth_p, str(clef_v)))
        if not truth_pos:
            continue

        box = row["page_box"]
        if not box:
            continue
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        if not line_rows:
            continue
        global_lines = [float(y) for y in line_rows[-1]["value"]]

        geom_pos = int(round(row["raw_pos"]))

        before_pos = reader_absolute_position(
            lg_before, gray, global_lines, cx, cy, pass_target=False
        )
        after_pos = reader_absolute_position(
            lg_after_mod, gray, global_lines, cx, cy, pass_target=True
        )

        def verdict(pos: Optional[int]) -> str:
            if pos is None:
                return "abstain"
            return "right" if pos in truth_pos else "wrong"

        v_geom, v_before, v_after = (
            verdict(geom_pos), verdict(before_pos), verdict(after_pos),
        )
        tally["geometry"][v_geom] += 1
        tally["rungs_before"][v_before] += 1
        tally["rungs_after"][v_after] += 1
        per_head.append(dict(
            subject=row["subject"], staff_key=staff_key,
            truth_pos=sorted(truth_pos), geom_pos=geom_pos, v_geom=v_geom,
            before_pos=before_pos, v_before=v_before,
            after_pos=after_pos, v_after=v_after,
        ))

    return dict(tally={k: dict(v) for k, v in tally.items()}, per_head=per_head)


def main() -> int:
    lg_before = _load_before_module()
    results = {}
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        r = score_doc(doc_id, lg_before, lg_after)
        results[doc_id] = r
        for key in ("geometry", "rungs_before", "rungs_after"):
            t = r["tally"].get(key, {})
            n = sum(t.values())
            print(f"  {key:<14} right={t.get('right',0):>3} wrong={t.get('wrong',0):>3} "
                 f"abstain={t.get('abstain',0):>3}  (n={n})")
        disagree = [h for h in r["per_head"] if h["v_after"] != h["v_before"]]
        print(f"  before/after disagree on {len(disagree)} of {len(r['per_head'])} scored heads")
        for h in disagree:
            print(f"    {h['subject']:<24} truth={h['truth_pos']} "
                 f"before={h['before_pos']}({h['v_before']}) "
                 f"after={h['after_pos']}({h['v_after']}) geom={h['geom_pos']}({h['v_geom']})")
        print()

    # --- control that can fail: shift every head's y by one half-step   ---
    # before measuring -- this must score clearly WORSE than the real read,
    # or the judge/metric itself cannot be trusted (CLAUDE.md rule 7).
    print("=== control: head y offset by one half-step (must score worse) ===")
    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        rows = _far_head_rows(doc_id, loaded)
        rec = loaded["rec"]
        gray = loaded["gray"]
        right = wrong = abst = 0
        for row in rows:
            truth_p = row["truth_pitches"]
            if not truth_p:
                continue
            staff_key = row["staff_key"]
            clef_v = rec.value(Q.CLEF, staff_key)
            if clef_v is None:
                continue
            truth_pos = set(truth_positions(truth_p, str(clef_v)))
            if not truth_pos:
                continue
            box = row["page_box"]
            if not box:
                continue
            x0, y0, x1, y1 = box
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            line_rows = rec.obs(Q.STAFF_LINES, staff_key)
            if not line_rows:
                continue
            global_lines = [float(y) for y in line_rows[-1]["value"]]
            spacing = (max(global_lines) - min(global_lines)) / 4.0
            broken_cy = cy + spacing / 2.0  # one half-step offset
            pos = reader_absolute_position(
                lg_after, gray, global_lines, cx, broken_cy, pass_target=True
            )
            if pos is None:
                abst += 1
            elif pos in truth_pos:
                right += 1
            else:
                wrong += 1
        print(f"  {doc_id:<24} right={right} wrong={wrong} abstain={abst}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
