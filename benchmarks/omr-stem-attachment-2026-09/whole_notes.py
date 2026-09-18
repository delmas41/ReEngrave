"""A WHOLE NOTE HAS NO STEM -- and the record gives 14 of them one.

Found while re-deriving the beam-mate tier's fire set, not looked for. It is
the same shape the 2026-09-17 handoff already records on the projection path
(*"the attachment test has false POSITIVES: 8 whole notes were given a
stem"*), arriving on the BORROW path as well: 6 of Breitkopf's 296 borrowed
directions land on a head whose class is a whole note.

⚠️ THE CONVENTION IS AS RIGID AS THEY GET. `docs/engraving-conventions.md`
`[C9 + L10]` excludes whole notes throughout -- a semibreve carries no stem, so
a stem direction for one is not a reading, it is a confident wrong answer fed
to `Q.EVENT` and `Q.VOICES`.

⚠️ AND THE RISK IS NAMED RATHER THAN WAVED AWAY: `notehead_class` can misread
a HALF note as a whole one, and a half note does have a stem. Refusing on the
class alone would then cost a correct reading. So this prices BOTH sides --
how many whole-note heads get a direction, and how large the class is -- and
proposes nothing.

    python3 whole_notes.py <record.json> [...]
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array                            # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: whole_notes.py <record.json> [...]", file=sys.stderr)
        return 2
    for p in sys.argv[1:]:
        klass = {}
        for o in stream_array(p, "observations"):
            if o.get("quantity") == "notehead_class":
                klass[o["subject"]] = str(o.get("value"))
        if not klass:
            print(f"DEAD: {Path(p).name} holds no notehead_class",
                  file=sys.stderr)
            return 2
        c: collections.Counter = collections.Counter()
        for v in stream_array(p, "verdicts"):
            if v.get("quantity") != "stem_direction":
                continue
            k = klass.get(v["subject"], "")
            if "Whole" not in k:
                continue
            c["whole-note heads with a stem_direction verdict"] += 1
            if v.get("outcome") == "decided":
                c[f"  DECIDED `{v.get('reason')}` -- a stem for a "
                  f"stemless note"] += 1
            else:
                c[f"  abstained `{v.get('reason')}` -- correct"] += 1
        tot_whole = sum(1 for k in klass.values() if "Whole" in k)
        print(f"{Path(p).name}")
        print(f"   noteheads in the record                  "
              f"{len(klass):>6}")
        print(f"   of which classed Whole                   {tot_whole:>6}"
              f"   ({tot_whole/len(klass):.1%})")
        for k, n in c.most_common():
            print(f"   {k:<54} {n:>6}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
