"""2306 r4 (measure first): on a saved record's rows, the page stems the r1 reader read (owner-stem claims) and how many END at a crossing with a
collinear vertical piece continuing past it, by kind of crossing (page_stems.join_runs over the record's own page strokes, heads from the page-head
rows, tremolo claims as slashes). Then the r4 reader on the same rows: stems, chord heads on one stem, Sean's p0 labels, tiles 6 / 7.
Usage: offline_runs.py REC.json [--pages ...] [--truth FILE]"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged import page_stems as PS

path = sys.argv[1]
pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")} if "--pages" in sys.argv else None
truth = sys.argv[sys.argv.index("--truth") + 1] if "--truth" in sys.argv else None
rec = load_record(path)["record"]
obs = rec["observations"]
pg = lambda s: int(s.split("/")[1])
gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in obs if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
oval = {}
for o in obs:
    d = o.get("detail") or {}
    if o["quantity"] == "claimed_area" and d.get("source") == "page_head_one" and d.get("oval"):
        for m in d.get("members") or ():
            oval[m] = d["oval"]
groups = collections.defaultdict(dict)
for o in obs:
    if o["quantity"] == "page_mark" and (o.get("detail") or {}).get("family") == "head":
        groups[pg(o["subject"])][o["subject"]] = o["detail"]["members"]
strokes = collections.defaultdict(list)
held = collections.defaultdict(dict)
stem_claims = collections.defaultdict(dict)
for o in obs:
    d = o.get("detail") or {}
    if o["quantity"] == "page_stroke" and o["value"] != "barline":
        strokes[pg(o["subject"])].append(dict(ord=d["ordinal"], kind=o["value"], box=tuple(d["bbox_page_px"]), sp=d.get("staff_space_local_px") or 30.0,
                                              th=d.get("thickness_spaces") or 0))
    if o["quantity"] == "claimed_area" and d.get("page_strokes") and o["value"] != "census":
        if d.get("owner") == "stem":
            stem_claims[pg(o["subject"])][int(o["value"])] = d
        elif d.get("owner") != "head" and d.get("standing", "READ") == "READ":
            for i in d["page_strokes"]:
                held[pg(o["subject"])].setdefault(int(i), d.get("owner"))
tot_r1 = collections.Counter()
tot_cen = collections.Counter()
res_by_page = {}
for p in sorted(strokes):
    if pages and p not in pages:
        continue
    heads = []
    for k, mem in groups[p].items():
        b = next((oval[m] for m in mem if m in oval), None) or next((gbox[m] for m in mem if m in gbox), None)
        if b:
            heads.append(dict(id=k, members=mem, box=tuple(b), sp=30.0, ink=any(m in oval for m in mem)))
    verts = [dict(ord=s["ord"], box=s["box"], sp=s["sp"]) for s in strokes[p] if s["kind"] == "vertical"]
    cross = [dict(ord=s["ord"], box=s["box"], kind=("slash" if held[p].get(s["ord"]) == "tremolo" else ("beam" if s["kind"] == "horizontal" and s["th"] >= 0.4 else s["kind"])))
             for s in strokes[p] if s["kind"] != "vertical"]
    runs, cen = PS.join_runs(verts, heads, cross, held[p])
    run_of = {m: r for r in runs for m in r["members"]}
    # r1 stems that end at a crossing with a collinear piece continuing: the r1 stem's stroke is in a run of 2+
    for o in stem_claims[p]:
        r = run_of.get(o)
        if r and len(r["members"]) > 1:
            tot_r1["r1 stem is part of a longer run"] += 1
            for k in set(r["joins"]):
                tot_r1["  crossing: " + k] += 1
        else:
            tot_r1["r1 stem whole"] += 1
    tot_cen.update(cen)
    res_by_page[p] = (PS.read(heads, verts, held[p], crossers=cross), heads, {v["ord"]: v for v in verts})
print("r1 stems (owner-stem claims):", dict(tot_r1))
print("join census over all vertical pieces:", dict(tot_cen))
cc = collections.Counter()
for p, (res, heads, vby) in res_by_page.items():
    for k, n in res["census"].items():
        if isinstance(n, int):
            cc[k] += n
print("r4 read:", {k: cc[k] for k in ("stems", "engraving_side", "no_stroke", "two_voices", "two_candidates", "stroke_read_both_ways", "second_on_partner_stem")})
for tile, (p, g) in {"6": (16, "glyph/16/0/9/6/1"), "7": (10, "glyph/10/1/0/14/6")}.items():
    if p not in res_by_page:
        continue
    res, heads, vby = res_by_page[p]
    hid = next((h["id"] for h in heads if g in h["members"]), None)
    r = res["heads"].get(hid)
    st = res["stems"].get(r["stroke"]) if r and r["stroke"] is not None else None
    print("tile", tile, g, r and r["how"], st and (st["box"], st["members"], [k for k in st["heads"]]))
if "--tile6" in sys.argv:
    res, heads, vby = res_by_page[16]
    for h in heads:
        b = h["box"]
        if 1230 <= b[0] <= 1290 and 1620 <= b[1] <= 1710:
            r = res["heads"][h["id"]]
            print(h["id"], h["members"], [round(v) for v in b], h["ink"], r["how"], [(c["direction"], c["stroke"], c["gap"], c["reach"]) for c in r["candidates"]])
if truth and 0 in res_by_page:
    T = json.load(open(truth))
    ts = [b["rect"] for b in T["boxes"] if b["cls"] == "stem"]
    res, heads, vby = res_by_page[0]
    mine = [s["box"] for s in res["stems"].values()]

    def hit(t, b):
        tx, bx = (t[0] + t[2]) / 2.0, (b[0] + b[2]) / 2.0
        ov = min(t[3], b[3]) - max(t[1], b[1])
        return abs(tx - bx) <= 8 and ov >= 0.5 * min(t[3] - t[1], b[3] - b[1])

    def full(t, b):     # the stem box covers 90% of Sean's stem's height
        return abs((t[0] + t[2]) / 2.0 - (b[0] + b[2]) / 2.0) <= 8 and (min(t[3], b[3]) - max(t[1], b[1])) >= 0.9 * (t[3] - t[1])
    found = sum(1 for t in ts if any(hit(t, b) for b in mine))
    whole = sum(1 for t in ts if any(full(t, b) for b in mine))
    right = sum(1 for b in mine if any(hit(t, b) for t in ts))
    print("Brahms p0 vs Sean's %d stems: found %d (whole length %d), not his %d, missed %d" % (len(ts), found, whole, len(mine) - right, len(ts) - found))
