"""`Q.KEYSIG_MARKER` — declared in `wants` AND `composed_from`, read by
nothing, and `no_evidence` was wrong on roughly half the staves it named.

⚠️ THE FAULT. `adjudicate_key_signature` abstains `no_evidence` when the CV
header reader produced no run. Measured on the two shared staged records,
**7 of 17** (Litolff) and **9 of 20** (Breitkopf) of those staves carry
DETECTED key accidentals. The detector saw ink; the fitter could not use it.
Reporting that as *no evidence* is the ABSENT/DECLINED collapse this record
exists to prevent, and it sends the next person to the wrong module — *nothing
was printed* wants a reader, *we could not fit what was printed* wants a
fitter.

⚠️⚠️ THE STATED REASON FOR LEAVING THE QUANTITY UNREAD WAS FALSE, which is why
it survived two gap lists. Both excused it as *"the decision reads
`keysig_clef_fit`, which the markers already feed in GATHER"*. They do not:
`Q.KEYSIG_CLEF_FIT` comes from `locate_key_signature` on the header CROP, and
the only place detections enter that call is `_occupied_boxes` — which filters
to NOTEHEADS. A gap list holds reasons a gap EXISTS; this one held a reason
that was not true.

⚠️ AND THE REPAIR IS A REASON, NEVER A VALUE. Counting key markers is a rule
this project has already built and condemned — seven spurious key flips on the
legacy path — and the staged record agrees from its own side: the marker count
equals the settled `|fifths|` on only 39% and 51% of decided staves.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

SUB = R.staff(0, 0, 0)


def _with_clef(log, clef="treble", sub=SUB):
    log.observe(sub, Q.CLEF_GLYPH, {"treble": "clefG", "bass": "clefF"}[clef],
                reader=READERS.DETECTOR, frame="cell:0", score=0.95)


#: ⚠️ ONE STAFF SPACE, AND WITHOUT IT THE DECISION ABSTAINS `no_cell_scale`.
#: The marker x's are in the CELL's canonical frame, so the slot test has no
#: unit until `Q.CELL_STAFF_SPACE` is filed — which is a refusal, not a
#: fixture wart: guessing the scale is how three flats become five.
SPACE = 85.0


def _space(log, sub=SUB):
    log.observe(R.cell(sub.page, sub.system, sub.staff, 0),
                Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY,
                frame="cell:0")


def _markers(log, *classes, sub=SUB):
    for i, c in enumerate(classes):
        log.observe(sub, Q.KEYSIG_MARKER, c, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.4, x=float(i) * SPACE,
                    y_center=0.0)


def _decide(log):
    adjudicate.run(log)
    return log.verdict(Q.KEY_SIGNATURE, SUB)


class TestTheSplit(unittest.TestCase):

    def test_ink_with_no_run_is_NOT_called_no_evidence(self):
        """⚠️ THE SPLIT SURVIVED ITS OWN REASON WORD. Until roadmap 2.9 this
        was an ABSTENTION named `markers_without_a_run`; the markers are the
        reading now, so the same staff DECIDES — but the thing this test was
        written to prevent is unchanged and still asserted: a staff the
        detector saw ink on may never come back as `no_evidence`."""
        log = Log()
        _with_clef(log)
        _space(log)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertNotEqual(v.reason, "no_evidence")
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.detail["keysig_marker_ink"], 3)

    def test_no_ink_and_no_run_really_is_no_evidence(self):
        """The positive control for the test above: without it, a rule that
        renamed EVERY abstention would pass."""
        log = Log()
        _with_clef(log)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")
        self.assertEqual(v.detail["keysig_marker_ink"], 0)

    def test_the_marker_CLASSES_are_recorded(self):
        log = Log()
        _with_clef(log)
        _markers(log, "keyFlat", "keySharp")
        v = _decide(log)
        self.assertEqual(v.detail["keysig_marker_classes"],
                         ["keyFlat", "keySharp"])


class TestTheCountBECAMETheReading(unittest.TestCase):
    """⚠️⚠️ THIS CLASS WAS CALLED `TestItIsNeverAVALUE` AND ITS PREMISE WAS
    OVERTURNED ON 2026-09-23. It asserted that markers may never decide a key,
    on two measurements: the legacy count-the-markers fallback cost SEVEN
    spurious key flips over eleven scanned pages, and the marker count equals
    the settled `|fifths|` on only 39% (Litolff) and 51% (Breitkopf) of
    decided staves.

    ⚠️ BOTH NUMBERS STAND; WHAT CHANGED IS WHICH SIDE THEY CONDEMN. The
    second was read as *the markers are unreliable*. Scoring both readings
    against the movement's own key — Beethoven 5 mvt 1 and Brahms 1 mvt 1 are
    C minor, so each staff's printed signature follows from its instrument —
    showed it was the FITTERS that disagreed: 330 right against 171 on
    Breitkopf, 50 against 45 on the engraved acceptance page. The first
    number is answered by what the legacy fallback did NOT have: a slot
    ladder rather than a count, and a system check behind it.

    ⚠️ AND THE LITOLFF COST IS REAL AND STAYS ASSERTED ELSEWHERE: on that
    MERGING plate the markers trade 25 abstentions for 10 more right and 15
    more wrong. `benchmarks/omr-key-majority-2026-09/FINDINGS.md`.
    """

    def test_markers_alone_DO_decide_a_key(self):
        log = Log()
        _with_clef(log)
        _space(log)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "markers")

    def test_markers_DO_overturn_a_fitted_reading(self):
        """Three markers beside a one-flat fit: the fit was reading one flat
        where the detector had drawn three boxes, which is the defect on the
        engraved acceptance page, 24 staves of 30."""
        log = Log()
        _with_clef(log)
        _space(log)
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=1, fifths=-1)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "markers")

    def test_the_overruled_fit_is_RECORDED(self):
        """⚠️ THE HALF THAT KEEPS THE OLD WARNING ALIVE. A reader that was
        overruled is the measurement of which reader to work on next; if the
        markers were ever the wrong side of this, the record is where that
        shows. Dropping the loser is how the evidence disappears."""
        log = Log()
        _with_clef(log)
        _space(log)
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=1, fifths=-1)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        said = v.detail["disagreeing_readers"]
        self.assertEqual(said[0]["fifths"], -1)
        self.assertEqual(said[0]["n_accidentals"], 1)

    def test_a_TEMPLATE_reading_is_overturned_the_same_way(self):
        log = Log()
        _with_clef(log)
        _space(log)
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, accidental="b", fifths=-3)
        _markers(log, "keyFlat")
        v = _decide(log)
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "markers")
        self.assertEqual(v.detail["disagreeing_readers"][0]["fifths"], -3)

    def test_an_AGREEING_fit_is_not_filed_as_a_disagreement(self):
        """The positive control for the test above: without it a rule that
        recorded EVERY fit as disagreeing would pass."""
        log = Log()
        _with_clef(log)
        _space(log)
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, accidental="b", fifths=-3)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertNotIn("disagreeing_readers", v.detail)
        self.assertEqual(v.detail["corroborated_by"], 1)


class TestTheDeclarations(unittest.TestCase):

    def test_the_reason_is_declared(self):
        """⚠️ A reason word with no branch is one documented anti-pattern here;
        a branch returning an UNDECLARED reason is its mirror.

        ⚠️ `markers_without_a_run` is GONE and its absence is asserted, not
        merely unmentioned: the branch it named is now the ordinary reading
        path, and a reason word left declared with nothing returning it is the
        first anti-pattern above."""
        from tools.omr.staged.adjudicate import REGISTRY, _ensure_decisions
        _ensure_decisions()
        reasons = REGISTRY[Q.KEY_SIGNATURE].reasons
        self.assertIn("markers", reasons)
        self.assertIn("mixed_marker_kinds", reasons)
        self.assertNotIn("markers_without_a_run", reasons)

    def test_the_quantity_is_actually_read_now(self):
        from tools.omr.staged.adjudicate import REGISTRY, _ensure_decisions
        import inspect
        from tools.omr.staged.adjudicators import header
        _ensure_decisions()
        self.assertIn(Q.KEYSIG_MARKER, REGISTRY[Q.KEY_SIGNATURE].wants)
        src = (inspect.getsource(header.adjudicate_key_signature)
               + inspect.getsource(header._marker_ink))
        self.assertIn("Q.KEYSIG_MARKER", src)


class TestTheStatedReasonWasFalse(unittest.TestCase):
    """⚠️⚠️ The claim both gap lists carried, checked rather than inherited:
    *"the markers already feed `keysig_clef_fit` in GATHER"*. They do not.

    This is asserted at SOURCE level because the consequence is invisible in
    behaviour — a decision reading a quantity that was never going to reach it
    produces the same answers as one that does not read it at all."""

    def test_the_marker_gatherer_RETURNS_NOTHING_to_feed_a_fit_with(self):
        """`_gather_keysig_markers` only LOGS. It hands its caller no value at
        all, so there is no route by which a marker could reach
        `locate_key_signature` — which is the call `Q.KEYSIG_CLEF_FIT` is
        filed from."""
        import inspect
        from tools.omr.staged import gather as g
        src = inspect.getsource(g._gather_keysig_markers)
        self.assertNotIn("return ", src.replace("return\n", ""),
                         "it returns a value; the excuse might have been true")
        fit_src = inspect.getsource(g.gather_key_signature)
        self.assertIn("locate_key_signature(crop", fit_src)

    def test_the_only_detections_reaching_the_fit_are_NOTEHEADS(self):
        import inspect
        from tools.omr.staged import gather as g
        src = inspect.getsource(g._occupied_boxes)
        self.assertIn("_NOTEHEAD_PREFIX", src)
        for cls in ("keySharp", "keyFlat", "keyNatural"):
            self.assertNotIn(cls, src)


if __name__ == "__main__":
    unittest.main()


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️⚠️ SIX MUTATIONS SURVIVED THE FIRST BATTERY. One was a real gap in the
# code's tests; the other five were the INSTRUMENTS' own controls, which no
# suite imported — the same shape the sibling lane hit, arriving again because
# a benchmark arm is a script and nothing exercises it by default.
# ─────────────────────────────────────────────────────────────────────────────


class TestTheNoInkBranchStillSaysWHICHSilence(unittest.TestCase):
    """⚠️ SURVIVOR 1, and it is this repair's own lesson one level down.

    The no-ink branch records `keysig_marker_state` beside its zero, because
    *the detector produced no row* and *it produced a row saying it saw
    nothing* are different facts. Deleting that left every assertion green:
    the tests checked the COUNT was 0 and never that the record could still
    say which kind of zero it was — which is precisely the ABSENT/DECLINED
    collapse this whole change exists to repair."""

    def test_a_staff_with_no_marker_row_records_its_STATE(self):
        log = Log()
        _with_clef(log)
        v = _decide(log)
        self.assertEqual(v.detail["keysig_marker_ink"], 0)
        self.assertIn("keysig_marker_state", v.detail)

    def test_a_DECLINED_marker_row_is_not_the_same_zero(self):
        """An abstention filed BY the detector is a row saying 'I looked and
        saw nothing' — a different fact from no row at all, and the state is
        what carries it."""
        from tools.omr.staged.record import ABSTAIN
        log = Log()
        _with_clef(log)
        log.abstain(SUB, Q.KEYSIG_MARKER, reader=READERS.DETECTOR,
                    frame="cell:0", reason=ABSTAIN.NO_DETECTIONS)
        v = _decide(log)
        self.assertEqual(v.detail["keysig_marker_ink"], 0)
        self.assertNotEqual(v.detail["keysig_marker_state"],
                            _no_row_state(),
                            "a DECLINED row and NO row must not report the "
                            "same state — that is the collapse this change "
                            "repairs, reappearing inside the repair")


def _no_row_state():
    log = Log()
    _with_clef(log)
    return _decide(log).detail["keysig_marker_state"]


class TestTheInstrumentsOwnControls(unittest.TestCase):
    """⚠️ SURVIVORS 2-6. `check_arm.py` and `probe_records.py` are scripts; no
    suite imports them, so every battery arm against them was free. These
    drive their `main()` over synthetic records — the point is the CONTROL's
    behaviour, not a measurement."""

    @staticmethod
    def _load(name):
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        path = root / "benchmarks" / "omr-keysig-staged-reach-2026-09" / name
        spec = importlib.util.spec_from_file_location(f"_{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _record(tmp, *, key_verdict, with_clef=True, with_fit=True,
                with_markers=False, keysig_glyph_cells=()):
        import json
        obs, n = [], 0

        def ob(subject, quantity, value, frame, score=None, **d):
            nonlocal n
            row = {"id": f"obs:{n:06d}", "subject": subject,
                   "quantity": quantity, "value": value, "score": score,
                   "reader": READERS.DETECTOR, "frame": frame, "detail": d}
            obs.append(row)
            n += 1

        if with_clef:
            # ⚠️ THE SCORE IS NOT DECORATION. `_with_clef` supplies 0.95 and
            # the clef decision needs it; without one the rebuild abstains
            # `needs_clef` and this fixture silently tests a different branch.
            ob("staff/0/0/0", Q.CLEF_GLYPH, "clefG", "cell:0", score=0.95)
        if with_fit:
            ob("staff/0/0/0", Q.KEYSIG_CLEF_FIT, "treble", "header_window",
               n_accidentals=1, fifths=-1)
        if with_markers:
            ob("staff/0/0/0", Q.KEYSIG_MARKER, "keyFlat", "cell:0")
        for i, cell in enumerate(keysig_glyph_cells):
            # `glyph/<page>/<system>/<staff>/<cell>/<n>` — the address the
            # probe reads a detection's CELL INDEX out of.
            ob(f"glyph/0/0/0/{cell}/{i}", Q.GLYPH_BOX,
               ["keyFlat", 0.0, 0.0, 1.0, 1.0], f"cell:{cell}")
        verdicts = []
        if key_verdict is not None:
            verdicts.append(dict(
                {"id": "vrd:000001", "subject": "staff/0/0/0",
                 "quantity": Q.KEY_SIGNATURE, "decider": "t"},
                **key_verdict))
        p = tmp / "rec.json"
        p.write_text(json.dumps({"record": {"observations": obs,
                                            "abstentions": [],
                                            "verdicts": verdicts}}))
        return str(p)

    def _run(self, mod, argv):
        """⚠️⚠️ `mod.HERE` IS REDIRECTED, AND THAT IS NOT TIDINESS.

        Both instruments write their results under `HERE/"out"`, which is a
        COMMITTED measurement artefact. The first version of these tests drove
        `main()` without redirecting it and **silently overwrote
        `out/probe-records.json` with the synthetic fixture's numbers** — the
        committed record of a real measurement, replaced by a one-staff test
        page, with nothing failing. It was caught by a later command reading
        that file and finding `rec.json` in it.

        An instrument that destroys its own artefact when exercised is worse
        than one with no test, because the artefact still LOOKS like a
        measurement."""
        import io, contextlib, shutil, sys as _sys, tempfile
        from pathlib import Path
        old_argv, old_here = _sys.argv, mod.HERE
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            # ⚠️ The SIBLING instruments come too: `check_arm` loads
            # `probe_records.py` from `HERE` to compare their restated
            # constant, so redirecting `HERE` alone breaks that check rather
            # than exercising it.
            for f in old_here.glob("*.py"):
                shutil.copy(f, Path(d) / f.name)
            mod.HERE = Path(d)
            (mod.HERE / "out").mkdir()
            _sys.argv = ["x"] + argv
            try:
                with contextlib.redirect_stdout(buf):
                    rc = mod.main()
            finally:
                _sys.argv, mod.HERE = old_argv, old_here
        return rc, buf.getvalue()

    def test_the_tests_do_not_write_into_the_committed_out_dir(self):
        """The guard for the hazard `_run` documents, asserted rather than
        trusted: after driving both instruments, the real `out/` is untouched."""
        import tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        out = root / "benchmarks" / "omr-keysig-staged-reach-2026-09" / "out"
        before = {f.name: f.stat().st_mtime_ns for f in out.glob("*.json")}
        probe = self._load("probe_records.py")
        with tempfile.TemporaryDirectory() as d:
            self._run(probe, [self._record(Path(d), key_verdict=None)])
        after = {f.name: f.stat().st_mtime_ns for f in out.glob("*.json")}
        self.assertEqual(before, after,
                         "an instrument's test must not rewrite the committed "
                         "artefact of its own measurement")

    # ── the arm ──────────────────────────────────────────────────────────
    def test_the_arm_DECLARES_ITSELF_SUPERSEDED(self):
        """⚠️⚠️ FOUR CONTROLS STOOD HERE AND THE RULE THEY ARMED IS GONE.

        They asserted that `check_arm.py` FAILS when a decided key moved,
        PASSES on a faithful record, REFUSES an abstention move outside
        `no_evidence -> markers_without_a_run`, and reports DEAD when no split
        happened. All four rest on the 2026-09-21 rule that reading
        `Q.KEYSIG_MARKER` may only SPLIT AN ABSTENTION REASON — and roadmap
        2.9 (Sean, 2026-09-23) made those markers the PRIMARY reader, so
        moving a decided key is now the point rather than the regression.

        Rewriting them to arm the new rule would be a different instrument
        wearing this one's name; leaving them red would report a replacement
        as a regression. So the arm asks the REGISTRY whether its rule still
        exists and says SUPERSEDED when it does not — which is a live check,
        not a comment: restore `markers_without_a_run` and it runs again. Its
        measurement stands in its own directory's `FINDINGS.md`, and the new
        one is `benchmarks/omr-key-majority-2026-09/`.
        """
        import tempfile
        from pathlib import Path
        arm = self._load("check_arm.py")
        with tempfile.TemporaryDirectory() as d:
            path = self._record(Path(d), with_fit=False, with_markers=True,
                                key_verdict={"outcome": "abstained",
                                             "value": None,
                                             "reason": "no_evidence"})
            rc, out = self._run(arm, [path])
        self.assertEqual(rc, 2, out)
        self.assertIn("SUPERSEDED", out)
        # ⚠️ The positive control on the banner itself: it must NOT be printed
        # unconditionally. The probe-constant check still runs before it.
        self.assertIn("CLASSES", out)

    def test_the_arm_REFUSES_a_drifted_probe_constant(self):
        """The probe restates `_KEYSIG_CLASSES` rather than importing it, so
        the two instruments stay independent. A drift would make them measure
        different populations in silence; the arm refuses instead."""
        import tempfile
        from pathlib import Path
        arm = self._load("check_arm.py")
        # Drift is symmetric, so it is induced on the side that needs no
        # import machinery: the arm's own copy of the tree's tuple.
        real = arm._KEYSIG_CLASSES
        arm._KEYSIG_CLASSES = ("keySharp",)
        try:
            with tempfile.TemporaryDirectory() as d:
                path = self._record(Path(d), key_verdict=None)
                rc, out = self._run(arm, [path])
        finally:
            arm._KEYSIG_CLASSES = real
        self.assertEqual(rc, 3, out)
        self.assertIn("REFUSED", out)

    # ── the probe ────────────────────────────────────────────────────────
    def test_the_probe_counts_ONLY_later_cells_as_out_of_reach(self):
        """⚠️ SURVIVOR. The whole Q2 finding is that the out-of-reach
        population is SMALL — 21 and 2 — against 105 and 146 in cell 0.
        Counting cell 0 into it inflates those to 126 and 148 and turns a
        *"do not build this yet"* into a *"look how much is missing"*, and
        no test could see the difference."""
        import tempfile
        from pathlib import Path
        probe = self._load("probe_records.py")
        with tempfile.TemporaryDirectory() as d:
            path = self._record(
                Path(d), with_markers=True,
                keysig_glyph_cells=(0, 0, 0, 0, 3, 7),   # 4 in cell 0, 2 later
                key_verdict={"outcome": "abstained", "value": None,
                             "reason": "no_evidence"})
            rc, out = self._run(probe, [path])
        self.assertEqual(rc, 0, out)
        self.assertIn("cells != 0: 2", out)
        self.assertIn("cell 0 holds 4", out)

    def test_the_probe_declares_itself_DEAD_with_no_key_verdicts(self):
        import tempfile
        from pathlib import Path
        probe = self._load("probe_records.py")
        with tempfile.TemporaryDirectory() as d:
            path = self._record(Path(d), key_verdict=None)
            rc, out = self._run(probe, [path])
        self.assertEqual(rc, 2, out)
        self.assertIn("DEAD", out)
