"""The part join: a slot that is the ordinal may not be used as a slot, and
the reader that would supply a real one must actually be called.

⚠️ TWO DEFECTS, ONE SYMPTOM. On Litolff Beethoven 5 mvt 1 pdf p.1-4 the
exported file held parts of 111, 93 and 16 measures -- `<measure number="82">`
naming a different instant in different parts -- and 12 of 75 staff-systems
were joined to the wrong instrument. Both trace to the SAME chain:

    pipeline.run_staged drops `pdf_path`
      -> gather_margin_labels abstains `not_implemented` on 75 of 75
      -> adjudicate_instrument abstains `no_evidence` on 75 of 75
      -> adjudicate_slot_index falls back to the staff's own ordinal
      -> adjudicate_part_partition calls that table a "slot" join
      -> the exporter grafts across systems of 12, 11 and 8 staves.

These tests pin the two links this repo can fix without a new reader: the
forward, and the refusal.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, pipeline
from tools.omr.staged import record as R
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged.adjudicators.identity import _slots_are_ordinals
from tools.omr.staged.record import Log, Outcome, Q, READERS


# ─────────────────────────────────────────────────────────────────────────────
# The forward: a reader that is never called reports "not implemented"
# ─────────────────────────────────────────────────────────────────────────────


class _SpyGather:
    """Stands in for `gather.gather`, recording what it was handed."""

    def __init__(self):
        self.kwargs = None

    def __call__(self, prepared, **kwargs):
        self.kwargs = kwargs
        log = Log()
        log.freeze()
        return log


class TestTheMarginLabelReaderIsReachable(unittest.TestCase):
    """⚠️ `gather` has taken a `pdf_path` since it was written and the ONLY
    call site that ever supplied it was its own internal forward to
    `gather_margin_labels`. `run_staged` took the path, rasterised with it and
    dropped it -- so every staged run this repo has ever made filed
    `not_implemented: "no pdf_path supplied to gather()"` on every staff.

    A parameter with no producer is indistinguishable from a page that prints
    no labels, which is why this is asserted rather than read off a run."""

    def _run(self, **kw):
        spy = _SpyGather()
        real_gather = pipeline.gather.gather
        real_prepare = pipeline.prepare_pages
        pipeline.gather.gather = spy
        pipeline.prepare_pages = lambda p, pages, dpi=600: []
        try:
            pipeline.run_staged("/some/score.pdf", [0], **kw)
        finally:
            pipeline.gather.gather = real_gather
            pipeline.prepare_pages = real_prepare
        return spy.kwargs

    def test_run_staged_forwards_the_pdf_path_to_gather(self):
        kwargs = self._run()
        self.assertEqual(kwargs["pdf_path"], "/some/score.pdf")

    def test_the_ocr_rungs_are_forwarded_and_default_off(self):
        """⚠️ OFF by default and the default is the claim: the free text-layer
        rung costs nothing and reads nothing on a 19th-century scan (measured
        0 of 75), while the OCR rungs read 50 of 75 and cost wall clock
        CLAUDE.md measures at ~75% of a whole-work run. Defaulting them on
        would treble a gather without anyone deciding to."""
        self.assertIs(self._run()["surya_fallback"], False)
        self.assertIs(self._run()["ocr_fallback"], False)
        on = self._run(surya_fallback=True, ocr_fallback=True)
        self.assertIs(on["surya_fallback"], True)
        self.assertIs(on["ocr_fallback"], True)

    def test_the_cli_exposes_the_rungs(self):
        """A forward nothing can switch on is still unreachable from the
        command line, which is where every artefact in this repo is made."""
        import contextlib
        import io

        from tools.omr.staged.__main__ import main

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit):
                main(["--help"])
        text = buf.getvalue()
        self.assertIn("--surya", text)
        self.assertIn("--ocr", text)


# ─────────────────────────────────────────────────────────────────────────────
# The refusal: a contiguous slot table carries nothing the ordinal does not
# ─────────────────────────────────────────────────────────────────────────────


def _two_systems(sizes, page=0):
    """A document whose systems print `sizes` staves each.

    Nothing supplies a margin label, so `adjudicate_slot_index` falls to the
    staff's own ordinal -- which is exactly what it does on every real page
    today, and is the input under test.
    """
    log = Log()
    for s, n in enumerate(sizes):
        log.observe(R.system(page, s), Q.SYSTEM_STAFF_COUNT, n,
                    reader=READERS.GEOMETRY, frame="system")
        for i in range(n):
            log.observe(R.staff(page, s, i), Q.STAFF_ORDINAL, i,
                        reader=READERS.GEOMETRY, frame="system")
    return log


class _V:
    """The two fields `_slots_are_ordinals` reads, and nothing else."""

    def __init__(self, page, system, value):
        self.subject = R.staff(page, system, 0)
        self.value = value


class TestASlotTableThatIsTheOrdinal(unittest.TestCase):
    def test_contiguous_on_every_system_is_the_ordinal(self):
        v = [_V(0, 0, i) for i in range(11)] + [_V(0, 1, i) for i in range(8)]
        self.assertTrue(_slots_are_ordinals(v))

    def test_a_gap_anywhere_is_a_real_slot_table(self):
        """⚠️ THE GAP IS THE WHOLE POINT. `slots.align` matches a system
        against a reference lineup with deletions allowed, so a tacet staff
        leaves a MISSING slot and the staves below it keep their identity.
        That is the information a slot has and an ordinal does not."""
        # system 1 suppresses slots 1, 5 and 6 -- the Litolff p.3 shape
        v = ([_V(0, 0, i) for i in range(11)]
             + [_V(0, 1, i) for i in (0, 2, 3, 4, 7, 8, 9, 10)])
        self.assertFalse(_slots_are_ordinals(v))

    def test_a_repeated_slot_is_not_the_ordinal_either(self):
        v = [_V(0, 0, i) for i in range(3)] + [_V(0, 1, 0), _V(0, 1, 0)]
        self.assertFalse(_slots_are_ordinals(v))

    def test_an_empty_table_is_not_an_ordinal_table(self):
        """Nothing to join on is a different answer from "the join is the
        ordinal", and the caller's two branches must not collapse."""
        self.assertFalse(_slots_are_ordinals([]))


