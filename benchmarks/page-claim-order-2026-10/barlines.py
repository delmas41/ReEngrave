"""ROADMAP 2.221, ahead of milestone 2: why did the census count 2 / 0 written notes on a barline column when Sean found
5 barlines among 12 m1 'quarters'?  READ-ONLY: saved records + exported symbols + the PDF pages. No gather, no replay.

    python3 benchmarks/page-claim-order-2026-10/barlines.py measure   # steps 1-4 -> barlines.json
    python3 benchmarks/page-claim-order-2026-10/barlines.py tiles     # up to 12 blind tiles -> out/print/2.221-barlines/

Steps (the numbers land in FINDINGS.md under "Barlines the census missed"):
  1  the 5 barline tiles of out/print/2.220-m1-notonehead: box, verdict in the saved record, nearest census cell edge,
     whether the census's barline band exists there, census share and DIRECT share, any exported note near it
  2  DIRECT rule measure (no measure_extractor): per staff, columns whose non-line rows over the whole staff are
     >= 90% dark = a rule (width <= 0.8 sp). A head 'sits on a rule' when >= 50% of its net ink is in the rule columns.
     CONTROL: the same rule columns moved +3 sp and -3 sp (must be ~0).
  3  the floor: width / height in staff spaces of the 5 boxes (code citation in FINDINGS)
  4  box-size picture of the WRITTEN notes (width x height in the staff's own spaces)
"""
from __future__ import annotations

import collections
import json
import pathlib
import pickle
import random
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import census as C                                   # noqa: E402  (Page, inter, key_parts, band_for_edge)
from tools.omr.staged import lane_report as LR       # noqa: E402

SCRATCH = C.SCRATCH
M1_KEY = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a05b0ad517dce3/out/print/2.220-m1-notonehead/key.json")
M1_ANS = M1_KEY.parent / "answers.json"
M1_DATA = {"litolff": SCRATCH / "lit.json", "brahms": SCRATCH / "bra.json"}   # 2.220 m1 mini-record extract (boxes, verdicts)
M1_PAGES = {"litolff": (4, 6), "brahms": (5, 14)}
OUT = HERE / "barlines.json"
POOL = SCRATCH / "barlines-pool.json"
PRINT = ROOT / "out" / "print" / "2.221-barlines"
BARLINE_TILES = (2, 4, 5, 11, 12)
SEED = 22211


def get_binary(plate, pg):
    """The pipeline's own binarisation (the same one census.Page uses); cached next to the other scratch rasters."""
    f = SCRATCH / ("page_%s_%d.npy" % (plate, pg))
    if f.exists():
        return np.load(f)
    from tools.omr.preprocessing import render_page
    b = render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600).binary
    np.save(f, b)
    return b


class RasterPage(C.Page):
    """census.Page but from a binary we already hold (no second render)."""

    def __init__(self, b, lines_y, thick):
        import cv2
        ink = (b > 0) if b.mean() < 128 else (b == 0)
        self.H, self.W = ink.shape
        self.ink_gross = ink
        self.line_rows = np.zeros(self.H, bool)
        for y in lines_y:
            h = int(round(thick / 2.0)) + 1
            self.line_rows[max(0, int(round(y)) - h):int(round(y)) + h + 1] = True
        net = ink.copy()
        net[self.line_rows, :] = False
        self.net = net
        self.I = cv2.integral(net.astype(np.uint8))


def rules_of_staff(P, x_lo, x_hi, top, bottom, sp):
    """Direct barline finder: columns (inside the staff's x extent) whose non-line rows over the full staff span are >= 90%
    dark; contiguous runs (grown to >= 80%) no wider than 0.8 sp are rules. Independent of measure_extractor."""
    ys = np.arange(int(top), int(bottom) + 1)
    ys = ys[~P.line_rows[ys]]
    if len(ys) < 4:
        return []
    x_lo, x_hi = max(0, int(x_lo)), min(P.W, int(x_hi) + 1)
    cov = P.ink_gross[ys, x_lo:x_hi].mean(axis=0)
    out, i, n = [], 0, len(cov)
    while i < n:
        if cov[i] >= 0.9:
            l = r = i
            while l > 0 and cov[l - 1] >= 0.8:
                l -= 1
            while r < n - 1 and cov[r + 1] >= 0.8:
                r += 1
            if (r - l + 1) <= 0.8 * sp:
                out.append((x_lo + l - 1, x_lo + r + 2))      # half-open, +-1 px fringe like census.band_for_edge
            i = r + 1
        else:
            i += 1
    return out


