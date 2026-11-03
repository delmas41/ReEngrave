"""The key signature's slot count READ from the header ink the page already measured -- ROADMAP 2.256 (STAGED ADJUDICATE; GATHER rows only read).

Flag `OMR_KEY_HEADER_INK` (default OFF; "1"/"true"/"yes"/"on" turns it on).

CAUSE (benchmarks/key-header-2026-11/FINDINGS.md): on Litolff the three key flats are printed crushed together and the detector boxes only one or
two of them (the third, lowest, flat has no box). `adjudicate_key_signature` counts the detector's `Q.KEYSIG_MARKER` slots (`_marker_run`), reads
1-2 where three are printed, and `_part_checked` then abstains the staff (`disagrees_with_document`): INFER `fill_part_key` writes the right key
back from the other systems, blue, so ~80 notes a page are blue for a key the page prints plainly. But GATHER had ALREADY read the header
ink: `gather_key_object` (2.187) chains the accidental-sized RASTER pieces and the detector boxes out of the clef's edge, takes the system's count
from two staves' agreement, and files per staff `own_slots` on its `Q.CLAIMED_AREA` row (`source: system_key_object`). Nothing in ADJUDICATE
read it: a value computed and unread.

What this does (with the flag), for a staff whose marker run is a clean run of ONE kind (flats or sharps, `reason == markers`): where the key
object's own slot count for that staff is GREATER than the marker slots, is at most the system's agreed count, and the staff reads that many accidentals of the marker run's kind. The kind is the DETECTOR's (the key object's shape
reader calls a crushed flat's bowl a sharp or a natural: measured 8 of 90 read pieces), never the key object's. It only RAISES a count the
detector under-counted; it never lowers one, never supplies a kind, and a staff with no marker run is untouched (no kind). The system and part
checks run on the new value exactly as on the old one -- a count that disagrees with the document is still abstained.

CONVENTION ASSUMED (page-facts, CLAUDE.md §4): the accidentals of a key signature stand in a fixed order, one slot apart, hard against the
clef; a staff's own slots are what its own raster pieces and boxes chain to. WHAT WOULD FALSIFY IT: a piece in `own_slots` that is not an
accidental (a first-bar accidental or a head chained on at 1-2 spaces) on a staff whose true key has fewer. NOT CONFIRMED beyond two plates.
"""
import os
from typing import Any, Dict, Optional, Sequence

ENV = "OMR_KEY_HEADER_INK"
READER = "cv_key_object"
SOURCE = "system_key_object"


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def key_object_of(rows: Sequence[Any]) -> Optional[Dict[str, Any]]:
    """The staff's `key_object` detail from its `cv_key_object` claim rows (the READ part carries it; the placed part repeats it), or None."""
    for r in rows:
        if getattr(r, "reader", None) != READER:
            continue
        d = r.detail or {}
        if d.get("source") != SOURCE:
            continue
        ko = d.get("key_object")
        if isinstance(ko, dict):
            return ko
    return None


def raise_count(ko: Optional[Dict[str, Any]], marker_slots: int, max_slots: int = 7) -> Dict[str, Any]:
    """`{"slots": N, "why": "raised"}` where the key object's own slots exceed the markers' `marker_slots`, else `{"slots": None, "why": <refusal>}`.

    `ko`: `key_object_of`. `marker_slots`: the slots `_marker_run` counted (>= 1). The refusals name which witness stood against it so a
    reader of the record can count them: `no_key_object`, `not_more_slots`, `more_than_system`."""
    if not ko:
        return {"slots": None, "why": "no_key_object"}
    own = ko.get("own_slots")
    n_sys = ko.get("system_count")
    if not isinstance(own, int) or not isinstance(n_sys, int) or marker_slots < 1:
        return {"slots": None, "why": "no_key_object"}
    if own <= marker_slots:
        return {"slots": None, "why": "not_more_slots", "own_slots": own}
    if own > n_sys or own > max_slots or ko.get("more_than_system"):
        return {"slots": None, "why": "more_than_system", "own_slots": own, "system_count": n_sys}
    pcs = ko.get("read_pieces") or []
    if len(pcs) < own:
        return {"slots": None, "why": "no_key_object", "own_slots": own}
    return {"slots": own, "why": "raised", "own_slots": own, "system_count": n_sys, "marker_slots": marker_slots}