class TestThePartJoinRefusesAGraft(unittest.TestCase):
    """⚠️ THE POSITIVE CONTROL IS IN THE SAME CLASS, deliberately: a battery
    of refusal tests can pass by refusing everything."""

    def test_disagreeing_systems_with_ordinal_slots_refuse(self):
        log = _two_systems([11, 8])
        adjudicate.run(log)
        v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "deduced_anchor")
        self.assertEqual(v.value["join"], "ordinal")
        self.assertEqual(v.value["reason"], "slots_are_ordinals")

    def test_agreeing_systems_still_join_by_ordinal(self):
        """The no-op branch, unchanged. Measured identical to truth and to the
        slot join on 3 documents, so it must not move."""
        log = _two_systems([11, 11])
        adjudicate.run(log)
        v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
        self.assertEqual(v.reason, "ordinal")
        self.assertEqual(v.value["join"], "ordinal")

    def test_the_slots_really_were_the_ordinals(self):
        """⚠️ The premise, asserted rather than assumed. If
        `adjudicate_slot_index` ever starts producing a gapped table this test
        goes red and the refusal above stops being the right one -- which is
        the signal the next repair needs."""
        log = _two_systems([11, 8])
        adjudicate.run(log)
        for s, n in ((0, 11), (1, 8)):
            got = [log.verdict(Q.SLOT_INDEX, R.staff(0, s, i)).value
                   for i in range(n)]
            self.assertEqual(got, list(range(n)))


def _vrd(i, subject, quantity, value, outcome="decided", reason="x"):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _record_with_join(join_value, join_reason, slots):
    """Two systems printing 3 and 2 staves -- the shape that refuses.

    `slots` maps a staff subject to its `Q.SLOT_INDEX`, so one fixture can
    express both a contiguous (ordinal) table and a gapped (real) one.
    """
    verdicts = [_vrd(1, "document", Q.PART_PARTITION, join_value,
                     reason=join_reason)]
    n = 10
    for s, count in enumerate((3, 2)):
        for i in range(count):
            key = f"staff/0/{s}/{i}"
            verdicts.append(_vrd(n, key, Q.MEASURE_PARTITION, 1))
            n += 1
            if key in slots:
                verdicts.append(_vrd(n, key, Q.SLOT_INDEX, slots[key]))
                n += 1
    return {"record": {"observations": [], "verdicts": verdicts,
                       "abstentions": [], "counts": {}}, "summary": {}}


class TestTheExporterTakesTheFragmentPath(unittest.TestCase):
    """⚠️ The refusal is only worth having if the exporter honours it. The
    fragment fallback is the LEGACY behaviour and is kept: it pairs with
    nothing in a reference and scores badly, and it is still right, because
    the alternative is grafting one instrument's music onto another."""

    def test_a_refused_join_exports_one_part_per_system_staff(self):
        from tools.omr.staged import export as SX

        ordinal_slots = {f"staff/0/0/{i}": i for i in range(3)}
        ordinal_slots.update({f"staff/0/1/{i}": i for i in range(2)})
        _xml, rep = SX.to_musicxml(_record_with_join(
            {"join": "ordinal", "reason": "slots_are_ordinals"},
            "deduced_anchor", ordinal_slots))
        self.assertEqual(rep["part_join"]["join_used"], "fragments")
        self.assertTrue(rep["part_join"]["fragmented"])
        self.assertEqual(rep["part_join"]["parts"], 5)

    def test_a_real_slot_table_still_joins(self):
        """THE POSITIVE CONTROL, at the exporter. A fixture that fragments
        under every input would pass the test above for free."""
        from tools.omr.staged import export as SX

        gapped = {f"staff/0/0/{i}": i for i in range(3)}
        gapped.update({"staff/0/1/0": 0, "staff/0/1/1": 2})   # slot 1 tacet
        _xml, rep = SX.to_musicxml(_record_with_join(
            {"join": "slot", "slots": [0, 1, 2]}, "slot", gapped))
        self.assertEqual(rep["part_join"]["join_used"], "slot")
        self.assertFalse(rep["part_join"]["fragmented"])
        self.assertEqual(rep["part_join"]["parts"], 3)


if __name__ == "__main__":
    unittest.main()
