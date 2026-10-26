"""ROADMAP 2.205 milestone: the 12 blind tiles for ONE OWNER PER STROKE, drawn from run (b) (beams + stems in both arms, ownership OFF vs ON).

usage: tiles_2205.py REPORT_OUT_DIR TILES_OUT_DIR KEY_2202
   REPORT_OUT_DIR = out/lane-report/2.205b; KEY_2202 = the 2.202 milestone tiles' key.json (the re-shown tiles).

Strata (FINDINGS 2.205 milestone plan; seed 2205; no two tiles on one ink -- a tile is skipped when its box, grown one staff space, meets one chosen):
  3  heads whose BEAM reading changed (detail.beams_from_strokes differs OFF vs ON) and whose live duration changed
  2  heads whose STEM reading changed (detail.stems_from_strokes.settled differs), a `disagree` that went away first (the 2.204 stem cases)
  2  CONTESTED strokes (`Q.STROKE_OWNER` value.contested), Brahms accidental|rest first -- the box is the stroke's own page box
  1  a head / rest box ownership says owns none of its ink that main KEPT
  4  2.202 tiles re-shown: 2 (sharp's crossbar), 6 (head + ledger), 12 (slur start) -- predicted to move to Sean's answer -- and 1 (erase-thinned beam,
     predicted unchanged: the control)
Blind: one neutral orange box, nothing of ours drawn; the key (what each tile is, OFF / ON) is written OUTSIDE the tile folder by `lane_report.cut_tiles`."""
import collections
import json
import pathlib
import random
import sys

import ijson

sys.path.insert(0, ".")
from tools.omr.staged import lane_report as LR      # noqa: E402

rep, out, key2202 = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
rng = random.Random(2205)
BASE = 375000


def first_and_live(path):
    """`{subject: (first duration verdict detail, live duration value summary)}` streamed from a mini-record."""
    first, live = {}, {}
    with open(path, "rb") as f:
        for v in ijson.items(f, "verdicts.item", use_float=True):
            if v["quantity"] != "duration":
                continue
            s = v["subject"]
            if not v.get("supersedes") and s not in first:
                first[s] = v.get("detail") or {}
            val = v.get("value") or {}
            live[s] = (v.get("outcome"), val.get("beats") if isinstance(val, dict) else None,
                       tuple(sorted(str((c.get("value") or {}).get("beats")) for c in v.get("candidates") or [])))
    return first, live


