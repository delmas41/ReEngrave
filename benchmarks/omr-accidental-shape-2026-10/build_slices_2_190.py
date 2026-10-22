"""ROADMAP 2.190 -- build a lane_report slice set that holds what a LIVE gather with `OMR_ONE_INK_ONE_MARK=1 OMR_ACCIDENTAL_SHAPE=1` would have filed,
without running the detector: the stored production GATHER rows of the 20261020-night slices (the 2.186 FINDINGS checked merge-on-stored == live on
1,537 of 1,537 cells), the 2.186 merge applied to them (`one_ink.plan`), and the shape measurement taken by the SAME gather function
(`gather._accidental_shape_detail`) on the cell rasters `pipeline.prepare_pages` cuts and staff-erases (the same call gather's own pages go through).
STAGED GATHER rows, replayed.  usage: build_slices_2_190.py OUTROOT   (writes OUTROOT/<plate>/{observations,abstentions,verdicts}.jsonl)"""
import collections, json, os, pathlib, sys
from types import SimpleNamespace
from tools.omr.staged import lane_report as LR, one_ink as OI, accidental_shape as AS, gather as G
from tools.omr.staged.pipeline import prepare_pages

OUT = pathlib.Path(sys.argv[1])
os.environ[AS.SHAPE_ENV] = "1"


def merged(obs):
    cells = collections.defaultdict(list)
    for o in obs:
        if o["quantity"] == "glyph_box" and o["reader"] == "detector" and isinstance(o["value"], list):
            cells["/".join(o["subject"].split("/")[:5])].append(o)
    win, winner_of, rivals_of = {}, {}, {}
    for cell, bs in cells.items():
        bs.sort(key=lambda o: int(o["subject"].split("/")[5]))
        p = OI.plan([(o["value"][0], *o["value"][1:5], o["score"] or 0.0) for o in bs])
        for i, info in p.items():
            win[bs[i]["subject"]] = OI.detail_of(info, bs[i]["value"][0], bs[i]["score"] or 0.0)
            rivals_of[bs[i]["subject"]] = [(r["class"], r["conf"]) for r in info["rivals"]]
            for j in info["absorbed"]:
                winner_of[bs[j]["subject"]] = bs[i]["subject"]
    out = []
    for o in obs:
        s = o["subject"]
        if o["quantity"] in ("glyph_box", "accidental_staff_position") and (s in win or s in winner_of) and \
                (o["quantity"] == "accidental_staff_position" or o["reader"] == "detector"):
            o = dict(o); o["detail"] = dict(o.get("detail") or {})
            if s in win:
                o["detail"].update(win[s])
            else:
                o["detail"]["one_ink_absorbed_by_index" if o["quantity"] == "glyph_box" else "one_ink_absorbed"] = True if o["quantity"] != "glyph_box" else winner_of[s]
        out.append(o)
    return out, rivals_of, set(winner_of)


sample = LR.load_sample()
for plate in ("litolff", "brahms"):
    src = LR.slice_dir(plate, sample["record_tag"])
    pages = LR.loaded_pages(sample, plate)
    obs = [json.loads(l) for l in open(src / "observations.jsonl")]
    obs, rivals_of, absorbed = merged(obs)
    box = {o["subject"]: o for o in obs if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "accidental"}
    cellbox = {}
    for o in obs:
        if o["quantity"] == "cell_box":
            cellbox[tuple(o["subject"].split("/")[1:5])] = o["value"]
    pos = {o["subject"]: o for o in obs if o["quantity"] == "accidental_staff_position"}
    bycell = collections.defaultdict(list)
    for s in pos:
        bycell[tuple(s.split("/")[1:5])].append(s)
    prep = prepare_pages(str(LR.LIB / LR.PLATES[plate]["pdf"]), pages)
    n = collections.Counter()
    for pws, cells in prep:
        for c in cells:
            bb = getattr(c, "bbox_page_px", None)
            if not bb:
                continue
            key = next((k for k, v in cellbox.items() if int(k[0]) == c.page_index and all(abs(a - b) < 1.5 for a, b in zip(v, bb))), None)
            if key is None or key not in bycell:
                continue
            grid = G._cell_grid(c)
            if grid is None:
                continue
            top_y, half = grid
            for s in bycell[key]:
                if s in absorbed:
                    continue
                b = box[s]["value"]
                d = SimpleNamespace(smufl_name=b[0], x_canonical=b[1], y_canonical=b[2], width_canonical=b[3], height_canonical=b[4],
                                    y_center=b[2] + b[4] / 2, confidence=box[s]["score"] or 0.0, one_ink_absorbed_by=None,
                                    one_ink_rivals=tuple(rivals_of.get(s, ())))
                extra = G._accidental_shape_detail(c, d, top_y, half)
                pos[s]["detail"].update(extra)
                n["merged" if s in rivals_of else "single"] += 1
                n["shape_" + extra["shape"]["shape"]] += 1
    print(plate, dict(n), flush=True)
    d = OUT / plate
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "observations.jsonl", "w") as fh:
        for o in obs:
            if o["quantity"] == "accidental_staff_position":
                o = pos[o["subject"]]
            fh.write(json.dumps(o, default=str) + "\n")
    for k in ("abstentions", "verdicts"):
        (d / (k + ".jsonl")).write_text((src / (k + ".jsonl")).read_text())
