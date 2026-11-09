"""2.274 round 3 DIAGNOSIS: for every printed arc of Sean's Brahms p0 hand truth (109 printed arcs = 153 hand boxes), the stage where it first goes wrong, flag OFF and ON.
    python3 census.py            (reads work/{off,on}.record.json, work/brahms.{off,on}.musicxml / mini-record, written by run_arms.py + mkmini.py)
Writes census.json (one record per printed arc) and prints the bucket table.  STAGED.  Changes no pipeline code.

Stage tests (each one is a measurement against Sean's boxes, not against our own file):
  box_cov   share of the printed arc's x span covered by the union of detector `arc_box` rows whose centre is inside a hand box (+0.5 sp)   [GATHER, night record, pre-2.273]
  run_cov   share covered by the best single step-1 `page_arc` run ON the arc (clipped_on rule of page-ink score.py), and whether a run reaches past it
  witnessed the run has a witnessing box
  binder    the `Q.PAGE_ARC_BINDING` entry of the run's piece that covers the arc: status, reason, ends (head x vs the printed arc's x ends, REACH 2.5 sp like truth_p0)
  file      truth_p0's scorer (ends within 2.5 sp, same staff, kind), flag OFF and ON files
  heads     the hand notehead nearest each printed end (<= 3 sp) and whether the file writes a note within 1 sp of it
"""
import collections
import json
import numpy as np
from load import *   # noqa
import truth_p0 as T  # noqa

P, HEADS = printed()
OUT = {}


def keyinfo(k):
    a = k.split("/")
    return int(a[2]), int(a[3]), int(a[4]), int(a[5])


def boxes_of(rec):
    d = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/"):
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b:
                d[o["subject"]] = dict(box=[float(x) for x in b], cat=(o["detail"] or {}).get("category"))
    return d


