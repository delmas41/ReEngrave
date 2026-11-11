"""ROADMAP 2.293 step 4: the page ledger's owners against SEAN'S OWN page-wide labels on Brahms p0 (Breitkopf), per kind.

    python3 benchmarks/one-ink-number-2026-11/sean_labels_compare.py --handtruth /path/to/checkout-of-lane-2.287-page-labelling [--slice DIR] [--page 0]

The 2.287 branch's `tools/omr/hand_truth/pagepass.py` + `pageink.py` (READ-ONLY, loaded from that checkout; never copied into tools/ and never imported by the
pipeline) compute the ink each of Sean's CONFIRMED labels owns (`InkMap.claims`: an arc takes its own thin curve, a barline its vertical run ...). This script
puts that ink beside `claim_readout`'s ledger canvas (`build_page(..., ledger=True)`) and prints, per Sean kind: of the ink his labels own, how much the ledger
gives the SAME kind / ANOTHER kind / only a weak claim / nobody; and, per ledger page-wide kind, how much of its ink Sean's labels do not cover.

A CAPTURE measure for nine page-wide kinds on ONE Breitkopf page. Not a standing test, not proof for cell-level kinds (noteheads, stems ...: Sean labelled none of
them in this pass, so the reverse table's "no Sean label" column holds every legitimate cell-level mark too).
"""
import argparse
import importlib.util
import json
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

#: Sean's page-pass kind -> the ledger's fine kind
SEAN_TO_LEDGER = {"staff": "staff_line", "barline": "barline", "bracket": "bracket", "clef": "clef", "key": "key", "meter": "meter", "word": "word",
                  "dynamic": "dynamic", "arc": "arc", "hairpin": "hairpin"}


