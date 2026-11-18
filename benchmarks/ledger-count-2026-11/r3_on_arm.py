"""ROADMAP 2.312 r3 -- the measure r2 lacked: the ON arm of a SAVED full frozen-sample gather (2.311, main 803c90513), built by
re-reading every far head's ledger count with `OMR_LEDGER_COUNT_TO_INK` off and on on the record's own inputs (r2_reread.py's
reader call), and replacing the far-head rows (own staff: `far_head_ledger_position`; and the own-staff candidate of
`far_head_owner_ledger`) where ON differs. CONTROL (can fail): the OFF re-read must reproduce the record's row; a subject whose OFF
re-read does not reproduce is LEFT AS RECORDED in the ON arm (counted). Then BOTH arms are re-adjudicated on this tree (verdicts stripped,
`rebuild_gather` + `run_stages`) and written as `<plate>.<arm>.gathered.record.json` for `lane_report --from gather` (2.315's reuse).

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r3_on_arm.py PLATE SAVED.record.json WORKDIR
"""
from __future__ import annotations

import collections
import copy
import importlib.util
import json
import os
import pathlib
import sys

import cv2

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import far_head_owner as FO
from tools.omr.annotate import ledger_grid as lg
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR
from tools.omr.staged.record_io import load_record

_spec = importlib.util.spec_from_file_location("r2r", str(pathlib.Path(__file__).with_name("r2_reread.py")))
r2r = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r2r)


def read_both(ctx, s, box, cls, gl):
    out = {}
    for arm in ("0", "1"):
        os.environ[lg.LEDGER_COUNT_TO_INK_ENV] = arm
        r = ctx.read(s, box, cls, gl)
        try:
            o = FO.read_toward(ctx, s, box, cls, gl)
        except Exception as e:     # said, not hidden
            o = dict(error=repr(e)[:80])
        out[arm] = (r, o)
    os.environ[lg.LEDGER_COUNT_TO_INK_ENV] = "0"
    return out


