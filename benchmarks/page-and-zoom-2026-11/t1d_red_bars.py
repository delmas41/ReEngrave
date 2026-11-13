"""ROADMAP 2.307 T1d -- which bars are red OFF only / ON only (gross, not net), from the two arms' MusicXML (measure only).

    python3 benchmarks/page-and-zoom-2026-11/t1d_red_bars.py WORK_DIR PLATE

A bar is red where any element in it carries the unread colour `#D00000`.
"""
import re
import sys
import xml.etree.ElementTree as ET


def red_bars(path):
    root = ET.parse(path).getroot()
    out = set()
    for part in root.iter("part"):
        for m in part.iter("measure"):
            if any((e.get("color") or "").upper() == "#D00000" for e in m.iter()):
                out.add((part.get("id"), m.get("number")))
    return out


def main():
    work, plate = sys.argv[1], sys.argv[2]
    a = red_bars("%s/%s.off.musicxml" % (work, plate))
    b = red_bars("%s/%s.on.musicxml" % (work, plate))
    print(plate, "red OFF", len(a), "ON", len(b), "| newly red", sorted(b - a), "| cleared", sorted(a - b))


if __name__ == "__main__":
    main()
