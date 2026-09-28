"""ROADMAP 2.7b — cut the MEASURED geometry of Sean's adjudicated heads out of
a record, as the fixture `tools/omr/tests/test_staged_nearer_staff.py` reads.

For every head of the 2.7 adjudication: its glyph box (canonical + page), the
page-frame lines and spacing of EVERY staff of its system, and every
`ledgerLine` box of its cell with its standing `ledger_is_not_a_ledger`
verdict, plus the `Q.GLYPH_BAND_DISTANCE` rows GATHER filed for it. Nothing
is decided here.

    python3 benchmarks/omr-accidental-2026-09/probe/extract_nearer_fixture.py \\
        <record.json> tools/omr/tests/fixtures/nearer_staff_litolff_p3.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))

from tools.omr.staged.record_io import load_record  # noqa: E402
from nearer_staff import named_heads, standing  # noqa: E402


def main() -> int:
    rec = load_record(sys.argv[1])["record"]
    V = standing(rec["verdicts"])
    neg, pos, other = named_heads()
    wanted = {**{h: ("wrong_staff", c) for h, c in neg.items()},
              **{h: ("confirmed", c) for h, c in pos.items()},
              **{h: ("not_a_head", c) for h, c in other.items()}}
    cells = {"cell/" + "/".join(h.split("/")[1:5]) for h in wanted}
    systems = {tuple(h.split("/")[1:3]) for h in wanted}
    staff = {}
    cellgeo = {}
    glyphs = {}
    bands = {}
    for o in rec["observations"]:
        q, sub = o["quantity"], o["subject"]
        if q in ("staff_lines", "staff_spacing") and \
                tuple(sub.split("/")[1:3]) in systems:
            staff.setdefault(sub, {})[q] = o["value"]
        elif q in ("cell_staff_space", "cell_box") and sub in cells:
            cellgeo.setdefault(sub, {})[q] = [o["value"], o.get("detail")]
        elif q == "glyph_box":
            cell = "cell/" + "/".join(sub.split("/")[1:5])
            if cell in cells and (sub in wanted or
                                  o["value"][0] == "ledgerLine"):
                glyphs[sub] = {"value": o["value"],
                               "bbox_page_px": (o.get("detail") or {})
                               .get("bbox_page_px"),
                               "category": (o.get("detail") or {})
                               .get("category")}
        elif q == "glyph_band_distance" and sub in wanted:
            bands.setdefault(sub, []).append(
                [o["value"], (o.get("detail") or {}).get("candidate")])
    heads = []
    for h, (kind, crops) in sorted(wanted.items()):
        cell = "cell/" + "/".join(h.split("/")[1:5])
        ledgers = []
        for g, v in sorted(glyphs.items()):
            if v["value"][0] != "ledgerLine" or \
                    "cell/" + "/".join(g.split("/")[1:5]) != cell:
                continue
            lv = V.get((g, "ledger_is_not_a_ledger"))
            ledgers.append({"subject": g, **v,
                            "refused": bool(lv and lv["outcome"] == "decided"
                                            and lv["value"] is True),
                            "reason": lv and lv.get("reason")})
        npv = V.get((h, "notehead_is_not_a_notehead"))
        heads.append({"subject": h, "sean": kind, "crops": crops,
                      **glyphs[h], "ledgers": ledgers,
                      "band_rows": bands.get(h, []),
                      "npv_on_base": npv and [npv["outcome"], npv["value"],
                                              npv["reason"]]})
    out = {"_readme": __doc__.split("\n\n")[0],
           "record": sys.argv[1].rsplit("/", 1)[-1],
           "staves": {k: v for k, v in sorted(staff.items())},
           "cells": {k: v for k, v in sorted(cellgeo.items())},
           "heads": heads}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
    print(len(heads), "heads,", len(staff), "staves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
