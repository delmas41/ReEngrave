"""Build the three EMPTY counting sheets for Sean's own cleanup count
(ROADMAP.md 1.4), one per acceptance document, matching the column layout of
the one proxy count already taken (`counts/beethoven5-litolff-p3-2026-09-23.csv`,
CLAUDE.md Sec.6a).

    python3 benchmarks/omr-cleanup-count-2026-09/build_empty_sheets.py

Pre-fills ONLY: page, system, staff position top-to-bottom, part name (our
file's own name for that staff), and the printed bar range for that system.
Every other column — including all four category columns — is left BLANK.
The machine proposes nothing here (contrast the earlier `export_arm.py` +
`build_sheet.py` pipeline, which filled `proposed_*` columns from the
record): this count is Sean's, start to finish, and pre-filling anything he
would judge would fit the count to what the machine already believes.

Reuses the same DOCS table `build_count_sidebyside.py` uses for the HTML, so
the two artefacts can never disagree about which systems/bars/parts this
count covers.
"""
from __future__ import annotations

import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from build_count_sidebyside import DOCS, part_list, TODAY  # noqa: E402

COUNTS_DIR = HERE / "counts"

COLUMNS = [
    "page", "system", "staff_slot_top_to_bottom", "part_name",
    "bars_PRINTED_on_this_system", "measures_in_file",
    "proposed_missing_bars_nothing_read", "ref_bars_sounding",
    "our_bars_sounding", "missing", "wrong", "spurious", "would_not_notice",
    "scope", "missable", "notes",
]


def build_sheet(doc: dict) -> Path:
    xml_text = doc["xml"].read_text()
    parts = part_list(xml_text)  # [(id, name), ...] in score order

    out_path = COUNTS_DIR / f"{doc['id']}-{doc['page_tag']}-SEAN-{TODAY}.csv"
    with out_path.open("w", newline="") as f:
        f.write(f"# counter=Sean date={TODAY} document={doc['id']} "
                f"page_tag={doc['page_tag']} pdf_page_index={doc['pdf_page_index']} "
                f"-- see counts/HOW-TO-COUNT.md before filling this in\n")
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for sysdef in doc["systems"]:
            sysi = sysdef["system"]
            lo, hi = sysdef["first_bar"], sysdef["last_bar"]
            bar_range = f"{lo}-{hi}"
            for slot, (_pid, name) in enumerate(parts):
                w.writerow([
                    doc["pdf_page_index"], sysi, slot, name, bar_range,
                    "", "", "", "",   # measures_in_file .. our_bars_sounding
                    "", "", "", "",   # missing, wrong, spurious, would_not_notice
                    "", "", "",       # scope, missable, notes
                ])
    return out_path


def main() -> int:
    COUNTS_DIR.mkdir(parents=True, exist_ok=True)
    for doc in DOCS:
        out_path = build_sheet(doc)
        print(f"wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
