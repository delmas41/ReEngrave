"""What does the PIPELINE read in the margin, and what does the rule make of it?

`run_arms.py`'s `label_ideal` arm feeds `players_for_label` the hand-read strings
in `works.json`, which prices the RULE with a perfect reader. This runs the
reader the pipeline actually uses (Surya, through `contextual`'s own free tier)
on the same pages, so the two can be told apart: a rule error and an OCR error
want opposite responses.

    python3 benchmarks/omr-condensed-parts-2026-09/probe_real_labels.py \
        --rows beethoven-sym5-mvt1-984073-p1 dvorak-sym9-mvt1-405834-p5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.condensed_parts import players_for_label  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_labels_surya import read_staff_labels_surya  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", default=str(
        ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"))
    ap.add_argument("--rows", nargs="*", default=None)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    works = json.loads(Path(args.works).read_text())
    rows = {r["row_id"]: r for r in works["rows"]}
    lib = library_root()
    wanted = args.rows or list(rows)
    out = []

    for rid in wanted:
        row = rows.get(rid)
        if row is None:
            print(f"!! unknown row {rid}")
            continue
        pdf = lib / row["edition"]["catalog_path"]
        page_index = row["page"]["pdf_page_index"]
        pws = detect_staves(render_page(pdf, page_index, dpi=args.dpi))
        labels = read_staff_labels_surya(pws)
        by_staff = {lab.staff_index: lab.text for lab in labels}
        print(f"\n### {rid}  ({len(pws.staves)} staves detected, "
              f"{len(labels)} labels read)")
        rec = []
        for staff in sorted(pws.staves, key=lambda s: s.top_y):
            text = (by_staff.get(staff.staff_index) or "").strip()
            n = players_for_label(text)
            print(f"   staff {staff.staff_index:2d}  {text[:34]:34s} -> {n}")
            rec.append({"staff": staff.staff_index, "text": text, "players": n})
        out.append({"row": rid, "staves": rec})

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
