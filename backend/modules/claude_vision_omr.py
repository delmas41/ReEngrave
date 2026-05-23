"""
Claude Vision OMR — optical music recognition powered by Claude's vision API.

Reads each page of a PDF score visually, extracts musical content as structured
JSON, and assembles valid MusicXML via the musicxml_builder module.

Drop-in replacement for audiveris_omr: same return type (AudiverisResult),
same interface.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

import anthropic
from pdf2image import convert_from_path
from PIL import Image

from modules.audiveris_omr import AudiverisResult
from modules.musicxml_builder import (
    PageAnalysis,
    ScoreHeader,
    build_musicxml,
    parse_header_json,
    parse_page_json,
    write_musicxml,
)

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = "claude-opus-4-6"
MAX_TOKENS_HEADER = 4096
MAX_TOKENS_PAGE = 32768  # dense orchestral pages need lots of room

# Type alias for the progress callback
ProgressCallback = Callable[[int, int, list[int]], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

HEADER_PROMPT = """\
You are a professional music engraver performing automated OMR. Analyze this first page \
of a music score and identify its structure.

CRITICAL: Your response must start with { and end with }. No text before or after the JSON. \
No markdown fences. No explanation. ONLY the JSON object.

Schema:

{
  "title": "<score title>",
  "composer": "<composer name>",
  "staves": [
    {
      "staff_id": 1,
      "instrument_name": "<e.g. Piano, Violin I>",
      "clef": "<treble or bass or alto or tenor>",
      "key_signature": {"fifths": <-7 to 7>, "mode": "<major or minor>"},
      "time_signature": {"beats": <int>, "beat_type": <int>}
    }
  ]
}

For piano: list TWO staves (staff_id 1 = treble, staff_id 2 = bass), \
both with instrument_name "Piano".

Key signature fifths: 0=C/Am, 1=G, 2=D, -1=F, -2=Bb, etc.

Be precise. Count staves carefully from top to bottom.\
"""


def _page_prompt(header: ScoreHeader, page_num: int, total_pages: int,
                 last_measure_num: int) -> str:
    # Build instrument context
    staff_info = "\n".join(
        f"  Staff {s.staff_id}: {s.instrument_name} ({s.clef_sign} clef)"
        for s in header.staves
    )

    return f"""\
You are a professional music engraver performing automated OMR. \
Read this page of the score "{header.title}" by {header.composer} and extract \
every note, rest, and chord precisely.

CRITICAL: Your response must start with {{ and end with }}. No text before or after. \
No markdown fences. No explanation. No preamble. ONLY the JSON object.

SCORE STRUCTURE (established from page 1):
{staff_info}

This is page {page_num} of {total_pages}. \
The last measure on the previous page was measure {last_measure_num}. \
Continue numbering from measure {last_measure_num + 1}.

Return ONLY valid JSON (no markdown fences, no explanation) with this schema:

{{
  "page_number": {page_num},
  "measures": [
    {{
      "number": <int>,
      "staves": [
        {{
          "staff_id": <int>,
          "voices": [
            {{
              "voice": 1,
              "elements": [
                {{
                  "type": "note",
                  "pitch": {{"step": "C", "octave": 5, "alter": 0}},
                  "duration": "quarter",
                  "dots": 0,
                  "tie": null,
                  "articulations": [],
                  "fermata": false
                }},
                {{
                  "type": "rest",
                  "duration": "half",
                  "dots": 0
                }},
                {{
                  "type": "chord",
                  "pitches": [
                    {{"step": "C", "octave": 4, "alter": 0}},
                    {{"step": "E", "octave": 4, "alter": 0}}
                  ],
                  "duration": "half",
                  "dots": 0
                }}
              ]
            }}
          ],
          "directions": [
            {{"type": "dynamic", "value": "mf"}},
            {{"type": "tempo", "value": "Allegro", "bpm": 120}}
          ]
        }}
      ]
    }}
  ]
}}