def owner_rows(path):
    """From the ON gathered record: the cells' `stroke_owner` verdicts, the strokes' page boxes, the glyph boxes, and main's kept heads / rests."""
    so, sbox, gbox, kept = {}, {}, {}, set()
    with open(path, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            s, q = o["subject"], o["quantity"]
            if q == "stroke":
                sbox[s] = (o.get("detail") or {}).get("bbox_page_px")
            elif q == "glyph_box" and s.startswith("glyph/"):
                gbox[s] = ((o.get("detail") or {}).get("bbox_page_px"), o["value"][0])
    with open(path, "rb") as f:
        for v in ijson.items(f, "record.verdicts.item", use_float=True):
            q = v["quantity"]
            if q == "stroke_owner" and isinstance(v.get("value"), dict):
                so[v["subject"]] = v
            elif q in ("notehead_is_not_a_notehead", "rest_is_not_a_rest"):
                if v.get("value") is False:
                    kept.add(v["subject"])
                else:
                    kept.discard(v["subject"])
    return so, sbox, gbox, kept


chosen = []


def near(a, b):
    if a["plate"] != b["plate"] or a["page"] != b["page"]:
        return False
    u = LR.PLATES[a["plate"]]["unit"]
    return not (a["box"][2] + u < b["box"][0] - u or b["box"][2] + u < a["box"][0] - u or a["box"][3] + u < b["box"][1] - u or b["box"][3] + u < a["box"][1] - u)


def take(pool, n):
    pool = list(pool)
    rng.shuffle(pool)
    got = 0
    for it in pool:
        if got >= n:
            break
        if it.get("box") is None or any(near(it, c) for c in chosen):
            continue
        chosen.append(it)
        got += 1
    return got


beam_pool, stem_pool, stem_gone, cont_pool, cont_ar, box_pool = [], [], [], [], [], []
counts = {}
for plate in ("litolff", "brahms"):
    off_first, off_live = first_and_live(rep / "work" / ("%s.off.mini-record.json" % plate))
    on_first, on_live = first_and_live(rep / "work" / ("%s.on.mini-record.json" % plate))
    so, sbox, gbox, kept = owner_rows(rep / "work" / ("%s.on.gathered.record.json" % plate))
    c = collections.Counter()
    for s, d_on in on_first.items():
        d_off = off_first.get(s) or {}
        g = gbox.get(s)
        if not g or not g[0]:
            continue
        base = dict(plate=plate, page=LR.page_of(s), box=[float(x) for x in g[0]], rg=s, kind="note", off=str(off_live.get(s)), on=str(on_live.get(s)))
        bo, bn = d_off.get("beams_from_strokes"), d_on.get("beams_from_strokes")
        if bo != bn and off_live.get(s) != on_live.get(s):
            c["beam_changed"] += 1
            beam_pool.append(dict(base, role="case", side="beam_reading_changed", settled_off=(bo or {}).get("settled"), settled_on=(bn or {}).get("settled")))
        so_, sn = (d_off.get("stems_from_strokes") or {}).get("settled"), (d_on.get("stems_from_strokes") or {}).get("settled")
        if so_ != sn:
            c["stem_changed"] += 1
            it = dict(base, role="case", side="stem_reading_changed", settled_off=so_, settled_on=sn)
            (stem_gone if so_ == "disagree" else stem_pool).append(it)
    for cell, v in so.items():
        ck = cell[len("cell/"):]
        for o in (v["value"].get("contested") or []):
            pb = sbox.get("glyph/%s/%d" % (ck, BASE + int(o)))
            ent = (v.get("detail") or {}).get("strokes", {}).get(str(o)) or []
            fams = sorted({c_[1] for c_ in (ent[4] if len(ent) > 4 else []) if c_[3] != "no"})
            if pb:
                it = dict(plate=plate, page=LR.page_of("glyph/" + ck + "/0"), box=[float(x) for x in pb], rg="stroke:%s/%d" % (ck, o), kind="ink",
                          role="case", side="contested:" + "|".join(fams))
                (cont_ar if fams == ["accidental", "rest"] else cont_pool).append(it)
                c["contested"] += 1
        for k, b in ((v.get("detail") or {}).get("boxes") or {}).items():
            g = gbox.get(k)
            if k in kept and g and g[0]:
                box_pool.append(dict(plate=plate, page=LR.page_of(k), box=[float(x) for x in g[0]], rg=k, kind=str(g[1]), role="case",
                                     side="ownership_%s_main_kept" % b[0]))
                c["box_owns_none_main_kept"] += 1
    counts[plate] = dict(c)

# the re-shown tiles FIRST, so no case drawn after them stands on the same ink
k2 = {t["tile"]: t for t in json.load(open(key2202))}
for n in (2, 6, 12, 1):
    t = k2[n]
    chosen.append(dict(plate=t["plate"], page=t["page"], box=t["box"], rg=t["rg"], kind=t.get("kind", "note"), role="control" if n == 1 else "reshown",
                       side="2.202 tile %d re-shown" % n))
take(beam_pool, 3)
take(stem_gone, 2) or None
if sum(1 for x in chosen if x["side"] == "stem_reading_changed") < 2:
    take(stem_pool, 2 - sum(1 for x in chosen if x["side"] == "stem_reading_changed"))
take([x for x in cont_ar if x["plate"] == "brahms"], 1)
take(cont_pool + [x for x in cont_ar if x not in chosen], 1)
take(box_pool, 1)
short = 12 - len(chosen)
if short > 0:
    take(beam_pool + stem_pool, short)
rng.shuffle(chosen)
res = LR.cut_tiles(chosen, out)
(out / "tile_counts.json").write_text(json.dumps(dict(counts=counts, pools=dict(beam=len(beam_pool), stem_gone=len(stem_gone), stem_other=len(stem_pool),
                                                                              contested_acc_rest=len(cont_ar), contested_other=len(cont_pool),
                                                                              boxes=len(box_pool)), tiles=res), indent=1))
print(json.dumps(dict(counts=counts, n=len(chosen), sides=[c["side"] for c in chosen]), indent=1))
