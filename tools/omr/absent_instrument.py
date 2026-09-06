"""A staff may not be named an instrument no page NEAR IT prints.

## The bug this is addressed to

`slots.build_reference` takes the largest recurring system across the WHOLE
document as the canonical part list. Run all 88 pages of Beethoven 5 in one
`transcribe` call and that reference is the FINALE's seventeen-staff lineup —
piccolo, contrabassoon and three trombones included. Every earlier page is then
a *reduced* system aligned into those seventeen slots, and `slots.align` decides
which slots it skips from label agreement, bracket group and position. Where a
staff carries no label the alignment has only position, and on page 23 three
string staves landed in the three trombone slots and were exported as
`Trombone`. Measured over the whole work: **91 of 855 staff records in movements
1-3 (10.6%) name an instrument the movement does not contain** — Trombone x75,
Contrabassoon x10, Piccolo x6, on 24 pages. Beethoven's trombones enter in the
finale.

## The rule

A veto, never an assignment, in the shape this project has used before (the
ledger ladder, the written-range veto, the bracket-family veto): where the
evidence is absent the staff is left UNNAMED rather than given a second guess.
An unnamed staff is honest; a second wrong name is not.

    A staff that carries no label of its own may not take a slot name that was
    read from a margin label, unless that same instrument is attested by a
    printed label within `window` pages of it.

Three clauses, each load-bearing:

* **"carries no label of its own"** — a staff the reader named on THIS page has
  direct evidence and is never touched. The veto only ever removes a name
  carried from somewhere else in the document.
* **"a slot name that was read from a margin label"** — only
  `instrument_source == "label"` is in scope. A name the score-order prior
  deduced (`score_order`) was never attested by a label anywhere, so an
  attestation test cannot speak to it; it is a different mechanism with a
  different failure mode and is left alone. Likewise `roster`, which has its
  own provenance and its own flag, and `score_order_ambiguity`, which is a label
  the prior disambiguated.
* **"within `window` pages"** — locality is the whole discriminator. The
  finale's trombone labels are 21 pages from page 23; the winds that really do
  play on page 23 are labelled on page 23.

## What it cannot do

It cannot see a *misread* label. If the margin reader turns `Viola.` into
`Trombone Basso.` on the page itself, that instrument is attested there and the
veto correctly stands aside — the fault is in the lexicon or the OCR, not in
the alignment. This is a locality check, not a plausibility check.

Off by default: `OMR_ABSENT_INSTRUMENT_VETO`.

    0 / off / unset   nothing happens; the JSON is byte-identical
    report            evidence is recorded, no name changes  (for sweeping)
    <int>             apply, with that page window
    1 / on / true     apply, with DEFAULT_WINDOW
"""

from __future__ import annotations

import os
from typing import Any, Iterable

# Sources whose names are in scope. See the module docstring.
VETOABLE_SOURCES = ("label",)

# ZERO, and the sweep says the constant is not load-bearing — which is the
# result, not a shrug. Over the whole of Beethoven 5 (88 pages, 1616 staves) the
# COST is flat at 18 vetoes for every window from 0 to 7, so widening buys
# nothing, while the BENEFIT falls monotonically from the first step: staves
# named an instrument their movement does not contain, 91 removed at W=0, 88 at
# W=1, 82 at W=2, 58 at W=7. A plateau on one axis and a strict loss on the
# other has one answer.
#
# The case for W > 0 would be an instrument whose label is missed on its own
# entry page, putting its span's edge one page late. Measured, that case is
# already covered from the other side: if the entry page attests the instrument
# then the entering staff carries its own label and is exempt anyway, and if it
# does not, the anchoring clause usually forces it. Nine impossible names is too
# much to pay for it.
DEFAULT_WINDOW = 0
DEFAULT_RULE = "span"

ENV_VAR = "OMR_ABSENT_INSTRUMENT_VETO"


