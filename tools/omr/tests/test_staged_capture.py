"""`staged.capture` — SHAPE, POSITION, IMAGE and RESOLUTION, per family.

⚠️ THREE KINDS OF TEST LIVE HERE AND THEY ARE NOT INTERCHANGEABLE.

**Instrument tests** drive the walkers over synthetic code whose fault is known
by construction, so a question that stops working goes red rather than
reporting a clean tree.

**Anti-drift tests** re-read the REAL `gather.py` and fail when a fact this
module declares stops being true of the tree — `_RESOLVED`'s one entry and
`UNIVERSAL_DETECTOR_ROWS` are both declarations, and a declaration nobody
checks is how `ARITY_FIELDS` shipped incomplete on its first day.

**Regression tests** pin the two modelling bugs this module's own first run
had. Both produced a plausible table:

* two EVALUATE rules share `effect=Q.PITCH` (`restate_pitch` and
  `move_glyph`), so a dict keyed on the effect kept the second — and the
  `note` family, the exemplar, reported NO shape fact and NO position fact.
* keying position on *"does this decision read a position quantity"* gave
  `slur` and `tie` a **MEASURED** position off the NOTEHEADS' positions, which
  `adjudicate_arc_kind` legitimately reads for the tie/slur grammar. The
  module's own KNOWN_GAPS text said *"the NOTES' positions, not the arc's"* and
  contradicted its own table.

Neither would have been caught by a test that only asserted the tool runs.
"""

from __future__ import annotations

import ast
import unittest

from tools.omr.staged import capture
from tools.omr.staged import gather  # noqa: F401  -- the subject of the walk
from tools.omr.staged.capture import (COMPOSES, DIRECT_PIXELS, ERASED,
                                      ERASED_ELSE_INTACT,
                                      INTACT, LETTERBOXED,
                                      NO_RASTER, OWN_ERASURE, PAGE_RASTER,
                                      STAFF_GRID_POSITION, UNSCORED)


# ─────────────────────────────────────────────────────────────────────────────
# The instrument is alive
# ─────────────────────────────────────────────────────────────────────────────

