"""A DEDUCED name may not be an instrument the work does not have.

## The fault this is addressed to

Brahms 1 / Breitkopf, the finale (pages 45-85). The printed lineup is sixteen
staves and the **3 trombones are braced over TWO of them** (alto C clef, then
bass), so the ninth slot is the SECOND TROMBONE STAFF. We call it `Tuba`,
seventeen times over the graded full systems — and **Brahms 1 has no tuba**
(IMSLP `InstrDetail` "3, 0" for trombones and tuba, `source_kind: catalog`,
independent of the MusicXML the benchmarks score against).

Measured in `benchmarks/omr-brahms-tuba-2026-09/`, the mechanism is exact and
has nothing to do with reading:

* every one of the affected staff records carries `instrument_source ==
  "score_order"` — 102 of 102 on the whole-work run. Nothing was READ; the name
  was DEDUCED;
* fifteen of the sixteen slots are named by a margin label or the document
  roster, so `fit_layouts` sees a nearly-complete ballot, picks
  `late-romantic-large` at 6.312 points a staff with that layout as the sole
  voter, and fills the one hole with the part that layout prints between a
  trombone and a timpani. That part is `Tuba`;
* the layout library writes **one entry per printed STAFF** and has no entry
  for a section's second staff. Given the truth as a label the DP scores it
  fine (100.99 vs 100.57); given a hole it has no evidence for a continuation,
  and duplicating `Trombone` and duplicating `Timpani` score **exactly equally**
  (100.99 each). So the model can represent the right answer and cannot choose
  it.

## The rule

    A slot whose name the score-order prior DEDUCED may not name an instrument
    the work's roster does not contain. The slot is left UNNAMED.

A veto, never an assignment — the shape of `absent_instrument.py`, the ledger
ladder and the written-range veto. An unnamed staff is honest; a second wrong
name is not.

⚠️ **It refuses; it does not repair.** Removing `Tuba` from the layout and
letting the existing continuation move (`score_layouts.EXTEND_PENALTY`) take
slot 9 was measured and gives **Timpani**, not Trombone — one wrong name for
another. That arm is recorded and REFUSED in the findings; do not re-try it
without new evidence about which neighbour continues.

## Why this is not `absent_instrument.find_vetoes`

That veto is an ATTESTATION-LOCALITY test and is structurally blind to this,
for two independent reasons, both measured on the committed blob:

1. `VETOABLE_SOURCES == ("label",)` and this name is `score_order` — stated in
   its own docstring, deliberately;
2. even with `score_order` admitted, `find_vetoes` guards on
   `if not pages: continue`, and `Tuba` is attested on **ZERO** of the 86
   pages. Widening the source scope changes its output by nothing at all
   (16 vetoes -> 16, 0 of them on the Tuba slot, in every arm).

An attestation test asks *where* a name was read. A name that was never read
anywhere has no attestation to be local to. This asks a different question —
*can this name be right at all* — and needs a different evidence tier.

## Where the admissible set comes from, and where it may NOT come from

`source_kind: "catalog"` only — the IMSLP work page, independent of the
encoding the benchmarks score against. The `editions` tier is
`source_kind: "page"`, an OMR output of the same raster, and a measurement path
that scores OMR may not read it.

This module does **no catalog reading of its own**, by design: the supplier is
`tools/omr/work_roster.py` (`claude/roster-constrained-labels`), and building a
second reader for the same facts is how two rosters end up disagreeing. Until
that module lands the caller abstains and this is a complete no-op — which is
the whole layer's behaviour with `admissible=None`, tested.

Off by default: `OMR_ROSTER_SCORE_ORDER_VETO`.
"""

from __future__ import annotations

import os
from typing import Any, Iterable

# Only names the score-order prior DEDUCED are in scope.
#
# ⚠️ `score_order_ambiguity` is deliberately NOT here. That source is a margin
# label the prior merely DISAMBIGUATED (`Tp.` -> Timpani rather than Trumpet):
# the ink is on the page and the prior chose between readings already on the
# table. Vetoing it would discard a reading, not a deduction. `roster` is
# likewise out — it is a name printed on the document's own roster system.
VETOABLE_SOURCES = ("score_order",)

ENV_VAR = "OMR_ROSTER_SCORE_ORDER_VETO"

