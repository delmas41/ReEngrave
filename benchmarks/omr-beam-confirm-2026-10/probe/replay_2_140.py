"""ROADMAP 2.140 -- re-decide (STAGED ADJUDICATE -> INFER, `pipeline.decide`) the PAGES of a saved record, flag OFF vs ON, from a STREAMED
subset of its rows (never the whole record). GATHER rows are the record's own, so the new reader's rows are ADDED here: for every
CV stem of the given pages the page-raster measurement of `gather.beam_runs_at_stem_end` (the product function) is converted to the
row `gather_beam_stem_levels` would file (thickness/reach in staff spaces are scale-free; the run y's are page px, unused by ADJUDICATE).
THIS IS THE READER ON THE 600 dpi PAGE RASTER, NOT ON THE CANONICAL CELL RASTER (that needs a re-gather).
    python3 replay_2_140.py lit|brah RECORD PAGE[,PAGE..] OUT.json
Writes {glyph: {"off": [outcome, beats, beam_levels, reason], "on": [...], "rec": [the record's own], "detail": the ON verdict's beam_stem_levels}}
for every glyph whose standing duration differs OFF vs ON, plus control counts (OFF vs the record's own standing verdicts).
"""
import json, os, sys, pathlib, collections
import numpy as np
from PIL import Image
sys.path.insert(0, ".")
from tools.omr.staged import judged as J
from tools.omr.staged.record import Q, Log
from tools.omr.staged.review import rerun as RR
from tools.omr.staged.gather import beam_runs_at_stem_end, local_line_thickness
from tools.omr.preprocessing import render_page
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"brah": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
       "lit": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
mov, rec_path, pages_arg, out = sys.argv[1:5]
pages = {int(x) for x in pages_arg.split(",")}
rec = pathlib.Path(rec_path)


def keep(s):
    p = s.split("/")
    if p[0] == "document":
        return True
    return len(p) > 1 and p[1].isdigit() and int(p[1]) in pages


obs = [o for o in J.iter_array(rec, "observations") if keep(o["subject"])]
absn = [o for o in J.iter_array(rec, "abstentions") if keep(o["subject"])]
recd = {"observations": obs, "abstentions": absn}
print(len(obs), "obs", len(absn), "abs kept")
stdur = {}
for v in J.iter_verdicts(rec):
    if v["quantity"] == "duration" and keep(v["subject"]):
        val = v.get("value") if isinstance(v.get("value"), dict) else {}
        stdur[v["subject"]] = [v["outcome"], val.get("beats"), val.get("beam_levels"), v["reason"]]


def stem_rows(obs, page):
    """(cell, stem row, page-frame stem box) via each cell's detector-box scale."""
    scale, stems, lines, cellsub = {}, [], {}, {}
    for o in obs:
        p = o["subject"].split("/")
        if p[0] == "glyph" and o["quantity"] == "glyph_box" and int(p[1]) == page:
            cell = tuple(int(x) for x in p[1:5]); v = o["value"]; bp = (o["detail"] or {}).get("bbox_page_px")
            if bp and v[3] > 0 and cell not in scale:
                sc = (bp[2] - bp[0]) / v[3]; scale[cell] = (sc, bp[0] - v[1] * sc, bp[1] - v[2] * sc)
        elif p[0] == "staff" and o["quantity"] == "staff_lines":
            lines[tuple(int(x) for x in p[1:4])] = o["value"]
        elif p[0] == "cell" and o["quantity"] == "stem" and o["reader"] == "cv_lines" and int(p[1]) == page:
            stems.append(o)
    return scale, stems, lines


