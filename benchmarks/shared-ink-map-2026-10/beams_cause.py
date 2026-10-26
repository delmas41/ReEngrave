"""ROADMAP 2.202 cause study (read-only; no gather): WHY did `OMR_BEAMS_FROM_STROKES` change a head main had right?

usage: beams_cause.py REPORT_OUT_DIR OUT.json            (REPORT_OUT_DIR = the milestone lane_report out dir holding work/<plate>.on.{mini-record,gathered.record}.json)

For every duration head of the ON arm whose `beams_from_strokes.settled` is `stroke_candidate` (the map counted MORE levels than the readers) or
`disagree_narrowed` (FEWER), rebuilds the cell's `Q.STROKE` views from the gathered ON record (streamed with ijson, only the cells needed), reads the tip
exactly as `rhythm._beams_from_strokes` did (`beam_strokes.roles`, `tip_reading`) and files the head under ONE cause by the measured fields of the strokes
at its stem tip. The cause list is the one the nine judged heads and a 20 + 20 crop look gave (FINDINGS 2.202 section 5b):

  more levels (stroke_candidate):
    head_end_blob   a counted `beam` stroke whose centre is >= 1.5 sp INWARD of the tip (the head end of a short stem): a notehead / chord cluster / ledger line /
                    accidental or dynamic letter, "horizontal" because it is wider than tall, touching this stem and one more vertical
    at_tip          every counted stroke is within 1.5 sp of the tip (a real second beam level, or a sharp's crossbar: the crops decide)
  fewer levels (disagree_narrowed):
    thin_remnant    a horizontal / curve stroke across >= 2 stems touches this stem at the tip, thickness < 0.30 sp (a beam on a staff line, erased to a sliver)
    thin_near_cut   the same, 0.30 <= thickness < 0.50 sp
    fused_double    the beam stroke that touches this stem is >= 1.0 sp thick (two levels fused into one slab) and the map counts one level
    join_missing    a beam-role stroke stands within 1.2 sp of the tip but does not touch this head's stem stroke
    no_stroke       nothing horizontal touches the stem near the tip
    other
  hook (flag_levels > 0): `hook_slur` when the "hook" stroke lies inside a detector slur / tie glyph box, else `hook_other`.
"""
import collections
import json
import pathlib
import sys

import ijson

sys.path.insert(0, ".")
from tools.omr.staged import beam_strokes as BS

BASE = 375000          # record.STROKE_GLYPH_BASE
HEAD_END_DY = 1.5


def views_of(rows):
    out = []
    for r in rows:
        if r["quantity"] != "stroke":
            continue
        d = r["detail"]
        out.append(BS.StrokeView(
            ordinal=int(r["subject"].rsplit("/", 1)[1]) - BASE, kind=r["value"], box=tuple(float(v) for v in d["stroke_box"][:4]),
            length=float(d.get("length_spaces") or 0), thickness=float(d.get("thickness_spaces") or 0), sagitta=d.get("sagitta_spaces"),
            angle=float(d.get("angle_deg") or 0), touches=tuple((int(a), float(b)) for a, b in d.get("touches") or ()),
            space_px=float(d.get("staff_space_local_px") or 0), row_id=r["id"], profile=tuple(d.get("profile_sixteenths") or ())))
    return out


def heads_of(mini):
    out = {}
    for v in mini["verdicts"]:
        if v["quantity"] != "duration" or v.get("supersedes"):
            continue
        d = (v.get("detail") or {}).get("beams_from_strokes")
        if d and (d["settled"] in ("stroke_candidate", "disagree_narrowed") or d.get("flag_levels")):
            out[v["subject"]] = dict(settled=d["settled"], before=d["before"], after=d["after"], tip=d.get("tip"), flag_levels=d.get("flag_levels"),
                                     side=v["detail"].get("beam_side"))
    return out


