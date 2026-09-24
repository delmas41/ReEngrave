"""The key signature — positions gathered clef-free, named with the clef."""

from __future__ import annotations

import os

from typing import Dict, List, Optional

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import Kind, Q, Scope, State

#: ⚠️⚠️ DEFAULT **ON** SINCE 2026-09-22 (evening) — **SEAN'S CALL**, on the
#: measurement in `benchmarks/omr-document-identity-2026-09/FINDINGS.md`: key
#: signature right **26 -> 47** of 50 and wrong **24 -> 3** on the engraved
#: fixture, **4 parts better and 0 worse** in the file, with exactly two
#: quantities moving of 29. It shipped OFF the same day because the evidence
#: was n = 1 document and 1 renderer with no print consulted; **those limits
#: are unchanged and are not what the flip rests on** — it rests on the rule
#: being ONE-SIDED, so every input the new fact cannot speak about keeps the
#: shipped behaviour exactly.
#:
#: ⚠️ THE OFF TEST IS A **DENY-LIST** BECAUSE THE DEFAULT IS ON. CLAUDE.md's
#: *"A flag's OFF test must follow its DEFAULT"*, under which five shipped
#: flags had it backwards: under a default-ON flag an allow-list would let an
#: empty value or a typo silently RESTORE the old precedence.
#: `test_flag_default_direction.py` derives this from the source and checks it.
ENGRAVED_KEYSIG_ENV = "OMR_ENGRAVED_KEYSIG"


def _engraved_keysig_enabled() -> bool:
    return os.environ.get(ENGRAVED_KEYSIG_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


def _proved_engraved(ev: Evidence) -> bool:
    """Is THIS DOCUMENT measured engraved? Anything else answers False.

    ⚠️⚠️ **ONE-SIDED, AND EVERY OTHER INPUT FALLS THROUGH TO THE SHIPPED
    PRECEDENCE.** A scan, a classifier abstention, a document with no identity
    row, a record gathered before this rung existed -- all four answer False
    and change nothing. That is this repo's standing rule for a new gate, and
    here it is load-bearing rather than tidy: the template's 20-right/0-wrong
    is an ENGRAVED figure, and on a scan the staff-line erasure works FOR the
    locator (it takes accidental-sized clusters 5 -> 11 on the Litolff plate,
    because there the lines MERGE glyphs and erasing SEPARATES them). The
    template's over-counting risk is exactly what the shipped refusal was
    written about and that side is NOT measured for accuracy.

    ⚠️ IT READS THE **MEASURED** ROW, NEVER `image_type`. The catalog's label
    is IMSLP's crowd-sourced string; it is filed beside this as a second
    witness and it is not what any decision keys on. It is also structurally
    unable to serve here: the engraved fixture is a render in no catalog, so
    the catalog row ABSTAINS on it while the container reader answers.

    ⚠️ `SELF_AND_ANCESTORS` IS NOT OPTIONAL. `Q.INPUT_DOMAIN` is filed on the
    DOCUMENT and this decision is `Kind.STAFF`; a bare `ev.rows(...)` returns
    nothing on every page forever, which is the fault `adjudicate_instrument`
    records against `Q.ROSTER_ENTRY` in the same words -- and it fails SILENT,
    reading exactly like an honest document with no identity.
    """
    if not _engraved_keysig_enabled():
        return False
    for row in ev.rows(Q.INPUT_DOMAIN, scope=Scope.SELF_AND_ANCESTORS):
        if str(row.value) == "engraved":
            return True
    return False


def _template_fit(ev: Evidence, clef):
    """The template reader's row for the SETTLED clef, and its fifths.

    ⚠️ IT RETURNS THE **ROW**, NOT A `Ruling`, AND THAT IS DELIBERATE. An
    earlier draft took the reason word as a PARAMETER and built the Ruling
    here, which is tidier and defeats `brakes --check`: that tool judges
    statically whether every declared reason is reachable, and a reason
    arriving as an argument made `fitted_by_template` and
    `fitted_by_template_engraved` UNRESOLVED -- exactly the trade INFER
    refused when it wrote two flag predicates out separately rather than share
    a helper taking the flag name, *"because the derived flag-direction scan
    finds flags by AST and a helper taking the name as a parameter would hide
    both."* The lookup is shared; the two literal reasons stay at their call
    sites where a derived check can see them.
    """
    for row in ev.rows(Q.KEYSIG_TEMPLATE_FIT):
        if str(row.value) != str(clef.value):
            continue
        fifths = row.detail.get("fifths")
        if fifths is None:
            continue
        return row, int(fifths)
    return None, None


def _template_detail(row) -> dict:
    return {"n_accidentals": row.detail.get("n_accidentals"),
            "accidental": row.detail.get("accidental"),
            "decided_by": "template"}


def _marker_ink(ev: Evidence, subject=None) -> dict:
    """What the DETECTOR saw of this staff's key accidentals, for a REFUSAL.

    ⚠️⚠️ THIS FUNCTION'S OWN PREMISE EXPIRED ON 2026-09-23 AND THE HISTORY IS
    KEPT BECAUSE IT IS THE COST SIDE OF THE RULE THAT REPLACED IT. It used to
    say *the count is not the answer*, on two measurements: the LEGACY path's
    fallback to counting markers cost **seven spurious key flips over eleven
    scanned pages, every one landing on exactly one accidental**
    (`key_signature_corroboration.py`), and over the staves this decision
    DECIDED the marker count equalled `|fifths|` on only **19 of 49**
    (Litolff) and **39 of 76** (Breitkopf).

    ⚠️ BOTH NUMBERS STAND; WHAT CHANGED IS WHICH SIDE THEY CONDEMN. The
    second one was read as *the markers are unreliable*, and scoring both
    readings against the movement's own key showed it was the FITTERS that
    disagreed: 330 right against 171 on Breitkopf, 50 against 45 on the
    engraved page. Litolff is the document where the old reading holds —
    +10 right and +15 wrong there — and the system check is what answers it.
    `_marker_run` is the reader now; this is only the detail a REFUSAL
    carries, so that a staff nobody could read says WHICH kind of silence it
    fell into.
    """
    marks = ev.rows(Q.KEYSIG_MARKER, subject=subject)
    if not marks:
        # ⚠️ ABSENT AND DECLINED ARE DIFFERENT HERE TOO. `ev.state` separates
        # "the detector produced no row" from "it produced a row saying it saw
        # nothing", and collapsing them would reintroduce, one level down,
        # exactly the fault this detail exists to repair.
        return {"keysig_marker_ink": 0,
                "keysig_marker_state": str(ev.state(Q.KEYSIG_MARKER,
                                                    subject=subject))}
    return {"keysig_marker_ink": len(marks),
            "keysig_marker_state": str(ev.state(Q.KEYSIG_MARKER,
                                                subject=subject)),
            "keysig_marker_classes": sorted({str(m.value) for m in marks})}


# ─────────────────────────────────────────────────────────────────────────────
# The run the DETECTOR drew, read as a ladder of slots
# ─────────────────────────────────────────────────────────────────────────────

_FLAT = "keyFlat"
_SHARP = "keySharp"
_NATURAL = "keyNatural"

#: Two marker boxes closer than this, in the CELL's own staff spaces, are ONE
#: slot. ⚠️ Measured, not chosen: on the engraved fixture Violin 1 carries
#: four `keyFlat` boxes at canonical x 375 / 461 / 463 / 545 with a cell staff
#: space of 85 px — the printed slots stand 86 and 83 px apart (≈1.0 space)
#: and the spurious pair 2 px apart, so anything from 0.03 to 0.9 spaces
#: separates the two populations and 0.5 sits in the middle of that gap.
MARKER_SLOT_TOLERANCE_SPACES = 0.5

#: Two slots further apart than this are not one RUN. A signature's
#: accidentals stand about ONE space apart; a mark this far right of the last
#: one is in the first BAR, not in the header — and cell 0 holds both.
MARKER_RUN_GAP_SPACES = 2.0

#: Circle-of-fifths limit. A run longer than this is not a key signature.
MAX_FIFTHS = 7


def _cell0_space(ev: Evidence, subject=None) -> float:
    """One staff space in the frame the marker x's are measured in.

    ⚠️⚠️ `Q.CELL_STAFF_SPACE`, NEVER `Q.STAFF_SPACING`. The marker rows carry
    `x_canonical` — the CELL's own rescaled frame — while `staff_spacing` is
    page pixels; on the engraved fixture those read 85 and 22.5 for ONE staff.
    Two frames under one name is how a consumer comes to compare lengths that
    were never in the same units (`record.Q.CELL_STAFF_SPACE` says so in those
    words), and here it would decide how many flats are printed.

    ⚠️ It is filed on the CELL, a DESCENDANT of the staff, so the scope is not
    optional — and the cell INDEX must be checked, because every bar of the
    staff files one and only cell 0 is the header's.
    """
    for row in ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=subject):
        if row.subject.cell == 0:
            try:
                value = float(row.value)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    # ⚠️ A FALLBACK THAT CANNOT INVENT A READING, ONLY REFUSE ONE. With no
    # measured space the slot test has no unit, so `_marker_run` returns
    # `no_cell_scale` and this decision abstains rather than clustering raw
    # pixels against a nominal that is wrong on half the cells of a
    # conductor's page.
    return 0.0


