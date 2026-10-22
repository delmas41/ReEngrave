"""ROADMAP 2.87 round 2: BLIND tiles for Sean. NOT product code. Only the print, a big number, ONE plain question and red corner
brackets on the SUBJECT head. Nothing of ours is drawn (no stem lines, no verdicts).

Tiles 1-5 ask "does this note have TWO stems, one up and one down?" (the `unison_two_voices` readings: 1 Brahms, 3 Litolff, + one more),
tiles 6-7 are CONTROLS (a note with one stem: expected "no") so a Yes-to-everything cannot pass, tiles 8-9 ask how many beams the note
has (the two Litolff durations `head_contact` took from decided to narrowed).

Frame control (it can fail): the bracket must lie on ink, against the same box moved two staff spaces away.
    python3 make_tiles2.py <scratch dir with the arm records>
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "1.7-far-notes-review"))
sys.path.insert(0, str(HERE.parents[3]))
import phone_tile as P
from tools.omr.hand_truth.session import _render
from tools.omr.staged.record_io import load_record

SP = Path(sys.argv[1])
BP = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
LP = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
recs = {"B": load_record(SP / "both-brahms.json")["record"], "L": load_record(SP / "both-litolff.json")["record"]}
pdfs = {"B": BP, "L": LP}
Q1 = "Two stems on this note?"
Q2 = "1 beam or none?"

def boxes(r):
    out = {}
    for o in r["observations"]:
        if o["quantity"] == "glyph_box":
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b: out[o["subject"]] = b
    return out
BX = {k: boxes(v) for k, v in recs.items()}

def pick_controls(k, n, seed):
    r = recs[k]
    ones = [v["subject"] for v in r["verdicts"] if v["quantity"] == "head_stem" and v["reason"] == "one_stem" and v["subject"].startswith("glyph/1/")]
    rnd = random.Random(seed); rnd.shuffle(ones)
    out = []
    for s in ones:
        b = BX[k].get(s)
        if b and (b[2] - b[0]) > 30 and (b[3] - b[1]) > 22: out.append(s)
        if len(out) == n: break
    return out

uni = [("B", "glyph/1/0/6/0/13"), ("L", "glyph/1/0/3/11/1"), ("L", "glyph/2/0/3/1/0"), ("L", "glyph/2/0/2/7/2"), ("L", "glyph/2/0/0/5/6")]
ctl = [("B", s) for s in pick_controls("B", 2, 11)]
dur = [("L", "glyph/2/1/10/0/1"), ("L", "glyph/2/1/10/0/14")]
order = [(k, s, Q1, "unison") for k, s in uni] + [(k, s, Q1, "control") for k, s in ctl] + [(k, s, Q2, "duration") for k, s in dur]
rnd = random.Random(5); rnd.shuffle(order)          # blind: the kind is not readable from the order
pages = {}
manifest = []
for n, (k, s, q, kind) in enumerate(order, 1):
    pg = int(s.split("/")[1]); key = (k, pg)
    if key not in pages:
        im = _render(pdfs[k], pg, 600); b = im.binary
        pages[key] = np.where(b < 128 if b.dtype != bool else b, 0, 255).astype(np.uint8)
    pix = pages[key]; x0, y0, x1, y1 = BX[k][s]
    ink = (pix[int(y0):int(y1), int(x0):int(x1)] == 0).mean()
    moved = max((pix[int(y0 + dy):int(y1 + dy), int(x0 + dx):int(x1 + dx)] == 0).mean() for dx, dy in ((100, 0), (-100, 0), (0, 100), (0, -100)))
    if ink < 0.12:
        print("FRAME CONTROL FAILED", n, s, round(float(ink), 3)); raise SystemExit(3)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (550, 325) if k == "B" else (260, 165)   # Litolff's staff space is ~half Brahms'
    win = (cx - hw, cy - hh, cx + hw, cy + hh)
    body, scale, (ox, oy) = P.crop_scaled(pix, win, width=1000)
    d = P.ImageDraw.Draw(body); pad = 6
    P.corner_brackets(d, ((x0 - pad - ox) * scale, (y0 - pad - oy) * scale, (x1 + pad - ox) * scale, (y1 + pad - oy) * scale), thick=5, arm=24)
    top = P.banner(1000, n, q, [("red corners = the note", P.RED), ("  (two stems = one up AND one down)" if q == Q1 else "  (a beam is the thick bar joining notes)", P.GREY)], subtitle=f"tile {n} of {len(order)}")
    P.save_small(P.compose(top, body), HERE / f"tile_{n:02d}.png")
    manifest.append({"n": n, "file": f"tile_{n:02d}.png", "question": q, "subject": s, "kind_HIDDEN": kind, "page_box_600dpi": [round(v, 1) for v in (x0, y0, x1, y1)],
                     "frame_ink_here": round(float(ink), 3), "frame_ink_moved_max": round(float(moved), 3)})
    print(n, kind, s, "ink", round(float(ink), 3), "moved", round(float(moved), 3))
(HERE / "manifest.json").write_text(json.dumps({"note": "blind; kind_HIDDEN is for scoring only", "tiles": manifest}, indent=1) + "\n")
(HERE / "answers.template.json").write_text(json.dumps({"judge": "sean", "answers": {str(m["n"]): "" for m in manifest}}, indent=1) + "\n")
