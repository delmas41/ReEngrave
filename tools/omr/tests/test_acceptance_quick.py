"""Fast unit tests for the pure logic in `tools.omr.acceptance_quick` that
does not need a gather, a shared record, or the score library — just the
manifest-parsing helper the manager review of ff8afcb8 (2026-09-30) added.

CLAUDE.md §6c: no `library/`, `omr-weights`, venv or `.pdf"` string appears
in this file, so it stays in the fast tier.
"""
import unittest

from tools.omr.acceptance_quick import QuickError, first_movement_page


class TestFirstMovementPage(unittest.TestCase):
    """The bug this guards: gathering ONLY the count page loses the meter/
    key CARRY from earlier pages (manager review, 2026-09-30) — the fix
    is gathering from the movement's first page through the count page,
    and that first page must be READ from the manifest, never guessed."""

    def test_reads_structural_whole_movement_field(self):
        doc = {"id": "x", "whole_movement": {"pages": "1-16"}}
        self.assertEqual(first_movement_page(doc), 1)

    def test_reads_zero_indexed_structural_field(self):
        doc = {"id": "x", "whole_movement": {"pages": "0-26"}}
        self.assertEqual(first_movement_page(doc), 0)

    def test_falls_back_to_prose_in_caveats(self):
        doc = {"id": "x", "caveats": [
            "Whole movement, pdf pages 0-26 (27 pages). The movement "
            "boundary was VERIFIED against the plate, not assumed."]}
        self.assertEqual(first_movement_page(doc), 0)

    def test_structural_field_wins_over_caveats(self):
        doc = {"id": "x", "whole_movement": {"pages": "1-16"},
              "caveats": ["Whole movement, pdf pages 9-99 (fake, should not win)."]}
        self.assertEqual(first_movement_page(doc), 1)

    def test_refuses_when_neither_is_present(self):
        doc = {"id": "x"}
        with self.assertRaises(QuickError):
            first_movement_page(doc)


if __name__ == "__main__":
    unittest.main()
