"""ROADMAP 2.326 small test (read-only, scratch): the judged / hand-labelled heads per plate against today's fill cuts and
the candidate page-relative measures. Reads work/{judged,pages,measures}-<doc>.json (+ Brahms p0 hand truth).
Writes work/heads-<doc>.json (one row per truth head) and prints the tables.

    python3 benchmarks/notehead-fill-by-page-2026-11/analyse.py litolff
"""
import json
import pathlib
import sys
from statistics import median

import numpy as np

W = pathlib.Path(__file__).parent / "work"
HT = pathlib.Path("data/hand-truth/pages/imslp317803/0.json")


def wins(nink):
    d = (nink or {}).get("detail") or {}
    out = {}
    for k in ("ink_raw", "ink_net", "ink_off_line"):
        w = ((d.get(k) or {}).get("windows") or {})
        out[k] = (w.get("center"), w.get("ring"))
    iw = d.get("interior_white") or {}
    loc = d.get("interior_white_located") or {}
    return out, iw.get("rows_share"), iw.get("hole_share"), loc.get("rows_share")


def today(h):
    """What the record writes for this head: (fill written, how) -- how in plain / blue / narrowed / abstained / refused."""
    n = h.get("not_a_notehead") or h.get("notehead_is_not_a_notehead")
    if n and n.get("outcome") == "decided" and n.get("value") is True:
        return None, "refused_not_a_note:" + str(n.get("reason"))
    v = h.get("duration")
    if not v:
        return None, "no_verdict"
    det = v.get("detail") or {}
    if v["outcome"] == "decided":
        val = v.get("value") or {}
        w, dots = float(val.get("written") or 0), int(val.get("dots") or 0)
        hw = w / (2.0 - 0.5 ** dots) if w else 0
        fill = "hollow" if hw >= 2.0 else "solid"
        g = det.get("head_ink_guess") or {}
        blue = bool(g.get("marks_blue")) or (v.get("decider") or "").startswith(("infer", "collapse", "one_note", "reconcile")) \
            or v.get("reason") in ("lone_event_fills_bar", "bar_corrects_one_note", "meter_reconciliation",
                                   "the_bars_arithmetic_forces_this_length")
        return fill, ("blue" if blue else "plain") + ":" + str(v.get("reason"))
    cands = []
    for c in v.get("candidates") or ():
        cv = (c or {}).get("value") or {}
        if isinstance(cv, dict) and cv.get("written"):
            dd = int(cv.get("dots") or 0)
            cands.append(float(cv["written"]) / (2.0 - 0.5 ** dd))
    kinds = sorted({"hollow" if x >= 2 else "solid" for x in cands})
    return "/".join(kinds) or None, v["outcome"] + ":" + str(v.get("reason"))


def ht_rows():
    """Brahms p0: Sean's hand boxes matched to the record's notehead boxes by centre (the hand rects are the confirmed
    detector boxes; 411 of 411 within 15 px)."""
    ht = json.load(open(HT))
    hb = [b for b in ht["boxes"] if b["cls"].startswith(("noteheadBlack", "noteheadHalf", "noteheadWhole"))]
    pg = [h for h in json.load(open(W / "pages-brahms.json"))["heads"] if h["subject"].startswith("glyph/0/")]
    R = np.array([[(h["bbox_page_px"][0] + h["bbox_page_px"][2]) / 2, (h["bbox_page_px"][1] + h["bbox_page_px"][3]) / 2]
                  for h in pg])
    out = []
    for b in hb:
        x, y = (b["rect"][0] + b["rect"][2]) / 2, (b["rect"][1] + b["rect"][3]) / 2
        dd = np.hypot(R[:, 0] - x, R[:, 1] - y)
        i = int(dd.argmin())
        if dd[i] > 15:
            continue
        h = dict(pg[i])
        h.update(src="hand:" + b["id"], truth=("hollow" if b["cls"].startswith(("noteheadHalf", "noteheadWhole")) else "solid"),
                 truth_cls=b["cls"], answer=b["cls"])
        out.append(h)
    return out