def _marker_run(marks, space: float):
    """The detector's key accidentals as `(fifths, reason, detail)`.

    ⚠️⚠️ THIS IS THE READING, AND UNTIL 2026-09-23 IT WAS READ BY NOTHING.
    `Q.KEYSIG_MARKER` was declared in this decision's `wants` AND in its
    `composed_from` from the day it was written, and every use of it was a
    DETAIL field (`_marker_ink`) explicitly labelled *not a proposed value*.
    The boxes were on the record the whole time: on the engraved acceptance
    page every staff carries three `keyFlat` boxes at score 0.91–0.94 while
    the header fitter reported ONE accidental, and the file wrote one flat.
    Sean, 2026-09-23: *"we just need to know what to do with the 3 boxes
    around the 3 flats on every staff."*

    ⚠️ SLOTS, NOT BOXES (conventions `[C21]`: the accidentals stand at fixed
    slots in a fixed order, so *the Nth accidental is fully determined by N*).
    Counting boxes reads Violin 1's neighbour-bleed pair as a fourth flat;
    counting SLOTS does not — the cell is padded 4 staff spaces and on a
    conductor's page that reaches the next staff's ink (CLAUDE.md §10).

    ⚠️ AND THE RUN IS A LADDER. `gather._gather_keysig_markers` reads
    `R.cell(p, s, i, 0)` — the whole first MEASURE, header and first bar
    together — so an accidental printed inside bar 1 is in this population.
    The chain stops at the first gap wider than `MARKER_RUN_GAP_SPACES`.

    ⚠️ MIXED KINDS ABSTAIN. A standard signature carries one kind only
    (`transcribe._staff_key_fifths` states it in the same words), so sharps
    and flats in one run is not a reading of anything; and an all-`keyNatural`
    run is a CANCELLATION, which this record has nowhere to put.
    """
    if not marks:
        return None, "no_markers", {}
    kinds = sorted({str(m.value) for m in marks})
    xs = sorted(float(m.detail.get("x") or 0.0) for m in marks)
    base = {"keysig_marker_ink": len(marks), "keysig_marker_classes": kinds}
    if len(kinds) > 1:
        return None, "mixed_marker_kinds", base
    if space <= 0:
        return None, "no_cell_scale", base
    centres = [xs[0]]
    for a, b in zip(xs, xs[1:]):
        if b - a > MARKER_SLOT_TOLERANCE_SPACES * space:
            centres.append(b)
    slots = 1
    for a, b in zip(centres, centres[1:]):
        if b - a > MARKER_RUN_GAP_SPACES * space:
            break
        slots += 1
    base.update(keysig_marker_slots=len(centres), keysig_run_slots=slots,
                cell_staff_space=space)
    if kinds == [_NATURAL]:
        return None, "natural_markers", base
    if slots > MAX_FIFTHS:
        return None, "too_many_markers", base
    if kinds == [_FLAT]:
        return -slots, "markers", base
    if kinds == [_SHARP]:
        return slots, "markers", base
    return None, "mixed_marker_kinds", base


def _fit_for_clef(rows, clef):
    """The reader's row for the SETTLED clef, and its fifths."""
    for row in rows:
        if str(row.value) != str(clef.value):
            continue
        fifths = row.detail.get("fifths")
        if fifths is None:
            continue
        return row, int(fifths)
    return None, None


