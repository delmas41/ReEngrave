"""Stable part identity — which staff is which instrument, across systems and pages.

The pipeline has no persistent part identity: every system is re-derived from
scratch and `export.to_musicxml` names parts `Page0-System1-merged`. So clef and
key state reset at every system boundary, per-instrument register priors are
unavailable, and nothing can be carried across a page turn. Contextual-analysis
item #1 (NOTES.md) is about fixing that; this module is its second half, after
`system_grouping` established correct systems.

## Why alignment, not indexing

Matching staff 3 of one system to staff 3 of the next fails on real orchestral
scores, because **a system omits the staves of instruments that are tacet
through it**. Beethoven 9 p65 has systems of 7 and 11 staves on one page; the
7-staff system is not a different orchestra, it is the same orchestra with four
parts resting.

Score order is **monotone** — instruments never appear out of family order — so
this is a sequence alignment, not a matching problem. Each system is aligned
against a reference layout with deletions allowed on the reference side (a part
omitted from this system) and reordering disallowed. That is a Needleman-Wunsch
style DP, cheap and deterministic.

## What drives the alignment

In descending order of strength:

* **Instrument labels** (`staff_labels.read_staff_labels`) — the same instrument
  is the same slot; two *different* named instruments cannot be the same slot,
  which is the only hard constraint available.
* **Bracket group** (`Staff.group_index`, from `system_grouping`) — winds do not
  align to strings.
* **Relative position** within the system, as a weak tiebreaker.

With none of those a system still aligns by position alone, which is correct
when staff counts match and is the honest best guess when they do not.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field

from .types import PageWithStaves, Staff

# Alignment scores. Label agreement dominates; a label CONFLICT is the only
# hard negative, because two differently-named instruments are certainly not
# the same part.
SCORE_LABEL_MATCH = 6.0
SCORE_LABEL_CONFLICT = -8.0
SCORE_GROUP_MATCH = 1.5
SCORE_GROUP_CONFLICT = -1.5
SCORE_POSITION_WEIGHT = 1.0     # scaled by 1 - |relative position difference|
GAP_PENALTY = -1.0              # skipping a reference slot (part tacet here)

# Labels below this confidence are treated as absent — a wrong instrument would
# propagate into every system, so `low` is not worth the risk here.
MIN_LABEL_CONFIDENCE = ("high", "medium")

# The reference is the largest system, but "largest" must not simply believe a
# system-grouping mistake: `system_grouping` fails by MERGING (2/14 pages), and a
# merged system is two systems concatenated — exactly the shape that wins a
# max-size contest. Unchecked, one bad boundary poisons the reference, and with
# it every page: on Beethoven 9 the reference came out as 24 slots listing
# Flute..Trumpet twice, and 20 of 24 slots then had an unstable bracket group.
# `_looks_merged` is the precise guard and catches the real case (the merged
# Beethoven 9 p25 repeats Oboe). This size cap is only a fallback for documents
# with no labels at all, so it is deliberately permissive: a concatenation is
# ~2x its neighbours, while a genuinely full system is only somewhat larger than
# the condensed ones around it, and too tight a cap throws the real reference
# away.
REFERENCE_MAX_SIZE_RATIO = 2.0


@dataclass
class Slot:
    """One part of the score, as seen in the reference layout."""

    index: int
    group_index: int
    instrument: str | None = None   # canonical name, when a label resolved it
    position: float = 0.0           # 0..1 down the reference system


@dataclass
class SystemView:
    """One system, reduced to what the alignment needs."""

    staves: list[Staff]
    labels: dict[int, str] = field(default_factory=dict)   # staff_index -> instrument name

    @property
    def size(self) -> int:
        return len(self.staves)


def labels_by_staff(staff_labels) -> dict[int, str]:
    """`{staff_index: instrument name}` for labels confident enough to align on."""
    return {
        lab.staff_index: lab.instrument.name
        for lab in staff_labels
        if lab.matched and lab.confidence in MIN_LABEL_CONFIDENCE
    }


def _views(pws: PageWithStaves, labels: dict[int, str] | None = None) -> list[SystemView]:
    by_system: dict[int, list[Staff]] = {}
    for s in sorted(pws.staves, key=lambda s: s.top_y):
        by_system.setdefault(s.system_index, []).append(s)
    labels = labels or {}
    return [
        SystemView(staves=staves,
                   labels={s.staff_index: labels[s.staff_index]
                           for s in staves if s.staff_index in labels})
        for _idx, staves in sorted(by_system.items())
    ]


def build_reference(views: list[SystemView]) -> list[Slot]:
    """The canonical part list: the largest system seen, since a system can omit
    tacet parts but never invent one.

    Guarded by `REFERENCE_MAX_SIZE_RATIO` against a merged system winning the
    max-size contest, and by a repeated-instrument check that recognises a
    concatenation directly. Ties go to the system carrying the most resolved
    labels, which makes the reference as identifiable as possible.
    """
    views = [v for v in views if v.size]
    if not views:
        return []
    sizes = sorted(v.size for v in views)
    median = sizes[len(sizes) // 2]
    cap = median * REFERENCE_MAX_SIZE_RATIO
    candidates = [v for v in views if v.size <= cap and not _looks_merged(v)]
    if not candidates:
        candidates = views

    # A merged "system" is a ONE-OFF; a real full system recurs, because the
    # orchestra is the same on every page. So prefer the largest size that
    # appears more than once. This is the label-free half of the guard, and it
    # is the half that matters: `_looks_merged` reads instrument names, so it is
    # blind on a score with no text layer — exactly where a 24-staff
    # concatenation of two 12-staff systems slipped through and became a
    # 24-slot reference of entirely unlabelled parts.
    counts = collections.Counter(v.size for v in candidates)
    recurring = [v for v in candidates if counts[v.size] > 1]
    if recurring:
        candidates = recurring
    best = max(candidates, key=lambda v: (v.size, len(v.labels)))
    n = max(1, best.size - 1)
    return [
        Slot(index=i,
             group_index=st.group_index,
             instrument=best.labels.get(st.staff_index),
             position=i / n)
        for i, st in enumerate(best.staves)
    ]


def _looks_merged(view: SystemView) -> bool:
    """Whether this "system" is really two systems concatenated.

    A score lists each instrument once per system, so a label sequence that
    repeats an instrument after an intervening different one — Flute, Oboe, ...,
    Flute again — is a concatenation, not an orchestra.
    """
    seen: set[str] = set()
    last: str | None = None
    for st in view.staves:
        name = view.labels.get(st.staff_index)
        if name is None:
            continue
        if name in seen and name != last:
            return True
        seen.add(name)
        last = name
    return False


def _pair_score(staff: Staff, label: str | None, slot: Slot,
                staff_position: float) -> float:
    score = 0.0
    if label is not None and slot.instrument is not None:
        score += SCORE_LABEL_MATCH if label == slot.instrument else SCORE_LABEL_CONFLICT
    if staff.group_index == slot.group_index:
        score += SCORE_GROUP_MATCH
    else:
        score += SCORE_GROUP_CONFLICT
    score += SCORE_POSITION_WEIGHT * (1.0 - abs(staff_position - slot.position))
    return score


def align(view: SystemView, reference: list[Slot]) -> list[int]:
    """Slot index for each staff of `view`, in order.

    Monotone alignment with deletions allowed on the reference side. Returns
    `-1` for a staff that could not be placed (only possible when the system has
    more staves than the reference, i.e. the reference is incomplete).
    """
    m, n = view.size, len(reference)
    if m == 0 or n == 0:
        return [-1] * m
    denom = max(1, m - 1)
    positions = [i / denom for i in range(m)]
    labels = [view.labels.get(st.staff_index) for st in view.staves]

    NEG = float("-inf")
    # dp[i][j] = best score having placed the first i staves within the first j slots
    dp = [[NEG] * (n + 1) for _ in range(m + 1)]
    back = [[None] * (n + 1) for _ in range(m + 1)]
    for j in range(n + 1):
        dp[0][j] = GAP_PENALTY * j
        back[0][j] = "gap"
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            skip = dp[i][j - 1] + GAP_PENALTY
            take = NEG
            if dp[i - 1][j - 1] > NEG:
                take = dp[i - 1][j - 1] + _pair_score(
                    view.staves[i - 1], labels[i - 1], reference[j - 1], positions[i - 1])
            if take >= skip:
                dp[i][j], back[i][j] = take, "take"
            else:
                dp[i][j], back[i][j] = skip, "gap"

    out = [-1] * m
    i, j = m, n
    while i > 0 and j > 0:
        if back[i][j] == "take":
            out[i - 1] = reference[j - 1].index
            i -= 1
            j -= 1
        else:
            j -= 1
    return out


def assign_slots(pages: list[PageWithStaves],
                 labels_per_page: list[dict[int, str]] | None = None
                 ) -> list[Slot]:
    """Set `Staff.slot_index` on every staff of every page, and return the
    reference layout the slots refer to.

    The reference is built from the largest system across ALL pages, so a page
    whose systems are all condensed still aligns against the full orchestra.
    """
    if labels_per_page is None:
        labels_per_page = [{} for _ in pages]
    all_views: list[list[SystemView]] = [
        _views(pws, labels) for pws, labels in zip(pages, labels_per_page)
    ]
    reference = build_reference([v for page_views in all_views for v in page_views])
    if not reference:
        return []
    for page_views in all_views:
        for view in page_views:
            for staff, slot in zip(view.staves, align(view, reference)):
                staff.slot_index = slot
    return reference
