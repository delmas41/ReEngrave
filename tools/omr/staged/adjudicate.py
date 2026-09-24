"""ADJUDICATE — decisions that declare their evidence.

A decision is a pure function of the frozen gathered record plus
earlier-adjudicated facts. It reads no raster. It returns a `Ruling`; the
HARNESS turns that into a `Verdict`, filling in what the decision was not
asked about: what it considered, what was missing, what a reader declined,
what the circularity filter refused, and which of its evidence is really one
signal wearing two hats.

⚠️ Because ADJUDICATE reads a FROZEN log, the order in which decisions run
inside this stage costs nothing and can differ per fact. That is Sean's "all
the info needs to flow in any direction once it is gathered", made safe
rather than merely permitted: there is no ordering to get wrong because
nothing a decision reads can still change.

⚠️ NO PROBABILITIES. Evidence combines as signed terms with a threshold, or
as ordering. An uncalibrated probability is worse than none -- measured here
at ECE 0.1277, with a top bin promising 0.989 and delivering 0.692. There is
deliberately no way to express a multiplier in this module.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import (Any, Callable, Dict, FrozenSet, Iterable, List, Optional,
                    Sequence, Set, Tuple, Union)

from .record import (ABSTAIN, Abstention, Candidate, Kind, Log, Observation,
                     Outcome, Q, Scope, State, Subject, Verdict)


__all_reexport__ = (Candidate,)


class UndeclaredEvidence(RuntimeError):
    """A decision asked for a quantity it did not declare in `wants`.

    This is what makes "the signature IS the declaration" true rather than
    aspirational. The precedent is `apply_contextual_analysis`, which raises
    TypeError if `assist is None` rather than defaulting -- no silent default
    for a decision that spends something.
    """


class UndeclaredReason(RuntimeError):
    """A decision returned a `reason` outside its declared vocabulary."""


# ─────────────────────────────────────────────────────────────────────────────
# What counts as READING a fact directly
#
# ⚠️ This table is the load-bearing half of the circularity filter, and it has
# to be declared rather than inferred. The rule is "an interpretation may
# anchor a decision only if its basis holds an INDEPENDENT READING" -- and
# "reading" cannot mean "any observation in the closure", because every
# closure bottoms out in page geometry and that would admit everything.
#
# So: for each adjudicated quantity, which observation quantities constitute
# a direct reading OF THAT QUANTITY off the page.
# ─────────────────────────────────────────────────────────────────────────────

READINGS: Dict[str, Tuple[str, ...]] = {
    Q.INSTRUMENT: (Q.MARGIN_LABEL, Q.TEXT_LAYER, Q.ROSTER_ENTRY),
    Q.CLEF: (Q.CLEF_GLYPH, Q.CLEF_POSITION, Q.CLEF_LOCATED, Q.CLEF_SEED),
    Q.KEY_SIGNATURE: (Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER,
                      Q.KEYSIG_TEMPLATE_FIT),
    Q.SYSTEM_KEY: (Q.KEYSIG_MARKER, Q.KEYSIG_RUN_POSITION,
                   Q.KEYSIG_TEMPLATE_FIT),
    Q.METER: (Q.METER_GLYPH, Q.METER_TEMPLATE, Q.DOSSIER_FACT),
    Q.STAFF_GROUP: (Q.BRACKET_BLOCK, Q.SYSTEMIC_COLUMN),
    Q.GROUP_SYMBOL: (Q.BRACKET_BLOCK,),
    Q.SYSTEM_MEMBERSHIP: (Q.GAP_BRIDGING, Q.SYSTEMIC_COLUMN),
    Q.MEASURE_PARTITION: (Q.BARLINE_COLUMN,),
    Q.DURATION: (Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS),
    Q.GLYPH_OWNER: (Q.GLYPH_BAND_DISTANCE, Q.GLYPH_LADDER),
    Q.SLOT_INDEX: (Q.MARGIN_LABEL, Q.TEXT_LAYER),
    Q.PART_PARTITION: (Q.MARGIN_LABEL, Q.TEXT_LAYER),
    Q.DIRECTION: (Q.DIRECTION_WORD,),
    Q.DYNAMIC: (Q.DYNAMIC_LETTER,),
    Q.ARC_KIND: (Q.ARC_BOX,),
    Q.ARC_OWNER: (Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION),
    Q.TUPLET_RATIO: (Q.TUPLET_MARKER,),
    Q.ARTICULATION_OWNER: (Q.ARTICULATION_MARK,),
    Q.WEDGE_ANCHOR: (Q.WEDGE_BOX,),
    Q.PITCH: (Q.NOTEHEAD_STAFF_POSITION,),
}


class Checkable(str, Enum):
    """Can this fact's own correctness be tested with NO ground truth?

    Sean, 2026-09-07:

        "There will be certain facts that can be determined by themselves:
        this measure is 4/4 and it has 9 eighth notes is a provable mistake.
        Other things like is this a C or a C# will not be internally provable.
        That needs to be connected to what weighs in the process."

    ⚠️ THIS IS NOT AN ACADEMIC DISTINCTION. Sean's stated primary input is
    SCANNED ORCHESTRAL SCORES FROM IMSLP, and the score library pairs a PDF
    with a reference encoding for **27 works out of 235 held editions**. For
    the overwhelming majority of real inputs there is no truth file and never
    will be, so **CHECKABLE names the errors the system can find on the actual
    work** and UNCHECKABLE names the ones that will always need a reference or
    a human. It is a map of where self-correction is possible at all.

    ⚠️ THREE REFINEMENTS THE BINARY HIDES, each of which changes a weight:

    1. **A check has RESOLUTION.** It catches errors larger than its own
       granularity and is blind below. The written-range test catches a whole
       CLEF error (two or more diatonic steps) and cannot see C vs C# (one
       semitone) -- which is precisely why Sean's example is the example.
    2. **A check has COVERAGE.** A tie's two ends must be the same pitch, so
       C vs C# IS checkable *at a tie* and nowhere else. "Uncheckable" almost
       always means "uncheckable in general, checkable in special positions".
    3. **A check inherits its inputs' reliability.** A test run on composed
       outputs is only as good as the composition -- which is why the tie/slur
       grammar veto measured NEUTRAL on engravings and +130 edits on SCANS:
       its input is the resolved pitch, and `wrong note` is 26% of that pool.
       ⚠️ A sound check over unreliable inputs is an unreliable check.
    """

    CHECKABLE = "checkable"      # an independent constraint must hold
    UNCHECKABLE = "uncheckable"  # determined, not verified
    MIXED = "mixed"              # unverifiable in itself, verifiable by (d)


class Mode(str, Enum):
    """⚠️ ADDITIVE vs COMPETITIVE is a real distinction, not tidiness.

    Measured on the grouping fact across 67 stored transcriptions: consuming
    it ADDITIVELY changed 20 exports, added 108 bracket groups, kept braces at
    2 -> 2 with none lost, and made zero content differences outside the group
    lines. Letting it OVERRULE the incumbent brace rule would have declared
    five Brahms wind pairs to be pianos.
    """

    ADDITIVE = "additive"          # may only ADD a fact where none stood
    COMPETITIVE = "competitive"    # may overturn -- needs a margin_floor


# ─────────────────────────────────────────────────────────────────────────────
# Signed terms -- the ONE sanctioned way to combine evidence
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Term:
    """One piece of signed evidence for one candidate.

    The shape is `slots._pair_score`'s, generalised: a fixed weight per kind
    of agreement, summed, compared to a threshold. `score_layouts._pair_score`
    goes one step further and conditions a weight on the PROVENANCE of the
    reading (`SCORE_TREBLE_CONFLICT = -0.3` against `SCORE_CLEF_CONFLICT =
    -1.5`, because a treble reading is weak evidence -- treble is both the
    failure mode and the positional default). That is expressible here by
    choosing the weight when the term is built.
    """

    name: str
    weight: float
    rows: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.weight != self.weight:  # NaN
            raise ValueError("a term's weight may not be NaN")


#: A term deliberately WITHHELD, because its evidence was absent or
#: incomparable. ⚠️ Withholding is not the same as scoring zero, and the tree
#: already knows it: `slots._pair_score` withholds its group term when
#: `group_map is None` rather than guessing, because "a wrong group verdict is
#: worth 3.0 against a position signal worth ~0.05".
WITHHELD = None


def tally(terms: Sequence[Optional[Term]], *,
          correlated: Sequence[FrozenSet[str]] = ()) -> float:
    """Sum the terms, counting each CORRELATED GROUP once.

    Withheld (None) terms contribute nothing and are not zeros -- a zero
    would say "I looked and found no support", which is a different claim.
    """
    live = [t for t in terms if t is not None]
    if not correlated:
        return sum(t.weight for t in live)

    total = 0.0
    spent: Set[FrozenSet[str]] = set()
    for term in live:
        group = _group_of(term, correlated)
        if group is None:
            total += term.weight
            continue
        if group in spent:
            continue          # this signal has already been counted once
        spent.add(group)
        # the strongest term the group supports, not the sum of its members
        members = [t for t in live if _group_of(t, correlated) == group]
        total += max(members, key=lambda t: abs(t.weight)).weight
    return total


def _group_of(term: Term,
              correlated: Sequence[FrozenSet[str]]) -> Optional[FrozenSet[str]]:
    for group in correlated:
        if any(r in group for r in term.rows):
            return group
    return None


# ─────────────────────────────────────────────────────────────────────────────
# What a decision returns
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Ruling:
    """Deliberately smaller than a Verdict: the decision fills only what it
    knows. Everything about what it was MISSING is the harness's job."""

    value: Any
    reason: str
    margin: Optional[float] = None
    used: Tuple[str, ...] = ()
    detail: Dict[str, Any] = field(default_factory=dict)

    #: Every value still admitted, best first. ⚠️ `support` is in the
    #: decision's OWN units and is NOT a probability -- see `record.Candidate`.
    candidates: Tuple[Candidate, ...] = ()

    @staticmethod
    def abstain(reason: str, **detail: Any) -> "Ruling":
        return Ruling(value=None, reason=reason, detail=dict(detail))

    @staticmethod
    def narrow(candidates: Sequence[Candidate], reason: str, *,
               used: Sequence[str] = (), **detail: Any) -> "Ruling":
        """⚠️ "It is one of these." Not a weaker abstention -- a DIFFERENT
        answer, and usually a more useful one than the single value a
        decide-or-abstain decision would have been forced to invent."""
        ordered = tuple(sorted(candidates, key=lambda c: -c.support))
        return Ruling(value=None, reason=reason, candidates=ordered,
                      used=tuple(used), detail=dict(detail))

    @property
    def abstained(self) -> bool:
        return self.value is None and not self.candidates


