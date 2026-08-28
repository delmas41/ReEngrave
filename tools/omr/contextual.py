"""Contextual analysis over a finished transcribe result.

One entry point that runs the chain a human reader runs at a glance:

    correct systems  (system_grouping)
        -> stable part identity per staff        (slots)
        -> what instrument each part is          (staff_labels + instruments)
        -> what clef and register that implies   (clef_correction)

It works on the built page dicts rather than inside the detection loop, because
a clef hypothesis is pure arithmetic on already-resolved pitches
(`pitch_resolver.clef_diatonic_shift`). That keeps it a post-pass: nothing about
detection, rhythm or segmentation changes, and a score where it finds nothing is
serialised unchanged.

Instrument identity currently comes from the PDF's text layer, so this is a
no-op on scans without one (about three quarters of the IMSLP corpus). It
abstains loudly rather than guessing: no labels, no slots, no proposals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .clef_correction import correct_clefs_from_instruments
from .instruments import Instrument, lookup
from .preprocessing import render_page
from .slots import Slot, assign_slots, labels_by_staff
from .staff_detector import detect_staves
from .staff_labels import has_text_layer, read_staff_labels


def _instrument_by_slot(reference: list[Slot]) -> dict[int, Instrument]:
    out: dict[int, Instrument] = {}
    for slot in reference:
        if not slot.instrument:
            continue
        match = lookup(slot.instrument)
        if match is not None:
            out[slot.index] = match.instrument
    return out


def apply_contextual_analysis(
    result: dict[str, Any],
    *,
    pdf_path: str | Path | None = None,
    dpi: int | None = None,
    apply_clefs: bool = True,
) -> dict[str, Any]:
    """Annotate a transcribe result with part identity, and fix clefs the
    detector never read.

    Mutates `result` in place and returns a summary. Staff dicts gain
    `slot_index` / `instrument`, and any staff whose clef is questioned gains
    `clef_proposal`. Returns counts plus the reference layout, so a caller can
    report what was inferred.
    """
    summary: dict[str, Any] = {
        "available": False, "reason": None, "reference": [],
        "labelled_staves": 0, "proposals": [], "clefs_applied": 0,
        "noteheads_restated": 0,
    }
    pdf_path = Path(pdf_path or result.get("source_pdf", ""))
    dpi = dpi or result.get("dpi") or 300
    pages = result.get("pages", [])
    if not pages or not pdf_path.exists():
        summary["reason"] = "no pages or source PDF unavailable"
        return summary

    page_indices = [p.get("page_index") for p in pages]
    if not any(has_text_layer(pdf_path, i) for i in page_indices):
        summary["reason"] = "no text layer — instrument identity unavailable"
        return summary

    staved, labels = [], []
    for page_index in page_indices:
        pws = detect_staves(render_page(pdf_path, page_index, dpi=dpi))
        staved.append(pws)
        labels.append(labels_by_staff(read_staff_labels(pws)))

    reference = assign_slots(staved, labels)
    if not reference:
        summary["reason"] = "no reference layout could be built"
        return summary

    instrument_by_slot = _instrument_by_slot(reference)
    slot_by_staff: dict[tuple[int, int, int], int] = {}
    for page_index, pws in zip(page_indices, staved):
        for staff in pws.staves:
            slot_by_staff[(page_index, staff.system_index, staff.staff_index)] = \
                staff.slot_index

    # Write identity onto the staff dicts so downstream consumers (export, the
    # consistency checks, the review UI) can see what part a staff is.
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                if slot is None or slot < 0:
                    continue
                staff["slot_index"] = slot
                instrument = instrument_by_slot.get(slot)
                if instrument is not None:
                    staff["instrument"] = instrument.name
                    staff["instrument_family"] = instrument.family
                    if instrument.unpitched:
                        staff["unpitched"] = True

    records = correct_clefs_from_instruments(
        pages, instrument_by_slot, slot_by_staff, apply=apply_clefs)

    summary.update(
        available=True,
        reference=[{"slot": s.index, "group": s.group_index,
                    "instrument": s.instrument} for s in reference],
        labelled_staves=sum(len(l) for l in labels),
        proposals=records,
        clefs_applied=sum(1 for r in records if r["applied"]),
        noteheads_restated=sum(r.get("noteheads_restated", 0) for r in records),
    )
    return summary
