"""ROADMAP 2.122 + 2.123 -- the exporter's ledger balances, and a bar is
named by where it stands, not by the number printed on it.

2.122: on Brahms 1 (20261013-night) the record refuses 3,407 boxes as
`too_narrow`; the exporter's not-written ledger counted 3,315. The other 92
were 2.80b's boxes read on their own ink as an eighth rest: WRITTEN (as
rests), so in no ledger. A refused box is now either dropped (counted by its
reason) or reinstated (counted in `refusals_reinstated`), exactly once.

2.123: Brahms prints bars 189-190 twice (1st/2nd endings). Every bar list is
named by `bar_key` (page/system/cell, CLAUDE.md §5) and `ordinal` (place in
the part's file), with the printed number only a label; the bars we read
nothing in, which had a count and no list, now have one.

Each `*_RED` test fails on the tree without the change (the key does not
exist there).
"""
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import (
    QUARTER, _obs, _one_staff_page, _vrd)
from tools.omr.tests.test_staged_repeats_endings import _page_with
from tools.omr.tests.test_staged_bar_sum_holdout import _bar

EIGHTH_REST = {"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 0,
               "is_rest": True, "reinstated_rest": True}


def _narrow_box(page, gi, *, reinstated):
    """A `noteheadBlack` box ADJUDICATE refused `too_narrow`; `reinstated`
    adds 2.80b's eighth-rest reading and EVALUATE's length."""
    sub = f"glyph/0/0/0/0/{gi}"
    o, v = page["record"]["observations"], page["record"]["verdicts"]
    o.append(_obs(500 + gi, sub, Q.GLYPH_BOX,
                  ["noteheadBlackOnLine", 100 * gi, 50, 12, 40],
                  category="notehead"))
    o.append(_obs(520 + gi, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
    v.append(_vrd(540 + gi, sub, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, True,
                  reason="too_narrow"))
    if reinstated:
        v.append(_vrd(560 + gi, sub, Q.NOTEHEAD_IS_AN_EIGHTH_REST, True,
                      reason="rest8th_shape"))
        v.append(_vrd(580 + gi, sub, Q.DURATION, EIGHTH_REST))
    return page


class TestATooNarrowRefusalIsCountedExactlyOnce(unittest.TestCase):

    def _page(self):
        page = _one_staff_page(notes=[("C4", QUARTER)], n_measures=1)
        _narrow_box(page, 1, reinstated=False)      # dropped
        _narrow_box(page, 2, reinstated=True)       # reinstated as a rest
        _narrow_box(page, 3, reinstated=True)
        return page

    def test_the_dropped_box_is_in_the_ledger(self):
        _xml, rep = SX.to_musicxml(self._page())
        self.assertEqual(
            rep["notes_not_written"]["not_a_notehead:too_narrow"], 1)

    def test_the_reinstated_boxes_are_in_the_ledger_too_RED(self):
        _xml, rep = SX.to_musicxml(self._page())
        r = rep["part_join"]["refusals_reinstated"]
        self.assertEqual(r["refused_then_read_as_rest"],
                         {"not_a_notehead:too_narrow": 2})
        self.assertEqual(r["placed_as_rest"],
                         {"not_a_notehead:too_narrow": 2})
        self.assertEqual(r["dropped_after"], {})

    def test_the_record_refusals_equal_dropped_plus_reinstated_RED(self):
        page = self._page()
        refused = sum(1 for v in page["record"]["verdicts"]
                      if v["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD
                      and v["value"] is True and v["reason"] == "too_narrow")
        _xml, rep = SX.to_musicxml(page)
        r = rep["part_join"]["refusals_reinstated"]
        dropped = rep["notes_not_written"]["not_a_notehead:too_narrow"]
        self.assertEqual(refused, 3)
        self.assertEqual(
            refused, dropped
            + r["refused_then_read_as_rest"]["not_a_notehead:too_narrow"])

    def test_a_reinstated_rest_is_in_the_file_as_a_rest(self):
        xml, _rep = SX.to_musicxml(self._page())
        self.assertGreaterEqual(len(ET.fromstring(xml).findall(".//rest")), 2)

    def test_CONTROL_with_no_narrow_box_the_ledger_line_is_empty_RED(self):
        _xml, rep = SX.to_musicxml(
            _one_staff_page(notes=[("C4", QUARTER)], n_measures=1))
        r = rep["part_join"]["refusals_reinstated"]
        self.assertEqual(r["total"], 0)
        self.assertNotIn("not_a_notehead:too_narrow",
                         rep["notes_not_written"])


def _measure_ordinals(xml):
    """Per part, the file's own `<measure>` sequence: (ordinal, number)."""
    return {part.get("id"): [(k, m.get("number")) for k, m in
                             enumerate(part.findall("measure"), start=1)]
            for part in ET.fromstring(xml).findall("part")}


class TestTwoBarsWithOnePrintedNumberAreTwoEntries(unittest.TestCase):

    def test_the_numbers_do_repeat_in_the_fixture(self):
        xml, _ = SX.to_musicxml(_page_with())
        nums = [n for _k, n in _measure_ordinals(xml)["P1"]]
        self.assertEqual(nums, ["1", "2", "3", "2", "3", "4"])

    def test_the_unread_empty_bars_are_listed_one_per_bar_RED(self):
        _xml, rep = SX.to_musicxml(_page_with())
        lst = rep["unread_empty_bars"]["list"]
        self.assertEqual(len(lst), 6)
        self.assertEqual(len({(b["part"], b["bar_key"]) for b in lst}), 6)
        self.assertEqual(len({b["ordinal"] for b in lst}), 6)
        # the printed number is only a label, and it repeats
        self.assertEqual([b["measure"] for b in lst], [1, 2, 3, 2, 3, 4])
        self.assertEqual([b["bar_key"] for b in lst],
                         ["0/0/%d" % i for i in range(6)])

    def test_every_listed_bar_is_the_file_bar_at_its_ordinal_RED(self):
        xml, rep = SX.to_musicxml(_page_with())
        file_bars = dict(_measure_ordinals(xml)["P1"])
        for b in rep["unread_empty_bars"]["list"]:
            self.assertEqual(file_bars[b["ordinal"]], str(b["measure"]))

    def test_the_unread_empty_count_equals_the_files_RED(self):
        xml, rep = SX.to_musicxml(_page_with())
        in_file = sum(
            1 for m in ET.fromstring(xml).iter("measure")
            if any((w.text or "").strip() == "unread"
                   for w in m.iter("words")))
        self.assertEqual(rep["unread_bar_marks"]["unread"], in_file)
        self.assertEqual(rep["unread_empty_bars"]["bars"], in_file)

    def test_a_held_out_bar_carries_the_same_key_RED(self):
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]))
        h = rep["bars_held_out_sum"]["held"]
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["bar_key"], "0/0/0")
        self.assertEqual(h[0]["ordinal"], 1)


if __name__ == "__main__":
    unittest.main()
