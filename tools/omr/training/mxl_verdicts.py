"""Pre-fill labeling verdicts from a reference MusicXML.

    python3 -m tools.omr.training.mxl_verdicts \\
        --bench-dir benchmarks/omr-labeling-NEW \\
        --transcription out.json --truth reference.mxl --windows windows.json \\
        --dry-run            # report only; add --write to save verdicts

The detector places the boxes; the reference confirms or relabels them.

This is the reverse of the closed MXL→bounding-box path (F1 0.064): nothing
here is placed in pixel space from the file. `transcribe` has already turned
the page into per-measure detections with a pitch and a duration on each,
and `voicing.group_chords_in_measure` has already ordered them into events.
The reference measure is a note sequence too. Align the two sequences
(`measure_align`) and every match is a verdict on a box that already has
coordinates:

    truth half note  ↔ detected noteheadBlackOnLine  → WRONG_CATEGORY → noteheadHalfOnLine
    truth quarter    ↔ detected noteheadBlackInSpace → TP
    detected head with no truth match                → left PENDING for the human
    truth note with no detected match                → a HINT (ghost marker) in the UI

Three joins have to hold before any of that is trusted, and each abstains
rather than guesses:

1. **Page ↔ reference measures** — from a hand-verified window row (the shape
   of `benchmarks/omr-scan-e2e-2026-09/works.json`): which reference measure
   the page's first measure is, and which parts each printed staff carries.
   Global measure number = window start + measures on this staff in earlier
   systems + measure index. When the staff's measure count across the page
   disagrees with the window's length the cell is abstained unless
   `--trust-measure-counts` (a barline error shifts every bar after it).
2. **Staff ↔ parts** — the row's `staves[i].parts`. A system whose staff
   count differs from the row's staff count abstains whole.
3. **Alignment strength** — matched tokens over the longer side must reach
   `--min-strength` (default 0.5). A bar from the wrong measure matches a
   few notes by chance; the gate refuses it.

Then the verdicts are written onto the BATCH's own detection ids (the
`detections/<cell>.json` the UI serves), matched by overlap after mapping
the transcription's cell frame onto the batch's cell frame through the two
staffs' line positions. A confirmed notehead the batch has no detection for
becomes an added box (id `M<n>`, so it never collides with a human's `H<n>`),
which is how a draw-from-scratch batch gets its labels. Provenance goes in
each entry's `notes`, the one field the server preserves on save.

`--score` compares the pre-fill against verdicts a human already saved in
the batch — precision and recall of the pre-filled boxes against the human
boxes — which is the number that decides whether pre-filled labels can be
admitted without review. Restricted to the pass's classes when the batch
carries a `batch_config.json`.

Output, per cell, in `<bench>/prefill/<cell>.json`: status, reason, the
alignment, the decisions, the hints. `<bench>/prefill/summary.json` totals
them. The annotate server reads the hints from there.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..voicing import group_chords_in_measure
from .measure_align import (
    Alignment,
    Token,
    align_tokens,
    collapse_tie_chains,
    collapse_tremolo_runs,
    event_tokens,
    expected_head_class,
    expected_rest_class,
    head_kind_for_type,
    merge_truth_parts,
    on_line_or_in_space,
    parse_head_class,
    staff_y_for_pitch,
    truth_tokens,
)
from .musicxml_truth import TruthNote, TruthScore, load_truth

PREFILL_DIR = "prefill"
DEFAULT_MIN_STRENGTH = 0.5
DEFAULT_MIN_IOU = 0.3
NOTE_TAG = "mxl_prefill"
# A head under this share of the cell's own median in BOTH dimensions is
# grace-sized and stays a queue item: Sean's grace boxes measure 41x38 and
# 44x45 against 51-83 wide neighbours, and the pre-fill cannot label a grace
# note from either source (0 `Small` detections, 0 <grace/> in the
# reference). Measured: 2/2 grace heads deferred for 1 good box
# (benchmarks/omr-prefill-admission-2026-09/FINDINGS.md).
SMALL_HEAD_RATIO = 0.85


# --------------------------------------------------------------------------
# Window rows
# --------------------------------------------------------------------------


@dataclass
class StaffSpec:
    name: str
    parts: list[int]


@dataclass
class WindowRow:
    pdf_page_index: int
    first_ref_measure: int
    last_ref_measure: int | None
    staves: list[StaffSpec]
    row_id: str = ""
    # Optional per-system override: {system_index: [StaffSpec, ...]} for pages
    # whose systems print different staff sets (tacet suppression).
    systems: dict[int, list[StaffSpec]] = field(default_factory=dict)

    def staves_for_system(self, system_index: int) -> list[StaffSpec]:
        return self.systems.get(system_index, self.staves)

    @property
    def n_measures(self) -> int | None:
        if self.last_ref_measure is None:
            return None
        return self.last_ref_measure - self.first_ref_measure + 1


def _staff_specs(raw: Any) -> list[StaffSpec]:
    out: list[StaffSpec] = []
    for s in raw or []:
        if isinstance(s, dict):
            out.append(StaffSpec(name=str(s.get("name", "")),
                                 parts=[int(p) for p in s.get("parts", [])]))
        else:
            out.append(StaffSpec(name=str(s), parts=[]))
    return out


def load_windows(path: str | Path, *, work_id: str | None = None,
                 row_ids: list[str] | None = None) -> dict[int, WindowRow]:
    """Rows keyed by 0-based PDF page index. Accepts the scan benchmark's
    `works.json` (a list, or `{"rows": [...]}`), including its
    `"same-as:<row_id>"` staves references.

    One page index means one page of ONE edition, so a file holding several
    editions must be narrowed with `work_id` and/or `row_ids` — otherwise a
    later edition's page 1 silently replaces an earlier one's, and the
    pre-fill would read one score's page against another's parts."""
    raw = json.loads(Path(path).read_text())
    rows = raw.get("rows", raw) if isinstance(raw, dict) else raw
    by_id: dict[str, dict] = {r.get("row_id", f"row{i}"): r for i, r in enumerate(rows)}
    wanted = set(row_ids) if row_ids else None
    out: dict[int, WindowRow] = {}
    for rid, r in by_id.items():
        if work_id is not None and r.get("work_id") != work_id:
            continue
        if wanted is not None and rid not in wanted:
            continue
        page = r.get("page") or {}
        window = r.get("window") or {}
        if "pdf_page_index" not in page or "first_ref_measure" not in window:
            continue
        staves_raw = r.get("staves")
        hops = 0
        while isinstance(staves_raw, str) and staves_raw.startswith("same-as:") and hops < 10:
            staves_raw = (by_id.get(staves_raw[len("same-as:"):]) or {}).get("staves")
            hops += 1
        systems: dict[int, list[StaffSpec]] = {}
        for k, v in (r.get("systems") or {}).items():
            systems[int(k)] = _staff_specs(v)
        key = int(page["pdf_page_index"])
        if key in out:
            raise ValueError(
                f"two window rows for page {key} ({out[key].row_id!r} and {rid!r}) — "
                "narrow with work_id / row_ids so one edition is selected")
        out[key] = WindowRow(
            pdf_page_index=int(page["pdf_page_index"]),
            first_ref_measure=int(window["first_ref_measure"]),
            last_ref_measure=(int(window["last_ref_measure"])
                              if window.get("last_ref_measure") is not None else None),
            staves=_staff_specs(staves_raw),
            row_id=rid,
            systems=systems,
        )
    return out


# --------------------------------------------------------------------------
# Transcription lookup
# --------------------------------------------------------------------------


def index_transcription(result: dict) -> dict[tuple[int, int, int, int], dict]:
    """(page_index, system_index, staff_index, measure_index) → context dict
    with the page, system, staff and measure dicts."""
    out: dict[tuple[int, int, int, int], dict] = {}
    for page in result.get("pages", []):
        p = page.get("page_index")
        for sys_ in page.get("systems", []):
            s = sys_.get("system_index")
            for staff in sys_.get("staves", []):
                st = staff.get("staff_index")
                for m in staff.get("measures", []):
                    out[(p, s, st, m.get("measure_index"))] = {
                        "page": page, "system": sys_, "staff": staff, "measure": m,
                    }
    return out


def system_measure_count(system: dict) -> int:
    """The bar count a system prints — the mode across its staves. Every
    staff of a system spans the same bars; one that reads differently has a
    barline error."""
    counts = [st.get("n_measures", len(st.get("measures", []))) for st in system.get("staves", [])]
    if not counts:
        return 0
    return Counter(counts).most_common(1)[0][0]


def measures_before(page: dict, system_index: int) -> int:
    """Bars printed in EARLIER systems of the page. `staff_index` is
    numbered across the page, so this never follows a staff index from one
    system into the next — it sums each earlier system's own count."""
    return sum(system_measure_count(sys_) for sys_ in page.get("systems", [])
               if sys_.get("system_index", 0) < system_index)