def main(doc):
    meas = json.load(open(W / ("measures-%s.json" % doc)))
    pages = json.load(open(W / ("pages-%s.json" % doc)))["heads"]
    rows = []
    jp = W / ("judged-%s.json" % doc)
    for h in (json.load(open(jp))["heads"] if jp.exists() else []):
        if h["status_today"] in ("unscored",):
            continue
        tb = h.get("tile_page_box")
        bb = (h["obs"].get("glyph_box") or {}).get("detail", {}).get("bbox_page_px")
        mq = "no_tile_box"
        if tb and bb:
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            small = max(tb[2] - tb[0], tb[3] - tb[1]) <= 120
            near = abs(cx - (tb[0] + tb[2]) / 2) <= 6 and abs(cy - (tb[1] + tb[3]) / 2) <= 6
            mq = ("mark_box" if near else "mark_box_off") if small else (
                "in_window" if tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3] else "outside_window")
        h = dict(h, src="tile:%s/%s" % (h["item"], h["tile"]), match=mq,
                 truth="hollow" if float(h["value"]) >= 2.0 - 1e-6 else "solid",
                 cls=((h["obs"].get("glyph_box") or {}).get("value") or [None])[0],
                 score=(h["obs"].get("glyph_box") or {}).get("score"))
        rows.append(h)
    if doc == "brahms":
        rows += ht_rows()
    # the page's own confidently-solid heads: detector says black at >= 0.8, the box is one head (Q.HEAD_INK filed a value),
    # and its verdict is a decided value whose head is black ON A BEAM OR FLAG (a hollow head never carries one) -- the
    # reader's own population, never Sean's marks
    ref = {}
    for h in pages:
        if not str(h["cls"]).startswith("noteheadBlack") or (h.get("score") or 0) < 0.8:
            continue
        v = h.get("duration") or {}
        val = v.get("value") if isinstance(v.get("value"), dict) else {}
        if v.get("outcome") != "decided" or not val or int(val.get("beam_levels") or 0) < 1:
            continue
        m = meas.get(h["subject"])
        if not m or m["box_from"] != "trimmed":
            continue
        ref.setdefault(int(h["subject"].split("/")[1]), []).append(m)
    refstat = {}
    for p, ms in ref.items():
        refstat[p] = {k: (median([m[k] for m in ms if m[k] is not None]),
                          float(np.percentile([m[k] for m in ms if m[k] is not None], 95)), len(ms))
                      for k in ("in_dark", "hull_paper", "hole_paper")}
    out = []
    for h in rows:
        obs = h.get("obs") or {}
        win, slit, hole, slit_loc = wins(obs.get("notehead_ink"))
        hi = obs.get("head_ink") or {}
        hid = hi.get("detail") or {}
        fill, how = today(h)
        m = meas.get(h["subject"]) or {}
        p = int(h["subject"].split("/")[1])
        rs = refstat.get(p)
        rel = {}
        if rs and m:
            rel = {"in_dark_rel": None if m.get("in_dark") is None or not rs["in_dark"][0] else round(m["in_dark"] / rs["in_dark"][0], 4),
                   "hull_paper_minus_ref": None if m.get("hull_paper") is None else round(m["hull_paper"] - rs["hull_paper"][0], 4),
                   "hull_paper_over_p95": None if m.get("hull_paper") is None else round(m["hull_paper"] - rs["hull_paper"][1], 4),
                   "ref_n": rs["in_dark"][2], "ref_in_dark": rs["in_dark"][0], "ref_hull_paper": rs["hull_paper"][0]}
        out.append({"subject": h["subject"], "page": p, "src": h["src"], "match": h.get("match", "hand"), "truth": h["truth"], "answer": h.get("answer"),
                    "cls": h.get("cls"), "score": h.get("score"), "status_today": h.get("status_today"),
                    "fill_today": fill, "how_today": how,
                    "slit": slit, "hole_share": hole, "slit_located": slit_loc,
                    "raw_c": win["ink_raw"][0], "raw_r": win["ink_raw"][1], "net_c": win["ink_net"][0], "net_r": win["ink_net"][1],
                    "off_c": win["ink_off_line"][0], "off_r": win["ink_off_line"][1],
                    "hi_value": hi.get("value"), "hi_slit": hid.get("slit"), "hi_win_c": (hid.get("window") or {}).get("center"),
                    "hi_extent": hid.get("extent_sp"),
                    "hf_first": ((h.get("duration") or {}).get("detail") or {}).get("head_fill_first"),
                    **{k: m.get(k) for k in ("in_dark", "hull_paper", "hole_paper", "hole_big", "line_rows", "box", "box_from")},
                    **rel})
    json.dump({"refstat": refstat, "heads": out}, open(W / ("heads-%s.json" % doc), "w"), default=str)
    print(doc, "truth heads", len(out), "ref pages", {p: v["in_dark"][2] for p, v in refstat.items()})


if __name__ == "__main__":
    main(sys.argv[1])
