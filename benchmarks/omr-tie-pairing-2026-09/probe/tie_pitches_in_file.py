"""How many WRITTEN ties in a MusicXML file join two notes of one pitch.

    python3 benchmarks/omr-tie-pairing-2026-09/probe/tie_pitches_in_file.py F.musicxml [...]

A `<tie type="start">` is matched to the next `<tie type="stop">` in the same
part and voice (document order). Reports matched pairs by pitch relation:
`same`, `same_step` (spelling differs), `different`; and unmatched ends.
⚠️ Internal consistency only -- a same-pitch tie can still be on the wrong
notes; this says nothing about the print.
"""
import collections
import sys
import xml.etree.ElementTree as ET


def pitch_of(note):
    p = note.find("pitch")
    if p is None:
        return None
    return (p.findtext("step"), p.findtext("alter") or "0",
            p.findtext("octave"))


def main(paths):
    for path in paths:
        root = ET.parse(path).getroot()
        rel = collections.Counter()
        for part in root.iter("part"):
            open_ = collections.defaultdict(list)
            for note in part.iter("note"):
                voice = note.findtext("voice") or "1"
                types = {t.get("type") for t in note.findall("tie")}
                pit = pitch_of(note)
                if "stop" in types:
                    if open_[voice]:
                        # the open start of the SAME step if any, else oldest
                        cands = open_[voice]
                        match = next((c for c in cands if pit and c
                                      and c[0] == pit[0] and c[2] == pit[2]),
                                     cands[0])
                        cands.remove(match)
                        if match == pit:
                            rel["same"] += 1
                        elif match and pit and match[0] == pit[0] \
                                and match[2] == pit[2]:
                            rel["same_step"] += 1
                        else:
                            rel["different"] += 1
                    else:
                        rel["stop_without_start"] += 1
                if "start" in types:
                    open_[voice].append(pit)
            for v in open_.values():
                rel["start_without_stop"] += len(v)
        print(path, dict(rel))


if __name__ == "__main__":
    main(sys.argv[1:])
