"""The per-staff identity table, and the print truth beside it.

Shared by every probe here so that no two of them can build the table
differently. It reads ONLY the cached slice (see extract_identity_slice.py)
and the two committed truth files; it never re-reads the 146 MB record.

⚠️ THE TRUTH IS THE PRINT, NOT OUR OWN READING. `printed-lineups.json` is a
human on the page corroborated by the margin OCR, and it is keyed on (page,
system) exactly as the record's subject addresses are, so joining the two
needs no geometry and cannot suffer the page-pixel frame error that has bitten
three probes in this repo.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
SLICE = HERE / "out" / "identity-slice.json"
LINEUPS = ROOT / "benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json"

# Which clef an instrument's staff is printed in, for the twelve this document
# prints. ⚠️ THIS IS A FACT ABOUT ORCHESTRAL ENGRAVING, not a fit to the data:
# a viola staff is in alto clef because that is what a viola part is written
# in, and it would be the same on any publisher's plate. It is stated here
# rather than read off the record precisely so that a probe using it as a
# witness is not scored against its own input.
PRINTED_CLEF: Dict[str, Tuple[str, ...]] = {
    "Flauti": ("treble",),
    "Oboi": ("treble",),
    "Clarinetti": ("treble",),
    "Fagotti": ("bass", "tenor"),
    "Corni": ("treble",),
    "Trombe": ("treble",),
    "Timpani": ("bass",),
    "Violino I": ("treble",),
    "Violino II": ("treble",),
    "Viola": ("alto",),
    "Violoncello": ("bass",),
    "Basso": ("bass",),
    "Violoncello e Basso": ("bass",),
}


class Staff:
    """One printed staff of one printed system, with every reading we hold."""

    __slots__ = ("subject", "page", "system", "ordinal", "instrument",
                 "slot", "slot_outcome", "slot_reason", "clef", "clef_outcome",
                 "key", "key_outcome", "n_staves", "printed")

    def __init__(self, subject: str):
        self.subject = subject
        _, page, system, staff = subject.split("/")
        self.page, self.system, self.ordinal = int(page), int(system), int(staff)
        self.instrument: Optional[str] = None
        self.slot: Optional[int] = None
        self.slot_outcome: Optional[str] = None
        self.slot_reason: Optional[str] = None
        self.clef: Optional[str] = None
        self.clef_outcome: Optional[str] = None
        self.key: Optional[int] = None
        self.key_outcome: Optional[str] = None
        self.n_staves: Optional[int] = None
        self.printed: Optional[str] = None

    @property
    def sys_key(self) -> Tuple[int, int]:
        return (self.page, self.system)

    @property
    def named(self) -> bool:
        return self.instrument is not None

    def __repr__(self) -> str:
        return "p%d/s%d st%d %-20s slot=%s clef=%s key=%s" % (
            self.page, self.system, self.ordinal, self.printed or "?",
            self.slot if self.slot is not None else self.slot_reason,
            self.clef, self.key)


def _value(v):
    return v.get("value")


def load() -> Tuple[List[Staff], Dict[Tuple[int, int], List[str]], dict]:
    """`(staves in reading order, {(page,system): printed lineup}, raw slice)`."""
    raw = json.loads(SLICE.read_text())
    staves: Dict[str, Staff] = {}
    counts: Dict[Tuple[int, int], int] = {}

    for v in raw["verdicts"]:
        sub, q = v["subject"], v["quantity"]
        if q == "system_staff_count":
            _, page, system = sub.split("/")
            counts[(int(page), int(system))] = _value(v)
            continue
        if not sub.startswith("staff/"):
            continue
        st = staves.setdefault(sub, Staff(sub))
        if q == "instrument":
            val = _value(v)
            st.instrument = val.get("name") if isinstance(val, dict) else val
        elif q == "slot_index":
            st.slot = _value(v)
            st.slot_outcome = v.get("outcome")
            st.slot_reason = v.get("reason")
        elif q == "clef":
            st.clef = _value(v)
            st.clef_outcome = v.get("outcome")
        elif q == "key_signature":
            val = _value(v)
            st.key = val.get("fifths") if isinstance(val, dict) else val
            st.key_outcome = v.get("outcome")

    ordered = sorted(staves.values(), key=lambda s: (s.page, s.system, s.ordinal))
    for st in ordered:
        st.n_staves = counts.get(st.sys_key)

    printed: Dict[Tuple[int, int], List[str]] = {}
    for row in json.loads(LINEUPS.read_text())["systems"]:
        printed[(row["page"], row["system"])] = row["lineup"]
    for st in ordered:
        lineup = printed.get(st.sys_key)
        if lineup is not None and st.ordinal < len(lineup):
            st.printed = lineup[st.ordinal]
    return ordered, printed, raw


def reference_lineup() -> List[str]:
    """The twelve slots of the document's widest printed system."""
    return json.loads(LINEUPS.read_text())["full"]
