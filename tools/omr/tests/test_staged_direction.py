"""Direction words on the staged path: the gatherer, the decision, the file.

⚠️⚠️ THE CENTRAL TESTS HERE ARE THE FOUR STATES, and they are what must go RED
if the gatherer's reasons are collapsed. A machine with neither `.venv-surya`
nor Tesseract reads zero directions on every page EXACTLY as a page with no
directions printed on it does -- `direction_text.read_directions` says so in
its own docstring and returns the counts to say it with, and until 2026-09-11
nothing consumed them. CLAUDE.md's governing rule is that a fallback must
never convert *cannot tell* into a definite answer; "this bar carries no
words" is a definite answer, so the two cannot share an outcome.

⚠️ THE LEXICON IS NOT TESTED HERE AND MUST NOT BE. It is
`direction_lexicon`'s, it is load-bearing, and nothing in the staged path
touches it -- a test asserting what it accepts would be a second, differently
spelled copy of it.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS


# ─────────────────────────────────────────────────────────────────────────────
# A page just real enough for the gatherer
# ─────────────────────────────────────────────────────────────────────────────


def _cell(measure_index, *, staff_index=0, page=0, x0=100):
    return SimpleNamespace(
        page_index=page, system_index=0, staff_index=staff_index,
        measure_index=measure_index,
        bbox_page_px=(x0, 200, x0 + 100, 400),
        upscale_factor=2.0)


def _pws():
    return SimpleNamespace(page=SimpleNamespace(page_index=0), staves=[])


def _run(log, *, candidates, found, info=None, readers=(("surya", None),),
         cells=None, detections=None, monkey=True):
    """Drive the REAL gatherer with the reader's two entry points stubbed.

    ⚠️ THE READER IS STUBBED AND THE GATHERER IS NOT, which is the split this
    file is about. What `find_candidates` and `read_directions` return is
    `direction_text`'s business and is measured on real pages; what GATHER
    does with the four answers they can give is this module's, and is what a
    unit test can pin.
    """
    from tools.omr import direction_text as DT
    cells = _CELLS if cells is None else cells
    detections = {} if detections is None else detections
    local = {0: (0, 0)}
    info = {"n_read": 0, "rejected": [], "conflicts": []} if info is None \
        else info
    old = (DT.find_candidates, DT.read_directions, DT.default_readers)
    try:
        if monkey:
            DT.find_candidates = lambda *a, **k: list(candidates)
            DT.read_directions = lambda *a, **k: (list(found), dict(info))
            DT.default_readers = lambda *a, **k: list(readers)
        G.gather_direction_words(log, _pws(), cells, local, detections)
    finally:
        (DT.find_candidates, DT.read_directions,
         DT.default_readers) = old
    return log


_CELLS = [_cell(0), _cell(1)]


def _cand(measure=0, staff=0, x=150, placement="below", n=4):
    from tools.omr.direction_text import TextCandidate
    return TextCandidate(staff_index=staff, measure_index=measure,
                         bbox_page=(x, 410, x + 60, 430),
                         placement=placement, n_components=n)


def _text(cand, text="legato", category="expression", reader="surya"):
    from tools.omr.direction_text import DirectionText
    return DirectionText(staff_index=cand.staff_index,
                         measure_index=cand.measure_index,
                         x_page=cand.x_page, text=text, category=category,
                         placement=cand.placement, terms=(text,),
                         reader=reader)


def _reasons(log, quantity=Q.DIRECTION_WORD):
    return {r.reason for r in log.all_rows()
            if getattr(r, "quantity", None) == quantity
            and hasattr(r, "reason")}


# ─────────────────────────────────────────────────────────────────────────────
# 1. The four states
# ─────────────────────────────────────────────────────────────────────────────


class TestTheFourStatesAreDistinguishable(unittest.TestCase):
    """⚠️ EACH ASSERTS THE *REASON*, NEVER MERELY THE COUNT. Every one of these
    four produces the same empty `<direction>` list in the file; the whole
    value of the record here is that the FILE cannot tell them apart and the
    RECORD can."""

    def test_no_ocr_rung_is_READER_UNAVAILABLE(self):
        log = _run(Log(), candidates=[_cand()], found=[], readers=[])
        self.assertIn(ABSTAIN.READER_UNAVAILABLE, _reasons(log))
        self.assertNotIn(ABSTAIN.NO_INK, _reasons(log))

    def test_no_ocr_rung_speaks_even_with_NO_candidates(self):
        """⚠️ THE BRANCH THE WHOLE FAMILY IS BUILT FOR. A machine with no OCR
        produces the same zero on every page; without a row here the record
        would carry the zero and not the blindness, which is the fallback
        converting *cannot tell* into "this page prints no words"."""
        log = _run(Log(), candidates=[], found=[], readers=[])
        self.assertIn(ABSTAIN.READER_UNAVAILABLE, _reasons(log))

    def test_rungs_ran_and_the_CV_found_nothing_is_NO_INK(self):
        log = _run(Log(), candidates=[], found=[])
        self.assertIn(ABSTAIN.NO_INK, _reasons(log))
        self.assertNotIn(ABSTAIN.READER_UNAVAILABLE, _reasons(log))

    def test_a_candidate_nobody_accepted_is_NO_READING(self):
        log = _run(Log(), candidates=[_cand()], found=[])
        self.assertIn(ABSTAIN.NO_READING, _reasons(log))
        self.assertIn(ABSTAIN.NOT_IN_LEXICON, _reasons(log),
                      "the page-level 'ran and accepted nothing' row is "
                      "missing")

    def test_an_accepted_word_is_an_OBSERVATION(self):
        c = _cand()
        log = _run(Log(), candidates=[c], found=[_text(c)])
        obs = [o for o in log.all_rows()
               if getattr(o, "quantity", None) == Q.DIRECTION_WORD
               and not hasattr(o, "reason")]
        self.assertEqual([o.value for o in obs], ["legato"])
        self.assertEqual(obs[0].detail["category"], "expression")
        self.assertEqual(obs[0].detail["placement"], "below")

    def test_the_flag_being_off_is_OUT_OF_SCOPE_not_NO_INK(self):
        """⚠️ A DELIBERATELY DISABLED READER IS NOT A PAGE WITH NO WORDS. It
        is also read the way a DEFAULT-ON flag must be -- an off WORD, never
        an allow-list -- so a typo leaves the reader ON."""
        import os
        old = os.environ.get("OMR_DIRECTION_TEXT")
        try:
            os.environ["OMR_DIRECTION_TEXT"] = "0"
            log = _run(Log(), candidates=[_cand()], found=[])
            self.assertIn(ABSTAIN.OUT_OF_SCOPE, _reasons(log))
            os.environ["OMR_DIRECTION_TEXT"] = "yess"      # a typo
            log2 = _run(Log(), candidates=[_cand()], found=[])
            self.assertNotIn(ABSTAIN.OUT_OF_SCOPE, _reasons(log2),
                             "a typo turned a default-ON reader off")
        finally:
            if old is None:
                os.environ.pop("OMR_DIRECTION_TEXT", None)
            else:
                os.environ["OMR_DIRECTION_TEXT"] = old

    def test_a_reader_that_RAISES_is_READER_UNAVAILABLE_not_silence(self):
        from tools.omr import direction_text as DT
        old = DT.find_candidates
        try:
            def _boom(*a, **k):
                raise RuntimeError("surya wedged")
            DT.find_candidates = _boom
            log = Log()
            G.gather_direction_words(log, _pws(), _CELLS, {0: (0, 0)}, {})
        finally:
            DT.find_candidates = old
        self.assertIn(ABSTAIN.READER_UNAVAILABLE, _reasons(log))

    def test_every_cell_ends_with_exactly_one_state(self):
        """⚠️ A PARTITION, not a selection: `coverage()`'s `abstained` dict is
        only meaningful over the page's bars if each bar is filed once."""
        c = _cand(measure=0)
        log = _run(Log(), candidates=[c], found=[_text(c)])
        seen = {}
        for row in log.all_rows():
            if getattr(row, "quantity", None) != Q.DIRECTION_WORD:
                continue
            sub = row.subject.at(R.Kind.CELL)
            if sub is None:
                continue                      # the page-level counts row
            seen.setdefault(sub.to_key(), []).append(row)
        self.assertEqual(sorted(seen), ["cell/0/0/0/0", "cell/0/0/0/1"])
        self.assertEqual([len(v) for v in seen.values()], [1, 1])


