"""The count page's own bars, base vs arm — ROADMAP 2.8's 68.

The Litolff count page (`benchmarks/acceptance/manifest.json`, pdf index 3,
works row `…984073-p3`) is bars 49–82. The roadmap records **68 of 408
staff-bars** there not summing to 2/4 before 2.8; this cuts the same window
out of an exported file so the before and the after are the same measurement,
taken the same way, and not two different ones compared.

⚠️ It reuses `bar_sum_check.bar_sums` rather than restating the arithmetic.
"""
from __future__ import annotations

import argparse
import collections
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bar_sum_check import bar_sums          # noqa: E402


def window(path, lo, hi):
    root = ET.parse(path).getroot()
    names = {sp.get("id"): (sp.find("part-name").text
                            if sp.find("part-name") is not None else sp.get("id"))
             for sp in root.findall(".//score-part")}
    total = 0
    bad_by_part = collections.Counter()
    kinds = collections.Counter()
    rows = []
    for part in root.findall("part"):
        div = beats = bt = None
        for meas in part.findall("measure"):
            attrs = meas.find("attributes")
            if attrs is not None:
                d = attrs.find("divisions")
                if d is not None:
                    div = float(d.text)
                t = attrs.find("time")
                if t is not None and t.find("beats") is not None:
                    beats = float(t.find("beats").text)
                    bt = float(t.find("beat-type").text)
            try:
                n = int(meas.get("number"))
            except (TypeError, ValueError):
                continue
            if not (lo <= n <= hi) or div is None or beats is None:
                continue
            total += 1
            want = beats * 4.0 / bt
            per_voice, _mr, holds = bar_sums(meas, div)
            got = None
            for _v, g in sorted(per_voice.items()):
                if g is None or abs(g - want) < 1e-6:
                    continue
                got = g
                break
            if got is None:
                continue
            name = names.get(part.get("id"), part.get("id"))
            bad_by_part[name] += 1
            kinds["overfull" if got > want else "short"] += 1
            rows.append({"part": name, "measure": n, "quarters": got,
                         "want": want, "holds": dict(holds)})
    return total, bad_by_part, kinds, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("musicxml", nargs="+")
    ap.add_argument("--first-bar", type=int, default=49)
    ap.add_argument("--last-bar", type=int, default=82)
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args(argv)
    for p in args.musicxml:
        total, bad, kinds, rows = window(p, args.first_bar, args.last_bar)
        print("%s  bars %d-%d: %d staff-bars, %d do not add up %s"
              % (Path(p).name, args.first_bar, args.last_bar, total,
                 sum(bad.values()), dict(kinds)))
        if bad:
            print("   by part: %s" % dict(bad.most_common()))
        for r in rows[: args.show]:
            print("     m%-5s %-24s %s of %s  %s"
                  % (r["measure"], r["part"][:24], r["quarters"], r["want"],
                     r["holds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