IMPORTANT RULES:
- "alter": -1 for flat, 1 for sharp, 0 for natural. Include accidentals as shown.
- "duration": one of "whole", "half", "quarter", "eighth", "16th", "32nd", "64th"
- "tie": "start", "stop", or null
- Include ALL voices. If a staff has multiple voices, list each separately.
- For piano: staff_id 1 = treble (right hand), staff_id 2 = bass (left hand)
- Read every single note. Do not summarize or skip repetitions.
- If a measure has a key or time signature change, add "key_change" or "time_change" \
to the staff object.
- Last measure on last page: add "barline": "light-heavy" to the measure object.
- Be extremely precise with pitch octaves. Middle C = C4.
"""


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from Claude's response, handling markdown fences and truncation."""
    # Strip markdown fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)(?:```|$)", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find the first { ... } block
    brace_start = text.find("{")
    if brace_start == -1:
        return None

    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace_start : i + 1])
                except json.JSONDecodeError:
                    return None

    # JSON was truncated — try to salvage by closing open brackets
    truncated = text[brace_start:]
    result = _repair_truncated_json(truncated)
    if result is not None:
        logger.info("Salvaged truncated JSON (%d chars)", len(truncated))
    return result


def _repair_truncated_json(text: str) -> Optional[dict]:
    """Attempt to repair truncated JSON by closing open brackets/braces."""
    # Find the last valid comma or complete value, then close everything
    # Strategy: progressively trim from the end until we can close brackets
    closers = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            closers.append("}")
        elif ch == "[":
            closers.append("]")
        elif ch in ("}", "]"):
            if closers:
                closers.pop()

    if not closers:
        return None

    # Trim trailing incomplete values (after last comma or colon)
    trimmed = text.rstrip()
    # Remove trailing comma if present
    if trimmed.endswith(","):
        trimmed = trimmed[:-1]
    # If it ends mid-string, close the string
    # Count unmatched quotes
    quote_count = 0
    esc = False
    for ch in trimmed:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            quote_count += 1
    if quote_count % 2 != 0:
        trimmed += '"'

    # Close all open brackets
    trimmed += "".join(reversed(closers))

    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def _image_to_base64(png_path: str) -> str:
    with open(png_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("ascii")


def _render_pdf_pages(pdf_path: str, output_dir: str, dpi: int = 300) -> list[str]:
    """Render all PDF pages to PNG files. Returns sorted list of paths."""
    os.makedirs(output_dir, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi)
    paths = []
    for i, img in enumerate(images):
        path = os.path.join(output_dir, f"page_{i+1:04d}.png")
        img.save(path, "PNG")
        img.close()
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Claude API calls
# ---------------------------------------------------------------------------


async def _call_claude_vision(
    client: anthropic.AsyncAnthropic,
    png_path: str,
    prompt: str,
    max_tokens: int = MAX_TOKENS_PAGE,
) -> Optional[dict]:
    """Send a single page image to Claude and parse the JSON response.

    Uses assistant prefill to force JSON output starting with '{'.
    """
    b64 = _image_to_base64(png_path)

    try:
        response = await client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=max_tokens,
            system="You are an automated OMR system. You ONLY output valid JSON. Never include explanatory text, markdown fences, or preamble. Start your response with { and end with }.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
                {
                    "role": "assistant",
                    "content": "{",
                },
            ],
        )
    except Exception as exc:
        logger.error("Claude API call failed: %s", exc)
        return None

    text = response.content[0].text if response.content else ""
    # Prepend the prefill "{" that was consumed by the assistant turn
    text = "{" + text
    result = _extract_json(text)
    if result is None:
        logger.warning("Failed to parse JSON from Claude response: %s", text[:200])
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_claude_vision_omr(
    pdf_path: str,
    output_dir: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> AudiverisResult:
    """Run Claude Vision OMR on a PDF score.

    1. Render PDF pages to PNG
    2. Extract score header from page 1
    3. Process each page sequentially
    4. Assemble MusicXML
    5. Return AudiverisResult

    The progress_callback is called after each page:
        await progress_callback(current_page, total_pages, failed_pages)
    """
    if not ANTHROPIC_API_KEY:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message="ANTHROPIC_API_KEY is not set",
        )

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    omr_dir = os.path.join(output_dir, "claude_omr")

    # Step 1: Render PDF pages
    logger.info("Rendering PDF pages: %s", pdf_path)
    try:
        page_pngs = await asyncio.get_event_loop().run_in_executor(
            None, _render_pdf_pages, pdf_path, omr_dir
        )
    except Exception as exc:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"PDF rendering failed: {exc}",
        )

    total_pages = len(page_pngs)
    if total_pages == 0:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message="PDF produced no pages",
        )

    logger.info("Rendered %d pages", total_pages)

    # Step 2: Extract header from page 1
    logger.info("Extracting score header from page 1")
    header_json = await _call_claude_vision(
        client, page_pngs[0], HEADER_PROMPT, MAX_TOKENS_HEADER
    )
    if not header_json:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message="Failed to extract score header from page 1",
        )

    header = parse_header_json(header_json)
    logger.info(
        "Header: %s by %s, %d staves", header.title, header.composer, len(header.staves)
    )

    # Step 3: Process each page
    pages: list[PageAnalysis] = []
    failed_pages: list[int] = []
    last_measure_num = 0

    # Determine which pages have actual music (skip title pages)
    # Heuristic: if page 1 only returned header data with no measures in the
    # header response, start music scanning from page 1 anyway.
    # Some scores have title on page 1, music starting page 2.
    # We'll try all pages — the prompt handles it.

    for i, png_path in enumerate(page_pngs):
        page_num = i + 1
        logger.info("Processing page %d/%d (last measure: %d)", page_num, total_pages, last_measure_num)

        prompt = _page_prompt(header, page_num, total_pages, last_measure_num)
        page_json = await _call_claude_vision(client, png_path, prompt)

        if page_json:
            try:
                page = parse_page_json(page_json)
                if page.measures:
                    pages.append(page)
                    last_measure_num = max(
                        m.number for m in page.measures
                    )
                    logger.info(
                        "Page %d: %d measures (up to m.%d)",
                        page_num, len(page.measures), last_measure_num,
                    )
                else:
                    logger.info("Page %d: no measures found (title/blank page?)", page_num)
            except Exception as exc:
                logger.warning("Page %d: parse error: %s", page_num, exc)
                failed_pages.append(page_num)
        else:
            logger.warning("Page %d: Claude returned no usable data", page_num)
            failed_pages.append(page_num)

        if progress_callback:
            try:
                await progress_callback(page_num, total_pages, failed_pages)
            except Exception:
                pass  # don't let callback errors stop processing

    if not pages:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"No pages produced usable data. Failed pages: {failed_pages}",
        )

    # Step 4: Assemble MusicXML
    logger.info("Assembling MusicXML from %d pages (%d measures)", len(pages), last_measure_num)
    try:
        xml_str = build_musicxml(header, pages)
        stem = Path(pdf_path).stem
        output_path = os.path.join(output_dir, f"{stem}_vision.musicxml")
        write_musicxml(xml_str, output_path)
    except Exception as exc:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"MusicXML assembly failed: {exc}",
        )

    # Step 5: Count measures and compute confidence
    total_measures = last_measure_num
    pages_succeeded = total_pages - len(failed_pages)
    confidence = pages_succeeded / total_pages if total_pages > 0 else 0.0

    error_msg = None
    if failed_pages:
        error_msg = f"{len(failed_pages)} of {total_pages} pages failed: {failed_pages}"

    logger.info(
        "Claude Vision OMR complete: %s (%d measures, %.0f%% confidence)",
        output_path, total_measures, confidence * 100,
    )

    # Clean up page PNGs
    for png in page_pngs:
        try:
            os.unlink(png)
        except OSError:
            pass

    return AudiverisResult(
        musicxml_path=output_path,
        book_path="",
        confidence_score=confidence,
        measures_count=total_measures,
        error_message=error_msg,
    )
