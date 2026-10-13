#!/usr/bin/env python3
"""l288_population: the heads ROADMAP 2.88 is about -- hollow-reading, one-head, own-stem noteheads whose standing ADJUDICATE duration
verdict is NOT 2.70's decided half -- with everything the head and its stem say, read off a saved record (GATHER+ADJUDICATE only,
CLAUDE.md 6b).  Read-only.

Per head (every notehead-classed glyph with a box and a known staff space):
  verdict (outcome:reason + the candidates' beats), status, box h / w in staff spaces, the three `Q.NOTEHEAD_INK` readings'
  `center` / `ring` windows, whether the head has its own stem (`Q.HEAD_STEM`) and its direction, and the `Q.STEM_TIP_INK` row (or the
  abstention reason) at the end the stem points to.

    python3 l288_population.py rec.json [--pages 3,4] [--json out.json] [--show]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

CENTER_MAX, GAP_MIN = 0.75, 0.1


def windows(detail, key):
    r = detail.get(key)
    if not isinstance(r, dict):
        return None
    w = r.get("windows") or {}
    if w.get("center") is None or w.get("ring") is None:
        return None
    return (w["center"], w["ring"])


def build(run):
    space_of = {}
    for o in run.observations:
        if o["quantity"] == Q.CELL_STAFF_SPACE:
            space_of[o["subject"]] = float(o["value"])
    ink = collections.defaultdict(list)
    for o in run.observations:
        if o["quantity"] == Q.NOTEHEAD_INK:
            ink[o["subject"]].append(o)
    tips = collections.defaultdict(list)
    for o in list(run.observations) + list(run.abstentions):
        if o["quantity"] == Q.STEM_TIP_INK:
            tips[o["subject"]].append(o)
    rows = []
    for key, g in run.glyphs.items():
        if not (g.cls or "").startswith("notehead") or not g.box_canon:
            continue
        sp = space_of.get(g.cell_key)
        if not sp:
            continue
        x0, y0, x1, y1 = g.box_canon
        du = run.standing(key, Q.DURATION, "ADJUDICATE")
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        status, why = RD.adjudicate_status(run, g)
        detail = (ink[key][-1].get("detail") or {}) if ink.get(key) else {}
        rd = {k: windows(detail, k) for k in ("ink_raw", "ink_net", "ink_off_line")}
        hollow = [k for k, v in rd.items() if v and v[0] <= CENTER_MAX and (v[1] - v[0]) >= GAP_MIN]
        stem_id = hs.get("value") if hs else None
        side = sd.get("value") if sd else None
        end = {"up": "top", "down": "bottom"}.get(side)
        tip = None
        if stem_id and end:
            for o in tips.get(g.cell_key, []):
                d = o.get("detail") or {}
                if d.get("stem_row_id") == stem_id and d.get("end") == end:
                    tip = {"value": o.get("value"), "reason": o.get("reason"), "witness": d.get("witness"),
                           "tip_disagree": d.get("tip_disagree"), "why": d.get("why")}
        cands = None
        if du and du.get("outcome") == "narrowed":
            cands = sorted((c.get("value") or {}).get("beats") for c in du.get("candidates") or [])
        rows.append({
            "key": key, "page": g.page, "cls": g.cls, "status": status, "status_reason": why,
            "outcome": du and du.get("outcome"), "reason": du and du.get("reason"),
            "beats": (du.get("value") or {}).get("beats") if du and du.get("outcome") == "decided" else None,
            "cands": cands, "h_sp": round((y1 - y0) / sp, 2), "w_sp": round((x1 - x0) / sp, 2),
            "ink": rd, "hollow_on": hollow, "stem": bool(stem_id), "side": side, "tip": tip,
            "box_page": list(g.box_page) if g.box_page else None,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--pages")
    ap.add_argument("--json")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    rows = build(run)
    if a.pages:
        ps = {int(p) for p in a.pages.split(",")}
        rows = [r for r in rows if r["page"] in ps]
    if a.json:
        Path(a.json).write_text(json.dumps(rows))
    c = collections.Counter((r["outcome"], r["reason"]) for r in rows if r["hollow_on"])
    print(a.record, len(rows), "noteheads;", sum(1 for r in rows if r["hollow_on"]), "read hollow on >=1 raster")
    for k, n in c.most_common():
        print(f"  {n:5d}  {k[0]}:{k[1]}")
    if a.show:
        for r in rows:
            if r["hollow_on"] and r["reason"] != "hollow_head_bare_stem":
                print(r["key"], r["status"], r["outcome"], r["reason"], r["cands"], "h", r["h_sp"], "w", r["w_sp"], "stem", r["stem"], r["side"], "tip", r["tip"], "hollow", r["hollow_on"])


if __name__ == "__main__":
    main()
