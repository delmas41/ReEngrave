"""The written arcs of an exported MusicXML, as (kind, start_rg, stop_rg) by glyph key (`rg` = the notehead's glyph key, stamped by the
traced export). Ties pair a `<tie type=start>` with the next note of the same part, voice and pitch carrying `<tie type=stop>`; slurs pair
by `number=` within the part, in document order. Also returns every note's rg so a head can be checked as 'in the file'."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple


def parse(xml_text: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_text)
    ties: List[Tuple[str, str]] = []
    slurs: List[Tuple[str, str]] = []
    notes: Dict[str, Dict[str, Any]] = {}
    dangling = {"tie_start": 0, "tie_stop": 0, "slur_start": 0, "slur_stop": 0}
    gcount = 0
    for part in root.iter("part"):
        open_ties: Dict[Tuple[str, str], str] = {}
        open_slurs: Dict[str, List[str]] = {}
        for m in part.findall("measure"):
            for el in m.findall("note"):
                rg = el.get("rg")
                if el.find("rest") is not None:
                    continue
                voice = el.findtext("voice") or "1"
                p = el.find("pitch")
                pit = "" if p is None else "%s%s%s" % (p.findtext("step"), p.findtext("alter") or "", p.findtext("octave"))
                if el.find("chord") is None:
                    gcount += 1                     # a new chord group (a note with no <chord/>); members share `grp`
                if rg:
                    notes[rg] = {"voice": voice, "pitch": pit, "grp": gcount, "part": part.get("id")}
                tis = [t.get("type") for t in el.findall("tie")]
                key = (voice, pit)
                if "stop" in tis:
                    s = open_ties.pop(key, None)
                    if s is not None and rg:
                        ties.append((s, rg))
                    else:
                        dangling["tie_stop"] += 1
                if "start" in tis:
                    if rg:
                        open_ties[key] = rg
                nt = el.find("notations")
                if nt is None:
                    continue
                for s in nt.findall("slur"):
                    n = s.get("number") or "1"
                    if s.get("type") == "start":
                        open_slurs.setdefault(n, []).append(rg or "")
                    elif s.get("type") == "stop":
                        st = open_slurs.get(n) or []
                        if st:
                            a = st.pop()
                            if a and rg:
                                slurs.append((a, rg))
                        else:
                            dangling["slur_stop"] += 1
        dangling["tie_start"] += len(open_ties)
        dangling["slur_start"] += sum(len(v) for v in open_slurs.values())
    return {"ties": ties, "slurs": slurs, "notes": notes, "dangling": dangling}


if __name__ == "__main__":
    import sys
    r = parse(open(sys.argv[1]).read())
    print(len(r["ties"]), "ties", len(r["slurs"]), "slurs", len(r["notes"]), "notes", r["dangling"])
