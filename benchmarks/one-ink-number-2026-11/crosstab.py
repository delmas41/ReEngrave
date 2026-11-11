"""ROADMAP 2.293 step 1, the pixel-level half of the reconciliation: which dark pixels move between the OLD readout's buckets (2.236 `PageInk`) and the NEW four lines
(`LedgerInk`), on ONE page, from the same slice, in one process.

    python3 benchmarks/one-ink-number-2026-11/crosstab.py SLICE PAGE [--out FILE.json]

Rows = the old state of a pixel, columns = the new line. Every number is dark pixels; each row and column sums to the page's dark pixels.
"""
import argparse
import collections
import json
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slice")
    ap.add_argument("page", type=int)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import claim_readout as CR
    src = CR.resolve_source(a.slice)
    rows = CR.read_rows(src, [a.page])
    pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
    old, *_ = CR.build_page(rows, pdf, a.page, CM.ROOT_DEFAULT)
    new, *_ = CR.build_page(rows, pdf, a.page, CM.ROOT_DEFAULT, ledger=True)
    assert (old.ink == new.ink).all()
    ink = new.ink
    old_name = np.array(old.cat_names, dtype=object)[old.cat[ink]]
    # the old buckets, grouped the way the old print grouped them
    def og(n):
        if n.startswith("contested"):
            return n
        if n.startswith(("unclaimed", "refused", "residue")):
            return "unclaimed/refused/residue"
        return n
    new_line = np.empty(ink.sum(), dtype=object)
    st = new.state[ink]
    names = {CR.ST_ONE: "ONE", CR.ST_STAFF: "ONE (staff line)", CR.ST_WEAK: "WEAK", CR.ST_NONE: "NONE", CR.ST_TWIN: "TWICE", CR.ST_TWIN_VIEWS: "TWICE",
             CR.ST_TWO_OPEN: "TWICE", CR.ST_TWO_VIEWS: "TWICE"}
    for code, nm in names.items():
        new_line[st == code] = nm
    tab = collections.defaultdict(collections.Counter)
    og_v = np.array([og(n) for n in old_name], dtype=object)
    for o in sorted(set(og_v)):
        sel = og_v == o
        vals, cnt = np.unique(new_line[sel].astype(str), return_counts=True)
        for v, c in zip(vals, cnt):
            tab[o][v] += int(c)
    cols = ["ONE", "ONE (staff line)", "WEAK", "TWICE", "NONE"]
    tot = int(ink.sum())
    print("old bucket \\ new line (dark px; %% of the page's %d)" % tot)
    print("  %-30s" % "" + "".join("%18s" % c for c in cols) + "%12s" % "row")
    for o in sorted(tab, key=lambda k: -sum(tab[k].values())):
        r = sum(tab[o].values())
        print("  %-30s" % o + "".join("%11d %5.1f%%" % (tab[o][c], 100.0 * tab[o][c] / tot) if tab[o][c] else "%18s" % "." for c in cols) + "%11.1f%%" % (100.0 * r / tot))
    colsum = {c: sum(tab[o][c] for o in tab) for c in cols}
    print("  %-30s" % "column" + "".join("%11d %5.1f%%" % (colsum[c], 100.0 * colsum[c] / tot) for c in cols))
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps({o: dict(v) for o, v in tab.items()}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
