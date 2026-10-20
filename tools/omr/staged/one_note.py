"""ROADMAP 2.165 -- THE ONE-NOTE CORRECTION (Sean 2026-10-18/19, DECISIONS "Direction for the bar sum"; CLAUDE section 4).

    "it can't simply choose a note based on insufficient evidence, but with a collection of solid evidence, it should be
    able to guess for instance, if we know the meter and we feel solid about all the other notes. It should be able to
    change the one note that it's unsure about if it adds up to the right bar math."

STAGED EVALUATE (`consequences.reconcile_duration`'s blocked branch, where 2.168 already finds the ONE decided note the bar
disputes) + EXPORT (`export.guess_of`, which writes any `reconcile_duration` verdict GUESSED/blue with both candidates).
INFER may not overturn a DECIDED verdict (infer.py rule 3), so the correction lives where the bar rule already lived; it is
labelled, and it is a guess. This module holds only the GATES: `refusal(...)` returns None when every gate holds, else the
name of the first gate that failed (recorded on the 2.168 mark, so a refusal says how close it came).

The gates (all must hold, else no change -- the note then keeps its value and 2.168 marks it blue as before):

1. METER read or carried (`voted` / `carried*`), never one the bars themselves derived (`derived_from_bars`).
2. The bar has a KNOWN length (no narrowed note; 2.162) and EVERY OTHER event is DECIDED on evidence MEASURED solid
   (`solid_refusal`): a class of reading with zero wrong answers among Sean's judged tiles. Never an assumed cut.
3. Every ink in the bar is accounted for: the ink witness is CLEAR (no staff-sized ink no standing glyph explains), no glyph
   was set aside, every head is one head on this staff's own lines, no tuplet evidence, ONE voice (a decided `Q.VOICES`).
4. EXACTLY ONE note is disputed (the bar's unique landing) and it is clearly the weakest: it is not itself solid.
5. Its alternative is among that note's own plausible values and fills the bar exactly with no tuplet; a SHORTENING needs
   beam ink in the cell (CLAUDE section 4: never an eighth with no flag and no beam seen); a note whose flag or beam was
   read cleanly is never changed.

`OMR_BAR_CORRECTS_ONE_NOTE`: DEFAULT ON in mode `loose_removed_boxes_ok` (Sean 2026-10-19); explicit 0/false/no/off = OFF. `strict` (or 1/true/on) = only reading classes with 0 wrong in >= 5 of
Sean's judged tiles count as solid. `loose` = a measurement arm, not a proposal: every DECIDED reader value counts as solid (the bar's own upper bound).
`relaxed` = strict plus the two-source beamed eighth (a beam read by BOTH the detector
and the CV reader) and a decided rest, which are measured below the 0-error floor / not measured; the lane's FINDINGS give
both arms so Sean sets the bar.
"""
from __future__ import annotations

import os
from typing import Any, Optional, Sequence

from .record import Kind, Outcome, Q, Subject, Verdict

ONE_NOTE_ENV = "OMR_BAR_CORRECTS_ONE_NOTE"
DEFAULT_MODE = "loose_removed_boxes_ok"     # Sean 2026-10-19 "Yes": land ON in the loosest arm, written blue
CORRECTS_REASON = "bar_corrects_one_note"

#: Reading classes (the reader's own `reason`) that are >= 95% right on >= 10 of Sean's judged tiles, pooled over both plates
#: (Litolff + Brahms, the 20261018-night OFF replay; stem_tip_reads_no_beam 32/33, beam_discounted_uncertain decided 24/24,
#: hooks_counted 16/16) -- `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` "2.165 one-note correction", table "what
#: solid means". Everything else (above all `head_and_marks`, 75% right, 137 of 182, on his tiles) is NOT solid. The 95% is a declared bar,
#: not a measured law (CLAUDE section 4), and a cut fitted on two plates may only NARROW.
SOLID_READINGS = frozenset({"stem_tip_reads_no_beam", "beam_discounted_uncertain", "hooks_counted"})
_UNROOTED = ("infer:", "reconcile_duration")     # a guess, or the bar's own move, is never evidence for another


def mode() -> str:
    """'' (off), 'strict', 'relaxed', 'loose' or 'loose_removed_boxes_ok'. Unset = DEFAULT_MODE (ON, Sean 2026-10-19)."""
    raw = os.environ.get(ONE_NOTE_ENV)
    if raw is None or not raw.strip():
        return DEFAULT_MODE
    raw = raw.strip().lower()
    if raw in ("0", "false", "no", "off"):
        return ""
    return raw if raw in ("relaxed", "loose", "loose_removed_boxes_ok") else "strict"


def enabled() -> bool:
    return bool(mode())


