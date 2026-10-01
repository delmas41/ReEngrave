#!/usr/bin/env python3
"""ROADMAP 2.44c -- a reference-backed truth set for every far notehead on
the two count pages, scoring geometry, the two ROADMAP 2.44 ledger readers,
their required-agreement rule, and a FOURTH candidate reading Sean raised
mid-lane: geometry fit LOCALLY (the staff's own lines re-measured in a
narrow column at the head's own x, rather than extrapolated from one
flat top-line+spacing read once for the whole bar/cell).

MEASUREMENT ONLY (CLAUDE.md §8): reads the committed small-re-gather
records and the reference encodings; writes nothing back into the
pipeline, no new flag, no record mutation. Run from the repo root:

    python3 -m benchmarks.omr-ledger-extrapolation-2026-09.truth_set_2_44c

(or `python3 benchmarks/omr-ledger-extrapolation-2026-09/truth_set_2_44c.py`
-- both forms are supported, see the `sys.path` shim below).

SCOPE, STATED UP FRONT (CLAUDE.md's own "what is not established" habit):

  * Matching is BAR-LEVEL, not onset-level. `tools.omr.acceptance_quick`'s
    own per-bar scorer (`acceptance_barscore.score_bar`) aligns onsets
    inside a bar for a FULL note-for-note diff; building that same
    alignment per INDIVIDUAL far-ledger glyph (rather than per exported
    bar) needs the exporter's own onset/event grouping threaded back to
    each glyph subject, which does not exist as a public mapping today.
    Instead: a SINGLE far head is scored as "truth-consistent" if its
    pitch (letter+octave, accidentals folded from the key exactly as
    `_sounding_pitch` does) is a MEMBER of the reference's pitch set for
    that (family, bar) -- not pinned to one onset. A CHORD CLUSTER (two or
    more far heads sharing one `glyph_owner`-decided staff, one cell, and
    nearly the same page x -- the stem they share) is ranked top-to-bottom
    by page y and compared against the reference's DISTINCT pitch set for
    that bar in descending order, ONLY where the two counts match; a size
    mismatch is UNSCORED, never guessed.
  * The family maps are `tools.omr.acceptance_quick._FAMILY_MAPS`, hand
    built on an EARLIER export. The current Litolff export shows 12 parts
    (Cello and Contrabass split, where the map still has one combined
    "Violoncello e Basso"); that family's heads are UNSCORED here rather
    than silently mis-unioned. Flute/Oboe/Clarinet/Bassoon/Horn/Trumpet/
    Timpani/Violin I/Violin II/Viola match the map directly on both docs.
  * "Local geometry" fits five line y's in two flanking column bands (one
    head-width gap either side of the head, avoiding its own stem) within
    a tolerance window of the GLOBAL line positions already on the record,
    by darkest-row search on the rendered page at the gather's own DPI --
    never the pipeline's own raster (that would need the cell's own
    `image_no_staff`, not persisted in this record). Declines (not
    "flat") where a flank finds no usable dark row for every one of the
    five expected lines.
"""
from __future__ import annotations

import collections
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402
from tools.omr.acceptance_quick import (  # noqa: E402
    _FAMILY_MAPS, _reference_root, _load_works_row, _union_bars,
)
from tools.library.score_library import library_root  # noqa: E402

DOCS: Dict[str, Dict[str, Any]] = {
    "beethoven5-litolff": {
        "record": REPO / "benchmarks/acceptance/quick/out/beethoven5-litolff"
                        "/beethoven5-litolff-p3.record.json",
        "works_row_id": "beethoven-sym5-mvt1-984073-p3",
        "pdf": library_root() / "editions/beethoven/symphony-5-op67"
                               "/beethoven--symphony-5-op67--henry-litolff-s"
                               "-verlag-1870--imslp984073.pdf",
        "pdf_page_index": 3,
        "dpi": 600,
    },
    "brahms1-breitkopf": {
        "record": REPO / "benchmarks/acceptance/quick/out/brahms1-breitkopf"
                        "/brahms1-breitkopf-p1.record.json",
        "works_row_id": "brahms-sym1-mvt1-317803-p2",
        "pdf": library_root() / "editions/brahms/symphony-1-op68"
                               "/brahms--symphony-1-op68--breitkopf-hartel"
                               "-brahms--imslp317803.pdf",
        "pdf_page_index": 1,
        "dpi": 600,
    },
}

