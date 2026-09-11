"""The table Sean's observation is about: rest <duration> values in the FILE.

The record probe (`reach.py`) can only see rests the record HOLDS. The
exporter also writes a rest into every bar it read nothing in, so the file's
population is strictly larger and the two must be counted apart. This counts
the file.

⚠️ `<duration>` is in DIVISIONS, and divisions are per part. The bar length is
taken from each part's own `<time>` where it declares one, and reported as
UNKNOWN otherwise -- never defaulted, because defaulting to 4/4 is the very
fault under measurement.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("musicxml")
    ap.add_argument("--bar-beats", type=float, default=2.0,
                    help="the PRINTED bar length, hand-read off the plate")
    args = ap.parse_args(argv)
    root = ET.parse(args.musicxml).getroot()

    lengths = Counter()
    measure_yes = 0
    with_type = Counter()
    divisions_seen = Counter()
    for part in root.findall("part"):
        div = None
        for meas in part.findall("measure"):
            d = meas.find("./attributes/divisions")
            if d is not None:
                div = float(d.text)
                divisions_seen[div] += 1
            for note in meas.findall("note"):
                rest = note.find("rest")
                if rest is None:
                    continue
                dur = note.find("duration")
                if dur is None or div is None:
                    lengths["no duration"] += 1
                    continue
                ql = float(dur.text) / div
                lengths[ql] += 1
                if rest.get("measure") == "yes":
                    measure_yes += 1
                t = note.find("type")
                with_type[(ql, t.text if t is not None else None)] += 1

    total = sum(n for k, n in lengths.items() if isinstance(k, float))
    print("divisions: %s" % dict(divisions_seen))
    print("rests: %d, with measure=\"yes\": %d" % (total, measure_yes))
    print("%-10s %-8s %s" % ("length(ql)", "count", "verdict"))
    for k in sorted((x for x in lengths if isinstance(x, float))):
        mark = "OK" if abs(k - args.bar_beats) < 1e-6 else "!!"
        print("%-10s %-8d %s" % (k, lengths[k], mark))
    print()
    print("by <type>:")
    for (ql, t), n in sorted(with_type.items()):
        print("   %-8s %-10s x%d" % (ql, t, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
