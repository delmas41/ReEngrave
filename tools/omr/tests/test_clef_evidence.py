"""The clef readers' EVIDENCE, as against which of them won.

`staff["clef_source"]` names the winner. It says nothing about the readers that
declined, and this project's most-repeated defect is a number computed at the
moment of a refusal and destroyed by the same expression that refuses. Two such
sites feed `staff["clef_evidence"]`:

* `clef_locator.locate_clef` has taken a `trace` out-parameter since it was
  written, filled it with the branch that ended the call and the geometry of the
  cluster that ended it — and NEITHER pipeline call site passed one, so in
  production the reason was computed and dropped on every staff the locator
  declined.
* the detector's clef argmax in `_detections_for_cell` keeps a running
  `best_clef_conf` and discards it, so a clef won at 0.98 over nothing and one
  won at 0.26 over a 0.25 runner-up were indistinguishable downstream.

A third feeds `staff["clef_proposal_evidence"]`:

* `clef_correction.propose_clef` has FIVE returns, four of them refusals, and
  every one discarded the whole `fits` table — so the additive-vs-gated survey
  had to reimplement the function to learn that ~50% of both populations exit
  at `already_in_effect`. (Five returns, SEVEN exit labels: two of the five
  `_note` sites are ternaries. One of the seven is unreachable with the shipped
  constants, which is asserted rather than faked.)

⚠️ Every test here was run RED first, with the recording removed, to prove it
exercises the mechanism rather than passing on the shape of an empty dict —
this repo has shipped a test that passed vacuously (the margin-label blob test
asserting on label LENGTH). The wiring tests are the ones that most need it:
an AST assertion that a call site passes an argument fails open if it looks in
the wrong place.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.omr import transcribe as T
from tools.omr.clef_correction import correct_clefs_from_instruments, propose_clef
from tools.omr.instruments import lookup
from tools.omr.tests.test_clef_locator import (
    blank_page,
    cell_with_c_clef,
    draw_g_clef,
    draw_noteheads,
    make_cell,
)


BASSOON = lookup("Fag.").instrument


def _notehead(pitch, x):
    return {"category": "notehead", "class": "noteheadBlack", "pitch": pitch,
            "bbox": [x, 0, 10, 10]}


def _staff_dict(pitches, clef):
    dets = [_notehead(p, 20 + 40 * i) for i, p in enumerate(pitches)]
    return {"staff_index": 0, "clef": clef, "key_signature": None,
            "measures": [{"measure_index": 0, "clef": clef,
                          "key_signature": None, "detections": dets}]}


#: Twelve notes far above a bassoon — the documented failure, a missed clef
#: defaulting to treble.
def _bassoon_staff_reading_treble():
    return _staff_dict(["C5", "D5", "E5", "F5", "G5", "A5",
                        "B5", "C6", "D5", "E5", "F5", "G5"], "treble")


def _staff_in_bass_register(clef):
    return _staff_dict(["C3", "D3", "E3", "F3", "G3", "A3",
                        "B2", "C3", "D3", "E3", "F3", "G2"], clef)


def _short_staff():
    return _staff_dict(["C5", "D5", "E5"], "treble")


def _percussion_staff():
    return _staff_dict(["C5"] * 12, "percussion")


class _NoDetections:
    """A detector that sees nothing — so the CV locator is reached."""

    def __init__(self, dets=()):
        self._dets = list(dets)

    def detect(self, cell, **kwargs):
        return list(self._dets)


def _run(cell, detector=None, **kwargs):
    """`_detections_for_cell` with an evidence dict attached. Returns it."""
    evidence: dict = {}
    T._detections_for_cell(
        detector or _NoDetections(),
        cell,
        conf_threshold=0.25,
        imgsz=512,
        iou_threshold=0.5,
        agnostic_nms=True,
        active_key_sig={},
        active_time_sig=None,
        clef_evidence=evidence,
        **{"active_clef": None, "read_clef": True, **kwargs},
    )
    return evidence


# ─── the locator's trace reaches the record ────────────────────────────────


class TestLocatorTraceIsRecorded:
    def test_a_located_clef_records_why_it_was_located(self):
        evidence = _run(cell_with_c_clef(4))
        trace = evidence["cv_locator"]
        assert trace["reason"] == "located"
        assert trace["clef"] == "tenor"
        # The geometry the decision was made on, not merely the verdict.
        assert trace["symmetry"] > 0
        assert trace["w_spaces"] > 0 and trace["h_spaces"] > 0

    def test_a_REFUSAL_records_the_branch_that_refused(self):
        """The population that was being lost: the locator says no, and until
        now said nothing about why — including the NUMBER it said no on.

        A G clef in the header reaches the snap and is turned away there, so
        this staff's record now carries the symmetry (0.80) and the size the
        refusal was made on. Those are exactly the quantities
        `benchmarks/omr-clef-geometry/` had to reimplement the locator to see.
        """
        img = blank_page()
        draw_g_clef(img)
        draw_noteheads(img)
        trace = _run(make_cell(img))["cv_locator"]
        assert trace["reason"] == "ambiguous_snap", trace
        assert trace["symmetry"] > 0
        assert trace["w_spaces"] > 0 and trace["h_spaces"] > 0
        assert trace["clusters"], "the geometry it judged, not just the verdict"

    def test_a_refusal_with_nothing_to_measure_says_so(self):
        """Not every refusal has a number behind it, and the record must not
        invent one: a header holding no glyph-sized ink refuses at
        `no_clusters`, with no cluster geometry to report."""
        img = blank_page()
        draw_noteheads(img)          # note ink, all of it past the header strip
        trace = _run(make_cell(img))["cv_locator"]
        assert trace["reason"] == "no_clusters"
        assert trace["clusters"] == []
        assert "symmetry" not in trace

    def test_the_crop_it_read_is_named(self):
        """A rejecting branch is about INK, and the header cell and the measure
        cell do not hold the same ink — so which one was read is part of the
        reading."""
        evidence = _run(cell_with_c_clef(3))
        assert evidence["cv_locator"]["cell"] == "measure"
        header = cell_with_c_clef(3)
        evidence = _run(cell_with_c_clef(3), header_cell=header,
                        prefer_header=True)
        assert evidence["cv_locator"]["cell"] == "header"

    def test_nothing_is_recorded_when_the_locator_is_off(self):
        """Recording must not manufacture a reading. With the locator disabled
        there is no refusal to record, and the key is absent rather than empty.
        """
        evidence = _run(cell_with_c_clef(4), locate_c_clefs=False)
        assert "cv_locator" not in evidence

    def test_the_locator_does_not_run_when_the_detector_already_read_a_clef(self):
        """The gate is unchanged: the locator only ever spoke where
        `clef_source` was still None, and recording must not widen its reach."""
        cell = cell_with_c_clef(4)
        evidence = _run(cell, detector=_NoDetections([_clef_detection(cell)]))
        assert "cv_locator" not in evidence


def _clef_detection(cell, *, name="clefG", conf=0.9, y=118, h=88):
    """A detector output the clef pass will resolve — a G clef straddling the
    staff's second line from the bottom, which is where one belongs."""
    from tools.omr.template_matcher import SymbolDetection

    return SymbolDetection(
        cell=cell,
        smufl_name=name,
        category="clef",
        x_canonical=22,
        y_canonical=y,
        width_canonical=40,
        height_canonical=h,
        confidence=conf,
    )


