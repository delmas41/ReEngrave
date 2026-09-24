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
    from ...key_consensus import (MAY_DIFFER_NOT_A_WITNESS,
                                  NO_SIGNATURE_CONVENTION, resolve_label)
    labels = ev.rows(Q.MARGIN_LABEL, subject=subject)
    if not labels or written is None:
        return None, None
    name, offset, known = resolve_label(str(labels[-1].value))
    if name is None or offset is None or not known:
        return None, name
    if name in NO_SIGNATURE_CONVENTION or name in MAY_DIFFER_NOT_A_WITNESS:
        return None, name
    return written - offset, name


#: ⚠️ ONE TUPLE, TWO DECISIONS, and it is shared rather than copied because
#: `_staff_reading` is shared: `Evidence` enforces `wants` at hand-in time, so
#: a quantity missing from either declaration would raise inside the other
#: decision's call of the same function — a failure that would only appear on
#: whichever document happened to reach that branch first.
_KEY_WANTS = (Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER, Q.KEYSIG_CLEF_FIT,
              Q.KEYSIG_TEMPLATE_FIT, Q.CLEF, Q.INPUT_DOMAIN,
              Q.CELL_STAFF_SPACE, Q.MARGIN_LABEL)


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
    ),
    implicates=(Q.KEY_SIGNATURE, Q.CLEF, Q.KEYSIG_RUN_POSITION,
                Q.KEYSIG_MARKER),
    composed_from=(Q.KEYSIG_MARKER, Q.KEYSIG_RUN_POSITION,
                   Q.KEYSIG_TEMPLATE_FIT, Q.CLEF),
    scope=Kind.STAFF,
    wants=_KEY_WANTS + (Q.SYSTEM_KEY,),
    reasons=("markers", "fitted_no_markers", "needs_clef",
             "run_fits_no_slot_table", "no_run", "mixed_marker_kinds",
             "natural_markers", "too_many_markers", "no_cell_scale",
             "disagrees_with_system", "no_evidence"),
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

    concert, name = _concert(ev, None, int(reading.value))
    if concert is None:
        # Not a witness about the system's key, and so not judged by it: an
        # unlabelled staff, an instrument whose key the label never named, or
        # one that prints no signature at all. Its own reading stands.
        return reading

    system = ev.verdict(Q.SYSTEM_KEY, subject=ev.subject.at(Kind.SYSTEM))
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