class TestTheToolIsAliveAtAll(unittest.TestCase):
    """⚠️ THE POSITIVE CONTROLS, ASSERTED RATHER THAN PRINTED.

    A derived check that matches nothing reports a clean tree. `--check` exits
    2 on any control at zero; these assert the controls are non-zero in the
    first place, so a walker that silently stops matching cannot pass by
    finding nothing.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rep = capture.report()

    def test_every_control_is_non_zero(self) -> None:
        zero = [k for k, v in self.rep["controls"].items() if not v]
        self.assertEqual(zero, [], "a control at zero means the question "
                                   "never reached its subject")

    def test_it_walks_every_observe_site_gather_actually_has(self) -> None:
        # Derived on both sides: count `log.observe` in the real source and
        # require the walker to have reached at least that many quantities.
        src = (capture._HERE / "gather.py").read_text()
        calls = sum(1 for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "observe")
        self.assertGreaterEqual(self.rep["observe"]["n_sites"], calls)

    def test_check_exits_TWO_on_a_dead_control(self) -> None:
        """⚠️⚠️ THE CONTROLS ARE CHECKED BEFORE THE FINDINGS, and a test that
        only asserts they are non-zero TODAY does not test that.

        Found by a mutation arm: deleting the dead-control guard from `main`
        left every test green, because the controls are non-zero on this tree
        — so the guard could stop existing and nothing would notice. This
        forces one to zero and requires exit 2, which must beat the ordinary
        findings path (exit 0/1).
        """
        import contextlib
        import io
        real = capture.report

        def dead_report():
            rep = real()
            rep["controls"]["observe_sites_walked"] = 0
            return rep

        capture.report = dead_report
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                rc = capture.main(["--check"])
        finally:
            capture.report = real
        self.assertEqual(rc, 2)
        self.assertIn("DEAD QUESTION", err.getvalue())

    def test_nothing_is_unresolved(self) -> None:
        """⚠️ EVERY UNRESOLVED SITE IS ACCOUNTED FOR, which is a weaker claim
        than *there are none* and became the true one on 2026-09-17.

        `positions.py` emits its ten quantities through two helpers that take
        the quantity as a PARAMETER, so the walker reads a name where it needs
        a literal. Both sites are in `KNOWN_GAPS` with the argument for why
        inlining six copies to satisfy this walker would be building to the
        instrument. ⚠️ The assertion is that each unresolved site is ON that
        list — so a NEW one still fails, which is what this test is for."""
        for u in self.rep["observe"]["unresolved"]:
            with self.subTest(where=u["where"]):
                self.assertIsNotNone(
                    capture._gap_key(f"UNRESOLVED observe site {u['where']}"),
                    "an unresolved site with no KNOWN_GAPS entry")
        self.assertEqual(self.rep["rasters"]["undeclared_readers"], [])

    def test_an_unaccounted_unresolved_site_still_FAILS(self) -> None:
        """The positive control the test above needs: relaxing *there are
        none* to *they are accounted for* is only safe if an unaccounted one
        is still caught."""
        self.assertIsNone(capture._gap_key(
            "UNRESOLVED observe site _some_new_helper:1 — its quantity "
            "could not be derived"))

    def test_render_produces_the_table(self) -> None:
        out = capture.render(self.rep)
        self.assertIn("family", out)
        self.assertIn("POSITIVE CONTROLS", out)


# ─────────────────────────────────────────────────────────────────────────────
# Question 1 — SHAPE, and the `**common` trap
# ─────────────────────────────────────────────────────────────────────────────

class TestTheShapeQuestion(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.by_q = capture.observe_sites()["by_quantity"]

    def test_a_kwargs_unpack_is_FOLLOWED(self) -> None:
        """⚠️⚠️ THE TRAP THE SHIPPED TOOL FELL INTO.

        `gather_glyph_families` passes `reader`/`frame`/`score` through a
        `**common` dict. A literal-keyword walker sees none of them, and
        `gather_coverage.gathered()` reports these five as having NO READER.
        Without the unpack resolution this module would have reported five
        families as capturing no shape confidence — the reverse of the truth,
        and a finding manufactured by the instrument.
        """
        for q in ("ARC_BOX", "ARTICULATION_MARK", "FERMATA_MARK",
                  "ORNAMENT_MARK", "REST"):
            with self.subTest(q=q):
                self.assertIn(q, self.by_q)
                self.assertTrue(self.by_q[q]["scored"],
                                f"Q.{q}'s score arrives through `**common`")
                self.assertEqual(self.by_q[q]["readers"], ["DETECTOR"])

    def test_a_literal_score_is_seen_too(self) -> None:
        # The positive control for the test above: if the unpack resolution
        # broke and the literal path broke with it, both would look the same.
        self.assertTrue(self.by_q["GLYPH_BOX"]["scored"])
        self.assertEqual(self.by_q["GLYPH_BOX"]["readers"], ["DETECTOR"])

    def test_a_scoreless_quantity_is_reported_scoreless(self) -> None:
        # ⚠️ The negative control. A walker that reported everything scored
        # would pass every assertion above.
        self.assertFalse(self.by_q["NOTEHEAD_STAFF_POSITION"]["scored"])
        self.assertFalse(self.by_q["CLEF_POSITION"]["scored"])

    def test_the_common_dict_binds_the_DETECTOR(self) -> None:
        """⚠️ ANTI-DRIFT. `_RESOLVED` is a one-entry declaration; this re-reads
        `gather.py` and fails the day `common` stops binding what it says.
        """
        src = (capture._HERE / "gather.py").read_text()
        found = {}
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.FunctionDef):
                continue
            for n in ast.walk(node):
                if (isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name)
                        and n.targets[0].id in capture._ObserveWalker._RESOLVED
                        and isinstance(n.value, ast.Call)
                        and isinstance(n.value.func, ast.Name)
                        and n.value.func.id == "dict"):
                    for kw in n.value.keywords:
                        if kw.arg == "reader":
                            found[n.targets[0].id] = kw.value.attr
        self.assertEqual(found, dict(capture._ObserveWalker._RESOLVED))

    def test_loop_bound_quantities_are_resolved(self) -> None:
        """`for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, ...))`.

        A walker reading only `Q.X` literals at the call site misses BOTH.
        """
        self.assertIn("STEM", self.by_q)
        self.assertIn("BEAM_STROKE", self.by_q)
        self.assertIn("CV_LINES", self.by_q["STEM"]["readers"])

    def test_dict_update_and_subscript_keys_reach_the_detail(self) -> None:
        # `box.update(bbox_page_px=...)` and `box["frame_note"] = ...` add
        # keys AFTER the binding; a walk that stopped at the assignment would
        # under-report the detail and could not see `staff_lines_erased`.
        self.assertIn("bbox_page_px", self.by_q["ARC_BOX"]["detail"])
        self.assertIn("frame_note", self.by_q["ARC_BOX"]["detail"])

    def test_the_universal_detector_rows_have_no_class_guard(self) -> None:
        """⚠️ ANTI-DRIFT for `UNIVERSAL_DETECTOR_ROWS`.

        `gather_detections` emits `Q.GLYPH_BOX`/`Q.GLYPH_CONF` for EVERY
        detection and `Q.NOTEHEAD_CLASS` only under `if
        d.smufl_name.startswith(...)`. The guarded one is the POSITIVE
        CONTROL: a test that could not tell the two apart would pass whatever
        the file said.
        """
        src = (capture._HERE / "gather.py").read_text()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "gather_detections")

        def guarded(quantity: str) -> bool:
            for node in ast.walk(fn):
                if not isinstance(node, ast.If):
                    continue
                for n in ast.walk(node):
                    if (isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Attribute)
                            and n.func.attr == "observe"
                            and any(capture._q_name(a) == quantity
                                    for a in n.args)):
                        return True
            return False

        for q in capture.UNIVERSAL_DETECTOR_ROWS:
            with self.subTest(q=q):
                self.assertFalse(guarded(q),
                                 f"Q.{q} is no longer unconditional")
        self.assertTrue(guarded("NOTEHEAD_CLASS"),
                        "positive control: this one IS class-guarded")


# ─────────────────────────────────────────────────────────────────────────────
# Question 2 — POSITION
# ─────────────────────────────────────────────────────────────────────────────

class TestThePositionQuestion(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.rep = capture.report()
        cls.rows = {r["family"]: r for r in cls.rep["rows"]}

    def test_the_exemplar_is_found(self) -> None:
        """If this ever fails the join is broken, not the pipeline."""
        self.assertEqual(self.rows["note"]["position"],
                         ["NOTEHEAD_STAFF_POSITION"])
        self.assertTrue(self.rows["note"]["shape"])

    def test_both_evaluate_rules_with_one_effect_are_read(self) -> None:
        """⚠️⚠️ REGRESSION. `restate_pitch` and `move_glyph` BOTH declare
        `effect=Q.PITCH`. A dict keyed on the effect kept the second, and the
        `note` row came out with no shape fact and no position fact — a
        plausible-looking table that was wrong about the one family this
        module is named after.
        """
        fams = capture._family_quantities()
        self.assertEqual(fams["note"]["via"], "rule_body")
        self.assertIn("restate_pitch", fams["note"]["decision"])
        self.assertIn("move_glyph", fams["note"]["decision"])
        self.assertIn("NOTEHEAD_STAFF_POSITION", fams["note"]["reads"])

    def test_a_family_gets_no_credit_for_ANOTHER_familys_position(self) -> None:
        """⚠️⚠️ REGRESSION, and the one that contradicted this module's own
        prose. `adjudicate_arc_kind` declares `notehead_staff_position` —
        the NOTES' positions, which is the right evidence for the tie/slur
        grammar and says nothing about where the curve is.
        """
        for family in ("slur", "tie"):
            with self.subTest(family=family):
                row = self.rows[family]
                self.assertEqual(row["position"], [])
                self.assertIn("NOTEHEAD_STAFF_POSITION", row["reads_gathered"],
                              "the read is real; it is just not its own ink")

    def test_exactly_the_declared_position_quantities_are_gathered(self) -> None:
        """⚠️⚠️ THIS WENT RED ON SUCCESS, 2026-09-17, and is REWRITTEN rather
        than relaxed. It hard-coded the three position facts that existed;
        `positions.py` landed TEN more, so the literal set was a property of
        the build's progress and not of the mechanism. What it was really
        asserting — every declared position fact is actually OBSERVED, and none
        of them carries a score — is kept and now covers all thirteen.

        ⚠️ The three ORIGINALS are still named explicitly, because they are the
        ones a regression would silently drop: the ten new ones are behind a
        default-OFF flag and their absence from a run is expected.
        """
        by_q = self.rep["observe"]["by_quantity"]
        declared = {q for q in UNSCORED if capture._is_position(q)}
        self.assertTrue(
            {"NOTEHEAD_STAFF_POSITION", "CLEF_POSITION",
             "KEYSIG_RUN_POSITION"} <= declared)
        # ⚠️⚠️ AND THE TEN NEW ONES ARE **NOT** ASSERTED TO BE OBSERVED HERE,
        # WHICH IS A LOSS AND IS NAMED RATHER THAN HIDDEN. `positions.py`
        # emits them through two helpers that take the quantity as a
        # PARAMETER, so `_ObserveWalker` reads a name where it needs a literal
        # and reports the site UNRESOLVED (both are in `KNOWN_GAPS`, with the
        # argument for why inlining six copies to satisfy this walker would be
        # building to the instrument). What covers them instead is a
        # measurement on real pages: `benchmarks/omr-family-positions-2026-09/
        # probe/position_reach.py`, which counts the rows each family actually
        # produces and exits non-zero at zero.
        for q in sorted(by_q.keys() & declared):
            with self.subTest(q=q):
                self.assertFalse(by_q[q]["scored"],
                                 "a ruler reading carries no confidence")

    def test_a_position_quantity_the_walker_CAN_see_is_observed(self) -> None:
        """The positive control the test above can no longer be: the three
        original position facts ARE emitted with a literal quantity, so their
        absence from `by_quantity` would be a real regression."""
        by_q = self.rep["observe"]["by_quantity"]
        for q in ("NOTEHEAD_STAFF_POSITION", "CLEF_POSITION",
                  "KEYSIG_RUN_POSITION"):
            with self.subTest(q=q):
                self.assertIn(q, by_q, "declared and never observed")
                self.assertFalse(by_q[q]["scored"])

    def test_every_position_fact_names_a_real_family(self) -> None:
        """⚠️ REWRITTEN FOR THE TUPLE FORM. `Q.ARC_POSITION` names BOTH `slur`
        and `tie` — one quantity over one piece of ink, because two position
        rows on one arc glyph would be the *two rows from one reader are ONE
        signal* fault made by accident — so the third field is now
        `str | tuple`, read through `_families_of`. This test read it raw and
        compared a TUPLE against a set of family names."""
        known = set(self.rows)
        for q in UNSCORED:
            if not capture._is_position(q):
                continue
            with self.subTest(q=q):
                fams = capture._families_of(q)
                self.assertTrue(fams, "a position must name whose ink it is")
                for fam in fams:
                    self.assertIn(fam, known)

    def test_every_scoreless_quantity_is_classified(self) -> None:
        """⚠️ THE GUARD ON THE DECLARED HALF. A scoreless quantity in neither
        `UNSCORED` nor `KNOWN_GAPS` fails `--check` — so a FOURTH staff-grid
        position fact announces itself instead of being quietly absorbed.
        """
        self.assertEqual(self.rep["unclassified_scoreless"], [])

    def test_an_UNCLASSIFIED_quantity_IS_reported(self) -> None:
        """⚠️⚠️ THE POSITIVE CONTROL THE TEST ABOVE CANNOT BE.

        A mutation battery found this: asserting a list is EMPTY cannot
        distinguish *nothing is wrong* from *the computation always returns
        empty*. Replacing the whole derivation with `[]` left
        `test_every_scoreless_quantity_is_classified` GREEN. This drops a real
        entry from `UNSCORED` and requires the finding to appear — the same
        shape as *a battery of refusal tests needs an input that is accepted*,
        arriving against its author.
        """
        original = dict(capture.UNSCORED)
        try:
            capture.UNSCORED.pop("STEM")
            rep = capture.report()
            self.assertIn("STEM", rep["unclassified_scoreless"])
            self.assertTrue(any(p.startswith("UNCLASSIFIED Q.STEM")
                                for p in rep["problems"]))
            self.assertTrue(rep["unaccounted"], "and `--check` must fail on it")
        finally:
            capture.UNSCORED.clear()
            capture.UNSCORED.update(original)
        # The tree is restored: the clean result comes back.
        self.assertEqual(capture.report()["unclassified_scoreless"], [])

    def test_a_side_read_off_the_class_name_is_NOT_a_position(self) -> None:
        """⚠️ The distinction this module refuses to collapse. `side` is
        DERIVED FROM THE CLASS, so it fails together with the classification
        and is not an independent witness.
        """
        self.assertIn("ARTICULATION_MARK", self.rep["side_is_not_a_ruler"])
        self.assertIn("FERMATA_MARK", self.rep["side_is_not_a_ruler"])
        for family in ("articulation", "fermata", "ornament"):
            with self.subTest(family=family):
                self.assertTrue(self.rows[family]["side_in_class_name"])
                self.assertEqual(self.rows[family]["position"], [])


# ─────────────────────────────────────────────────────────────────────────────
# Question 3 — IMAGE
# ─────────────────────────────────────────────────────────────────────────────

class TestTheImageQuestion(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.ras = capture.rasters()["by_reader"]

    def _variants(self, reader: str):
        return [v["variant"] for v in self.ras[reader]["variants"]]

    def test_the_detector_reads_lines_INTACT(self) -> None:
        # The standing measured rule: never erase for the detector.
        self.assertEqual(self._variants("DETECTOR"), [INTACT])

    def test_a_silent_fallback_is_named_as_one(self) -> None:
        """`x.image_no_staff if ... is not None else x.image` — which raster
        answered is a RUNTIME fact, and the return value does not say.
        """
        self.assertIn(ERASED_ELSE_INTACT, self._variants("TEMPLATE"))
        self.assertIn(ERASED_ELSE_INTACT, self._variants("CV_LINES"))

    def test_a_getattr_access_is_seen(self) -> None:
        """⚠️⚠️ REGRESSION. `getattr(cell, "image_no_staff", None)` is not an
        `ast.Attribute`; an attribute-only walk reported `gather._ink_
        components` — the ONE rung that reads only the erased raster — as
        touching NO RASTER AT ALL, confidently and wrongly.
        """
        self.assertEqual(self._variants("CV_INK"), [ERASED])

    def test_own_erasure_is_a_THIRD_raster(self) -> None:
        """`header_ink_mask` starts from the INTACT cell and erases the lines
        ITSELF, by its own algorithm. A row saying `staff_lines_erased=True`
        would not distinguish it from `staff_line_removal`'s output.
        """
        self.assertEqual(self._variants("CV_HEADER"), [OWN_ERASURE])

    def test_a_page_reader_is_not_called_a_cell_reader(self) -> None:
        self.assertEqual(self._variants("CV_HAIRPINS"), [PAGE_RASTER])

    def test_a_reader_that_touches_no_raster_says_so(self) -> None:
        # ⚠️ GEOMETRY is the exemplar's reader: the position facts are
        # computed off line positions the geometry stage already measured, so
        # they are not a third reading of the ink at all.
        self.assertEqual(self._variants("GEOMETRY"), [NO_RASTER])

    def test_one_reader_can_cover_two_rasters_and_both_are_reported(self) -> None:
        # `clef_locator._ink_mask` is erased-preferred; the same module's
        # `_staff_left_column` is intact-only and says so in its docstring
        # (*"here the lines ARE the measurement"*). Folding them to one answer
        # would be a guess about which row came from which.
        self.assertEqual(sorted(self._variants("CV_LOCATOR")),
                         sorted([ERASED_ELSE_INTACT, INTACT]))

    def test_an_unfound_function_is_None_and_NEVER_defaulted(self) -> None:
        """⚠️⚠️ A fallback must never convert *cannot tell* into a definite
        answer — not into "same", not into "clean", and not into "intact".

        Found by a mutation arm: returning `INTACT` for a function that does
        not exist left every test green, because every function named in
        `READER_RASTER` IS found on this tree. The branch is unreachable from
        the real table, so only a direct drive can reach it.
        """
        got = capture._raster_of("yolo_detector.py", "no_such_function")
        self.assertIsNone(got["variant"])
        self.assertIn("not found", got["why"])
        # The positive control: the same call with a REAL function answers.
        real = capture._raster_of("yolo_detector.py", "detect")
        self.assertEqual(real["variant"], INTACT)

    def test_the_only_rows_that_record_their_raster_are_the_cv_line_ones(self):
        """⚠️ WIDENED 2026-09-18 FOR `Q.VERTICAL_RUN`, WHICH IS A THIRD
        `cv_lines` ROW AND RECORDS ITS RASTER FOR THE SAME REASON THE OTHER
        TWO DO: `line_detection` prefers the erased variant and falls back to
        `cell.image` SILENTLY, so without the key a whole-rung fallback is
        indistinguishable from a thin page. The test's NAME is still true --
        these are the cv-line rows -- and the point it pins is unchanged:
        every OTHER reader in GATHER still fails to say which raster
        answered, which is `capture.py`'s IMAGE finding."""
        by_q = capture.observe_sites()["by_quantity"]
        recording = {q for q, v in by_q.items()
                     if "staff_lines_erased" in v["detail"]}
        self.assertEqual(recording, {"STEM", "BEAM_STROKE", "VERTICAL_RUN"})