def measures_on_page(page: dict) -> int:
    return sum(system_measure_count(sys_) for sys_ in page.get("systems", []))


# --------------------------------------------------------------------------
# Frames and overlap
# --------------------------------------------------------------------------


@dataclass
class FrameMap:
    """Transcription canonical cell → batch canonical cell. y through the
    staff lines, x through the cell widths; identity when either side
    lacks geometry."""
    sx: float = 1.0
    sy: float = 1.0
    tx0: float = 0.0
    bx0: float = 0.0
    ty0: float = 0.0
    by0: float = 0.0

    def box(self, bbox: list[float]) -> dict[str, int]:
        x, y, w, h = bbox
        X = self.bx0 + (x - self.tx0) * self.sx
        Y = self.by0 + (y - self.ty0) * self.sy
        return {"x": int(round(X)), "y": int(round(Y)),
                "w": int(round(w * self.sx)), "h": int(round(h * self.sy))}


def frame_map(measure: dict, entry: dict) -> FrameMap:
    t_lines = measure.get("staff_line_ys_canonical") or []
    b_lines = entry.get("staff_line_ys_canonical") or []
    fm = FrameMap()
    if len(t_lines) >= 5 and len(b_lines) >= 5 and t_lines[-1] > t_lines[0]:
        fm.sy = (b_lines[-1] - b_lines[0]) / (t_lines[-1] - t_lines[0])
        fm.ty0, fm.by0 = float(t_lines[0]), float(b_lines[0])
    bp = measure.get("bbox_page_px")      # [x0, y0, x1, y1] in page pixels
    up = measure.get("upscale_factor")
    b_w = entry.get("cell_canonical_w")
    if bp and up and b_w:
        t_w = (bp[2] - bp[0]) * up
        if t_w > 0:
            fm.sx = b_w / t_w
    elif fm.sy != 1.0:
        fm.sx = fm.sy
    return fm


def iou(a: dict, b: dict) -> float:
    ax1, ay1 = a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1 = b["x"] + b["w"], b["y"] + b["h"]
    iw = min(ax1, bx1) - max(a["x"], b["x"])
    ih = min(ay1, by1) - max(a["y"], b["y"])
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


def _centre_inside(a: dict, b: dict) -> bool:
    cx, cy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
    return b["x"] <= cx <= b["x"] + b["w"] and b["y"] <= cy <= b["y"] + b["h"]


def _category_of(cls: str | None) -> str:
    if parse_head_class(cls):
        return "notehead"
    if cls and cls.startswith("rest"):
        return "rest"
    return "other"


# --------------------------------------------------------------------------
# Per-cell decision
# --------------------------------------------------------------------------


@dataclass
class CellPrefill:
    cell_id: str
    status: str                       # prefilled | abstained | skipped
    reason: str = ""
    measure_number: int | None = None
    parts: list[int] = field(default_factory=list)
    alignment: dict = field(default_factory=dict)
    decisions: list[dict] = field(default_factory=list)   # on batch detection ids
    added: list[dict] = field(default_factory=list)       # new boxes
    hints: list[dict] = field(default_factory=list)
    verdict_state: dict | None = None

    def summary(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "status": self.status,
            "reason": self.reason,
            "measure_number": self.measure_number,
            "parts": self.parts,
            "alignment": self.alignment,
            "n_tp": sum(1 for d in self.decisions if d["verdict"] == "TP"),
            "n_wrong_category": sum(1 for d in self.decisions if d["verdict"] == "WRONG_CATEGORY"),
            "n_added": len(self.added),
            "n_hints_missing": sum(1 for h in self.hints if h["kind"] == "missing"),
            "n_hints_extra": sum(1 for h in self.hints if h["kind"] == "extra"),
            "n_conflicts": sum(1 for h in self.hints if h["kind"] == "conflict"),
            "n_admit_labels": sum(1 for d in self.decisions if d.get("admission") == "labels"),
            "n_admit_queue": sum(1 for d in self.decisions if d.get("admission") == "queue"),
        }


def _init_detection(d: dict) -> dict:
    """The shape `annotate.server._init_detection_v2` writes, replicated so
    this module does not import FastAPI. Pinned by a test that serves the
    file back through the server unchanged."""
    return {
        "id": d["id"],
        "verdict": None,
        "model_predicted_class": d.get("smufl_name", ""),
        "human_corrected_class": None,
        "model_predicted_category": d.get("category", ""),
        "human_corrected_category": None,
        "model_bbox": {"x": int(d.get("x", 0)), "y": int(d.get("y", 0)),
                       "w": int(d.get("w", 0)), "h": int(d.get("h", 0))},
        "human_bbox": None,
        "confidence": float(d.get("confidence", 0.0)),
        "notes": "",
    }