def _staff_reading(ev: Evidence, subject=None) -> Optional[Ruling]:
    """What ONE staff's header says, before any system check.

    Returns `None` where the clef abstained — the guard, expressed as a
    dependency rather than as a boolean inside a reader.

    ⚠️ IT TAKES AN EXPLICIT SUBJECT so `adjudicate_system_key`, which is
    `Kind.SYSTEM`, reads every staff of its system through THIS function
    rather than a second copy of the precedence. One projection, two callers
    — `_spans_from_numbering`'s discipline, and the reason the tally and the
    staff verdict cannot drift apart.
    """
    clef = ev.verdict(Q.CLEF, subject=subject)
    if clef is None or clef.value is None:
        return None

    marks = ev.rows(Q.KEYSIG_MARKER, subject=subject)
    fifths, reason, detail = _marker_run(marks, _cell0_space(ev, subject))

    fits = ev.rows(Q.KEYSIG_CLEF_FIT, subject=subject)
    tpls = ev.rows(Q.KEYSIG_TEMPLATE_FIT, subject=subject)
    fit_row, fit_fifths = _fit_for_clef(fits, clef)
    tpl_row, tpl_fifths = _fit_for_clef(tpls, clef)

    if fifths is not None:
        # ⚠️ THE FITTERS BECOME CORROBORATION, AND A DISAGREEMENT IS RECORDED
        # RATHER THAN RESOLVED. A fit that agrees joins the basis — two
        # readers of ONE crop, which the harness will mark as one signal in
        # `Verdict.correlated` — and a fit that disagrees is written into the
        # detail, never dropped: it is the standing evidence about which
        # reader fails where, and it would be invisible if the loser were
        # simply discarded.
        detail = dict(detail)
        detail["fit_fifths"] = fit_fifths
        detail["template_fifths"] = tpl_fifths
        agrees = []
        for row, value in ((fit_row, fit_fifths), (tpl_row, tpl_fifths)):
            if row is None or value is None:
                continue
            if value == fifths:
                agrees.append(row.id)
            else:
                detail.setdefault("disagreeing_readers", []).append(
                    {"reader": row.reader, "fifths": value,
                     "n_accidentals": row.detail.get("n_accidentals")})
        detail["corroborated_by"] = len(agrees)
        return Ruling(value=fifths, reason=reason,
                      used=tuple(m.id for m in marks) + (clef.id,)
                      + tuple(agrees), detail=detail)

    if reason != "no_markers":
        # An incoherent run is a refusal with its evidence named, not a gap.
        return Ruling.abstain(reason, **detail)

    # ── no markers at all: the FITTERS speak alone, exactly as before ───────
    # ⚠️⚠️ THIS BRANCH IS WHY THE MARKER RULE IS SURVIVABLE ON A SCAN. Litolff
    # MERGES its ink, so the detector misses key accidentals outright on
    # staves where the template reads them; where the detector saw NOTHING
    # there is nothing to contradict, and the 2.2 precedence — template first
    # on a document MEASURED engraved, locator first otherwise — runs
    # untouched underneath. 80 of 331 staves on Litolff and 145 of 691 on
    # Breitkopf arrive here.
    if _proved_engraved(ev) and tpl_row is not None:
        return Ruling(value=tpl_fifths, reason="fitted_no_markers",
                      used=(tpl_row.id, clef.id),
                      detail=dict(_template_detail(tpl_row),
                                  decided_by="template_engraved"))
    if fit_row is not None:
        return Ruling(value=fit_fifths, reason="fitted_no_markers",
                      used=(fit_row.id, clef.id),
                      detail={"n_accidentals": fit_row.detail.get("n_accidentals"),
                              "accidental": fit_row.detail.get("accidental"),
                              "decided_by": fit_row.detail.get("decided_by")})
    if tpl_row is not None:
        return Ruling(value=tpl_fifths, reason="fitted_no_markers",
                      used=(tpl_row.id, clef.id),
                      detail=dict(_template_detail(tpl_row),
                                  decided_by="template"))

    if not fits:
        state = ev.state(Q.KEYSIG_RUN_POSITION, subject=subject)
        if state is State.READ:
            return Ruling.abstain("no_run", **_marker_ink(ev, subject))
        return Ruling.abstain("no_evidence", **_marker_ink(ev, subject))

    # The run was read and fits SOME slot table, but not the one this staff's
    # settled clef chooses, and no template answered for that clef either.
    return Ruling.abstain("run_fits_no_slot_table",
                          clef=str(clef.value),
                          fits=[str(r.value) for r in fits],
                          **_marker_ink(ev, subject))


def _concert(ev: Evidence, subject, written: Optional[int]):
    """`(concert fifths, instrument name)` for a staff — `(None, name)` if it
    may not stand as a witness about its system's key.

    ⚠️ THE TRANSPOSITION MUST BE **READ**, NEVER DEFAULTED, and the test for
    that is `key_consensus.resolve_label`'s third value — IMPORTED rather
    than restated, because the obvious test for it is WRONG: comparing the
    matched offset against the instrument's default cannot tell *named
    B-flat* from *defaulted to B-flat*, the default clarinet being the B-flat
    one. Measured there on Beethoven 5 p1, the naive test let the one
    correctly-deduced transposing staff on the page escape judgement. A staff
    resting on the default may neither corroborate another nor be
    contradicted by one.

    ⚠️ AND A STAFF THAT PRINTS NO SIGNATURE AT ALL IS NOT A DISSENTER
    (conventions `[C81]`, `key_consensus.NO_SIGNATURE_CONVENTION`): natural
    horns, natural trumpets and timpani read 0 whatever the key, so on
    Beethoven 5's Litolff plate they would stand as three staves per system
    disagreeing with the whole page.
    """
    name, offset = _transposition(ev, subject)
    if offset is None or written is None:
        return None, name
    return written - offset, name


def _transposition(ev: Evidence, subject):
    """`(instrument name, fifths offset)` — the offset is None where the staff
    may neither speak about the key nor be judged by it.

    ⚠️ ROADMAP 2.9b LIFTED THIS OUT OF `_concert` AND CHANGED NOTHING IN IT.
    The two callers need opposite directions of one fact: `_concert` maps a
    WRITTEN signature to concert pitch so staves can be compared, and the
    document tier maps a CONCERT key back to what THIS staff should print. A
    second copy of the eligibility test is how the two directions come to
    admit different staves, which is the drift `key_consensus`' own docstring
    warns about one module over.
    """
    from ...key_consensus import (MAY_DIFFER_NOT_A_WITNESS,
                                  NO_SIGNATURE_CONVENTION, resolve_label)
    labels = ev.rows(Q.MARGIN_LABEL, subject=subject)
    if not labels:
        return None, None
    name, offset, known = resolve_label(str(labels[-1].value))
    if name is None or offset is None or not known:
        return name, None
    if name in NO_SIGNATURE_CONVENTION or name in MAY_DIFFER_NOT_A_WITNESS:
        return name, None
    return name, offset


#: ⚠️ ONE TUPLE, TWO DECISIONS, and it is shared rather than copied because
#: `_staff_reading` is shared: `Evidence` enforces `wants` at hand-in time, so
#: a quantity missing from either declaration would raise inside the other
#: decision's call of the same function — a failure that would only appear on
#: whichever document happened to reach that branch first.
_KEY_WANTS = (Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER, Q.KEYSIG_CLEF_FIT,
              Q.KEYSIG_TEMPLATE_FIT, Q.CLEF, Q.INPUT_DOMAIN,
              Q.CELL_STAFF_SPACE, Q.MARGIN_LABEL)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.9b — the key in force, read across the whole DOCUMENT and each PART
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️⚠️ WHAT SEAN ADJUDICATED, AND WHY THIS IS A DOCUMENT RULE AND NOT ONLY A
# PART RULE. 2.9 put four system-header crops in front of him; his answer,
# 2026-09-23, covers all four: *"all 4 of those crops are pieces with 3 flats
# and the staffs that have fewer flats are transposing clefs."* Both works are
# in C minor, so on both count pages EVERY non-transposing staff prints three
# flats, the B-flat clarinet prints one, and horn / trumpet / timpani print
# none. Scored against that, the 2.9 reader is wrong on **20 of 46 staves**,
# and the wrong values are scattered (+2, -4, +1, -2) while the right answer
# is the SAME on 26 of 46. That shape — one answer repeated, noise everywhere
# else — is what a majority is for, and the population that holds it is the
# DOCUMENT, not the system (8 vs 8 on the engraved page) and not only the part
# (which on a merging plate can be under-counted on its own first systems).
#
# The order, and each tier speaks only where the one above it cannot:
#
#   (1) the staff's own DECIDED key, where the document has nothing to say
#       about it;
#   (2) the DOCUMENT-WIDE majority of decided CONCERT keys, over every staff
#       of every system in the stretch — a staff whose key disagrees is
#       abstained `disagrees_with_document` and INFER fills it with that key
#       RE-TRANSPOSED for this staff;
#   (3) the PART's own cross-system majority of WRITTEN keys, for the staves
#       tier (2) cannot reach at all because nothing on the page names their
#       instrument. On Litolff that is most of them, and the number is
#       reported rather than hidden: it is roadmap 2.6's identity gap
#       measured from a third direction.