def classify(h, views, rows):
    side = h["side"]
    if not h.get("tip") or side not in ("up", "down"):
        return "no_tip", {}
    by = {v.ordinal: v for v in views}
    stem = by.get(h["tip"]["stem"])
    if stem is None:
        return "no_stem", {}
    role = BS.roles(views)
    tip = BS.tip_reading(views, role, stem, side)
    sp = stem.space_px
    tip_y = stem.box[1] if side == "up" else stem.box[1] + stem.box[3]

    def inward(v):
        c = v.box[1] + v.box[3] / 2.0
        return ((c - tip_y) if side == "up" else (tip_y - c)) / sp

    info = dict(stem_len=round(stem.length, 1), counted=[(o, round(inward(by[o]), 2), round(by[o].thickness, 2)) for o in tip["beams"]])
    if h["flag_levels"]:
        hk = [by[o] for o in tip["hooks"]]
        arcs = [r["value"][0] for r in rows if r["quantity"] == "glyph_box" and r["value"][0] in ("slur", "tie")
                and any(not (v.box[0] > r["value"][1] + r["value"][3] or v.box[0] + v.box[2] < r["value"][1]
                             or v.box[1] > r["value"][2] + r["value"][4] or v.box[1] + v.box[3] < r["value"][2]) for v in hk)]
        return ("hook_slur" if arcs else "hook_other"), info
    if h["settled"] == "stroke_candidate":
        far = [o for o in tip["beams"] if inward(by[o]) >= HEAD_END_DY]
        return ("head_end_blob" if far else "at_tip"), info
    near = [v for v in views if v.kind in ("horizontal", "curve") and any(j == stem.ordinal for j, _ in v.touches)
            and not (v.box[1] + v.box[3] < tip_y - 3.3 * sp - 0.5 * sp or v.box[1] > tip_y + 3.3 * sp + 0.5 * sp)]
    spans = [v for v in near if role[v.ordinal]["role"] in ("span_thin", "beam") and role[v.ordinal].get("stems", 0) >= 2]
    thick = [v for v in spans if v.thickness >= 1.0]
    if thick and len(tip["beams"]) <= 1:
        info["thickness"] = round(thick[0].thickness, 2)
        return "fused_double", info
    thin = [v for v in spans if v.thickness < BS.BEAM_MIN_THICKNESS_SP]
    if thin:
        t = max(v.thickness for v in thin)
        info["thickness"] = round(t, 3)
        return ("thin_remnant" if t < 0.30 else "thin_near_cut"), info
    close = [v for v in views if role[v.ordinal]["role"] == "beam" and abs(inward(v)) <= 1.2 and not any(j == stem.ordinal for j, _ in v.touches)]
    if close:
        return "join_missing", info
    return ("no_stroke" if not near else "other"), info


def main():
    rep = pathlib.Path(sys.argv[1])
    res = {}
    for plate in ("litolff", "brahms"):
        mini = json.load(open(rep / "work" / ("%s.on.mini-record.json" % plate)))
        heads = heads_of(mini)
        del mini
        cells = {rg.rsplit("/", 1)[0] for rg in heads}
        got = collections.defaultdict(list)
        with open(rep / "work" / ("%s.on.gathered.record.json" % plate), "rb") as f:
            for o in ijson.items(f, "record.observations.item", use_float=True):
                s = o["subject"]
                if not s.startswith("glyph/"):
                    continue
                c = s.rsplit("/", 1)[0]
                if c in cells and o["quantity"] in ("stroke", "glyph_box"):
                    got[c].append(o)
        tab = collections.Counter()
        per = {}
        for rg, h in heads.items():
            rows = got[rg.rsplit("/", 1)[0]]
            cause, info = classify(h, views_of(rows), rows)
            tab[("hook" if h["flag_levels"] else h["settled"], cause)] += 1
            per[rg] = dict(settled=h["settled"], before=h["before"], after=h["after"], cause=cause, **info)
        res[plate] = dict(table={"%s/%s" % k: v for k, v in sorted(tab.items())}, heads=per)
        print(plate, len(heads))
        for k, v in sorted(tab.items()):
            print("   %-18s %-14s %d" % (k[0], k[1], v))
    json.dump(res, open(sys.argv[2], "w"))


if __name__ == "__main__":
    main()
