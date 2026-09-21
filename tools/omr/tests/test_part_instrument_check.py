"""`part_partition`'s SECOND DECLARED CHECK — performed, and it records.

⚠️ THE DECLARATION CAME FIRST AND THE CODE NEVER FOLLOWED. `adjudicate_part_
partition` has declared *"each part carries ONE instrument across every system
it appears on"* in its `checked_by` since it was written, and its body read
`Q.INSTRUMENT` on NO path at all --
`benchmarks/omr-convention-coverage-2026-09/` found it by counting, along with
15 other declared-and-absent checks. It is the third documentation shape this
project has named: not a stale claim about the past, but a claim about the
code in front of you.

⚠️ WHAT THESE TESTS PIN IS A CHECK THAT RECORDS AND DOES NOT ACT. The wiring
plan's condition is that *a wiring pass may CONNECT a decision, it may not let
one GUESS*, so `test_the_check_changes_NOTHING_about_the_join` is the
load-bearing one here: every other test is about the check's own answer.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import record as R
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged.adjudicate import ORDER
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

_INSTR = {"Flute": {"name": "Flute", "family": "woodwind"},
          "Oboe": {"name": "Oboe", "family": "woodwind"},
          "Timpani": {"name": "Timpani", "family": "percussion"},
          "Viola": {"name": "Viola", "family": "string"}}


def _log(systems):
    """A document of `systems` = [(n_staves, ...), ...] with ordinals filed."""
    log = Log()
    for s, n in enumerate(systems):
        log.observe(R.system(0, s), Q.SYSTEM_STAFF_COUNT, n,
                    reader=READERS.GEOMETRY, frame="system")
        for i in range(n):
            log.observe(R.staff(0, s, i), Q.STAFF_ORDINAL, i,
                        reader=READERS.GEOMETRY, frame="system")
    log.freeze()
    return log


def _inject(log, subject, quantity, value, reason="injected"):
    log.record(Verdict(id=log._next_id("vrd"), subject=subject,
                       quantity=quantity, outcome=Outcome.DECIDED,
                       value=value, decider="injected", reason=reason))


def _name(log, page, system, staff, instrument):
    _inject(log, R.staff(page, system, staff), Q.INSTRUMENT,
            _INSTR[instrument], reason="label")


def _run(log, *, with_slots=False):
    order = ([Q.SYSTEM_STAFF_COUNT] + ([] if with_slots else [])
             + [Q.PART_PARTITION])
    adjudicate.run(log, order=tuple(order))
    return log.verdict(Q.PART_PARTITION, R.DOCUMENT)


def _check(v):
    return (v.detail or {}).get("instrument_consistency") or {}


class TestTheCheckIsPerformedAtAll(unittest.TestCase):

    def test_an_ordinal_join_carries_the_check(self):
        log = _log([2, 2])
        _name(log, 0, 0, 0, "Flute")
        _name(log, 0, 1, 0, "Flute")
        v = _run(log)
        self.assertEqual(v.value["join"], "ordinal")
        self.assertTrue(_check(v)["checked"])

    def test_the_slots_are_ordinals_branch_carries_it_too(self):
        """⚠️ Checked as an ORDINAL join, because that branch has just decided
        the slot table amounts to the ordinal. Asking it in slot terms would
        check a partition that does not ship."""
        log = _log([3, 2])
        for s, n in ((0, 3), (1, 2)):
            for i in range(n):
                _inject(log, R.staff(0, s, i), Q.SLOT_INDEX, i)
        _name(log, 0, 0, 0, "Flute")
        _name(log, 0, 1, 0, "Flute")
        v = _run(log)
        self.assertEqual(v.reason, "deduced_anchor")
        self.assertEqual(v.value["reason"], "slots_are_ordinals")
        self.assertEqual(_check(v)["join_checked"], "ordinal")

    def test_the_slots_unusable_branch_carries_it_too(self):
        log = _log([3, 2])
        _name(log, 0, 0, 0, "Flute")
        _name(log, 0, 1, 0, "Flute")
        v = _run(log)
        self.assertEqual(v.value["reason"], "slots_unusable")
        self.assertTrue(_check(v)["checked"])

    def test_a_real_slot_join_carries_it_and_keys_BY_SLOT(self):
        """⚠️⚠️ THE FRAME, AND IT IS THE WHOLE POINT OF THE SLOT JOIN. System 1
        suppresses slot 0, so its staff 0 IS slot 1. Keyed by ordinal the two
        Flute/Oboe staves would collide and read as a contested part; keyed by
        slot they are two parts that each agree with themselves.

        A check asked in the wrong join's terms measures a partition that does
        not ship, and would report the shipping one broken."""
        log = _log([2, 1])
        for i in range(2):
            _inject(log, R.staff(0, 0, i), Q.SLOT_INDEX, i)
        _inject(log, R.staff(0, 1, 0), Q.SLOT_INDEX, 1)   # the GAP
        _name(log, 0, 0, 0, "Flute")
        _name(log, 0, 0, 1, "Oboe")
        _name(log, 0, 1, 0, "Oboe")
        v = _run(log)
        self.assertEqual(v.value["join"], "slot")
        c = _check(v)
        self.assertEqual(c["join_checked"], "slot")
        self.assertEqual(c["parts_contested"], 0)
        self.assertEqual(c["parts_with_two_or_more_named_staves"], 1)


class TestWhatTheCheckSays(unittest.TestCase):

    def test_a_part_naming_two_instruments_is_CONTESTED(self):
        """The Phase 2 shape, in miniature: an interior staff is suppressed,
        everything below it shifts up, and the ordinal join files the Viola
        under the Timpani's part."""
        log = _log([2, 2])
        _name(log, 0, 0, 1, "Timpani")
        _name(log, 0, 1, 1, "Viola")
        v = _run(log)
        c = _check(v)
        self.assertEqual(c["parts_contested"], 1)
        self.assertEqual(c["contested"]["1"], ["Timpani", "Viola"])

    def test_agreement_is_reported_as_agreement(self):
        log = _log([2, 2])
        _name(log, 0, 0, 1, "Timpani")
        _name(log, 0, 1, 1, "Timpani")
        v = _run(log)
        c = _check(v)
        self.assertEqual(c["parts_contested"], 0)
        self.assertEqual(c["contested"], {})

    def test_a_part_named_on_ONE_system_is_reported_APART(self):
        """⚠️ It cannot disagree with itself, so counting it among the parts
        that agree would report reach the check does not have. 3 parts named,
        only 1 of them able to say anything."""
        log = _log([2, 2])
        _name(log, 0, 0, 0, "Flute")
        _name(log, 0, 1, 0, "Flute")
        _name(log, 0, 0, 1, "Timpani")          # system 1 staff 1 unnamed
        v = _run(log)
        c = _check(v)
        self.assertEqual(c["parts_named"], 2)
        self.assertEqual(c["parts_with_two_or_more_named_staves"], 1)

    def test_ABSENT_IS_NOT_CLEAN(self):
        """⚠️⚠️ THE ONE THAT MATTERS MOST. Before `run_staged` forwarded
        `pdf_path`, `adjudicate_instrument` abstained `no_evidence` on 75 of 75
        staves on EVERY staged run this repo had made. A check that read that
        silence as agreement would have reported the part join sound on exactly
        the documents where it was worst."""
        log = _log([2, 2])
        v = _run(log)
        c = _check(v)
        self.assertFalse(c["checked"])
        self.assertEqual(c["why_not"], "no_instrument_was_read")
        self.assertNotIn("parts_contested", c)

    def test_a_staff_with_no_slot_is_COUNTED_not_dropped(self):
        """Under a slot join a staff whose slot never decided belongs to no
        part. That is a hole in the check's reach, not a part that agrees with
        itself, and it is reported as one."""
        # a third staff on system 0 exists in GATHER and no slot ever names it
        log = _log([3, 1])
        for i in range(2):
            _inject(log, R.staff(0, 0, i), Q.SLOT_INDEX, i)
        _inject(log, R.staff(0, 1, 0), Q.SLOT_INDEX, 1)
        _name(log, 0, 0, 0, "Flute")
        _name(log, 0, 0, 1, "Oboe")
        _name(log, 0, 1, 0, "Oboe")
        _name(log, 0, 0, 2, "Viola")
        v = _run(log)
        c = _check(v)
        self.assertEqual(c["staves_unkeyed"], 1)