def _events_with_orphans(detections: list[dict]) -> list[dict]:
    """`voicing.group_chords_in_measure` keeps only noteheads that carry BOTH
    a pitch and a duration — a head whose stem the CV never found has no
    duration and would vanish from the alignment, and on a scan those are
    exactly the heads worth confirming. They are appended as one-note events
    at their own x, so the reference can still vouch for the box."""
    events = group_chords_in_measure(detections)
    placed = {id(nh) for ev in events for nh in ev.get("noteheads", [])}
    for d in detections:
        if d.get("category") != "notehead" or d.get("pitch") is None or id(d) in placed:
            continue
        bbox = d.get("bbox", [0, 0, 0, 0])
        events.append({"kind": "chord", "x_position": bbox[0] + bbox[2] // 2,
                       "duration_beats": None, "duration_type": None, "dots": 0,
                       "noteheads": [d], "rest": None, "orphan": True})
    events.sort(key=lambda e: e.get("x_position", 0))
    return events


def _truth_notes_for(truth: TruthScore, parts: list[int], number: int) -> list[TruthNote] | None:
    """Notes of `number` across `parts`, merged for a shared staff. None
    when a part lacks that measure."""
    per_part: list[list[TruthNote]] = []
    for pi in parts:
        if pi < 0 or pi >= len(truth.parts):
            return None
        m = truth.part(pi).by_number().get(number)
        if m is None:
            return None
        per_part.append(m.notes)
    if not per_part:
        return None
    return merge_truth_parts(per_part)


def _measure_length(notes: list[TruthNote]) -> float:
    end = 0.0
    for n in notes:
        end = max(end, n.onset_ql + n.duration_ql)
    return end


def _x_estimates(missing: list[Token], matched_x: list[tuple[float, float]],
                 length: float, width: int) -> dict[int, float]:
    """An approximate batch-frame x for each missing truth token, from the
    onsets of its matched neighbours; falling back to onset as a fraction of
    the bar across the cell's inner 70%."""
    matched_x = sorted(matched_x)
    out: dict[int, float] = {}
    for t in missing:
        o = t.onset_ql or 0.0
        before = [(on, x) for on, x in matched_x if on <= o]
        after = [(on, x) for on, x in matched_x if on > o]
        if before and after:
            (o0, x0), (o1, x1) = before[-1], after[0]
            f = (o - o0) / (o1 - o0) if o1 > o0 else 0.0
            out[t.index] = x0 + f * (x1 - x0)
        else:
            frac = (o / length) if length > 0 else 0.0
            out[t.index] = width * (0.15 + 0.7 * min(1.0, max(0.0, frac)))
    return out


def _bar_is_trusted(exact: int, matched: int, n_notes: int, in_range: int,
                    min_strength: float) -> bool:
    """Whether the alignment says this is the right bar, well enough read
    to confirm boxes from.

    At least one EXACT match, always — near matches alone would let a bar
    from the wrong measure pass whenever its notes sit a step from the
    reading's. Then either the exact matches reach the recall floor (and
    number at least two, or account for every head the reading placed in
    range), or exact plus near matches cover almost all of the bar."""
    if n_notes == 0 or exact == 0:
        return False
    if exact / n_notes >= min_strength and (exact >= 2 or exact >= in_range):
        return True
    return matched / n_notes >= 0.8


