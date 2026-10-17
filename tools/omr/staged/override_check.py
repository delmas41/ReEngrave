"""ONE SHARED OVERRIDE CHECK -- ROADMAP 2.165 (Sean 2026-10-17, DECISIONS; design: docs/override-map-2026-10-17.md §11).

STAGED, every stage. Behind ONE flag, `OMR_ONE_OVERRIDE_CHECK`, default OFF (only `1/true/yes/on` enables).

Sean, 2026-10-17: *"Build the one shared check"* -- one question asked in ONE place, *may this step change that
verdict?*, instead of a small guard per rule (`_admitted`, `bare_stem_confirmable`, `_shortens_without_evidence`,
`lone_event_decline`, `infer._admit` ...), because every find of that week was a guard one rule had and its neighbour
lacked.

WHERE IT SITS. `record.Log.record` -- the single place every verdict is written -- calls `check()` before it appends.
A verdict that names `supersedes=` is checked against the verdict it supersedes; a FIRST verdict whose own reason says
it overturns an earlier reading (a flag at step 3 reopening a head read at step 1; the bars refusing a carried meter)
is checked against that implied earlier step. EXPORT, which writes no verdicts, asks the same table through
`export_may()` for its two rows.

THE KEY. Every verdict has a (stage, step): the stage it was written in (ADJUDICATE / EVALUATE / INFER / EXPORT) and
its step in the note reading order (Sean 2026-10-16: notehead 1, stem 2, beam or flag 3, chord / shared stem 4,
anything else 5; then the bar sum 6 and the carried meter 7, docs/override-map §11), or, for a verdict about
something other than a note's value, the kind of fact it is (owner, pitch, a reader's own reading). The guard looks
up the pair (new key, prior key) in `TABLE`; the row's rule answers. **An unknown pair is a rule nobody has
guarded**: under pytest it RAISES (`UnguardedOverride`), so a new `supersedes=` site cannot land without a row; in
a run it is refused and counted (`no_row_for_this_pair`), never silently allowed.

THE RULES (CLAUDE §3, §4; DECISIONS 2026-10-16/17):
  * a later step may only WIDEN an earlier DECIDED value (to an abstention, or a narrowing that contains it) or
    CONFIRM it; it never replaces it. A narrowing may be settled only within its own candidates;
  * EVALUATE writes only what is forced -- a convention, an earlier step's answer, a downhill consequence;
  * INFER never overturns a DECIDED verdict, chooses only among the reader's own candidates, and its result is
    GUESSED (`inferred: True`);
  * the bar sum may only confirm, except Sean's GUESSED exceptions: the 2.154 bare-stem quarter, the 2.158 lone
    event, and (2026-10-17) the shared-stem majority (three or more heads, one dissent);
  * a bar holding a narrowed note has no known length (2.162's helper decides; this module never sums a bar).

A REFUSED CHANGE IS NOT DROPPED. The prior verdict stands, `Log.record` returns it, and the attempted verdict is kept
on the log as a NEAR MISS -- `{row, why, attempted, prior}` -- written into the record (`near_misses`) so every
refusal can be counted per row. With the flag OFF nothing here runs and the record is byte-identical.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

FLAG = "OMR_ONE_OVERRIDE_CHECK"

A, E, I, X = "ADJUDICATE", "EVALUATE", "INFER", "EXPORT"

#: The reading order's steps (DECISIONS 2026-10-16; override-map §11), and the non-note kinds of fact.
STEPS = {
    "identity": 0,        # what the box IS (a rest, not a note) -- read before its value
    "notehead": 1,
    "own_reading": 3,     # `adjudicate_duration` reads steps 1-3 of ONE head in one verdict
    "beam_flag": 3,
    "shared_stem": 4,
    "shared_stem_guess": 4,
    "other": 5,           # dots, slashes, anything else
    "bar_sum": 6,
    "carried_meter": 7,
}


def enabled() -> bool:
    return os.environ.get(FLAG, "").strip().lower() in ("1", "true", "yes", "on")


class UnguardedOverride(RuntimeError):
    """A (new step, prior step) pair with no row in `TABLE`: a new rule tried to change a verdict unguarded."""


# ─────────────────────────────────────────────────────────────────────────────
# 1. Which (stage, step) a verdict is
# ─────────────────────────────────────────────────────────────────────────────

#: Non-ADJUDICATE-decision writers, by decider name. Every `supersedes=` site's decider is here (asserted by a test
#: that reads the sites from the code, not from this list).
DECIDER_KEY: Dict[str, Tuple[str, str]] = {
    # ADJUDICATE reconcilers run right after their decision (adjudicators/ownership.py, aug_dot_join.py)
    "reconcile_group_owners": (A, "owner"),
    "reconcile_dot_owners": (A, "owner"),
    "reconcile_articulation_twins": (A, "owner"),
    "reconcile_unjoined_dots": (A, "other"),
    # EVALUATE (consequences.py)
    "share_stem_value": (E, "shared_stem"),
    "reconcile_chord_duration": (E, "shared_stem"),
    "size_measure_rest": (E, "rest_convention"),
    "size_reinstated_rest": (E, "identity"),
    "size_unboxed_rest": (E, "identity"),
    "size_head_ink_rest": (E, "identity"),
    "reconcile_duration": (E, "bar_sum"),
    "reinstate_rest_between_staves": (E, "bar_sum"),
    "restate_pitch": (E, "pitch"),
    "move_glyph": (E, "pitch"),
    "respell_accidental": (E, "pitch"),
    "apply_printed_accidental": (E, "pitch"),
}

#: INFER rules whose only witness is the bar's arithmetic -- the two GUESSED exceptions (2.154, 2.158).
INFER_BAR_RULES = frozenset({"collapse_bare_stem_by_bar", "collapse_narrowed_by_bar"})
INFER_BAR_REASONS = frozenset({"the_bars_arithmetic_forces_this_length", "lone_event_fills_bar"})

#: `adjudicate_duration` reasons where a flag or beam (step 3) re-opens a head read open at step 1 (audit A7).
STEP3_OVER_STEP1_REASONS = frozenset({"open_head_flag_contradiction", "second_hollow_contradicted_by_marks"})

#: `adjudicate_meter` reasons where the bars' arithmetic refuses a carried meter or names one (audit A9).
METER_BAR_SUM_REASONS = frozenset({"carry_not_corroborated", "carry_outweighed_by_the_bars", "derived_from_bars",
                                   "bars_name_a_length_without_a_form"})

#: The implied earlier step a FIRST verdict overturns, by its own key.
IMPLIED_PRIOR = {(A, "beam_flag"): (A, "notehead"), (A, "bar_sum"): (A, "carried_meter")}


def is_guess(v: Any) -> bool:
    """GUESSED: an INFER collapse, a bar-sum guess, or the shared-stem majority (Sean 2026-10-17)."""
    d = v.decider or ""
    return (d.startswith("infer:") or d == "reconcile_duration"
            or bool((v.detail or {}).get("guessed")))


def key_of(v: Any) -> Optional[Tuple[str, str]]:
    d = v.decider or ""
    if d.startswith("infer:"):
        return (I, "bar_sum" if d[len("infer:"):] in INFER_BAR_RULES else "collapse")
    if d == "share_stem_value" and (v.detail or {}).get("guessed"):
        return (E, "shared_stem_guess")
    if d in DECIDER_KEY:
        return DECIDER_KEY[d]
    if d.startswith("adjudicate_"):
        from .record import Q
        if v.quantity == Q.DURATION:
            return (A, "beam_flag") if v.reason in STEP3_OVER_STEP1_REASONS else (A, "own_reading")
        if v.quantity == Q.STEM_VALUE:
            return (A, "shared_stem")
        if v.quantity == Q.METER and v.reason in METER_BAR_SUM_REASONS:
            return (A, "bar_sum")
        return (A, "reading")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Value identity
# ─────────────────────────────────────────────────────────────────────────────

def _ident(value: Any) -> Any:
    if isinstance(value, dict) and "written" in value:
        try:
            return ("dur", round(float(value["written"]), 6), int(value.get("dots") or 0),
                    int(value.get("beam_levels") or 0), bool(value.get("is_rest")))
        except (TypeError, ValueError):
            pass
    if isinstance(value, dict):
        return tuple(sorted((k, repr(x)) for k, x in value.items()))
    return repr(value)


def _base(value: Any) -> Optional[float]:
    """The head's own base (4 whole, 2 half, 1 black) -- its FILL, step 1."""
    if not isinstance(value, dict):
        return None
    try:
        written = float(value["written"])
        dots = int(value.get("dots") or 0)
        levels = int(value.get("beam_levels") or 0)
    except (KeyError, TypeError, ValueError):
        return None
    return round(written * (2 ** levels) / (2.0 - 2.0 ** (-dots)), 3)


