"""The separating values themselves, inside a bucket geometry did not choose.

⚠️ WHY THIS IS SEPARATE FROM THE MAIN PROBE'S AUC TABLE. An AUC of 0.000 reads
as "perfect separation" and says nothing about the MARGIN. This repo's tell for
a real discriminator is a MEASURED EMPTY INTERVAL, and an interval can be
perfect and still be 0.02 staff spaces wide on nine cases -- which is a
different claim from the one the AUC appears to make. So the values are printed
rather than summarised.

The bucket matters: the crop pass sampled from the rejection census, whose
buckets are named for COMPONENT geometry (`too TALL`, `too WIDE`, `too SHORT`),
so box width is correlated with the sampling stratum in most of them -- a
barline called a notehead has a narrow BOX and a tall COMPONENT, and lands in
`too TALL` 12 times out of 12. `NO component overlaps the head at all` is
selected on the ABSENCE of a component, not on any dimension of the box, which
is why it is the one place the comparison is not circular.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_ink_first_breitkopf as P  # noqa: E402

CLEAN_BUCKET = "NO component overlaps the head at all"
REAL = P.REAL
JUNK = P.JUNK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--crop-root",
                    default="benchmarks/omr-stem-crop-pass-2026-09")
    ap.add_argument("--bucket", default=CLEAN_BUCKET)
    a = ap.parse_args()

    obs, _meta = P.load_observations(a.record)
    ink, gl, cf, _sp = P.index_rows(obs)
    man = json.load(open(os.path.join(
        a.crop_root, "out", "crop-manifest-breitkopf.json")))
    adj = json.load(open(os.path.join(
        a.crop_root, "ADJUDICATION-breitkopf.json")))
    v = {r["id"]: r["verdict"] for r in adj["rows"]}

    rows = []
    for t in man["tiles"]:
        if t.get("bucket") != a.bucket:
            continue
        g = gl.get(t["subject"])
        if not g:
            continue
        tile = {**t, "verdict": v.get(t["id"])}
        f = P.describe(tile, g, ink.get(P.cell_of(t["subject"]), []),
                       cf.get(t["subject"]))
        if f and not f["no_ink"]:
            rows.append(f)

    print(f"bucket: {a.bucket!r}")
    print(f"n = {len(rows)}")
    if not rows:
        print("DEAD: no tile of this bucket is in this record.")
        return 2

    for key, desc in (("box_w_spaces", "BOX ALONE: box width (spaces)"),
                      ("box_aspect", "BOX ALONE: box h/w"),
                      ("conf", "BOX ALONE: detector confidence"),
                      ("ink_over_box", "INK: piece extent / box extent"),
                      ("box_share_of_piece", "INK: box's share of the piece"),
                      ("piece_h_spaces", "INK: piece height (spaces)")):
        junk = sorted(round(float(f[key]), 4) for f in rows
                      if f["tile"]["verdict"] in JUNK and f.get(key) is not None)
        real = sorted(round(float(f[key]), 4) for f in rows
                      if f["tile"]["verdict"] in REAL and f.get(key) is not None)
        if len(junk) < 2 or len(real) < 2:
            print(f"\n  {desc}: DEAD (junk {len(junk)}, real {len(real)})")
            continue
        gap, lo, hi = P.widest_empty_interval(junk, real)
        clean = max(junk) < min(real) or max(real) < min(junk)
        margin = (min(real) - max(junk)) if max(junk) < min(real) else (
            min(junk) - max(real) if max(real) < min(junk) else 0.0)
        print(f"\n  {desc}")
        print(f"    junk (n={len(junk)}): {junk}")
        print(f"    real (n={len(real)}): {real}")
        print(f"    perfectly ordered: {clean}"
              + (f"   MARGIN between the two populations: {margin:.4f}"
                 if clean else ""))
        print(f"    widest empty interval anywhere: {gap:.4f} "
              f"in ({lo}, {hi})")
        if clean and margin < 0.05:
            print("    ⚠️ PERFECT ORDER, NEGLIGIBLE MARGIN -- this is an "
                  "ordering claim, not a measured gap, and n is tiny.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
