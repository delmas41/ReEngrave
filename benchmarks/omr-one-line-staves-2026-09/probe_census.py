"""Census: what actually appears in `pws.staves` with fewer than five lines?

`measure_extractor` drops every such staff at three sites. Before touching that
filter, ask what it is dropping. `_group_into_staves` only ever accepts
five-peak windows, so a sub-five staff is always exactly one line and always
came from `staff_detector._single_line_staff_rows`.

Runs phase 1 (render -> detect_staves) over a page sample of the score library
and records every one-line staff with the geometry needed to adjudicate it by
hand, plus enough to cut a crop so a human can look at the ink.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page                    # noqa: E402
from tools.omr.staff_detector import detect_staves                 # noqa: E402
from tools.library.score_library import library_root               # noqa: E402

OUT = Path(__file__).parent


def edition_paths() -> list[dict]:
    cat = json.loads((ROOT / "data/score-library/catalog.json").read_text())
    return [e for e in cat["entries"] if e.get("kind") == "edition"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-edition", type=int, default=2)
    ap.add_argument("--editions", type=int, default=0, help="0 = all")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--seed", type=int, default=20260906)
    ap.add_argument("--out", default="census.json")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    eds = edition_paths()
    eds.sort(key=lambda e: e["path"])
    if args.editions:
        eds = eds[: args.editions]
    root = library_root()

    # Pre-draw the page list per edition with a fixed seed so shards agree.
    plan: list[tuple[dict, int]] = []
    for e in eds:
        n = int(e.get("pages") or 0)
        if n <= 0:
            continue
        lo = 1 if n > 3 else 0   # page 0 is often a title page
        pages = sorted(rng.sample(range(lo, n), min(args.per_edition, n - lo)))
        for p in pages:
            plan.append((e, p))
    plan = [pp for i, pp in enumerate(plan) if i % args.nshards == args.shard]

    rows = []
    t0 = time.time()
    for i, (e, pidx) in enumerate(plan):
        pdf = root / e["path"]
        if not pdf.is_file():
            continue
        rec = {"path": e["path"], "work_id": e["work_id"],
               "composer": e.get("composer_slug"), "page": pidx,
               "publisher": e.get("publisher"), "image_type": e.get("image_type")}
        try:
            page = render_page(str(pdf), pidx, dpi=args.dpi)
            pws = detect_staves(page)
        except Exception as exc:                                   # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(rec)
            continue
        staves = pws.staves
        one = [s for s in staves if len(s.line_ys) < 5]
        rec.update({
            "n_staves": len(staves),
            "n_five": len(staves) - len(one),
            "n_one": len(one),
            "page_w": int(page.binary.shape[1]),
            "page_h": int(page.binary.shape[0]),
            "one_line": [
                {"staff_index": s.staff_index,
                 "y": int(s.line_ys[0]),
                 "x_start": int(s.x_start), "x_end": int(s.x_end),
                 "system_index": s.system_index,
                 "spacing": s.nominal_line_spacing_px,
                 "n_lines": len(s.line_ys)}
                for s in one],
        })
        rows.append(rec)
        if (i + 1) % 20 == 0:
            el = time.time() - t0
            print(f"  {i+1}/{len(plan)}  {el:.0f}s  ({el/(i+1):.2f}s/page)",
                  flush=True)
    out = OUT / args.out
    out.write_text(json.dumps(
        {"args": vars(args), "n_pages": len(rows), "rows": rows}, indent=1) + "\n")
    npages = sum(1 for r in rows if "n_one" in r)
    nwith = sum(1 for r in rows if r.get("n_one"))
    ntot = sum(r.get("n_one", 0) for r in rows)
    print(f"\n{npages} pages read, {nwith} with a one-line staff, "
          f"{ntot} one-line staves total, {time.time()-t0:.0f}s")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
