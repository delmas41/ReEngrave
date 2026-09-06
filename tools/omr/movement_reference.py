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


def lineup_spans(page_systems: Sequence[tuple[int, Sequence[int]]]
                 ) -> list[list[int]]:
    """Partition pages into lineup spans. Returns lists of page indices.

    `page_systems` is `(page_index, [system sizes])` per page, in any order.
    Returns a single span — i.e. today's behaviour — whenever the rule finds no
    boundary it can prove, which includes every run too short to prove one.
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
    if len(spans) > 1 and not _well_supported(spans, page_systems):
        return [[p for p, _ in page_systems]]
    # Pages with no staves at all (front matter) belong to whichever span
    # follows them; they carry nothing either way.
    return _readmit_empty(spans, [p for p, _ in page_systems])


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
