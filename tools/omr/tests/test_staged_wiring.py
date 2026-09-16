"""`staged.wiring` — the derived check for *the value existed and nothing read
it*, and the roster repair it found.

⚠️ TWO KINDS OF TEST LIVE HERE AND THEY ARE NOT INTERCHANGEABLE.

The first kind exercises the INSTRUMENT on synthetic code whose fault is known
by construction, so a question that stops working goes red. The second kind
asserts the ANSWER COMES OUT of `adjudicate_instrument` — and it is the only
kind that has ever caught a FRAME fault in this repo. CLAUDE.md records four
instances: *"Neither `inventory --check` nor `gather_coverage` can catch that
— the `wants` entry IS read and the quantity IS gathered — and only a test
asserting a word comes out did."* A test that asserted the roster row is on
the log would pass with the decision reading it at the wrong scope.
"""

from __future__ import annotations

import ast
import unittest

from tools.omr.staged import adjudicate, gather, wiring
from tools.omr.staged import record as R
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged.record import (ABSTAIN, Kind, Log, Outcome, Q, READERS,
                                     Scope)
from tools.omr.work_roster import WorkRoster


# ─────────────────────────────────────────────────────────────────────────────
# The instrument
# ─────────────────────────────────────────────────────────────────────────────

class TestTheToolIsAliveAtAll(unittest.TestCase):
    """⚠️ THE POSITIVE CONTROLS, ASSERTED RATHER THAN PRINTED.

    A derived check that matches nothing reports a clean tree, and this repo
    has shipped exactly that: the flag-direction guard's first version
    descended THROUGH `environ.get` onto `os.environ`, matched NOTHING, and
    both its real assertions passed vacuously. `health.py` reported "EMPTY
    CELLS: none" by accident. These assert each question REACHED its subject.
    """

    @classmethod
    def setUpClass(cls):
        cls.rep = wiring.report()

    def test_every_control_is_non_zero(self):
        zero = [k for k, v in self.rep["controls"].items() if not v]
        self.assertEqual(zero, [], "a control at zero means the question did "
                                   "not run; a clean result means NOTHING")

    def test_check_refuses_before_it_looks_at_findings_when_a_control_dies(self):
        """⚠️ THE ORDER IS THE CLAIM. `--check` must fail on a DEAD question
        before it fails on a finding, or a tool that stopped working exits 0
        and reads as a clean tree."""
        rep = dict(self.rep)
        rep["controls"] = dict(rep["controls"], frame_reads_that_line_up=0)
        rep["unaccounted"], rep["stale_gaps"] = [], []
        import unittest.mock as mock
        with mock.patch.object(wiring, "report", return_value=rep):
            self.assertEqual(wiring.main(["--check"]), 2)


# ⚠⚠ THE PRODUCER TESTS LEFT THIS FILE 2026-09-15 WITH THE QUESTION THEY
# COVERED. *A parameter threaded with no supplier* is
# `tools/omr/no_producer.py`'s question — a sibling session landed it on main
# the same day this module was written, derived from the AST over the whole of
# `tools/`, finding `pdf_path` and `roster` with no hint. This module had a
# duplicate and it is gone. `tools/omr/tests/test_no_producer.py` is where
# that question is tested; what survives here is the roster REPAIR, which
# closes one of that tool's own open findings.


