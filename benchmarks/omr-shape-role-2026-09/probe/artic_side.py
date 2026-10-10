"""ROADMAP 2.12f — where does an articulation's MEASURED side (above / below the
notehead it is printed against) disagree with the side its class NAME states,
and what does the geometry look like, BEFORE any cut is chosen?

The audit (`FINDINGS.md` Sec.1 row 3) counted 1,134 boxes by comparing a
mark's y to "the nearest notehead in x, any side". That is not what the
staged owner pick does: `adjudicate_articulation_owner` takes the suffix as a
PREMISE (only heads on the declared side are candidates), so it never reports
a disagreement -- it abstains `no_notehead`, or attaches to a different head.
This probe reproduces the audit's number AND counts what the owner pick did
with each disagreeing mark, so the reach of the repair is a count of rows and
not of boxes.

For every `Q.ARTICULATION_MARK` row it reports, in the cell's own canonical
frame (a mark and the head beside it are one frame by construction, so the
difference is a LOCAL measurement -- CLAUDE.md Sec.10, no staff-wide value):

  * the mark's class, suffix side (`detail.side`);
  * the heads inside the SAME x window the owner pick uses (0.75 median
    notehead widths of the mark's centre), side-blind;
  * the side-blind pick (nearest in x, ties -> nearest in y) and the SIGNED
    dy to it in staff spaces (positive = the mark is ABOVE the head), plus the
    edge-to-edge gap;
  * what the standing `Q.ARTICULATION_OWNER` verdict did (decided/abstained,
    reason), and whether its owner is the side-blind pick.

READ-ONLY. Decides nothing, changes no code. Every record is read through
`record_io.load_record` (via `role_disagreement.Rec`), never a naive json.load.

    python3 benchmarks/omr-shape-role-2026-09/probe/artic_side.py \
        --record <path> --label <id> --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from role_disagreement import Rec, _box_value, _cell_of, _staff_of  # noqa: E402

#: The owner pick's own x window (`transcribe._ARTIC_MAX_DX_NOTEHEAD_WIDTHS`),
#: IMPORTED so this probe cannot drift from the decision it measures.
from tools.omr import transcribe as _legacy  # noqa: E402

_LIMIT = _legacy._ARTIC_MAX_DX_NOTEHEAD_WIDTHS


def _suffix_side(cls: str):
    if cls.endswith("Above"):
        return "above"
    if cls.endswith("Below"):
        return "below"
    return None


def measure(r: Rec) -> dict:
    # heads per cell: (subject, x, y, w, h) -- category notehead only, the owner
    # pick's own population (it reads `detail.category == "notehead"`).
    heads = collections.defaultdict(list)
    for subj, o in r.box.items():
        if (o.get("detail") or {}).get("category") != "notehead":
            continue
        b = _box_value(o["value"])
        if b is None:
            continue
        heads[_cell_of(subj)].append((subj,) + b[1:])

    # every notehead on a page in PAGE pixels, for the cross-staff question:
    # is the head the class names on ANOTHER staff than the one the mark was
    # filed under? (a canonical x/y is meaningless across two staves)
    page_heads = collections.defaultdict(list)
    for subj, o in r.box.items():
        if (o.get("detail") or {}).get("category") != "notehead":
            continue
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb:
            page_heads[int(subj.split("/")[1])].append(
                (subj, _staff_of(subj), [float(v) for v in bb]))

    owners = r.verdict.get("articulation_owner", {})
    # the STAFF ruler (`Q.ARTICULATION_POSITION`): where the mark stands against
    # ITS OWN cell's staff -- the independent view of the class name's side.
    pos = {o["subject"]: o for o in r.by_q.get("articulation_position", ())}
    rows = []
    for o in r.by_q.get("articulation_mark", ()):
        d = o.get("detail") or {}
        cls = str(o["value"])
        cell = _cell_of(o["subject"])
        sp = r.cell_space_px(o["subject"])
        cands = heads.get(cell) or []
        row = {"subject": o["subject"], "cell": cell, "class": cls,
               "mark_bbox_page": d.get("bbox_page_px"),
               "page": int(o["subject"].split("/")[1]),
               "suffix_side": d.get("side") or _suffix_side(cls),
               "score": o.get("score")}
        po = (pos.get(o["subject"]) or {}).get("detail") or {}
        row["staff_side"] = po.get("measured_side")
        row["steps_outside_staff"] = po.get("steps_outside_staff")
        v = owners.get(o["subject"])
        row["owner_outcome"] = v["outcome"] if v else None
        row["owner_reason"] = v.get("reason") if v else None
        row["owner_value"] = v.get("value") if v and v["outcome"] == "decided" else None
        try:
            mx = (float(d["x0"]) + float(d["x1"])) / 2.0
            y0, y1 = float(d["y0"]), float(d["y1"])
        except (KeyError, TypeError, ValueError):
            row["unmeasurable"] = "no_box"
            rows.append(row)
            continue
        my = (y0 + y1) / 2.0
        if not cands or not sp:
            row["unmeasurable"] = "no_head_in_cell" if not cands else "no_staff_space"
            rows.append(row)
            continue
        widths = sorted(c[3] for c in cands)
        nh_w = widths[len(widths) // 2] or 1.0
        lim = nh_w * _LIMIT
        in_win = []
        for (hs, hx, hy, hw, hh) in cands:
            dx = abs(mx - (hx + hw / 2.0))
            if dx <= lim:
                in_win.append((dx, hs, hx, hy, hw, hh))
        row["n_heads_in_window"] = len(in_win)
        # every head the x window admits, side-blind: where the geometry has a
        # CHOICE to make is a property of this list and not of any one pick.
        win = []
        for (wdx, whs, whx, why, whw, whh) in in_win:
            whyc = why + whh / 2.0
            wgap = (why - y1) if my < whyc else (y0 - (why + whh))
            win.append({"head": whs, "dx_widths": round(wdx / nh_w, 3),
                        "dy_spaces": round((whyc - my) / sp, 3),
                        "gap_spaces": round(wgap / sp, 3),
                        "side": "above" if my < whyc else "below",
                        "bbox_page": (r.box[whs].get("detail") or {}
                                      ).get("bbox_page_px")})
        row["window"] = win
        if not in_win:
            row["unmeasurable"] = "no_head_in_x_window"
            rows.append(row)
            continue
        # side-blind pick: nearest in x; within 0.25 widths of the best dx the
        # heads are one stacked column, so break the tie by nearest in y.
        best_dx = min(w[0] for w in in_win)
        col = [w for w in in_win if w[0] <= best_dx + 0.25 * nh_w]
        pick = min(col, key=lambda w: abs(my - (w[3] + w[5] / 2.0)))
        dx, hs, hx, hy, hw, hh = pick
        hyc = hy + hh / 2.0
        row["blind_pick"] = hs
        row["pick_bbox_page"] = (r.box[hs].get("detail") or {}).get("bbox_page_px")
        row["dx_head_widths"] = round(dx / nh_w, 3)
        row["dy_spaces"] = round((hyc - my) / sp, 3)      # + = mark ABOVE head
        # edge-to-edge: + = a clear gap between mark and head; - = overlap
        if my < hyc:
            gap = hy - y1
        else:
            gap = y0 - (hy + hh)
        row["gap_spaces"] = round(gap / sp, 3)
        row["head_h_spaces"] = round(hh / sp, 3)
        row["blind_side"] = "above" if my < hyc else "below"
        # cross-staff: a head on the DECLARED side, in another staff, in the
        # same page-pixel x window, within the same reach (1.5 head heights).
        mb = d.get("bbox_page_px")
        suf = row["suffix_side"]
        row["declared_side_head_elsewhere"] = None
        if mb and suf:
            pg = row["page"]
            hs_all = page_heads.get(pg, [])
            wp = sorted(b[2] - b[0] for _s, _st, b in hs_all)
            medw = wp[len(wp) // 2] if wp else 0
            mxp = (mb[0] + mb[2]) / 2.0
            found = []
            for hsub, hst, hb in hs_all:
                if hst == _staff_of(o["subject"]):
                    continue
                hh_p = hb[3] - hb[1]
                if abs((hb[0] + hb[2]) / 2.0 - mxp) > _LIMIT * medw:
                    continue
                gap_p = (hb[1] - mb[3]) if suf == "above" else (mb[1] - hb[3])
                if gap_p < 0 or gap_p > 1.5 * hh_p:
                    continue
                found.append({"head": hsub, "staff": hst,
                              "gap_heads": round(gap_p / hh_p, 3)})
            row["declared_side_head_elsewhere"] = found
        row["blind_pick_is_owner"] = (row["owner_value"] == hs
                                       if row["owner_value"] else None)
        # the audit's own measure: nearest in x only, any side
        ax = min(cands, key=lambda c: abs(mx - (c[1] + c[3] / 2.0)))
        row["audit_side"] = "above" if my < ax[2] + ax[4] / 2.0 else "below"
        rows.append(row)
    return {"rows": rows}


def summarize(rows: list) -> dict:
    out = {"marks": len(rows)}
    c = collections.Counter()
    for r in rows:
        c["class:" + r["class"]] += 1
        c["owner:%s/%s" % (r["owner_outcome"], r["owner_reason"])] += 1
        if "unmeasurable" in r:
            c["unmeasurable:" + r["unmeasurable"]] += 1
            continue
        suf = r["suffix_side"]
        if suf is None:
            c["no_suffix_side"] += 1
        elif suf != r["blind_side"]:
            c["suffix_vs_blind_DISAGREE"] += 1
            c["disagree_owner:%s/%s" % (r["owner_outcome"], r["owner_reason"])] += 1
        else:
            c["suffix_vs_blind_agree"] += 1
        if suf is not None and suf != r["audit_side"]:
            c["audit_measure_DISAGREE"] += 1
        if r["owner_outcome"] == "decided":
            c["decided_blind_pick_is_owner" if r["blind_pick_is_owner"]
              else "decided_blind_pick_differs"] += 1
    out["counts"] = dict(sorted(c.items()))
    # signed dy histogram (staff spaces, 0.25 bins, clipped at +-6)
    hist = collections.Counter()
    for r in rows:
        if "dy_spaces" in r:
            b = max(-6.0, min(6.0, r["dy_spaces"]))
            hist[round(int(b * 4 // 1) / 4.0, 2)] += 1
    out["dy_hist_0.25"] = {str(k): hist[k] for k in sorted(hist)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default=None)
    ap.add_argument("--rows", action="store_true", help="include every row")
    a = ap.parse_args(argv)
    r = Rec(Path(a.record))
    m = measure(r)
    res = {"label": a.label, "record": a.record,
           "provenance": {k: r.provenance.get(k) for k in ("commit", "dirty")},
           "pdf": ((r.provenance.get("settings") or {}).get("args") or {}
                   ).get("pdf"),
           "summary": summarize(m["rows"])}
    if a.rows:
        res["rows"] = m["rows"]
    txt = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).write_text(txt)
    print(json.dumps(res["summary"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