def prefill_cell(entry: dict, ctx: dict | None, row: WindowRow | None,
                 truth: TruthScore, batch_dets: list[dict], *,
                 match: str = "position", min_strength: float = DEFAULT_MIN_STRENGTH,
                 min_iou: float = DEFAULT_MIN_IOU,
                 trust_measure_counts: bool = False) -> CellPrefill:
    cell_id = entry["cell_id"]
    if row is None:
        return CellPrefill(cell_id, "abstained", "no window row for this page")
    if ctx is None:
        return CellPrefill(cell_id, "abstained", "cell not in the transcription")

    page, system, staff, measure = ctx["page"], ctx["system"], ctx["staff"], ctx["measure"]
    sys_idx = system.get("system_index", 0)
    staff_idx = staff.get("staff_index", 0)
    specs = row.staves_for_system(sys_idx)
    sys_staves = system.get("staves", [])
    n_staves = len(sys_staves)
    if len(specs) != n_staves:
        return CellPrefill(cell_id, "abstained",
                           f"system {sys_idx} has {n_staves} staves, the window row names {len(specs)}")
    # `staff_index` is numbered across the PAGE; the row's staff list is
    # top-to-bottom WITHIN the system, so join on the position in the system.
    position = next((i for i, st in enumerate(sys_staves) if st is staff), None)
    if position is None or position >= len(specs) or not specs[position].parts:
        return CellPrefill(cell_id, "abstained",
                           f"staff {staff_idx} (position {position} in system {sys_idx}) names no parts")
    spec = specs[position]

    sys_count = system_measure_count(system)
    own_count = staff.get("n_measures", len(staff.get("measures", [])))
    if own_count != sys_count and not trust_measure_counts:
        return CellPrefill(cell_id, "abstained",
                           f"staff reads {own_count} bars, its system reads {sys_count}",
                           parts=list(spec.parts))
    expected = row.n_measures
    if expected is not None:
        got = measures_on_page(page)
        if got != expected and not trust_measure_counts:
            return CellPrefill(cell_id, "abstained",
                               f"page reads {got} bars across its systems, window has {expected}",
                               parts=list(spec.parts))

    number = row.first_ref_measure + measures_before(page, sys_idx) \
        + int(measure.get("measure_index", 0))
    if row.last_ref_measure is not None and number > row.last_ref_measure:
        return CellPrefill(cell_id, "abstained",
                           f"measure {number} lies past the window end {row.last_ref_measure}",
                           measure_number=number, parts=list(spec.parts))
    notes = _truth_notes_for(truth, spec.parts, number)
    if notes is None:
        return CellPrefill(cell_id, "abstained",
                           f"reference has no measure {number} for parts {spec.parts}",
                           measure_number=number, parts=list(spec.parts))

    condensed = len(spec.parts) > 1
    truth_clef = next((n.clef for n in notes if n.clef), None)
    # Position keys need a clef on the reference side; where the file names
    # none (percussion, or no <clef> at all) BOTH sides fall back to step
    # keys, else a position on one side can never meet a step on the other.
    cell_match = match if (match != "position" or truth_clef) else "step"
    detections = measure.get("detections", [])
    events = _events_with_orphans(detections)
    p_tokens = event_tokens(events, match=cell_match, include_rests=not condensed,
                            line_ys=measure.get("staff_line_ys_canonical"))
    det_index = {id(d): i for i, d in enumerate(detections)}
    # A tremolo the reference spells out is one head where the page
    # abbreviates it; the reading says which bars do. Decided before the
    # tokens are cut, so everything downstream sees one note of the run's
    # total value.
    read_positions = ([int(t.key[1:]) for t in p_tokens if t.key.startswith("P")]
                      if cell_match == "position" else None)
    # Ties first: they are explicit notation, and a collapsed chain is an
    # ordinary note by the time the run-shape inference looks at the bar.
    notes = collapse_tie_chains(notes, read_positions)
    notes = collapse_tremolo_runs(notes, read_positions)
    t_tokens = truth_tokens(notes, match=cell_match, include_rests=not condensed)

    fm = frame_map(measure, entry)
    # The clef for placing hints: the reference's written clef first (a fact
    # about the part), the pipeline's reading only where the file names none.
    clef = truth_clef or measure.get("clef") or staff.get("clef") or entry.get("clef")
    b_lines = entry.get("staff_line_ys_canonical") or []
    width = int(entry.get("cell_canonical_w") or 0)

    out = CellPrefill(cell_id, "prefilled", measure_number=number, parts=list(spec.parts))
    # A cell is cut with air above and below its staff, and on a conductor's
    # page that air holds the neighbours' notes — a flute bar of 4 notes read
    # 21 heads, with positions 7 spaces below the staff. Only heads within
    # the reference's own vertical range (plus a step either side) take part
    # in the alignment; the rest stay pending and become "extra" hints.
    in_range = list(range(len(p_tokens)))
    if cell_match == "position":
        t_pos = [int(t.key[1:]) for t in t_tokens if t.key.startswith("P")]
        if t_pos:
            lo, hi = min(t_pos) - 2, max(t_pos) + 2
            in_range = [i for i, t in enumerate(p_tokens)
                        if not t.key.startswith("P") or lo <= int(t.key[1:]) <= hi]
    al_sub = align_tokens(t_tokens, [p_tokens[i] for i in in_range])
    al = Alignment(pairs=[(ti, in_range[pj]) for ti, pj in al_sub.pairs],
                   truth_unmatched=al_sub.truth_unmatched,
                   pred_unmatched=[i for i in range(len(p_tokens))
                                   if i not in {in_range[pj] for _, pj in al_sub.pairs}],
                   n_truth=len(t_tokens), n_pred=len(p_tokens),
                   near_pairs=[(ti, in_range[pj]) for ti, pj in al_sub.near_pairs])
    near_set = set(al.near_pairs)
    # Recall is over the reference's NOTES. Rests are aligned and confirmed
    # when found, but a rest the detector missed says nothing about whether
    # this is the right bar, and rest recall on a scan is poor. EXACT
    # matches are what say this is the right bar; near matches (a head
    # rounded half a space off) only fill in once an exact one vouches.
    truth_note_idx = [i for i, t in enumerate(t_tokens) if not t.is_rest]
    matched_notes = sum(1 for ti, _ in al.pairs if not t_tokens[ti].is_rest)
    exact_notes = sum(1 for pr in al.pairs if not t_tokens[pr[0]].is_rest and pr not in near_set)
    n_notes = len(truth_note_idx)
    recall = (matched_notes / n_notes) if n_notes else None
    recall_exact = (exact_notes / n_notes) if n_notes else None
    read_notes_in_range = sum(1 for i in in_range if not p_tokens[i].is_rest)
    # Is the batch's cell the same bar as the transcription's measure? The
    # batch was cut by its own segmentation run; if a barline moved between
    # then and now, the widths disagree once both are put on the same scale.
    bp = measure.get("bbox_page_px") or [0, 0, 0, 0]   # [x0, y0, x1, y1]
    up = measure.get("upscale_factor") or 1.0
    t_w = (bp[2] - bp[0]) * up
    b_w = float(entry.get("cell_canonical_w") or 0)
    width_ratio = round(b_w / (t_w * fm.sy), 3) if t_w and fm.sy else None
    out.alignment = {
        "n_truth": al.n_truth, "n_pred": al.n_pred, "matched": al.matched,
        "n_truth_notes": n_notes, "matched_notes": matched_notes,
        "exact_notes": exact_notes, "near_pairs": al.near_pairs,
        "n_pred_in_range": len(in_range),
        "strength": None if recall is None else round(recall, 3),
        "strength_exact": None if recall_exact is None else round(recall_exact, 3),
        "match": cell_match,
        "truth_keys": [t.key for t in t_tokens],
        "pred_keys": [t.key for t in p_tokens],
        "pairs": al.pairs,
        "geometry": {"transcription_w": round(t_w), "batch_w": round(b_w),
                     "y_scale": round(fm.sy, 3), "width_ratio": width_ratio},
    }

    # Verdict state on the batch's own detections.
    state = {
        "cell_id": cell_id,
        "schema_version": 2,
        "labeled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detections": [_init_detection(d) for d in batch_dets],
        "added_detections": [],
        "inspected_passes": [],
    }
    by_id = {d["id"]: d for d in state["detections"]}
    claimed: set[str] = set()

    if not p_tokens and t_tokens:
        out.reason = "no notes in the reading — hints only"
    elif not truth_note_idx:
        # Nothing to confirm — an empty bar, or rests only. Every read head
        # stays pending, marked extra; a matched rest is still confirmed.
        out.reason = ("reference has only rests in this bar" if t_tokens
                      else "reference has no notes in this bar" if p_tokens
                      else "nothing to align — reference and reading both empty")
    elif recall is not None and not _bar_is_trusted(
            exact_notes, matched_notes, n_notes, read_notes_in_range, min_strength):
        # The gate is RECALL of the reference's notes — did the reading find
        # the notes the bar holds — not a share of the longer side, because
        # extra heads cost nothing (they stay pending) while a missed bar
        # costs a wrong verdict.
        out.status = "abstained"
        out.reason = (f"weak alignment: {matched_notes} of {n_notes} reference notes matched, "
                      f"{exact_notes} exactly ({read_notes_in_range} of {al.n_pred} read heads "
                      f"in the bar's range)")
        return out

    matched_x: list[tuple[float, float]] = []
    matched_pred: set[int] = set()

    def _decide(pt: Token, tt: Token, near: bool = False) -> None:
        det = pt.ref
        if det is None:
            return
        tn: TruthNote = tt.ref
        cls = det.get("class")
        variant_corrected = False
        if pt.is_rest:
            want = expected_rest_class(tn)
            category = "rest"
        else:
            # On an exactly-paired note the reference knows the on-line /
            # in-space variant too — its staff position IS the pairing key.
            # A near pair sits a step off, where the truth's parity is the
            # wrong one by construction, so the detector's variant stands.
            truth_variant = (on_line_or_in_space(tn.pitch, tn.clef)
                             if not near and cell_match == "position" else None)
            want = expected_head_class(tn.type, cls, variant=truth_variant)
            parsed_cls = parse_head_class(cls)
            variant_corrected = bool(truth_variant and parsed_cls
                                     and parsed_cls[1] != truth_variant)
            category = "notehead"
        if want is None:
            return
        verdict = "TP" if want == cls else "WRONG_CATEGORY"
        trem = f" ({tn.tremolo_of}× repeated in the reference — tremolo abbreviation)" \
            if tn.tremolo_of else ""
        if tn.tied_of:
            trem += f" ({tn.tied_of} tied fragments in the reference)"
        label = f"{NOTE_TAG}: {'rest' if tn.rest else tn.pitch} {tn.type or '?'}" \
                f"{'.' * tn.dots} m{number}{trem}"
        bbox = fm.box(det.get("bbox", [0, 0, 0, 0]))
        parsed = parse_head_class(cls)
        if (verdict == "WRONG_CATEGORY" and parsed and parsed[0] != "Black"
                and head_kind_for_type(tn.type) == "Black"):
            # The detector read a HOLLOW head where the reference has a black
            # one. The reverse (a hollow head read black) is the scan's
            # commonest miss and is relabelled freely; this direction is the
            # two sources disagreeing about the page, and a hollow reading is
            # rarely invented. Neither side gets the verdict: the head stays
            # pending with the disagreement written on it.
            matched_x.append((tt.onset_ql or 0.0, bbox["x"] + bbox["w"] / 2))
            note = (f"{NOTE_TAG}: CONFLICT — reference says {tn.pitch} {tn.type or '?'}"
                    f"{'.' * tn.dots}{trem}, detector read {cls}; decide on the page")
            for bd in batch_dets:
                if bd["id"] in claimed:
                    continue
                bb = {"x": bd.get("x", 0), "y": bd.get("y", 0), "w": bd.get("w", 0), "h": bd.get("h", 0)}
                if iou(bbox, bb) >= min_iou:
                    by_id[bd["id"]]["notes"] = note
                    claimed.add(bd["id"])
                    break
            out.hints.append({"kind": "conflict", "label": f"{cls} vs {tn.pitch} {tn.type or '?'}",
                              "bbox": bbox, "class": cls, "pitch": tn.pitch, "type": tn.type})
            return
        if verdict == "WRONG_CATEGORY":
            label += f" → {want}"
        if near:
            label += " (≈ one step off)"
        matched_x.append((tt.onset_ql or 0.0, bbox["x"] + bbox["w"] / 2))
        # Which batch detection is this box?
        best_id, best_iou = None, 0.0
        for bd in batch_dets:
            if bd["id"] in claimed:
                continue
            if (bd.get("category") or _category_of(bd.get("smufl_name"))) != category:
                continue
            bb = {"x": bd.get("x", 0), "y": bd.get("y", 0), "w": bd.get("w", 0), "h": bd.get("h", 0)}
            v = iou(bbox, bb)
            if v < min_iou and not (v > 0 and (_centre_inside(bbox, bb) or _centre_inside(bb, bbox))):
                continue
            if v > best_iou:
                best_id, best_iou = bd["id"], v
        decision = {
            "verdict": verdict, "class": want, "category": category, "near": near,
            "variant_corrected": variant_corrected,
            "truth": {"pitch": tn.pitch, "type": tn.type, "dots": tn.dots,
                      "duration_ql": tn.duration_ql, "onset_ql": tn.onset_ql},
            "read": {"class": cls, "pitch": det.get("pitch"),
                     "duration_type": det.get("duration_type"),
                     "detection_index": det_index.get(id(det))},
            "bbox": bbox,
        }
        if best_id is not None:
            claimed.add(best_id)
            entry_v = by_id[best_id]
            entry_v["verdict"] = verdict
            entry_v["notes"] = label
            if verdict == "WRONG_CATEGORY":
                entry_v["human_corrected_class"] = want
                entry_v["human_corrected_category"] = category
            decision.update({"detection_id": best_id, "iou": round(best_iou, 3)})
        else:
            mid = f"M{len(state['added_detections'])}"
            state["added_detections"].append({
                "id": mid, "human_class": want, "human_category": category,
                "bbox": bbox, "notes": label,
            })
            decision.update({"detection_id": mid, "iou": None})
            out.added.append({"id": mid, "class": want, "bbox": bbox})
        out.decisions.append(decision)

    for ti, pi in al.pairs:
        matched_pred.add(pi)
        _decide(p_tokens[pi], t_tokens[ti], near=(ti, pi) in near_set)

    # Predicted tokens the reference does not account for: pending, with a
    # note on the batch detection they sit on, and an "extra" hint.
    for pi in al.pred_unmatched:
        pt = p_tokens[pi]
        det = pt.ref
        if det is None:
            continue
        bbox = fm.box(det.get("bbox", [0, 0, 0, 0]))
        what = "rest" if pt.is_rest else (pt.pitch or "?")
        note = f"{NOTE_TAG}: read {what}, no match in the reference m{number}"
        for bd in batch_dets:
            if bd["id"] in claimed:
                continue
            bb = {"x": bd.get("x", 0), "y": bd.get("y", 0), "w": bd.get("w", 0), "h": bd.get("h", 0)}
            if iou(bbox, bb) >= min_iou:
                by_id[bd["id"]]["notes"] = note
                break
        out.hints.append({"kind": "extra", "label": f"read {what}", "bbox": bbox,
                          "class": det.get("class")})

    # Truth tokens the reading has no note for: ghost markers.
    length = _measure_length(notes)
    missing = [t_tokens[ti] for ti in al.truth_unmatched]
    xs = _x_estimates(missing, matched_x, length, width)
    half_space = ((b_lines[-1] - b_lines[0]) / 4.0) if len(b_lines) >= 5 else 0.0
    for t in missing:
        tn: TruthNote = t.ref
        hint_type, hint_dots = tn.type, tn.dots
        run_note = f" ({tn.tremolo_of}× repeated in the reference — tremolo?)" if tn.tremolo_of else ""
        if tn.tied_of:
            run_note += f" ({tn.tied_of} tied fragments in the reference)"
        if tn.rest:
            want_cls = expected_rest_class(tn)
            y = ((b_lines[0] + b_lines[-1]) / 2.0) if len(b_lines) >= 5 else None
            label = f"rest {tn.type or ''}".strip()
        else:
            y = staff_y_for_pitch(tn.pitch, clef, b_lines)
            pos = on_line_or_in_space(tn.pitch, clef)
            kind = head_kind_for_type(hint_type)
            want_cls = f"notehead{kind}{pos}" if pos else None
            label = f"{tn.pitch} {hint_type or '?'}{'.' * hint_dots}{run_note}"
        h = int(round(half_space)) if half_space else 0
        w = int(round(half_space * 1.2)) if half_space else 0
        x = xs.get(t.index)
        bbox = None
        if x is not None and y is not None and h:
            bbox = {"x": int(round(x - w / 2)), "y": int(round(y - h / 2)), "w": w, "h": h}
        out.hints.append({"kind": "missing", "label": label, "class": want_cls,
                          "pitch": tn.pitch, "type": hint_type, "dots": hint_dots,
                          "tremolo_run": tn.tremolo_of or None,
                          "tied_run": tn.tied_of or None,
                          "onset_ql": tn.onset_ql, "bbox": bbox,
                          "x_estimated": True})

    # ---- Admission tier: which pre-filled boxes could one day be admitted
    # as labels without a glance, and which stay a queue for the human.
    # METADATA ONLY — nothing about what is written changes, and today even
    # the "labels" tier is still a queue; `--score` prices the tiers so the
    # random completion pass can decide. Reasons are per box (a near pair, a
    # grace-sized head, a variant the reference corrected) plus one per-cell
    # demotion: a cell holding any variant correction has boxes that wobble
    # against the staff grid, and the phantom cell in the measured batch was
    # exactly such a cell (benchmarks/omr-prefill-admission-2026-09/).
    head_dec = [d for d in out.decisions if d.get("category") == "notehead"]
    med_w = statistics.median([d["bbox"]["w"] for d in head_dec]) if head_dec else 0
    med_h = statistics.median([d["bbox"]["h"] for d in head_dec]) if head_dec else 0
    cell_flip = any(d.get("variant_corrected") for d in out.decisions)
    for d in out.decisions:
        reasons = []
        if d.get("near"):
            reasons.append("near_match")
        if d.get("variant_corrected"):
            reasons.append("variant_corrected")
        if (d.get("category") == "notehead" and med_w and med_h
                and d["bbox"]["w"] < SMALL_HEAD_RATIO * med_w
                and d["bbox"]["h"] < SMALL_HEAD_RATIO * med_h):
            reasons.append("small_head")
        if cell_flip and not reasons:
            reasons.append("cell_has_variant_correction")
        d["admission"] = "queue" if reasons else "labels"
        if reasons:
            d["admission_reasons"] = reasons

    out.verdict_state = state
    return out


