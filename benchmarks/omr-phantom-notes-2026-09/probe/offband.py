"""THE RECALL SIDE: rest-SHAPED noteheads that the POSITION witness refuses.

⚠️ A veto's cost is the population it declines, and this repo's record is that
a rule is priced by what it REFUSES as much as by what it catches. These are
the noteheads whose ink is squat and wide -- rest-shaped -- but which do NOT
stand where a whole rest is obliged to stand. A random sample of them is
tiled, so the refusal can be looked at rather than assumed correct.

    python3 .../offband.py --record R.json --out rows.json
"""
from __future__ import annotations

import argparse
import collections
import json
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--seed", type=int, default=20260911)
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]
    spacing, lines = {}, {}
    for o in rec["observations"]:
        if o["subject"].startswith("staff/"):
            k = tuple(int(x) for x in o["subject"].split("/")[1:4])
            if o["quantity"] == "staff_spacing":
                spacing[k] = float(o["value"])
            elif o["quantity"] == "staff_lines":
                lines[k] = o["value"]
    conf = {o["subject"]: o["score"] for o in rec["observations"]
            if o["quantity"] == "glyph_conf"}

    rows = []
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        pg = (o.get("detail") or {}).get("bbox_page_px")
        if not pg:
            continue
        b = o["subject"].split("/")
        k = (int(b[1]), int(b[2]), int(b[3]))
        sp, ly = spacing.get(k), lines.get(k)
        if not sp or not ly:
            continue
        cls = o["value"][0]
        if not cls.startswith("notehead"):
            continue
        w, h = (pg[2] - pg[0]) / sp, (pg[3] - pg[1]) / sp
        if h <= 0:
            continue
        step = (max(ly) - (pg[1] + pg[3]) / 2.0) / (sp / 2.0)
        rows.append({"subject": o["subject"], "page": k[0], "system": k[1],
                     "staff": k[2], "cell": int(b[4]), "cls": cls,
                     "conf": conf.get(o["subject"]) or 0.0,
                     "w": w, "h": h, "a": w / h, "step": step})

    print(f"noteheads measured            {len(rows)}")
    shape = [r for r in rows if r["h"] < 0.85 and r["a"] > 1.8]
    inband = [r for r in shape if 4.6 <= r["step"] <= 6.6]
    off = [r for r in shape if not (4.6 <= r["step"] <= 6.6)]
    print(f"  rest-SHAPED                 {len(shape)}")
    print(f"    and in the whole-rest band {len(inband)}")
    print(f"    and OFF the band           {len(off)}")
    print(f"  off-band step histogram: "
          f"{dict(collections.Counter(round(r['step']) for r in off).most_common(24))}")
    random.seed(a.seed)
    samp = random.sample(off, min(a.n, len(off)))
    json.dump(samp, open(a.out, "w"), indent=1)
    print(f"  sampled {len(samp)} (seed {a.seed}) -> {a.out}")


if __name__ == "__main__":
    main()
