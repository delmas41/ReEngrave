"""The clef — five readers, a floor, and the ability to say "I don't know".

⚠️ WHAT IS DIFFERENT FROM TODAY, in one list:

  * Today the measure-cell detector argmax WINS AT ANY CONFIDENCE. There is
    no floor anywhere in the chain. Here a contest inside `MARGIN_FLOOR`
    abstains and records the margin.
  * Today the CV locator is silenced by PRESENCE (`transcribe.py:1953`,
    `if read_clef and locate_c_clefs and clef_source is None`) -- a detector
    clef at 0.11 permanently mutes it. Here every reader speaks and the
    scoring decides.
  * Today one crop is chosen for the locator by a boolean
    (`_header_cell_beats_measure_cell`), and on 14 of 14 divergent staves it
    chose the crop the reader COULD NOT READ while the other had already
    been read and thrown away in the same run. Here both crops are rows.
  * Today the losing candidates are recorded (`clef_evidence["contest"]`, 29
    writer references) and read by NOBODY. Here they are the input.

⚠️ AND WHAT IS NOT DIFFERENT: the readers. None is retrained, re-tuned or
rewritten. This is a change to how their opinions are combined.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..adjudicate import (Candidate, Checkable, READINGS, Evidence, Mode, Ruling, Term, decision,
                          tally)
from ..record import ABSTAIN, Kind, Q, READERS, Scope, State
# ⚠️ The ONE measured answer to "which clef family is this class name",
# imported rather than restated: it collapses both spellings of the
# vocabulary (`clefCAlto` and DeepScoresV2's `cClefAlto`) onto one core, and a
# second copy here is precisely how `_c_family_support` came to be keyed on a
# name the detector never emits.
#
# ⚠️ ROADMAP 3.4f ALSO IMPORTS THE LINE TABLE AND TOLERANCE, for the same
# reason: `CLEF_BY_FAMILY_LINE["C"]` and `DEFAULT_CONFIG.max_residual` are
# the ONE measured answer to "which line does this position name" -- the CV
# locator already trusts them (`clef_geometry.resolve_clef`), and a second
# copy here is exactly how a human's row would drift from the locator's.
#
# ⚠️ AND `_clef_core` / `clef_name_from_class`, for what a human's OWN class
# choice (`clefC` / `clefCAlto` / `clefCTenor`) claims -- manager review of
# the first cut of 3.4f: a specific sub-class is a READING, not a class-only
# guess, and geometry must not silently overrule it. A second name table here
# is exactly how that reading would drift from `clef_geometry`'s.
from ...clef_geometry import (CLEF_BY_FAMILY_LINE, DEFAULT_CONFIG, _clef_core,
                              clef_family, clef_name_from_class)

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ ASSUMED CONSTANTS. NOT ONE OF THESE IS MEASURED.
#
# They are deliberately coarse and few. The project's standing finding is that
# an uncalibrated probability is worse than none (ECE 0.1277, top bin promising
# 0.989 and delivering 0.692), so a detector's confidence is used as a TIER,
# never as a multiplier. Three tiers, because three is what the evidence can
# plausibly support and a fourth would be invention.
# ─────────────────────────────────────────────────────────────────────────────

CONF_HIGH = 0.60          # (A-CLEF-1)
CONF_LOW = 0.30           # (A-CLEF-1)

W_DETECTOR_HIGH = 3.0     # (A-CLEF-2)
W_DETECTOR_MID = 1.5
W_DETECTOR_LOW = 0.4
W_LOCATOR = 2.0           # the CV C-clef locator, per crop it read
W_SPECIALIST = 1.0
W_CARRY = 1.5             # this part's own reading on another system
W_INSTRUMENT = 1.0        # the instrument's expected clef
W_DOSSIER = 4.0           # external truth, when admitted

#: A contest closer than this abstains. (A-CLEF-3)
#:
#: ⚠️ THE FLOOR IS THE POINT, NOT ITS VALUE. Today there is no floor at all,
#: so the number matters far less than its existence: the reachable change is
#: "a staff whose readers disagree says so" rather than "the winner is
#: better chosen".
#:
#: ⚠️ AND IT CARRIES TWO JOBS (A-CLEF-6). With a single candidate the
#: runner-up is 0, so this is also an ABSOLUTE floor on a lone reading -- a
#: solitary clef at confidence 0.05 with nothing corroborating it does not
#: take a staff. That is deliberate, but a sweep of this constant moves both
#: behaviours at once and the two should be reported apart.
MARGIN_FLOOR = 1.0

_GLYPH_TO_CLEF = {
    "clefG": "treble",
    "clefF": "bass",
    "clefUnpitchedPercussion": "percussion",
}

#: The five clefs that are the SAME GLYPH on different lines.
C_CLEF_NAMES = ("alto", "tenor", "soprano", "mezzosoprano", "baritone")

#: The clefs `key_signature_geometry` has slot tables for. A run fitting all
#: four discriminates nothing.
_SLOT_TABLE_CLEFS = ("treble", "bass", "alto", "tenor")

#: What a `clefC` detection is worth as support for a C clef the LOCATOR
#: named. It cannot name one itself. (A-CLEF-5)
W_C_FAMILY = 1.5

#: What "this glyph is standing ON this staff" is worth. (A-CLEF-8)
#:
#: ⚠️ THE ONE CONSTANT IN THIS FILE THAT SITS ON AN EMPTY GAP RATHER THAN ON
#: AN ASSUMPTION, and the gap is wide. A measure cell is the staff plus four
#: staff spaces of air, so on a conductor's page a NEIGHBOURING staff's clef
#: lands in this staff's cell. Measured over two scanned pages, the six staves
#: whose clef could not decide each hold one glyph at **+3.1 to +3.5 steps**
#: and the rest at **-6.9, -5.8, -4.8, +13.3, +13.6, +14.8** -- nothing
#: between +3.5 and +13.3, nothing between -4.8 and +3.1.
#:
#: It must EXCEED `MARGIN_FLOOR`, because the population it is for is an exact
#: tie: five of those six score 3.0 against 3.0, two clef glyphs at high
#: confidence on one staff, and a term that only matches the floor leaves them
#: abstaining.
W_ON_THIS_STAFF = 1.5

#: A five-line staff spans 0..+8 steps measured DOWN from the top line. The
#: band is widened by one space each way because a clef's BOX centre is not
#: its notated line -- a bass clef reads +3.1..+3.5 here and a treble clef
#: sits lower in its own box.
#:
#: ⚠️ WIDE ON PURPOSE. The separation measured is 8 steps clear on the near
#: side, so nothing here needs a tight band; a tight one would start deciding
#: cases the evidence does not separate.
ON_STAFF_MIN_STEPS = -2.0
ON_STAFF_MAX_STEPS = 10.0


#: What "the measured accidental run fits this clef's slot table" is worth.
#: (A-CLEF-7) ⚠️ Contributed only when the fit DISCRIMINATES -- a run that fits
#: every candidate says nothing, and a 0-accidental key fits them all.
W_KEYSIG_FIT = 1.5


def _clef_of(glyph_name: str) -> Optional[str]:
    """⚠️ A CLASS NAME CANNOT NAME A C CLEF. Every C clef returns None, on
    purpose -- `clefC` AND the fine `clefCAlto` / `clefCTenor`.

    Alto, tenor, soprano, mezzo and baritone are THE SAME GLYPH on different
    lines, so `clefC` says a C clef is present and nothing about WHICH -- only
    geometry can, which is exactly why `clef_geometry.py` exists.

    ⚠️⚠️ AND THE FINE SPELLINGS LOOK LIKE AN EXCEPTION AND ARE NOT, WHICH IS
    THE ONE THING A READER IS MOST LIKELY TO GET WRONG HERE. `clefCAlto` and
    `clefCTenor` are separate trained classes that DO appear to name the
    line, so adding them to `_GLYPH_TO_CLEF` reads like a free repair.

    Measured, it is not -- and THE FIRST DRAFT OF THIS PARAGRAPH OVERCLAIMED
    HOW, which the mutation battery caught and review did not. It said the
    class name would "flip a staff that is right today to wrong". On Brahms 1
    p3/s1/st11 the detector fires `clefCTenor` where the locator measures
    ALTO on TWO crops at 0.91 -- staff 11 of a 14-staff system whose staff 12
    reads tenor, i.e. viola over cello -- and naming the clef does NOT flip
    it: two crops are two signals, so alto holds 2.0 + 2.0 + 1.5 = 5.5
    against tenor's 3.0 + 1.5 = 4.5. What it does is take that staff from
    UNCONTESTED to a margin of exactly `MARGIN_FLOOR` (1.0), one crop or one
    confidence tier from a NARROWED verdict -- i.e. one step from losing its
    clef altogether.

    ⚠️ AND THE CORRECTION OVERCLAIMED TOO, WHICH IS WHY THE ARM EXISTS. It
    then said the class name flips any staff whose locator read ONE crop. Run
    over all nine affected staves with their real evidence
    (`benchmarks/omr-staged-c-clef-2026-09/clef_flip_arm.py`): **0 FLIP, 2
    margins eroded**. `staff/1/1/10` does have one crop and does NOT flip,
    because it also carries two `clefCAlto` detections that AGREE. No staff on
    either document has the shape that flips; 4.5-against-3.5 is a synthetic
    demonstration of the mechanism. Twice now a claim about this contest was
    reasoned instead of run, and twice it was wrong: a weighted contest is
    decided by how many INDEPENDENT rows a candidate has, which is a property
    of the page and not of the weight table.

    ⚠️ The class could not express the answer anyway: DeepScoresV2 annotates
    only alto and tenor, so a soprano, mezzo or baritone clef can arrive only
    under one of those two names. They are admitted as FAMILY support instead
    (`_c_family_support`), which is what the detector can honestly claim.

    ⚠️ THE FIRST CUT OF THIS MODULE MAPPED `clefC -> alto` AND CALLED IT A
    PLACEHOLDER. That was worse than it looked: the detector's weight (3.0 at
    high confidence) would have BEATEN the locator's measured name (2.0), so
    the placeholder would have outvoted the only reader that can actually
    answer the question -- and any measurement taken then would have priced
    the placeholder rather than the mechanism.

    So a `clefC` detection now contributes FAMILY SUPPORT to whichever C clef
    the locator named, and names none on its own. With no locator reading, the
    clef abstains rather than guessing alto.
    """
    return _GLYPH_TO_CLEF.get(glyph_name)


def _c_family_support(ev: Evidence):
    """C-clef detections, as support for a C clef somebody else named.

    ⚠️⚠️ THIS MATCHED THE LITERAL STRING `"clefC"`, WHICH FIRES ZERO TIMES.
    `clefC` is the COARSE spelling (id 142) and `class_aliases` records the
    whole coarse block firing zero times on every document measured; the
    detector emits the FINE `clefCAlto` / `clefCTenor` instead. So the one
    mechanism built to let a detector's C clef contribute was keyed on a name
    that never arrives, and the names that do arrive reached neither this
    function nor `_clef_of`. Measured over both shared records: 16 C-clef
    detections on 9 staves, every one silent.

    ⚠️ THE FAMILY, NOT THE NAME, AND THE DISTINCTION IS THE WHOLE POINT. A
    `clefCAlto` detection is admitted here as evidence that a C clef IS
    PRESENT -- which is all `_clef_of` will let any class name claim, and
    this measurement is why that refusal stands rather than being relaxed for
    the fine spellings. On Brahms 1 p3/s1/st11 the detector fires
    `clefCTenor` and the locator measures ALTO, twice, at 0.91; the staff is
    staff 11 of a 14-staff system with `clefCTenor`/tenor on staff 12 below
    it, which is viola-in-alto over cello-in-tenor. ⚠️ Letting the fine name
    into `_GLYPH_TO_CLEF` does NOT flip that particular staff -- two locator
    crops outweigh it 5.5 to 4.5 -- but it takes the staff from UNCONTESTED
    to a margin of exactly `MARGIN_FLOOR` -- one step from a NARROWED
    verdict. Measured over all nine affected staves, the naming mutation
    flips **none** of them and erodes **two** margins; see `_clef_of`, which
    records that BOTH earlier statements of this cost were reasoned rather
    than run, and what caught each. One disagreement in nine is still enough:
    the class names the family, geometry names the line -- and DeepScoresV2
    has no soprano, mezzo or baritone class at all, so the name could not
    carry the answer even when it is right.
    """
    out = []
    for row in ev.rows(Q.CLEF_GLYPH):
        if clef_family(str(row.value)) == "C":
            out.append(row)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ ROADMAP 3.4f -- A HUMAN'S OWN C-CLEF BOX MAY NAME ITS LINE.
#
# `_clef_of` and `_c_family_support` above are right for the DETECTOR: a
# class name cannot say WHICH C clef, only geometry can. They are wrong for a
# PERSON, who did not classify a glyph -- he read which line the clef is
# printed on, and `review/human_evidence.py` files that reading as the SAME
# `Q.CLEF_POSITION` row `gather_clef` files for a detected clef (measured on
# Sean's own `act-0001`, `benchmarks/omr-stage-review-2026-09/FINDINGS.md`
# §C7a: a relabel to `clefCAlto` filed a position 0.083 of a step off the
# printed middle line, and the clef stayed ABSTAINED `no_candidates` because
# nothing named a candidate at all). Everything below is ONE branch on
# `_c_family_support`'s population, keyed on the row's READER -- see the call
# site in `adjudicate_clef`.
# ─────────────────────────────────────────────────────────────────────────────

#: Readers `review/human_evidence.py` may stamp on a box a person drew --
#: `record.READERS`'s own closed "THE HUMAN (roadmap 3.4)" section.
#:
#: ⚠️ SESSION_TEST COUNTS TOO, AND THAT IS NOT A RELAXATION. `record.READERS`
#: says SESSION_TEST rows are "NOT A HUMAN WITNESS" and must never be read as
#: evidence ABOUT THE PRINT -- true, and irrelevant to what this tuple gates.
#: This gates which rows may exercise the REVIEW WIRING, not which rows are
#: admissible as measurement: `ownership._human_owner` and
#: `notehead_precision._human_not_a_symbol` already treat SEAN and
#: SESSION_TEST identically for the same reason -- a session standing in for
#: a person exercises the IDENTICAL mechanism a real reading would -- and
#: this lane's own real-case artefact
#: (`benchmarks/omr-stage-review-2026-09/out/relabel-clefCAlto.sidecar.json`,
#: `staff/3/0/9`) is itself stamped `"session-test"`, not `"sean"`. A reader
#: outside this closed section can never reach a `Q.CLEF_GLYPH` row in the
#: first place -- `human_evidence.py` refuses an unrecognised reader at
#: ingest -- so widening this tuple is never silent; it is a one-line,
#: reviewed change beside the vocabulary it mirrors.
_HUMAN_CLEF_READERS = (READERS.SEAN, READERS.SESSION_TEST)


def _is_human_clef_reader(reader: Optional[str]) -> bool:
    return reader in _HUMAN_CLEF_READERS


#: `Q.CLEF_POSITION` counts HALF-spaces down from a staff's TOP line
#: (`gather_clef`, `_on_staff_rows` below): a five-line staff's own lines
#: fall at steps 0, 2, 4, 6, 8 -- `test_staged_c_clef.py`'s fixture: a 40px
#: line spacing, `half_step` 20px, the middle line at position 4.0.
#: `clef_geometry.DEFAULT_CONFIG.max_residual` is in units of one FULL line
#: spacing, i.e. two of these steps -- the conversion below is that ratio,
#: not a second calibration.
_STEPS_PER_LINE_SPACING = 2.0

#: What a human's OWN C-clef reading is worth once it names a candidate --
#: whether the name comes from his measured POSITION (the unplaced `clefC`
#: case), from his CLASS confirmed by that position, or from his CLASS alone
#: where the position can't confirm or contradict it. (A-CLEF-9) ⚠️ NOT
#: MEASURED, like every weight in this file (line 38ff). Set equal to
#: `W_LOCATOR` because it plays the IDENTICAL functional role -- naming a C
#: clef's LINE from something more than a bare class label -- not because a
#: measurement has shown them equal; none has. A lone human reading clears
#: `MARGIN_FLOOR` on its own -- the same absolute floor a lone detector or
#: locator reading must clear (line 66ff).
W_HUMAN_C_LINE = W_LOCATOR


def _human_clef_position(ev: Evidence, glyph_row: Any) -> Optional[Any]:
    """The `Q.CLEF_POSITION` row `review/human_evidence.py` filed beside this
    SAME box -- matched by reader and `y_center`, the one key the two rows
    share (see `_on_staff_rows`). Both come from one ingest of one review
    action, so an exact float match is the same value computed twice, not a
    coincidence to guard against.
    """
    y_center = (glyph_row.detail or {}).get("y_center")
    if y_center is None:
        return None
    for row in ev.rows(Q.CLEF_POSITION):
        if row.reader != glyph_row.reader:
            continue
        row_y = (row.detail or {}).get("y_center")
        if row_y is not None and float(row_y) == float(y_center):
            return row
    return None


def _snap_c_clef_position(position: float) -> Optional[Tuple[str, float]]:
    """Which of the five staff lines this measured position sits on, read as
    a C clef -- `(name, residual_in_line_spacings)`, or `None` where the
    position will not snap within tolerance.

    CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: this reuses
    `clef_geometry.CLEF_BY_FAMILY_LINE["C"]` and `DEFAULT_CONFIG.
    max_residual` rather than restating either, on the assumption that a
    cell's recovered grid always places a staff's five lines at steps
    0/2/4/6/8 in `Q.CLEF_POSITION`'s own units -- true of every grid measured
    so far (`test_staged_c_clef.py`). It would be falsified by a grid
    recovered from other than 5 visible staff lines; `Q.CLEF_POSITION`
    carries no line count to check that against, so this cannot detect that
    case and does not try to.
    """
    nearest_step = round(position / _STEPS_PER_LINE_SPACING) * _STEPS_PER_LINE_SPACING
    if not (0.0 <= nearest_step <= 8.0):
        return None
    residual = abs(position - nearest_step) / _STEPS_PER_LINE_SPACING
    if residual > DEFAULT_CONFIG.max_residual:
        return None
    line_from_bottom = 5 - int(nearest_step // _STEPS_PER_LINE_SPACING)
    name = CLEF_BY_FAMILY_LINE["C"].get(line_from_bottom)
    if name is None:
        return None
    return name, residual


#: Reason word filed in `detail` (not returned as the verdict's own `reason`
#: -- the verdict may still be `scored` on OTHER evidence) when a human's own
#: two witnesses -- the class he clicked, the position he drew -- disagree.
CONTRADICTION_REASON = "human_class_contradicts_position"


def _human_class_name(value: str) -> Optional[str]:
    """The alto/tenor name a human's OWN class choice claims, or `None` where
    he left it UNPLACED.

    `review/static/labels.js` offers three C-clef choices: `clefC` ("C clef
    (alto or tenor -- unplaced)"), `clefCAlto` ("alto clef") and `clefCTenor`
    ("tenor clef"). Clicking one of the latter two is a READING -- he looked
    at the print and said which one -- and is treated as evidence in its own
    right below; clicking the first is exactly as unplaced as a detector's
    `clefC` box would be, and geometry is the only thing that can name it.

    ⚠️ `clef_geometry.clef_name_from_class` answers `"alto"` for EVERY
    C-family class, including the unplaced one -- that is ITS fallback
    default for when geometry cannot run at all, not a signal that the class
    was specific. Telling "unplaced" apart from "specifically alto" needs
    `_clef_core`: the unplaced class's core is the bare family letter, `"c"`,
    and a specific one's is longer (`"calto"`, `"ctenor"`).
    """
    core = _clef_core(value)
    if not core or core == "c":
        return None
    return clef_name_from_class(value)


def _human_named_c_clef(ev: Evidence, glyph_row: Any
                         ) -> Tuple[Optional[Tuple[str, Term]], Optional[str]]:
    """Does this human's C-clef box name a candidate -- and where his own two
    witnesses (the class he clicked, the position he drew) disagree, say so
    rather than letting one silently overrule the other.

    Returns `(named, contradiction)`. `named` is `(clef_name, Term)` to add
    to the contest, or `None`. `contradiction` is `CONTRADICTION_REASON`, or
    `None`. Manager review of the first cut of this function (it let geometry
    decide unconditionally): four cases, by `_human_class_name`.

      **UNPLACED** (`clefC`) -- he named a C clef and nothing more; geometry
      alone may name the line, exactly as it does for the CV locator. Citing
      the POSITION row only, exactly as `_locator_terms` cites the locator's
      -- citing the glyph row too would put the term in the wrong correlated
      group and risk double-counting against `_c_family_support`'s own
      (glyph-row) citation for a row that falls through instead. Unsnappable
      -> `(None, None)`: the pre-existing family-support-only path.

      **SPECIFIC CLASS** (`clefCAlto` / `clefCTenor`), **geometry AGREES** --
      two of his own witnesses corroborate one answer. Cites BOTH rows: the
      glyph row is now itself evidence (the class IS the reading), and the
      position confirms it.

      **SPECIFIC CLASS, geometry NAMES A DIFFERENT LINE** -- a contradiction
      between two things ONE PERSON said. Geometry does not get to overrule
      the class he read, and the class does not get to overrule the position
      he measured either: name NOTHING (CLAUDE.md rule 8, a fallback never
      turns "cannot tell" into an answer), fall through to plain family
      support, and say why via `CONTRADICTION_REASON` so `trace` shows it.

      **SPECIFIC CLASS, position does not snap within tolerance** (a loosely
      drawn box, or no recoverable position at all) -- geometry has nothing
      to contradict him with, so his reading of the CLASS stands alone,
      citing the glyph row.
    """
    class_name = _human_class_name(str(glyph_row.value))
    pos_row = _human_clef_position(ev, glyph_row)
    snapped = (_snap_c_clef_position(float(pos_row.value))
               if pos_row is not None else None)

    if class_name is None:
        # UNPLACED: geometry alone may name the line.
        if snapped is None:
            return None, None
        name, _residual = snapped
        return (name, Term("human_c_clef_line", W_HUMAN_C_LINE,
                            (pos_row.id,))), None

    if snapped is None:
        # A loose box, or an unrecoverable grid: nothing to contradict him
        # with. His reading of the CLASS stands alone.
        return (class_name, Term("human_c_clef_class_name_only",
                                  W_HUMAN_C_LINE, (glyph_row.id,))), None

    geom_name, _residual = snapped
    if geom_name == class_name:
        return (class_name, Term("human_c_clef_line_confirmed",
                                  W_HUMAN_C_LINE,
                                  (glyph_row.id, pos_row.id))), None

    return None, CONTRADICTION_REASON


def _on_staff_rows(ev: Evidence) -> Dict[float, Any]:
    """`{y_center: position row}` for the clef glyphs the GRID could place.

    ⚠️ Keyed on `y_center` because that is what the two readers share: the
    detector's row records where it saw the glyph, and the geometry row
    records what that y means on this staff's own lines. Nothing else pairs
    them, and inventing a shared index would put an ordering assumption
    between two readers.
    """
    return {float(r.detail.get("y_center", -1e9)): r
            for r in ev.rows(Q.CLEF_POSITION)}


def _stands_on_this_staff(row) -> Optional[bool]:
    """Is this clef glyph standing on THIS staff, or on a neighbour?

    ⚠️ `None` WHERE THE CELL HAD NO GRID, not False. A staff whose lines were
    never measured cannot answer the question, and treating "unmeasured" as
    "off the staff" would silently withdraw the detector's evidence on exactly
    the pages whose geometry is worst.
    """
    if row is None:
        return None
    return ON_STAFF_MIN_STEPS <= float(row.value) <= ON_STAFF_MAX_STEPS


def _detector_terms(ev: Evidence) -> Dict[str, List[Term]]:
    out: Dict[str, List[Term]] = {}
    placed = _on_staff_rows(ev)
    for row in ev.rows(Q.CLEF_GLYPH):
        name = _clef_of(str(row.value))
        if name is None:
            continue
        score = row.score if row.score is not None else 0.0
        if score >= CONF_HIGH:
            w = W_DETECTOR_HIGH
        elif score >= CONF_LOW:
            w = W_DETECTOR_MID
        else:
            # ⚠️ NOT dropped. A low-confidence reading is weak evidence, not
            # no evidence -- and dropping it is how the incumbent chain ends
            # up with an argmax over one survivor.
            w = W_DETECTOR_LOW
        out.setdefault(name, []).append(
            Term(f"detector@{score:.2f}", w, (row.id,)))

        # ⚠️ ADDITIVE, NOT A FILTER, and the difference is the whole design.
        # Removing an off-staff glyph's term would make an arbitration
        # invisibly -- and it would be the WRONG call where a staff's only
        # candidate stands off it, which is still the best evidence there is.
        # A glyph standing ON this staff simply gets a second term.
        #
        # ⚠️ AND IT CITES THE GEOMETRY ROW, NOT THE GLYPH ROW. Citing the
        # glyph would put this term in the detector's own correlated group,
        # where `tally` counts the group once and 1.5 beside 3.0 is 3.0.
        pos_row = placed.get(float(row.detail.get("y_center", -1e9)))
        if _stands_on_this_staff(pos_row):
            out[name].append(
                Term("stands_on_this_staff", W_ON_THIS_STAFF, (pos_row.id,)))
    return out


def _locator_terms(ev: Evidence) -> Dict[str, List[Term]]:
    """Both crops. Two rows on two frames are TWO signals; the correlation
    check only collapses them if they are really the same reading."""
    out: Dict[str, List[Term]] = {}
    for row in ev.rows(Q.CLEF_LOCATED):
        name = str(row.value)
        out.setdefault(name, []).append(
            Term(f"locator@{row.frame}", W_LOCATOR, (row.id,)))
    return out


def _carry_terms(ev: Evidence, *,
                 page_spoke: bool) -> Tuple[Dict[str, List[Term]], int]:
    """This part's own clef on another system, and the SUPPLIED one.

    ⚠️ The carry is `clef_continuity`'s mechanism, which is the ONE carry in
    the existing pipeline that survives -- it is keyed on the staff's ROLE
    within its system rather than on `(page, system, staff)`, which is
    exactly why it inherits across systems while the three key/clef/meter
    carry dicts can never hit. Same idea, expressed as evidence rather than
    as a seed. It is UNTOUCHED by the gap rule below.

    ⚠️⚠️ THE `dossier` TIER IS ADMITTED **GAPS ONLY**, AND THAT IS THE WHOLE
    OF WHAT MAKES IT AN OPTION RATHER THAN AN OVERRIDE. A supplied clef is
    the one term here that did not come off this page at all, and
    `W_DOSSIER = 4.0` stands ABOVE `W_DETECTOR_HIGH = 3.0` -- so on any staff
    where the page WAS read it did not corroborate the reading, it replaced
    it, silently, including where the reading was right and the sheet was a
    typo. Sean, 2026-09-21: *"redo our work tonight to be an option to turn
    on when we can't get the info we need"*; the information we could not get
    is the only place it may speak.

    ⚠️ The precedent is `adjudicate_key_signature`, whose template reader
    answers GAPS ONLY for the identical reason and whose own measurement
    refused letting the fuller reading win. Inherited rather than
    re-litigated.

    ⚠️ It is a REFUSAL TO SPEAK, not a weight change. Lowering `W_DOSSIER`
    below the detector would still let a supplied clef out-vote a *pair* of
    weak read terms, and would make the honest case -- a staff nothing was
    read on -- weaker for no reason. The two questions are *may it speak
    here* and *how loud*, and only the first one is in doubt.

    Returns the terms, and how many supplied rows were WITHHELD, so the
    verdict can carry the count rather than the rule being silent.
    """
    out: Dict[str, List[Term]] = {}
    withheld = 0
    for row in ev.rows(Q.CLEF_SEED):
        name = str(row.value)
        if row.detail.get("tier") == "dossier":
            if page_spoke:
                withheld += 1
                continue
            out.setdefault(name, []).append(
                Term("supplied", W_DOSSIER, (row.id,)))
            continue
        out.setdefault(name, []).append(Term("carry", W_CARRY, (row.id,)))
    return out, withheld


@decision(
    quantity=Q.CLEF,
    checkable=Checkable.MIXED,
    checked_by=(
        "implied pitches: this staff's own measured positions under this candidate must fall in the instrument's written range (clef_correction.propose_clef) -- ⚠️ DECLARED AND NOT IMPLEMENTED, and it cannot be here: it needs the INSTRUMENT, which abstains on 22 of 22 and 27 of 27 staves of the two scanned pages measured. `inventory --check` lists it",
        "the glyph stands ON this staff: a measure cell is the staff plus four staff spaces of air, so a neighbour's clef lands in it -- and unlike the range test this needs NO identity",
        "key-signature slot fit: the measured accidental RUN fits this candidate's slot table and not another's -- needs NO identity",
        "continuity: a part's clef is stable across systems unless a change is printed",
    ),
    implicates=(Q.CLEF, Q.INSTRUMENT, Q.NOTEHEAD_STAFF_POSITION, Q.KEY_SIGNATURE),
    composed_from=(Q.CLEF_GLYPH, Q.CLEF_POSITION, Q.CLEF_LOCATED, Q.CLEF_SEED),
    scope=Kind.STAFF,
    wants=(Q.CLEF_GLYPH, Q.CLEF_POSITION, Q.CLEF_LOCATED, Q.CLEF_SEED,
           Q.NOTEHEAD_STAFF_POSITION, Q.INSTRUMENT, Q.KEYSIG_CLEF_FIT),
    reasons=("scored", "no_candidates", "margin_below_floor",
             "all_candidates_excluded"),
    mode=Mode.COMPETITIVE,
    margin_floor=MARGIN_FLOOR,
    # ⚠️ A QUALITY hold-out, NOT a circularity one, and kept separate on
    # purpose. `roster` identity's basis is a catalog row, not a clef
    # descendant, so the circularity filter would ADMIT it -- correctly. The
    # reason it is held out is a measured judgement about the tier
    # (`OMR_ROSTER_CLEF=0`), and folding a measured judgement into a
    # structural safety rule is how one of them goes silently missing.
    excludes_tiers=("roster",),
)
def adjudicate_clef(ev: Evidence) -> Ruling:
    candidates: Dict[str, List[Term]] = {}
    # ⚠️ ROADMAP 3.4f. A human's two witnesses (his class, his position)
    # disagreeing on ONE box is recorded here rather than silently resolved
    # either way -- see `_human_named_c_clef`.
    contradictions: List[Dict[str, Any]] = []
    # ⚠️ THE GAP TEST IS THE READ EVIDENCE ONLY, and `page_spoke` is computed
    # BEFORE the supplied terms are built so it can never see them. A staff
    # the page said nothing about is the supplied clef's entire domain.
    read = (_detector_terms(ev), _locator_terms(ev))
    page_spoke = any(bool(source) for source in read)
    carried, seeds_withheld = _carry_terms(ev, page_spoke=page_spoke)
    for source in (*read, carried):
        for name, terms in source.items():
            candidates.setdefault(name, []).extend(terms)

    # The instrument's expected clef, IF identity was admitted. The
    # circularity filter has already refused a deduced identity by this point
    # -- this function contains no provenance code at all, which is the point.
    instrument = ev.verdict(Q.INSTRUMENT)
    if instrument is not None and isinstance(instrument.value, dict):
        expected = instrument.value.get("expected_clef")
        if expected:
            candidates.setdefault(str(expected), []).append(
                Term("instrument", W_INSTRUMENT, (instrument.id,)))

    # ⚠️ THE IMPLICATION TEST THAT NEEDS NO IDENTITY. The run's positions are
    # clef-free; the slot table is chosen by the clef. So which clefs the run
    # FITS is evidence about the clef -- and it reaches exactly the staves the
    # written-range test cannot, because on a scan 29 of 29 unresolved
    # non-treble staves print no label at all.
    fits = ev.rows(Q.KEYSIG_CLEF_FIT)
    discriminating = [r for r in fits if (r.detail.get("n_accidentals") or 0) > 0]
    if discriminating and len(discriminating) < len(_SLOT_TABLE_CLEFS):
        for row in discriminating:
            candidates.setdefault(str(row.value), []).append(
                Term("keysig_slot_fit", W_KEYSIG_FIT, (row.id,)))
    elif fits:
        # ⚠️ THE TEST RAN AND SAID NOTHING, AND THAT MUST READ AS AN
        # ABSTENTION RATHER THAN AS AGREEMENT. A run fitting every candidate
        # discriminates nothing, and a 0-ACCIDENTAL KEY FITS THEM ALL -- so on
        # a page in C major this contributes exactly zero and must not appear
        # to have contributed. Recording it in `declined` is what stops a
        # later reader counting silence as support.
        ev._declined.add(Q.KEYSIG_CLEF_FIT)

    # ⚠️ A `clefC` detection supports every C clef a reader NAMED, and names
    # none itself. If nothing named one, it supports nothing -- which is the
    # honest outcome, not a fallback to alto.
    #
    # ⚠️ ROADMAP 3.4f -- THE ONE BRANCH, KEYED ON THE READER. A human witness
    # did not classify a glyph; he read the clef -- as a placed sub-class, a
    # specific line, or both -- and `_human_named_c_clef` reconciles his own
    # class choice against his own measured position (manager review: a
    # contradiction between his two witnesses names NOTHING and falls
    # through here rather than letting either overrule the other). Every
    # other reader's row falls straight through to the existing
    # support-only treatment below, unchanged -- and so does a human's row
    # this reconciliation could not name (unplaced and unsnappable, or
    # contradictory), which is the SAME "supports nothing" honest outcome
    # the comment above already describes, not a new fallback.
    for row in _c_family_support(ev):
        if _is_human_clef_reader(row.reader):
            named, contradiction = _human_named_c_clef(ev, row)
            if named is not None:
                name, term = named
                candidates.setdefault(name, []).append(term)
                continue
            if contradiction is not None:
                contradictions.append({"glyph_row": row.id,
                                        "reason": contradiction})
        named_c = [n for n in candidates if n in C_CLEF_NAMES]
        for name in named_c:
            candidates[name].append(
                Term("detector_c_family", W_C_FAMILY, (row.id,)))
        if not named_c:
            ev._declined.add(Q.CLEF_LOCATED)

    if not candidates:
        # ⚠️ A contradiction still belongs in `detail` even where nothing
        # else named a candidate -- an abstention that hides WHY a human's
        # own row named nothing is exactly the silence rule 8 forbids.
        if contradictions:
            return Ruling.abstain("no_candidates",
                                   **{CONTRADICTION_REASON: contradictions})
        return Ruling.abstain("no_candidates")

    correlated = ev.correlated_groups()
    scored = sorted(
        ((tally(terms, correlated=correlated), name)
         for name, terms in candidates.items()),
        reverse=True)

    top_score, top_name = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    margin = top_score - runner_up

    # ⚠️ EVERY id a term cites, not just the first. `_human_named_c_clef`'s
    # CONFIRMED case is this file's first multi-row term (`(glyph_row.id,
    # pos_row.id)`) -- every other term here has always carried exactly one,
    # so `rows[0]` alone happened to mean "all of them" until now.
    used = tuple(rid for terms in candidates.values() for t in terms
                 for rid in t.rows)
    # ⚠️ THE CONTEST TRAVELS WITH THE VERDICT, and it costs nothing: `scored`
    # was already computed and thrown away. Where the margin clears the floor
    # this rides along on a DECIDED verdict so a consumer can see the winner
    # was close; where it does not, the harness turns it into a NARROWED one
    # instead of the old bare `margin_below_floor` -- which reported
    # "the readers disagreed between alto and tenor" and "nothing was read"
    # as the same answer.
    cands = tuple(Candidate(value=n, support=sc) for sc, n in scored)
    detail: Dict[str, Any] = {"scores": {n: s for s, n in scored}}
    if seeds_withheld:
        # ⚠️ RECORDED, NOT DISCARDED. A supplied clef that was refused is a
        # fact about this run -- it is how a human reading the record can see
        # that the sheet disagreed with a page that spoke, which is the one
        # signal a GAPS-ONLY rule would otherwise throw away.
        detail["supplied_clefs_withheld_because_the_page_spoke"] = seeds_withheld
    if contradictions:
        detail[CONTRADICTION_REASON] = contradictions
    return Ruling(value=top_name, reason="scored", margin=margin, used=used,
                  candidates=cands, detail=detail)