# ─────────────────────────────────────────────────────────────────────────────
# The instrument on synthetic code — each question, driven to a KNOWN fault
# ─────────────────────────────────────────────────────────────────────────────

class TestThereAreNoExemptions(unittest.TestCase):
    """⚠️⚠️ SEAN'S RULING, 2026-09-17, after two earlier framings of the
    POSITION question were withdrawn.

    The test for whether a family should carry a position is not *does it need
    one*, and not *does recording it compose into a useful prior*. It is: **we
    cannot yet know, therefore yes.** So EVERY family with no staff-grid
    position of its own is a finding, and `KNOWN_GAPS` holds reasons a gap
    EXISTS — never reasons one is acceptable.

    ⚠️ Scoped to DISCOVERY. A later reader must not take it as a standing claim
    that the record may grow without bound.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rep = capture.report()
        cls.rows = {r["family"]: r for r in cls.rep["rows"]}

    def test_every_family_without_a_position_is_REPORTED(self) -> None:
        """⚠️⚠️ RED ON SUCCESS, 2026-09-17, AND THE REWRITE IS THE FINDING.

        *"There is none"* and *"there is one and nothing reads it"* are
        different findings and different repairs — write the adjudicator's
        input against wire the input it already has. Until `positions.py` they
        could not be different, because no family had a position its decision
        did not read, so this test could assume ONE vocabulary (`POSITION
        <family>`). Eleven families now have a position fact that no decision
        reads, and the accurate report for them is `UNREAD-POSITION`.

        **The claim being defended is unchanged and is the one that matters:
        a family with no position reaching its decision produces a finding,
        whichever vocabulary names it. There are still no exemptions.**
        """
        missing = {f for f, r in self.rows.items() if not r["position"]}
        self.assertTrue(missing, "positive control: some family must lack one")
        reported = {p.split()[1] for p in self.rep["problems"]
                    if p.startswith("POSITION ")}
        for p in self.rep["problems"]:
            if not p.startswith("UNREAD-POSITION Q."):
                continue
            q = p.split()[1][2:]
            reported |= set(capture._families_of(q))
        self.assertEqual(missing, reported,
                         "a family with no position that produces no finding "
                         "is an exemption, and there are none")

    def test_a_class_name_SIDE_does_not_exempt_a_family(self) -> None:
        # The withdrawn framing, pinned so it cannot come back: these three
        # state a side in the class name AND are still findings.
        #
        # ⚠️ The VOCABULARY moved (see above) and the claim did not: each still
        # has `position: []` — its decision reads no position — and each still
        # produces a finding. What changed is that the finding now says the
        # fact EXISTS and is unread, which is a truer and weaker statement.
        for family in ("articulation", "fermata", "ornament"):
            with self.subTest(family=family):
                self.assertTrue(self.rows[family]["side_in_class_name"])
                self.assertEqual(self.rows[family]["position"], [])
                self.assertTrue(
                    any(p.startswith(f"POSITION {family} ")
                        or (p.startswith("UNREAD-POSITION Q.")
                            and family in capture._families_of(p.split()[1][2:]))
                        for p in self.rep["problems"]),
                    f"{family} produces no position finding of any kind")

    def test_no_gap_reason_reads_as_an_exemption(self) -> None:
        """⚠️ A reason saying a gap is FINE is the category that was deleted."""
        banned = ("probably fine", "no gap", "not a gap", "acceptable",
                  "needs none", "does not need", "no position is needed")
        for key, reason in capture.KNOWN_GAPS.items():
            low = reason.lower()
            for phrase in banned:
                with self.subTest(key=key, phrase=phrase):
                    self.assertNotIn(phrase, low)


class TestLocationIsNotPosition(unittest.TestCase):
    """⚠️ A GRADING OF WHAT IS THERE, NEVER AN EXEMPTION.

    A staff-space float composes across documents; a raw page pixel does not,
    because pages differ in size and dpi; a canonical-cell box does not either,
    and `Q.ONSET_COLUMN` already paid for that — two staves' canonical frames
    coincide BY CONSTRUCTION, so agreeing there is evidence of nothing.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = {r["family"]: r for r in capture.report()["rows"]}

    def test_a_family_with_only_page_and_cell_frames_does_not_compose(self):
        for family in ("rest", "time", "slur"):
            with self.subTest(family=family):
                self.assertNotIn(COMPOSES, self.rows[family]["location_frames"])

    def test_a_staff_relative_fact_DOES_compose(self) -> None:
        # ⚠️ The positive control. A grader that answered "does not compose"
        # for everything would pass the test above for the wrong reason.
        for family in ("note", "dynamic", "wedge"):
            with self.subTest(family=family):
                self.assertIn(COMPOSES, self.rows[family]["location_frames"])

    def test_a_position_quantitys_VALUE_counts_even_with_cell_detail_keys(self):
        """⚠️ REGRESSION. `Q.CLEF_POSITION` and `Q.KEYSIG_RUN_POSITION` carry a
        staff-grid float as the VALUE and cell-frame keys beside it, so grading
        the detail keys alone reported `clef` and `key` as not composing — the
        two families that certainly do.
        """
        for family in ("clef", "key"):
            with self.subTest(family=family):
                self.assertTrue(self.rows[family]["position"])
                self.assertIn(COMPOSES, self.rows[family]["location_frames"])

    def test_placement_is_not_filed_as_a_class_name_side(self) -> None:
        """⚠️ REGRESSION. `placement` is DERIVED FROM THE BAND and `side` is
        read off the CLASS NAME — opposite provenances. Folding them made the
        `direction` family report *"the class name states a SIDE"* about a word
        that is not in the class space at all.
        """
        self.assertEqual(self.rows["direction"]["side_in_class_name"], [])
        self.assertTrue(self.rows["direction"]["coarse_band_only"])


