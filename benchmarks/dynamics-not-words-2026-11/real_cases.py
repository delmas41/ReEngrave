"""ROADMAP 2.296 step 4: controls from REAL judged cases -- case by case, which kind owns the ink Sean named.

    python3 benchmarks/dynamics-not-words-2026-11/real_cases.py --ht HT_DIR --brahms OFF_REC ON_REC --out FILE [--by-source]

Brahms p0: every confirmed page-pass label of kind `dynamic` (14: the `f` of each staff, read-only labels of `lane-2.287-page-labelling`) and every confirmed `word`
label, from Sean's own pass: the ink his label owns (`pageink.InkMap.claims`, the same helper 2.293's `sean_labels_compare.py` uses) is read off the ledger canvas of
the arm (a dynamic claim named a dynamic: `kind_patch`, unless --raw), and the kind holding most of it is printed per label, OFF and ON. A dynamic must end owned by
`dynamic`, a word by `word`; a label whose ink the ledger gives half to each prints SPLIT. The Litolff tiles Sean named are replayed by `judged_claims` (see the
FINDINGS), not here. Reads records; writes only --out.
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def load_handtruth(root):
    base = pathlib.Path(root) / "tools" / "omr" / "hand_truth"
    mods = {}
    for name in ("pagepass", "pageink"):
        spec = importlib.util.spec_from_file_location("tools.omr.hand_truth." + name, base / (name + ".py"))
        m = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = m
        spec.loader.exec_module(m)
        mods[name] = m
    return mods["pagepass"], mods["pageink"]


def per_label(rec, ht, patched, page=0):
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import cell_map as CM
    if patched:
        import kind_patch
        kind_patch.apply()
    PP, PI = load_handtruth(ht)
    pp = PP.load(pathlib.Path(ht) / "data" / "hand-truth" / "pages" / "imslp317803" / ("%d.pagepass.json" % page))
    labels = pp.truth()
    src = CR.resolve_source(rec)
    rows = CR.read_rows(src, [page])
    ed = CR.edition_info(rows)
    pdf = CR.LIB / ed["edition_path"]
    canvas, _v, _pws, cells = CR.build_page(rows, pdf, page, CM.ROOT_DEFAULT, ledger=True)
    canvas.tally()
    ink = canvas.ink
    lines = [(float(c.bbox_page_px[0]), float(c.bbox_page_px[2]), [c.bbox_page_px[1] + float(y) / c.upscale_factor for y in c.staff_line_ys_canonical])
             for c in cells if len(getattr(c, "staff_line_ys_canonical", None) or []) >= 5]
    im = PI.InkMap(ink, PI.measure_sp(lines), lines)
    cl = im.claims(labels)
    own = cl.owner
    fam, st = canvas.fam_eff, canvas.state
    out = []
    for i, l in enumerate(cl.labels):
        if l.kind not in ("dynamic", "word"):
            continue
        m = (own == i + 1) & ink
        n = int(m.sum())
        if n == 0:
            continue
        by = {}
        for k in CR.FINE_KINDS:
            bit = int(CR.FINE_BIT[k])
            px = int((m & ((fam & bit) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE)).sum())
            if px:
                by[k] = px
        weak = int((m & (st == CR.ST_WEAK)).sum())
        none = int((m & (st == CR.ST_NONE)).sum())
        want = l.kind
        bit = int(CR.FINE_BIT[want])
        exact = int((m & (fam == bit) & (st == CR.ST_ONE)).sum())                       # ONE owner, and it is Sean's kind
        present = int((m & ((fam & bit) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE)).sum())   # his kind stands on it (alone or beside another)
        top = max(by, key=by.get) if by else None
        if exact >= 0.5 * n:
            verdict = "RIGHT"
        elif present >= 0.5 * n:
            verdict = "SHARED (%s)" % "+".join(sorted(k for k in by if k != want)[:2])
        elif weak >= 0.5 * n:
            verdict = "WEAK ONLY"
        elif top:
            verdict = "WRONG KIND (%s)" % top
        else:
            verdict = "NOBODY"
        out.append(dict(id=getattr(l, "id", i), kind=l.kind, text=getattr(l, "text", None), ink_px=n, one_owner_his_kind_px=exact, present_px=present,
                        by_kind={k: v for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:4]}, weak_px=weak, none_px=none, verdict=verdict))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ht", required=True)
    ap.add_argument("--brahms", nargs=2, required=True, metavar=("OFF_REC", "ON_REC"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw", action="store_true", help="the tool as it stands (a dynamic claim is a `word`)")
    a = ap.parse_args()
    res = {}
    for arm, rec in zip(("off", "on"), a.brahms):
        res[arm] = per_label(rec, a.ht, not a.raw)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    print("%-5s %-8s %-18s %8s | %-22s | %-22s" % ("id", "kind", "text", "ink px", "OFF", "ON"))
    off, on = res["off"], res["on"]
    for o, n in zip(off, on):
        print("%-5s %-8s %-18s %8d | %-26s | %-26s" % (o["id"], o["kind"], str(o["text"])[:18], o["ink_px"], o["verdict"], n["verdict"]))
    for arm in ("off", "on"):
        for kind in ("dynamic", "word"):
            rows = [r for r in res[arm] if r["kind"] == kind]
            tot = sum(r["ink_px"] for r in rows)
            right = sum(r["one_owner_his_kind_px"] for r in rows)
            pres = sum(r["present_px"] for r in rows)
            print("%s %-8s labels %d, RIGHT on %d, ink %d, one owner = his kind %.1f%%, his kind stands there (alone or beside another) %.1f%%"
                  % (arm.upper(), kind, len(rows), sum(r["verdict"] == "RIGHT" for r in rows), tot, 100.0 * right / max(1, tot), 100.0 * pres / max(1, tot)))


main()
