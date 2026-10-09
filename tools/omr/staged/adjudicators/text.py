"""Dynamics and direction words."""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from ..adjudicate import (Candidate, Checkable, Evidence, Mode, Ruling,
                          decision, is_relocated_copy)
from ..record import ABSTAIN, Kind, Q, Scope, Subject
from . import structure as _structure


#: The 17 words MusicXML has a `<dynamics>` child element for. Anything else a
#: run spells is `<other-dynamics>`, or nothing.
DYNAMIC_WORDS = frozenset({
    "p", "pp", "ppp", "pppp", "f", "ff", "fff", "ffff",
    "mp", "mf", "sf", "sfz", "fp", "rf", "rfz", "sfp", "fz",
})

#: ROADMAP 2.27c, registry `[C46 + L53]`
#: (`benchmarks/omr-owner-domain-2026-09/PLACEMENT-CONVENTIONS.md`'s
#: Dynamics-letters row). `Q.DYNAMIC_BAND_POSITION` is staff spaces BELOW
#: the HOME cell's own staff's bottom line (`gather._band_offset_spaces`;
#: negative means above the bottom line). Measured over 1246 letters on 18
#: pages of 9 publishers: 73% sit in their OWN staff's band (this project's
#: own dynamics-band study puts that population at +0.0 to +5.6 spaces) and
#: 24% sit in the band of the staff IMMEDIATELY ABOVE home -- "distance
#: exactly 1, no exceptions" -- with a measured EMPTY interval between the
#: two populations of (-3.04, -0.52) spaces (`capture.py`'s own
#: "UNREAD-POSITION Q.DYNAMIC_BAND_POSITION" note). A reading at or above
#: `DYNAMIC_OWN_BAND_MIN_SPACES` is this staff's own; one at or below
#: `DYNAMIC_ABOVE_BAND_MAX_SPACES` is decisively the staff above's; the gap
#: between the two is left exactly where it already stood (CLAUDE.md rule
#: 8, a fallback never turns "cannot tell" into an answer).
DYNAMIC_OWN_BAND_MIN_SPACES = -0.52
DYNAMIC_ABOVE_BAND_MAX_SPACES = -3.04


def _staff_above(subject: Subject) -> Optional[str]:
    """The key of the staff immediately above `subject`'s own staff, in the
    SAME system, or None where there is no staff above (the top staff of a
    system) or the subject carries no staff at all.

    ⚠️ Staff ordinals run top-to-bottom within a system (CLAUDE.md's own
    "staff is the index WITHIN ITS SYSTEM" -- `record.Subject`'s docstring),
    so "immediately above" is `staff - 1`, never a page-wide index.
    """
    staff_sub = subject.at(Kind.STAFF)
    if staff_sub is None or staff_sub.staff is None or staff_sub.staff <= 0:
        return None
    return Subject(Kind.STAFF, page=staff_sub.page, system=staff_sub.system,
                   staff=staff_sub.staff - 1).to_key()


def _staff_it_is_printed_below(row: Any) -> Optional[str]:
    """ROADMAP 2.68, Sean (DECISIONS 2026-10-08, restated 2026-10-09): *"It
    sits below the staff it belongs to."* The key of the staff this letter is
    printed BELOW -- or INSIDE -- read off the letter's own LOCAL positions
    (`local_position_in_staves`: half-steps from the top line of the staff
    above, its own and the staff beneath, each measured against that staff's
    own cell grid at the letter's x, filed by `gather_dynamic_letters`).

    The staff is the LAST one whose top line lies above the letter's centre:
    under staff N and above staff N+1's top line that is N; inside N+1's lines
    it is N+1. Neither distance nor an instrument range enters.

    None where it cannot tell (rule 8): no positions on the row (an older
    record), no position against its own staff, or the letter stands above
    every staff measured -- above a system's first staff there is nothing in
    this system to be below, and the old chain keeps what it had."""
    pos = (row.detail or {}).get("local_position_in_staves")
    if not isinstance(pos, dict) or "0" not in pos:
        return None
    try:
        measured = {int(k): float(v) for k, v in pos.items()}
    except (TypeError, ValueError):
        return None
    reached = [off for off, half_steps in measured.items() if half_steps >= 0.0]
    if not reached:
        return None
    staff = row.subject.at(Kind.STAFF)
    if staff is None or staff.staff is None:
        return None
    return Subject(Kind.STAFF, page=staff.page, system=staff.system,
                   staff=staff.staff + max(reached)).to_key()


#: Two letter boxes overlapping by this share of the SMALLER area are one
#: printed letter cut from two cells (`gather._same_ink_boxes`' own 0.5). Not
#: IoU: the same `f` boxed tall from one cell and as its lower half from the
#: other overlaps at IoU 0.28 (Brahms p0, the oboe's `f legato`) and was kept
#: twice -- `ff`.
SAME_LETTER_SHARE = 0.5


def _same_ink(a: Tuple[float, float, float, float],
              b: Tuple[float, float, float, float]) -> bool:
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return False
    small = max(1.0, min((a[2] - a[0]) * (a[3] - a[1]),
                         (b[2] - b[0]) * (b[3] - b[1])))
    return ix * iy >= SAME_LETTER_SHARE * small


def _has_a_twin_on(rows: Any, staff_key: str, row: Any) -> bool:
    """Is the SAME printed letter also a row cut from `staff_key`'s own cell?
    Then the copy cut from elsewhere is its duplicate. Without a twin it is
    the only evidence the mark exists, and it is moved, not dropped."""
    mine = (row.detail or {}).get("bbox_page_px")
    if not mine or len(mine) != 4:
        return False
    box = tuple(float(v) for v in mine)
    for other in rows:
        if other is row or other.subject.at(Kind.STAFF).to_key() != staff_key:
            continue
        theirs = (other.detail or {}).get("bbox_page_px")
        if theirs and len(theirs) == 4 and _same_ink(
                box, tuple(float(v) for v in theirs)):
            return True
    return False


