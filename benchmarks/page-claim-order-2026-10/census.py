"""ROADMAP 2.221 milestones 0, 0b: the READ-ONLY census of which ink a page-wide claim order could change.

    python3 benchmarks/page-claim-order-2026-10/census.py extract   # stream the two saved records once -> scratch pickle
    python3 benchmarks/page-claim-order-2026-10/census.py count     # rasters + counts -> census.json, tiles pool
    python3 benchmarks/page-claim-order-2026-10/census.py tiles     # up to 12 blind tiles -> out/print/2.221-census/

STAGED throughout; it changes no flag, no record, no tool. It reads the saved gathered records of the frozen sample
(ROADMAP 2.202f, ON arm = beams ON = main's defaults) and the MusicXML their EXPORT wrote, and the PDF pages. One process
at a time.

What is counted (per plate; sample pages only, context pages are loaded never counted):
  populations   P_boxes = every detector notehead box on a sample page
                P_live  = the boxes ADJUDICATE still calls a notehead (notehead_is_not_a_notehead == False)
                P_written = the head boxes that EXPORT wrote as a note, matched by PLACE (page + glyph key + box)
  regions       (a) interior barline columns: the cell edge between two cells of one staff, kept only where the
                    unerased page shows a vertical ink run over the staff's full span (the barline itself)
                (b) accepted direction words (Q.DIRECTION_WORD boxes: the lexicon gate already passed them) and the
                    letters of a spelled dynamic (Q.DYNAMIC_LETTER rows that the decided `dynamic` verdict used)
                (c) bracket / brace: the detector's `brace` boxes; bracket_reader.strokes_at_left_edge on the page (a
                    reader with NO consumer today, run here as a measurement); and, labelled as a PROXY, the
                    system's left-edge region (staff start - 9 spaces .. staff start + 0.5 space)
                (d) READ clef/key/meter claims: Q.CLAIMED_AREA unit=area, standing READ (the owner's own box excluded)
  the number    share = dark pixels of the head box that lie in the region / dark pixels of the head box, staff-line rows
                taken out of both (a line is see-through, plan §3). "ink on it" = share >= 0.25; 0.5 and 0.9 also printed.
  0b            accidental / rest / dot boxes that intersect a WRITTEN head box: the dark pixels of the intersection are
                the only ink whose owner the order (heads first or heads last) can change.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import pickle
import random
import sys

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR            # noqa: E402
from tools.omr.staged.judged import iter_array            # noqa: E402

WORK = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/2-202-beams-cause-1f79a5/out/lane-report/2.202f/work")
SCRATCH = pathlib.Path("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad")
CACHE = SCRATCH / "census-extract.pkl"
OUT_JSON = HERE / "census.json"
POOL_JSON = SCRATCH / "census-pool.json"
PRINT_DIR = ROOT / "out" / "print" / "2.221-census"
SAMPLE = json.loads((ROOT / "benchmarks" / "lane-report" / "sample.json").read_text())
QUANTS = ("glyph_box", "cell_box", "staff_lines", "staff_extent", "staff_spacing", "staff_skew", "direction_word",
          "dynamic_letter", "claimed_area", "letter_look_cover")
VQ = ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "accidental_is_not_an_accidental", "dot_role", "dynamic")


def pages_of(plate):
    return set(SAMPLE["plates"][plate]["pages"])


# ───────────────────────────── 1. extract (stream the saved record once) ─────────────────────────────

def extract():
    data = {}
    for plate in ("litolff", "brahms"):
        keep = pages_of(plate)
        rec = WORK / ("%s.on.gathered.record.json" % plate)
        rows = collections.defaultdict(list)
        for o in iter_array(rec, "observations"):
            q = o.get("quantity")
            if q not in QUANTS:
                continue
            pg = LR.page_of(o.get("subject"))
            if pg not in keep:
                continue
            d = o.get("detail") or {}
            rows[q].append(dict(id=o["id"], subject=o["subject"], value=o["value"], reader=o.get("reader"),
                                detail={k: d[k] for k in ("bbox_page_px", "category", "letter", "unit", "standing", "owner",
                                                          "owner_glyph", "cls", "group_box_page", "status", "thickness_px",
                                                          "cell") if k in d}))
        ver = collections.defaultdict(list)
        for v in iter_array(rec, "verdicts"):
            if v.get("quantity") in VQ and LR.page_of(v.get("subject")) in keep:
                ver[v["quantity"]].append(dict(subject=v["subject"], outcome=v.get("outcome"), value=v.get("value"),
                                               reason=v.get("reason"), used=v.get("used"), decider=v.get("decider")))
        sym = json.loads((WORK / ("%s.on.symbols.json" % plate)).read_text())
        data[plate] = dict(rows=dict(rows), verdicts=dict(ver), hosts=sym["hosts"], loose=sym["loose"],
                           flags=sym["flags"], notes_not_written=sym["notes_not_written"])
        print(plate, {k: len(v) for k, v in rows.items()}, {k: len(v) for k, v in ver.items()}, len(sym["hosts"]), flush=True)
    CACHE.write_bytes(pickle.dumps(data))


# ───────────────────────────── 2. geometry helpers ─────────────────────────────

class Page:
    """One page's binary raster (the pipeline's own binarisation, deskewed frame), with the staff-line rows taken out."""

    def __init__(self, plate, pg, lines_y, thick):
        from tools.omr.preprocessing import render_page
        pi = render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600)
        b = pi.binary
        ink = (b > 0) if b.mean() < 128 else (b == 0)       # ink = the minority colour
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

    def n(self, x0, y0, x1, y1):
        """dark non-line pixels in the box."""
        x0, y0 = max(0, int(round(x0))), max(0, int(round(y0)))
        x1, y1 = min(self.W, int(round(x1))), min(self.H, int(round(y1)))
        if x1 <= x0 or y1 <= y0:
            return 0
        I = self.I
        return int(I[y1, x1] - I[y0, x1] - I[y1, x0] + I[y0, x0])


def inter(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def key_parts(s):
    p = s.split("/")
    return p[0], [int(x) for x in p[1:]]


def band_for_edge(P, x, top, bottom, sp):
    """The barline at cell edge x: the contiguous columns within +-1 space whose NON-LINE rows over the staff's full
    span are >= 90% dark. None if the unerased page shows no vertical rule there (a header edge, a stem)."""
    xa, xb = int(x - sp), int(x + sp) + 1
    ys = np.arange(int(top), int(bottom) + 1)
    ys = ys[~P.line_rows[ys]]
    if len(ys) < 4 or xa < 0 or xb > P.W:
        return None
    cov = P.ink_gross[ys, xa:xb].mean(axis=0)
    i = int(np.argmax(cov))
    if cov[i] < 0.9:
        return None
    l = r = i
    while l > 0 and cov[l - 1] >= 0.8:
        l -= 1
    while r < len(cov) - 1 and cov[r + 1] >= 0.8:
        r += 1
    if (r - l + 1) > 0.8 * sp:          # wider than a barline: a stem + head column, not a rule
        return None
    return (xa + l - 1, int(top), xa + r + 2, int(bottom))


# ───────────────────────────── 3. count ─────────────────────────────

class Share:
    def __init__(self):
        self.shares = []          # (share, item)

    def add(self, share, item):
        self.shares.append((share, item))

    def tally(self):
        s = [x for x, _ in self.shares]
        return {"any_ink": sum(x > 0 for x in s), ">=0.10": sum(x >= 0.10 for x in s), ">=0.25": sum(x >= 0.25 for x in s),
                ">=0.50": sum(x >= 0.50 for x in s), ">=0.90": sum(x >= 0.90 for x in s)}


def count():
    data = pickle.loads(CACHE.read_bytes())
    result, pool = {}, []
    for plate, D in data.items():
        rows, ver = D["rows"], D["verdicts"]
        sp_of, lines_of, ext_of, thick_of = {}, {}, {}, {}
        for r in rows["staff_lines"]:
            lines_of[r["subject"]] = r["value"]
        for r in rows["staff_spacing"]:
            sp_of[r["subject"]] = float(r["value"])
        for r in rows["staff_extent"]:
            ext_of[r["subject"]] = r["value"]
        for r in rows.get("staff_skew", []):
            t = r["detail"].get("thickness_px") or [4]
            thick_of[r["subject"]] = float(np.mean(t))
        cells = collections.defaultdict(dict)
        for r in rows["cell_box"]:
            _, (pg, sy, st, c) = key_parts(r["subject"])
            cells[(pg, sy, st)][c] = r["value"]
        boxes = {}
        for r in rows["glyph_box"]:
            b = r["detail"].get("bbox_page_px")
            if b:
                boxes[r["subject"]] = dict(page=LR.page_of(r["subject"]), box=[float(x) for x in b], cls=r["value"][0])
        heads = {k: v for k, v in boxes.items() if v["cls"].startswith("notehead")}
        notehead_verdict = {v["subject"]: v for v in ver["notehead_is_not_a_notehead"]}
        live = {k for k in heads if notehead_verdict.get(k, {}).get("value") is False}
        refusals = collections.Counter((v["value"], v["reason"]) for v in ver["notehead_is_not_a_notehead"])
        # written notes, matched by PLACE: same page, same glyph key, and the host's box is the glyph's box
        written, unmatched = {}, 0
        for h in D["hosts"]:
            if h["kind"] != "note":
                continue
            g = heads.get(h["rg"])
            if g and g["page"] == h["page"] and inter(g["box"], h["box"]) and \
                    (lambda i: (i[2] - i[0]) * (i[3] - i[1]) / ((g["box"][2] - g["box"][0]) * (g["box"][3] - g["box"][1])))(inter(g["box"], h["box"])) > 0.8:
                written[h["rg"]] = h
            else:
                unmatched += 1
        NH = collections.Counter(h["rg"] for h in D["hosts"] if h["kind"] == "note")
        # regions that need no raster
        words = [dict(id=r["id"], page=LR.page_of(r["subject"]), box=r["detail"]["bbox_page_px"], text=r["value"],
                      category=r["detail"].get("category"), reader=r["reader"]) for r in rows["direction_word"]]
        letters = {r["id"]: dict(page=LR.page_of(r["subject"]), box=r["detail"]["bbox_page_px"], letter=r["detail"].get("letter"),
                                 key=r["subject"]) for r in rows["dynamic_letter"]}
        spelled_ids = set()
        for v in ver["dynamic"]:
            if v["value"] and v["reason"] == "spelled":
                spelled_ids.update(i for i in (v["used"] or []) if i in letters)
        spelled = [dict(letters[i], id=i) for i in spelled_ids]
        other_letters = [dict(letters[i], id=i) for i in letters if i not in spelled_ids]
        braces = [dict(page=v["page"], box=v["box"], key=k) for k, v in boxes.items() if v["cls"] == "brace"]
        claims = [dict(page=LR.page_of(r["subject"]), box=r["value"], owner=r["detail"].get("owner"),
                       owner_glyph=r["detail"].get("owner_glyph"), cls=r["detail"].get("cls"))
                  for r in rows["claimed_area"] if r["detail"].get("unit") == "area" and r["detail"].get("standing") == "READ"
                  and isinstance(r["value"], list) and len(r["value"]) == 4]
        oth = {k: v for k, v in boxes.items() if v["cls"].startswith(("accidental", "rest", "augmentationDot"))}
        oth_ver = {}
        for q, ky in (("accidental_is_not_an_accidental", "accidental"), ("rest_is_not_a_rest", "rest")):
            for v in ver[q]:
                oth_ver[v["subject"]] = v["value"] is False
        for v in ver["dot_role"]:
            oth_ver[v["subject"]] = v["outcome"] == "decided"

        res = {"populations": dict(P_boxes=len(heads), P_live=len(live), P_written=len(written), host_notes_unmatched=unmatched,
                                   notes_in_file=sum(h["kind"] == "note" for h in D["hosts"])),
               "notehead_refusals_by_reason": {"%s|%s" % k: n for k, n in refusals.most_common()},
               "n_words": len(words), "n_spelled_letters": len(spelled), "n_other_dynamic_letters": len(other_letters),
               "n_braces": len(braces), "n_read_claims": len(claims),
               "claim_owners": {"%s|%s" % k: n for k, n in collections.Counter((c["owner"], c["cls"]) for c in claims).items()}}
        S = collections.defaultdict(lambda: {"boxes": Share(), "live": Share(), "written": Share()})
        zero_ink = collections.Counter()
        bands_info = dict(edges=0, with_barline=0)
        pair0b = []
        by_page = collections.defaultdict(list)
        for k, v in heads.items():
            by_page[v["page"]].append(k)

        for pg in sorted(pages_of(plate)):
            staves = sorted({s for s in lines_of if int(s.split("/")[1]) == pg})
            all_lines = [y for s in staves for y in lines_of[s]]
            thick = float(np.mean([thick_of.get(s, 4.0) for s in staves])) if staves else 4.0
            P = Page(plate, pg, all_lines, thick)
            print(plate, pg, "raster", P.W, P.H, "ink %.3f" % P.ink_gross.mean(), flush=True)
            # (a) barline bands
            bands = []
            for s in staves:
                _, (_, sy, st) = key_parts(s)
                cs = cells.get((pg, sy, st), {})
                ys = lines_of[s]
                sp = sp_of[s]
                for c in sorted(cs):
                    if c + 1 in cs:
                        bands_info["edges"] += 1
                        b = band_for_edge(P, cs[c][2], ys[0], ys[-1], sp)
                        if b:
                            bands_info["with_barline"] += 1
                            bands.append(dict(box=b, staff=s, edge=cs[c][2], cell=c))
            # (c) bracket_reader strokes + left-edge proxy, per system
            br_boxes, left_boxes = [], []
            systems = collections.defaultdict(list)
            for s in staves:
                _, (_, sy, st) = key_parts(s)
                systems[sy].append(s)
            from tools.omr.bracket_reader import strokes_at_left_edge

            class St:
                pass
            for sy, ss in systems.items():
                objs = []
                for s in ss:
                    o = St(); y = lines_of[s]
                    o.top_y, o.bottom_y, o.line_spacing_px, o.x_start = int(y[0]), int(y[-1]), sp_of[s], ext_of[s][0]
                    objs.append(o)
                objs.sort(key=lambda o: o.top_y)
                spc = float(np.median([o.line_spacing_px for o in objs]))
                xs = float(np.median([o.x_start for o in objs]))
                left_boxes.append(dict(box=[xs - 9 * spc, objs[0].top_y - 3 * spc, xs + 0.5 * spc, objs[-1].bottom_y + 3 * spc], system=sy))
                try:
                    strokes, geom = strokes_at_left_edge(P.ink_gross.astype(np.uint8) * 255, objs)
                except Exception as e:           # a reader failing is a count, not a zero
                    zero_ink["bracket_reader_error:%s" % type(e).__name__] += 1
                    continue
                for st_ in strokes:
                    br_boxes.append(dict(box=[st_.x_left, st_.y_top, st_.x_right + 1, st_.y_bot], system=sy,
                                         height_sp=st_.height_spacings))
            zero_ink["bracket_reader_strokes_p%d" % pg] = len(br_boxes)

            def measure(group, regions, kind, excl=None):
                """For each head box of this page against each region: share of its net ink inside the region."""
                for k in by_page[pg]:
                    hb = heads[k]["box"]
                    tot = P.n(*hb)
                    if tot <= 0:
                        continue
                    best, bestreg = 0.0, None
                    for rg in regions:
                        if rg.get("page", pg) != pg:
                            continue
                        if excl and excl(k, rg):
                            continue
                        i = inter(hb, rg["box"])
                        if not i:
                            continue
                        sh = P.n(*i) / tot
                        if sh > best:
                            best, bestreg = sh, rg
                    S[(group, kind)]["boxes"].add(best, dict(key=k, page=pg, box=hb, region=bestreg and bestreg["box"]))
                    if k in live:
                        S[(group, kind)]["live"].add(best, dict(key=k, page=pg, box=hb, region=bestreg and bestreg["box"]))
                    if k in written:
                        S[(group, kind)]["written"].add(best, dict(key=k, page=pg, box=hb, region=bestreg and bestreg["box"],
                                                                    host=written[k]["measure"], onset=written[k]["onset"], n_hosts=NH[k]))

            measure("a_barline", [dict(r, page=pg) for r in bands], "interior barline column")
            sh = lambda rs, dx: [dict(r, box=[r["box"][0] + dx, r["box"][1], r["box"][2] + dx, r["box"][3]]) for r in rs]
            measure("a_barline_CONTROL_shifted_3sp", sh([dict(r, page=pg) for r in bands], 3 * float(np.median([sp_of[s_] for s_ in staves]))), "CONTROL: barline columns moved 3 spaces right (must be ~0)")
            measure("b_dynamic_CONTROL_shifted_4sp", sh([w for w in spelled if w["page"] == pg], 4 * float(np.median([sp_of[s_] for s_ in staves]))), "CONTROL: spelled-letter boxes moved 4 spaces right (must be ~0)")
            measure("b_word", [w for w in words if w["page"] == pg], "accepted direction word")
            measure("b_dynamic", [w for w in spelled if w["page"] == pg], "spelled dynamic letters")
            measure("b_dynamic_other", [w for w in other_letters if w["page"] == pg], "dynamic-letter box not used by a spelled dynamic (info)")
            measure("c_brace_box", [b for b in braces if b["page"] == pg], "detector brace box")
            measure("c_bracket_reader", br_boxes, "bracket_reader left-edge rule strokes")
            measure("c_left_edge_proxy", left_boxes, "system left-edge region (PROXY)")
            measure("d_read_claim", [c for c in claims if c["page"] == pg], "READ clef/key/meter claim area",
                    excl=lambda k, rg: rg.get("owner_glyph") == k)
            # 0b
            wk = [k for k in by_page[pg] if k in written]
            for ox, ov in oth.items():
                if ov["page"] != pg:
                    continue
                cls = "dot" if ov["cls"] == "augmentationDot" else ("rest" if ov["cls"].startswith("rest") else "accidental")
                for k in wk:
                    i = inter(heads[k]["box"], ov["box"])
                    if not i:
                        continue
                    shared = P.n(*i)
                    pair0b.append(dict(plate=plate, page=pg, kind=cls, other=ox, other_cls=ov["cls"], other_box=ov["box"],
                                       other_live=oth_ver.get(ox), head=k, head_box=heads[k]["box"], shared_px=shared,
                                       head_ink=P.n(*heads[k]["box"]), other_ink=P.n(*ov["box"])))
            # pool for tiles
            del P

        out = {}
        for (g, kind), s in sorted(S.items()):
            out[g] = dict(region=kind, boxes=s["boxes"].tally(), live=s["live"].tally(), written=s["written"].tally())
            for sub in ("boxes", "live", "written"):
                for share, item in s[sub].shares:
                    if share >= 0.25:
                        pool.append(dict(plate=plate, group=g, pop=sub, share=round(share, 3), **item))
        res["groups"] = out
        res["barline_bands"] = bands_info
        res["extra"] = dict(zero_ink)
        # 0b summary
        def sum0b(sel, thr_head=0.0):
            rs = [p for p in pair0b if sel(p)]
            return dict(pairs=len(rs), pairs_with_shared_ink=sum(p["shared_px"] > 0 for p in rs),
                        pairs_shared_ge5px=sum(p["shared_px"] >= 5 for p in rs),
                        pairs_shared_ge_10pct_of_head=sum(p["shared_px"] >= 0.10 * max(1, p["head_ink"]) for p in rs),
                        pairs_shared_ge_25pct_of_other=sum(p["shared_px"] >= 0.25 * max(1, p["other_ink"]) for p in rs),
                        shared_px_total=sum(p["shared_px"] for p in rs),
                        written_heads_touched=len({p["head"] for p in rs if p["shared_px"] > 0}))
        res["zero_b"] = {kind: dict(all_boxes=sum0b(lambda p, kind=kind: p["kind"] == kind),
                                    live_boxes=sum0b(lambda p, kind=kind: p["kind"] == kind and p["other_live"]))
                         for kind in ("accidental", "rest", "dot")}
        res["zero_b_pairs"] = pair0b
        result[plate] = res
    OUT_JSON.write_text(json.dumps({p: {k: v for k, v in r.items() if k != "zero_b_pairs"} for p, r in result.items()}, indent=1, default=str))
    POOL_JSON.write_text(json.dumps(dict(pool=pool, pairs={p: r["zero_b_pairs"] for p, r in result.items()}), default=str))
    print(json.dumps({p: {k: v for k, v in r.items() if k not in ("zero_b_pairs",)} for p, r in result.items()}, indent=1, default=str))


if __name__ == "__main__":
    {"extract": extract, "count": count}[sys.argv[1]]()
