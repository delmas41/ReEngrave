"""Cut a crop around every one-line staff the census found, so a human can say
whether it is a percussion rule or junk.

The census can only report GEOMETRY. Whether a full-width rule between two
staves is a bass-drum part or a rehearsal rule is a question about ink, and the
only honest way to answer it is to look — the same standard the ledger-zone
label audit settled on after five geometric fixes failed to generalise
(`benchmarks/omr-snap-ledger-2026-09/LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md`).

Each crop is the rule plus four staff spaces either side and the full staff
width, downscaled so a page-wide rule is legible.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page                    # noqa: E402
from tools.library.score_library import library_root               # noqa: E402

HERE = Path(__file__).parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="census.json")
    ap.add_argument("--out-dir", default="crops")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--pad-spaces", type=float, default=5.0)
    ap.add_argument("--max-width", type=int, default=1400)
    args = ap.parse_args(argv)

    doc = json.loads((HERE / args.census).read_text())
    out = HERE / args.out_dir
    out.mkdir(exist_ok=True)
    root = library_root()

    hits = [r for r in doc["rows"] if r.get("n_one")]
    print(f"{len(hits)} pages carry a one-line staff")
    index = []
    for r in hits:
        pdf = root / r["path"]
        page = render_page(str(pdf), r["page"], dpi=args.dpi)
        rgb = page.rgb
        for e in r["one_line"]:
            sp = float(e.get("spacing") or 20.0)
            pad = int(round(args.pad_spaces * sp))
            y0 = max(0, e["y"] - pad)
            y1 = min(rgb.shape[0], e["y"] + pad)
            x0 = max(0, e["x_start"] - pad)
            x1 = min(rgb.shape[1], e["x_end"] + pad)
            crop = rgb[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            if crop.shape[1] > args.max_width:
                sc = args.max_width / crop.shape[1]
                crop = cv2.resize(crop, (args.max_width, max(1, int(crop.shape[0] * sc))),
                                  interpolation=cv2.INTER_AREA)
            slug = (r["path"].replace("/", "__").replace(".pdf", "")
                    + f"__p{r['page']}__s{e['staff_index']}.png")
            cv2.imwrite(str(out / slug), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            index.append({"file": slug, "path": r["path"], "page": r["page"],
                          "work_id": r["work_id"], "staff_index": e["staff_index"],
                          "y": e["y"], "spacing": sp,
                          "n_staves": r["n_staves"], "n_one": r["n_one"]})
            print("  ", slug, flush=True)
    (out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(f"\n{len(index)} crops -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