def main(plate, saved, work):
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    R = load_record(saved)
    rec = R["record"] if "record" in R else R
    pages = LR.loaded_pages(LR.load_sample(), plate)
    obs_all, abs_all = rec["observations"], rec["abstentions"]
    want = ("far_head_ledger_position", "glyph_box", "notehead_staff_position", "staff_lines", "cell_box", "staff_extent",
            "notehead_stem_cross_ink")
    obs = [o for o in obs_all if o.get("quantity") in want]
    abst = [a for a in abs_all if a.get("quantity") == "far_head_ledger_position"]
    row_of = {}     # subject -> (list name, index) of the own far-head row
    for i, o in enumerate(obs_all):
        if o.get("quantity") == "far_head_ledger_position":
            row_of[o["subject"]] = ("observations", i)
    for i, a in enumerate(abs_all):
        if a.get("quantity") == "far_head_ledger_position":
            row_of[a["subject"]] = ("abstentions", i)
    own_owner = {}  # subject -> (list, index) of the own-staff candidate owner row
    for name, lst in (("observations", obs_all), ("abstentions", abs_all)):
        for i, o in enumerate(lst):
            if o.get("quantity") == "far_head_owner_ledger":
                p = o["subject"].split("/")
                own = "staff/%s/%s/%s" % (p[1], p[2], p[3])
                if (o.get("detail") or {}).get("candidate") == own:
                    own_owner[o["subject"]] = (name, i)
    recd = {}
    for o in obs:
        if o["quantity"] == "far_head_ledger_position":
            recd[o["subject"]] = ("pos", int(o["value"]), o["detail"].get("ledger_reason"))
    for a in abst:
        recd[a["subject"]] = ("abs", None, (a.get("detail") or {}).get("ledger_reason"))
    boxes = collections.defaultdict(list)
    geo, conf, staff_lines, cell_box, cross = {}, {}, {}, {}, {}
    for o in obs:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            boxes[LR.page_of(s)].append((s, o["value"][0], tuple(float(v) for v in o["detail"]["bbox_page_px"])))
            conf[s] = o.get("score") or 0.0
        elif q == "notehead_staff_position":
            geo[s] = int(round(float(o["value"])))
        elif q == "staff_lines":
            staff_lines[s] = [float(v) for v in o["value"]]
        elif q == "cell_box":
            cell_box[tuple(int(v) for v in s.split("/")[1:5])] = tuple(float(v) for v in o["value"])
        elif q == "notehead_stem_cross_ink":
            cross[s] = dict(o.get("detail") or {})
    cuts = collections.defaultdict(set)
    for (p, sy, st, _c), bb in cell_box.items():
        cuts[(p, sy, st)].update((bb[0], bb[2]))
    want_n = {}
    for o in obs:
        if o["quantity"] == "far_head_ledger_position":
            src = str(o["detail"].get("shape_source") or "")
            if src.startswith("document pool n="):
                want_n[LR.page_of(o["subject"])] = int(src.split("=")[1])
    pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
    doc_pool = []
    for page in pages:
        hs = []
        for (s, c, b) in boxes[page]:
            p = s.split("/")
            own = "staff/%s/%s/%s" % (p[1], p[2], p[3])
            if c.startswith("notehead") and s in geo and own in staff_lines:
                hs.append(dict(subject=s, box=b, pos=geo[s], cls=c, score=float(conf.get(s, 0.0)), global_lines=staff_lines[own]))
        if hs:
            g0 = cv2.cvtColor(render_page(pdf, page, dpi=600).rgb, cv2.COLOR_RGB2GRAY)
            doc_pool.extend(FH.FarHeadPage(g0, hs, boxes[page], {}, not_a_note={}).samples)
    stats = collections.Counter()
    changes = []
    for page in pages:
        pi = render_page(pdf, page, dpi=600)
        gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
        grid, _unm = r2r.page_grids(pi, staff_lines, page)
        heads, used, jobs = [], {}, []
        for (s, c, b) in boxes[page]:
            if not c.startswith("notehead") or s not in geo:
                continue
            p = s.split("/")
            own = "staff/%s/%s/%s" % (p[1], p[2], p[3])
            if own not in staff_lines:
                continue
            used[own] = staff_lines[own]
            gl = grid.get((int(p[2]), int(p[3]), int(p[4]))) or staff_lines[own]
            heads.append(dict(subject=s, box=b, pos=geo[s], cls=c, score=float(conf.get(s, 0.0)), global_lines=gl))
            if s in recd:
                jobs.append(dict(subject=s, box=b, cls=c, gl=gl))
        nan = {}
        for j in jobs:
            p = [int(v) for v in j["subject"].split("/")[1:5]]
            ev = dict(cell_box=cell_box.get(tuple(p)), barline_xs=sorted(cuts.get(tuple(p[:3]), ())))
            if j["subject"] in cross:
                ev["cross"] = cross[j["subject"]]
            nan[j["subject"]] = ev
        ctx = FH.FarHeadPage(gray, heads, boxes[page], used, not_a_note=nan)
        if ctx.shape is None and page in want_n:
            ctx.adopt(FH.pooled_shape(doc_pool[:want_n[page]]), "document pool n=%d" % want_n[page])
        for j in jobs:
            s = j["subject"]
            both = read_both(ctx, s, j["box"], j["cls"], j["gl"])
            r0, r1 = both["0"][0], both["1"][0]
            g0 = ("pos", r0["pos"], r0["reason"]) if r0["pos"] is not None else ("abs", None, r0["reason"])
            g1 = ("pos", r1["pos"], r1["reason"]) if r1["pos"] is not None else ("abs", None, r1["reason"])
            w = recd[s]
            repro = g0[0] == w[0] and g0[1] == w[1] and (g0[0] == "pos" or g0[2] == w[2])
            if not repro:
                stats["off_does_not_reproduce"] += 1
                continue
            stats["repro"] += 1
            if (g1[0], g1[1]) == (g0[0], g0[1]):
                stats["same"] += 1
                continue
            stats["changed_%s_to_%s" % (g0[0], g1[0])] += 1
            changes.append(dict(subject=s, off=list(g0), on=list(g1), box=[round(float(v), 1) for v in j["box"]]))
            # rewrite the own far-head row
            name, i = row_of[s]
            row = copy.deepcopy(rec[name][i])
            det = dict(row.get("detail") or {})
            det["ledger_reason"] = r1["reason"]
            det["r3_on_arm"] = True
            row["detail"] = det
            if g1[0] == "pos":
                row["value"] = int(r1["pos"])
                det.setdefault("box_source", r1.get("box_source"))
                det.setdefault("shape_source", r1.get("shape_source"))
                det.pop("reason", None)
                row.pop("reason", None)
            else:
                row["value"] = None
                row["reason"] = "ledger_not_read"
            stats["row_kind_moved"] += int((name == "observations") != (g1[0] == "pos"))
            rec[name][i] = None
            (rec["observations"] if g1[0] == "pos" else rec["abstentions"]).append(row)
            # the own-staff owner candidate
            if s in own_owner:
                o0, o1 = both["0"][1], both["1"][1]
                on_, oi = own_owner[s]
                orow = rec[on_][oi]
                if orow is None or "error" in o0 or "error" in o1:
                    stats["owner_row_skipped"] += 1
                    continue
                ov = orow.get("value")
                if (o0.get("pos") if o0.get("fits") else None) != (int(ov) if (on_ == "observations" and ov is not None) else None):
                    stats["owner_off_not_repro"] += 1
                    continue
                nrow = copy.deepcopy(orow)
                nd = dict(nrow.get("detail") or {})
                nd["ledger_reason"] = o1.get("reason")
                nd["r3_on_arm"] = True
                nrow["detail"] = nd
                if o1.get("fits"):
                    nrow["value"] = int(o1["pos"])
                    nrow.pop("reason", None)
                else:
                    nrow["value"] = None
                    nrow["reason"] = orow.get("reason") or "ledger_not_read"
                rec[on_][oi] = None
                (rec["observations"] if o1.get("fits") else rec["abstentions"]).append(nrow)
                stats["owner_rewritten"] += 1
        print(plate, "page", page, dict(stats), flush=True)
    for k in ("observations", "abstentions"):
        rec[k] = [r for r in rec[k] if r is not None]
    json.dump(dict(stats=dict(stats), changes=changes), open(work / ("%s.r3changes.json" % plate), "w"), default=str)
    print(plate, "FINAL", dict(stats), flush=True)
    return R


def readjudicate(R, out):
    from tools.omr.staged.review import rerun as RR
    rec = R["record"] if "record" in R else R
    rec = dict(rec)
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    res = {"record": log.to_json(), "summary": log.summary()}
    pathlib.Path(out).write_text(json.dumps(res, default=str))


if __name__ == "__main__":
    plate, saved, work = sys.argv[1], sys.argv[2], sys.argv[3]
    arm = sys.argv[4] if len(sys.argv) > 4 else "both"
    W = pathlib.Path(work)
    if arm in ("off", "both"):
        R0 = load_record(saved)
        readjudicate(R0, W / ("%s.off.gathered.record.json" % plate))
        del R0
        print(plate, "off arm written", flush=True)
    if arm in ("on", "both"):
        R1 = main(plate, saved, work)
        readjudicate(R1, W / ("%s.on.gathered.record.json" % plate))
        print(plate, "on arm written", flush=True)
