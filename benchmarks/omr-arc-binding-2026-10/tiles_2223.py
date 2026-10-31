"""ROADMAP 2.223: 12 blind tiles for page-wide binding -- arcs and hairpins mixed.

    python3 benchmarks/omr-arc-binding-2026-10/tiles_2223.py OUT_DIR PLATE:DUMP.json [PLATE:DUMP.json ...] [--seed N]

DUMP is a re-adjudicated slice (both flags ON) holding `wedge_box` / `system_arc` / `staff_lines` rows, the notehead boxes and the
`wedge_anchor` / `arc_kind` verdicts. A candidate is a mark the ON binding bound at BOTH ends (`bound_page_wide` hairpins; arcs whose
`arc_kind` carries a `page_binding` with a kind). Six hairpins and six arcs are drawn at random (seed stated in key.json; fewer of one
kind -> more of the other). Each tile shows ONE staff (the mark's own, 3 spaces above and below its lines, hairpin included) with two
thin orange boxes at the mark's two ENDS (its tips) and nothing else drawn; the key (OUTSIDE the tile folder) names the notes the
binding chose. Sean answers "which note does this mark start on and which does it end on?".
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

ORANGE = (255, 140, 0)
README = """# One question per tile

Each picture is one staff of a score page with TWO thin orange boxes on it and nothing else drawn. The boxes sit at the two ends of
ONE mark -- a hairpin (crescendo / diminuendo wedge) or an arc (tie or slur). They only say which mark to look at.

**For every tile: which note does this mark start on, and which note does it end on?**

Say it however is easiest (for example "starts on the first quarter of the bar, ends on the half note in the next bar"). If the mark
starts or ends where there is no note (under a held note, at a rest, off the edge of the system), say that. If the boxed ink is not a
hairpin or an arc, say what it is.

