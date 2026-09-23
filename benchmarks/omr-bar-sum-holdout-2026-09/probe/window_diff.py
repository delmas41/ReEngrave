"""Which bars of a window changed between two exported files, and how.

⚠️ THE QUESTION IT ANSWERS is the one the count-page figure raises: 68 bars of
the Litolff count page did not add up before and 0 do after, while the export
report NAMES only 59 held bars there. A difference of nine between two numbers
that ought to describe one fact is exactly the shape this project has been
burned by, so it is measured rather than explained away.
"""
from __future__ import annotations

import argparse
import collections
import xml.etree.ElementTree as ET


def bars(path, lo, hi):
    root = ET.parse(path).getroot()
    names = {sp.get("id"): (sp.find("part-name").text
                            if sp.find("part-name") is not None else sp.get("id"))
             for sp in root.findall(".//score-part")}
    out = {}
    for part in root.findall("part"):
        pid = part.get("id")
        for meas in part.findall("measure"):
            try:
                n = int(meas.get("number"))
            except (TypeError, ValueError):
                continue
            if not (lo <= n <= hi):
                continue
            notes = meas.findall("note")
            lone_measure_rest = (
                len(notes) == 1
                and notes[0].find("rest") is not None
                and notes[0].find("rest").get("measure") == "yes")
            out[(pid, n)] = {
                "part": names.get(pid, pid),
                "notes": len(notes),
                "pitched": len([x for x in notes if x.find("pitch") is not None]),
                "lone_measure_rest": lone_measure_rest,
            }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base")
    ap.add_argument("arm")
    ap.add_argument("--first-bar", type=int, default=49)
    ap.add_argument("--last-bar", type=int, default=82)
    args = ap.parse_args(argv)
    b = bars(args.base, args.first_bar, args.last_bar)
    a = bars(args.arm, args.first_bar, args.last_bar)
    changed = [k for k in b if k in a and b[k] != a[k]]
    became_empty = [k for k in changed if a[k]["lone_measure_rest"]
                    and not b[k]["lone_measure_rest"]]
    by_part = collections.Counter(a[k]["part"] for k in became_empty)
    print("window %d-%d: %d staff-bars in base, %d in arm"
          % (args.first_bar, args.last_bar, len(b), len(a)))
    print("  changed                 %d" % len(changed))
    print("  became a marked empty bar %d" % len(became_empty))
    print("  by part: %s" % dict(by_part.most_common()))
    other = [k for k in changed if k not in became_empty]
    print("  changed some OTHER way  %d %s" % (len(other), other[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
