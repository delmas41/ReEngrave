"""INFER — what is most LIKELY, given everything at once. The fourth stage.

⚠️⚠️ READ `docs/plan-2026-09-10-wire-first-then-reconcile.md` §5 BEFORE
CHANGING ANYTHING HERE. This stage is the one place in the pipeline where an
answer may be BEST rather than FORCED, and every guard below exists to stop
that licence leaking into the three stages in front of it.

    GATHER     what is on the page?                 decides nothing
    ADJUDICATE what does this ONE thing mean?       reads it, or abstains
    EVALUATE   what FOLLOWS from what we know?      acts only when FORCED
    INFER      what is most LIKELY, given it all?   acts when the answer is BEST
    EXPORT     write it, and count what did not     always

**The property this stage exists to keep sayable**, and the reason it is a
separate stage rather than a widened EVALUATE:

    Everything in the record before EXPORT was READ or ENTAILED.
    Everything after INFER was read, entailed, or INFERRED -- and LABELLED.

The boundary between the stages is exactly where that guarantee changes,
which is the right place for one.

─────────────────────────────────────────────────────────────────────────────
⚠️ WHAT THIS STAGE MAY NOT DO. Five rules, each enforced by the harness
rather than by a docstring, because a discipline nobody can break is worth
more than one everybody has read.

1.  **It may not run before EVALUATE.** `run()` requires the EVALUATE report
    as an argument, so it cannot be called before one exists. Structural: no
    ordering convention to remember.

2.  **It may not loosen GATHER or ADJUDICATE.** `run()` refuses an unfrozen
    log. The whole design rests on the earlier stages still refusing to
    guess, so that this stage can always tell *"nobody could read this"* from
    *"this was read and it is wrong"*. Destroy that distinction upstream and
    INFER is unbuildable -- so the temptation to relax a reader "because
    INFER will clean it up" is the one failure mode that would cost the
    architecture rather than a number.

3.  **It may only speak where the record has no answer.** `INFERABLE` is
    `{NARROWED, ABSTAINED}`. An inference may NEVER overturn a DECIDED
    verdict: a decision is a READING, and replacing a reading with a guess is
    the thing that makes a cleanup count unable to tell a reading fault from
    an inference fault.

4.  **It may not invent a value.** Where the prior is NARROWED the proposed
    value must be one of the candidates the reader itself admitted --
    `_admit` raises `ValueNotAdmitted` otherwise. So the reader's refusal
    bounds the inference: INFER chooses among what was admitted, it does not
    widen the field.

5.  **It supersedes VISIBLY.** A rule returns a `Proposal`, never a
    `Verdict`; the harness builds the verdict, stamps `decider="infer:..."`
    and `detail["inferred"]=True`, and points `supersedes` at the prior. The
    log is append-only, so the narrowing STAYS in the record with its
    candidates and their support. Nothing is overwritten and nothing is lost.

─────────────────────────────────────────────────────────────────────────────
⚠️⚠️ THE TWO HAZARDS, BOTH ALREADY PAID FOR IN THIS REPOSITORY.

**(a) An uncalibrated number must not be laundered into evidence.**
`Candidate.support` is a sum of signed terms in the deciding function's OWN
units. It does not normalise and 3.0 does not mean twice 1.5. This project
measured what happens when such a number is treated as a probability: ECE
0.1277, failing WORST at the top of the range, the top bin promising 0.989
and delivering 0.692.

    ⚠️ So NOTHING IN THIS MODULE MAY RANK CANDIDATES BY `support` ALONE.
    A rule must reach its answer through evidence the prior did not already
    weigh; `support` may be REPORTED beside the answer and may never be the
    reason for it. `Rule.forbids_argmax` is asserted by the test suite.

**(b) Two readers can fall silent TOGETHER.** *The bars are not an
independent umpire over a bad reading*: a page whose meter the reader mangles
is a page whose ink is degraded, and the same degradation stops its bars from
summing -- so **the case that most needs an arbiter is the case where the
arbiter is silent**. Measured twice independently here (bar sums; `arc_kind`'s
position grammar, available on 81 of 199 arcs and absent on exactly the weaker
readings).

    ⚠️ So A RULE THAT COUNTS N AGREEING WITNESSES MUST SAY WHY THEY ARE N AND
    NOT ONE, and here that is not an argument, it is a COMPUTATION.
    `independent_groups()` partitions witnesses by whether their verdicts'
    provenance closures INTERSECT -- two witnesses resting on a shared row
    are one signal. The partition is recorded on the verdict's `correlated`
    field, which has existed for exactly this and until now was consumed by
    nothing.

─────────────────────────────────────────────────────────────────────────────
⚠️ BYPASS. Default OFF, and off means ABSENT rather than quiet: `pipeline`
adds no `inference` key when the stage did not run, so a record from a tree
carrying this module is byte-identical to one from a tree without it. That is
asserted by `test_infer_bypass.py` rather than asserted here -- an earlier
stage's arm (`readjudicate`, `reexport_arm`) must never have to know this
stage exists.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import (Any, Callable, Dict, List, Mapping, Optional, Sequence,
                    Tuple)

from .record import Kind, Log, Outcome, Q, Subject, Verdict

# ─────────────────────────────────────────────────────────────────────────────
# The flag
# ─────────────────────────────────────────────────────────────────────────────

INFER_ENV = "OMR_INFER"

#: ⚠️ AN ALLOW-LIST, BECAUSE THE DEFAULT IS OFF, and the direction has to
#: follow the default. A default-OFF flag written as a deny-list is switched
#: ON by a typo -- `OMR_INFER=` or `OMR_INFER=nope` would enable a stage whose
#: whole job is to put values in the file that nobody read. Five shipped flags
#: had this backwards; `tools/omr/tests/test_flag_default_direction.py`
#: derives the rule from the source and will fail on a mistake here.
_ON_WORDS = ("1", "true", "yes", "on")


def infer_enabled() -> bool:
    """Read the flag. Anything but an explicit on-word is OFF."""
    return os.environ.get(INFER_ENV, "0").strip().lower() in _ON_WORDS


# ─────────────────────────────────────────────────────────────────────────────
# The vocabulary
# ─────────────────────────────────────────────────────────────────────────────


class Inference(str, Enum):
    """What kind of claim an inference is making."""

    #: A narrowed duration collapsed by what the OTHER staves of the system
    #: say about the same stretch of time.
    COLLAPSE_DURATION_BY_COLUMN = "collapse_duration_by_column"

    #: The same claim for a note that runs to the BARLINE -- the bucket the
    #: rule above declines by design, because a note with no further onset
    #: has the bar's own length and the bar's length is the METER.
    #:
    #: ⚠️⚠️ IT IS A SEPARATE RULE AND NOT A WIDENING, because it needs a
    #: guard the other one does not: a witness whose own length reached it
    #: THROUGH the meter is refused. Folding the two together would hide that
    #: guard behind a branch and put the two reach numbers in one bucket,
    #: which is exactly what stops a reader seeing what the new claim bought.
    COLLAPSE_DURATION_TO_BARLINE = "collapse_duration_to_barline"


#: The only prior states an inference may speak into.
#:
#: ⚠️ `DECIDED` IS DELIBERATELY ABSENT AND MUST STAY ABSENT. See rule 3 in the
#: module docstring: an inference that can overturn a reading makes a cleanup
#: count unable to separate a reading fault from an inference fault, which is
#: the one thing that would cost the architecture rather than a number.
INFERABLE: Tuple[Outcome, ...] = (Outcome.NARROWED, Outcome.ABSTAINED)

#: Every verdict this stage writes carries a decider beginning with this.
DECIDER_PREFIX = "infer:"


def is_inferred(verdict: Any) -> bool:
    """True for a verdict this stage wrote. Takes a `Verdict` or its JSON.

    ⚠️ The SEPARABILITY primitive. A consumer asking *"was this inferred?"*
    gets a straight answer from the record alone, with no side table to keep
    in sync -- the fault that let `clef_final` go stale in 9 of 20 rows.
    """
    decider = getattr(verdict, "decider", None)
    if decider is None and isinstance(verdict, Mapping):
        decider = verdict.get("decider")
    return bool(decider) and str(decider).startswith(DECIDER_PREFIX)


# ─────────────────────────────────────────────────────────────────────────────
# What a rule returns -- and what it CANNOT return
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Proposal:
    """One inference, before the harness has stamped it.

    ⚠️⚠️ A RULE RETURNS THESE AND NEVER A `Verdict`, WHICH IS WHAT MAKES THE
    LABELLING STRUCTURAL. A rule physically cannot write an unlabelled
    verdict, cannot overturn a DECIDED one, and cannot point `supersedes`
    somewhere convenient -- the harness does all three, once, for every rule.

    That is mechanism 3 of `record.py` (*"the decision is not asked to be
    honest about what it was missing, it is not consulted"*) applied to the
    one stage where the temptation to be less than honest is greatest.
    """

    #: Where the inference lands. Required, because a rule at SYSTEM scope
    #: emits proposals about many glyphs.
    subject: Subject
    value: Any
    reason: str
    #: Row ids the inference rests on. The prior is added by the harness.
    basis: Tuple[str, ...] = ()
    #: The independent witnesses, as verdict ids, BEFORE the correlation
    #: partition. `_admit` computes the partition and records it.
    witnesses: Tuple[str, ...] = ()
    detail: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    """One inference rule.

    ⚠️ `bound` and `why_witnesses_are_independent` are REQUIRED PROSE, on the
    model of `evaluate.Rule.bound`. Every propagation in this tree that works
    is bounded and the boundedness is what makes it safe; a rule that cannot
    state its bound in one sentence has not been thought through, and this
    parameter makes that obvious at the point of writing rather than after a
    run.
    """

    inference: Inference
    target: str                     # the quantity it writes
    reads: Tuple[str, ...]          # the quantities it consumes
    scope: Kind
    fn: Callable[[Log, Subject], Sequence[Proposal]]
    bound: str
    #: ⚠️ Declares that this rule looks ACROSS siblings -- the thing EVALUATE
    #: structurally cannot do, and the reason this stage exists at all. A
    #: rule that is not sideways should be asked why it is not a consequence.
    sideways: bool
    why_witnesses_are_independent: str
    #: ⚠️ Asserted by the suite. A rule may REPORT `support` and may never
    #: choose by it -- see hazard (a).
    forbids_argmax: bool = True
    stub: bool = False


RULES: List[Rule] = []


def rule(*, inference: Inference, target: str, reads: Sequence[str],
         scope: Kind, bound: str, sideways: bool,
         why_witnesses_are_independent: str, stub: bool = False):
    """Register an inference rule."""
    if target not in Q.all():
        raise ValueError(f"{target!r} is not a known quantity")
    for q in reads:
        if q not in Q.all():
            raise ValueError(f"{q!r} is not a known quantity")

    def wrap(fn):
        RULES.append(Rule(inference, target, tuple(reads), scope, fn, bound,
                          sideways, why_witnesses_are_independent, True, stub))
        return fn

    return wrap


# ─────────────────────────────────────────────────────────────────────────────
# Independence -- hazard (b), computed rather than argued
# ─────────────────────────────────────────────────────────────────────────────


def independent_groups(log: Log,
                       verdict_ids: Sequence[str]) -> Tuple[frozenset, ...]:
    """Partition witnesses into groups that share no provenance.

    ⚠️⚠️ THIS IS THE ANSWER TO *"why are they N witnesses and not one"*, and
    it is a COMPUTATION rather than an argument. Two verdicts whose
    `Log.closure` intersects rest on a shared row -- the same detection, the
    same staff spacing, the same external document -- and counting them twice
    is the double-counting that `Observation.derived_from` was added to stop.

    Returns one frozenset of verdict ids per INDEPENDENT group, so
    `len(independent_groups(...))` is the honest witness count and
    `len(verdict_ids)` is not.

    ⚠️ It is a ONE-SIDED test and says so here rather than in a write-up:
    DISJOINT closures prove the rows differ, they do NOT prove the readings
    fail independently. Two staves of one badly-printed page share no row and
    still degrade together -- that is the CONVENTION/INK correlation CLAUDE.md
    records as measured but unquantified. So this rules out the correlation
    the record can see and is silent about the one it cannot.
    """
    closures = {vid: log.closure(vid) for vid in verdict_ids}
    groups: List[set] = []
    members: List[set] = []
    for vid, cl in closures.items():
        hit = [i for i, g in enumerate(groups) if g & cl]
        if not hit:
            groups.append(set(cl))
            members.append({vid})
            continue
        first = hit[0]
        for i in reversed(hit[1:]):
            groups[first] |= groups[i]
            members[first] |= members[i]
            del groups[i]
            del members[i]
        groups[first] |= cl
        members[first].add(vid)
    return tuple(frozenset(m) for m in members)


# ─────────────────────────────────────────────────────────────────────────────
# Errors -- each names a rule this stage refuses to break
# ─────────────────────────────────────────────────────────────────────────────


class NotEvaluated(RuntimeError):
    """INFER was asked to run without EVALUATE's report.

    The stage ordering, made structural. See rule 1.
    """


class LogNotFrozen(RuntimeError):
    """INFER was asked to run on a log still open for measurement.

    See rule 2: this stage may not loosen GATHER.
    """


class ValueNotAdmitted(RuntimeError):
    """An inference proposed a value the reader never admitted.

    See rule 4. The reader's own candidate set bounds the inference: INFER
    chooses among what was admitted, it does not widen the field. A rule that
    wants to widen it is not an inference, it is a second reader, and belongs
    in ADJUDICATE where it would have to declare its evidence.
    """


class NoRulesRegistered(RuntimeError):
    """INFER ran with no rules loaded.

    ⚠️ AN ERROR, NOT AN EMPTY RESULT, and for the reason
    `evaluate.NoRulesRegistered` gives at length: a stage that runs with zero
    rules reports `inferred: []`, which is indistinguishable from a stage that
    ran and found nothing to infer. This tree already had that fault twice
    (`OMR_CONTEST_DUMP`, `locate_clef(trace=)`) -- complete recorders that
    recorded NOTHING because they were off, with nothing in the output saying
    so.
    """


# ─────────────────────────────────────────────────────────────────────────────
# The report
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Report:
    """What INFER did. Event-shaped, like everything else here."""

    #: (inference, subject, verdict id)
    inferred: List[Tuple[str, str, str]] = field(default_factory=list)
    #: (inference, subject, why)
    skipped: List[Tuple[str, str, str]] = field(default_factory=list)
    stubs: List[str] = field(default_factory=list)
    #: Reach, per rule, BEFORE any inference is made -- how much there was to
    #: speak about at all.
    #:
    #: ⚠️ REPORTED FIRST AND SEPARATELY, because this repository has burned a
    #: session on a clean zero that meant nothing: a change that moves nothing
    #: because it is INERT and one that moves nothing because the page holds
    #: NOTHING TO MOVE are the same number.
    reach: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "inferred": [list(i) for i in self.inferred],
            "skipped": [list(s) for s in self.skipped],
            "stubs": sorted(set(self.stubs)),
            "reach": self.reach,
            "counts": {"inferred": len(self.inferred),
                       "skipped": len(self.skipped)},
        }


def _ensure_rules() -> None:
    """Load the inference rules. Idempotent, and a lazy import so `inferences`
    can import this module."""
    if not RULES:
        from . import inferences  # noqa: F401
    if not RULES:
        raise NoRulesRegistered(
            "INFER has no rules. An empty stage is not an empty result.")


def _candidate_values(prior: Verdict) -> Tuple[Any, ...]:
    return tuple(c.value for c in (prior.candidates or ()))


def _same_value(a: Any, b: Any) -> bool:
    """Value equality that survives a round trip through JSON.

    ⚠️ A duration value is a dict, and `reinfer.py` rebuilds one from a saved
    record -- where an int has become an int and a tuple a list. Comparing
    with `==` on the raw objects would make a rebuilt arm silently admit
    nothing, which would read as *"the rule is inert"*.
    """
    if a is b:
        return True
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return (set(a) == set(b)
                and all(_same_value(a[k], b[k]) for k in a))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same_value(x, y) for x, y in zip(a, b))
    return a == b


def _admit(log: Log, r: Rule, p: Proposal, report: Report) -> Optional[Verdict]:
    """Every guard in the module docstring, in one place.

    ⚠️ ONE PLACE ON PURPOSE. A guard repeated per rule is a guard that a new
    rule can forget; this one runs for every proposal of every rule and there
    is no path around it.
    """
    key = p.subject.to_key()
    prior = log.verdict(r.target, p.subject)
    if prior is None:
        report.skipped.append((r.inference.value, key, "no_prior_verdict"))
        return None
    if prior.outcome not in INFERABLE:
        # Rule 3. Reported by NAME so a reader can see that the stage declined
        # to overturn a reading, rather than that it found nothing.
        report.skipped.append(
            (r.inference.value, key, f"prior_is_{prior.outcome.value}"))
        return None
    if prior.outcome is Outcome.NARROWED:
        admitted = _candidate_values(prior)
        if not any(_same_value(p.value, v) for v in admitted):
            raise ValueNotAdmitted(
                f"{r.inference.value} proposed a value for {key} that "
                f"{prior.decider} never admitted. An inference chooses among "
                f"the candidates the reader kept; widening the field is a "
                f"second READING and belongs in ADJUDICATE, where it would "
                f"have to declare its evidence. Proposed {p.value!r}; "
                f"admitted {list(admitted)!r}.")

    groups = independent_groups(log, p.witnesses) if p.witnesses else ()
    detail = dict(p.detail)
    detail.update({
        # ⚠️ The label, stamped by the HARNESS. A rule cannot omit it.
        "inferred": True,
        "rule": r.inference.value,
        "sideways": r.sideways,
        "prior_outcome": prior.outcome.value,
        "n_witnesses": len(p.witnesses),
        "n_independent_witnesses": len(groups),
    })
    v = Verdict(
        id=log._next_id("vrd"),          # noqa: SLF001 -- same module family
        subject=p.subject,
        quantity=r.target,
        outcome=Outcome.DECIDED,
        value=p.value,
        decider=f"{DECIDER_PREFIX}{r.inference.value}",
        reason=p.reason,
        used=tuple(p.witnesses),
        # ⚠️ The prior is ALWAYS in the basis: an inference that collapses a
        # narrowing has read that narrowing, and saying so is what lets the
        # fixpoint guard in `Log.record` do its job.
        basis=tuple(p.basis) + (prior.id,),
        correlated=groups,
        # ⚠️ The candidates the reader kept travel FORWARD onto the inferred
        # verdict, so the narrowing is legible from the answer itself and not
        # only by walking back to a superseded row.
        candidates=prior.candidates,
        supersedes=prior.id,
        detail=detail,
    )
    log.record(v)
    report.inferred.append((r.inference.value, key, v.id))
    return v


def run(log: Log, evaluated: Any, *, progress: bool = False) -> Report:
    """One pass. No fixpoint, and there must never be one.

    `evaluated` is EVALUATE's `Report` and is REQUIRED -- it is how the stage
    ordering is enforced rather than remembered (rule 1). Pass the real one;
    a caller that has not run EVALUATE has nothing to pass.

    ⚠️ There is deliberately no `while` in this function. If you find
    yourself wanting to re-run it until stable, that is the escalation
    signal, not a design. `Log.record`'s `UphillConsequence` guard is still
    live underneath and will refuse a verdict that reaches its own prior
    through its other inputs.
    """
    if evaluated is None:
        raise NotEvaluated(
            "INFER needs EVALUATE's report. It may not run before "
            "consequences are settled -- a narrowed duration that a "
            "consequence was about to restate is not a narrowing to infer "
            "over.")
    if not log.frozen:
        raise LogNotFrozen(
            "INFER was handed a log still open for measurement. This stage "
            "may not loosen GATHER: the whole design rests on the earlier "
            "stages still refusing to guess, so that INFER can tell 'nobody "
            "could read this' from 'this was read and it is wrong'.")
    _ensure_rules()

    report = Report()
    for r in RULES:
        if r.stub:
            report.stubs.append(f"{r.inference.value}({r.target})")
            continue
        produced = 0
        for subject in log.subjects(r.scope):
            for p in r.fn(log, subject):
                if _admit(log, r, p, report) is not None:
                    produced += 1
        report.reach.setdefault(r.inference.value, {})["inferred"] = produced
        if progress:
            print(f"  infer {r.inference.value}: {produced} inferred")
    return report


def inferred_verdicts(log: Log) -> Tuple[Verdict, ...]:
    """Every verdict this stage wrote, for a consumer that wants to strip
    them -- the separability requirement, as a query rather than a list
    somebody maintains."""
    return tuple(v for v in log.all_verdicts() if is_inferred(v))


def scoring_conflict(r: Rule, quantities: Sequence[str]) -> Tuple[str, ...]:
    """The quantities a self-check would share with what this rule CONSUMED.

    ⚠️⚠️ THE TRAP THIS EXISTS TO STOP, AND IT HAS ALREADY BEEN PAID FOR HERE:
    **do not score an inference by the quantity it consumed.** If a rule
    collapses a duration USING the bar sum, then scoring it BY bar-fill is
    scoring it by the thing it optimises -- the fault CLAUDE.md records
    against the tie-pairing repair, where *"same-y and same-pitch are near
    equivalent, and the rule is being scored by a quantity it optimises"*.

    A non-empty result means the invariant is NOT a legitimate self-check for
    this rule. `probe/self_check.py` refuses to print a score rather than
    printing one with a caveat, because a caveat beside a number is read as a
    number.
    """
    return tuple(sorted(set(r.reads) & set(quantities)))
