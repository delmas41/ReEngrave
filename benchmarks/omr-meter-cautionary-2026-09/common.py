"""Shared reading of the committed meter artefacts.

⚠️ NOTHING HERE RE-DERIVES A NUMBER. It reads
`benchmarks/omr-staged-meter-boundary-2026-09/out/*.meter.json` — the committed
extracts every figure of that benchmark was taken off — and the truth tables
out of `report_boundary.py` itself, IMPORTED rather than restated so this
benchmark and that one cannot drift about what the page prints.

⚠️⚠️ THE ARMS ARE NOT INDEPENDENT OBSERVATIONS AND A NAIVE COUNT IS ~4x TOO
BIG. `out/` holds the same six fixtures re-measured across five merged trees
(`m2`..`m7`) and up to four flag arms each, so one printed cautionary appears
in six files. Everything here is deduped on the address of the INK —
`(fixture, system, from_cell, raw)` — never on the address of the run.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
BOUNDARY = ROOT / "benchmarks" / "omr-staged-meter-boundary-2026-09"

if str(BOUNDARY) not in sys.path:
    sys.path.insert(0, str(BOUNDARY))

# ⚠️ IMPORTED, NOT RESTATED. `TRUTH` is hand-read off the print by the session
# that built the boundary fixtures; copying it here would give this repository
# two truths for one page, which is the failure mode CLAUDE.md records for
# every restated figure.
import report_boundary as _rb                                   # noqa: E402
import summarize as _sum                                        # noqa: E402

TRUTH: Dict[tuple, str] = _rb.TRUTH
TRUTH_CHANGES: Dict[tuple, Any] = _rb.TRUTH_CHANGES
FIXTURE_OF: Dict[str, str] = _sum.FIXTURE_OF

_GEN = re.compile(r"^m(\d+)")


def _generation(tag: str) -> int:
    """Which re-measured tree an arm belongs to. `full` is 1, `m7full` is 7.

    ⚠️ IT MATTERS: only the `m5` and `m7` trees carry the cautionary rule. An
    earlier arm records the same printed glyph as an ordinary mid-system
    SEGMENT, so counting cautionaries across all arms without this would report
    the rule's arrival as the ink's absence.
    """
    m = _GEN.match(tag)
    return int(m.group(1)) if m else 1


@dataclass
class Arm:
    path: Path
    tag: str            # e.g. "m7brahms1scan"
    flag_arm: str       # e.g. "OFF"
    fixture: str        # e.g. "brahms1-317803"
    generation: int
    verdicts: List[dict]

    def meters(self):
        for v in self.verdicts:
            if v.get("quantity") != "meter":
                continue
            yield v["subject"], (v.get("value") or {})

    def verdict(self, subject: str) -> Optional[dict]:
        for v in self.verdicts:
            if v.get("quantity") == "meter" and v["subject"] == subject:
                return v
        return None

    def subjects(self) -> List[str]:
        return [v["subject"] for v in self.verdicts
                if v.get("quantity") == "meter"]


def load_arms(out_dir: Path) -> List[Arm]:
    arms: List[Arm] = []
    for p in sorted(out_dir.glob("*.meter.json")):
        stem = p.name[: -len(".meter.json")]
        tag, _, flag = stem.rpartition("-")
        fixture = FIXTURE_OF.get(tag)
        if fixture is None:
            continue
        arms.append(Arm(p, tag, flag, fixture, _generation(tag),
                        json.loads(p.read_text())))
    return arms


def parse_subject(subject: str) -> Tuple[int, int]:
    """`system/1/0` -> (page 1, system 0), in the RUN's own page numbering."""
    _, page, sysi = subject.split("/")
    return int(page), int(sysi)


def next_system_of(arm: Arm, subject: str) -> Optional[str]:
    """The system a cautionary at the end of `subject` would announce.

    Reading order: the next system on this page, else the first system of the
    next page **that the run holds**. ⚠️ A run that stops at the page boundary
    has no next system, and that is reported rather than guessed at.
    """
    here = parse_subject(subject)
    later = sorted(parse_subject(s) for s in arm.subjects())
    for cand in later:
        if cand > here:
            return f"system/{cand[0]}/{cand[1]}"
    return None


def truth_for(fixture: str, subject: Optional[str]) -> Optional[str]:
    """What the PRINT says this system's meter is.

    ⚠️ The boundary truth table keys some fixtures on the page alone and one
    (the Brahms scan, whose page 1 holds two systems with different truths) on
    `(fixture, page, system)`. Both spellings are tried, most specific first.
    """
    if subject is None:
        return None
    page, sysi = parse_subject(subject)
    if (fixture, page, sysi) in TRUTH:
        return TRUTH[(fixture, page, sysi)]
    return TRUTH.get((fixture, page))
