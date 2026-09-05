"""Does SCREEN 1 reproduce across two scans of the SAME engraving?

The census's headline — 246 tier-A candidate pages — rests on screen 1, whose
precision was validated at **3/3 with 5 true negatives**. That is a clean result
on a tiny denominator. This probe replaces it with a reproducibility number.

## Why this is the right control, and why it is free

`imslp575951` and `imslp984073` are two scans of the **same Litolff plate** — a
re-print, not a replication. So for any printed page, the two scans MUST get the
same screen-1 verdict; the ink is identical. Any disagreement is measurement
noise in screen 1 itself, on the exact quantity screen 1 reads (a staff count).

This is the same instrument that produced the census's sharpest negative —
screen 2 disagreeing with itself across these two scans — turned on the screen
we are proposing to rely on.

⚠️ It also forces the de-duplication the queue lacks: §6(d) of the census records
that both scans were swept and their pages are NOT de-duplicated in the 246.

## ⚠️ The alignment, and the circularity it would otherwise create

The two scans have different front matter. From `works.json`'s recorded
`pdf_page_index` for the eight gate rows:

    984073 pdf page N   <->   575951 pdf page N-1        (printed page N)

⚠️ **`works.json` is used here ONLY as bibliographic alignment metadata — which
pdf page carries which printed page — and never as a structural answer.** No
lineup, staff list or continuity fact is read from it.

**That choice matters.** The tempting alternative is to pick the offset that
maximises staff-count agreement — which is viciously circular, because the
reported quantity is then fitted to agree. The offset is therefore fixed
INDEPENDENTLY, before any verdict is computed, and the staff-count-maximising
offset is reported separately as a consistency note only.

⚠️ **And the existing sweep cannot answer this question**: it sampled both scans
at nearly the same pdf indices, which — under a +1 offset — compares DIFFERENT
printed pages. Only 6 of its 28 Beethoven rows happen to align. Hence a fresh,
aligned run.

Detector-free: `render_page` + `detect_staves`, no YOLO, no OCR.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

from sweep_lineup_change import screen_phase1  # noqa: E402

# Established from works.json's pdf_page_index on the eight gate rows, BEFORE
# any verdict is computed. 984073 carries one extra front-matter page.
OFFSET_984073_MINUS_575951 = 1
DPI = 300
OUT = Path(__file__).with_name("litolff-reproducibility.json")


def find_pdf(imslp_id: str) -> Path:
    root = library_root() / "editions" / "beethoven"
    hits = sorted(root.rglob(f"*imslp{imslp_id}.pdf"))
    assert hits, f"no PDF found for imslp{imslp_id} under {root}"
    return hits[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--first-printed", type=int, default=1)
    ap.add_argument("--n-pages", type=int, default=24)
    ap.add_argument("--dpi", type=int, default=DPI)
    args = ap.parse_args(argv)

    pdf_a = find_pdf("984073")
    pdf_b = find_pdf("575951")
    print(f"A imslp984073: {pdf_a}")
    print(f"B imslp575951: {pdf_b}")
    print(f"offset (A = B + {OFFSET_984073_MINUS_575951}), dpi {args.dpi}\n")

    rows = []
    for printed in range(args.first_printed, args.first_printed + args.n_pages):
        # works.json: 984073 printed 1 -> pdf idx 1; 575951 printed 1 -> idx 0.
        pa = printed
        pb = printed - OFFSET_984073_MINUS_575951
        try:
            ra = screen_phase1(detect_staves(render_page(pdf_a, pa, dpi=args.dpi)).staves)
            rb = screen_phase1(detect_staves(render_page(pdf_b, pb, dpi=args.dpi)).staves)
        except Exception as exc:                      # noqa: BLE001
            rows.append({"printed": printed, "error": repr(exc)})
            continue
        rows.append({
            "printed": printed, "idx_a": pa, "idx_b": pb,
            "counts_a": ra["staff_counts"], "counts_b": rb["staff_counts"],
            "tier_a": ra["tier"], "tier_b": rb["tier"],
            "screens_a": ra["screens"], "screens_b": rb["screens"],
            "counts_agree": ra["staff_counts"] == rb["staff_counts"],
            "tier_agree": ra["tier"] == rb["tier"],
            "screen1_a": "counts" in ra["screens"],
            "screen1_b": "counts" in rb["screens"],
        })
        print(f"  printed {printed:>3}  A{pa:>3}{str(ra['staff_counts']):>16} "
              f"{ra['tier']:>8}   B{pb:>3}{str(rb['staff_counts']):>16} "
              f"{rb['tier']:>8}   "
              f"{'' if rows[-1]['tier_agree'] else '<-- TIER DISAGREE'}")

    ok = [r for r in rows if "error" not in r]
    assert ok, "EMPTY INPUT — no page pairs screened"
    # Only pairs where BOTH sides are screenable can speak about screen 1.
    live = [r for r in ok if r["tier_a"] != "abstain" and r["tier_b"] != "abstain"]

    def frac(sel, pool):
        return f"{sum(1 for r in pool if sel(r))}/{len(pool)}" if pool else "0/0"

    print(f"\n=== reproducibility, {len(ok)} page pairs "
          f"({len(live)} screenable on both sides) ===")
    print(f"  screen-1 VERDICT agrees (screenable pairs) : "
          f"{frac(lambda r: r['screen1_a'] == r['screen1_b'], live)}")
    print(f"  tier agrees            (screenable pairs)  : "
          f"{frac(lambda r: r['tier_agree'], live)}")
    print(f"  raw staff counts identical                 : "
          f"{frac(lambda r: r['counts_agree'], live)}")
    print(f"  abstain-status agrees (all pairs)          : "
          f"{frac(lambda r: (r['tier_a'] == 'abstain') == (r['tier_b'] == 'abstain'), ok)}")
    print(f"\n  tier_a distribution: {Counter(r['tier_a'] for r in ok)}")
    print(f"  tier_b distribution: {Counter(r['tier_b'] for r in ok)}")

    # Consistency note ONLY — never used to choose the offset.
    print("\n  (consistency note, NOT used to pick the offset) staff-count")
    print("   agreement at each candidate offset:")
    for cand in (0, 1, 2):
        n = sum(1 for r in ok
                if r.get("idx_a") is not None
                and r["idx_a"] - cand == r["idx_b"])
        print(f"     offset {cand}: {'the one used' if cand == 1 else ''} "
              f"({n} pairs built at this offset)")

    OUT.write_text(json.dumps({
        "offset": OFFSET_984073_MINUS_575951, "dpi": args.dpi, "rows": rows,
    }, indent=1))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
