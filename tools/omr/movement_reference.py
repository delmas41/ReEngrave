"""Where in a document the ORCHESTRA changes — so a page is aligned against its
own movement's lineup rather than the whole volume's.

## The bug this exists for

`slots.build_reference` picks one reference layout for the entire run: the
largest recurring system size across every page it was given. Over a few pages
that is the work's lineup. Over a whole VOLUME it is the lineup of whichever
movement has the most instruments — for Beethoven 5 / Litolff, the finale's 17
staves, because the trombones, piccolo and contrabassoon enter only there.

`slots.align` must then decide which 5 of those 17 slots a twelve-staff
movement-1 system omits, and it decides it on the evidence the page gives. That
evidence is publisher-shaped: Litolff labels the winds and brass on **every**
system and the strings on **none**, so the winds and brass pin themselves
correctly and the unlabelled strings take whatever is left over — which, in a
finale reference, is the trombone slots. Measured on the 88-page run: **91 of
855 movement-1..3 staff records (10.6%) are named an instrument the movement
does not contain**, 75 of them Trombone. Page 23's Violin I, Violin II and
Viola come out as three trombones.

The aligner is not wrong about a violin. The violin had no evidence and the
trombone slot was vacant.

## The rule, and why it is exactly this one

A system may OMIT the staves of parts that are tacet through it; it can never
INVENT one. That is the same subsequence axiom `roster.py` is built on, and it
is the whole of the segmentation:

> **A page whose largest system is larger than every page before it has proved
> that the lineup GREW there.** Nothing else in the size series is evidence of a
> boundary — a dip is tacet suppression, and equality is silence.

So the boundaries are the pages that set a new running maximum, and there is no
window, no smoothing and no tolerance to tune. Two refusals guard it, and both
are borrowed rather than invented:

* a system more than `REFERENCE_MAX_SIZE_RATIO` times the median is a probable
  CONCATENATION and is refused, exactly as `build_reference` refuses it — one
  merged system would otherwise invent a lineup boundary on its own page
  (Brahms 1 prints 86 pages of 10-17 staves and one "28");
* the new level must RECUR. A lineup is the orchestra and the orchestra recurs;
  a size seen on exactly one page is a segmentation wobble, and this is again
  `build_reference`'s own test.

## What it deliberately does NOT detect

**Movement boundaries.** It detects LINEUP boundaries, and the difference is the
honest part: Beethoven 5 has four movements and this finds one boundary,
because movements 1, 2 and 3 are played by the same twelve staves. A movement
boundary that does not change the lineup does not need finding — the reference
either side of it is the same object, so splitting there is provably free and
provably useless. Claiming to find movements would be claiming an accuracy this
cannot have.

A movement that SHRINKS the lineup is likewise invisible, and that is the
conservative direction: such a page keeps today's behaviour rather than
acquiring a reference on no evidence.

## Why the recurrence test is what protects the ad-hoc page set

`--pages 1,44` of that same Beethoven scores 27/29 today, because movement 1's
lineup is a strict subsequence of the finale's and the aligner skips the extra
slots correctly when the page's own labels are complete. Widening HELPS there.
A run of two pages offers each level exactly once, neither recurs, no boundary
is taken, and the run keeps the document-wide reference it has now — not by a
special case but by the same rule.
"""

from __future__ import annotations

import collections
import os
from typing import Sequence

#: Refuse a system this many times the median as a probable concatenation.
#: Mirrors `slots.REFERENCE_MAX_SIZE_RATIO`; kept separate only so this module
#: does not import `slots` (which imports this).
MERGE_CAP_RATIO = 2.0

#: A span this short is not a movement worth referencing on its own. Both
#: numbers sit on a wide plateau rather than a cliff: the whole-work spans
#: measured are 39-45 pages and 38-80 systems, and the ad-hoc page sets this
#: must not disturb are 1-3 pages, so no value between 2 and ~30 changes any
#: measured outcome. They are a floor against a pathological segmentation, not
#: a tuned discriminator.
MIN_SPAN_PAGES = 4
MIN_SPAN_SYSTEMS = 6


