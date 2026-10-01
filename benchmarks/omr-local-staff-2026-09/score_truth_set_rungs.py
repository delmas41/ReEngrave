#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01, round 2) -- score `measure_ledger_rungs`
+ `derive_far_head_step` (`tools/omr/annotate/ledger_grid.py`) against
2.44c's reference-backed far-head truth set, at STAFF POSITION, never
pitch (CLAUDE.md Sec6b).

Round 2 fixes four things the manager found reading two page-3 crops
against the print (DECISIONS 2026-10-01):

  1. The far-head GATE now applies `far_head_needs_ledger_read` -- a
     first-space head (-1/9, on-staff per rule b) is scored as geometry,
     never sent to the reader at all. This also fixes the truth-set size
     (round 1's own bug): it should land near 2.44c's own 47/11.
  2. The reader's own position arithmetic is `ledger_grid.
     derive_far_head_step` -- the gap, in staff spaces, from the head's
     NEAR edge to the last clean rung -- replacing the old generic
     distance-tolerance match.
  3. `exclude_boxes` -- every OTHER notehead's own box on the page is
     masked out of the ink before a rung's stubs are checked, so a
     neighbouring head's ink can no longer fake one side of a stub.
  4. Per-PAGE rendering: a far head's subject names its own GATHER page,
     which is not always the one PDF page `truth_set_2_44c.DOCS` names
     for the count page -- round 1 read every head's ink off that ONE
     rendered page regardless, which is simply the wrong raster for any
     head on a different page (confirmed: round 1's page-1 crops had
     staff lines with ~0 ink coverage). Rendered per page now, cached.

MEASUREMENT ONLY -- writes nothing back into the pipeline. Reuses
`truth_set_2_44c`'s own doc loading, far-head truth-matching
(`onset_exact_truth`) and family maps UNCHANGED (CLAUDE.md rule 9).
"""
from __future__ import annotations

import collections
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
from tools.omr.annotate import ledger_grid as lg  # noqa: E402


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
# fix 4: a far head's own GATHER page names the PDF page to render -- not
# necessarily `DOCS[doc_id]["pdf_page_index"]` (the count page only)
# ─────────────────────────────────────────────────────────────────────────

class PageCache:
    def __init__(self, cfg: Dict[str, Any]):
        self._cfg = cfg
        self._cache: Dict[int, Any] = {}

    def get(self, page_index: int):
        if page_index not in self._cache:
            self._cache[page_index] = ts._render_page_gray(
                self._cfg["pdf"], page_index, self._cfg["dpi"]
            )
        return self._cache[page_index]


def _notehead_boxes_by_page(rec: EXP.Record) -> Dict[int, List[Tuple[str, tuple]]]:
    out: Dict[int, List[Tuple[str, tuple]]] = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] != Q.NOTEHEAD_STAFF_POSITION:
            continue
        sub = o["subject"]
        page = int(sub.split("/")[1])
        box_obs = rec.obs(Q.GLYPH_BOX, sub)
        if not box_obs:
            continue
        detail = box_obs[-1].get("detail") or {}
        pb = detail.get("bbox_page_px")
        if pb:
            out[page].append((sub, tuple(float(v) for v in pb)))
    return out


# ─────────────────────────────────────────────────────────────────────────
# the reader's own absolute-position derivation
# ─────────────────────────────────────────────────────────────────────────

def reader_absolute_position(
    gray, global_lines: Sequence[float], box: Sequence[float],
    subject: str, page_notehead_boxes: Sequence[Tuple[str, tuple]],
) -> Tuple[Optional[int], str]:
    """Returns (absolute position or None, reason). Fixes 2 + 3."""
    ys = sorted(float(v) for v in global_lines)
    if len(ys) < 2:
        return None, "no_staff_lines"
    spacing = (ys[-1] - ys[0]) / 4.0
    if spacing <= 0:
        return None, "bad_spacing"
    top, bottom = ys[0], ys[-1]
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    if cy < top:
        side, edge, sign, edge_pos, near_y = "above", top, -1.0, 0, y1
    else:
        side, edge, sign, edge_pos, near_y = "below", bottom, 1.0, 8, y0

    # exclude every OTHER notehead's own box, by SUBJECT -- never by box
    # value, which float round-trips could coincidentally match or miss.
    others = [b for (s, b) in page_notehead_boxes if s != subject]
    items = lg.measure_ledger_rungs(
        gray, ys, cx, head_y=cy, exclude_boxes=others
    ).get(side, [])
    step = lg.derive_far_head_step(items, edge, sign, near_y, spacing)
    if step["offset"] is None:
        return None, step["reason"]
    return edge_pos + int(sign * step["offset"]), step["reason"]


# ─────────────────────────────────────────────────────────────────────────

def _far_head_rows(doc_id: str, loaded: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`truth_set_2_44c.build_rows`'s own population + truth-matching,
    reused UNCHANGED (CLAUDE.md rule 9). The far-head GATE is read off
    `Q.NOTEHEAD_STAFF_POSITION` (that quantity's own values, not the
    unmerged `Q.LEDGER_CLEAN_COUNT_POSITION`/`Q.LEDGER_RUNG_GRID_POSITION`
    2.44c itself reads, absent on this record's schema) and now applies
    `far_head_needs_ledger_read` (fix 1, round 2) -- a first-space head
    is NOT in this population at all; it is scored as on-staff geometry
    directly by the caller."""
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
        if lg.far_head_needs_ledger_read(pos):
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
            subject=sub, staff_key=staff_key, raw_pos=raw_pos, page=page,
            page_box=page_box, truth_pitches=truth_pitches,
        ))
    return rows


def score_doc(doc_id: str) -> Dict[str, Any]:
    loaded = ts.load_doc(doc_id)
    rows = _far_head_rows(doc_id, loaded)
    rec = loaded["rec"]
    pages = PageCache(loaded["cfg"])
    boxes_by_page = _notehead_boxes_by_page(rec)

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
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        if not line_rows:
            continue
        global_lines = [float(y) for y in line_rows[-1]["value"]]
        gray = pages.get(row["page"])

        geom_pos = int(round(row["raw_pos"]))
        after_pos, reason = reader_absolute_position(
            gray, global_lines, box, row["subject"],
            boxes_by_page.get(row["page"], [])
        )

        def verdict(pos: Optional[int]) -> str:
            if pos is None:
                return "abstain"
            return "right" if pos in truth_pos else "wrong"

        v_geom, v_after = verdict(geom_pos), verdict(after_pos)
        tally["geometry"][v_geom] += 1
        tally["rungs_after"][v_after] += 1
        per_head.append(dict(
            subject=row["subject"], staff_key=staff_key, page=row["page"],
            truth_pos=sorted(truth_pos), geom_pos=geom_pos, v_geom=v_geom,
            after_pos=after_pos, v_after=v_after, reason=reason,
        ))

    return dict(tally={k: dict(v) for k, v in tally.items()}, per_head=per_head)


def main() -> int:
    results = {}
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        r = score_doc(doc_id)
        results[doc_id] = r
        n_far_total = len(_far_head_rows(doc_id, ts.load_doc(doc_id)))
        print(f"  far-head population (gate applied): {n_far_total}")
        for key in ("geometry", "rungs_after"):
            t = r["tally"].get(key, {})
            n = sum(t.values())
            print(f"  {key:<14} right={t.get('right',0):>3} wrong={t.get('wrong',0):>3} "
                 f"abstain={t.get('abstain',0):>3}  (n={n})")
        wrong_or_abstain = [h for h in r["per_head"] if h["v_after"] != "right"]
        print(f"  rungs-after wrong or abstaining: {len(wrong_or_abstain)} of {len(r['per_head'])} scored heads")
        print()

    # --- control that can fail: shift every head's y by one half-step   ---
    print("=== control: head y offset by one half-step (must score worse) ===")
    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        rows = _far_head_rows(doc_id, loaded)
        rec = loaded["rec"]
        pages = PageCache(loaded["cfg"])
        boxes_by_page = _notehead_boxes_by_page(rec)
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
            line_rows = rec.obs(Q.STAFF_LINES, staff_key)
            if not line_rows:
                continue
            global_lines = [float(y) for y in line_rows[-1]["value"]]
            spacing = (max(global_lines) - min(global_lines)) / 4.0
            x0, y0, x1, y1 = box
            broken_box = (x0, y0 + spacing / 2.0, x1, y1 + spacing / 2.0)
            gray = pages.get(row["page"])
            pos, _reason = reader_absolute_position(
                gray, global_lines, broken_box, row["subject"],
                boxes_by_page.get(row["page"], [])
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
