"""l283_dataset: Sean's page-0 stems, labelled from HIS boxes (l281_truth's derivation), joined to the cached CV stems
(l283_cells.py) so a tip reader can be scored on the REAL erased cell raster. ROADMAP 2.83 probe, no product code.

A row = one truth stem at its TIP end (the end farther from its head), with the label from his boxes:
  flag   a `flag*` box of his hangs off that stem and no beam box reaches it
  beam   a beam box of his reaches its tip
  bare   neither (levels 0), a head whose stem he boxed
  trem   a tremolo slash is on it (excluded from every count: Sean 2026-10-09, a slash is neither flag nor beam)
and `cv`: the matched CV stem (cell key, index, the cell, the stem box in canonical px) or None where the CV rung found
no stem Sean boxed (reported, never scored).

CONVENTION: the same as l281_truth's (rule 3, stated there). The label is Sean's; the CV match is by box overlap.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_truth import Truth, hbase  # noqa: E402
from l283_common import cv_stems_page, load_cells, match_truth_stems  # noqa: E402


def build(cells_path):
    T = Truth()
    cells = load_cells(cells_path)
    matched = match_truth_stems(T, cv_stems_page(cells))
    by_stem = {}
    for h in T.heads:
        d = T.derive(h)
        if d.get("status") != "ok" or hbase(h.cls) != 1.0:
            continue          # black heads only: the population the quarter rule and the flag reader both name
        sid = d["stem"]
        row = by_stem.setdefault(sid, {"stem": sid, "tip_end": d["tip_end"], "stem_rect": d["stem_rect"],
                                       "levels_beam": d["levels_beam"], "levels_flag": d["levels_flag"],
                                       "tremolo": d["tremolo"], "heads": [], "flag_ids": d["flag_ids"],
                                       "full_cell": d["full_cell"]})
        row["heads"].append(h.id)
    rows = []
    for sid, r in by_stem.items():
        if r["tremolo"]:
            r["label"] = "trem"
        elif r["levels_beam"] > 0:
            r["label"] = "beam"
        elif r["levels_flag"] > 0:
            r["label"] = "flag"
        else:
            r["label"] = "bare"
        m = matched.get(sid)
        r["cv"] = None
        if m:
            frac, key, i, c, rect = m
            r["cv"] = {"key": key, "i": i, "cell": c, "stem": c["stems"][i], "frac": frac}
        rows.append(r)
    return T, cells, rows


if __name__ == "__main__":
    T, cells, rows = build(sys.argv[1])
    c = collections.Counter((r["label"], r["cv"] is not None) for r in rows)
    for k in sorted(c):
        print(k, c[k])
