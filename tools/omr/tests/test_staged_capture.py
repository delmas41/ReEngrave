"""`staged.capture` — SHAPE, POSITION and IMAGE, asked of every family.

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
from tools.omr.staged.capture import (ERASED, ERASED_ELSE_INTACT, INTACT,
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
        self.assertEqual(self.rep["observe"]["unresolved"], [])
        self.assertEqual(self.rep["rasters"]["undeclared_readers"], [])

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
        by_q = self.rep["observe"]["by_quantity"]
        declared = {q for q, (k, _r, _f) in UNSCORED.items()
                    if k == STAFF_GRID_POSITION}
        self.assertEqual(declared, {"NOTEHEAD_STAFF_POSITION", "CLEF_POSITION",
                                    "KEYSIG_RUN_POSITION"})
        for q in declared:
            with self.subTest(q=q):
                self.assertIn(q, by_q)
                self.assertFalse(by_q[q]["scored"],
                                 "a ruler reading carries no confidence")

    def test_every_position_fact_names_a_real_family(self) -> None:
        known = set(self.rows)
        for q, (kind, _reason, fam) in UNSCORED.items():
            if kind == STAFF_GRID_POSITION:
                with self.subTest(q=q):
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
        by_q = capture.observe_sites()["by_quantity"]
        recording = {q for q, v in by_q.items()
                     if "staff_lines_erased" in v["detail"]}
        self.assertEqual(recording, {"STEM", "BEAM_STROKE"})


# ─────────────────────────────────────────────────────────────────────────────
# The instrument on synthetic code — each question, driven to a KNOWN fault
# ─────────────────────────────────────────────────────────────────────────────

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
        self.assertIn("POSITION time", capture.stale_gaps([]))


if __name__ == "__main__":
    unittest.main()