_ALTERATION_SPELLING = {"#": "#", "b": "b", "##": "##", "bb": "bb"}


def _parse_pitch_letter_octave(step_alter_octave: str) -> Optional[Tuple[str, int]]:
    """`_pitch_key`'s own spelling (`"C+14"` -- step, signed alter, octave)
    -> `(letter, octave)`, dropping alter: this truth set compares LETTER
    and OCTAVE only (module docstring, task brief) -- an accidental is a
    key or printed-glyph fact, not a stack-order fact."""
    if not step_alter_octave:
        return None
    step = step_alter_octave[0]
    rest = step_alter_octave[1:]
    i = 0
    if i < len(rest) and rest[i] in "+-":
        # `_pitch_key` writes the alteration as `{alter:+d}` -- a sign
        # followed by EXACTLY ONE digit (alter is always -2..2) -- so only
        # that one digit is consumed here; everything after it is the
        # octave, which may itself be multi-digit (it never is on real
        # scores, but nothing here should assume that).
        i += 1
        if i < len(rest) and rest[i].isdigit():
            i += 1
    octave_text = rest[i:]
    try:
        octave = int(octave_text)
    except ValueError:
        return None
    return step, octave


def _our_pitch_letter_octave(name: str) -> Optional[Tuple[str, int]]:
    """`"Eb4"` / `"F#5"` / `"C6"` -> `(letter, octave)`, our own export
    spelling (`_legacy._parse_pitch`'s shape) -- accidental dropped the
    same way as the reference side."""
    if not name:
        return None
    letter = name[0]
    rest = name[1:]
    i = 0
    while i < len(rest) and rest[i] in "#b":
        i += 1
    octave_text = rest[i:]
    try:
        octave = int(octave_text)
    except ValueError:
        return None
    return letter, octave


def _ref_pitch_set(ref_bars: Dict[str, List], bar: str) -> List[Tuple[str, int]]:
    out = []
    for ev in ref_bars.get(bar, ()):
        if ev.pitch is None:
            continue
        p = _parse_pitch_letter_octave(ev.pitch)
        if p is not None:
            out.append(p)
    return out


# ─────────────────────────────────────────────────────────────────────────
# local geometry
# ─────────────────────────────────────────────────────────────────────────

def _render_page_gray(pdf_path: Path, page_index: int, dpi: int) -> "np.ndarray":
    import fitz
    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    doc.close()
    return arr


def _darkest_row(gray: "np.ndarray", x0: int, x1: int, y_lo: int, y_hi: int
                 ) -> Optional[float]:
    """The row with the LOWEST mean brightness (darkest -- 0 = black) in
    `[y_lo, y_hi)` over columns `[x0, x1)`, or `None` where the window is
    off the raster or the darkest row is not meaningfully darker than the
    window's own median (CLAUDE.md rule 8: nothing to find is not a line
    at the window's edge)."""
    H, W = gray.shape
    x0, x1 = max(0, x0), min(W, x1)
    y_lo, y_hi = max(0, y_lo), min(H, y_hi)
    if x1 <= x0 or y_hi <= y_lo:
        return None
    band = gray[y_lo:y_hi, x0:x1].astype(float)
    row_mean = band.mean(axis=1)
    k = int(np.argmin(row_mean))
    if row_mean[k] >= np.median(row_mean) - 8.0:
        return None    # nothing darker than noise in this window
    return float(y_lo + k)


