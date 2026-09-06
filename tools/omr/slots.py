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
import os
from dataclasses import dataclass, field

from . import movement_reference
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


def most_labelled_reference_mode() -> str:
    """`OMR_REFERENCE_MOST_LABELLED` — `off` (default) / `on` / `pure`.

    Picks the reference by how many staves a system NAMES rather than by which
    staff count recurs. `on` keeps the never-shrink guard described in
    `build_reference`; `pure` drops it and exists to reproduce the measurement
    that refused it.
    """
    v = os.environ.get("OMR_REFERENCE_MOST_LABELLED", "").strip().lower()
    if v == "pure":
        return "pure"
    return "on" if v in ("1", "true", "yes", "on") else "off"


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


def build_reference(views: list[SystemView],
                    most_labelled: str | bool | None = None) -> list[Slot]:
    """The canonical part list: the largest system seen, since a system can omit
    tacet parts but never invent one.

    Guarded by `REFERENCE_MAX_SIZE_RATIO` against a merged system winning the
    max-size contest, and by a repeated-instrument check that recognises a
    concatenation directly. Ties go to the system carrying the most resolved
    labels, which makes the reference as identifiable as possible.

    ⚠️ **THE RECURRING RULE IS BACKWARDS ON A MULTI-PAGE RUN**, and that is what
    `most_labelled` (env `OMR_REFERENCE_MOST_LABELLED`, default off) exists for.
    A movement's FIRST page prints the full lineup and every page after it
    condenses — Beethoven 5 / Litolff prints 12 staves on p.1 and 11 on p.2+,
    because `Violoncello e Basso` share a staff — so over a run 11 recurs and 12
    does not, the recurring filter throws the full system away, and `align`
    (which deletes on the reference side only) then drops the twelve-staff
    system's TOP staff and slides every name up one: `Corni` becomes Bassoon.
    Measured on that PDF: `--pages 1` names 11 of 12 staves and `--pages 0-2`
    names 4 — the web app's own `OMR_MAX_PAGES=5` default reproduces it.

    A system that NAMES its parts is better evidence of what the parts are than
    a shape that merely recurs, and the recurring shape is systematically the
    *condensed* one because condensation is what repeats. So with the flag on,
    the reference is the system with the most resolved labels, ties broken by
    size (so a fully-labelled edition still picks its fullest system).

    ⚠️ It ABSTAINS where no system names anything — 27 of 234 documents print no
    labels at all, and there the label count is 0 everywhere and would pick an
    arbitrary first system. Those fall through to the recurring rule unchanged,
    which is also where the recurring filter's real job lies: it is the
    label-free half of the merge guard (`_looks_merged` reads names, so it is
    blind exactly there).

    ⚠️ AND IT NEVER SHRINKS THE REFERENCE. The labelled system is not always the
    fullest one: a Bote Dvořák serenade names its opening 5-staff system and
    prints 6-staff systems later, and a reference SHORTER than a system cannot
    name that system's overflow at all — `align` leaves it at slot -1, which is
    a worse failure than the misnaming this fixes. So the label winner is taken
    only where it is at least as large as what the recurring rule would have
    chosen; otherwise the recurring pick stands. `most_labelled="pure"` drops
    that guard and is kept only to reproduce the measurement that refused it.
    """
    best = reference_view(views, most_labelled)
    if best is None:
        return []
    return _slots_of(best)


def _slots_of(view: SystemView) -> list[Slot]:
    n = max(1, view.size - 1)
    return [
        Slot(index=i,
             group_index=st.group_index,
             instrument=view.labels.get(st.staff_index),
             position=i / n)
        for i, st in enumerate(view.staves)
    ]


