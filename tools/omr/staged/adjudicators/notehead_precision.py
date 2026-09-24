"""Notehead PRECISION on the staged path — ROADMAP 2.4a.

⚠️ TWO FILTERS EXIST, MEASURED, AND NEITHER IS CALLED FROM `tools/omr/staged/`.
Verified 2026-09-22 (`git log --all --oneline -S` on both names under
`staged/` returns nothing; `git log --all --oneline -S` under `tools/omr/`
finds only their `transcribe.py` definitions and call sites):
`transcribe._drop_clipped_notehead_fragments` (a notehead-shaped sliver flush
against a measure cell's crop boundary — the neighbouring staff's ink bleeding
into this cell's padding) and `transcribe._drop_unladdered_noteheads` (a
low-confidence notehead standing outside its own staff, with not one ledger
rung joining it to that staff). CLAUDE.md's own §1c records both as
legacy-only. The LEGACY PATH IS FROZEN (`docs/DECISIONS.md` 2026-09-22), so
this ports the two filters as an ADJUDICATE decision rather than moving them,
plus a third rule that was measured and never shipped anywhere: a
`noteheadBlack*` box under 1.0 staff spaces wide
(`benchmarks/omr-notehead-width-2026-09/FINDINGS.md`).

⚠️ THE RECORD KEEPS THE ROW, WHICH THE LEGACY FILTERS DO NOT. Both legacy
functions call `dets.remove(det)` — the glyph vanishes with no trace, which is
exactly the ABSENT/DECLINED collapse this project's own record format exists
to prevent. Here the glyph stays a `Q.GLYPH_BOX` row and this decision
REFUSES it with a named reason; `export._place_notes` is the one place that
acts on the refusal, and it counts what it drops.

⚠️ THE POPULATION Q.GLYPH_LADDER COVERS IS NOT THE POPULATION THIS RULE NEEDS,
AND THAT IS WORTH RECORDING RATHER THAN SILENTLY WORKING AROUND.
`gather_ownership_evidence` files `Q.GLYPH_LADDER` ONLY for a glyph inside a
CROSS-STAFF CONTEST (`subjects_from=Q.GLYPH_BAND_DISTANCE` on
`adjudicate_glyph_owner`) — same CATEGORY (ROADMAP 2.6; it was the smufl NAME
until 2026-09-23), different staff, overlapping ink. The
legacy `_drop_unladdered_noteheads` population is a letter bowl, a key-
signature flat's loop, a bare ledger line: ink detected ONCE, on no other
staff, so it never forms a contest and `Q.GLYPH_LADDER` is never gathered for
it. Reusing that quantity would silently narrow the rule to a population it
was never built for. This decision instead reads the quantities every
notehead glyph carries UNCONDITIONALLY — `Q.GLYPH_BOX` (canonical AND page
frame), `Q.CELL_BOX`, `Q.CELL_STAFF_SPACE`, `Q.NOTEHEAD_STAFF_POSITION`,
`Q.GLYPH_CONF` — and re-derives the ladder search itself, with every
threshold IMPORTED from `tools.omr.transcribe`, never restated. This is
ADJUDICATE reading GATHER's existing facts more thoroughly, not a GATHER
change: no new producer, no new row, and `readjudicate.py` prices it exactly.

⚠️ THE EDGE TEST RUNS IN PAGE FRAME, NOT CANONICAL, AND THAT IS AN EXACT
SUBSTITUTION, NOT AN APPROXIMATION. The legacy rule compares a canonical
`y_canonical` / `y_canonical + height_canonical` against `cell.image.shape[0]`
— the crop's own canonical pixel height, which the frozen staged record does
not carry (only the cell's PAGE rectangle, `Q.CELL_BOX`). But `gather._page_box`
maps canonical -> page by a single per-cell affine transform (divide by
`upscale_factor`), so canonical row 0 maps EXACTLY to the cell's own page-frame
top edge and canonical row `img_h` maps EXACTLY to its page-frame bottom edge —
verified independently by `benchmarks/omr-notehead-width-2026-09/FINDINGS.md`
§0, which cross-checked the same two box conventions on 5,684 boxes and found
them agreeing to 0.0000-0.0142 STAFF SPACES (i.e. the residual is float
rounding, not a frame mismatch). Testing edge-coincidence against `Q.CELL_BOX`
in page pixels is therefore the SAME comparison the legacy rule makes, in a
frame the record actually carries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ... import transcribe as _legacy
from ..adjudicate import Evidence, Mode, Ruling, decision
from .. import record as R
from ..record import ABSTAIN, Kind, Q, Scope

# ─────────────────────────────────────────────────────────────────────────────
# Thresholds — IMPORTED from the legacy path, never restated, so the two
# cannot drift. `benchmarks/omr-notehead-width-2026-09/FINDINGS.md`'s 1.0
# staff-space width floor has no home in `transcribe.py` (it was measured and
# never shipped anywhere), so it alone is a new constant, named after the
# benchmark that measured it.
# ─────────────────────────────────────────────────────────────────────────────

#: A notehead sliver cut off by the cell crop boundary: under this height, at
#: the crop's own edge. `transcribe._CLIPPED_NOTEHEAD_MAX_SPACES`.
CLIPPED_NOTEHEAD_MAX_SPACES = float(_legacy._CLIPPED_NOTEHEAD_MAX_SPACES)

#: How close a box's edge must sit to the cell's own page-frame edge to count
#: as "cut off by the crop", in PAGE pixels. ⚠️ NOT a restatement of
#: `transcribe._CELL_EDGE_TOLERANCE_PX` (1 CANONICAL px) — that quantity has
#: no meaning in a frame this record does not carry the canonical height for.
#: The two frames are exactly affine-related per cell (see the module
#: docstring), so a small page-pixel tolerance is the equivalent test; this
#: is comfortably larger than the floating-point residual the affine map
#: leaves (0.0000-0.0142 staff spaces, i.e. well under a page pixel at any
#: DPI this project reads) and comfortably smaller than any genuine margin a
#: real notehead leaves a crop edge.
CELL_EDGE_TOLERANCE_PAGE_PX = 1.0

#: A `noteheadBlack*` box under this many staff spaces wide is not a
#: notehead. `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §2-3: costs
#: 0 of 103 print-confirmed noteheads on two publishers (Litolff 0.42%,
#: Breitkopf 0.67% of the `decided` population, both under a pre-registered
#: 2% bar), catches 39 of 46 print-confirmed non-noteheads. ⚠️ RESTRICTED TO
#: `noteheadBlack*`: the FINDINGS' own §6 measures the under-floor count as
#: ZERO for every Half and Whole class on both plates — the contamination
#: there is a class-identity fault (mostly not whole/half notes at all, per
#: the crop pass), not a narrow one, and this rule has no opinion on it.
TOO_NARROW_MIN_SPACES = 1.0
TOO_NARROW_CLASS_PREFIX = "noteheadblack"

#: A low-confidence outside-staff notehead with no ledger rung.
#: `transcribe._UNLADDERED_NOTEHEAD_MAX_CONF`.
UNLADDERED_MAX_CONF = float(_legacy._UNLADDERED_NOTEHEAD_MAX_CONF)
#: `transcribe._LEDGER_RUNG_EXPECTED_SLACK` — a note ON the k-th ledger line
#: measures ~k.0 spacings past the staff edge, not k.5; truncation without
#: this reads that as needing no rung.
LEDGER_RUNG_EXPECTED_SLACK = float(_legacy._LEDGER_RUNG_EXPECTED_SLACK)
#: `transcribe._LEDGER_RUNG_Y_TOL_SPACES`.
LEDGER_RUNG_Y_TOL_SPACES = float(_legacy._LEDGER_RUNG_Y_TOL_SPACES)
#: `transcribe._LEDGER_RUNG_MIN_X_OVERLAP`.
LEDGER_RUNG_MIN_X_OVERLAP = float(_legacy._LEDGER_RUNG_MIN_X_OVERLAP)

#: ⚠️⚠️ MEASURED AND HELD BACK, 2026-09-22, ON THE ACCEPTANCE DOCUMENTS
#: THEMSELVES — `benchmarks/omr-notehead-precision-2026-09/`. Joined against
#: the stem-crop-pass's blind print verdicts (the only place "is this a
#: notehead" has a truth value): `unladdered` catches 0 of 34 (Litolff) / 2 of
#: 44 (Breitkopf) print-confirmed non-noteheads and COSTS 4 of 29 / 4 of 74
#: print-confirmed REAL noteheads — net NEGATIVE, worse than a coin flip,
#: where `too_narrow` on the identical join reproduces the prior 0-cost / ~40-
#: caught result almost exactly. Every traced cost is the SAME mechanism: the
#: note's own ledger rung was never DETECTED anywhere in its cell (verified by
#: hand for two cases — zero `ledgerLine` glyphs at all in that cell) — a
#: detection-recall gap the legacy rule's own comment already names
#: ("ledger recall is imperfect, so real notes with ZERO found rungs exist"),
#: sharper here because these are LOW-CONFIDENCE SCAN glyphs, not the
#: confidence>=0.82 engraved population that comment was written against.
#: ⚠️ THIS TASK CARRIES NO FLAG (`docs/DECISIONS.md` convention: a default is
#: a decision, not a code path to leave switchable), so there is no way to
#: ship this LIVE and revert it later without a code change — and "print
#: before default" (the ten rules, §5) means a rule that costs more real notes
#: than it catches on the two ACCEPTANCE documents may not go live on the
#: strength of its legacy ancestry alone. So the rule is fully BUILT, TESTED
#: and MEASURED, and its finding is recorded in `detail` on every notehead
#: (`unladdered_signal`) — but it does NOT set `value=True`. See
#: `adjudicate_notehead_is_not_a_notehead`'s docstring and the 2.4a report for
#: what would need to change before this could ship: the ledger search is
#: SAME-CELL ONLY (a simplification stated in `_ledger_rungs_in_cell`'s own
#: docstring); a PAGE-FRAME, cross-cell search — using `bbox_page_px`, which
#: every glyph already carries, exactly as `Q.ONSET_COLUMN` had to for the
#: identical cross-cell frame reason — is the next thing to try, unbuilt and
#: unmeasured here.
UNLADDERED_SHIPS = False

#: Above this staff position (half-step units, top line = 0), a note is
#: standing on the bottom line of a normal 5-line staff.
_STAFF_BOTTOM_POSITION = 8.0


def _glyph_box_row(ev: Evidence):
    rows = ev.rows(Q.GLYPH_BOX)
    return rows[-1] if rows else None


def _cell_staff_space(ev: Evidence) -> Optional[float]:
    rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS)
    if not rows:
        return None
    try:
        v = float(rows[-1].value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _cell_box_page(ev: Evidence) -> Optional[List[float]]:
    rows = ev.rows(Q.CELL_BOX, scope=Scope.SELF_AND_ANCESTORS)
    if not rows or not isinstance(rows[-1].value, (list, tuple)) \
            or len(rows[-1].value) != 4:
        return None
    return [float(v) for v in rows[-1].value]


def _clipped_fragment(ev: Evidence, box_row, spacing_canonical: float,
                      detail: Dict[str, Any]) -> bool:
    """A sliver cut off by the cell's own crop boundary — height AND edge."""
    _name, _x, y_c, _w, h_c = box_row.value
    h_spaces = h_c / spacing_canonical
    detail["height_spaces"] = round(h_spaces, 3)
    if h_spaces >= CLIPPED_NOTEHEAD_MAX_SPACES:
        return False
    page_box = (box_row.detail or {}).get("bbox_page_px")
    cell_box = _cell_box_page(ev)
    if not page_box or len(page_box) != 4 or cell_box is None:
        # ⚠️ DECLINED, NOT DEFAULTED. Without a page frame for both the glyph
        # and its cell the edge test cannot run, and a short notehead in the
        # middle of a cell is "some other problem" this rule has no opinion
        # on (`transcribe._CLIPPED_NOTEHEAD_MAX_SPACES`'s own docstring) — so
        # the honest default is NOT clipped, never a guess either way.
        return False
    py0, py1 = page_box[1], page_box[3]
    cy0, cy1 = cell_box[1], cell_box[3]
    touching = (abs(py0 - cy0) <= CELL_EDGE_TOLERANCE_PAGE_PX
                or abs(py1 - cy1) <= CELL_EDGE_TOLERANCE_PAGE_PX)
    detail["edge_distance_page_px"] = round(
        min(abs(py0 - cy0), abs(py1 - cy1)), 3)
    return touching