# ─────────────────────────────────────────────────────────────────────────────
# Evidence -- the whole surface a decision sees
# ─────────────────────────────────────────────────────────────────────────────


class Evidence:
    """The declared evidence for one decision on one subject.

    Every access is checked against the decision's `wants`. A decision that
    reads something it did not declare fails loudly in the first test that
    exercises it.
    """

    __slots__ = ("log", "subject", "_spec", "_seen", "_excluded", "_declined",
                 "_missing")

    def __init__(self, log: Log, subject: Subject, spec: "DecisionSpec"):
        self.log = log
        self.subject = subject
        self._spec = spec
        self._seen: List[str] = []
        self._excluded: List[Tuple[str, str]] = []
        self._declined: Set[str] = set()
        self._missing: Set[str] = set()

    # ── declaration enforcement ─────────────────────────────────────────────

    def _check(self, quantity: str) -> None:
        if quantity not in self._spec.wants:
            raise UndeclaredEvidence(
                f"{self._spec.name} read {quantity!r} without declaring it. "
                f"Add it to wants= -- the declaration is what lets the harness "
                f"record that it was missing.")

    # ── queries ─────────────────────────────────────────────────────────────

    def rows(self, quantity: str, *, scope: Scope = Scope.EXACT,
             subject: Optional[Subject] = None) -> Tuple[Observation, ...]:
        self._check(quantity)
        sub = subject if subject is not None else self.subject
        found = self.log.rows(quantity, sub, scope=scope)
        kept = tuple(r for r in found if self._admit(r))
        self._note(quantity, kept, sub, scope)
        return kept

    def refusals(self, quantity: str, *, scope: Scope = Scope.EXACT,
                 subject: Optional[Subject] = None) -> Tuple[Abstention, ...]:
        self._check(quantity)
        sub = subject if subject is not None else self.subject
        return self.log.refusals(quantity, sub, scope=scope)

    def verdict(self, quantity: str, *,
                subject: Optional[Subject] = None) -> Optional[Verdict]:
        self._check(quantity)
        sub = subject if subject is not None else self.subject
        found = self.log.verdict(quantity, sub)
        if found is None:
            self._missing.add(quantity)
            return None
        if not self._admit(found):
            return None
        self._seen.append(found.id)
        return found

    def verdicts(self, quantity: str, *, scope: Scope = Scope.EXACT,
                 subject: Optional[Subject] = None) -> Tuple[Verdict, ...]:
        self._check(quantity)
        sub = subject if subject is not None else self.subject
        found = self.log.verdicts(quantity, sub, scope=scope)
        kept = tuple(v for v in found if self._admit(v))
        for v in kept:
            self._seen.append(v.id)
        return kept

    def admitted(self, quantity: str, *,
                 subject: Optional[Subject] = None) -> Tuple[Any, ...]:
        """Every value still admitted for `quantity`, best first.

        ⚠️ THE POINT IS THAT A CONSUMER NEED NOT COLLAPSE THE SET EARLY. One
        value for a DECIDED verdict, N for a NARROWED one, none for an
        ABSTAINED one -- so a consumer can carry the ambiguity forward and let
        its OWN evidence settle it, which is what `reconcile_duration` does
        with the meter.
        """
        v = self.verdict(quantity, subject=subject)
        if v is None:
            return ()
        if v.outcome is Outcome.DECIDED:
            return (v.value,)
        return tuple(c.value for c in v.candidates)

    def subjects(self, kind: Kind) -> Tuple[Subject, ...]:
        """Every subject of `kind` the log holds, in reading order.

        ⚠️ STRUCTURAL, AND THAT IS WHY IT TAKES NO QUANTITY AND CHECKS NO
        DECLARATION. It answers "what pages and systems does this document
        have", which is a fact about the raster's layout, not evidence about
        anything. Nothing is read here -- a decision that wants a VALUE off
        one of these subjects must still go through `rows`/`verdict` with the
        quantity declared, and is still checked.

        `Subject` is an ordered dataclass keyed (kind, page, system, ...), so
        the tuple is already in reading order and a caller asking "what came
        BEFORE me" can compare directly.
        """
        return self.log.subjects(kind)

    def state(self, quantity: str, *, scope: Scope = Scope.EXACT,
              subject: Optional[Subject] = None) -> State:
        """⚠️ The three-state answer. Use it: DECLINED carries a reason and
        ABSENT does not, and a decision that treats them alike has thrown the
        reason away."""
        self._check(quantity)
        sub = subject if subject is not None else self.subject
        return self.log.state(quantity, sub, scope=scope)

    # ── bookkeeping the decision never sees ─────────────────────────────────

    def _note(self, quantity: str, kept: Sequence[Any], sub: Subject,
              scope: Scope) -> None:
        for r in kept:
            self._seen.append(r.id)
        if kept:
            return
        state = self.log.state(quantity, sub, scope=scope)
        if state is State.DECLINED:
            self._declined.add(quantity)
        elif state is State.ABSENT:
            self._missing.add(quantity)

    # ── the circularity filter ──────────────────────────────────────────────

    def _admit(self, row: Any) -> bool:
        """The independent-witness rule, applied at hand-in time.

        The decision writes no circularity code at all -- which is the point.
        The three standing refusals in the tree
        (`clef_correction.py:566`, `dossier.py:434`, `score_layouts.py:682`)
        were each won by measurement after being bitten; this reproduces them
        as a set operation, and must also reproduce the DELIBERATE exception
        (`score_order_ambiguity`, admitted on purpose at `contextual.py:409`).
        """
        verdict_q = self._spec.quantity

        # A quality hold-out is NOT a circularity question and is kept apart.
        # `roster` identity is held out of clef decisions by default while its
        # basis is a catalog row, not a clef descendant -- the filter would
        # admit it, and should. Merging the two is how a measured judgement
        # goes silently missing.
        tier = getattr(row, "detail", {}).get("tier") if hasattr(row, "detail") else None
        if tier and tier in self._spec.excludes_tiers:
            self._excluded.append((row.id, f"tier:{tier}"))
            return False
        if getattr(row, "reader", None) in self._spec.excludes_tiers:
            self._excluded.append((row.id, f"reader:{row.reader}"))
            return False

        # (a) our own quantity is nowhere in its ancestry -> nothing to check.
        closure_q = self.log.quantities_in_closure(row.id)
        if verdict_q not in closure_q:
            return True

        # An Observation whose own quantity is what we are deciding is a
        # READING of it, not a circular derivation. Readings are the input.
        if isinstance(row, Observation):
            return True

        # (b) it is an interpretation with our output in its ancestry. Admit
        #     ONLY if it also rests on an independent reading of ITS OWN
        #     quantity -- one whose closure does not contain our quantity.
        for reading_q in READINGS.get(row.quantity, ()):
            for rid in self.log.closure(row.id):
                other = self.log.row(rid)
                if other is None or other.quantity != reading_q:
                    continue
                if verdict_q not in self.log.quantities_in_closure(rid):
                    return True

        self._excluded.append(
            (row.id, f"circular:{verdict_q}_in_basis_without_independent_reading"))
        return False

    # ── correlation ─────────────────────────────────────────────────────────

    def correlated_groups(self) -> Tuple[FrozenSet[str], ...]:
        """Rows that are ONE signal wearing two hats.

        Two rows are one signal when they come from the same reader on the
        same crop, or when their provenance closures intersect above the
        raster.

        ⚠️ The live example that motivates it: the header clef pre-pass and
        the measure-pass clef argmax LOOK like two readings and are measured
        to be the same call on the same list object -- divergent on exactly 0
        of 396 staves. Comparing them as an agreement signal would have
        produced a healthy-looking 77% agreement rate carrying no information.

        ⚠️ ROADMAP 1.2. The connected components of the `_one_signal` graph
        used to be found by an O(n^2) all-pairs walk over everything the
        decision consulted (`_seen`), which for `arc_owner` on the Litolff
        record is n~=770 -- measured at 26x the cost of the rest of the
        decision combined (8.6s / 64 arcs WITH this walk against 0.3s / 64
        arcs without it). `_one_signal`'s OWN two branches are each far
        cheaper to answer in bulk than pairwise:

          * two Observations are one signal iff they share the exact key
            (reader, frame, quantity) -- a hash-bucket, not a comparison;
          * anything else needs `Log.closure()` intersection, but the
            candidates for THAT are only the rows outside the observation
            buckets (`others`, below), which is a small fraction of `_seen`
            for every decision measured so far.

        Union-find turns the same connectivity question into ONE bucketing
        pass over the observations (O(n)), one all-pairs pass restricted to
        `others`, and one pass of `others` against only those observations
        that CARRY A BASIS (O(k^2 + k*d), d = derived observations, which is
        0 on every document without a confirmed fact sheet). The last of
        those three is where the correctness lives, and the argument is
        below at its site: an empty-basis Observation provably cannot be one
        signal with a non-observation, so it is skipped rather than tested,
        while a derived one is tested MEMBER BY MEMBER because a bucket key
        does not fix `derived_from`.

        ⚠️ An earlier draft of this rewrite tested ONE REPRESENTATIVE per
        bucket instead, reasoning that `_one_signal` does not special-case on
        the specific observation. It does, through `closure(b)`. That draft
        was caught before landing and the counter-example is recorded in
        `benchmarks/omr-decide-stage-cost-2026-09/FINDINGS.md` §4.
        """
        rows = [self.log.row(i) for i in self._seen]
        rows = list({r.id: r for r in rows if r is not None}.values())

        parent: Dict[str, str] = {r.id: r.id for r in rows}

        def find(x: str) -> str:
            root = x
            while parent[root] != root:
                root = parent[root]
            while parent[x] != root:
                parent[x], x = root, parent[x]
            return root

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        obs_buckets: Dict[Tuple[str, str, str], List[Observation]] = {}
        others: List[Any] = []
        for r in rows:
            if isinstance(r, Observation):
                obs_buckets.setdefault((r.reader, r.frame, r.quantity), []).append(r)
            else:
                others.append(r)

        # Every Observation sharing a (reader, frame, quantity) key is one
        # signal BY DEFINITION (`_one_signal`'s first branch) -- union the
        # whole bucket against its first member, which is O(n) total rather
        # than O(n^2).
        for bucket in obs_buckets.values():
            if len(bucket) < 2:
                continue
            first = bucket[0].id
            for r in bucket[1:]:
                union(first, r.id)

        # `others` (Verdicts/Abstentions) need the general, closure-based
        # test -- against each other, and against observations.
        #
        # ⚠️ AN OBSERVATION WITH AN EMPTY BASIS CAN NEVER BE ONE SIGNAL WITH
        # A NON-OBSERVATION, and that is a PROOF rather than a measurement:
        # `closure(obs)` is then exactly `{obs.id}`, so `_one_signal`'s
        # intersection is at most `{obs.id}` -- which `_one_signal`'s very
        # next line discards along with `a.id`. The whole empty-basis
        # population, which is nearly every row on every document measured so
        # far, is therefore skipped OUTRIGHT here, not merely tested once per
        # bucket.
        #
        # ⚠️ THE REMAINDER IS TESTED MEMBER BY MEMBER, NOT BY A BUCKET
        # REPRESENTATIVE, and the difference is not pedantry. A (reader,
        # frame, quantity) key does NOT force one `derived_from`:
        # `Observation`'s own docstring records that the empty-basis
        # invariant was found TOO STRONG on 2026-09-07 -- "a modelling error
        # with a live consequence" -- and that an external fact's descendants
        # carry it. Two dossier-seeded rows sharing a bucket but resting on
        # DIFFERENT source rows get opposite answers from `_one_signal`
        # (measured: `benchmarks/omr-decide-stage-cost-2026-09/FINDINGS.md`
        # §4), so a representative would settle the group by INSERTION ORDER.
        # Today's one derived producer, `gather_clef_seed`, happens to hang
        # every row off a single `sources["dossier"]` row, which makes a
        # representative accidentally right on today's tree and is not a
        # property the bucket key guarantees.
        derived_obs = [r for bucket in obs_buckets.values()
                       for r in bucket if r.basis]
        for i, a in enumerate(others):
            for b in others[i + 1:]:
                if _one_signal(self.log, a, b):
                    union(a.id, b.id)
            for obs in derived_obs:
                if _one_signal(self.log, a, obs):
                    union(a.id, obs.id)

        components: Dict[str, List[str]] = {}
        for r in rows:
            components.setdefault(find(r.id), []).append(r.id)
        return tuple(frozenset(ids) for ids in components.values() if len(ids) > 1)


