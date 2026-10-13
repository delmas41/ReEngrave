"""ROADMAP 2.94 / 2.95: `lookup` reads a parenthetical crook printed BEFORE the
instrument word (`(C) Hr.`) exactly as it reads the trailing one (`Hr. (C)`).

RED on the unrepaired tree: `(C) Hr.` and `(Es) Hr.` fell through to the
horn's default F offset (1).
"""
import unittest

from tools.omr.instruments import lookup


def _off(text):
    m = lookup(text)
    return m.fifths_offset if m else None


class TestLeadingCrook(unittest.TestCase):
    def test_leading_equals_trailing(self):
        self.assertEqual(_off("(C) Hr."), 0)
        self.assertEqual(_off("(Es) Hr."), 3)
        self.assertEqual(_off("(C) Hr."), _off("Hr. (C)"))
        self.assertEqual(_off("(Es) Hr."), _off("Hr. (Es)"))

    def test_trailing_form_unchanged(self):
        self.assertEqual(_off("Hr. (C)"), 0)
        self.assertEqual(_off("Hr. (Es)"), 3)
        self.assertEqual(_off("Hr."), 1)
        self.assertEqual(lookup("(C) Hr.").instrument.name, "Horn")

    def test_a_parenthetical_that_is_not_a_crook_stays_default(self):
        self.assertEqual(_off("(Solo) Hr."), 1)
        self.assertEqual(_off("(2) Hr."), 1)

    def test_a_bare_leading_letter_is_not_claimed(self):
        self.assertEqual(_off("C Hr."), 1)

    def test_a_non_transposing_instrument_is_untouched(self):
        self.assertEqual(_off("(C) Fl."), 0)


if __name__ == "__main__":
    unittest.main()