# ─── the wiring, asserted against the source ───────────────────────────────


class TestBothCallSitesPassATrace:
    """`locate_clef` filling a trace nobody passes is the exact bug this fixes,
    so the test is on the CALL SITES and not on the recorder.

    Run RED by deleting `trace=` from either call — verified for both.
    """

    def test_every_locate_clef_call_in_transcribe_passes_a_trace(self):
        source = Path(inspect.getfile(T)).read_text()
        tree = ast.parse(source)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "locate_clef"
        ]
        assert len(calls) == 2, (
            "expected the two known call sites — the measure loop's and the "
            f"header pre-pass's — found {len(calls)}"
        )
        for call in calls:
            kwargs = {kw.arg for kw in call.keywords}
            assert "trace" in kwargs, (
                f"locate_clef at line {call.lineno} discards its own reasoning"
            )


# ─── the detector's argmax, and that it WAS a contest ──────────────────────


class TestClefContestIsRecorded:
    """`best_clef_conf` is initialised to -1.0, used once, and discarded — so
    a clef won at 0.98 unopposed and a clef won at 0.26 over a 0.25 runner-up
    left the same trace: `clef_source == "detector"`. These pin the record of
    the margin. Run RED with the `clef_evidence["contest"]` block removed.
    """

    def test_an_uncontested_reading_records_no_runner_up(self):
        cell = cell_with_c_clef(4)
        evidence = _run(cell, detector=_NoDetections([_clef_detection(cell)]))
        contest = evidence["contest"]
        assert contest["winner"] == "treble"
        assert contest["winner_confidence"] == pytest.approx(0.9)
        assert contest["n_resolved"] == 1
        assert "runner_up" not in contest and "margin" not in contest

    def test_a_close_contest_records_the_margin_and_the_loser(self):
        """The quantity the audit is about: two clefs, four hundredths apart,
        and downstream this used to be indistinguishable from a walkover."""
        cell = cell_with_c_clef(4)
        winner = _clef_detection(cell, name="clefG", conf=0.29, y=118, h=88)
        loser = _clef_detection(cell, name="clefF", conf=0.25, y=98, h=48)
        evidence = _run(cell, detector=_NoDetections([winner, loser]))
        contest = evidence["contest"]
        assert contest["winner"] == "treble"
        assert contest["runner_up"] == "bass"
        assert contest["runner_up_confidence"] == pytest.approx(0.25)
        assert contest["margin"] == pytest.approx(0.04, abs=1e-6)
        assert contest["disagrees"] is True

    def test_two_boxes_agreeing_is_a_duplicate_not_a_contest(self):
        """A contest is only interesting where the candidates DISAGREE. Two
        boxes on one glyph both reading treble would otherwise inflate this
        population on exactly the dense pages anyone would read it on."""
        cell = cell_with_c_clef(4)
        a = _clef_detection(cell, conf=0.90)
        b = _clef_detection(cell, conf=0.40)
        contest = _run(cell, detector=_NoDetections([a, b]))["contest"]
        assert contest["runner_up"] == "treble"
        assert contest["disagrees"] is False

    def test_a_candidate_the_geometry_could_not_NAME_is_still_recorded(self):
        """"The detector fired at 0.9 and nothing could be made of it" is a
        different page from "nothing fired", and the argmax `continue`d past
        both identically."""
        cell = cell_with_c_clef(4)
        # Zero height: the snap has nothing to measure, so `resolve_clef`
        # abstains — and the detection is still evidence that it fired.
        unnameable = _clef_detection(cell, name="clefUnpitchedPercussion",
                                     conf=0.77)
        contest = _run(cell, detector=_NoDetections([unnameable]))["contest"]
        assert contest["n_candidates"] == 1
        assert contest["n_resolved"] == 0
        assert contest["candidates"][0]["resolved"] is False
        assert contest["candidates"][0]["confidence"] == pytest.approx(0.77)

    def test_the_winner_matches_the_clef_that_was_actually_used(self):
        """The record must describe the decision, not a parallel one. A
        recording that could disagree with the verdict would be worse than
        none — the standard this repo set for uncalibrated probabilities."""
        cell = cell_with_c_clef(4)
        dets = [_clef_detection(cell, name="clefF", conf=0.6, y=98, h=48),
                _clef_detection(cell, name="clefG", conf=0.8)]
        evidence: dict = {}
        _, active_clef, _, _, source = T._detections_for_cell(
            _NoDetections(dets), cell,
            conf_threshold=0.25, imgsz=512, iou_threshold=0.5,
            agnostic_nms=True, active_clef=None, active_key_sig={},
            active_time_sig=None, read_clef=True, clef_evidence=evidence,
        )[:5]
        assert source == "detector"
        assert active_clef.startswith(evidence["contest"]["winner"])


