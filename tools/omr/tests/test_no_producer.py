"""The no-producer check: it finds both known instances, and it can go RED.

⚠️ The headline assertions are `test_roster_is_found_with_no_hint` and
`test_dossier_is_found_with_no_hint` — the check is handed NOTHING but the
tree, and must name the parameters unaided. A check that needs to be told
what to look for is `export_coverage.VISIBLE` again.

⚠️⚠️ **A CHECK THAT CANNOT FAIL IS WORSE THAN NO CHECK.** `EMPTY CELLS: none`
was emptied in one line in this repo and nobody noticed. So the synthetic
trees here include a POSITIVE CONTROL in the same class: a chain that IS
supplied, which must NOT be reported. Every refusal test is paired with an
acceptance test, because a battery of refusal tests passes by refusing
everything.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.omr import no_producer as NP

REPO = Path(__file__).resolve().parents[3]


def _write(root: Path, rel: str, src: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src)


def _names(report: NP.Report) -> set:
    return {f.param for f in report.findings}


# --------------------------------------------------------------------------
# The real tree.


class TestTheKnownInstances(unittest.TestCase):
    """Both instances the repo found BY ACCIDENT, found by the walk."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = NP.scan([REPO / "tools"])

    def test_roster_is_no_longer_a_finding(self) -> None:
        """⚠⚠ RED ON SUCCESS, AND CONVERTED RATHER THAN DELETED. This
        asserted `roster` IS found, which was true on the day it was written
        and stopped being true when `staged/__main__.py` gained `--work-id`
        the same day. *An assertion that a finding exists is a property of
        the BUILD'S PROGRESS, not of the mechanism* — so it is now the mirror
        of `test_pdf_path_is_no_longer_a_finding`.

        ⚠️⚠️ THE LIVE-INSTANCE CLAUSE RETIRED 2026-09-21 AND THAT IS THE
        THING TO BE SUSPICIOUS OF. It read `assertIn("dossier", ...)` — "the
        question must still fire on a LIVE instance, or this file is asserting
        a zero it cannot interpret" — and `dossier` was repaired the day
        `--sheet` landed. **All three instances this check ever found are now
        repaired, so there is no live one left to anchor on.** The anchor moves
        to the SYNTHETIC trees below, which reconstruct each topology; that is
        the whole of the red proof now and the reason those tests may never be
        allowed to go quiet."""
        self.assertNotIn("roster", _names(self.report))

    def test_dossier_is_no_longer_a_finding(self) -> None:
        """⚠️ RED ON SUCCESS, CONVERTED NOT DELETED — the third and last.

        `staged/__main__.py` gained `--sheet` on 2026-09-21 and the chain is
        supplied, under Sean's ruling that a dossier reaches the pipeline only
        through a sheet a human confirmed. Its `RECORDED` entry left the
        inventory the same day, as that entry itself instructed.
        """
        self.assertNotIn("dossier", _names(self.report))

    def test_a_chain_names_every_layer(self) -> None:
        """⚠️ RE-POINTED AT A SYNTHETIC TREE WHEN `dossier` WAS REPAIRED —
        it had already been re-pointed once, off `roster` onto `dossier`, and
        there is no third live instance to move to. The property is unchanged:
        a finding must name EVERY layer, not only its ends. What moved is that
        the tree carrying it is now built by the test rather than found in the
        repo, which is exactly what `test_THE_PDF_PATH_TOPOLOGY` already does.
        """
        r = TestTheMechanism()._scan({"m.py": '''
def run_staged(pdf, pages, *, dossier=None):
    return run_staged_on(prepare(pdf), dossier=dossier)

def run_staged_on(prepared, *, dossier=None):
    return gather(prepared, dossier=dossier)

def gather(prepared, *, dossier=None):
    return gather_external(prepared, dossier=dossier)

def gather_external(prepared, *, dossier=None):
    if dossier is None:
        abstain("no dossier supplied")
        return None
    return read(dossier)
'''})
        self.assertEqual(_names(r), {"dossier"})
        self.assertEqual(
            [k[0] for k in r.findings[0].keys],
            ["run_staged", "run_staged_on", "gather", "gather_external"],
        )

    def test_pdf_path_is_no_longer_a_finding(self) -> None:
        """It was repaired in 3a725f07 and the check agrees."""
        self.assertNotIn("pdf_path", _names(self.report))

    def test_the_funnel_narrows(self) -> None:
        """REACH BEFORE ACCURACY: a report with no funnel cannot be judged."""
        r = self.report
        self.assertGreater(r.total_params, 1000)
        self.assertGreater(r.none_defaulted, 0)
        self.assertLess(r.none_defaulted, r.total_params)
        self.assertLessEqual(r.threaded, r.none_defaulted)
        self.assertLessEqual(r.unsupplied, r.threaded)
        self.assertLessEqual(r.guarded_chains, r.chains)
        # and it actually discriminates rather than reporting everything
        self.assertLess(len(r.findings), 10)

    def test_the_benign_chains_are_reported_apart_and_not_suppressed(self) -> None:
        """`None means use the module default` is an ANSWER, not a silence.

        They are printed under NOT REPORTED with the reason the guard test
        gives, rather than being dropped or hand-listed by name.
        """
        self.assertGreater(len(self.report.unguarded), 0)
        text = NP.format_report(self.report)
        self.assertIn("NOT REPORTED", text)
        for f in self.report.unguarded:
            self.assertIn(f.name, text)


