"""A staff that contradicts its own margin label.

Three things are pinned here, and the second is the one that matters.

1. The rule itself — what fires and what does not.

2. **That it is WIRED.** This project's most-repeated failure is a signal
   computed and consumed by nobody: the five internal-consistency checks compute
   a graded confidence nothing reads (85 warnings fire inert on one document),
   and `export.py` mentions detection confidence once, in a comment. So the
   anti-drift tests below assert at source level that `apply_contextual_analysis`
   calls `find_contradictions`, puts the summary on `summary`, warns when it
   fires, and writes the per-staff field — following
   `test_export.py::TestEventlessMeasureKeepsItsMarks` and
   `test_contextual_roster_ambiguity.py`, and verified to fail when each call
   site is removed.

3. **That it reads the PER-STAFF evidence and not `instrument_label`.** That
   field is slot-carried — one raw text per slot, stamped onto every staff of
   the slot on every page — so a check built on it is unable to disagree, and
   `contextual.py` says so in its own comment. A test on the wrong field would
   pass while measuring nothing, which is the specific way this check could
   ship dead.

The characterisation the module docstring quotes (158 contradictions over two
whole works, 0.873 export-wrong / 0.127 label-wrong / 0 both-right) is pinned
against the committed artefacts at the bottom.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from tools.omr import contextual
from tools.omr.label_contradiction import (contradictable,
                                           find_contradictions,
                                           report_from_result, summarise)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(contextual.__file__).read_text()


# ── the rule ────────────────────────────────────────────────────────────────

def _call(*, slots, names, sources=None, evidence, vetoed=()):
    return find_contradictions(
        staff_keys=list(slots), slot_by_staff=slots,
        instrument_name_by_slot=names,
        instrument_source=sources or {s: "label" for s in names},
        evidence=evidence, vetoed_keys=vetoed)


class TestTheRule:
    def test_a_staff_whose_label_disagrees_with_its_name_fires(self):
        rows = _call(slots={(0, 0, 3): 7}, names={7: "Trumpet"},
                     evidence={0: {3: "Timpani"}})
        assert [(r["read"], r["exported"]) for r in rows] == \
            [("Timpani", "Trumpet")]

    def test_agreement_is_silent(self):
        assert _call(slots={(0, 0, 3): 7}, names={7: "Timpani"},
                     evidence={0: {3: "Timpani"}}) == []

    def test_a_staff_with_no_label_of_its_own_cannot_contradict(self):
        assert _call(slots={(0, 0, 3): 7}, names={7: "Trumpet"},
                     evidence={0: {}}) == []

    def test_a_staff_with_no_slot_or_no_name_is_skipped(self):
        assert _call(slots={(0, 0, 3): -1}, names={7: "Trumpet"},
                     evidence={0: {3: "Timpani"}}) == []
        assert _call(slots={(0, 0, 3): 7}, names={},
                     evidence={0: {3: "Timpani"}}) == []

    def test_the_evidence_is_per_page(self):
        """Page 1's staff 3 must not be judged against page 0's label."""
        assert _call(slots={(1, 0, 3): 7}, names={7: "Trumpet"},
                     evidence={0: {3: "Timpani"}}) == []

    def test_a_vetoed_staff_has_no_name_to_contradict(self):
        assert _call(slots={(0, 0, 3): 7}, names={7: "Trumpet"},
                     evidence={0: {3: "Timpani"}},
                     vetoed=[(0, 0, 3)]) == []

    @pytest.mark.parametrize("source", ["label", "roster", "score_order",
                                        "score_order_ambiguity"])
    def test_every_source_is_in_scope_and_reported(self, source):
        """⚠️ `instrument_source` is a SPLIT to report, never a filter.

        On the 88-page Beethoven the largest single population — 93 staves
        printed `Tp.` and exported `Trumpet` — carries
        `score_order_ambiguity`, the same source as the three correct `Basso.`
        overturns on that document. Excluding the source to suppress the three
        would hide the ninety-three.
        """
        rows = _call(slots={(0, 0, 3): 7}, names={7: "Trumpet"},
                     sources={7: source}, evidence={0: {3: "Timpani"}})
        assert [r["source"] for r in rows] == [source]

    def test_the_duplicate_flag_is_context_and_is_scoped_to_the_system(self):
        rows = _call(
            slots={(0, 0, 2): 6, (0, 0, 3): 7, (0, 1, 9): 7},
            names={6: "Trumpet", 7: "Trumpet"},
            evidence={0: {2: "Trumpet", 3: "Timpani", 9: "Timpani"}})
        by_staff = {r["staff_index"]: r for r in rows}
        # System 0 carries a label-agreeing Trumpet; system 1 does not.
        assert by_staff[3]["name_already_on_system"] is True
        assert by_staff[9]["name_already_on_system"] is False

    def test_the_denominator_counts_what_could_have_contradicted(self):
        slots = {(0, 0, 1): 5, (0, 0, 2): 6, (0, 0, 3): 7, (0, 0, 4): -1}
        names = {5: "Flute", 6: "Oboe", 7: "Trumpet"}
        evidence = {0: {1: "Flute", 3: "Timpani"}}
        assert contradictable(staff_keys=list(slots), slot_by_staff=slots,
                              instrument_name_by_slot=names,
                              evidence=evidence) == 2

    def test_the_summary_reports_the_split_not_only_the_total(self):
        rows = _call(slots={(0, 0, 3): 7, (0, 0, 4): 8},
                     names={7: "Trumpet", 8: "Contrabass"},
                     sources={7: "label", 8: "score_order_ambiguity"},
                     evidence={0: {3: "Timpani", 4: "Bass voice"}})
        s = summarise(rows, 20)
        assert s["contradictions"] == 2 and s["labelled_staff_records"] == 20
        assert s["by_source"] == {"label": 1, "score_order_ambiguity": 1}
        assert s["by_pair"] == {"Bass voice -> Contrabass": 1,
                                "Timpani -> Trumpet": 1}


# ── that it is wired ────────────────────────────────────────────────────────

def _contextual_body() -> list[ast.stmt]:
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if (isinstance(node, ast.FunctionDef)
                and node.name == "apply_contextual_analysis"):
            return list(ast.walk(node))
    raise AssertionError("apply_contextual_analysis is gone")


WIRING = (
    "if this moved, re-point the test rather than deleting it: an identity "
    "signal that is computed and read by nobody is this project's most "
    "repeated failure, and the accuracy metric cannot see a wrong "
    "<part-name> at all."
)


def test_contextual_calls_find_contradictions():
    calls = [n for n in _contextual_body()
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "find_contradictions"]
    assert calls, f"apply_contextual_analysis no longer computes it — {WIRING}"


def test_it_is_computed_unconditionally():
    """No flag, and not inside the veto's `if`.

    The check renames nothing and refuses nothing, so there is no behaviour to
    gate; putting it behind `OMR_ABSENT_INSTRUMENT_VETO` would make it absent
    from exactly the runs someone turned the veto off to inspect.
    """
    tree = ast.parse(SOURCE)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef)
              and n.name == "apply_contextual_analysis")
    guarded = [n for n in ast.walk(fn) if isinstance(n, ast.If)
               and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                       and c.func.id == "find_contradictions"
                       for c in ast.walk(n))]
    assert not guarded, (
        "find_contradictions is now inside an `if` — it must run on every "
        f"contextual pass. {WIRING}")


def test_the_summary_carries_the_report():
    # An ASSIGNMENT specifically. Matching any `summary["label_contradiction"]`
    # subscript passes on the READS in the warning's arguments, so deleting the
    # write went undetected until a mutation run said so.
    assigns = [n for n in _contextual_body() if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Subscript)
                       and isinstance(t.value, ast.Name)
                       and t.value.id == "summary"
                       and isinstance(t.slice, ast.Constant)
                       and t.slice.value == "label_contradiction"
                       for t in n.targets)]
    assert assigns, f"summary['label_contradiction'] is never assigned — {WIRING}"


def test_a_firing_raises_a_warning():
    """Loud, on the channel `unresolved_labels` already uses.

    A wrong `<part-name>` is invisible to musicdiff, so a run that produced 110
    of them can otherwise complete in silence.
    """
    warns = [n for n in _contextual_body()
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "warning"
             and isinstance(n.func.value, ast.Name) and n.func.value.id ==
             "logger"
             and any(isinstance(a, ast.Constant)
                     and "CONTRADICT" in str(a.value) for a in n.args)]
    assert warns, f"the contradiction warning is gone — {WIRING}"


def test_the_per_staff_field_comes_from_the_per_staff_evidence():
    """⚠️ NOT from `instrument_label`, which is slot-carried and cannot disagree.

    Asserts the staff-dict write reads `_contradiction_by_key`, which is built
    from `find_contradictions` over `label_evidence`. Building it from
    `instrument_label` or `raw_label_by_slot` would give a check that passes
    while measuring nothing — the failure `contextual.py`'s own comment warns
    about.
    """
    writes = [n for n in _contextual_body() if isinstance(n, ast.Subscript)
              and isinstance(n.value, ast.Name) and n.value.id == "staff"
              and isinstance(n.slice, ast.Constant)
              and n.slice.value == "label_contradiction"]
    assert writes, f"staff['label_contradiction'] is gone — {WIRING}"
    sources = [n for n in _contextual_body()
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "get" and isinstance(n.func.value, ast.Name)
               and n.func.value.id == "_contradiction_by_key"]
    assert sources, (
        "the per-staff field is no longer read out of `_contradiction_by_key`. "
        "It must never be derived from `instrument_label` / "
        "`raw_label_by_slot`: those are SLOT-carried, so an audit on them is "
        f"unable to disagree. {WIRING}")


def test_nothing_derives_the_contradiction_from_the_slot_carried_label():
    """The vacuity trap, asserted directly.

    Prose is allowed to name the field — the module docstring explains at
    length why it must not be used — so this looks at the CODE: identifiers
    and non-docstring string literals.
    """
    path = Path(contextual.__file__).parent / "label_contradiction.py"
    tree = ast.parse(path.read_text())
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            used.add(node.value)
    for field in ("instrument_label", "raw_label_by_slot"):
        assert field not in used, (
            f"label_contradiction.py reads {field}, which is slot-carried: "
            "one raw text per SLOT stamped onto every staff of that slot on "
            "every page. A check on it cannot fail.")


# ── the characterisation, pinned to the committed artefacts ─────────────────

ARTEFACTS = {
    # (artefact, contradictions, labelled staff records)
    "beet5/-fitsearch-spans-on.json": (110, 973),
    "brahms1/-fitsearch-spans-on.json": (48, 1713),
    # The known span regression, and the fix. The count TRACKS a defect it was
    # never told about: `OMR_SPAN_REFERENCE_FIT=off` with spans on is the arm
    # that names 149 staves an instrument the work has not got yet, and this
    # rises 44 -> 167 there and falls back to 48 when `search` lands. Free
    # evidence, no truth file. Cross-checked against
    # `benchmarks/omr-span-composition-2026-09/probe/score_brahms.py`, which
    # computes the same column independently and prints 44 / 167 / 48.
    "brahms1/-fitoff-spans-on.json": (167, 1713),
    "brahms1/-fitsearch-spans-off.json": (44, 1713),
}


def _artefact(pattern: str) -> Path:
    files = subprocess.run(["git", "ls-files", "*.json"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    hits = [f for f in files if pattern in f]
    assert len(hits) == 1, f"{len(hits)} artefacts match {pattern}: {hits}"
    return ROOT / hits[0]


@pytest.mark.parametrize("pattern,expected", sorted(ARTEFACTS.items()))
def test_the_committed_artefacts_still_read_the_recorded_figures(pattern,
                                                                 expected):
    path = _artefact(pattern)
    rep = report_from_result(json.loads(path.read_text()))
    assert (rep["contradictions"], rep["labelled_staff_records"]) == expected


def test_every_adjudicated_row_is_still_produced():
    """The 158 hand-adjudicated rows, against the artefacts they came from.

    `benchmarks/omr-label-contradiction-2026-09/out/adjudication.json` carries
    one verdict per row, each settled by opening the printed page. If the
    detector changes what those pages read the adjudication must be redone, and
    this is what says so.
    """
    adj = json.loads((ROOT / "benchmarks/omr-label-contradiction-2026-09"
                      "/out/adjudication.json").read_text())
    assert len(adj) == 158
    assert sum(1 for a in adj if a["verdict"] == "export_wrong") == 138
    assert sum(1 for a in adj if a["verdict"] == "label_wrong") == 20
    for work, pattern in (("beet5", "beet5/-fitsearch-spans-on.json"),
                          ("brahms1", "brahms1/-fitsearch-spans-on.json")):
        rep = report_from_result(json.loads(_artefact(pattern).read_text()))
        live = {(r["page_index"], r["system_index"], r["staff_index"],
                 r["read"], r["exported"]) for r in rep["rows"]}
        want = {(a["page_index"], a["system_index"], a["staff_index"],
                 a["read"], a["exported"]) for a in adj if a["work"] == work}
        assert live == want