class TestTheFrameQuestion(unittest.TestCase):
    """A declared input read at a Kind where nothing files it."""

    def test_a_downward_read_with_its_own_reach_is_NOT_a_fault(self):
        """⚠️ COLLAPSING THIS MADE THE FIRST DRAFT REPORT 28 FALSE TRAPS. A
        SYSTEM-scoped decision reading `Q.EVENT`, filed at CELL, reads
        DOWNWARD through an explicit `subject=` — correct and common."""
        rep = wiring.report()
        self.assertGreater(rep["controls"]["frame_reads_with_their_own_reach"],
                           0)
        pairs = {(b["decision"], b["quantity"])
                 for b in rep["frames"]["latent"] + rep["frames"]["broken"]}
        self.assertNotIn(("adjudicate_meter", "EVENT"), pairs)

    def test_the_roster_trap_is_CLOSED(self):
        rep = wiring.report()
        pairs = {(b["decision"], b["quantity"])
                 for b in rep["frames"]["latent"] + rep["frames"]["broken"]}
        self.assertNotIn(("adjudicate_instrument", "ROSTER_ENTRY"), pairs)

    def test_it_still_reports_the_traps_that_remain(self):
        """A check with nothing left to say is a check nobody re-runs. These
        are real and each is its own job."""
        rep = wiring.report()
        pairs = {(b["decision"], b["quantity"])
                 for b in rep["frames"]["latent"]}
        self.assertIn(("adjudicate_clef", "NOTEHEAD_STAFF_POSITION"), pairs)

    def test_an_unresolvable_subject_is_NAMED_never_defaulted(self):
        """⚠️ A fallback must never convert "cannot tell" into a definite
        answer. Two guards in this repo reintroduced the exact failure they
        guarded against in their own fallback branches."""
        self.assertIsNone(wiring._kind_of_expr(
            ast.parse("Subject.from_key(k)", mode="eval").body, {}))
        # ⚠️⚠️ THE BARE NAME BRANCH, AND THE MUTATION BATTERY IS WHAT FOUND
        # IT MISSING. This test was NAMED for the hazard and reached only the
        # Call branch: defaulting an unbound local to `'staff'` left it GREEN.
        # *A test named for a hazard it does not reach is the better
        # CAMOUFLAGE* — the name is what a reviewer trusts and the only part
        # they cannot check by reading. Only a mutation says otherwise.
        self.assertIsNone(wiring._kind_of_expr(
            ast.parse("sub", mode="eval").body, {}))
        self.assertEqual("cell", wiring._kind_of_expr(
            ast.parse("sub", mode="eval").body, {"sub": "cell"}))
        # and the SHAPE that names an unbound local must still be reported
        shapes = {u["shape"] for u in wiring.report()["frames"]["unresolved"]}
        self.assertTrue(any(sh.startswith("local ") for sh in shapes),
                        "a defaulted local would silently leave this set")
        rep = wiring.report()
        for u in rep["frames"]["unresolved"]:
            self.assertTrue(u["shape"],
                            "an unresolved site must say WHY, or it cannot go "
                            "on a gap list with a reason")

    def test_the_gather_walk_reaches_a_FIXPOINT_over_its_own_parameters(self):
        """`_gather_keysig_markers(log, sub, ...)` takes its subject as a
        PARAMETER, so a walker that follows only local assignments cannot say
        what Kind it files at — the callers know. Five sites left
        `unresolved` when this round was added.

        ⚠️ `GLYPH_LADDER` is deliberately NOT the case asserted here: its
        caller passes a `g` that is itself unresolved (unpacked from a list),
        so the fixpoint honestly cannot reach it and it stays named in
        `unresolved`. Asserting on it would be asserting the tool does
        something it does not."""
        walker = wiring._walk_gather()
        self.assertIn("staff", walker.filed.get("KEYSIG_MARKER", set()))
        self.assertNotIn("GLYPH_LADDER", walker.filed)


class TestTheDetailQuestion(unittest.TestCase):
    def test_the_row_kwarg_list_is_DERIVED_from_the_signature(self):
        """⚠️ A HAND LIST HERE WOULD ROT SILENTLY the day a parameter is
        added — a new structural parameter would start being reported as an
        unread detail key. `ARITY_FIELDS` is this repo's worked example of
        answering a hand list with a hand list."""
        kw = wiring._row_kwargs()
        self.assertIn("reader", kw)
        self.assertIn("frame", kw)
        self.assertNotIn("self", kw)

    def test_it_finds_keys_written_and_named_nowhere_else(self):
        rep = wiring.details()
        keys = {d["key"] for d in rep["unread"]}
        self.assertIn("Q.MARGIN_LABEL.reader_confidence", keys)
        self.assertGreater(rep["read"], 0, "positive control: most keys ARE "
                                           "named somewhere")


