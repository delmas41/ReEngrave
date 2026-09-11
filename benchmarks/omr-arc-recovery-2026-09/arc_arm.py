"""ONE gather, exported twice — with and without the stem probes.

⚠️ IT IS AN EXPORT-ONLY ARM AND SAYS SO BEFORE IT SAYS ANYTHING ELSE. It
replays a SAVED record, so it is blind by construction to any GATHER or
ADJUDICATE change; `readjudicate.py` is the instrument for the second and two
full re-gathers for the first. What it CAN isolate is the exporter, with no
detector jitter between the arms, which is what this change is.

Three controls, each able to fail:

* **the NOTE SEQUENCE is unchanged.** Every note of every part, as
  (pitch, type, dots, duration, voice, staff, chord), must come back in the
  same order -- a note moved, added or dropped by an arc change shows here and
  nowhere else.

  ⚠️ THE OBVIOUS TEXTUAL CONTROL IS WRONG AND ITS FAILURE IS THE EVIDENCE. A
  first cut stripped `<slur>` and `<tied>` lines and compared the rest, and it
  FAILED -- on `<tie>` (MusicXML writes the sounding `<tie>` in the note AND
  the notational `<tied>` inside `<notations>`, so one tie is TWO elements)
  and on the `<notations>` wrapper appearing or emptying. Those are the arc,
  not a moved note. Rather than widen the strip until it passes -- *widening a
  control while teaching it about a legitimate-sounding exception is how a
  control stops being one* -- the control was made structural, and the strip
  is kept beside it with the whole arc family named.
* **the tie same-pitch invariant.** `record.Checkable`'s own rule: a tie joins
  two notes of the SAME pitch. It needs no print and no truth file, it is
  ONE-SIDED (an unresolved tie is certainly wrong; a resolved one may still be
  invented), and it is the check the chord-tie session used. A repair that
  RELOCATES ties could make it worse, and that would be decisive.
* **the accounting balance**, which stays an EQUALITY.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple

from tools.omr.staged import export as E

#: The whole arc FAMILY, which is four spellings of two things: `<slur>` and
#: `<tied>` are the notation, `<tie>` is the sound, and `<notations>` is the
#: wrapper that exists only when something is inside it.
ARC_LINE = re.compile(r"^\s*</?(slur|tied|tie|notations)\b")


def _strip_arcs(xml: str) -> str:
    return "\n".join(l for l in xml.splitlines() if not ARC_LINE.match(l))


def _note_sequence(xml: str) -> List[Tuple[Any, ...]]:
    """Every note of every part, in order, by everything except its arcs."""
    root = ET.fromstring(xml)
    out: List[Tuple[Any, ...]] = []
    for pi, part in enumerate(root.iter("part")):
        for m in part.iter("measure"):
            for n in m.iter("note"):
                p = n.find("pitch")
                pitch = None if p is None else (
                    p.findtext("step"), p.findtext("alter"), p.findtext("octave"))
                out.append((pi, m.get("number"), pitch,
                            n.findtext("type"), len(n.findall("dot")),
                            n.findtext("duration"), n.findtext("voice"),
                            n.findtext("staff"), n.find("chord") is not None,
                            n.find("rest") is not None))
    return out


def _tie_pitches(xml: str) -> Tuple[int, int, int]:
    """(tie starts, resolved onto a next note of the SAME pitch, unresolved).

    A `<tied>` carries no `number=`, so its partner is resolved BY PITCH --
    which is exactly why an unresolved one cannot be written correctly by any
    renderer.
    """
    root = ET.fromstring(xml)
    starts = same = unresolved = 0
    for part in root.iter("part"):
        seq: List[Tuple[str, bool, bool]] = []
        for m in part.iter("measure"):
            for n in m.iter("note"):
                p = n.find("pitch")
                name = "rest" if p is None else "".join(
                    (p.findtext("step") or "", p.findtext("alter") or "",
                     p.findtext("octave") or ""))
                kinds = {t.get("type") for t in n.iter("tied")}
                seq.append((name, "start" in kinds, "stop" in kinds))
        for i, (name, is_start, _stop) in enumerate(seq):
            if not is_start:
                continue
            starts += 1
            if any(seq[j][0] == name and seq[j][2]
                   for j in range(i + 1, min(i + 12, len(seq)))):
                same += 1
            else:
                unresolved += 1
    return starts, same, unresolved


def arm(record: Dict[str, Any], probes: bool) -> Tuple[str, Dict[str, Any]]:
    real = E._stem_probes
    if not probes:
        E._stem_probes = lambda *a, **k: {}
    try:
        return E.to_musicxml(record)
    finally:
        E._stem_probes = real


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out-dir", default="benchmarks/omr-arc-recovery-2026-09/out")
    a = ap.parse_args()
    rec = json.load(open(a.record))

    off_xml, off_rep = arm(rec, False)
    on_xml, on_rep = arm(rec, True)

    # ⚠️ REACH FIRST. A change that reaches nothing produces a clean zero that
    # means nothing, so the arm declares itself DEAD rather than reporting one.
    reach = on_rep["written"].get("arc_notes_reachable_at_a_stem", 0)
    print(f"REACH: notes reachable at a stem: {reach}")
    if not reach:
        raise SystemExit("DEAD: no note on this record has a stem -- "
                         "any figure below would be a zero about the "
                         "instrument, not about the change")

    keys = ("slurs", "ties", "slur_spans_marked", "tie_spans_marked",
            "tie_links_marked", "tie_chains_marked", "notes", "rests",
            "dynamics", "articulations", "fermatas", "accidentals")
    print(f"\n{'':34s} {'OFF':>7s} {'ON':>7s}")
    for k in keys:
        o, n = off_rep["written"].get(k), on_rep["written"].get(k)
        flag = "" if o == n else "   <-"
        print(f"{k:34s} {str(o):>7s} {str(n):>7s}{flag}")
    print(f"\narcs_not_written OFF {off_rep['arcs_not_written']}")
    print(f"arcs_not_written ON  {on_rep['arcs_not_written']}")

    seq_off, seq_on = _note_sequence(off_xml), _note_sequence(on_xml)
    same_seq = seq_off == seq_on
    print(f"\nCONTROL the note sequence is unchanged: {same_seq} "
          f"({len(seq_off)} vs {len(seq_on)} notes)")
    ident = _strip_arcs(off_xml) == _strip_arcs(on_xml)
    print(f"CONTROL identical with the arc FAMILY stripped: {ident}")
    for label, rep in (("OFF", off_rep), ("ON", on_rep)):
        bal = rep.get("balance") or rep.get("note_balance") or {}
        print(f"CONTROL {label} balance: {bal}")

    for label, xml in (("OFF", off_xml), ("ON", on_xml)):
        s, same, un = _tie_pitches(xml)
        print(f"CONTROL {label} tie starts {s}: resolved onto the same pitch "
              f"{same}, unresolved {un}"
              + (f"  ({same/s:.1%})" if s else ""))

    open(f"{a.out_dir}/arm-off.musicxml", "w").write(off_xml)
    open(f"{a.out_dir}/arm-on.musicxml", "w").write(on_xml)
    json.dump({"off": off_rep, "on": on_rep},
              open(f"{a.out_dir}/arm-reports.json", "w"), indent=1)
    if not (ident and same_seq):
        raise SystemExit("CONTROL FAILED: the change moved something that is "
                         "not an arc")


if __name__ == "__main__":
    main()