# ─────────────────────────────────────────────────────────────────────────────
# 2. The shim — the corner/width hazard, directly
# ─────────────────────────────────────────────────────────────────────────────


class TestThePageDictShim(unittest.TestCase):
    def test_a_detection_arrives_as_x_y_W_H_not_as_corners(self):
        """⚠️⚠️ THE HAZARD THIS REPO HAS PAID FOR TWICE. `_page_box` returns
        CORNERS and `direction_text._blank_detections` reads WIDTHS; confusing
        them does not raise, it blanks the wrong rectangle and the word
        survives as unaccounted ink. The fixture puts the cell at x0=100 ON
        PURPOSE -- at the origin the two spellings agree in every coordinate
        and the test would pass either way, which is the frame-error lesson
        the arc work recorded.
        """
        det = SimpleNamespace(smufl_name="noteheadBlack", category="notehead",
                              x_canonical=20.0, y_canonical=40.0,
                              width_canonical=8.0, height_canonical=6.0,
                              confidence=0.9)
        page = G._direction_page_dict(
            _pws(), [_cell(0)], {0: (0, 0)},
            {"cell/0/0/0/0": [det]})
        box = page["systems"][0]["staves"][0]["measures"][0]["detections"][0]
        # cell x0=100, y0=200, upscale 2.0 -> page x 110, y 220, w 4, h 3
        self.assertEqual(box["bbox_page"], [110, 220, 4, 3])

    def test_measure_spans_are_corners_because_the_reader_reads_them_so(self):
        page = G._direction_page_dict(_pws(), [_cell(0)], {0: (0, 0)}, {})
        m = page["systems"][0]["staves"][0]["measures"][0]
        self.assertEqual(m["bbox_page_px"], [100, 200, 200, 400])
        from tools.omr.direction_text import _measure_spans
        self.assertEqual(_measure_spans(
            page["systems"][0]["staves"][0]), [(0, 100, 200)])


