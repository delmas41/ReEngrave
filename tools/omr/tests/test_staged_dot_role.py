"""ROADMAP 2.12c — a small filled dot's ROLE (augmentation dot vs staccato)
comes from WHERE IT SITS, not from which of two detector classes it was
called.

DECISIONS 2026-09-23 "SHAPE FROM THE CLASS, ROLE FROM THE GEOMETRY":
`augmentationDot` and every `articStaccato*` spelling name the SAME shape --
one small filled dot -- and the class only guesses which role it plays.
`gather.gather_rhythm_marks` files both into ONE quantity, `Q.AUG_DOT`
(tagged `detail.detector_role`), and `adjudicate_dot_role` decides the role
from the ink's position relative to a notehead: CLAUDE.md Sec.10 -- an
augmentation dot sits to the RIGHT of its notehead and level with it (a
space higher on a line note); a staccato sits directly ABOVE or BELOW,
centred on the head's x. Neither window fitting ABSTAINS and never defaults
(CLAUDE.md rule 8).

⚠️ COHERENCE, NOT ACCURACY -- the same discipline `test_staged_duration.py`
states for its own synthetic fixtures: these positions are chosen to land
cleanly inside or outside the measured windows, not read off a real page.

⚠️ CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: Sean has not
adjudicated a print crop of this family; see
`benchmarks/omr-shape-role-2026-09/FINDINGS.md` Sec.2.12c.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Scope

CELL = R.cell(0, 0, 0, 0)
X = 100          # every synthetic notehead sits in the same column
SPACE = 16       # one staff space in the synthetic cell's own frame


# ─────────────────────────────────────────────────────────────────────────────
# GATHER: the class routes by SHAPE, never by role
# ─────────────────────────────────────────────────────────────────────────────

class _Det:
    def __init__(self, name, x=100, y=50, w=8, h=8, conf=0.8,
                category="ornament"):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence, self.category = conf, category

    @property
    def x_center(self):
        return self.x_canonical + self.width_canonical / 2.0

    @property
    def y_center(self):
        return self.y_canonical + self.height_canonical / 2.0


def _gather(*dets):
    log = Log()
    detections = {CELL.to_key(): list(dets)}
    gather.gather_rhythm_marks(log, [], {}, detections)
    gather.gather_glyph_families(log, detections)
    return log


class TestGatherFilesOneQuantityForBothClasses(unittest.TestCase):
    def test_augmentationDot_is_tagged_dot(self):
        log = _gather(_Det("augmentationDot"))
        rows = log.rows(Q.AUG_DOT, CELL, scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["detector_role"], "dot")

    def test_articStaccatoAbove_is_tagged_staccato_and_filed_as_aug_dot(self):
        log = _gather(_Det("articStaccatoAbove"))
        rows = log.rows(Q.AUG_DOT, CELL, scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["detector_role"], "staccato")

    def test_a_staccato_class_never_also_reaches_articulation_mark(self):
        """⚠️ CLAUDE.md Sec.4b: two rows from one reader on one glyph is the
        correlation fault. Filing a staccato-classed box into BOTH
        `Q.AUG_DOT` and `Q.ARTICULATION_MARK` would be exactly that."""
        for cls in ("articStaccatoAbove", "articStaccatoBelow",
                   "articulationStaccato"):
            log = _gather(_Det(cls))
            self.assertEqual(
                log.rows(Q.ARTICULATION_MARK, CELL,
                        scope=Scope.SELF_AND_DESCENDANTS), (), cls)

    def test_the_coarse_no_side_spelling_is_also_pooled(self):
        """`articulationStaccato` (`class_aliases.COARSER_THAN_CANONICAL`:
        "no SIDE") is still one small filled dot, and the role decision never
        reads a side -- so it is pooled exactly like the fine spellings."""
        log = _gather(_Det("articulationStaccato"))
        rows = log.rows(Q.AUG_DOT, CELL, scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual(rows[0].detail["detector_role"], "staccato")


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE: the role comes from the geometry
# ─────────────────────────────────────────────────────────────────────────────

def _staff_space(log, space=SPACE):
    return log.observe(CELL, Q.CELL_STAFF_SPACE, float(space),
                       reader=READERS.GEOMETRY, frame="cell:0")


def _note(log, gi, head="noteheadBlack", x=X):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x - 10, 0, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _mark(log, *, gi, cls, x, y, w=4, h=8):
    """One dot-or-staccato-class detection, filed exactly as
    `gather.gather_rhythm_marks` files it -- its own glyph, its own box, one
    `Q.AUG_DOT` row tagged `detail.detector_role`."""
    d = R.glyph(0, 0, 0, 0, gi)
    log.observe(d, Q.GLYPH_BOX, (cls, x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8)
    role = "dot" if cls == "augmentationDot" else "staccato"
    log.observe(d, Q.AUG_DOT, (x + w / 2.0, y + h / 2.0),
               reader=READERS.DETECTOR, frame="cell:0", score=0.8,
               detector_role=role, detector_class=cls)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.27c: a candidate `glyph_owner` has DECIDED belongs to the
# neighbour is not this staff's dot to attach -- the SAME shape 2.27 fixed
# for `articulation_owner`/`fermata_owner`/`ornament_owner`.
# ─────────────────────────────────────────────────────────────────────────────

HOME = R.staff(0, 0, 0)
NEIGHBOUR = R.staff(0, 0, 1)


def _owned_by_the_neighbour(log, glyph, *, near=1.0, far=4.0):
    """A real cross-staff contest `glyph_owner` DECIDES for `NEIGHBOUR` --
    filed on `glyph`'s OWN subject exactly as `test_staged_articulation_
    owner._owned_by_the_neighbour` proves the identical composition: two
    `Q.GLYPH_BAND_DISTANCE` rows, near the winning candidate and far from
    the losing one. `glyph` itself stays filed under HOME's own cell (`_note`
    always writes `R.glyph(0, 0, 0, 0, gi)`), exactly as a real padded-cell
    ghost is -- the contest, not the subject's address, is what names the
    true owner."""
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, far, reader=READERS.GEOMETRY,
                frame="page", candidate=HOME.to_key(), own=True,
                position_in_candidate=2.0)
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, near, reader=READERS.GEOMETRY,
                frame="page", candidate=NEIGHBOUR.to_key(), own=False,
                position_in_candidate=2.0)


class TestGlyphOwnerPrecedesDotRoleAndDurationInORDER(unittest.TestCase):
    """The new read is safe only because ADJUDICATE reads a FROZEN log and
    `Q.GLYPH_OWNER` is already decided before either consumer runs
    (CLAUDE.md rule: ADJUDICATE reads a frozen log, so ordering here is a
    dependency, not a preference). `Q.DOT_ROLE`'s own ORDER comment calls
    itself needing "no verdict of any kind" -- true of ITS OWN pre-2.27c
    evidence, and unaffected by this: the new read does not move it, it
    only becomes possible because `Q.GLYPH_OWNER` already precedes it."""

    def test_glyph_owner_precedes_dot_role(self):
        self.assertLess(adjudicate.ORDER.index(Q.GLYPH_OWNER),
                        adjudicate.ORDER.index(Q.DOT_ROLE))

    def test_glyph_owner_precedes_duration(self):
        self.assertLess(adjudicate.ORDER.index(Q.GLYPH_OWNER),
                        adjudicate.ORDER.index(Q.DURATION))


class TestDotRoleRespectsADecidedOwner(unittest.TestCase):
    """⚠️ THE FIX. Remove the `_owned_by_a_different_staff` filter from
    `adjudicate_dot_role` and
    `test_the_only_candidate_owned_by_the_neighbour_does_not_admit_the_dot`
    goes RED -- the ghost's box, alone in the cell, still admits the
    augmentation window and the role is wrongly decided `augmentation`."""

    @mock.patch.dict(os.environ, {"OMR_DOT_FOLLOWS_NOTE": "0"})
    def test_the_only_candidate_owned_by_the_neighbour_does_not_admit_the_dot(self):
        # The pre-2.59 path: with `OMR_DOT_FOLLOWS_NOTE` ON (default since
        # 2026-10-07) a dot follows its note to the neighbour staff instead --
        # `test_dot_not_a_note_2026_10_07.py` covers that.
        log = Log()
        _staff_space(log)
        ghost = _note(log, 0, "noteheadHalf")
        _owned_by_the_neighbour(log, ghost)
        _mark(log, gi=1, cls="augmentationDot", x=X + 12, y=4)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, ghost).value,
                         NEIGHBOUR.to_key())
        role = log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(role.outcome, Outcome.ABSTAINED)
        self.assertEqual(role.reason, "owned_by_another_staff")
        self.assertEqual(role.detail["n_candidates"], 1)

    def test_POSITIVE_CONTROL_an_uncontested_candidate_still_admits_the_dot(self):
        """The identical page, minus the contest -- an uncontested candidate
        is untouched, so the abstention above is not passing by refusing
        everything."""
        log = Log()
        _staff_space(log)
        _note(log, 0, "noteheadHalf")
        _mark(log, gi=1, cls="augmentationDot", x=X + 12, y=4)
        adjudicate.run(log)
        role = log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(role.value, "augmentation")


class TestAttachedDotsRespectsADecidedOwner(unittest.TestCase):
    """⚠️ THE FIX. Remove the `_owned_by_a_different_staff` filter from
    `_attached_dots` and `test_a_closer_ghost_does_not_steal_the_dot` goes
    RED -- the ghost's box, being CLOSER to the mark, wins the reciprocal
    nearest-candidate search and the real note's own duration stays
    undotted."""

    def test_a_closer_ghost_does_not_steal_the_dot(self):
        log = Log()
        _staff_space(log)
        real = _note(log, 0, "noteheadHalf", x=X)
        ghost = _note(log, 1, "noteheadBlack", x=X + 4)   # closer to the mark
        _owned_by_the_neighbour(log, ghost)
        _mark(log, gi=2, cls="augmentationDot", x=X + 14, y=4)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, ghost).value,
                         NEIGHBOUR.to_key())
        duration = log.verdict(Q.DURATION, real)
        self.assertEqual(duration.value["dots"], 1)
        self.assertEqual(duration.value["beats"], 3.0)   # 2.0 + half

    def test_POSITIVE_CONTROL_an_uncontested_closer_head_still_wins(self):
        """Without the neighbour contest the closer head is legitimately the
        best candidate, and this filter existing must not change that --
        the reciprocal-nearest rule 2.12c measured is untouched."""
        log = Log()
        _staff_space(log)
        near = _note(log, 0, "noteheadHalf", x=X + 4)
        far = _note(log, 1, "noteheadHalf", x=X)
        _mark(log, gi=2, cls="augmentationDot", x=X + 14, y=4)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, near).value["dots"], 1)
        self.assertEqual(log.verdict(Q.DURATION, far).value["dots"], 0)


class TestDotRoleComesFromPosition(unittest.TestCase):
    def test_RED_a_staccato_class_box_right_of_the_head_is_an_augmentation(self):
        """43 + 9 measured on the acceptance records (FINDINGS Sec.2.12c):
        a staccato-CLASSED box sitting where a dot sits must dot the note."""
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        _staff_space(log)
        # to the RIGHT of the head and level with it -- the augmentation
        # window `DOT_ABOVE_NOTE_MAX_SPACES`/`DOT_BELOW_NOTE_MAX_SPACES`
        # admits, exactly where a real dot would sit.
        _mark(log, gi=1, cls="articStaccatoAbove", x=X + 12, y=4)
        adjudicate.run(log)
        role = log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(role.outcome, Outcome.DECIDED)
        self.assertEqual(role.value, "augmentation")
        duration = log.verdict(Q.DURATION, g)
        self.assertEqual(duration.value["dots"], 1)
        self.assertEqual(duration.value["beats"], 3.0)   # 2.0 + half

    def test_a_dot_class_box_directly_above_the_head_is_a_staccato(self):
        """The mirror: a dot-CLASSED box sitting where a staccato sits must
        NOT lengthen the note."""
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        _staff_space(log)
        # centred on the head's x, a full space above it -- well outside the
        # augmentation window (0.75 spaces) and inside the staccato one.
        _mark(log, gi=1, cls="augmentationDot", x=X - 2, y=-16, w=4, h=4)
        adjudicate.run(log)
        role = log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(role.outcome, Outcome.DECIDED)
        self.assertEqual(role.value, "staccato")
        self.assertEqual(role.detail.get("owner"), g.to_key())
        self.assertEqual(role.detail.get("articulation"), "staccato")
        duration = log.verdict(Q.DURATION, g)
        self.assertEqual(duration.value["dots"], 0)
        self.assertEqual(duration.value["beats"], 2.0)   # unchanged

    def test_POSITIVE_CONTROL_a_correctly_classed_and_placed_dot_stays_a_dot(self):
        """A real augmentation dot, classed and placed as one, must still
        dot the note through the new role gate -- the regression the other
        two tests would not by themselves catch."""
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        _staff_space(log)
        _mark(log, gi=1, cls="augmentationDot", x=X + 12, y=4)
        adjudicate.run(log)
        role = log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(role.value, "augmentation")
        self.assertEqual(log.verdict(Q.DURATION, g).value["dots"], 1)

    def test_an_ambiguous_offset_ABSTAINS_and_feeds_NEITHER_consumer(self):
        """Diagonal and close -- not right-of-and-level (dx too small for the
        augmentation window's `dx > head width` test to admit it once the
        head is this close) and not centred-and-clear either (dy under the
        staccato floor). Rule 8: a fallback never converts cannot-tell into
        an answer."""
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        _staff_space(log)
        # dx small (not clearly right of the head's ink), dy small (not
        # clearly off the head's centre either) -- the gap between the two
        # windows this decision must not guess across.
        _mark(log, gi=1, cls="augmentationDot", x=X + 2, y=2, w=4, h=4)
        adjudicate.run(log)
        role = log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(role.outcome, Outcome.ABSTAINED)
        self.assertEqual(role.reason, "dot_role_ambiguous")
        duration = log.verdict(Q.DURATION, g)
        self.assertEqual(duration.value["dots"], 0)
        self.assertEqual(duration.value["beats"], 2.0)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT: augmentation feeds duration silently; staccato reaches the file;
# an abstention is counted under a named reason and never silently dropped
# ─────────────────────────────────────────────────────────────────────────────

def _log_json(observations, verdicts):
    return {"record": {"observations": list(observations),
                       "verdicts": list(verdicts), "abstentions": [],
                       "counts": {}},
            "summary": {}}


def _obs(i, subject, quantity, value, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": "detector", "frame": "cell:0",
            "score": 0.9, "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x",
        used=(), detail=None):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": list(used),
            "missing": [], "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": dict(detail or {})}


#: A WHOLE note in 4/4 -- the bar must ADD UP or ROADMAP 2.8 holds it out and
#: replaces it with a measure rest, which is what a QUARTER note alone in
#: 4/4 did the first time this fixture was written (RED: the note vanished
#: and `<staccato/>` never had anywhere to land).
WHOLE = {"beats": 4.0, "written": 4.0, "dots": 0}


def _page(note_gi=0):
    """One notehead, decided, on a page the exporter will actually write."""
    sub = f"glyph/0/0/0/0/{note_gi}"
    obs = [_obs(0, sub, Q.GLYPH_BOX,
               ["noteheadBlackOnLine", 100 * note_gi, 50, 40, 40],
               category="notehead"),
          _obs(1, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine")]
    vrd = [_vrd(0, sub, Q.PITCH, "C4"), _vrd(1, sub, Q.DURATION, WHOLE),
          _vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 1),
          _vrd(901, "staff/0/0/0", Q.CLEF, "treble"),
          _vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1),
          _vrd(903, "document", Q.PART_PARTITION,
              {"join": "ordinal", "staves_per_system": 1}, reason="ordinal"),
          _vrd(904, "system/0/0", Q.METER,
              {"numerator": 4, "denominator": 4, "raw": "4/4"})]
    return _log_json(obs, vrd), sub


class TestExportRoutesByRole(unittest.TestCase):
    def test_a_staccato_role_dot_reaches_the_file_as_staccato(self):
        page, note_sub = _page()
        dot_sub = "glyph/0/0/0/0/950"
        page["record"]["observations"].append(
            _obs(950, dot_sub, Q.AUG_DOT, [104.0, 46.0],
                detector_role="staccato", detector_class="articStaccatoAbove"))
        page["record"]["verdicts"].append(
            _vrd(950, dot_sub, Q.DOT_ROLE, "staccato",
                reason="centred_and_offset_from_a_head",
                detail={"owner": note_sub, "articulation": "staccato"}))
        xml, rep = SX.to_musicxml(page)
        self.assertIn("<staccato/>", xml)
        self.assertEqual(rep["dot_role_balance"]["written_staccato"], 1)
        self.assertEqual(rep["dot_role_balance"]["attached_augmentation"], 0)
        self.assertTrue(rep["dot_role_balance"]["balanced"], rep["dot_role_balance"])
        # ⚠️ NOT counted as a real articulation -- `Q.ARTICULATION_MARK` never
        # gathered it, so `articulation_balance`'s population must not move.
        self.assertEqual(rep["articulation_balance"]["marks_in_log"], 0)

    def test_an_augmentation_role_dot_is_not_written_as_an_articulation(self):
        page, note_sub = _page()
        dot_sub = "glyph/0/0/0/0/951"
        page["record"]["observations"].append(
            _obs(951, dot_sub, Q.AUG_DOT, [104.0, 46.0],
                detector_role="dot", detector_class="augmentationDot"))
        page["record"]["verdicts"].append(
            _vrd(951, dot_sub, Q.DOT_ROLE, "augmentation",
                reason="right_of_and_level_with_a_head"))
        # simulate `_attached_dots` having consumed this row already.
        page["record"]["verdicts"][1]["used"] = ["obs:000951"]
        xml, rep = SX.to_musicxml(page)
        self.assertNotIn("<staccato/>", xml)
        self.assertEqual(rep["dot_role_balance"]["attached_augmentation"], 1)
        self.assertEqual(rep["dot_role_balance"]["written_staccato"], 0)
        self.assertTrue(rep["dot_role_balance"]["balanced"], rep["dot_role_balance"])

    def test_an_abstained_dot_role_is_counted_BY_ITS_REASON(self):
        """Rule 8: a fallback never converts cannot-tell into an answer, and
        an abstention must still reach a NAMED bucket -- never silently
        dropped."""
        page, _note_sub = _page()
        dot_sub = "glyph/0/0/0/0/952"
        page["record"]["observations"].append(
            _obs(952, dot_sub, Q.AUG_DOT, [104.0, 46.0],
                detector_role="dot", detector_class="augmentationDot"))
        page["record"]["verdicts"].append(
            _vrd(952, dot_sub, Q.DOT_ROLE, None, outcome="abstained",
                reason="dot_role_ambiguous"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(
            rep["dot_role_not_placed"].get("abstained_dot_role_ambiguous"), 1)
        self.assertTrue(rep["dot_role_balance"]["balanced"], rep["dot_role_balance"])

    def test_the_balance_is_a_PARTITION_over_every_gathered_dot_or_staccato(self):
        page, note_sub = _page()
        page["record"]["observations"].append(
            _obs(953, "glyph/0/0/0/0/953", Q.AUG_DOT, [104.0, 46.0],
                detector_role="staccato"))
        page["record"]["verdicts"].append(
            _vrd(953, "glyph/0/0/0/0/953", Q.DOT_ROLE, "staccato",
                reason="centred_and_offset_from_a_head",
                detail={"owner": note_sub, "articulation": "staccato"}))
        page["record"]["observations"].append(
            _obs(954, "glyph/0/0/0/0/954", Q.AUG_DOT, [104.0, 46.0],
                detector_role="dot"))
        page["record"]["verdicts"].append(
            _vrd(954, "glyph/0/0/0/0/954", Q.DOT_ROLE, None,
                outcome="abstained", reason="no_notehead_or_rest_in_cell"))
        _xml, rep = SX.to_musicxml(page)
        b = rep["dot_role_balance"]
        self.assertEqual(b["population"],
                         b["attached_augmentation"] + b["written_staccato"]
                         + b["not_placed"])
        self.assertTrue(b["balanced"], b)


if __name__ == "__main__":
    unittest.main()
