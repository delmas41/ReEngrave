"""Read instrument labels off the page margin with Claude, for scans with no
text layer.

`staff_labels.read_staff_labels` gets instrument identity for free from a PDF's
text layer, but only 18 of 65 IMSLP score PDFs have one. This module covers the
rest: crop the left margin, ask Claude to read the printed labels, and put the
answers through the same `instruments.lookup` the text-layer path uses.

## Why this is a different task from the failed VLM pilot

`benchmarks/vlm-vqa-pilot-2026-07` found Claude tops out at 89.7% on narrow
visual questions about degraded orchestral cells — *counting noteheads, rests
and accidentals*. That was a NO-GO for a symbol verifier and it is worth taking
seriously, but it does not transfer here: this asks the model to **read printed
words** in a clean margin, which is what a vision model is actually good at.
Different task, so it gets its own measurement — see
`benchmarks/omr-margin-labels-2026-08/`.

## Design

**One call per system, not per staff.** The margin of a whole system is a
compact vertical strip, and sending it whole gives the model the context a
reader uses: the labels form a known running order, so seeing `Fl. / Ob. / Cl.`
above makes a smudged fourth entry legible as `Fag.`.

**The crop is annotated with staff indices.** A gutter is drawn on the left
carrying each staff's index and a tick at its vertical centre, and the model is
asked to key its answer to those numbers. Matching by order instead would break
on exactly the common case — strings are routinely unlabelled below the first
system, so the label count and the staff count disagree.

**Unlabelled staves must come back as null.** The prompt says so explicitly and
the schema allows it; a model that invents a plausible instrument for an
unlabelled staff is worse than one that abstains, because a wrong instrument
propagates through slots into a wrong clef and wrong pitches.

## Requires a current SDK, on the HOST

Structured outputs (`output_config.format`) need `anthropic>=0.116`, which is
what `backend/requirements.txt` pins for the container. This module also runs
host-side, outside that container, and an old host SDK raises
`TypeError: create() got an unexpected keyword argument 'output_config'` —
measured on a host carrying 0.28.0. That failure is caught per system so one bad
page cannot kill a batch, but it is logged at ERROR precisely because zero
labels from a broken dependency and zero labels from an unlabelled margin are
otherwise the same observation.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
from dataclasses import dataclass

import numpy as np

from .instruments import lookup
from .staff_labels import StaffLabel
from .types import PageWithStaves, Staff

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"

# How far left of the staves to crop, in staff-line spacings. Instrument names
# sit between the page edge and the bracket.
#
# 14.0 was the original guess and it DID NOT clear the longest spelled-out names,
# despite the comment that used to say so. Measured 2026-08-31 on 12 systems of
# Beethoven 5 and 6 (`benchmarks/omr-margin-labels-2026-08/SURYA_BAKEOFF_2026-08-31.md`): at
# 14 the crop cuts through the first letters — "Clarinetti" arrives as
# "arinetti", "Timpani in C.G" as "ani in C.G", "Viola" as "Fola". Claude repairs
# those from context and so the damage was invisible while it was the only
# reader; an OCR engine transcribes them faithfully and the lexicon rejects them.
#
# Worse, the narrow crop provoked REPETITION: on 2 of 12 systems Surya emitted
# one label seven times over, 20 surplus lines in all, which the row assignment
# then spread across staves that carry no label at all. At 20.0 that is zero.
#
# 20.0 rather than 26.0 because the two measured identically, so 20 is the
# smaller change that gets the whole benefit. Claude scored 36/0/19 at both 14
# and 20 — byte-identical tallies — so this is free for the paid reader and
# worth 91% -> 94% agreement for the free one.
MARGIN_SPACINGS = 20.0
# ...and how far INTO the staves, for scores that print the name tight against
# the bracket.
OVERLAP_SPACINGS = 1.0

GUTTER_PX = 70          # drawn on the left, carrying each staff's index
MAX_EDGE_PX = 1568      # the API downsizes above this; do it ourselves, once

_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "staff_index": {"type": "integer"},
                    "text": {
                        "type": ["string", "null"],
                        "description": "The instrument label printed beside this "
                                       "staff, exactly as printed. null if this "
                                       "staff has no label.",
                    },
                },
                "required": ["staff_index", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["labels"],
    "additionalProperties": False,
}

_PROMPT = """This is the left margin of one system of an orchestral score, rotated \
upright. Each staff is marked in the grey gutter on the left with its index number \
and a tick at the staff's vertical centre.

