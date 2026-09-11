"""Does each exported bar ADD UP to the meter -- and what does a short bar hold?

⚠️ THIS IS THE PROBE THE OBSERVATION IS ACTUALLY ABOUT, and it exists because
asking the renderer refuted the obvious reading. Sean's complaint names a
GLYPH ("a single quarter note") and says why it is wrong ("the measure needs 2
quarters to be filled") -- so the fact he is reporting is an UNDERFULL BAR, and
the glyph is only how he spotted it. Verovio draws our unsized 4.0 whole rests
as whole rests, so those are not what his eye caught.

It sums each measure's voice-1 timeline the way a reader does -- `<backup>` and
`<forward>` move the cursor, a chord member does not advance it -- and reports
every bar whose total is not the meter, with what it holds.
"""
from __future__ import annotations

import argparse
import collections
import xml.etree.ElementTree as ET
from pathlib import Path


def bar_total(meas, div):
    """Quarter-notes of the LONGEST voice in the bar, and what it holds."""
    per_voice = collections.defaultdict(float)
    holds = collections.Counter()
    for el in meas:
        if el.tag == "note":
            if el.find("chord") is not None:
                continue            # a chord member does not advance time
            if el.find("grace") is not None:
                continue
            d = el.find("duration")
            if d is None:
                continue
            v = el.find("voice")
            v = v.text if v is not None else "1"
            per_voice[v] += float(d.text) / div
            if el.find("rest") is not None:
                t = el.find("type")
                holds["rest:%s" % (t.text if t is not None else
                                   ("measure" if el.find("rest").get("measure")
                                    else "untyped"))] += 1
            else:
                holds["note"] += 1
    return (max(per_voice.values()) if per_voice else 0.0), holds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("musicxml")
    ap.add_argument("--bar-beats", type=float, default=2.0)
    ap.add_argument("--show", type=int, default=8)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero when the instrument measured NOTHING")
    args = ap.parse_args(argv)
    root = ET.parse(args.musicxml).getroot()

    verdict = collections.Counter()
    short_shapes = collections.Counter()
    long_shapes = collections.Counter()
    lone_quarter = 0
    for part in root.findall("part"):
        div = None
        for meas in part.findall("measure"):
            d = meas.find("./attributes/divisions")
            if d is not None:
                div = float(d.text)
            if div is None:
                continue
            total, holds = bar_total(meas, div)
            if abs(total) < 1e-9:
                verdict["EMPTY (no timed content)"] += 1
                continue
            if abs(total - args.bar_beats) < 1e-6:
                verdict["exact"] += 1
            elif total < args.bar_beats:
                verdict["SHORT"] += 1
                short_shapes[(round(total, 4),
                              tuple(sorted(holds.items())))] += 1
                if holds == collections.Counter({"rest:quarter": 1}):
                    lone_quarter += 1
            else:
                verdict["OVERFULL"] += 1
                long_shapes[(round(total, 4),
                             tuple(sorted(holds.items())))] += 1

    n = sum(verdict.values())
    print("BARS: %d" % n)
    for k, v in verdict.most_common():
        print("   %-26s %5d  (%.1f%%)" % (k, v, 100.0 * v / n))
    print("\n   of the SHORT bars, %d hold exactly ONE QUARTER REST and "
          "nothing else" % lone_quarter)
    print("\ncommonest SHORT bars (total ql, contents):")
    for (t, holds), c in short_shapes.most_common(args.show):
        print("   %-7s %-46s x%d" % (t, dict(holds), c))
    print("\ncommonest OVERFULL bars:")
    for (t, holds), c in long_shapes.most_common(args.show):
        print("   %-7s %-46s x%d" % (t, dict(holds), c))

    if args.check:
        # ⚠️ THE CHECK IS ABOUT THE INSTRUMENT, NOT ABOUT THE SCORE. It fails
        # when nothing was assessable -- a file with no `<divisions>`, no
        # measures, or no timed content -- because that is the state in which
        # a clean "0 short, 0 overfull" would be a lie. It deliberately does
        # NOT fail on a threshold of bad bars: the moment this number becomes
        # a gate it becomes a number to drive down, and it is gamed by
        # emitting FEWER symbols, which is the direction that makes the file
        # worse.
        if n == 0:
            print("\nINSTRUMENT DEAD: no bar could be assessed.")
            return 1
        print("\ninstrument LIVE: %d bars assessed" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