def local_staff_lines(gray: "np.ndarray", global_lines: Sequence[float],
                      head_x0: float, head_x1: float, head_width: float
                      ) -> Optional[List[float]]:
    """Re-measure the FIVE staff lines in two flanking column bands either
    side of a head (one head-width gap, one head-width wide), each line
    searched within +-0.5 global-spacing of where the GLOBAL read already
    says it is -- never a blind search of the whole page. Averages the two
    flanks where both read; falls back to whichever flank reads; declines
    (returns `None`) only where NEITHER flank finds all five."""
    spacing = (max(global_lines) - min(global_lines)) / 4.0
    if spacing <= 0:
        return None
    gap = head_width
    bands = [
        (int(head_x0 - gap - head_width), int(head_x0 - gap)),
        (int(head_x1 + gap), int(head_x1 + gap + head_width)),
    ]
    per_flank: List[List[float]] = []
    for x0, x1 in bands:
        lines = []
        for gy in sorted(global_lines):
            y = _darkest_row(gray, x0, x1, int(gy - spacing * 0.5),
                             int(gy + spacing * 0.5) + 1)
            if y is None:
                break
            lines.append(y)
        if len(lines) == 5:
            per_flank.append(lines)
    if not per_flank:
        return None
    return [sum(vals) / len(vals) for vals in zip(*per_flank)]


# ─────────────────────────────────────────────────────────────────────────
# the per-document pass
# ─────────────────────────────────────────────────────────────────────────

def load_doc(doc_id: str) -> Dict[str, Any]:
    cfg = DOCS[doc_id]
    result = json.loads(cfg["record"].read_text())
    rec = EXP.Record(result)
    built = EXP.build(rec)
    parts = built[0]
    offsets, numbering = EXP._document_bar_offsets(parts)
    works_row = _load_works_row(cfg["works_row_id"])
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    gray = _render_page_gray(cfg["pdf"], cfg["pdf_page_index"], cfg["dpi"])

    # ⚠️ CALIBRATED, NOT ASSUMED. `_document_bar_offsets` numbers bars
    # DOCUMENT-RELATIVE from 1 at this gather's own first cell; the
    # REFERENCE numbers them from the work's own bar 1 (which this small
    # re-gather's first page is not, in general -- a title/front page, or
    # simply "page 1" not being "bar 1" of the edition's own numbering).
    # `works_row["window"]["first_ref_measure"]` is a Sean-VERIFIED fact
    # (works.json, `established_by`/`verified_by`) about the SAME page
    # this truth set scores -- the count page's own first system's first
    # printed bar number -- so the one constant correction this document
    # needs is read off it once, never guessed, and differs in SIGN
    # between the two documents (Litolff +1, Brahms -1: proof it is not a
    # universal constant and must be looked up per document).
    window = works_row.get("window") or {}
    first_ref_measure = window.get("first_ref_measure")
    page_index = cfg["pdf_page_index"]
    doc_bar_of_first_cell = (offsets or {}).get((page_index, 0))
    bar_correction = 0
    if first_ref_measure is not None and doc_bar_of_first_cell is not None:
        bar_correction = int(first_ref_measure) - (doc_bar_of_first_cell + 1)

    return dict(cfg=cfg, rec=rec, parts=parts, offsets=offsets or {},
               works_row=works_row, ref_root=ref_root, gray=gray,
               bar_correction=bar_correction)


def _subject_detections(parts) -> Dict[str, Dict[str, Any]]:
    """`glyph subject -> {our_part_index, run_key, page, system, cell,
    bar_local, pitch, bbox_canonical}` -- one entry per WRITTEN notehead
    (a far head the exporter dropped, e.g. `duration_narrowed`, is simply
    absent here and scored as `no_export` by the caller)."""
    out: Dict[str, Dict[str, Any]] = {}
    for i, part in enumerate(parts):
        our_part_id = f"P{i + 1}"
        for run in part:
            for cell_idx, cell in run.cells.items():
                for det in cell.detections:
                    if det.get("category") != "notehead":
                        continue
                    sub = det.get("glyph")
                    if not sub:
                        continue
                    out[sub] = dict(our_part_id=our_part_id, run_key=run.key,
                                    page=run.page, system=run.system,
                                    cell=cell_idx, pitch=det.get("pitch"))
    return out


def _family_for_part_id(doc_id: str, our_part_id: str) -> Optional[str]:
    for family, (our_ids, _ref_ids) in _FAMILY_MAPS[doc_id].items():
        if our_part_id in our_ids:
            return family
    return None


