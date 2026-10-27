"""ROADMAP 2.205 (read-only, no gather): what would ONE OWNER PER STROKE do to the heads 2.202's beam rule changed?

usage: owner_on_2202_heads.py REPORT_OUT_DIR TILE_KEY OUT.json
   REPORT_OUT_DIR = the 2.202 milestone (work/<plate>.on.mini-record.json, work/<plate>.on.gathered.record.json); TILE_KEY = its tiles' key.json.

For every duration head of the ON arm whose `beams_from_strokes` settled `stroke_candidate` (the map counted MORE levels than the readers),
`disagree_narrowed` (FEWER) or read a flag from hooks, the cell's strokes are owned by `stroke_owner.own_strokes` (the boxes, the register's
areas -- exactly as `adjudicate_stroke_owner` does), the owned / contested strokes are MASKED as the consumers mask them, and 2.202's own tip
reading (`beam_strokes.roles`, `tip_reading`) is taken again on the head's stem:
  stroke_candidate  -> `resolved` when the masked count is back to the readers' count (the extra "level" was another mark's ink), else `unchanged`
  disagree_narrowed -> ownership can only take strokes away, never thicken a beam the erase thinned: `unchanged` / `worse` (it took one more)
  hook heads        -> `no_longer_a_flag` when no hook survives the mask, else `still_a_flag`
This is the TIP count only (the box-support part of 2.202 is not replayed): a prediction of the milestone, not its result."""
import collections
import json
import pathlib
import sys

import ijson

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/shared-ink-map-2026-10")
import multi_claim_census as MC                      # noqa: E402
from tools.omr.staged import beam_strokes as BS      # noqa: E402
from tools.omr.staged import stroke_owner as SO      # noqa: E402


def heads(mini_path):
    out = {}
    with open(mini_path, "rb") as f:
        for v in ijson.items(f, "verdicts.item", use_float=True):
            if v["quantity"] != "duration" or v.get("supersedes"):
                continue
            d = (v.get("detail") or {}).get("beams_from_strokes")
            if d and (d.get("settled") in ("stroke_candidate", "disagree_narrowed") or d.get("flag_levels")):
                out[v["subject"]] = dict(settled=d.get("settled"), before=d.get("before"), after=d.get("after"), tip=d.get("tip"),
                                         flag_levels=d.get("flag_levels"), side=(v.get("detail") or {}).get("beam_side"))
    return out


