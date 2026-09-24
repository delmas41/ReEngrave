"""ROADMAP 2.12b and 2.12e — shape from the class, role from the geometry.

Two families, one methodology (Sean, 2026-09-23, `docs/DECISIONS.md`): *a
detector class is TWO claims — the SHAPE, which the detector is good at, and
the ROLE, which is a guess about context made from a crop.*

* **2.12b — a rest's VALUE comes from the line it hangs on.** `restWhole` and
  `restHalf` are the SAME filled rectangle; a whole rest HANGS under the
  fourth line from the bottom and a half rest SITS on the third, and the
  registry says in terms that *no shape, size or aspect-ratio classifier can
  ever separate them*. So the detector choosing between those two classes is
  reporting something it cannot know, and `_rest_ruling` took the report as
  the value.
* **2.12e — a flag's stem direction is the STEM's.** `flag8thUp` encodes the
  direction in the class while `adjudicate_stem_direction` decides the same
  fact from `Q.STEM` on the notehead's own subject, and the two were never
  compared. The flag's SHAPE claim — how many hooks — is untouched.

⚠️⚠️ **EVERY REFUSAL TEST HERE CARRIES ITS POSITIVE CONTROL IN THE SAME
CLASS**, because a battery of refusal tests passes by refusing everything: a
rule that narrowed every rest and one that narrows the 134 rows the geometry
contradicts are the same green tick without the control.

⚠️ **RUN RED FIRST, AND THE EXACT SPLIT IS RECORDED BECAUSE IT IS THE PROOF.**
Restore `rhythm.py` from `de6213e7` and run this file: **17 fail, 4 pass.**

The **4 that pass on the unrepaired tree are the positive controls**, and
they are what says this battery does not pass by refusing everything:

* `test_a_restWhole_hanging_where_it_belongs_is_DECIDED` — a rest in its own
  slot still reads 4.0, before and after;
* `test_a_rest_DISPLACED_but_still_nearest_its_own_slot_is_DECIDED` — the
  slack still protects a bowed plate, before and after;
* `test_the_disagreeing_flag_still_COUNTS_AS_A_FLAG` — the hook count, the
  attachment and the 0.5 beats are untouched, before and after. **This is
  2.12e's whole gate** (*zero durations move*) and it passes on both trees;
* `test_a_note_with_NO_flag_carries_no_flag_direction_key_at_all`.

Of the 17 reds, three fail because `HALF_REST_STEP`, `REST_SLOT_SLACK` and
`_REST_SLOT_BY_CLASS` do not exist there at all, and the rest because the
verdict is DECIDED where it must narrow or abstain, or because the detail the
record must now carry is absent. Both are the repair's absence, and the list
above is the control that separates them from a rule that fires on
everything.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS

CELL = R.cell(0, 0, 0, 0)
STAFF = R.staff(0, 0, 0)

#: A staff whose five lines sit 16 px apart, bottom line at y = 400. One staff
#: STEP is half a space, 8 px. ⚠️ The same numbers `test_staged_whole_rest_ink`
#: uses, on purpose: the two rules measure ONE fact from opposite sides, and a
#: second fixture geometry would let them drift apart silently.
LINES = (336, 352, 368, 384, 400)
SPACING = 16.0


def _y_at_step(step: float) -> float:
    """Page y of a given staff step — the inverse of `rhythm._staff_step`."""
    return max(LINES) - step * SPACING / 2.0


def _staff(log, lines=LINES, spacing=SPACING):
    log.observe(STAFF, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                frame="page")
    log.observe(STAFF, Q.STAFF_SPACING, spacing, reader=READERS.GEOMETRY,
                frame="page")


def _rest_at(log, gi, cls, *, step=None, cy=None, page_box=True):
    """One rest detection whose PAGE box centres on a given staff step.

    ⚠️ THE CANONICAL BOX IS DELIBERATELY A DIFFERENT, WRONG SHAPE from the
    page box. The decision must read `detail.bbox_page_px`: a canonical box is
    measured inside one cell rescaled so the staff span is constant, so it
    cannot be compared with a staff's own lines at all, and a fixture whose
    two frames agree cannot tell a frame error from a correct reading. This is
    the `Q.ONSET_COLUMN` fault, pinned.
    """
    cy = _y_at_step(step) if cy is None else cy
    h, w = 0.55 * SPACING, 1.13 * SPACING
    g = R.glyph(0, 0, 0, 0, gi)
    kw = {}
    if page_box:
        kw["bbox_page_px"] = [1000.0, cy - h / 2.0, 1000.0 + w, cy + h / 2.0]
    log.observe(g, Q.GLYPH_BOX, (cls, 7, 7, 999, 999),
                reader=READERS.DETECTOR, frame="cell:0", score=0.5,
                category="rest", **kw)
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0",
                score=0.5)
    return g


def _duration(log, g):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.DURATION,))
    return log.verdict(Q.DURATION, g)


# ─────────────────────────────────────────────────────────────────────────────
# 2.12b — the slot
# ─────────────────────────────────────────────────────────────────────────────

class TestTheTwoSlotsAreOneLineApart(unittest.TestCase):
    """The arithmetic the whole rule stands on, asserted rather than trusted."""

    def test_the_half_rest_slot_is_DERIVED_from_the_whole_rest_slot(self):
        """⚠️ ONE CONSTANT, NOT TWO. The convention's entire content is *the
        same rectangle, one line apart*; two independently typed constants
        would be free to drift into a gap that is not one line, and the gap is
        what `REST_SLOT_SLACK` is the midpoint of."""
        self.assertEqual(rhythm.HALF_REST_STEP, rhythm.WHOLE_REST_STEP - 1.0)
        self.assertEqual(rhythm.REST_SLOT_SLACK,
                         abs(rhythm.WHOLE_REST_STEP
                             - rhythm.HALF_REST_STEP) / 2.0)

    def test_the_audit_frame_and_the_adjudicator_frame_are_the_same_slot(self):
        """⚠️ TWO FRAMES, ONE FACT, AND THE PROBE'S NUMBERS MUST CARRY OVER.
        `probe/role_disagreement.py` measures from the TOP line DOWN (whole
        2.5, half 3.5); `rhythm._staff_step` measures from the BOTTOM line UP
        (whole 5.5, half 4.5). A staff is 8 steps tall, so the two are a
        reflection — and if they were not, the 134 / 433 split this rule is
        built to act on would be a measurement of a different population."""
        span = 8.0
        self.assertEqual(span - 2.5, rhythm.WHOLE_REST_STEP)
        self.assertEqual(span - 3.5, rhythm.HALF_REST_STEP)

    def test_only_restWhole_and_restHalf_have_a_slot_at_all(self):
        """⚠️ A LONE QUARTER REST DOES NOT MEAN THE BAR (CLAUDE.md §10), and a
        quarter rest is not a half rest one line away — it is a different
        glyph. Widening this map is how that fact would be lost."""
        self.assertEqual(set(rhythm._REST_SLOT_BY_CLASS),
                         {"restwhole", "resthalf"})


class TestARestsValueComesFromTheLineItHangsOn(unittest.TestCase):

    def test_a_restWhole_hanging_where_it_belongs_is_DECIDED(self):
        """POSITIVE CONTROL. The engraved acceptance record's 216 of 216
        `restWhole` land here (median step 2.55 in the audit's frame, a
        0.02-step spread), and this rule must leave every one of them alone."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", step=rhythm.WHOLE_REST_STEP)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 4.0)
        self.assertEqual(v.reason, "rest_class")

    def test_a_restHalf_sitting_where_it_belongs_is_DECIDED(self):
        """POSITIVE CONTROL, the other half of the pair."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restHalf", step=rhythm.HALF_REST_STEP)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 2.0)

    def test_a_restHalf_HANGING_below_line_4_is_narrowed(self):
        """⚠️ RED ON THE UNREPAIRED TREE: it reads 2.0 beats, DECIDED, because
        the class is taken as the value. The ink hangs in the whole rest's
        slot, which is the one measurement that can separate the two."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restHalf", step=rhythm.WHOLE_REST_STEP)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "rest_slot_contradicts_class")
        self.assertEqual(v.detail["slot_prefers"], "restWhole")
        # ⚠️ THE ORDER IS THE CLAIM: the MEASURED slot outranks the class.
        # `support` is in this decision's own units and is not a probability.
        self.assertEqual([c.value["beats"] for c in v.candidates], [4.0, 2.0])
        # ⚠️ AND IT IS NOT FLIPPED. A narrowing is not a quiet decision: no
        # value is on the verdict at all, so EXPORT has nothing to argmax.
        self.assertIsNone(v.value)

    def test_a_restWhole_SITTING_on_line_3_is_narrowed(self):
        """The mirror, so the rule cannot be passing by always preferring the
        whole rest — which is the value a plate prints far more of."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", step=rhythm.HALF_REST_STEP)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["slot_prefers"], "restHalf")
        self.assertEqual([c.value["beats"] for c in v.candidates], [2.0, 4.0])

    def test_a_rectangle_on_NEITHER_convention_abstains(self):
        """⚠️ NO FALLBACK TO THE CLASS. The class is the guess this ink has
        just contradicted, and 4.0 quarters of silence is a very loud answer
        to *we cannot tell* (CLAUDE.md §2 rule 8). 433 rows on the two scans
        land here — the bigger bucket and the weaker claim, and a DIFFERENT
        finding: `benchmarks/omr-shape-role-2026-09/FINDINGS.md` §2.12b."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", step=0.0)   # on the bottom line
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "rest_stands_where_no_rest_hangs")
        self.assertIsNone(v.value)
        self.assertEqual(v.detail["slot_says"], rhythm.SLOT_NEITHER)

    def test_a_rest_DISPLACED_but_still_nearest_its_own_slot_is_DECIDED(self):
        """POSITIVE CONTROL FOR THE SLACK, and the reason the predicate is
        asymmetric rather than *which slot is nearest*. A scanned staff tilts
        and bows up to a whole step (`[C8]`), so a rule firing on every rest
        off its nominal slot would fire on the whole population of a warped
        plate."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole",
                     step=rhythm.WHOLE_REST_STEP + 0.4)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.DECIDED)

    def test_the_agreeing_slot_is_RECORDED_beside_the_class(self):
        """The corroboration itself, asserted apart from the controls above so
        that those stay green on the unrepaired tree and remain controls
        rather than a second copy of the new assertion."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", step=rhythm.WHOLE_REST_STEP)
        v = _duration(log, g)
        self.assertEqual(v.detail["slot_says"],
                         rhythm.SLOT_NOT_CONTRADICTED)
        self.assertEqual(v.detail["slot"], "measured")
        self.assertAlmostEqual(v.detail["staff_step"], rhythm.WHOLE_REST_STEP)

    def test_ink_below_the_staff_is_RECORDED_as_such_and_decides_nothing(self):
        """⚠️⚠️ THE BIGGEST HALF OF THE `neither` BUCKET IS AN OWNERSHIP
        QUESTION, NOT A REST-READING ONE — 276 of the 433, and 186 of
        Breitkopf's 235 clustered at step −7.3, which is the next staff down.
        The measure cell is padded 4 staff spaces and on a conductor's page
        that reaches the next staff's ink (CLAUDE.md §10).

        ⚠️ SO IT IS RECORDED AND NOT DECIDED. *Which staff owns this ink* is
        `glyph_owner`'s contest — ladder, then range, then distance — and a
        duration decision inventing an ownership verdict would be a second,
        weaker copy of it wearing a rhythm decision's name. One reason word,
        the fact beside it."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", step=-7.3)   # the next staff down
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "rest_stands_where_no_rest_hangs")
        self.assertEqual(v.detail["outside_its_own_staff"], "below")

    def test_ink_INSIDE_the_staff_is_not_called_outside_it(self):
        """The positive control for the field: without it every abstention
        would read as an ownership problem, which is the claim it exists to
        keep apart from a slot problem (157 of the 433 are inside)."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", step=0.0)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertIsNone(v.detail["outside_its_own_staff"])

    def test_a_restQuarter_is_UNTOUCHED_wherever_it_stands(self):
        """⚠️ THE CONTROL THAT KEEPS THE RULE INSIDE ITS DOMAIN. A quarter
        rest names its value by its SHAPE, so no slot can corroborate or
        contradict it; a rule that abstained here would delete rests it has
        nothing to say about."""
        log = Log()
        _staff(log)
        for step in (0.0, rhythm.WHOLE_REST_STEP, rhythm.HALF_REST_STEP):
            with self.subTest(step=step):
                sub = Log()
                _staff(sub)
                g = _rest_at(sub, 0, "restQuarter", step=step)
                v = _duration(sub, g)
                self.assertIs(v.outcome, Outcome.DECIDED)
                self.assertEqual(v.value["beats"], 1.0)
                self.assertIsNone(v.detail.get("slot_says"))

    def test_no_page_frame_leaves_the_class_reading_STANDING_and_says_so(self):
        """⚠️ DECLINED, NOT DEFAULTED, AND NOT WEAKENED EITHER. `Q.GLYPH_BOX`
        carries the page box BESIDE its canonical one and omits it rather than
        inventing one. With no page box there is no measurement, so there is
        nothing for the class to disagree with — and the record says which of
        the two silences this was."""
        log = Log()
        _staff(log)
        g = _rest_at(log, 0, "restWhole", cy=_y_at_step(0.0), page_box=False)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.detail["slot"], "no_page_frame")
        self.assertIsNone(v.detail.get("slot_says"))

    def test_no_staff_geometry_leaves_the_class_reading_STANDING(self):
        """The other silence, and it must not read like the first."""
        log = Log()                                   # no `_staff(log)`
        g = _rest_at(log, 0, "restWhole", step=0.0)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.detail["slot"], "no_staff_geometry")

    def test_the_dots_survive_the_narrowing(self):
        """A dotted rest whose slot contradicts its class must narrow over the
        two DOTTED values, not over the bare ones — otherwise the narrowing
        silently drops a mark the reader did see."""
        log = Log()
        _staff(log)
        log.observe(CELL, Q.CELL_STAFF_SPACE, SPACING, reader=READERS.GEOMETRY,
                    frame="cell:0")
        g = _rest_at(log, 0, "restHalf", step=rhythm.WHOLE_REST_STEP)
        d = R.glyph(0, 0, 0, 0, 500)
        cy = _y_at_step(rhythm.WHOLE_REST_STEP)
        log.observe(d, Q.GLYPH_BOX, ("augmentationDot", 7, 7, 4, 8),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    bbox_page_px=[1000.0 + 1.13 * SPACING + 2.0, cy - 2.0,
                                  1000.0 + 1.13 * SPACING + 6.0, cy + 2.0])
        log.observe(d, Q.AUG_DOT, (7.0, 7.0), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.8)
        v = _duration(log, g)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual([c.value["dots"] for c in v.candidates],
                         [v.candidates[0].value["dots"]] * len(v.candidates))


