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

Instrument identity comes from three readers tried cheapest first — the PDF's
text layer, then Surya 2 locally, then Claude:

    read_staff_labels          text layer   free      18 of 65 IMSLP PDFs have one
    read_staff_labels_surya    Surya 2      free      needs .venv-surya + llama.cpp
    read_staff_labels_vision   Claude       ~1c/sys   off by default

Each runs only where the one above came back empty. Both free rungs are on by
default; `surya_fallback` self-disables when the venv is absent, so leaving it
switched on costs a machine that never built it nothing at all.

Measured on the same crops and the same free ground truth
(`benchmarks/omr-margin-labels-2026-08/SURYA_BAKEOFF_2026-08-31.md`): Surya and
Claude both scored ZERO disagreements against the text layer, and Surya resolved
89% of the staves Claude did. So the free rung is not a worse reader — on
everything the truth can check it is exactly as accurate, and what it gives up is
reach: Claude repairs a damaged label from the running order, Surya transcribes
what is printed.

`vision_fallback=True` is still **off by default** because it costs money;
roughly $0.01 per system read.

That cost is small because identity is a property of the SCORE, not of each
page. Slots propagate one reading across every system and page, so
`vision_system_budget` (default 3) caps how many systems are ever sent — a few
cents covers a whole work, not a few cents per page.

With neither source it abstains loudly rather than guessing: no labels, no
slots, no proposals.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .clef_correction import (
    correct_clefs_from_instruments,
    veto_implausible_clef_changes,
)
from .absent_instrument import (DEFAULT_WINDOW, find_vetoes,
                                label_evidence, veto_config)
from .dossier import join_parts_to_slots
from .instruments import Instrument, candidates_for_alias, lookup
from .preprocessing import render_page
from .score_layouts import fit_layouts, resolve_ambiguous_label
from .roster import Roster, acquire_roster
from .roster import enabled as roster_enabled
from .slots import (MIN_LABEL_CONFIDENCE, Slot, SystemView, align,
                    assign_slots, labels_by_staff)
from .staff_detector import detect_staves
from .staff_labels import StaffLabel, has_text_layer, read_staff_labels

# Both margin readers log and degrade when they fail rather than taking the
# whole contextual pass down with them. This was referenced before it existed:
# a failing vision call raised NameError out of its own `except` clause, so the
# fallback that was written to be optional was fatal instead. Never exercised
# because nothing had made the reader fail.
logger = logging.getLogger(__name__)


def _roster_instrument_by_slot(
    roster: Roster, reference: list[Slot]) -> dict[int, Instrument]:
    """Which slot each roster name belongs to.

    The roster system is aligned into slot space by the SAME DP every other
    system goes through (`slots.align`) — monotone, deletions allowed on the
    reference side, a label conflict the only hard negative. Nothing new is
    invented for the roster: it is simply a system this run may not have
    transcribed, whose labels are then available to every system that did.

    ⚠️ Holes are DROPPED rather than filled. An unread roster position aligns as
    an unlabelled staff, which the DP already handles; healing the gap from the
    layout prior measured better (0.848 -> 0.876) and is CLOSED — see the module
    docstring in `roster.py`.
    """
    if not roster.staves or not reference:
        return {}
    names = roster.names
    view = SystemView(
        staves=list(roster.staves),
        labels={st.staff_index: names[i]
                for i, st in enumerate(roster.staves) if i in names},
    )
    # ⚠️ NO CONFLICT ARBITRATION HERE, and that is a property of `align` rather
    # than an omission: the DP is monotone and consumes each reference slot at
    # most once, so two roster positions can never land on one slot. A guard for
    # it was written, tested, found UNREACHABLE and removed — dead code carrying
    # a claim about a hazard that does not exist is worse than no code.
    out: dict[int, Instrument] = {}
    for ordinal, slot_index in enumerate(align(view, reference)):
        if slot_index < 0 or ordinal not in names:
            continue
        match = lookup(names[ordinal])
        if match is not None:
            out[slot_index] = match.instrument
    return out


def _instrument_by_slot(reference: list[Slot]) -> dict[int, Instrument]:
    out: dict[int, Instrument] = {}
    for slot in reference:
        if not slot.instrument:
            continue
        match = lookup(slot.instrument)
        if match is not None:
            out[slot.index] = match.instrument
    return out


def _apply_dossier_clefs(pages, slot_by_staff, reference, labels_by_slot,
                        dossier) -> list[dict]:
    """Give each staff the clef its part carries IN THE SCORE, where the join
    can be trusted.

    Unlike everything else here the dossier is not another reader: it is the
    work. So this may overrule a clef that WAS read — which nothing else in this
    module does — and that licence is exactly why it is confined to slots the
    part-join is anchored on, meaning a labelled slot above and below. Measured
    on the two orchestral ground-truth pages, that fixes a bassoon the detector
    read as treble and changes nothing else; unanchored, the same join walks
    into the string section and gets three staves wrong.

    What the readers said is kept on the staff as `clef_overridden_by_dossier`,
    so seeding can never hide how well the page was actually read.
    """
    facts = join_parts_to_slots(len(reference), dossier, labels_by_slot)
    applied: list[dict] = []
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                if slot is None or not (0 <= slot < len(facts)):
                    continue
                fact = facts[slot]
                if not fact or not fact.get("anchored") or not fact.get("clef"):
                    continue
                if staff.get("clef") == fact["clef"]:
                    continue
                applied.append({
                    "page_index": key[0], "system_index": key[1],
                    "staff_index": key[2], "slot": slot, "part": fact["part"],
                    "from_clef": staff.get("clef"), "to_clef": fact["clef"],
                    "was_read": bool(staff.get("clef_source")),
                })
                if staff.get("clef_source"):
                    staff["clef_overridden_by_dossier"] = {
                        "clef": staff.get("clef"), "source": staff.get("clef_source"),
                    }
                staff["clef"] = fact["clef"]
                staff["clef_source"] = "dossier"
    return applied


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


def _ambiguous_label_slots(
    staff_labels_per_page, slot_by_staff, page_indices, staved,
) -> set[int]:
    """Slots whose instrument rests on an alias the lexicon cannot settle.

    These are exactly the slots `_resolve_ambiguous_labels` exists to decide by
    POSITION, and so exactly the slots that must not be fed to the positional
    prior as if they were known — the same reason `score_layouts` withdraws a
    PIN from an ambiguous alias, which it already documents: "a pin is the one
    move that takes position off the table". Handing the fit `Bass voice` does
    the same thing more quietly, and it silences the prior rather than merely
    biasing it: no orchestral layout has a voice anywhere, so the aligner can
    place that staff in NONE of them and every voter abstains. Measured on
    Beethoven 5 p.1, slot 11: agreement 0.000 with the label, 0.643 without it.
    """
    out: set[int] = set()
    for page_index, pws, staff_labels in zip(
            page_indices, staved, staff_labels_per_page):
        for label in staff_labels:
            if len(candidates_for_alias(label.alias or "")) < 2:
                continue
            key = (page_index, next(
                (s.system_index for s in pws.staves
                 if s.staff_index == label.staff_index), 0), label.staff_index)
            slot = slot_by_staff.get(key)
            if slot is not None and slot >= 0:
                out.add(slot)
    return out


