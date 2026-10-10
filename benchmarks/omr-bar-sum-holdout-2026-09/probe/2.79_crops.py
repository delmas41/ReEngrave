"""2.79 blind print crops: Brahms 1/i Breitkopf (317803) pdf page 1, system 0.

A crop of the plate at the gather's own DPI (600) in the gather's own frame
(`render_page` deskews, and the record's page px are in that frame), a red
corner bracket on the BAR, and NOTHING of ours drawn. Our readings go in the
manifest, not on the image.

Frame control (it can fail): the five staff lines the record filed for the
staff must stand out in the crop -- mean ink on the five line rows >= 2x the
mean ink on the four rows half a space between them. The same measure shifted
half a staff space is run as the NEGATIVE control and must FAIL.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
       "symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--"
       "imslp317803.pdf")
PAGE = 1
SYSTEM = 0
OUT = Path(sys.argv[2])
rec = load_record(sys.argv[1])
import xml.etree.ElementTree as ET


def read_bar(path, part_id, bar):
    """What a MusicXML says about one bar of one part: the time in force, and
    each note/rest with its duration. Divisions are reported with it."""
    root = ET.parse(path).getroot()
    for part in root.findall("part"):
        if part.get("id") != part_id:
            continue
        div = time = None
        for m in part.findall("measure"):
            a = m.find("attributes")
            if a is not None:
                if a.find("divisions") is not None:
                    div = int(a.findtext("divisions"))
                if a.find("time") is not None:
                    time = "%s/%s" % (a.findtext("time/beats"), a.findtext("time/beat-type"))
            if int(m.get("number")) == bar:
                ev = []
                for e in m.findall("note"):
                    if e.find("chord") is not None:
                        continue
                    d = int(e.findtext("duration"))
                    if e.find("rest") is not None:
                        ev.append("measure rest" if e.find("rest").get("measure") == "yes" else "rest")
                        ev[-1] += " (duration %d)" % d
                    else:
                        ev.append("note (duration %d)" % d)
                held = any(e.tag == "direction" for e in m)
                return {"time_written": time, "divisions": div, "events": ev,
                        "bar_length_in_units": None if not (div and time) else
                        int(round(div * 4 * int(time.split("/")[0]) / int(time.split("/")[1])))}
    return None


BASE_XML, C1_XML, AFTER_XML = sys.argv[3], sys.argv[4], sys.argv[5]
PART_OF_STAFF = {1: "P2", 4: "P5", 12: "P13", 13: "P14"}
PART_NAME = {1: "Oboe", 4: "Contrabassoon", 12: "Cello", 13: "Contrabass"}

obs = rec["record"]["observations"]
cell_box, staff_lines = {}, {}
for o in obs:
    p = o["subject"].split("/")
    if o["quantity"] == "cell_box" and p[0] == "cell" and p[1] == str(PAGE) and p[2] == str(SYSTEM):
        cell_box[(int(p[3]), int(p[4]))] = o["value"]
    elif o["quantity"] == "staff_lines" and p[0] == "staff" and p[1] == str(PAGE) and p[2] == str(SYSTEM):
        staff_lines[int(p[3])] = o["value"]

img = render_page(PDF, PAGE, dpi=600).rgb          # deskewed RGB, record frame
gray = np.asarray(Image.fromarray(img).convert("L")).astype(float)
ink = 255.0 - gray


def frame_control(box, lines, shift=0.0):
    x0, x1 = int(box[0]) + 40, int(box[2]) - 40
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return {"ink_on_lines": round(on, 1), "ink_between": round(off, 1),
            "ratio": round(on / max(off, 1e-6), 2), "passes": bool(on >= 2.0 * off)}


def bracket(arr, x0, y0, x1, y1, arm=46, thick=6, colour=(220, 0, 0)):
    h, w = arr.shape[:2]

    def hline(y, xa, xb):
        arr[max(y - thick // 2, 0):y + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour

    def vline(x, ya, yb):
        arr[max(ya, 0):min(yb, h), max(x - thick // 2, 0):x + thick // 2 + 1] = colour

    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        hline(cy, cx, cx + dx * arm) if dx > 0 else hline(cy, cx + dx * arm, cx)
        vline(cx, cy, cy + dy * arm) if dy > 0 else vline(cx, cy + dy * arm, cy)


# (file, staff, first_cell, last_cell, bracket_cell, part, bar_label)
SPECS = [
    ("1-bar10-contrabassoon.png", 4, 0, 3, 2),
    ("2-bar12-oboe.png", 1, 3, 5, 4),
    ("3-bar14-contrabass.png", 13, 4, 6, 6),
    ("4-bar10-cello.png", 12, 0, 3, 2),
    ("5-bar13-contrabass.png", 13, 4, 6, 5),
    ("6-bar13-cello.png", 12, 4, 6, 5),
    ("7-bar14-cello.png", 12, 4, 6, 6),
]
OUT.mkdir(parents=True, exist_ok=True)
manifest = {"dpi": 600, "pdf": PDF, "pdf_page_index": PAGE, "system": SYSTEM,
            "frame": "the gather's own (render_page, deskewed); crops are of the plate, "
                     "a red corner bracket on the bar, nothing of ours drawn",
            "question": "In the bracketed bar, is there ONE whole rest and nothing else, "
                        "and is the bar six eighths long (the time signature 6/8 printed at "
                        "the bar before)?",
            "tiles": []}
for i, (name, staff, c0, c1, cb) in enumerate(SPECS, 1):
    lines = staff_lines[staff]
    first, last, bar = cell_box[(staff, c0)], cell_box[(staff, c1)], cell_box[(staff, cb)]
    pad = 70
    # one bar of lead-in on the left where there is one: the printed 6/8 sits there
    wx0, wy0 = int(first[0]) - pad, int(first[1]) - pad
    wx1, wy1 = int(last[2]) + pad, int(last[3]) + pad
    crop = img[wy0:wy1, wx0:wx1].copy()
    # ⚠️ THE BRACKET FOLLOWS THE STAFF, NOT THE PADDED CELL: the cell box is
    # padded 4 spaces and on a conductor's page that reaches the neighbours'
    # ink, so a bracket on it frames three staves. Staff lines +-1.3 spaces.
    sp = float(np.mean(np.diff(lines)))
    bx0, bx1 = int(bar[0]) - wx0 + 6, int(bar[2]) - wx0 - 6
    by0, by1 = int(lines[0] - 1.3 * sp) - wy0, int(lines[-1] + 1.3 * sp) - wy0
    bracket(crop, bx0, by0, bx1, by1)
    Image.fromarray(crop).save(OUT / name)
    fc = frame_control(bar, lines)
    neg = frame_control(bar, lines, shift=0.5)
    tile = {
        "n": i, "file": name, "staff_index": staff,
        "cells_shown": [c0, c1], "bar_bracketed_cell": cb,
        "bar_number": cb + 8,
        "page_box_600dpi": [wx0, wy0, wx1, wy1],
        "bar_box_600dpi": [int(v) for v in bar],
        "bracket_box_600dpi": [bx0 + wx0, by0 + wy0, bx1 + wx0, by1 + wy0],
        "staff_lines_600dpi": [int(v) for v in lines],
        "frame_control": fc,
        "frame_control_negative_shifted_half_a_space": neg,
        "part": PART_NAME[staff],
        "our_reading_overnight_tree_26fdb4d0_small_rerun": read_bar(BASE_XML, PART_OF_STAFF[staff], cb + 8),
        "our_reading_after_commit_1_rest_sizing_only": read_bar(C1_XML, PART_OF_STAFF[staff], cb + 8),
        "our_reading_after_commit_2_reconcile_and_reinstate_too": read_bar(AFTER_XML, PART_OF_STAFF[staff], cb + 8),
    }
    assert fc["passes"], (name, fc)
    assert not neg["passes"], ("the control cannot fail", name, neg)
    manifest["tiles"].append(tile)
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("wrote", OUT, [t["file"] for t in manifest["tiles"]])
