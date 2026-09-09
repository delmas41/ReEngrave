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

from typing import Dict, List, Optional, Tuple

from ..adjudicate import (Candidate, Checkable, READINGS, Evidence, Mode, Ruling, Term, decision,
                          tally)
from ..record import ABSTAIN, Kind, Q, Scope, State

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
    """⚠️ A CLASS NAME CANNOT NAME A C CLEF. `clefC` returns None, on purpose.

    Alto, tenor, soprano, mezzo and baritone are THE SAME GLYPH on different
    lines, so `clefC` says a C clef is present and nothing about WHICH -- only
    geometry can, which is exactly why `clef_geometry.py` exists.

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
    """`clefC` detections, as support for a C clef somebody else named."""
    out = []
    for row in ev.rows(Q.CLEF_GLYPH):
        if str(row.value) == "clefC":
            out.append(row)
    return out


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


def _carry_terms(ev: Evidence) -> Dict[str, List[Term]]:
    """This part's own clef on another system.

    ⚠️ This is `clef_continuity`'s mechanism, which is the ONE carry in the
    existing pipeline that survives -- it is keyed on the staff's ROLE within
    its system rather than on `(page, system, staff)`, which is exactly why
    it inherits across systems while the three key/clef/meter carry dicts
    can never hit. Same idea, expressed as evidence rather than as a seed.
    """
    out: Dict[str, List[Term]] = {}
    for row in ev.rows(Q.CLEF_SEED):
        name = str(row.value)
        weight = W_DOSSIER if row.detail.get("tier") == "dossier" else W_CARRY
        out.setdefault(name, []).append(Term("carry", weight, (row.id,)))
    return out


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
    for source in (_detector_terms(ev), _locator_terms(ev), _carry_terms(ev)):
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
    for row in _c_family_support(ev):
        named_c = [n for n in candidates if n in C_CLEF_NAMES]
        for name in named_c:
            candidates[name].append(
                Term("detector_c_family", W_C_FAMILY, (row.id,)))
        if not named_c:
            ev._declined.add(Q.CLEF_LOCATED)

    if not candidates:
        return Ruling.abstain("no_candidates")

    correlated = ev.correlated_groups()
    scored = sorted(
        ((tally(terms, correlated=correlated), name)
         for name, terms in candidates.items()),
        reverse=True)

    top_score, top_name = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    margin = top_score - runner_up

    used = tuple(t.rows[0] for terms in candidates.values() for t in terms
                 if t.rows)
    # ⚠️ THE CONTEST TRAVELS WITH THE VERDICT, and it costs nothing: `scored`
    # was already computed and thrown away. Where the margin clears the floor
    # this rides along on a DECIDED verdict so a consumer can see the winner
    # was close; where it does not, the harness turns it into a NARROWED one
    # instead of the old bare `margin_below_floor` -- which reported
    # "the readers disagreed between alto and tenor" and "nothing was read"
    # as the same answer.
    cands = tuple(Candidate(value=n, support=sc) for sc, n in scored)
    return Ruling(value=top_name, reason="scored", margin=margin, used=used,
                  candidates=cands, detail={"scores": {n: s for s, n in scored}})