def _cands(v: Any) -> list:
    return [_ident(c.value) for c in (v.candidates or ())]


def _admits(v: Any) -> Optional[list]:
    """What a prior still admits: one value if DECIDED and READ, its candidates if NARROWED or GUESSED (a guess is
    its narrowing, labelled), None if ABSTAINED."""
    from .record import Outcome
    if v.outcome is Outcome.ABSTAINED:
        return None
    if v.outcome is Outcome.NARROWED or (is_guess(v) and v.candidates):
        return _cands(v)
    return [_ident(v.value)]


# ─────────────────────────────────────────────────────────────────────────────
# 3. The rules a row may carry. Each returns None (allowed) or the refusal's reason word.
# ─────────────────────────────────────────────────────────────────────────────

def r_later_step(new, prior, log) -> Optional[str]:
    """A later step may WIDEN an earlier DECIDED value or CONFIRM it, and settle a narrowing only within it."""
    from .record import Outcome
    if new.outcome is Outcome.ABSTAINED:
        return None                                   # the widest widening
    admitted = _admits(prior)
    if admitted is None:
        return "a_later_step_supplies_what_was_not_read"
    decided_read = prior.outcome is Outcome.DECIDED and not (is_guess(prior) and prior.candidates)
    if new.outcome is Outcome.NARROWED:
        if decided_read:
            return None if admitted[0] in _cands(new) else "a_later_step_replaces_a_decided_value"
        return None
    if _ident(new.value) in admitted:
        return None
    return ("a_later_step_replaces_a_decided_value" if decided_read
            else "a_later_step_leaves_the_narrowing")