added = []
lpx = {}
nxt = 10 ** 9
for page in sorted(pages):
    img = (np.asarray(Image.fromarray(render_page(PDF[mov], page, dpi=600).rgb).convert("L")) < 128)
    scale, stems, lines = stem_rows(obs, page)
    for o in stems:
        cell = tuple(int(x) for x in o["subject"].split("/")[1:5]); sc = scale.get(cell); st = lines.get(cell[:3])
        if sc is None or st is None:
            continue
        x, y, w, h = o["value"][:4]
        px, py, pw, ph = sc[1] + x * sc[0], sc[2] + y * sc[0], w * sc[0], h * sc[0]
        sp = float(np.mean(np.diff(st)))
        ends = {}
        lk = (page, cell[:3], int(px) // 800)
        if lk not in lpx:
            x0s = int(sc[1]); lpx[lk] = local_line_thickness(img, list(st), max(0, int(px) - 600), int(px) + 600, sp) or 0.0
        for end, tip in (("top", py), ("bottom", py + ph)):
            ends[end] = beam_runs_at_stem_end(img, px + pw / 2.0, tip, end, sp, list(st), lpx[lk])
        best = max(len(e[s]) for e in ends.values() for s in ("left", "right"))
        nxt += 1
        added.append({"id": "obs:%d" % nxt, "subject": o["subject"], "quantity": Q.BEAM_STEM_LEVELS, "value": best, "reader": "cv_beam_levels",
                      "frame": o["frame"], "score": None, "detail": {"stem_row_id": o["id"], "ends": ends, "space_px": sp}, "basis": []})
print(len(added), "stem-level rows built from the page raster")


def rebuild(r):
    """`review.rerun.rebuild_gather` with the ids inside `detail` (`beam_row_id`, `stem_row_id`, ...) remapped too. The restricted
    row set renumbers the log, and rebuild_gather remaps only `basis`: without this every row that names another row by id points
    at nothing (the first replay of this probe failed its own control that way: 193 of 1,434 differed)."""
    from tools.omr.staged.record import Subject
    log = Log()
    rows = [(x, "obs") for x in r.get("observations") or ()] + [(x, "abs") for x in r.get("abstentions") or ()]
    rows.sort(key=lambda t: RR._row_no(t[0]["id"]))
    idmap = {}

    def fix(v):
        if isinstance(v, str) and v in idmap:
            return idmap[v]
        if isinstance(v, dict):
            return {k: fix(x) for k, x in v.items()}
        if isinstance(v, list):
            return [fix(x) for x in v]
        return v
    for x, kind in rows:
        sub = Subject.from_key(x["subject"])
        detail = fix(dict(x.get("detail") or {}))
        if kind == "obs":
            basis = tuple(idmap[b] for b in (x.get("basis") or ()) if b in idmap)
            new = log.observe(sub, x["quantity"], x["value"], reader=x["reader"], frame=x["frame"], score=x.get("score"),
                              derived_from=basis, **detail)
        else:
            new = log.abstain(sub, x["quantity"], reader=x["reader"], frame=x["frame"], reason=x["reason"], **detail)
        idmap[x["id"]] = new.id
    return log


def decide(on):
    r = dict(recd)
    r["observations"] = obs + added
    os.environ["OMR_BEAM_STEM_LEVELS"] = "1" if on else "0"
    log = rebuild(r)
    RR.run_stages(log)
    m = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] == Q.DURATION:
            val = v.get("value") if isinstance(v.get("value"), dict) else {}
            m[v["subject"]] = [v["outcome"], val.get("beats"), val.get("beam_levels"), v["reason"], (v.get("detail") or {}).get("beam_stem_levels")]
    return m


off, on = decide(False), decide(True)
ctrl = collections.Counter()
for g, v in stdur.items():
    o = off.get(g)
    ctrl["same" if o and o[:3] == v[:3] else "differ"] += 1
chg = {g: {"off": off[g][:4], "on": on.get(g, [None])[:4], "rec": stdur.get(g), "detail": (on.get(g) or [None] * 5)[4]}
       for g in off if on.get(g, [None])[:3] != off[g][:3]}
json.dump({"control_off_vs_record": dict(ctrl), "changed": chg}, open(out, "w"), indent=0, default=str)
print("CONTROL OFF vs the record's standing durations:", dict(ctrl))
print(len(chg), "standing verdicts change ON vs OFF:", collections.Counter((v["off"][0], v["on"][0]) for v in chg.values()))