def veto_config(env: dict[str, str] | None = None) -> tuple[str, int, str]:
    """`(mode, window, rule)`; mode in `off` / `report` / `apply`.

    Accepted: `0`/`off`, `report`, `1`/`on`, an integer window, or
    `<rule>:<window>` with rule in `span` / `window`.
    """
    raw = (env if env is not None else os.environ).get(ENV_VAR, "")
    raw = raw.strip().lower()
    rule = DEFAULT_RULE
    prefixed = False
    if ":" in raw:
        head, _, tail = raw.partition(":")
        if head in ("span", "window"):
            rule, raw, prefixed = head, tail.strip(), True
    if prefixed and raw.isdigit():
        # `span:0` is a window of zero, not "off" — the prefix already said the
        # veto is wanted, and 0 is the tightest legitimate window.
        return "apply", int(raw), rule
    if raw in ("", "0", "off", "no", "false"):
        return "off", 0, rule
    if raw == "report":
        return "report", 0, rule
    if raw in ("1", "on", "yes", "true"):
        return "apply", DEFAULT_WINDOW, rule
    try:
        return "apply", max(0, int(raw)), rule
    except ValueError:
        return "off", 0, rule


def label_evidence(page_indices: Iterable[int],
                   staff_labels_per_page) -> dict[int, dict[int, str]]:
    """`{page_index: {staff_index: canonical instrument name}}`.

    Confidence-filtered exactly as `slots.labels_by_staff` filters, so the
    evidence this veto reasons about is the same evidence the alignment was
    allowed to use. A label too weak to align on is too weak to attest with.
    """
    from .slots import MIN_LABEL_CONFIDENCE
    out: dict[int, dict[int, str]] = {}
    for page_index, page_labels in zip(page_indices, staff_labels_per_page):
        out[page_index] = {
            lab.staff_index: lab.instrument.name
            for lab in page_labels
            if lab.matched and lab.confidence in MIN_LABEL_CONFIDENCE
        }
    return out


def attested_pages(evidence: dict[int, dict[int, str]]) -> dict[str, set[int]]:
    """`{instrument name: pages a label for it was read on}`."""
    out: dict[str, set[int]] = {}
    for page_index, by_staff in evidence.items():
        for name in by_staff.values():
            out.setdefault(name, set()).add(page_index)
    return out


def _anchored_keys(staff_keys, slot_by_staff, evidence,
                   reference_size: int = 0) -> set:
    """Staves whose slot their own system already forces. Not a heuristic.

    `slots.align` is a MONOTONE DP that places `m` staves into `n` reference
    slots, deletions allowed on the reference side only. Between two staves
    whose slots are known, the slots in between run in order and cannot be
    reordered: if the stretch from slot A to slot B contains exactly `B - A - 1`
    staves, every slot in it is consumed with nothing skipped and the staves in
    the middle have NO FREEDOM. Their names are a consequence of their
    neighbours, not a guess, so there is nothing here for a veto to refuse.

    The same anchoring `_apply_dossier_clefs` requires ("a labelled slot above
    and below"), with one addition: **the system's own ends are anchors too.**
    Before the first staff lies slot -1 and after the last lies slot `n`, both
    known exactly, so a run of unlabelled staves at the TOP or the BOTTOM of a
    system is forced whenever its arithmetic closes against that boundary. That
    is not a special case bolted on — it falls out of the same equality, and the
    familiar "a system with as many staves as the reference has slots is
    entirely forced" is simply what it says when a system carries no labels at
    all (`n + 1 == m + 1`).

    Two measurements it is carrying, both from Beethoven 5 / Litolff:

    * **Page 1's oboe.** The margin reader misses `Oboi.` and nothing else. The
      staff sits between a labelled Flute (slot 1) and a labelled Clarinet
      (slot 3) — one staff, one slot, forced, exempt. Without this clause the
      veto strips a correct name and the `--pages 1,44` control regresses.
    * **The finale's strings.** Litolff labels the winds on every system and the
      strings only at MOVEMENT STARTS: over the whole work `Violin`, `Viola` and
      `Cello` are attested on FOUR pages each of eighty-eight, spanning [1, 44],
      and `Contrabass` on exactly ONE (page 37). Every finale page after 44 has
      its strings outside their own attestation span, and locality alone strips
      all of them — 174 staves. The end anchor keeps them, because those pages
      print the full lineup and the string block runs to the foot of the system.

    Page 23 is untouched by all of it: the three string staves that took the
    trombone slots have a labelled Timpani above them, nothing labelled below,
    and a system of 12 staves against 17 slots — five slots are skipped
    somewhere below them and the arithmetic cannot close. Unanchored, vetoed.
    """
    by_system: dict[tuple[int, int], list[int]] = {}
    for page_index, system_index, staff_index in staff_keys:
        by_system.setdefault((page_index, system_index), []).append(staff_index)
    out = set()
    for (page_index, system_index), staff_indices in by_system.items():
        order = sorted(staff_indices)
        page_labels = evidence.get(page_index, {})
        # (position, slot) for everything whose slot is known: the labelled
        # staves, plus the two boundaries when a reference size is available.
        anchors: list[tuple[int, int]] = []
        if reference_size > 0:
            anchors.append((-1, -1))
        for pos, si in enumerate(order):
            if si in page_labels:
                slot = slot_by_staff.get((page_index, system_index, si))
                if slot is not None and slot >= 0:
                    anchors.append((pos, slot))
        if reference_size > 0:
            anchors.append((len(order), reference_size))
        for pos, si in enumerate(order):
            if si in page_labels:
                continue
            above = [a for a in anchors if a[0] < pos]
            below = [a for a in anchors if a[0] > pos]
            if not above or not below:
                continue
            (j, slot_a), (k, slot_b) = above[-1], below[0]
            if slot_b - slot_a == k - j:
                out.add((page_index, system_index, si))
    return out