# --------------------------------------------------------------------------
# Scoring against human verdicts already in the batch
# --------------------------------------------------------------------------


def _human_boxes(state: dict) -> list[dict]:
    out: list[dict] = []
    for d in state.get("detections", []):
        v = d.get("verdict")
        if v == "TP":
            out.append({"class": d.get("model_predicted_class"), "bbox": d.get("model_bbox")})
        elif v == "WRONG_CATEGORY":
            out.append({"class": d.get("human_corrected_class"), "bbox": d.get("model_bbox")})
        elif v == "WRONG_BBOX":
            out.append({"class": d.get("model_predicted_class"),
                        "bbox": d.get("human_bbox") or d.get("model_bbox")})
    for h in state.get("added_detections", []):
        if str(h.get("id", "")).startswith("M"):
            continue  # a previous pre-fill, not a human
        out.append({"class": h.get("human_class"), "bbox": h.get("bbox")})
    return [b for b in out if b["bbox"] and b["class"]]


def _prefill_boxes(cp: CellPrefill) -> list[dict]:
    return [{"class": d["class"], "bbox": d["bbox"]} for d in cp.decisions]


def _kind(cls: str | None) -> str | None:
    p = parse_head_class(cls)
    if p:
        return p[0]
    return cls


def pass_classes(bench: Path) -> set[str] | None:
    cfg = bench / "batch_config.json"
    if not cfg.exists():
        return None
    try:
        raw = json.loads(cfg.read_text())
    except json.JSONDecodeError:
        return None
    out: set[str] = set()
    for c in raw.get("classes", raw.get("active_classes", [])) or []:
        if isinstance(c, str):
            out.add(c)
        elif isinstance(c, dict):
            for k in ("name", "on_line", "in_space"):
                if c.get(k):
                    out.add(str(c[k]))
    return out or None