#: How many staves must change at one system, by the SAME delta, before a key
#: CHANGE is admitted there.
#:
#: ⚠️⚠️ NOT CHOSEN HERE. It is `[C24]`'s own **Numbers** field --
#: *`MIN_WITNESSES = 2`* -- and the registry states the mechanism in the form
#: this rule needs it: *"the BAR is the shared fact even where the VALUE
#: differs by transposition, so a mid-staff key change that no other staff of
#: the same system also changes at the same bar can be reverted, WITHOUT
#: needing the staves to agree on the key."* The LEGACY path enforces exactly
#: that (`key_signature_corroboration.MIN_WITNESSES`, default ON since
#: 2026-09-07, 7 of 7 spurious flips stopped) and the staged METER mirror
#: asserts equality with it (`rhythm.METER_CHANGE_MIN_STAVES`). This is the
#: third site and it asserts equality too, so the three cannot drift.
CHANGE_MIN_WITNESSES = 2

#: ...and what SHARE of the staves that could have changed must have done so.
#:
#: ⚠️⚠️ THE FLOOR ALONE IS NOT ENOUGH AT DOCUMENT SCALE, and `[C24]` says why:
#: a change is printed *on EVERY staff of it*. Two staves out of twenty-four
#: is not that sentence; it is two staves misreading. The absolute floor stays
#: because a system may hold only a handful of readable headers, and the share
#: is what carries the convention's actual claim.
CHANGE_MIN_SHARE = 0.5

#: How many of a part's own READ systems must hold the new key before the
#: change is believed.
#:
#: ⚠️⚠️ MEASURED, AND IT IS THE GUARD `[C24]` ALONE DOES NOT SUPPLY. On the
#: Litolff plate the detector under-counts flats in RUNS -- the Flute part's
#: base sequence opens `-3 -3 -2 -2 -3`, two consecutive systems misreading
#: the same wrong value -- so a witness count alone admits a change the plate
#: does not print. Requiring the new value to survive the part's NEXT read
#: system costs a real change nothing (a printed change holds until the next
#: one) and costs a correlated misreading everything. The sweep behind the
#: number is `part_sim.py --sweep`; the figures are in FINDINGS.md §2.9b.
#:
#: ⚠️ A run of ONE is not "no persistence rule", it is the rule switched off,
#: and the sweep prices that column too so the guard's cost is visible.
CHANGE_MIN_RUN = 2


def _assert_change_threshold_matches_legacy() -> None:
    """⚠️ THE THIRD SITE, AND IT MUST NOT DRIFT FROM THE OTHER TWO.

    `rhythm.METER_CHANGE_MIN_STAVES` asserts the same equality for the meter
    and says why: a convention with a number in the registry and three
    independent copies in code is a convention that will be changed in one of
    them. Imported at call time so a failure names this module.
    """
    from ...key_signature_corroboration import MIN_WITNESSES as _legacy
    if CHANGE_MIN_WITNESSES != _legacy:
        raise AssertionError(
            f"[C24] says MIN_WITNESSES = {_legacy} and this module says "
            f"{CHANGE_MIN_WITNESSES}. One convention, one number.")


def admitted_changes(readings, *,
                     min_witnesses: int = CHANGE_MIN_WITNESSES,
                     min_share: float = CHANGE_MIN_SHARE,
                     min_run: int = CHANGE_MIN_RUN):
    """The systems at which a key CHANGE is corroborated ACROSS THE DOCUMENT.

    `readings` is `{part: [((page, system), fifths or None), ...]}` in
    document order, already filtered to parts that may witness a change.
    Returns `[((page, system), delta), ...]`, sorted.

    ⚠️⚠️ THE DELTA, NEVER THE VALUE (`[C24]`). Transposing parts print
    DIFFERENT signatures for one key and the same SHIFT at a change, so two
    parts corroborate each other on `+2` without either knowing what the other
    is transposed by -- which is what lets this test run on the staves whose
    margin label is not printed on their own system and which the concert-key
    tally cannot reach at all.

    ⚠️ A SYSTEM WHOSE WITNESSES DISAGREE ABOUT THE DELTA ADMITS NOTHING. Two
    parts saying `+1` and two saying `+2` is not a change read twice; it is a
    system this reader is unreliable on, and taking the larger bloc would be
    the argmax INFER's own harness refuses.

    ⚠️ THE DENOMINATOR IS THE PARTS THAT COULD HAVE CHANGED -- those with a
    reading at this system AND an earlier one to compare it against. Counting
    against every part in the score would make a change unprovable on any page
    the reader is patchy about, which is every page this matters on.
    """
    tally = {}
    eligible = {}
    for rows in readings.values():
        read = [(sys_key, v) for sys_key, v in rows if v is not None]
        for i in range(1, len(read)):
            eligible[read[i][0]] = eligible.get(read[i][0], 0) + 1
            prev, here = read[i - 1][1], read[i][1]
            if here == prev:
                continue
            # ⚠️⚠️ PERSISTENCE ON **BOTH** SIDES, and the one-sided version was
            # written first and is WRONG. Counting only forward, the sequence
            # `-3 -3 -2 -3 -3` refuses the change INTO the misreading (the -2
            # stands alone) and then admits the change OUT of it, because -3
            # holds for two systems afterwards: a transient misreading became
            # a key change at the system where the reader RECOVERED. The
            # fixture `test_a_value_that_does_not_HOLD_is_not_a_change` is
            # that sequence and it caught this.
            #
            # ⚠️ Counted over the part's own READ systems -- a gap is not a
            # contradiction, and treating it as one would refuse every change
            # on a part the reader is patchy about.
            before = 1
            for j in range(i - 2, -1, -1):
                if read[j][1] != prev:
                    break
                before += 1
            after = 1
            for j in range(i + 1, len(read)):
                if read[j][1] != here:
                    break
                after += 1
            if before < min_run or after < min_run:
                continue
            tally.setdefault(read[i][0], {}).setdefault(here - prev, 0)
            tally[read[i][0]][here - prev] += 1
    out = []
    for sys_key, deltas in tally.items():
        best = max(deltas.values())
        if best < min_witnesses:
            continue
        if best < min_share * eligible.get(sys_key, 0):
            continue
        winners = [d for d, n in deltas.items() if n == best]
        if len(winners) != 1:
            continue
        out.append((sys_key, winners[0]))
    return sorted(out)