def staff_of(key):
    p = key.split("/")
    return "staff/%s/%s/%s" % (p[1], p[2], p[3])


def load_inputs():
    data = pickle.loads(C.CACHE.read_bytes())
    m1 = {pl: json.loads(f.read_text()) for pl, f in M1_DATA.items()}
    return data, m1


def build_plate(plate, D, m1d):
    """Per-plate tables the steps share."""
    rows, ver = D["rows"], D["verdicts"]
    T = dict(lines={r["subject"]: r["value"] for r in rows["staff_lines"]},
             sp={r["subject"]: float(r["value"]) for r in rows["staff_spacing"]},
             ext={r["subject"]: r["value"] for r in rows["staff_extent"]},
             thick={}, cells=collections.defaultdict(dict))
    for r in rows.get("staff_skew", []):
        t = r["detail"].get("thickness_px") or [4]
        T["thick"][r["subject"]] = float(np.mean(t))
    for r in rows["cell_box"]:
        _, (pg, sy, st, c) = C.key_parts(r["subject"])
        T["cells"][(pg, sy, st)][c] = r["value"]
    boxes = {}
    for r in rows["glyph_box"]:
        b = r["detail"].get("bbox_page_px")
        if b:
            boxes[r["subject"]] = dict(page=LR.page_of(r["subject"]), box=[float(x) for x in b], cls=r["value"][0])
    heads = {k: v for k, v in boxes.items() if v["cls"].startswith("notehead")}
    nv = {v["subject"]: v for v in ver["notehead_is_not_a_notehead"]}
    live = {k for k in heads if nv.get(k, {}).get("value") is False}
    written, hosts_by_rg = {}, collections.defaultdict(list)
    for h in D["hosts"]:
        if h["kind"] != "note":
            continue
        hosts_by_rg[h["rg"]].append(h)
        g = heads.get(h["rg"])
        if g and g["page"] == h["page"]:
            i = C.inter(g["box"], h["box"])
            if i and (i[2] - i[0]) * (i[3] - i[1]) / ((g["box"][2] - g["box"][0]) * (g["box"][3] - g["box"][1])) > 0.8:
                written[h["rg"]] = h
    # the m1 population: boxes with a DECIDED duration whose written value is known (what the m1 sample was drawn from)
    dur = {}
    for s, v in m1d["ver"].items():
        d = v.get("duration") or {}
        if d.get("o") == "decided" and isinstance(d.get("v"), dict) and d["v"].get("written") is not None:
            dur[s] = d["v"]["written"]
    return dict(T=T, boxes=boxes, heads=heads, nv=nv, live=live, written=written, hosts_by_rg=hosts_by_rg, dur=dur,
                hosts=[h for h in D["hosts"] if h["kind"] == "note"])


