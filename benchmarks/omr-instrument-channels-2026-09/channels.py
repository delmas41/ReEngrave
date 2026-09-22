"""The per-staff table, and the four channels, shared by every probe here.

⚠️⚠️ THE RULE'S INPUT IS THE RECORD; THE PRINT IS ONLY EVER THE SCORE. The
reference lineup is derived the way `adjudicate_slot_index._pick_reference`
derives it -- the document's WIDEST system, which is a lower bound on the
lineup because a system can omit a tacet part and can never invent one -- and
its names are the pipeline's OWN `Q.INSTRUMENT` verdicts. `printed-lineups.
json` is joined on the SLOT INDEX afterwards, for scoring alone. A probe that
took the lineup from the print would be grading the rule against its own
evidence, which is how this repo's last clef probe reported a number that
meant nothing.

⚠️ `printed-lineups.json` IS LITOLFF ONLY. Scoring is opt-in per record; an
arm that scored a Brahms record against it reported 21 grafts that were its
own.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
LINEUPS = ROOT / "benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json"

#: A clef verdict this thin is one crop or one confidence tier from being
#: withdrawn, and on this document the two verdicts at exactly the floor
#: include a FALSE `tenor` on a bassoon staff that printed a bass clef -- the
#: locator firing unopposed because the detector found nothing to contest it.
#: Sean, 2026-09-22: *"we would need to be sure of the clef to have it impact
#: the instrument."* This is what "sure" is operationalised as, and it is
#: reported as its own arm so the cost of the bar is visible.
CLEF_CORROBORATED_MARGIN = 2.0


class Staff:
    __slots__ = ("subject", "page", "system", "ordinal", "instrument",
                 "family", "instrument_reason", "expected_clef", "slot",
                 "slot_outcome", "slot_reason", "clef", "clef_outcome",
                 "clef_margin", "block", "n_staves", "label", "printed")

    def __init__(self, subject: str):
        self.subject = subject
        _, page, system, staff = subject.split("/")
        self.page, self.system, self.ordinal = int(page), int(system), int(staff)
        self.instrument = self.family = self.instrument_reason = None
        self.expected_clef: Optional[str] = None
        self.slot = self.slot_outcome = self.slot_reason = None
        self.clef = self.clef_outcome = None
        self.clef_margin: Optional[float] = None
        self.block: Optional[int] = None
        self.n_staves: Optional[int] = None
        self.label: Optional[str] = None
        self.printed: Optional[str] = None

    @property
    def sys_key(self) -> Tuple[int, int]:
        return (self.page, self.system)

    @property
    def named(self) -> bool:
        return self.instrument is not None

    def sure_clef(self) -> Optional[str]:
        if self.clef_outcome != "decided" or self.clef is None:
            return None
        if self.clef_margin is None or self.clef_margin < CLEF_CORROBORATED_MARGIN:
            return None
        return self.clef

    def __repr__(self) -> str:
        return "p%d/s%d st%-2d %-20s block=%s clef=%s" % (
            self.page, self.system, self.ordinal, self.printed or "?",
            self.block, self.clef)


def load(name: str) -> Tuple[List[Staff], Dict[Tuple[int, int], int], dict]:
    raw = json.loads((HERE / "out" / ("slice-%s.json" % name)).read_text())
    staves: Dict[str, Staff] = {}
    counts: Dict[Tuple[int, int], int] = {}

    for v in raw["verdicts"]:
        sub, q = v["subject"], v["quantity"]
        if q == "system_staff_count" and sub.startswith("system/"):
            _, page, system = sub.split("/")
            counts[(int(page), int(system))] = v.get("value")
            continue
        if not sub.startswith("staff/"):
            continue
        st = staves.setdefault(sub, Staff(sub))
        if q == "instrument":
            val = v.get("value")
            if isinstance(val, dict):
                st.instrument, st.family = val.get("name"), val.get("family")
                st.expected_clef = val.get("expected_clef")
            st.instrument_reason = v.get("reason")
        elif q == "slot_index":
            st.slot, st.slot_outcome = v.get("value"), v.get("outcome")
            st.slot_reason = v.get("reason")
        elif q == "clef":
            st.clef, st.clef_outcome = v.get("value"), v.get("outcome")
            st.clef_margin = v.get("margin")
        elif q == "staff_group":
            st.block = v.get("value")

    for o in raw["observations"]:
        if o["quantity"] == "margin_label" and o.get("value") is not None:
            st = staves.get(o["subject"])
            if st is not None:
                st.label = str(o["value"])

    ordered = sorted(staves.values(),
                     key=lambda s: (s.page, s.system, s.ordinal))
    for st in ordered:
        st.n_staves = counts.get(st.sys_key)
    return ordered, counts, raw


#: The instruments whose part legitimately ALTERNATES between two clefs, so
#: that one reading of one system is not a property of the slot.
#:
#: ⚠️ THIS IS A FACT ABOUT ORCHESTRAL ENGRAVING AND IT IS MEASURED HERE, not
#: assumed: `probe_clef_stability.py` finds a slot's clef constant across both
#: documents for every instrument EXCEPT these -- Breitkopf's cello slot reads
#: `tenor` on the reference system and `bass` on three later ones, all four at
#: margin 4.5, and the Litolff and Breitkopf bassoons each read `tenor` once.
#: Every other slot reads one clef on every system it appears on.
ALTERNATING_CLEFS = {
    "Cello": ("bass", "tenor"),
    "Bassoon": ("bass", "tenor"),
    "Contrabassoon": ("bass", "tenor"),
    "Trombone": ("bass", "tenor"),
}


def clefs_for(instrument: Optional[str],
              expected: Optional[str]) -> Optional[Tuple[str, ...]]:
    """Every clef this instrument's part may be printed in, or None."""
    if instrument is None:
        return None
    alt = ALTERNATING_CLEFS.get(instrument)
    if alt is not None:
        return alt
    return (expected,) if expected else None


