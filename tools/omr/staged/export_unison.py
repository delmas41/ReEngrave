"""EXPORT of a head with a stem each way as TWO notes -- ROADMAP 2.175 (flag `OMR_UNISON_TWO_NOTES`, default OFF).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: see `adjudicators/unison_two.py`. This module only WRITES what
`Q.UNISON_VOICES` decided; it reads nothing off the page and decides nothing.

Three steps, called from `export._place_notes` (three one-line hooks, nothing else in export.py reads this):

* `split(rec, sub, det)` -- the head's detection gets the UP voice's value and direction, and carries its twin (the DOWN
  voice, same box and pitch, its own value and direction) in `det["_unison_twin"]`, with the head's own OFF reading kept in
  `det["_unison_off"]`.
* `expand(runs)` -- the twins join their cell right after their head, so `group_chords_in_measure`'s divisi guard (two
  heads at one x whose stems point opposite ways are two voices, not a chord) keeps them apart.
* `settle(runs, stats)` -- AFTER `_settle_divisi_pairs` decided which bars can be written as two voices: where a bar was
  NOT kept as two voices (its directions came off) the twin is DROPPED and the head returns to its OFF reading. A bar the
  exporter cannot write as two voices never gets a duplicated head in one chord.
"""
from __future__ import annotations

from typing import Any, Dict

from .record import Q

#: the detection keys a voice's value sets
_VALUE_KEYS = ("duration_beats", "duration_type", "dots", "beam_levels")


def _value_of(voice: Dict[str, Any]):
    from .. import export as _legacy
    fit = _legacy._dotted_duration_for_beats(float(voice.get("written") or voice.get("beats") or 0.0))
    if fit is None:
        return None
    dtype, dots = fit
    return {"duration_beats": float(voice.get("beats")), "duration_type": dtype, "dots": max(0, int(dots)),
            "beam_levels": int(voice.get("beam_levels") or 0)}


def split(rec, sub: str, det: Dict[str, Any]) -> bool:
    """Mutate `det` into the UP voice and attach its DOWN-voice twin. False (det untouched) unless a DECIDED
    `Q.UNISON_VOICES` stands on `sub` and both values fit a note value."""
    from .adjudicators import unison_two
    if not unison_two.enabled():
        return False
    v = rec.verdict(Q.UNISON_VOICES, sub)
    if not v or v.get("outcome") != "decided" or not isinstance(v.get("value"), dict):
        return False
    voices = (v["value"] or {}).get("voices") or {}
    up, down = _value_of(voices.get("up") or {}), _value_of(voices.get("down") or {})
    if up is None or down is None:
        return False
    twin = dict(det)
    twin.update(down)
    twin["stem_direction"] = "down"
    twin["unison_twin"] = True
    det["_unison_off"] = {k: det.get(k) for k in _VALUE_KEYS}
    det.update(up)
    det["stem_direction"] = "up"
    det["unison_head"] = True
    det["_unison_twin"] = twin
    return True


def expand(runs) -> int:
    """Put each head's twin into its cell right after it. Returns the number of twins placed."""
    n = 0
    for run in runs.values():
        for cell in run.cells.values():
            out = []
            for d in cell.detections:
                out.append(d)
                tw = d.pop("_unison_twin", None)
                if tw is not None:
                    out.append(tw)
                    n += 1
            cell.detections[:] = out
    return n


VOICE_GUESSED = "voice_guessed"


def _guess_voices(cell, stats: Dict[str, int]) -> None:
    """Sean 2026-10-20 "I go ahead and guess which voice": a note with an UNREAD stem direction in a kept unison bar goes
    to voice 1 (`split_events_into_voices`) -- a GUESS, so it is written GUESSED (blue, `voice_guessed`, both voices as
    candidates). A note that already carries another status keeps that colour; the voice guess is only counted."""
    for d in cell.detections:
        if d.get("category") != "notehead" or d.get("unison_twin") or d.get("unison_head") or d.get("stem_direction"):
            continue
        if d.get("guess"):
            stats["unison_voice_guess_in_a_coloured_note"] = stats.get("unison_voice_guess_in_a_coloured_note", 0) + 1
            continue
        d["guess"] = {"rule": VOICE_GUESSED, "stage": "EXPORT", "quantity": "voice",
                      "candidates": [{"value": {"voice": 1}, "support": 1.0}, {"value": {"voice": 2}, "support": 1.0}],
                      "chosen": {"voice": 1}}
        stats["unison_voice_guessed_notes"] = stats.get("unison_voice_guessed_notes", 0) + 1


def settle(runs, stats: Dict[str, int]) -> None:
    """After `_settle_divisi_pairs`: a twin whose bar was not kept as two voices is dropped, its head restored."""
    for run in runs.values():
        for cell in run.cells.values():
            twins = [d for d in cell.detections if d.get("unison_twin")]
            if not twins:
                continue
            if all(t.get("stem_direction") == "down" for t in twins):
                stats["unison_twins_kept"] = stats.get("unison_twins_kept", 0) + len(twins)
                _guess_voices(cell, stats)
                continue
            # the bar was left fused (its directions came off): one note per head, as with the flag OFF
            keep = []
            for d in cell.detections:
                if d.get("unison_twin"):
                    stats["unison_twins_dropped_bar_left_fused"] = stats.get("unison_twins_dropped_bar_left_fused", 0) + 1
                    continue
                off = d.pop("_unison_off", None)
                if off is not None and d.get("unison_head"):
                    d.update(off)
                    d.pop("unison_head", None)
                keep.append(d)
            cell.detections[:] = keep


def unfuse(cell) -> bool:
    """A bar that could not be written as two voices: drop its twins, restore its heads to their OFF reading. True if
    anything changed."""
    if not any(d.get("unison_twin") for d in cell.detections):
        return False
    keep = []
    for d in cell.detections:
        if d.get("unison_twin"):
            continue
        off = d.pop("_unison_off", None)
        if off is not None and d.get("unison_head"):
            d.update(off)
            d.pop("unison_head", None)
            d["stem_direction"] = None
        if (d.get("guess") or {}).get("rule") == VOICE_GUESSED:
            d.pop("guess")                  # the bar is fused again: no voice was guessed
        keep.append(d)
    cell.detections[:] = keep
    return True