def reference_view(views: list[SystemView],
                   most_labelled: str | bool | None = None
                   ) -> SystemView | None:
    """The SYSTEM the reference is read off, kept rather than discarded.

    `build_reference` always chose a particular system and then threw it away,
    returning only the slots. The system itself is what a second alignment
    needs — see `movement_reference`: a movement's own reference has to be
    placed into the document's, and it is placed the way every other system is,
    by aligning the system it came from. The whole choice lives here, including
    `most_labelled`, so a per-SPAN reference is chosen by exactly the rule a
    per-document one is.
    """
    if most_labelled is None:
        most_labelled = most_labelled_reference_mode()
    if most_labelled is True:
        most_labelled = "on"
    elif most_labelled is False:
        most_labelled = "off"
    views = [v for v in views if v.size]
    if not views:
        return None
    sizes = sorted(v.size for v in views)
    median = sizes[len(sizes) // 2]
    cap = median * REFERENCE_MAX_SIZE_RATIO
    candidates = [v for v in views if v.size <= cap and not _looks_merged(v)]
    if not candidates:
        candidates = views

    # A merged "system" is a ONE-OFF; a real full system recurs, because the
    # orchestra is the same on every page. So prefer the largest size that
    # appears more than once. This is the label-free half of the guard, and
    # it is the half that matters: `_looks_merged` reads instrument names,
    # so it is blind on a score with no text layer — exactly where a
    # 24-staff concatenation of two 12-staff systems slipped through and
    # became a 24-slot reference of entirely unlabelled parts.
    counts = collections.Counter(v.size for v in candidates)
    recurring = [v for v in candidates if counts[v.size] > 1] or candidates
    best = max(recurring, key=lambda v: (v.size, len(v.labels)))

    labelled = [v for v in candidates if v.labels] if most_labelled != "off" else []
    if labelled:
        # Most-labelled wins; size breaks the tie, so an edition that labels
        # every system (Breitkopf) still gets its fullest one, and an edition
        # that labels only winds and brass on every system (Litolff) ties on
        # labels and is decided by size — the full lineup either way.
        by_labels = max(labelled, key=lambda v: (len(v.labels), v.size))
        if most_labelled == "pure" or by_labels.size >= best.size:
            best = by_labels
    return best


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


def group_term_mode() -> str:
    """`OMR_SLOT_GROUP_MAP` — `map` (default) / `ordinal` / `off`.

    `map` relates the two bracket vocabularies with `map_groups` before
    comparing them. `ordinal` is the pre-2026-09-06 behaviour, comparing
    `Staff.group_index` to `Slot.group_index` raw; it exists to reproduce the
    measurement that refused it and should not be used. `off` withholds the
    group term entirely.
    """
    v = os.environ.get("OMR_SLOT_GROUP_MAP", "").strip().lower()
    return v if v in ("map", "ordinal", "off") else "map"


def _blocks(groups: list) -> list[tuple]:
    """Contiguous runs of one group, as `(group, size)`, top to bottom."""
    out: list[tuple] = []
    for g in groups:
        if out and out[-1][0] == g:
            out[-1] = (g, out[-1][1] + 1)
        else:
            out.append((g, 1))
    return out


def _partitions(m: int, n: int):
    """Every monotone assignment of `m` system blocks to `n` reference blocks.

    Each system block takes a consecutive, non-empty run of reference blocks;
    runs appear in order and do not overlap; reference blocks between or around
    them may be left UNTAKEN — a whole bracket group can be tacet through a
    system, which is the ordinary case (`test_assign_slots_across_systems_and_
    pages`: winds absent, so the reference's first block is taken by nobody).
    Yields lists of `(start, stop)` half-open runs.
    """
    def walk(i: int, lo: int, acc: list):
        if i == m:
            yield list(acc)
            return
        # leave room for the remaining m-i-1 blocks, one reference block each
        for a in range(lo, n - (m - i - 1)):
            for b in range(a + 1, n - (m - i - 1) + 1):
                acc.append((a, b))
                yield from walk(i + 1, b, acc)
                acc.pop()
    yield from walk(0, 0, [])


#: Above this many bracket blocks on either side the enumeration is not worth
#: doing; real scores have a handful. Abstaining is the documented failure.
MAX_GROUP_BLOCKS = 12


def map_groups(view: SystemView, reference: list[Slot]) -> dict | None:
    """`{system group -> set of reference groups}`, or None if undecidable.

    A system's bracket blocks and the reference's appear in the same order —
    score order is monotone for brackets exactly as it is for parts — so the
    correspondence is a monotone assignment: each system block takes a
    consecutive run of reference blocks, runs keep their order, and reference
    blocks nobody takes are groups tacet through this system. The best
    assignment is the one whose block SIZES agree best.

    On Beethoven 5 / Litolff p23 the reduced system is `[(0, 7), (1, 5)]` and
    the reference `[(0, 6), (1, 6), (2, 5)]`. The winning assignment pairs the
    system's five string staves with the reference's five string slots, so the
    strings MATCH slots 12-14 and CONFLICT with the Trombones — the sign the
    term was always supposed to have.

    ⚠️ **A TIE ABSTAINS.** Where two assignments of different meaning share the
    best cost there is no evidence between them, and picking one would be the
    same class of silent wrong answer as comparing raw ordinals — rarer, and
    harder to find later. `test_assign_slots_across_systems_and_pages` is a real
    tie under the size cost alone (`[(1,2),(2,3)]` against
    `[(0,4),(1,2),(2,3)]`), which is why untaken reference blocks are free:
    with them free the truth costs 0 and nothing else does.

    Returns None where the system has MORE blocks than the reference (the
    reference is incomplete, so there is nothing to map onto), where either side
    exceeds `MAX_GROUP_BLOCKS`, or on a tie.
    """
    sb = _blocks([st.group_index for st in view.staves])
    rb = _blocks([sl.group_index for sl in reference])
    if not sb or not rb or len(sb) > len(rb):
        return None
    if len(sb) > MAX_GROUP_BLOCKS or len(rb) > MAX_GROUP_BLOCKS:
        return None

    best_cost, best_maps = None, []
    for runs in _partitions(len(sb), len(rb)):
        sizes = [sum(rb[t][1] for t in range(a, b)) for a, b in runs]
        # A block of s staves cannot be the reference's s-1 slots: every staff
        # printed is a part present, so the slots it maps onto must number at
        # least as many. This is what makes the assignment decidable on
        # Beethoven 5 p23 -- of the six monotone assignments only ONE gives the
        # seven-staff wind-and-brass block enough room, and abstaining for want
        # of it was costing the fix its own case.
        if any(sz < sb[i][1] for i, sz in enumerate(sizes)):
            continue
        cost = sum(abs(sb[i][1] - sz) for i, sz in enumerate(sizes))
        if best_cost is None or cost < best_cost:
            best_cost, best_maps = cost, [runs]
        elif cost == best_cost:
            best_maps.append(runs)

    def as_mapping(runs):
        out: dict = {}
        for i, (a, b) in enumerate(runs):
            out.setdefault(sb[i][0], set()).update(rb[t][0] for t in range(a, b))
        return out

    if not best_maps:
        return None          # no assignment gives every block room
    winner = as_mapping(best_maps[0])
    for runs in best_maps[1:]:
        if as_mapping(runs) != winner:
            return None          # a tie of different meanings: no evidence
    return winner


def groups_are_comparable(view: SystemView, reference: list[Slot]) -> bool:
    """Whether this system's bracket ordinals mean the same thing as the
    reference's, so `group_index` may be compared across the two at all.

    ⚠️ **`Staff.group_index` is a PER-SYSTEM ORDINAL, not a family identity.**
    `system_grouping` numbers the bracket groups it finds on one system, from
    the top. Nothing carries a group's meaning from one system to the next, so
    "group 1" is whatever the second bracket happens to be THERE — and the
    module docstring's promise that "winds do not align to strings" holds only
    while both sides happen to have found the same brackets.

    On a reduced system they do not, and the term then argues for exactly the
    alignment it exists to prevent. Measured on Beethoven 5 / Litolff p23
    (`benchmarks/omr-slot-alignment-2026-09/`): the twelve-staff system detects
    **two** groups (winds and brass merged, then strings) against the
    seventeen-slot reference's **three** (winds, brass+timpani, strings), so its
    three unlabelled string staves carry group 1 — which MATCHES the reference's
    three Trombone slots and CONFLICTS with the real Violin/Viola slots. The DP
    scored the wrong alignment **+8.9489**, and **+9.0 of that was this term**
    while position favoured the truth by 0.0511 and the labels were identical.
    Violin, Violin and Viola came out as Trombone, Trombone and Trombone.

    Both alignments delete five slots, so the gap cost cannot separate them.
    This term was the whole decision, and it had the sign backwards.

    ⚠️ The bracket detection is also UNSTABLE across pages of one movement —
    p31 finds three groups where p23 and p38 find two, on the same printed
    lineup. That is a `system_grouping` fault and is recorded, not fixed here;
    the alignment has to be right whether or not it is repaired, because a
    reference and a reduced system can legitimately differ in bracket structure
    (the reference is the FULL lineup and brackets enclose the parts present).

    So the ordinals are compared only when the two vocabularies match. Where
    they do not, the term is WITHHELD (contributes nothing) rather than guessed:
    a wrong group verdict is worth 3.0 against a position signal worth ~0.05, so
    asserting it on incomparable ordinals cannot be a tiebreak — it is a
    veto with no evidence behind it.
    """
    return ({st.group_index for st in view.staves}
            == {sl.group_index for sl in reference})


def _pair_score(staff: Staff, label: str | None, slot: Slot,
                staff_position: float, group_map: dict | None = None) -> float:
    """`group_map` is `map_groups`' verdict: `{system group -> {reference
    groups}}`, or None where the two bracket vocabularies cannot be related, in
    which case the group term is WITHHELD rather than guessed. A wrong group
    verdict is worth 3.0 against a position signal worth ~0.05, so asserting one
    on ordinals that do not correspond is a veto with no evidence behind it.
    """
    score = 0.0
    if label is not None and slot.instrument is not None:
        score += SCORE_LABEL_MATCH if label == slot.instrument else SCORE_LABEL_CONFLICT
    if group_map is not None:
        allowed = group_map.get(staff.group_index)
        if allowed is not None:
            score += (SCORE_GROUP_MATCH if slot.group_index in allowed
                      else SCORE_GROUP_CONFLICT)
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
    mode = group_term_mode()
    if mode == "off":
        mapping = None
    elif mode == "ordinal":
        mapping = {g: {g} for g in {st.group_index for st in view.staves}}
    else:
        mapping = map_groups(view, reference)

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
                    view.staves[i - 1], labels[i - 1], reference[j - 1],
                    positions[i - 1], mapping)
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
                 labels_per_page: list[dict[int, str]] | None = None,
                 most_labelled: bool | None = None) -> list[Slot]:
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
    reference = build_reference(
        [v for page_views in all_views for v in page_views],
        most_labelled=most_labelled)
    if not reference:
        return []

    if movement_reference.enabled():
        spans = _span_views(pages, all_views)
        if len(spans) > 1 and _align_by_span(spans, reference):
            return reference

    for page_views in all_views:
        for view in page_views:
            for staff, slot in zip(view.staves, align(view, reference)):
                staff.slot_index = slot
    return reference


