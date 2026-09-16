"""Does each bar sum to the meter THE FILE ITSELF DECLARES at that bar?

⚠️ THIS IS A SECOND QUESTION, NOT A BETTER ONE, and on Brahms the two come
apart where on Litolff they could not. `probe/bar_fill.py` compares every bar
against ONE hand-read `--bar-beats`, i.e. against the PRINT. That is the right
question for a cost measurement. But the Litolff figure CLAUDE.md quotes
("38.0% -> 69.2%") was taken on a document whose declared meter IS the printed
one, so it is simultaneously a self-consistency figure -- and a carry that
propagates a WRONG meter can raise self-consistency while lowering truth.

So both are reported, and they must be read as a PAIR:

  * TRUTH-referenced (`bar_fill.py --bar-beats`)  -- is the music right?
  * SELF-referenced (this)                        -- does the file agree with
                                                     its own `<time>`?

`bar_total` is IMPORTED from `bar_fill.py`, never restated: this repo has a
recorded case of one numbering rule living in two places and the copies
disagreeing by 108 rows.
"""
from __future__ import annotations
import argparse, collections, sys, xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "omr-rest-sizing-2026-09" / "probe"))
from bar_fill import bar_total                                   # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("musicxml")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    root = ET.parse(a.musicxml).getroot()

    verdict = collections.Counter()
    declared = collections.Counter()
    for part in root.findall("part"):
        div = None
        beats = None
        for meas in part.findall("measure"):
            d = meas.find("./attributes/divisions")
            if d is not None:
                div = float(d.text)
            t = meas.find("./attributes/time")
            if t is not None:
                n = t.findtext("beats")
                b = t.findtext("beat-type")
                if n and b:
                    beats = float(n) * 4.0 / float(b)
                    declared["%s/%s" % (n, b)] += 1
            if div is None or beats is None:
                verdict["NO DECLARED METER"] += 1
                continue
            total, _ = bar_total(meas, div)
            if abs(total) < 1e-9:
                verdict["EMPTY (no timed content)"] += 1
            elif abs(total - beats) < 1e-6:
                verdict["exact"] += 1
            elif total < beats:
                verdict["SHORT"] += 1
            else:
                verdict["OVERFULL"] += 1

    n = sum(verdict.values())
    print("BARS: %d  (scored against the file's OWN <time>)" % n)
    for k, v in verdict.most_common():
        print("   %-26s %5d  (%.1f%%)" % (k, v, 100.0 * v / n))
    print("\n<time> declarations in the file:")
    for k, v in declared.most_common():
        print("   %-10s x%d" % (k, v))
    if a.check:
        # Same contract as bar_fill: it fails when the INSTRUMENT measured
        # nothing, and NEVER on a threshold -- a bar-fill number used as a
        # gate is gamed by emitting FEWER symbols.
        if n == 0:
            print("\nINSTRUMENT DEAD: no bar could be assessed.")
            return 1
        print("\ninstrument LIVE: %d bars assessed" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