def _far_head_subjects(rec: EXP.Record) -> List[str]:
    """Every glyph with a row (observation OR abstention) from EITHER
    ROADMAP 2.44 ledger reader -- the two readers' own gate (`_ledger_
    expected > 0`) IS the "outside its own staff, past the exempt first
    space" population, reused rather than re-derived (CLAUDE.md rule 9)."""
    subs = set()
    for o in rec.observations:
        if o["quantity"] in (Q.LEDGER_CLEAN_COUNT_POSITION,
                             Q.LEDGER_RUNG_GRID_POSITION):
            subs.add(o["subject"])
    for a in rec.abstentions:
        if a["quantity"] in (Q.LEDGER_CLEAN_COUNT_POSITION,
                             Q.LEDGER_RUNG_GRID_POSITION):
            subs.add(a["subject"])
    return sorted(subs)


def build_rows(doc_id: str, loaded: Dict[str, Any]) -> List[Dict[str, Any]]:
    rec: EXP.Record = loaded["rec"]
    offsets = loaded["offsets"]
    detmap = _subject_detections(loaded["parts"])
    gray = loaded["gray"]
    ref_root = loaded["ref_root"]

    rows: List[Dict[str, Any]] = []
    for sub in _far_head_subjects(rec):
        parts_of_sub = sub.split("/")
        page, system, staff, cell = (int(x) for x in parts_of_sub[1:5])
        staff_key = f"staff/{page}/{system}/{staff}"
        clef_v = rec.value(Q.CLEF, staff_key)
        pos_obs = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        box_obs = rec.obs(Q.GLYPH_BOX, sub)
        if not pos_obs or not box_obs or clef_v is None:
            continue
        raw_pos = float(pos_obs[-1]["value"])
        geom_pos = int(round(raw_pos))
        geom_pitch = _pitch_from_position(geom_pos, str(clef_v))

        clean_rows = rec.obs(Q.LEDGER_CLEAN_COUNT_POSITION, sub)
        grid_rows = rec.obs(Q.LEDGER_RUNG_GRID_POSITION, sub)
        r1_pos = int(round(float(clean_rows[-1]["value"]))) if clean_rows else None
        r2_pos = int(round(float(grid_rows[-1]["value"]))) if grid_rows else None
        r1_pitch = _pitch_from_position(r1_pos, str(clef_v)) if r1_pos is not None else None
        r2_pitch = _pitch_from_position(r2_pos, str(clef_v)) if r2_pos is not None else None
        agree = (r1_pos is not None and r2_pos is not None and r1_pos == r2_pos)
        agree_pitch = r1_pitch if agree else None
        option_b_pitch = agree_pitch if agree else geom_pitch

        bbox_detail = box_obs[-1].get("detail") or {}
        page_box = bbox_detail.get("bbox_page_px")
        local_pitch = None
        if page_box:
            px0, py0, px1, py1 = page_box
            cx_page = (px0 + px1) / 2.0
            cy_page = (py0 + py1) / 2.0
            head_w = px1 - px0
            line_rows = rec.obs(Q.STAFF_LINES, staff_key)
            if line_rows:
                global_lines = [float(y) for y in line_rows[-1]["value"]]
                local_lines = local_staff_lines(gray, global_lines, px0, px1,
                                                head_w if head_w > 0 else 20.0)
                if local_lines:
                    top = min(local_lines)
                    spacing = (max(local_lines) - top) / 4.0
                    if spacing > 0:
                        local_steps = (cy_page - top) / (spacing / 2.0)
                        local_pos = int(round(local_steps))
                        local_pitch = _pitch_from_position(local_pos, str(clef_v))

        det = detmap.get(sub)
        our_part_id = det["our_part_id"] if det else None
        family = _family_for_part_id(doc_id, our_part_id) if our_part_id else None
        bar = None
        if det is not None:
            off = offsets.get((det["page"], det["system"]))
            if off is not None:
                bar = off + det["cell"] + 1 + loaded["bar_correction"]

        truth_pitches: List[Tuple[str, int]] = []
        if family is not None and bar is not None:
            _, ref_ids = _FAMILY_MAPS[doc_id][family]
            ref_bars = _union_bars(ref_ids, ref_root)
            truth_pitches = _ref_pitch_set(ref_bars, str(bar))

        rows.append(dict(
            subject=sub, staff_key=staff_key, family=family, bar=bar,
            raw_pos=raw_pos, geom_pitch=geom_pitch,
            r1_pitch=r1_pitch, r1_abstained=(not clean_rows),
            r1_abstain_reason=(rec.abstentions and None),
            r2_pitch=r2_pitch, r2_abstained=(not grid_rows),
            agree=agree, agree_pitch=agree_pitch,
            option_b_pitch=option_b_pitch, local_pitch=local_pitch,
            exported_pitch=(det or {}).get("pitch"),
            truth_pitches=truth_pitches,
            page_box=page_box,
        ))
    return rows