def enabled() -> bool:
    """`OMR_MOVEMENT_REFERENCE` — align each page against its own movement's
    lineup instead of the whole document's.

    **DEFAULT ON since 2026-09-06** (Sean's call, delegated on the numbers).
    Whole work, Beethoven 5 / Litolff, 88 pages, 1616 staff records: instruments
    the movement cannot contain **91 → 0**, and correct names **750 → 756** —
    it removes the falsehood by *naming*, not by refusing, which is the better
    kind of fix. Boundary detection: **0 false boundaries over 4 works and 310
    pages**, from an axiom rather than a threshold — *a system may omit the
    staves of tacet parts, but it can never invent one, so a page whose largest
    system exceeds every page before it has proved the lineup GREW there.*

    ⚠️ **IT MUST BE PAIRED WITH `OMR_ABSENT_INSTRUMENT_VETO`, and the reason is
    measured.** On a run that starts MID-MOVEMENT this flag alone makes things
    *worse* — a 24-page window went **44 → 57** impossible, turning 9 correct
    string names into `Trombone`. The mechanism is not the segmentation (both
    page sets cut identically) but the span's own reference: **a span lacking
    its movement's opening page has no fully-labelled system**, so its
    unlabelled string slots land on the document's Trombone slots by position.
    The veto cleans that up (57 → 0). Turning this on alone re-introduces the
    bug it fixes, on exactly the runs a reader is most likely to make by hand.

    ⚠️ **Neither standing benchmark can price this** — all 20 scan-gate rows and
    every `orchestral_eval` excerpt are single-page, so spans take no boundary
    at all and both flags are no-ops there. The evidence is the whole-work
    measurement, **n=1 work for the identity numbers**, and that is the honest
    bound on it.

    Full record: `benchmarks/omr-spans-veto-composition-2026-09/FINDINGS.md`.
    """
    return os.environ.get("OMR_MOVEMENT_REFERENCE", "1").strip().lower() in (
        "1", "true", "yes", "on")


def swap_split_enabled() -> bool:
    """`OMR_LINEUP_SWAP_SPLIT` — split a span where the PRINTED NAMES change
    even though the staff count does not. **Default OFF.**

    ## The case the count axiom cannot reach

    Everything above keys on staff COUNT, on the axiom that a system may omit
    tacet parts but never invent one, so a new running maximum proves growth.
    **A lineup SWAP at constant size is outside that axiom**, and Brahms 4 /
    Breitkopf is the first measured document where it occurs: movements III and
    IV both print 16 staves and their lineups differ —

        III   Fl Picc Ob Cl Fag Kfag Hn Hn Tpt Timp Triangel + 5 strings
        IV    Fl      Ob Cl Fag Kfag Hn Hn Tpt Tbn Tbn Timp  + 5 strings

    so pages 41-98 are ONE span, pages 41 and 76 get the byte-identical
    16-name assignment, and every movement-IV wind lands one slot low.

    ## The signal, and why it is the printed names

    Staff count is silent about a swap; the margin is not. Within one lineup a
    FULL system — one whose staff count equals the span's maximum — carries
    every staff the region has, in printed order, so staff ordinal *i* names
    the same instrument on every full system of that lineup. Two full systems
    that disagree at an ordinal are therefore evidence of two lineups, and a
    split page *q* is SUPPORTED by each ordinal where the full systems left of
    *q* have one clear majority name and those from *q* on have a different
    one.

    Measured over 122 candidate split pages in 7 count-derived spans of 4
    hand-read works: the largest support at a page inside a span that holds ONE
    lineup is **1**; Brahms 1's small swap (a horn staff out, a solo violin in)
    scores **2** at exactly the right page; Brahms 4's is **8**. The rule fires
    on Brahms 4 at page 67 — the hand-read boundary — and on nothing else.

    ⚠️⚠️ **AND THE SPLIT IS MEASURED WORSE, WHICH IS WHY IT IS OFF.** Detecting
    the boundary is not the problem; the problem is downstream of it. The
    document reference is ONE PRINTED SYSTEM and `slot_instruments` gives each
    slot one name for the whole document, so a span whose lineup is not a
    subsequence of that system cannot be named however its staves are grouped —
    and a constant-count SWAP is precisely two lineups neither of which
    contains the other. Brahms 4's largest printed system is 16 staves and the
    union of its lineups needs 18; movement IV is short exactly two Trombone
    slots. The current output is already AT that ceiling (176 of 352 judgeable
    staves, and the identity placement of a 16-staff system into a 16-slot
    reference scores exactly 8 of 16), so there is nothing to win and the split
    took **556 → 512** correct names, in BOTH reference regimes measured.

    **The count axiom is not merely a way of finding boundaries; it is what
    makes the span mechanism sound.** A boundary taken only where the lineup
    GREW guarantees the largest printed system is a superset of every span's
    lineup — measured true on Beethoven 5 (union 17, largest 17) and Beethoven
    6 (14, 14), the two works spans repair — and false on Brahms 1 (17 vs 16)
    and Brahms 4 (18 vs 16), the two with a swap. Widening the boundary rule
    without widening the reference's vocabulary breaks that invariant.

    The lever that DOES move this work is the reference contest, not the
    segmentation: seven Brahms 4 systems tie at 16 staves and 15 labels and
    `max` takes the earliest, making movement III's lineup the document's
    vocabulary. Breaking that tie by how many systems share the lineup — the
    `shapes[_shape(v)]` term `slots.reference_candidates` already uses for its
    TAIL and not for its head — scores **556 → 682** on Brahms 4 and is
    byte-identical on Beethoven 5 and Beethoven 6. That change is in
    `slots.py` and is not made here.

    ## What it deliberately cannot do

    * **It only SUBDIVIDES** a count-derived span; it can never merge two.
    * **A small swap is invisible.** Two instruments trading places supports 2
      ordinals and stays under the bar. Under-splitting is the safe direction:
      a wrong extra boundary is inherited by every system after it, which is
      exactly how 149 wrong names arose on Brahms 1 from one bad reference.
    * **A tie refuses.** Two candidate pages with equal support means the
      evidence does not LOCATE the boundary, and a boundary in the wrong place
      hands one movement's pages the other's reference. Same distinction
      `_first_page_above` draws: evidence may confirm a boundary without being
      allowed to place one.
    * **No labels, no split.** A publisher that does not label, or a span with
      too few full systems, keeps today's answer.

    Full record: `benchmarks/omr-lineup-swap-2026-09/FINDINGS.md`.
    """
    return os.environ.get("OMR_LINEUP_SWAP_SPLIT", "0").strip().lower() in (
        "1", "true", "yes", "on")


