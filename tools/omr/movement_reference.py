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

    **Default OFF.** A default flip is a decision with a number attached, and
    the number is in `benchmarks/omr-movement-reference-2026-09/`.
    """
    return os.environ.get("OMR_MOVEMENT_REFERENCE", "0").strip().lower() in (
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
    for p in pages[1:]:
        v = peak[p]
        if v > running and counts[v] > 1:
            starts.append(p)
            running = v
        elif v > running:
            # A one-off larger system is a wobble, not a lineup. It must not
            # raise the running maximum either, or the real level that follows
            # it can never be seen to exceed it.
            continue

    spans = _split_at(pages, starts)
    if len(spans) > 1 and not _well_supported(spans, page_systems):
        return [[p for p, _ in page_systems]]
    # Pages with no staves at all (front matter) belong to whichever span
    # follows them; they carry nothing either way.
    return _readmit_empty(spans, [p for p, _ in page_systems])


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
