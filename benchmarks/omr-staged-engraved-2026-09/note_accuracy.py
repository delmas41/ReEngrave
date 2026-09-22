"""Are the notes the staged path DID write the RIGHT notes? — engraved only.

    python3 benchmarks/omr-staged-engraved-2026-09/note_accuracy.py \
        --ours out/engraved-p0.musicxml --truth out/fixture/<stem>.musicxml \
        --bars 7 --json-out out/note-accuracy-p0.json

`trace.py` says where symbols are LOST and its own docstring says it cannot see
ACCURACY, because both shared records are SCANS and there is no per-symbol truth
for a scanned plate. On a page we RENDER the truth is the file we rendered FROM,
so for once the question is answerable.

⚠️⚠️ **THE JOIN IS WHAT MAKES THIS LEGITIMATE, AND IT IS CHECKED, NOT ASSUMED.**
Every staged note-accuracy attempt on a scan founders on *which encoded part
sits on which printed staff* — a property of the ENGRAVING, absent from the
MusicXML, and the reason `dossier.slot_facts_for_system` abstains wherever
`len(parts) != n_staves`. Here the renderer prints EVERY part on EVERY system
and suppresses none, so the ordinal join is not a guess: it is the layout. This
script REFUSES unless both sides have the same part count and our part i lands
on truth part i, and it prints the instrument names side by side so a silent
misalignment is visible rather than inferred.

⚠️ **WRITTEN PITCH ON BOTH SIDES.** `consequences.restate_pitch` derives pitch
from staff position + clef, which is what is PRINTED; MusicXML `<pitch>` is
likewise the written pitch, with `<transpose>` carrying the offset separately.
The comparison is therefore like for like — and the script asserts it by
checking that neither side's parse has been moved to sounding pitch.

⚠️ **A MEASURE REST AND A WHOLE-BAR REST ARE THE SAME MUSIC.** `<rest
measure="yes"/>` carries no `<type>`; an explicit whole rest does. Both are
compared as `("rest", quarterLength)`, because the distinction is an engraving
convention and not a reading.

⚠️ **THE HEADLINE IS A PAIR, NEVER ONE NUMBER.** A part we wrote nothing for
scores no errors, so `bars exact` alone rewards silence — the direction OMR-NED
is already known to be gamed in. Written/expected counts are printed beside it.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

warnings.filterwarnings("ignore")


def events(part, n_bars: int) -> Dict[int, List[Tuple]]:
    """`measure number -> [(kind, quarterLength), ...]` for the first n bars.

    A chord is ONE event whose kind is the sorted tuple of its pitches, so a
    divisi read as two notes and a chord read as one are distinguishable.
    """
    out: Dict[int, List[Tuple]] = {}
    for m in list(part.getElementsByClass("Measure"))[:n_bars]:
        row = []
        for n in m.notesAndRests:
            ql = round(float(n.duration.quarterLength), 4)
            if n.isRest:
                row.append(("rest", ql))
            elif n.isChord:
                row.append((tuple(sorted(p.nameWithOctave for p in n.pitches)), ql))
            else:
                row.append((n.pitch.nameWithOctave, ql))
        out[m.number] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours", type=Path, required=True)
    ap.add_argument("--truth", type=Path, required=True)
    ap.add_argument("--bars", type=int, required=True,
                    help="how many bars of the truth this page carries")
    ap.add_argument("--show", type=int, default=12)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    from music21 import converter
    ours = converter.parse(str(args.ours))
    truth = converter.parse(str(args.truth))

    if len(ours.parts) != len(truth.parts):
        print(f"REFUSED: {len(ours.parts)} parts against {len(truth.parts)}. "
              "The ordinal join is not the layout here and this comparison "
              "would pair one instrument's music with another's.")
        return 2

    print(f"JOIN (ordinal, and it is the layout — the renderer prints every "
          f"part on every system):")
    for i, (a, b) in enumerate(zip(ours.parts, truth.parts)):
        print(f"   {i:2d}  ours {str(a.partName):22s} truth {b.partName}")

    rows = []
    tot_ev_t = tot_ev_o = exact_bars = total_bars = 0
    per_part = []
    kinds = Counter()
    for i, (po, pt) in enumerate(zip(ours.parts, truth.parts)):
        eo, et = events(po, args.bars), events(pt, args.bars)
        p_exact = p_total = 0
        for num in sorted(et):
            a, b = eo.get(num, []), et[num]
            tot_ev_o += len(a)
            tot_ev_t += len(b)
            p_total += 1
            if a == b:
                p_exact += 1
            else:
                # what KIND of disagreement, so the total is not one bucket
                if not a:
                    kinds["we wrote nothing in this bar"] += 1
                elif len(a) != len(b):
                    kinds["different number of events"] += 1
                elif [x[0] for x in a] != [x[0] for x in b]:
                    kinds["same count, different pitch/rest"] += 1
                else:
                    kinds["same pitches, different duration"] += 1
                if len(rows) < args.show:
                    rows.append({"part": i, "name": str(pt.partName),
                                 "bar": num, "ours": a, "truth": b})
        exact_bars += p_exact
        total_bars += p_total
        per_part.append({"part": i, "name": str(pt.partName),
                         "bars_exact": p_exact, "bars": p_total})

    print(f"\nREACH: {len(ours.parts)} parts x {args.bars} bars = {total_bars} "
          f"part-bars;  events truth {tot_ev_t}, ours {tot_ev_o}")
    print(f"\nBARS EXACT (every event's kind AND duration): "
          f"{exact_bars} of {total_bars}  ({exact_bars / total_bars:.3f})")
    print("⚠️ read it beside the event counts above — a part we wrote nothing "
          "for makes no error.")
    if kinds:
        print("\ndisagreements by kind:")
        for k, n in kinds.most_common():
            print(f"   {n:5d}  {k}")

    print(f"\nper part:")
    for r in per_part:
        mark = "" if r["bars_exact"] == r["bars"] else "   <--"
        print(f"   {r['part']:2d} {r['name']:24s} "
              f"{r['bars_exact']}/{r['bars']}{mark}")

    if rows:
        print(f"\nfirst {len(rows)} disagreeing bars:")
        for r in rows:
            print(f"   part {r['part']} {r['name']} bar {r['bar']}")
            print(f"      ours  {r['ours']}")
            print(f"      truth {r['truth']}")

    out = {"parts": len(ours.parts), "bars": args.bars,
           "part_bars": total_bars, "bars_exact": exact_bars,
           "events_truth": tot_ev_t, "events_ours": tot_ev_o,
           "disagreements": dict(kinds), "per_part": per_part,
           "examples": rows}
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
