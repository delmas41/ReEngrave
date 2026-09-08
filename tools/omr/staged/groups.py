"""REDUNDANT GROUPS — several witnesses to ONE fact, and whether they agree.

⚠️ WHY THIS EXISTS, AND WHY IT COMES BEFORE MORE DECISIONS.

Nothing anywhere in this codebase says *"these N rows are witnesses to ONE
fact, and here is whether they agree."* The tree has three ad-hoc instances of
the idea (`key_signature_corroboration`'s `MIN_WITNESSES = 2`,
`rhythm._dominant_detected_meter`'s one-vote-per-staff, `key_signature_vote`'s
cross-system reconcile) and each one re-invents the machinery inside itself,
so none of them is queryable and none of them generalises.

**Agreement among witnesses is the only correctness signal available with no
ground truth.** The score library pairs a PDF with a reference encoding for
**27 of 235 held editions**, and Sean's stated primary input is scanned
orchestral scores from IMSLP — so for the overwhelming majority of real work
there is no truth file and never will be. A page that prints a fact more than
once is the page checking itself.

⚠️⚠️ THE PROPERTY THAT MATTERS MOST, AND THE ONE EASIEST TO BREAK.

    A FAILED CHECK IS CERTAIN ABOUT THE GROUP AND SILENT ABOUT THE MEMBER.

Nine eighths in a 4/4 bar proves an error without naming which symbol — it
could be the meter, a duration, a spurious note, a missing one, or a mis-owned
glyph. So `Group.suspects` is **every witness, including the majority's**, and
there is deliberately no `culprit`, no `correct_value` and no `repair` field
anywhere in this module. A disagreeing group raises every member's suspicion;
it never convicts the cheapest member to change.

The tree already honours this in the one place it is implemented:
`_reconcile_measure_to_meter` repairs only when the answer is UNIQUE — i.e. it
declines exactly when more than one member could explain the failure.

⚠️ THE INDEPENDENCE RULE, NOW MECHANICALLY ENFORCEABLE.

*Two signals sharing an ancestor are ONE signal, not corroboration.* Until
`Verdict.basis` carried the ancestor closure that was a principle applied by
hand. It is now a set operation, and it is not decoration: the header clef
pre-pass and the measure-pass clef argmax LOOK like two readings and are
measured to be the same call on the same list object — divergent on exactly
**0 of 396 staves**. Counting them as agreement would have produced a
healthy-looking **77% agreement rate carrying no information**. A group whose
witnesses collapse to one signal reports `SINGLE`, never `UNANIMOUS`, and
`Group.uninformative` is True.

⚠️ WHAT IS REDUNDANT IS AN *ASPECT*, NOT A QUANTITY — and getting that wrong
is how you break real music.

`key_signature_corroboration` had to work this out the hard way and its
finding is the reason `Redundancy.aspect` is a required field:

    A meter change is corroborated by other staves reading THE SAME METER,
    because a meter is one fact shared by the system. A key signature is not:
    transposing instruments genuinely carry different keys at the same bar, so
    "the other staves read something else" is not evidence of anything. What
    DOES transplant is the POSITION — a key change is printed at one bar of
    one system on every staff; the VALUE differs per transposition, the BAR
    does not.

So `Redundancy.reading` is not a formatting helper. **It names the aspect that
is genuinely printed more than once**, and a wrong `reading` manufactures
disagreement out of correct engraving.

⚠️ THIS MODULE HAS NO CONSUMER TODAY, AND THAT IS DELIBERATE.

Building the ability to SEE that witnesses disagree is this task; deciding
what to *do* about a disagreement is a later, separate call. The named
consumer is the implication-test layer (ASSUMPTIONS D4). Recorded here rather
than left implicit because "computed, kept, consumed by nobody" is a fault
class this project has paid for — the five internal-consistency checks fire
**85 warnings on one real document and every one is inert**. The difference
between that and this is that this one says so, in its own docstring, with the
consumer named.

⚠️ AND NOTHING HERE HAS BEEN MEASURED. No arm has been run. Every declaration
below is an assumption; see ASSUMPTIONS.md `A-GROUPS-*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (Any, Callable, Dict, FrozenSet, List, Optional, Sequence,
                    Set, Tuple)

from .record import (Kind, Log, Observation, Outcome, Q, Row, Subject, Verdict)


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ REFUSED REDUNDANCIES — things that LOOK printed twice and are not
#
# Each of these is a group somebody will otherwise declare, because the shape
# is so nearly right. An unrecorded refusal gets re-tried.
#
#   key signature across the STAVES OF ONE SYSTEM
#       REFUSED. Transposing instruments genuinely carry different written
#       keys at the same bar — a B-flat clarinet in a 3-flat movement is
#       stored `fifths: -1` — so disagreement here is correct engraving.
#       `key_signature_corroboration` states it outright: "the other staves
#       read something else" is not evidence of anything. What IS redundant
#       across a system is the POSITION of a key CHANGE, not its value; that
#       needs a mid-staff change to be a row and none is emitted yet.
#
#   staff count across the SYSTEMS OF A PAGE
#       REFUSED. A printed score suppresses tacet staves — the Beethoven 5
#       scan reads 11 staves then 8 on one page — and `export._stitch_slots`
#       refuses the ordinal join for exactly this reason. Two systems with
#       different staff counts are not two witnesses to one lineup; they are
#       two different lineups.
#
#   the same GLYPH detected in two overlapping measure cells
#       REFUSED, and it is the sharpest case. A cross-staff duplicate is ONE
#       piece of ink read twice, which is the definition of one signal — it is
#       an OWNERSHIP contest (`adjudicate_glyph_owner`), not corroboration.
#       Counting it as two witnesses would turn every padded cell overlap into
#       manufactured agreement.
#
#   two READERS on one crop, joined into one group
#       NOT REFUSED, NOT DECLARED — deferred, because it needs a reading
#       function that maps both readers' value shapes onto one aspect, and for
#       the meter those shapes are a SMuFL name (`timeSig4`) and a pair
#       (4, 4). Joining them is a DECISION, not a group. Parked as D17.
# ─────────────────────────────────────────────────────────────────────────────


class Agreement(str, Enum):
    """What a group of witnesses came to.

    ⚠️ FIVE states, and the two that a naive `all(x == y)` collapses are the
    ones that matter:

      * `SINGLE` is not agreement. One witness agrees with itself, and so do
        several witnesses that are really one signal. This is where the 77%
        rate carrying no information would have landed.
      * `NONE` is not disagreement. No witness spoke at all — a page that
        prints no meter is the COMMON case, not a failure.
    """

    NONE = "none"            # no witness produced a reading
    SINGLE = "single"        # exactly one INDEPENDENT signal — not agreement
    UNANIMOUS = "unanimous"  # >= 2 independent signals, all the same reading
    MAJORITY = "majority"    # a strict plurality, with named dissenters
    SPLIT = "split"          # no plurality — the whole group is in question


#: The two outcomes a human or a later consumer should look at.
DISAGREEING: Tuple[Agreement, ...] = (Agreement.MAJORITY, Agreement.SPLIT)


@dataclass(frozen=True)
class Witness:
    """One row testifying to one fact."""

    row_id: str
    subject: Subject
    reading: Any
    #: Which signal class this row belongs to. Rows sharing a signal are ONE
    #: witness however many rows they are.
    signal: int

    def to_json(self) -> dict:
        return {"row": self.row_id, "subject": self.subject.to_key(),
                "reading": self.reading, "signal": self.signal}


@dataclass(frozen=True)
class Group:
    """N witnesses to one fact, and whether they agree.

    ⚠️ THERE IS NO `culprit` FIELD AND THERE MUST NEVER BE ONE. `suspects` is
    every witness row, majority included. A consumer that wants to know which
    member is wrong is asking a question this evidence cannot answer, and the
    answer it would invent is "whichever is cheapest to change".
    """

    redundancy: str
    fact: str
    agreement: Agreement
    witnesses: Tuple[Witness, ...]
    #: reading -> the row ids voting for it, ordered by vote count, best first.
    readings: Tuple[Tuple[Any, Tuple[str, ...]], ...]
    #: How many INDEPENDENT signals the witnesses amount to.
    n_signals: int
    #: Rows whose signal did not vote for the plurality reading.
    #: ⚠️ EMPTY ON A SPLIT, on purpose: with no plurality nobody is the
    #: dissenter and everybody is a suspect.
    dissenting: Tuple[str, ...]
    #: Signal classes whose own rows disagree with each other — one reader,
    #: one crop, two answers. They vote for nothing.
    internally_split: Tuple[Tuple[str, ...], ...]
    #: ⚠️ EVERY witness row, including the majority's. This is the whole
    #: point: a failed check implicates the GROUP.
    suspects: Tuple[str, ...]
    #: The quantities a disagreement raises suspicion on.
    implicates: Tuple[str, ...]
    #: Subjects in this fact's reach that produced NO reading, with why.
    #: Absence is a value: a staff that abstained is not a staff that agreed.
    silent: Tuple[Tuple[str, str], ...] = ()
    #: ⚠️ Prose, present only where witnesses may legitimately differ — a
    #: clef genuinely changes mid-part. Without this a legal change reads as
    #: an error.
    legitimate_difference: Optional[str] = None

    @property
    def uninformative(self) -> bool:
        """True when this group cannot corroborate anything.

        Fewer than two independent signals. ⚠️ Read this before reading
        `agreement`: a page of `UNANIMOUS` groups that are all uninformative
        is a page that checked nothing.
        """
        return self.n_signals < 2

    @property
    def disagrees(self) -> bool:
        return self.agreement in DISAGREEING

    def to_json(self) -> dict:
        return {
            "redundancy": self.redundancy, "fact": self.fact,
            "agreement": self.agreement.value,
            "n_witnesses": len(self.witnesses), "n_signals": self.n_signals,
            "uninformative": self.uninformative,
            "readings": [{"reading": r, "rows": list(ids)}
                         for r, ids in self.readings],
            "witnesses": [w.to_json() for w in self.witnesses],
            "dissenting": list(self.dissenting),
            "internally_split": [list(g) for g in self.internally_split],
            "suspects": list(self.suspects),
            "implicates": list(self.implicates),
            "silent": [list(s) for s in self.silent],
            "legitimate_difference": self.legitimate_difference,
        }


# ─────────────────────────────────────────────────────────────────────────────
# The declaration
# ─────────────────────────────────────────────────────────────────────────────


class Source(str, Enum):
    """Which kind of row testifies."""

    OBSERVATION = "observation"   # readers, straight off the page
    VERDICT = "verdict"           # adjudicated facts


@dataclass(frozen=True)
class Redundancy:
    """A declaration that one fact is printed more than once.

    ⚠️ `why` and `aspect` are REQUIRED PROSE and are checked for substance,
    on the model of `evaluate.rule`'s `bound`. A redundancy that cannot say
    *why the page prints this twice* has not been thought through, and a
    redundancy that cannot name *which aspect* is the redundant one is the
    key-signature trap waiting to happen.
    """

    name: str
    quantity: str
    source: Source
    #: The scope each witness lives at.
    witness_scope: Kind
    #: row -> a hashable naming the ONE FACT it witnesses, or None if this row
    #: cannot be placed (recorded as unplaced, never silently dropped).
    fact_key: Callable[[Log, Row], Any]
    #: row -> the redundant ASPECT, hashable, or None for "nothing to say".
    reading: Callable[[Log, Row], Any]
    #: Why the page prints this fact more than once. PROSE.
    why: str
    #: WHICH aspect is redundant, as against which merely looks it. PROSE.
    aspect: str
    #: What a disagreement raises suspicion on. Must include `quantity`.
    implicates: Tuple[str, ...]
    #: Prose, where witnesses may legitimately differ.
    legitimate_difference: Optional[str] = None


REDUNDANCIES: List[Redundancy] = []


def redundancy(*, name: str, quantity: str, source: Source,
               witness_scope: Kind,
               fact_key: Callable[[Log, Row], Any],
               reading: Callable[[Log, Row], Any],
               why: str, aspect: str,
               implicates: Sequence[str],
               legitimate_difference: Optional[str] = None) -> Redundancy:
    """Declare a redundant group. Registers and returns it."""
    Q.check(quantity, "quantity")
    for q in implicates:
        Q.check(q, "quantity")
    if quantity not in implicates:
        raise ValueError(
            f"redundancy {name!r} must implicate {quantity} ITSELF. A check "
            f"that implicates only OTHER facts has quietly decided the fact "
            f"under test is innocent.")
    if len(why.strip()) < 40:
        raise ValueError(
            f"redundancy {name!r} must say WHY the page prints this fact more "
            f"than once. A group with no stated reason is an assumption "
            f"wearing a mechanism's clothes.")
    if len(aspect.strip()) < 40:
        raise ValueError(
            f"redundancy {name!r} must name WHICH ASPECT is redundant. The "
            f"key signature is printed on every staff of a system and is NOT "
            f"redundant across them, because transposing instruments differ; "
            f"only its change POSITION is. Say which one this is.")
    if any(r.name == name for r in REDUNDANCIES):
        raise ValueError(f"redundancy {name!r} is already declared")
    r = Redundancy(name=name, quantity=quantity, source=source,
                   witness_scope=witness_scope, fact_key=fact_key,
                   reading=reading, why=why, aspect=aspect,
                   implicates=tuple(implicates),
                   legitimate_difference=legitimate_difference)
    REDUNDANCIES.append(r)
    return r


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ Independence — and why this is NOT `adjudicate._one_signal`
# ─────────────────────────────────────────────────────────────────────────────


def one_signal(log: Log, a: Row, b: Row) -> bool:
    """True when two rows are ONE signal wearing two hats.

    ⚠️ THIS IS SUBJECT-AWARE AND `adjudicate._one_signal` IS NOT, and the
    difference is load-bearing HERE and inert THERE.

    `adjudicate._one_signal` calls two Observations one signal when
    `(reader, frame, quantity)` match. A decision's evidence is almost always
    about ONE subject, so that reads as "the same reader on the same crop" and
    is right. A REDUNDANT GROUP is the opposite case by construction: its
    witnesses are twelve different staves, all read by the same reader on the
    same KIND of crop, so `frame` matches for all twelve — and the
    adjudicate rule would collapse an entire system's meter vote to one
    witness.

    So `subject` joins the key. Two rows are one signal when

      * the same reader read the same subject in the same frame for the same
        quantity (literally one reading, recorded twice), or
      * their provenance closures intersect ABOVE the raster — which is how an
        external document's two descendants are caught, and is the whole
        reason `Observation.derived_from` exists.

    ⚠️ THE CASE THIS CANNOT SEE YET, and it will matter the moment it exists:
    `READERS.CARRY` is declared ("this fact, read on another system") and
    nothing emits it. A carried reading IS the other system's reading, so a
    carry row that does not name its origin in `derived_from` will be counted
    as an independent witness and manufacture unanimity. Whoever wires the
    carry: it must be `derived_from` the row it carries.
    """
    if isinstance(a, Observation) and isinstance(b, Observation):
        if (a.subject == b.subject
                and (a.reader, a.frame, a.quantity)
                == (b.reader, b.frame, b.quantity)):
            return True
    shared = log.closure(a.id) & log.closure(b.id)
    shared -= {a.id, b.id}
    return bool(shared)


def _signal_classes(log: Log, rows: Sequence[Row]) -> List[List[int]]:
    """Partition row indices into signal classes (a union-find by pairs)."""
    parent = list(range(len(rows)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if one_signal(log, rows[i], rows[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    buckets: Dict[int, List[int]] = {}
    for i in range(len(rows)):
        buckets.setdefault(find(i), []).append(i)
    return [buckets[k] for k in sorted(buckets)]


# ─────────────────────────────────────────────────────────────────────────────
# Assessing one redundancy
# ─────────────────────────────────────────────────────────────────────────────


def _candidate_rows(log: Log, red: Redundancy) -> Tuple[List[Row], List[Tuple[str, str]]]:
    """Every row that could witness, and every subject that stayed silent.

    ⚠️ Silence is recorded, not dropped. A staff whose reader ABSTAINED and a
    staff nobody looked at are different, and a staff that agreed is a third
    thing — collapsing them is the exact fault `record.State` exists for.
    """
    rows: List[Row] = []
    silent: List[Tuple[str, str]] = []

    if red.source is Source.OBSERVATION:
        for row in log.all_rows():
            if not isinstance(row, Observation):
                continue
            if row.quantity != red.quantity:
                continue
            if row.subject.kind is not red.witness_scope:
                continue
            rows.append(row)
        seen = {r.subject.to_key() for r in rows}
        for sub in log.subjects(red.witness_scope):
            if sub.to_key() in seen:
                continue
            state = log.state(red.quantity, sub)
            silent.append((sub.to_key(), state.value))
        return rows, silent

    for sub in log.subjects(red.witness_scope):
        v = log.verdict(red.quantity, sub)
        if v is None:
            silent.append((sub.to_key(), "absent"))
        elif v.outcome is Outcome.DECIDED:
            rows.append(v)
        else:
            # ⚠️ A NARROWED verdict is not a witness — it holds two answers,
            # so it can neither agree nor dissent — but it is very much not
            # nothing, and its outcome is recorded so a reader can tell it
            # from an abstention.
            silent.append((sub.to_key(), v.outcome.value + ":" + v.reason))
    return rows, silent


def assess(log: Log, red: Redundancy) -> Tuple[Group, ...]:
    """Every group this redundancy finds in the log."""
    rows, silent_all = _candidate_rows(log, red)

    by_fact: Dict[Any, List[Row]] = {}
    unplaced: List[Row] = []
    for row in rows:
        key = red.fact_key(log, row)
        if key is None:
            unplaced.append(row)
            continue
        by_fact.setdefault(key, []).append(row)

    # A silent subject belongs to whichever fact its own key names, but a
    # silent row has no reading to key on, so it is reported per redundancy
    # rather than per fact where the key cannot be derived without one.
    silent_by_fact: Dict[Any, List[Tuple[str, str]]] = {}
    for subject_key, why in silent_all:
        sub = Subject.from_key(subject_key)
        key = _silent_fact_key(log, red, sub)
        silent_by_fact.setdefault(key, []).append((subject_key, why))

    # ⚠️ A fact whose every member stayed silent still gets a group. The
    # union is the point: a system that prints no meter must appear as an
    # explicit NONE, not as an absence in a table of facts that spoke.
    keys = set(by_fact) | {k for k in silent_by_fact if k is not None}
    out: List[Group] = []
    for key in sorted(keys, key=repr):
        out.append(_one_group(log, red, key, by_fact.get(key, []),
                              tuple(sorted(silent_by_fact.get(key, ())))))
    orphan_silent = tuple(sorted(silent_by_fact.get(None, ())))
    if unplaced or orphan_silent:
        out.append(_unplaced_group(red, unplaced, orphan_silent))
    return tuple(out)


def _silent_fact_key(log: Log, red: Redundancy, sub: Subject) -> Any:
    """Best-effort fact key for a subject that produced no row.

    ⚠️ Deliberately best-effort and deliberately not clever. Where the key is
    plain containment we can place a silent subject exactly; where the key
    needs a reading the subject did not produce (a slot it never got), we
    cannot, and it is filed under `None` rather than guessed into a group it
    might not belong to.
    """
    try:
        return red.fact_key(log, _PhantomRow(sub))
    except Exception:                                          # noqa: BLE001
        return None


class _PhantomRow:
    """A stand-in carrying only a subject, for keying a silent subject.

    Any `fact_key` needing more than the subject will raise on it, which is
    caught and filed as unplaceable — never guessed.
    """

    __slots__ = ("subject", "id", "quantity", "value", "detail")

    def __init__(self, subject: Subject) -> None:
        self.subject = subject
        self.id = "phantom"
        self.quantity = ""
        self.value = None
        self.detail = {}


def _one_group(log: Log, red: Redundancy, key: Any, rows: List[Row],
               silent: Tuple[Tuple[str, str], ...]) -> Group:
    readings = [red.reading(log, r) for r in rows]
    live = [(r, v) for r, v in zip(rows, readings) if v is not None]
    mute = [r for r, v in zip(rows, readings) if v is None]

    silent = tuple(sorted(silent + tuple(
        (r.subject.to_key(), "no_reading") for r in mute)))

    live_rows = [r for r, _v in live]
    classes = _signal_classes(log, live_rows)

    witnesses: List[Witness] = []
    for n, members in enumerate(classes):
        for i in members:
            witnesses.append(Witness(live_rows[i].id, live_rows[i].subject,
                                     live[i][1], n))

    votes: Dict[Any, List[str]] = {}
    split_classes: List[Tuple[str, ...]] = []
    n_voting = 0
    for members in classes:
        vals = {live[i][1] for i in members}
        ids = tuple(live_rows[i].id for i in members)
        if len(vals) != 1:
            split_classes.append(ids)
            continue
        n_voting += 1
        votes.setdefault(next(iter(vals)), []).extend(ids)

    ordered = tuple(sorted(votes.items(),
                           key=lambda kv: (-_class_count(kv[1], classes,
                                                         live_rows),
                                           repr(kv[0]))))
    readings_out = tuple((r, tuple(ids)) for r, ids in ordered)

    agreement, dissenting = _verdict_on(classes, live_rows, ordered,
                                        n_voting, split_classes)

    return Group(
        redundancy=red.name, fact=_fact_str(key), agreement=agreement,
        witnesses=tuple(witnesses), readings=readings_out,
        n_signals=len(classes), dissenting=dissenting,
        internally_split=tuple(split_classes),
        suspects=tuple(w.row_id for w in witnesses),
        implicates=red.implicates, silent=silent,
        legitimate_difference=red.legitimate_difference)


def _class_count(ids: Sequence[str], classes: Sequence[Sequence[int]],
                 rows: Sequence[Row]) -> int:
    """How many SIGNAL CLASSES those row ids span — the vote unit."""
    idx = {r.id: i for i, r in enumerate(rows)}
    spanned = set()
    for n, members in enumerate(classes):
        if any(rows[i].id in ids for i in members):
            spanned.add(n)
    return len(spanned)


def _verdict_on(classes, live_rows, ordered, n_voting, split_classes):
    """⚠️ The vote unit is the SIGNAL CLASS, never the row.

    Twelve staves read by one reader are twelve signals; two rows recording
    one reading twice are one. And a class whose own rows disagree votes for
    NOTHING — it is evidence of disagreement, not of either value.
    """
    if not live_rows:
        return Agreement.NONE, ()
    if n_voting == 0:
        # Every class disagreed with itself. There is a reading here and no
        # coherent one, which is a SPLIT and not an absence.
        return Agreement.SPLIT, ()
    if n_voting == 1:
        # ⚠️ One coherent signal. If another class contradicted itself the
        # group is still in disagreement, so it may not report SINGLE.
        return (Agreement.SPLIT if split_classes else Agreement.SINGLE), ()
    if len(ordered) == 1 and not split_classes:
        return Agreement.UNANIMOUS, ()

    top = _class_count(ordered[0][1], classes, live_rows)
    runner = (_class_count(ordered[1][1], classes, live_rows)
              if len(ordered) > 1 else 0)
    if top <= runner:
        # ⚠️ NO PLURALITY. `dissenting` stays EMPTY: with the group evenly
        # divided nobody is the odd one out, and naming a side would be
        # exactly the "convict the cheapest member" move this refuses.
        return Agreement.SPLIT, ()

    dissent = [rid for _r, ids in ordered[1:] for rid in ids]
    dissent += [rid for grp in split_classes for rid in grp]
    return Agreement.MAJORITY, tuple(sorted(dissent))


def _unplaced_group(red: Redundancy, rows: Sequence[Row],
                    silent: Tuple[Tuple[str, str], ...] = ()) -> Group:
    """Rows and silent subjects the declaration could not attach to any fact.

    ⚠️ A group of its own rather than a silent drop. A redundancy that places
    nothing is a redundancy whose key is wrong, and the only way to see that
    is to count what it failed to place. A staff with no slot verdict lands
    here rather than being guessed into a part.
    """
    return Group(redundancy=red.name, fact="<unplaced>",
                 agreement=Agreement.NONE,
                 witnesses=tuple(Witness(r.id, r.subject, None, -1)
                                 for r in rows),
                 readings=(), n_signals=0, dissenting=(),
                 internally_split=(), suspects=tuple(r.id for r in rows),
                 implicates=red.implicates, silent=silent,
                 legitimate_difference=None)


def _fact_str(key: Any) -> str:
    if isinstance(key, Subject):
        return key.to_key()
    if isinstance(key, tuple):
        return "|".join(_fact_str(k) for k in key)
    return str(key)


# ─────────────────────────────────────────────────────────────────────────────
# The report
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GroupReport:
    groups: Tuple[Group, ...]

    def by_redundancy(self) -> Dict[str, Tuple[Group, ...]]:
        out: Dict[str, List[Group]] = {r.name: [] for r in REDUNDANCIES}
        for g in self.groups:
            out.setdefault(g.redundancy, []).append(g)
        return {k: tuple(v) for k, v in out.items()}

    def disagreements(self) -> Tuple[Group, ...]:
        return tuple(g for g in self.groups if g.disagrees)

    def to_json(self) -> dict:
        per: Dict[str, dict] = {}
        for name, groups in self.by_redundancy().items():
            counts: Dict[str, int] = {a.value: 0 for a in Agreement}
            for g in groups:
                counts[g.agreement.value] += 1
            per[name] = {
                "n_facts": len(groups),
                "n_witnesses": sum(len(g.witnesses) for g in groups),
                "agreement": counts,
                # ⚠️ Reported beside the agreement counts on purpose. A wall of
                # UNANIMOUS that is entirely uninformative checked nothing, and
                # a single number would hide which one you have.
                "uninformative": sum(1 for g in groups if g.uninformative),
            }
        return {
            "per_redundancy": per,
            # ⚠️ THREE KINDS OF ZERO, REPORTED APART. A zero is a suspect,
            # not a result -- seven-plus probes in this project have printed
            # clean tables of zeros at exit 0 -- and these three have
            # different causes and different fixes.
            #
            #   declared_but_empty  the declaration placed NO FACT. Its
            #                       fact_key is wrong, or the quantity is
            #                       never emitted. A bug in the declaration.
            #   witnessed_by_nobody facts exist and NOT ONE witness spoke.
            #                       The readers are silent, not the
            #                       declaration. A page printing no meter is
            #                       the honest common case.
            #   checked_nothing     EVERY group has fewer than two
            #                       independent signals. ⚠️ THE ONE THAT
            #                       HIDES: such a redundancy can report a
            #                       wall of UNANIMOUS or SINGLE and look
            #                       busy while corroborating precisely
            #                       nothing. It is the 77%-agreement-rate
            #                       shape at the level of a whole redundancy.
            "declared_but_empty": sorted(
                name for name, groups in self.by_redundancy().items()
                if not groups),
            "witnessed_by_nobody": sorted(
                name for name, groups in self.by_redundancy().items()
                if groups and not any(g.witnesses for g in groups)),
            "checked_nothing": sorted(
                name for name, groups in self.by_redundancy().items()
                if all(g.uninformative for g in groups)),
            "n_groups": len(self.groups),
            "n_disagreements": len(self.disagreements()),
            "disagreements": [g.to_json() for g in self.disagreements()],
            "groups": [g.to_json() for g in self.groups],
        }


class NoRedundanciesDeclared(RuntimeError):
    """The group stage ran with an empty registry.

    ⚠️ An error rather than an empty report, for the same reason
    `adjudicate.NoDecisionsRegistered` and `evaluate.NoRulesRegistered` are:
    a stage that found nothing because nothing was loaded is
    indistinguishable from one that found nothing because there was nothing
    to find. That is A-BUILD-5, and it was itself found by a test whose empty
    run read as a pass.
    """


def run(log: Log, *, progress: bool = False) -> GroupReport:
    """Assess every declared redundancy over the log.

    ⚠️ Runs AFTER adjudication and BEFORE evaluation. Verdict-sourced
    redundancies need the decisions to have run; running before EVALUATE means
    the report describes what was ADJUDICATED rather than what consequences
    later restated, which is the cleaner claim.
    """
    _ensure_declarations()
    out: List[Group] = []
    for red in REDUNDANCIES:
        found = assess(log, red)
        out.extend(found)
        if progress:
            bad = sum(1 for g in found if g.disagrees)
            print(f"  groups {red.name}: {len(found)} facts, {bad} disagree")
    return GroupReport(tuple(out))


def _ensure_declarations() -> None:
    if not REDUNDANCIES:
        _declare()
    if not REDUNDANCIES:
        raise NoRedundanciesDeclared(
            "the group stage has no redundancies. An empty stage is not an "
            "empty result.")


# ─────────────────────────────────────────────────────────────────────────────
# The declared redundancies
#
# ⚠️ FIVE, and each names prior art in the tree. They are declarations, not
# measurements: nothing below has been run against a benchmark.
# ─────────────────────────────────────────────────────────────────────────────


def _system_of(log: Log, row: Row) -> Any:
    sub = row.subject.at(Kind.SYSTEM)
    return sub if sub is not None else None


def _slot_fact(log: Log, row: Row) -> Any:
    """A PART, keyed by its slot AND by its system's staff count.

    ⚠️ THE STAFF COUNT IS IN THE KEY AND IT IS NOT A DETAIL. `slot_index` is
    today the staff's ORDINAL within its own system, and a printed score
    suppresses tacet staves — so joining slot 4 of an 11-staff system to slot
    4 of an 8-staff system grafts a horn's continuation onto a trumpet's part.
    That is the population `export._stitch_slots` REFUSES and where the
    partition gate measured 3 of 27 staves misgrouped.

    So two systems witness one part only when they print the same number of
    staves. Systems of different lineups are different facts and never
    corroborate each other. It costs coverage and buys the only version of
    this join that is defensible today.
    """
    system = row.subject.at(Kind.SYSTEM)
    staff = row.subject.at(Kind.STAFF)
    if system is None or staff is None:
        return None
    slot = log.verdict(Q.SLOT_INDEX, staff)
    count = log.verdict(Q.SYSTEM_STAFF_COUNT, system)
    if slot is None or slot.outcome is not Outcome.DECIDED:
        return None
    if count is None or count.outcome is not Outcome.DECIDED:
        return None
    return ("slot", slot.value, "of", count.value)


def _declare() -> None:
    """Register the redundancies. Idempotent; called by `_ensure_declarations`."""

    redundancy(
        name="meter_across_staves",
        quantity=Q.METER_TEMPLATE,
        source=Source.OBSERVATION,
        witness_scope=Kind.STAFF,
        fact_key=_system_of,
        # ⚠️ THE PRINTED FORM, NOT THE BAR LENGTH. `C` and `4/4` are one bar
        # length and two engravings; musicdiff charges the difference at 3
        # edits per staff, so averaging them into one answer is a real loss.
        reading=lambda log, r: (r.detail.get("raw")
                                or (tuple(r.value) if isinstance(r.value, (list, tuple))
                                    else r.value)),
        why=("A time signature is a fact of the SYSTEM and the engraver prints "
             "it once on every staff of that system, so a 12-staff system "
             "carries twelve readings of one meter."),
        aspect=("The VALUE, and here that is legitimate: unlike a key "
                "signature, a meter does not transpose, so every staff of a "
                "system prints the same numerals."),
        implicates=(Q.METER, Q.METER_TEMPLATE, Q.DURATION),
    )

    redundancy(
        name="measure_count_across_staves",
        quantity=Q.MEASURE_PARTITION,
        source=Source.VERDICT,
        witness_scope=Kind.STAFF,
        fact_key=_system_of,
        reading=lambda log, r: r.value,
        why=("Every staff of a system spans the same music, so every staff "
             "prints the same number of bars — a barline runs the full height "
             "of the system and cuts all of them at once."),
        aspect=("The COUNT, not the positions: staves are engraved with "
                "different spacing, so two staves' barline x positions "
                "legitimately differ while their count cannot."),
        implicates=(Q.MEASURE_PARTITION, Q.BARLINE_COLUMN,
                    Q.SYSTEM_MEMBERSHIP, Q.DURATION),
    )

    redundancy(
        name="instrument_across_systems",
        quantity=Q.INSTRUMENT,
        source=Source.VERDICT,
        witness_scope=Kind.STAFF,
        fact_key=_slot_fact,
        reading=lambda log, r: (r.value or {}).get("name")
        if isinstance(r.value, dict) else r.value,
        why=("A part is the same instrument on every system it appears on — "
             "the engraver re-prints its margin label at each system head, so "
             "a five-system page reads one instrument up to five times."),
        aspect=("The instrument NAME. Not the label STRING, which legitimately "
                "shortens after the first system (`Flauti` then `Fl.`), and "
                "not the transposition, which the label may or may not "
                "restate."),
        implicates=(Q.INSTRUMENT, Q.SLOT_INDEX, Q.MARGIN_LABEL,
                    Q.SYSTEM_STAFF_COUNT),
    )

    redundancy(
        name="clef_across_systems",
        quantity=Q.CLEF,
        source=Source.VERDICT,
        witness_scope=Kind.STAFF,
        fact_key=_slot_fact,
        reading=lambda log, r: r.value,
        why=("A clef is in force until it changes and is RESTATED at the head "
             "of every system, so one part's clef is printed once per system "
             "on the page."),
        aspect=("The clef NAME — which line the glyph names. `contextual."
                "_fill_defaulted_clefs` already uses this shape, taking the "
                "clef a part read on another system where every reading "
                "agrees."),
        implicates=(Q.CLEF, Q.SLOT_INDEX, Q.CLEF_GLYPH, Q.CLEF_LOCATED),
        legitimate_difference=(
            "⚠️ A CLEF CHANGE IS REAL MUSIC. A cello moves between bass and "
            "tenor within a movement, and a bassoon between bass and tenor, so "
            "two systems of one part genuinely differing is not by itself an "
            "error. What makes a disagreement suspicious is a MINORITY of one "
            "against many, and even then the group is what is implicated — a "
            "real change would look the same to this evidence."),
    )

    redundancy(
        name="key_signature_across_systems",
        quantity=Q.KEY_SIGNATURE,
        source=Source.VERDICT,
        witness_scope=Kind.STAFF,
        fact_key=_slot_fact,
        reading=lambda log, r: r.value,
        why=("A key signature is restated at the head of every system for "
             "every staff, so one part's written key is printed once per "
             "system — which is the redundancy `key_signature_vote` already "
             "reconciles across systems for a part."),
        aspect=("The WRITTEN key of ONE PART across systems. ⚠️ NOT across the "
                "staves of one system: transposing instruments carry different "
                "written keys at the same bar, and that group is refused at "
                "the head of this module."),
        implicates=(Q.KEY_SIGNATURE, Q.SLOT_INDEX, Q.KEYSIG_RUN_POSITION,
                    Q.CLEF),
        legitimate_difference=(
            "A key CHANGE is real music and is printed behind a double "
            "barline mid-system. Its witness is the POSITION, not the value — "
            "and this group compares values, so a genuine change appears here "
            "as a disagreement. It implicates the group, never the dissenter."),
    )