def _segments(values_by_system, changes):
    """Majority per stretch of systems. The one body both tiers use.

    `values_by_system` is `[((page, system), value or None), ...]` in document
    order -- one row per STAFF for the document tier, one per SYSTEM for a
    part. Returns `[{"from", "fifths", "support", "read", "tally"}, ...]`.

    ⚠️⚠️ THE MAJORITY IS TAKEN INSIDE A STRETCH AND NEVER ACROSS ONE. That is
    the whole difference between this and flattening a movement to one key: an
    admitted change cuts the sequence in two and each side keeps its own
    answer, so the rule cannot delete a change it has itself admitted.

    ⚠️ A TIE ABSTAINS -- Sean's standing rule for every vote in this tree, and
    load-bearing in a second way here: a population read eight ways once each
    is one this rule knows nothing about, and answering with the earliest or
    the alphabetically-first reading would convert *cannot tell* into an
    answer (CLAUDE.md rule 8).
    """
    cuts = [sys_key for sys_key, _delta in changes]
    bounds = [None] + sorted(cuts)
    out = []
    for i, start in enumerate(bounds):
        end = bounds[i + 1] if i + 1 < len(bounds) else None
        inside = [v for sys_key, v in values_by_system
                  if (start is None or sys_key >= start)
                  and (end is None or sys_key < end)]
        read = [v for v in inside if v is not None]
        tally = {}
        for v in read:
            tally[v] = tally.get(v, 0) + 1
        fifths, support = None, 0
        if tally:
            support = max(tally.values())
            winners = [v for v, n in tally.items() if n == support]
            if len(winners) == 1:
                fifths = winners[0]
            else:
                support = 0
        out.append({"from": list(start) if start else None,
                    "fifths": fifths, "support": support,
                    "read": len(read), "rows": len(inside),
                    "tally": {str(k): v for k, v in sorted(tally.items())}})
    return out


def segment_fifths(segments, sys_key):
    """The value one sequence holds at one system, or None. Pure lookup."""
    answer = None
    for seg in segments or ():
        start = seg.get("from")
        if start is None or tuple(start) <= tuple(sys_key):
            answer = seg
        else:
            break
    if answer is None:
        return None
    return answer.get("fifths")


def _slot_of(ev: Evidence, subject):
    """`(slot, instrument name)` for one staff -- the PART it sits on.

    ⚠️⚠️ THE SLOT IS THE PART AND `Q.INSTRUMENT` IS ONLY A LABEL ON IT, which
    is `inferences._part_of`'s finding one stage over and the reason 2.10's
    clef rule keys on the slot: on the Litolff plate the margin label is
    printed on the first system and nowhere else, so `Q.INSTRUMENT` abstains
    on most continuation systems while `Q.SLOT_INDEX` is decided on 320 of
    331. A rule keyed on the label alone would reach the 76 staff-systems
    `Q.SYSTEM_KEY` reaches and no more.

    ⚠️ AND THE EXPORTER JOINS ITS PARTS BY THIS SAME SLOT (`export.build`,
    `join == "slot"`), so *the part this rule speaks about* and *the `<part>`
    the file writes* are one object rather than two that happen to line up.
    """
    slot = ev.verdict(Q.SLOT_INDEX, subject=subject)
    if slot is None or not isinstance(slot.value, int):
        return None, None
    name = None
    inst = ev.verdict(Q.INSTRUMENT, subject=subject)
    if inst is not None and isinstance(inst.value, dict):
        name = inst.value.get("name")
    if not name:
        name = (slot.detail or {}).get("instrument")
    return int(slot.value), (str(name) if name else None)


def _system_checked(ev: Evidence, subject, reading: Ruling) -> Ruling:
    """`Q.SYSTEM_KEY`'s check, applied to one staff's reading (roadmap 2.9).

    ⚠️ LIFTED OUT OF `adjudicate_key_signature` UNCHANGED so that
    `adjudicate_part_key` can tally the readings that SURVIVED it rather than
    the raw ones -- a document or part majority must not be built out of
    readings the system check has already condemned as lone dissenters. One
    projection, three callers, which is `_staff_reading`'s own discipline.
    """
    concert, name = _concert(ev, subject, int(reading.value))
    if concert is None:
        return reading
    system_subject = (ev.subject if subject is None else subject).at(Kind.SYSTEM)
    system = ev.verdict(Q.SYSTEM_KEY, subject=system_subject)
    if system is None or system.value is None:
        return reading
    tally = system.value.get("tally") or {}
    if concert in system.value.get("corroborated", ()):
        detail = dict(reading.detail)
        detail.update(concert_fifths=concert, instrument=name,
                      system_peers=int(tally.get(str(concert), 0)))
        return Ruling(value=reading.value, reason=reading.reason,
                      used=tuple(reading.used) + (system.id,), detail=detail)
    return Ruling.abstain(
        "disagrees_with_system",
        concert_fifths=concert, instrument=name,
        written_fifths=int(reading.value), read_by=reading.reason,
        system_tally=(system.value or {}).get("tally"),
        **{k: v for k, v in reading.detail.items()
           if k.startswith("keysig_") or k == "disagreeing_readers"})


def effective_offset(part_key_value, slot, offset):
    """This staff's transposition: its OWN label's, else its PART's.

    ⚠️⚠️ THE PART'S TRANSPOSITION IS READ ONCE AND VALID ON EVERY SYSTEM OF
    IT, and without this the document tier is nearly inert on a scan. Litolff
    prints its margin labels on the first system and nowhere else, so a tier
    keyed on THIS staff's own label reaches 76 of 331 staff-systems — and the
    count page is not among them. A part is ONE instrument with ONE
    transposition, so an offset a label stated anywhere on the part is a READ
    fact about every staff of it. That is not the DEFAULT
    `key_consensus.resolve_label`'s third value exists to refuse: the default
    is the lexicon guessing that an unnamed clarinet is the B-flat one, and
    this is a label on this very part, on this very document, being carried
    to the staves of the part it names.

    ⚠️ `adjudicate_part_key` publishes it only where every resolvable label on
    the slot AGREES, so a slot the JOIN got wrong lends nothing.
    """
    if offset is not None:
        return int(offset)
    if slot is None or not part_key_value:
        return None
    part = (part_key_value.get("parts") or {}).get(str(slot)) or {}
    value = part.get("offset")
    return None if value is None else int(value)


def expected_fifths(part_key_value, slot, offset, sys_key):
    """What the file should carry on ONE staff — `(fifths, tier)` or `(None, why)`.

    ⚠️⚠️ ONE FUNCTION, TWO CONSUMERS, AND THAT IS THE POINT. The ADJUDICATE
    check (`_part_checked`) and the INFER rule (`inferences.fill_part_key`)
    must agree about what a staff should carry or the check abstains a staff
    the inference then fills with a DIFFERENT value — a disagreement invisible
    in the file and visible only as a count that does not add up. So the
    answer is computed once, here, from the published verdict alone.

    `offset` is this staff's `fifths_offset` (None where the transposition was
    never READ, in which case tier (2) is unavailable to it).
    """
    if not part_key_value:
        return None, "no_part_key"
    part = ((part_key_value.get("parts") or {}).get(str(slot)) or {}
            if slot is not None else {})
    offset = effective_offset(part_key_value, slot, offset)
    document = part_key_value.get("document") or ()
    if offset is not None:
        concert = segment_fifths(document, sys_key)
        if concert is not None:
            return int(concert) + int(offset), "document_majority"
    if slot is not None:
        written = segment_fifths(part.get("segments") or (), sys_key)
        if written is not None:
            return int(written), "part_majority"
    return None, "nothing_to_compare"