class TestTheRunCorroboration(unittest.TestCase):
    """`--run` resolves the 11 sites the static walk cannot.

    ⚠️⚠️ THIS TEST EXISTS BECAUSE THE FIRST DRAFT OF `with_run` READ
    `data["log"]` AND THE REAL RECORD WRITES `data["record"]` —
    `pipeline.run_staged` does `result["record"] = log.to_json()`. A reader of
    `"log"` finds NOTHING on every real record and reports `agree: 0`, which
    reads as *"the static table disagrees with every run"* rather than as
    *"this consumer is looking in the wrong place"*. The bug class this module
    exists to catch, committed inside it, in the path its own gap list cites
    as the answer.

    ⚠️ **THE FIXTURE IS BUILT BY THE REAL PRODUCER**, never typed. *A fixture
    that does not match GATHER tests the test* — this repo's own recorded
    lesson, which cost `Q.METER_GLYPH` a rule that read no boxes on any real
    page while five unit tests stayed green."""

    def _record(self):
        import json
        from tools.omr.staged import pipeline
        log = Log()
        gather.gather_external(log, None, roster=_ROSTER)
        sub = R.staff(0, 0, 0)
        log.observe(sub, Q.MARGIN_LABEL, "Flauti", reader=READERS.TEXT_LAYER,
                    frame="system_margin")
        # the shape the CLI writes, from the PRODUCER's own key
        return json.loads(json.dumps({"record": log.to_json()}, default=str))

    def test_it_reads_the_rows_a_real_record_carries(self):
        import json, tempfile, os
        rep = wiring.report()
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump(self._record(), f)
            path = f.name
        try:
            out = wiring.with_run(rep, path)
        finally:
            os.unlink(path)
        self.assertGreater(out["run"]["agree"]
                           + len(out["run"]["disagree"]), 0,
                           "zero rows seen means the consumer is looking in "
                           "the wrong place, not that the record is empty")
        # the roster row is on the DOCUMENT in the record, as the static
        # table says — the corroboration the flag is for
        static = rep["frames"]["filed"].get("ROSTER_ENTRY")
        self.assertEqual(static, ["document"])

    def test_a_record_with_no_rows_key_RAISES_rather_than_reporting_zero(self):
        """⚠️ A fallback must never convert "cannot tell" into a definite
        answer. Silently reporting `agree: 0` is that conversion."""
        import json, tempfile, os
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump({"log": {"observations": []}}, f)
            path = f.name
        try:
            with self.assertRaises(KeyError):
                wiring.with_run(wiring.report(), path)
        finally:
            os.unlink(path)