def run_plate(plate, D, m1d, pool):
    S = build_plate(plate, D, m1d)
    T, heads, nv, live, written, dur = S["T"], S["heads"], S["nv"], S["live"], S["written"], S["dur"]
    pages = sorted(C.pages_of(plate))
    res = dict(rows=[], pages=pages)
    by_page = collections.defaultdict(list)
    for k, v in heads.items():
        by_page[v["page"]].append(k)
    ctl_hits = collections.Counter()
    detail = {}
    for pg in pages:
        staves = sorted({s for s in T["lines"] if int(s.split("/")[1]) == pg})
        all_lines = [y for s in staves for y in T["lines"][s]]
        thick = float(np.mean([T["thick"].get(s, 4.0) for s in staves])) if staves else 4.0
        P = RasterPage(get_binary(plate, pg), all_lines, thick)
        rules = {}
        for s in staves:
            ys = T["lines"][s]
            rules[s] = rules_of_staff(P, T["ext"][s][0], T["ext"][s][1], ys[0], ys[-1], T["sp"][s])
        print(plate, pg, "staves", len(staves), "rules", sum(len(v) for v in rules.values()), flush=True)
        for k in by_page[pg]:
            hb = heads[k]["box"]
            s = staff_of(k)
            if s not in T["sp"]:
                continue
            sp = T["sp"][s]
            tot = P.n(*hb)
            ys = T["lines"][s]
            # rule columns of this staff, and of its neighbours (a box can belong to a staff above/below)
            share = {}
            for tag, dx in (("real", 0.0), ("ctl_plus3", 3 * sp), ("ctl_minus3", -3 * sp)):
                best, bestx = 0.0, None
                for (xa, xb) in rules.get(s, []):
                    if tot <= 0:
                        break
                    ra = [xa + dx, hb[1], xb + dx, hb[3]]
                    i = C.inter(hb, ra)
                    if i:
                        sh = P.n(*i) / tot
                        if sh > best:
                            best, bestx = sh, (xa + dx + xb + dx) / 2.0
                share[tag] = (best, bestx)
            w_sp, h_sp = (hb[2] - hb[0]) / sp, (hb[3] - hb[1]) / sp
            # nearest census cell edge on this staff
            _, (_, sy, st) = C.key_parts(s)
            cs = T["cells"].get((pg, sy, st), {})
            edges = sorted({cs[c][2] for c in cs if c + 1 in cs})
            cx = (hb[0] + hb[2]) / 2.0
            ne = min(edges, key=lambda e: abs(e - cx)) if edges else None
            cb = C.band_for_edge(P, ne, ys[0], ys[-1], sp) if ne is not None else None
            census_share = None
            if cb:
                i = C.inter(hb, [cb[0], cb[1], cb[2], cb[3]])
                census_share = (P.n(*i) / tot) if (i and tot > 0) else 0.0
            nr = min(((abs((a + b) / 2.0 - cx), (a + b) / 2.0) for a, b in rules.get(s, [])), default=(None, None))
            row = dict(key=k, plate=plate, page=pg, cls=heads[k]["cls"], box=hb, w_sp=round(w_sp, 3), h_sp=round(h_sp, 3), sp=round(sp, 2),
                       ink=tot, direct=round(share["real"][0], 3), direct_x=share["real"][1],
                       ctl_plus3=round(share["ctl_plus3"][0], 3), ctl_minus3=round(share["ctl_minus3"][0], 3),
                       nearest_edge=ne, edge_dist_px=None if ne is None else round(abs(ne - cx), 1),
                       edge_dist_sp=None if ne is None else round(abs(ne - cx) / sp, 2),
                       edge_has_band=bool(cb), census_share=None if census_share is None else round(census_share, 3),
                       nearest_rule_dist_px=None if nr[0] is None else round(nr[0], 1),
                       refusal="%s|%s" % (nv.get(k, {}).get("value"), nv.get(k, {}).get("reason")),
                       live=k in live, written=k in written, dur=dur.get(k), m1_page=(pg in M1_PAGES[plate]))
            res["rows"].append(row)
        del P
    return res, S


def pop_stats(rows, pred, thr=0.5):
    sel = [r for r in rows if pred(r)]
    return dict(n=len(sel),
                direct_ge=sum(r["direct"] >= thr for r in sel),
                ctl_plus3_ge=sum(r["ctl_plus3"] >= thr for r in sel),
                ctl_minus3_ge=sum(r["ctl_minus3"] >= thr for r in sel),
                direct_ge_025=sum(r["direct"] >= 0.25 for r in sel),
                ctl_plus3_ge_025=sum(r["ctl_plus3"] >= 0.25 for r in sel),
                ctl_minus3_ge_025=sum(r["ctl_minus3"] >= 0.25 for r in sel),
                census_ge=sum((r["census_share"] or 0) >= thr for r in sel))