# **Default OFF.** The reach is measured and small, and its live cost is
# concentrated in one work: over 213 catalog rosters the Brahms shape (a roster
# holding `Trombone` and not `Tuba`) covers **42 works**, but on the two
# committed whole-work runs it fires on Brahms 1 (1 slot, 102 staff records)
# and on Beethoven 5 **not at all** — that run has 16 label slots, one
# `score_order_ambiguity`, and no plain `score_order` slot to veto.
#
# ⚠️ It is also inert until `work_roster.py` lands, because there is then no
# supplier for `admissible`. Turning it on today changes nothing anywhere.
DEFAULT_MODE = "off"


def enabled(env: dict[str, str] | None = None) -> bool:
    """`OMR_ROSTER_SCORE_ORDER_VETO` — refuse a deduced off-roster name."""
    raw = (env if env is not None else os.environ).get(ENV_VAR, DEFAULT_MODE)
    return raw.strip().lower() in ("1", "true", "yes", "on")


def find_offroster_vetoes(
    *,
    staff_keys: Iterable[tuple[int, int, int]],
    slot_by_staff: dict[tuple[int, int, int], int],
    instrument_name_by_slot: dict[int, str],
    instrument_source: dict[int, str],
    admissible: frozenset[str] | set[str] | None,
    evidence: dict[int, dict[int, str]] | None = None,
) -> list[dict[str, Any]]:
    """One record per staff whose DEDUCED slot name the work cannot contain.

    Pure and side-effect free, so the same function serves the applied path and
    an offline replay over a committed blob.

    `admissible` is the work's roster as a set of canonical
    `instruments.Instrument` names. ⚠️ **`None` or empty abstains entirely** —
    a work whose roster could not be acquired must not have every deduced name
    stripped, and an empty set would do exactly that. This is the single most
    dangerous way the layer could fail and it is the first thing checked.

    ⚠️ **`evidence` is REPORTED, never acted on, and that is a measured
    reversal.** `absent_instrument.py` exempts a staff the reader named on this
    page — "the staff speaks for itself" — and the first cut of this rule
    copied that clause. It is WRONG here, and the reason generalises: over
    there the name under veto came FROM a label elsewhere, so the staff's own
    label is CORROBORATION; here the name is a DEDUCTION, so the staff's own
    label is a **CONTRADICTION**, and exempting on it protects a wrong name
    with the very evidence that disproves it.

    Measured on Brahms 1's shipped run: the exemption spares 8 of the 23
    slot-9 records, and on **four full finale systems (p68, p75, p81, p82) the
    page's own margin reads `Trombone`, the hand-read truth says `Trombone`,
    and we export `Tuba`.** Graded, the exemption leaves 4 of the 17
    `Trombone -> Tuba` confusions standing for nothing. Its own label is
    recorded on the record so a reader can see it, and `label_contradiction`
    already reports the same four independently.
    """
    if not admissible:
        return []
    ev = evidence or {}
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
        if name in admissible:
            continue
        out.append({"page_index": page_index, "system_index": system_index,
                    "staff_index": staff_index, "slot": slot,
                    "instrument": name,
                    "source": instrument_source.get(slot),
                    # What THIS staff's own margin said, where anything did.
                    # Reported, never acted on — see the docstring. Where it is
                    # present it is a second, independent reason the vetoed
                    # name was wrong, not a reason to keep it.
                    "read": ev.get(page_index, {}).get(staff_index),
                    "rule": "offroster"})
    return out


def summarise(vetoes: list[dict[str, Any]],
              admissible: frozenset[str] | set[str] | None,
              work_id: str | None) -> dict[str, Any]:
    """The block that goes in the run summary. Reports the ABSTENTION too.

    A layer that abstains silently is indistinguishable from one that found
    nothing, and this project has paid for that confusion more than once — so
    `roster` is `None` when no roster was available and the reader can tell the
    two apart without reading the code.
    """
    by_name: dict[str, int] = {}
    for r in vetoes:
        by_name[r["instrument"]] = by_name.get(r["instrument"], 0) + 1
    return {
        "work_id": work_id,
        "roster": sorted(admissible) if admissible else None,
        "staff_records_vetoed": len(vetoes),
        "slots_vetoed": sorted({r["slot"] for r in vetoes}),
        "by_instrument": dict(sorted(by_name.items())),
        "vetoes": vetoes,
    }