# ─────────────────────────────────────────────────────────────────────────────
# 3. The decision
# ─────────────────────────────────────────────────────────────────────────────


class TestTheDecision(unittest.TestCase):
    def _decide(self, log, cell=R.cell(0, 0, 0, 0)):
        log.freeze()
        adjudicate.run(log)
        return log.verdict(Q.DIRECTION, cell)

    def test_it_decides_the_accepted_words(self):
        c = _cand()
        v = self._decide(_run(Log(), candidates=[c], found=[_text(c)]))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, ["legato"])
        self.assertEqual(v.reason, "in_lexicon")

    def test_two_words_in_one_bar_come_out_in_PAGE_X_ORDER(self):
        a, b = _cand(x=400), _cand(x=150)
        log = _run(Log(), candidates=[a, b],
                   found=[_text(a, "dolce"), _text(b, "legato")])
        self.assertEqual(self._decide(log).value, ["legato", "dolce"])

    def test_no_words_is_a_DECISION_and_no_rung_is_an_ABSTENTION(self):
        """⚠️⚠️ THE ONE THAT MUST GO RED IF THE STATES ARE COLLAPSED. Both
        produce an empty list in the file; only the record separates them, and
        only if these are different OUTCOMES."""
        ran = self._decide(_run(Log(), candidates=[], found=[]))
        self.assertIs(ran.outcome, Outcome.DECIDED)
        self.assertEqual(ran.value, [])
        self.assertEqual(ran.reason, "no_words")

        blind = self._decide(_run(Log(), candidates=[], found=[], readers=[]))
        self.assertIs(blind.outcome, Outcome.ABSTAINED)
        self.assertEqual(blind.reason, ABSTAIN.READER_UNAVAILABLE)

    def test_a_refused_candidate_is_still_a_DECISION_that_the_bar_is_empty(self):
        """The rungs RAN over this bar and the lexicon refused what they read.
        That is a reading of the page, not a missing rung -- and the count of
        refusals rides on the verdict so the shortfall is attributable."""
        v = self._decide(_run(Log(), candidates=[_cand()], found=[]))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, [])
        self.assertGreaterEqual(v.detail["candidates_refused"], 1)

    def test_it_is_not_a_stub_and_reads_what_it_declares(self):
        spec = adjudicate.REGISTRY[Q.DIRECTION]
        self.assertFalse(spec.stub)
        self.assertEqual(spec.subjects_from, Q.DIRECTION_WORD)
        self.assertIn(Q.DIRECTION_WORD, spec.wants)


# ─────────────────────────────────────────────────────────────────────────────
# 4. The file, and the counter
# ─────────────────────────────────────────────────────────────────────────────


def _page_with(words, *, outcome="decided", reason="in_lexicon", cells=1):
    """A staged record holding one staff, `cells` bars, and a direction verdict
    on bar 0 -- in the shape `adjudicate_direction` files it."""
    from tools.omr.tests.test_staged_export import _one_staff_page, QUARTER
    page = _one_staff_page(notes=[("C4", QUARTER)])
    page["record"]["verdicts"].append({
        "id": "vrd:dir1", "subject": "cell/0/0/0/0", "quantity": Q.DIRECTION,
        "outcome": outcome, "value": list(words) if words is not None else None,
        "reason": reason, "basis": [], "detail": {
            "words": [{"text": w, "x_page": 100.0 + 10 * i,
                       "category": "expression", "placement": "below",
                       "reader": "surya"}
                      for i, w in enumerate(words or ())]},
        "confidence": None, "supersedes": None,
    })
    return page


