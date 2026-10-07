"""night 2026-10-07 read, item 1: WHICH STAGE got slower.  The record and the overnight logs hold only the whole-run wall
time (no per-stage seconds), so this times the candidate steps on saved pages, never a gather:

  (a) GATHER, per page: `detect_staves` + `extract_measures` with OMR_CELL_LINE_FIND=1 (today's default) vs =0
      (the 10-06 run); alternated, `reps` times each, median.
  (b) GATHER, per head: the far-head reader on one page's far heads with the 10-07 reader (per-bar grid, edge-vs-through,
      edge-merge fixes) vs the 10-06 reader (those keywords off); same heads, same rows, alternated per head.

  python3 night_1007_timing.py <doc> <extract json (x7/...night.json)> <pages> [reps]
"""
from __future__ import annotations
import json, os, statistics, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import overnight_1004_report as R
from tools.omr.annotate import far_head_reader as FH

OLD_OFF = dict(per_bar_grid=False, edge_vs_through=False, edge_jut_kept=False, split_welded_bands=False,
               rows_clear_of_box=False)


def main(doc, src, pages, reps=3):
    import night_1007_replay as RP
    from frame import render_page_matching_gather
    from tools.omr.staff_detector import detect_staves
    from tools.omr.measure_extractor import extract_measures
    data = json.loads(Path(src).read_text())
    rep = RP.GridReplay(doc, data)
    out = {}
    for page in pages:
        pi = render_page_matching_gather(rep.pdf, page, 600)
        t = {"1": [], "0": []}
        for _ in range(reps):
            for flag in ("1", "0"):
                os.environ["OMR_CELL_LINE_FIND"] = flag
                t0 = time.time()
                pws = detect_staves(pi)
                cells = extract_measures(pws)
                t[flag].append(time.time() - t0)
        os.environ.pop("OMR_CELL_LINE_FIND", None)
        a = dict(cells=len(cells), find_on_s=statistics.median(t["1"]), find_off_s=statistics.median(t["0"]))
        # (b) far-head reader per head
        far = {s: g for s, g in data["glyphs"].items()
               if R.page_of(s) == page and R.is_far(g) and "geo" in g and "box" in g and "fh" in g}
        ctx = rep.adopt_for(page, next(iter(far.values()))["fh"]["shape_source"]) if far else None
        tn = to = 0.0
        n = 0
        saved = dict(FH.READER_KEYWORDS)
        for s, g in far.items():
            cls = next((c for (ss, c, b) in rep.boxes_by_page[page] if ss == s), g.get("cls"))
            gl = rep.head_lines(s)
            for arm in ("new", "old"):
                FH.READER_KEYWORDS.update(saved if arm == "new" else OLD_OFF)
                t0 = time.time()
                ctx.read(s, tuple(g["box"]), cls, gl)
                dt = time.time() - t0
                if arm == "new":
                    tn += dt
                else:
                    to += dt
            n += 1
        FH.READER_KEYWORDS.update(saved)
        a.update(far_heads=n, reader_new_s=tn, reader_old_s=to)
        out[page] = a
        print(doc, page, a, flush=True)
    return out


if __name__ == "__main__":
    pg = []
    for part in sys.argv[3].split(","):
        pg.append(int(part))
    res = main(sys.argv[1], sys.argv[2], pg, int(sys.argv[4]) if len(sys.argv) > 4 else 3)
    Path(sys.argv[2]).with_suffix(".timing.json").write_text(json.dumps(res))