class TestTheRoundTripQuestion(unittest.TestCase):
    """A field declared on a serialisable class and dropped by its own
    `to_json` — the `works.json` `lines` fault, one layer in."""

    def test_it_finds_the_live_instance_WITHOUT_being_told(self):
        """⚠️ `Verdict.single_pass_revision` is declared, READ by the fixpoint
        guard, and absent from `Verdict.to_json` — so a replayed record comes
        back `False` and the guard's one sanctioned exemption is silently not
        there. Found independently by a sibling agent; this asserts the check
        reproduces it FROM THE TREE, with no hand-listing."""
        rep = wiring.roundtrip()
        hit = [r for r in rep["dropped"]
               if (r["class"], r["field"]) == ("Verdict",
                                               "single_pass_revision")]
        self.assertEqual(len(hit), 1)
        self.assertTrue(hit[0]["read"],
                        "a dropped field a real consumer READS is a different "
                        "fact from dead weight, and they are reported apart")

    def test_a_RENAME_is_not_a_DROP(self):
        """⚠️⚠️ THE FIRST CUT COMPARED KEY NAMES AND REPORTED A RENAME AS A
        DROP. `Witness` emits `self.row_id` under the key `"row"` — the field
        survives the round trip perfectly. A check that cannot tell those
        apart has one false positive per renamed key and trains the next
        reader to skim the list."""
        rep = wiring.roundtrip()
        pairs = {(r["class"], r["field"]) for r in rep["dropped"]}
        self.assertNotIn(("Witness", "row_id"), pairs)

    def test_the_question_reached_its_subject(self):
        rep = wiring.roundtrip()
        self.assertGreater(rep["classes_with_to_json"], 1)
        self.assertGreater(rep["fields_emitted"], 10)

    def test_it_is_REPORTED_and_NOT_repaired(self):
        """⚠️ DELIBERATE. Adding a key to `Verdict.to_json` changes EVERY
        record this repo writes, so every byte-identity control over a record
        would report a difference that is not the change under test. Pricing
        that is Sean's call. This test exists so a later session cannot
        quietly repair it and leave the reasoning behind."""
        from tools.omr.staged.record import Verdict
        self.assertIn("single_pass_revision",
                      {f for f in Verdict.__dataclass_fields__})
        # ⚠️ AND IT IS STILL DROPPED — asserted against the CLASS's own
        # `to_json` output rather than against the tool, so this goes red the
        # moment somebody repairs it without pricing it.
        import tools.omr.staged.record as _R
        v = _R.Verdict(id="v", subject=_R.DOCUMENT, quantity="q",
                       outcome=_R.Outcome.DECIDED, value=1, decider="d",
                       reason="r")
        self.assertNotIn("single_pass_revision", v.to_json())
        key = "ROUNDTRIP Verdict.single_pass_revision"
        self.assertIn(key, wiring.KNOWN_GAPS)
        self.assertIn("price", wiring.KNOWN_GAPS[key].lower())


class TestTheGapListIsAnInventoryNotASuppressionList(unittest.TestCase):
    """⚠️ Same contract as `export_coverage.KNOWN_GAPS` and
    `inventory.KNOWN_GAPS`: a CLOSED gap must LEAVE, or the list stops
    describing the pipeline and starts describing its history."""

    def test_no_entry_is_stale(self):
        rep = wiring.report()
        self.assertEqual(rep["stale_gaps"], [],
                         "entries nothing reports any more — delete them")

    def test_check_is_green_on_this_tree(self):
        self.assertEqual(wiring.main(["--check"]), 0)

    def test_every_gap_carries_a_REASON(self):
        """⚠️ A CROSS-REFERENCE MUST NAME ITS REFERENT. "as the row above" is
        a POSITIONAL reference into a dict, and it stops being true the first
        time an entry is inserted — the same shape as the anchored markdown
        insertion that orphaned a sentence in CLAUDE.md and cost two sessions
        a false `git blame` diagnosis."""
        for key, why in wiring.KNOWN_GAPS.items():
            if why.startswith("as `"):
                self.assertIn("`", why[4:], f"{key}: unnamed cross-reference")
                continue
            self.assertGreater(len(why), 40,
                               f"{key} has no reason worth the name")


# ─────────────────────────────────────────────────────────────────────────────
# The repair — and these are the tests that could have caught it
# ─────────────────────────────────────────────────────────────────────────────

_ROSTER = WorkRoster(
    work_id="beethoven--symphony-5-op67",
    instruments=frozenset({"Flute", "Oboe", "Clarinet", "Bassoon", "Horn",
                           "Trumpet", "Timpani", "Trombone", "Violin",
                           "Viola", "Cello", "Contrabass"}),
    families=frozenset({"woodwind", "brass", "percussion", "string"}),
    complete=True)


def _page(labels, roster=None):
    log = Log()
    if roster is not None:
        gather.gather_external(log, None, roster=roster)
    for i, text in enumerate(labels):
        sub = R.staff(0, 0, i)
        log.observe(sub, Q.STAFF_ORDINAL, i, reader=READERS.GEOMETRY,
                    frame="system")
        log.observe(sub, Q.MARGIN_LABEL, text, reader=READERS.TEXT_LAYER,
                    frame="system_margin")
    log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, len(labels),
                reader=READERS.GEOMETRY, frame="system")
    return log


