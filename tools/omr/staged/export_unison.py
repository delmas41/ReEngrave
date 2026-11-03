"""EXPORT of a head with a stem each way as TWO notes -- ROADMAP 2.175 (flag `OMR_UNISON_TWO_NOTES`, default ON).

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


def unfuse(cell, counters: Dict[str, int] = None) -> bool:
    """A bar that could not be written as two voices: drop its twins, restore its heads to their OFF reading. True if
    anything changed. A dropped twin's tie end (2.252 r3, `OMR_UNISON_TIE_VOICE`) is counted, never lost silently."""
    if not any(d.get("unison_twin") for d in cell.detections):
        return False
    keep = []
    for d in cell.detections:
        if d.get("unison_twin"):
            if counters is not None:
                for flag in ("tied_to_next", "tied_from_prev"):
                    if d.get(flag):
                        counters["unison_tie_end_lost_bar_unfused"] = counters.get(
                            "unison_tie_end_lost_bar_unfused", 0) + 1
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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.252 r3 (flag `OMR_UNISON_TIE_VOICE`, default OFF): EACH VOICE OF A UNISON CARRIES ITS OWN TIE.
#
# CONVENTION (Sean 2026-11-02, r2 tile 4: "a unison half note with ties above and below on both sides"; page-facts: an
# arc is OVER its notes; 2.75: the tie belongs to the head on the arc's side): at a head with a stem each way, the arc
# ABOVE the head is the UP-stem voice's tie and the arc BELOW is the DOWN-stem voice's. `Q.TIE_PAIR` names GLYPHS, and a
# unison is ONE glyph written as two notes (the head = up voice, its twin = down voice), so before this every arc of
# the pair landed on the up voice: the down voice's tie was never written, and a lone arc BELOW was written on the up
# voice. This only CONNECTS the arc's measured side to the voice that owns it; it decides no pairing and no kind.
# WHAT WOULD FALSIFY IT: an arc below a unison that ties the up voice (or above, the down voice); a unison whose voices
# hold one tie between them. NOT CONFIRMED beyond Sean's tile 4 -- the r3 tiles ask it.
# ─────────────────────────────────────────────────────────────────────────────

TIE_VOICE_ENV = "OMR_UNISON_TIE_VOICE"


def tie_voice_enabled() -> bool:
    """`OMR_UNISON_TIE_VOICE` (ROADMAP 2.252 r3), default OFF; an explicit on-word enables."""
    import os
    return os.environ.get(TIE_VOICE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _head_yc(det: Dict[str, Any]):
    box = det.get("bbox_page")
    try:
        return float(box[1]) + float(box[3]) / 2.0
    except (TypeError, ValueError, IndexError):
        return None


def arc_side(rec, arc: str, head_yc: float):
    """'above' / 'below' when the arc's page box lies wholly on one side of the heads' centre line, else None (an arc
    box that crosses the line is not read for a side -- nothing is guessed)."""
    for o in rec.obs(Q.GLYPH_BOX, arc):
        box = (o.get("detail") or {}).get("bbox_page_px")
        if not box or len(box) != 4:
            continue
        y0, y1 = float(box[1]), float(box[3])
        if y1 <= head_yc:
            return "above"
        if y0 >= head_yc:
            return "below"
        return None
    return None


def written_member(rec, index) -> Dict[str, str]:
    """glyph -> the member of its `Q.MARK_GROUP` (one mark read by several boxes, 2.58b) that reached the file, for
    every member that did NOT. At a unison two boxes often cover the one head, and the binder ties the upper arc to one
    box and the lower arc to the other; the one-mark-one-note rule writes one, so the other arc's end had no note.
    A group with no written member, or more than one, maps nothing."""
    members: Dict[str, list] = {}
    for o in rec.obs_of(Q.MARK_GROUP):
        members.setdefault(str(o["value"]), []).append(str(o["subject"]))
    out: Dict[str, str] = {}
    for subs in members.values():
        written = [s for s in subs if s in index]
        if len(written) != 1:
            continue
        for s in subs:
            if s not in index:
                out[s] = written[0]
    return out


def _count(counters: Dict[str, int], key: str) -> None:
    counters[key] = counters.get(key, 0) + 1


def tie_ends(rec, arcs, first: Dict[str, Any], last: Dict[str, Any], twin_first, twin_last,
             dropped: Dict[str, int], counters: Dict[str, int]):
    """The (start, stop) note pairs one record tie pair is written on. With no twin at either end it is
    `[(first, last)]`, as with the flag OFF. Both ends written as two voices: the arcs above -> the heads (up voice),
    the arcs below -> the twins (down voice); no arc read for a side -> the heads, counted. One end two voices and the
    other one note: unchanged (the heads), counted where an arc below has no down voice to go to. What does not reach a
    voice is counted in `dropped` (arcs_not_written); what is written in `counters`."""
    ys = [y for y in (_head_yc(first), _head_yc(last)) if y is not None]
    known = set()
    if ys:
        yc = sum(ys) / len(ys)
        known = {arc_side(rec, a, yc) for a in arcs} - {None}
    if twin_first is None and twin_last is None:
        if known == {"above", "below"}:
            # two curves, one each side, name one pair whose ends are each ONE note: the second voice has no note
            _count(dropped, "unison_tie_second_voice_has_no_note")
        return [(first, last)]
    if twin_first is None or twin_last is None:
        if "below" in known:
            _count(dropped, "unison_tie_one_end_one_voice")
        return [(first, last)]
    if not known:
        _count(counters, "unison_tie_side_unread")
        return [(first, last)]
    out = []
    if "above" in known:
        out.append((first, last))
    if "below" in known:
        out.append((twin_first, twin_last))
        _count(counters, "unison_tie_down_voice_written")
        if "above" not in known:
            _count(counters, "unison_tie_moved_to_down_voice")
    return out
