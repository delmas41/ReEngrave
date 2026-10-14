"""2.117 side-by-side crops: the PRINT bar (nothing of ours drawn on it) above
OUR LilyPond-rendered bar with `OMR_PARTIAL_BARS=1`.

usage: crops.py RECORD PDF EXPORT_DIR OUT_DIR
  EXPORT_DIR holds on.bars.json + on.lilybars.json from the export run.

Legend (also written on every image): black = read, blue = guessed,
red = unread gap (nothing invented). One tile per bar; the last tile is a bar
that STAYS held (its whole bar is red `unread`).

Frame control (it can fail): the five staff lines the record filed for the
staff must stand out in the crop (mean ink on the line rows >= 2x the rows
half a space between), and the same measure shifted half a space must FAIL.
"""
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

REC, PDF, EXP, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
rec = load_record(REC)
bars = json.load(open(EXP / "on.bars.json"))
lily = {tuple(b["where"]): b for b in json.load(open(EXP / "on.lilybars.json"))}

cell_box, staff_lines = {}, {}
for o in rec["record"]["observations"]:
    p = o["subject"].split("/")
    if o["quantity"] == "cell_box" and p[0] == "cell":
        cell_box[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))] = o["value"]
    elif o["quantity"] == "staff_lines" and p[0] == "staff":
        staff_lines[(int(p[1]), int(p[2]), int(p[3]))] = o["value"]

CLEF = {"treble": "treble", "bass": "bass", "alto": "alto", "tenor": "tenor"}


def pick():
    rnd = random.Random(117)
    part = [b for b in bars if b["status"] == "partial" and not b["two_voice"]
            and 3 <= b["events"] <= 9
            and (b["page"], b["system"], b["staff"], b["cell"]) in lily
            and (b["page"], b["system"], b["staff"], b["cell"]) in cell_box]
    rnd.shuffle(part)
    chosen, used_pages = [], set()

    def take(pred, label, n=1):
        k = 0
        for b in part:
            if k >= n:
                break
            if b in [c[0] for c in chosen] or not pred(b):
                continue
            if (b["page"], b["system"]) in used_pages:
                continue
            chosen.append((b, label))
            used_pages.add((b["page"], b["system"]))
            k += 1

    beam = lambda b: "duration_narrowed" in b["unread_glyphs"]
    refused = lambda b: any(r.startswith("not_a_notehead:too_narrow")
                            or r.startswith("not_a_notehead:clipped")
                            for r in b["unread_glyphs"])
    suffix_only = lambda b: sum(b["prefix_events"]) == 0
    prefix_only = lambda b: sum(b["suffix_events"]) == 0
    take(lambda b: beam(b) and sum(b["prefix_events"]) and sum(b["suffix_events"]),
         "beam-narrowed head, prefix + suffix", 2)
    take(lambda b: refused(b) and not beam(b), "head refused as too narrow / clipped", 2)
    take(lambda b: suffix_only(b), "suffix only (the gap opens the bar)", 1)
    take(lambda b: prefix_only(b), "prefix only (the gap closes the bar)", 1)
    held = [b for b in bars if b["status"] == "held"
            and b["why"] == "short_without_an_unread_symbol"
            and not b["two_voice"] and 3 <= b["events"] <= 7
            and (b["page"], b["system"], b["staff"], b["cell"]) in cell_box]
    rnd.shuffle(held)
    for b in held:
        if (b["page"], b["system"]) not in used_pages:
            chosen.append((b, "STAYS HELD: short with no refused symbol, so the "
                              "missing note's place is unknown"))
            break
    return chosen


