"""ROADMAP 2.96 -- the held-bar funnel re-run on the 2026-10-11 night records.

PATH: STAGED (EXPORT-only: the record is loaded once, exported with today's
exporter, never re-gathered, never re-decided).

`held_funnel_mvt_2_22.py` is reused WHOLE (its `dump` wraps the exporter's own
`_bar_holds_out`; its control -- bars captured == `bars_held_out_sum` minus
bars on a doubled staff -- must PASS). This script then ENRICHES each captured
bar with the evidence the 2.22 dump did not carry, read straight off the
record's rows (nothing re-derived by a reader of ours):

  * `ink`: the cell's `Q.CELL_INK_PIECES` row, and the pieces NO standing glyph
    box explains (2.80's `_missed_rest_witness` rule, restated over dicts:
    boxes a DECIDED not-a-notehead / not-a-rest took out do not explain, a
    box decided a whole rest does; stems/barline crumbs ignored);
  * `dots`: the cell's `Q.AUG_DOT` rows and each dot's `Q.DOT_ROLE` verdict;
  * `cell_w_px` / `sys_cell_w_median_px`: for a missed barline (a cell twice
    its neighbours' width);
  * per event: the owner verdict, the duration verdict (outcome, reason) and the
    beam-doubt counters its detail carries.

    python3 .../held_funnel_2_96.py <record.json> --label L --out-dir D
"""
from __future__ import annotations

import argparse
import collections
import gc
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

T0 = time.time()


