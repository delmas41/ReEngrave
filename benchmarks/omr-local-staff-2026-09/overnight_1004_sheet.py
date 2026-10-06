"""out/print/ledgers/overnight_1004_sample.png -- 12 seeded-random OUT-OF-SAMPLE far heads where the 10-04 overnight
RUN 2 (`20261004-farhead-all`) reads a position different from geometry; 6 Litolff (pages 4-16) + 6 Brahms (pages 2-26).
There is NO reference on these pages: the sheet exists so Sean can say which of the two ticks sits on the head.

The reader is REPLAYED on the page raster in the gather's own frame (`render_page(...)`, one call, deskewed) with the
record's boxes, staff lines and class names, and the page's head shape (its own, or the pooled one the gather used --
rebuilt from the `shape_source` string on the row). CONTROL that can fail: a replay that does not give the position
RUN 2 recorded is NOT drawn (counted and printed), so every tile shows what the record holds.

  python3 overnight_1004_sheet.py <dir holding the extracted JSONs (RUN 2 with `boxes`)> [--seed 20261004]
"""
from __future__ import annotations
import collections, json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import frame_drop_pairs as P
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH
import overnight_1004_report as R

S = P.S
BLUE, GREEN, ORANGE, RED, MAGENTA = P.BLUE, P.GREEN, P.ORANGE, P.RED, P.MAGENTA
OUT = Path(__file__).resolve().parents[2] / "out/print/ledgers/overnight_1004_sample.png"
DOCS = R.DOCS
PER_DOC = 6


class DocReplay:
    """Rebuilds the gather's per-page FarHeadPage (and the pooled shape it fell back to) from a record's extract."""

    def __init__(self, doc, data):
        self.doc, self.data = doc, data
        self.pdf = ts.DOCS[doc]["pdf"]
        self.boxes_by_page = collections.defaultdict(list)
        for s, c, b in data["boxes"]:
            self.boxes_by_page[R.page_of(s)].append((s, c, tuple(b)))
        self.gray, self.pages_ctx, self.pool_after = {}, {}, {}
        self.pool = []
        self.pooled_through = 0
        self.first_page = min(self.boxes_by_page)

    def gray_of(self, page):
        if page not in self.gray:
            pi = render_page_matching_gather(self.pdf, page, 600)
            import cv2 as _cv
            self.gray[page] = _cv.cvtColor(pi.rgb, _cv.COLOR_RGB2GRAY)
        return self.gray[page]

    def page_ctx(self, page):
        if page in self.pages_ctx:
            return self.pages_ctx[page]
        G = self.data["glyphs"]
        cls_of = {s: c for (s, c, b) in self.boxes_by_page[page]}
        heads, used = [], {}
        for s, g in G.items():
            if R.page_of(s) != page or "geo" not in g or "box" not in g:
                continue
            c = cls_of.get(s)
            if not c or not c.startswith("notehead"):
                continue
            key = "staff/" + "/".join(s.split("/")[1:4])
            lines = self.data["staff_lines"].get(key)
            if lines is None:
                continue
            used[key] = lines
            heads.append(dict(subject=s, box=tuple(g["box"]), pos=int(round(float(g["geo"]))), cls=c,
                              score=1.0, global_lines=lines))
        ctx = FH.FarHeadPage(self.gray_of(page), heads, self.boxes_by_page[page], used)
        self.pages_ctx[page] = ctx
        return ctx

    def adopt_for(self, page, shape_source):
        """The FarHeadPage for `page` with the shape the gather read it with."""
        ctx = self.page_ctx(page)
        if shape_source.startswith("page"):
            return ctx
        m = re.search(r"n=(\d+)", shape_source)
        k = int(m.group(1))
        # replay the pool: pages in gather order, samples appended, until the pool holds exactly k
        pages = sorted(self.boxes_by_page)
        pool = []
        for p in pages:
            pool.extend(self.page_ctx(p).samples)
            if len(pool) >= k:
                break
        if len(pool) != k:
            print(f"   (pool replay: wanted n={k}, got {len(pool)})")
        shape = FH.pooled_shape(pool)
        ctx.adopt(shape, shape_source)
        return ctx