def reference(staves: Sequence[Staff],
              counts: Dict[Tuple[int, int], int]) -> Tuple[Tuple[int, int],
                                                           List[Optional[str]],
                                                           List[Optional[int]]]:
    """`(system, [name by slot], [block by slot])` for the widest system.

    `_pick_reference`'s rule, restated only as far as this probe needs it: a
    LARGEST system, and among those the one naming the most staves. Where two
    equally large, equally well-named systems disagree this would have to
    abstain; on both documents here they do not, and the probe says so.
    """
    if not counts:
        return None, [], []
    widest = max(counts.values())
    cands = sorted(k for k, n in counts.items() if n == widest)
    by_sys = {k: [s for s in staves if s.sys_key == k] for k in cands}

    def named_count(k):
        return sum(1 for s in by_sys[k] if s.named)

    best = max(named_count(k) for k in cands)
    pick = [k for k in cands if named_count(k) == best][0]
    grp = sorted(by_sys[pick], key=lambda s: s.ordinal)
    names: List[Optional[str]] = [None] * widest
    blocks: List[Optional[int]] = [None] * widest
    for s in grp:
        if s.ordinal < widest:
            names[s.ordinal] = s.instrument
            blocks[s.ordinal] = s.block
    return pick, names, blocks


def printed_truth() -> Tuple[List[str], Dict[Tuple[int, int], List[str]]]:
    d = json.loads(LINEUPS.read_text())
    return d["full"], {(r["page"], r["system"]): r["lineup"]
                       for r in d["systems"]}


def classify(printed: Optional[str], slot_name: Optional[str]) -> str:
    """`ok` | `condensation` | `graft`, the 2026-09-15 membership test.

    ⚠️ Reproduced from `benchmarks/omr-unnamed-staves-2026-09/probe_forced_
    by_clef.py` rather than imported, because importing would drag that
    lane's own record loader in. A looser test (`startswith`) read
    `Violino II` as a condensation of `Violino I` and is what this exact
    shape exists to refuse.
    """
    if printed is None or slot_name is None:
        return "unknown"
    if printed == slot_name:
        return "ok"
    parts = [p.strip() for p in printed.split(" e ")]
    if len(parts) > 1 and slot_name in parts:
        return "condensation"
    return "graft"