class TestBlockedReadersAreRecorded:
    def test_the_header_gap_fill_says_why_it_did_not_run(self):
        """A gap-fill pass that never fires because someone always speaks
        first is a different finding from one that fires and finds nothing —
        and both used to look like silence."""
        cell = cell_with_c_clef(4)
        evidence = _run(cell, detector=_NoDetections([_clef_detection(cell)]),
                        header_cell=cell)
        assert evidence["detector_header"]["skipped"] == "another reader spoke"

    def test_the_header_gap_fill_records_what_it_read_when_it_does_run(self):
        cell = cell_with_c_clef(4)
        # Nothing detected anywhere, so the locator claims the staff and the
        # header pass is not reached; disable the locator to reach it.
        evidence = _run(cell, header_cell=cell, locate_c_clefs=False)
        assert "read" in evidence["detector_header"]


# ─── the clef proposal's fits table, at every exit ─────────────────────────


class TestProposeClefRecordsItsFits:
    """Four refusals and one proposal, and the `fits` table survives all five.

    Every test here was run RED with the `_note` calls and the `trace["fits"]`
    assignment removed.
    """

    def test_a_proposal_records_the_table_it_was_chosen_from(self):
        staff = _bassoon_staff_reading_treble()
        trace: dict = {}
        proposal = propose_clef(staff, BASSOON, trace=trace)
        assert proposal is not None
        assert trace["exit"] == "proposed"
        assert trace["fits"]["bass"] > 0.9 and trace["fits"]["treble"] < 0.2
        assert trace["branch"] == "convention"
        assert trace["n_noteheads"] == 12

    def test_ALREADY_IN_EFFECT_is_named_and_carries_its_fits(self):
        """The exit the survey had to reimplement the function to count — and
        the one where the refusal is least interesting and the TABLE most so:
        this staff measured a perfect fit and reported nothing."""
        staff = _staff_in_bass_register(clef="bass")
        trace: dict = {}
        assert propose_clef(staff, BASSOON, trace=trace) is None
        assert trace["exit"] == "already_in_effect"
        assert trace["chosen"] == "bass"
        assert trace["fits"]["bass"] == pytest.approx(1.0)
        assert trace["current_fit"] == pytest.approx(1.0)

    def test_too_few_noteheads_records_how_few(self):
        trace: dict = {}
        assert propose_clef(_short_staff(), BASSOON, trace=trace) is None
        assert trace["exit"] == "too_few_noteheads"
        assert trace["n_noteheads"] == 3
        # ⚠️ The table is recorded even here. A register estimate not worth
        # ACTING on is still the measurement that was made.
        assert trace["fits"]

    def test_an_unanchored_clef_is_the_one_exit_with_nothing_behind_it(self):
        """Recording must not invent a table. With no anchor no shift can be
        computed, so there is no `fits` to report and the record says so."""
        trace: dict = {}
        assert propose_clef(_percussion_staff(), BASSOON, trace=trace) is None
        assert trace["exit"] == "no_clef_anchor"
        assert "fits" not in trace
        assert trace["current_clef"] == "percussion"

    def test_NO_MARGIN_records_the_two_fits_that_were_too_close(self):
        """The range-only branch: the convention is contradicted, so the best
        fit has to win by MIN_FIT_MARGIN — and the margin it failed by is the
        whole content of the refusal."""
        cello = lookup("Vc.").instrument
        staff = _staff_dict(["D4", "A3", "C3", "E3", "G3", "C3",
                             "F4", "C3", "C4", "C3", "D3", "G4"], "treble")
        trace: dict = {}
        assert propose_clef(staff, cello, trace=trace) is None
        assert trace["exit"] == "no_margin"
        assert trace["branch"] == "range_only"
        # treble and alto both place every note in range: nothing to choose.
        assert trace["margin"] == pytest.approx(0.0)
        assert trace["fits"]["treble"] == trace["fits"]["alto"]

    def test_WOULD_WORSEN_FIT_is_recorded_apart_from_already_in_effect(self):
        """A different finding about a staff, and the pass exits at the same
        `return None`: the convention's clef was proposable and places FEWER
        notes in range than the one already in effect."""
        horn = lookup("Cor.").instrument
        staff = _staff_dict(["B3", "G4", "A3", "G3", "B3", "B4",
                             "A3", "D4", "E3", "C4", "F4", "D4"], "tenor")
        trace: dict = {}
        assert propose_clef(staff, horn, trace=trace) is None
        assert trace["exit"] == "would_worsen_fit"
        assert trace["chosen"] == "treble"
        assert trace["chosen_fit"] < trace["current_fit"]

    def test_the_SEVENTH_exit_label_is_unreachable_and_that_is_why_it_is_untested(
            self):
        """⚠️ Five `_note` sites yield SEVEN labels, not six — two are
        ternaries. Review caught the undercount, and the missing one
        (`no_candidate_clefs`) has zero test hits for a reason better than
        neglect: it cannot fire.

        `fits` is empty only if every CANDIDATE_CLEFS entry fails
        `clef_diatonic_shift`, and all four are in `_CLEF_ANCHORS` — so once
        `current` clears the anchor test there is always a table. Asserting the
        unreachability is worth more than a monkeypatched hit, because the day
        someone adds an unanchored candidate this goes red and the branch
        becomes live.
        """
        from tools.omr.clef_correction import CANDIDATE_CLEFS
        from tools.omr.pitch_resolver import _CLEF_ANCHORS, clef_diatonic_shift

        assert all(c in _CLEF_ANCHORS for c in CANDIDATE_CLEFS), (
            "an unanchored candidate makes `no_candidate_clefs` reachable — "
            "give it a test"
        )
        for anchored in _CLEF_ANCHORS:
            assert any(clef_diatonic_shift(anchored, c) is not None
                       for c in CANDIDATE_CLEFS), anchored

    def test_the_recorded_exit_agrees_with_the_verdict(self):
        """A record that could disagree with the decision would be worse than
        none. `proposed` if and only if a proposal came back."""
        for staff, instrument in (
            (_bassoon_staff_reading_treble(), BASSOON),
            (_staff_in_bass_register(clef="bass"), BASSOON),
            (_short_staff(), BASSOON),
            (_percussion_staff(), BASSOON),
            (_staff_dict(["D4", "A3", "C3", "E3", "G3", "C3",
                          "F4", "C3", "C4", "C3", "D3", "G4"], "treble"),
             lookup("Vc.").instrument),
            (_staff_dict(["B3", "G4", "A3", "G3", "B3", "B4",
                          "A3", "D4", "E3", "C4", "F4", "D4"], "tenor"),
             lookup("Cor.").instrument),
        ):
            trace: dict = {}
            got = propose_clef(staff, instrument, trace=trace)
            assert (trace["exit"] == "proposed") is (got is not None)

    def test_the_caller_puts_the_record_on_the_staff_even_when_it_refuses(self):
        """The wiring: a refusal writes nothing to `clef_proposal`, so before
        this a declined staff carried no trace of the pass at all."""
        staff = _staff_in_bass_register(clef="bass")
        page = {"page_index": 0, "systems": [
            {"system_index": 0, "staves": [staff]}]}
        records = correct_clefs_from_instruments(
            [page], {0: BASSOON}, {(0, 0, 0): 0}, apply=False)
        assert records == []                      # it refused, as before
        assert staff["clef_proposal_evidence"]["exit"] == "already_in_effect"
        assert "clef_proposal" not in staff