def _part_checked(ev: Evidence, subject, reading: Ruling) -> Ruling:
    """The DOCUMENT and PART checks, applied to one staff (roadmap 2.9b).

    ⚠️⚠️ IT ABSTAINS, IT DOES NOT OVERWRITE, AND THAT IS NOT A STYLE CHOICE.
    INFER *"never overturns a DECIDED one"* (CLAUDE.md §4a, `infer.INFERABLE`),
    so a staff whose DECIDED key disagrees with the document's own majority
    cannot be repaired by an inference while it stands decided. The repair has
    to happen HERE, where it is a CHECK that reads rows and can FAIL — the
    shape `adjudicate_system_key` already has — and the staff's own reading
    survives in the abstention's `written_fifths` and in the marker and fit
    OBSERVATIONS underneath it. INFER then fills the gap with the same value
    `expected_fifths` computed here, labelled. Nothing is silently rewritten
    at any step, and a reader of the record can see every one of them.

    ⚠️ A STAFF NEITHER TIER CAN REACH IS NOT JUDGED. No READ transposition and
    no decided slot means no other reading of THIS staff's key exists anywhere
    in the document; its own reading stands exactly as it did before 2.9b.
    """
    # ⚠️⚠️ ONE FLAG OVER BOTH HALVES OF ONE RULE, AND IT LIVES IN `infer` WITH
    # THE OTHER THREE. The check and the inference are not two features: the
    # check abstains a staff exactly so the inference may fill it, so gating
    # only the INFER half would leave `disagrees_with_document` abstentions
    # standing with nothing to fill them — a state no shipped tree has ever
    # been in, which would report as a regression of a rule nobody turned on.
    # The predicate is `infer.part_key_enabled`'s, imported rather than
    # copied, so the AST flag-direction scan still sees exactly one
    # `os.environ.get` for `OMR_PART_KEY`.
    from ..infer import part_key_enabled
    if not part_key_enabled():
        return reading
    slot, name = _slot_of(ev, subject)
    part_key = ev.verdict(Q.PART_KEY, subject=ev.subject.at(Kind.DOCUMENT))
    if part_key is None or part_key.value is None:
        return reading
    _name, offset = _transposition(ev, subject)
    staff = ev.subject if subject is None else subject
    sys_key = (staff.page or 0, staff.system or 0)
    want, tier = expected_fifths(part_key.value, slot, offset, sys_key)
    if want is None:
        return reading
    if int(reading.value) == int(want):
        detail = dict(reading.detail)
        detail.update(part_slot=slot, part_instrument=name or _name,
                      agrees_with=tier, expected_fifths=int(want))
        return Ruling(value=reading.value, reason=reading.reason,
                      used=tuple(reading.used) + (part_key.id,), detail=detail)
    reason = ("disagrees_with_document" if tier == "document_majority"
              else "disagrees_with_part")
    return Ruling.abstain(
        reason,
        part_slot=slot, part_instrument=name or _name, tier=tier,
        expected_fifths=int(want), written_fifths=int(reading.value),
        fifths_offset=offset, read_by=reading.reason,
        **{k: v for k, v in reading.detail.items()
           if k.startswith("keysig_") or k in ("disagreeing_readers",
                                               "concert_fifths",
                                               "system_peers")})


@decision(
    quantity=Q.PART_KEY,
    checkable=Checkable.CHECKABLE,
    checked_by=(
        '"the clef and key signature are reprinted at the head of EVERY system [C25 + L38], so one fact has many independent readings"',
        '"a key CHANGE is printed at ONE bar of ONE system, on EVERY staff of it [C24] -- so a change on a few staves alone is a misreading of those staves"',
        '"across the staves of a system the DELTA is shared, never the value -- so a change is corroborated on the SHIFT and needs no transposition"',
        '"timpani, horns and trumpets are conventionally written WITHOUT a key signature [C81], so they neither vote nor are judged by the concert tally"',
    ),
    implicates=(Q.PART_KEY, Q.KEY_SIGNATURE, Q.SLOT_INDEX, Q.MARGIN_LABEL),
    composed_from=(Q.KEYSIG_MARKER, Q.KEYSIG_CLEF_FIT, Q.KEYSIG_TEMPLATE_FIT,
                   Q.CLEF, Q.SLOT_INDEX, Q.MARGIN_LABEL, Q.SYSTEM_KEY),
    scope=Kind.DOCUMENT,
    wants=_KEY_WANTS + (Q.SYSTEM_KEY, Q.SLOT_INDEX, Q.INSTRUMENT),
    reasons=("read", "no_staff_read_a_key"),
    mode=Mode.ADDITIVE,
)
def adjudicate_part_key(ev: Evidence) -> Ruling:
    """The key in force over the DOCUMENT, and over each PART, per stretch.

    Roadmap 2.9b. Sean's 2.9 decision settled a key per SYSTEM; the
    measurement that closed 2.9 said the file was still wrong on a PART
    (`benchmarks/omr-key-majority-2026-09/FINDINGS.md` §6a: Litolff 11 of 12
    parts opening right became 6 of 12 while the per-staff wrong count FELL,
    37 to 33), and his adjudication of the four crops said the population that
    holds the answer is wider still — every non-transposing staff of both
    count pages prints the same three flats, and the reader's wrong answers
    are scattered noise.

    ⚠️⚠️ IT DECIDES NO STAFF, EXACTLY AS `adjudicate_system_key` DECIDES NONE.
    It publishes what the document and each part read, and where a key CHANGE
    is corroborated. `adjudicate_key_signature` uses it for ONE thing —
    abstaining a staff whose decided key disagrees — and INFER fills the
    abstention afterwards, labelled.

    ⚠️ TWO TIERS, ONE SEGMENTATION. The document tier speaks in CONCERT pitch
    and reaches only staves whose transposition was READ off a margin label;
    the part tier speaks in WRITTEN fifths, needs no label at all, and reaches
    every staff with a decided slot. They share the change boundaries because
    a key change is a property of the SCORE, not of a part — publishing two
    segmentations would let the two tiers disagree about where the movement
    changes key, which is a contradiction the record could hold and no
    consumer could see.

    ⚠️ AND THE TWO REACHES ARE BOTH REPORTED, because the gap between them is
    roadmap 2.6's identity gap measured from a third direction: on Litolff 76
    of 331 staff-systems can be stated in concert pitch and 320 of 331 have a
    part. `detail["staves_normalised"]` and `detail["staves_with_a_part"]`
    carry the two counts on every run.
    """
    _assert_change_threshold_matches_legacy()
    from ...key_consensus import (MAY_DIFFER_NOT_A_WITNESS,
                                  NO_SIGNATURE_CONVENTION)
    by_part = {}
    names = {}
    part_offsets = {}
    rows_used = []
    read = []
    for staff in ev.subjects(Kind.STAFF):
        sys_key = (staff.page or 0, staff.system or 0)
        slot, name = _slot_of(ev, staff)
        if name and slot is not None and slot not in names:
            names[slot] = name
        # ⚠️⚠️ THE PART'S TRANSPOSITION IS COLLECTED HERE AND AGREEMENT IS
        # REQUIRED. Every resolvable label on one slot must resolve to ONE
        # (name, offset); a slot whose labels disagree is a slot the JOIN got
        # wrong -- `adjudicate_part_partition`'s own docstring records the
        # case, a tacet "2 Trompeten in C" grafted onto "4 Hörner in Es" --
        # and a part with two instruments on it may not lend either one's
        # transposition to the other's staves. `None` marks the contradiction
        # so a later label cannot quietly repair it.
        label_name, label_offset = _transposition(ev, staff)
        if slot is not None and label_offset is not None:
            here = (label_name, int(label_offset))
            if slot not in part_offsets:
                part_offsets[slot] = here
            elif part_offsets[slot] != here:
                part_offsets[slot] = None
        # ⚠️ `_staff_reading` AND `_system_checked` ARE CALLED HERE RATHER THAN
        # THROUGH A `_checked_reading` WRAPPER, and the wrapper existed until
        # `inventory --check` reported this decision declaring `input_domain`
        # and `cell_staff_space` and reading neither. It follows the call
        # chain three levels deep inside the module, and one extra hop pushed
        # `_cell0_space` and `_proved_engraved` out of reach — so the tool
        # would have reported a real inertness where there was none, on every
        # run, for ever. The tidier call is the one that makes the inventory
        # lie.
        reading = _staff_reading(ev, staff)
        ruling = (reading if reading is None or reading.value is None
                  else _system_checked(ev, staff, reading))
        value = None
        if ruling is not None and ruling.value is not None:
            value = int(ruling.value)
            rows_used.extend(ruling.used)
        read.append((sys_key, slot, value, label_offset))
        if slot is not None:
            by_part.setdefault(slot, []).append((sys_key, value))
    for slot in by_part:
        by_part[slot].sort()

    # ⚠️ THE CONCERT TALLY IS BUILT IN A SECOND PASS because a staff's
    # transposition may have been read on ANOTHER system of its part, and that
    # is not known until every staff has been walked. One pass would silently
    # normalise only the staves whose own system happened to print a label —
    # 76 of 331 on Litolff, and none of them on the count page.
    concert_rows = []
    own_label = 0
    for sys_key, slot, value, label_offset in read:
        if value is None:
            continue
        offset = label_offset
        if offset is None and slot is not None:
            pair = part_offsets.get(slot)
            offset = pair[1] if pair else None
        else:
            own_label += 1
        if offset is not None:
            concert_rows.append((sys_key, value - int(offset)))
    concert_rows.sort()

    # ⚠️ THE CHANGE WITNESSES ARE THE PARTS THAT PRINT A SIGNATURE AT ALL. A
    # natural horn, trumpet or timpani reads 0 whatever the key, so its delta
    # is 0 at a real change and any non-zero delta it shows is noise by
    # construction ([C81]); Harp is excluded for `MAY_DIFFER_NOT_A_WITNESS`'s
    # reason — its signature is a fact about pedals.
    witnesses = {slot: rows for slot, rows in by_part.items()
                 if names.get(slot) not in NO_SIGNATURE_CONVENTION
                 and names.get(slot) not in MAY_DIFFER_NOT_A_WITNESS}
    changes = admitted_changes(witnesses)

    document = _segments(concert_rows, changes)
    parts = {str(slot): {"name": names.get(slot),
                         "offset": (part_offsets.get(slot) or (None, None))[1],
                         "segments": _segments(rows, changes)}
             for slot, rows in sorted(by_part.items())}
    # ⚠️ TWO REACH NUMBERS, REPORTED SEPARATELY ON EVERY RUN. `own_label` is
    # what 2.9's concert tally could see; `staves_normalised` is what this one
    # sees once the part's transposition is carried along the part. The gap
    # between them and `staves_with_a_part` is roadmap 2.6's identity gap,
    # measured from a third direction.
    detail = {"parts": len(parts), "changes": len(changes),
              "staves_normalised": len(concert_rows),
              "staves_with_their_own_label": own_label,
              "staves_with_a_part": sum(len(r) for r in by_part.values()),
              "parts_with_a_read_transposition":
                  sum(1 for v in part_offsets.values() if v),
              "document_tally": [s["tally"] for s in document]}
    if not any(s["fifths"] is not None for s in document) \
            and not any(seg["fifths"] is not None
                        for p in parts.values() for seg in p["segments"]):
        return Ruling.abstain("no_staff_read_a_key", **detail)
    return Ruling(value={"document": document, "parts": parts,
                         "changes": [[list(s), d] for s, d in changes]},
                  reason="read", used=tuple(rows_used), detail=detail)


