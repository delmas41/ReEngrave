"""Read the PART LIST out of a reference encoding — names, count, nothing else.

Deliberately stdlib-only and deliberately shallow. The question this answers is
"how many parts does the encoder declare, and what does it call them", which is
one read of `<part-list>`. Anything deeper (notes, measures) belongs to the
scoring harnesses that already exist.

⚠️ A `<score-part>` is not a staff and is not an instrument. It is the encoder's
unit of accounting, and the whole point of this benchmark is that it does not
agree with what the page prints.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def _score_root(path: Path) -> ET.Element:
    """Parse .mxl (zipped) or .musicxml (plain), returning the score element."""
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as zf:
            # META-INF/container.xml names the rootfile; fall back to the one
            # non-META .xml member, which is what every file here actually has.
            name = None
            try:
                container = ET.fromstring(zf.read("META-INF/container.xml"))
                rf = container.find(".//{*}rootfile")
                if rf is not None:
                    name = rf.get("full-path")
            except KeyError:
                pass
            if name is None:
                cands = [n for n in zf.namelist()
                         if n.lower().endswith((".xml", ".musicxml"))
                         and not n.startswith("META-INF")]
                if not cands:
                    raise ValueError(f"no score member in {path}")
                name = cands[0]
            return ET.fromstring(zf.read(name))
    return ET.parse(path).getroot()


def part_list(path: Path) -> list[dict]:
    """Every `<score-part>`, in document order, with the names it declares."""
    root = _score_root(path)
    out: list[dict] = []
    for sp in root.findall(".//{*}part-list/{*}score-part"):
        pid = sp.get("id")
        name_el = sp.find("{*}part-name")
        abbr_el = sp.find("{*}part-abbreviation")
        out.append({
            "id": pid,
            "name": (name_el.text or "").strip() if name_el is not None else "",
            "abbrev": (abbr_el.text or "").strip() if abbr_el is not None else "",
        })
    return out


def staves_declared(path: Path) -> dict[str, int]:
    """Max `<staves>` each part declares — a part CAN print on more than one.

    A piano part is the ordinary case (2 staves, 1 part), and it is the exact
    mirror of the condensation this benchmark is about: there, several parts
    share one staff; here, one part spreads over several. Both break a
    parts==staves assumption, in opposite directions.
    """
    root = _score_root(path)
    out: dict[str, int] = {}
    for part in root.findall(".//{*}part"):
        pid = part.get("id")
        n = 1
        for s in part.findall(".//{*}attributes/{*}staves"):
            try:
                n = max(n, int((s.text or "1").strip()))
            except ValueError:
                pass
        out[pid] = n
    return out


def main(argv: list[str]) -> int:
    for arg in argv:
        p = Path(arg)
        parts = part_list(p)
        st = staves_declared(p)
        total = sum(st.get(x["id"], 1) for x in parts)
        print(f"\n{p.name}: {len(parts)} parts, {total} declared staves")
        for i, x in enumerate(parts):
            n = st.get(x["id"], 1)
            extra = f"  [{n} staves]" if n != 1 else ""
            print(f"  {i:3d} {x['name'][:44]:44s} {x['abbrev'][:14]:14s}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
