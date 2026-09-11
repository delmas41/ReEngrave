"""ADJUDICATE EVERY WRITTEN TIE WITHOUT A TRUTH FILE.

⚠️ `record.Checkable`'s own docstring: *"A tie's two ends must be the same
pitch, so C vs C# IS checkable at a tie and nowhere else."* That is the
invariant this probe runs, over a whole exported file: for each
`<tied type="start">`, does a note of the SAME PITCH, in the SAME voice,
carrying `<tied type="stop">`, follow it?

It needs no reference encoding and no print, so it can adjudicate **every**
element a change moves rather than a hand-picked sample — which is what the
chord-tie repair needs, because it moves more than a person can look at.

⚠️ WHAT IT IS NOT. A resolving tie is not a tie the PAGE prints: two spurious
same-pitch detections resolve perfectly. The measure is one-sided — a tie that
does NOT resolve is certainly wrong, a tie that does may still be invented —
so read the UNRESOLVED count as the defect and never the resolved count as
accuracy.

    python3 benchmarks/omr-chord-tie-2026-09/probe/tie_resolves.py A.musicxml...
"""
from __future__ import annotations

import pathlib
import sys
import xml.etree.ElementTree as ET


def _pitch(note: ET.Element) -> str | None:
    p = note.find("pitch")
    if p is None:
        return None
    return "%s%s/%s" % (p.findtext("step", ""), p.findtext("alter", "0"),
                        p.findtext("octave", ""))


def check(path: pathlib.Path) -> dict:
    root = ET.parse(path).getroot()
    starts = stops = resolved = 0
    for part in root.iter("part"):
        # One flat stream per voice, in document order; a tie may cross a
        # barline, which is why the measures are flattened before the walk.
        by_voice: dict[str, list[ET.Element]] = {}
        for measure in part.iter("measure"):
            for note in measure.iter("note"):
                by_voice.setdefault(note.findtext("voice", "1"),
                                    []).append(note)
        for notes in by_voice.values():
            for i, note in enumerate(notes):
                if note.find('.//tied[@type="stop"]') is not None:
                    stops += 1
                if note.find('.//tied[@type="start"]') is None:
                    continue
                starts += 1
                want = _pitch(note)
                if want is None:
                    continue
                # Scan forward past this note's remaining chord members to
                # the next event, and accept a stop anywhere in it.
                j = i + 1
                while j < len(notes) and notes[j].find("chord") is not None:
                    j += 1
                while j < len(notes):
                    if (_pitch(notes[j]) == want
                            and notes[j].find('.//tied[@type="stop"]')
                            is not None):
                        resolved += 1
                        break
                    j += 1
                    if j < len(notes) and notes[j].find("chord") is None:
                        break
    return {"starts": starts, "stops": stops, "resolved": resolved,
            "unresolved": starts - resolved}


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    pooled = {"starts": 0, "stops": 0, "resolved": 0, "unresolved": 0}
    for arg in sys.argv[1:]:
        t = check(pathlib.Path(arg))
        for k in pooled:
            pooled[k] += t[k]
        print(f"{pathlib.Path(arg).name[:56]:58s} "
              f"starts={t['starts']:4d} resolved={t['resolved']:4d} "
              f"UNRESOLVED={t['unresolved']:4d}")
    print(f"\n  pooled  starts={pooled['starts']} "
          f"resolved={pooled['resolved']} UNRESOLVED={pooled['unresolved']}")
    if not pooled["starts"]:
        sys.stderr.write("⚠️ ZERO ties read. A dead instrument reads exactly "
                         "like a clean file — check the input.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
