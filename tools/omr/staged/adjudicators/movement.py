"""ROADMAP 4.2b -- detect a movement boundary OFF THE PAGE, so
`tools.reengrave import` can split a whole work with no human page ranges.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md rule 3
-- nobody was available to ask before this landed):

    A movement starts on a system that shows SEVERAL of these together: a
    tempo heading above the top staff, a time signature STATEMENT (not a
    carried meter) on nearly every staff, a reset to FULL instrument names in
    the margin where the previous system showed fewer or shorter labels, and
    a wider first-system indent. No single cue is enough -- a tempo change
    mid-movement also prints a tempo word (measured: `gather.
    _gather_meter_glyphs`'s own docstring names Litolff Beethoven 5 p.62,
    "Tempo I." plus a new meter on every staff, as a MID-MOVEMENT case this
    convention must not trip on). This module requires at least
    `MIN_CUES_REQUIRED` (2) of the 4 cues below before it will call a system
    a boundary, AND `label_reset` MUST be one of the two (`is_movement_
    start`'s own docstring) -- tightened 2026-09-28 on manager review before
    merge: `tempo_word` + `meter_statement` together are the exact shape a
    mid-movement formal tempo/meter change prints too (Brahms 1/i's own `Un
    poco sostenuto` [6/8] -> `Allegro` [2/2]), and reprinting FULL
    instrument names is the one cue that is genuinely movement-specific.

    WHAT WOULD FALSIFY IT: a real movement-2 opening that fires `label_
    reset` plus fewer than one other cue (the brief's own worked example,
    Beethoven 5 / Litolff `imslp984073`, is the first check -- see
    `benchmarks/omr-movements-2026-09/FINDINGS.md`). A system that fires
    `label_reset` plus 1+ more but is NOT a movement start (a corroborated
    false positive on a second work) would also falsify the rule; so would
    a real movement start that never reprints full names at all (not
    observed on either acceptance record checked 2026-09-28).

    NOT CONFIRMED: the exact thresholds below (`METER_STATEMENT_MAJORITY`,
    `LABEL_COVERAGE_MIN`, `LABEL_LENGTH_RATIO`, `LABEL_LENGTH_DELTA`,
    `INDENT_RATIO`, `MIN_CUES_REQUIRED`) are reasonable-looking numbers, not
    measured ones -- there is no benchmark corpus of confirmed movement
    starts yet to fit them against. Sean's read of the one real boundary this
    item gathers (Beethoven 5 / Litolff) is the first data point; ANY of
    these six constants may need to move once there is a second.

⚠️ A FIFTH CUE THE BRIEF NAMES AND THIS MODULE DOES NOT IMPLEMENT: "the
system after a final double barline". No quantity in this record carries a
barline's TYPE (single/double/final) -- `record.Q` has no such vocabulary
and grepping the gatherer finds none -- so there is nothing here to read.
The brief's own wording is conditional ("if barlines carry that"); this
module reads only what GATHER already files (CLAUDE.md rule 1: brief from
the tree), and the tree files no such fact.

⚠️ THIS DECISION READS GATHER ONLY, NEVER ANOTHER DECISION'S VERDICT. That
is what lets it sit FIRST in `adjudicate.ORDER` -- before `Q.KEY_SIGNATURE`,
`Q.SYSTEM_KEY`, `Q.PART_KEY` and `Q.METER`, whose carries
(`rhythm._carry_meter`, `header.admitted_changes`'s consumers) must never
cross an UNDETECTED boundary either. Those two modules' own `_movement_spans`
helper reads the human `--movements` OBSERVATION first (unconditionally --
CLAUDE.md rule 3, "a human `--movements` ALWAYS wins over detection") and
falls back to THIS decision's VERDICT only where no human fact was filed;
see the `⚠️ ROADMAP 4.2b` note on each copy of `_movement_spans` in
`rhythm.py` and `header.py` for why ORDER (not a GATHER-time write) is the
mechanism that makes a detected boundary reach them at all -- `ev.rows()`
reads the FROZEN gather log, which nothing produced in ADJUDICATE can add
to, so a detected boundary can only reach a later decision through
`ev.verdict()`, which requires this decision to already have run.

A human `--movements` is filed as a GATHER Observation on the DOCUMENT
subject (`gather.gather_movements`); this decision ABSTAINS unconditionally
the moment one exists, so detection never contests a human answer -- it can
only fill the gap where none was given.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..adjudicate import Checkable, Evidence, Ruling, decision
from ..record import DOCUMENT, Kind, Observation, Q, Scope, Subject

#: "Nearly every staff" -- a meter glyph observed at CELL 0 (the system's own
#: first bar; gather.py's own `frame_cell(0)`) on at least this share of the
#: system's staves. NOT CONFIRMED -- see the module docstring.
METER_STATEMENT_MAJORITY = 0.6

#: A margin-label "reset" needs labels on at least this share of the
#: system's staves before it counts at all -- a lone label is not a reset.
LABEL_COVERAGE_MIN = 0.5

#: ...and then EITHER this multiple of the previous system's own average
#: label length, OR this many more characters outright -- "Violoncello" vs
#: "Vc." is both; "Fl. II" vs "Fl." is neither, which is deliberate: a
#: continuation system that keeps printing (short) labels every system is
#: not the pattern this cue exists to catch.
LABEL_LENGTH_RATIO = 1.5
LABEL_LENGTH_DELTA = 4

#: The top staff's own left edge (`Q.STAFF_EXTENT[0]`) at least this much
#: wider than the document's OWN median indent.
INDENT_RATIO = 1.15

#: CLAUDE.md's brief: "Require at least 2-3 cues." Two, not three -- see the
#: module docstring's WHAT WOULD FALSIFY IT.
MIN_CUES_REQUIRED = 2

_CUE_NAMES = ("tempo_word", "meter_statement", "label_reset", "wider_indent")


# ─────────────────────────────────────────────────────────────────────────────
# Pure cue readers -- each takes exactly the GATHER rows for ONE system (and,
# where the cue is relative, the rows for the system immediately before it)
# and answers a bool. Kept pure and small so a unit test can build the three
# or four rows a cue needs without assembling a whole page.
# ─────────────────────────────────────────────────────────────────────────────


def _tempo_word_fires(direction_word_rows: Sequence[Observation]) -> bool:
    """A `Q.DIRECTION_WORD` at this system's own CELL 0 (the header bar, "an
    the system's start" -- not a mid-system tempo change) whose lexicon
    category is `"tempo"` (`direction_lexicon`'s own vocabulary, read back
    exactly as `gather.gather_direction_words` filed it -- never re-guessed
    here).
    """
    return any(row.subject.cell == 0 and str((row.detail or {}).get("category") or "") == "tempo"
              for row in direction_word_rows)


def _meter_statement_fires(meter_glyph_rows: Sequence[Observation],
                           n_staves: int,
                           *, majority: float = METER_STATEMENT_MAJORITY
                           ) -> bool:
    """A time signature PRINTED at this system's own header -- `Q.METER_GLYPH`
    observed at `frame == "cell:0"` (gather.py's `frame_cell(0)`), on at
    least `majority` of the system's staves. A mid-system meter CHANGE is
    filed at a later cell and never satisfies this on its own, which is the
    exact discrimination the module docstring's Litolff p.62 example needs.
    """
    if n_staves <= 0:
        return False
    staves_with_a_statement = {
        row.subject.to_key() for row in meter_glyph_rows
        if row.frame == "cell:0"}
    if not staves_with_a_statement:
        return False
    return (len(staves_with_a_statement) / n_staves) >= majority


def _label_lengths(margin_label_rows: Sequence[Observation]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in margin_label_rows:
        text = str(row.value or "").strip()
        if text:
            out[row.subject.to_key()] = len(text)
    return out


def _label_reset_fires(cur_rows: Sequence[Observation],
                       prev_rows: Sequence[Observation],
                       n_staves: int,
                       *, coverage_min: float = LABEL_COVERAGE_MIN,
                       ratio: float = LABEL_LENGTH_RATIO,
                       delta: float = LABEL_LENGTH_DELTA) -> bool:
    """A majority of this system's staves print a margin label, and either
    the PREVIOUS system printed none at all, or this system's average label
    is markedly LONGER than the previous system's own average -- "Fl." to
    "Flauti" is a reset; "Fl." to "Fl." every system is not.
    """
    if n_staves <= 0:
        return False
    cur = _label_lengths(cur_rows)
    if not cur or (len(cur) / n_staves) < coverage_min:
        return False
    cur_avg = sum(cur.values()) / len(cur)
    prev = _label_lengths(prev_rows)
    if not prev:
        return True
    prev_avg = sum(prev.values()) / len(prev)
    return cur_avg >= prev_avg * ratio or (cur_avg - prev_avg) >= delta


def _top_staff_indent(staff_extent_rows: Sequence[Observation]
                      ) -> Optional[float]:
    """The system's own top staff's (`staff == 0`, system-local ordinal)
    `Q.STAFF_EXTENT` left edge, in page px -- `None` where geometry never
    reached this system at all."""
    for row in staff_extent_rows:
        if row.subject.staff == 0:
            try:
                return float(row.value[0])
            except (TypeError, IndexError, ValueError):
                return None
    return None


def _indent_fires(cur_x: Optional[float], baseline_x: Optional[float],
                  *, ratio: float = INDENT_RATIO) -> bool:
    if cur_x is None or baseline_x is None or baseline_x <= 0:
        return False
    return cur_x >= baseline_x * ratio


# ─────────────────────────────────────────────────────────────────────────────
# Grouping GATHER rows by the system they fall under
# ─────────────────────────────────────────────────────────────────────────────


def _group_by_system(rows: Sequence[Observation]
                     ) -> Dict[str, List[Observation]]:
    out: Dict[str, List[Observation]] = {}
    for row in rows:
        sys_subject = row.subject.at(Kind.SYSTEM)
        if sys_subject is None:
            continue
        out.setdefault(sys_subject.to_key(), []).append(row)
    return out


def cues_for_system(*, direction_word_rows: Sequence[Observation],
                    meter_glyph_rows: Sequence[Observation],
                    label_rows: Sequence[Observation],
                    prev_label_rows: Sequence[Observation],
                    n_staves: int,
                    indent_x: Optional[float],
                    baseline_indent_x: Optional[float]) -> Dict[str, bool]:
    """Every cue, computed for one system. Exposed at module level (rather
    than nested in the decision) so a unit test can drive it directly with
    hand-built rows and no `Log`/`Evidence` at all.
    """
    return {
        "tempo_word": _tempo_word_fires(direction_word_rows),
        "meter_statement": _meter_statement_fires(meter_glyph_rows, n_staves),
        "label_reset": _label_reset_fires(label_rows, prev_label_rows,
                                          n_staves),
        "wider_indent": _indent_fires(indent_x, baseline_indent_x),
    }


def is_movement_start(cues: Dict[str, bool], *,
                      min_cues: int = MIN_CUES_REQUIRED) -> bool:
    """⚠️ TIGHTENED 2026-09-28, manager review before merge. `tempo_word` +
    `meter_statement` together are NOT movement-specific: a mid-movement
    formal tempo/meter change prints both (Brahms 1/i's own `Un poco
    sostenuto` [6/8] -> `Allegro` [2/2] is the named worked case, and
    Beethoven 5's own Scherzo -> Finale bridge is the same shape one system
    later). `label_reset` is the one cue that IS movement-specific: full
    instrument names are reprinted at a movement's own opening and never
    mid-movement (players do not need re-announcing between formal
    sections) -- CLAUDE.md itself: "the clef and key signature are
    reprinted at the head of EVERY system", never the FULL name. So
    `label_reset` is now REQUIRED, not merely one of an interchangeable
    four -- `min_cues` still gates the total (a lone label reset, with
    nothing else, is still too little), but the two-of-four count can no
    longer be satisfied by {tempo_word, meter_statement, wider_indent}
    alone.

    Measured against this item's own acceptance records before shipping
    this tightening (`adjudicate_movement_start` run alone, GATHER only,
    over each record's frozen log -- never a full re-decision):
    `brahms1-breitkopf-mvt1-whole-20260928` (52 systems) and
    `beethoven5-litolff-mvt1-whole-20260928` (30 systems) each already
    abstained under the OLD (untightened) rule too -- the only cue either
    ever fires alone anywhere in either whole movement is `wider_indent`,
    never paired with a second -- so this tightening changes no PAST
    verdict on file; see `benchmarks/omr-movements-2026-09/FINDINGS.md`
    §6. It exists for the case those two records happen not to exercise:
    a reader that DOES accept a `tempo_word` together with a real
    `meter_statement`, at a system that starts a formal section rather
    than a movement.
    """
    if not cues.get("label_reset"):
        return False
    return sum(1 for v in cues.values() if v) >= min_cues


def spans_from_boundaries(systems: Sequence[Subject],
                          boundary_systems: Sequence[Subject]
                          ) -> List[Dict[str, Any]]:
    """`{"number", "first_page", "first_system", "last_page", "last_system"}`
    dicts, the exact shape `tools.omr.staged.movements` parses `--movements`
    into -- so a detected boundary and a human-typed one are indistinguishable
    to every consumer downstream of this decision.
    """
    boundary_keys = {s.to_key() for s in boundary_systems}
    cuts = [i for i, s in enumerate(systems) if s.to_key() in boundary_keys]
    starts = [0] + cuts
    ends = [c - 1 for c in cuts] + [len(systems) - 1]
    spans: List[Dict[str, Any]] = []
    for number, (a, b) in enumerate(zip(starts, ends), start=1):
        first, last = systems[a], systems[b]
        spans.append({
            "number": number,
            "first_page": first.page, "first_system": first.system,
            "last_page": last.page, "last_system": last.system,
        })
    return spans


@decision(
    quantity=Q.MOVEMENT_SPANS,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.DIRECTION_WORD, Q.METER_GLYPH, Q.MARGIN_LABEL,
                  Q.STAFF_LINES, Q.STAFF_EXTENT, Q.MOVEMENT_SPANS),
    scope=Kind.DOCUMENT,
    wants=(Q.DIRECTION_WORD, Q.METER_GLYPH, Q.MARGIN_LABEL, Q.STAFF_LINES,
          Q.STAFF_EXTENT, Q.MOVEMENT_SPANS),
    reasons=("human_spans_supplied", "too_few_systems",
             "no_boundary_detected", "detected"),
)
def adjudicate_movement_start(ev: Evidence) -> Ruling:
    """ROADMAP 4.2b. Detect an ADDITIONAL movement boundary off the page,
    where no human `--movements` was given.

    See the module docstring for the convention, its falsifiers, and why
    this reads GATHER only and runs first in `adjudicate.ORDER`.
    """
    human_rows = ev.rows(Q.MOVEMENT_SPANS, subject=DOCUMENT)
    if human_rows:
        # CLAUDE.md rule 3 / this item's own brief: a human `--movements`
        # ALWAYS wins. Detection does not even run, so it cannot disagree.
        return Ruling.abstain("human_spans_supplied", n_rows=len(human_rows))

    systems = ev.subjects(Kind.SYSTEM)
    if len(systems) < 2:
        # One system cannot hold a SECOND movement's start; nothing to check.
        return Ruling.abstain("too_few_systems", n_systems=len(systems))

    direction_by_system = _group_by_system(
        ev.rows(Q.DIRECTION_WORD, scope=Scope.SELF_AND_DESCENDANTS))
    meter_by_system = _group_by_system(
        ev.rows(Q.METER_GLYPH, scope=Scope.SELF_AND_DESCENDANTS))
    label_by_system = _group_by_system(
        ev.rows(Q.MARGIN_LABEL, scope=Scope.SELF_AND_DESCENDANTS))
    staff_by_system = _group_by_system(
        ev.rows(Q.STAFF_LINES, scope=Scope.SELF_AND_DESCENDANTS))
    extent_by_system = _group_by_system(
        ev.rows(Q.STAFF_EXTENT, scope=Scope.SELF_AND_DESCENDANTS))

    n_staves: Dict[str, int] = {}
    indent_x: Dict[str, Optional[float]] = {}
    for system in systems:
        key = system.to_key()
        staves = {row.subject.to_key() for row in staff_by_system.get(key, ())}
        n_staves[key] = len(staves)
        indent_x[key] = _top_staff_indent(extent_by_system.get(key, ()))

    known_indents = [x for x in indent_x.values() if x is not None]
    baseline_indent = statistics.median(known_indents) if known_indents \
        else None

    boundary_systems: List[Subject] = []
    cues_by_system: Dict[str, Dict[str, bool]] = {}
    for i, system in enumerate(systems):
        if i == 0:
            # The document's own first system is movement 1's start by
            # definition -- there is no "previous system" for it to differ
            # from, and it is never itself an ADDITIONAL boundary.
            continue
        key = system.to_key()
        prev_key = systems[i - 1].to_key()
        cues = cues_for_system(
            direction_word_rows=direction_by_system.get(key, ()),
            meter_glyph_rows=meter_by_system.get(key, ()),
            label_rows=label_by_system.get(key, ()),
            prev_label_rows=label_by_system.get(prev_key, ()),
            n_staves=n_staves.get(key, 0),
            indent_x=indent_x.get(key),
            baseline_indent_x=baseline_indent)
        cues_by_system[key] = cues
        if is_movement_start(cues):
            boundary_systems.append(system)

    if not boundary_systems:
        # CLAUDE.md rule 8: no confident boundary is a DECLINE, never a
        # decided "definitely one movement" -- the pre-existing single-
        # movement default (no `Q.MOVEMENT_SPANS` fact at all) already reads
        # that way everywhere `movements.same_movement` is asked, so an
        # abstention here changes nothing downstream.
        return Ruling.abstain("no_boundary_detected",
                              systems_checked=len(systems) - 1,
                              cues_by_system=cues_by_system)

    spans = spans_from_boundaries(systems, boundary_systems)
    return Ruling(
        value=spans, reason="detected",
        detail={
            "boundaries": [
                {"system": s.to_key(),
                 "cues": sorted(k for k, v in cues_by_system[s.to_key()].items()
                               if v)}
                for s in boundary_systems],
            "cues_by_system": cues_by_system,
            "min_cues_required": MIN_CUES_REQUIRED,
        })
