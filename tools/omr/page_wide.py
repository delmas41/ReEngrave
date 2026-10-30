"""THE PAGE-WIDE PASS (Sean 2026-10-29, plan §10): the one GATHER-stage structure scan, read once per system off the page raster.

STAGED. Its scan is `measure_extractor.detect_barlines` (already run by `staged/pipeline.prepare_pages` through `extract_measures`; this
module adds NO second scan) with `staged_page_wide` set, flag `OMR_BARLINE_SYSTEM_COLUMNS`. Readers plug in here; the first are barlines
(columns, through-ink first) and the left-edge rules (systemic barline, bracket, brace).

`system_rules(pws, system_index)` -> {"columns": [{x, span (through_system|through_group|per_staff), staff_indices, reinforced,
n_votes}], "left_edge": <the dict of `bracket_reader.read_brackets`: blocks, boundaries, interior, verdict, levels (x_centre, covers, ...),
geom>} or None when the pass did not run (flag OFF, LEGACY page).

ONE LEFT-EDGE READER: `bracket_reader.read_brackets` stays (five publishers measured, strokes and levels, bracket vs brace by reach).
The m2 draft `left_edge_rules` is deleted: its kinds came from three numbers tuned on two plates and misnamed a bracket+systemic-barline
pair as a brace (Litolff p6 s0) and a whole Brahms group as a brace (p5 s0). 2.221 m1b claims brackets and braces from this dict.
"""
from __future__ import annotations

from typing import Any, Optional


def system_rules(pws: Any, system_index: int) -> Optional[dict]:
    store = getattr(pws, "system_structure", None)
    return None if not store else store.get(system_index)


def whole_mark(pws: Any, system_index: int, box) -> Optional[dict]:
    """The WHOLE left-edge mark (`system_rules(...)["left_edge"]["marks"]`: kind brace|bracket|systemic_barline, box, staff_indices) that
    contains the centre of `box`, or None. A claimant that holds a fragment (a detector box over one stretch of a bracket) takes this mark's
    box and kind instead of its own (Sean's tiles 7 and 11: a piece of a bracket is not a brace)."""
    rules = system_rules(pws, system_index)
    if not rules:
        return None
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    best = None
    for m in rules["left_edge"].get("marks", []):
        x0, y0, x1, y1 = m["box"]
        if x0 - 6 <= cx <= x1 + 6 and y0 <= cy <= y1:
            if best is None or (y1 - y0) < (best["box"][3] - best["box"][1]):
                best = m
    return best