def _is_a_clef(ev: Evidence):
    """ROADMAP 2.11 — this box is part of a clef the locator READ over it.

    ⚠️ A CONNECT, NOT A GUESS, AND THE DISTINCTION IS THE WHOLE POINT. This
    rule measures nothing and decides nothing on its own. It asks whether a
    `Q.CLEF_LOCATED` row on this glyph's own STAFF NAMES this glyph as a box
    it overrode — `gather._occupied_notehead_rows` put the subject key there,
    from the detector ordinal the glyph subject is built from. If the clef was
    not read, or was read without overriding anything, this returns None and
    the glyph is judged on shape as before.

    ⚠️ SCOPE IS `SELF_AND_ANCESTORS` BECAUSE THE ROW IS FILED ON THE STAFF.
    At `EXACT` — the default — a GLYPH subject's query returns nothing and the
    rule would fail SILENTLY, which is the failure mode CLAUDE.md §4b names
    and `wiring --check` exists to catch.

    ⚠️ IT DOES NOT ASK WHETHER THE STAFF'S `clef` VERDICT AGREES. That verdict
    is an ADJUDICATE product of this same stage; reading it here would make
    the refusal depend on decision order, and a located clef that loses the
    clef contest still tells us what this ink is. The evidence is the READ,
    not the winner.
    """
    me = ev.subject.to_key()
    for r in ev.rows(Q.CLEF_LOCATED, scope=Scope.SELF_AND_ANCESTORS):
        d = r.detail or {}
        if me in (d.get("overrode_glyph_subjects") or ()):
            return r
    return None


