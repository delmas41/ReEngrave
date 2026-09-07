"""The key-signature vote's MAJORITY SHARE, kept instead of destroyed.

`reconcile` computes each system's modal reference and the share of weight it
commands, compares that share once — `majority <= config.min_majority` — and
drops it. So a reference agreed by every staff of a system and one scraping past
the threshold left the same record, and the verdict reason "no majority to check
against" named the branch without ever saying how far off a majority the page
was.

Recorded on `VoteResult.majority_by_system`, with the tally it is a share of on
`vote_totals_by_system`, and per staff on `staff["key_signature_evidence"]`.

⚠️ Run RED with the two `result.*_by_system` assignments removed, and again with
the `_modal_reference` trace removed.
"""

from __future__ import annotations

import pytest

from tools.omr.key_signature_vote import StaffCandidate, reconcile


def _cand(staff_index, ordinal, fifths, weight=3.0, system=0, source="locator"):
    return StaffCandidate(staff_index=staff_index, system_index=system,
                          ordinal=ordinal, fifths=fifths, weight=weight,
                          source=source)


class TestMajorityShareSurvives:
    def test_a_unanimous_system_records_a_share_of_one(self):
        result = reconcile([_cand(i, i, -3) for i in range(4)])
        assert result.majority_by_system[0] == pytest.approx(1.0)
        assert result.vote_totals_by_system[0] == {-3: pytest.approx(12.0)}

    def test_a_SPLIT_system_records_how_split_it_was(self):
        """The distinction being lost: this page and the unanimous one above
        both produced a reference and both said nothing about the margin."""
        result = reconcile([_cand(0, 0, -3), _cand(1, 1, -3), _cand(2, 2, 2)])
        assert result.majority_by_system[0] == pytest.approx(6.0 / 9.0, abs=1e-4)
        assert result.vote_totals_by_system[0] == {-3: pytest.approx(6.0),
                                                   2: pytest.approx(3.0)}

    def test_the_recorded_share_is_the_one_the_branch_was_chosen_on(self):
        """A record that could disagree with the decision would be worse than
        none. Below `min_majority` (0.5) the vote must have taken the
        no-majority branch, and its reason says so."""
        # Four distinct readings, all equal weight: the modal one holds 0.25.
        result = reconcile([_cand(0, 0, -3), _cand(1, 1, 2),
                            _cand(2, 2, 4), _cand(3, 3, -1)])
        assert result.majority_by_system[0] == pytest.approx(0.25)
        assert result.majority_by_system[0] <= 0.5
        assert all("no majority" in v.reason
                   for v in result.verdicts.values())

    def test_a_system_whose_readings_all_weigh_under_one_records_an_EMPTY_tally(
            self):
        """`_modal_reference` drops readings weighing under 1.0 before it
        counts, so "everything was read and nothing voted" and "nothing was
        read" both return (None, 0.0). The tally separates them."""
        result = reconcile([_cand(i, i, -3, weight=0.4) for i in range(3)])
        assert result.majority_by_system[0] == pytest.approx(0.0)
        assert result.vote_totals_by_system[0] == {}
        assert result.reference_written_by_system[0] is None


class TestTheEvidenceReachesTheStaff:
    def test_header_key_signatures_fills_the_evidence_dict(self):
        """The wiring — `_header_key_signatures` returns a lossy 3-tuple and
        widening it would touch three existing tests, so the record is an
        out-parameter."""
        import inspect

        from tools.omr.transcribe import _header_key_signatures

        params = inspect.signature(_header_key_signatures).parameters
        assert "evidence" in params
        assert params["evidence"].default is None, (
            "the record must be opt-in: a caller that passes nothing pays "
            "nothing and behaves exactly as before"
        )

    def test_the_staff_dict_is_given_the_record(self):
        """AST wiring check: the transcribe loop must actually write it, or
        the vote's number stops at a local dict again."""
        import ast
        import inspect
        from pathlib import Path

        from tools.omr import transcribe as T

        tree = ast.parse(Path(inspect.getfile(T)).read_text())
        writes = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "key_signature_evidence"
        ]
        assert writes, "nothing puts key_signature_evidence on the staff dict"