def say(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def _cell(sub):
    p = (sub or "").split("/")
    if len(p) >= 5 and p[0] in ("glyph", "cell"):
        return tuple(int(x) for x in p[1:5])
    return None


BEAM_DOUBT = ("beams_ledger_line", "beams_slash", "beams_neighbour_staff",
              "beams_decided_arc", "beams_not_by_ink", "beams_far_side",
              "beams_beyond_stem")

# restated from consequences.py (2.80); the numbers are that file's, copied so
# this probe is a read of the same rule. If they drift the witness-rate check in
# FINDINGS is the control.
THIN, TALL, TALL_THIN, SHARE, MERGED_SP2, EXPL_MAX_W = 0.3, 4.5, 0.8, 0.5, 3.5, 8.0


def shape_class(w, h):
    """A rest-shaped ink piece, by size in staff spaces (a HEURISTIC, named: the
    print crops are the check). eighth/16th ~0.65 x 1.2-1.8 after line erasure;
    quarter ~0.9 x 2.5-3.2; half/whole ~1.2 x 0.5."""
    if 0.8 <= w <= 2.2 and 0.25 <= h <= 0.9:
        return "half_whole"
    if 0.5 <= w <= 1.6 and 2.3 < h <= 3.8:
        return "quarter"
    if 0.4 <= w <= 1.4 and 0.9 <= h <= 2.3:
        return "eighth"
    return "other"


def unexplained(pieces, space, boxes, centres):
    out = []
    for (x0, y0, x1, y1, _a) in pieces:
        w, h = (x1 - x0) / space, (y1 - y0) / space
        if w <= THIN:
            continue
        if h >= TALL and w <= TALL_THIN:
            continue
        import numpy as np
        wi, hi = int(np.ceil(x1 - x0)), int(np.ceil(y1 - y0))
        if wi <= 0 or hi <= 0:
            continue
        mask = np.zeros((hi, wi), dtype=bool)
        for (bx0, by0, bx1, by1) in boxes:
            ix0, iy0, ix1, iy1 = max(x0, bx0), max(y0, by0), min(x1, bx1), min(y1, by1)
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            mask[int(iy0 - y0):int(np.ceil(iy1 - y0)),
                 int(ix0 - x0):int(np.ceil(ix1 - x0))] = True
        cov = float(mask.mean())
        if cov >= SHARE:
            continue
        if w * h > MERGED_SP2 and any(x0 <= cx <= x1 and y0 <= cy <= y1
                                      for cx, cy in centres):
            continue
        out.append({"box": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                    "w_sp": round(w, 2), "h_sp": round(h, 2),
                    "cls": shape_class(w, h)})
    return out


def enrich(doc, path_in, path_out):
    from tools.omr.staged.record import Q
    from tools.omr.staged.review import rerun as RR

    d = json.load(open(path_in))
    rec = doc["record"] if "record" in doc else doc
    held = {tuple(b["cell"]): b for b in d["bars"]}
    standing = RR._verdict_index(rec["verdicts"])
    gone_q = (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)

    def v(q, s):
        return standing.get((q, s))

    cell_boxes = {}                       # (p,s,st,c) -> box
    pieces = {}
    glyph_boxes = collections.defaultdict(list)    # held cell -> [(sub, bbox_page)]
    words = collections.defaultdict(list)
    dots = collections.defaultdict(list)
    for o in rec["observations"]:
        q = o["quantity"]
        if q == Q.CELL_BOX:
            cell_boxes[_cell(o["subject"])] = o["value"]
            continue
        c = _cell(o["subject"])
        if q == Q.CELL_INK_PIECES:
            pieces[c] = o
            continue
        if q == Q.GLYPH_BOX:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp and len(bp) == 4:
                glyph_boxes[c].append((o["subject"], bp))
            continue
        if q == Q.DIRECTION_WORD:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp and len(bp) == 4:
                words[c].append(bp)
            continue
        if c not in held:
            continue
        if False:
            pass
        elif q == Q.GLYPH_BOX:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp and len(bp) == 4:
                glyph_boxes[c].append((o["subject"], bp))
        elif q == Q.DIRECTION_WORD:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp and len(bp) == 4:
                words[c].append(bp)
        elif q == Q.AUG_DOT:
            dots[c].append(o)
    say("enrich: rows indexed")

    by_sys = collections.defaultdict(list)
    for c, bx in cell_boxes.items():
        if bx:
            by_sys[c[:2]].append(bx[2] - bx[0])
    sys_med = {k: statistics.median(vs) for k, vs in by_sys.items()}

    ctr = collections.Counter()

    def ink_for(c):
        pr = pieces.get(c)
        if pr is None:
            return {"answer": "unread"}
        space = (pr.get("detail") or {}).get("staff_space_page_px")
        pcs = (pr.get("detail") or {}).get("pieces")
        if not space or pcs is None:
            return {"answer": "unread"}
        boxes, centres = [], []
        for sub, bp in glyph_boxes[c]:
            gone = any((vv := v(q_, sub)) and vv["outcome"] == "decided"
                       and vv.get("value") is True for q_ in gone_q)
            whole = v(Q.NOTEHEAD_IS_A_WHOLE_REST, sub)
            is_whole = bool(whole and whole["outcome"] == "decided"
                            and whole.get("value") is True)
            eight = v(Q.NOTEHEAD_IS_AN_EIGHTH_REST, sub)
            is_8 = bool(eight and eight["outcome"] == "decided"
                        and eight.get("value") is True)
            if gone and not (is_whole or is_8):
                continue
            if (bp[2] - bp[0]) / space > EXPL_MAX_W:
                continue
            boxes.append(tuple(bp))
            centres.append(((bp[0] + bp[2]) / 2, (bp[1] + bp[3]) / 2))
        for bp in words[c]:
            boxes.append(tuple(bp))
        un = unexplained(pcs, space, boxes, centres)
        return {"answer": "unexplained" if un else "clear",
                "space_px": space, "n_pieces": len(pcs), "unexplained": un}

    # BASE RATE (the control the witness needs): the same test over every cell
    # that is NOT held. If good bars carry unexplained ink as often as held
    # ones, "unexplained ink" is not evidence of a missed mark.
    base = collections.Counter()
    base_sizes = collections.Counter()
    for c in pieces:
        if c in held:
            continue
        r = ink_for(c)
        base[r["answer"]] += 1
        for u in r.get("unexplained") or []:
            base_sizes[(round(u["w_sp"]), round(u["h_sp"]))] += 1
        for cl in {u["cls"] for u in r.get("unexplained") or []}:
            base["cells_with_" + cl] += 1
    d["ink_base_rate_non_held_cells"] = dict(base)
    d["ink_base_sizes_non_held_cells"] = {f"{k[0]}x{k[1]}": n for k, n in
                                          base_sizes.most_common(40)}
    for c, b in held.items():
        bx = cell_boxes.get(c)
        b["cell_w_px"] = (bx[2] - bx[0]) if bx else None
        b["sys_cell_w_median_px"] = sys_med.get(c[:2])
        b["ink"] = ink_for(c)
        ctr["ink_" + b["ink"]["answer"]] += 1
        b["dots"] = [{"subject": o["subject"], "score": o.get("score"),
                      "value": o["value"],
                      "role": (lambda x: None if not x else
                               {"outcome": x["outcome"], "value": x.get("value"),
                                "reason": x.get("reason")})(
                                    v(Q.DOT_ROLE, o["subject"]))}
                     for o in dots[c]]
        for s in b["streams"]:
            for e in s:
                e["owner"] = [(lambda x: None if not x else x["outcome"])(
                    v(Q.GLYPH_OWNER, g)) for g in e["glyphs"]]
                dv = [v(Q.DURATION, g) for g in e["glyphs"]]
                e["dur"] = [None if not x else
                            {"outcome": x["outcome"], "reason": x.get("reason"),
                             "beam_doubt": {k: (x.get("detail") or {}).get(k)
                                            for k in BEAM_DOUBT
                                            if (x.get("detail") or {}).get(k)},
                             "cv_beams": (x.get("detail") or {}).get("cv_beams"),
                             "yolo_beams": (x.get("detail") or {}).get("yolo_beams"),
                             "beam_evidence": (x.get("detail") or {}).get(
                                 "beam_evidence")} for x in dv]
    d["enrich_counters"] = dict(ctr)
    d["phase"] = "own"
    json.dump(d, open(path_out, "w"), default=str)
    say(f"enrich: {dict(ctr)} -> {path_out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    import held_funnel_mvt_2_22 as H
    from tools.omr.staged.record_io import load_record
    say(f"loading {a.record}")
    doc = load_record(a.record)
    say("loaded")
    ok = H.dump(doc, a.label, "own", out_dir, False)
    gc.collect()
    enrich(doc, out_dir / f"{a.label}-own.held.json",
           out_dir / f"{a.label}-2.96.held.json")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
