"""WHICH FILTER IS EATING THE MISSING STEMS -- and is it a filter at all?

`pair_rule_arm.py` settled one: `drop_accidental_pairs=False` recovers 73 of
793 heads on Litolff. That is 9.2%, not the bulk, and it refutes this
session's own raster proxy, which had predicted a much larger share.

`detect_stems` exposes every filter it applies as a keyword, so each can be
relaxed ALONE and scored, and then ALL AT ONCE. The all-at-once arm is the
number that matters: it is the CEILING on what any amount of filter-tuning
could ever recover. Whatever the ceiling does not reach is lost EARLIER --
in step 3, the vertical morphological opening on the staff-line-ERASED image,
where a stem crossed by an erased staff line is cut into pieces shorter than
the kernel and stops being one component at all.

⚠️ THE CONTROL RUNS FIRST AND MUST BE EXACT. The shipped settings must
reproduce the record's `Q.STEM` rows cell for cell; `pair_rule_arm.py` got
783 of 783 and 1920 = 1920 on this document. A re-cut that does not reproduce
the record is a different document, not an arm.

⚠️ RELAXING IS NOT SHIPPING. Every filter here was measured onto its value --
`STEM_MAX_HEIGHT_LINES = 8.0` sits where a barline population separates, the
height FLOOR was tried instead of the pair rule and scored worse (36 vs 24),
and raising it destroys keyboard music where beamed stems are legitimately
short. This arm prices RECALL only, and the cost column is the minimum honest
counterweight, not a full price.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

# name -> kwargs that RELAX exactly one filter
ARMS = {
    "shipped (control)":            {},
    "no accidental-pair rule":      {"drop_accidental_pairs": False},
    "height cap 8.0 -> 24.0":       {"max_height_lines": 24.0},
    "height floor 2.0 -> 1.0":      {"min_height_lines": 1.0},
    "width cap 0.6 -> 1.5":         {"max_width_lines": 1.5},
    "ALL FOUR relaxed (ceiling)":   {"drop_accidental_pairs": False,
                                     "max_height_lines": 24.0,
                                     "min_height_lines": 1.0,
                                     "max_width_lines": 1.5},
}


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.line_detection import detect_stems

    heads, accid, rec_stems = {}, collections.defaultdict(list), \
        collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "glyph_box":
            v = o.get("value")
            if not (isinstance(v, list) and len(v) == 5):
                continue
            name = str(v[0])
            box = (float(v[1]), float(v[2]), float(v[3]), float(v[4]))
            if name.startswith("notehead"):
                heads[o["subject"]] = box
            elif name.startswith("accidental") or name.startswith("key"):
                p = o["subject"].split("/")
                accid["cell/" + "/".join(p[1:5])].append(box)
        elif q == "stem":
            v = o["value"]
            rec_stems[o["subject"]].append(tuple(float(x) for x in v))
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}
    print(f"{a.label}: {len(heads)} noteheads, {len(missing)} abstain no_stem")

    pages = [int(x) for x in a.pages.split(",")]
    t0 = time.time()
    prepared = [(pws, cells, pg) for (pws, cells), pg
                in zip(prepare_pages(a.pdf, pages, dpi=600), pages)]
    print(f"re-cut in {time.time() - t0:.0f}s")

    results: dict[str, dict[str, list]] = {}
    for name, kw in ARMS.items():
        t = time.time()
        store: dict[str, list] = {}
        for pws, cells, pg in prepared:
            local = _system_local(pws.staves)
            for c in cells:
                key = local.get(c.staff_index)
                if key is None:
                    continue
                ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
                store[ck] = [(float(d.x_canonical), float(d.y_canonical),
                              float(d.width_canonical),
                              float(d.height_canonical))
                             for d in detect_stems(c, **kw)]
        results[name] = store
        print(f"  {name:<28} {sum(len(v) for v in store.values()):>6} strokes"
              f"   {time.time() - t:.0f}s")

    base = results["shipped (control)"]
    shared = set(base) & set(rec_stems)
    same = sum(1 for k in shared if sorted(base[k]) == sorted(rec_stems[k]))
    print(f"\n== CONTROL: {same} of {len(shared)} cells reproduce the record "
          f"exactly; strokes {sum(len(v) for v in base.values())} vs "
          f"{sum(len(v) for v in rec_stems.values())}")
    out = {"label": a.label, "no_stem_total": len(missing),
           "control_cells_identical": same, "control_cells": len(shared),
           "arms": {}}
    if not shared or same != len(shared):
        print("DEAD: the re-cut does not reproduce the record.", file=sys.stderr)
        Path(a.json).write_text(json.dumps(out, indent=1))
        return 2

    print(f"\n== RECALL: heads that abstain `no_stem` today and would gain an "
          f"overlapping stroke")
    print(f"{'arm':<28} {'recovered':>10} {'of 793':>8} {'new strokes':>12} "
          f"{'on an accidental':>17}")
    for name, store in results.items():
        rec = 0
        for s in missing:
            p = s.split("/")
            ck = "cell/" + "/".join(p[1:5])
            if ck in store and any(overlaps(heads[s], st) for st in store[ck]):
                rec += 1
        new = onacc = 0
        for ck, sts in store.items():
            extra = [st for st in sts if st not in base.get(ck, [])]
            new += len(extra)
            onacc += sum(1 for st in extra
                         if any(overlaps(st, ac) for ac in accid.get(ck, [])))
        out["arms"][name] = {"recovered": rec, "new_strokes": new,
                             "new_on_accidental": onacc}
        print(f"{name:<28} {rec:>10} {rec/max(1,len(missing)):>7.1%} "
              f"{new:>12} {onacc:>17}")

    ceil = out["arms"]["ALL FOUR relaxed (ceiling)"]["recovered"]
    print(f"\n⚠️  CEILING: relaxing EVERY filter recovers {ceil} of "
          f"{len(missing)} ({ceil/max(1,len(missing)):.1%}). The remaining "
          f"{len(missing)-ceil} are not lost to a filter -- they never "
          f"survive the morphological opening as one component.")
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
