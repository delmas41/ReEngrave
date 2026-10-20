"""A head with a stem each way is TWO notes -- ROADMAP 2.175 (flag `OMR_UNISON_TWO_NOTES`, default OFF).

CONVENTION ASSUMED (Sean 2026-10-19, "Why are we not getting flags on both sides of the unison notes?"; DECISIONS
2026-10-11 *"They would go in different directions"*): a notehead with a stem on BOTH sides -- an up stem at its right, a
down stem at its left -- belongs to two voices that share one pitch (an a 2 or a divisi unison). Each stem carries its OWN
value (flag, beam, or neither). Two notes are written at that pitch, one per voice, each valued from its own stem.
WHAT WOULD FALSIFY IT: a head that prints one stem each way and means ONE note (a stem plus a barline or a slur boxed as a
stem; one stem through a chord that the stem finder cut in two), or a pair of stems whose marks belong to a neighbour. The
blind tiles ask Sean how many notes the head stands for. NOT CONFIRMED by Sean beyond the 2.167e tile 3 (Litolff p13).

WHAT EXISTS (brief from the tree, rule 1): `stem_value.adjudicate_head_stem` rules `unison_two_voices` (2.87, one head, a
stem each way, no other head under the stems); `rhythm.adjudicate_duration` (2.75 / 2.141h) then counts each stem's beams on
its OWN side and keeps the head ONE note whose value is the voices' range; `adjudicate_event` filed one glyph as one
event; `adjudicate_voices` gave it one voice; EXPORT wrote each glyph once. So the second stem's flag was consumed as a
witness for one value and the second note never existed. This decision reads the two stems' values SEPARATELY and files
them; `adjudicate_event` makes one event per voice; EXPORT writes both (flag OFF: none of this runs, bit for bit).

⚠️ NOTHING IS INVENTED. A voice's value is read only from a mark on its OWN stem: a beam its side's strokes joined
(`Q.DURATION`'s own per-voice count, `detail.beam_voices`) or a flag attached to its stem (`rhythm._attached_flags`, called
on that voice's stems). A voice with NO mark while the other has one is NOT a quarter by absence: the head keeps its single
OFF reading and no second note is made (`one_voice_unmarked`), as does a voice whose beam count is a range, a dotted head
(which voice owns the dot is not read), a tuplet member, a head whose fill disagrees with its class, or a flag shared by
both stems (one ink, counted for neither). Both voices unmarked is two plain quarters (the head's own reading, doubled).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import Kind, Outcome, Q, Scope

ENV = "OMR_UNISON_TWO_NOTES"


def enabled() -> bool:
    """`OMR_UNISON_TWO_NOTES`, default OFF; only an explicit on-word enables."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def voice_event_beats(unison_value: Optional[Dict[str, Any]], voice: str) -> Optional[float]:
    """Beats of one voice of a DECIDED `Q.UNISON_VOICES` value, or None."""
    try:
        return float(unison_value["voices"][voice]["beats"])
    except (TypeError, KeyError, ValueError):
        return None


def _reading(side: str, level: Optional[int], source: Optional[str], **extra: Any) -> Dict[str, Any]:
    return {"side": side, "level": level, "source": source, **extra}


