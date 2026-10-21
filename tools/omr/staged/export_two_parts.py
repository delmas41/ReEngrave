"""EXPORT of a voice GUESSED for two parts on one staff -- ROADMAP 2.182 (flag `OMR_TWO_PARTS_ONE_STAFF`, default OFF).

`Q.VOICES` (`adjudicators/two_parts.py`) names in `voice_guessed` the notes whose part it chose by height because their
stem direction was unread. This writes each such note GUESSED (blue, `voice_guessed`, both parts as candidates) -- the
same carrier 2.175 uses (`export_unison.VOICE_GUESSED`). A note that already carries another guess keeps that colour.
It reads nothing off the page and decides nothing.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

from .export_unison import VOICE_GUESSED


def mark_voice_guessed(streams: Sequence[List[Dict[str, Any]]], glyphs: Iterable[int]) -> int:
    """Mark the noteheads of `glyphs` (glyph indices) in `streams` GUESSED; idempotent. Returns how many were marked."""
    want = {int(g) for g in glyphs}
    if not want:
        return 0
    n = 0
    for k, stream in enumerate(streams):
        for ev in stream:
            for d in ev.get("noteheads") or ():
                try:
                    gi = int(str(d.get("glyph")).rsplit("/", 1)[-1])
                except (TypeError, ValueError):
                    continue
                if gi not in want or d.get("guess") is not None:
                    continue
                d["guess"] = {"rule": VOICE_GUESSED, "stage": "ADJUDICATE", "quantity": "voice",
                              "candidates": [{"value": {"voice": 1}, "support": 1.0},
                                             {"value": {"voice": 2}, "support": 1.0}],
                              "chosen": {"voice": k + 1}}
                n += 1
    return n