class TestTheDisciplines(unittest.TestCase):

    def test_the_check_changes_NOTHING_about_the_join(self):
        """⚠️⚠️ A WIRING PASS MAY CONNECT A DECISION, IT MAY NOT LET ONE GUESS.

        Two documents identical but for the instruments — one where every part
        agrees and one where a part is contested — must produce the SAME join,
        the same reason and the same value. Every way of acting on this result
        is a guess today: refusing the join over a contradiction would hand the
        document to the fragment fallback on one misread margin label, and
        repairing it would need to know WHICH staff is misfiled, which this
        cannot say."""
        clean = _log([2, 2])
        _name(clean, 0, 0, 1, "Timpani")
        _name(clean, 0, 1, 1, "Timpani")
        a = _run(clean)

        contested = _log([2, 2])
        _name(contested, 0, 0, 1, "Timpani")
        _name(contested, 0, 1, 1, "Viola")
        b = _run(contested)

        self.assertEqual(_check(b)["parts_contested"], 1)   # positive control
        self.assertIs(a.outcome, b.outcome)
        self.assertEqual(a.reason, b.reason)
        self.assertEqual(a.value, b.value)

    def test_the_INSTRUMENT_is_decided_BEFORE_the_partition(self):
        """⚠️ THE `wedge_anchor` LESSON, ASSERTED RATHER THAN HOPED FOR. That
        decision was placed at its natural home in `ORDER`, ran before
        `Q.VOICES` and read `None` every time — and NO behavioural test could
        have found it, because "one voice" and "voices unknown" give the same
        answer on every fixture in the suite. Here the failure would be
        quieter still: the check would report `checked: False` on every real
        page and read as *this document prints no labels*."""
        self.assertLess(ORDER.index(Q.INSTRUMENT),
                        ORDER.index(Q.PART_PARTITION))

    def test_the_read_is_SCOPED_or_it_can_never_answer(self):
        """⚠️ `Q.INSTRUMENT` is filed on STAVES and this decision runs at
        DOCUMENT, so a bare `ev.verdicts(Q.INSTRUMENT)` returns nothing and the
        check reports a clean zero on every page. `wiring.py`'s SCOPE-LATENT
        entry for this exact declaration said so in terms before the check was
        written. Asserted at source level because a bare read FAILS SILENTLY —
        it produces the same `checked: False` an honest empty page produces."""
        import inspect
        from tools.omr.staged.adjudicators import identity
        src = inspect.getsource(identity._instrument_consistency)
        self.assertIn("Q.INSTRUMENT", src)
        self.assertIn("Scope.SELF_AND_DESCENDANTS", src)

    def test_the_declared_check_is_still_declared(self):
        """The decorator's claim and the body must not drift apart again — in
        either direction. A check performed under a declaration that has been
        deleted is as hard to find as a declaration with no check."""
        from tools.omr.staged.adjudicate import REGISTRY, _ensure_decisions
        _ensure_decisions()
        spec = REGISTRY[Q.PART_PARTITION]
        self.assertIn(
            "each part carries ONE instrument across every system it appears on",
            spec.checked_by)
        self.assertIn(Q.INSTRUMENT, spec.wants)