def _one_signal(log: Log, a: Any, b: Any) -> bool:
    if isinstance(a, Observation) and isinstance(b, Observation):
        return (a.reader, a.frame, a.quantity) == (b.reader, b.frame, b.quantity)
    shared = log.closure(a.id) & log.closure(b.id)
    shared = {s for s in shared if s not in (a.id, b.id)}
    return bool(shared)


# ─────────────────────────────────────────────────────────────────────────────
# The declaration
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DecisionSpec:
    name: str
    quantity: str
    scope: Kind
    wants: Tuple[str, ...]
    reasons: Tuple[str, ...]
    mode: Mode
    margin_floor: Optional[float]
    excludes_tiers: Tuple[str, ...]
    revises: Optional[str]
    stub: bool
    fn: Callable[[Evidence], Optional[Ruling]]
    #: The quantity -- or quantities -- whose rows define this decision's
    #: DOMAIN. `None` means every subject at `scope`.
    #:
    #: ⚠️ A TUPLE IS NOT A CONVENIENCE. `duration` answers ONE question --
    #: how long is this event -- for two kinds of ink, a notehead and a rest,
    #: and "one quantity, one owner" is about the ANSWER, not about the
    #: evidence. Splitting it into `duration` and `rest_duration` would make
    #: every consumer ask twice for one fact and would let the two drift.
    #:
    #: ⚠️ This is not an optimisation. `Q.GLYPH_OWNER`'s domain is the
    #: CONTESTED population -- a glyph nobody disputes has nothing to
    #: arbitrate -- and adjudicating every detection would emit a verdict per
    #: glyph on a page that can carry 67,000 of them, burying the contests in
    #: their own no-ops. A decision that names its domain says what it is
    #: ABOUT.
    subjects_from: Optional[str] = None

    #: ⚠️ ROADMAP 3.4g. NARROWS `subjects_from` TO THE ROWS WHOSE DETECTOR
    #: CLASS STARTS WITH ONE OF THESE, case-insensitively, read off
    #: `row.value[0]` — the spelling every `Q.GLYPH_BOX` row uses.
    #:
    #: ⚠️⚠️ IT EXISTS BECAUSE THREE GATHERED FAMILIES HAVE NO QUANTITY OF
    #: THEIR OWN AND A DECISION MUST STILL BE ABLE TO NAME ITS DOMAIN.
    #: `gather_coverage.FAMILY_TO_Q` maps `ledger`, `accidental` and
    #: `arpeggiato` to `None`: their ink reaches the record as an anonymous
    #: `Q.GLYPH_BOX` and nothing else. A per-family refusal for them can
    #: therefore only declare `subjects_from=Q.GLYPH_BOX`, whose domain is
    #: EVERY detection on the page — 8,486 on four Litolff pages — so the
    #: decision would file an abstention per glyph and bury 1,878 ledger
    #: verdicts under 6,608 no-ops. That is the exact fault `subjects_from`'s
    #: own docstring names one field up, arriving by a different door.
    #:
    #: ⚠️ A DECLARED TUPLE OF PREFIXES, NOT A PREDICATE, so `inventory` can
    #: PRINT a decision's domain and a reader can check it against
    #: `class_aliases.vocabulary()` without running anything. A lambda would
    #: make the domain unreadable to every derived check at once.
    #:
    #: ⚠️ IT IS A NARROWING AND NEVER A WIDENING: with no `subjects_from` it
    #: is meaningless and `decision()` refuses it.
    subjects_classed: Tuple[str, ...] = ()

    #: Can this fact be checked with NO ground truth? See `Checkable`.
    checkable: Checkable = Checkable.UNCHECKABLE
    #: The SPECIFIC constraints, named. Never "consistency".
    checked_by: Tuple[str, ...] = ()
    #: ⚠️ What a FAILED check implicates -- the GROUP, not the culprit.
    #:
    #: A failed check is CERTAIN ABOUT THE GROUP AND SILENT ABOUT THE MEMBER.
    #: Nine eighths in a 4/4 bar proves an error; it does not say whether the
    #: meter, a duration, a spurious note or a missing one is wrong. A
    #: violated constraint must raise EVERY member's suspicion and must never
    #: condemn the cheapest member to change.
    #:
    #: ⚠️ The tree already honours this in the one place it is implemented:
    #: `_reconcile_measure_to_meter` refuses unless the corrected bar lands
    #: EXACTLY on the meter and the answer is UNIQUE -- i.e. it declines
    #: whenever more than one member could explain the failure.
    implicates: Tuple[str, ...] = ()
    #: What an unverifiable fact is COMPOSED FROM. ⚠️ Its reliability is its
    #: WEAKEST INPUT, not the sum of them: agreement among witnesses ADDS,
    #: composition takes the MINIMUM, because if any input of a composition is
    #: wrong the output is wrong.
    composed_from: Tuple[str, ...] = ()


