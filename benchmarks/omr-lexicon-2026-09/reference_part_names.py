#!/usr/bin/env python3
"""Every part name the reference encodings hold — the widest no-regression net.

`<part-name>` / `<part-abbreviation>` / `<instrument-name>` out of every
MusicXML in the score library's `reference/` tree, deduplicated. This is the
measurement LEXICON_TR_ALT_2026-08-31.md calls "0": cheapest, broadest, and
almost blind to the fault it is guarding — engraving software writes
"Contrabassoon" where a printed margin says "C. Fag." — so it proves a change
breaks nothing across a very wide vocabulary and proves nothing about it
working.

    python3 benchmarks/omr-lexicon-2026-09/reference_part_names.py --out part-names.json

Reads `.mxl` (zipped) and `.musicxml` with the stdlib only, the way
`tools/omr/training/musicxml_truth.py` does, so it runs anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root          # noqa: E402

TAGS = ("part-name", "part-abbreviation", "instrument-name",
        "part-name-display", "part-abbreviation-display")


def _xml_bytes(path: Path) -> bytes | None:
    if path.suffix.lower() != ".mxl":
        return path.read_bytes()
    try:
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if name.endswith((".xml", ".musicxml")) and not name.startswith("META-INF"):
                    return zf.read(name)
    except (zipfile.BadZipFile, KeyError, OSError):
        return None
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=None)
    args = ap.parse_args(argv)

    root = args.root or (library_root() / "reference")
    names: set[str] = set()
    files = failed = 0
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in (".mxl", ".musicxml", ".xml"):
            continue
        raw = _xml_bytes(path)
        if raw is None:
            failed += 1
            continue
        try:
            tree = ET.fromstring(raw)
        except ET.ParseError:
            failed += 1
            continue
        files += 1
        for tag in TAGS:
            for el in tree.iter(tag):
                text = "".join(el.itertext()).strip()
                if text:
                    names.add(text)

    args.out.write_text(json.dumps(sorted(names), indent=1, ensure_ascii=False))
    print(f"{len(names)} distinct names from {files} files ({failed} unreadable) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
