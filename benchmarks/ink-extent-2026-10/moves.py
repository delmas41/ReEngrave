"""2.248: positions the ON arm moved (`from_head_ink`), split inside the staff (-1..9) vs far, and by size.
usage: moves.py ON_RECORD [OFF_MUSICXML ON_MUSICXML]"""
import collections
import json
import re
import sys


def main(path, off_xml=None, on_xml=None):
    r = json.load(open(path))
    r = r.get("record", r)
    c = collections.Counter()
    for o in r["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] != "notehead_staff_position":
            continue
        c["head rows"] += 1
        if "from_head_ink" in d:
            p0 = d["detector_position_float"]
            c["moved"] += 1
            c["  inside staff (-1..9)" if -1.5 < p0 < 9.5 else "  far"] += 1
            s = abs(o["value"] - p0)
            c["  shift %s" % ("<0.3" if s < 0.3 else ("0.3-1" if s < 1 else ">=1"))] += 1
    print(dict(c))
    if off_xml and on_xml:
        def pitches(f):
            return re.findall(r"<step>(.)</step>(?:\s*<alter>[^<]*</alter>)?\s*<octave>(\d)</octave>", open(f).read())
        a, b = pitches(off_xml), pitches(on_xml)
        print("written pitches OFF %d ON %d, differing in sequence: %d" % (len(a), len(b), sum(x != y for x, y in zip(a, b))))


if __name__ == "__main__":
    main(*sys.argv[1:])