REGISTRY: Dict[str, DecisionSpec] = {}


def decision(*, quantity: str, scope: Kind, wants: Sequence[str],
             reasons: Sequence[str], mode: Mode = Mode.ADDITIVE,
             margin_floor: Optional[float] = None,
             excludes_tiers: Sequence[str] = (),
             revises: Optional[str] = None,
             subjects_from: Optional[str] = None,
             subjects_classed: Sequence[str] = (),
             checkable: Checkable = Checkable.UNCHECKABLE,
             checked_by: Sequence[str] = (),
             implicates: Sequence[str] = (),
             composed_from: Sequence[str] = (),
             stub: bool = False):
    """Declare a decision.

    ⚠️ `wants` is not documentation. The harness resolves it, `Evidence`
    enforces it, and the difference between it and what the log held becomes
    `Verdict.missing` / `.declined` without the decision being consulted.

    ⚠️ `reasons` is a closed vocabulary per decision. The model is
    `propose_clef`'s `_note(exit_, **fields)` closure
    (`clef_correction.py:239-243`), which records which of its exits was taken
    -- `no_clef_anchor`, `already_in_effect`, `no_candidate_clefs`. It is the
    tree's cleanest existing "a decision declares its exit" primitive; this
    copies it rather than inventing a rival.

    `stub=True` DECLARES that this decision is not implemented yet. A stub is
    fine; a missing decision is not. It always abstains with
    ABSTAIN.NOT_IMPLEMENTED and is listed by `stubs()`.
    """
    Q.check(quantity, "quantity")
    if checkable in (Checkable.CHECKABLE, Checkable.MIXED):
        if not checked_by or not implicates:
            raise ValueError(
                f"{quantity} is declared {checkable.value} and must name both "
                f"`checked_by` (the SPECIFIC constraint, never 'consistency') "
                f"and `implicates` (the GROUP a failure raises suspicion on). "
                f"A check whose failure has no stated membership will convict "
                f"whichever member is cheapest to change.")
    if checkable in (Checkable.UNCHECKABLE, Checkable.MIXED):
        if not composed_from:
            raise ValueError(
                f"{quantity} is declared {checkable.value} and must name "
                f"`composed_from`: an unverifiable fact's reliability is its "
                f"WEAKEST INPUT, and a consumer cannot weigh it without "
                f"knowing what those are.")
    if subjects_classed and subjects_from is None:
        raise ValueError(
            f"{quantity} declares `subjects_classed` with no `subjects_from`. "
            f"It is a NARROWING of a domain and never a domain of its own: "
            f"without one, a reader would have to guess which quantity's rows "
            f"the class names are matched against.")
    if mode is Mode.COMPETITIVE and margin_floor is None:
        raise ValueError(
            f"a COMPETITIVE decision on {quantity} must declare a "
            f"margin_floor: it may overturn an incumbent, and an overturn "
            f"with no margin is an argmax with no floor -- which is exactly "
            f"what the clef does today.")

    def wrap(fn: Callable[[Evidence], Optional[Ruling]]) -> Callable:
        spec = DecisionSpec(
            name=fn.__name__, quantity=quantity, scope=scope,
            wants=tuple(wants), reasons=tuple(reasons) + (ABSTAIN.NOT_IMPLEMENTED,),
            mode=mode, margin_floor=margin_floor,
            excludes_tiers=tuple(excludes_tiers), revises=revises,
            stub=stub, fn=fn, subjects_from=subjects_from,
            subjects_classed=tuple(subjects_classed),
            checkable=checkable, checked_by=tuple(checked_by),
            implicates=tuple(implicates),
            composed_from=tuple(composed_from))
        if quantity in REGISTRY:
            raise ValueError(
                f"{quantity} already has an adjudicator "
                f"({REGISTRY[quantity].name}). One quantity, one owner.")
        REGISTRY[quantity] = spec
        fn.spec = spec  # type: ignore[attr-defined]
        return fn

    return wrap