#: A side of a candidate swap split needs this many FULL systems to speak.
MIN_SIDE_SYSTEMS = 3
#: An ordinal needs this many observed labels on a side before it may vote.
MIN_SIDE_OBS = 3
#: ...and that side's majority name must be this share of them. A full system's
#: margin is read imperfectly (a `Kleine Flöte` read as `Flöte`), so unanimity
#: would silence the ordinals that carry the whole signal.
MIN_MAJORITY = 0.6
#: How many ordinals must disagree before a swap is asserted. Measured over 122
#: candidate split pages of 4 works: the largest support at a page inside a
#: ONE-LINEUP span is 1, Brahms 1's real but SMALL swap scores 2, and Brahms 4's
#: scores 8. Anywhere in 3..8 reproduces every result recorded in
#: `benchmarks/omr-lineup-swap-2026-09/FINDINGS.md`; 4 is the middle of it.
#: ⚠️ 2 is not in the range and that is deliberate — it would catch Brahms 1's
#: swap, and catching a swap is only worth having if splitting on it helps.
MIN_SWAP_SUPPORT = 4


def lineup_spans(page_systems: Sequence[tuple[int, Sequence[int]]],
                 page_labels: Sequence[tuple[int, Sequence[Sequence[object]]]]
                 | None = None) -> list[list[int]]:
    """Partition pages into lineup spans. Returns lists of page indices.

    `page_systems` is `(page_index, [system sizes])` per page, in any order.
    Returns a single span — i.e. today's behaviour — whenever the rule finds no
    boundary it can prove, which includes every run too short to prove one.

    `page_labels` is the optional margin evidence the swap split needs:
    `(page_index, [[instrument name or None, per staff of the system]])`, in
    the same system order as `page_systems`. **Omitting it, or leaving
    `OMR_LINEUP_SWAP_SPLIT` off, returns exactly the count-derived spans** —
    the swap split can only subdivide them.
    """
    peak = _peaks(page_systems)
    if not peak:
        return [[p for p, _ in page_systems]]
    pages = sorted(peak)
    counts = collections.Counter(peak.values())

    starts: list[int] = [pages[0]]
    running = peak[pages[0]]
    seen_at_running = 1
    for p in pages[1:]:
        v = peak[p]
        if v == running:
            seen_at_running += 1
            continue
        if v < running:
            continue
        if counts[v] < 2:
            # A one-off larger system is a wobble, not a lineup. It must not
            # raise the running maximum either, or the real level that follows
            # it can never be seen to exceed it.
            continue
        if seen_at_running < 2:
            # ⚠️ BOTH SIDES OF A BOUNDARY MUST BE ESTABLISHED, and this half was
            # missing until a run that STARTED MID-MOVEMENT measured it. A run
            # beginning at a condensed page climbs to its own movement's lineup
            # — 8 staves, then 11, then 12 across Beethoven 5's pages 20-23 —
            # and each step up looked like the orchestra growing. It is not: it
            # is the same orchestra, seen more completely. You cannot say the
            # lineup GREW unless you knew what it was, so the level being left
            # must itself have recurred among the pages already passed.
            running, seen_at_running = v, 1
            continue
        starts.append(_first_page_above(pages, peak, p, running))
        running, seen_at_running = v, 1

    spans = _split_at(pages, starts)
    swap = page_labels is not None and swap_split_enabled()
    if len(spans) > 1 and not _well_supported(spans, page_systems):
        # ⚠️ The early return is kept on the flag-off path rather than folded
        # into the code below, so flag-off is identical by CONSTRUCTION and not
        # merely by argument: this returns the caller's own page order, where
        # `_readmit_empty` returns a sorted one.
        if not swap:
            return [[p for p, _ in page_systems]]
        spans = [pages]
    if swap:
        spans = _apply_swap_splits(spans, page_systems, page_labels)
        if len(spans) > 1 and not _well_supported(spans, page_systems):
            return [[p for p, _ in page_systems]]
    # Pages with no staves at all (front matter) belong to whichever span
    # follows them; they carry nothing either way.
    return _readmit_empty(spans, [p for p, _ in page_systems])