Read the instrument label printed beside each numbered staff and return it exactly \
as printed, including any key designation — "Cl. B", "Cor. D.", "2 Clarinetti in B", \
"Fl.", "Vla.".

Rules:
- Report one entry per numbered staff, using the number from the gutter.
- If a staff has NO label printed beside it, return null for that staff. Do not \
guess from position or from the instruments above it. Strings in particular are \
often left unlabelled, and an invented label is worse than none.
- Transcribe what is printed. Do not expand abbreviations, translate them, or \
correct spelling."""


@dataclass(frozen=True)
class MarginCrop:
    """A rendered margin strip and the staff indices drawn on it.

    `tick_ys` and `gutter_px` are in the FINAL image's pixels, after any
    downscale, and exist for readers that return boxes rather than answers.
    Claude is told to key its reply to the numbers in the gutter and so needs
    none of this; an OCR engine hands back text and coordinates, and something
    has to say which staff a given y belongs to. Carrying the geometry that
    `build_margin_crop` already knows beats recovering it from the pixels — the
    Surya bake-off did the latter and had to detect the grey gutter and cluster
    dark rows to do it.
    """

    png: bytes
    staff_indices: list[int]
    tick_ys: tuple[float, ...] = ()
    gutter_px: int = GUTTER_PX


def _spacing(staves: list[Staff]) -> float:
    vals = [s.line_spacing_px for s in staves if s.line_spacing_px]
    return (sum(vals) / len(vals)) if vals else 10.0


def margin_strip(pws: PageWithStaves, staves: list[Staff]):
    """The bare margin beside `staves`: `(PIL image, y offset into the page)`.

    Split out from `build_margin_crop` so that every reader of the margin — the
    vision model, the OCR tier, and the benchmark that compares them — is
    provably looking at the same pixels. The annotated crop below is this strip
    plus a gutter; nothing else differs.
    """
    from PIL import Image

    if not staves:
        return None, 0
    page = pws.page
    height, width = page.binary.shape
    spacing = _spacing(staves)

    # Median absorbs the broken x_start values a degraded scan produces.
    x_starts = sorted(s.x_start for s in staves)
    x_ref = x_starts[len(x_starts) // 2]
    x0 = max(0, int(x_ref - MARGIN_SPACINGS * spacing))
    x1 = min(width, int(x_ref + OVERLAP_SPACINGS * spacing))
    y0 = max(0, min(s.top_y for s in staves) - int(2 * spacing))
    y1 = min(height, max(s.bottom_y for s in staves) + int(2 * spacing))
    if x1 <= x0 or y1 <= y0:
        return None, 0
    return Image.fromarray(page.rgb[y0:y1, x0:x1]).convert("RGB"), y0


def build_margin_crop(pws: PageWithStaves, staves: list[Staff]) -> MarginCrop | None:
    """Crop the margin beside `staves` and annotate it with their indices."""
    from PIL import Image, ImageDraw

    strip, y0 = margin_strip(pws, staves)
    if strip is None:
        return None
    canvas = Image.new("RGB", (strip.width + GUTTER_PX, strip.height), (255, 255, 255))
    canvas.paste(strip, (GUTTER_PX, 0))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, GUTTER_PX - 1, canvas.height], fill=(232, 232, 232))
    indices, tick_ys = [], []
    for staff in staves:
        cy = int((staff.top_y + staff.bottom_y) / 2) - y0
        if not (0 <= cy < canvas.height):
            continue
        draw.line([GUTTER_PX - 14, cy, GUTTER_PX - 1, cy], fill=(0, 0, 0), width=3)
        draw.text((6, cy - 6), str(staff.staff_index), fill=(0, 0, 0))
        indices.append(staff.staff_index)
        tick_ys.append(float(cy))
    if not indices:
        return None

    scale = MAX_EDGE_PX / max(canvas.width, canvas.height)
    gutter = GUTTER_PX
    if scale < 1.0:
        canvas = canvas.resize((max(1, int(canvas.width * scale)),
                                max(1, int(canvas.height * scale))),
                               Image.LANCZOS)
        # The ticks and the gutter shrink with the canvas, so a reader working
        # in final-image pixels needs them scaled too.
        tick_ys = [y * scale for y in tick_ys]
        gutter = max(1, int(GUTTER_PX * scale))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return MarginCrop(png=buf.getvalue(), staff_indices=indices,
                      tick_ys=tuple(tick_ys), gutter_px=gutter)


def read_system_labels(crop: MarginCrop, *, client=None, model: str = DEFAULT_MODEL,
                       max_tokens: int = 2048) -> dict[int, str]:
    """`{staff_index: printed label}` for one system's margin crop.

    Staves the model reports as unlabelled are simply absent from the result.
    """
    if client is None:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png",
                    "data": base64.standard_b64encode(crop.png).decode("utf-8"),
                }},
                {"type": "text", "text": _PROMPT},
            ],
        }],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    if response.stop_reason == "refusal":
        logger.warning("margin label read refused: %s", response.stop_details)
        return {}

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("margin label read returned unparseable JSON")
        return {}

    wanted = set(crop.staff_indices)
    out: dict[int, str] = {}
    for entry in data.get("labels", []):
        idx, label = entry.get("staff_index"), entry.get("text")
        # Only indices we actually drew — a hallucinated staff number is not a staff.
        if idx in wanted and isinstance(label, str) and label.strip():
            out[idx] = label.strip()
    return out


def read_staff_labels_vision(pws: PageWithStaves, *, client=None,
                             model: str = DEFAULT_MODEL) -> list[StaffLabel]:
    """Instrument labels for a page, read from the margin with Claude.

    Same return shape as `staff_labels.read_staff_labels`, so the two are
    interchangeable and a caller can fall back from the free text-layer path to
    this one. One API call per system.
    """
    by_system: dict[int, list[Staff]] = {}
    for staff in sorted(pws.staves, key=lambda s: s.top_y):
        by_system.setdefault(staff.system_index, []).append(staff)

    out: list[StaffLabel] = []
    failures = 0
    for _sys_index, staves in sorted(by_system.items()):
        crop = build_margin_crop(pws, staves)
        if crop is None:
            continue
        try:
            texts = read_system_labels(crop, client=client, model=model)
        except Exception as exc:                      # noqa: BLE001
            # ERROR, not warning, and naming the exception type: a read that
            # could not RUN returns the same empty result as a margin with
            # nothing printed on it, and those two want opposite responses.
            # `output_config` unexpected-keyword here means the host's anthropic
            # SDK predates structured outputs — see the module docstring.
            logger.error("margin label read FAILED on system %s (%s: %s) — "
                         "0 labels here means the reader did not run, not that "
                         "the margin is empty",
                         _sys_index, type(exc).__name__, exc)
            failures += 1
            continue
        for staff in staves:
            text = texts.get(staff.staff_index)
            if not text:
                continue
            hit = lookup(text)
            centre = (staff.top_y + staff.bottom_y) / 2.0
            out.append(StaffLabel(
                staff_index=staff.staff_index,
                text=text,
                instrument=hit.instrument if hit else None,
                fifths_offset=hit.fifths_offset if hit else 0,
                y_center_px=centre,
                confidence=hit.confidence if hit else "none",
                alias=hit.alias if hit else "",
            ))
    if failures:
        logger.error("margin label read: %d of %d systems FAILED; the %d labels "
                     "returned are from the systems that ran",
                     failures, len(by_system), len(out))
    return out