def by_checkability() -> Dict[str, Tuple[str, ...]]:
    """The map of where self-correction is possible at all."""
    out: Dict[str, List[str]] = {c.value: [] for c in Checkable}
    for quantity, spec in REGISTRY.items():
        out[spec.checkable.value].append(quantity)
    return {k: tuple(sorted(v)) for k, v in out.items()}


def stubs() -> Tuple[str, ...]:
    """Every decision that is DECLARED not implemented."""
    return tuple(sorted(q for q, s in REGISTRY.items() if s.stub))


def is_relocated_copy(subject: Union[Subject, str],
                      owner_value: Optional[Any]) -> bool:
    """Does this glyph row name ANOTHER staff as its owner?

    ⚠️⚠️ WHY THAT MEANS "DROP IT" AND NOT "MOVE IT", WHICH IS THE WHOLE POINT.
    `adjudicate_glyph_owner` declares `subjects_from=Q.GLYPH_BAND_DISTANCE`,
    and `gather_ownership_evidence` files a band-distance row ONLY for a glyph
    that overlaps a SAME-CATEGORY glyph on ANOTHER staff (ROADMAP 2.6 moved
    that test from `smufl_name` to `category`, which is the frozen legacy
    predicate; it WIDENS the contested population and does not change this
    argument, because a twin is still there by construction). So a glyph with an
    ownership verdict naming a different staff has a TWIN on that staff BY
    CONSTRUCTION -- the contest is built from the pair. Relocating the copy
    therefore puts a second element on a staff that already holds one; it can
    never rescue ink that is only in the wrong cell, because such ink is
    UNCONTESTED and its verdict names its own staff (`reason="no_contest"`).

    ⚠️ THE CONTRAST WITH `arc_owner` IS EXACT AND IS WHY THIS IS NOT A GENERAL
    RULE ABOUT OWNERSHIP. That decision's domain is `subjects_from=Q.ARC_BOX`
    -- every arc, contested or not -- so it CAN move an arc onto a staff that
    detected nothing, and CLAUDE.md records six of its twelve moves doing
    exactly that. Applying this rule there would delete real arcs. It is a
    property of `glyph_owner`'s DOMAIN, not of ownership, and
    `test_staged_dedupe.py` asserts that domain off the registry so widening
    it goes red rather than silently making this unsafe.

    ⚠️ THE ONE WAY IT CAN LOSE INK is a SWAP -- every member of one contest
    naming somebody else, so every copy is dropped. Measured on Litolff
    Beethoven 5 p1-4: **1 of 636 contest groups, and it is a dynamic letter;
    zero noteheads.** It is not structurally impossible, only rare, so the
    drop is COUNTED and `probe/contest_groups.py` reports it. Making it
    impossible needs the twin SUBJECT on the record, which is a GATHER change
    -- see FINDINGS §6.
    """
    if not isinstance(owner_value, str) or not owner_value:
        return False
    sub = (subject if isinstance(subject, Subject)
           else Subject.from_key(str(subject)))
    own = sub.at(Kind.STAFF)
    return own is not None and own.to_key() != owner_value