def _too_narrow(box_row, spacing_canonical: float,
                detail: Dict[str, Any]) -> bool:
    """A `noteheadBlack*` box under the measured width floor."""
    name, _x, _y, w_c, _h = box_row.value
    if not str(name).lower().startswith(TOO_NARROW_CLASS_PREFIX):
        return False
    w_spaces = w_c / spacing_canonical
    detail["width_spaces"] = round(w_spaces, 3)
    return w_spaces < TOO_NARROW_MIN_SPACES


def _ledger_rungs_in_cell(ev: Evidence) -> List[Tuple[float, float, float]]:
    """Every `ledgerLine` glyph's canonical `(x0, x1, y_centre)` in this cell.

    ⚠️ SAME CELL ONLY, not the legacy rule's whole-page search. A staff's
    own ledger rungs for a note it printed are cut into that SAME cell — the
    padding that makes the crop wide enough to hold the note also holds its
    rungs — so this is a faithful narrowing, not a different question, and it
    avoids re-deriving a page-wide affine map this decision has no need of.
    """
    cell = ev.subject.at(Kind.CELL)
    out: List[Tuple[float, float, float]] = []
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        if str(v[0]) != "ledgerLine":
            continue
        x_c, y_c, w_c, h_c = v[1], v[2], v[3], v[4]
        out.append((x_c, x_c + w_c, y_c + h_c / 2.0))
    return out


