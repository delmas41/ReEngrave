"""lane-farhead-5-6 (2026-10-07) step 1: what the far-head reader sees at Sean's two tiles (brahms p25 `25/1/5/5/1`, p18 `18/1/0/5/21`).
Replays the 10-07 reader (per-bar grid) on the gather-frame raster from the 10-07 extract; prints the lines it used, the staff
edge, every ledger row it found, and each step's number. READ ONLY, no gather.
  python3 farhead_5_6_diag.py <x7 extract json> [subject ...]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import night_1007_replay as NR
import overnight_1004_report as R
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg

DEFAULT = ["glyph/25/1/5/5/1", "glyph/18/1/0/5/21"]


def load(src, doc="brahms1-breitkopf"):
    data = json.loads(Path(src).read_text())
    return data, NR.GridReplay(doc, data)


def read_one(rep, data, s):
    g = data["glyphs"][s]
    page = R.page_of(s)
    shape = (g.get("fh") or g.get("fh_abs") or {}).get("shape_source", "page n=0")
    ctx = rep.adopt_for(page, shape)
    gl = rep.head_lines(s)
    cls = next((c for (ss, c, b) in rep.boxes_by_page[page] if ss == s), g.get("cls"))
    r, cap = NR.read_spied(ctx, s, tuple(g["box"]), cls, gl)
    return g, r, cap, gl, ctx


if __name__ == "__main__":
    src = sys.argv[1]
    subs = sys.argv[2:] or DEFAULT
    data, rep = load(src)
    for s in subs:
        g, r, cap, gl, ctx = read_one(rep, data, s)
        print("==", s, "box", g["box"], "recorded", g.get("fh") or g.get("fh_abs"))
        print("  replay pos", r["pos"], "reason", r["reason"])
        print("  lines_used", [round(v, 1) for v in (r.get("lines_used") or [])], "grid", [round(v, 1) for v in gl],
              "raw", [round(v, 1) for v in data["staff_lines"]["staff/" + "/".join(s.split("/")[1:4])]])
        print("  box_used", r.get("box_used"), "cap", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in cap.items() if k != "rungs"},
              "rungs", [round(v, 1) for v in cap.get("rungs", [])])
        d = r.get("detail") or {}
        print("  detail keys", list(d)[:20])
        print("  note_first", json.dumps(d.get("note_first"), default=str)[:600])