class TestNothingAccumulatesAcrossDocuments(unittest.TestCase):
    """⚠️ Sean's aggregate question needs a store and a conditioning variable,
    and the tool reports that neither is reachable. Derived, with counts, so
    neither half is taken on trust.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.xd = capture.across_documents()

    def test_data_holds_no_store_of_measured_geometry(self) -> None:
        # Reported by LISTING, so adding a store falsifies the claim.
        self.assertTrue(self.xd["data_dirs"], "positive control: data/ exists")
        for d in self.xd["data_dirs"]:
            with self.subTest(d=d):
                self.assertIn(d, {"dossiers", "score-library", "user-labeled",
                                  "user-labeled-clef-fix",
                                  "user-labeled-distill25"})

    def test_publisher_IS_now_reachable_in_gather(self) -> None:
        """⚠️⚠️ RED ON SUCCESS, 2026-09-17, and REWRITTEN rather than deleted.

        This asserted `== 0` — *publisher reaches no code in GATHER* — and it
        was true when written. `gather_document_identity` closed it, so the
        assertion became a claim the tree contradicts. CLAUDE.md records the
        same shape the day the last stub closed: eight assertions went red
        because the thing they asserted had been achieved, and none was
        deleted. The mechanism is still exercised — the number must now be
        NON-zero, so the tool still has to find it.
        """
        self.assertGreater(
            self.xd["publisher_in_gather_code"], 0,
            "publisher stopped reaching GATHER — the positional store's "
            "conditioning variable is gone")

    def test_but_the_catalog_HAS_it(self) -> None:
        """⚠️ THE POSITIVE CONTROL, and it still earns its keep after the
        closure: the reachability above is worth nothing if the catalog holds
        no publisher to reach for.
        """
        cat = self.xd["catalog"]
        self.assertTrue(cat["present"])
        self.assertGreater(cat["with_publisher"], 200)
        self.assertGreater(cat["distinct_publishers"], 100)

    def test_it_is_on_entries_NOT_on_the_editions_map(self) -> None:
        """⚠️ A reader that went to `editions` for it would find nothing and
        conclude it was absent — so the tool states where it actually lives.
        """
        self.assertNotIn("publisher", self.xd["catalog"]["on_editions_map"])


class TestTheResolutionQuestion(unittest.TestCase):
    """⚠️ QUESTION 4 (`A-INK-2`) — is the consumer getting the resolution the
    SOURCE actually has? `OMR_DPI` is a constant applied to a scanned plate,
    which has a native resolution, and to a vector page, which has none.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.nat = capture.native_resolution()
        cls.ras = capture.rasters()["by_reader"]

    def test_nothing_reads_the_native_pixel_dimensions(self) -> None:
        self.assertEqual(self.nat["native_keys_read"], [])
        for k in ("width", "height"):
            with self.subTest(k=k):
                self.assertIn(k, self.nat["native_keys_unread"])

    def test_the_walk_CAN_see_a_key_being_read(self) -> None:
        """⚠️⚠️ THE POSITIVE CONTROL, AND WITHOUT IT THE ZERO ABOVE IS
        WORTHLESS. A walker that could not see a subscript reports every key
        as unread — which is exactly how the flag-direction guard's first
        version passed vacuously. `bbox` and `Filter` ARE read from the image
        dictionary by `input_domain._classify_page`, so they must appear.
        """
        self.assertIn("bbox", self.nat["keys_they_read"])
        self.assertIn("Filter", self.nat["keys_they_read"])

    def test_it_finds_the_module_that_already_opens_the_dictionary(self) -> None:
        # `OMR_WEIGHT_ROUTING`'s shipped classifier: it reads the adjacent
        # facts out of the very dict that carries the native resolution.
        self.assertIn("input_domain.py",
                      self.nat["modules_opening_the_image_dict"])

    def test_letterboxed_and_direct_pixels_are_NOT_flattened(self) -> None:
        """⚠️⚠️ The distinction the measured `OMR_IMGSZ` result turns on.
        *Larger is NOT better* is about the DETECTOR — ultralytics letterboxes
        to `imgsz²` whatever the cell's size, so a big value buys anchors and
        false noteheads. A geometry or CV reader has neither, so that finding
        says nothing about it, and a table with one column for both would
        licence quoting it against every reader in the pipeline.
        """
        self.assertEqual(self.ras["DETECTOR"]["resolution"], LETTERBOXED)
        for reader in ("CV_LINES", "CV_INK", "CV_HAIRPINS", "TEMPLATE"):
            with self.subTest(reader=reader):
                self.assertEqual(self.ras[reader]["resolution"], DIRECT_PIXELS)

    def test_a_reader_with_no_raster_is_not_called_direct_pixels(self) -> None:
        self.assertEqual(self.ras["GEOMETRY"]["resolution"], NO_RASTER)

    def test_the_resolution_probe_reads_the_signature_not_a_name_list(self) -> None:
        # Driven straight at the derivation: `imgsz` in the signature is what
        # makes a reader letterboxed, so the real entry point must answer.
        self.assertEqual(
            capture._resolution_of("yolo_detector.py", "detect"), LETTERBOXED)
        self.assertEqual(
            capture._resolution_of("line_detection.py", "detect_stems"),
            DIRECT_PIXELS)


