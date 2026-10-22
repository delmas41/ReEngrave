"""THE CENSUS, PER HEAD — so a sample can be drawn from it and CROPPED.

`omr-stem-ink-2026-09/rejection_census.py` partitions the 793 / 1,529
stemless heads into six named buckets and writes only the TALLY. A crop pass
needs the ROWS: which head, in which bucket, at which page box.

⚠️ THIS IS THE SAME CHAIN, NOT A SECOND ONE. `census()` is imported from that
module rather than restated, so the buckets here cannot drift from the
published table, and its per-cell FAITHFULNESS assertion (this replication's
accepted set is identical to the real `detect_stems`) is inherited with it.
A drifted cell is EXCLUDED and reported, never counted.

⚠️ It also flags the WIDTH-CAP RECOVERED stratum, by running `detect_stems`
twice per cell exactly as `width_cap_check.py` does (shipped 0.6, then 1.5) --
the 217 heads whose realness that check could only estimate at 83.6%
convention-vs-convention. That stratum is what the print is most needed for,
so it must be addressable BEFORE the sample is drawn.

REACH IS THE FIRST THING PRINTED and the run EXITS NON-ZERO at zero rows.

    python3 probe/census_rows.py --record R --pdf P --pages 1,2,3,4 \
        --label litolff --json out/litolff-rows.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-stem-ink-2026-09"))
from recordstream import stream_array  # noqa: E402
from rejection_census import census, overlaps  # noqa: E402  the SHIPPED chain


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
    from tools.omr import line_detection as ld

    heads, pboxes, klass, conf = {}, {}, {}, {}
    lines_of, spacing_of = {}, {}
    for o in stream_array(a.record, "observations"):
        q, s = o.get("quantity"), o.get("subject")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[s] = sorted(float(x) for x in o["value"])
        elif q == "staff_spacing":
            spacing_of[s] = float(o["value"])
        elif q == "notehead_class":
            klass[s] = str(o.get("value"))
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
                heads[s] = (float(v[1]), float(v[2]), float(v[3]), float(v[4]))
                d = o.get("detail") or {}
                bp = d.get("bbox_page_px")
                if bp:
                    pboxes[s] = [float(x) for x in bp]
                if d.get("confidence") is not None:
                    conf[s] = float(d["confidence"])
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}
    print(f"{a.label}: {len(missing)} heads abstain `no_stem`   "
          f"(of {len(heads)} notehead boxes)")
    if not missing:
        print("DEAD: no stemless head in this record", file=sys.stderr)
        return 2

    pages = [int(x) for x in a.pages.split(",")]
    t0 = time.time()
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))
    print(f"re-cut in {time.time() - t0:.0f}s")

    per_cell, base, wide = {}, {}, {}
    drift = 0
    for (pws, cells), pg in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            rows = census(c, ld)
            mine = sorted(b for why, b in rows
                          if why == "ACCEPTED (before the pair rule)")
            real = sorted((float(d.x_canonical), float(d.y_canonical),
                           float(d.width_canonical), float(d.height_canonical))
                          for d in ld.detect_stems(c, drop_accidental_pairs=False))
            if mine != real:
                drift += 1
                continue
            per_cell[ck] = rows
            for store, kw in ((base, {}), (wide, {"max_width_lines": 1.5})):
                store[ck] = [(float(d.x_canonical), float(d.y_canonical),
                              float(d.width_canonical),
                              float(d.height_canonical))
                             for d in ld.detect_stems(c, **kw)]
    print(f"cells censused: {len(per_cell)}   EXCLUDED for drift: {drift}")
    if drift > len(per_cell) * 0.02:
        print("DEAD: the replication has drifted from detect_stems",
              file=sys.stderr)
        return 2

    out, tally, no_pagebox = [], collections.Counter(), 0
    for s in sorted(missing):
        p = s.split("/")
        ck = "cell/" + "/".join(p[1:5])
        rows = per_cell.get(ck)
        if rows is None:
            tally["cell not censused"] += 1
            continue
        hit = [why for why, b in rows if overlaps(heads[s], b)]
        if not hit:
            bucket = "NO component overlaps the head at all"
        elif any(w.startswith("ACCEPTED") for w in hit):
            bucket = "a component WAS accepted (pair rule dropped it)"
        else:
            bucket = min(hit, key=lambda w: hit.count(w))
        tally[bucket] += 1
        # the width-cap stratum, exactly as width_cap_check.py defines it
        recovered = False
        if not any(overlaps(heads[s], st) for st in base.get(ck, [])):
            recovered = any(overlaps(heads[s], st) for st in wide.get(ck, []))
        if s not in pboxes:
            no_pagebox += 1
        sk = f"staff/{p[1]}/{p[2]}/{p[3]}"
        out.append({
            "subject": s,
            "bucket": bucket,
            "width_cap_recovered": recovered,
            "where": {"page": int(p[1]), "system": int(p[2]),
                      "staff": int(p[3]), "cell": int(p[4]),
                      "glyph": int(p[5])},
            "cls": klass.get(s), "conf": conf.get(s),
            "bbox_page_px": pboxes.get(s),
            "bbox_canonical": list(heads[s]),
            "staff_key": sk,
            "staff_lines": lines_of.get(sk),
            "staff_spacing": spacing_of.get(sk),
        })

    print(f"\n== rows: {len(out)}   width-cap recovered: "
          f"{sum(1 for r in out if r['width_cap_recovered'])}"
          f"   without a page box: {no_pagebox}")
    print(f"{'bucket':<50} {'n':>6} {'recov':>6}")
    for why, n in tally.most_common():
        rec = sum(1 for r in out if r["bucket"] == why
                  and r["width_cap_recovered"])
        print(f"{why:<50} {n:>6} {rec:>6}")
    Path(a.json).write_text(json.dumps(
        {"label": a.label, "pdf": a.pdf, "pages": pages,
         "no_stem": len(missing), "cells": len(per_cell), "drift": drift,
         "rows": out}, indent=1))
    print(f"\nwrote {a.json}")
    return 0 if out else 2


if __name__ == "__main__":
    raise SystemExit(main())