# ─── the flip: a LATER cell overturning the staff's clef ───────────────────


class TestTheOverturnIsRecorded:
    """⚠️ `read_clef` does NOT gate the detector argmax.

    An earlier version of the caller passed `clef_evidence` only on
    `cell_idx == 0`, on the stated grounds that "only the staff's first cell
    reads a clef". That is false in the failure direction: `read_clef` gates the
    CV locator, the header rung and the specialist, and the argmax is ungated —
    it sets `clef_source = "detector"` on EVERY cell. So one detection in the
    middle of a staff can flip its clef, and those cells were exactly the ones
    the record was skipping.

    ⚠️ `disagrees` cannot answer this. Each such flip is the ONLY clef detection
    in its cell, so it carries `n_resolved == 1` and no `disagrees` key at all;
    the comparison that matters is the winner against the INHERITED clef.

    ⚠️ And `overturns_inherited` is PRE-REPAIR — it says the argmax flipped the
    clef, not that the flip reached the file. The dossier override runs later
    and can put the inherited clef back, so a probe reading `measure["clef"]`
    counts survivors and will report fewer. Different quantities; do not
    difference them.
    """

    def test_read_clef_does_not_gate_the_argmax(self):
        """The falsified premise, pinned so it cannot be re-assumed."""
        cell = cell_with_c_clef(4)
        det = _clef_detection(cell, name="clefF", conf=0.5, y=98, h=48)
        _dets, active_clef, _ks, _ts, source = T._detections_for_cell(
            _NoDetections([det]), cell,
            conf_threshold=0.25, imgsz=512, iou_threshold=0.5,
            agnostic_nms=True, active_clef="treble", active_key_sig={},
            active_time_sig=None, read_clef=False,
        )[:5]
        assert source == "detector", "the argmax ran with read_clef False"
        assert active_clef == "bass", "...and it moved the staff's clef"

    def test_a_later_cell_that_OVERTURNS_the_inherited_clef_says_so(self):
        cell = cell_with_c_clef(4)
        det = _clef_detection(cell, name="clefF", conf=0.32, y=98, h=48)
        contest = _run(cell, detector=_NoDetections([det]),
                       active_clef="treble", read_clef=False)["contest"]
        assert contest["clef_in_effect_before"] == "treble"
        assert contest["clef_in_effect_after"] == "bass"
        assert contest["overturns_inherited"] is True
        assert contest["read_clef_rung_ran"] is False
        # ...and this is exactly the shape `disagrees` cannot see.
        assert contest["n_resolved"] == 1
        assert "disagrees" not in contest

    def test_a_later_cell_that_CONFIRMS_the_inherited_clef_says_so(self):
        cell = cell_with_c_clef(4)
        contest = _run(cell, detector=_NoDetections([_clef_detection(cell)]),
                       active_clef="treble", read_clef=False)["contest"]
        assert contest["clef_in_effect_before"] == "treble"
        assert contest["overturns_inherited"] is False

    def test_a_staff_opening_with_no_inherited_clef_does_not_claim_an_overturn(
            self):
        """None is not a clef, and a first reading is not an overturn."""
        cell = cell_with_c_clef(4)
        contest = _run(cell, detector=_NoDetections([_clef_detection(cell)]),
                       active_clef=None)["contest"]
        assert contest["clef_in_effect_before"] is None
        assert contest["overturns_inherited"] is False

    def test_a_cell_that_decided_NOTHING_records_nothing(self):
        """The population is bounded on purpose: a mid-staff cell with no clef
        detection and no reader rung decided nothing, and a record on each of a
        112-measure page's cells would be noise rather than evidence."""
        evidence = _run(cell_with_c_clef(4), active_clef="treble",
                        read_clef=False)
        assert "contest" not in evidence