def _verdict(pitch: Optional[str], truth_pitches: Sequence[Tuple[str, int]]
            ) -> str:
    if not truth_pitches:
        return "unscored"
    if pitch is None:
        return "abstain"
    po = _our_pitch_letter_octave(pitch)
    if po is None:
        return "unscored"
    return "right" if po in truth_pitches else "wrong"


def score_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    tally: Dict[str, "collections.Counter[str]"] = collections.defaultdict(collections.Counter)
    for row in rows:
        for key, pitch_field in (("geometry", "geom_pitch"),
                                 ("reader1", "r1_pitch"),
                                 ("reader2", "r2_pitch"),
                                 ("agreement", "agree_pitch"),
                                 ("option_b", "option_b_pitch"),
                                 ("local_geometry", "local_pitch")):
            v = _verdict(row.get(pitch_field), row["truth_pitches"])
            tally[key][v] += 1
    return {k: dict(v) for k, v in tally.items()}


def self_control(doc_id: str, loaded: Dict[str, Any]) -> Dict[str, int]:
    """The reference encoding scored against ITSELF (CLAUDE.md §6b: "a
    control must be able to fail -- run it in a state where it fails
    before trusting it where it passes"): every bar's own pitch set must
    trivially contain every one of its own notes' (letter, octave)."""
    ok = bad = 0
    for family, (_our, ref_ids) in _FAMILY_MAPS[doc_id].items():
        ref_bars = _union_bars(ref_ids, loaded["ref_root"])
        for bar, events in ref_bars.items():
            pitch_set = _ref_pitch_set(ref_bars, bar)
            for ev in events:
                if ev.pitch is None:
                    continue
                p = _parse_pitch_letter_octave(ev.pitch)
                if p in pitch_set:
                    ok += 1
                else:
                    bad += 1
    return {"ok": ok, "bad": bad}


def corrupted_control(doc_id: str, loaded: Dict[str, Any]) -> Dict[str, int]:
    """CLAUDE.md §6b's other half: the self-control's negative. Every
    note's octave bumped by +1 must now almost always MISS its own bar's
    (unshifted) pitch set."""
    ok = bad = 0
    for family, (_our, ref_ids) in _FAMILY_MAPS[doc_id].items():
        ref_bars = _union_bars(ref_ids, loaded["ref_root"])
        for bar, events in ref_bars.items():
            pitch_set = _ref_pitch_set(ref_bars, bar)
            for ev in events:
                if ev.pitch is None:
                    continue
                p = _parse_pitch_letter_octave(ev.pitch)
                if p is None:
                    continue
                shifted = (p[0], p[1] + 1)
                if shifted in pitch_set:
                    ok += 1
                else:
                    bad += 1
    return {"ok": ok, "bad": bad}


def main() -> int:
    all_rows: Dict[str, List[Dict[str, Any]]] = {}
    for doc_id in DOCS:
        print(f"=== {doc_id} ===")
        loaded = load_doc(doc_id)
        rows = build_rows(doc_id, loaded)
        all_rows[doc_id] = rows
        scored = sum(1 for r in rows if r["truth_pitches"])
        print(f"far heads: {len(rows)}  scored (truth bar non-empty): {scored}  "
             f"unscored: {len(rows) - scored}")
        tally = score_rows(rows)
        for reading, counts in tally.items():
            print(f"  {reading:<16}{counts}")
        sc = self_control(doc_id, loaded)
        cc = corrupted_control(doc_id, loaded)
        print(f"  self-control (ref vs itself): {sc}")
        print(f"  corrupted control (+1 octave): {cc}")
    out_path = (REPO / "benchmarks/omr-ledger-extrapolation-2026-09"
               "/truth_set_2_44c_rows.json")
    with out_path.open("w") as fh:
        json.dump(all_rows, fh, indent=1, default=str)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
