"""A bar's LENGTH, from the durations standing in it -- the one helper every consumer asks (ROADMAP 2.162; the bar-length
half of 2.165's shared override check, Sean 2026-10-17 DECISIONS).

    bar_length(log, cell, notes) -> BarLength          # EVALUATE / INFER: a cell, its standing duration verdicts
    length_of_events(events)     -> BarLength          # any caller that has already grouped the verdicts (ADJUDICATE)

A `BarLength` is one of three things:

* KNOWN  -- `lo == hi`: every event's value is DECIDED (or, flag off, a narrowing counted at its FIRST candidate -- the
  pre-2.162 reading, kept bit-for-bit so the flag-off path is unchanged);
* a RANGE -- `lo < hi` (or `ranged`): under `OMR_NARROWED_BAR_LENGTH_UNKNOWN` a bar holding a NARROWED note has no known
  length, only the sum at every narrowing's shortest candidate .. at its longest. A range may only CONFIRM: a meter whose
  length lies inside it (`contains`), never refute one;
* UNKNOWN -- the bar cannot be summed at all (no decided grouping; a standing verdict that admits no length where the caller
  asked `missing="unknown"`).

Sean 2026-10-17 (DECISIONS): *"a bar holding an undecided note has no known length: it may not vote against a meter, refute
a carried meter, or undo a bar-sum move"*. CLAUDE.md §4: the bar sum is the weakest witness and can only confirm.

One event contributes ONE duration: the MODE of its members' values when all are known (`voicing.group_chords_in_measure`'s
own definition of an event's duration); an event holding a narrowed member spans the shortest to the longest length any of
its members admits (which head is right is exactly what is undecided).
"""
from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from .record import Outcome, Q

#: ROADMAP 2.162, default ON (Sean 2026-10-18): unset = ON, an explicit `0/false/no/off` disables.
NARROWED_BAR_LENGTH_UNKNOWN_ENV = "OMR_NARROWED_BAR_LENGTH_UNKNOWN"

EPS = 1e-6


def narrowed_bar_length_unknown() -> bool:
    raw = os.environ.get(NARROWED_BAR_LENGTH_UNKNOWN_ENV)
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")


@dataclass(frozen=True)
class BarLength:
    lo: Optional[float]
    hi: Optional[float]
    ranged: bool = False          # a narrowed note made this a range (even where lo == hi)

    @property
    def unknown(self) -> bool:
        return self.lo is None

    @property
    def known(self) -> bool:
        """A single, certain length (no range, not unknown)."""
        return not self.unknown and not self.ranged

    @property
    def value(self) -> Optional[float]:
        """The length where it is KNOWN, else None."""
        return self.lo if self.known else None

    def contains(self, length: float) -> bool:
        return not self.unknown and self.lo - EPS <= length <= self.hi + EPS

    def shifted(self, delta: float) -> "BarLength":
        return self if self.unknown else BarLength(self.lo + delta, self.hi + delta, self.ranged)


UNKNOWN = BarLength(None, None)


def _range_of(v, first_candidate: bool):
    """(lo, hi, ranged) for one standing duration verdict, or None where it admits no length."""
    if v.outcome is Outcome.DECIDED:
        if not v.value:
            return None
        b = float(v.value.get("beats") or 0.0) if isinstance(v.value, dict) else 0.0
        return (b, b, False)
    cands = [c.value for c in (v.candidates or ()) if isinstance(c.value, dict)]
    if not v.candidates:
        return None
    if first_candidate:
        val = v.candidates[0].value
        if not val:
            return None
        b = float(val.get("beats") or 0.0)
        return (b, b, False)
    beats = [float(c.get("beats")) for c in cands if c.get("beats") is not None]
    if not beats:
        return None
    return (min(beats), max(beats), True)


def length_of_events(events: Iterable[Sequence], *, missing: str = "unknown",
                     first_candidate: Optional[bool] = None) -> BarLength:
    """The length of a bar given as EVENTS, each a sequence of standing duration verdicts (one per glyph; a loose glyph is
    an event of one). `missing="unknown"`: a verdict admitting no length makes the bar UNKNOWN; `"skip"`: it is passed over
    (the meter witness's reading). `first_candidate=None` follows the flag (off -> a narrowing counts at its first candidate,
    the pre-2.162 reading); `True` forces that reading -- only for 2.154's bare-stem confirm, which the 2.162 brief keeps as
    it is."""
    if first_candidate is None:
        first_candidate = not narrowed_bar_length_unknown()
    lo = hi = 0.0
    ranged = False
    for event in events:
        parts = []
        for v in event:
            if v is None:
                continue
            r = _range_of(v, first_candidate)
            if r is None:
                if missing == "unknown":
                    return UNKNOWN
                continue
            parts.append(r)
        if not parts:
            continue
        if any(p[2] for p in parts):
            ranged = True
            lo += min(p[0] for p in parts)
            hi += max(p[1] for p in parts)
        else:
            mode = Counter(p[0] for p in parts).most_common(1)[0][0]
            lo += mode
            hi += mode
    return BarLength(lo, hi, ranged)


def bar_length(log, cell, notes: Sequence, *, first_candidate: Optional[bool] = None) -> BarLength:
    """The length of `cell` over `notes` (its standing duration verdicts still in the bar), counted per DECIDED `Q.EVENT`
    grouping; a note the grouping does not mention is still time in the bar (an event of its own). UNKNOWN without a
    decided grouping, or where a note admits no length."""
    grouping = log.verdict(Q.EVENT, cell)
    if grouping is None or grouping.outcome is not Outcome.DECIDED:
        return UNKNOWN
    by_glyph = {v.subject.glyph: v for v in notes}
    events: List[List] = []
    seen = set()
    for event in (grouping.value or {}).get("events", ()):
        members = [by_glyph[g] for g in event.get("glyphs", ()) if g in by_glyph]
        if members:
            events.append(members)
            seen.update(m.id for m in members)
    events += [[v] for v in notes if v.id not in seen]
    return length_of_events(events, missing="unknown", first_candidate=first_candidate)
