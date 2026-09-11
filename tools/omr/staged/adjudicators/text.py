"""Dynamics and direction words."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..adjudicate import Candidate, Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope, State


#: The 17 words MusicXML has a `<dynamics>` child element for. Anything else a
#: run spells is `<other-dynamics>`, or nothing.
DYNAMIC_WORDS = frozenset({
    "p", "pp", "ppp", "pppp", "f", "ff", "fff", "ffff",
    "mp", "mf", "sf", "sfz", "fp", "rf", "rfz", "sfp", "fz",
})


def _letter_of(row: Any) -> Optional[str]:
    letter = row.detail.get("letter")
    if letter:
        return str(letter)
    value = str(row.value or "")
    return value.replace("dynamic", "").lower() or None


def _geometry(row: Any) -> Optional[Tuple[float, float, float]]:
    """`(x0, x1, y_center)` in PAGE pixels, or None if this row has no page box.

    ⚠️ A row without a page box is NOT silently placed in the cell frame. The
    two frames differ by the cell's padding, which is 4 to 6 staff spaces
    depending on how crowded the staff's neighbours are -- so mixing them would
    move a letter's position with the page's crowding rather than with the ink.
    A run assembled from a mixture would be assembled in no frame at all.
    """
    box = row.detail.get("bbox_page_px")
    if not box or len(box) != 4:
        return None
    return float(box[0]), float(box[2]), (float(box[1]) + float(box[3])) / 2.0


@decision(
    quantity=Q.DYNAMIC,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER),
    scope=Kind.CELL,
    wants=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER),
    # ⚠️ The subjects are the cells `Q.DYNAMIC_LETTER` speaks about --
    # OBSERVATIONS AND ABSTENTIONS ALIKE, because `subjects_for` reads
    # `log.all_rows()` and an abstention is a row. That is what makes this
    # compose with `gather_dynamic_letters` writing a row for EVERY cell: a
    # bar holding no letter of its own still has a subject, so a letter that
    # ownership moves onto it has somewhere to land.
    subjects_from=Q.DYNAMIC_LETTER,
    # ⚠️ Union of both sessions' reasons. `no_page_frame` and
    # `reader_unavailable` are declared and not currently raised -- declaring
    # a reason the code can reach is cheap; discovering one it cannot name is
    # not.
    reasons=("spelled", "unspellable", "no_letters", "no_page_frame",
             "owned_elsewhere", "reader_unavailable"),
    mode=Mode.ADDITIVE,
)
def adjudicate_dynamic(ev: Evidence) -> Ruling:
    """Join dynamic letters into the words this cell's staff actually carries.

    ⚠️ **THE FIX IS THE OWNERSHIP QUERY, NOT THE SPELLING.**
    `export.measure_dynamics` uses NO VERTICAL INFORMATION AT ALL: it reads the
    detections of ONE measure dict and joins them by x-adjacency. Measured over
    1246 letters on 18 pages of 9 publishers, 73% of letters stand in their own
    staff's band and **24% in the band of the staff IMMEDIATELY ABOVE** --
    distance exactly 1, no exceptions -- because a measure cell is the staff
    plus four to six staff spaces of air and that air is where the neighbour
    prints its dynamics.

    ⚠️ **AND A BAND GATE IS THE WRONG FIX, MEASURED.** Dropping out-of-band
    letters under-emits on both arms (0.63 engraved, 0.59 scanned), because
    **83% of re-attributed letters are the target staff's SOLE evidence** --
    the mark exists once, in the wrong cell, and it is sole evidence *because
    `_dedupe_cross_staff_detections` already deleted the twin by distance*. A
    gate deletes it a second time. The letter has to MOVE, which is an
    ownership question, which is why this reads `Q.GLYPH_OWNER` rather than a
    threshold. That adjudicator already exists and already has a ladder /
    range / distance tier stack; nothing here re-implements it.

    So a letter belongs to this cell when the ownership verdict names this
    cell's STAFF, whatever cell it was cut from -- and a letter cut from this
    cell whose owner is another staff is dropped from it, both directions of
    the same move.

    ⚠️ **THE ASSEMBLY RULE IS DELIBERATELY THE EXPORTER'S, UNCHANGED**, so
    that the only difference between this and the shipped path is the
    ownership query and the frame. It is not a good rule: measured on the
    committed Brahms 1 transcription it produces `ppmsf` and `ppzmf` -- five
    letters run together, which no dynamic is -- and re-assembling on the
    MEDIAN letter width instead of the max moves kept runs 159 -> 162 and
    leaves those intact, so the max is not the fault. Changing it is a
    separate, measurable question and this records what a change would need:
    every run carries its own `band_offsets`, the vertical positions in the
    STAFF's frame that the exporter has never had.

    ⚠️ **AN UNSPELLABLE RUN IS `narrow`, NOT `abstain`.** "There is a mark here
    and I cannot spell it" is a different answer from "I saw nothing", and it
    is the answer for the dominant failure -- a lone `s` is an `sf` whose `f`
    was not detected. The candidates are every dynamic word the run could still
    become, which is exactly what a consumer needs to decide whether the
    agreed prefix is worth exporting (`export._partial_dynamic_word`).
    """
    mine = ev.subject.at(Kind.STAFF).to_key()
    system = ev.subject.at(Kind.SYSTEM)

    # ⚠️ Queried across the SYSTEM, not this cell, because ownership can carry
    # a letter INTO this staff from the cell above it. Filtering afterwards on
    # the owner verdict and the measure index is what makes that safe.
    rows = ev.rows(Q.DYNAMIC_LETTER, scope=Scope.SELF_AND_DESCENDANTS,
                   subject=system)
    if not rows:
        # ⚠️ THE THREE-STATE DISTINCTION, AT THE ONE PLACE IT DECIDES SOMETHING.
        # "The reader looked at this system and found no dynamic letter" is a
        # DECISION that this cell carries none. "No reader ran" is not, and
        # returning an empty word list for it would manufacture a fact out of
        # a missing rung -- exactly what `State.DECLINED` exists to prevent.
        blocked = [a for a in ev.refusals(
            Q.DYNAMIC_LETTER, scope=Scope.SELF_AND_DESCENDANTS, subject=system)
            if a.reason in (ABSTAIN.READER_UNAVAILABLE,
                            ABSTAIN.NOT_IMPLEMENTED)]
        if blocked:
            return Ruling.abstain(ABSTAIN.READER_UNAVAILABLE,
                                  blocked_rows=len(blocked))
        return Ruling(value=[], reason="no_letters",
                      detail={"letters": 0, "scope": "system"})

    kept: List[Tuple[float, float, float, str, Any]] = []
    moved_in = moved_out = no_frame = 0
    for row in rows:
        if row.subject.cell != ev.subject.cell:
            continue
        home = row.subject.at(Kind.STAFF).to_key()
        owner = ev.verdict(Q.GLYPH_OWNER, subject=row.subject)
        owned_by = (owner.value if owner is not None and owner.value
                    else home)
        if owned_by != mine:
            moved_out += (home == mine)
            continue
        moved_in += (home != mine)
        letter = _letter_of(row)
        geom = _geometry(row)
        if letter is None:
            continue
        if geom is None:
            no_frame += 1
            continue
        kept.append((geom[0], geom[1], geom[2], letter, row))

    if not kept:
        if no_frame:
            return Ruling.abstain("no_page_frame", letters_without_page_box=no_frame)
        if moved_out:
            return Ruling(value=[], reason="owned_elsewhere",
                          detail={"letters_moved_out": moved_out})
        return Ruling(value=[], reason="no_letters")

    kept.sort()
    width = max(x1 - x0 for x0, x1, _y, _l, _r in kept) or 1.0

    words: List[Dict[str, Any]] = []
    used: List[str] = []
    run: List[Tuple[float, float, float, str, Any]] = [kept[0]]
    prev_right = kept[0][1]
    for entry in kept[1:]:
        x0, x1, y, _letter, _row = entry
        if x0 - prev_right <= width and abs(y - run[0][2]) <= width:
            run.append(entry)
        else:
            words.append(_close(run))
            run = [entry]
        prev_right = x1
    words.append(_close(run))
    for w in words:
        used.extend(w.pop("_ids"))

    unspellable = [w for w in words if not w["spelled"]]
    detail: Dict[str, Any] = {
        "words": words, "letters": len(kept),
        "letters_moved_in": moved_in, "letters_moved_out": moved_out,
        "letters_without_page_box": no_frame,
        "assembly": "x_adjacency_max_letter_width_page_px",
    }
    if unspellable and not any(w["spelled"] for w in words):
        # ⚠️ Only the whole-cell case narrows. A cell holding one good `ff` and
        # one unspellable `s` has DECIDED something, and reporting it as
        # narrowed would lose the `ff`.
        return Ruling.narrow(
            [Candidate(value=c, support=1.0) for c in
             sorted({c for w in unspellable for c in w["completions"]})],
            reason="unspellable", used=used, **detail)
    return Ruling(value=[w["text"] for w in words if w["spelled"]],
                  reason="spelled", used=tuple(used), detail=detail)


def _close(run: List[Tuple[float, float, float, str, Any]]) -> Dict[str, Any]:
    """One assembled run, with the vertical evidence the exporter never had."""
    text = "".join(e[3] for e in run)
    offsets = [e[4].detail.get("band_offset_spaces") for e in run]
    offsets = [float(o) for o in offsets if o is not None]
    return {
        "text": text,
        "spelled": text in DYNAMIC_WORDS,
        "completions": sorted(w for w in DYNAMIC_WORDS if w.startswith(text)),
        "x_page": run[0][0],
        "n_letters": len(run),
        #: ⚠️ RECORDED, NOT USED. The letters of one word sit at one height, so
        #: a spread here is the signature of a run joined across two marks --
        #: the `ppmsf` shape. No constant is asserted because none has been
        #: measured; the numbers are emitted so one can be.
        "band_offsets": offsets,
        "band_offset_spread": (max(offsets) - min(offsets)) if offsets else None,
        "_ids": [e[4].id for e in run],
    }


@decision(
    quantity=Q.DIRECTION,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.DIRECTION_WORD,),
    scope=Kind.CELL,
    wants=(Q.DIRECTION_WORD,),
    # ⚠️ The subjects are the cells `Q.DIRECTION_WORD` speaks about --
    # OBSERVATIONS AND ABSTENTIONS ALIKE, because `subjects_for` reads
    # `log.all_rows()`. That is what makes the reader-unavailable state
    # REACHABLE: `gather_direction_words` files its page-wide reason on every
    # cell, so a machine with no OCR rung still ASKS this decision and still
    # gets a refusal back, rather than producing no subject and reporting a
    # silent `decided: 0`.
    subjects_from=Q.DIRECTION_WORD,
    reasons=("in_lexicon", "no_words", "reader_unavailable", "out_of_scope"),
    mode=Mode.ADDITIVE,
)
def adjudicate_direction(ev: Evidence) -> Ruling:
    """The direction words this bar of this staff carries.

    ⚠️⚠️ THE LEXICON GATE IS THE READER'S AND NOTHING HERE TOUCHES IT.
    `direction_text` subtracts every detection from the page's ink, refuses
    the curves by fill ratio, OCRs the residue with Surya and Tesseract, and
    accepts only what `direction_lexicon.lookup` names -- 181 musical terms,
    which CLAUDE.md records as load-bearing and never to be loosened. A word
    that reaches this decision has already been accepted; a word that did not
    arrives as an abstention with the reader's own reason on it. Re-testing
    the text here would be a second, differently spelled lexicon.

    ⚠️⚠️ SO WHAT IS LEFT TO DECIDE IS THE THREE-STATE ANSWER, AND IT IS THE
    WHOLE JOB. "There are no words in this bar" and "no reader ran over this
    page" produce the SAME empty list in the legacy path and in every figure
    derived from it, because a machine with neither `.venv-surya` nor
    Tesseract reads zero directions on every page exactly as a page with no
    directions printed on it does. `read_directions` says so in its own
    docstring and returns the counts to say it with; nothing consumed them.
    CLAUDE.md's governing rule is that **a fallback must never convert
    *cannot tell* into a definite answer**, and "this bar carries no words" is
    a definite answer. So the two are different outcomes here: a DECISION with
    an empty value, and an ABSTENTION.

    ⚠️ OWNERSHIP IS NOT RE-ASKED, unlike `adjudicate_dynamic`, and the
    asymmetry is geometric rather than an oversight. A dynamic LETTER reaches
    the exporter through a per-measure cell padded 4 to 6 staff spaces into
    the neighbouring staff, so 24% of letters stand in the wrong cell and the
    move is an ownership question. A direction word never passes through that
    frame: `direction_text._bands_for_page` works in PAGE pixels, gives the
    whole within-system gap to the upper staff and splits a between-system gap
    at its midpoint, so it "guarantees that no word is ever offered to two
    staves". The answer is already made, once, geometrically. Asking
    `Q.GLYPH_OWNER` about a word the detector never detected would also have
    nothing to answer with -- there is no contested detection to arbitrate.

    ⚠️ THE TWO RUNGS' DISAGREEMENT IS RECORDED AND NOT RE-ARBITRATED. Where
    Surya and Tesseract both accept and name different words the reader takes
    Surya by a documented precedence and counts the conflict; that count rides
    on the row. Moving the two rungs into the record as two INDEPENDENT
    readings -- which is what `READERS` is for, and what would let this
    decision weigh them -- means returning per-rung readings from
    `read_directions`, a change to the reader itself. That is not a wiring
    change and is deliberately not made here.
    """
    rows = ev.rows(Q.DIRECTION_WORD)
    if rows:
        # ⚠️ ORDERED BY PAGE x, the only frame these carry. It is used to
        # order marks WITHIN one bar and is never compared against a notehead
        # box: `Q.GLYPH_BOX` carries a CANONICAL x, and mixing the two frames
        # is the fault that made `Q.ONSET_COLUMN` report 1,062 columns of
        # nothing.
        words = []
        for row in rows:
            d = row.detail or {}
            words.append({
                "text": str(row.value),
                "category": d.get("category"),
                "placement": d.get("placement"),
                "x_page": d.get("x_page"),
                "reader": d.get("winning_reader"),
            })
        words.sort(key=lambda w: (w["x_page"] if w["x_page"] is not None
                                  else 0.0, w["text"]))
        return Ruling(value=[w["text"] for w in words], reason="in_lexicon",
                      used=tuple(r.id for r in rows),
                      detail={"words": words, "n_words": len(words)})

    blocked = [a for a in ev.refusals(Q.DIRECTION_WORD)
               if a.reason in (ABSTAIN.READER_UNAVAILABLE,
                               ABSTAIN.NOT_IMPLEMENTED)]
    if blocked:
        # ⚠️ AN ABSTENTION, NOT AN EMPTY VALUE. This is the one branch the
        # whole family is built around; see the docstring.
        return Ruling.abstain(ABSTAIN.READER_UNAVAILABLE,
                              blocked_rows=len(blocked),
                              note=(blocked[0].detail or {}).get("note"))
    off = [a for a in ev.refusals(Q.DIRECTION_WORD)
           if a.reason == ABSTAIN.OUT_OF_SCOPE]
    if off:
        return Ruling.abstain(ABSTAIN.OUT_OF_SCOPE, blocked_rows=len(off))

    refusals = ev.refusals(Q.DIRECTION_WORD)
    if not refusals:
        # No row of any kind: the gatherer never spoke about this cell, which
        # it is built never to do. Reported rather than assumed away.
        return Ruling.abstain(ABSTAIN.ABSENT)
    reasons: Dict[str, int] = {}
    for a in refusals:
        reasons[str(a.reason)] = reasons.get(str(a.reason), 0) + 1
    # ⚠️ A DECISION, and it is entitled to be one: the rungs RAN over this
    # bar's bands and either found no word-shaped ink or read nothing the
    # lexicon names. That is a reading of the page, not a missing rung.
    return Ruling(value=[], reason="no_words",
                  detail={"refusals": reasons,
                          "candidates_refused": sum(
                              n for r, n in reasons.items()
                              if r in (ABSTAIN.NO_READING,
                                       ABSTAIN.NOT_IN_LEXICON))})