if __name__ == "__main__":
    unittest.main()


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️⚠️ THE THREE TESTS BELOW EXIST BECAUSE A MUTATION SURVIVED, and the
# mutations only became visible once the battery's judge stopped carrying
# pytest's own elapsed time. With " in 0.57s" left in the summary line, two
# runs of an UNMUTATED tree differed and every arm scored RED for free: the
# first battery reported 13 of 13 red and was measuring nothing. Stripping the
# duration turned it into 10 red and THREE SURVIVORS, all three real.
# ─────────────────────────────────────────────────────────────────────────────


class TestTheSurvivors(unittest.TestCase):

    def test_a_contested_SLOT_join_is_still_not_acted_on(self):
        """⚠️ SURVIVOR 1, and the load-bearing one.

        `test_the_check_changes_NOTHING_about_the_join` builds two systems of
        equal staff count, so it takes the ORDINAL branch and never reaches
        the slot branch at all — a mutation that abstains on a contested SLOT
        join walked straight past it. *A test named for a hazard it does not
        reach* is this project's own recorded shape, and here the name was
        exactly right while the fixture was two staves short of the branch."""
        def build(second_name):
            log = _log([2, 1])
            for i in range(2):
                _inject(log, R.staff(0, 0, i), Q.SLOT_INDEX, i)
            _inject(log, R.staff(0, 1, 0), Q.SLOT_INDEX, 1)   # the GAP
            _name(log, 0, 0, 0, "Flute")
            _name(log, 0, 0, 1, "Oboe")
            _name(log, 0, 1, 0, second_name)
            return _run(log)

        clean = build("Oboe")
        contested = build("Viola")
        self.assertEqual(clean.value["join"], "slot")          # the branch
        self.assertEqual(_check(contested)["parts_contested"], 1)  # positive
        self.assertIs(clean.outcome, contested.outcome)
        self.assertEqual(clean.reason, contested.reason)
        self.assertEqual(clean.value, contested.value)


