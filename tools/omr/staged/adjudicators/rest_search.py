"""Empty-bar whole-rest search — ROADMAP 2.52.

CLAUDE.md §10's padded-measure-cell lesson and the whole-rest convention
(§10: *"A whole rest means the BAR whatever the meter"*) both start from a
rest the detector BOXED. `size_measure_rest` (EVALUATE) sizes a lone
`restWhole` glyph to the bar's length; `adjudicate_notehead_is_a_whole_rest`
(ADJUDICATE) catches one the detector mis-called a notehead. Neither can
see a bar the detector drew NO box in at all — "a box it never drew has no
subject" (CLAUDE.md §9) — and the unboxed-ink lane found exactly that
population on Litolff p3 (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md`
§14).

Sean / `docs/DECISIONS.md` 2026-10-01: *"If a bar has no notes it should
expect to find a whole note rest and look in the middle of the bar first.
If it finds it then the bar is complete."* And the 2026-10-01 companion
line, *"Leave the whole rest alone"*: this lane only FINDS a rest in a bar
that has nothing else in it; it never removes a note, a rest, or any other
reading because a whole rest was found nearby, and it never fires on a bar
that already has a kept notehead or rest.

## Stage

ADJUDICATE: the answer FOLLOWS from `Q.EMPTY_BAR_REST_SEARCH`, a GATHER row
(`gather.gather_empty_bar_rest_search`) that already ran the shape-and-
position test over the cell's own connected components, locally, in the
cell's own canonical frame. This decision adds no geometry of its own — it
only reads that row and turns a match into "this bar is a whole-bar rest"
and a miss into an ABSTENTION, never a `False` that would claim the bar is
empty (CLAUDE.md §2 rule 8: a fallback never converts "cannot tell" into an
answer — "not found" is not evidence the bar has nothing in it, only that
this search did not find the one shape it was looking for).

⚠️ ADDITIVE, NEVER A GATE, same posture as `adjudicate_unread_mark`: this
decision does not touch any note or rest another decision placed (it only
ever runs on a cell GATHER already confirmed holds no notehead/rest box),
and it manufactures no `Q.REST` or `Q.DURATION` row itself — EVALUATE/EXPORT
wiring that bar's duration from this verdict is explicitly OUT of scope for
this GATHER+ADJUDICATE-only lane (Sean, 2026-09-30: *"I want all our tests
for now to just be the first 2 stages"*).
"""
from __future__ import annotations

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import Kind, Q


@decision(
    quantity=Q.EMPTY_BAR_WHOLE_REST,
    scope=Kind.CELL,
    wants=(Q.EMPTY_BAR_REST_SEARCH,),
    subjects_from=Q.EMPTY_BAR_REST_SEARCH,
    reasons=("whole_rest_found_by_search", "not_found_by_search",
            "no_mask", "no_staff_geometry"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.EMPTY_BAR_REST_SEARCH,),
)
def adjudicate_empty_bar_whole_rest(ev: Evidence) -> Ruling:
    """Did GATHER's own search find a whole rest hanging in this boxless
    bar?

    `True` ("whole_rest_found_by_search") only where the GATHER row itself
    says `found=True` — a filled, whole-rest-shaped, whole-rest-positioned
    piece of ink, measured against this cell's own LOCAL staff lines, that
    is neither a crop artefact nor a half rest one line away (both already
    ruled out at GATHER). Every other case — the row says `found=False`, or
    GATHER could not even test (no mask, no staff geometry) — ABSTAINS: the
    bar stays unread and counted, never defaulted to "no rest here either"
    (rule 8).
    """
    rows = ev.rows(Q.EMPTY_BAR_REST_SEARCH)
    if rows:
        row = rows[-1]
        detail = row.detail or {}
        if bool(row.value):
            return Ruling(value=True, reason="whole_rest_found_by_search",
                          used=(row.id,), detail=dict(detail))
        # `found=False` -- GATHER looked and the test did not match. This is
        # NOT evidence the bar has nothing in it (rule 8): abstain, counted,
        # never a `False` verdict that would claim the opposite.
        return Ruling.abstain("not_found_by_search")

    refusals = ev.refusals(Q.EMPTY_BAR_REST_SEARCH)
    if refusals:
        reason = refusals[-1].reason
        if reason == "no_mask":
            return Ruling.abstain("no_mask")
        return Ruling.abstain("no_staff_geometry")
    return Ruling.abstain("no_mask")