@decision(
    quantity=Q.SYSTEM_KEY,
    checkable=Checkable.CHECKABLE,
    checked_by=(
        '"a key CHANGE is printed at ONE bar of ONE system, on EVERY staff of it [C24]"',
        '"across the staves of a system the DELTA is shared, never the value -- transposing parts print different signatures for one key"',
        '"timpani, horns and trumpets are conventionally written WITHOUT a key signature [C81], so their zero is not a disagreement"',
    ),
    implicates=(Q.SYSTEM_KEY, Q.KEY_SIGNATURE, Q.CLEF, Q.MARGIN_LABEL),
    composed_from=(Q.KEYSIG_MARKER, Q.KEYSIG_CLEF_FIT, Q.KEYSIG_TEMPLATE_FIT,
                   Q.CLEF, Q.MARGIN_LABEL),
    scope=Kind.SYSTEM,
    wants=_KEY_WANTS,
    reasons=("read", "one_staff_only", "no_staff_read_a_key"),
    mode=Mode.ADDITIVE,
)
def adjudicate_system_key(ev: Evidence) -> Ruling:
    """The CONCERT keys this system's staves read, and how many read each.

    ⚠️⚠️ NARROWED BY CONSTRUCTION, AND THAT IS THE DESIGN RATHER THAN A
    LIMITATION. Sean decided on 2026-09-23 that a key is settled per SYSTEM,
    and the first draft of that was a MAJORITY that rewrote every staff. The
    trace refused it: on the engraved acceptance page the two readings split
    EIGHT to EIGHT once normalised to concert, so a majority would have been
    a coin toss — while the actual defect was one reader counting one flat
    where the detector had already drawn three boxes. So this decides nothing
    about any staff. It publishes the tally, and `adjudicate_key_signature`
    uses it for ONE thing: a staff whose concert key has NO PEER on its own
    system is a misreading of that staff (conventions `[C24]`, CLAUDE.md §10)
    and abstains.

    ⚠️ A CHECK THAT CAN FAIL, WHICH A MAJORITY IS NOT. Where two staves share
    a value neither is touched, however many disagree — so a genuinely bitonal
    system (Holst's `Mercury` is the recorded case) and a page this reader
    half-misreads both lose nothing. It also cannot fire at all where only one
    staff can speak, and that is reported by its own reason rather than folded
    into the tally.

    ⚠️ ITS WITNESSES ARE INDEPENDENT, WHICH IS WHAT THE CHECK RESTS ON: each
    staff has its OWN header crop and its own detector cell, so they are not
    `Evidence.correlated_groups`' *one reader on one crop*. The two READERS of
    a single staff ARE — which is why a fit corroborating that staff's markers
    joins the staff's own term in `_staff_reading` instead of adding a second
    witness here.
    """
    staves = [s for s in ev.subjects(Kind.STAFF) if ev.subject.contains(s)]
    tally: Dict[int, int] = {}
    used: List[str] = []
    read_a_key = 0
    for sub in staves:
        ruling = _staff_reading(ev, sub)
        if ruling is None or ruling.value is None:
            continue
        read_a_key += 1
        concert, _name = _concert(ev, sub, int(ruling.value))
        if concert is None:
            continue
        tally[concert] = tally.get(concert, 0) + 1
        used.extend(ruling.used)
    detail = {"staves": len(staves), "staves_with_a_reading": read_a_key,
              "tally": {str(k): v for k, v in sorted(tally.items())}}
    if not tally:
        return Ruling.abstain("no_staff_read_a_key", **detail)
    if sum(tally.values()) < 2:
        # ⚠️ ONE WITNESS CANNOT CONTRADICT ITSELF. Its own reason, because
        # "this system has one staff whose key we can state in concert pitch"
        # and "its staves agree" are different facts, and the check is INERT
        # in the first — which is what `reach` needs to be able to see.
        return Ruling.abstain("one_staff_only", **detail)
    # ⚠️⚠️ A LIST, AND `Ruling.narrow` WAS TRIED FIRST AND IS WRONG HERE. The
    # harness clears a candidate set of one — *a single survivor is not a
    # narrowing* — so a system whose staves AGREE, which is the common case
    # and the strongest possible evidence, would have come back ABSTAINED
    # with nothing attached: the exact ABSENT/DECLINED collapse this record
    # exists to prevent, inverted. The value is therefore the set of concert
    # keys MORE THAN ONE staff of this system read, which is a fact and is
    # decidable; a set of one is the unanimous page and a set of none is a
    # system in which every reading stands alone.
    corroborated = sorted(k for k, v in tally.items() if v >= 2)
    return Ruling(value={"corroborated": corroborated,
                         "tally": detail["tally"]},
                  reason="read", used=tuple(used), detail=detail)


