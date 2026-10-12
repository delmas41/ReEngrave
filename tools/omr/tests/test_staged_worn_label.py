"""ROADMAP 2.94: a worn instrument label (`Oh.` for `Ob.`) is named only in the
system's own gap, from the catalog roster, never by widening the lexicon.

RED against the unrepaired tree: `decide` has no `named_in_system` and
`adjudicate_instrument` never reads a sibling, so the positive test fails
there; the refusal tests pass there by refusing everything, which is why each
has a positive control in the same class (the lone-gap case below).
"""

from __future__ import annotations

import unittest

from tools.omr import work_roster as WR
from tools.omr.instruments import lookup
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS


def _roster(instruments, families=("woodwind",)):
    return WR.WorkRoster(work_id="t", instruments=frozenset(instruments),
                         families=frozenset(families), complete=True)


def _system(labels, roster_instruments=("Oboe", "Flute", "Clarinet",
                                        "Bassoon")):
    log = Log()
    for i, text in enumerate(labels):
        sub = R.staff(0, 0, i)
        log.observe(sub, Q.STAFF_ORDINAL, i, reader=READERS.GEOMETRY,
                    frame="system")
        if text is not None:
            log.observe(sub, Q.MARGIN_LABEL, text, reader=READERS.SURYA,
                        frame="page")
    log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, len(labels),
                reader=READERS.GEOMETRY, frame="system")
    if roster_instruments is not None:
        log.observe(R.DOCUMENT, Q.ROSTER_ENTRY,
                    {"work_id": "t", "instruments": list(roster_instruments),
                     "families": ["woodwind"], "complete": True,
                     "source_kind": "catalog"},
                    reader=READERS.CATALOG, frame="page")
    adjudicate.run(log)
    return log


def _name(log, i):
    v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, i))
    return v, (v.value or {}).get("name") if v.value else None


class TestRecoverWorn(unittest.TestCase):
    def test_the_lexicon_itself_still_does_not_know_oh(self):
        """Nothing is widened: `lookup` is unchanged for every caller."""
        self.assertIsNone(lookup("Oh."))

    def test_gap_in_the_system_is_named(self):
        """The real shape: Fl. / Oh. / Cl. / Fag. -- Oboe is the gap."""
        log = _system(["Fl.", "Oh.", "Cl.", "Fag."])
        v, name = _name(log, 1)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(name, "Oboe")
        self.assertEqual(v.detail["roster_decision"], "recovered_worn")
        # the label row AND the catalog row are in the basis
        self.assertGreaterEqual(len(v.basis), 2)

    def test_gap_already_taken_abstains(self):
        """Positive control above; here a sibling already is the oboe."""
        log = _system(["Fl.", "Oh.", "Ob.", "Fag."])
        v, name = _name(log, 1)
        self.assertIsNone(name)
        self.assertEqual(v.reason, "not_in_lexicon")

    def test_instrument_not_in_roster_is_not_invented(self):
        log = _system(["Fl.", "Oh.", "Cl.", "Fag."],
                      roster_instruments=("Flute", "Clarinet", "Bassoon"))
        v, name = _name(log, 1)
        self.assertIsNone(name)

    def test_no_roster_no_name(self):
        log = _system(["Fl.", "Oh.", "Cl.", "Fag."], roster_instruments=None)
        v, name = _name(log, 1)
        self.assertIsNone(name)

    def test_two_instruments_one_letter_away_abstains(self):
        """`Fug.` is one letter from `Fag.` (bassoon) AND, were `Fg.`'s
        neighbours present, ambiguous strings must refuse. Constructed with a
        token that sits one letter from two roster aliases: `Cl.`/`Ck.`-style
        collisions are checked directly on the rule."""
        roster = _roster(["Oboe", "Flute", "Clarinet", "Bassoon"])
        # `fb.` is one letter from `fl` (flute) and `fg` (bassoon): two
        self.assertIsNone(WR.recover_worn("Fb.", roster, frozenset()))
        # positive control in the same class: `Oh.` has exactly one
        got = WR.recover_worn("Oh.", roster, frozenset())
        self.assertIsNotNone(got)
        self.assertEqual(got.instrument.name, "Oboe")

    def test_long_word_is_not_a_worn_abbreviation(self):
        roster = _roster(["Oboe", "Flute", "Clarinet", "Bassoon"])
        self.assertIsNone(WR.recover_worn("Oboei", roster, frozenset()))  # 1 off `oboen`

    def test_decide_without_the_system_never_uses_it(self):
        """Legacy `contextual.py` calls `decide` with no system names."""
        roster = _roster(["Oboe"])
        d = WR.decide("Oh.", roster)
        self.assertEqual(d.kind, "unchanged")
        self.assertIsNone(d.match)


if __name__ == "__main__":
    unittest.main()
