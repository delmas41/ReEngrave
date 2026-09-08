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

from ..adjudicate import (READINGS, Evidence, Mode, Ruling, Term, decision,
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
MARGIN_FLOOR = 1.0

_GLYPH_TO_CLEF = {
    "clefG": "treble",
    "clefF": "bass",
    "clefC": "alto",       # ⚠️ SEE BELOW -- this is a placeholder, not a read
    "clefUnpitchedPercussion": "percussion",
}


def _clef_of(glyph_name: str) -> Optional[str]:
    """⚠️ A CLASS NAME CANNOT NAME A C CLEF, AND THIS IS A KNOWN CEILING.

    Alto, tenor, soprano, mezzo and baritone are THE SAME GLYPH on different
    lines, so `clefC` does not say which one it is -- only geometry does
    (`clef_geometry.py` measures which line the clef names, and that is why
    it exists). Mapping `clefC -> alto` here is a PLACEHOLDER that reproduces
    the commonest case; the real value must come from a
    `Q.CLEF_LOCATED` row, which carries the located line.

    Recorded rather than quietly shipped: this is the single largest known
    wrongness in this module.
    """
    return _GLYPH_TO_CLEF.get(glyph_name)


def _detector_terms(ev: Evidence) -> Dict[str, List[Term]]:
    out: Dict[str, List[Term]] = {}
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
    scope=Kind.STAFF,
    wants=(Q.CLEF_GLYPH, Q.CLEF_LOCATED, Q.CLEF_SEED,
           Q.NOTEHEAD_STAFF_POSITION, Q.INSTRUMENT),
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
    return Ruling(value=top_name, reason="scored", margin=margin, used=used,
                  detail={"scores": {n: s for s, n in scored}})
