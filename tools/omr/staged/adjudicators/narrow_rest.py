"""A narrow "notehead" that is an eighth rest -- ROADMAP 2.80b.

Sean, 2026-10-11, on tile 1 of `out/print/2.80-review/` (Brahms Contrabass bar
13, the blue mark): *"It is an 8th note rest"*. The detector boxed the rest's
blob as `noteheadBlackInSpace`, 0.67 spaces wide; `adjudicate_notehead_is_not_
a_notehead` refused it `too_narrow` (a head is ~1.3 spaces); and the bar was
left short by an eighth, which `reconcile_duration` then "repaired" by
stretching a note (2.80, the witness) -- or, with the witness, holds out.

## Stage

ADJUDICATE: *what does this ONE thing mean, on what evidence?* The evidence is
the MARK'S OWN, read by GATHER (`Q.NARROW_BOX_SHAPE`): the ink under the box
joined with the pieces stacked against it (staff-line erasure splits an eighth
rest into a blob and a tail), its size in staff spaces, the staff step of its
centre, whether another detection already owns the ink.

⚠️⚠️ **NO BAR IS CONSULTED, AND THAT IS THE RULE** (coordinator, 2026-10-11;
CLAUDE.md §2 rule 8; §10 *"two witnesses off the same raster fall silent
together"*). That the bar is short by exactly an eighth would be a SECOND
witness only if it came from somewhere else, and it does not: the bar's sum is
made of the same readings the mark was refused out of. A bar's shortfall may
at most RANK between rest candidates the shape already allows, and that
ranking would live in INFER, labelled -- there is none, because the shape
admits one candidate (the eighth rest) here. If the shape cannot tell, this
ABSTAINS and the bar stays held out (2.8).

## What it decides

* `True`   -- the ink is an eighth rest's shape, hung on the middle of the
  staff, and no standing glyph already reads it.
* `False`  -- decisively NOT an eighth rest's shape, or the ink is already
  read as a standing rest/notehead (a duplicate box over a kept rest).
* abstain  -- the shape sits between, another class (a flag, a beam) claims
  the ink, or there is nothing to measure.

It only ever speaks on a box ALREADY refused `too_narrow`. EVALUATE's
`size_reinstated_rest` gives a `True` its length (an eighth, 0.5 quarters) and
EXPORT writes it as a rest.
"""
from __future__ import annotations

from typing import Any, Dict

from .. import margins as M
from ..adjudicate import Evidence, Mode, Ruling, decision
from .. import record as R
from ..record import Kind, Outcome, Q, Scope
from .. import box_kind as _box_kind

#: An eighth rest's ink, in staff spaces, MEASURED off the 107 + 17 kept
#: `rest8th` boxes of Brahms p0-1 and Litolff p1-3 (`FINDINGS` 2.80b): 1.2-1.4
#: wide, 1.9-2.4 tall; the staff step of its centre (bottom line = 0) has a
#: median of 3.9 and the refused-narrow candidates all sit at 4.0-4.3. The
#: windows are wider than the measured spread.
REST8TH_WIDTH_SPACES = (0.9, 1.6)
REST8TH_HEIGHT_SPACES = (1.6, 2.6)
REST8TH_MAX_PIECES = 3
REST8TH_STEP_CENTRE = 4.0
REST8TH_STEP_TOLERANCE = 1.0
#: Outside these the ink is decisively not an eighth rest (a lone crumb, a
#: head-with-stem, a quarter rest, a beam), not a close call.
DECISIVELY_NOT_WIDTH_SPACES = (0.5, 2.0)
DECISIVELY_NOT_HEIGHT_SPACES = (1.0, 3.2)

#: ROADMAP 2.106: the declared bands, `{axis: [lo, hi]}`. The eighth-rest
#: window is the "shaped" cut; the decisive window is the "not a rest" cut;
#: between them is the abstention band.
_BAND = {"width_spaces/rest": REST8TH_WIDTH_SPACES,
         "height_spaces/rest": REST8TH_HEIGHT_SPACES,
         "width_spaces/decisive": DECISIVELY_NOT_WIDTH_SPACES,
         "height_spaces/decisive": DECISIVELY_NOT_HEIGHT_SPACES}
_UNIT = "mixed (staff spaces, staff steps, pieces)"


def _shaped_slacks(w, h, step, pieces):
    return (("width_spaces", M.slack(w, *REST8TH_WIDTH_SPACES)),
            ("height_spaces", M.slack(h, *REST8TH_HEIGHT_SPACES)),
            ("staff_step", M.slack(step, REST8TH_STEP_CENTRE
                                   - REST8TH_STEP_TOLERANCE,
                                   REST8TH_STEP_CENTRE
                                   + REST8TH_STEP_TOLERANCE)),
            ("pieces", REST8TH_MAX_PIECES - pieces))