def main():
    recs = {a: record(a) for a in ("off", "on")}
    rec = recs["on"]
    gb = boxes_of(rec)
    arcbox = {}
    for o in rec["observations"]:
        if o["quantity"] == "arc_box" and o["subject"].startswith("glyph/0/"):
            d = o["detail"]
            arcbox[o["subject"]] = dict(box=[float(x) for x in d["bbox_page_px"]], cls=o["value"])
    refused = {v["subject"]: v["value"] for v in rec["verdicts"] if v["quantity"] == "arc_is_not_an_arc"}
    owner = {v["subject"]: v["value"] for v in rec["verdicts"] if v["quantity"] == "arc_owner"}
    kindv = {v["subject"]: v["value"] for v in rec["verdicts"] if v["quantity"] == "arc_kind"}
    runs = {}
    for o in rec["observations"]:
        if o["quantity"] == "page_arc" and o["value"] == "run":
            runs[o["detail"]["ordinal"]] = o["detail"]
    bind = [v for v in rec["verdicts"] if v["quantity"] == "page_arc_binding"][0]["detail"]["runs"]
    syscurves = [o for o in rec["observations"] if o["quantity"] == "system_arc" and o["subject"].startswith("glyph/0/")]
    written = {a: xml_notes(a) for a in ("off", "on")}
    spans_all = {}
    for arm in ("off", "on"):
        xml = (WORK / ("brahms.%s.musicxml" % arm)).read_text()
        boxes = T.boxes_p0(WORK / ("brahms.%s.mini-record.json" % arm))
        sp = []
        for a in A.arcs_of_xml(xml):
            if not a["start"].startswith("glyph/0/") or a["start"] not in boxes or a["stop"] not in boxes:
                continue
            ba, bz = boxes[a["start"]], boxes[a["stop"]]
            sa, sz = a["start"].split("/")[2:4], a["stop"].split("/")[2:4]
            sp.append(dict(kind=a["kind"], staff="/".join(sa), same_staff=sa == sz, cl=(ba[0] + ba[2]) / 2, cr=(bz[0] + bz[2]) / 2, start=a["start"], stop=a["stop"]))
        spans_all[arm] = sp
    truthrows = {}
    for arm in ("off", "on"):
        _, _, _, rows = T.score(WORK, arm)
        truthrows[arm] = {(r[0], r[1], r[2], r[3]): r for r in rows}

    for p in P:
        rec_p = dict(n=p["n"], staff=p["staff"], kind=p["kind"], x0=round(p["x0"]), x1=round(p["x1"]), width_sp=round((p["x1"] - p["x0"]) / SP, 1), hand_boxes=len(p["ids"]),
                     y0=round(p["box"][1]), y1=round(p["box"][3]))
        # ---- GATHER: detector boxes
        bx = []
        for k, a in arcbox.items():
            b = a["box"]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if inside(cx, cy, p["rects"], 0.5 * SP):
                bx.append(k)
        spans = [(arcbox[k]["box"][0], arcbox[k]["box"][2]) for k in bx]
        rec_p["boxes"] = bx
        rec_p["box_cov"] = round(covered(spans, p["x0"], p["x1"]), 2)
        rec_p["boxes_refused"] = [k for k in bx if refused.get(k)]
        rec_p["boxes_kept"] = [k for k in bx if not refused.get(k)]
        kept_spans = [(arcbox[k]["box"][0], arcbox[k]["box"][2]) for k in rec_p["boxes_kept"]]
        rec_p["box_cov_kept"] = round(covered(kept_spans, p["x0"], p["x1"]), 2)
        # system curve (join_traces) coverage
        cs = []
        for o in syscurves:
            d = o["detail"]
            cx = (d["x_left_page"] + d["x_right_page"]) / 2
            cy = (d["y_left_page"] + d["y_right_page"]) / 2
            if any(pk in bx for pk in d.get("pieces", [])):
                cs.append((d["x_left_page"], d["x_right_page"], o["subject"], o["value"]))
        rec_p["curve_cov"] = round(covered([(a, b) for a, b, _, _ in cs], p["x0"], p["x1"]), 2)
        rec_p["curves"] = [(c[2], c[3]) for c in cs]
        # ---- GATHER: step-1 runs
        on_runs = []
        for ordv, d in runs.items():
            pts = np.array(d["points"])
            if S.clipped_on(pts, p, SP):
                sel = pts[(pts[:, 0] >= p["x0"] - 0.5 * SP) & (pts[:, 0] <= p["x1"] + 0.5 * SP)]
                cov = covered([(float(sel[:, 0].min()), float(sel[:, 0].max()))], p["x0"], p["x1"])
                over = max(p["x0"] - pts[:, 0].min(), pts[:, 0].max() - p["x1"])
                on_runs.append(dict(ordinal=ordv, cov=round(cov, 2), run_x0=round(pts[:, 0].min()), run_x1=round(pts[:, 0].max()), past_sp=round(over / SP, 1), witnesses=d.get("witnesses")))
        on_runs.sort(key=lambda r: -r["cov"])
        rec_p["runs"] = on_runs
        rec_p["run_cov"] = on_runs[0]["cov"] if on_runs else 0.0
        rec_p["run_union_cov"] = round(covered([(r["run_x0"], r["run_x1"]) for r in on_runs], p["x0"], p["x1"]), 2)
        # ---- ADJUDICATE: binding entries of the pieces
        ents = []
        for e in bind:
            if e["ordinal"] not in [r["ordinal"] for r in on_runs]:
                continue
            xr = e.get("x_range") or [runs[e["ordinal"]]["bbox_page_px"][0], runs[e["ordinal"]]["bbox_page_px"][2]]
            ov = min(xr[1], p["x1"]) - max(xr[0], p["x0"])
            if ov > 0.5 * min(xr[1] - xr[0], p["x1"] - p["x0"]):
                ents.append((ov / (p["x1"] - p["x0"]), e))
        ents.sort(key=lambda t: -t[0])
        rec_p["bind"] = [dict(ordinal=e["ordinal"], piece=e.get("piece"), status=e["status"], why=e.get("why"), kind=e.get("kind"), start=e.get("start"), stop=e.get("stop"), x_range=e.get("x_range"),
                              left=({k: e["left"].get(k) for k in ("head", "distance_spaces", "out_by_spaces", "via_closest", "chord", "outside_window", "by_height")} if e.get("left") else None),
                              right=({k: e["right"].get(k) for k in ("head", "distance_spaces", "out_by_spaces", "via_closest", "chord", "outside_window", "by_height")} if e.get("right") else None),
                              witnesses=e.get("witnesses"), rule=e.get("rule"), ov=round(ov, 2)) for ov, e in ents]
        # ---- FILE (both arms)
        for arm in ("off", "on"):
            key = (p["kind"] if len(p["cls"]) == 1 else "slur", p["staff"], round(p["x0"]), round(p["x1"]))
            tr = truthrows[arm][key]
            rec_p["file_" + arm] = tr[4]
            rec_p["file_" + arm + "_arc"] = [tr[5], tr[6]]
            # nearest written span on the staff
            best = None
            for s in spans_all[arm]:
                if s["staff"] != p["staff"] or not s["same_staff"]:
                    continue
                el, er = (s["cl"] - p["x0"]) / SP, (s["cr"] - p["x1"]) / SP
                m = max(abs(el), abs(er))
                if best is None or m < best[0]:
                    best = (m, el, er, s)
            rec_p["near_" + arm] = None if best is None else dict(err_sp=round(best[0], 1), el=round(best[1], 1), er=round(best[2], 1), kind=best[3]["kind"], start=best[3]["start"], stop=best[3]["stop"])
        # ---- heads
        hs = {}
        for side, x in (("L", p["x0"]), ("R", p["x1"])):
            cand = [h for h in HEADS if h["staff"] == p["staff"] and abs((h["rect"][0] + h["rect"][2]) / 2 - x) <= 3 * SP]
            if not cand:
                hs[side] = dict(hand_head=None)
                continue
            h = min(cand, key=lambda h: abs((h["rect"][0] + h["rect"][2]) / 2 - x))
            hx, hy = (h["rect"][0] + h["rect"][2]) / 2, (h["rect"][1] + h["rect"][3]) / 2
            res = dict(hand_head=[round(hx), round(hy)], dx_sp=round((hx - x) / SP, 1))
            for arm in ("off", "on"):
                ok = False
                for k in written[arm]:
                    if k in gb and keyinfo(k)[:2] == tuple(int(t) for t in p["staff"].split("/")):
                        b = gb[k]["box"]
                        if abs((b[0] + b[2]) / 2 - hx) <= SP and abs((b[1] + b[3]) / 2 - hy) <= 1.2 * SP:
                            ok = True
                            break
                res["written_" + arm] = ok
            hs[side] = res
        rec_p["heads"] = hs
        OUT[p["n"]] = rec_p
    json.dump(list(OUT.values()), open(HERE / "census.json", "w"), indent=1, default=str)
    print("printed", len(OUT))


main()