# ─────────────────────────────────────────────────────────────────────────────
# 2.12e — the flag
# ─────────────────────────────────────────────────────────────────────────────

X = 100
HEAD_SPACE = 16


def _note(log, gi=0, x=X):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x - 10, 100, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _stem(log, *, x, y, h):
    return log.observe(CELL, Q.STEM, (x, y, 4, h), reader=READERS.CV_LINES,
                       frame="cell:0", x0=x, x1=x + 4, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


def _flag(log, *, gi, cls, x, y, w=12, h=40):
    f = R.glyph(0, 0, 0, 0, gi)
    log.observe(f, Q.GLYPH_BOX, (cls, x, y, w, h), reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    return log.observe(f, Q.FLAG, cls, reader=READERS.DETECTOR,
                       frame="cell:0", score=0.9,
                       x_center=x + w / 2.0, y_center=y + h / 2.0)


def _flagged(log, cls, *, down=True):
    """A head, the stem that carries it, and a flag meeting the stem's far end.

    `down=True` puts the stem BELOW the head (head y 100..116, stem 108..168),
    so `_project` reads `down`; `down=False` puts it above.
    """
    g = _note(log)
    if down:
        _stem(log, x=X - 10, y=108, h=60)
        _flag(log, gi=50, cls=cls, x=X - 10, y=140, w=12, h=40)
    else:
        _stem(log, x=X - 10, y=48, h=60)             # 48..108, meets the head
        _flag(log, gi=50, cls=cls, x=X - 10, y=48, w=12, h=40)
    return g


def _flag_verdict(log, g):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.STEM_DIRECTION, Q.DURATION))
    return log.verdict(Q.STEM_DIRECTION, g), log.verdict(Q.DURATION, g)