SCORE_CLASSES_PASS = "pass"
SCORE_CLASSES_ALL = "all"


def resolve_score_classes(bench: Path, spec: str) -> tuple[set[str] | None, bool]:
    """Which classes `--score` compares over, and whether that WIDENS the pass.

    Returns (classes, wider). `classes` of None means "every class".

    ⚠️ Widening is the dangerous direction, and the danger is silent. A
    single-symbol batch's verdicts contain ONLY that pass's boxes — a hollow
    sweep draws no black noteheads — so scoring a wider set against them
    counts every correctly pre-filled black head as a false positive. The
    number that comes out is not a weak result for the pre-fill; it is a
    measurement of which pass the human happened to run, and it looks like a
    damning verdict. Hence `wider`, and the caller's refusal to use it
    without cells that were actually swept for these classes.
    """
    declared = pass_classes(bench)
    if spec == SCORE_CLASSES_PASS:
        return declared, False
    if spec == SCORE_CLASSES_ALL:
        return None, declared is not None
    chosen = {c.strip() for c in spec.split(",") if c.strip()}
    if not chosen:
        raise ValueError("--score-classes was given no usable class name")
    wider = declared is not None and not chosen <= declared
    return chosen, wider


def cell_was_swept_for(human_state: dict, pass_name: str) -> bool:
    """Did this cell's human actually LOOK for the pass being scored?

    `inspected_passes` is stamped on the way out of a cell, so it means
    "looked and moved on" — which is exactly the claim a wider score needs,
    and it is recorded even for a cell that legitimately held nothing.
    """
    return pass_name in (human_state.get("inspected_passes") or [])


def _tier_zeros() -> dict:
    return {"n_prefill": 0, "matched_exact": 0, "matched_kind": 0}


def score_cell(cp: CellPrefill, human_state: dict, classes: set[str] | None,
               min_iou: float = DEFAULT_MIN_IOU) -> dict:
    human = _human_boxes(human_state)
    pre = list(cp.decisions)
    if classes is not None:
        human = [b for b in human if b["class"] in classes]
        pre = [d for d in pre if d["class"] in classes]
    used: set[int] = set()
    exact = kind = 0
    tiers = {"labels": _tier_zeros(), "queue": _tier_zeros()}
    for d in pre:
        best, best_i = 0.0, None
        for i, h in enumerate(human):
            if i in used:
                continue
            v = iou(d["bbox"], h["bbox"])
            if v >= min_iou and v > best:
                best, best_i = v, i
        t = tiers[d.get("admission") or "labels"]
        t["n_prefill"] += 1
        if best_i is not None:
            used.add(best_i)
            if human[best_i]["class"] == d["class"]:
                exact += 1
                t["matched_exact"] += 1
            if _kind(human[best_i]["class"]) == _kind(d["class"]):
                kind += 1
                t["matched_kind"] += 1
    return {"n_prefill": len(pre), "n_human": len(human),
            "matched_exact": exact, "matched_kind": kind,
            "by_admission": tiers}


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def _has_human_content(state: dict) -> bool:
    if any(d.get("verdict") for d in state.get("detections", [])):
        return True
    if any(not str(h.get("id", "")).startswith("M") for h in state.get("added_detections", [])):
        return True
    return bool(state.get("inspected_passes"))