#: ROADMAP 2.68 (twins). Two boxes of DIFFERENT letter classes are one printed
#: ink only where they are comparable boxes: the shared area must be at least
#: this share of the LARGER one. Measured on Litolff, the `s` of a printed `sf`
#: is a small box (14 x 26 px) tucked inside the `f`'s (42 x 48): shared area
#: 0.05-0.2 of the larger on 84 same-cell pairs, and those are TWO letters
#: (the 37 `sf` of Litolff p2-p3, seen on the print). One `p` boxed also as
#: `dynamicF` shares 0.47-0.99. Two boxes of the SAME class that nest are one
#: ink without this test -- no two printed `f`s nest.
SAME_INK_SHARE_OF_LARGER = 0.4


def same_ink_letters(a_box: Sequence[float], a_letter: Optional[str],
                     b_box: Sequence[float], b_letter: Optional[str]) -> bool:
    """Are these two dynamic-letter boxes ONE printed letter boxed twice?
    (`rest_is_a_duplicate_box`'s principle: one ink, one mark.) Distinct ink
    side by side (`ff`, `fp`, `sf`) is not."""
    ix = min(a_box[2], b_box[2]) - max(a_box[0], b_box[0])
    iy = min(a_box[3], b_box[3]) - max(a_box[1], b_box[1])
    if ix <= 0 or iy <= 0:
        return False
    area_a = max(1.0, (a_box[2] - a_box[0]) * (a_box[3] - a_box[1]))
    area_b = max(1.0, (b_box[2] - b_box[0]) * (b_box[3] - b_box[1]))
    if ix * iy < SAME_LETTER_SHARE * min(area_a, area_b):
        return False
    if a_letter == b_letter:
        return True
    return ix * iy >= SAME_INK_SHARE_OF_LARGER * max(area_a, area_b)


def _same_ink_groups(rows: Sequence[Any]) -> Dict[str, List[Any]]:
    """row id -> every row (itself included) on the same printed ink, across
    cells and staves of the system (transitive: a box boxed three times)."""
    items = []
    for r in rows:
        box = (r.detail or {}).get("bbox_page_px")
        if box and len(box) == 4:
            items.append((r, tuple(float(v) for v in box), _letter_of(r)))
    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if same_ink_letters(items[i][1], items[i][2], items[j][1], items[j][2]):
                parent[find(i)] = find(j)
    members: Dict[int, List[Any]] = {}
    for i, (r, _b, _l) in enumerate(items):
        members.setdefault(find(i), []).append(r)
    return {r.id: members[find(i)] for i, (r, _b, _l) in enumerate(items)}


#: ROADMAP 2.68 (twins): the ink HEIGHT, in staff spaces, each dynamic letter
#: can have. An `f` rises above the x-height and falls below it; a `p` only
#: falls; `s m z r` are x-height letters. MEASURED, not fitted to a result:
#: Sean's 12 hand-labelled `f` boxes (Brahms 317803 pdf 0) are 2.4-2.6 spaces
#: tall; the `p`s the two plates' detectors agree on, 1.4-2.1. The bands
#: leave a GAP (2.1-2.3) on purpose: an ink in it is read as neither, and the
#: identity abstains. WHAT WOULD FALSIFY IT: a printed `f` under 2.3 spaces
#: (a small-print edition) -- the first sign is `identity_by_ink` choosing `p`
#: for an ink Sean calls `f`.
INK_HEIGHT_BANDS_SPACES: Dict[str, Tuple[float, float]] = {
    "f": (2.3, 5.0),
    "p": (1.4, 2.1),
    "s": (0.0, 1.5), "z": (0.0, 1.5), "m": (0.0, 1.5), "r": (0.0, 1.5),
}


def _identity_of_ink(group: Sequence[Any]) -> Tuple[Optional[str], str, Tuple[str, ...]]:
    """Which letter is ONE ink the detector boxed as one or several classes?
    `(letter | None, how, the letters still possible)`.

    In order: every box agrees -> that letter (`agreed`). They disagree -> the
    ink's own height (`ink_height`): the letters whose band holds it; exactly
    one -> it. Otherwise None -- present, identity abstained (rule 8). The
    detector's SCORE is not consulted: on Brahms p1 it ranks the `f` twin above
    the printed `p` on 5 of 12 same-ink pairs.
    """
    letters = tuple(sorted({_letter_of(r) for r in group if _letter_of(r)}))
    if len(letters) == 1:
        return letters[0], "agreed", letters
    heights = [float(r.detail["ink_height_spaces"]) for r in group
               if (r.detail or {}).get("ink_height_spaces") is not None]
    if not heights:
        return None, "no_ink_measure", letters
    h = max(heights)
    fits = tuple(l for l in letters
                 if INK_HEIGHT_BANDS_SPACES.get(l) is None
                 or INK_HEIGHT_BANDS_SPACES[l][0] <= h <= INK_HEIGHT_BANDS_SPACES[l][1])
    if len(fits) == 1:
        return fits[0], "ink_height", letters
    return (None, "ink_height_fits_none" if not fits else "ink_height_fits_several",
            fits or letters)


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