def _unladdered(ev: Evidence, box_row, spacing_canonical: float,
                detail: Dict[str, Any]) -> bool:
    """A low-confidence notehead outside the staff with NO ledger rung.

    ⚠️ `found == 0`, not "incomplete" — the legacy rule's own condition
    (`transcribe._drop_unladdered_noteheads`: `if found == 0: dets.remove`).
    An incomplete but non-empty ladder is left alone; this is deliberately
    the more conservative of the two shapes the legacy comment considers.
    """
    conf_rows = ev.rows(Q.GLYPH_CONF)
    if not conf_rows:
        return False
    try:
        conf = float(conf_rows[-1].value)
    except (TypeError, ValueError):
        return False
    if conf >= UNLADDERED_MAX_CONF:
        return False

    pos_rows = ev.rows(Q.NOTEHEAD_STAFF_POSITION)
    if not pos_rows:
        return False
    try:
        pos_float = float(pos_rows[-1].value)
    except (TypeError, ValueError):
        return False
    if 0.0 <= pos_float <= _STAFF_BOTTOM_POSITION:
        return False               # inside the staff band -- no ladder needed

    half_step = spacing_canonical / 2.0
    _name, x_c, y_c, w_c, h_c = box_row.value
    y_center = y_c + h_c / 2.0
    if pos_float < 0.0:
        dist_spaces = abs(pos_float) / 2.0
        anchor = y_center - pos_float * half_step        # canonical top line
        sign = -1.0
    else:
        dist_spaces = (pos_float - _STAFF_BOTTOM_POSITION) / 2.0
        anchor = y_center - (pos_float - _STAFF_BOTTOM_POSITION) * half_step
        sign = 1.0
    n_expected = int(dist_spaces + LEDGER_RUNG_EXPECTED_SLACK)
    detail["ledger_expected"] = n_expected
    if n_expected <= 0:
        return False

    rungs = _ledger_rungs_in_cell(ev)
    tol = LEDGER_RUNG_Y_TOL_SPACES * spacing_canonical
    min_overlap = LEDGER_RUNG_MIN_X_OVERLAP * max(1.0, w_c)
    x0, x1 = x_c, x_c + w_c
    found = 0
    for k in range(1, n_expected + 1):
        want_y = anchor + sign * k * spacing_canonical
        for rx0, rx1, ry in rungs:
            if abs(ry - want_y) > tol:
                continue
            if min(rx1, x1) - max(rx0, x0) < min_overlap:
                continue
            found += 1
            break
    detail["ledger_found"] = found
    return found == 0


