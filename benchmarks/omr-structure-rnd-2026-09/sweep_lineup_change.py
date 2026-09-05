"""Wide sweep of the library for pages whose printed lineup CHANGES between systems.

Runs OMR **phase 1 only** -- render, binarize, deskew, detect staves, group
systems.  No YOLO, no header reading, ~0.9 s per page at 300 dpi.  That buys
screen 1 (staff counts) and screen 3 (bracket-block shape) and NOT screen 2
(clef sequences), which needs the detector.

Screen 2 is left out of the wide sweep **because it failed the pre-registered
validation** -- see `LINEUP_CHANGE_CENSUS.md`.  It fired on 4 of the 5 negative
controls, every one of them with `clef_source == "detector"` on both sides, so
its firings cannot be separated from clef noise and a wide screen-2 queue would
be a queue of misreads.

⚠️ NO GROUND TRUTH IS AN INPUT.  Only `data/score-library/catalog.json` (parsed
with `json`) and the PDFs it points at.

Writes one JSON object per page to a JSONL file as it goes, so a long run that
dies still leaves everything it measured.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

from probe_lineup_change import (  # noqa: E402
    DOUBTFUL_NARROW_SYSTEM,
    DOUBTFUL_WIDE_SYSTEM,
    _blocks_shape,
)

# A page whose widest system is narrower than this is not a conductor's page --
# a piano score, a part, or front matter.  Recorded and excluded from the rate,
# never silently dropped.
ORCHESTRAL_MIN_STAVES = 6


def screen_phase1(staves) -> dict[str, Any]:
    """Screens 1 and 3 from phase-1 output alone."""
    systems: dict[int, list] = {}
    for s in staves:
        systems.setdefault(s.system_index, []).append(s)
    order = sorted(systems)
    counts = [len(systems[k]) for k in order]
    shapes = [_blocks_shape([st.group_index for st in systems[k]]) for k in order]

    rec: dict[str, Any] = {
        "n_systems": len(order),
        "staff_counts": counts,
        "block_shapes": [list(sh) if sh else None for sh in shapes],
        "screens": [],
        "abstain": None,
        "doubtful": False,
        "doubtful_reason": None,
    }
    if not counts:
        rec["abstain"] = "no staves detected -- blank page or phase-1 failure"
        rec["tier"] = "abstain"
        return rec
    if max(counts) < ORCHESTRAL_MIN_STAVES:
        rec["abstain"] = (
            f"widest system is {max(counts)} staves -- not a conductor's page"
        )
        rec["tier"] = "abstain"
        return rec
    if len(order) < 2:
        rec["abstain"] = "fewer than two systems -- nothing to compare"
        rec["tier"] = "abstain"
        return rec

    if max(counts) >= DOUBTFUL_WIDE_SYSTEM and min(counts) <= DOUBTFUL_NARROW_SYSTEM:
        rec["doubtful"] = True
        rec["doubtful_reason"] = (
            f"a system of {min(counts)} staves beside one of {max(counts)} -- "
            "phase 1 probably failed on this page"
        )

    if len(set(counts)) > 1:
        rec["screens"].append("counts")
    if all(sh is not None for sh in shapes) and len(set(shapes)) > 1:
        rec["screens"].append("blocks")

    if rec["doubtful"]:
        rec["tier"] = "doubtful"
    elif "counts" in rec["screens"]:
        rec["tier"] = "A"
    elif "blocks" in rec["screens"]:
        rec["tier"] = "D"
    else:
        rec["tier"] = "none"
    return rec


def page_plan(n_pages: int, per_edition: int) -> list[int]:
    """Evenly spaced 0-based page indices, skipping page 0 (title / front matter)."""
    if n_pages <= 1:
        return []
    body = list(range(1, n_pages))
    if len(body) <= per_edition:
        return body
    step = len(body) / per_edition
    return sorted({body[int(i * step)] for i in range(per_edition)})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default="data/score-library/catalog.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-edition", type=int, default=20)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--time-budget-s", type=float, default=6000.0)
    ap.add_argument("--only", nargs="*", default=None,
                    help="substring filter on the edition path (for the DPI control)")
    ap.add_argument("--pages", nargs="*", type=int, default=None,
                    help="explicit 0-based page indices (overrides --per-edition)")
    ap.add_argument("--shard", default=None,
                    help="i/n -- take every n'th edition starting at i, so several "
                         "workers can share the CPU over disjoint editions")
    args = ap.parse_args(argv)

    catalog = json.loads(Path(args.catalog).read_text())
    entries = catalog["entries"]
    assert entries, "catalog.json has no entries"
    editions = [e for e in entries if e.get("kind") == "edition"]
    assert editions, "catalog.json holds no editions"

    root = library_root()
    present = [e for e in editions if (root / e["path"]).exists()]
    assert present, f"no edition PDFs found under {root} -- nothing to sweep"
    if args.only:
        present = [e for e in present
                   if any(tok in e["path"] for tok in args.only)]
        assert present, f"--only {args.only} matched no edition"

    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        assert 0 <= i < n, f"bad shard {args.shard}"
        present = present[i::n]
        assert present, f"shard {args.shard} is empty"

    print(f"catalog: {len(editions)} editions, {len(present)} present under {root}"
          + (f" (shard {args.shard})" if args.shard else ""), flush=True)

    done: set[tuple[str, int]] = set()
    out = Path(args.out)
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["path"], r["page_index"]))
        print(f"resuming: {len(done)} pages already measured", flush=True)

    started = time.time()
    n_pages = n_fail = 0
    fh = out.open("a")
    try:
        for ei, e in enumerate(present):
            pdf = root / e["path"]
            plan = args.pages if args.pages is not None else page_plan(
                int(e.get("pages") or 0), args.per_edition)
            for pi in plan:
                if (e["path"], pi) in done:
                    continue
                if time.time() - started > args.time_budget_s:
                    print("time budget reached -- stopping cleanly", flush=True)
                    return _finish(fh, n_pages, n_fail)
                rec: dict[str, Any] = {
                    "path": e["path"],
                    "page_index": pi,
                    "work_id": e.get("work_id"),
                    "composer": e.get("composer"),
                    "title": e.get("title"),
                    "publisher": e.get("publisher"),
                    "variant": e.get("variant"),
                    "imslp_id": e.get("imslp_id"),
                    "image_type": e.get("image_type"),
                    "dpi": args.dpi,
                }
                try:
                    page = render_page(pdf, pi, dpi=args.dpi)
                    pws = detect_staves(page)
                    rec.update(screen_phase1(pws.staves))
                    rec["n_staves_detected"] = len(pws.staves)
                except Exception as exc:  # noqa: BLE001
                    n_fail += 1
                    rec.update({
                        "tier": "error",
                        "abstain": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc()[-800:],
                    })
                fh.write(json.dumps(rec) + "\n")
                n_pages += 1
                if n_pages % 100 == 0:
                    fh.flush()
                    el = time.time() - started
                    print(f"  {n_pages} pages, {n_fail} errors, {el:.0f}s "
                          f"({el / max(n_pages, 1):.2f} s/page), edition "
                          f"{ei + 1}/{len(present)}", flush=True)
    finally:
        if not fh.closed:
            fh.flush()
            fh.close()
    return _finish(fh, n_pages, n_fail)


def _finish(fh, n_pages: int, n_fail: int) -> int:
    if fh is not None and not fh.closed:
        fh.flush()
        fh.close()
    assert n_pages > 0, "the sweep rendered ZERO pages -- refusing to report a census"
    print(f"done: {n_pages} pages measured, {n_fail} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
