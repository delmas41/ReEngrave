"""lane-offbox-check: replay the far-head reader on the gather-frame raster to recover the LEDGER ROWS IT MEASURED for
every decided far head (and for the truth-set heads), the way `overnight_1004_sheet.py` does, with its control: a
replay whose position differs from the recorded one is marked `repro=False` and left out of the measured-rows
variant (counted, never silently dropped).

  python3 offbox_measured.py <extract json (with `boxes`)> <doc> <out json> [--pages a,b]

Writes per head: rungs (y px, the rows handed to the reader's step rule), cap_box (the box the step rule used),
the local lines, the replayed position, repro.
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import frame_drop_pairs as P
import overnight_1004_report as R
import overnight_1004_sheet as SH
from tools.omr.annotate import far_head_reader as FH


class CachedReplay(SH.DocReplay):
    """DocReplay with the adopted (page, shape_source) context cached: the pooled shape is rebuilt once per k."""

    def __init__(self, doc, data):
        super().__init__(doc, data)
        self._adopted = {}
        self._pool_by_k = {}
        self._samples = {}

    def samples_of(self, page):
        if page not in self._samples:
            self._samples[page] = list(self.page_ctx(page).samples)
        return self._samples[page]

    def adopt_for(self, page, shape_source):
        key = (page, shape_source)
        if key in self._adopted:
            return self._adopted[key]
        ctx = self.page_ctx(page)
        if shape_source.startswith("page"):
            self._adopted[key] = ctx
            return ctx
        import re
        k = int(re.search(r"n=(\d+)", shape_source).group(1))
        if k not in self._pool_by_k:
            pool = []
            for p in sorted(self.boxes_by_page):
                pool.extend(self.samples_of(p))
                if len(pool) >= k:
                    break
            if len(pool) != k:
                print(f"   (pool replay: wanted n={k}, got {len(pool)})", flush=True)
            self._pool_by_k[k] = FH.pooled_shape(pool)
        ctx.adopt(self._pool_by_k[k], shape_source)
        self._adopted[key] = ctx
        return ctx


def main(src, doc, out, pages=None):
    data = json.loads(Path(src).read_text())
    assert "boxes" in data, "extract needs `boxes`"
    G = data["glyphs"]
    rep = CachedReplay(doc, data)
    far = {s: g for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g and "fh" in g}
    res = {}
    stats = collections.Counter()
    by_page = collections.defaultdict(list)
    for s in far:
        by_page[R.page_of(s)].append(s)
    for page in sorted(by_page):
        if pages and page not in pages:
            continue
        for s in by_page[page]:
            g = far[s]
            ctx = rep.adopt_for(page, g["fh"]["shape_source"])
            key = "staff/" + "/".join(s.split("/")[1:4])
            gl = data["staff_lines"][key]
            cls = next((c for (ss, c, b) in rep.boxes_by_page[page] if ss == s), g.get("cls"))
            try:
                r, cap, lines = P.capture_read(ctx, dict(subject=s, box=tuple(g["box"]), cls=cls), gl)
            except Exception as e:  # a replay that raises is a replay that did not reproduce
                stats["raised"] += 1
                res[s] = dict(repro=False, error=repr(e))
                continue
            rec = R.decided_pos(g)
            ok = (r["pos"] == rec)
            stats["repro" if ok else "mismatch"] += 1
            res[s] = dict(repro=bool(ok), replay_pos=r["pos"], rungs=[float(y) for y in cap.get("rungs", [])],
                          cap_box=[float(v) for v in cap["box"]] if "box" in cap else None,
                          lines=[float(y) for y in lines])
        print(doc, "page", page, dict(stats), flush=True)
        rep.gray.pop(page, None)
    Path(out).write_text(json.dumps(dict(doc=doc, src=src, stats=dict(stats), heads=res)))
    print("wrote", out, dict(stats))


if __name__ == "__main__":
    a = sys.argv[1:]
    pages = set(int(x) for x in a[a.index("--pages") + 1].split(",")) if "--pages" in a else None
    main(a[0], a[1], a[2], pages)