Answer by tile number.
"""


def load(dump):
    d = json.loads(pathlib.Path(dump).read_text())
    heads = {o["subject"]: o["detail"]["bbox_page_px"] for o in d["heads"]
             if (o.get("detail") or {}).get("category") == "notehead" and o["detail"].get("bbox_page_px")}
    lines = {o["subject"]: o["value"] for o in d["obs"] if o["quantity"] == "staff_lines"}
    return d, heads, lines


def candidates(plate, d, heads):
    out = []
    wb = {o["subject"]: o for o in d["obs"] if o["quantity"] == "wedge_box"}
    for v in d["verdicts"]:
        if v["quantity"] == "wedge_anchor" and v["outcome"] == "decided" and v["reason"] == "bound_page_wide":
            o = wb.get(v["subject"])
            b = o["detail"]["bbox_page_px"]
            st = "/".join(["staff"] + v["subject"].split("/")[1:4])
            ym = (b[1] + b[3]) / 2.0
            out.append(dict(plate=plate, kind="hairpin", mark=v["subject"], what=str(o["value"]), staff=st,
                            ends=[[b[0], ym], [b[2], ym]], start=v["value"][0], stop=v["value"][1],
                            start_how=v["detail"].get("start_how"), stop_how=v["detail"].get("stop_how"),
                            span=[b[0], b[1], b[2], b[3]]))
    seen = set()
    for v in d["verdicts"]:
        if v["quantity"] != "arc_kind" or v["outcome"] != "decided":
            continue
        pb = (v.get("detail") or {}).get("page_binding") or {}
        if pb.get("kind") not in ("tie", "slur") or pb.get("curve") in seen:
            continue
        seen.add(pb["curve"])
        sa = [o for o in d["obs"] if o["quantity"] == "system_arc" and o["subject"] == pb["curve"]]
        if not sa:
            continue
        dt = sa[0]["detail"]
        xl, yl, xr, yr = dt["x_left_page"], dt["y_left_page"], dt["x_right_page"], dt["y_right_page"]
        out.append(dict(plate=plate, kind="arc", mark=pb["curve"], what=pb["kind"], staff=pb["home"],
                        ends=[[xl, yl], [xr, yr]], start=pb["start"], stop=pb["stop"], start_how="at", stop_how="at",
                        span=[min(xl, xr), min(yl, yr), max(xl, xr), max(yl, yr)]))
    return out


def main(argv):
    out = pathlib.Path(argv[0])
    seed = 2223
    args = [a for a in argv[1:]]
    if "--seed" in args:
        i = args.index("--seed")
        seed = int(args[i + 1])
        del args[i:i + 2]
    from tools.omr.preprocessing import render_page
    from tools.omr.staged import lane_report as L
    pool, ctx = [], {}
    for spec in args:
        plate, dump = spec.split(":", 1)
        d, heads, lines = load(dump)
        ctx[plate] = (heads, lines)
        pool += candidates(plate, d, heads)
    rng = random.Random(seed)
    hp = [c for c in pool if c["kind"] == "hairpin"]
    ar = [c for c in pool if c["kind"] == "arc"]
    rng.shuffle(hp)
    rng.shuffle(ar)
    nh = min(6, len(hp))
    pick = hp[:nh] + ar[:12 - nh]
    rng.shuffle(pick)
    tiles = out / "tiles"
    tiles.mkdir(parents=True, exist_ok=True)
    pages = {}
    keys = []
    thumbs = []
    for n, c in enumerate(pick, start=1):
        heads, lines = ctx[c["plate"]]
        pg = int(c["mark"].split("/")[1])
        if (c["plate"], pg) not in pages:
            pages[(c["plate"], pg)] = Image.fromarray(render_page(str(L.LIB / L.PLATES[c["plate"]]["pdf"]), pg, dpi=600).rgb).convert("RGB")
        im = pages[(c["plate"], pg)]
        ln = lines[c["staff"]]
        sp = (ln[-1] - ln[0]) / 4.0
        xs = [c["span"][0], c["span"][2]] + [heads[k][0] for k in (c["start"], c["stop"]) if k in heads] + \
             [heads[k][2] for k in (c["start"], c["stop"]) if k in heads]
        y0 = min(ln[0] - 3 * sp, c["span"][1] - sp)
        y1 = max(ln[-1] + 3 * sp, c["span"][3] + sp)
        box = (int(max(0, min(xs) - 6 * sp)), int(max(0, y0)), int(min(im.width, max(xs) + 6 * sp)), int(min(im.height, y1)))
        t = im.crop(box).copy()
        dr = ImageDraw.Draw(t)
        r = 0.45 * sp
        for ex, ey in c["ends"]:
            dr.rectangle([ex - box[0] - r, ey - box[1] - r, ex - box[0] + r, ey - box[1] + r], outline=ORANGE, width=2)
        t.save(tiles / ("tile_%02d.png" % n))
        thumbs.append(t)
        keys.append(dict(tile=n, crop_origin=[box[0], box[1]], page=pg, **{k: c[k] for k in (
            "plate", "kind", "what", "mark", "staff", "start", "stop", "start_how", "stop_how", "ends")},
            start_cell=int(c["start"].split("/")[4]), stop_cell=int(c["stop"].split("/")[4]),
            start_head_box=heads.get(c["start"]), stop_head_box=heads.get(c["stop"])))
    W = 900
    rows = []
    for i, t in enumerate(thumbs):
        s = t.resize((W, max(1, int(t.height * W / t.width))))
        lab = Image.new("RGB", (W, s.height + 40), "white")
        lab.paste(s, (0, 40))
        ImageDraw.Draw(lab).text((10, 10), "tile %d" % (i + 1), fill=(0, 0, 0))
        rows.append(lab)
    sheet = Image.new("RGB", (2 * W, sum(r.height for r in rows[::2]) + 10), "white")
    y = 0
    for i in range(0, len(rows), 2):
        sheet.paste(rows[i], (0, y))
        if i + 1 < len(rows):
            sheet.paste(rows[i + 1], (W, y))
        y += max(r.height for r in rows[i:i + 2])
    sheet.save(tiles / "sheet.png")
    (tiles / "README.md").write_text(README)
    (out / "key.json").write_text(json.dumps(dict(seed=seed, pool=dict(hairpins=len(hp), arcs=len(ar)),
                                                  question="which note does this mark start on and which does it end on?",
                                                  tiles=keys), indent=1))
    print("tiles", len(pick), "pool", len(hp), "hairpins", len(ar), "arcs")


if __name__ == "__main__":
    main(sys.argv[1:])
