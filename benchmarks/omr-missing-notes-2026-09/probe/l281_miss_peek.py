#!/usr/bin/env python3
"""l281_miss_peek: print the rows of one cell (and its staff) from a `l281_miss_rows.py` JSON -- the schema
look that precedes `l281_miss_images.py` (cell box, staff lines, frame of each row).

    python3 l281_miss_peek.py --rows rows.json --cell cell/0/0/0/3
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--cell", required=True)
    a = ap.parse_args()
    d = json.loads(Path(a.rows).read_text())
    staff = "staff/" + "/".join(a.cell.split("/")[1:4])
    system = "system/" + "/".join(a.cell.split("/")[1:3])
    for o in d["observations"]:
        if o["subject"] in (a.cell, staff, system) and o["quantity"] not in (
                "stem", "beam_stroke", "beam_stroke_ink", "stem_tip_ink", "stem_slash", "ledger_rung_ink",
                "beam_stem_join", "ink", "barline_column", "stem_run"):
            v = json.dumps(o["value"], default=str)
            print(o["subject"], o["quantity"], v[:200], o["frame"], json.dumps(o.get("detail"), default=str)[:160])


if __name__ == "__main__":
    main()
