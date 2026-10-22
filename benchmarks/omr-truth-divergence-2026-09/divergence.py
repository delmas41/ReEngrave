"""Encoded parts vs printed staves, per row, with every difference attributed.

The question, in Sean's words: *"I am not sure our MXL will work as a ground
truth. Unless we can determine that the amount of staves matches."*

So this compares three counts that are routinely conflated:

    encoded parts      `<score-part>` entries in the reference        (the FILE)
    printed staves     staff bands the page actually prints           (the PAGE)
    detected staves    what our phase 1 produced                      (US)

and attributes every non-zero difference to a cause. The causes are not
interchangeable and pooling them would hide the only one that is our fault:

    condensation       one printed staff carries several parts (`Flauti`)
    multi-staff part   one part declares several staves — the MIRROR of
                       condensation, and it is why Mahler's "38 parts" is not a
                       part count at all
    tacet suppression  a printed score omits a staff resting for the system
    detection error    OURS. A staff the page prints and we did not read, or
                       one we read that is not there.

⚠️ A `same-as:` staves entry defers to another row (two scans of one plate), so
the hand-read map has to be RESOLVED before it is counted. Taking `len()` of
that string reports a 37-staff lineup, which is how long the string is.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
READINGS = HERE / "readings"
SCAN_WORKS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"


# ── the three counts ────────────────────────────────────────────────────────

def hand_read_staves(row: dict, by_id: dict[str, dict]) -> list[dict] | None:
    """The row's hand-read per-system lineup, following a `same-as:` deferral.

    Returns dicts with at least a `name`; `parts` is present only where the row
    recorded the part->staff map, which is the thing that makes a row usable as
    PER-STAFF truth rather than merely aggregate truth.
    """
    st = row.get("staves")
    seen = set()
    while isinstance(st, str) or (isinstance(st, list) and len(st) == 1
                                  and isinstance(st[0], str)
                                  and st[0].startswith("same-as:")):
        ref = st if isinstance(st, str) else st[0]
        if not ref.startswith("same-as:"):
            return None
        target = ref.split(":", 1)[1]
        if target in seen:                      # a cycle is a corrupt file
            raise ValueError(f"same-as cycle at {row['row_id']}")
        seen.add(target)
        other = by_id.get(target)
        if other is None:
            return None
        st = other.get("staves")
    if not isinstance(st, list) or not st:
        return None
    if not all(isinstance(s, dict) for s in st):
        return None
    return st


def detected(row_id: str, corpus: str) -> dict | None:
    """Staff and system counts our pipeline read, from the stored transcription."""
    p = READINGS / f"{corpus}--{row_id}.omr.json"
    if not p.exists():
        return None
    doc = json.loads(p.read_text())
    pages = doc["pages"]
    per_system = [len(s["staves"]) for pg in pages for s in pg["systems"]]
    return {
        "n_systems": len(per_system),
        "per_system": per_system,
        "total": sum(per_system),
        "doc": doc,
    }


def raw_staff_span(doc: dict) -> int | None:
    """How many staves phase 1 DETECTED, before the five-line filter.

    `staff_index` is preserved across that filter, so the highest index plus one
    is the raw count — which is how the roster's own `n_staves` can exceed the
    pipeline's without either being wrong about the same thing. On the Mahler
    scan the gap is exactly the one-line percussion staves.
    """
    idx = [st["staff_index"] for pg in doc["pages"]
           for sy in pg["systems"] for st in sy["staves"]]
    return max(idx) + 1 if idx else None


# ── attribution ─────────────────────────────────────────────────────────────

def attribute(n_parts: int, lineup: list[dict] | None,
              n_printed: int | None) -> dict:
    """Split `encoded parts - printed staves` into named causes.

    Only the hand-read map can do this exactly: a staff whose `parts` list has
    more than one entry is condensed by exactly that surplus, and any part no
    staff claims is suppressed. Without the map we can report the difference but
    not its composition, and saying so is the point of the `usable` field.
    """
    if lineup is None:
        return {"attributable": False,
                "delta": (n_parts - n_printed) if n_printed is not None else None}
    claimed: set[int] = set()
    condensed = 0
    for s in lineup:
        parts = s.get("parts")
        if not parts:
            continue
        claimed.update(parts)
        condensed += max(0, len(parts) - 1)
    suppressed = n_parts - len(claimed)
    return {
        "attributable": True,
        "n_staves_lineup": len(lineup),
        "condensation": condensed,
        "tacet_suppressed": suppressed,
        "delta": n_parts - len(lineup),
        # A row balances when condensation + suppression explains the whole
        # difference. Anything left over is unexplained and wants a human.
        "residual": (n_parts - len(lineup)) - condensed - suppressed,
    }