def _origin(log, v: Verdict) -> Verdict:
    seen = set()
    while v.supersedes and v.id not in seen:
        seen.add(v.id)
        prev = log.row(v.supersedes)
        if prev is None or not hasattr(prev, "outcome"):
            break
        v = prev
    return v


def _is_rest(v: Verdict) -> bool:
    return isinstance(v.value, dict) and bool(v.value.get("is_rest"))


def two_source_beam(origin: Verdict) -> bool:
    d = origin.detail or {}
    return (d.get("beam_evidence") == "read" and (d.get("yolo_beams") or 0) > 0 and (d.get("cv_beams") or 0) > 0
            and not d.get("beams_not_by_ink"))


def solid_refusal(log, v: Verdict, m: Optional[str] = None) -> Optional[str]:
    """None when this standing duration verdict is solid under the current mode, else why not."""
    m = m or mode()
    if v.outcome is not Outcome.DECIDED:
        return "not_decided"
    if any((v.decider or "").startswith(p) for p in _UNROOTED):
        return "a_guess_is_not_evidence"
    origin = _origin(log, v)
    if origin.outcome is not Outcome.DECIDED:
        return "settled_from_a_narrowing"
    if m.startswith("loose"):      # MEASUREMENT ARM ONLY: any decided reader value counts -- the upper bound Sean sets the bar against
        return None
    if _is_rest(v):
        return None if m == "relaxed" else "rest_reading_not_measured"
    if origin.reason in SOLID_READINGS:
        return None
    if m == "relaxed" and origin.reason == "head_and_marks" and two_source_beam(origin):
        return None
    return "reading_class_not_measured_solid:%s" % origin.reason


def meter_refusal(meter: Verdict) -> Optional[str]:
    if meter.outcome is not Outcome.DECIDED:
        return "meter_not_decided"
    if not (meter.reason == "voted" or str(meter.reason).startswith("carried")):
        return "meter_derived_from_the_bars:%s" % meter.reason
    return None


def one_voice(log, subject: Subject) -> bool:
    v = log.verdict(Q.VOICES, subject.at(Kind.CELL))
    if v is None or v.outcome is not Outcome.DECIDED:
        return False
    return isinstance(v.value, dict) and v.value.get("n_voices") == 1


def alternative_refusal(log, note: Verdict, option: dict, subject: Subject) -> Optional[str]:
    """Gate 5 on the note itself."""
    origin = _origin(log, note)
    d = origin.detail or {}
    now_levels = int(note.value.get("beam_levels") or 0)
    new_levels = int(option.get("beam_levels") or 0)
    if new_levels > now_levels:                 # a SHORTENING needs beam ink in the cell
        if not ((d.get("yolo_beams") or 0) > 0 or (d.get("cv_beams") or 0) > 0 or (d.get("beams_not_by_ink") or 0) > 0):
            return "shortening_without_a_beam_seen_in_the_cell"
        if (d.get("flag_levels") or 0) > 0 or d.get("beam_evidence") == "flag":
            return "flag_read_cleanly"
    else:                                       # a LENGTHENING: a cleanly read beam or flag is never undone
        if two_source_beam(origin) or (d.get("flag_levels") or 0) > 0 or d.get("beam_evidence") == "flag":
            return "beam_or_flag_read_cleanly"
    return None


def refusal(log, subject: Subject, meter: Verdict, notes: Sequence[Verdict], note: Verdict, option: dict,
            *, set_aside: Sequence[Any], bar_known: bool, ink_clear: bool, heads_clean: bool, tuplet: bool) -> Optional[str]:
    """The first gate that fails, or None when the correction may be written. The callers pass what only they can compute
    (`ink_clear`, `heads_clean`, `tuplet`, `bar_known`) so this module does not import `consequences`."""
    why = meter_refusal(meter)
    if why:
        return why
    if not bar_known:
        return "bar_length_unknown"
    for other in notes:
        if other.id == note.id:
            continue
        why = solid_refusal(log, other)
        if why:
            return "other_note_not_solid:" + why
    if set_aside and mode() != "loose_removed_boxes_ok":     # MEASUREMENT ARM: what the removed-box gate costs
        return "a_glyph_was_set_aside_in_the_bar:" + "+".join(map(str, set_aside))
    if not ink_clear:
        return "unexplained_ink_in_the_bar"
    if not heads_clean:
        return "heads_not_clean"
    if tuplet:
        return "tuplet_evidence"
    if not one_voice(log, subject):
        return "not_one_voice"
    if solid_refusal(log, note, "strict" if mode() == "strict" else "relaxed") is None:
        return "disputed_note_is_itself_solid"
    return alternative_refusal(log, note, option, subject)
