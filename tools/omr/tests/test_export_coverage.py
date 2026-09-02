"""A signal the pipeline reads must survive into the file.

Seven times the defect has been the same: recognised correctly, then dropped on
the way out. Six of the seven were found forensically, after a metric bucket had
grown large enough for someone to open it; the seventh was found by comparing
element counts between the truth and our export, in two greps, before anyone
looked at its bucket.

This is that comparison, kept. The point is the eighth: it should be caught the
day it appears rather than after a day of forensics.
"""
from __future__ import annotations

import pytest

from tools.omr import export_coverage as ec


TRUTH = """<score-partwise>
  <part><measure>
    <note><pitch><step>C</step><octave>4</octave></pitch>
      <type>quarter</type><dot/><accidental>sharp</accidental>
      <beam number="1">begin</beam>
      <notations><slur number="1" type="start"/><fermata type="upright"/></notations>
    </note>
    <barline><bar-style>light-heavy</bar-style></barline>
  </measure></part>
</score-partwise>"""


def _ours(**drop):
    """The same content, with named elements removed."""
    xml = TRUTH
    for name in drop:
        xml = xml.replace(f"<{name}", "<dropped")
    return xml


class TestTheComparison:

    def test_identical_files_have_no_gap(self):
        assert ec.compare(TRUTH, TRUTH) == []

    def test_an_element_we_emit_none_of_is_a_gap(self):
        gaps = ec.compare(TRUTH, _ours(accidental=1))
        assert ("accidental", 1, 0) in gaps

    def test_emitting_FEWER_is_not_a_gap(self):
        """The distinction the whole check rests on.

        Truth 5, ours 3 is a recognition shortfall and belongs to the accuracy
        metric. Truth 5, ours 0 is categorical — nothing consumes it — and that
        is what every one of the seven looked like. Conflating them would make
        this fire on every page and get it deleted.
        """
        truth = "<a><beam>1</beam><beam>2</beam><beam>3</beam></a>"
        ours = "<a><beam>1</beam></a>"
        assert ec.compare(truth, ours) == []

    def test_metadata_and_layout_are_out_of_scope(self):
        """A MusicXML file is mostly not notation, and a check that said so
        would list 55 elements and be ignored."""
        truth = ("<a><midi-program>1</midi-program><tenths>7</tenths>"
                 "<software>x</software><voice>1</voice></a>")
        assert ec.compare(truth, "<a></a>") == []

    def test_an_element_only_we_emit_is_not_a_gap(self):
        assert ec.compare("<a></a>", TRUTH) == []

    def test_every_visible_element_carries_its_reason(self):
        assert all(VISIBLE_reason.strip() for VISIBLE_reason in ec.VISIBLE.values())

    def test_every_known_gap_is_a_visible_element(self):
        """A reason for something the check never looks at is dead text."""
        assert set(ec.KNOWN_GAPS) <= set(ec.VISIBLE)

    def test_every_known_gap_carries_a_reason(self):
        for name, why in ec.KNOWN_GAPS.items():
            assert len(why) > 40, f"{name}'s reason is too thin to act on"


class TestTheRepositoryItself:

    @pytest.fixture(autouse=True)
    def _needs_fixtures(self):
        """⚠️ These three read UNPINNED artifacts — see the module docstring.

        The `.omr.musicxml` files are gitignored output of whatever
        configuration last ran the eval, so a red here can mean the fixtures are
        stale or were written with `--direction-text`, not that the exporter
        regressed. Check what last wrote them before believing the failure.
        """
        if not (ec.FIXTURES / f"{ec.WORKS[0]}.omr.musicxml").is_file():
            pytest.skip("benchmark fixtures not built — run orchestral_eval")

    def test_no_unexplained_export_gap(self):
        """The one that matters. Every element the truth shows and we emit none
        of must be written down in KNOWN_GAPS with a reason — so the list is an
        inventory someone reviewed, and anything new fails here."""
        new = ec.unexplained(ec.survey())
        assert new == [], (
            "a visible element the truth shows is missing from our export and "
            f"is not explained: {new}"
        )

    def test_the_inventory_has_no_stale_entries(self):
        """A gap that has been CLOSED must leave KNOWN_GAPS, or the list stops
        describing the exporter and starts describing its history."""
        still_missing = {name for name, _, _ in ec.survey()}
        stale = sorted(set(ec.KNOWN_GAPS) - still_missing)
        assert stale == [], (
            f"these are emitted now and should come out of KNOWN_GAPS: {stale}"
        )

    def test_the_seven_that_were_fixed_stay_fixed(self):
        """Regression guard for the actual history: each of these was once
        `truth N, ours 0`."""
        missing = {name for name, _, _ in ec.survey()}
        for name in ("accidental", "beam", "dot", "dynamics", "fermata",
                     "slur", "tuplet", "notations", "tied"):
            assert name not in missing, f"<{name}> has stopped being exported"