class TestItReachesTheFile(unittest.TestCase):
    def test_a_decided_word_is_written_as_words(self):
        xml, report = SX.to_musicxml(_page_with(["legato"]))
        self.assertIn("<words>legato</words>", xml)
        self.assertEqual(report["written"]["direction_words"], 1)

    def test_the_counter_is_PER_KIND_and_a_word_is_not_billed_to_dynamics(self):
        """⚠️⚠️ IT WAS ONE COUNTER. `counters["dynamics"] += len(directions)`
        counted every entry of the list, so the day words arrived a `<words>`
        would have been billed to the `dynamic` family -- `dynamic` reading as
        emitting more than it does, and `direction` reading
        `decided_but_unwritten` with its elements in the file. `FAMILIES`'s own
        rule is that only the counter says what reached the FILE; a counter
        that cannot tell two families apart says it of neither."""
        _xml, report = SX.to_musicxml(_page_with(["legato", "dolce"]))
        self.assertEqual(report["written"]["direction_words"], 2)
        self.assertEqual(report["written"].get("dynamics", 0), 0)

    def test_an_ABSTAINING_cell_writes_nothing(self):
        xml, report = SX.to_musicxml(
            _page_with(None, outcome="abstained",
                       reason=ABSTAIN.READER_UNAVAILABLE))
        self.assertNotIn("<words>", xml)
        self.assertEqual(report["written"].get("direction_words", 0), 0)

    def test_a_no_words_DECISION_writes_nothing_either(self):
        """⚠️ AND THAT IS CORRECT: MusicXML has no way to say "a reader could
        not run over this bar", so the FILE is not asked to distinguish the
        two. The RECORD is, which is where the distinction belongs."""
        xml, _r = SX.to_musicxml(_page_with([], reason="no_words"))
        self.assertNotIn("<words>", xml)

    def test_the_family_reports_emitted_rather_than_decided_but_unwritten(self):
        page = _page_with(["legato"])
        _xml, report = SX.to_musicxml(page)
        row = {r["family"]: r
               for r in SX.coverage(page, report["written"])["families"]
               }["direction"]
        self.assertEqual(row["status"], "emitted")
        self.assertEqual(row["written"], 1)


class TestTheBalanceIsAnEquality(unittest.TestCase):
    """⚠️⚠️ THE WEDGE CONTROL SHIPPED AS A `<=` AND REPORTED `balanced: True`
    WHILE TEN DECIDED HAIRPINS WERE COUNTED BY NOBODY. The session before that
    one had warned about `<=` in writing. So this is `==`, and the residue has
    a name."""

    def test_it_balances_when_every_word_is_written(self):
        _xml, report = SX.to_musicxml(_page_with(["legato", "dolce"]))
        b = report["direction_balance"]
        self.assertTrue(b["balanced"])
        self.assertEqual((b["words_decided"], b["placed"], b["written"]),
                         (2, 2, 2))
        self.assertEqual(report["direction_words_not_written_total"], 0)

    def test_a_verdict_on_a_cell_NO_PART_CARRIES_is_named_not_swallowed(self):
        """⚠️ The only way a decided word can go unwritten is that its cell is
        not in the export -- a PART-JOIN fact. Naming it is what stops it
        being read as a direction fact."""
        page = _page_with(["legato"])
        page["record"]["verdicts"].append({
            "id": "vrd:dir2", "subject": "cell/0/0/0/99",
            "quantity": Q.DIRECTION, "outcome": "decided",
            "value": ["dolce"], "reason": "in_lexicon", "basis": [],
            "detail": {"words": [{"text": "dolce", "x_page": 1.0}]},
            "confidence": None, "supersedes": None,
        })
        _xml, report = SX.to_musicxml(page)
        b = report["direction_balance"]
        self.assertEqual(b["words_decided"], 2)
        self.assertEqual(b["written"], 1)
        self.assertEqual(
            report["direction_words_not_written"]["cell_not_in_any_part"], 1)
        self.assertTrue(b["balanced"],
                        "the residue is named, so the partition still holds")

    def test_the_control_is_written_as_an_equality(self):
        """⚠️ ASSERTED ON THE SOURCE, because the code path cannot today
        produce an unbalanced input (`written + not_written` is `decided` by
        construction) -- a KNOWN EQUIVALENT MUTANT, named rather than chased.
        What a source-level assertion CAN do is stop the spelling regressing to
        the `<=` that hid ten hairpins."""
        import inspect
        src = inspect.getsource(SX.to_musicxml)
        block = src[src.index('report["direction_balance"]'):]
        block = block[:block.index("fermata_marks")]
        self.assertIn("== d_decided", block)
        self.assertNotIn("<= d_decided", block)


if __name__ == "__main__":
    unittest.main()
