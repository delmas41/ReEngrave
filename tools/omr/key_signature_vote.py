"""Reconcile per-staff key-signature readings across a page.

A key signature read from one staff in isolation is a fragile thing. The
locator can miss accidentals — on real prints it routinely finds one of three —
and a run of one carries no pattern, so both the count and the sharp/flat
decision fall to whatever single glyph survived. That is exactly how a
three-flat staff comes back as one flat, and a bass-clef flat that fragments
high comes back as a sharp.

But a page prints the same information many times over, in two independent
ways, and neither is available to a staff on its own:

  * **Across systems, down the page.** The oboe part is the same part in every
    system, so its written key signature is the same in every system. A staff
    that reads three flats in system 2 and one flat in system 1 is not
    reporting a key change; it is reporting a missed accidental.
  * **Across staves, within a system.** Every staff of a system is playing in
    one concert key. Transposing instruments print different signatures for it,
    but only by a fixed set of offsets, which
    `transcribe._flag_key_signature_inconsistency` already models.

This module uses both, and it is deliberately careful about what each can prove.

## What the concert-key relation can and cannot do

It is weaker than it looks. For a concert key K the consistent written
signatures are {K−3, K, K+1, K+2, K+3} — five of the fifteen possible values.
So an under-counted signature usually lands on a *legal* offset rather than an
illegal one: three flats misread as one flat (−3 → −1) looks exactly like a B♭
instrument correctly notated. Measured on both ground-truth pages, the concert
key alone rejected neither wrong answer.

What separates them is that a transposing instrument is a MINORITY. Strings,
flutes, oboes and bassoons all print the concert signature, so the reference to
measure a staff against is the system's own MODAL written signature, and a staff
that departs from it is claiming to be a transposing instrument. That claim
needs evidence — either a strong read (several accidentals, all matched) or the
same reading from the same part in another system. A lone accidental that merely
*could* be a B♭ clarinet is not evidence, and gets abstained on.

The mode is used in preference to the best-fitting concert key, and the
difference matters. Choosing the key that EXPLAINS the most readings rewards
keys with permissive offset sets: on Beethoven 6, whose staves mostly print one
flat, a spurious three-flat reading pulled the best-fit key to E♭ major, whose
consistent set then covered both — and the spurious reading was accepted for
agreeing with a key it had itself created. The mode cannot do that; it is what
the staves actually print, and it is exactly as conservative as it should be. If
the modal signature is itself a transposed one, the allowed set computed from it
is narrower than the truth, so the vote abstains more and asserts no more.

## The asymmetry that makes carrying safe

Readings do not fail symmetrically. The locator can lose an accidental to a
broken glyph, but it cannot invent one: `key_signature_geometry` requires the
first slot to be observed, forbids extending past the last observation, and caps
inferred slots below observed ones. So where two systems disagree about the same
part, the reading with MORE accidentals is the better one — under-counting is
the failure mode that exists.

Carrying across systems is guarded on the systems having the same number of
staves, so that position within a system identifies the instrument. A condensed
system with fewer staves is left alone rather than aligned by guesswork.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


# The written-signature offsets a standard transposing instrument prints for a
# given concert key: A (−3), C (0), F (+1), Bb (+2), Eb (+3). `transcribe`
# imports this so the vote and the cross-staff warning cannot drift apart.
TRANSPOSITION_FIFTHS_OFFSETS = (-3, 0, 1, 2, 3)

FIFTHS_TO_MAJOR = {
    0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
    -1: "F", -2: "Bb", -3: "Eb", -4: "Ab", -5: "Db", -6: "Gb", -7: "Cb",
}


def fifths_key_name(c: int) -> str:
    return f"{FIFTHS_TO_MAJOR.get(c, '?')} major"


def fifths_accidentals(c: int) -> str:
    if c > 0:
        return f"{c} sharp{'s' if c != 1 else ''}"
    if c < 0:
        return f"{-c} flat{'s' if c != -1 else ''}"
    return "no accidentals"


@dataclass(frozen=True)
class VoteConfig:
    """Knobs for reconciliation.

    strong_weight:
        The weight at or above which a reading may depart from its system's
        modal signature on its own authority — i.e. be believed as a genuine
        transposing instrument without corroboration. Callers pass the number of
        accidentals actually matched, so the default of 2.0 means "a lone
        accidental is never enough on its own".
    min_majority:
        Fraction of weight the modal signature must hold — STRICTLY exceed —
        before the vote will call anything an outlier. At or below it the page
        is too unevenly read to say which staff is the odd one out, and every
        reading stands. The strictness matters at exactly the interesting
        boundary: a two-way tie has no majority to appeal to, and the
        cross-staff checks in `transcribe` abstain there for the same reason.
    """

    strong_weight: float = 2.0
    min_majority: float = 0.5


DEFAULT_VOTE_CONFIG = VoteConfig()


@dataclass(frozen=True)
class StaffCandidate:
    """One staff's key-signature reading, before reconciliation.

    ordinal:  the staff's position within its own system (0 = top). This, not
              `staff_index`, is what identifies the instrument across systems.
    fifths:   +N sharps / −N flats / 0 for none; None when nothing was read.
    weight:   how much the reading is worth — the number of accidentals actually
              observed is the natural measure, and what the locator supplies.
    can_carry: whether this reading's SOURCE obeys the asymmetry in the module
              docstring — that a reader loses accidentals and never invents
              them. False marks a source that can OVER-count, and that has two
              consequences, not one:

              * such a reading may not travel to the same part in another
                system. Measured on WTC I p.17: one staff's spurious fifth
                sharp, carried by `abs(fifths)` winning, made every treble
                staff of all five systems read five sharps where the page
                prints four.
              * such a reading may not assert on its own staff **unchecked**.
                It stays usable where the system's reference accepts it, but
                where there is no reference to check it against it must clear
                `strong_weight` like any other departure. Measured on Boléro
                p.10: five template readings of a single flat, on headers that
                print nothing — one of them a percussion staff — survived
                because a genuinely polytonal page has no majority, and the
                no-majority branch used to keep everything.
    """

    staff_index: int
    system_index: int
    ordinal: int
    fifths: int | None
    weight: float = 1.0
    source: str = ""
    can_carry: bool = True


@dataclass(frozen=True)
class StaffVerdict:
    """What reconciliation decided for one staff.

    fifths:  the signature to use, or None to leave the staff as it was.
    action:  "kept"      — the reading stands
             "carried"   — taken from the same part in another system
             "rejected"  — the reading was dropped; the staff abstains
             "unread"    — there was nothing to decide
    reason:  short human-readable justification, carried into the output JSON.
    """

    staff_index: int
    fifths: int | None
    action: str
    reason: str


@dataclass
class VoteResult:
    """The page's reconciled readings.

    reference_written_by_system holds each system's modal WRITTEN signature —
    the thing departures are judged against. It is usually the concert key, but
    it is not asserted to be: see the module docstring.
    """

    verdicts: dict[int, StaffVerdict] = field(default_factory=dict)
    reference_written_by_system: dict[int, int | None] = field(default_factory=dict)

    def fifths_for(self, staff_index: int) -> int | None:
        verdict = self.verdicts.get(staff_index)
        return verdict.fifths if verdict else None


def consistent_written_set(reference: int) -> set[int]:
    """The written signatures that reconcile with `reference` through a standard
    instrument transposition — `reference` itself included."""
    return {reference + off for off in TRANSPOSITION_FIFTHS_OFFSETS}


def _modal_reference(
    values_with_weight: list[tuple[int, float]]
) -> tuple[int | None, float]:
    """The system's modal written signature and the share of weight it holds.

    Ties go to the signature with fewer accidentals: it is the likelier reading,
    since the reader loses accidentals and does not invent them.

    Readings weighted below 1 do not vote for the reference at all. A weight
    under one accidental is a caller saying the reading is too weak to assert on
    its own — a signature fitted against a DEFAULTED clef, in the one case that
    exists — and such a reading must be able to AGREE with the system without
    being able to define what the system says.

    This was expected to recover a staff on the Pastoral and did not: it
    measured neutral on all three ground-truth pages. It is kept as the
    invariant it is, not for a gain it does not deliver.
    """
    totals: dict[int, float] = defaultdict(float)
    for fifths, weight in values_with_weight:
        if weight < 1.0:
            continue
        totals[fifths] += max(weight, 1.0)
    if not totals:
        return None, 0.0
    total = sum(totals.values())
    modal = max(totals, key=lambda f: (totals[f], -abs(f)))
    return modal, totals[modal] / total


def _trustworthy(
    fifths: int | None, weight: float, reference: int | None, config: VoteConfig
) -> bool:
    """Whether a reading carries enough evidence to be asserted — either on its
    own staff, or exported to the same part in another system.

    Agreeing with the system's reference is enough. Departing from it is a claim
    to be a transposing instrument, which needs both a legal offset and a strong
    reading behind it. The same test governs keeping and carrying deliberately:
    carrying asserts a signature onto a staff that read NOTHING, so it cannot be
    allowed on weaker evidence than keeping one. Before this was shared, a
    reading rejected as too weak in its own system was still exported, and
    arrived in the next system as an unchallenged fact — which is how a bassoon
    misread as one sharp among a system of one-flat parts got rejected where it
    was read and accepted where it was not.
    """
    if fifths is None:
        return False
    if reference is None or fifths == reference or fifths == 0:
        return True
    if fifths not in consistent_written_set(reference):
        return False
    return weight >= config.strong_weight


def _consolidate_across_systems(
    candidates: list[StaffCandidate],
    references: dict[int, int | None],
    config: VoteConfig,
) -> tuple[dict[int, tuple[int, float]], set[int]]:
    """Resolve each part's signature using every system it appears in.

    Returns `({ordinal: (fifths, weight)}, conflicted_ordinals)`. A part whose
    systems disagree about the KIND of accidental is conflicted — one reading is
    simply wrong and nothing here can say which — so the caller abstains on it.
    Disagreement about the COUNT is not a conflict: the higher count wins,
    because the reader under-counts and never invents (see the module docstring).
    """
    by_system: dict[int, set[int]] = defaultdict(set)
    for cand in candidates:
        by_system[cand.system_index].add(cand.ordinal)
    sizes = {len(ordinals) for ordinals in by_system.values()}
    if len(by_system) < 2 or len(sizes) != 1:
        # One system, or systems of differing height — position no longer
        # identifies the instrument, so there is nothing safe to align.
        return {}, set()

    # A sign disagreement is judged on the RAW readings, deliberately. If one
    # system read sharps for a part and another read flats, one of them is
    # simply wrong — and that is reason to distrust the survivor too, so the
    # test must run before the trustworthiness filter has quietly dropped the
    # side that made the disagreement visible.
    conflicted: set[int] = set()
    raw: dict[int, set[int]] = defaultdict(set)
    for cand in candidates:
        if cand.fifths:
            raw[cand.ordinal].add(1 if cand.fifths > 0 else -1)
    conflicted = {ordinal for ordinal, signs in raw.items() if len(signs) > 1}

    readings: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for cand in candidates:
        if not cand.can_carry:
            continue
        if cand.fifths and cand.ordinal not in conflicted and _trustworthy(
            cand.fifths, cand.weight, references.get(cand.system_index), config
        ):
            readings[cand.ordinal].append((cand.fifths, cand.weight))

    resolved: dict[int, tuple[int, float]] = {}
    for ordinal, seen in readings.items():
        fifths, _ = max(seen, key=lambda fw: (abs(fw[0]), fw[1]))
        resolved[ordinal] = (fifths, max(w for _, w in seen))
    return resolved, conflicted


def reconcile(
    candidates: list[StaffCandidate],
    config: VoteConfig = DEFAULT_VOTE_CONFIG,
) -> VoteResult:
    """Reconcile a page's key-signature readings.

    Every staff comes back with a verdict. A staff is only ever left with a
    reading it — or the same part in another system — actually produced: the
    vote rejects and carries, and never synthesises a signature from the
    reference, because the reference cannot say what a given staff's
    transposition is.
    """
    result = VoteResult()
    by_system: dict[int, list[StaffCandidate]] = defaultdict(list)
    for cand in candidates:
        by_system[cand.system_index].append(cand)

    # The reference. Every system on a page has the same instrumentation and is
    # playing in the same key, so when the systems line up (equal staff counts)
    # the reference is computed from the WHOLE page's readings rather than each
    # system's own. It matters: on Beethoven 5 p.2 the lower system was read
    # badly enough that its own modal signature came out as one flat on a page of
    # three-flat parts, and three wrong readings were then kept for "agreeing"
    # with a reference they had themselves set. Pooling lets the system that was
    # read well decide for the page.
    #
    # A real key change part-way down a page would be pooled over — but the vote
    # only ever rejects a departing reading, never rewrites it, so the cost there
    # is abstention rather than a wrong signature.
    references: dict[int, int | None] = {}
    majorities: dict[int, float] = {}
    aligned = len({len(staves) for staves in by_system.values()}) == 1 and len(by_system) > 1
    if aligned:
        pooled = _modal_reference([(c.fifths, c.weight) for c in candidates if c.fifths])
        references = {i: pooled[0] for i in by_system}
        majorities = {i: pooled[1] for i in by_system}
    else:
        for system_index, staves in by_system.items():
            readings = [(c.fifths, c.weight) for c in staves if c.fifths]
            references[system_index], majorities[system_index] = _modal_reference(readings)

    resolved, conflicted = _consolidate_across_systems(candidates, references, config)

    for system_index, staves in sorted(by_system.items()):
        reference = references[system_index]
        majority = majorities[system_index]
        result.reference_written_by_system[system_index] = reference

        for cand in staves:
            fifths, weight, carried = cand.fifths, cand.weight, False
            if cand.ordinal in conflicted:
                result.verdicts[cand.staff_index] = StaffVerdict(
                    cand.staff_index, None, "rejected",
                    "systems disagree about sharps vs flats for this part",
                )
                continue
            if cand.ordinal in resolved:
                other_fifths, other_weight = resolved[cand.ordinal]
                if fifths is None or abs(other_fifths) > abs(fifths):
                    carried = fifths != other_fifths
                    fifths, weight = other_fifths, other_weight

            if fifths is None:
                result.verdicts[cand.staff_index] = StaffVerdict(
                    cand.staff_index, None, "unread", "no key signature read",
                )
            elif reference is None or majority <= config.min_majority or fifths == 0:
                # "No majority" is a statement about the PAGE, not a licence for
                # the reading. A source that can over-count (see
                # StaffCandidate.can_carry) has nothing checking it here, so it
                # must clear `strong_weight` on its own — the same bar a
                # departure clears when there IS a reference. A lone accidental
                # never does, which is exactly what this branch used to wave
                # through on Boléro p.10.
                if (fifths != 0 and not cand.can_carry
                        and weight < config.strong_weight):
                    result.verdicts[cand.staff_index] = StaffVerdict(
                        cand.staff_index, None, "rejected",
                        f"{fifths_accidentals(fifths)} from a reader that can "
                        f"over-count, with no majority to check it against",
                    )
                else:
                    result.verdicts[cand.staff_index] = StaffVerdict(
                        cand.staff_index, fifths, "carried" if carried else "kept",
                        "no majority to check against",
                    )
            elif fifths == reference:
                result.verdicts[cand.staff_index] = StaffVerdict(
                    cand.staff_index, fifths, "carried" if carried else "kept",
                    f"agrees with the system's {fifths_accidentals(fifths)}",
                )
            elif _trustworthy(fifths, weight, reference, config):
                result.verdicts[cand.staff_index] = StaffVerdict(
                    cand.staff_index, fifths, "carried" if carried else "kept",
                    f"{fifths_accidentals(fifths)} is a standard transposition of a "
                    f"part printing {fifths_accidentals(reference)}",
                )
            else:
                result.verdicts[cand.staff_index] = StaffVerdict(
                    cand.staff_index, None, "rejected",
                    f"{fifths_accidentals(fifths)} differs from the system's "
                    f"{fifths_accidentals(reference)} on too little evidence",
                )
    return result