def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def measure():
    data, m1 = load_inputs()
    out = {}
    keyt = json.loads(M1_KEY.read_text())
    for plate in ("litolff", "brahms"):
        res, S = run_plate(plate, data[plate], m1[plate], None)
        rows = res["rows"]
        out[plate] = dict(rows=rows)
        r = {}
        # step 2: populations
        r["written_all_16_pages"] = pop_stats(rows, lambda x: x["written"])
        r["written_m1_pages"] = pop_stats(rows, lambda x: x["written"] and x["m1_page"])
        r["live_all"] = pop_stats(rows, lambda x: x["live"])
        r["all_boxes_all"] = pop_stats(rows, lambda x: True)
        r["dur_written_m1_pages"] = pop_stats(rows, lambda x: x["dur"] is not None and x["m1_page"])
        r["dur_written_m1_pages_refused"] = pop_stats(rows, lambda x: x["dur"] is not None and x["m1_page"] and not x["live"])
        r["dur_written_m1_pages_notrefused"] = pop_stats(rows, lambda x: x["dur"] is not None and x["m1_page"] and x["live"])
        # step 4: sizes of written notes
        w = [x["w_sp"] for x in rows if x["written"]]
        h = [x["h_sp"] for x in rows if x["written"]]
        sizes = dict(n=len(w), w_pct={q: pct(w, q) for q in (1, 5, 25, 50, 75, 95, 99)}, h_pct={q: pct(h, q) for q in (1, 5, 25, 50, 75, 95, 99)},
                     w_max=pct(w, 100), h_max=pct(h, 100), w_min=pct(w, 0), h_min=pct(h, 0))
        n = max(1, len(w))
        sizes["w_out_1.0_1.9"] = dict(under=sum(v < 1.0 for v in w), over=sum(v > 1.9 for v in w))
        sizes["h_out_0.9_1.8"] = dict(under=sum(v < 0.9 for v in h), over=sum(v > 1.8 for v in h))
        sizes["either_out"] = sum((a < 1.0 or a > 1.9 or b < 0.9 or b > 1.8) for a, b in zip(w, h))
        sizes["either_out_share"] = round(sizes["either_out"] / n, 4)
        bycls = collections.defaultdict(list)
        for x in rows:
            if x["written"]:
                bycls[x["cls"]].append((x["w_sp"], x["h_sp"]))
        sizes["by_class"] = {c: dict(n=len(v), w_med=pct([a for a, _ in v], 50), h_med=pct([b for _, b in v], 50),
                                     w_out=sum((a < 1.0 or a > 1.9) for a, _ in v), h_out=sum((b < 0.9 or b > 1.8) for _, b in v))
                             for c, v in sorted(bycls.items(), key=lambda kv: -len(kv[1]))}
        # written notes whose width is under the 1.0 floor (the floor is on noteheadBlack* only)
        sizes["written_under_floor_by_class"] = dict(collections.Counter(x["cls"] for x in rows if x["written"] and x["w_sp"] < 1.0))
        # the distribution for the m1 sample pages only
        w1 = [x["w_sp"] for x in rows if x["written"] and x["m1_page"]]
        h1 = [x["h_sp"] for x in rows if x["written"] and x["m1_page"]]
        sizes["m1_pages"] = dict(n=len(w1), w_out=sum((a < 1.0 or a > 1.9) for a in w1), h_out=sum((b < 0.9 or b > 1.8) for b in h1),
                                 either_out=sum((a < 1.0 or a > 1.9 or b < 0.9 or b > 1.8) for a, b in zip(w1, h1)))
        r["sizes_written"] = sizes
        out[plate]["summary"] = r
        # the exported-note hosts: any whose box sits mostly on a rule
        out[plate]["written_on_rule_rows"] = [x for x in rows if x["written"] and x["direct"] >= 0.5]
        out[plate]["hosts_for_rows"] = None
    # step 1: the five tiles
    tiles = {}
    for t in keyt:
        if t["tile"] not in BARLINE_TILES:
            continue
        plate = t["plate"]
        row = next(x for x in out[plate]["rows"] if x["key"] == t["rg"])
        # exported notes whose box meets the tile's box (+-1 sp)
        sp = row["sp"]
        hb = row["box"]
        near = []
        for h in data[plate]["hosts"]:
            if h["kind"] != "note" or h["page"] != t["page"]:
                continue
            bb = h["box"]
            if bb[2] >= hb[0] - sp and bb[0] <= hb[2] + sp and bb[3] >= hb[1] - 0.5 * sp and bb[1] <= hb[3] + 0.5 * sp:
                near.append(dict(rg=h["rg"], box=[round(v, 1) for v in bb], type=h["type"], onset=h["onset"], measure=h["measure"]))
        row = dict(row, tile=t["tile"], exported_notes_within_1sp=near, m1_noh=t["noh"], m1_trimmed=t["trimmed"])
        tiles[t["tile"]] = row
    out["tiles"] = tiles
    # sizes of all 12 m1 tiles
    twelve = []
    for t in keyt:
        row = next(x for x in out[t["plate"]]["rows"] if x["key"] == t["rg"])
        twelve.append(dict(tile=t["tile"], plate=t["plate"], page=t["page"], w_sp=row["w_sp"], h_sp=row["h_sp"], refusal=row["refusal"],
                           written=row["written"], dur=row["dur"], direct=row["direct"], ans=json.loads(M1_ANS.read_text())["tiles"][t["tile"] - 1]["answer"]))
    out["m1_twelve"] = twelve
    # light output: drop per-row tables for the json that lands in the tree
    slim = {pl: {k: v for k, v in out[pl].items() if k not in ("rows", "hosts_for_rows")} for pl in ("litolff", "brahms")}
    slim["tiles"], slim["m1_twelve"] = out["tiles"], out["m1_twelve"]
    OUT.write_text(json.dumps(slim, indent=1, default=str))
    POOL.write_text(json.dumps({pl: out[pl]["rows"] for pl in ("litolff", "brahms")}, default=str))
    print(json.dumps({pl: slim[pl]["summary"] for pl in ("litolff", "brahms")}, indent=1, default=str))
    print(json.dumps(slim["tiles"], indent=1, default=str))
    print(json.dumps(slim["m1_twelve"], indent=1, default=str))