def stream_cells(path, want):
    cells = collections.defaultdict(lambda: {"strokes": {}, "boxes": {}, "gs": {}, "stems": []})
    areas = collections.defaultdict(list)
    with open(path, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            q, s = o["quantity"], o["subject"]
            if q == "claimed_area":
                d = o.get("detail") or {}
                ck = "%s/%s" % (s[6:], d.get("cell"))
                if ck in want and d.get("unit") == "area" and d.get("standing", "READ") == "READ":
                    areas[ck].append((d.get("owner"), tuple(o["value"][:4]), o["id"]))
                continue
            if not s.startswith("glyph/") or q not in ("stroke", "glyph_box", "glyph_strokes"):
                continue
            ck = s[6:].rsplit("/", 1)[0]
            if ck not in want:
                continue
            c = cells[ck]
            d = o.get("detail") or {}
            if q == "stroke":
                c["strokes"][int(s.rsplit("/", 1)[1]) - MC.BASE] = (o["value"], tuple(d["stroke_box"][:4]), float(d.get("length_spaces") or 0),
                                                                   float(d.get("thickness_spaces") or 0), float(d.get("sagitta_spaces") or 0),
                                                                   float(d.get("angle_deg") or 0),
                                                                   tuple((int(a), float(b)) for a, b in d.get("touches") or ()),
                                                                   float(d.get("staff_space_local_px") or 0), tuple(d.get("bbox_page_px") or ()),
                                                                   o["id"], float(d.get("fill") or 0))
            elif q == "glyph_box":
                c["boxes"][s] = (o["value"][0], d.get("category"), o.get("reader"))
            else:
                c["gs"][s] = (tuple(int(v) for v in o["value"]), tuple((int(a), float(b)) for a, b in d.get("partial") or ()), o["id"])
    return cells, areas


def owned_mask(c, area_rows):
    claims = []
    for k, (cov, partial, rid) in c["gs"].items():
        b = c["boxes"].get(k)
        if b is None or str(b[2] or "").startswith("yolo_rescue"):
            continue
        fam = SO.family_of(b[0], b[1])
        if fam is not None:
            claims.append(SO.Claim(k, fam, b[0], cov, partial, rid))
    for owner, (x0, y0, x1, y1), rid in area_rows:
        inside = tuple(o for o, t in sorted(c["strokes"].items()) if len(t[8]) == 4
                       and x0 <= (t[8][0] + t[8][2]) / 2 <= x1 and y0 <= (t[8][1] + t[8][3]) / 2 <= y1)
        if owner in SO.AREA_OWNERS and inside:
            claims.append(SO.Claim(rid, owner, owner, inside, (), rid, area=True))
    inks = [SO.Ink(o, t[0], tuple(float(v) for v in t[1]), t[2], t[3], MC.area_sp2(t), t[7], t[6], t[9], t[5]) for o, t in c["strokes"].items()]
    own = SO.own_strokes(inks, claims)
    return {o: ("owned" if w.state in ("decided", "merged") else "contested") for o, w in own.items() if w.claimed}, own


def main():
    rep = pathlib.Path(sys.argv[1])
    key = {k["rg"]: k["tile"] for k in json.load(open(sys.argv[2]))}
    res = {}
    for plate in ("litolff", "brahms"):
        hs = heads(rep / "work" / ("%s.on.mini-record.json" % plate))
        want = {rg[6:].rsplit("/", 1)[0] for rg in hs}
        cells, areas = stream_cells(rep / "work" / ("%s.on.gathered.record.json" % plate), want)
        tab = collections.Counter()
        per = {}
        for rg, h in hs.items():
            ck = rg[6:].rsplit("/", 1)[0]
            c = cells.get(ck)
            if not c or not h.get("tip") or h["side"] not in ("up", "down"):
                tab[(h["settled"] if not h["flag_levels"] else "hook", "no_tip")] += 1
                continue
            mask, own = owned_mask(c, areas.get(ck, ()))
            views = [BS.StrokeView(o, mask.get(o, t[0]), tuple(float(v) for v in t[1]), t[2], t[3], t[4], t[5], t[6], t[7], t[9])
                     for o, t in c["strokes"].items()]
            by = {v.ordinal: v for v in views}
            stem = by.get(h["tip"]["stem"])
            if stem is None or stem.kind != "vertical":
                out = "stem_owned" if stem is not None else "no_stem"
            else:
                tip = BS.tip_reading(views, BS.roles(views), stem, h["side"])
                if h["flag_levels"]:
                    out = "no_longer_a_flag" if not tip["hooks"] else "still_a_flag"
                elif h["settled"] == "stroke_candidate":
                    readers = (h.get("before") or [0, 0])[-1]
                    out = "resolved" if len(tip["beams"]) <= readers else "unchanged"
                else:
                    out = "unchanged" if len(tip["beams"]) >= len(h["tip"].get("beams") or ()) else "worse"
            kind = "hook" if h["flag_levels"] else h["settled"]
            tab[(kind, out)] += 1
            took = sorted({o: (own[o].state, own[o].family) for o in (h["tip"].get("beams") or []) + (h["tip"].get("hooks") or [])
                           if o in mask}.items())
            per[rg] = dict(kind=kind, outcome=out, tile=key.get(rg), masked_tip_strokes=took)
        res[plate] = {"table": {"%s|%s" % k: v for k, v in sorted(tab.items())},
                      "tiles": {str(v["tile"]): v for v in per.values() if v["tile"] is not None}, "heads": per}
        print(plate, res[plate]["table"])
        for t, v in sorted(res[plate]["tiles"].items(), key=lambda kv: int(kv[0])):
            print("   tile", t, v["kind"], v["outcome"], v["masked_tip_strokes"])
    json.dump(res, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    main()
