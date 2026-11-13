"""ROADMAP 2.305 round 4 (STAGED EXPORT, page-pass arcs joined across a system break, flag `OMR_PAGE_ARC_WRITE` default OFF): the two halves of one arc stand on
physically CONSECUTIVE systems -- the same page's next system, or the next page's first. Built from the REAL rows of the 2305 Brahms record that held pages 0 and 11
only: page 0's staff 5 right-edge half (run 88, head `glyph/0/0/5/6/12`, its end x 5382) and page 11's staff 5 left-edge half (run 8, head `glyph/11/0/5/0/5`, its end
x 881.7) were adjacent runs of part P6, and a slur was written from page 0 to page 11. Fails on the round-3 tree (that slur is written)."""
import collections
import unittest

from tools.omr.staged import export as E


def _det(key, box, pitch):
    x0, y0, x1, y1 = box
    return {"glyph": key, "category": "notehead", "bbox_page": [x0, y0, x1 - x0, y1 - y0], "pitch": pitch}


A_KEY, A_BOX = "glyph/0/0/5/6/12", [4720, 3624, 4760, 3652]           # page 0, system 0, staff 5 (Sean's P191 note)
B_KEY, B_BOX = "glyph/11/0/5/0/5", [927, 1761, 967, 1795]             # page 11, system 0, staff 5


def _scene(b_key):
    a = _det(A_KEY, A_BOX, "C3")
    b = _det(b_key, B_BOX, "C3")
    measures = [{"detections": [a], "bbox_page_px": [4400, 3500, 5390, 3700]},
                {"detections": [b], "bbox_page_px": [800, 1650, 1300, 1850]}]
    edges = [{"curve": "page_arc/obs:029098", "side": "right", "head": A_KEY, "x_end": 5382.0, "sp": 32.0},
             {"curve": "page_arc/obs:088989", "side": "left", "head": b_key, "x_end": 881.7, "sp": 27.5}]
    counters = collections.Counter()
    slurs, ties = E._across_system_spans(None, [], measures, [1], {}, edges, {A_KEY: 10, b_key: 10}, set(), counters)
    return slurs, ties, counters


class TestHalvesOnConsecutiveSystems(unittest.TestCase):
    def test_page_0_to_page_11_is_not_one_arc(self):
        slurs, ties, counters = _scene(B_KEY)
        self.assertEqual(slurs + ties, [])
        self.assertEqual(counters["arc_across_systems_partner_page_not_in_record"], 1)

    def test_the_same_halves_on_the_next_page_are_joined(self):
        # the twin: the second half on page 1, system 0 (the next page's first system) -- the join stands
        slurs, ties, counters = _scene("glyph/1/0/5/0/5")
        self.assertEqual(len(slurs + ties), 1)
        self.assertEqual(counters["arc_across_systems_partner_page_not_in_record"], 0)


if __name__ == "__main__":
    unittest.main()