def _human_not_a_symbol(ev: Evidence, detail: Dict[str, Any]) -> Optional[Any]:
    """A human looked at this box and said the ink is not that kind of symbol.

    ⚠️⚠️ ROADMAP 3.4 — THE ONE READ THAT MAKES A CORRECTION A WITNESS RATHER
    THAN A NOTE. `review/human_evidence.py` files `Q.HUMAN_BOX_VERDICT` on the
    glyph subject the detector already owns; this is the only place in the
    pipeline that acts on it. Everything else a review pass produces is
    reported and applied by nobody, which is the design: a stance on a VERDICT
    is never read by a stage at all.

    ⚠️ DELIBERATELY ITS OWN FUNCTION AND NOT A BRANCH IN THE BODY, so that
    roadmap 2.11's `is_a_clef` refusal — the other new reason this decision is
    about to grow, from a different lane on a different branch — lands beside
    it rather than through it.

    ⚠️ THREE OF THE FIVE LABELS, AND THE OTHER TWO ARE DECLINED HERE ON
    PURPOSE (ROADMAP 3.4c, Sean: *"and to label boxes as nothing or belongs to
    another staff etc."*). The value vocabulary is
    `review/human_evidence.HUMAN_BOX_LABELS` and it is parsed by that module's
    `human_says`, never by a second `split(":")` here:

      `not_a_symbol`              ✅ refuse. There is no symbol here.
      `duplicate_of:<glyph>`      ✅ refuse. One piece of ink is one note, and
                                     the twin he named is the one that keeps
                                     it. ⚠️ THIS DECISION DOES NOT CHECK THAT
                                     THE TWIN SURVIVES — if the human names a
                                     box that is itself refused, both go and
                                     the ink is lost. `rerun.py` measures the
                                     note count, which is where that would
                                     show; a rule that kept one of a pair
                                     alive would be a rule nobody has written.
      `is_a:<non-notehead>`       ✅ refuse, `detail.human_says` naming the
                                     class. He looked at the print and said it
                                     is a clef; a clef is not a notehead.
      `is_a:<notehead class>`     ❌ NOT a refusal. black -> half is a
                                     disagreement about WHICH head, not about
                                     whether there is one, and answering it
                                     here would delete the note instead of
                                     re-reading it. `ingest` files the new
                                     class as a human BOX of its own, so
                                     `adjudicate_duration` decides on that
                                     subject; the machine's head stands beside
                                     it and `rerun.py` reports both.
      `owner:<staff>`             ❌ a different question entirely — that is
                                     `ownership._human_owner`'s.
      `redrawn`                   ❌ the box is in the wrong PLACE, and what to
                                     do with the machine's own box is a
                                     decision nobody has taken. Reported by
                                     `review/feedback.py` as a human row that
                                     reached no verdict rather than quietly
                                     read as a refusal.

    ⚠️ IT DOES NOT WEIGH ANYTHING. A human reading the print is not a term
    beside the width floor; he is the ground the width floor was measured
    against (`benchmarks/omr-notehead-width-2026-09`, 255 print-adjudicated
    boxes). So this is tested FIRST and returns the row that said so.
    """
    from ..review.human_evidence import (NOTEHEAD_PREFIX as _HEAD,
                                         human_says as _says)
    rows = []
    for r in ev.rows(Q.HUMAN_BOX_VERDICT):
        verb, arg = _says(getattr(r, "value", None))
        if verb == "not_a_symbol" or verb == "duplicate_of":
            rows.append((r, verb, arg))
        elif verb == "is_a" and not str(arg or "").startswith(_HEAD):
            rows.append((r, verb, arg))
    if not rows:
        return None
    row, verb, arg = rows[-1]
    detail["human_reader"] = row.reader
    detail["human_row"] = row.id
    # ⚠️ WHAT HE SAID, IN HIS OWN SPELLING, ON THE VERDICT'S OWN DETAIL. A
    # refusal that records only *a human refused this* cannot be turned into a
    # fix; a refusal that records *a human says this is a clefCAlto* can.
    detail["human_says"] = (f"{verb}:{arg}" if arg is not None else verb)
    # ⚠️ The sidecar and the action id travel WITH the row, so the feedback
    # file can name the click that produced a refusal without re-reading the
    # sidecar and hoping the ids still line up.
    for k in ("sidecar", "action", "note"):
        if k in (row.detail or {}):
            detail[f"human_{k}"] = row.detail[k]
    return row