class TestTheRosterReachesTheDecision(unittest.TestCase):

    def test_the_row_is_filed_on_the_DOCUMENT(self):
        """The premise of the frame fault, asserted by RUNNING GATHER rather
        than by a fixture. ⚠️ *A fixture that does not match GATHER tests the
        test* — this file's own recorded lesson, which cost `Q.METER_GLYPH` a
        rule that read no boxes on any real page while five unit tests and
        three mutation arms stayed green."""
        log = Log()
        gather.gather_external(log, None, roster=_ROSTER)
        rows = log.rows(Q.ROSTER_ENTRY, R.DOCUMENT)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].value["work_id"], _ROSTER.work_id)
        # and NOT on the staff, which is what makes EXACT unable to answer
        self.assertEqual(log.rows(Q.ROSTER_ENTRY, R.staff(0, 0, 0)), ())

    def test_an_EXACT_read_from_a_staff_finds_NOTHING(self):
        """⚠️⚠️ THE FRAME FAULT ITSELF, PINNED. This is what
        `ev.rows(Q.ROSTER_ENTRY)` — the obvious line — would have returned,
        forever, with the declaration satisfied and the quantity gathered."""
        log = Log()
        gather.gather_external(log, None, roster=_ROSTER)
        staff = R.staff(0, 0, 0)
        self.assertEqual(log.rows(Q.ROSTER_ENTRY, staff, scope=Scope.EXACT),
                         ())
        self.assertEqual(
            len(log.rows(Q.ROSTER_ENTRY, staff,
                         scope=Scope.SELF_AND_ANCESTORS)), 1)

    def test_a_singer_on_a_work_with_no_singers_is_VETOED(self):
        """⚠️ THE ANSWER COMING OUT, which is the only thing that has ever
        caught a frame fault here. `Tromboni Alto e Tenore` cut to `Alto e
        Tenore` reads as a TENOR — a singer — at medium confidence."""
        log = _page(["Alto e Tenore"], roster=_ROSTER)
        adjudicate.run(log)
        v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "vetoed_by_the_work_roster")
        self.assertEqual(v.detail["lexicon_said"], "Tenor")

    def test_WITHOUT_the_roster_the_singer_stands(self):
        """⚠️ THE POSITIVE CONTROL FOR THE VETO, and without it the test
        above passes for a reason that has nothing to do with the roster: an
        abstention is what this decision does on most inputs."""
        log = _page(["Alto e Tenore"], roster=None)
        adjudicate.run(log)
        v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["name"], "Tenor")

    def test_an_ordinary_label_is_UNTOUCHED_by_the_roster(self):
        """The overwhelming majority. A layer that changed common labels
        would be a different and much riskier thing."""
        for roster in (None, _ROSTER):
            log = _page(["Flauti"], roster=roster)
            adjudicate.run(log)
            v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
            self.assertEqual(v.value["name"], "Flute")
            self.assertEqual(v.reason, "label")

    def test_the_roster_row_is_in_the_verdict_BASIS(self):
        """⚠️ PROVENANCE IS `Verdict.basis`, NOT A FIELD. It cannot be
        defaulted, because it is not a lookup — and the circularity filter
        needs the dependency recorded."""
        log = _page(["Alto e Tenore"], roster=_ROSTER)
        adjudicate.run(log)
        v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
        (roster_row,) = log.rows(Q.ROSTER_ENTRY, R.DOCUMENT)
        self.assertIn(roster_row.id, v.used)

    def test_an_INCOMPLETE_roster_vetoes_NOTHING(self):
        """⚠️⚠️ A ROSTER IS A POSITIVE LIST AND IS INCOMPLETE BY
        CONSTRUCTION. Tchaikovsky 6's InstrDetail ends `..., strings` and
        that segment landed in `segments_ignored`, so the work's parsed
        roster names NO STRING AT ALL at `parse_rate 1.0`. A veto reading
        absence as denial would delete every violin on that page."""
        partial = WorkRoster(work_id="x", instruments=frozenset({"Flute"}),
                             families=frozenset({"woodwind"}), complete=False)
        log = _page(["Alto e Tenore"], roster=partial)
        adjudicate.run(log)
        v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)

    def test_a_PAGE_sourced_roster_is_REFUSED_at_the_point_of_use(self):
        """⚠️ `source_kind` IS LOAD-BEARING. The `editions` tier is `page` —
        an OMR output of the same raster — and a witness read off the ink it
        arbitrates falls silent exactly when it is needed. `work_roster()`
        enforces the tier when it BUILDS one; nothing enforced it on a row
        that arrived some other way."""
        from tools.omr.staged.adjudicators import identity
        ok = {"work_id": "x", "instruments": ["Flute"],
              "families": ["woodwind"], "complete": True,
              "source_kind": "catalog"}
        self.assertIsNotNone(identity._work_roster(ok))
        self.assertIsNone(identity._work_roster(dict(ok, source_kind="page")))
        self.assertIsNone(identity._work_roster(dict(ok, source_kind=None)))

    def test_the_record_carries_a_DICT_a_consumer_can_parse(self):
        """⚠️ `staged/__main__.py` serialises with `default=str`, so a frozen
        dataclass reaches the file as its own `repr()`. A quantity that
        survives the round trip only as prose is one step from being unread."""
        import json
        log = Log()
        gather.gather_external(log, None, roster=_ROSTER)
        (row,) = log.rows(Q.ROSTER_ENTRY, R.DOCUMENT)
        again = json.loads(json.dumps(row.value, default=str))
        self.assertIn("Flute", again["instruments"])
        self.assertEqual(again["source_kind"], "catalog")


