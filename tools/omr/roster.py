"""The document's instrument ROSTER — read once, available to every page.

## What was missing

`transcribe` is asked for a set of pages and reads only those. A conductor's
score, however, names its instruments in the margin of **one system** — the
first of the movement — and prints nothing, or an abbreviation, on every page
after it. So a run over page 40 of a Simrock Dvořák sees a page with no names at
all, and identity there fell to the score-order prior, which is right about
roughly nine staves in ten.

Everything needed to fix that was measured in
`benchmarks/omr-staff-identity-layer-2026-09/` and none of it was wired:

* the roster procedure holds — every later system is a strict SUBSEQUENCE of the
  work's first labelled system, 11 of 11 systems, zero violations;
* acquisition is **51 of 51 named positions correct, zero misnamed** through the
  real label ladder (coverage 0.962). The reader names a staff correctly or says
  nothing;
* carrying that observed identity onto later pages is **22 of 22 correct**
  (`probe_roster_carry.py`) — while carrying DERIVED identity the same way is
  0.550 and drags pooled precision below the observed rate.

That last pair is the design rule this module is built on, and it is why
provenance is per-FACT rather than per-document: **only label-sourced identity
is carried. Derived identity is recomputed per page and never travels.**

## What this module does

`acquire_roster` finds the first system of the document that carries instrument
names, reads it through the ordinary label ladder ONCE, and returns it as
evidence. The caller aligns it into slot space with the same DP every other
system goes through (`slots.align`), so a roster name reaches a page that prints
nothing.

⚠️ **A roster is ONE SYSTEM's, never one page's.** Brahms 1 / Breitkopf p.1 is
27 staves in two systems; reading "the page" reports the orchestra twice and the
alignment then has a reference that repeats itself. The search is per SYSTEM and
stops at the first one that resolves anything.

⚠️ **"Page 1" is the wrong unit.** Measured over 234 documents, 8.1% give up
their roster only beyond the first three pages — front matter, a title page, a
publisher's index. So the search runs a bounded WINDOW and records which pages
it opened, rather than assuming the first.

⚠️ **There is no yield threshold, deliberately.** Every read becomes a partial
roster and the alignment decides what to do with it. A 0.50 floor tried earlier
in this workstream turned 29 documents into false negatives — a roster naming
three staves of twenty is still three staves more than the prior knows.

⚠️ **The read is CACHED, never repeated.** Surya has a known temperature
nondeterminism (`contextual.py`, "45 replays of frozen crop bytes"), so re-reading
the same margin on a later page could resolve differently and the layer would
stop being reproducible within one run.

⚠️ **Holes are DROPPED, not healed and not wildcarded.** A partial roster is
measured at 0.848 with its holes simply absent, 0.841 with neutral placeholders
pinned at their own ordinals (refuted — a placeholder is not the missing name),
and 0.876 with the layout prior filling the gaps. **Healing is CLOSED** (Sean,
2026-09-05): the catalog tier supplies which instruments exist far better than a
positional guess, and healing tops out exactly where multiplicity begins.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from .types import PageWithStaves, Staff

logger = logging.getLogger(__name__)

# How many pages from the front of the document may be opened looking for a
# labelled system. Measured over 234 documents: 0.735 of them give up a roster
# on page 1 as the sweep gated it, and the population is BIMODAL — a document
# either names its first system or carries front matter first. Three pages
# covers 91.9%; the tail is title pages and publisher indices, and paying for
# more pages on every document to reach it is not obviously worth it. Reported
# per run as `pages_searched`, so the cost is never hidden.
ROSTER_PAGE_WINDOW = 3

# Fewer names than this is not a roster, it is a stray word the lexicon
# happened to match. ⚠️ This is NOT the refused yield THRESHOLD — that one was
# a fraction of the system's staves (0.50) and turned 29 documents into false
# negatives. This is an absolute floor of two, which only ever rejects a system
# where a single word resolved; such a system is indistinguishable from a
# tempo marking read as an instrument.
MIN_ROSTER_NAMES = 2


def enabled() -> bool:
    """`OMR_ROSTER` — acquire and use a document-level roster.

    ⚠️ DEFAULT OFF pending Sean's call on the default. The measurements are in
    `benchmarks/omr-roster-wiring-2026-09/FINDINGS.md`; the acquisition and its
    evidence block are recorded regardless of this flag, because recording what
    was read changes no music and a fact that is computed and discarded is the
    shape this project has paid for nine times.
    """
    return os.environ.get("OMR_ROSTER", "0").strip().lower() in (
        "1", "true", "yes", "on")


@dataclass(frozen=True)
class RosterEntry:
    """One position of the roster system, as READ."""

    ordinal: int                  # position within the roster SYSTEM, top down
    instrument: str               # canonical `instruments.Instrument` name
    text: str                     # the raw margin text, kept for auditing
    confidence: str


@dataclass(frozen=True)
class Roster:
    """The document's instrument lineup, read off one system of one page."""

    page_index: int
    system_index: int
    n_staves: int                 # staves in the roster SYSTEM, not the page
    entries: tuple[RosterEntry, ...]
    pages_searched: tuple[int, ...]
    pages_opened: tuple[int, ...]  # pages this had to render itself
    tiers: tuple[int, ...] = (0, 0, 0, 0, 0)
    staves: tuple[Staff, ...] = field(default=(), repr=False, compare=False)

    @property
    def names(self) -> dict[int, str]:
        return {e.ordinal: e.instrument for e in self.entries}

    @property
    def coverage(self) -> float:
        return len(self.entries) / self.n_staves if self.n_staves else 0.0

    def evidence(self) -> dict[str, Any]:
        """The block written into the result JSON. Data, never a decision."""
        return {
            "page_index": self.page_index,
            "system_index": self.system_index,
            "n_staves": self.n_staves,
            "named": len(self.entries),
            "coverage": round(self.coverage, 4),
            "pages_searched": list(self.pages_searched),
            "pages_opened": list(self.pages_opened),
            "label_tiers": {"text_layer": self.tiers[0], "surya": self.tiers[1],
                            "tesseract": self.tiers[2], "vision": self.tiers[3],
                            "human": self.tiers[4]},
            "entries": [{"ordinal": e.ordinal, "instrument": e.instrument,
                         "text": e.text, "confidence": e.confidence}
                        for e in self.entries],
        }


