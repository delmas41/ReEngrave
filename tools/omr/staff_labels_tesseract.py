"""Read instrument labels off the margin with Tesseract — the free middle tier.

`staff_labels.read_staff_labels` gets identity from a PDF's text layer for
nothing, but only 18 of 65 IMSLP score PDFs have one and it is often partial when
they do. `staff_labels_vision` reads the margin with Claude and is measured at
ceiling, but costs about a cent per system. This sits between them: the same
margin pixels, read locally and free.

## What it is worth, measured

`benchmarks/omr-margin-labels-2026-08/TESSERACT_2026-08-31.md`, two hand-verified
pages, 29 printed labels:

    text layer   0 of 12 on Beethoven 5 p.48 (that edition has no text layer)
    tesseract   26 of 29 = 90%, 1 wrong, 0 invented
    vision      29 of 29

So it recovers most of the margin for nothing. It does NOT replace the vision
tier, and the reason is that label accuracy overstates it: a lost label does not
cost one staff, it collapses the pinned block that label opens. On p.48
`Tr. Alt.` reads as `A.` and the trombone block starts one staff late, so the
alto, tenor and bass clefs all move — **one misread character costs three
clefs**, 17/17 down to 14/17. Its errors land on the QUALIFIED abbreviations
(`Tr. Alt.`, `Kl. Tr.`) that separate members of a section, which are exactly the
staves whose clefs differ from their neighbours'.

## Design

**One read per system**, like the vision tier, so a label is attached to the
staves it sits beside rather than to the page.

**Never overrides a higher tier.** `contextual._labels_for_page` uses this to
FILL staves the readers above it left unlabelled, never to replace a label one of
them already found. It is the least accurate reader in the ladder and the one
most likely to return a plausible wrong word, so it is additive only.

**It sits BELOW Surya, and the two are not redundant.** Surya 2 reads better —
as accurate as Claude on everything the text layer can check, at 89% of the yield
(`SURYA_BAKEOFF_2026-08-31.md`) — but it wants a Python 3.10 venv and llama.cpp.
Tesseract wants a brew binary. Both rungs call `available()` first, so a machine
with either never pays for the margin and a machine with neither falls straight
through to Claude.

**psm 6 at 2×**, which was the best of a swept grid (psm 4/6/11/12 × upscale ×
binarise) and best on BOTH benchmark pages, so it is one setting rather than a
per-page pick.

**Words are attached to the nearest staff centre** and joined in reading order,
which is what turns `Fl.` above `pic.` into `Fl. pic.` — Tesseract reports
position but has no idea what a staff is.
"""

from __future__ import annotations

import logging

from .instruments import lookup
from .staff_labels import StaffLabel
from .staff_labels_vision import margin_strip
from .types import PageWithStaves, Staff

logger = logging.getLogger(__name__)

# The best of a swept grid, and best on both benchmark pages — see the module
# docstring. `psm 6` reads the strip as one uniform block, which beats the
# "sparse text" modes because the labels really are a single column.
PSM = 6
UPSCALE = 2
# Tesseract's own per-word confidence, 0-100. Below this the word is noise —
# staff-line fragments and bar numbers read as letters.
MIN_WORD_CONF = 30.0


def available() -> bool:
    """Is there a working Tesseract to call?"""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception:                                       # noqa: BLE001
        return False
    return True


def _words(image, upscale: int = UPSCALE) -> list[tuple[float, float, str]]:
    """`(y centre, x, word)` in STRIP coordinates, for words worth keeping."""
    import pytesseract
    from PIL import Image

    work = image
    if upscale > 1:
        work = work.resize((work.width * upscale, work.height * upscale),
                           Image.LANCZOS)
    data = pytesseract.image_to_data(
        work, config=f"--psm {PSM}", output_type=pytesseract.Output.DICT)
    out = []
    for text, conf, left, top, height in zip(
            data["text"], data["conf"], data["left"], data["top"], data["height"]):
        text = (text or "").strip()
        try:
            confidence = float(conf)
        except (TypeError, ValueError):
            continue
        if not text or confidence < MIN_WORD_CONF:
            continue
        out.append(((top + height / 2.0) / upscale, left / upscale, text))
    return out


def read_system_labels(pws: PageWithStaves,
                       staves: list[Staff]) -> dict[int, str]:
    """`{staff_index: text}` for one system's margin, from OCR."""
    strip, y0 = margin_strip(pws, staves)
    if strip is None:
        return {}
    try:
        words = _words(strip)
    except Exception as exc:                                # noqa: BLE001
        # Loud, and for the same reason the vision tier is: an OCR pass that
        # could not RUN returns the same empty result as a margin with nothing
        # printed on it, and those two want opposite responses.
        logger.error("margin OCR FAILED (%s: %s) — 0 labels here means the "
                     "reader did not run, not that the margin is empty",
                     type(exc).__name__, exc)
        return {}

    centres = [((s.top_y + s.bottom_y) / 2.0) - y0 for s in staves]
    if not centres:
        return {}
    grouped: dict[int, list[tuple[float, float, str]]] = {}
    for y, x, text in words:
        nearest = min(range(len(centres)), key=lambda i: abs(centres[i] - y))
        grouped.setdefault(nearest, []).append((y, x, text))

    out: dict[int, str] = {}
    for position, found in grouped.items():
        # Reading order within a staff: top to bottom, then left to right. That
        # is what joins a two-line "Fl." / "pic." into one label.
        joined = " ".join(t for _, _, t in sorted(found, key=lambda w: (w[0], w[1])))
        if joined.strip():
            out[staves[position].staff_index] = joined.strip()
    return out


def read_staff_labels_tesseract(pws: PageWithStaves) -> list[StaffLabel]:
    """Instrument labels for a page, read from the margin with Tesseract.

    Same return shape as `staff_labels.read_staff_labels` and
    `staff_labels_vision.read_staff_labels_vision`, so the three are
    interchangeable and a caller can tier them.
    """
    if not available():
        logger.info("tesseract not available; the free OCR tier is skipped")
        return []

    by_system: dict[int, list[Staff]] = {}
    for staff in sorted(pws.staves, key=lambda s: s.top_y):
        by_system.setdefault(staff.system_index, []).append(staff)

    out: list[StaffLabel] = []
    for _system_index, staves in sorted(by_system.items()):
        texts = read_system_labels(pws, staves)
        for staff in staves:
            text = texts.get(staff.staff_index)
            if not text:
                continue
            hit = lookup(text)
            out.append(StaffLabel(
                staff_index=staff.staff_index,
                text=text,
                instrument=hit.instrument if hit else None,
                fifths_offset=hit.fifths_offset if hit else 0,
                y_center_px=(staff.top_y + staff.bottom_y) / 2.0,
                confidence=hit.confidence if hit else "none",
                alias=hit.alias if hit else "",
            ))
    return out
