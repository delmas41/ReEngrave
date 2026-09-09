"""EVALUATE — the consequences of a settled decision, with one owner.

⚠️ WHY THIS IS A STAGE, against my own design document's conclusion.

The design argued that evaluation is the TAIL of adjudication, because nothing
in the existing pipeline iterates -- all three of its propagations are
single-pass `for` loops with no `while` and no repeat-until-stable. Sean and
the coordinator overruled that, and the ruling is right for a reason the
argument missed: **that was a description of the pipeline we have, and we are
not building the pipeline we have.**

The observable fault it fixes is on the record. Consequences today are
scattered inline at the sites that CAUSE them -- a clef settles and pitches
are restated inside `clef_correction`; a key settles and notes are respelled
inside `key_signature_corroboration`; a meter settles and durations are
re-read inside `transcribe`. Because each cause owns its own consequences,
the SUMMARY of the result -- `clef_final`, `key_signature_final`,
`time_signature_final` -- has to be re-maintained by every one of them, and
it was not: 9 of 20, 19 of 26, and one field with no keeper at all. Two
keepers were bolted on after two fields went stale, which is a shape failing
rather than three oversights.

Giving consequences one owner is what removes the need for a keeper. Nothing
in here writes a `*_final` value; a consequence is an EVENT appended to the
log, and "the current pitch" is a query.

⚠️ THE CONSTRAINT THAT SURVIVES, and it is not negotiable: consequences flow
DOWNHILL ONLY, one pass, no fixpoint. `Log.record` refuses a verdict that
supersedes something in its own basis. If a consequence seems to need to flow
uphill -- a restated pitch wanting to re-open the clef that restated it -- DO
NOT BUILD A FIXPOINT. Record the tension and escalate. This project has twice
declined to build a convergence argument and both declines were right.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import (Any, Callable, Dict, List, Optional, Sequence, Tuple)

from .record import (ABSTAIN, Kind, Log, Outcome, Q, Scope, State, Subject,
                     Verdict)


class Consequence(str, Enum):
    """What a settled fact forces to be restated."""

    RESTATE_PITCH = "restate_pitch"          # clef settled
    RESPELL_ACCIDENTAL = "respell_accidental"  # key settled
    RECONCILE_DURATION = "reconcile_duration"  # meter settled
    MOVE_GLYPH = "move_glyph"                # ownership settled
    JOIN_PARTS = "join_parts"                # part boundaries settled
    NAME_PART = "name_part"                  # instrument settled
    SIZE_MEASURE_REST = "size_measure_rest"  # meter settled, over a silent bar


@dataclass(frozen=True)
class Rule:
    """One consequence rule.

    `cause` must be strictly ABOVE `effect` in the dependency order, and
    `check_downhill` asserts it. That is the fixpoint refused structurally
    rather than by discipline.
    """

    consequence: Consequence
    cause: str                     # the quantity whose settling triggers this
    effect: str                    # the quantity that gets restated
    scope: Kind
    fn: Callable[[Log, Subject, Verdict], List[Verdict]]
    bound: str                     # ⚠️ REQUIRED. What stops it running away.
    stub: bool = False
    #: ⚠️ Declares that this rule's cause depends on what it revises, and
    #: that the loop is single-pass. See `Verdict.single_pass_revision`.
    single_pass: bool = False


#: The assumed downhill order. A rule may only write an `effect` that sits
#: LATER in this list than its `cause`.
#:
#: ⚠️ ASSUMPTION (A-EVAL-1). This is the order we believe consequences flow
#: in. It is not measured. It is the single place to change it.
DOWNHILL: Tuple[str, ...] = (
    Q.SYSTEM_MEMBERSHIP,
    Q.STAFF_GROUP,
    Q.MEASURE_PARTITION,
    Q.INSTRUMENT,
    Q.SLOT_INDEX,
    Q.PART_PARTITION,
    Q.PART_NAME,
    Q.CLEF,
    Q.KEY_SIGNATURE,
    Q.GLYPH_OWNER,
    Q.PITCH,
    Q.ACCIDENTAL,
    Q.METER,
    Q.DURATION,
)


RULES: List[Rule] = []


def rule(*, consequence: Consequence, cause: str, effect: str, scope: Kind,
         bound: str, stub: bool = False, single_pass: bool = False):
    """Register a consequence rule.

    ⚠️ `bound` is REQUIRED and is prose, deliberately. Every propagation in
    the tree that works is bounded, and the boundedness is what makes it
    safe: `_reconcile_measure_to_meter` may re-read a beam level by +/-1 ONLY,
    the bar must land EXACTLY on the meter, the answer must be UNIQUE, and it
    is single-voice measures only -- it never adds, deletes or re-pitches a
    note. A rule that cannot state its bound in one sentence has not been
    thought through, and this parameter is here to make that obvious at the
    point of writing rather than after a run.
    """
    check_downhill(cause, effect)

    def wrap(fn: Callable[[Log, Subject, Verdict], List[Verdict]]) -> Callable:
        RULES.append(Rule(consequence, cause, effect, scope, fn, bound, stub,
                          single_pass))
        return fn

    return wrap


def check_downhill(cause: str, effect: str) -> None:
    if cause not in DOWNHILL or effect not in DOWNHILL:
        raise ValueError(
            f"{cause} -> {effect}: both must appear in DOWNHILL so the "
            f"direction can be checked. Add them deliberately.")
    if DOWNHILL.index(effect) <= DOWNHILL.index(cause):
        raise UphillRule(
            f"{cause} -> {effect} runs UPHILL. Do not build a fixpoint. "
            f"Record the tension and escalate -- this is exactly the case "
            f"the design says to bring back rather than resolve silently.")


class UphillRule(RuntimeError):
    """A consequence rule that would close a loop."""


@dataclass
class Report:
    """What EVALUATE did. Event-shaped, like everything else here."""

    fired: List[Tuple[str, str, str]]      # (consequence, subject, effect)
    skipped: List[Tuple[str, str, str]]    # (consequence, subject, why)
    stubs: List[str]

    def to_json(self) -> dict:
        return {"fired": [list(f) for f in self.fired],
                "skipped": [list(s) for s in self.skipped],
                "stubs": sorted(set(self.stubs)),
                "counts": {"fired": len(self.fired),
                           "skipped": len(self.skipped)}}


class NoRulesRegistered(RuntimeError):
    """EVALUATE was asked to run with no consequence rules loaded.

    ⚠️ THIS IS AN ERROR, NOT AN EMPTY RESULT, and the distinction is the same
    one the whole record layer is about. A stage that runs with zero rules
    produces `fired: []` and `skipped: []` -- which is indistinguishable from
    a stage that ran and found nothing to do. The tree already has that fault
    twice over: `OMR_CONTEST_DUMP` and `locate_clef(trace=)` are complete
    recorders that recorded NOTHING because they were off, and nothing about
    their output said so.

    Found during the build by exactly this route: a test imported
    `adjudicators` but not `consequences`, EVALUATE reported an empty run, and
    the empty run read as a pass.
    """


def _ensure_rules() -> None:
    """Load the consequence rules. Idempotent, and a lazy import so
    `consequences` can import this module."""
    if not RULES:
        from . import consequences  # noqa: F401
    if not RULES:
        raise NoRulesRegistered(
            "EVALUATE has no rules. An empty stage is not an empty result.")


def _cause_for(log: Log, quantity: str, subject: Subject):
    """The causing verdict, looked up at the subject OR any ancestor.

    ⚠️ FIX-NOW, FOUND BY A TEST REFUSING TO FIRE. A rule's `scope` is the
    scope of its EFFECT, and the cause can legitimately be coarser: the meter
    is decided at SYSTEM scope while `reconcile_duration` acts on a CELL. An
    exact-subject lookup found nothing, so the rule reported `cause_absent`
    and did nothing -- **silently, and identically to a page with no meter.**

    Every consequence whose cause sits at a coarser scope than its effect was
    dead the same way, which is why this is a substrate fix rather than a
    one-rule patch: a rule wired after it would have inherited the same
    silence.
    """
    found = log.verdict(quantity, subject)
    if found is not None:
        return found
    for ancestor in subject.ancestors():
        found = log.verdict(quantity, ancestor)
        if found is not None:
            return found
    return None


def run(log: Log, *, progress: bool = False) -> Report:
    """One pass, downhill, in DOWNHILL order.

    ⚠️ There is deliberately no `while` in this function and there must never
    be one. If you find yourself wanting to re-run it until stable, that is
    the escalation signal.
    """
    _ensure_rules()
    report = Report(fired=[], skipped=[], stubs=[])
    ordered = sorted(RULES, key=lambda r: DOWNHILL.index(r.cause))

    for r in ordered:
        if r.stub:
            report.stubs.append(f"{r.consequence.value}({r.cause}->{r.effect})")
            continue
        for subject in log.subjects(r.scope):
            cause = _cause_for(log, r.cause, subject)
            if cause is None:
                report.skipped.append(
                    (r.consequence.value, subject.to_key(), "cause_absent"))
                continue
            if cause.outcome is Outcome.ABSTAINED:
                # ⚠️ An abstention is a RESULT, not a failure. A consequence
                # of a fact nobody settled must not fire on a default.
                report.skipped.append(
                    (r.consequence.value, subject.to_key(), "cause_abstained"))
                continue
            if cause.outcome is Outcome.NARROWED:
                # ⚠️ REPORTED APART FROM AN ABSTENTION, deliberately. "It is
                # one of these two" and "I have nothing" are different states,
                # and a rule that could choose among the survivors on its own
                # evidence is exactly what `reconcile_duration` is -- so a
                # narrowed cause is an opportunity a future rule may take, not
                # a dead end. Collapsing the two would hide the opportunity.
                report.skipped.append(
                    (r.consequence.value, subject.to_key(), "cause_narrowed"))
                continue
            produced = r.fn(log, subject, cause)
            for v in produced:
                report.fired.append(
                    (r.consequence.value, subject.to_key(), v.quantity))
        if progress:
            print(f"  evaluate {r.consequence.value}: "
                  f"{len(report.fired)} fired so far")
    return report
