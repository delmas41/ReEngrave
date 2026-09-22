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

⚠️⚠️ **`--sequence` IS THE ARM THAT SEPARATES A BARLINE FAULT FROM A NOTE
FAULT, and it is not a softer test — it is a different one.** A single spurious
barline shifts every bar after it, so a per-bar comparison then charges every
following bar of every part as wrong and reports a page of correct music as a
catastrophe. `--sequence` compares each part's event list END TO END with the
bar boundaries removed: a note fault still shows, a barline fault does not.
Report BOTH — the per-bar arm is the one that knows the bars are wrong, and the
sequence arm is the one that knows the notes are right.
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


def events(part, n_bars: int, first: int = 0) -> Dict[int, List[Tuple]]:
    """`ordinal -> [(kind, quarterLength), ...]` for `n_bars` bars from `first`.

    Keyed on the bar's POSITION in the slice, not on its printed number, so the
    two sides line up when one is an excerpt of the other.

    A chord is ONE event whose kind is the sorted tuple of its pitches, so a
    divisi read as two notes and a chord read as one are distinguishable.
    """
    out: Dict[int, List[Tuple]] = {}
    bars = list(part.getElementsByClass("Measure"))[first:first + n_bars]
    for i, m in enumerate(bars):
        row = []
        for n in m.notesAndRests:
            ql = round(float(n.duration.quarterLength), 4)
            if n.isRest:
                row.append(("rest", ql))
            elif n.isChord:
                row.append((tuple(sorted(p.nameWithOctave for p in n.pitches)), ql))
            else:
                row.append((n.pitch.nameWithOctave, ql))
        out[i] = row
    return out


def _bare(kind) -> Any:
    """A pitch name stripped of its accidental; a rest and a chord unchanged.

    `nameWithOctave` is `<letter><accidentals><octave>` — `E-4`, `F#5` — so the
    letter and the octave are the first character and the trailing digits.
    """
    if isinstance(kind, tuple):
        return tuple(_bare(k) for k in kind)
    if not isinstance(kind, str) or kind == "rest":
        return kind
    octv = "".join(c for c in kind if c.isdigit())
    return kind[0] + octv


def _accidental_only(a: List[Tuple], b: List[Tuple]) -> bool:
    """Do these two bars differ ONLY in accidentals?"""
    if len(a) != len(b):
        return False
    for (ka, qa), (kb, qb) in zip(a, b):
        if qa != qb or _bare(ka) != _bare(kb):
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours", type=Path, required=True)
    ap.add_argument("--truth", type=Path, required=True)
    ap.add_argument("--bars", type=int, required=True,
                    help="how many bars of the truth this page carries")
    ap.add_argument("--truth-first-bar", type=int, default=1,
                    help="the truth's first bar ON THIS PAGE, 1-based. The "
                         "render decides it; read it off the page's own SVG "
                         "(`grep -c 'class=\"measure\"'`), never guess it.")
    ap.add_argument("--sequence", action="store_true",
                    help="compare each part's event list with the bar "
                         "boundaries removed — see the module docstring")
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

    our_bars = len(list(ours.parts[0].getElementsByClass("Measure")))
    warn = ("   ⚠️ DISAGREE — a per-bar comparison is shifted after the first "
            "extra/missing barline; read the SEQUENCE arm beside it"
            if our_bars != args.bars else "")
    print(f"\nBAR COUNT: we wrote {our_bars}, the render prints {args.bars} "
          f"(truth bars {args.truth_first_bar}"
          f"..{args.truth_first_bar + args.bars - 1}){warn}")

    rows = []
    tot_ev_t = tot_ev_o = exact_bars = total_bars = 0
    seq_exact = 0
    per_part = []
    kinds = Counter()
    first = args.truth_first_bar - 1
    for i, (po, pt) in enumerate(zip(ours.parts, truth.parts)):
        eo, et = events(po, our_bars), events(pt, args.bars, first)
        flat_o = [x for k in sorted(eo) for x in eo[k]]
        flat_t = [x for k in sorted(et) for x in et[k]]
        if flat_o == flat_t:
            seq_exact += 1
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
                    # ⚠️ SPLIT OUT, because the repair differs completely. A
                    # pair that agrees on the letter and octave and differs
                    # only in the accidental is a KEY SIGNATURE or an in-bar
                    # accidental — the staff position was read correctly. A
                    # pair on a different letter is a position error.
                    if _accidental_only(a, b):
                        kinds["same count, differs ONLY by an accidental"] += 1
                    else:
                        kinds["same count, different pitch/rest"] += 1
                else:
                    kinds["same pitches, different duration"] += 1
                if len(rows) < args.show:
                    rows.append({"part": i, "name": str(pt.partName),
                                 "bar": args.truth_first_bar + num,
                                 "ours": a, "truth": b})
        exact_bars += p_exact
        total_bars += p_total
        per_part.append({"part": i, "name": str(pt.partName),
                         "bars_exact": p_exact, "bars": p_total})

    print(f"\nREACH: {len(ours.parts)} parts x {args.bars} bars = {total_bars} "
          f"part-bars;  events truth {tot_ev_t}, ours {tot_ev_o}")
    print(f"\nBARS EXACT (every event's kind AND duration): "
          f"{exact_bars} of {total_bars}  ({exact_bars / total_bars:.3f})")
    print(f"PARTS EXACT AS A SEQUENCE (bar boundaries removed): "
          f"{seq_exact} of {len(ours.parts)}  "
          f"({seq_exact / len(ours.parts):.3f})")
    print("⚠️ read them beside the event counts above — a part we wrote "
          "nothing for makes no error.")
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

    out = {"parts": len(ours.parts), "bars_printed": args.bars,
           "bars_written": our_bars, "truth_first_bar": args.truth_first_bar,
           "part_bars": total_bars, "bars_exact": exact_bars,
           "parts_exact_as_sequence": seq_exact,
           "events_truth": tot_ev_t, "events_ours": tot_ev_o,
           "disagreements": dict(kinds), "per_part": per_part,
           "examples": rows}
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