def tiles():
    pool = json.loads(POOL.read_text())
    rng = random.Random(SEED)
    items = []
    cands = []
    for pl in ("litolff", "brahms"):
        for x in pool[pl]:
            if x["written"] and x["direct"] >= 0.5 and not ((x["census_share"] or 0) >= 0.5):
                cands.append(x)
    print("candidates (written, direct>=0.5, census did not count):", len(cands))
    rng.shuffle(cands)
    for c in cands:
        it = dict(plate=c["plate"], page=c["page"], box=c["box"], rg=c["key"], role="case", direct=c["direct"], census_share=c["census_share"],
                  w_sp=c["w_sp"], h_sp=c["h_sp"])
        if any(LR._same_ink(it, y) for y in items):
            continue
        items.append(it)
        if len(items) >= 12:
            break
    rng.shuffle(items)
    PRINT.mkdir(parents=True, exist_ok=True)
    print(LR.cut_tiles(items, PRINT))
    (PRINT / "tiles" / "README.md").write_text(
        "# 2.221 barline tiles (read-only; nothing about any change)\n\n"
        "Each picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn.\n\n"
        "**What the orange box means.** It is a place where our reader WROTE a note into the exported file. "
        "It says nothing about whether we were right.\n\n"
        "**Question, for every tile:** what is inside the orange box? A real note head, or a barline "
        "(or part of a barline, or a stem, or something else)? If a note head and a barline share the box, say which.\n\n"
        "Answer by tile number. Our key is in `../key.json`, outside this folder, and is not for the reader.\n")
    print("wrote", PRINT)


if __name__ == "__main__":
    {"measure": measure, "tiles": tiles}[sys.argv[1]]()