@decision(
    quantity=Q.NOTEHEAD_IS_AN_EIGHTH_REST,
    composed_from=(Q.NARROW_BOX_SHAPE,),
    scope=Kind.GLYPH,
    wants=(Q.NARROW_BOX_SHAPE, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.GLYPH_BOX, Q.CELL_STAFF_SPACE,
           Q.REST_IS_NOT_A_REST),
    subjects_from=Q.NARROW_BOX_SHAPE,
    reasons=("rest8th_shape", "not_rest_shaped", "ink_already_read_as_a_glyph",
             "claimed_by_another_class", "shape_cannot_tell",
             "not_refused_as_too_narrow", "no_ink_under_box",
             "no_shape_reading"),
    mode=Mode.ADDITIVE,
)
def adjudicate_narrow_box_is_an_eighth_rest(ev: Evidence) -> Ruling:
    """Is this narrow box, refused as a head, an eighth rest's ink?

    See the module docstring: the mark's own shape, never the bar.
    """
    refusal = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
    if (refusal is None or refusal.outcome is not Outcome.DECIDED
            or refusal.value is not True or refusal.reason != "too_narrow"):
        return Ruling.abstain("not_refused_as_too_narrow")
    rows = ev.rows(Q.NARROW_BOX_SHAPE)
    if not rows:
        return Ruling.abstain("no_shape_reading")
    row = rows[-1]
    d: Dict[str, Any] = row.detail or {}
    if not d.get("n_pieces"):
        return Ruling.abstain("no_ink_under_box")
    w, h = d.get("width_spaces"), d.get("height_spaces")
    step = d.get("staff_step")
    if w is None or h is None or step is None:
        return Ruling.abstain("no_shape_reading")
    detail = {"width_spaces": w, "height_spaces": h, "staff_step": step,
              "n_pieces": d.get("n_pieces"), "fill": d.get("fill")}
    used = (refusal.id, row.id)

    # Who else already reads this ink? A STANDING rest/notehead box over it
    # means this narrow box is a duplicate of an existing reading, not a
    # missed one; any other class (a flag, a beam, a stem) is a claim this
    # decision cannot see past.
    for o in d.get("overlapping_detections") or ():
        cls = str(o.get("class") or "")
        other = R.glyph(ev.subject.page, ev.subject.system, ev.subject.staff,
                        ev.subject.cell, int(o["glyph"]))
        if cls.lower().startswith("rest"):
            v = ev.verdict(Q.REST_IS_NOT_A_REST, subject=other)
            if v is None or v.outcome is not Outcome.DECIDED:
                return Ruling.abstain("claimed_by_another_class", **detail)
            if v.value is False:
                return Ruling(value=False, reason="ink_already_read_as_a_glyph",
                              used=used, detail={**detail, "by": cls})
        elif cls.lower().startswith("notehead"):
            v = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=other)
            if v is None or v.outcome is not Outcome.DECIDED:
                return Ruling.abstain("claimed_by_another_class", **detail)
            if v.value is False:
                return Ruling(value=False, reason="ink_already_read_as_a_glyph",
                              used=used, detail={**detail, "by": cls})
        else:
            if _box_kind.enabled() and _box_kind.printed_size(cls):
                # ROADMAP 2.245 round 2 (2.247 hand-off): a fixed-size glyph's box far bigger than its printed glyph is not that glyph
                # (Litolff p4 4/0/8/5: a 1.45 x 1.87 sp "double sharp" on an eighth rest; printed 0.99 x 1.01): it does not block
                ob = ev.rows(Q.GLYPH_BOX, subject=other)
                sp = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS)
                if ob and sp and isinstance(ob[-1].value, (list, tuple)) and len(ob[-1].value) == 5 and float(sp[-1].value) > 0:
                    u = float(sp[-1].value)
                    if _box_kind.oversized_for_its_class(cls, float(ob[-1].value[3]) / u, float(ob[-1].value[4]) / u):
                        detail.setdefault("not_blocking_oversized", []).append(cls)
                        continue
            return Ruling.abstain("claimed_by_another_class",
                                  **{**detail, "by": cls})

    if (not DECISIVELY_NOT_WIDTH_SPACES[0] <= w <= DECISIVELY_NOT_WIDTH_SPACES[1]
            or not DECISIVELY_NOT_HEIGHT_SPACES[0] <= h
            <= DECISIVELY_NOT_HEIGHT_SPACES[1]):
        # margin: how far OUTSIDE the decisive window (positive = refused by
        # this much, a decided "no").
        far = max((("width_spaces",
                    -M.slack(w, *DECISIVELY_NOT_WIDTH_SPACES)),
                   ("height_spaces",
                    -M.slack(h, *DECISIVELY_NOT_HEIGHT_SPACES))),
                  key=lambda t: t[1])
        return M.attach(
            Ruling(value=False, reason="not_rest_shaped", used=used,
                   detail=detail),
            margin=far[1], axis=far[0], unit=_UNIT, band=_BAND,
            would_choose=(False,))
    shaped = (REST8TH_WIDTH_SPACES[0] <= w <= REST8TH_WIDTH_SPACES[1]
              and REST8TH_HEIGHT_SPACES[0] <= h <= REST8TH_HEIGHT_SPACES[1]
              and d["n_pieces"] <= REST8TH_MAX_PIECES
              and abs(step - REST8TH_STEP_CENTRE) <= REST8TH_STEP_TOLERANCE
              and not d.get("touches_cell_edge"))
    if shaped:
        axis, m = M.tightest(_shaped_slacks(w, h, step, d["n_pieces"]))
        return M.attach(
            Ruling(value=True, reason="rest8th_shape", used=used,
                   detail=detail),
            margin=m, axis=axis, unit=_UNIT, band=_BAND,
            would_choose=(True,))
    axis, m = M.tightest(_shaped_slacks(w, h, step, d["n_pieces"]))
    return M.attach(
        Ruling.abstain("shape_cannot_tell", **detail),
        margin=m, axis=axis, unit=_UNIT, band=_BAND, would_choose=(True,),
        **({"blocked_by": "touches_cell_edge"} if d.get("touches_cell_edge")
           else {}))
