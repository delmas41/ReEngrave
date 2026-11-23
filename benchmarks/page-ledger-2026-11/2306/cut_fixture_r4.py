"""2306 r4 real-case fixtures: around Sean's r1 tiles 6 (Litolff p16 glyph/16/0/9/6/1) and 7 (Litolff p10 glyph/10/1/0/14/6), and the first real
`heads_both_sides` refusal on Brahms (two voices end to end) -- heads (page-head rows), vertical pieces, the other strokes as crossers (tremolo
claims = slash), held strokes. Usage: cut_fixture_r4.py LIT_REC BRA_REC OUT.json"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged import page_stems as PS


def page_parts(rec, p):
    obs = rec["observations"]
    pg = lambda s: int(s.split("/")[1])
    gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in obs if o["quantity"] == "glyph_box" and pg(o["subject"]) == p and (o.get("detail") or {}).get("bbox_page_px")}
    oval = {}
    held = {}
    for o in obs:
        d = o.get("detail") or {}
        if o["quantity"] == "claimed_area" and pg(o["subject"]) == p:
            if d.get("source") == "page_head_one" and d.get("oval"):
                for m in d.get("members") or ():
                    oval[m] = d["oval"]
            elif d.get("page_strokes") and d.get("owner") not in ("head", "stem") and d.get("standing", "READ") == "READ" and o["value"] != "census":
                for i in d["page_strokes"]:
                    held.setdefault(int(i), d.get("owner"))
    heads = []
    for o in obs:
        if o["quantity"] == "page_mark" and pg(o["subject"]) == p and (o.get("detail") or {}).get("family") == "head":
            mem = o["detail"]["members"]
            b = next((oval[m] for m in mem if m in oval), None) or next((gbox[m] for m in mem if m in gbox), None)
            if b:
                heads.append(dict(id=o["subject"], members=mem, box=[float(v) for v in b], sp=30.0, ink=any(m in oval for m in mem)))
    verts, cross = [], []
    for o in obs:
        if o["quantity"] == "page_stroke" and pg(o["subject"]) == p and o["value"] != "barline":
            d = o["detail"]
            b = [float(v) for v in d["bbox_page_px"]]
            if o["value"] == "vertical":
                verts.append(dict(ord=d["ordinal"], box=b, sp=float(d.get("staff_space_local_px") or 30.0)))
            else:
                k = "slash" if held.get(d["ordinal"]) == "tremolo" else ("beam" if o["value"] == "horizontal" and (d.get("thickness_spaces") or 0) >= 0.4 else o["value"])
                cross.append(dict(ord=d["ordinal"], box=b, kind=k))
    return heads, verts, cross, held


def cut(parts, x0, y0, x1, y1):
    heads, verts, cross, held = parts
    m = lambda b: b[0] <= x1 and b[2] >= x0 and b[1] <= y1 and b[3] >= y0
    vs = [v for v in verts if m(v["box"])]
    return dict(heads=[h for h in heads if m(h["box"])], verticals=vs, crossers=[c for c in cross if m(c["box"])],
                held={str(k): v for k, v in held.items() if any(int(k) == x["ord"] for x in vs)}, window=[x0, y0, x1, y1])


lit = load_record(sys.argv[1])["record"]
bra = load_record(sys.argv[2])["record"]
out = {"about": "ROADMAP 2.306 r4 real-case fixtures, cut from the 2306 gathers (main 718c83964 + r1, OMR_PAGE_STEMS=1) by benchmarks/page-ledger-2026-11/2306/"
                "cut_fixture_r4.py: page px at 600 dpi. tile6 / tile7 = Sean's r1 tiles 6 and 7 ('all stems. Tile 6 and 7 stop a bit short. 6 is interrupted "
                "by a trem slash and 7 is a long stem on a chord'); divisi = the first real pair of collinear vertical pieces whose gap holds heads on both "
                "sides (two voices end to end)."}
out["tile6"] = dict(page=16, glyph="glyph/16/0/9/6/1", **cut(page_parts(lit, 16), 1180, 1560, 1340, 1760))
out["tile7"] = dict(page=10, glyph="glyph/10/1/0/14/6", **cut(page_parts(lit, 10), 2480, 1990, 2640, 2290))
for p in (0, 4, 5, 8, 12, 14, 19, 25):
    parts = page_parts(bra, p)
    pairs = []
    PS.join_runs([dict(v, box=tuple(v["box"])) for v in parts[1]], [dict(h, box=tuple(h["box"])) for h in parts[0]],
                 [dict(c, box=tuple(c["box"])) for c in parts[2]], {int(k): v for k, v in parts[3].items()}, pairs)
    hit = [t for t in pairs if t[2] == "!heads_both_sides"]
    if hit:
        a, b, _k = hit[0]
        vb = {v["ord"]: v["box"] for v in parts[1]}
        x0 = min(vb[a][0], vb[b][0]) - 80
        out["divisi"] = dict(page=p, pair=[a, b], **cut(parts, x0, vb[a][1] - 20, x0 + 170, vb[b][3] + 20))
        break
json.dump(out, open(sys.argv[3], "w"), indent=0)
print({k: (len(v["heads"]), len(v["verticals"]), len(v["crossers"])) for k, v in out.items() if isinstance(v, dict)}, out.get("divisi", {}).get("pair"))
