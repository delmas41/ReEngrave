"""
Claude Vision comparison module.
Compares PDF measure images against rendered MusicXML images using Claude's vision API.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import anthropic
from pdf2image import convert_from_path
from PIL import Image

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = "claude-opus-4-5"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MeasureDiff:
    measure_number: int
    instrument: str
    difference_type: str  # note/rhythm/articulation/dynamic/beam/slur/accidental/clef/other
    description: str
    confidence: float
    pdf_image_b64: str = ""
    xml_image_b64: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compare_score_measures(
    pdf_path: str,
    musicxml_path: str,
    score_metadata: dict,
    prompt_version: Optional[str] = None,
) -> list[MeasureDiff]:
    """Main comparison function.

    1. Renders MusicXML measures to PNG images via Verovio.
    2. Extracts measure crops from the PDF.
    3. Sends each pair to Claude Vision for comparison.

    Returns a list of MeasureDiff objects for measures where differences
    were detected.
    """
    tmp_dir = os.path.join(
        os.path.dirname(pdf_path), "tmp_compare"
    )
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    pdf_image_paths = await extract_pdf_measure_images(pdf_path, tmp_dir)
    xml_image_paths = await render_musicxml_to_images(musicxml_path, tmp_dir)

    if not pdf_image_paths or not xml_image_paths:
        # TODO: Handle partial extraction (e.g., multi-page PDFs)
        return []

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    prompt = build_comparison_prompt(score_metadata, measure_num=0)

    # Pair up images by index (assumes 1:1 correspondence)
    pairs = list(zip(pdf_image_paths, xml_image_paths))
    tasks = [
        compare_measure_pair(
            pdf_img,
            xml_img,
            measure_num=i + 1,
            metadata=score_metadata,
            client=client,
            prompt=prompt,
        )
        for i, (pdf_img, xml_img) in enumerate(pairs)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    diffs: list[MeasureDiff] = []
    for r in results:
        if isinstance(r, MeasureDiff):
            diffs.append(r)
        # Silently skip exceptions / None returns for now
        # TODO: Log exceptions for debugging

    return diffs


async def render_musicxml_to_images(
    musicxml_path: str, output_dir: str
) -> list[str]:
    """Render MusicXML measures to PNG images using Verovio CLI.

    TODO: Integrate with Verovio CLI or Python bindings (verovio package).
    Command:  verovio --page-width 400 --page-height 200 --all-pages
              --output {output_dir} {musicxml_path}
    Then split output SVGs and render to PNG via librsvg or cairosvg.

    This stub returns an empty list so the pipeline degrades gracefully.
    """
    # TODO: Replace with actual Verovio subprocess call
    image_paths: list[str] = []

    try:
        proc = await asyncio.create_subprocess_exec(
            "verovio",
            "--page-width", "800",
            "--page-height", "300",
            "--svg",
            "--all-pages",
            "--output", output_dir,
            musicxml_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        # Collect generated SVG files
        svg_files = sorted(Path(output_dir).glob("*.svg"))
        # TODO: Convert SVGs to PNGs using cairosvg or Inkscape
        image_paths = [str(p) for p in svg_files]
    except FileNotFoundError:
        # verovio not installed – return empty list
        pass

    return image_paths


async def extract_pdf_measure_images(
    pdf_path: str, output_dir: str
) -> list[str]:
    """Extract measure-level crops from a PDF using pdf2image.

    Converts each PDF page to an image, then divides horizontally
    into measure-width strips.

    TODO: Implement proper measure boundary detection using:
      - MusicXML measure position data
      - Or image analysis (staff line detection) via OpenCV
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_event_loop()

    def _convert() -> list[Image.Image]:
        return convert_from_path(pdf_path, dpi=150)

    pages: list[Image.Image] = await loop.run_in_executor(None, _convert)

    image_paths: list[str] = []
    for page_idx, page_img in enumerate(pages):
        # Stub: save each full page as a "measure" image
        # TODO: Detect actual measure boundaries and crop precisely
        out_path = os.path.join(output_dir, f"pdf_page_{page_idx + 1:04d}.png")
        page_img.save(out_path, "PNG")
        image_paths.append(out_path)

    return image_paths


async def compare_measure_pair(
    pdf_image_path: str,
    xml_image_path: str,
    measure_num: int,
    metadata: dict,
    client: anthropic.AsyncAnthropic,
    prompt: str,
) -> Optional[MeasureDiff]:
    """Send a PDF/MusicXML image pair to Claude Vision for comparison.

    Returns a MeasureDiff if a difference is found, else None.
    """
    prompt_text = build_comparison_prompt(metadata, measure_num)

    # Encode images to base64
    def _encode(path: str) -> tuple[str, str]:
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        ext = Path(path).suffix.lower().lstrip(".")
        media_type = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        return b64, media_type

    try:
        pdf_b64, pdf_media = _encode(pdf_image_path)
        xml_b64, xml_media = _encode(xml_image_path)
    except FileNotFoundError:
        return None

    message = await client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": pdf_media,
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": xml_media,
                            "data": xml_b64,
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    )

    raw_text = message.content[0].text if message.content else ""

    # Parse structured JSON from Claude's response
    diff_data = _parse_claude_response(raw_text)
    if diff_data is None:
        return None

    return MeasureDiff(
        measure_number=measure_num,
        instrument=metadata.get("instrument", "unknown"),
        difference_type=diff_data.get("difference_type", "other"),
        description=diff_data.get("description", ""),
        confidence=float(diff_data.get("confidence", 0.5)),
        pdf_image_b64=pdf_b64,
        xml_image_b64=xml_b64,
    )


def build_comparison_prompt(metadata: dict, measure_num: int) -> str:
    """Build the Claude Vision comparison prompt from score metadata.

    The prompt instructs Claude to identify specific differences between
    the PDF scan (original) and the MusicXML render (OMR output).

    TODO: Refine this prompt using patterns from ClaudePromptVersion records
    to improve accuracy over time (self-improving agent loop).
    """
    title = metadata.get("title", "Unknown")
    composer = metadata.get("composer", "Unknown")
    era = metadata.get("era", "unknown")
    instrument = metadata.get("instrument", "unknown")

    return f"""You are an expert music engraver reviewing OMR (Optical Music Recognition) output.

You are given two images:
1. LEFT IMAGE: A scan from the original PDF score (ground truth)
2. RIGHT IMAGE: The MusicXML rendered by Audiveris OMR software

Score: "{title}" by {composer} ({era} era)
Instrument: {instrument}
Measure number: {measure_num}

Compare the two images carefully. Identify any differences between them.

Respond ONLY with a JSON object in this exact format:
{{
  "has_difference": true or false,
  "difference_type": one of ["note", "rhythm", "articulation", "dynamic", "beam", "slur", "accidental", "clef", "other"],
  "description": "clear description of the difference",
  "confidence": 0.0 to 1.0 (how confident you are this is a real difference vs OMR error),
  "is_omr_error": true or false (true = the MusicXML is wrong, false = genuine difference)
}}

If there is no meaningful difference, set "has_difference" to false.
Focus on musically significant differences, not minor rendering style variations.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_claude_response(text: str) -> Optional[dict]:
    """Extract and parse JSON from Claude's response text."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Attempt to find a JSON object in the response
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return None
        else:
            return None

    if not data.get("has_difference", False):
        return None

    return data