def _canonical_grand_staff_owner(ev: Evidence, owned_by: str) -> str:
    """ROADMAP 2.27d, Sean, DECISIONS 2026-09-29 ("build anyway"):
    *"a dynamic between its two staves belongs to BOTH staves (the part),
    not one."* `owned_by` is `Q.GLYPH_OWNER`'s answer for one CONTESTED
    letter -- ink caught by BOTH staves' padded cells, which is exactly
    what makes it "between" them rather than merely detected once (an
    UNCONTESTED letter never reaches this function -- see the call site,
    inside `adjudicate_dynamic` below).

    On a DECIDED brace pair this rewrites that answer to the pair's own
    canonical member -- by convention the staff with the SMALLER staff
    ordinal (the upper of the two, matching where a shared MusicXML
    `<staves>` direction is filed by convention) -- so the SAME letter is
    filed ONCE, on ONE staff: this function is pure and deterministic in
    `owned_by`, so BOTH staves of the pair compute the identical canonical
    answer when their own `adjudicate_dynamic` calls it, and the existing
    `is_relocated_copy` dedupe (below) drops the copy cut from the other
    cell exactly as it already drops a same-staff duplicate detection.

    Off a decided brace (`grand_staff_partner_staff` returns `None`) this
    returns `owned_by` unchanged -- inert on every orchestral system, and
    on any letter that was never contested in the first place.

    ⚠️ A SEPARATE FUNCTION, DELIBERATELY, so 2.27c's own edit to the band
    rule in this same file touches neither this branch nor its call site.

    ⚠️ THE CHEAP HALF OF THE GATE IS READ DIRECTLY, HERE, ON PURPOSE: the
    common case on every orchestral system is that `owned_by`'s own SYSTEM
    never decides `Q.GROUP_SYMBOL` "brace" at all, so checking that (and
    `owned_by`'s own `Q.STAFF_GROUP`) before ever asking `structure` to
    enumerate the system's other staves is a real short-circuit, not
    ceremony -- and it is what makes `wants`' declaration of the two
    quantities true of THIS file's own body, not only of `structure.py`'s.
    """
    home_sub = Subject.from_key(owned_by)
    brace = ev.verdict(Q.GROUP_SYMBOL, subject=home_sub.at(Kind.SYSTEM))
    if brace is None or brace.value != "brace":
        return owned_by
    own_group = ev.verdict(Q.STAFF_GROUP, subject=home_sub)
    if own_group is None or own_group.value is None:
        return owned_by
    partner = _structure.grand_staff_partner_staff(ev, owned_by)
    if partner is None:
        return owned_by
    a = Subject.from_key(owned_by)
    b = Subject.from_key(partner)
    return owned_by if a.staff <= b.staff else partner


