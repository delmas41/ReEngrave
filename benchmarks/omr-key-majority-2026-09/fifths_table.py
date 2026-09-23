"""`<key><fifths>` per part per measure out of a MusicXML file.

    python3 benchmarks/omr-key-majority-2026-09/fifths_table.py <file.musicxml|.mxl>

Prints one row per part: its name, the fifths it opens on, and every CHANGE
(`measure=fifths`) after that. A part that never states a key prints `-` —
MusicXML carries the last stated key forward, so an omitted `<key>` is a
CARRY, not a zero, and this tool keeps the two apart.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
import zipfile


def load(path: str) -> ET.Element:
    if path.endswith(".mxl"):
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist()
                        if n.endswith(".xml") and not n.startswith("META-INF"))
            return ET.fromstring(z.read(name))
    return ET.parse(path).getroot()


def part_names(root: ET.Element) -> dict:
    out = {}
    for sp in root.iter("score-part"):
        pid = sp.get("id")
        nm = sp.findtext("part-name") or ""
        out[pid] = nm.strip()
    return out


def rows(root: ET.Element):
    names = part_names(root)
    for part in root.iter("part"):
        pid = part.get("id")
        seq = []
        for measure in part.findall("measure"):
            num = measure.get("number")
            for attrs in measure.findall("attributes"):
                f = attrs.findtext("key/fifths")
                if f is not None:
                    seq.append((num, int(f)))
        yield pid, names.get(pid, ""), seq


def main(path: str) -> None:
    root = load(path)
    print(f"== {path}")
    for pid, name, seq in rows(root):
        if not seq:
            print(f"{pid:>6} {name[:28]:<28} -")
            continue
        opening = seq[0][1]
        changes = [f"m{n}={v}" for (n, v), (_, prev)
                   in zip(seq[1:], seq[:-1]) if v != prev]
        print(f"{pid:>6} {name[:28]:<28} {opening:>3}"
              + (("   changes: " + " ".join(changes)) if changes else ""))


if __name__ == "__main__":
    main(sys.argv[1])
