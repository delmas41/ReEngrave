"""Print the contradiction rows of named artefacts, grouped by kind."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCAN = ROOT / "benchmarks/omr-label-contradiction-2026-09/out/scan.json"


def main(argv: list[str]) -> None:
    rows = {r["artefact"]: r for r in json.loads(SCAN.read_text())}
    wanted = argv or list(rows)
    for name in wanted:
        matches = [k for k in rows if name in k]
        for k in matches:
            r = rows[k]
            print(f"== {k}  {r['contradictions']}/{r['labelled_records']}")
            c = Counter((x["source"], x["read"], x["exported"])
                        for x in r["rows"])
            for (src, read, exp), n in c.most_common():
                print(f"   {src:24} {read:16} -> {exp:16} x{n}")
            pages = Counter(x["page_index"] for x in r["rows"])
            print("   pages:", dict(sorted(pages.items())))


if __name__ == "__main__":
    main(sys.argv[1:])