class TestTheInventoryDescribesTheTreeNotItsHistory(unittest.TestCase):
    """The KNOWN_GAPS rule: a CLOSED entry must LEAVE the list."""

    def test_every_recorded_entry_still_fires(self) -> None:
        report = NP.scan([REPO / "tools"])
        live = {f.ident for f in report.findings}
        stale = sorted(set(NP.RECORDED) - live)
        self.assertEqual(stale, [], (
            "These entries no longer fire — the chain was wired up. DELETE "
            "them from RECORDED; an inventory that outlives its findings "
            "stops describing the code."))

    def test_check_is_green_because_the_tree_is_CLEAN_not_because_it_is_excused(self) -> None:
        """⚠️⚠️ THIS TEST CHANGED MEANING ON 2026-09-21 AND SAYS SO.

        It asserted `report.findings` is non-empty — "the findings did not
        disappear silently" — which was the right question while any instance
        was open. All three are now repaired and `RECORDED` is empty, so green
        means CLEAN. The two are indistinguishable from the outside, which is
        why the red proof moved wholesale onto the synthetic trees: see
        `TestTheMechanism` and the CLI red proof below.
        """
        report = NP.scan([REPO / "tools"])
        unrecorded = [f.ident for f in report.findings if f.ident not in NP.RECORDED]
        self.assertEqual(unrecorded, [])
        self.assertEqual(dict(NP.RECORDED), {}, (
            "RECORDED is expected empty now; if an entry returns, this test "
            "must go back to asserting the findings are non-empty"))


# --------------------------------------------------------------------------
# Synthetic trees — the mechanism, and the proof it can go red.


_GUARD_BODY = '''
def consumer(x, *, thing=None):
    if thing is None:
        report("no thing supplied")
        return None
    return thing
'''


