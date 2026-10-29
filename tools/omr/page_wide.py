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
