"""ROADMAP 2.6 — does the record-side recompute agree with a gather that RAN?

⚠️⚠️ THIS IS THE CONTROL ON THE INSTRUMENT, NOT ON THE CHANGE.
`regather_ownership.py` re-runs ONE gather site over inputs rebuilt from a
saved record. That is cheap and it is blind to everything else a gather does,
so its answer is only usable if a real base-vs-arm CLI gather on the same page
moves the same way. This compares the two.

⚠️ THE TWO INSTRUMENTS ARE NOT THE SAME RUN AND MUST NOT BE READ AS ONE.
The real pair runs `--no-surya --no-ocr`, so its staves have no OCR'd identity
and `glyph_owner`'s range veto has nothing to veto on; the saved record was
gathered WITH those rungs. Absolute verdict counts therefore differ by
construction. What must agree is the DELTA the change makes: how many glyph
subjects gain a contest, and which ink they are.

⚠️ THE INK IS MATCHED BY PAGE BOX, NOT BY SUBJECT KEY. A glyph subject's last
coordinate is an index into that cell's detection list, so two detector runs
name the same ink differently. Boxes are matched at IoU >= 0.9 — and the
detector-agreement line is printed FIRST, because if the two runs did not find
the same ink then nothing downstream is comparable.

    python3 benchmarks/omr-owner-domain-2026-09/real_gather_agreement.py \\
        --base out/real-p3-base.json --arm out/real-p3-arm.json \\
        --record library/_shared-records/beethoven5-p1-p4-ink-identity.record.json \\
        --recompute out/beethoven5-p1-p4.json --page 3
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

for _p in list(Path(__file__).resolve().parents):
    if (_p / "tools" / "omr" / "staged" / "record_io.py").exists():
        sys.path.insert(0, str(_p))
        break

from tools.omr.staged.record_io import load_record            # noqa: E402
from tools.omr.staged.gather import _iou                      # noqa: E402


def boxes(rec, page):
    out = {}
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        if int(o["subject"].split("/")[1]) != page:
            continue
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b is not None:
            out[o["subject"]] = tuple(float(v) for v in b)
    return out


def contested(rec, page):
    return {o["subject"] for o in rec["observations"]
            if o["quantity"] == "glyph_band_distance"
            and int(o["subject"].split("/")[1]) == page}


def owners(rec, page):
    return {v["subject"] for v in rec["verdicts"]
            if v["quantity"] == "glyph_owner"
            and int(v["subject"].split("/")[1]) == page}


def match(a_boxes, b_boxes, floor=0.9):
    """Pair ink between two runs by page box. Greedy, and it reports misses."""
    by_key = collections.defaultdict(list)
    for sub, b in b_boxes.items():
        by_key[(int(b[0]) // 32, int(b[1]) // 32)].append((sub, b))
    pairs, unmatched = {}, []
    used = set()
    for sub, a in a_boxes.items():
        best, best_v = None, floor
        kx, ky = int(a[0]) // 32, int(a[1]) // 32
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for osub, b in by_key.get((kx + dx, ky + dy), ()):
                    if osub in used:
                        continue
                    v = _iou(a, b)
                    if v >= best_v:
                        best, best_v = osub, v
        if best is None:
            unmatched.append(sub)
        else:
            pairs[sub] = best
            used.add(best)
    return pairs, unmatched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--recompute", required=True)
    ap.add_argument("--page", type=int, default=3)
    ap.add_argument("--json", dest="out_json")
    a = ap.parse_args()
    page = a.page

    rbase = load_record(a.base)["record"]
    rarm = load_record(a.arm)["record"]
    saved = load_record(a.record)["record"]
    recomp = json.loads(Path(a.recompute).read_text())

    bb, ab = boxes(rbase, page), boxes(rarm, page)
    pairs, unmatched = match(bb, ab)
    print("DETECTOR AGREEMENT between the two real arms (the precondition)")
    print(f"  glyph boxes on page {page}: base {len(bb)}  arm {len(ab)}")
    print(f"  matched at IoU >= 0.9   : {len(pairs)}  "
          f"unmatched from base {len(unmatched)}  "
          f"unmatched from arm {len(ab) - len(pairs)}")
    if len(pairs) != len(bb) or len(bb) != len(ab):
        print("  ⚠️ THE TWO RUNS DID NOT FIND THE SAME INK — every count below "
              "carries that difference as well as the change's")

    b_con, a_con = contested(rbase, page), contested(rarm, page)
    b_own, a_own = owners(rbase, page), owners(rarm, page)
    print()
    print(f"THE REAL GATHER PAIR, page {page}")
    print(f"  glyph subjects with a band row : base {len(b_con):5d}  ->  "
          f"arm {len(a_con):5d}   ({len(a_con) - len(b_con):+d})")
    print(f"  glyph_owner verdicts           : base {len(b_own):5d}  ->  "
          f"arm {len(a_own):5d}   ({len(a_own) - len(b_own):+d})")

    # ── the recompute, restricted to the same page ──────────────────────────
    s_con = contested(saved, page)
    added = [s for s in recomp["band_subjects_added"]
             if int(s.split("/")[1]) == page]
    print()
    print(f"THE RECORD-SIDE RECOMPUTE, page {page} "
          f"({Path(a.record).name})")
    print(f"  glyph subjects with a band row : base {len(s_con):5d}  ->  "
          f"arm {len(s_con) + len(added):5d}   ({len(added):+d})")

    print()
    print("AGREEMENT")
    print(f"  subjects newly contested — real gather {len(a_con) - len(b_con):+d}"
          f"   recompute {len(added):+d}")
    sb = boxes(saved, page)
    rec_added_boxes = [sb[s] for s in added if s in sb]
    real_added_subs = a_con - {pairs[s] for s in b_con if s in pairs}
    real_added_boxes = [ab[s] for s in real_added_subs if s in ab]
    hit = 0
    for rb in rec_added_boxes:
        if any(_iou(rb, xb) >= 0.9 for xb in real_added_boxes):
            hit += 1
    print(f"  the SAME INK, matched by page box at IoU >= 0.9: "
          f"{hit} of {len(rec_added_boxes)} of the recompute's newly-contested "
          f"glyphs are also newly contested in the real gather")
    if hit != len(rec_added_boxes):
        print("  ⚠️ where they differ, it is one of: a detector box that moved "
              "between the two runs, or a cell the --no-surya arm cut "
              "differently. Named in the --json.")

    if a.out_json:
        missing = [list(map(lambda v: round(v, 1), rb))
                   for rb in rec_added_boxes
                   if not any(_iou(rb, xb) >= 0.9 for xb in real_added_boxes)]
        Path(a.out_json).write_text(json.dumps({
            "page": page,
            "detector": {"base_boxes": len(bb), "arm_boxes": len(ab),
                         "matched": len(pairs),
                         "unmatched_base": len(unmatched),
                         "unmatched_arm": len(ab) - len(pairs)},
            "real": {"contested_base": len(b_con), "contested_arm": len(a_con),
                     "owner_base": len(b_own), "owner_arm": len(a_own)},
            "recompute": {"contested_base": len(s_con),
                          "newly_contested": len(added)},
            "same_ink_matched": hit,
            "recompute_added": len(rec_added_boxes),
            "recompute_added_not_in_real": missing,
        }, indent=1))
        print(f"\nwrote {a.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