# ─────────────────────────────────────────────────────────────────────────────
# Running a decision
# ─────────────────────────────────────────────────────────────────────────────


def adjudicate_one(log: Log, spec: DecisionSpec, subject: Subject) -> Verdict:
    """Run one decision on one subject and record the verdict.

    Everything the decision did not tell us is computed here.
    """
    ev = Evidence(log, subject, spec)

    if spec.stub:
        ruling = Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)
    else:
        ruling = spec.fn(ev)
        if ruling is None:
            ruling = Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)

    if ruling.reason not in spec.reasons:
        raise UndeclaredReason(
            f"{spec.name} returned reason {ruling.reason!r}, which is not in "
            f"its declared vocabulary {spec.reasons}.")

    # ── the margin floor ────────────────────────────────────────────────────
    #
    # ⚠️ A CONTEST TOO CLOSE TO CALL NOW *NARROWS* RATHER THAN VANISHING.
    # Before candidate sets this discarded the whole contest and reported
    # `margin_below_floor` with nothing attached -- so "the readers disagreed
    # between alto and tenor" and "nothing was read at all" arrived at the
    # consumer as the same answer. Where the decision supplied candidates they
    # survive; where it did not, the old abstention stands.
    value, reason, margin = ruling.value, ruling.reason, ruling.margin
    candidates = tuple(ruling.candidates)
    if (spec.mode is Mode.COMPETITIVE and value is not None
            and spec.margin_floor is not None):
        if margin is None or margin < spec.margin_floor:
            value = None
            reason = "margin_below_floor"

    if value is not None:
        outcome = Outcome.DECIDED
    elif len(candidates) >= 2:
        outcome = Outcome.NARROWED
    else:
        outcome = Outcome.ABSTAINED
        candidates = ()          # a single survivor is not a narrowing

    considered = tuple(dict.fromkeys(ev._seen))
    basis: Set[str] = set(considered)
    for rid in considered:
        basis |= log.closure(rid)

    prior = log.verdict(spec.quantity, subject) if spec.revises else None

    verdict = Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=spec.quantity,
        outcome=outcome, value=value, decider=spec.name, reason=reason,
        candidates=candidates,
        considered=considered,
        used=tuple(ruling.used),
        missing=tuple(sorted(ev._missing)),
        declined=tuple(sorted(ev._declined)),
        excluded=tuple(ev._excluded),
        correlated=ev.correlated_groups(),
        basis=tuple(sorted(basis)),
        margin=margin,
        supersedes=prior.id if prior is not None else None,
        detail=dict(ruling.detail),
    )
    return log.record(verdict)