class TestTheWalkerOnSyntheticCode(unittest.TestCase):

    def test_it_finds_a_score_passed_literally(self) -> None:
        src = ("def g(log):\n"
               "    log.observe(s, Q.THING, v, reader=READERS.DETECTOR,\n"
               "                frame=f, score=0.5)\n")
        got = capture.observe_sites(src)["by_quantity"]
        self.assertTrue(got["THING"]["scored"])

    def test_it_finds_a_score_passed_through_a_dict(self) -> None:
        src = ("def g(log):\n"
               "    common = dict(reader=READERS.DETECTOR, frame=f, score=0.5)\n"
               "    log.observe(s, Q.THING, v, **common)\n")
        got = capture.observe_sites(src)["by_quantity"]
        self.assertTrue(got["THING"]["scored"])

    def test_a_scoreless_site_is_NOT_reported_scored(self) -> None:
        src = ("def g(log):\n"
               "    log.observe(s, Q.THING, v, reader=READERS.GEOMETRY,\n"
               "                frame=f)\n")
        got = capture.observe_sites(src)["by_quantity"]
        self.assertFalse(got["THING"]["scored"])

    def test_an_unresolvable_quantity_is_NAMED_never_dropped(self) -> None:
        """⚠️ A fallback here never converts *cannot tell* into an answer. A
        site whose quantity cannot be derived lands in `unresolved`, which
        `--check` fails on; a silent skip is how a derivation quietly stops
        covering the thing it names.
        """
        src = ("def g(log):\n"
               "    log.observe(s, some_runtime_q, v, reader=r, frame=f)\n")
        rep = capture.observe_sites(src)
        self.assertEqual(rep["by_quantity"], {})
        self.assertEqual(len(rep["unresolved"]), 1)
        self.assertEqual(rep["unresolved"][0]["shape"], "quantity")


