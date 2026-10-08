"""ROADMAP 2.58d -- run `gather.measure_head_stem` (the SAME pure function `gather_head_stem_reach` calls) over every
contested head of a 10-07 day record, on the page raster rendered in GATHER's own frame. This is the replay of the new
GATHER reader WITHOUT a re-gather: the reader there reads `pws.page.rgb` (gray < 128), and so does this.

  python3 benchmarks/omr-local-staff-2026-09/stem_owner_measure.py <litolff|brahms> <extract.pkl> <out.json> [pages a,b,c]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
import numpy as np  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402
from tools.library.score_library import library_root  # noqa: E402
from tools.omr.staged.gather import measure_head_stem  # noqa: E402
import stem_owner_lib as L  # noqa: E402

LIB = library_root()
PDF = {"litolff": LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}


def main(tag, pkl, out, pages=None):
    data = L.load(pkl)
    heads = L.contested(data)
    sp = L.staff_spacing(data)
    by_page = {}
    for s, box in heads.items():
        by_page.setdefault(int(s.split("/")[1]), []).append(s)
    want = sorted(by_page) if pages is None else [int(p) for p in pages.split(",")]
    res = {}
    for p in want:
        pi = render_page_matching_gather(PDF[tag], p, 600)
        rgb = np.asarray(pi.rgb)
        gray = rgb if rgb.ndim == 2 else rgb[..., :3].mean(axis=2)
        ink = gray < 128
        for s in by_page.get(p, []):
            staff = "staff/" + "/".join(s.split("/")[1:4])
            r = measure_head_stem(ink, heads[s], sp[staff])
            r["head_box_page"] = [round(v, 2) for v in heads[s]]
            res[s] = r
        print("page", p, len(by_page.get(p, [])), flush=True)
    json.dump(res, open(out, "w"))
    from collections import Counter
    print(Counter(r["direction"] for r in res.values()))


if __name__ == "__main__":
    main(*sys.argv[1:5])