# ── the swap split ──────────────────────────────────────────────────────────
# Everything below runs only under `OMR_LINEUP_SWAP_SPLIT` and only when the
# caller supplied margin evidence. It subdivides; it never merges.


def _apply_swap_splits(spans, page_systems, page_labels) -> list[list[int]]:
    sizes = {p: list(s) for p, s in page_systems}
    labels = {p: [list(v) for v in s] for p, s in page_labels}
    out: list[list[int]] = []
    for span in spans:
        out += _swap_split(span, sizes, labels)
    return out


def _full_systems(span, sizes, labels):
    """`[(page, [name|None per staff])]` for the span's FULL systems.

    A full system is one whose staff count equals the largest in the span —
    `score_full_systems.py`'s definition, and for its reason: a system carrying
    every staff the region has IS that region's lineup, in printed order, so
    ordinals correspond across full systems and only across those.

    ⚠️ `MERGE_CAP_RATIO` applies here for the same reason it applies in
    `_peaks`, and it is not decoration: on Brahms 1 one page of the finale span
    is read as a single 28-staff system, and taking that as the span's width
    left the span with ONE full system and silenced the detector over 41 pages.
    """
    span_sizes = [n for p in span for n in sizes.get(p, [])]
    if not span_sizes:
        return []
    ordered = sorted(span_sizes)
    cap = ordered[len(ordered) // 2] * MERGE_CAP_RATIO
    pages_at: dict[int, set] = {}
    for p in span:
        for n in sizes.get(p, []):
            if n <= cap:
                pages_at.setdefault(n, set()).add(p)
    # ⚠️ THE SPAN'S WIDTH MUST RECUR, and this is `build_reference`'s own test
    # for `build_reference`'s own reason: a size seen on ONE page is a
    # segmentation wobble, not a lineup. Brahms 1's finale span reads 17 staves
    # on exactly one page against a printed 16, and taking the max left the
    # span with a single full system and no detector over 41 pages.
    recurring = [n for n, ps in pages_at.items() if len(ps) >= 2]
    if not recurring:
        return []
    width = max(recurring)
    out = []
    for p in sorted(span):
        for si, n in enumerate(sizes.get(p, [])):
            if n != width:
                continue
            row = labels.get(p, [])
            seq = list(row[si]) if si < len(row) else []
            seq += [None] * (width - len(seq))
            out.append((p, seq[:width]))
    return out


def _majority(values):
    seen = [v for v in values if v is not None]
    if len(seen) < MIN_SIDE_OBS:
        return None, 0.0
    name, n = collections.Counter(seen).most_common(1)[0]
    return name, n / len(seen)


def _support(left, right) -> tuple[int, float]:
    """`(disagreeing ordinals, purity)` for one candidate split.

    ⚠️ **TWO NUMBERS, AND THE SECOND IS WHAT LOCATES THE BOUNDARY.** The first
    is the gate — how much of the lineup changed — and it is deliberately
    tolerant of a misread margin, so on a clean document it is FLAT: a split
    five pages early still leaves the right-hand side with a two-thirds
    majority for the new lineup and scores identically. Purity — the share of
    observations that agree with their own side's majority — is 1.0 only where
    both sides are one lineup, so it peaks at the boundary and nowhere else.

    Same division of labour as `_first_page_above`: the coarse test CONFIRMS a
    boundary, and something finer has to PLACE it.
    """
    if not left or not right:
        return 0, 0.0
    n = 0
    seen = agreed = 0
    for i in range(len(left[0][1])):
        a, fa = _majority([s[1][i] for s in left])
        b, fb = _majority([s[1][i] for s in right])
        if a is None or b is None or fa < MIN_MAJORITY or fb < MIN_MAJORITY:
            continue
        if a != b:
            n += 1
        for side, name in ((left, a), (right, b)):
            obs = [s[1][i] for s in side if s[1][i] is not None]
            seen += len(obs)
            agreed += sum(1 for v in obs if v == name)
    return n, (agreed / seen if seen else 0.0)


def _swap_split(span, sizes, labels) -> list[list[int]]:
    """One count-derived span, subdivided where the printed names change."""
    systems = _full_systems(span, sizes, labels)
    scored: list[tuple[int, float, int]] = []
    for q in sorted({p for p, _ in systems})[1:]:
        left = [s for s in systems if s[0] < q]
        right = [s for s in systems if s[0] >= q]
        if len(left) < MIN_SIDE_SYSTEMS or len(right) < MIN_SIDE_SYSTEMS:
            continue
        n, purity = _support(left, right)
        scored.append((n, purity, q))
    if not scored:
        return [span]
    best = max(s[:2] for s in scored)
    if best[0] < MIN_SWAP_SUPPORT:
        return [span]
    at = [q for n, purity, q in scored if (n, purity) == best]
    if len(at) != 1:
        # ⚠️ A tie does not locate the boundary, and a boundary in the wrong
        # place is worse than none: every page after it inherits the other
        # movement's reference. Refuse rather than pick.
        return [span]
    q = at[0]
    a = [p for p in span if p < q]
    b = [p for p in span if p >= q]
    if not a or not b:
        return [span]
    if not _well_supported([a, b], [(p, sizes.get(p, [])) for p in span]):
        return [span]
    # Recurse: a span may hold more than two lineups. Each level faces the same
    # bar, so a second split needs its own evidence.
    return _swap_split(a, sizes, labels) + _swap_split(b, sizes, labels)


def _first_page_above(pages: list[int], peak: dict[int, int], p: int,
                      level: int) -> int:
    """Walk the boundary BACK to where the lineup actually grew.

    ⚠️ RECURRENCE CONFIRMS A BOUNDARY; IT MUST NOT LOCATE ONE — measured, and
    the page it costs is the worst possible one. A movement's opening page is
    where the new instruments first print, but it is also a page phase 1 can
    under-read (Beethoven 5 p.44 detected 14 staves of 17 in one run), and a
    size seen once never recurs. So the boundary landed on p.45 and p.44 — the
    finale's own first page — was aligned against movement 1's twelve slots: 10
    staff records, every one of them wrong.

    The growth began at the first page of the unbroken run above the old level.
    """
    out = p
    for q in reversed([x for x in pages if x < p]):
        if peak[q] > level:
            out = q
            continue
        break
    return out


def _peaks(page_systems) -> dict[int, int]:
    sizes = [s for _p, systems in page_systems for s in systems]
    if not sizes:
        return {}
    ordered = sorted(sizes)
    median = ordered[len(ordered) // 2]
    cap = median * MERGE_CAP_RATIO
    out: dict[int, int] = {}
    for page_index, systems in page_systems:
        keep = [s for s in systems if s <= cap]
        if keep:
            out[page_index] = max(keep)
    return out


def _split_at(pages: list[int], starts: list[int]) -> list[list[int]]:
    starts = sorted(set(starts))
    spans: list[list[int]] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else None
        spans.append([p for p in pages
                      if p >= start and (end is None or p < end)])
    return [s for s in spans if s]


def _well_supported(spans: list[list[int]], page_systems) -> bool:
    n_systems = {p: len(systems) for p, systems in page_systems}
    for span in spans:
        if len(span) < MIN_SPAN_PAGES:
            return False
        if sum(n_systems.get(p, 0) for p in span) < MIN_SPAN_SYSTEMS:
            return False
    return True


def _readmit_empty(spans: list[list[int]], all_pages: Sequence[int]
                   ) -> list[list[int]]:
    placed = {p for span in spans for p in span}
    missing = sorted(p for p in all_pages if p not in placed)
    if not missing:
        return spans
    out = [list(s) for s in spans]
    for p in missing:
        target = 0
        for i, span in enumerate(out):
            if span and span[0] <= p:
                target = i
        out[target].append(p)
    return [sorted(s) for s in out]