def find_vetoes(*,
                staff_keys: Iterable[tuple[int, int, int]],
                slot_by_staff: dict[tuple[int, int, int], int],
                instrument_name_by_slot: dict[int, str],
                instrument_source: dict[int, str],
                evidence: dict[int, dict[int, str]],
                window: int,
                rule: str = "span",
                anchored_exempt: bool = True,
                reference_size: int = 0) -> list[dict[str, Any]]:
    """One record per staff whose slot name is not attested near it.

    Pure and side-effect free, so the same function serves the applied path and
    an offline sweep over `window` and `rule`.

    Two readings of "near", measured against each other in
    `benchmarks/omr-absent-instrument-veto-2026-09`:

    `window`
        the nearest page attesting this instrument is more than `window` pages
        away. Literal, and it treats a page the OCR simply failed on exactly
        like a page where the instrument does not exist.

    `span`  (default)
        the page lies outside `[first, last]` attestation, widened by `window`.
        This is the shape of the musical fact: an instrument that enters in the
        finale is attested only from the finale on, while an instrument that
        plays throughout is attested at both ends of the document and every
        page between them is INSIDE its span whether or not that page's label
        was read. That is what separates *absent because tacet* from *absent
        because unlabelled* — the case the window rule cannot see, and the one
        most likely to break a veto on this repertoire, since Litolff's string
        labels are read on some pages and missed on others.
    """
    attested = attested_pages(evidence)
    staff_keys = list(staff_keys)
    anchored = (_anchored_keys(staff_keys, slot_by_staff, evidence,
                               reference_size)
                if anchored_exempt else set())
    out: list[dict[str, Any]] = []
    for key in staff_keys:
        page_index, system_index, staff_index = key
        slot = slot_by_staff.get(key)
        if slot is None or slot < 0:
            continue
        name = instrument_name_by_slot.get(slot)
        if name is None:
            continue
        if instrument_source.get(slot) not in VETOABLE_SOURCES:
            continue
        if evidence.get(page_index, {}).get(staff_index) is not None:
            continue                      # the staff speaks for itself
        if key in anchored:
            continue                      # its neighbours leave it no freedom
        pages = attested.get(name)
        if not pages:
            # Named `label` but attested nowhere is a contradiction; the honest
            # answer is to leave it alone rather than act on a broken invariant.
            continue
        nearest = min(pages, key=lambda p: abs(p - page_index))
        distance = abs(nearest - page_index)
        if rule == "span":
            lo, hi = min(pages) - window, max(pages) + window
            if lo <= page_index <= hi:
                continue
            outside = (lo - page_index) if page_index < lo else (page_index - hi)
        else:
            if distance <= window:
                continue
            outside = distance - window
        out.append({"page_index": page_index, "system_index": system_index,
                    "staff_index": staff_index, "slot": slot,
                    "instrument": name, "nearest_attested_page": nearest,
                    "distance_pages": distance,
                    "attested_first": min(pages), "attested_last": max(pages),
                    "pages_outside": outside, "rule": rule})
    return out