def r_widen(new, prior, log) -> Optional[str]:
    """Only a widening (or a confirm): the dot join, a twin withdrawn, a revision (A1, A3, A5)."""
    from .record import Outcome
    if new.outcome is Outcome.ABSTAINED:
        return None
    admitted = _admits(prior)
    if admitted is None:
        return "a_widening_has_nothing_to_widen"
    if new.outcome is Outcome.NARROWED:
        return None if set(admitted) <= set(_cands(new)) else "not_a_widening"
    return None if [_ident(new.value)] == admitted else "not_a_widening"


def r_shared_stem(new, prior, log) -> Optional[str]:
    """Step 4 over steps 1-3. The stem's value may give a head the stem's beams and dots (they hang at the stem's
    tip: Sean's 2.78 tiles 1 and 13), never overwrite a head's own DECIDED FILL (Sean 2026-10-17, 2.163 violation 3),
    except a box classed WHOLE, which on a stem is a half ("Whole notes never have stems", 2026-10-09)."""
    from .record import Outcome
    why = r_later_step(new, prior, log)
    if why != "a_later_step_replaces_a_decided_value":
        return why
    if new.outcome is not Outcome.DECIDED:
        return why
    b_new, b_old = _base(new.value), _base(prior.value)
    if b_new is None or b_old is None:
        return why
    if b_new == b_old:
        return None                                   # the stem's tip reading: beams / dots
    if b_old >= 4.0 and b_new == 2.0:
        return None                                   # whole notes never have stems
    return "shared_stem_overwrites_a_decided_fill"


def r_shared_stem_guess(new, prior, log) -> Optional[str]:
    """Sean 2026-10-17: three or more heads on one stem, all agreeing but one -- the stem is GUESSED to the majority
    and the dissent marked. Allowed only as a labelled guess that keeps the head's own reading among its candidates."""
    if not (new.detail or {}).get("guessed"):
        return "a_shared_stem_guess_must_be_labelled"
    # The head's own READING is its fill (step 1); its beams and dots are the stem's (tip rule, as `r_shared_stem`).
    from .record import Outcome
    if prior.outcome is Outcome.DECIDED:
        own = {_base(prior.value)}
    else:
        own = {_base(c.value) for c in (prior.candidates or ())}
    if own and None not in own and not own & {_base(c.value) for c in (new.candidates or ())}:
        return "a_shared_stem_guess_drops_the_heads_own_reading"
    return None


