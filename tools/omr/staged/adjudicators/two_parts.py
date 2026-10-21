"""Two parts sharing one staff -- ROADMAP 2.182 (flag `OMR_TWO_PARTS_ONE_STAFF`, default OFF). STAGED ADJUDICATE.

Sean 2026-10-20: "Yes open the lane on 2 parts sharing a staff". Called from `rhythm.adjudicate_voices` (`Q.VOICES`) only
where Sean's three 2026-09-29 rules leave the bar ONE line without a split (one direction only) or ABSTAINED
(`no_voice_convention_fits`); never over rule 1 (same beat, opposite stems) and never over rule 3 (one line that sums).

CONVENTION ASSUMED: two parts written on one staff (Fl./Ob./Cl./Fag. 1.2, divisi strings) are told apart on the page by
(1) STEM DIRECTION -- the upper part's stems up, the lower part's down -- and the upper part's heads stand above the lower
part's; one line whose stems merely flip at the middle line has the OPPOSITE order (its down-stem heads are the high ones),
which is how the two are told apart; (2) RESTS DISPLACED high or low (2.27c, Sean 2026-09-29: a rest pushed above the
middle line is the upper part's, below the lower part's) -- a part that rests while the other plays; (3) the words `a2`
(both parts play ONE line: never split) and `1.` / `2.` (one part only). Each part must add up on its own; the bar sum
NEVER picks the split -- it is judged after, per part, by the exporter (a part that does not fill is a red bar, 2.173).
WHAT WOULD FALSIFY IT: Sean's 2.182 tiles showing a bar split here that is one line, or the parts' notes swapped.
NOT CONFIRMED: `1.` / `2.` are not read by any reader on the record (only `a2` is: `direction_word` terms), so that
witness is wired for `a2` alone; the 1.5-step displacement is 2.27c's, set without a crop.

A note whose part cannot be told (its stem direction unread) goes to the LIKELIER part by its head's height -- a GUESS,
Sean 2026-10-20 "I go ahead and guess which voice" -- and is named in the verdict's `voice_guessed` so EXPORT writes it
blue (GUESSED, both parts as candidates).
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..record import Kind, Q, Scope, Subject

ENV = "OMR_TWO_PARTS_ONE_STAFF"

#: the reasons `adjudicate_voices` files for a split made here
BY_STEMS = "two_parts_by_stem_and_height"
BY_RESTS = "two_parts_one_resting"


def enabled() -> bool:
    """`OMR_TWO_PARTS_ONE_STAFF`, default OFF; an explicit 1/true/yes/on enables."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _positions(ev, cell: Subject, e) -> List[float]:
    out = []
    for g in e.get("_glyphs") or ():
        sub = Subject(Kind.GLYPH, page=cell.page, system=cell.system, staff=cell.staff, cell=cell.cell, glyph=g)
        for r in ev.rows(Q.NOTEHEAD_STAFF_POSITION, subject=sub):
            try:
                out.append(float(r.value))
            except (TypeError, ValueError):
                pass
            break
    return out


#: the staff's middle line in `Q.NOTEHEAD_STAFF_POSITION`'s frame (half-steps from the TOP line, larger = lower)
MIDDLE_LINE_POS = 4.0
#: a head this far past the middle line is clearly on the far side (half a space)
PAST_THE_MIDDLE = 0.5


def _against_one_line(ev, cell: Subject, chords, direction: str) -> bool:
    """Every chord's heads sit where ONE line would point the stem the OTHER way: for stems down, at or below the middle
    line (and one clearly below); for stems up, at or above it (and one clearly above). One line's stems follow the
    head (above the middle -> down), two parts' stems follow the part."""
    means = []
    for e in chords:
        ps = _positions(ev, cell, e)
        if not ps:
            return False
        means.append(sum(ps) / len(ps))
    if direction == "down":
        return all(m >= MIDDLE_LINE_POS for m in means) and any(m > MIDDLE_LINE_POS + PAST_THE_MIDDLE for m in means)
    return all(m <= MIDDLE_LINE_POS for m in means) and any(m < MIDDLE_LINE_POS - PAST_THE_MIDDLE for m in means)


#: 2.27c's displacement (`rhythm.REST_VOICE_DISPLACEMENT_MIN_STEPS` off the middle line, step 4 in the rest frame:
#: bottom line 0, top line 8, up positive) -- and NO FURTHER than a quarter space outside the staff: a rest farther out is
#: another staff's (a whole rest hanging from the staff above), not this staff's upper part (a crop, 2.182).
REST_PART_MAX_STEPS_OUTSIDE = 0.5


