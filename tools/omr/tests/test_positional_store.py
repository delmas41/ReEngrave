"""The positional store: what it must keep, and what it must refuse.

⚠️ Each test names the PROPERTY it pins rather than the function it calls,
because this file exists to stop three specific regressions -- a single-field
label, a pooled provenance tier, and a page-pixel position -- each of which
would leave every other test green.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.omr.positional_store import (
    KIND_DETECTOR_CLASS, KIND_OVERLAPS, TIER_OBSERVED, TIER_TRUE, UNKNOWN,
    Entry, EntryStore, Membership, PositionIndex, entries_from_record,
    publisher_label, vbucket,
)
from tools.omr.staged import gather as G
from tools.omr.staged.record import ABSTAIN, Log, Q


def _e(pos, names=(), *, tier=TIER_OBSERVED, pub="litolff", h=None,
       frac=None, edition="ed/a.pdf"):
    ms = tuple(Membership(KIND_DETECTOR_CLASS, n, "detector") for n in names)
    return Entry(tier=tier, publisher=pub, memberships=ms, staff_position=pos,
                 bar_fraction=frac, height_spaces=h, width_spaces=h,
                 edition_path=edition)


class TestMembershipIsASetNeverAField(unittest.TestCase):
    """Sean, on the design that keyed a dot to one name: *"we need to find a
    way to do it that doesn't limit every dot of black from being potentially
    nothing, something, or a part of many things."*"""

    def test_a_piece_of_ink_may_belong_to_NOTHING(self) -> None:
        e = _e(2.0, ())
        self.assertEqual(e.memberships, ())
        self.assertEqual(e.primary, UNKNOWN)
        # ⚠️ AND IT IS STILL STORED AND STILL INDEXED. Unclassified ink is the
        # population this whole layer exists for.
        st = EntryStore()
        st.extend([e])
        idx = PositionIndex(st)
        r = idx.ask(2.0, tier=TIER_OBSERVED)
        self.assertEqual([c["name"] for c in r["candidates"]], [UNKNOWN])

    def test_a_piece_of_ink_may_belong_to_MANY_things(self) -> None:
        e = _e(2.0, ("noteheadBlack", "slur", "ledgerLine"))
        self.assertEqual(len(e.memberships), 3)
        idx = PositionIndex(EntryStore())
        st = EntryStore()
        st.extend([e])
        idx = PositionIndex(st)
        names = {c["name"] for c in idx.ask(2.0, tier=TIER_OBSERVED)["candidates"]}
        self.assertEqual(names, {"noteheadBlack", "slur", "ledgerLine"})

    def test_an_entry_with_several_memberships_is_indexed_under_EACH(self) -> None:
        # ⚠️ So counts across names sum to MORE than the entry count, which is
        # the honest shape for many-to-many. Collapsing to one name here would
        # reintroduce the single-label flattening one layer down.
        st = EntryStore()
        st.extend([_e(2.0, ("a", "b"))])
        idx = PositionIndex(st)
        self.assertEqual(idx.entries_indexed, 1)
        self.assertEqual(
            sum(c["count"] for c in idx.ask(2.0, tier=TIER_OBSERVED)["candidates"]), 2)

    def test_ink_explained_by_becomes_SEVERAL_memberships(self) -> None:
        """`Q.INK`'s `ink_explained_by` is already many-to-many on the record
        and nothing reads it; flattening it on the way in would destroy it."""
        rec = {"observations": [
            {"subject": "staff/0/0/0", "quantity": "staff_lines",
             "value": [100, 110, 120, 130, 140], "detail": {}},
            {"subject": "glyph/0/0/0/0/900", "quantity": "ink", "value": "ink",
             "detail": {"y_center_page": 110.0, "x_center_page": 50.0,
                        "ink_explained_by": ["noteheadBlackOnLine", "slur"],
                        "ink_detector_coverage": 0.4,
                        "width_spaces": 1.0, "height_spaces": 1.0}},
        ]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            p.write_text(json.dumps({"record": rec}, indent=2))
            got = list(entries_from_record(p, publisher="x"))
        self.assertEqual(len(got), 1)
        self.assertEqual({m.name for m in got[0].memberships},
                         {"noteheadBlackOnLine", "slur"})
        self.assertTrue(all(m.kind == KIND_OVERLAPS for m in got[0].memberships))


class TestProvenanceTiersAreNeverPooledByDefault(unittest.TestCase):
    """A store populated from our own readings and then used to identify new
    ink is learning from its own output -- the `source_kind` hazard."""

    def setUp(self) -> None:
        st = EntryStore()
        st.extend([_e(2.0, ("x",)), _e(2.0, ("y",), tier=TIER_TRUE)])
        self.idx = PositionIndex(st)

    def test_ask_REFUSES_without_a_tier(self) -> None:
        with self.assertRaises(ValueError):
            self.idx.ask(2.0, tier=None)

    def test_a_tier_query_sees_only_its_own_tier(self) -> None:
        self.assertEqual(
            [c["name"] for c in self.idx.ask(2.0, tier=TIER_OBSERVED)["candidates"]],
            ["x"])
        self.assertEqual(
            [c["name"] for c in self.idx.ask(2.0, tier=TIER_TRUE)["candidates"]],
            ["y"])

    def test_pooling_is_possible_but_must_be_SAID(self) -> None:
        r = self.idx.ask(2.0, tier=None, require_tier=False)
        self.assertEqual({c["name"] for c in r["candidates"]}, {"x", "y"})

    def test_an_unknown_tier_is_REFUSED_at_the_door(self) -> None:
        st = EntryStore()
        with self.assertRaises(ValueError):
            st.extend([_e(2.0, ("x",), tier="guessed")])


class TestThePositionComposesAcrossDocuments(unittest.TestCase):
    """A `bbox_page_px` is a fact about one page at one dpi and pools with
    nothing.  The store is only worth building if its key survives that."""

    def _record(self, top, spacing, y_of_mark):
        lines = [top + i * spacing for i in range(5)]
        return {"observations": [
            {"subject": "staff/0/0/0", "quantity": "staff_lines",
             "value": lines, "detail": {}},
            {"subject": "glyph/0/0/0/0/0", "quantity": "glyph_box",
             "value": ["restWhole", 0, 0, 1, 1], "score": 0.9,
             "detail": {"y_center_page": y_of_mark, "x_center_page": 10.0,
                        "bbox_page_px": [0.0, 0.0, spacing, spacing]}},
        ]}

    def test_the_SAME_music_at_two_dpi_gives_the_SAME_position(self) -> None:
        # One page at 300 dpi and the same page at 600: every pixel doubles.
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.json"
            b = Path(d) / "b.json"
            a.write_text(json.dumps(
                {"record": self._record(100.0, 10.0, 120.0)}, indent=2))
            b.write_text(json.dumps(
                {"record": self._record(200.0, 20.0, 240.0)}, indent=2))
            pa = list(entries_from_record(a, publisher="p"))[0]
            pb = list(entries_from_record(b, publisher="p"))[0]
        self.assertAlmostEqual(pa.staff_position, 4.0)
        self.assertAlmostEqual(pb.staff_position, 4.0)
        # ⚠️ AND THE SHAPE COMPOSES TOO, for the same reason: it is measured
        # in the staff's own spaces, not in pixels.  BOTH AXES are asserted --
        # a mutation battery caught this file asserting only the height while
        # the width silently reverted to pixels, which is the same fault as a
        # page-pixel position one field over.
        self.assertAlmostEqual(pa.height_spaces, pb.height_spaces)
        self.assertAlmostEqual(pa.width_spaces, pb.width_spaces)
        self.assertAlmostEqual(pa.width_spaces, 1.0)

    def test_a_staff_with_no_span_DECLINES_rather_than_defaulting(self) -> None:
        """A one-line percussion staff has no origin and no spacing.  A
        fabricated number in the one field the store is keyed on is worse than
        no entry."""
        rec = {"observations": [
            {"subject": "staff/0/0/0", "quantity": "staff_lines",
             "value": [100.0], "detail": {}},
            {"subject": "glyph/0/0/0/0/0", "quantity": "glyph_box",
             "value": ["restWhole", 0, 0, 1, 1], "score": 0.9,
             "detail": {"y_center_page": 120.0, "x_center_page": 10.0}},
        ]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            p.write_text(json.dumps({"record": rec}, indent=2))
            got = list(entries_from_record(p, publisher="p"))
        self.assertIsNone(got[0].staff_position)

    def test_an_unpositioned_entry_is_COUNTED_never_dropped(self) -> None:
        st = EntryStore()
        st.extend([_e(None, ("x",)), _e(2.0, ("x",))])
        self.assertEqual(st.summary()["entries"], 2)
        self.assertEqual(st.summary()["unpositioned"], 1)
        self.assertEqual(PositionIndex(st).unpositioned, 1)


class TestTheIndexIsADerivedView(unittest.TestCase):
    """Bucket size must not be a decision taken at storage time."""

    def test_rebuilding_at_another_resolution_changes_NOTHING_stored(self) -> None:
        st = EntryStore()
        st.extend([_e(p / 10.0, ("x",)) for p in range(0, 80)])
        before = [e.staff_position for e in st.entries]
        coarse = PositionIndex(st, vbucket_spaces=4.0)
        fine = PositionIndex(st, vbucket_spaces=0.05)
        self.assertEqual(before, [e.staff_position for e in st.entries])
        self.assertLess(coarse.summary()["buckets"], fine.summary()["buckets"])

    def test_every_cell_keeps_row_indices_back_into_the_store(self) -> None:
        # ⚠️ This is what keeps the view a VIEW: any number in it can be
        # traced to the ink that made it, so no aggregate is the only copy.
        st = EntryStore()
        st.extend([_e(2.0, ("x",)), _e(2.0, ("x",))])
        idx = PositionIndex(st)
        cell = list(idx._c[(TIER_OBSERVED, "litolff", "x")].values())[0]
        self.assertEqual(sorted(cell.rows), [0, 1])

    def test_the_store_round_trips_through_JSONL(self) -> None:
        st = EntryStore()
        st.extend([_e(2.0, ("x", "y"), h=0.5, frac=0.25), _e(None, ())])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            st.write(p)
            back = EntryStore.read(p)
        self.assertEqual(back.summary()["entries"], 2)
        self.assertEqual({m.name for m in back.entries[0].memberships},
                         {"x", "y"})
        self.assertEqual(back.entries[1].memberships, ())
        self.assertIsNone(back.entries[1].staff_position)

    def test_a_query_MERGES_across_the_unconstrained_axis(self) -> None:
        """⚠️ A REAL DEFECT, found by running the demo rather than by review:
        cells are keyed `(vbucket, hbucket)`, so a query naming no
        `bar_fraction` matched every horizontal bucket and returned ONE NAME
        AS NINE ROWS, each with its share nine times too small."""
        st = EntryStore()
        st.extend([_e(2.0, ("restWhole",), frac=f) for f in (0.1, 0.5, 0.9)])
        idx = PositionIndex(st)
        r = idx.ask(2.0, tier=TIER_OBSERVED)
        self.assertEqual(len(r["candidates"]), 1)
        self.assertEqual(r["candidates"][0]["count"], 3)
        self.assertAlmostEqual(r["candidates"][0]["share_of_this_position"], 1.0)
        # ⚠️ and naming the axis still narrows to one of them
        self.assertEqual(
            idx.ask(2.0, tier=TIER_OBSERVED, bar_fraction=0.5)
            ["candidates"][0]["count"], 1)

    def test_an_entry_with_NO_bar_fraction_survives_a_bar_fraction_query(self) -> None:
        """⚠️ AN ENTRY CANNOT BE EXCLUDED ON AN AXIS IT HAS NO VALUE FOR.

        A mark whose cell box was never read has `bar_fraction=None`, and a
        query naming a bar fraction must still return it -- that is the
        ABSENT/DECLINED distinction, in the query.  A mutation battery found
        this untested: the fixture above gives every entry a bar fraction, so
        the branch that handles a MISSING one was unreachable and dropping it
        changed nothing.
        """
        st = EntryStore()
        st.extend([_e(2.0, ("restWhole",)),                 # no bar_fraction
                   _e(2.0, ("noteheadBlack",), frac=0.5)])
        idx = PositionIndex(st)
        got = {c["name"]: c["count"]
               for c in idx.ask(2.0, tier=TIER_OBSERVED,
                                bar_fraction=0.5)["candidates"]}
        self.assertEqual(got, {"restWhole": 1, "noteheadBlack": 1})
        # ⚠️ and one that genuinely sits elsewhere in the bar IS excluded, so
        # the clause above is not simply ignoring the constraint.
        st2 = EntryStore()
        st2.extend([_e(2.0, ("elsewhere",), frac=0.05)])
        self.assertEqual(
            PositionIndex(st2).ask(2.0, tier=TIER_OBSERVED,
                                   bar_fraction=0.95)["candidates"], [])


class TestPublisherReachesGather(unittest.TestCase):
    """The conditioning variable had no producer: `grep publisher
    tools/omr/staged/gather.py` returned one comment."""

    def setUp(self) -> None:
        self._old = os.environ.get(G.DOCUMENT_IDENTITY_ENV)

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop(G.DOCUMENT_IDENTITY_ENV, None)
        else:
            os.environ[G.DOCUMENT_IDENTITY_ENV] = self._old

    def test_the_flag_is_default_OFF_and_an_ALLOW_list(self) -> None:
        # ⚠️ CLAUDE.md's "A flag's OFF test must follow its DEFAULT": a
        # default-OFF mechanism must be an allow-list, so a typo leaves it OFF.
        for word, on in (("1", True), ("true", True), ("on", True),
                         ("0", False), ("", False), ("yess", False),
                         ("ON!", False)):
            os.environ[G.DOCUMENT_IDENTITY_ENV] = word
            self.assertEqual(G._document_identity_enabled(), on, word)
        os.environ.pop(G.DOCUMENT_IDENTITY_ENV, None)
        self.assertFalse(G._document_identity_enabled())

    def test_flag_OFF_writes_NOTHING_AT_ALL(self) -> None:
        # ⚠️ Not an abstention: a record from a tree carrying this rung must be
        # byte-identical to one from a tree without it, or the rung perturbs
        # every A/B in the repo by existing.
        os.environ[G.DOCUMENT_IDENTITY_ENV] = "0"
        log = Log()
        G.gather_document_identity(log, "anything.pdf")
        self.assertEqual(len(log._obs) + len(log._abs), 0)

    def test_an_unknown_pdf_ABSTAINS_and_does_not_default(self) -> None:
        os.environ[G.DOCUMENT_IDENTITY_ENV] = "1"
        log = Log()
        G.gather_document_identity(log, "/nowhere/not-a-held-edition.pdf")
        self.assertEqual(len(log._obs), 0)
        reasons = [a.reason for a in log._abs.values()]
        self.assertEqual(reasons, [ABSTAIN.NOT_IN_CATALOG])

    def test_no_pdf_path_is_a_DIFFERENT_abstention(self) -> None:
        # ⚠️ "we declined to look" and "the catalog does not hold it" have
        # different repairs (flip the flag; or name the work with
        # OMR_WORK_ID), so they must not fold into one number.
        os.environ[G.DOCUMENT_IDENTITY_ENV] = "1"
        log = Log()
        G.gather_document_identity(log, None)
        self.assertEqual([a.reason for a in log._abs.values()],
                         [ABSTAIN.OUT_OF_SCOPE])

    def test_the_identity_carries_source_kind_catalog(self) -> None:
        """⚠️ THE LOAD-BEARING FIELD.  A publisher read off the PLATE would be
        an OMR output of the same raster and would fall silent exactly when
        the raster is bad; this one comes from IMSLP's work page."""
        os.environ[G.DOCUMENT_IDENTITY_ENV] = "1"
        log = Log()
        G.gather_document_identity(
            log, "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
                 "imslp984073.pdf")
        rows = [o for o in log._obs.values()
                if o.quantity == Q.DOCUMENT_IDENTITY]
        if not rows:
            self.skipTest("catalog.json not readable in this checkout")
        self.assertEqual(rows[0].detail.get("source_kind"), "catalog")
        self.assertIn("Litolff", rows[0].detail.get("publisher") or "")

    def test_it_files_ONCE_per_document_not_once_per_page(self) -> None:
        """⚠️ `gather()` calls this once per PAGE, and the identity is a fact
        about the DOCUMENT.

        Measured before the guard existed: a four-page run filed FOUR identical
        rows on the one DOCUMENT subject, so a consumer counting rows would
        over-count the plate fourfold. The guard is inside the function rather
        than at the call site so it holds wherever it is called from — and it
        demonstrably CAN fire, which is what this repo requires of an
        idempotence guard, having once deleted one whose rule could not.
        """
        os.environ[G.DOCUMENT_IDENTITY_ENV] = "1"
        log = Log()
        for _page in range(4):
            G.gather_document_identity(log, "/nowhere/not-held.pdf")
        self.assertEqual(len(log._obs) + len(log._abs), 1)

    def test_a_publisher_key_collapses_plates_of_one_house(self) -> None:
        self.assertEqual(
            publisher_label("Henry Litolff's Verlag, Braunschweig, 1870, "
                            "plate 2769"), "litolff")
        self.assertEqual(
            publisher_label("Breitkopf & Härtel (Brahms Sämtliche Werke)"),
            "breitkopf")
        self.assertEqual(publisher_label(None), "unknown")


class TestTheBucketArithmetic(unittest.TestCase):
    def test_width_is_in_SPACES_and_position_in_STEPS(self) -> None:
        # ⚠️ One space is two steps. The criterion was pre-registered in
        # spaces and the record's unit is the step; a second spelling of this
        # conversion is how the two drift.
        self.assertEqual(vbucket(0.0, 0.5), 0)
        self.assertEqual(vbucket(0.99, 0.5), 0)
        self.assertEqual(vbucket(1.0, 0.5), 1)
        self.assertEqual(vbucket(-0.1, 0.5), -1)


if __name__ == "__main__":
    unittest.main()