def r_earlier_step(new, prior, log) -> Optional[str]:
    """An earlier step's answer (what the box IS) restates a later one: forced, EVALUATE (E3). Needs a DECIDED cause."""
    from .record import Outcome
    for bid in new.basis:
        b = log.row(bid)
        if b is not None and getattr(b, "outcome", None) is Outcome.DECIDED and b.quantity != new.quantity:
            return None
    return "no_decided_cause"


def r_rest_convention(new, prior, log) -> Optional[str]:
    """A whole rest means the bar (page-facts; E2): the rest's length follows from the meter, never a sum."""
    v = prior.value if isinstance(prior.value, dict) else {}
    return None if v.get("is_rest") else "rest_convention_on_a_note"


def r_connect(new, prior, log) -> Optional[str]:
    """Same-stage reconcilers that connect a decision (the ledger names the owner, a dot follows its note): A2, A4."""
    return None


def r_downhill(new, prior, log) -> Optional[str]:
    """A pitch or accidental restated on a DECIDED clef / owner / key change (E7): forced."""
    return r_earlier_step(new, prior, log)


def r_infer(new, prior, log) -> Optional[str]:
    """INFER never overturns a DECIDED verdict, chooses among the reader's own candidates, and is GUESSED (I1)."""
    from .record import Outcome
    if prior.outcome is Outcome.DECIDED:
        return "infer_never_overturns_decided"
    if not (new.detail or {}).get("inferred"):
        return "an_inference_must_be_guessed"
    if prior.outcome is Outcome.NARROWED and _ident(new.value) not in _cands(prior):
        return "infer_outside_the_readers_candidates"
    return None


def r_infer_bar(new, prior, log) -> Optional[str]:
    """The bar sum in INFER: only Sean's two GUESSED exceptions (2.154 bare stem, 2.158 lone event)."""
    why = r_infer(new, prior, log)
    if why:
        return why
    return None if new.reason in INFER_BAR_REASONS else "bar_sum_may_only_confirm"


def r_bar_sum_confirm(new, prior, log) -> Optional[str]:
    """The bar sum in EVALUATE may only CONFIRM (CLAUDE §4). A DECIDED value is never moved -- audit violation 1
    (E5b: a quarter with no flag and no beam made an eighth by the bar; E5c: one head of a decided chord moved
    alone). A narrowing is settled only at a bare stem's unbeamed value (2.154, GUESSED: `reconcile_duration` is an
    EVALUATE guesser)."""
    from .record import Outcome
    if prior.outcome is Outcome.DECIDED:
        if is_guess(prior) and prior.candidates:
            return None if _ident(new.value) in _cands(prior) else "bar_sum_may_only_confirm"
        return None if _ident(new.value) == _ident(prior.value) else "bar_sum_moves_a_decided_value"
    if prior.outcome is Outcome.NARROWED:
        from .consequences import confirms_bare_stem
        return None if confirms_bare_stem(prior, new.value) else "bar_sum_picks_from_a_narrowing"
    return "bar_sum_supplies_what_was_not_read"


def r_bar_sum_known_length(new, prior, log) -> Optional[str]:
    """A rest reinstated because the bar is short (E6, audit violation 7) -- only where the bar HAS a length: 2.162's
    helper (`consequences._event_range`) must give one exact length, never a range."""
    from .bar_length import bar_length
    from .consequences import _standing, _is_rest
    from .record import Kind, Q
    try:
        cell = new.subject.at(Kind.CELL)
    except Exception:                                  # noqa: BLE001 -- a subject with no cell has no bar
        return "bar_length_unknown"
    if cell is None:
        return "bar_length_unknown"
    notes = [v for v in _standing(log, cell, Q.DURATION) if not _is_rest(v)]
    if not notes:
        return None                                    # an empty bar: its length is the rests', all decided
    return None if bar_length(log, cell, notes, first_candidate=False).known else "bar_length_unknown"


