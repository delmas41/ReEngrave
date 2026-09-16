"""THE POPULATION Sean is pointing at, read off the artefact he actually read.

⚠️ REACH FIRST. This probe reads ONE committed file --
`benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4.musicxml`, the
cleanup artefact of 2026-09-11 -- and says nothing about any other document.
It exits non-zero if that file yields no bars at all, so a dead instrument
cannot read as a clean result.

Sean, reading it against the print: *"in bars where it should be just whole
note rest in two four. It's showing an actual quarter note, not a quarter note
rest."*

The unit is a BAR whose entire written content is one PITCHED note.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
ARTEFACT = HERE / "benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4.musicxml"

#: The six bars the 2026-09-11 handoff names, so a probe that has drifted off
#: the population says so loudly rather than quietly measuring something else.
NAMED = {("P1", "45"), ("P1", "85"), ("P1", "88"), ("P1", "89"),
         ("P2", "49"), ("P2", "87")}


def bars(xml_path):
    """Every measure of every part, with what it holds and how long it is."""
    root = ET.parse(xml_path).getroot()
    out = []
    for part in root.findall("part"):
        pid = part.get("id")
        div = beats = btype = None
        for m in part.findall("measure"):
            a = m.find("attributes")
            if a is not None:
                d = a.find("divisions")
                if d is not None:
                    div = int(d.text)
                tm = a.find("time")
                if tm is not None:
                    beats = int(tm.find("beats").text)
                    btype = int(tm.find("beat-type").text)
            notes = m.findall("note")
            pitched = [n for n in notes if n.find("pitch") is not None]
            rests = [n for n in notes if n.find("rest") is not None]
            barlen = div * 4 * beats / btype if (div and beats and btype) else None
            out.append(dict(part=pid, number=m.get("number"), n_notes=len(notes),
                            n_pitched=len(pitched), n_rests=len(rests),
                            barlen=barlen, div=div,
                            events=[_event(n) for n in notes]))
    return out


def _event(n):
    d = n.find("duration")
    t = n.find("type")
    p = n.find("pitch")
    return dict(
        dur=int(d.text) if d is not None else None,
        type=t.text if t is not None else None,
        pitch=(p.find("step").text + p.find("octave").text) if p is not None else None,
        measure_rest=(n.find("rest") is not None
                      and n.find("rest").get("measure") == "yes"),
        chord=n.find("chord") is not None,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xml", default=str(ARTEFACT))
    ap.add_argument("--json-out")
    args = ap.parse_args()

    rows = bars(args.xml)
    if not rows:
        print("DEAD: the artefact yielded no measures at all", file=sys.stderr)
        return 2
    print(f"REACH  file={Path(args.xml).name}")
    print(f"REACH  measures={len(rows)}  parts={len(set(r['part'] for r in rows))}")

    lone = [r for r in rows if r["n_notes"] == 1 and r["n_pitched"] == 1]
    under = [r for r in lone
             if r["events"][0]["dur"] is not None and r["barlen"]
             and r["events"][0]["dur"] < r["barlen"]]
    quarter = [r for r in under
               if r["events"][0]["dur"] == 96 and r["barlen"] == 192]

    print()
    print(f"bars whose ENTIRE content is one PITCHED note : {len(lone)}")
    print(f"  ...of which UNDERFULL                       : {len(under)}")
    print(f"  ...of which a lone QUARTER in a 2/4 bar     : {len(quarter)}")

    seen = {(r["part"], r["number"]) for r in lone}
    missing = NAMED - seen
    print()
    print(f"the handoff's six named bars, found here     : {len(NAMED - missing)}/6")
    if missing:
        print(f"  ⚠️ NOT in this population: {sorted(missing)}")
    for r in sorted(lone, key=lambda r: (r["part"], int(r["number"]))):
        if (r["part"], r["number"]) in NAMED:
            e = r["events"][0]
            print(f"  {r['part']:>3} m{r['number']:<4} {e['pitch']:<4} "
                  f"dur={e['dur']} of {int(r['barlen'])}  type={e['type']}")

    print()
    c = collections.Counter((r["events"][0]["dur"], int(r["barlen"] or 0),
                             r["events"][0]["type"]) for r in lone)
    print("lone-pitched bars by (duration, bar length, type):")
    for k, v in c.most_common():
        print(f"   dur={k[0]:<5} bar={k[1]:<5} type={k[2]:<10} n={v}")
    print()
    print("by part:", dict(collections.Counter(r["part"] for r in lone)))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            dict(lone=lone, under=under, quarter=quarter), indent=1))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
