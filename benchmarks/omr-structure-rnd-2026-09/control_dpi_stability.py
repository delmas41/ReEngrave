"""Control: is the screen-1 verdict a property of the PAGE or of the DPI?

The census sweeps at 300 dpi for cost.  Screen 1 asks whether two systems on a
page report different staff COUNTS -- and a staff count is exactly the quantity
that moved when the 20-row gate was re-measured at 300 dpi against its own
600 dpi fixtures: 16 of 20 rows matched, and the four that did not were the
dense Peters Mahler pages, which read 17/13/18/17 staves at 600 and 19/15/20/21
at 300.

So a tier-A rate measured at one DPI is only as good as its stability across
DPI.  This re-measures a stratified random sample at 600 dpi and reports how
often the VERDICT (fires / does not fire) survives.

A high disagreement rate here means the census's headline rate is a measurement
of the renderer, not of the library.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

from sweep_lineup_change import screen_phase1  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-per-tier", type=int, default=30)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--seed", type=int, default=20260905)
    ap.add_argument("--time-budget-s", type=float, default=2400.0)
    args = ap.parse_args()

    recs = []
    for p in args.jsonl:
        recs += [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
    assert recs, "no sweep records -- nothing to control"

    rng = random.Random(args.seed)
    strata = {t: [r for r in recs if r.get("tier") == t] for t in ("A", "none", "D")}
    sample = []
    for t, pool in strata.items():
        assert pool, f"stratum {t} is empty -- cannot control it"
        sample += rng.sample(pool, min(args.n_per_tier, len(pool)))
    assert sample, "empty control sample"
    print(f"control sample: {len(sample)} pages "
          f"({ {t: min(args.n_per_tier, len(p)) for t, p in strata.items()} })",
          flush=True)

    root = library_root()
    started = time.time()
    out = []
    partial = Path(args.out).with_suffix(".partial.jsonl")
    if partial.exists():
        partial.unlink()
    for i, r in enumerate(sample):
        if time.time() - started > args.time_budget_s:
            print("time budget reached", flush=True)
            break
        try:
            page = render_page(root / r["path"], r["page_index"], dpi=args.dpi)
            hi = screen_phase1(detect_staves(page).staves)
        except Exception as exc:  # noqa: BLE001
            out.append({**{k: r[k] for k in ("path", "page_index", "tier")},
                        "hi_dpi_error": f"{type(exc).__name__}: {exc}"})
            continue
        out.append({
            "path": r["path"],
            "page_index": r["page_index"],
            "publisher": r.get("publisher"),
            "tier_300": r["tier"],
            "counts_300": r["staff_counts"],
            "tier_600": hi["tier"],
            "counts_600": hi["staff_counts"],
            "screen1_300": "counts" in r.get("screens", []),
            "screen1_600": "counts" in hi.get("screens", []),
            "counts_identical": r["staff_counts"] == hi["staff_counts"],
        })
        with partial.open("a") as ph:
            ph.write(json.dumps(out[-1]) + "\n")
        print(f"  {i + 1}/{len(sample)} {out[-1]['tier_300']} "
              f"{out[-1]['counts_300']} -> {out[-1]['counts_600']}", flush=True)

    scored = [o for o in out if "screen1_600" in o]
    assert scored, "the control measured ZERO pages at high DPI"
    agree = sum(1 for o in scored if o["screen1_300"] == o["screen1_600"])
    same_counts = sum(1 for o in scored if o["counts_identical"])
    # the number that matters: of the pages screen 1 fired on at 300, how many
    # still fire at 600?
    fired300 = [o for o in scored if o["screen1_300"]]
    held = sum(1 for o in fired300 if o["screen1_600"])
    payload = {
        "dpi_hi": args.dpi,
        "seed": args.seed,
        "n_scored": len(scored),
        "n_verdict_agree": agree,
        "verdict_agreement": round(agree / len(scored), 4),
        "n_counts_identical": same_counts,
        "counts_identical_rate": round(same_counts / len(scored), 4),
        "n_fired_at_300": len(fired300),
        "n_still_fires_at_600": held,
        "screen1_persistence": round(held / len(fired300), 4) if fired300 else None,
        "rows": out,
    }
    Path(args.out).write_text(json.dumps(payload, indent=1))
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