class TestTheCLIHasTheProducer(unittest.TestCase):
    def test_work_id_and_no_roster_are_real_arguments(self):
        """⚠️ DERIVED FROM THE PARSER, not from a grep: a flag mentioned in a
        docstring and never added is this repo's *rule described in bold and
        never built*, one layer down."""
        import io
        import contextlib
        from tools.omr.staged import __main__ as M
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            M.main(["--help"])
        text = buf.getvalue()
        self.assertIn("--work-id", text)
        self.assertIn("--no-roster", text)

    def test_run_staged_actually_receives_it(self):
        """⚠️ THE ARGUMENT EXISTING IS NOT THE ARGUMENT ARRIVING. `pdf_path`
        was a parameter on `gather` whose only caller was `gather`'s own
        forward; the flag half of that bug is exactly this half."""
        import unittest.mock as mock
        from tools.omr.staged import __main__ as M
        seen = {}

        def fake(pdf, pages, **kw):
            seen.update(kw)
            return {"adjudication": {"decided": 0, "abstained": 0,
                                     "excluded_as_circular": []},
                    "evaluation": {"counts": {"fired": 0, "skipped": 0}},
                    "stubs": {"decisions": [], "consequences": []}}

        with mock.patch("tools.omr.staged.pipeline.run_staged", fake), \
                mock.patch("tools.omr.work_roster.roster_for_pdf",
                           return_value=_ROSTER):
            M.main(["x.pdf", "--out", "/dev/null"])
        self.assertIs(seen.get("roster"), _ROSTER)

    def test_no_roster_turns_it_off(self):
        import unittest.mock as mock
        from tools.omr.staged import __main__ as M
        seen = {}

        def fake(pdf, pages, **kw):
            seen.update(kw)
            return {"adjudication": {"decided": 0, "abstained": 0,
                                     "excluded_as_circular": []},
                    "evaluation": {"counts": {"fired": 0, "skipped": 0}},
                    "stubs": {"decisions": [], "consequences": []}}

        with mock.patch("tools.omr.staged.pipeline.run_staged", fake), \
                mock.patch("tools.omr.work_roster.roster_for_pdf",
                           return_value=_ROSTER):
            M.main(["x.pdf", "--out", "/dev/null", "--no-roster"])
        self.assertIsNone(seen.get("roster"))


if __name__ == "__main__":
    unittest.main()
