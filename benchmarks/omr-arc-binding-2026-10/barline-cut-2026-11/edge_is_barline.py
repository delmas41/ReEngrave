"""Is each interior cell edge a PRINTED barline? Page raster (600 dpi), per staff: a barline inks the centre row of all 4 spaces between the 5 staff lines
within +-0.5 sp of the edge x. Control: the same test at x positions 2-4 sp inside each cell (should be rare: only stems/notes), run on the same staves.

    python3 edge_is_barline.py PLATE      (adds edge_is_barline.PLATE.json)
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aac9f13c6fcc2a60b/benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11")
import crops as C   # noqa: E402

SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/%s/observations.jsonl"
SAMPLE = {"litolff": [2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}


def main():
    plate = sys.argv[1]
    pages = set(SAMPLE[plate])
    cells, lines = {}, {}
    for l in open(SL % plate):
        if '"cell_box"' not in l and '"staff_lines"' not in l:
            continue
        o = json.loads(l)
        s = o["subject"]
        if int(s.split("/")[1]) not in pages:
            continue
        if o["quantity"] == "cell_box":
            cells[s] = o["value"]
        elif o["quantity"] == "staff_lines":
            lines[s] = o["value"]
    out = {}
    ctl = []
    bypage = {}
    for ck in cells:
        bypage.setdefault(int(ck.split("/")[1]), []).append(ck)
    for pg in sorted(bypage):
        im = np.asarray(C.page_image(plate, pg).convert("L")) < 128
        for ck in bypage[pg]:
            _, p, sy, st, m = ck.split("/")
            ls = lines.get("staff/%s/%s/%s" % (p, sy, st))
            if not ls:
                continue
            sp = (ls[-1] - ls[0]) / (len(ls) - 1)
            rows = [int(round((ls[i] + ls[i + 1]) / 2)) for i in range(len(ls) - 1)]
            b = cells[ck]
            w = max(2, int(round(0.5 * sp)))

            top, bot = int(round(ls[0])), int(round(ls[-1]))

            def test(x):
                x = int(round(x))
                col = im[top:bot + 1, max(0, x - w):x + w + 1].mean(axis=0)
                return bool((col >= 0.97).any())
            for side, x in (("l", b[0]), ("r", b[2])):
                out["%s|%s" % (ck, side)] = bool(test(x))
            # control: positions inside the cell
            for f in (0.35, 0.5, 0.65):
                ctl.append(bool(test(b[0] + f * (b[2] - b[0]))))
        print("page", pg, "done", flush=True)
    json.dump(dict(edges=out, control_hits=sum(ctl), control_n=len(ctl)), open("results/edge_is_barline.%s.json" % plate, "w"))
    inter = [k for k in out]
    print(plate, "edges", len(out), "printed barline %.1f%%" % (100 * sum(out.values()) / len(out)), "| control inside-cell hits %d/%d" % (sum(ctl), len(ctl)))


main()
