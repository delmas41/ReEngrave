"""THE PAGE-WIDE PASS (Sean 2026-10-29, plan §10): the one GATHER-stage structure scan, read once per system off the page raster.

STAGED. Its scan is `measure_extractor.detect_barlines` (already run by `staged/pipeline.prepare_pages` through `extract_measures`; this
module adds NO second scan) with `staged_page_wide` set, flag `OMR_BARLINE_SYSTEM_COLUMNS`. Readers plug in here; the first are barlines
(columns, through-ink first) and the left-edge rules (systemic barline, bracket, brace).

`system_rules(pws, system_index)` -> {"columns": [{x, span (through_system|through_group|per_staff), staff_indices, reinforced,
n_votes}], "left_edge": [{kind (systemic_barline|bracket|brace|left_rule), x, x0, x1, staff_indices, box (page px, for the claimant to
cover strokes with), width_sp, drift_sp, width_var_sp}]} or None when the pass did not run (flag OFF, LEGACY page).

OVERLAP, said plainly: `bracket_reader.read_brackets` (no consumer today) also reads the left edge, from strokes; `left_edge_rules` reads
the same slice of the already-held binary directly. 2.221 m1b should pick one; `kind` is a labelled reading from three measured numbers
(CONVENTION ASSUMED: bracket = thick straight rule, brace = swelling/curved rule; WHAT WOULD FALSIFY IT: a thin bracket; NOT CONFIRMED).
"""
from __future__ import annotations

from typing import Any, Optional


def system_rules(pws: Any, system_index: int) -> Optional[dict]:
    store = getattr(pws, "system_structure", None)
    return None if not store else store.get(system_index)
