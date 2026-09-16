"""THE CONTROL: renumbering is RENAMING, so the music must not move.

Two files, one record, two trees. With every `<measure number="N">` replaced
by a placeholder the two must be BYTE-IDENTICAL, and the numbers themselves
must have MOVED. Both halves are required:

  * byte-identity alone is the control this repo has already recorded passing
    VACUOUSLY -- a wedge byte-identity check passed because the function under
    test was never called on any of the three fixtures;
  * "the numbers moved" alone says nothing about whether a note went with them.

So the probe FAILS on either: identical content with no moved number is a dead
instrument, and a moved number with changed content is the thing we are
guarding against.

    python3 .../probe/content_identity.py out/before.musicxml out/after.musicxml
    python3 .../probe/content_identity.py A B --mutate drop-note   # must FAIL

⚠️ `--mutate` is the proof the control CAN fail. It corrupts the SECOND file
in memory in one of three ways -- delete a note, alter a pitch, delete a slur
-- and the probe must then report a content difference and exit non-zero. A
control nobody has seen go red is an assumption.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import re
import sys
from pathlib import Path

MEASURE = re.compile(r'<measure number="(\d+)"')

#: Counted per family so a difference NAMES what moved rather than saying
#: "the files differ". Ordered as the exporter writes them.
ELEMENTS = ("note", "rest", "chord", "pitch", "tie ", "tied", "slur",
            "dynamics", "articulations", "fermata", "words", "wedge",
            "ornaments", "backup", "attributes", "time", "key", "clef",
            "measure")


def normalise(text: str) -> str:
    return MEASURE.sub('<measure number="#"', text)


def numbers(text: str):
    return [int(m) for m in MEASURE.findall(text)]


def counts(text: str):
    return {name.strip(): text.count("<" + name) for name in ELEMENTS}


def mutate(text: str, how: str) -> str:
    """Corrupt the CONTENT while leaving every measure number alone."""
    if how == "drop-note":
        i = text.index("<note")
        j = text.index("</note>", i) + len("</note>")
        return text[:i] + text[j:]
    if how == "alter-pitch":
        return text.replace("<step>C</step>", "<step>D</step>", 1)
    if how == "drop-slur":
        i = text.index("<slur ")
        j = text.index("/>", i) + 2
        return text[:i] + text[j:]
    raise SystemExit("unknown mutation %r" % how)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--mutate", choices=("drop-note", "alter-pitch",
                                         "drop-slur"))
    args = ap.parse_args(argv)

    a = Path(args.before).read_text()
    b = Path(args.after).read_text()
    if args.mutate:
        b = mutate(b, args.mutate)
        print("*** MUTATED the AFTER file: %s -- this run MUST fail ***\n"
              % args.mutate)

    na, nb = numbers(a), numbers(b)
    same_len = len(na) == len(nb)
    moved = (sum(1 for x, y in zip(na, nb) if x != y) if same_len else None)

    print("=" * 74)
    print("1. THE NUMBERS -- did anything happen at all? (positive control)")
    print("=" * 74)
    print("  measure elements   before %d   after %d" % (len(na), len(nb)))
    if same_len:
        print("  numbers that MOVED : %d of %d" % (moved, len(na)))
        deltas = collections.Counter(y - x for x, y in zip(na, nb) if x != y)
        for d, n in sorted(deltas.items()):
            print("     %+d on %d measures" % (d, n))
    else:
        print("  ⚠️ different number of measures -- that is a CONTENT change")

    print()
    print("=" * 74)
    print("2. THE CONTENT -- identical with every measure number blanked?")
    print("=" * 74)
    norm_a, norm_b = normalise(a), normalise(b)
    identical = norm_a == norm_b
    print("  byte-identical outside `<measure number=...>` : %s"
          % ("YES" if identical else "NO"))
    if not identical:
        la, lb = norm_a.splitlines(), norm_b.splitlines()
        print("  lines: before %d, after %d" % (len(la), len(lb)))
        shown = 0
        for line in difflib.unified_diff(la, lb, "before", "after", n=0,
                                         lineterm=""):
            if line.startswith(("---", "+++", "@@")):
                continue
            print("     " + line.strip()[:100])
            shown += 1
            if shown >= 10:
                print("     ...")
                break

    print()
    print("=" * 74)
    print("3. THE FAMILIES -- element counts, so a difference has a NAME")
    print("=" * 74)
    ca, cb = counts(a), counts(b)
    bad_family = False
    for name in ca:
        flag = "" if ca[name] == cb[name] else "   <-- MOVED"
        if flag:
            bad_family = True
        print("  %-14s %7d %7d%s" % (name, ca[name], cb[name], flag))

    print()
    problems = []
    if not identical or bad_family:
        problems.append("the CONTENT moved")
    if same_len and not moved:
        problems.append("no measure number moved -- the instrument is DEAD, "
                        "or the change did not run")
    if not same_len:
        problems.append("the files hold different numbers of measures")
    if problems:
        for p in problems:
            print("FAIL: %s" % p)
        return 1
    print("PASS: %d measure numbers moved and NOTHING else changed." % moved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
