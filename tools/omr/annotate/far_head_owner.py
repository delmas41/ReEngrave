"""Which staff owns a far head -- read off its LEDGERS (ROADMAP 2.56b, 2026-10-05).

Sean (CLAUDE.md §10, 2026-09-28/29, 2026-10-05): the ledger lines name the owner
and are authoritative. A far note has ledgers TOWARD its own staff and none
toward the other; nearness is only a hint; "no rungs either way" is OUR failure.
Of 12 seeded heads the note-first reader abstained on, 6 belonged to the
neighbour staff.

The witness: run the note-first look (the note's own line first, then the ledgers
counted from that line to the staff's edge, every gap of the chain one ledger
pitch -- `far_head_reader`, `ledger_grid.derive_note_first_step`) toward EACH
candidate staff -- the head's own, and the next staff beyond it in the head's
direction. A candidate FITS where

  * the head lies on its lines or in the first space outside (no ledger is
    needed, Sean 2026-10-01), or
  * the note-first look reads it: its line is found and the ledgers between the
    staff's edge and that line complete an evenly-spaced chain.

Exactly one fitting candidate owns the head. Both, or neither, say nothing: the
witness never breaks a tie by distance and never converts "cannot tell" into an
owner (rule 8).

Pure arrays and boxes in, a plain dict out. Page frame throughout.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import far_head_reader as FH
from . import ledger_grid as lg

#: reasons that mean the reader could not LOOK (no head size, no usable staff
#: lines) -- not that it looked and the ledgers did not fit. A candidate in this
#: state is unread, never refuted: it could be the owner.
UNREAD_REASONS = ("no_page_shape", "no_staff_lines", "bad_spacing")


def is_unread(reason, note_first=None) -> bool:
    """A candidate we could not RULE OUT: the reader could not look, or it saw
    ledger ink toward that staff that it could not assemble -- a gap below one
    ledger pitch is two marks of one ledger (or a neighbour's mark), i.e. there
    ARE rungs there, so "no ledger reaches this staff" is not what it saw.
    A candidate with no rung at all (`no_rungs`), no line at the note, or a gap
    with room for a missing ledger is the refuted case. (Set after tile 12 of
    the 12-head abstain sheet, `brahms 5/1/2/3/20`: IN-SAMPLE.)"""
    if reason in UNREAD_REASONS:
        return True
    gaps = (note_first or {}).get("gaps") or []
    return bool((reason or "").startswith("count_does_not_fit") and gaps
                and min(gaps) < lg.NOTE_GAP_MIN_SPACES)

#: the reading word on a candidate whose lines the head lies on / just beside
NO_LEDGER_NEEDED = "no_ledger_needed"


def neighbour_staff(box: Sequence[float], own_key: str,
                    staves: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The next staff beyond the head's own, in the head's direction, whose x
    extent the head's centre falls in (two spaces of slack for a cell's pad).
    `staves`: dicts with `key`, `lines` (five page ys), `x0`, `x1`. None where
    the head sits beside its own staff, or no staff lies beyond."""
    own = next((s for s in staves if s["key"] == own_key), None)
    if own is None:
        return None
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    top, bot = min(own["lines"]), max(own["lines"])
    if cy < top:
        beyond = [s for s in staves if s["key"] != own_key
                  and max(s["lines"]) < top]
        pick = lambda ss: max(ss, key=lambda s: max(s["lines"]))
    elif cy > bot:
        beyond = [s for s in staves if s["key"] != own_key
                  and min(s["lines"]) > bot]
        pick = lambda ss: min(ss, key=lambda s: min(s["lines"]))
    else:
        return None
    sp = (bot - top) / 4.0
    near = [s for s in beyond if s["x0"] - 2 * sp <= cx <= s["x1"] + 2 * sp]
    return pick(near) if near else None


def read_toward(ctx: "FH.FarHeadPage", subject: str, box: Sequence[float],
                cls: Optional[str], cand_lines: Sequence[float]) -> Dict[str, Any]:
    """The head read toward ONE candidate staff: `dict(fits, pos, reason,
    how)`. `fits` is True only where a position is read or none is needed."""
    box = tuple(float(v) for v in box)
    lines = FH.frame_lines_for_head(ctx.gray, cand_lines, box)
    if not lines:           # the candidate staff cannot be fitted at this x: unread, so not ruled out
        return dict(fits=False, pos=None, reason="no_staff_lines", how=None, unread=True)
    top, bot = min(lines), max(lines)
    sp = (bot - top) / 4.0
    if sp <= 0:
        return dict(fits=False, pos=None, reason="bad_spacing", how=None,
                    unread=True)
    cy = (box[1] + box[3]) / 2.0
    geo = int(round((cy - top) / (sp / 2.0)))
    if not lg.far_head_needs_ledger_read(geo):
        return dict(fits=True, pos=geo, reason=NO_LEDGER_NEEDED, unread=False,
                    how="geometry", geometry_position=geo)
    r = ctx.read(subject, box, cls, cand_lines)
    return dict(fits=r["pos"] is not None, pos=r["pos"], reason=r["reason"],
                unread=is_unread(r["reason"], (r.get("detail") or {}).get("note_first")),
                how="note_first", geometry_position=geo,
                note_first=(r.get("detail") or {}).get("note_first"),
                edge_y=(r.get("detail") or {}).get("edge_y"),
                box_used=r.get("box_used"))


def decide(per_candidate: Dict[str, Dict[str, Any]]
           ) -> Tuple[Optional[str], str]:
    """`(owner key or None, word)` from `{candidate key: read_toward(...)}`."""
    if any(v.get("unread") for v in per_candidate.values()):
        return None, "unread"
    fits = sorted(k for k, v in per_candidate.items() if v["fits"])
    if len(fits) == 1:
        return fits[0], "one_ladder_fits"
    return None, ("both_fit" if len(fits) > 1 else "neither_fits")


def owner_by_ledgers(ctx: "FH.FarHeadPage", subject: str, box: Sequence[float],
                     cls: Optional[str], own_key: str,
                     staves: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Read the head toward its own staff and its neighbour; name the owner or
    say why not. `own` is `dict(key, lines)` among `staves`."""
    own = next(s for s in staves if s["key"] == own_key)
    cands: Dict[str, Dict[str, Any]] = {
        own_key: read_toward(ctx, subject, box, cls, own["lines"])}
    nb = neighbour_staff(box, own_key, staves)
    if nb is not None:
        cands[nb["key"]] = read_toward(ctx, subject, box, cls, nb["lines"])
    owner, word = decide(cands) if len(cands) > 1 else (
        (own_key, "one_candidate") if cands[own_key]["fits"]
        else (None, "unread" if cands[own_key].get("unread") else "neither_fits"))
    return dict(owner=owner, word=word, candidates=cands,
                neighbour=None if nb is None else nb["key"])