def our_bar_png(b, entry, held, work):
    meter = entry["meter"] if entry else None
    n, d = ((meter or {}).get("numerator", 4), (meter or {}).get("denominator", 4))
    if held:
        body = ('\\once \\override MultiMeasureRest.color = #red '
                f'R1*{n}/{d}^\\markup {{ "unread" }}')
        clef, key = "treble", 0
    else:
        body = entry["text"]
        clef = CLEF.get(entry["clef"] or "treble", "treble")
    ly = ('\\version "2.24.0"\n\\header { tagline = ##f }\n'
          '\\paper { indent = 0 \\mm  paper-width = 90\\mm  page-breaking = #ly:one-line-breaking }\n'
          '\\layout { \\context { \\Score \\remove "Bar_number_engraver" } }\n'
          f'\\new Staff {{ \\clef {clef} \\time {n}/{d} {body} }}\n')
    src = Path(work) / "bar.ly"
    src.write_text(ly)
    subprocess.run(["lilypond", "-dresolution=170", "--png", "-o", str(Path(work) / "bar"),
                    str(src)], check=True, capture_output=True)
    im = Image.open(Path(work) / "bar.png").convert("RGB")
    arr = np.asarray(im)
    ys, xs = np.where(arr.sum(axis=2) < 740)
    return im.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0),
                    xs.max() + 12, ys.max() + 12))


def frame_control(ink, box, lines, shift=0.0):
    x0, x1 = int(box[0]) + 40, int(box[2]) - 40
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return on >= 2.0 * off


pages = {}
manifest = []
chosen = pick()
for n, (b, label) in enumerate(chosen, 1):
    key = (b["page"], b["system"], b["staff"], b["cell"])
    if b["page"] not in pages:
        pages[b["page"]] = render_page(PDF, b["page"], dpi=600).rgb
    img = pages[b["page"]]
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    box = cell_box[key]
    lines = staff_lines[(b["page"], b["system"], b["staff"])]
    sp = float(np.mean(np.diff(lines)))
    assert frame_control(ink, box, lines), ("frame control", key)
    assert not frame_control(ink, box, lines, 0.5), ("control cannot fail", key)
    y0, y1 = int(lines[0] - 3 * sp), int(lines[-1] + 3 * sp)
    # the bar, with a sliver of its neighbours either side
    x0, x1 = int(box[0]) - int(2 * sp), int(box[2]) + int(2 * sp)
    print_crop = Image.fromarray(img[y0:y1, x0:x1].copy())
    entry = lily.get(key)
    with tempfile.TemporaryDirectory() as work:
        ours = our_bar_png(b, entry, b["status"] == "held", work)
    scale = print_crop.width / max(ours.width, 1)
    if scale < 1.0:
        ours = ours.resize((int(ours.width * scale), int(ours.height * scale)))
    W = max(print_crop.width, ours.width) + 20
    H = print_crop.height + ours.height + 150
    canvas = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(canvas)
    dr.text((10, 6), f"{n}. {label}", fill=(0, 0, 0))
    dr.text((10, 24), "PRINT (nothing of ours drawn)", fill=(90, 90, 90))
    canvas.paste(print_crop, (10, 44))
    yo = 44 + print_crop.height + 14
    dr.text((10, yo), "OURS with OMR_PARTIAL_BARS=1  (black = read, blue = guessed, "
                      "red = unread gap)", fill=(90, 90, 90))
    canvas.paste(ours, (10, yo + 20))
    name = f"{n}-p{b['page']}-s{b['system']}-staff{b['staff']}-cell{b['cell']}.png"
    canvas.save(OUT / name)
    manifest.append({"n": n, "file": name, "label": label, "page": b["page"],
                     "system": b["system"], "staff": b["staff"], "cell": b["cell"],
                     "measure": b["measure"], "status": b["status"], "why": b["why"],
                     "unread_glyphs": b["unread_glyphs"],
                     "prefix_events": b["prefix_events"], "suffix_events": b["suffix_events"],
                     "rows_in_gap": b["rows_in_gap"], "gap_quarters": b["gap_quarters"],
                     "page_box_600dpi": [x0, y0, x1, y1]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("wrote", len(manifest), "tiles to", OUT)
