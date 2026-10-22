"""2.173 side-by-side crops: the PRINT bar (nothing of ours drawn on it) above the SAME bar engraved by our LilyPond path with
`OMR_RED_BARS=1` (the bar's own `_render_bar` text, so what Sean sees is what the exported .ly holds).

usage: crops.py RECORD PDF OUT_DIR DOC N_SHORT N_OVER N_GUESSED
  one tile per bar: N_SHORT short bars, N_OVER overfull bars, N_GUESSED bars holding a GUESSED event (kept in the data, drawn red).
Legend (also on every image): RED bracket + words = the bar does not add up (written with what was read, nothing invented, nothing padded
with a rest); the red bracket's words say should-hold vs counted, in quarters.

Frame control (it can fail): the five staff lines the record filed for the staff must stand out in the print crop (mean ink on
the line rows >= 2x the rows half a space between) and the same measure shifted half a space must FAIL.
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
os.environ["OMR_RED_BARS"] = "1"
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import export as SX  # noqa: E402
from tools.omr.staged import lilypond as LY  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr import export as LEG  # noqa: E402

REC, PDF, OUT, DOC = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
N_SHORT, N_OVER, N_GUESS = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
OUT.mkdir(parents=True, exist_ok=True)
result = load_record(REC)

captured = {}
_orig = LY._render_bar


def _spy(bar, wedges, counters):
    text = _orig(bar, wedges, counters)
    if bar.red is not None and bar.where is not None:
        captured[bar.where] = dict(text=text, clef=bar.clef, key=bar.key, meter=bar.red.get("meter") or bar.meter,
                                   red=bar.red, n=len(bar.events or []) + sum(len(s) for s in (bar.streams or ())),
                                   two=bar.kind == "two_voice", events=bar.events or [])
    return text


LY._render_bar = _spy
LY.to_lilypond(result)
_, rep = SX.to_musicxml(result)
reds = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in rep["bars_written_red"]["bars_list"]}
print(DOC, "red bars captured", len(captured), "listed", len(reds), flush=True)

cell_box, staff_lines = {}, {}
for o in result["record"]["observations"]:
    p = o["subject"].split("/")
    if o["quantity"] == "cell_box" and p[0] == "cell":
        cell_box[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))] = o["value"]
    elif o["quantity"] == "staff_lines" and p[0] == "staff":
        staff_lines[(int(p[1]), int(p[2]), int(p[3]))] = o["value"]


def pool():
    out = []
    for k, c in captured.items():
        b = reds.get(k)
        if (b is None or k not in cell_box or (k[0], k[1], k[2]) not in staff_lines or c["two"]
                or not (3 <= b["events"] <= 8) or b["doubled_staff_copy"] or len(b["counted_quarters"]) != 1):
            continue
        out.append((k, b))
    return out


rnd = random.Random(173)
cands = pool()
rnd.shuffle(cands)
def frame_control(ink, box, lines, shift=0.0):
    x0, x1 = int(box[0]) + 40, int(box[2]) - 40
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return on >= 2.0 * off


pages, manifest = {}, []
checked = {}


def frame_ok(key):
    """The print crop's frame control; True when the staff lines stand out AND the half-space shift fails."""
    if key in checked:
        return checked[key]
    page, system, staff, cell = key
    if page not in pages:
        pages[page] = render_page(PDF, page, dpi=600).rgb
    ink = 255.0 - np.asarray(Image.fromarray(pages[page]).convert("L")).astype(float)
    box, lines = cell_box[key], staff_lines[(page, system, staff)]
    checked[key] = frame_control(ink, box, lines) and not frame_control(ink, box, lines, 0.5)
    return checked[key]


chosen, used = [], set()


def take(pred, label, n):
    k = 0
    for key, b in cands:
        if k >= n:
            break
        if (key[0], key[1]) in used or any(key == c[0] for c in chosen) or not pred(b) or not frame_ok(key):
            continue
        chosen.append((key, b, label))
        used.add((key[0], key[1]))
        k += 1


