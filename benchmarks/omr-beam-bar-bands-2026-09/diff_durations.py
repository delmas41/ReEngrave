"""Diff the two arms' exported MusicXML, note by note, and name every change.

Reports each differing note as `part / measure / index: old -> new`, so the
claim "these durations changed" is a list rather than a count.

Exits non-zero if an arm's file is missing — an absent arm must never read as
"nothing changed".
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def notes(path: Path) -> list[tuple[str, str, int, str, str, str]]:
    """(part, measure, index, pitch, written value, duration IN WHOLE NOTES).

    ⚠️ **`<duration>` is not comparable across the two arms and comparing it
    raw is a measurement bug — one this probe shipped with and which invented
    1,144 duration changes on `brahms-sym1-mvt1-317803-p4`, every note in the
    file.** `<duration>` is an integer count of `<divisions>` per quarter, and
    `export._compute_divisions` sets divisions as the LCM over the part's note
    values. One note on the page becoming a 16th where the part had none takes
    divisions 8 -> 16 and DOUBLES every `<duration>` integer in that part while
    every `<type>` stays exactly as it was. The notes did not change; the scale
    they are counted in did.

    So the value is normalised by its own part's divisions, and the written
    `<type>` (with dots and any tuplet ratio) is compared alongside it.
    """
    root = ET.parse(path).getroot()
    out = []
    for part in root.findall("part"):
        pid = part.get("id", "?")
        divisions = 1.0
        for measure in part.findall("measure"):
            mno = measure.get("number", "?")
            d = measure.find("attributes/divisions")
            if d is not None and d.text:
                divisions = float(d.text)
            for i, n in enumerate(measure.findall("note")):
                p = n.find("pitch")
                name = (f"{p.findtext('step','?')}{p.findtext('octave','?')}"
                        if p is not None else "rest")
                written = n.findtext("type", "-") + "." * len(n.findall("dot"))
                tm = n.find("time-modification")
                if tm is not None:
                    written += (f"[{tm.findtext('actual-notes','?')}:"
                                f"{tm.findtext('normal-notes','?')}]")
                raw = n.findtext("duration")
                quarters = f"{float(raw) / divisions:.6g}" if raw else "-"
                out.append((pid, mno, i, name, written, quarters))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--rows", nargs="+", required=True)
    a = ap.parse_args()

    grand = Counter()
    missing = []
    for row in a.rows:
        fe = a.out_dir / f"{row}.even.musicxml"
        ff = a.out_dir / f"{row}.fixed.musicxml"
        if not (fe.is_file() and ff.is_file()):
            missing.append(row)
            continue
        ne, nf = notes(fe), notes(ff)
        if ne == nf:
            print(f"  IDENTICAL  {row}  ({len(ne)} notes)")
            continue
        by_key_e = {(p, m, i): (nm, t, d) for p, m, i, nm, t, d in ne}
        by_key_f = {(p, m, i): (nm, t, d) for p, m, i, nm, t, d in nf}
        changed = [k for k in sorted(by_key_e.keys() & by_key_f.keys())
                   if by_key_e[k] != by_key_f[k]]
        only_e = by_key_e.keys() - by_key_f.keys()
        only_f = by_key_f.keys() - by_key_e.keys()
        dur = [k for k in changed if by_key_e[k][1:] != by_key_f[k][1:]]
        print(f"  DIFFERS    {row}: {len(ne)} -> {len(nf)} notes, "
              f"{len(changed)} changed ({len(dur)} of them a DURATION), "
              f"{len(only_e)} dropped, {len(only_f)} added")
        for k in changed:
            oe, of = by_key_e[k], by_key_f[k]
            mark = "DURATION" if oe[1:] != of[1:] else "pitch/other"
            print(f"      {mark:11s} {k[0]} m{k[1]} #{k[2]}: "
                  f"{oe[0]} {oe[1]}(dur {oe[2]})  ->  {of[0]} {of[1]}(dur {of[2]})")
        grand["changed"] += len(changed)
        grand["duration"] += len(dur)
        grand["dropped"] += len(only_e)
        grand["added"] += len(only_f)

    print(f"\nTOTAL across {len(a.rows)} rows: {dict(grand) or 'no differences'}")
    if missing:
        print(f"FATAL: no arm files for {missing}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
