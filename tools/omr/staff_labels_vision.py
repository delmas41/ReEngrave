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
# sit between the page edge and the bracket; 14 spacings clears the longest
# spelled-out names ("Violoncello e Contrabasso") without pulling in the
# facing page's gutter on a two-up scan.
MARGIN_SPACINGS = 14.0
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
    """A rendered margin strip and the staff indices drawn on it."""

    png: bytes
    staff_indices: list[int]


def _spacing(staves: list[Staff]) -> float:
    vals = [s.line_spacing_px for s in staves if s.line_spacing_px]
    return (sum(vals) / len(vals)) if vals else 10.0


def build_margin_crop(pws: PageWithStaves, staves: list[Staff]) -> MarginCrop | None:
    """Crop the margin beside `staves` and annotate it with their indices."""
    from PIL import Image, ImageDraw

    if not staves:
        return None
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
        return None

    strip = Image.fromarray(page.rgb[y0:y1, x0:x1]).convert("RGB")
    canvas = Image.new("RGB", (strip.width + GUTTER_PX, strip.height), (255, 255, 255))
    canvas.paste(strip, (GUTTER_PX, 0))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, GUTTER_PX - 1, canvas.height], fill=(232, 232, 232))
    indices = []
    for staff in staves:
        cy = int((staff.top_y + staff.bottom_y) / 2) - y0
        if not (0 <= cy < canvas.height):
            continue
        draw.line([GUTTER_PX - 14, cy, GUTTER_PX - 1, cy], fill=(0, 0, 0), width=3)
        draw.text((6, cy - 6), str(staff.staff_index), fill=(0, 0, 0))
        indices.append(staff.staff_index)
    if not indices:
        return None

    scale = MAX_EDGE_PX / max(canvas.width, canvas.height)
    if scale < 1.0:
        canvas = canvas.resize((max(1, int(canvas.width * scale)),
                                max(1, int(canvas.height * scale))),
                               Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return MarginCrop(png=buf.getvalue(), staff_indices=indices)


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
    for _sys_index, staves in sorted(by_system.items()):
        crop = build_margin_crop(pws, staves)
        if crop is None:
            continue
        try:
            texts = read_system_labels(crop, client=client, model=model)
        except Exception as exc:                      # noqa: BLE001
            logger.warning("margin label read failed: %s", exc)
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
    return out