def tick_y(lines, p):
    return P.y_of_pos(lines, p)


def brackets(img, x0, y0, x1, y1, col, L=14, t=2):
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(img, (cx, cy), (cx + dx * L, cy), col, t)
        cv2.line(img, (cx, cy), (cx, cy + dy * L), col, t)


def draw_tile(gray, win, lines, cap, box, read_pos, geo_pos, title, sub, num, drawn):
    x0, y0, x1, y1 = win
    crop = gray[y0:y1, x0:x1]
    img = cv2.cvtColor(cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
    H, W = img.shape[:2]
    row_of = lambda y: int(round((y - y0 + 0.5) * S - 0.5))
    col_of = lambda x: int(round((x - x0) * S))
    for y in lines:
        r = row_of(y)
        if 0 <= r < H:
            img[r, :] = BLUE
            drawn.append(("staff", y, r, title))
    for y in cap.get("rungs", []):
        r = row_of(y)
        if 0 <= r < H:
            for c in range(0, W, 12):
                img[r, c:c + 7] = GREEN
            drawn.append(("ledger", y, r, title))
    b = cap.get("box", box)
    brackets(img, col_of(b[0]), row_of(b[1]), col_of(b[2]), row_of(b[3]), ORANGE)
    for p, col, side, tag in ((read_pos, RED, 0, "tick_read"), (geo_pos, MAGENTA, 1, "tick_geo")):
        r = row_of(tick_y(lines, p))
        if 0 <= r < H:
            c0, c1 = (0, 26) if side == 0 else (W - 26, W)
            img[max(0, r - 1):r + 2, c0:c1] = col
            drawn.append((tag, tick_y(lines, p), r, title))
    img = cv2.copyMakeBorder(img, 22, 34, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(img, str(num), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(img, title, (34, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(img, sub[0], (4, img.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 200), 1, cv2.LINE_AA)
    cv2.putText(img, sub[1], (4, img.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 0, 150), 1, cv2.LINE_AA)
    return img


def main(d, seed=20261004):
    rng = random.Random(seed)
    tiles, drawn, rasters, wins = [], [], {}, {}
    meta = []
    replay_stats = {}
    for doc in DOCS:
        data = R.load(d, doc, "20261004-farhead-all")
        assert "boxes" in data, "re-run overnight_1004_extract.py on RUN 2 (needs the boxes field)"
        ins = R.IN_SAMPLE_PAGES[doc]
        cands = sorted(s for s, g in data["glyphs"].items()
                       if R.is_far(g) and "fh" in g and "box" in g and R.page_of(s) not in ins
                       and g.get("np", {}).get("outcome") == "decided"
                       and R.decided_pos(g) != R.geo_pos(g))
        print(f"{doc}: {len(cands)} out-of-sample far heads where RUN 2 decided a position different from geometry")
        rng.shuffle(cands)
        rep = DocReplay(doc, data)
        chosen, tried, bad = [], 0, 0
        for s in cands:
            if len(chosen) >= PER_DOC:
                break
            g = data["glyphs"][s]
            tried += 1
            page = R.page_of(s)
            ctx = rep.adopt_for(page, g["fh"]["shape_source"])
            key = "staff/" + "/".join(s.split("/")[1:4])
            gl = data["staff_lines"][key]
            cls = next(c for (ss, c, b) in rep.boxes_by_page[page] if ss == s)
            capd = {}
            r, cap, lines = P.capture_read(ctx, dict(subject=s, box=tuple(g["box"]), cls=cls), gl)
            if r["pos"] != R.decided_pos(g):
                bad += 1
                print(f"   replay MISMATCH {s}: record {R.decided_pos(g)} replay {r['pos']} -- not drawn")
                continue
            chosen.append((s, g, r, cap, lines, page))
        replay_stats[doc] = dict(tried=tried, mismatch=bad, drawn=len(chosen))
        print(f"   replay control: tried {tried}, did not reproduce the record {bad}, drawn {len(chosen)}")
        for (s, g, r, cap, lines, page) in chosen:
            b = tuple(g["box"])
            gray = rep.gray_of(page)
            cy = (b[1] + b[3]) / 2
            geo, pos = R.geo_pos(g), r["pos"]
            ys = [b[1], b[3], min(lines), max(lines)] + list(cap.get("rungs", [])) + [tick_y(lines, p) for p in (geo, pos)]
            y0, y1 = int(min(ys) - 22), int(max(ys) + 22)
            cx = (b[0] + b[2]) / 2
            win = (int(round(cx - 42)), y0, int(round(cx + 42)), y1)
            title = f"{doc.split('-')[0][:5]} p{page} {s.replace('glyph/', '')}"
            num = len(tiles) + 1
            rasters[title], wins[title] = gray, win
            sub = (f"reader {pos} ({g['fh']['box_source']})", f"geometry {geo}")
            tiles.append(draw_tile(gray, win, lines, cap, b, pos, geo, title, sub, num, drawn))
            meta.append(dict(n=num, doc=doc, subject=s, page=page, reader=pos, geometry=geo,
                             box_source=g["fh"]["box_source"], shape_source=g["fh"]["shape_source"]))
    off = P.verify(drawn, rasters, wins)
    for kind, v in off.items():
        v = np.array(v)
        print(f"re-measured {kind} overlays vs dark-band centre (overlay minus ink, px): n={len(v)} "
              f"median {np.median(v):+.2f} p10 {np.percentile(v, 10):+.2f} p90 {np.percentile(v, 90):+.2f}")
    assert abs(np.median(off["staff"])) <= 1.5, "staff overlay off the ink: sheet NOT saved"
    # layout: 4 across
    per = 4
    rows = []
    for i in range(0, len(tiles), per):
        grp = tiles[i:i + per]
        hmax = max(t.shape[0] for t in grp)
        cells = []
        for t in grp:
            cells.append(cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 3, 3, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
            cells.append(np.full((hmax, 10, 3), 90, np.uint8))
        rows.append(np.hstack(cells[:-1]))
    W = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 12, 0, W - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
    body = np.vstack(rows)
    caps = [("blue", BLUE, "the five staff lines of THIS staff, re-measured at the head's own x"),
            ("green dashes", GREEN, "the ledger lines the reader counted from (a dash row with no ink under it was implied, not seen)"),
            ("orange corners", ORANGE, "the head box the reader measured with"),
            ("red bar (left edge)", RED, "the position the reader read"),
            ("magenta bar (right edge)", MAGENTA, "the position the staff geometry gives")]
    top = np.full((len(caps) * 20 + 64, max(body.shape[1], 1100), 3), 255, np.uint8)
    cv2.putText(top, "Overnight 10-04 RUN 2: far heads on pages the rules were NOT written on, where reader and geometry disagree. "
                "No reference exists here: which tick sits on the head?", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(top, "Tiles 1-6 Litolff (p4-16), 7-12 Brahms (p2-26); seeded random draw (seed %d); 3x, cut at the gather's 600 dpi." % seed,
                (6, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 1, cv2.LINE_AA)
    for i, (nm, col, txt) in enumerate(caps):
        y = 62 + i * 20
        cv2.rectangle(top, (6, y - 11), (30, y + 3), col, -1)
        cv2.putText(top, f"{nm}: {txt}.", (38, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 1, cv2.LINE_AA)
    Wm = max(top.shape[1], body.shape[1])
    top = cv2.copyMakeBorder(top, 0, 0, 0, Wm - top.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    body = cv2.copyMakeBorder(body, 0, 0, 0, Wm - body.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    out = np.vstack([top, body])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), out)
    print("wrote", OUT, out.shape)
    (OUT.parent / "overnight_1004_sample.json").write_text(json.dumps(dict(seed=seed, tiles=meta, replay=replay_stats), indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261004)