class TestAFlagsStemDirectionIsTheStems(unittest.TestCase):

    def test_a_flag8thUp_on_a_DOWN_stem_reads_DOWN(self):
        """⚠️ RED ON THE UNREPAIRED TREE: no `flag_direction` key exists at
        all, and the class suffix is read by nothing — the audit's row 9 is
        *THE VALUE EXISTS AND NOTHING READS IT*."""
        log = Log()
        g = _flagged(log, "flag8thUp", down=True)
        sd, v = _flag_verdict(log, g)
        self.assertEqual(sd.value, "down")
        self.assertEqual(v.detail["flag_direction"], "down")
        self.assertEqual(v.detail["flag_direction_source"], "stem_direction")
        self.assertEqual(v.detail["flag_class_says"], ["up"])
        self.assertTrue(v.detail["detector_role_disagrees"])

    def test_the_disagreeing_flag_still_COUNTS_AS_A_FLAG(self):
        """⚠️⚠️ A FLAG IS A FLAG WHATEVER WAY IT POINTS. Its SHAPE claim — a
        flag of N hooks stands on this stem — is what sets the duration, and
        the role disagreement must never drop it. A rule that refused the
        contradicted flag would turn 27 + 21 recorded disagreements into 48
        wrong durations."""
        log = Log()
        g = _flagged(log, "flag8thUp", down=True)
        _, v = _flag_verdict(log, g)
        # ⚠️ ALL THREE HOLD ON THE UNREPAIRED TREE TOO, and that is the point:
        # this is the control that 2.12e changed NOTHING about the duration.
        self.assertEqual(v.detail["flags_attached"], 1)
        self.assertEqual(v.detail["flag_levels"], 1)
        self.assertEqual(v.value["beats"], 0.5)

    def test_agreement_is_DECIDED_and_records_NO_disagreement(self):
        """POSITIVE CONTROL. Without it the battery passes by calling every
        flag a disagreement, which would be a 3,299-row claim off a 48-row
        population."""
        log = Log()
        g = _flagged(log, "flag8thDown", down=True)
        sd, v = _flag_verdict(log, g)
        self.assertEqual(sd.value, "down")
        self.assertEqual(v.detail["flags_attached"], 1)
        self.assertEqual(v.value["beats"], 0.5)
        # ⚠️ the assertion that is NEW on this tree, kept apart from the two
        # above, which hold on the unrepaired tree and are the control
        self.assertEqual(v.detail["flag_direction"], "down")
        self.assertEqual(v.detail["flag_class_says"], ["down"])
        self.assertNotIn("detector_role_disagrees", v.detail)

    def test_an_UP_stem_hands_the_flag_UP(self):
        """The other direction, so the rule is reading the stem and not a
        constant."""
        log = Log()
        g = _flagged(log, "flag8thDown", down=False)
        sd, v = _flag_verdict(log, g)
        self.assertEqual(sd.value, "up")
        self.assertEqual(v.detail["flag_direction"], "up")
        self.assertTrue(v.detail["detector_role_disagrees"])

    def test_a_sixteenth_flags_HOOK_COUNT_is_untouched_by_the_direction(self):
        """⚠️ THE TWO HALVES OF ONE NAME, READ SEPARATELY. A `flag16thUp` on a
        down stem contributes TWO levels and the stem's direction; the audit's
        gate for this line is that ZERO durations move."""
        log = Log()
        g = _flagged(log, "flag16thUp", down=True)
        _, v = _flag_verdict(log, g)
        # the two that hold on BOTH trees -- the gate for this line
        self.assertEqual(v.detail["flag_levels"], 2)
        self.assertEqual(v.value["beats"], 0.25)
        # the one that is new
        self.assertEqual(v.detail["flag_direction"], "down")

    def test_a_flag_whose_head_has_NO_decided_direction_says_WHICH_silence(self):
        """⚠️ *NO READER RAN* AND *THE READER COULD NOT SAY* ARE THE
        DISTINCTION THE RECORD EXISTS FOR (CLAUDE.md §4b). 205 of 3,299 flags
        on the three acceptance records cannot reach a decided direction, and
        folding that into a plain `None` is how `Q.STEM` stayed unread through
        three separate discoveries."""
        log = Log()
        g = _note(log)
        # a stem that meets the head, and a SECOND stem meeting it the other
        # way -- `stem_direction` abstains `stems_disagree` rather than voting
        _stem(log, x=X - 10, y=108, h=60)
        _stem(log, x=X - 10, y=48, h=60)
        _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=140, w=12, h=40)
        sd, v = _flag_verdict(log, g)
        self.assertIs(sd.outcome, Outcome.ABSTAINED)
        self.assertIsNone(v.detail["flag_direction"])
        self.assertEqual(v.detail["flag_direction_source"],
                         "stem_direction_abstained")
        self.assertEqual(v.detail["stem_direction_reason"], "stems_disagree")
        # and the flag still counts, because a flag is a flag
        self.assertEqual(v.detail["flags_attached"], 1)

    def test_a_note_with_NO_flag_carries_no_flag_direction_key_at_all(self):
        """⚠️ *NO FLAG* MUST NOT READ LIKE *A FLAG WITH NO DIRECTION*. A
        counter over `flag_direction is None` would otherwise count every
        unflagged notehead on the page."""
        log = Log()
        g = _note(log)
        _stem(log, x=X - 10, y=108, h=60)
        _, v = _flag_verdict(log, g)
        self.assertEqual(v.detail["flags_attached"], 0)
        self.assertNotIn("flag_direction", v.detail)
        self.assertNotIn("flag_class_says", v.detail)
        self.assertNotIn("flag_direction_source", v.detail)


if __name__ == "__main__":
    unittest.main()
