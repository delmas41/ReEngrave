"""Per-movement part list from a reference .mxl / .musicxml — stdlib only.

This is the ground truth for "does the instrumentation change between
movements".  It is a fact about the ENCODING, not the engraving, so it is used
here only to say WHICH INSTRUMENTS EXIST in each movement — never how many
staves the printed page devotes to them.
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def read_xml(path: Path) -> bytes:
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if n.lower().endswith((".xml", ".musicxml"))
                     and not n.startswith("META-INF")]
            # container.xml points at the rootfile; the heuristic below is
            # enough for these files and is asserted by the caller's counts.
            names.sort(key=lambda n: (n.count("/"), len(n)))
            return z.read(names[0])
    return path.read_bytes()


def parts(path: Path):
    root = ET.fromstring(read_xml(path))
    out = []
    for sp in root.iter("score-part"):
        name = (sp.findtext("part-name") or "").strip()
        abbr = (sp.findtext("part-abbreviation") or "").strip()
        inst = ""
        for si in sp.iter("score-instrument"):
            inst = (si.findtext("instrument-name") or "").strip()
            break
        out.append((sp.get("id"), name, abbr, inst))
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        p = Path(a)
        ps = parts(p)
        print(f"### {p.name}  ({len(ps)} parts)")
        for pid, name, abbr, inst in ps:
            print(f"  {pid:6s} {name!r:34s} abbr={abbr!r:12s} inst={inst!r}")
        print()