# ─── the wiring, asserted against the source ───────────────────────────────


class TestTheClefRecordIsWiredIn:
    """⚠️ THIS CLASS EXISTS BECAUSE ITS ABSENCE WAS CAUGHT IN REVIEW.

    Every other test in this file calls `_detections_for_cell` directly, so
    deleting the `clef_evidence=` argument from `transcribe()`'s only call site
    — switching the entire record off in production — left all 44 of them green.
    The key-signature site got an AST wiring guard and the clef site, with the
    harder wiring, did not.

    Each test below was run RED: the argument deleted, the value re-gated to
    `cell_idx == 0`, and each of the two dict writes removed in turn.
    """

    @staticmethod
    def _calls(name):
        source = Path(inspect.getfile(T)).read_text()
        return [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == name
        ]

    def test_the_pipeline_call_site_passes_clef_evidence(self):
        calls = self._calls("_detections_for_cell")
        # Counted BEFORE iterating: `all([])` over an empty list is True, and a
        # wiring test that passes when it found nothing guards nothing.
        assert len(calls) == 1, (
            f"expected transcribe()'s one call site, found {len(calls)}"
        )
        assert "clef_evidence" in {kw.arg for kw in calls[0].keywords}, (
            "the whole record is switched off at the call site"
        )

    def test_the_record_is_NOT_gated_back_to_the_first_cell(self):
        """The blocking defect this class was added for. A conditional value
        here means later cells pass None, and the mid-staff flips — the
        population the sweep exists for — go unrecorded."""
        call, = self._calls("_detections_for_cell")
        value, = [kw.value for kw in call.keywords if kw.arg == "clef_evidence"]
        assert not isinstance(value, ast.IfExp), (
            "clef_evidence is passed conditionally; `read_clef` does not gate "
            "the detector argmax, so every cell can read a clef"
        )
        assert isinstance(value, ast.Name), (
            f"expected a plain name, got {type(value).__name__}"
        )

    def test_both_the_staff_and_the_measure_are_given_the_record(self):
        source = Path(inspect.getfile(T)).read_text()
        # ⚠️ `ast.Store` is load-bearing. Without it a future READ of
        # `clef_evidence` would satisfy the count while one of the two WRITES
        # had been deleted — a guard that stops guarding on someone else's
        # unrelated edit. This branch's third blocking finding was a guard that
        # did not guard; not leaving a second one open.
        writes = [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "clef_evidence"
            and isinstance(node.ctx, ast.Store)
        ]
        assert len(writes) >= 2, (
            "expected the staff-level and measure-level writes; found "
            f"{len(writes)}"
        )