def _system_of(pws, staff_index: int) -> int:
    return next((s.system_index for s in pws.staves
                 if s.staff_index == staff_index), 0)


def _names_claimed_by_alias(pws, staff_labels) -> dict[int, dict[str, set[str]]]:
    """Per system: which instrument each label names, and under which alias.

    Keyed by system because a margin is printed per system — two systems of one
    page can carry different lineups, and what settles a reading is what THIS
    system names beside it.

    An ambiguous label is included, under its own lexicon answer. That is what
    makes the Handel case come out right: `Bassi` and `BASSO` are both
    ambiguous, they resolve to Contrabass and Bass voice respectively, and each
    is then the thing that stops the other being moved onto it. Requiring the
    blocker to be unambiguous would leave that page with nothing to say.
    """
    out: dict[int, dict[str, set[str]]] = {}
    for lab in staff_labels:
        if not _label_is_consumable(lab):
            continue
        by_name = out.setdefault(_system_of(pws, lab.staff_index), {})
        by_name.setdefault(lab.instrument.name, set()).add(lab.alias or "")
    return out


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

    ⚠️ **AND THE PRIOR MAY NOT MOVE A STAFF ONTO AN INSTRUMENT ANOTHER LABEL ON
    THE SAME SYSTEM ALREADY NAMES.** Beethoven 5 / Litolff prints `Tr.` over the
    trumpets and `Tp.` over the timpani on one system; `Tp.` is ambiguous, the
    layout fit has the timpani after the trombones (the standard order, which
    this edition deviates from — `score_layouts` documents the same deviation
    where it explains pinning), so the fit proposed Trumpet and the timpani
    staff exported as a SECOND trumpet. An engraver does not name one section
    with two different abbreviations on one system, so `Tr.` standing four
    staves up is evidence that `Tp.` is not the trumpets — the same shape as the
    `Tr. Alt.` lexicon fix, and it needs no lexicon change because it is a fact
    about the PAGE, not about the word.

    ⚠️ **The constraint is ASYMMETRIC, and that is what makes it safe.** It only
    ever refuses an OVERTURN; it never removes the lexicon's own answer. Both
    directions were measured over the 1422-label margin corpus and the
    asymmetry is forced by `Tr. Bas.`: on Beethoven 5 p.48 that staff's
    candidates are Trombone and Trumpet and BOTH are separately named on the
    system (`Tr. Alt.`/`Tr. Ten.` and `Tr.`), so a rule that excluded every
    clashing candidate would leave nothing and lose a reading that is already
    right.

    Measured, `probe_ambiguous_cooccurrence.py`: 158 ambiguous-alias
    occurrences over 6 sources, 86 of them sharing a page with a different alias
    that names one of their candidates — 52 `cor`, 18 `tp`, 9 `tr bas`, 7
    `basso`/`bassi`. **In 86 of 86 this keeps or restores the right answer, and
    in 0 does it block a correct overturn.** The control that matters is that
    the `basso` clashes are Handel's ALONE: no orchestral page in the corpus
    names Contrabass twice, so `c0a80ae7`'s measured win — `Basso.` at the foot
    of Beethoven, Mahler, Mozart 41 and Tchaikovsky 6 overturned from a singer
    to the contrabasses — passes through untouched.

    ⚠️ Known limit, accepted with its reason: a real tromba bassa printed on a
    page that also prints `Tr.` for the trumpets would be blocked from the
    correct overturn. Nothing in either corpus prints one, and the lexicon
    already records Trombone as "much the commoner" reading.
    """
    for page_index, pws, staff_labels in zip(page_indices, staved, staff_labels_per_page):
        claimed = _names_claimed_by_alias(pws, staff_labels)
        for label in staff_labels:
            candidates = candidates_for_alias(label.alias)
            if len(candidates) < 2:
                continue
            system_index = _system_of(pws, label.staff_index)
            key = (page_index, system_index, label.staff_index)
            slot = slot_by_staff.get(key)
            if slot is None or slot < 0:
                continue
            chosen = resolve_ambiguous_label(slot, candidates, fit)
            if chosen is None:
                continue
            # The overturn test. `label.instrument` is the lexicon's own answer,
            # so a `chosen` equal to it is not an overturn and is never refused.
            lexicon = label.instrument.name if label.instrument else None
            if chosen.name != lexicon:
                aliases = claimed.get(system_index, {}).get(chosen.name, set())
                if aliases - {label.alias or ""}:
                    continue
            current = instrument_by_slot.get(slot)
            instrument_by_slot[slot] = chosen
            for s in reference:
                if s.index == slot:
                    s.instrument = chosen.name
            if current is None or current.name != chosen.name:
                instrument_source[slot] = "score_order_ambiguity"


# What fraction of a system's staves the text layer must name before the margin
# reader is left alone. A PARTIAL text layer used to short-circuit the fallback
# exactly as a complete one did — any label at all and it stopped — which is the
# case that matters most, because a scanned score's OCR layer is routinely
# patchy rather than absent. Measured on the Pastoral: the text layer names 4
# staves of 10 and the margin reader names 10 of 10, all correct
# (`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`), and the
# six it adds are the ones that carry the part-join down past the winds.
LABEL_COVERAGE_OK = 0.75


def _usable(labels: list[StaffLabel]) -> int:
    """How many of these labels the lexicon can actually turn into a part.

    The only count worth comparing two readers on: an unresolved label reaches
    the join as nothing, so it must not let a worse read tie a better one.
    """
    return sum(1 for lab in labels if lab.matched)


# Confidences a downstream consumer will actually act on: a `low` label reaches
# the join as nothing exactly as an unmatched one does.
#
# TAKEN FROM `slots`, NOT RESTATED. Two consumers already hold this floor —
# `slots.MIN_LABEL_CONFIDENCE` ("a wrong instrument would propagate into every
# system") and `roster.py`, whose comment says "same floor `slots.
# labels_by_staff` uses". A third copy here is a third thing to leave stale, and
# this repo has paid for exactly that with a figure held in four places.
CONSUMABLE_CONFIDENCES = MIN_LABEL_CONFIDENCE


def _label_is_consumable(lab: StaffLabel) -> bool:
    return bool(lab.matched and lab.instrument
                and lab.confidence in CONSUMABLE_CONFIDENCES)


def _consumable(labels: list[StaffLabel]) -> int:
    """How many labels survive as far as a CONSUMER, not just as far as here.

    `_usable` counts `matched`, which is one notch too generous: a match made
    only by folding an OCR confusion is tagged `low` (`instruments.Match.
    confidence`), and every consumer drops `low`. So two readers can tie on
    `_usable` while one of them is contributing strictly less.

    MEASURED on `beethoven-sym5-mvt1-575951-p1`, the one scan-gate row whose
    PDF carries a text layer. Staff 8 prints `Violino II.`; the text layer
    encodes it `Yiolino II.`, which resolves to Violin only through the `Y`->`V`
    fold and is therefore `low`. Surya reads the same staff cleanly at `high`.
    Both readers score `_usable` 12, `12 > 12` is false, the text layer's copy
    is kept, and the page reaches the join with ELEVEN labels where Surya alone
    would have given twelve. Adding a stronger source and getting fewer labels
    is the shape this ladder has already been repaired for once, one notch
    coarser (raw presence vs `matched`, 2026-09-01); this is the same fault at
    the next notch down.
    """
    return sum(1 for lab in labels if _label_is_consumable(lab))


def _merge_key(labels: list[StaffLabel]) -> tuple[int, int]:
    """How two whole-page reads are ranked against each other.

    Quality first, reach second — a reader that resolves the same number of
    staves but more of them CONSUMABLY is the better read, and a reader that
    resolves more staves still wins when the consumable counts tie.
    """
    if not quality_merge_enabled():
        return (0, _usable(labels))
    return (_consumable(labels), _usable(labels))


def quality_merge_enabled() -> bool:
    """`OMR_LABEL_MERGE_QUALITY` — rank the reader rungs on consumability.

    **DEFAULT ON since 2026-09-06.** It changes which reader's text is kept on
    any page where a weaker rung ties a stronger one on `matched` alone.

    **The diagnosis, read off the printed page.** Staff 8 of Beethoven 5 p.1
    prints `Violino II.` with a blotted serif on the `V`. The PDF's own text
    layer — which is itself OCR, run once by someone else years ago — encodes it
    `Yiolino II.`, and `instruments.lookup` resolves that only by folding
    `Y`→`V`, which is tagged `low`. Consumers keep `high`/`medium` and drop
    `low`, so the label is **read correctly, carried correctly, and discarded at
    the join.** Surya reads the same staff cleanly and was never asked.

    **Three notches of one too-coarse test**, all fixed here: `_well_covered`
    returned before Surya ran at all — ⚠️ **contradicting this module's own
    docstring twice**, which documents the free rungs as unconditional; the
    `12 > 12` tie on `matched`, which is literally the fault the adjacent
    comment records fixing on 2026-09-01, one notch down; and Tesseract's
    raw-presence block, the documented live fault. ⚠️ The notch is **not the
    threshold** — 11 of 12 clears `0.75×12` however it is counted.

    ⚠️ **Tesseract's half is ONE-WAY on purpose**: an unresolved label yields
    only to a reading that *resolves*, never sideways. The first cut allowed
    sideways swaps and the row with the MOST changed staves gained nothing —
    unmatched `'I'`/`'III'` traded for unmatched `'|'`/`'HI'`/`'(1'`. A count of
    staves-changed scored that as the largest effect in the corpus.

    **Measured, one-directional everywhere:** 289 editions, 71 carry a text
    layer (24.6%); over the 29 with staves, **+24 consumable labels, 12 editions
    gain, 0 lose**. Engraved part names **67 → 71 correct, placeholders 2 → 0,
    4 of 4 better and 0 worse.**

    ⚠️ **BOTH BENCHMARKS ARE NULL, AND THE REASON IS THE POINT.** Scan gate
    0.8441 both ways on all 20 rows; engraved 0.1122 both ways. Established at
    three levels rather than assumed: the transcriptions DO differ (so the flag
    ran), the exports differ on 5 files, and **the entire export difference is
    `<part-name>`** — which musicdiff does not score. So the metric is blind to
    the only channel this acts through, not to the flag. Same footing as
    `OMR_ROSTER`, which shipped on for exactly this reason.

    **What would reverse it:** any edition where a rung's text gets *worse*.
    Every measurement so far is one-directional, and that is the claim to
    falsify. Record: `benchmarks/omr-label-ladder-2026-09/`.
    """
    return os.environ.get("OMR_LABEL_MERGE_QUALITY", "1").strip().lower() in (
        "1", "true", "yes", "on")


def _well_covered(labels: list[StaffLabel], pws) -> bool:
    """Has the text layer named enough of the largest system to stand alone?"""
    if not labels:
        return False
    by_system: dict[int, int] = {}
    for staff in pws.staves:
        by_system[staff.system_index] = by_system.get(staff.system_index, 0) + 1
    widest = max(by_system.values(), default=0)
    if not widest:
        return True
    named = {lab.staff_index for lab in labels if lab.matched}
    best = 0
    for system_index in by_system:
        hits = sum(1 for s in pws.staves
                   if s.system_index == system_index and s.staff_index in named)
        best = max(best, hits)
    return best >= LABEL_COVERAGE_OK * widest


def _labels_for_page(pws, pdf_path: Path, page_index: int, *,
                     assist, budget: list[int],
                     surya_fallback: bool = True,
                     ocr_fallback: bool = True,
                     tiers: list[int] | None = None,
                     review_dir: Path | None = None) -> list[StaffLabel]:
    """Instrument labels, cheapest reader first.

        PDF text layer  ->  Surya 2  ->  Tesseract  ->  whoever `assist` names

    The three free rungs run unconditionally; where they leave a system thinly
    covered, `assist` says who settles it — a person, the vision model, or
    nobody.

    TWO free margin readers, not one, and they are not redundant: they need
    different things installed. Surya wants a Python 3.10 venv and llama.cpp and
    reads better; Tesseract wants a brew binary and is everywhere. Each rung
    calls `available()` first, so a machine with neither falls straight through
    to the paid reader and a machine with either never pays.

        PDF text layer  ->  Surya 2 (local)  ->  Claude (paid)

    Each rung runs only where the one above came back empty. The two free rungs
    are tried unconditionally; the paid one is still gated on `vision_fallback`
    and on `budget`.

    `budget` is a one-element list of systems still allowed to be read by the
    PAID reader, mutated in place. It exists because instrument identity is a
    property of the SCORE, not of each page: slots propagate one reading across
    every system and page, so a handful of calls covers a whole work. Scores
    also label their first system most fully and abbreviate or omit later — so
    reading early systems buys the most, and reading all of them buys almost
    nothing extra. Surya takes no budget because it costs nothing.

    WHY SURYA IS ALL-OR-NOTHING PER PAGE rather than topping up the staves it
    missed. Its shortfall is not whole systems returning nothing — it is the odd
    staff whose printed label the lexicon rejects, and asking Claude about a page
    Surya has already largely read would spend the budget on pages that need it
    least. Measured, Surya and Claude disagree on nothing the ground truth can
    check; the gap is reach, not correctness. See
    `benchmarks/omr-margin-labels-2026-08/SURYA_BAKEOFF_2026-08-31.md`.
    """
    tiers = tiers if tiers is not None else [0, 0, 0, 0, 0]
    # Tier 1, free and instant: the PDF's own text layer.
    labels = read_staff_labels(pws)
    # NOT `if labels` — a PARTIAL text layer must not stop the ladder. A scanned
    # score's OCR layer is routinely patchy rather than absent, and that is the
    # case that matters: the Pastoral names 4 staves of 10 from its text layer,
    # so any-label-at-all kept the free margin readers from ever being asked,
    # and the four it names are all winds. Measured, reading the margin there
    # takes the page from 18 of 20 clefs to 20 of 20.
    tiers[0] += len(labels)
    # ⚠️ THIS EARLY RETURN CONTRADICTS THIS FUNCTION'S OWN DOCSTRING, twice
    # over: "the three free rungs run unconditionally" and "the two free rungs
    # are tried unconditionally; the paid one is still gated". They are not —
    # a text layer that clears `LABEL_COVERAGE_OK` returns here and the free
    # readers are never asked. `_well_covered` is a COST control, and the cost
    # it is protecting is the PAID rung's; Surya and Tesseract spend no budget.
    #
    # What it costs, measured on `beethoven-sym5-mvt1-575951-p1` (see
    # `_consumable`): the text layer names 12 of 12 staves, 11 of them
    # consumably, and returns here — so Surya, which reads all twelve cleanly,
    # never runs. The ladder ends with fewer labels than one of its own rungs
    # would have given alone. `11 >= 0.75 * 12` clears the bar whichever way
    # the bar is counted, so the notch is not in the THRESHOLD; it is that a
    # free rung is gated at all.
    #
    # Under `OMR_LABEL_MERGE_QUALITY` the free rungs run as the docstring says
    # they do, and `_merge_key` decides who wins. The residual cost is Surya's
    # wall time on pages that used to skip it — real, which is why this is a
    # flag and not a fix.
    if not quality_merge_enabled() and _well_covered(labels, pws):
        return labels

    if surya_fallback:
        from . import staff_labels_surya
        # `available()` keeps this silent on a machine that never built the
        # venv, so the free rung costs nothing to leave switched on.
        if staff_labels_surya.available():
            try:
                read = staff_labels_surya.read_staff_labels_surya(pws)
            except Exception as exc:                      # noqa: BLE001
                logger.warning("surya label fallback failed on page %s: %s",
                               page_index, exc)
            else:
                # Keep whichever read more — counting USABLE labels, for the
                # reason the paid rung below already states: a label the
                # lexicon cannot resolve reaches the join as nothing, so
                # counting it lets a worse read tie or beat a better one. This
                # rung compared RAW counts until 2026-09-01 while the rung
                # below compared usable ones, and the inconsistency cost a
                # page: Beethoven 9 p.30's text layer returns 8 labels of which
                # 6 resolve, Surya returns 7 of which 7 resolve, and `8 > 7`
                # kept the worse read.
                #
                # Surya used to run only where the text layer was silent, so
                # replacing wholesale was safe; now that it also runs on a
                # partly-covered page, replacing could throw away labels the
                # text layer had — which is why this is a comparison and not an
                # override.
                # ⚠️ AND `matched` IS STILL ONE NOTCH TOO GENEROUS, which is
                # what `OMR_LABEL_MERGE_QUALITY` fixes: an OCR-folded match is
                # tagged `low` and every consumer drops it, so a text layer
                # that resolves twelve staves of which eleven are consumable
                # TIES a Surya read whose twelve all are, and `12 > 12` keeps
                # the worse one. Exactly the fault this comment describes,
                # measured one notch further down. See `_consumable`.
                if _merge_key(read) > _merge_key(labels):
                    tiers[0] = 0
                    tiers[1] += len(read)
                    labels = read
                if not quality_merge_enabled() and _well_covered(labels, pws):
                    return labels

    # And the second free rung, below Surya because it reads less well but is
    # far likelier to be installed. Measured at 26 of 29 labels on two
    # hand-verified pages against the vision reader's 29, and 11 of 12 on a page
    # whose text layer gives NOTHING
    # (`benchmarks/omr-margin-labels-2026-08/TESSERACT_2026-08-31.md`).
    #
    # ADDITIVE ONLY. It is the least accurate reader here and the one most
    # likely to return a plausible wrong word — one of its 29 was `Ki.Tr.` for
    # `Kl.Tr.`, which resolves to Trumpet — so it fills staves that carry no
    # label yet and never overwrites one that does.
    if ocr_fallback:
        from . import staff_labels_tesseract
        if staff_labels_tesseract.available():
            # ⚠️ AND THIS SET IS THE DOCUMENTED LIVE FAULT, on RAW presence:
            # a staff where an earlier rung returned `'(C)'` — present, and
            # resolving to nothing — blocks Tesseract from supplying `'(C) Hr.'`
            # It is the same shape the Surya rung above was repaired for on
            # 2026-09-01, and the comment there names the fix.
            #
            # Under the flag the block is on RESOLUTION, not presence: a label
            # the lexicon could not turn into an instrument stops nothing.
            # ⚠️ Deliberately NOT extended to `low`-confidence labels, unlike
            # `_merge_key` above. This is the least accurate reader here and
            # the one most likely to return a plausible wrong word (`Ki.Tr.` ->
            # Trumpet), so letting it overwrite a weak-but-real reading from a
            # better rung is a trade nothing here has priced. Unmatched only.
            #
            # ⚠️ AND THE UNBLOCKING IS ONE-WAY: Tesseract may take over a staff
            # whose label is unresolved ONLY IF ITS OWN READING RESOLVES. The
            # spec is "an unresolved label must not out-rank a later rung's
            # output THAT DOES resolve" — where the later rung also resolves to
            # nothing it has no claim, and swapping is a pure text downgrade for
            # no gain.
            #
            # MEASURED, and it is the whole of the noise this change makes on
            # the scan gate. Without this clause `bach-brandenburg3-mvt1-468678
            # -p1` changes FIVE staves and gains nothing — Surya's `'I'` /
            # `'III'` (unmatched) replaced by Tesseract's `'|'`, `'[il'`, `'HI'`,
            # `'(1'` (also unmatched) — and `brahms-...-p1` staff 5 and
            # `-p3` staff 6 do the same. With it, that row goes blind and all
            # eight real gains are untouched, including the documented case
            # verbatim: `-p3` staff 19, `'(C)'` -> `'(C) Hr.'` -> Horn [high].
            held = {lab.staff_index: lab for lab in labels}

            def _tesseract_may_take(lab) -> bool:
                standing = held.get(lab.staff_index)
                if standing is None:
                    return True                  # empty staff — as it always was
                if not quality_merge_enabled():
                    return False                 # the fault, kept as it stands
                if standing.matched:
                    return False                 # never overwrite a real reading
                return lab.matched               # only trade up, never sideways

            added = [lab for lab in
                     staff_labels_tesseract.read_staff_labels_tesseract(pws)
                     if _tesseract_may_take(lab)]
            if added:
                # A staff whose only label was unresolved now has a resolved
                # one; drop the dead reading rather than shipping two labels
                # for one staff, which nothing downstream is written for.
                superseded = {lab.staff_index for lab in added}
                labels = [lab for lab in labels
                          if lab.staff_index not in superseded] + added
                tiers[2] += len(added)

    if assist.mode == "none" or _well_covered(labels, pws):
        return labels

    # Tier 3a, free but not cheap: ask the person who chose to be asked. Only
    # the staves a trigger fired on, and the machine's reading is the default,
    # so the common case is a keypress.
    if assist.mode == "human":
        from .staff_labels_human import read_staff_labels_human
        answered = read_staff_labels_human(
            pws, labels, assist, page_index=page_index,
            out_dir=Path(review_dir or ".omr-review"))
        if answered:
            already = {lab.staff_index for lab in labels}
            labels = labels + [a for a in answered if a.staff_index not in already]
            tiers[4] += len(answered)
        # A human may have handed the rest over mid-question; fall through so
        # the new mode takes effect on this page rather than the next.
        if assist.mode != "vision":
            return labels

    if budget[0] <= 0:
        return labels

    # Tier 3b, about a cent a system: the margin read by Claude.
    from .staff_labels_vision import read_staff_labels_vision
    n_systems = len({s.system_index for s in pws.staves})
    budget[0] -= n_systems
    try:
        read = read_staff_labels_vision(pws)
    except Exception as exc:                              # noqa: BLE001
        logger.warning("vision label fallback failed on page %s: %s", page_index, exc)
        return labels
    # Keep whichever read more. The margin reader is a whole-system read and
    # self-consistent, and it abstains on staves that carry no label — so more
    # labels from it is more evidence, not more guessing. Unlike tier 2 it MAY
    # override, because it is the most accurate of the three. If it comes back
    # thinner than what we have (or empty, because it failed), that stands.
    # Compare USABLE labels, not raw ones. A label the lexicon cannot resolve is
    # not evidence — it reaches the join as nothing at all — so counting it lets
    # a worse read tie a better one. Beethoven 5 p.48 is exactly that: the OCR
    # tier and the vision reader both return twelve labels, but OCR's ninth is
    # `A.` for `Tr. Alt.` and resolves to nothing, while the vision reader's
    # resolves to the trombones. Comparing raw counts kept the OCR read and cost
    # three clefs; comparing matched counts keeps the right one.
    #
    # A TIE GOES TO THIS RUNG, not to whichever cheap reader ran first. A count
    # cannot see that one of the labels it is counting is WRONG, so where the
    # counts cannot separate two readers the ladder's own accuracy ordering
    # must — and this is the rung it ranks highest. The call has already been
    # made and paid for by the time we get here, so preferring it costs nothing.
    # An EMPTY read is still not a tie: a reader that returned nothing because
    # it failed must never win the page, which is why `read` is tested and not
    # only its count.
    #
    # Measured on the ten-page hand-read corpus, `--contextual --dossier
    # --wide`, with `.venv-surya` renamed as the control:
    #
    #                          --assist none   --assist vision
    #     Surya absent               145             149
    #     Surya present, `>`         146             146
    #     Surya present, `>=`        146             149
    #
    # Before this, installing the free reader COST three staves on the paid
    # path and silently wasted the whole vision budget: the paid read was made
    # on every page and used on one. Beethoven 5 p.48 is where it shows —
    # twelve usable labels from either reader, `12 > 12` false, the cheaper one
    # kept, and the dossier join then anchors six staves instead of nine.
    #
    # WHAT IS NOT ESTABLISHED, recorded so nobody re-derives a wrong answer:
    # WHICH label makes the two twelves behave differently. Read the measured
    # readings before assuming; they have moved between sessions on identical
    # input, which is itself unexplained.
    #
    # 2026-09-01, 45 replays of frozen crop bytes across warm, cold, concurrent
    # x4 and x8, mixed with other pages' crops, and 1/8/16 llama.cpp slots:
    # staff 10 reads `Tr. Teq.` -> Trumpet at MEDIUM confidence every time, and
    # that IS a wrong instrument on a trombone staff. An earlier session
    # recorded `Tr. Ten.` -> Trombone as consistently, on the same commit and
    # the same crop, and no version of surya, llama.cpp or the GGUF differs.
    # Staff 0 moved the same way: `'Fl. pic.'` now, `'Fl. fl. pic.'` then.
    #
    # Surya is NOT load-dependent — that hypothesis was tested and refused, and
    # the disputed character is decided at p=0.991 with a 5.53-nat margin, so
    # batching cannot be what moves it. The only sampled path in surya's client
    # is `_should_retry`, which raises the temperature on a failed or repetitive
    # request; a retry is silent in production because worker stderr is
    # discarded. See benchmarks/omr-clef-geometry/RESULTS.md, "JOB A".
    if read and _usable(read) >= _usable(labels):
        # The vision read replaces what the cheap tiers found, so the credit
        # does too — otherwise the summary would name tiers that were overruled.
        tiers[0] = tiers[1] = tiers[2] = 0
        tiers[3] += len(read)
        return read
    return labels


def apply_contextual_analysis(
    result: dict[str, Any],
    *,
    pdf_path: str | Path | None = None,
    dpi: int | None = None,
    apply_clefs: bool = True,
    dossier: dict[str, Any] | None = None,
    assist: "Assist | None" = None,
    vision_system_budget: int = 3,
    surya_fallback: bool = True,
    ocr_fallback: bool = True,
    staved: list[Any] | None = None,
    review_dir: Path | None = None,
    instrument_clef_default: bool | None = None,
) -> dict[str, Any]:
    """Annotate a transcribe result with part identity, and fix clefs the
    detector never read.

    Mutates `result` in place and returns a summary. Staff dicts gain
    `slot_index` / `instrument`, and any staff whose clef is questioned gains
    `clef_proposal`. Returns counts plus the reference layout, so a caller can
    report what was inferred.

    Labels come from up to five readers. The three free ones always run — the
    PDF text layer, then Surya, then Tesseract. Where they leave a system thinly
    covered, `assist` says who settles it: a person, the vision model, or nobody.

    **`assist` is required and has no default.** The two that cost something
    spend different things — a cent a system, or somebody's attention — and
    choosing one silently would spend one of them without asking. Pass
    `Assist("none")` to say explicitly that neither should be spent.

    The summary reports `label_tiers` and `assist`, because which reader answered
    changes how far the labels can be trusted and should never have to be
    guessed.
    """
    from .assist import Assist

    if assist is None:
        raise TypeError(
            "apply_contextual_analysis() needs an `assist`: who resolves the "
            "margin where the free readers fall short. There is deliberately no "
            "default — pass Assist('human'), Assist('vision'), or Assist('none') "
            "to say that neither should be spent. See tools/omr/assist.py.")
    if instrument_clef_default is None:
        # None means "the caller has no opinion": honor the env flag, so a
        # benchmark that calls this directly (eval_pipeline_clefs) exercises
        # the same configuration a transcription would. Default OFF.
        #
        # ⚠️ `os` is imported at MODULE level, not here. A function-local
        # `import os` inside this `if` makes `os` local to the WHOLE function,
        # so any other `os.environ` read further down raises UnboundLocalError
        # on the branch where a caller passed an explicit bool.
        instrument_clef_default = os.environ.get(
            "OMR_INSTRUMENT_CLEF_DEFAULT", "0").strip().lower() not in (
            "0", "", "false", "no", "off")
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

    # `transcribe` already rendered and detected every page, so it passes its
    # own `pws` list rather than paying for phase 1 twice. That is also a
    # CORRECTNESS point, not only a speed one: re-detecting could hand this pass
    # a different set of staves from the ones already written into `result`, and
    # the slot indices would then be attached to the wrong staves.
    #
    # The check runs FIRST, before any reader is consulted or any page is
    # opened, because it is pure argument checking and depends on nothing else.
    # It used to sit below the `unlabelled` computation, where it was only
    # reachable on the paths that survived that I/O: on a machine with no
    # `.venv-surya`, `has_text_layer` opened the file first and a caller who had
    # passed a mismatched list got a PyMuPDF file error instead of the mismatch
    # that actually caused it.
    if staved is not None and len(staved) != len(page_indices):
        raise ValueError(
            f"staved has {len(staved)} pages, result has {len(page_indices)}"
        )

    # No text layer used to end the analysis here: with no labels there was no
    # instrument identity, and everything downstream of identity was
    # unavailable. Score order supplies a second source — instruments appear in
    # family order and never out of it, so position alone says a good deal —
    # and it needs no text at all. The run continues, and `score_layouts`
    # decides for itself whether the page says enough to name anything.
    #
    # Surya counts as a reader here for the same reason the paid one does: a
    # page with no text layer is only "unlabelled" when nothing can read the
    # margin. `available()` is checked rather than assumed so a machine without
    # the venv takes the old path exactly as before.
    # Is there ANY reader for the margin? Whoever `assist` names, plus the two
    # free ones where they are installed. Only if none of them can run does a
    # page with no text layer have nothing to hope for.
    can_read_margin = assist.mode != "none"
    if not can_read_margin and surya_fallback:
        from . import staff_labels_surya
        can_read_margin = staff_labels_surya.available()
    if not can_read_margin and ocr_fallback:
        from . import staff_labels_tesseract
        can_read_margin = staff_labels_tesseract.available()
    unlabelled = (
        not can_read_margin
        and not any(has_text_layer(pdf_path, i) for i in page_indices)
    )

    budget = [vision_system_budget]
    # Labels credited to each reader, page set wide:
    # [text layer, Surya, Tesseract, vision, human].
    tiers = [0, 0, 0, 0, 0]
    labels = []
    staff_labels_per_page = []

    if staved is None:
        staved = [detect_staves(render_page(pdf_path, i, dpi=dpi))
                  for i in page_indices]

    for page_index, pws in zip(page_indices, staved):
        read = [] if unlabelled else _labels_for_page(
            pws, pdf_path, page_index,
            assist=assist, budget=budget,
            surya_fallback=surya_fallback, ocr_fallback=ocr_fallback,
            tiers=tiers, review_dir=review_dir)
        staff_labels_per_page.append(read)
        labels.append(labels_by_staff(read))

    reference = assign_slots(staved, labels)
    if not reference:
        summary["reason"] = "no reference layout could be built"
        return summary

    # ── The document's roster ────────────────────────────────────────────────
    # Read ONCE, from the first system of the document that carries names, and
    # available to every page of the run — including pages this run never asked
    # for, which is the whole point: a score names its orchestra on the first
    # system of the movement and abbreviates or omits it everywhere after.
    #
    # ACQUISITION IS UNCONDITIONAL AND ITS RESULT IS RECORDED; only its USE is
    # behind `OMR_ROSTER`. Recording what the margin said changes no music, and
    # a signal read correctly and then discarded is the shape this project has
    # paid for nine times. What the flag gates is whether a roster name is
    # allowed to NAME A SLOT.
    roster: Roster | None = None
    if not unlabelled:
        try:
            roster = acquire_roster(
                pdf_path=pdf_path, dpi=dpi, run_pages=page_indices,
                run_staves=staved, run_labels=staff_labels_per_page,
                read_labels=lambda pws, i: _labels_for_page(
                    pws, pdf_path, i, assist=assist, budget=budget,
                    surya_fallback=surya_fallback, ocr_fallback=ocr_fallback,
                    tiers=tiers, review_dir=review_dir),
            )
        except Exception as exc:                              # noqa: BLE001
            # An enrichment that could not run must not lose a transcription
            # that succeeded — the same contract every optional pass here has.
            logger.info("roster acquisition unavailable: %s", exc)
    summary["roster"] = roster.evidence() if roster else None

    instrument_by_slot = _instrument_by_slot(reference)
    page_read_slots = set(instrument_by_slot)
    # Where the roster names a slot the reference system did not, it supplies
    # the name — and its provenance says so. ⚠️ It never OVERRIDES a name read
    # on a page of this run: a label printed on the page the reader is looking
    # at outranks one carried from another page, and `setdefault` is what keeps
    # that true.
    roster_by_slot: dict[int, Instrument] = {}
    if roster is not None and roster_enabled():
        roster_by_slot = _roster_instrument_by_slot(roster, reference)
        for slot_index, instrument in roster_by_slot.items():
            instrument_by_slot.setdefault(slot_index, instrument)
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
    #
    # A slot named by an AMBIGUOUS alias is withheld — see
    # `_ambiguous_label_slots`. It is the one kind of label the prior is meant
    # to overturn, and feeding it in first is what stopped it: the prior was
    # being asked to confirm the reading it exists to question.
    clef_by_slot = _read_clefs_by_slot(pages, slot_by_staff)
    ambiguous_slots = _ambiguous_label_slots(
        staff_labels_per_page, slot_by_staff, page_indices, staved)
    fit_labels = {s.index: s.instrument for s in reference
                  if s.instrument and s.index not in ambiguous_slots}
    # A roster name is a label — printed on the page the roster came off and
    # read by the same ladder — so it CONSTRAINS the prior exactly as the
    # reference system's own labels do. Withholding it would leave the prior
    # guessing at slots the document has already named, which is the shape this
    # whole workstream is about.
    #
    # ⚠️ EXCEPT at an ambiguous slot, and the exception is not a special case —
    # it is the same rule. `ambiguous_slots` is withheld because the AMBIGUITY
    # LIVES IN THE LEXICON, NOT IN THE READING: `Basso.` at the foot of a string
    # section resolves to `Bass voice` no matter which page it was read from, so
    # a roster inherits the unsettleable answer rather than settling it. Refilling
    # it here handed the prior exactly the reading the prior exists to overturn,
    # every voter abstained (no orchestral layout has a voice anywhere), and
    # `resolve_ambiguous_label` returned None — measured 2026-09-06 as 7 staves
    # exported as a SINGER on 9 orchestral rows (Beethoven `Basso.`, Mahler
    # `Bässe`, Mozart 41 and Tchaikovsky 6 `Basso`, and a truncated
    # `'mbone Basso'` — a bass TROMBONE). Controlled A/B, roster off: support
    # `Contrabass 0.643 / Cello 0.357`, which reproduces
    # `resolve_ambiguous_label`'s own docstring figure to the digit.
    #
    # ⚠️ Nothing in the metric could have caught this. The roster shipped on a
    # measured 0 edits, correctly argued — musicdiff does not score
    # `<part-name>` — and that same blindness hides this. A consumer the metric
    # cannot see needs a check the metric is not.
    for slot_index, instrument in roster_by_slot.items():
        if slot_index in ambiguous_slots:
            continue
        fit_labels.setdefault(slot_index, instrument.name)
    fit = fit_layouts(
        len(reference), labels=fit_labels, clefs=clef_by_slot)
    # The RAW text of each slot's margin label, kept beside the instrument the
    # lexicon resolved it to. `lookup` answers "which instrument", which is a
    # singular noun — so `Flauti`, `2 Flöten` and `Flauto` all resolve to
    # `Flute` and the PLURALITY is thrown away at that call. That is the
    # project's recurring shape (a signal read correctly and dropped
    # downstream), and it is the one signal a condensed-staff reader needs.
    # Retained as data only: nothing here interprets it.
    raw_label_by_slot: dict[int, str] = {}
    for page_index, pws, page_labels in zip(page_indices, staved,
                                            staff_labels_per_page):
        by_staff = {lab.staff_index: lab.text for lab in page_labels
                    if (lab.text or "").strip()}
        for staff in pws.staves:
            text = by_staff.get(staff.staff_index)
            if text and staff.slot_index >= 0:
                raw_label_by_slot.setdefault(staff.slot_index, text.strip())

    # Per-FACT provenance, which is what makes the carry implementable at all:
    # `probe_roster_carry.py` measured observed identity carrying at 22/22 and
    # DERIVED identity carrying at 0.550, so a layer that cannot say, of each
    # individual name, whether it was read or deduced cannot carry safely.
    #
    #   label   printed on a page of THIS run and read there
    #   roster  printed on the document's roster system and carried here
    #   score_order / score_order_ambiguity   deduced from where the staff sits
    instrument_source: dict[int, str] = {
        i: ("label" if i in page_read_slots else "roster")
        for i in instrument_by_slot}
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

    # ── The absent-instrument veto (OMR_ABSENT_INSTRUMENT_VETO, off) ─────────
    # A whole-document reference is the FINALE's lineup, and a reduced earlier
    # system aligned into it can take a slot whose instrument the movement does
    # not contain. See `absent_instrument.py` for the measurement and the rule.
    # `report` records the evidence and changes nothing, so one expensive run
    # supports an offline sweep over the window.
    _veto_mode, _veto_window, _veto_rule = veto_config()
    absent_vetoes: list[dict] = []
    vetoed_keys: set[tuple[int, int, int]] = set()
    if _veto_mode != "off":
        _evidence = label_evidence(page_indices, staff_labels_per_page)
        _keys = [k for k in slot_by_staff]
        _name_by_slot = {s: i.name for s, i in instrument_by_slot.items()}
        # Computed in BOTH modes, so `report` can price the veto on a benchmark
        # whose scored artefact must not move: the names are only withheld in
        # `apply`. In `report` the window is the default one, since the sweep
        # recomputes every other window from the recorded evidence anyway.
        absent_vetoes = find_vetoes(
            staff_keys=_keys, slot_by_staff=slot_by_staff,
            instrument_name_by_slot=_name_by_slot,
            instrument_source=instrument_source, evidence=_evidence,
            window=_veto_window if _veto_mode == "apply" else DEFAULT_WINDOW,
            rule=_veto_rule, reference_size=len(reference))
        if _veto_mode == "apply":
            vetoed_keys = {(r["page_index"], r["system_index"],
                            r["staff_index"]) for r in absent_vetoes}
        summary["absent_instrument_veto"] = {
            "mode": _veto_mode,
            "window": _veto_window,
            "rule": _veto_rule,
            "reference_size": len(reference),
            # The raw material, so the sweep needs no second transcription.
            "label_evidence": [
                {"page_index": p, "staff_index": si, "instrument": nm}
                for p, by_staff in sorted(_evidence.items())
                for si, nm in sorted(by_staff.items())],
            "staff_slots": [
                {"page_index": k[0], "system_index": k[1], "staff_index": k[2],
                 "slot": v} for k, v in sorted(slot_by_staff.items())],
            "slot_instruments": [
                {"slot": s, "instrument": n,
                 "source": instrument_source.get(s, "label")}
                for s, n in sorted(_name_by_slot.items())],
            "vetoes": absent_vetoes,
        }

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
                raw = raw_label_by_slot.get(slot)
                instrument = instrument_by_slot.get(slot)
                if key in vetoed_keys:
                    # Vetoed: the staff is left UNNAMED rather than given a
                    # second guess. `slot_index` stays — it is an observation.
                    #
                    # ⚠️ `instrument_label` does NOT stay, and that is the whole
                    # point of the veto stated in one field. `raw_label_by_slot`
                    # is the raw text of the FIRST page in the run that labelled
                    # this slot, stamped onto every staff of the slot on every
                    # page — so on a vetoed staff it is the text of a label
                    # printed twenty pages away, and leaving it beside
                    # `instrument_veto` would put the discarded evidence back on
                    # the record as though the page carried it. (This carry is
                    # also what makes a "does the staff's own label agree with
                    # its name" audit unable to disagree.)
                    instrument = None
                    raw = None
                    staff["instrument_veto"] = "absent_instrument"
                if raw:
                    staff["instrument_label"] = raw
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
    #
    # ⚠️ ROSTER-SOURCED IDENTITY IS HELD OUT OF THE CLEF CONSUMER BY DEFAULT,
    # and the reason is REACH rather than doubt about the roster. `clef_correction`
    # has two paths: FILL applies only where NO reader read a clef, and OVERRIDE
    # (gated separately on `OMR_INSTRUMENT_CLEF_DEFAULT`) requires source
    # `label`. Measured on the 20-row gate, 91.4% of staves already carry a read
    # clef, so FILL's population is 34 staves — and the staves a roster newly
    # names and the staves needing a fill are very nearly DISJOINT, which is why
    # a perfect-precision roster tier priced at exactly **0 edits**
    # (`benchmarks/omr-staff-identity-layer-2026-09/price_clef_consumer.py`,
    # tier B). A consumer that moves zero edits ships disabled. `OMR_ROSTER_CLEF`
    # exists so the finding is reproducible, not because the default is in doubt.
    _roster_to_clef = os.environ.get(
        "OMR_ROSTER_CLEF", "0").strip().lower() in ("1", "true", "yes", "on")
    # ⚠️ `score_order_ambiguity` stays ADMITTED, exactly as before this block
    # existed — it is a label the prior disambiguated, not a name the prior
    # invented, and changing that is not this workstream's to change.
    _not_clef_evidence = {"score_order"}
    if not _roster_to_clef:
        _not_clef_evidence.add("roster")
    read_instruments = {
        slot: inst for slot, inst in instrument_by_slot.items()
        if instrument_source.get(slot) not in _not_clef_evidence
    }
    # Fill defaulted clefs from the same part in another system BEFORE the
    # instrument pass, so that pass sees the borrowed reading and leaves those
    # staves alone — a clef read on the page outranks one deduced from an
    # instrument's convention.
    clefs_filled = _fill_defaulted_clefs(pages, slot_by_staff) if apply_clefs else []

    # The work itself, where one was supplied and the part-join is anchored.
    labels_by_slot: dict[int, str] = {}
    for page_index, pws, page_labels in zip(page_indices, staved, labels):
        for staff in pws.staves:
            name = page_labels.get(staff.staff_index)
            if name and staff.slot_index >= 0:
                labels_by_slot.setdefault(staff.slot_index, name)
    dossier_clefs = (
        _apply_dossier_clefs(pages, slot_by_staff, reference, labels_by_slot, dossier)
        if (dossier and apply_clefs) else []
    )

    # The OMR_INSTRUMENT_CLEF_DEFAULT tier (off by default; see
    # clef_correction.py's tables and benchmarks/omr-clef-string-staves-2026-09
    # for the sites that earned each entry). The change veto runs FIRST so a
    # staff whose mid-staff state it repairs is uniform again before the
    # header tier asks its uniformity question.
    # A vetoed staff has no instrument, so it must not reach a consumer that
    # reasons FROM the instrument. Hiding it here rather than mutating
    # `slot_by_staff` keeps slot identity (which is an observation) intact for
    # everyone else, including `_fill_defaulted_clefs`, which reads clefs across
    # a slot and never asks what the slot is called.
    clef_slot_by_staff = ({k: v for k, v in slot_by_staff.items()
                           if k not in vetoed_keys}
                          if vetoed_keys else slot_by_staff)
    change_vetoes = (
        veto_implausible_clef_changes(
            pages, read_instruments, clef_slot_by_staff, instrument_source)
        if (instrument_clef_default and apply_clefs) else []
    )

    records = correct_clefs_from_instruments(
        pages, read_instruments, clef_slot_by_staff, apply=apply_clefs,
        treble_override=(instrument_clef_default and apply_clefs),
        instrument_source_by_slot=instrument_source)

    # Labels that were READ off the page and then dropped. This is reported
    # because the failure is otherwise invisible: a label the lexicon cannot
    # match produces no label, which is indistinguishable from a staff that
    # carries no label at all — and the two want opposite responses. One is the
    # engraving telling you nothing; the other is an alias missing from
    # `instruments.py`, with the text you need sitting right there.
    #
    # Measured on Mahler 5 p.4: the margin reader returned seventeen labels, all
    # seventeen correct, and eight of them fell out here in silence. Nothing in
    # the pipeline said so — the page simply behaved like a sparsely labelled
    # one. See `benchmarks/omr-part-staff-join-2026-08/RESULTS.md`.
    unresolved = sorted({lab.text.strip() for page_labels in staff_labels_per_page
                         for lab in page_labels
                         if not lab.matched and lab.text.strip()})
    low_confidence = sorted({lab.text.strip() for page_labels in staff_labels_per_page
                             for lab in page_labels
                             if lab.matched and lab.staff_index not in
                             {k for l in labels for k in l}})
    if unresolved:
        logger.warning(
            "%d margin label(s) read but NOT MATCHED by the lexicon, so they were "
            "dropped and this page will behave as if unlabelled there: %s — "
            "these are the strings to add to tools/omr/instruments.py",
            len(unresolved), ", ".join(repr(t) for t in unresolved))

    summary.update(
        available=True,
        label_tiers={"text_layer": tiers[0], "surya": tiers[1],
                     "tesseract": tiers[2], "vision": tiers[3],
                     "human": tiers[4]},
        assist=assist.summary,
        unresolved_labels=unresolved,
        low_confidence_labels=low_confidence,
        reference=[{"slot": s.index, "group": s.group_index,
                    "instrument": s.instrument} for s in reference],
        labelled_staves=sum(len(l) for l in labels),
        layout=(fit.layout.name if fit else None),
        layout_named_slots=(fit.n_named if fit else 0),
        instruments_from_score_order=sum(
            1 for v in instrument_source.values() if v == "score_order"),
        instruments_from_roster=sum(
            1 for v in instrument_source.values() if v == "roster"),
        roster_slots_offered=len(roster_by_slot),
        ambiguous_labels_resolved=sum(
            1 for v in instrument_source.values() if v == "score_order_ambiguity"),
        proposals=records,
        clefs_applied=sum(1 for r in records if r["applied"]),
        clefs_filled_from_slot=len(clefs_filled),
        clef_fills=clefs_filled,
        clefs_from_dossier=len(dossier_clefs),
        dossier_clefs=dossier_clefs,
        noteheads_restated=sum(r.get("noteheads_restated", 0) for r in records),
    )
    if instrument_clef_default:
        # Only under the flag, so a default run's JSON is byte-identical.
        summary.update(
            clef_treble_overrides=sum(
                1 for r in records if r.get("override") == "treble_misread"),
            clef_change_vetoes=change_vetoes,
        )
    return summary