class TestTheMechanism(unittest.TestCase):

    def _scan(self, files: dict) -> NP.Report:
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "pkg"
        for rel, src in files.items():
            _write(root, rel, src)
        return NP.scan([root])

    def test_a_chain_with_no_producer_is_reported(self) -> None:
        r = self._scan({"m.py": '''
def entry(a, *, thing=None):
    return middle(a, thing=thing)

def middle(a, *, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY})
        self.assertEqual(_names(r), {"thing"})

    def test_THE_POSITIVE_CONTROL_a_supplied_chain_is_not_reported(self) -> None:
        """The same tree with ONE real producer added must go quiet."""
        r = self._scan({"m.py": '''
def top():
    return entry(1, thing="a real value")

def entry(a, *, thing=None):
    return middle(a, thing=thing)

def middle(a, *, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY})
        self.assertEqual(_names(r), set())

    def test_a_positional_producer_counts(self) -> None:
        """`run_staged(args.pdf, pages)` is how `pdf_path` is supplied today."""
        r = self._scan({"m.py": '''
def top():
    return entry(1, "a real value")

def entry(a, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY})
        self.assertEqual(_names(r), set())

    def test_an_optional_argument_that_merely_defaults_is_not_a_finding(self) -> None:
        """`thing or DEFAULT` changes no behaviour — the D5 discriminator."""
        r = self._scan({"m.py": '''
DEFAULT = 4

def entry(a, *, thing=None):
    return middle(a, thing=thing)

def middle(a, *, thing=None):
    return (thing or DEFAULT) + a
'''})
        self.assertEqual(_names(r), set())
        self.assertEqual({f.param for f in r.unguarded}, {"thing"})

    def test_one_layer_is_not_a_chain(self) -> None:
        """A single unsupplied parameter is an optional argument, not a fault."""
        r = self._scan({"m.py": '''
def entry(a, *, thing=None):
    if thing is None:
        report("none")
        return None
    return thing
'''})
        self.assertEqual(_names(r), set())

    def test_a_LONE_unsupplied_node_that_an_edge_touches_is_not_a_chain(self) -> None:
        """⚠️ The test above is named for a hazard it does not REACH.

        Its `thing` never enters D3 at all — no edge touches it — so the
        chain-size rule is never consulted and a mutation to `len(keys) < 0`
        walked straight past it (mutation battery, first run). The case that
        exercises the rule is a node that IS unsupplied and IS touched by an
        edge whose OTHER end is supplied: `caller` hands to `consumer`, and
        somebody else hands `consumer` a real value. `caller(thing)` is then
        a perfectly ordinary optional argument, and the value does arrive.
        """
        r = self._scan({"m.py": '''
def other():
    return consumer(1, thing="a real value")

def caller(a, *, thing=None):
    if thing is None:
        report("no thing in caller")
        return None
    return consumer(a, thing=thing)
''' + _GUARD_BODY})
        self.assertEqual(_names(r), set())
        self.assertEqual(r.unsupplied, 1)   # the node IS in D3
        self.assertEqual(r.chains, 0)       # and the size rule is what drops it

    def test_a_test_file_is_not_a_producer(self) -> None:
        """The choice that separates 2 findings from 0 on the real tree."""
        files = {"m.py": '''
def entry(a, *, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY,
                 "tests/test_m.py": '''
from pkg.m import entry

def test_it():
    entry(1, thing="fixture")
'''}
        self.assertEqual(_names(self._scan(files)), {"thing"})

    def test_but_the_arm_is_switchable_so_the_choice_can_be_priced(self) -> None:
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "pkg"
        _write(root, "m.py", '''
def entry(a, *, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY)
        _write(root, "tests/test_m.py", '''
def test_it():
    entry(1, thing="fixture")
''')
        self.assertEqual(_names(NP.scan([root], tests_produce=True)), set())

    def test_a_splat_we_cannot_read_supplies_everything(self) -> None:
        """Conservative on purpose: an unreadable call must not produce a finding."""
        r = self._scan({"m.py": '''
def top(**opts):
    return entry(1, **opts)

def entry(a, *, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY})
        self.assertEqual(_names(r), set())

    def test_an_external_module_of_the_same_name_does_not_silence_it(self) -> None:
        """MEASURED: `asyncio.gather(*tasks)` silenced BOTH live findings.

        Name-keying matched it to `staged.gather` and its splat marked every
        parameter supplied. Adding `backend/` to the scan took the report from
        2 to 0 before `_local_packages` existed.
        """
        r = self._scan({"m.py": '''
import asyncio

async def unrelated(tasks):
    return await asyncio.entry(*tasks, thing=True)

def entry(a, *, thing=None):
    return consumer(a, thing=thing)
''' + _GUARD_BODY})
        self.assertEqual(_names(r), {"thing"})

    def test_a_decorator_argument_is_not_this_functions_parameter(self) -> None:
        """A decorator is evaluated in the OUTER scope; a name in it is not a forward.

        ⚠️ The first version of this test passed a STRING on the decorator, so
        it could not distinguish the two placements at all — a test named for a
        hazard it does not reach, caught by the mutation battery. The name in
        the decorator has to be one that ALSO names a parameter of the function
        below it: read in the outer scope it is the module global and a real
        producer; read inside the function it is a forward from an unsupplied
        parameter, and the whole chain goes dark.
        """
        r = self._scan({"m.py": '''
thing = "a real value, supplied at the decorator"

def deco(*, thing=None):
    return consumer(1, thing=thing)

@deco(thing=thing)
def entry(a, *, thing=None):
    return a
''' + _GUARD_BODY})
        self.assertEqual(_names(r), set())

    def test_THE_PDF_PATH_TOPOLOGY(self) -> None:
        """Instance 1's exact shape, reconstructed.

        The REAL pre-`3a725f07` tree was scanned separately and the check
        reports `pdf_path: gather() -> gather_margin_labels()` there; see
        `benchmarks/omr-no-producer-check-2026-09/FINDINGS.md`. This pins the
        topology so the demonstration survives without a git checkout.
        """
        r = self._scan({"m.py": '''
def run_staged(pdf_path, pages, *, dpi=300):
    prepared = prepare_pages(pdf_path, pages, dpi=dpi)
    return run_staged_on(prepared)

def run_staged_on(prepared, *, pdf_path=None):
    return gather(prepared, pdf_path=pdf_path)

def gather(prepared, *, pdf_path=None):
    return gather_margin_labels(prepared, pdf_path=pdf_path)

def gather_margin_labels(prepared, *, pdf_path=None):
    if pdf_path is None:
        abstain("no pdf_path supplied to gather()")
        return None
    return read(pdf_path)
'''})
        self.assertEqual(_names(r), {"pdf_path"})
        chain = r.findings[0]
        self.assertEqual([k[0] for k in chain.keys],
                         ["run_staged_on", "gather", "gather_margin_labels"])


class TestTheCli(unittest.TestCase):

    def test_check_exits_zero_when_every_finding_is_recorded(self) -> None:
        out = subprocess.run(
            [sys.executable, "-m", "tools.omr.no_producer", "--check"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_check_exits_non_zero_on_an_unrecorded_finding(self) -> None:
        """RED PROOF at the CLI level.

        ⚠️ IT USED TO EMPTY `RECORDED` AND SCAN THE REAL TREE, which worked
        only while a live finding existed to un-excuse. All three are repaired
        now, so that mutation makes no difference and the proof would pass
        vacuously — it is pointed at a SYNTHETIC tree instead, which is the
        only thing that can still turn this check red.
        """
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "pkg"
        root.mkdir(parents=True)
        (root / "__init__.py").write_text("")
        (root / "m.py").write_text(
            "def outer(a, *, thing=None):\n"
            "    return middle(a, thing=thing)\n"
            "\n"
            "def middle(a, *, thing=None):\n"
            "    return inner(a, thing=thing)\n"
            "\n"
            "def inner(a, *, thing=None):\n"
            "    if thing is None:\n"
            "        abstain('no thing supplied')\n"
            "        return None\n"
            "    return thing\n")
        out = subprocess.run(
            [sys.executable, "-m", "tools.omr.no_producer",
             "--scan", str(root), "--check"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        self.assertIn("threaded with no producer", out.stderr)


if __name__ == "__main__":
    unittest.main()