@decision(
    quantity=Q.KEY_SIGNATURE,
    checkable=Checkable.MIXED,
    checked_by=(
        '"the accidental ORDER is fixed (F#-C#-G#... / Bb-Eb-Ab...): a run that SKIPS a slot is impossible [C21]"',
        '"a key signature\'s accidentals stand at fixed SLOTS, so two boxes at one x are ONE slot [C21]"',
        '"across the staves of a system the DELTA is shared, never the value -- transposing parts print different signatures for one key"',
        '"a key CHANGE is printed at ONE bar of ONE system, on EVERY staff of it [C24] -- so a concert key with no peer on its own system is a misreading"',
        '"the clef and key signature are reprinted at the head of EVERY system [C25 + L38] -- so a staff disagreeing with its own document\'s majority is a misreading of that staff"',
    ),
    implicates=(Q.KEY_SIGNATURE, Q.CLEF, Q.KEYSIG_RUN_POSITION,
                Q.KEYSIG_MARKER),
    composed_from=(Q.KEYSIG_MARKER, Q.KEYSIG_RUN_POSITION,
                   Q.KEYSIG_TEMPLATE_FIT, Q.CLEF),
    scope=Kind.STAFF,
    wants=_KEY_WANTS + (Q.SYSTEM_KEY, Q.PART_KEY, Q.SLOT_INDEX, Q.INSTRUMENT),
    reasons=("markers", "fitted_no_markers", "needs_clef",
             "run_fits_no_slot_table", "no_run", "mixed_marker_kinds",
             "natural_markers", "too_many_markers", "no_cell_scale",
             "disagrees_with_system", "disagrees_with_document",
             "disagrees_with_part", "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_key_signature(ev: Evidence) -> Ruling:
    """The key signature, read off the DETECTOR's own boxes and then checked.

    ⚠️ THE GUARD MOVED; IT WAS NOT REMOVED. `key_signature_locator.py:310`
    refuses to run without a clef, and it is right to: fitting three flats
    against a guessed clef once returned TWO SHARPS — a different accidental
    type fitting a different prefix well inside tolerance. GATHER asks the
    reader once per CANDIDATE clef, which is the honest form of the question;
    this decision reads the answer for the clef that actually won, and IF THE
    CLEF ABSTAINED SO DOES THIS.

    ⚠️⚠️ THE PRIMARY READER IS NOW `Q.KEYSIG_MARKER`, AND IT WAS ALREADY ON
    THE RECORD (`_marker_run`). Measured 2026-09-23 over the three acceptance
    documents, scored against the movement's own key — Beethoven 5 mvt 1 and
    Brahms 1 mvt 1 are both C minor, so every staff's printed signature
    follows from its instrument and needs no page truth:

      * engraved acceptance page, 50 scored staves — the header fitters read
        **45 right / 3 wrong / 2 abstained**, the marker run **50 / 0 / 0**;
      * Brahms 1, Breitkopf, whole movement, 583 scored — **171 / 241 / 171**
        against **330 / 198 / 55**;
      * Beethoven 5, Litolff, whole movement, 200 scored — **91 / 37 / 72**
        against **101 / 52 / 47**.

    ⚠️ THE LITOLFF ROW IS THE COST AND IT IS NOT HIDDEN. That plate MERGES its
    ink, so where the detector fires at all it UNDER-counts the run: the
    marker rule trades 25 abstentions there for 10 more right and 15 more
    wrong. The system check below is what pays that back, and the figures with
    it are in `benchmarks/omr-key-majority-2026-09/FINDINGS.md`.

    ⚠️ THE FITTERS ARE NOT DEMOTED WHERE THE DETECTOR IS SILENT. With no
    marker rows at all the old precedence runs untouched — template first on a
    document MEASURED engraved (`OMR_ENGRAVED_KEYSIG`, roadmap 2.2, Sean's
    call 2026-09-22), locator first otherwise — under one reason word,
    `fitted_no_markers`, so the branch is countable in the record. ⚠️ That
    word REPLACES `fitted`, `fitted_by_template` and
    `fitted_by_template_engraved`: the precedence they named is unchanged in
    code, and which reader answered is now `detail["decided_by"]`.

    ⚠️ A DISAGREEING FIT IS RECORDED, NEVER DROPPED. `detail
    ["disagreeing_readers"]` names the reader and what it said. On the
    engraved page that is 24 of the 30 staves where both spoke — the
    measurement that says which reader to work on next.

    ⚠️⚠️ THE SYSTEM CHECK IS A CHECK, NOT A VOTE. A staff whose CONCERT key
    has no peer on its own system abstains `disagrees_with_system`, and EXPORT
    then writes no `<key>` for it — which in MusicXML CARRIES the part's last
    stated key, so nothing is invented. It never writes another staff's value
    onto this one: the majority that would do so was designed, priced and
    REFUSED (`adjudicate_system_key`).

    ⚠️ AND `markers_without_a_run` IS GONE BECAUSE ITS PREMISE EXPIRED. It
    said *the detector saw ink and the fitter could not speak*, which was true
    and is now the ordinary path: those staves are exactly the ones this
    decision now reads. It stood on 4 of 54 verdicts on the engraved record.
    """
    reading = _staff_reading(ev)
    if reading is None:
        return Ruling.abstain("needs_clef")
    if reading.value is None:
        return reading

    # ── the SYSTEM check (roadmap 2.9) ──────────────────────────────────────
    # ⚠️ Its body lives in `_system_checked` so `adjudicate_part_key` can tally
    # exactly the readings this decision keeps — one projection, three callers,
    # and the part majority cannot drift from the staff verdict.
    checked = _system_checked(ev, None, reading)
    if checked.value is None:
        return checked

    # ── the PART check (roadmap 2.9b) ───────────────────────────────────────
    return _part_checked(ev, None, checked)