take(lambda b: b["counted_quarters"][0] < b["want_quarters"] and b["guessed"] == 0, "SHORT bar (all read)", N_SHORT)
take(lambda b: b["counted_quarters"][0] > b["want_quarters"] and b["guessed"] == 0, "OVERFULL bar (all read)", N_OVER)
take(lambda b: b["guessed"] > 0, "bar with a GUESSED note (blue, as in any bar)", N_GUESS)

CLEF = {"treble": "treble", "bass": "bass", "alto": "alto", "tenor": "tenor"}


def our_bar_png(c, work):
    meter = c["meter"] or {}
    n, d = meter.get("numerator", 4), meter.get("denominator", 4)
    clef = LEG._clef_to_lily(c["clef"] or "treble")
    key = LEG._lily_key_name(c["key"] or {})
    ly = ('\\version "2.24.0"\n' + f"guessedColor = #{SX.GUESS_COLOR_LILY}\n"
          '\\header { tagline = ##f }\n'
          '\\paper { indent = 0 \\mm  paper-width = 140\\mm  page-breaking = #ly:one-line-breaking }\n'
          '\\layout { \\context { \\Score \\remove "Bar_number_engraver" } }\n'
          f'\\new Staff {{ \\clef {clef} \\key {key} \\major \\time {n}/{d} {c["text"]} }}\n')
    src = Path(work) / "bar.ly"
    src.write_text(ly)
    subprocess.run(["lilypond", "-dresolution=170", "--png", "-o", str(Path(work) / "bar"), str(src)],
                   check=True, capture_output=True)
    im = Image.open(Path(work) / "bar.png").convert("RGB")
    arr = np.asarray(im)
    ys, xs = np.where(arr.sum(axis=2) < 740)
    return im.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), xs.max() + 12, ys.max() + 12))


for n, (key, b, label) in enumerate(chosen, 1):
    page, system, staff, cell = key
    if page not in pages:
        pages[page] = render_page(PDF, page, dpi=600).rgb
    img = pages[page]
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    box = cell_box[key]
    lines = staff_lines[(page, system, staff)]
    sp = float(np.mean(np.diff(lines)))
    y0, y1 = int(lines[0] - 3 * sp), int(lines[-1] + 3 * sp)
    x0, x1 = int(box[0]) - int(2 * sp), int(box[2]) + int(2 * sp)
    print_crop = Image.fromarray(img[y0:y1, x0:x1].copy())
    with tempfile.TemporaryDirectory() as work:
        ours = our_bar_png(captured[key], work)
    TW = 640
    print_crop = print_crop.resize((TW - 20, int(print_crop.height * (TW - 20) / print_crop.width)), Image.LANCZOS)
    f = min((TW - 20) / ours.width, 2.5)
    ours = ours.resize((int(ours.width * f), int(ours.height * f)), Image.LANCZOS)
    W = TW
    H = print_crop.height + ours.height + 110
    canvas = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(canvas)
    dr.text((10, 6), "%s #%d (%s p%d system %d staff %d bar %s): %s -- should hold %s, counted %s (quarters)"
            % (DOC, n, label, page, system, staff, b["measure"], b["bar_key"], b["want_quarters"],
               b["counted_quarters"]), fill=(0, 0, 0))
    dr.text((10, 24), "PRINT (nothing of ours drawn)", fill=(90, 90, 90))
    canvas.paste(print_crop, (10, 44))
    yo = 44 + print_crop.height + 14
    dr.text((10, yo), "OURS, OMR_RED_BARS=1: red bracket = this bar does not add up; each note keeps its own colour "
                      "(black read, blue guessed); nothing invented, no rest added", fill=(180, 0, 0))
    canvas.paste(ours, (10, yo + 20))
    name = "%s-%d-p%d-s%d-staff%d-cell%d.png" % (DOC, n, page, system, staff, cell)
    canvas.save(OUT / name)
    manifest.append(dict(n=n, file=name, label=label, page=page, system=system, staff=staff, cell=cell,
                         measure=b["measure"], want=b["want_quarters"], counted=b["counted_quarters"],
                         read=b["read"], guessed=b["guessed"], rows=b["rows"]))
(OUT / ("manifest.%s.json" % DOC)).write_text(json.dumps(manifest, indent=1, default=str))
print("wrote", len(manifest), "tiles to", OUT, flush=True)
