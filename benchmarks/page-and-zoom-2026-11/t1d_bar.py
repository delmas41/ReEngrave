"""Print one bar of both arms (notes/rests with value, pitch, colour) -- for tracing a bar that got worse. Measure only.

    python3 benchmarks/page-and-zoom-2026-11/t1d_bar.py WORK_DIR PLATE PART MEASURE
"""
import sys
import xml.etree.ElementTree as ET


def bar(path, part, num):
    root = ET.parse(path).getroot()
    for p in root.iter("part"):
        if p.get("id") != part:
            continue
        for m in p.iter("measure"):
            if m.get("number") == num:
                rows = []
                for e in m:
                    if e.tag == "note":
                        pitch = e.find("pitch")
                        ps = (pitch.findtext("step") + pitch.findtext("octave")) if pitch is not None else ("rest" if e.find("rest") is not None else "?")
                        rows.append("%s %s v%s%s%s" % (ps, e.findtext("type"), e.findtext("voice"), " chord" if e.find("chord") is not None else "",
                                                       " color=" + e.get("color") if e.get("color") else ""))
                    elif e.tag in ("backup", "forward"):
                        rows.append("%s %s" % (e.tag, e.findtext("duration")))
                    elif e.tag == "direction":
                        rows.append("direction " + " ".join(t.text or "" for t in e.iter("words")))
                return rows
    return None


def main():
    work, plate, part, num = sys.argv[1:5]
    for arm in ("off", "on"):
        print("==", arm)
        for r in bar("%s/%s.%s.musicxml" % (work, plate, arm), part, num) or ["(no bar)"]:
            print("  ", r)


if __name__ == "__main__":
    main()
