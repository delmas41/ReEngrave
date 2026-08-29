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

Instrument identity comes from the PDF's text layer where there is one (18 of 65
IMSLP score PDFs). For the rest, `vision_fallback=True` reads the margin with
Claude instead — measured at 100% agreement with the text layer where both
resolve, plus 30 staves recovered that the text layer's OCR had garbled
(`benchmarks/omr-margin-labels-2026-08/`). It is **off by default** because it
costs money; roughly $0.01 per system read.

That cost is small because identity is a property of the SCORE, not of each
page. Slots propagate one reading across every system and page, so
`vision_system_budget` (default 3) caps how many systems are ever sent — a few
cents covers a whole work, not a few cents per page.

With neither source it abstains loudly rather than guessing: no labels, no
slots, no proposals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .clef_correction import correct_clefs_from_instruments
from .instruments import Instrument, candidates_for_alias, lookup
from .preprocessing import render_page
from .score_layouts import fit_layouts, resolve_ambiguous_label
from .slots import Slot, assign_slots, labels_by_staff
from .staff_detector import detect_staves
from .staff_labels import StaffLabel, has_text_layer, read_staff_labels


def _instrument_by_slot(reference: list[Slot]) -> dict[int, Instrument]:
    out: dict[int, Instrument] = {}
    for slot in reference:
        if not slot.instrument:
            continue
        match = lookup(slot.instrument)
        if match is not None:
            out[slot.index] = match.instrument
    return out


def _fill_defaulted_clefs(pages, slot_by_staff) -> list[dict]:
    """Give a staff that read no clef the clef its own part read elsewhere.

    A part keeps its clef from system to system, and the pipeline already knows
    which staves are the same part — that is what `slots` established. So a
    staff carrying nothing but the positional default can borrow from a system
    where the same part WAS read. Measured on the 52 hand-read staves of
    `benchmarks/omr-key-signature/ground_truth.json`: seven such staves exist,
    filling them fixes one and breaks none (Pastoral p.2, where the bassoon
    reads bass in the second system and defaults to treble in the first).

    This is deliberately not the cross-system clef vote that was tried and
    dropped in 2026-07 (`docs/internal-consistency-checks.md`). That one
    majority-voted each role's FINAL clef across same-sized systems, and it
    failed two ways: "same-sized systems are the same instruments" is false on
    condensed scores, and the majority reading can be the wrong one, so it
    flagged correct staves. Both objections are answered here rather than
    argued with — the parts come from slot ALIGNMENT rather than from equal
    staff counts, and nothing that was read is ever overruled: a silence is
    filled, and only when every reading of that part agrees.
    """
    read_by_slot: dict[int, set[str]] = {}
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                if not staff.get("clef_source") or not staff.get("clef"):
                    continue
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                if slot is None or slot < 0:
                    continue
                read_by_slot.setdefault(slot, set()).add(staff["clef"])

    filled: list[dict] = []
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                if staff.get("clef_source"):
                    continue
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                if slot is None or slot < 0:
                    continue
                agreed = read_by_slot.get(slot)
                if not agreed or len(agreed) != 1:
                    continue
                clef = next(iter(agreed))
                if clef == staff.get("clef"):
                    continue
                filled.append({
                    "page_index": key[0], "system_index": key[1],
                    "staff_index": key[2], "slot": slot,
                    "from_clef": staff.get("clef"), "to_clef": clef,
                })
                staff["clef"] = clef
                staff["clef_source"] = "slot_continuity"
    return filled


def _read_clefs_by_slot(pages, slot_by_staff) -> dict[int, str]:
    """The clef each slot actually READS, by majority across its staves.

    Only clefs a reader produced count (`clef_source` present). A staff carrying
    the positional default would otherwise vote "treble" for every part on the
    page, which is exactly the failure the key-signature reader abstains around:
    a guess fed into a prior comes back out looking like evidence.
    """
    votes: dict[int, dict[str, int]] = {}
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                if not staff.get("clef_source"):
                    continue
                clef = staff.get("clef")
                if not clef:
                    continue
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                if slot is None or slot < 0:
                    continue
                votes.setdefault(slot, {})
                votes[slot][clef] = votes[slot].get(clef, 0) + 1
    return {
        slot: max(tally.items(), key=lambda kv: kv[1])[0]
        for slot, tally in votes.items()
    }


def _resolve_ambiguous_labels(
    reference, staff_labels_per_page, slot_by_staff, page_indices, staved,
    fit, instrument_by_slot, instrument_source,
) -> None:
    """Let position settle the labels a lexicon cannot.

    `Tp.` is Timpani in the German and Italian tradition and Trumpet in the
    English one. `instruments.py` has to pick one for its alias table and picks
    the commoner reading for this corpus, with the page it was measured on named
    in a comment. Here the page itself answers: the layout fit knows what sits
    at that position, and a staff below the trumpets is the timpani.

    Only ever chooses among the candidates the alias already allows, and only
    when the fit names that slot — so a page the prior cannot read keeps exactly
    the reading it had.
    """
    for page_index, pws, staff_labels in zip(page_indices, staved, staff_labels_per_page):
        for label in staff_labels:
            candidates = candidates_for_alias(label.alias)
            if len(candidates) < 2:
                continue
            key = (page_index, next(
                (s.system_index for s in pws.staves
                 if s.staff_index == label.staff_index), 0), label.staff_index)
            slot = slot_by_staff.get(key)
            if slot is None or slot < 0:
                continue
            chosen = resolve_ambiguous_label(slot, candidates, fit)
            if chosen is None:
                continue
            current = instrument_by_slot.get(slot)
            instrument_by_slot[slot] = chosen
            for s in reference:
                if s.index == slot:
                    s.instrument = chosen.name
            if current is None or current.name != chosen.name:
                instrument_source[slot] = "score_order_ambiguity"