def load_handtruth(root: pathlib.Path):
    base = root / "tools" / "omr" / "hand_truth"
    mods = {}
    for name in ("pagepass", "pageink"):                       # pageink imports pagepass by its package name
        spec = importlib.util.spec_from_file_location("tools.omr.hand_truth." + name, base / (name + ".py"))
        m = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = m
        spec.loader.exec_module(m)
        mods[name] = m
    return mods["pagepass"], mods["pageink"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handtruth", required=True, help="a checkout of lane-2.287-page-labelling (read-only)")
    ap.add_argument("--slice", default="/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/claim-readout-slices-2284b-r2-brahms.on.gathered")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    ht = pathlib.Path(a.handtruth)
    PP, PI = load_handtruth(ht)
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import cell_map as CM

    pp = PP.load(ht / "data" / "hand-truth" / "pages" / "imslp317803" / ("%d.pagepass.json" % a.page))
    labels = pp.truth()                                         # CONFIRMED only; pending pre-fills and rejected proposals are not truth
    src = CR.resolve_source(a.slice)
    rows = CR.read_rows(src, [a.page])
    ed = CR.edition_info(rows)
    pdf = CR.LIB / ed["edition_path"]
    canvas, ver, pws, cells = CR.build_page(rows, pdf, a.page, CM.ROOT_DEFAULT, ledger=True)
    t = canvas.tally()
    print("ledger canvas: %d dark px, %s" % (t["ink_px"], ver))
    ink = canvas.ink
    # the 2.287 helper reads cell attributes this tree does not have (`kind`, `rect`); the same five lines per cell, from this tree's own names
    lines = [(float(c.bbox_page_px[0]), float(c.bbox_page_px[2]), [c.bbox_page_px[1] + float(y) / c.upscale_factor for y in c.staff_line_ys_canonical])
             for c in cells if len(getattr(c, "staff_line_ys_canonical", None) or []) >= 5]
    sp = PI.measure_sp(lines)
    im = PI.InkMap(ink, sp, lines)
    cl = im.claims(labels)
    own = cl.owner
    kind_of = {i + 1: l.kind for i, l in enumerate(cl.labels)}
    n_by_kind = {}
    for l in cl.labels:
        n_by_kind[l.kind] = n_by_kind.get(l.kind, 0) + 1
    fam, st = canvas.fam_eff, canvas.state
    res = {"page": a.page, "sean_labels": n_by_kind, "sp": sp, "dark_px": int(ink.sum()), "sean_owned_px": int((own > 0).sum()),
           "forward": {}, "reverse": {}}

    # forward: the ink each Sean kind owns, and what the ledger says about it (same > other > weak > nobody)
    print("\nOf the ink Sean's confirmed labels own, what the ledger says (px):")
    print("  %-8s %5s %9s %8s %8s %8s %8s   %s" % ("kind", "boxes", "ink px", "SAME", "OTHER", "weak", "nobody", "other kinds (px)"))
    for k, lk in SEAN_TO_LEDGER.items():
        ids = [i for i, kk in kind_of.items() if kk == k]
        if not ids:
            continue
        m = np.isin(own, ids) & ink
        n = int(m.sum())
        bit = int(CR.FINE_BIT[lk])
        if lk == "staff_line":
            same = m & (st == CR.ST_STAFF)
        else:
            same = m & ((fam & bit) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE) & (st != CR.ST_STAFF)
        other = m & ~same & ((fam != 0) | (st == CR.ST_STAFF)) & (st != CR.ST_NONE) & (st != CR.ST_WEAK)
        weak = m & ~same & ~other & (st == CR.ST_WEAK)
        none = m & ~same & ~other & ~weak
        oth = {}
        vals, cnt = np.unique(np.where(st[other] == CR.ST_STAFF, int(CR.FINE_BIT["staff_line"]), fam[other]), return_counts=True)
        for v, c in zip(vals, cnt):
            oth["+".join(CR.mask_fine(int(v)))] = int(c)
        twice = int((same & np.isin(st, (CR.ST_TWIN, CR.ST_TWIN_VIEWS, CR.ST_TWO_OPEN, CR.ST_TWO_VIEWS))).sum())
        row = {"boxes": len(ids), "ink_px": n, "same": int(same.sum()), "same_of_which_claimed_twice": twice, "other": int(other.sum()), "weak": int(weak.sum()),
               "nobody": int(none.sum()), "other_kinds": dict(sorted(oth.items(), key=lambda kv: -kv[1])[:5])}
        res["forward"][k] = row
        print("  %-8s %5d %9d %7.1f%% %7.1f%% %7.1f%% %7.1f%%   %s" % (k, len(ids), n, 100.0 * row["same"] / max(1, n), 100.0 * row["other"] / max(1, n),
                                                                   100.0 * row["weak"] / max(1, n), 100.0 * row["nobody"] / max(1, n), row["other_kinds"]))
    # reverse: the ledger's ink of each page-wide kind, and whether Sean's labels cover it
    print("\nOf the ink the ledger gives each page-wide kind (any state), how much Sean's labels do not cover (px):")
    print("  %-10s %9s %9s %12s %12s" % ("kind", "ledger px", "Sean SAME", "Sean OTHER", "no Sean label"))
    for k, lk in SEAN_TO_LEDGER.items():
        bit = int(CR.FINE_BIT[lk])
        m = (((fam & bit) != 0) & (st != CR.ST_NONE) & (st != CR.ST_WEAK)) & ink
        if lk == "staff_line":
            m = (st == CR.ST_STAFF) & ink
        n = int(m.sum())
        if not n:
            continue
        ids = [i for i, kk in kind_of.items() if kk == k]
        same = m & np.isin(own, ids)
        oth = m & (own > 0) & ~np.isin(own, ids)
        nolab = m & (own == 0)
        row = {"ledger_px": n, "sean_same": int(same.sum()), "sean_other": int(oth.sum()), "no_sean_label": int(nolab.sum())}
        res["reverse"][k] = row
        print("  %-10s %9d %8.1f%% %11.1f%% %11.1f%%" % (k, n, 100.0 * row["sean_same"] / n, 100.0 * row["sean_other"] / n, 100.0 * row["no_sean_label"] / n))
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