@decision(
    quantity=Q.UNISON_VOICES,
    composed_from=(Q.HEAD_STEM, Q.DURATION, Q.STEM, Q.FLAG),
    scope=Kind.GLYPH,
    wants=(Q.HEAD_STEM, Q.DURATION, Q.STEM, Q.FLAG, Q.FLAG_IS_NOT_A_FLAG, Q.GLYPH_BOX, Q.CELL_STAFF_SPACE,
           Q.NOTEHEAD_CLASS, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.TUPLET_RATIO),
    subjects_from=Q.NOTEHEAD_CLASS,
    reasons=("two_notes", "flag_off", "not_a_unison", "head_refused", "duration_missing", "dotted_head", "in_a_tuplet",
             "head_fill_disagrees", "one_voice_unmarked", "voice_beams_range", "shared_flag", "stems_not_read"),
    mode=Mode.ADDITIVE,
)
def adjudicate_unison_voices(ev: Evidence) -> Ruling:
    """What does EACH stem of a head that carries one each way say?

    See the module docstring. DECIDED `{"voices": {"up": v, "down": v}, "agree": bool}` only where both voices are read;
    every other exit abstains with its reason and whatever each voice's own reading was.
    """
    if not enabled():
        return Ruling.abstain("flag_off")
    hs = ev.verdict(Q.HEAD_STEM)
    if hs is None or hs.reason != "unison_two_voices":
        return Ruling.abstain("not_a_unison", head_stem=None if hs is None else hs.reason)
    refusal = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
    if refusal is not None and refusal.outcome is Outcome.DECIDED and refusal.value is True:
        return Ruling.abstain("head_refused", why=str(refusal.reason))
    # late imports: rhythm imports stem_value, which imports this module for the flag
    from . import rhythm as R
    cell = ev.subject.at(Kind.CELL)
    head = R._head_class(ev)
    base = None
    for name, beats in R._HEAD_BEATS.items():
        if head is not None and str(head).startswith(name):
            base = beats
            break
    if base is None or base > 2.0:
        return Ruling.abstain("head_fill_disagrees", head=str(head), why="no stemmed head value")
    box = ev.rows(Q.GLYPH_BOX)
    head_box = R._xywh_head(box[-1].value) if box else None
    stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
    if head_box is None:
        return Ruling.abstain("stems_not_read")
    own = R._stems_on(head_box, stems)
    vs = R._voice_stems(own, head_box)
    if not vs["up"] or not vs["down"]:
        return Ruling.abstain("stems_not_read", up=len(vs["up"]), down=len(vs["down"]))
    dur = ev.verdict(Q.DURATION)
    if dur is None:
        return Ruling.abstain("duration_missing")
    dd = dur.detail or {}
    open_head = bool(dd.get("head_is_open"))
    if open_head != (base != R._HEAD_BEATS["noteheadBlack"]):
        return Ruling.abstain("head_fill_disagrees", head=str(head), head_is_open=open_head)
    dots = int(dd.get("dots_attached") or 0)
    if dots:
        return Ruling.abstain("dotted_head", dots=dots)
    ratio = ev.verdict(Q.TUPLET_RATIO, subject=cell)
    if (ratio is not None and isinstance(ratio.value, dict)
            and ev.subject.glyph in (ratio.value.get("members") or [])):
        return Ruling.abstain("in_a_tuplet")
    tol = R._join_tolerance(ev, cell)
    used = [hs.id, dur.id]
    readings: Dict[str, Dict[str, Any]] = {}
    flag_ids: Dict[str, set] = {}
    bv = dd.get("beam_voices") or {}
    for side in ("up", "down"):
        rows, flag_level = R._attached_flags(ev, cell, vs[side], tol)
        flag_ids[side] = {r.id for r in rows}
        rng = bv.get(side)
        c, pz = (rng[0], rng[1]) if isinstance(rng, (list, tuple)) and len(rng) == 2 else (None, None)
        if open_head:
            readings[side] = _reading(side, 0, "open_head")
        elif c is not None and pz is not None and c != pz:
            readings[side] = _reading(side, None, None, beams=[c, pz], flags=flag_level, range=True)
        elif c:
            readings[side] = _reading(side, int(c), "beam", beams=[c, pz], flags=flag_level)
        elif flag_level:
            readings[side] = _reading(side, int(flag_level), "flag", beams=[c, pz], flags=flag_level)
            used.extend(r.id for r in rows)
        else:
            readings[side] = _reading(side, None, "none_seen", beams=[c, pz], flags=0)
    if flag_ids["up"] & flag_ids["down"]:
        return Ruling.abstain("shared_flag", voices=readings)
    # CORROBORATION ONLY (Sean 2026-10-19: "when multiple voices land unison on eighth notes that have beams, the beams are
    # both above and below ... easier to see the beam outside of the staff ... just helps as corroboration"). The OTHER
    # stem's beam is different ink, a second witness: where one voice's beam count is a RANGE and the other voice's level is
    # READ (c == pz > 0 or a flag) and lies inside that range, it confirms that level. It never supplies a value: a voice with
    # no beam ink at all stays unmarked (the voices may differ -- one holds a quarter while the other moves in eighths), and
    # a read level outside the range settles nothing.
    for side, other in (("up", "down"), ("down", "up")):
        r, o = readings[side], readings[other]
        if r.get("range") and o["level"] and o["source"] in ("beam", "flag"):
            lo, hi = r["beams"]
            if lo <= o["level"] <= hi:
                readings[side] = _reading(side, int(o["level"]), "beam_corroborated", beams=r["beams"],
                                          flags=r.get("flags"), corroborated_by=other)
    if any(r.get("range") for r in readings.values()):
        return Ruling.abstain("voice_beams_range", voices=readings)
    marked = [s for s, r in readings.items() if r["level"]]
    unmarked = [s for s, r in readings.items() if r["level"] is None]
    if marked and unmarked:
        return Ruling.abstain("one_voice_unmarked", voices=readings)
    out: Dict[str, Dict[str, Any]] = {}
    for side, r in readings.items():
        level = r["level"] or 0
        beats = R._at_level_value(base, level, 0)
        out[side] = {"beats": beats, "written": beats, "dots": 0, "beam_levels": level,
                     "source": r["source"] if r["level"] is not None else "none_seen"}
    return Ruling(value={"voices": out, "agree": out["up"]["beats"] == out["down"]["beats"]},
                  reason="two_notes", used=tuple(used), detail={"readings": readings})