# ─────────────────────────────────────────────────────────────────────────────
# The gap inventory
# ─────────────────────────────────────────────────────────────────────────────

class TestItDoesNotSILENCEItsSiblings(unittest.TestCase):
    """⚠️⚠️ AN AUDITOR THAT NAMES A KEY IS NOT A CONSUMER OF IT.

    This module asks whether a row records which raster it came from, so
    `"staff_lines_erased"` appears in its own source. `wiring`'s DETAIL
    question reports a key written and read by nobody — and it counted that
    mention as a read, turning its own two entries STALE and taking
    `wiring --check` from 0 to 1 on a key still consumed by nothing.

    The control was run BEFORE the conclusion: `wiring --check` exits 0 on the
    base commit and 1 with this module added, so the break is this module's
    and not pre-existing. (`gather_coverage --check` exits 2 on BOTH, which is
    what a pre-existing failure looks like.)
    """

    def test_this_module_declares_itself_a_derived_check(self) -> None:
        self.assertIs(capture.DERIVED_CHECK, True)

    def test_wiring_skips_it_and_NOT_a_real_consumer(self) -> None:
        from tools.omr.staged import wiring
        self.assertTrue(wiring._declares_derived_check(
            capture._HERE / "capture.py"))
        # ⚠️ THE POSITIVE CONTROL. A predicate that answered True for
        # everything would pass the assertion above and silence the question
        # for every module in the tree.
        for other in ("gather.py", "export.py", "record.py"):
            with self.subTest(other=other):
                self.assertFalse(wiring._declares_derived_check(
                    capture._HERE / other))

    def test_the_marker_is_read_from_the_AST_not_by_substring(self) -> None:
        """A mention in a comment must not opt a real consumer out."""
        import pathlib
        import tempfile
        from tools.omr.staged import wiring
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "pretend.py"
            p.write_text("# DERIVED_CHECK = True\n"
                         "x = 'DERIVED_CHECK = True'\n")
            self.assertFalse(wiring._declares_derived_check(p))
            p.write_text("DERIVED_CHECK = True\n")
            self.assertTrue(wiring._declares_derived_check(p))

    def test_wiring_still_reports_the_key_this_module_names(self) -> None:
        """The repair must not close the finding — only stop this module from
        closing it. Every `staff_lines_erased` entry must still be LIVE.

        ⚠️ 2 -> 3 ON 2026-09-18: `Q.VERTICAL_RUN` carries the same key for the
        same reason and it is unread there too. The number is the TREE's, not
        this line's -- what the test pins is that none of them is closed by a
        module MENTIONING the key, which is the hazard it was written for.
        """
        from tools.omr.staged import wiring
        rep = wiring.report()
        live = [p for p in rep["problems"] if "staff_lines_erased" in p]
        self.assertEqual(len(live), 3, rep["problems"])
        self.assertEqual(rep["unaccounted"], [])
        self.assertEqual(rep["stale_gaps"], [])