def _systems(pws: PageWithStaves) -> list[tuple[int, list[Staff]]]:
    """Each system of a page in printed order, staves top to bottom.

    ⚠️ Systems, not the page. See the module docstring — a first page holding
    two systems reports the orchestra twice if the page is taken whole.
    """
    by_system: dict[int, list[Staff]] = {}
    for staff in pws.staves:
        by_system.setdefault(staff.system_index, []).append(staff)
    return [(i, sorted(by_system[i], key=lambda s: s.top_y))
            for i in sorted(by_system)]


def _roster_from(pws: PageWithStaves, labels, page_index: int
                 ) -> Roster | None:
    """A roster from one page's staves and its already-read labels, or None.

    Systems are tried in printed order and the FIRST that resolves enough names
    wins. Trying only the topmost would miss a page whose opening system is a
    continuation and whose second system starts a movement — and trying them all
    and pooling would be the two-systems-on-one-page trap the docstring names.
    """
    for system_index, staves in _systems(pws):
        roster = _roster_from_system(staves, labels, page_index, system_index)
        if roster is not None:
            return roster
    return None


def _roster_from_system(staves: list[Staff], labels, page_index: int,
                        system_index: int) -> Roster | None:
    if not staves:
        return None
    ordinal_of = {st.staff_index: i for i, st in enumerate(staves)}
    entries = []
    for label in labels:
        ordinal = ordinal_of.get(label.staff_index)
        if ordinal is None or not label.matched:
            continue
        if label.confidence not in ("high", "medium"):
            # Same floor `slots.labels_by_staff` uses: a low-confidence read
            # would propagate one wrong instrument onto every page of the run,
            # which is the one failure mode a roster has that a page read does
            # not.
            continue
        entries.append(RosterEntry(ordinal=ordinal,
                                   instrument=label.instrument.name,
                                   text=(label.text or "").strip(),
                                   confidence=label.confidence))
    entries.sort(key=lambda e: e.ordinal)
    # One ordinal, one name. A duplicate is a reader artefact, not two staves.
    seen: set[int] = set()
    entries = [e for e in entries if not (e.ordinal in seen or seen.add(e.ordinal))]
    if len(entries) < MIN_ROSTER_NAMES:
        return None
    return Roster(page_index=page_index, system_index=system_index,
                  n_staves=len(staves), entries=tuple(entries),
                  pages_searched=(), pages_opened=(),
                  staves=tuple(staves))


def acquire_roster(
    *,
    pdf_path: Path,
    dpi: int,
    run_pages: Sequence[int],
    run_staves: Sequence[PageWithStaves],
    run_labels: Sequence[list],
    read_labels: Callable[[PageWithStaves, int], list],
    window: int = ROSTER_PAGE_WINDOW,
    n_pages: int | None = None,
) -> Roster | None:
    """Find and read the document's roster system. Called ONCE per run.

    Pages already transcribed by this run are consulted FIRST and cost nothing —
    their staves are detected and their margins read already. Only if none of
    them carries a labelled first system does this open a page of its own, and
    it opens at most `window` of them from the front of the document.

    ⚠️ The in-run pages are tried in PAGE order, not in the order they were
    requested, so a run over pages 5 and 2 acquires from 2. A roster is a
    property of the document, and which page the caller happened to list first
    is not evidence about where the orchestra is named.

    `read_labels(pws, page_index)` is the label ladder, injected so this module
    neither imports the reader stack nor decides what `assist` may spend.
    """
    searched: list[int] = []
    opened: list[int] = []

    # ── Free tier: pages this run already has ───────────────────────────────
    in_run = sorted(zip(run_pages, range(len(run_pages))))
    for page_index, i in in_run:
        searched.append(page_index)
        roster = _roster_from(run_staves[i], run_labels[i], page_index)
        if roster is not None:
            return _stamp(roster, searched, opened)

    # ── Paid tier: open pages from the front of the document ────────────────
    from .preprocessing import render_page
    from .staff_detector import detect_staves

    already = set(run_pages)
    for page_index in range(window):
        if page_index in already:
            continue
        if n_pages is not None and page_index >= n_pages:
            break
        searched.append(page_index)
        try:
            pws = detect_staves(render_page(pdf_path, page_index, dpi=dpi))
        except Exception as exc:                              # noqa: BLE001
            # A front-matter page need not be a music page at all, and a page
            # that fails to render is an ABSTENTION, not a failure of the run.
            logger.info("roster: page %d unreadable (%s)", page_index, exc)
            continue
        opened.append(page_index)
        if not pws.staves:
            continue
        try:
            labels = read_labels(pws, page_index)
        except Exception as exc:                              # noqa: BLE001
            logger.info("roster: page %d labels unavailable (%s)",
                        page_index, exc)
            continue
        roster = _roster_from(pws, labels, page_index)
        if roster is not None:
            return _stamp(roster, searched, opened)
    return None


def _stamp(roster: Roster, searched: list[int], opened: list[int]) -> Roster:
    from dataclasses import replace
    return replace(roster, pages_searched=tuple(searched),
                   pages_opened=tuple(opened))
