"""ROADMAP 2.315 -- dump REAL bars (the staff-erased raster of one measure cell, as GATHER's search reads it) to small .npz fixtures, so the search is replayed on the
page's own pixels, never a drawing (rule 7; 2.288 r3's synthetic control passed while a real page failed).

    PYTHONPATH=. python3 benchmarks/whole-rests-2026-11/dump_real_cells.py

Each case: image_no_staff (bit-packed), the cell's canonical staff lines, and what the case IS and who says so. `sean` = Sean's own reading of the bar (2.311 set-b tiles);
`ours` = our look at the crop (a control, not evidence)."""
from __future__ import annotations

import collections
import json
import pathlib

import numpy as np

from tools.omr.staged.lane_report import LIB, PLATES
from tools.omr.staged.pipeline import prepare_pages

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "real_cells"
EXTRA = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/2311/%s.extra.json"

#: id -> (plate, "page/system/staff/cell", is_whole_rest_bar, who says, note)
CASES = {
    "b-tile12": ("brahms", "8/0/0/5", True, "sean", "set b tile 12: 'a whole note rest'; the cell holds one head that is another staff's"),
    "b-tile8": ("brahms", "25/0/5/7", True, "sean", "set b tile 8: nothing but a whole rest; the cell holds one barline-ink box"),
    "lit-8-0-1-4": ("litolff", "8/0/1/4", True, "ours", "a whole rest 0.89 sp tall, aspect 1.56 on the erased raster: the box numbers turn it down"),
    "lit-6-0-1-5": ("litolff", "6/0/1/5", True, "ours", "a whole rest 0.87 sp tall: the box numbers turn it down"),
    "bra-8-1-0-5": ("brahms", "8/1/0/5", True, "ours", "a whole rest 0.87 sp tall: the box numbers turn it down"),
    "lit-10-1-3-4": ("litolff", "10/1/3/4", False, "ours", "a half-note chord the detector never boxed: not a rest"),
    "lit-11-1-3-7": ("litolff", "11/1/3/7", False, "ours", "a chord the detector never boxed: not a rest"),
    "bra-8-1-5-10": ("brahms", "8/1/5/10", False, "ours", "a hollow half note with a tie: not a rest"),
    "bra-8-1-10-5": ("brahms", "8/1/10/5", False, "ours", "a hollow half note with a tie: not a rest"),
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    by_page = collections.defaultdict(list)
    for cid, (plate, bar, *_r) in CASES.items():
        by_page[(plate, int(bar.split("/")[0]))].append(cid)
    extra = {p: json.load(open(EXTRA % t)) for p, t in (("litolff", "lit-a"), ("brahms", "bra-a"))}
    meta_all = {}
    for (plate, page), cids in sorted(by_page.items()):
        pws, cells = prepare_pages(str(LIB / PLATES[plate]["pdf"]), [page], dpi=600)[0]
        for cid in cids:
            _plate, bar, is_rest, who, note = CASES[cid]
            box = extra[plate]["cell_box"][bar]
            best = min(cells, key=lambda c: sum(abs(a - b) for a, b in zip(getattr(c, "bbox_page_px", (1e9,) * 4), box)))
            img = best.image_no_staff
            np.savez_compressed(OUT / (cid + ".npz"), ink=np.packbits(img == 0, axis=1), shape=np.array(img.shape), lines=np.array(best.staff_line_ys_canonical, dtype=float))
            meta_all[cid] = dict(plate=plate, bar=bar, is_whole_rest_bar=is_rest, says=who, note=note, shape=list(img.shape))
            print(cid, img.shape, flush=True)
    (HERE / "real_cells.json").write_text(json.dumps(meta_all, indent=1))


if __name__ == "__main__":
    main()
