"""The 2x2: movement spans x absent-instrument veto, over one read pass.

Two fixes for the same bug landed on two branches and neither was measured
beside the other.

    `OMR_MOVEMENT_REFERENCE`      (branch A) a page belongs to its MOVEMENT's
                                  lineup, not the volume's. Changes which SLOT
                                  each staff is aligned to.
    `OMR_ABSENT_INSTRUMENT_VETO`  (branch B) a staff may not be named an
                                  instrument no page near it prints. Changes
                                  which slot names are ALLOWED TO BE ASSERTED.

They act on different halves of the same join, so they compose at the data
level and the 2x2 is the measurement neither branch could take alone.

## Why one read pass, and why that is a control rather than a shortcut

`apply_contextual_analysis` spends essentially all of its wall clock on phase 1
(render + `detect_staves`) and the margin readers, and NEITHER depends on either
flag: both flags act downstream of `staff_labels_per_page`. So the read is done
once, cached per page, and served to all four arms through a patched
`_labels_for_page`. Any difference between arms is then the flags and nothing
else -- which also removes the Surya nondeterminism this repo has recorded
(`docs`/CLAUDE.md: temperature nondeterminism in the margin reader) from a
comparison whose whole content is a difference of a few dozen names.

## Why TWO runs give FOUR arms

`OMR_ABSENT_INSTRUMENT_VETO=report` computes the veto list and applies nothing
(see `absent_instrument.py`), and the vetoed set is not an input to slot
assignment or to `instrument_by_slot` -- it is read only when the staff dicts
are written and when clefs are corrected. So one `report` run per spans setting
carries BOTH veto arms: veto-off is the names as assigned, veto-on is those
names minus the vetoed keys. `score_2x2.py` derives the four cells from the two
recorded blobs, and `--verify-apply` re-runs one cell in `apply` mode to check
that derivation against the real thing rather than trusting it.

Usage:
    compose.py PDF --out-dir DIR [--pages 0-87] [--dpi 600] [--cache DIR]
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
from tools.omr.preprocessing import render_page                 # noqa: E402
from tools.omr.staff_detector import detect_staves              # noqa: E402

_EMPTY = np.zeros((1, 1), np.uint8)
_EMPTY3 = np.zeros((1, 1, 3), np.uint8)

#: (tag, OMR_MOVEMENT_REFERENCE, veto arm). The veto arm is derived offline
#: from a `report` run, so both rows here are one process each.
SPAN_ARMS = [("spans-off", "0"), ("spans-on", "1")]


def parse_pages(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        out += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    return sorted(set(out))


class PageCache:
    """Staves + margin labels per page, on disk, shared by every arm.

    Also serves pages the ROSTER opens that the run did not ask for:
    `acquire_roster` reads outside the run through the same
    `_labels_for_page`, so an uncached page is read for real and then cached,
    and the second arm gets the first arm's answer.
    """

    def __init__(self, root: Path, pdf: Path, dpi: int):
        self.root = root
        self.pdf = pdf
        self.dpi = dpi
        self.root.mkdir(parents=True, exist_ok=True)
        self.labels: dict[int, list] = {}
        self.reads = 0
        self.hits = 0

    def _blob(self, page_index: int) -> Path:
        return self.root / f"p{page_index:04d}.pkl"

    def read(self, page_index: int, real_reader):
        """`(pws, labels)` for a page, reading only if it is not cached."""
        blob = self._blob(page_index)
        if blob.exists():
            pws, labels = pickle.loads(blob.read_bytes())
            self.hits += 1
            self.labels[page_index] = labels
            return pws, labels
        pws = detect_staves(render_page(self.pdf, page_index, dpi=self.dpi))
        labels = real_reader(pws, page_index)
        # ⚠️ Drop the rasters once the margin is read. A 600 dpi page holds
        # ~130 MB of rgb + binary; 88 of those alongside llama.cpp is what the
        # sibling branch's replay stalled under. Nothing downstream of
        # `_labels_for_page` in `apply_contextual_analysis` touches an image
        # (verified: `render_page` appears there exactly once, to BUILD
        # `staved`), so this cannot change an answer.
        pws.page.rgb = _EMPTY3
        pws.page.binary = _EMPTY
        blob.write_bytes(pickle.dumps((pws, labels)))
        self.reads += 1
        self.labels[page_index] = labels
        return pws, labels


def install(cache: PageCache):
    """Serve `contextual._labels_for_page` from the cache.

    The real reader stays reachable, so a page nobody has read yet -- a roster
    page outside the run -- is read once and cached like any other.
    """
    real = contextual_mod._labels_for_page

    def patched(pws, pdf_path, page_index, **kw):
        if page_index in cache.labels:
            return cache.labels[page_index]
        blob = cache._blob(page_index)
        if blob.exists():
            _pws, labels = pickle.loads(blob.read_bytes())
            cache.labels[page_index] = labels
            cache.hits += 1
            return labels
        labels = real(pws, pdf_path, page_index, **kw)
        cache.labels[page_index] = labels
        return labels

    contextual_mod._labels_for_page = patched
    return real


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pages", default="0-87")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--veto", default="report",
                    help="OMR_ABSENT_INSTRUMENT_VETO for every arm "
                         "(`report` gives both veto cells offline)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    pages = parse_pages(args.pages)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = PageCache(Path(args.cache) if args.cache
                      else out_dir / "cache", pdf, args.dpi)

    print(f"pdf={pdf.name} pages={len(pages)} dpi={args.dpi} "
          f"veto={args.veto} cache={cache.root}", flush=True)

    real_reader_holder = {}

    def real_reader(pws, page_index):
        return real_reader_holder["fn"](
            pws, pdf, page_index, assist=Assist("none"), budget=[0],
            tiers=[0, 0, 0, 0, 0])

    real_reader_holder["fn"] = install(cache)

    # ── One read pass ───────────────────────────────────────────────────────
    t0 = time.time()
    staved = []
    for i in pages:
        pws, labels = cache.read(i, real_reader)
        staved.append(pws)
        print(f"  page {i}: {len(pws.staves)} staves, "
              f"{sum(1 for l in labels if l.matched)} labels", file=sys.stderr,
              flush=True)
    print(f"read {len(pages)} pages in {time.time() - t0:.0f}s "
          f"({cache.reads} read, {cache.hits} cached)", flush=True)

    os.environ["OMR_ABSENT_INSTRUMENT_VETO"] = args.veto
    written = []
    for tag, mvt in SPAN_ARMS:
        os.environ["OMR_MOVEMENT_REFERENCE"] = mvt
        # `assign_slots` writes `slot_index` onto the staves it is given, and
        # the arms share those objects. Reset, or arm 2 starts from arm 1.
        for pws in staved:
            for st in pws.staves:
                st.slot_index = -1
        result = {"source_pdf": str(pdf), "dpi": args.dpi,
                  "pages": [{"page_index": i, "systems": []} for i in pages]}
        t1 = time.time()
        summary = apply_contextual_analysis(
            result, pdf_path=pdf, dpi=args.dpi, apply_clefs=False,
            assist=Assist("none"), staved=staved)
        blob = summary.get("absent_instrument_veto")
        print(f"[{tag}] available={summary.get('available')} "
              f"reason={summary.get('reason')} in {time.time() - t1:.0f}s "
              f"reference={len(summary.get('reference') or [])} slots "
              f"vetoes={len(blob['vetoes']) if blob else 'NONE'}", flush=True)
        if not blob:
            print(f"REFUSING [{tag}]: no veto report block — "
                  f"OMR_ABSENT_INSTRUMENT_VETO={args.veto}")
            return 1
        name = f"{args.tag + '-' if args.tag else ''}{tag}.json"
        dst = out_dir / name
        json.dump({
            "source": "compose.py",
            "source_pdf": str(pdf),
            "pages": pages,
            "dpi": args.dpi,
            "movement_reference": mvt,
            "veto_mode": args.veto,
            "contextual": {k: summary.get(k) for k in (
                "reference", "roster", "absent_instrument_veto",
                "instruments_from_score_order", "instruments_from_roster",
                "ambiguous_labels_resolved", "labelled_staves",
                "unresolved_labels")},
        }, open(dst, "w"), sort_keys=True)
        written.append(str(dst))
        print(f"  wrote {dst}", flush=True)

    print("INPUT ASSERTION: both arms ran off ONE read pass "
          f"({cache.reads} pages read, {cache.hits} cache hits), so every "
          "difference below is OMR_MOVEMENT_REFERENCE and nothing else")
    for w in written:
        print(f"  {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
