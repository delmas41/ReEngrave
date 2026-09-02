"""Is there a stroke through the C — asked by POSITION, not by shape.

Adding `timeSigCutCommon` to the candidate list fails twice (`sweep_cutC.json`):
it reads a meter on nine systems that print none, AND it still loses to the plain
`C` on the two pages that really print a cut common (Mozart 40: 10 of 11 staves
vote `C`; Brahms 4: 12 of 13). The second half is the interesting one and it is
not a tuning problem — a `C` template is a SUBSET of a cut-C's ink, so on a real
cut common both templates match and the one with less ink to account for wins.
No threshold between two NCC scores can fix that; a bigger template is not
rewarded for the extra ink it explains.

So this probe asks the question the way the clef and key-signature work learned
to ask it: **where is the ink**, not what shape is it. A cut common is a common
with a vertical stroke through the middle, and that stroke is somewhere a plain C
has nothing:

    A   the CENTRE COLUMN of the glyph, over the C's own vertical extent — the
        C's aperture faces right, so its middle is hollow;
    B   the rows immediately ABOVE and BELOW the C, still in the centre column —
        the stroke overshoots the bowl in every face that draws one.

Both are measured here over every staff whose winning template is `C`, on pages
that print a real cut common, on pages that print a real C, and on pages that
print no meter at all and matched one anyway. A discriminator has to separate all
three; the third is the population the 08 work could not have had.

    python3 benchmarks/omr-timesig-2026-09/probe_cut_stroke.py
    python3 benchmarks/omr-timesig-2026-09/probe_cut_stroke.py --only mozart40-p1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.header_ink import staff_metrics  # noqa: E402
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import (  # noqa: E402
    header_cells_for_page,
    header_windows_for_page,
)
from tools.omr.time_signature_locator import (  # noqa: E402
    DEFAULT_LOCATOR_CONFIG,
    _meter_templates,
)

BENCH = Path(__file__).resolve().parent
CORPUS = json.loads((BENCH / "corpus.json").read_text())
LIB = Path(CORPUS["library_root"])
REPO = Path(__file__).resolve().parents[2]

GRADUS = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
PHASE4 = REPO / "benchmarks" / "omr-phase4-extension" / "output"
WTC_BOOK = GRADUS / "PDF Scores" / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf"

#: (label, pdf, page, what the page prints) — only pages where a `C` can be
#: matched are useful here, so this is the C / cut-C slice of both corpora plus
#: the meterless pages that produced a false cut-C in `sweep_cutC.json`.
CASES: list[tuple[str, Path, int, str]] = [
    ("mozart40-p1", LIB / CORPUS["cases"][0]["pdf"], 0, "cut"),
    ("brahms4-p1", LIB / CORPUS["cases"][2]["pdf"], 0, "cut"),
    ("bruckner5-p1", LIB / CORPUS["cases"][4]["pdf"], 0, "cut"),
    ("mozart41-p1", LIB / CORPUS["cases"][5]["pdf"], 0, "common"),
    ("ravel-bolero", PHASE4 / "ravel-bolero.pdf", 0, "common"),
    ("handel-reduction", PHASE4 / "handel-reduction.pdf", 0, "common"),
    ("bach-wtc", PHASE4 / "bach-wtc.pdf", 0, "common"),
    ("wtc-book-p2", WTC_BOOK, 2, "common-then-none"),
    ("wtc-book-p3", WTC_BOOK, 3, "none"),
    ("mozart41-p2", LIB / CORPUS["cases"][6]["pdf"], 1, "none"),
    ("beet3-p2", LIB / CORPUS["cases"][8]["pdf"], 1, "none"),
    ("mozart40-p2", LIB / CORPUS["cases"][1]["pdf"], 1, "none"),
]


def measure_cell(cell, config=DEFAULT_LOCATOR_CONFIG) -> dict | None:
    """Match every meter template in one header cell and, if `C` wins, measure
    the two stroke statistics at the winning position."""
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, bottom_y = metrics
    if spacing <= 0:
        return None
    image = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if image is None:
        return None
    if image.ndim == 3:
        image = image[:, :, 0]
    scale = (config.template_em_px / 4.0) / spacing
    ink = cv2.resize((255 - image).astype(np.uint8), None, fx=scale, fy=scale,
                     interpolation=cv2.INTER_AREA)
    pad = int(round(config.band_pad_spaces * config.template_em_px / 4.0))
    y0 = max(0, int(round(top_y * scale)) - pad)
    y1 = min(ink.shape[0], int(round(bottom_y * scale)) + pad)
    strip = ink[y0:y1, :]
    if strip.size == 0:
        return None

    best = None
    for key, template in _meter_templates(config.template_em_px, tuple(config.meters)):
        if template.shape[0] > strip.shape[0] or template.shape[1] > strip.shape[1]:
            continue
        response = cv2.matchTemplate(strip, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(response)
        if best is None or score > best[1]:
            best = (key, score, loc, template.shape)
    if best is None:
        return None
    (num, den, raw), score, (mx, my), (th, tw) = best
    out = {"raw": raw, "score": round(float(score), 4)}
    if raw != "C" or score < config.min_score:
        return out

    # The glyph occupies the middle two of the template's four staff spaces —
    # the C is centred on the staff's middle line. Everything below is measured
    # relative to THAT box, not to the four-space template box.
    space = config.template_em_px / 4.0
    box = strip[my:my + th, mx:mx + tw].astype(np.float32) / 255.0
    glyph_top, glyph_bot = int(round(space)), int(round(3 * space))
    centre = slice(int(round(tw * 0.40)), int(round(tw * 0.60)))

    def _rows_inked(y_a: int, y_b: int) -> float:
        band = box[max(0, y_a):min(box.shape[0], y_b), centre]
        if band.size == 0:
            return 0.0
        return float((band.max(axis=1) > 0.5).mean())

    over = int(round(space * 0.35))  # how far a stroke overshoots, ~1/3 space
    return out | {
        # A: how much of the C's own height is inked down its middle
        "centre_fill": round(_rows_inked(glyph_top, glyph_bot), 3),
        # B: the overshoot, above and below the bowl, same column
        "over_above": round(_rows_inked(glyph_top - over, glyph_top), 3),
        "over_below": round(_rows_inked(glyph_bot, glyph_bot + over), 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    rows = []
    for label, pdf, page_index, truth in CASES:
        if args.only and label != args.only:
            continue
        if not Path(pdf).is_file():
            print(f"{label:<18} MISSING {pdf}")
            continue
        page = render_page(Path(pdf), page_index, dpi=600)
        pws = detect_barlines(detect_staves(page))
        cells = header_cells_for_page(pws, windows=header_windows_for_page(pws))
        by_system: dict[int, list[int]] = {}
        for staff in pws.staves:
            by_system.setdefault(staff.system_index, []).append(staff.staff_index)
        for system_index in sorted(by_system):
            for staff_index in sorted(by_system[system_index]):
                if staff_index not in cells:
                    continue
                m = measure_cell(cells[staff_index])
                if m is None or "centre_fill" not in m:
                    continue
                rows.append({"case": label, "truth": truth, "system": system_index,
                             "staff": staff_index, **m})
                print(f"{label:<18} sys{system_index} st{staff_index:2d} "
                      f"{truth:<16} score={m['score']:.3f} "
                      f"centre={m['centre_fill']:.2f} "
                      f"above={m['over_above']:.2f} below={m['over_below']:.2f}")

    (BENCH / "cut_stroke.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"\n{len(rows)} staves matched C above threshold")
    for truth in ("cut", "common", "common-then-none", "none"):
        sel = [r for r in rows if r["truth"] == truth]
        if not sel:
            continue
        for stat in ("centre_fill", "over_above", "over_below"):
            vals = sorted(r[stat] for r in sel)
            print(f"  {truth:<18} {stat:<12} n={len(vals):3d}  "
                  f"min {vals[0]:.2f}  med {vals[len(vals) // 2]:.2f}  "
                  f"max {vals[-1]:.2f}")


if __name__ == "__main__":
    main()