def r_meter_bars_known_length(new, prior, log) -> Optional[str]:
    """The bars may refuse a carried meter, or name one (A9, audit violation 2), only from bars of KNOWN length:
    2.162's helper must be the one that summed them (a narrowed bar is a range that may confirm, never refute)."""
    from .bar_length import narrowed_bar_length_unknown
    if not narrowed_bar_length_unknown():
        raise RuntimeError("OMR_ONE_OVERRIDE_CHECK is on but 2.162's bar-length helper is off -- the meter's bars "
                           "would be summed at a narrowing's first candidate")
    return None


def r_step3_keeps_step1(new, prior, log) -> Optional[str]:
    """A flag or beam (step 3) never re-opens a head read open at step 1 (A7, audit violation 6). Where the head's
    own ink does not read filled, the narrowing is refused and the head keeps its open value (`rewrite()`); where
    the head was never decided at step 1 (a head only the second detector saw), abstaining is a widening."""
    from .record import Outcome
    if new.outcome is Outcome.ABSTAINED:
        return None
    if (new.detail or {}).get("open_on_stem", {}).get("ink_filled"):
        return None                                    # step 1 itself is in question: the ink reads filled
    return "a_flag_reopens_an_open_head"


def r_export_refuses(new, prior, log) -> Optional[str]:
    return "export_refuses"


@dataclass(frozen=True)
class Row:
    name: str
    rule: Callable[..., Optional[str]]
    covers: str          # the audit item(s) / ruling the row answers