#: The order decisions run in.
#:
#: ⚠️ ASSUMPTION (A-ORDER-1). Adjudication reads a FROZEN log, so this order
#: is free for measurements -- but a decision that consumes another decision's
#: VERDICT does depend on it having run. This list is the assumed dependency
#: order and is the single place to change it. It is an assumption, not a
#: measurement: see ASSUMPTIONS.md.
ORDER: Tuple[str, ...] = (
    # structure first -- everything else is addressed in terms of it
    Q.SYSTEM_MEMBERSHIP,
    Q.STAFF_GROUP,
    Q.MEASURE_PARTITION,
    Q.STAFF_ORDINAL,
    Q.SYSTEM_STAFF_COUNT,
    # ⚠️ IDENTITY BEFORE OWNERSHIP AND BEFORE THE CLEF. That inversion is the
    # whole point of the split (A-ORDER-2): today the instrument arrives 647
    # lines AFTER the note, so ownership's strongest tier (the instrument's
    # written range) is unavailable when ownership runs, and the clef's is too.
    Q.INSTRUMENT,
    Q.SLOT_INDEX,
    Q.PART_PARTITION,
    Q.GROUP_SYMBOL,
    # now the header facts, with identity in hand
    Q.CLEF,
    # ⚠️ BEFORE `Q.KEY_SIGNATURE`, AND THE ORDER IS THE WHOLE REASON THERE IS
    # NO CYCLE. `adjudicate_system_key` reads its staves' MARKER AND FIT ROWS
    # through `_staff_reading`, never their key VERDICTS, so `Q.KEY_SIGNATURE`
    # is nowhere in its ancestry and the staff decision may read it back as an
    # ancestor fact. The reverse order -- tally the verdicts, then revise them
    # -- is the fixpoint `Log.record` refuses, and it is also the majority
    # this item deliberately did not build.
    Q.SYSTEM_KEY,
    Q.KEY_SIGNATURE,
    # ⚠️ ROADMAP 2.4a. BEFORE OWNERSHIP, so a box `glyph_owner` is about to
    # arbitrate has already been asked whether it is a notehead at all --
    # the same "a question about what a thing IS cannot honestly be settled
    # after the questions that assume the answer" this file states for
    # `Q.NOTEHEAD_IS_A_WHOLE_REST`. ⚠️ NOT A FULL FIX: `glyph_owner`'s own
    # scoring does not read this verdict (see the adjudicator's own
    # docstring), so the ordering guarantees a refused glyph is never WRITTEN
    # but does not yet guarantee it cannot WIN a contest against a genuine
    # partner. Measured, not assumed -- see the 2.4a report.
    # ⚠️ ROADMAP 3.4g. THE LEDGER GOES BEFORE THE NOTEHEAD, AND THE ORDER IS A
    # DEPENDENCY RATHER THAN A PREFERENCE: `notehead_precision.
    # _ledger_rungs_in_cell` reads this decision's VERDICT so a refused rung
    # is not counted in ADJUDICATE's own ladder search. The reverse order
    # would let a staff-line fragment vouch for a note.
    Q.LEDGER_IS_NOT_A_LEDGER,
    Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
    # ⚠️ THE OTHER FIVE FAMILIES DEPEND ON NOTHING AND NOTHING IN ADJUDICATE
    # DEPENDS ON THEM EXCEPT `Q.DYNAMIC`, which must not spell a refused
    # letter into a word — so they stand here, beside the two refusals that
    # do have an order, and before every consumer of theirs.
    Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL,
    Q.REST_IS_NOT_A_REST,
    Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO,
    Q.ARC_IS_NOT_AN_ARC,
    Q.DYNAMIC_IS_NOT_A_DYNAMIC,
    Q.ARTICULATION_IS_NOT_AN_ARTICULATION,
    # ownership, with identity and clef available
    Q.GLYPH_OWNER,
    Q.ARC_OWNER,
    Q.ARC_KIND,
    Q.ARTICULATION_OWNER,
    # ⚠️ BESIDE THE ARTICULATION AND NOT AFTER THE RHYTHM. A fermata's
    # carriers are noteheads and RESTS, both of which are GATHER rows
    # (`Q.GLYPH_BOX`), so this needs no verdict of any kind -- putting it
    # after `Q.EVENT` would imply a dependency it does not have.
    Q.FERMATA_OWNER,
    # ⚠️ Beside the fermata and the articulation, and for the same
    # reason: its carriers are `Q.GLYPH_BOX` rows, so it needs no
    # verdict of any kind.
    Q.ORNAMENT_OWNER,
    # rhythm
    # ⚠️ TUPLET BEFORE DURATION. `adjudicate_duration` reads the tuplet
    # verdict to scale its beats, so a tuplet decided afterwards would arrive
    # too late and every triplet would export at its written value -- the
    # exact fault the ratio exists to fix. Found by wiring them, not by
    # reasoning: the ORDER list had them the other way round.
    # ⚠️ STEM DIRECTION BEFORE THE EVENTS, because the divisi guard in
    # `group_chords_in_measure` is what the events are grouped UNDER: a
    # real chord shares one physical stem, so two heads at one x whose
    # stems point opposite ways are two voices and not one chord. Decided
    # afterwards it would arrive too late to separate them, which is the
    # `TUPLET_RATIO` before `DURATION` lesson in a second family.
    Q.STEM_DIRECTION,
    # ⚠️ BEFORE THE DURATION AND THE EVENTS, though nothing in ADJUDICATE reads
    # its verdict today: this asks whether a glyph is a notehead AT ALL, and a
    # question about what a thing IS cannot honestly be settled after the
    # questions that assume the answer. Filed here so the first consumer that
    # wants it -- a bar sum that should not count this ink, an event grouping
    # that should not admit it -- finds it already decided rather than having
    # to move it and rediscover `wedge_anchor`'s ORDER fault.
    Q.NOTEHEAD_IS_A_WHOLE_REST,
    Q.TUPLET_RATIO,
    Q.DURATION,
    # ⚠️ EVENTS BEFORE THE METER, and it is the bar sum that forces it. A bar
    # is summed over EVENTS, not over noteheads -- a chord's members sound
    # together and advance time once -- so anything that checks a bar against
    # a meter needs this first. Until 2026-09-09 the grouping existed ONLY in
    # `export._events`, at serialisation time, so every stage before EXPORT
    # counted each chord member as a separate event.
    Q.EVENT,
    # ⚠️ AFTER `EVENT`, because a voice is a stream OF events -- and it
    # calls `voicing.split_events_into_voices` rather than restating the
    # rule, so the staged and legacy paths cannot come to disagree about
    # a file's `<backup>` arithmetic.
    Q.VOICES,
    # ⚠️ AFTER `EVENT`, because it consumes that verdict rather than
    # re-clustering the glyphs: within-staff simultaneity is decided per
    # cell, and this groups those decisions across the staves of one
    # system. Answering the same question twice would let the two
    # answers disagree.
    Q.ONSET_COLUMN,
    # ⚠️⚠️ AFTER `VOICES`, AND IT SAT BESIDE THE FERMATA UNTIL THE INVENTORY
    # SAID OTHERWISE. Both ends of a hairpin must come from ONE voice --
    # MusicXML pairs a wedge within a `<voice>` stream, so a start in voice 1
    # closed by a stop in voice 2 leaves both ends unpaired and the file
    # malformed rather than merely wrong. Placed with the other glyph-owner
    # decisions it ran BEFORE `Q.VOICES` was decided and read None every time:
    # a declared input that could never answer, which is the fault
    # `arc_owner`'s frame bug and `Q.STEM`'s 916 unread rows are both
    # instances of. Caught in one line by `inventory --check`, which knows the
    # ORDER and the `wants` and compares them -- not by review, and not by any
    # test, because "one voice" and "voices unknown" produce the SAME ANSWER
    # on every page that has only one voice.
    Q.WEDGE_ANCHOR,
    Q.METER,
    # text
    Q.DYNAMIC,
    Q.DIRECTION,
)