@decision(
    quantity=Q.DYNAMIC,
    checkable=Checkable.UNCHECKABLE,
    # ⚠️ 2.27d adds `Q.GROUP_SYMBOL`/`Q.STAFF_GROUP` (grand-staff canonical
    # owner); 2.27c adds `Q.DYNAMIC_BAND_POSITION` (the band rule for an
    # UNCONTESTED letter). Two separate branches below.
    composed_from=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER, Q.DYNAMIC_BAND_POSITION,
                   Q.DYNAMIC_IS_NOT_A_DYNAMIC, Q.GROUP_SYMBOL, Q.STAFF_GROUP,
                   Q.DIRECTION_WORD, Q.DYNAMIC_LETTER_NEIGHBOURS),
    scope=Kind.CELL,
    # ⚠️ ROADMAP 2.68 adds `Q.DIRECTION_WORD` and `Q.DYNAMIC_LETTER_NEIGHBOURS`:
    # a letter AMONG letters that make a KNOWN word is that word's letter
    # (`_is_a_letter_of_a_known_word`).
    wants=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER, Q.DYNAMIC_BAND_POSITION,
           Q.DYNAMIC_IS_NOT_A_DYNAMIC, Q.GROUP_SYMBOL, Q.STAFF_GROUP,
           Q.DIRECTION_WORD, Q.DYNAMIC_LETTER_NEIGHBOURS),
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
    gate deletes it a second time. So this asks ownership rather than a
    threshold; that adjudicator already exists and already has a ladder /
    range / distance tier stack, and nothing here re-implements it.

    ⚠️⚠️ **THAT MEASUREMENT IS THE LEGACY PATH'S AND ITS CONCLUSION DOES NOT
    CARRY HERE — CORRECTED 2026-09-11.** The sole-evidence case exists there
    *because the dedupe ran first*. On this path it did not, so the twin is
    still on the record, and a letter this staff is handed from another cell
    is a SECOND COPY of a letter this staff already has. Keeping it is how one
    printed `ff` reached the file as `ffff`. Worse, the rescue the paragraph
    above credits is **structurally unreachable here**: `glyph_owner`'s domain
    is `subjects_from=Q.GLYPH_BAND_DISTANCE`, the CONTESTED population, so a
    letter with no twin is never offered to another staff at all — its verdict
    names its own staff, `reason="no_contest"`, and it stays where it was cut.

    So a letter belongs to this cell when the ownership verdict names this
    cell's STAFF **and it was cut from this staff** — a letter cut from here
    and owned elsewhere is dropped as the neighbour's, and a letter cut
    elsewhere and owned here is dropped as this staff's own duplicate. The two
    drops are reported apart (`letters_moved_out`,
    `letters_dropped_as_duplicate`) because only the second is redundant.

    ⚠️⚠️ ROADMAP 2.27c: `Q.GLYPH_OWNER` NAMES NOTHING FOR THE UNTWINNED CASE,
    AND `Q.DYNAMIC_BAND_POSITION` IS WHAT SPEAKS THERE. `glyph_owner` only
    ever sees the CONTESTED population (`subjects_from=Q.GLYPH_BAND_
    DISTANCE`); a letter whose twin was never independently re-detected in
    the neighbour's own cell reaches this decision as `owner is None`, and
    the code above falls back to `home` unchanged -- which is right for the
    73% that really are home's own, and wrong for the 24% that are not.
    `Q.DYNAMIC_BAND_POSITION` is a SEPARATE, independently-scored reading
    (`READERS.GEOMETRY`, promoted rather than folded into the letter's own
    detector term -- CLAUDE.md's `correlated_groups` rule: "a second witness
    needs its own quantity and its own reader") of exactly the offset the
    band study measured. Only where `Q.GLYPH_OWNER` gave no decisive answer
    is it consulted, and only its own DECISIVE zone moves anything: a
    reading at or below `DYNAMIC_ABOVE_BAND_MAX_SPACES` reassigns `owned_by`
    to the staff immediately above home; the gap between the two measured
    populations, and a home staff with no staff above it, are left exactly
    as `home` already had them. This never overrides a `Q.GLYPH_OWNER`
    verdict that IS decided -- that query runs first and, where it names a
    staff, `owned_by` already differs from `home` before this is reached.

    ⚠️⚠️ ROADMAP 2.68, SEAN (DECISIONS 2026-10-08/09): *"It sits below the
    staff it belongs to."* The three paragraphs above are the FALLBACK. Where
    GATHER filed the letter's LOCAL positions against its neighbours' staves
    (`local_position_in_staves`), the staff it is printed below (or inside) is
    its owner and `Q.GLYPH_OWNER` is not asked: measured on the 10-09 small
    re-gather, 43 of 213 kept Litolff letters and 23 of 94 Brahms ones stood
    under the staff above their cell and the contest gave them to the staff
    beneath by `distance` (3.29 vs 3.02 spaces), `range_veto` (an instrument
    range has no say over a dynamic) or `tied`, and the 2.27c band rule that
    should have caught the rest reads a quantity gathered only under an OFF
    flag. Such a letter is a duplicate only where the same ink is also a row
    of the owner's own cell (`_has_a_twin_on`); otherwise it is the mark's
    sole evidence and MOVES. Not decided (and left to the chain): no
    positions, or above a system's first staff.

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
    dup_dropped = moved_out = no_frame = not_a_letter = inside_word = 0
    inside_alone = inside_unmeasured = in_a_dynamic_token = 0
    # ROADMAP 2.68 (twins): one printed letter boxed twice is ONE letter.
    ink_groups = _same_ink_groups(rows)
    seen_ink: set = set()
    alts_of: Dict[str, Tuple[str, ...]] = {}
    group_ids: Dict[str, List[str]] = {}
    same_ink_collapsed = identity_by_ink = identity_abstained = 0
    # ⚠️ ROADMAP 2.68: the words the OCR read anywhere on this system, in
    # page pixels -- a second reader (Tesseract/Surya, not the detector).
    word_boxes = [(tuple(float(v) for v in (w.detail or {})["bbox_page_px"]),
                   str(w.value or ""))
                  for w in ev.rows(Q.DIRECTION_WORD,
                                   scope=Scope.SELF_AND_DESCENDANTS,
                                   subject=system)
                  if (w.detail or {}).get("bbox_page_px")]
    grand_staff_shared = 0
    placed_below_n = 0
    for row in rows:
        if row.subject.cell != ev.subject.cell:
            continue
        # ⚠️⚠️ ROADMAP 3.4g — A REFUSED LETTER IS NOT SPELLED. One spurious
        # `f` beside a real one is the difference between `f` and `ff`, which
        # is the exact fault the `dup_dropped` branch below was written for,
        # arriving by the other door: there the second `f` is a TWIN of real
        # ink, here it is ink that is not a letter at all. Counted in
        # `detail` rather than dropped silently, so a word that lost a letter
        # can be traced to the refusal that took it.
        refused = ev.verdict(Q.DYNAMIC_IS_NOT_A_DYNAMIC, subject=row.subject)
        if refused is not None and refused.value is True:
            not_a_letter += 1
            continue
        home = row.subject.at(Kind.STAFF).to_key()
        owner = ev.verdict(Q.GLYPH_OWNER, subject=row.subject)
        # ⚠️ ROADMAP 2.68, SEAN: a dynamic sits below the staff it belongs to.
        # Where the letter's own LOCAL position says which staff it is below,
        # that is the owner -- `Q.GLYPH_OWNER` (distance, an instrument range,
        # a tie) is not asked, because none of them is a reason to move a
        # dynamic to the staff beneath it.
        placed_below = _staff_it_is_printed_below(row)
        owned_by = (placed_below if placed_below is not None
                    else owner.value if owner is not None and owner.value
                    else home)
        if placed_below is None and owner is not None and owner.value:
            # ⚠️ ROADMAP 2.27d, ONLY THE CONTESTED CASE. `owner` exists
            # here only for a letter `glyph_owner` actually adjudicated --
            # i.e. one BOTH staves' padded cells caught, which is the
            # ink this project's own convention calls "between" them
            # (`PLACEMENT-CONVENTIONS.md`, "Dynamics on a grand staff").
            # An uncontested letter (`owner is None`) is left alone: it
            # was printed once, for one staff, and canonicalising it would
            # RELOCATE a mark CLAUDE.md rule 6 says never to relocate from
            # pad position alone.
            owned_by = _canonical_grand_staff_owner(ev, owned_by)
            grand_staff_shared += (owned_by != (owner.value or home))
        # ⚠️ ROADMAP 2.27c: only where ownership gave NO decisive answer
        # (owned_by fell back to home, above) does the band position get a
        # say, and only in its own DECISIVE zone -- see the docstring.
        moved_by_band = False
        # (Merge of 2.27c with 2.27d: the band rule speaks ONLY where no
        # contest was decided -- `owner` absent or valueless -- so it can
        # never override a decided owner, including a grand-staff one.)
        if (placed_below is None and owned_by == home
                and (owner is None or not owner.value)):
            band_rows = ev.rows(Q.DYNAMIC_BAND_POSITION, subject=row.subject)
            if band_rows:
                offset = float(band_rows[-1].value)
                if offset <= DYNAMIC_ABOVE_BAND_MAX_SPACES:
                    above = _staff_above(row.subject)
                    if above is not None:
                        owned_by = above
                        moved_by_band = True
        if owned_by != mine:
            moved_out += (home == mine)
            continue
        # ⚠️ A BAND-POSITION RESCUE IS NEVER A DUPLICATE. `is_relocated_copy`
        # assumes `owned_by` came from `Q.GLYPH_OWNER`, whose domain is the
        # CONTESTED population -- a decided verdict naming another staff
        # exists only because that staff's own cell independently detected
        # the SAME ink, so `mine` already holds a twin and the copy this
        # `row` names must be dropped. A band-position rescue fires only
        # where `owned_by == home` (owner undecided/absent, i.e. UNCONTESTED
        # by construction) -- there is no twin on `mine` to be a duplicate
        # of, so skipping the check here is not a special case of the rule,
        # it is the rule's own premise not holding.
        if placed_below is not None:
            # a letter placed by its position is a duplicate only where the
            # SAME ink is also a row of this staff's own cell; else it is the
            # sole evidence of the mark and is moved here, not dropped
            if owned_by != home and _has_a_twin_on(rows, owned_by, row):
                dup_dropped += 1
                continue
        elif not moved_by_band and is_relocated_copy(row.subject, owned_by):
            # ⚠️⚠️ A LETTER WHOSE HOME IS ANOTHER STAFF IS A SECOND COPY, NOT
            # A RESCUE, AND THE DOCSTRING ABOVE USED TO CLAIM OTHERWISE.
            # `glyph_owner` speaks only about the CONTESTED population
            # (`subjects_from=Q.GLYPH_BAND_DISTANCE`), so a letter it hands to
            # this staff was detected in this staff's own cell too. Keeping
            # both is how one printed `ff` reached the file as `ffff`: on
            # Litolff Beethoven 5 p1-4 every one of the 21 long f/p words
            # traces to an overlapping letter pair, and 11 `ffff` + 10 `fff`
            # stood on a page Sean says prints only `ff`.
            #
            # The "83% of re-attributed letters are the target staff's SOLE
            # evidence" measurement is the LEGACY path's, where
            # `_dedupe_cross_staff_detections` had already deleted the twin
            # before the letters were read. Here it has not, and the sole-
            # evidence case cannot reach this branch at all: a letter with no
            # twin is uncontested, so its verdict names its own staff and it
            # is never offered to another.
            dup_dropped += 1
            continue
        # (after ownership: counted once, on the staff that keeps the letter)
        if _letter_of_a_known_word(row, word_boxes):
            sides = ev.rows(Q.DYNAMIC_LETTER_NEIGHBOURS, subject=row.subject)
            if not sides:
                # inside a known word, but nobody read the ink beside it:
                # CANNOT TELL, so it stays what the detector said (rule 8)
                inside_unmeasured += 1
            elif _is_a_letter_of_a_known_word(sides[-1].value):
                inside_word += 1
                continue
            else:
                inside_alone += 1
        elif _inside_a_read_word(row, word_boxes):
            # inside a read word's box, but the word's own text puts the spot
            # at its dynamic (`f espr.`, `P dolce`), or two readings disagree
            # about it: the dynamic stays
            in_a_dynamic_token += 1
        letter = _letter_of(row)
        geom = _geometry(row)
        group = ink_groups.get(row.id) or [row]
        if len(group) > 1:
            # ⚠️ ROADMAP 2.68 (twins, Sean 2026-10-09: *"many dynamic markings
            # could ... get double boxed"*). Every box on this ink is ONE
            # letter, written once; WHICH letter it is comes from the ink, and
            # where nothing separates the candidates the letter stays present
            # and its identity abstains.
            key = frozenset(r.id for r in group)
            if key in seen_ink:
                same_ink_collapsed += 1
                continue
            seen_ink.add(key)
            ident, how, possible = _identity_of_ink(group)
            boxes = [tuple(float(v) for v in r.detail["bbox_page_px"])
                     for r in group if (r.detail or {}).get("bbox_page_px")]
            geom = (min(b[0] for b in boxes), max(b[2] for b in boxes),
                    (min(b[1] for b in boxes) + max(b[3] for b in boxes)) / 2.0)
            group_ids[row.id] = [r.id for r in group]
            if ident is None:
                identity_abstained += 1
                letter = "?"
                alts_of[row.id] = possible
            else:
                identity_by_ink += (how == "ink_height")
                letter = ident
        if letter is None:
            continue
        if geom is None:
            no_frame += 1
            continue
        kept.append((geom[0], geom[1], geom[2], letter, row))
        placed_below_n += placed_below is not None

    if not kept:
        if no_frame:
            return Ruling.abstain("no_page_frame", letters_without_page_box=no_frame)
        if moved_out:
            return Ruling(value=[], reason="owned_elsewhere",
                          detail={"letters_moved_out": moved_out})
        # ⚠️ ROADMAP 3.4g. A cell whose every letter was REFUSED reports the
        # count rather than reading as a cell nobody found a letter in — the
        # READ / DECLINED distinction, one stage along.
        empty_detail = {}
        if not_a_letter:
            empty_detail["letters_refused_as_not_a_dynamic"] = not_a_letter
        if inside_word:
            empty_detail["letters_inside_a_read_word"] = inside_word
        return Ruling(value=[], reason="no_letters", detail=empty_detail)

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
            words.append(_close(run, alts_of))
            run = [entry]
        prev_right = x1
    words.append(_close(run, alts_of))
    for w in words:
        # ⚠️ KEPT PER RUN AS `letters` (ROADMAP 2.68): `used` flattens every
        # run's letters into one list, and the pairing of a word with ITS
        # dynamic (`consequences.pair_word_and_dynamic`) needs to know which
        # letters -- and so which page boxes -- made which dynamic. A letter
        # boxed twice lists every box on its ink.
        w["letters"] = [i for rid in w.pop("_ids") for i in group_ids.get(rid, [rid])]
        used.extend(w["letters"])

    unspellable = [w for w in words if not w["spelled"]]
    detail: Dict[str, Any] = {
        "words": words, "letters": len(kept),
        "letters_dropped_as_duplicate": dup_dropped,
        "letters_moved_out": moved_out,
        "letters_without_page_box": no_frame,
        # ⚠️ ROADMAP 3.4g. Letters a `Q.DYNAMIC_IS_NOT_A_DYNAMIC`
        # verdict refused, counted so a short word names its cause.
        "letters_refused_as_not_a_dynamic": not_a_letter,
        # ⚠️ ROADMAP 2.68. Letters AMONG letters of a word the OCR read and
        # the lexicon knows: the `p` of `più` boxed as `dynamicP`. Kept: a
        # letter inside such a word's box with no letter beside it (a `p`
        # standing alone is piano -- Sean 2026-10-09), and one whose
        # neighbours were never read.
        "letters_inside_a_read_word": inside_word,
        "letters_alone_inside_a_word_box": inside_alone,
        "letters_inside_a_word_box_unmeasured": inside_unmeasured,
        "letters_at_a_words_dynamic_token": in_a_dynamic_token,
        # ⚠️ ROADMAP 2.27d. Contested letters `_canonical_grand_staff_
        # owner` moved onto this staff (or off it) because they sit
        # between the two staves of a decided brace pair -- zero on every
        # system that never decides `Q.GROUP_SYMBOL` "brace".
        "letters_shared_on_grand_staff": grand_staff_shared,
        # ⚠️ ROADMAP 2.68. Letters kept on the staff they are printed BELOW
        # (Sean 2026-10-09), from their own local positions -- not by the
        # contest, the band flag or the cell they were cut from.
        "letters_placed_below_their_staff": placed_below_n,
        # ⚠️ ROADMAP 2.68 (twins). Boxes dropped because the SAME printed ink
        # was already a letter of this bar (one ink, one letter), the inks
        # whose letter the ink's height settled, and the inks whose identity
        # nothing settled (present, not spelled).
        "letters_same_ink_collapsed": same_ink_collapsed,
        "letters_identity_by_ink_height": identity_by_ink,
        "letters_identity_abstained": identity_abstained,
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


#: A letter box with at least this share of its area inside a word box is one
#: of the word's letters (ROADMAP 2.68).
INSIDE_READ_WORD_SHARE = 0.5


def _is_a_letter_of_a_known_word(sides) -> bool:
    """Sean 2026-10-09: *"When p is by itself it is piano when it is
    surrounded by other letter the context solves it ... only if it makes a
    word we know."* The KNOWN word is the caller's test (`_letter_of_a_known_word`:
    a word the OCR read AND the lexicon accepted, the letter in a token of its
    text that is not a dynamic); this is the other half --
    the letter has letter ink beside it on its own line
    (`Q.DYNAMIC_LETTER_NEIGHBOURS`). A letter with space on both sides is a
    dynamic even inside a word's box (`p espr.`: the `p` is the dynamic)."""
    return isinstance(sides, dict) and bool(sides.get("left") or sides.get("right"))


def _inside_a_read_word(row, word_boxes) -> bool:
    """Is this dynamic LETTER one of the letters of a word the OCR read?

    The detector reads italic text letter by letter and calls some of those
    letters dynamics: on Brahms p3 staff 12 it boxes the `p` of `più` as
    `dynamicP` and the `ù` as `dynamicM`, and the run beside the real `f`
    spelled `pmf`, which no dynamic is -- so the bar's dynamic abstained and
    the word could not be paired with its `f`. A word the OCR READ and the
    lexicon ACCEPTED is a second, independent reader saying that ink is text;
    a letter box mostly inside such a word's box is that word's letter, not a
    dynamic. Counted (`letters_inside_a_read_word`), never dropped silently.
    This is the BOX half; `_letter_of_a_known_word` adds the TEXT half.
    """
    return bool(_words_around(row, word_boxes))


def _words_around(row, word_boxes):
    """The read words whose box holds at least `INSIDE_READ_WORD_SHARE` of this
    letter's box: `[(box, text)]`."""
    box = (row.detail or {}).get("bbox_page_px")
    if not box or not word_boxes:
        return []
    x0, y0, x1, y1 = (float(v) for v in box)
    area = max(1.0, (x1 - x0) * (y1 - y0))
    out = []
    for item in word_boxes:
        # a bare box (no text read with it) or (box, text)
        w, text = (item if len(item) == 2 and not isinstance(item[0], (int, float))
                   else (item, None))
        ix = max(0.0, min(x1, w[2]) - max(x0, w[0]))
        iy = max(0.0, min(y1, w[3]) - max(y0, w[1]))
        if ix * iy >= INSIDE_READ_WORD_SHARE * area:
            out.append((w, text))
    return out


def _letter_of_a_known_word(row, word_boxes) -> bool:
    """Sean's DEDUCTIVE rule (2026-10-09), the TEXT half: *"only if it makes a
    word we know"*. The letter lies inside a word the OCR read and the lexicon
    accepted, AND the word's own text puts that spot in a token that is not a
    dynamic. A reading with no dynamic token in it (`espr. e legato`, `A PIZZ.`)
    holds no dynamic: every dynamic-classed box inside it is a letter of it. A
    reading that names one (`f espr. e legato`, `P dolce`, `p cresc. f`) holds
    the dynamic at its leading and/or trailing end: a letter standing there is
    the dynamic, one past it is the word's. Several words may hold the same ink
    (a sibling window, a joined reading): ALL must say `letter of the word`, or
    nothing is decided -- the letter stays what the detector said (rule 8)."""
    around = _words_around(row, word_boxes)
    if not around:
        return False
    box = row.detail["bbox_page_px"]
    # a word held with no text can say nothing about tokens: cannot tell
    return all(text is not None and _token_is_a_word(box, w, text)
               for w, text in around)


def _token_is_a_word(letter_box, word_box, text: str) -> bool:
    """Does the OCR'd `text`, laid along `word_box` in proportion to its
    characters, put the letter at `letter_box` in a token that is a word rather
    than a dynamic? The proportion is crude (an italic `p` is wider than the
    average letter), so only the two ENDS are asked, and by the letter's OUTER
    edge: a leading dynamic token (`f`, `P`, `fp`) claims the letters whose left
    edge falls in its share of the box plus its space; a trailing one the
    letters whose right edge does."""
    from ...direction_lexicon import _DYNAMIC_LETTERS, _normalise
    tokens = text.split()
    if not tokens:
        return False
    total = sum(len(t) for t in tokens) + len(tokens) - 1
    width = max(1.0, word_box[2] - word_box[0])
    per_char = width / max(1, total)
    lead = 0
    while lead < len(tokens) and _normalise(tokens[lead]) in _DYNAMIC_LETTERS:
        lead += 1
    trail = 0
    while (trail < len(tokens) - lead
           and _normalise(tokens[len(tokens) - 1 - trail]) in _DYNAMIC_LETTERS):
        trail += 1
    if lead == len(tokens):
        return False        # the text IS a dynamic: not a word at all
    if lead:
        chars = sum(len(t) for t in tokens[:lead]) + lead     # tokens + one space each
        if letter_box[0] <= word_box[0] + chars * per_char:
            return False
    if trail:
        chars = sum(len(t) for t in tokens[len(tokens) - trail:]) + trail
        if letter_box[2] >= word_box[2] - chars * per_char:
            return False
    return True


def _close(run: List[Tuple[float, float, float, str, Any]],
           alts: Optional[Dict[str, Tuple[str, ...]]] = None) -> Dict[str, Any]:
    """One assembled run, with the vertical evidence the exporter never had.

    `alts` maps a row id to the letters its ink may still be (ROADMAP 2.68,
    twins: one ink boxed as `dynamicF` and `dynamicP` whose identity nothing
    settled). Such a slot is written `?`. The run is spelled only where the
    lexicon leaves ONE reading (`s?` -> `sf`: `sp` is not a dynamic) and
    says so (`identity="lexicon"`); where it leaves several the run is not
    spelled and every word it could be is the candidate."""
    alts = alts or {}
    text = "".join(e[3] for e in run)
    slots = [sorted(alts.get(e[4].id) or (e[3],)) for e in run]
    open_slot = any(len(sl) > 1 for sl in slots)
    if open_slot:
        combos = {"".join(c) for c in itertools.product(*slots)}
        full = sorted(c for c in combos if c in DYNAMIC_WORDS)
        spelled = len(full) == 1
        if spelled:
            text = full[0]
        completions = full if full else sorted(
            w for w in DYNAMIC_WORDS if any(w.startswith(c) for c in combos))
        identity = "lexicon" if spelled else "open"
    else:
        spelled = text in DYNAMIC_WORDS
        completions = sorted(w for w in DYNAMIC_WORDS if w.startswith(text))
        identity = "read"
    offsets = [e[4].detail.get("band_offset_spaces") for e in run]
    offsets = [float(o) for o in offsets if o is not None]
    return {
        "text": text,
        "spelled": spelled,
        "identity": identity,
        "completions": completions,
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
    reasons=("in_lexicon", "no_words", "reader_unavailable", "out_of_scope",
             "no_detections"),
    mode=Mode.ADDITIVE,
)
def adjudicate_direction(ev: Evidence) -> Ruling:
    """The direction words this bar of this staff carries.

    ⚠️⚠️ THE LEXICON GATE IS THE READER'S AND NOTHING HERE TOUCHES IT.
    `direction_text` subtracts every detection from the page's ink, refuses
    the curves by fill ratio, OCRs the residue with Surya and Tesseract, and
    accepts only what `direction_lexicon.lookup` names -- **156** strings
    (`direction_lexicon.TERMS` 140 + `CONNECTIVE` 25, counted from the
    module), which CLAUDE.md records as load-bearing and never to be
    loosened. ⚠️ The figure read **181** here, in CLAUDE.md and in the
    2026-09-10 manager log until 2026-09-21; it was never 181, and the
    symbol-dossier sweep found it by counting. A word
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
    # ⚠️ SELF_AND_DESCENDANTS, AND THE DEFAULT WOULD HAVE READ NOTHING. A
    # word is gathered on the CANDIDATE's own glyph subject -- one row per
    # piece of word-shaped ink -- while the page-wide states are filed on the
    # CELL. `Scope.EXACT` sees only the second, so with the default this
    # decision would have reported `no_words` on every bar that HAS a word:
    # the "declared input that could never answer" shape, which this path has
    # now hit three times (`Q.STEM`'s 916 unread rows, `arc_owner`'s frame,
    # `wedge_anchor`'s ORDER position).
    rows = ev.rows(Q.DIRECTION_WORD, scope=Scope.SELF_AND_DESCENDANTS)
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
                # ONE marking: the word and the dynamic glyph(s) it includes
                # (`più f`); the export writes them as one direction and the
                # dynamic reader does not write the glyph a second time.
                "includes_dynamic_glyphs": list(
                    d.get("includes_dynamic_glyphs") or ()),
                "dynamics": list(d.get("dynamics") or ()),
            })
        words.sort(key=lambda w: (w["x_page"] if w["x_page"] is not None
                                  else 0.0, w["text"]))
        return Ruling(value=[w["text"] for w in words], reason="in_lexicon",
                      used=tuple(r.id for r in rows),
                      detail={"words": words, "n_words": len(words)})

    blocked = [a for a in ev.refusals(Q.DIRECTION_WORD,
                       scope=Scope.SELF_AND_DESCENDANTS)
               if a.reason in (ABSTAIN.READER_UNAVAILABLE,
                               ABSTAIN.NOT_IMPLEMENTED)]
    if blocked:
        # ⚠️ AN ABSTENTION, NOT AN EMPTY VALUE. This is the one branch the
        # whole family is built around; see the docstring.
        return Ruling.abstain(ABSTAIN.READER_UNAVAILABLE,
                              blocked_rows=len(blocked),
                              note=(blocked[0].detail or {}).get("note"))
    off = [a for a in ev.refusals(Q.DIRECTION_WORD,
                       scope=Scope.SELF_AND_DESCENDANTS)
           if a.reason == ABSTAIN.OUT_OF_SCOPE]
    if off:
        return Ruling.abstain(ABSTAIN.OUT_OF_SCOPE, blocked_rows=len(off))

    refusals = ev.refusals(Q.DIRECTION_WORD,
                       scope=Scope.SELF_AND_DESCENDANTS)
    if not refusals:
        # No row of any kind. `subjects_from` means this cannot be reached
        # from a real gather -- a subject EXISTS because a row named it -- so
        # this is the unreachable-by-construction case, reported rather than
        # assumed away. ⚠️ `NO_DETECTIONS` and not a new word: the vocabulary
        # already names "this reader produced no row here", and inventing a
        # second spelling for it would make a typo indistinguishable from an
        # absent reading, which is what the closed vocabulary is for.
        return Ruling.abstain(ABSTAIN.NO_DETECTIONS)
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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.13: the printed bar number
# ─────────────────────────────────────────────────────────────────────────────

import re as _re

_BAR_NUMBER_DIGITS = _re.compile(r"\d+")


def _bar_number_from_text(text: str) -> Optional[int]:
    """The integer a printed numeral names, or `None` if `text` is not one.

    ⚠️ A SECOND COPY OF `bar_number_text.bar_number_from_text`, DELIBERATELY.
    ADJUDICATE reads a FROZEN log and may import nothing that touches a
    raster or a subprocess -- `bar_number_text` imports `pytesseract` and
    `PIL` at call time inside `read_crop`, which this module must never do.
    The two are asserted equal by `test_staged_printed_bar_number.py` so they
    cannot drift; duplicating the five-line predicate is cheaper than a
    shared import that would make this decision's module graph reach a
    subprocess-capable reader.
    """
    if not text:
        return None
    runs = _BAR_NUMBER_DIGITS.findall(text)
    if len(runs) != 1:
        return None
    try:
        n = int(runs[0])
    except ValueError:
        return None
    if n <= 0 or n > 9999:
        return None
    return n


@decision(
    quantity=Q.PRINTED_BAR_NUMBER,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.PRINTED_BAR_NUMBER,),
    scope=Kind.SYSTEM,
    wants=(Q.PRINTED_BAR_NUMBER,),
    reasons=("read", "no_reading", "not_numeric",
             "ambiguous_multiple_readings"),
    mode=Mode.ADDITIVE,
)
def adjudicate_printed_bar_number(ev: Evidence) -> Ruling:
    """What the numeral GATHER read above this system's first bar MEANS, as
    an integer -- "what does this ONE thing mean, on what evidence" (ADJUDICATE,
    CLAUDE.md §4a).

    ⚠️ IT NEVER COMPARES AGAINST THE FILE'S OWN BAR COUNT. That comparison is
    a fact about the DOCUMENT's joined parts (`tools.omr.staged.export.
    _document_bar_offsets`), which does not exist until EXPORT -- this
    decision runs over the GATHERED log alone, exactly like every other
    ADJUDICATE decision, and reports only what the numeral itself says.
    `_printed_bar_number_check` (`export.py`) is where the two facts meet,
    and it NEVER renumbers or inserts a bar from the result -- see that
    function's own docstring.

    ⚠️ A REHEARSAL LETTER IS NOT THIS QUANTITY. Some editions print a
    rehearsal letter in the same spot a bar number would occupy on another;
    `_bar_number_from_text` refuses anything that is not EXACTLY one run of
    digits, so `"A"`, `"12 3"` (two runs -- which one is the bar number is a
    guess this refuses to make, CLAUDE.md rule 6) and an empty read all
    abstain rather than being coerced into a number.
    """
    rows = ev.rows(Q.PRINTED_BAR_NUMBER)
    if not rows:
        refusals = ev.refusals(Q.PRINTED_BAR_NUMBER)
        return Ruling.abstain("no_reading", n_refusals=len(refusals),
                              reasons=sorted({str(a.reason) for a in refusals}))

    numeric = [(row, _bar_number_from_text(str(row.value))) for row in rows]
    numeric = [(row, n) for row, n in numeric if n is not None]
    if not numeric:
        return Ruling.abstain("not_numeric",
                              texts=[str(row.value) for row in rows])

    values = sorted({n for _row, n in numeric})
    if len(values) > 1:
        candidates = tuple(Candidate(value=n, support=1.0) for n in values)
        return Ruling.narrow(candidates, "ambiguous_multiple_readings",
                             used=tuple(row.id for row, _n in numeric),
                             readings=values)

    row, n = numeric[0]
    return Ruling(value=n, reason="read", used=(row.id,),
                  detail={"raw_text": str(row.value)})
