"""Classify EVERY tie that two arms disagree about, one by one.

⚠️ AN AGGREGATE HIDES A TRANSITION. `resolved 115 -> 113` is consistent with
nothing moving, with two losses, and with 40 losses against 38 gains. This
names each tie by (part, measure, voice, pitch) and reports the four cells:

    both      resolves in both arms
    GAINED    resolves only in the fix arm
    LOST      resolves only in the base arm
    neither   resolves in neither

"Resolves" is `record.Checkable`'s invariant — a tie's two ends must be the
same pitch — read off the exported file, so it needs no truth and reaches
every moved element. ⚠️ ONE-SIDED: an unresolved tie is certainly wrong; a
resolved one may still be invented.

    python3 .../tie_delta.py --base A.musicxml --fix B.musicxml [--list]
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys
import xml.etree.ElementTree as ET


def _pitch(note: ET.Element) -> str | None:
    p = note.find("pitch")
    if p is None:
        return None
    return "%s%s%s" % (p.findtext("step", ""),
                       {"-1": "b", "1": "#", "-2": "bb", "2": "x"}.get(
                           p.findtext("alter", "0"), ""),
                       p.findtext("octave", ""))


def ties(path: pathlib.Path) -> dict[tuple, bool]:
    """key -> resolves. Key names the tie, not its ordinal."""
    out: dict[tuple, bool] = {}
    root = ET.parse(path).getroot()
    for part in root.iter("part"):
        pid = part.get("id")
        stream: dict[str, list[tuple[str, ET.Element]]] = {}
        for measure in part.iter("measure"):
            num = measure.get("number")
            for note in measure.iter("note"):
                stream.setdefault(note.findtext("voice", "1"),
                                  []).append((num, note))
        for voice, notes in stream.items():
            for i, (num, note) in enumerate(notes):
                if note.find('.//tied[@type="start"]') is None:
                    continue
                want = _pitch(note)
                j = i + 1
                while j < len(notes) and notes[j][1].find("chord") is not None:
                    j += 1
                ok = False
                while j < len(notes):
                    nxt = notes[j][1]
                    if (_pitch(nxt) == want
                            and nxt.find('.//tied[@type="stop"]') is not None):
                        ok = True
                        break
                    j += 1
                    if j < len(notes) and notes[j][1].find("chord") is None:
                        break
                key = (pid, num, voice, want)
                # A repeated key on one event is a genuine second tied head;
                # number them so neither is lost.
                n = 0
                while (key + (n,)) in out:
                    n += 1
                out[key + (n,)] = ok
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--fix", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if len(args.base) != len(args.fix):
        raise SystemExit("FATAL: arms must have the same number of files")

    cells: collections.Counter = collections.Counter()
    rows: collections.Counter = collections.Counter()
    for b, f in zip(sorted(args.base), sorted(args.fix)):
        tb, tf = ties(b), ties(f)
        for key in set(tb) | set(tf):
            rb, rf = tb.get(key), tf.get(key)
            if rb is None:
                cell = "ADDED_resolves" if rf else "ADDED_unresolved"
            elif rf is None:
                cell = "REMOVED_resolved" if rb else "REMOVED_unresolved"
            elif rb and rf:
                cell = "both"
            elif rf:
                cell = "GAINED"
            elif rb:
                cell = "LOST"
            else:
                cell = "neither"
            cells[cell] += 1
            if cell in ("GAINED", "LOST", "ADDED_resolves",
                        "ADDED_unresolved", "REMOVED_resolved",
                        "REMOVED_unresolved"):
                rows[(b.name.split(".")[0], cell)] += 1
                if args.list:
                    print(f"  {cell:19s} {b.name.split('.')[0][:34]:36s} "
                          f"part={key[0]} m{key[1]} voice{key[2]} {key[3]}")
    total = sum(cells.values())
    if not total:
        sys.stderr.write("⚠️ ZERO ties compared — a dead instrument.\n")
        return 2
    print(f"\n  {total} ties named across {len(args.base)} file pairs")
    for k in ("both", "neither", "GAINED", "LOST", "ADDED_resolves",
              "ADDED_unresolved", "REMOVED_resolved", "REMOVED_unresolved"):
        print(f"    {k:20s} {cells[k]}")
    if rows:
        print("\n  by file:")
        for (name, cell), n in sorted(rows.items()):
            print(f"    {name[:40]:42s} {cell:20s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
