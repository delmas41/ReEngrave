"""ONE commit, ONE read pass, TWO label sets.

The question this exists for: two whole-work passes over the same Beethoven 5
PDF differ by 50 of 807 judgeable identity records, and the pass with STRICTLY
MORE margin labels (973 vs 962, 962/962 shared rows agreeing, zero
contradictions) is the WORSE one.  The two passes also differ in CODE, so the
committed artefacts cannot say whether the extra evidence or the code drift did
it.

This holds everything except the label evidence fixed:

    * one commit (whatever is checked out),
    * one cached read pass, so the STAVES are byte-identical between arms,
    * one flag configuration,
    * two label sets, the second the first minus a named list of rows.

`--drop` names (page_index, staff_index) rows to withhold from
`contextual._labels_for_page`.  Withholding is the honest operation: the
question is what the join does with evidence it does not have, and a pass that
never read a margin has no label object there at all.

Usage:
    run_labelsets.py PDF --cache DIR --out-dir DIR --tag NAME [--drop rows.json]
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np                                              # noqa: E402

from tools.omr import contextual as contextual_mod              # noqa: E402
from tools.omr.assist import Assist                             # noqa: E402
from tools.omr.contextual import apply_contextual_analysis      # noqa: E402
from tools.omr.slots import MIN_LABEL_CONFIDENCE                # noqa: E402

_EMPTY = np.zeros((1, 1), np.uint8)
_EMPTY3 = np.zeros((1, 1, 3), np.uint8)


def parse_pages(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        out += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--pages", default="0-87")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--drop", default=None,
                    help="JSON list of [page_index, staff_index] to withhold")
    ap.add_argument("--keep-only", default=None,
                    help="JSON list of [page_index, staff_index]; every OTHER "
                         "row of the drop list is withheld (single-row arms)")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    pages = parse_pages(args.pages)
    cache = Path(args.cache)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    drop = set()
    if args.drop:
        drop = {tuple(x) for x in json.loads(Path(args.drop).read_text())}
    if args.keep_only:
        keep = {tuple(x) for x in json.loads(Path(args.keep_only).read_text())}
        drop = drop - keep
    print(f"tag={args.tag} pages={len(pages)} drop={len(drop)} rows", flush=True)

    # -- the read pass, from cache only.  A cache miss is a REFUSAL: an arm that
    # silently re-read a page would put Surya nondeterminism back into a
    # comparison whose entire content is a handful of names.
    staved, labels_by_page = [], {}
    withheld = []
    for i in pages:
        blob = cache / f"p{i:04d}.pkl"
        if not blob.exists():
            print(f"REFUSING: cache miss for page {i} ({blob})")
            return 1
        pws, labels = pickle.loads(blob.read_bytes())
        pws.page.rgb, pws.page.binary = _EMPTY3, _EMPTY
        for st in pws.staves:
            st.slot_index = -1
        kept = []
        for lab in labels:
            if (i, lab.staff_index) in drop:
                withheld.append([i, lab.staff_index,
                                 lab.instrument.name if lab.instrument else None,
                                 lab.alias, lab.confidence, bool(lab.matched)])
                continue
            kept.append(lab)
        staved.append(pws)
        labels_by_page[i] = kept

    n_conf = sum(1 for ls in labels_by_page.values() for l in ls
                 if l.matched and l.confidence in MIN_LABEL_CONFIDENCE)
    print(f"read pass: {len(staved)} pages from cache, "
          f"{n_conf} admissible labels, {len(withheld)} withheld", flush=True)
    for w in withheld:
        print(f"  withheld p{w[0]} s{w[1]}: {w[2]} (alias={w[3]!r} "
              f"conf={w[4]} matched={w[5]})")

    def patched(pws, pdf_path, page_index, **kw):
        if page_index in labels_by_page:
            return labels_by_page[page_index]
        raise RuntimeError(f"uncached page requested: {page_index}")

    contextual_mod._labels_for_page = patched

    os.environ["OMR_ABSENT_INSTRUMENT_VETO"] = "report"
    os.environ.setdefault("OMR_MOVEMENT_REFERENCE", "1")

    result = {"source_pdf": str(pdf), "dpi": args.dpi,
              "pages": [{"page_index": i, "systems": []} for i in pages]}
    t0 = time.time()
    summary = apply_contextual_analysis(
        result, pdf_path=pdf, dpi=args.dpi, apply_clefs=False,
        assist=Assist("none"), staved=staved)
    print(f"contextual in {time.time() - t0:.0f}s "
          f"available={summary.get('available')} reason={summary.get('reason')} "
          f"reference={len(summary.get('reference') or [])} slots", flush=True)

    dst = out_dir / f"{args.tag}.json"
    json.dump({
        "source": "run_labelsets.py",
        "source_pdf": str(pdf),
        "tag": args.tag,
        "pages": pages,
        "dpi": args.dpi,
        "cache": str(cache),
        "dropped": sorted(drop),
        "withheld": withheld,
        "admissible_labels": n_conf,
        "contextual": {k: summary.get(k) for k in (
            "reference", "roster", "absent_instrument_veto",
            "instruments_from_score_order", "instruments_from_roster",
            "ambiguous_labels_resolved", "labelled_staves",
            "unresolved_labels")},
    }, open(dst, "w"), sort_keys=True)
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