class TestTheGapInventory(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.rep = capture.report()

    def test_check_is_clean_on_this_tree(self) -> None:
        self.assertEqual(self.rep["unaccounted"], [],
                         "a NEW finding must be added to KNOWN_GAPS with its "
                         "reason, or fixed")

    def test_no_entry_is_stale(self) -> None:
        """⚠️ A CLOSED GAP MUST LEAVE THE LIST, or it stops describing the
        pipeline and starts describing its history.
        """
        self.assertEqual(self.rep["stale_gaps"], [])

    def test_the_gap_list_is_not_a_suppression_list(self) -> None:
        # Every entry carries a reason with substance, not a placeholder.
        for key, reason in capture.KNOWN_GAPS.items():
            with self.subTest(key=key):
                self.assertGreater(len(reason), 60, f"{key} has no reason")

    def test_main_exits_zero_and_check_exits_zero(self) -> None:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(capture.main([]), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(capture.main(["--check"]), 0)
        self.assertIn("family", buf.getvalue())

    def test_unaccounted_and_stale_are_inverse(self) -> None:
        # The instrument's own control: a problem matching no key is
        # unaccounted, and a key matching no problem is stale.
        self.assertEqual(capture.unaccounted(["ZZZ nothing matches this"]),
                         ["ZZZ nothing matches this"])
        # ⚠️ RED ON SUCCESS: the sample key was `"POSITION time"`, which LEFT
        # `KNOWN_GAPS` on 2026-09-17 when the `time` family got a position
        # fact — a closed gap must LEAVE the list or the list stops describing
        # the pipeline and starts describing its history. Keyed on a LIVE
        # entry instead, and asserted derivedly so the next closure renames
        # nothing: EVERY key is stale when nothing is reported.
        self.assertEqual(sorted(capture.stale_gaps([])),
                         sorted(capture.KNOWN_GAPS))


if __name__ == "__main__":
    unittest.main()