def run(bench: Path, transcription: dict, truth: TruthScore, windows: dict[int, WindowRow], *,
        write: bool = False, hints_only: bool = False, force: bool = False, score: bool = False,
        match: str = "position", min_strength: float = DEFAULT_MIN_STRENGTH,
        min_iou: float = DEFAULT_MIN_IOU, trust_measure_counts: bool = False,
        cells: list[str] | None = None, score_classes: str = SCORE_CLASSES_PASS,
        score_inspected_for: str | None = None) -> dict:
    manifest = json.loads((bench / "cells.json").read_text())
    if cells:
        wanted = set(cells)
        manifest = [e for e in manifest if e["cell_id"] in wanted]
    ctx_by_key = index_transcription(transcription)
    det_dir = bench / "detections"
    ver_dir = bench / "verdicts"
    pre_dir = bench / PREFILL_DIR
    write_verdicts = write and not hints_only
    if write:
        pre_dir.mkdir(parents=True, exist_ok=True)
    if write_verdicts:
        ver_dir.mkdir(parents=True, exist_ok=True)
    classes, wider = resolve_score_classes(bench, score_classes)
    if score and wider and not (cells or score_inspected_for):
        raise ValueError(
            "--score-classes widens beyond this batch's own pass, and its verdicts "
            "hold only that pass's boxes — so every correctly pre-filled symbol of "
            "another kind would count as a false positive and the precision would "
            "measure the labeling pass, not the pre-fill. Restrict to cells that "
            "were swept for these classes: --cells <ids>, or --score-inspected-for "
            "<pass name>."
        )

    results: list[dict] = []
    totals = {"cells": 0, "prefilled": 0, "abstained": 0, "skipped": 0, "written": 0,
              "n_tp": 0, "n_wrong_category": 0, "n_added": 0,
              "n_hints_missing": 0, "n_hints_extra": 0, "n_conflicts": 0,
              "n_admit_labels": 0, "n_admit_queue": 0}
    score_tot = {"n_prefill": 0, "n_human": 0, "matched_exact": 0, "matched_kind": 0,
                 "cells_scored": 0,
                 "by_admission": {"labels": _tier_zeros(), "queue": _tier_zeros()}}

    for entry in manifest:
        cid = entry["cell_id"]
        key = (entry.get("page"), entry.get("system_index"), entry.get("staff_index"),
               entry.get("measure_index"))
        ctx = ctx_by_key.get(key)
        row = windows.get(int(entry.get("page", -1)))
        dp = det_dir / f"{cid}.json"
        batch_dets = json.loads(dp.read_text()).get("detections", []) if dp.exists() else []
        cp = prefill_cell(entry, ctx, row, truth, batch_dets, match=match,
                          min_strength=min_strength, min_iou=min_iou,
                          trust_measure_counts=trust_measure_counts)

        vp = ver_dir / f"{cid}.verdict.json"
        existing: dict | None = None
        if vp.exists():
            try:
                existing = json.loads(vp.read_text())
            except json.JSONDecodeError:
                existing = None

        if (score and existing is not None and cp.status == "prefilled"
                and (score_inspected_for is None
                     or cell_was_swept_for(existing, score_inspected_for))):
            s = score_cell(cp, existing, classes, min_iou)
            for k in ("n_prefill", "n_human", "matched_exact", "matched_kind"):
                score_tot[k] += s[k]
            for tier, tv in s["by_admission"].items():
                agg = score_tot["by_admission"][tier]
                for k in ("n_prefill", "matched_exact", "matched_kind"):
                    agg[k] += tv[k]
            score_tot["cells_scored"] += 1
            cp.alignment["score"] = s

        written = False
        if cp.status == "prefilled" and cp.verdict_state is not None:
            if existing is not None and _has_human_content(existing) and not force:
                cp.status = "skipped"
                cp.reason = "verdict file already carries human work (use --force)"
            elif write_verdicts:
                vp.write_text(json.dumps(cp.verdict_state, indent=2))
                written = True

        summ = cp.summary()
        summ["written"] = written
        if write:
            (pre_dir / f"{cid}.json").write_text(json.dumps({
                **summ, "decisions": cp.decisions, "hints": cp.hints,
            }, indent=2))
        results.append(summ)
        totals["cells"] += 1
        totals[cp.status] = totals.get(cp.status, 0) + 1
        totals["written"] += int(written)
        for k in ("n_tp", "n_wrong_category", "n_added", "n_hints_missing", "n_hints_extra",
                  "n_conflicts", "n_admit_labels", "n_admit_queue"):
            totals[k] += summ[k]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bench": str(bench),
        "truth": truth.path,
        "match": match,
        "min_strength": min_strength,
        "min_iou": min_iou,
        "trust_measure_counts": trust_measure_counts,
        "hints_only": hints_only,
        "pass_classes": sorted(classes) if classes else None,
        "score_classes": score_classes,
        "score_widened_beyond_pass": wider,
        "score_inspected_for": score_inspected_for,
        "totals": totals,
        "cells": results,
    }
    if score:
        n_pre, n_hum = score_tot["n_prefill"], score_tot["n_human"]
        for tv in score_tot["by_admission"].values():
            n = tv["n_prefill"]
            tv["precision_exact"] = round(tv["matched_exact"] / n, 3) if n else None
            tv["precision_kind"] = round(tv["matched_kind"] / n, 3) if n else None
        summary["score"] = {
            **score_tot,
            "precision_exact": round(score_tot["matched_exact"] / n_pre, 3) if n_pre else None,
            "precision_kind": round(score_tot["matched_kind"] / n_pre, 3) if n_pre else None,
            "recall_exact": round(score_tot["matched_exact"] / n_hum, 3) if n_hum else None,
            "recall_kind": round(score_tot["matched_kind"] / n_hum, 3) if n_hum else None,
        }
    if write:
        (pre_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _print_summary(summary: dict) -> None:
    t = summary["totals"]
    print(f"cells {t['cells']}: prefilled {t['prefilled']}, abstained {t['abstained']}, "
          f"skipped {t['skipped']}, written {t['written']}")
    print(f"  TP {t['n_tp']}  WRONG_CATEGORY {t['n_wrong_category']}  added {t['n_added']}  "
          f"hints: missing {t['n_hints_missing']}, extra {t['n_hints_extra']}, "
          f"conflicts {t.get('n_conflicts', 0)}")
    if t.get("n_admit_labels", 0) or t.get("n_admit_queue", 0):
        print(f"  admission: labels {t['n_admit_labels']}, queue {t['n_admit_queue']} "
              f"(metadata — every tier is still a queue until the random-pass re-test)")
    reasons: dict[str, int] = {}
    for c in summary["cells"]:
        if c["status"] != "prefilled":
            reasons[c["reason"]] = reasons.get(c["reason"], 0) + 1
    for r, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {r}")
    abstained = [c for c in summary["cells"] if c["status"] == "abstained"]
    if abstained:
        print("  abstained cells (width ratio ≈ 1.0 means the batch cell and the transcription "
              "measure are the same bar):")
        for c in abstained:
            al = c.get("alignment") or {}
            strength = ("" if al.get("strength") is None
                        else f"  {al.get('matched_notes', al['matched'])}/{al.get('n_truth_notes', al['n_truth'])} notes")
            g = al.get("geometry") or {}
            wr = g.get("width_ratio")
            print(f"    {c['cell_id']}  m{c.get('measure_number')}{strength}"
                  + (f"  width ratio {wr}" if wr is not None else ""))
    for c in summary["cells"]:
        if c["cell_id"] in summary.get("debug_cells", []):
            al = c.get("alignment") or {}
            print(f"  --- {c['cell_id']}  m{c.get('measure_number')}  {c['status']}: {c['reason']}")
            print(f"      match: {al.get('match')}  geometry: {al.get('geometry')}")
            print(f"      truth ({al.get('n_truth')}): {' '.join(al.get('truth_keys', []))}")
            print(f"      read  ({al.get('n_pred')}): {' '.join(al.get('pred_keys', []))}")
            print(f"      pairs: {al.get('pairs')}")
    if "score" in summary:
        s = summary["score"]
        scope = (f"classes {summary['pass_classes']}" if summary.get("pass_classes")
                 else "ALL classes")
        if summary.get("score_inspected_for"):
            scope += f", cells swept for {summary['score_inspected_for']!r}"
        print(f"score over {s['cells_scored']} cells with human verdicts "
              f"({scope}): prefill {s['n_prefill']} boxes, human {s['n_human']} boxes")
        if summary.get("score_widened_beyond_pass"):
            print("  NOTE: scored beyond the batch's own pass — the number is only "
                  "meaningful for cells swept for these classes.")
        if s["cells_scored"] == 0:
            print("  no cells scored: none carried human verdicts matching the selection.")
        print(f"  precision exact {s['precision_exact']}  kind {s['precision_kind']}   "
              f"recall exact {s['recall_exact']}  kind {s['recall_kind']}")
        by = s.get("by_admission") or {}
        if any(tv.get("n_prefill") for tv in by.values()):
            parts = []
            for tier in ("labels", "queue"):
                tv = by.get(tier) or {}
                n = tv.get("n_prefill", 0)
                parts.append(f"{tier} {n} boxes"
                             + (f" — exact {tv.get('precision_exact')}"
                                f" kind {tv.get('precision_kind')}" if n else ""))
            print("  by admission tier: " + "; ".join(parts))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bench-dir", required=True, type=Path)
    ap.add_argument("--transcription", required=True, type=Path,
                    help="transcribe JSON covering the batch's pages")
    ap.add_argument("--truth", required=True, type=Path, help="reference .musicxml / .mxl")
    ap.add_argument("--windows", required=True, type=Path,
                    help="window rows (works.json shape): page ↔ reference measures, staff ↔ parts")
    ap.add_argument("--write", action="store_true", help="write verdicts/ and prefill/")
    ap.add_argument("--write-hints", action="store_true",
                    help="write prefill/ only (hints + queue order in the UI), leaving verdicts/ "
                         "untouched — so a human's labels stay independent for --score")
    ap.add_argument("--dry-run", action="store_true", help="report only (the default)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite verdict files that already carry human work")
    ap.add_argument("--score", action="store_true",
                    help="compare against human verdicts already in the batch")
    ap.add_argument("--score-classes", default=SCORE_CLASSES_PASS,
                    help="which classes --score compares over: 'pass' (default, the batch's "
                         "own batch_config classes), 'all', or a comma-separated list. "
                         "Widening past the batch's pass needs --cells or "
                         "--score-inspected-for, because a single-symbol batch's verdicts "
                         "hold only that pass's boxes")
    ap.add_argument("--score-inspected-for", default=None, metavar="PASS",
                    help="score only cells whose verdict records this pass in "
                         "inspected_passes — i.e. cells a human actually swept for it")
    ap.add_argument("--match", choices=("position", "step", "exact"), default="position",
                    help="position: staff position from the reference clef vs the box (default, "
                         "immune to a misread clef); step: step+octave; exact: the spelling too")
    ap.add_argument("--min-strength", type=float, default=DEFAULT_MIN_STRENGTH)
    ap.add_argument("--min-iou", type=float, default=DEFAULT_MIN_IOU)
    ap.add_argument("--trust-measure-counts", action="store_true",
                    help="pre-fill even where the staff's measure count disagrees with the window")
    ap.add_argument("--work-id", default=None,
                    help="keep only window rows of this work_id (a works.json holds several)")
    ap.add_argument("--row-id", action="append", default=None,
                    help="keep only this window row (repeatable)")
    ap.add_argument("--cells", nargs="*", default=None, help="restrict to these cell ids")
    ap.add_argument("--debug-cell", action="append", default=None,
                    help="print both token sequences and the geometry for this cell (repeatable)")
    args = ap.parse_args(argv)

    transcription = json.loads(args.transcription.read_text())
    truth = load_truth(args.truth)
    windows = load_windows(args.windows, work_id=args.work_id, row_ids=args.row_id)
    if not windows:
        print(f"no usable window rows in {args.windows}", file=sys.stderr)
        return 2
    write = bool((args.write or args.write_hints) and not args.dry_run)
    try:
        summary = run(args.bench_dir, transcription, truth, windows,
                      write=write, hints_only=bool(args.write_hints and not args.write),
                      force=args.force,
                      score=args.score, match=args.match, min_strength=args.min_strength,
                      min_iou=args.min_iou, trust_measure_counts=args.trust_measure_counts,
                      cells=args.cells, score_classes=args.score_classes,
                      score_inspected_for=args.score_inspected_for)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    summary["debug_cells"] = list(args.debug_cell or [])
    _print_summary(summary)
    if not write:
        print("(dry run — nothing written; add --write, or --write-hints for the UI only)")
    elif summary["hints_only"]:
        print("(hints only — prefill/ written, verdicts/ untouched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