def domain_of(spec: DecisionSpec) -> Tuple[str, ...]:
    """`subjects_from` as a tuple, whichever form it was declared in."""
    d = spec.subjects_from
    if d is None:
        return ()
    return (d,) if isinstance(d, str) else tuple(d)


def subjects_for(log: Log, spec: DecisionSpec) -> Tuple[Subject, ...]:
    """The subjects this decision is ABOUT.

    With `subjects_from`, only subjects carrying a row of that quantity --
    which for ownership is the contested population and nothing else, and for
    `duration` is every notehead AND every rest.
    """
    wanted = domain_of(spec)
    if not wanted:
        return log.subjects(spec.scope)
    # ⚠️ ROADMAP 3.4g. A CLASS NARROWING IS APPLIED TO THE ROW, NOT TO THE
    # SUBJECT, because a subject can carry several rows and it is the one
    # naming the family that puts it in this decision's domain.
    classes = tuple(c.lower() for c in spec.subjects_classed)
    out = {}
    for row in log.all_rows():
        if getattr(row, "quantity", None) not in wanted:
            continue
        if classes:
            v = getattr(row, "value", None)
            # ⚠️ AN ABSTENTION HAS NO VALUE AND THEREFORE NO CLASS, so it
            # cannot put a subject in a class-narrowed domain. Admitting it
            # would hand the decision a subject it can say nothing about and
            # file an abstention that means only "the row we filtered on was
            # itself an abstention".
            if not (isinstance(v, (list, tuple)) and v
                    and str(v[0]).lower().startswith(classes)):
                continue
        sub = row.subject.at(spec.scope)
        if sub is not None:
            out[sub.to_key()] = sub
    return tuple(sorted(out.values()))


class NoDecisionsRegistered(RuntimeError):
    """ADJUDICATE was asked to run with an empty registry.

    ⚠️ An error rather than an empty result, for the same reason
    `evaluate.NoRulesRegistered` is: a stage that produces no verdicts because
    nothing was loaded is indistinguishable from one that produced no verdicts
    because it had nothing to decide.
    """


def _ensure_decisions() -> None:
    if not REGISTRY:
        from . import adjudicators  # noqa: F401
    if not REGISTRY:
        raise NoDecisionsRegistered(
            "ADJUDICATE has no decisions. An empty stage is not an empty "
            "result.")


def run(log: Log, *, order: Sequence[str] = ORDER,
        progress: bool = False) -> List[Verdict]:
    """Run every registered decision, in `order`, over every subject.

    The log is frozen first: ADJUDICATE may not gather.
    """
    _ensure_decisions()
    if not log.frozen:
        log.freeze()
    out: List[Verdict] = []
    for quantity in order:
        spec = REGISTRY.get(quantity)
        if spec is None:
            continue
        for subject in subjects_for(log, spec):
            out.append(adjudicate_one(log, spec, subject))
        if progress:
            print(f"  adjudicate {quantity}: {len(out)} verdicts so far")
    return out