def _side(step: Optional[float]) -> Optional[str]:
    from .rhythm import REST_VOICE_DISPLACEMENT_MIN_STEPS as D, STAFF_MIDDLE_LINE_STEP as M
    if step is None or step > 8.0 + REST_PART_MAX_STEPS_OUTSIDE or step < -REST_PART_MAX_STEPS_OUTSIDE:
        return None
    if step >= M + D:
        return "upper"
    if step <= M - D:
        return "lower"
    return None


def a2_in_bar(ev, cell: Subject) -> bool:
    """An `a2` word stands in this bar (`Q.DIRECTION_WORD` terms): both parts play one line."""
    for r in ev.rows(Q.DIRECTION_WORD, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        if "a2" in ((r.detail or {}).get("terms") or ()):
            return True
    return False


def split(ev, events: Sequence[Dict[str, Any]],
          rest_step: Callable[[Any, Sequence[int]], Optional[float]], a2: bool = False
          ) -> Optional[Tuple[List[List[Dict[str, Any]]], str, Dict[str, Any]]]:
    """`(streams, reason, detail)` -- stream 0 the upper part, stream 1 the lower -- or None where no witness says two
    parts. `events` are `adjudicate_voices`' shims (`kind`, `stem_direction` DECIDED or None, `_glyphs`, `x_position`).
    Rests: a displaced rest joins its own part only; a centred rest stands in both (the existing cover). Nothing here
    reads a duration."""
    cell = ev.subject
    if a2:                                  # `a2_in_bar`, read by the caller: both parts play one line
        return None
    chords = [e for e in events if e["kind"] == "chord"]
    rests = [e for e in events if e["kind"] == "rest"]
    ups = [e for e in chords if e.get("stem_direction") == "up"]
    downs = [e for e in chords if e.get("stem_direction") == "down"]
    unknown = [e for e in chords if e.get("stem_direction") not in ("up", "down")]
    sides = {id(r): _side(rest_step(ev, r["_glyphs"])) for r in rests}
    detail: Dict[str, Any] = {"n_up": len(ups), "n_down": len(downs), "n_unknown": len(unknown),
                              "rests_high": sum(1 for s in sides.values() if s == "upper"),
                              "rests_low": sum(1 for s in sides.values() if s == "lower")}
    up_pos = [p for e in ups for p in _positions(ev, cell, e)]
    down_pos = [p for e in downs for p in _positions(ev, cell, e)]
    if ups and downs:
        # (1) stems AND height: every up-stem head above every down-stem head (positions grow DOWNWARD).
        if not up_pos or not down_pos or not max(up_pos) < min(down_pos):
            return None
        reason = BY_STEMS
        detail["up_range"] = [min(up_pos), max(up_pos)]
        detail["down_range"] = [min(down_pos), max(down_pos)]
    elif not unknown and ((ups and detail["rests_low"] and not detail["rests_high"]
                           and _against_one_line(ev, cell, ups, "up"))
                          or (downs and detail["rests_high"] and not detail["rests_low"]
                              and _against_one_line(ev, cell, downs, "down"))):
        # One part rests (its rest displaced to its side) while the other plays -- and the playing part's stems point
        # the way only a PART's do: down on heads at or below the middle line (up on heads at or above it). In one line
        # those stems would point the other way, so a displaced rest beside them is not a single line's rest moved
        # aside. Every stem in the bar must be read: a part made of rests has no note to guess.
        reason = BY_RESTS
    else:
        return None
    upper, lower = list(ups), list(downs)
    guessed: List[int] = []
    # The likelier part of a note whose stem was not read: by its head's height against the parts' own heads; where one
    # part holds no note (it rests), the note goes with the part that plays. A GUESS, named for EXPORT.
    mid = ((sum(up_pos) / len(up_pos)) + (sum(down_pos) / len(down_pos))) / 2.0 if up_pos and down_pos else None
    for e in unknown:
        ps = _positions(ev, cell, e)
        if mid is not None and ps:
            (upper if sum(ps) / len(ps) < mid else lower).append(e)
        elif ups and not downs:
            upper.append(e)
        elif downs and not ups:
            lower.append(e)
        else:
            return None
        guessed.extend(e["_glyphs"])
    for r in rests:
        s = sides[id(r)]
        if s != "lower":
            upper.append(r)
        if s != "upper":
            lower.append(r)
    if not upper or not lower:
        return None
    upper.sort(key=lambda e: e["x_position"])
    lower.sort(key=lambda e: e["x_position"])
    detail["voice_guessed"] = sorted(guessed)
    return [upper, lower], reason, detail