@decision(
    quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
    composed_from=(Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
                  Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_CONF, Q.CLEF_LOCATED,
                  Q.HUMAN_BOX_VERDICT),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
          Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_CONF, Q.CLEF_LOCATED,
          Q.HUMAN_BOX_VERDICT),
    subjects_from=Q.NOTEHEAD_CLASS,
    reasons=("human_not_a_symbol", "is_a_clef", "clipped_fragment",
             "too_narrow", "notehead", ABSTAIN.NO_STAFF_GEOMETRY),
    mode=Mode.ADDITIVE,
)
def adjudicate_notehead_is_not_a_notehead(ev: Evidence) -> Ruling:
    """Is this glyph the detector called a notehead actually something else?

    ⚠️ THREE MEASURED RULES SHIP, A FOURTH IS MEASURED AND HELD BACK, AND A
    HUMAN'S OWN READING OUTRANKS ALL OF THEM — none of them a GATHER filter.
    See the module docstring for where each threshold comes from and why the
    held-back one does not set the value.

    -1. `human_not_a_symbol` (roadmap 3.4) — a `Q.HUMAN_BOX_VERDICT` row
       reading `not_a_symbol`, filed by `review/human_evidence.py` from a
       review pass. Tested FIRST and OUTSIDE the geometry gate; see
       `_human_not_a_symbol`.
    0. `is_a_clef` (ROADMAP 2.11) — the CV clef locator READ a clef on this
       very box's ink, having found the box too small to be what the ink is
       (Sean, 2026-09-23). This rule MEASURES NOTHING: it reads the
       `overrode_glyph_subjects` the read itself named, so the refusal and the
       read can never disagree. It runs before the measured rules because it
       is backed by a positive identification rather than by a shape that
       looks wrong, and after the human because a human looked at the print.

    1. `clipped_fragment` — a sliver of ink flush against the cell's own crop
       boundary: a neighbouring staff's ink bleeding into this cell's
       padding, read as a hollow notehead because a flat sliver has that
       shape (`transcribe._drop_clipped_notehead_fragments`).
    2. `too_narrow` — a `noteheadBlack*` box under 1.0 staff spaces wide,
       measured against the print on two publishers and costing 0 of 103
       confirmed real noteheads (`omr-notehead-width-2026-09`), REPRODUCED
       here on the same crop-pass join (0 of 103 confirmed heads cost,
       ~40 confirmed non-noteheads caught).
    3. `unladdered` (`UNLADDERED_SHIPS = False`, see its own constant for the
       measurement) — a low-confidence notehead standing outside the staff
       with not one ledger rung joining it to that staff
       (`transcribe._drop_unladdered_noteheads`). MEASURED NET NEGATIVE on
       the two acceptance documents: costs 4 of 29 / 4 of 74 confirmed real
       noteheads against 0 of 34 / 2 of 44 confirmed non-noteheads caught.
       Its signal is still COMPUTED and recorded in `detail["unladdered_
       signal"]` on every notehead so the finding stays on the record and a
       future session can re-enable it once a page-frame, cross-cell ledger
       search is built and re-measured — it does not set `value=True`.

    ⚠️ A GLYPH NONE OF THE SHIPPED RULES CONDEMNS DECIDES `False`, REASON
    `notehead` — not an abstention. Geometry was available and was tested;
    silence would read as "we could not tell" when the honest claim is "we
    looked and found nothing wrong with it", the same distinction
    `adjudicate_notehead_is_a_whole_rest` draws for the identical reason.

    ⚠️ ABSTAINS ONLY WHEN THE UNIT ITSELF IS MISSING (`Q.CELL_STAFF_SPACE`),
    which every rule above needs to convert a canonical pixel distance into
    staff spaces. A missing PAGE frame (needed only by `clipped_fragment`)
    does not abstain the whole decision — it just cannot condemn on that one
    rule, and `too_narrow` still runs.
    """
    box_row = _glyph_box_row(ev)

    # ⚠️⚠️ ROADMAP 3.4, AND IT IS FIRST — BEFORE THE GEOMETRY GATE. Every
    # other rule here abstains `no_staff_geometry` when the cell cannot supply
    # a unit, and that is right for a rule that measures. A human did not
    # measure: he looked at the print. Putting this test after the gate would
    # have thrown his reading away on exactly the cells where the machine can
    # say least, which is where he is worth most.
    human_detail: Dict[str, Any] = {}
    human_row = _human_not_a_symbol(ev, human_detail)
    if human_row is not None:
        if box_row is not None and isinstance(box_row.value, (list, tuple)) \
                and len(box_row.value) == 5:
            human_detail["class"] = box_row.value[0]
        return Ruling(value=True, reason="human_not_a_symbol",
                      used=(human_row.id,), detail=human_detail)

    if box_row is None or not isinstance(box_row.value, (list, tuple)) \
            or len(box_row.value) != 5:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)

    # ⚠️ BEFORE THE STAFF-SPACE GUARD, because this rule needs no unit at all:
    # it cites a row that already did the geometry. Putting it after would
    # make a clef-box refusal depend on a measurement it does not use.
    clef_row = _is_a_clef(ev)
    if clef_row is not None:
        return Ruling(
            value=True, reason="is_a_clef",
            used=(clef_row.id, box_row.id),
            detail={"class": box_row.value[0],
                    "clef_read": clef_row.value,
                    "clef_frame": clef_row.frame,
                    "clef_symmetry": clef_row.score})

    spacing = _cell_staff_space(ev)
    if spacing is None:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)

    detail: Dict[str, Any] = {"class": box_row.value[0]}
    used = [box_row.id]

    # ⚠️ COMPUTED UNCONDITIONALLY, BEFORE THE SHIPPED RULES RETURN, so the
    # measurement stays on the record even where a shipped rule already
    # condemns the glyph for a different reason (the two populations
    # overlap: 5 of 205 / 2 of 134 `unladdered`-flagged glyphs on the two
    # documents are ALSO `too_narrow`).
    ladder_detail: Dict[str, Any] = {}
    would_unladder = _unladdered(ev, box_row, spacing, ladder_detail)
    if ladder_detail:
        detail["unladdered_signal"] = {"would_fire": would_unladder,
                                       **ladder_detail}

    if _clipped_fragment(ev, box_row, spacing, detail):
        return Ruling(value=True, reason="clipped_fragment",
                      used=tuple(used), detail=detail)
    if _too_narrow(box_row, spacing, detail):
        return Ruling(value=True, reason="too_narrow",
                      used=tuple(used), detail=detail)
    if UNLADDERED_SHIPS and would_unladder:
        return Ruling(value=True, reason="unladdered",
                      used=tuple(used), detail=detail)
    return Ruling(value=False, reason="notehead", used=tuple(used),
                  detail=detail)