_ROWS = [
    # ── INFER (I1-I7): `infer._admit` is this check for its stage ───────────────────────────────────────────────────
    ((I, "collapse"), (A, "own_reading"), "infer_collapses_a_narrowing", r_infer, "I1, I4, I5"),
    ((I, "collapse"), (A, "beam_flag"), "infer_collapses_a_step3_narrowing", r_infer, "I1"),
    ((I, "collapse"), (A, "other"), "infer_collapses_a_dot_narrowing", r_infer, "I1, A5"),
    ((I, "collapse"), (A, "reading"), "infer_fills_a_reading", r_infer, "I6, I7"),
    ((I, "bar_sum"), (A, "own_reading"), "infer_bar_sum_exception", r_infer_bar, "I2, I3 (2.154, 2.158)"),
    ((I, "bar_sum"), (A, "beam_flag"), "infer_bar_sum_exception_step3", r_infer_bar, "I2, I3"),
    ((I, "bar_sum"), (A, "other"), "infer_bar_sum_exception_dot", r_infer_bar, "I2, I3"),
    # ── ADJUDICATE reconcilers ───────────────────────────────────────────────────────────────────────────────────────
    ((A, "own_reading"), (A, "own_reading"), "adjudicate_revises_a_reading", r_widen, "A1 (dead path)"),
    ((A, "reading"), (A, "reading"), "adjudicate_revises", r_widen, "A1 (dead path)"),
    ((A, "owner"), (A, "reading"), "owner_reconciled", r_connect, "A2, A3, A4"),
    ((A, "owner"), (A, "owner"), "owner_reconciled_again", r_connect, "A2, A4"),
    ((A, "other"), (A, "own_reading"), "dot_widens_a_value", r_widen, "A5"),
    ((A, "other"), (A, "beam_flag"), "dot_widens_a_step3_value", r_widen, "A5"),
    ((A, "other"), (A, "other"), "dot_widens_again", r_widen, "A5"),
    ((A, "beam_flag"), (A, "notehead"), "flag_never_reopens_an_open_head", r_step3_keeps_step1,
     "A7 = audit violation 6"),
    ((A, "bar_sum"), (A, "carried_meter"), "meter_bars_need_a_known_length", r_meter_bars_known_length,
     "A9 = audit violation 2 (2.162)"),
    # ── EVALUATE ─────────────────────────────────────────────────────────────────────────────────────────────────────
    ((E, "shared_stem"), (A, "own_reading"), "stem_value_over_a_head", r_shared_stem, "A8/E1 = audit violation 3"),
    ((E, "shared_stem"), (A, "beam_flag"), "stem_value_over_a_step3_head", r_shared_stem, "E1"),
    ((E, "shared_stem"), (A, "other"), "stem_value_over_a_dot_narrowing", r_shared_stem, "E1"),
    ((E, "shared_stem"), (I, "collapse"), "stem_value_over_a_guess", r_shared_stem, "E8"),
    ((E, "shared_stem"), (I, "bar_sum"), "stem_value_over_a_bar_guess", r_shared_stem, "E8"),
    ((E, "shared_stem_guess"), (A, "own_reading"), "stem_majority_guess", r_shared_stem_guess,
     "Sean 2026-10-17 shared stem"),
    ((E, "shared_stem_guess"), (A, "beam_flag"), "stem_majority_guess_step3", r_shared_stem_guess, "Sean 2026-10-17"),
    ((E, "shared_stem_guess"), (A, "other"), "stem_majority_guess_dot", r_shared_stem_guess, "Sean 2026-10-17"),
    ((E, "shared_stem_guess"), (I, "collapse"), "stem_majority_guess_over_a_guess", r_shared_stem_guess,
     "Sean 2026-10-17, E8"),
    ((E, "shared_stem_guess"), (I, "bar_sum"), "stem_majority_guess_over_a_bar_guess", r_shared_stem_guess,
     "Sean 2026-10-17, E8"),
    ((E, "identity"), (A, "own_reading"), "rest_shape_restates_a_head", r_earlier_step, "E3"),
    ((E, "identity"), (A, "beam_flag"), "rest_shape_restates_a_step3_head", r_earlier_step, "E3"),
    ((E, "identity"), (A, "other"), "rest_shape_restates_a_dot_narrowing", r_earlier_step, "E3"),
    ((E, "identity"), (E, "shared_stem"), "rest_shape_restates_a_stem_value", r_earlier_step, "E3"),
    ((E, "identity"), (E, "shared_stem_guess"), "rest_shape_restates_a_stem_guess", r_earlier_step, "E3"),
    ((E, "rest_convention"), (A, "own_reading"), "whole_rest_means_the_bar", r_rest_convention, "E2"),
    ((E, "bar_sum"), (A, "own_reading"), "bar_sum_confirms_only", r_bar_sum_confirm,
     "E5a, E5b, E5c = audit violation 1"),
    ((E, "bar_sum"), (A, "beam_flag"), "bar_sum_confirms_only_step3", r_bar_sum_confirm, "audit violation 1"),
    ((E, "bar_sum"), (A, "other"), "bar_sum_confirms_only_dot", r_bar_sum_confirm, "audit violation 1"),
    ((E, "bar_sum"), (E, "shared_stem"), "bar_sum_confirms_only_stem", r_bar_sum_confirm,
     "E5c = audit violation 1 (8)"),
    ((E, "bar_sum"), (E, "shared_stem_guess"), "bar_sum_confirms_only_stem_guess", r_bar_sum_confirm,
     "audit violation 1"),
    ((E, "bar_sum"), (E, "identity"), "bar_sum_confirms_only_rest", r_bar_sum_confirm, "audit violation 1"),
    ((E, "bar_sum"), (A, "reading"), "bar_sum_reinstates_only_in_a_known_bar", r_bar_sum_known_length,
     "E6 = audit violation 7 (2.162)"),
    ((E, "pitch"), (A, "reading"), "pitch_follows_its_cause", r_downhill, "E7"),
    ((E, "pitch"), (E, "pitch"), "pitch_restated", r_downhill, "E7"),
    ((E, "pitch"), (I, "collapse"), "pitch_over_an_inferred_reading", r_downhill, "E7, E8"),
    # ── EXPORT (asked through `export_may`) ──────────────────────────────────────────────────────────────────────────
    ((X, "chord_value"), (A, "shared_stem"), "export_never_writes_a_chord_mode", r_export_refuses,
     "X2 = audit violation 4"),
    ((X, "carried_meter"), (A, "bar_sum"), "export_never_judges_a_refused_carry", r_export_refuses,
     "X3 = audit violation 5"),
]

TABLE: Dict[Tuple[Tuple[str, str], Tuple[str, str]], Row] = {}
for _n, _p, _name, _rule, _covers in _ROWS:
    assert (_n, _p) not in TABLE, (_n, _p)
    TABLE[(_n, _p)] = Row(_name, _rule, _covers)
del _n, _p, _name, _rule, _covers