class TestTheArmsOwnControls(unittest.TestCase):
    """⚠️ SURVIVORS 2 AND 3: the arm's controls were guarded by nothing.

    A benchmark arm is a script, so no suite imports it and a battery arm
    against it is free unless something exercises it. Both survivors were of
    that shape — the arm could stop asserting the join is unmoved, or stop
    declaring itself DEAD at zero reach, and the whole suite stayed green.

    ⚠️ These drive the arm's `main()` over a synthetic record rather than a
    shared one: the point is the CONTROL's behaviour, not a measurement, and
    a real record costs many minutes to re-adjudicate."""

    @staticmethod
    def _arm():
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        path = (root / "benchmarks" / "omr-part-instrument-check-2026-09"
                / "check_arm.py")
        spec = importlib.util.spec_from_file_location("_check_arm", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _record(tmp, part_partition_value):
        """A two-system document with no instrument read anywhere."""
        import json
        obs, n = [], 0
        for s, count in ((0, 2), (1, 2)):
            obs.append({"id": f"obs:{n:06d}", "subject": f"system/0/{s}",
                        "quantity": Q.SYSTEM_STAFF_COUNT, "value": count,
                        "reader": READERS.GEOMETRY, "frame": "system"})
            n += 1
            for i in range(count):
                obs.append({"id": f"obs:{n:06d}", "subject": f"staff/0/{s}/{i}",
                            "quantity": Q.STAFF_ORDINAL, "value": i,
                            "reader": READERS.GEOMETRY, "frame": "system"})
                n += 1
        rec = {"record": {"observations": obs, "abstentions": [], "verdicts": [
            {"id": "vrd:000001", "subject": "document", "quantity":
             Q.PART_PARTITION, "outcome": "decided",
             "value": part_partition_value, "decider": "t", "reason": "ordinal"}
        ]}}
        p = tmp / "rec.json"
        p.write_text(json.dumps(rec))
        return str(p)

    def _run_arm(self, argv):
        import io, contextlib, sys as _sys
        mod = self._arm()
        old = _sys.argv
        _sys.argv = ["check_arm.py"] + argv
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = mod.main()
        finally:
            _sys.argv = old
        return rc, buf.getvalue()

    def test_the_control_FAILS_when_the_join_moved(self):
        """⚠️ The control must be able to fail, or it is not a control. The
        record claims a join the rebuild will not produce."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path = self._record(Path(d), {"join": "slot", "slots": [7]})
            rc, out = self._run_arm([path, "--control"])
        self.assertEqual(rc, 1)
        self.assertIn("MOVED THE JOIN", out)

    def test_the_control_PASSES_on_a_faithful_record(self):
        """The positive control for the test above: the same arm, on a record
        whose join the rebuild reproduces, must exit 0 — otherwise the failure
        test passes for free."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path = self._record(Path(d),
                                {"join": "ordinal", "staves_per_system": 2})
            rc, out = self._run_arm([path, "--control"])
        self.assertEqual(rc, 0, out)
        self.assertIn("UNMOVED", out)
        self.assertIn("DID run", out)

    def test_the_arm_declares_itself_DEAD_at_zero_reach(self):
        """⚠️ REACH BEFORE ACCURACY. This record names no instrument on any
        staff, so the check cannot speak. An arm that printed a table here
        would report `contested: 0` as a result, which is the silence-read-as-
        agreement failure the check itself is built to refuse — reappearing one
        layer out, in the instrument that measures it."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path = self._record(Path(d),
                                {"join": "ordinal", "staves_per_system": 2})
            rc, out = self._run_arm([path])
        self.assertEqual(rc, 2)
        self.assertIn("DEAD", out)
        self.assertIn("no_instrument_was_read", out)