def _labels_for_page(pws, pdf_path: Path, page_index: int, *,
                     vision_fallback: bool, budget: list[int]) -> list[StaffLabel]:
    """Text-layer labels, falling back to the vision reader when there are none.

    `budget` is a one-element list of systems still allowed to be read, mutated
    in place. It exists because instrument identity is a property of the SCORE,
    not of each page: slots propagate one reading across every system and page,
    so a handful of calls covers a whole work. Scores also label their first
    system most fully and abbreviate or omit later — so reading early systems
    buys the most, and reading all of them buys almost nothing extra.
    """
    labels = read_staff_labels(pws)
    if labels or not vision_fallback or budget[0] <= 0:
        return labels
    from .staff_labels_vision import read_staff_labels_vision
    n_systems = len({s.system_index for s in pws.staves})
    budget[0] -= n_systems
    try:
        return read_staff_labels_vision(pws)
    except Exception as exc:                              # noqa: BLE001
        logger.warning("vision label fallback failed on page %s: %s", page_index, exc)
        return []


def apply_contextual_analysis(
    result: dict[str, Any],
    *,
    pdf_path: str | Path | None = None,
    dpi: int | None = None,
    apply_clefs: bool = True,
    vision_fallback: bool = False,
    vision_system_budget: int = 3,
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
    # No text layer used to end the analysis here: with no labels there was no
    # instrument identity, and everything downstream of identity was
    # unavailable. Score order supplies a second source — instruments appear in
    # family order and never out of it, so position alone says a good deal —
    # and it needs no text at all. The run continues, and `score_layouts`
    # decides for itself whether the page says enough to name anything.
    unlabelled = (
        not vision_fallback
        and not any(has_text_layer(pdf_path, i) for i in page_indices)
    )

    budget = [vision_system_budget]
    staved, labels = [], []
    staff_labels_per_page = []
    for page_index in page_indices:
        pws = detect_staves(render_page(pdf_path, page_index, dpi=dpi))
        staved.append(pws)
        read = [] if unlabelled else _labels_for_page(
            pws, pdf_path, page_index,
            vision_fallback=vision_fallback, budget=budget)
        staff_labels_per_page.append(read)
        labels.append(labels_by_staff(read))

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

    # ── The score-order prior ────────────────────────────────────────────────
    # Fitted to the REFERENCE rather than to a page, because instrumentation is
    # a property of the work: one fit then reaches every system through the
    # slots. It is given whatever is already known — the labels that resolved,
    # and the clefs that were actually READ — and fills in only what is missing.
    clef_by_slot = _read_clefs_by_slot(pages, slot_by_staff)
    fit = fit_layouts(
        len(reference),
        labels={s.index: s.instrument for s in reference if s.instrument},
        clefs=clef_by_slot,
    )
    instrument_source: dict[int, str] = {i: "label" for i in instrument_by_slot}
    if fit is not None:
        for slot in reference:
            proposed = fit.instrument_for(slot.index)
            if proposed is None:
                continue
            if slot.index not in instrument_by_slot:
                match = lookup(proposed)
                if match is not None:
                    instrument_by_slot[slot.index] = match.instrument
                    instrument_source[slot.index] = "score_order"
        _resolve_ambiguous_labels(
            reference, staff_labels_per_page, slot_by_staff, page_indices,
            staved, fit, instrument_by_slot, instrument_source)

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
                    # Where the name came from. A reader has to be able to tell
                    # a name that was PRINTED on the page from one deduced from
                    # where the staff sits.
                    staff["instrument_source"] = instrument_source.get(slot, "label")
                    if instrument.unpitched:
                        staff["unpitched"] = True

    # Clef correction runs on identity that was READ, never on identity the
    # score-order prior deduced. The prior is a hypothesis about where a staff
    # sits, and it inherits the clef problem it would then be used to fix: on
    # Beethoven 5 p.15 two string staves whose clefs are misread as treble come
    # out of the prior as violins, and letting that rewrite their clefs would
    # close the loop on its own mistake. So the deduction is written into the
    # JSON, where a reader can see it and judge it, and stops there.
    read_instruments = {
        slot: inst for slot, inst in instrument_by_slot.items()
        if instrument_source.get(slot) != "score_order"
    }
    # Fill defaulted clefs from the same part in another system BEFORE the
    # instrument pass, so that pass sees the borrowed reading and leaves those
    # staves alone — a clef read on the page outranks one deduced from an
    # instrument's convention.
    clefs_filled = _fill_defaulted_clefs(pages, slot_by_staff) if apply_clefs else []

    records = correct_clefs_from_instruments(
        pages, read_instruments, slot_by_staff, apply=apply_clefs)

    summary.update(
        available=True,
        reference=[{"slot": s.index, "group": s.group_index,
                    "instrument": s.instrument} for s in reference],
        labelled_staves=sum(len(l) for l in labels),
        layout=(fit.layout.name if fit else None),
        layout_named_slots=(fit.n_named if fit else 0),
        instruments_from_score_order=sum(
            1 for v in instrument_source.values() if v == "score_order"),
        ambiguous_labels_resolved=sum(
            1 for v in instrument_source.values() if v == "score_order_ambiguity"),
        proposals=records,
        clefs_applied=sum(1 for r in records if r["applied"]),
        clefs_filled_from_slot=len(clefs_filled),
        clef_fills=clefs_filled,
        noteheads_restated=sum(r.get("noteheads_restated", 0) for r in records),
    )
    return summary