# ─────────────────────────────────────────────────────────────────────────────
# 4. The check `Log.record` calls
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Decision:
    allowed: bool
    row: Optional[str] = None
    why: Optional[str] = None
    record_instead: Any = None      # a verdict to record in place of the refused first verdict (violation 6)


def _in_tests() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ


def lookup(new_key, prior_key) -> Row:
    row = TABLE.get((new_key, prior_key))
    if row is None:
        raise UnguardedOverride(f"no row for {new_key} changing {prior_key}: add one to override_check.TABLE")
    return row


def check(log: Any, verdict: Any, prior: Any) -> Decision:
    """May `verdict` change `prior` (or, for a first verdict, the earlier step its reason overturns)?"""
    new_key = key_of(verdict)
    if prior is None or verdict.supersedes is None:
        implied = IMPLIED_PRIOR.get(new_key)
        if implied is None:
            return Decision(True)
        row = lookup(new_key, implied)
        why = row.rule(verdict, None, log)
        if why is None:
            return Decision(True, row.name)
        return Decision(False, row.name, why, record_instead=rewrite(log, verdict, row.name))
    prior_key = key_of(prior)
    try:
        row = lookup(new_key, prior_key)
    except UnguardedOverride:
        if _in_tests():
            raise
        return Decision(False, "no_row", f"no_row_for_this_pair:{new_key}>{prior_key}")
    why = row.rule(verdict, prior, log)
    return Decision(why is None, row.name, why)


def rewrite(log: Any, verdict: Any, row: str) -> Any:
    """The verdict that stands where a FIRST verdict was refused: the head's step-1 open value (violation 6)."""
    from .record import Outcome, Verdict
    if row != "flag_never_reopens_an_open_head" or verdict.outcome is not Outcome.NARROWED:
        return None
    opens = [c for c in verdict.candidates
             if isinstance(c.value, dict) and int(c.value.get("beam_levels") or 0) == 0]
    if len(opens) != 1:
        return None
    detail = dict(verdict.detail or {})
    detail["flag_on_an_open_head"] = sorted({int(c.value.get("beam_levels") or 0) for c in verdict.candidates} - {0})
    return Verdict(id=verdict.id, subject=verdict.subject, quantity=verdict.quantity, outcome=Outcome.DECIDED,
                   value=dict(opens[0].value), decider=verdict.decider, reason="open_head_kept_over_a_flag",
                   considered=verdict.considered, used=verdict.used, missing=verdict.missing,
                   declined=verdict.declined, excluded=verdict.excluded, correlated=verdict.correlated,
                   basis=verdict.basis, candidates=verdict.candidates, margin=verdict.margin, supersedes=None,
                   detail=detail)


def near_miss(verdict: Any, prior: Any, decision: Decision) -> Dict[str, Any]:
    return {"row": decision.row, "why": decision.why, "subject": verdict.subject.to_key(),
            "quantity": verdict.quantity, "prior": prior.id if prior is not None else None,
            "attempted": verdict.to_json()}


def export_may(new_step: str, prior_key: Tuple[str, str]) -> Decision:
    """EXPORT's two rows (violations 4 and 5), asked by name. Raises on a pair with no row."""
    row = lookup((X, new_step), prior_key)
    why = row.rule(None, None, None)
    return Decision(why is None, row.name, why)


def supersede_sites(root: Optional[str] = None) -> list:
    """Every `supersedes=` keyword in `tools/omr/staged/` that can carry a verdict id, with the decider literal of
    the same call (or the non-literal expression), read from the code by `ast` -- the list the table is tested
    against, never kept by hand."""
    import ast
    import pathlib
    base = pathlib.Path(root or pathlib.Path(__file__).parent)
    out = []
    for path in sorted(base.rglob("*.py")):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            kws = {k.arg: k.value for k in node.keywords if k.arg}
            if "supersedes" not in kws:
                continue
            sv = kws["supersedes"]
            if isinstance(sv, ast.Constant) and sv.value is None:
                continue
            dec = kws.get("decider")
            if isinstance(dec, ast.Constant):
                decider = dec.value
            elif isinstance(dec, ast.JoinedStr):
                decider = "infer:*"
            elif dec is not None:
                decider = ast.unparse(dec)
            else:
                decider = None
            out.append((str(path.relative_to(base)), node.lineno, decider))
    return out