def _span_views(pages: list[PageWithStaves],
                all_views: list[list[SystemView]]) -> list[list[SystemView]]:
    """The run's systems grouped into lineup spans — see `movement_reference`."""
    page_systems = [
        (pws.page.page_index, [v.size for v in views])
        for pws, views in zip(pages, all_views)
    ]
    by_page = {pws.page.page_index: views
               for pws, views in zip(pages, all_views)}
    return [[v for p in span for v in by_page.get(p, [])]
            for span in movement_reference.lineup_spans(page_systems)]


def _align_by_span(spans: list[list[SystemView]],
                   reference: list[Slot]) -> bool:
    """Align each span's systems against that span's OWN reference, composed
    into the document's slot space. Returns whether it could be done.

    Two alignments, both the ordinary one:

    1. the span's reference SYSTEM into the document reference — the strongest
       case the DP ever gets, because a movement's opening system is the one
       page in the movement that labels every staff it has;
    2. each system of the span into the span reference — where an unreduced
       system now has as many staves as the reference has slots, and the only
       order-preserving mapping of m onto m is one-to-one.

    Refuses (leaving the caller on the document-wide path) if any span's
    reference cannot be placed whole. A span whose lineup the document
    reference cannot express is evidence that the segmentation is wrong, and
    guessing past it would be worse than not splitting at all.
    """
    plans: list[tuple[list[SystemView], list[Slot], list[int]]] = []
    for span in spans:
        span_view = reference_view(span)
        if span_view is None:
            return False
        to_global = align(span_view, reference)
        if any(g < 0 for g in to_global):
            return False
        plans.append((span, _slots_of(span_view), to_global))

    for span, span_reference, to_global in plans:
        for view in span:
            for staff, local in zip(view.staves, align(view, span_reference)):
                staff.slot_index = to_global[local] if local >= 0 else -1
    return True
