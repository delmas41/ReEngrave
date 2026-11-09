"""ROADMAP 2.271 step 3 (`OMR_ARC_ACROSS_SYSTEMS`, default OFF): an arc that runs off one system and picks up on the next is joined in EXPORT from the
binder's own edge curves, on evidence only. Synthetic runs: no library, no weights."""
import collections
import os
import unittest

from tools.omr.staged import arc_claim, export as E

SP = 16.0


def _note(key, x, pitch):
    return {"category": "notehead", "glyph": key, "bbox_page": [x - 10, 100, 20, 16], "pitch": pitch}


def _run(first_key, last_key, pitch):
    """Two bars: bar 0 holds a note near the left, bar 1 a note near the right edge of the system (page x 2000 .. 2400)."""
    return [{"bbox_page_px": [300, 80, 1200, 240], "detections": [_note(first_key, 700, pitch)]},
            {"bbox_page_px": [1200, 80, 2400, 240], "detections": [_note(last_key, 2200, pitch)]}]


def _edge(curve, side, head, x_end):
    return {"curve": curve, "side": side, "head": head, "x_end": x_end, "sp": SP, "page": 0, "system": 0, "home": None, "pieces": 1, "trace_box": None}


class AcrossSystems(unittest.TestCase):
    def _call(self, edges, measures, positions=None, voice_of=None):
        counters = collections.Counter()
        out = E._across_system_spans(None, [], measures, frozenset([2]), voice_of or {}, edges, positions or {}, set(), counters)
        return out, counters

    def _measures(self, pa="G4", pb="G4"):
        # run 0 = bars 0-1 (last note g/0/1), run 1 = bars 2-3 (first note g/1/0)
        a = _run("g/0/0", "g/0/1", pa)
        b = _run("g/1/0", "g/1/1", pb)
        # the first run's LAST note is the arc's start; the second run's FIRST note is its stop; drop the other notes so they are adjacent
        a[0]["detections"] = []
        b[1]["detections"] = []
        return a + b

    def test_flag_default_off(self):
        os.environ.pop(arc_claim.ENV_ACROSS_SYSTEMS, None)
        self.assertFalse(arc_claim.across_systems_enabled())

    def test_same_pitch_adjacent_is_a_tie(self):
        edges = [_edge("c1", "right", "g/0/1", 2390.0), _edge("c2", "left", "g/1/0", 650.0)]
        (slurs, ties), c = self._call(edges, self._measures(), positions={"g/0/1": 3, "g/1/0": 3})
        self.assertEqual((len(slurs), len(ties)), (0, 1))
        self.assertEqual(c["tie_spans_across_systems"], 1)

    def test_different_pitch_is_a_slur(self):
        edges = [_edge("c1", "right", "g/0/1", 2390.0), _edge("c2", "left", "g/1/0", 650.0)]
        (slurs, ties), _ = self._call(edges, self._measures("G4", "A4"), positions={"g/0/1": 3, "g/1/0": 4})
        self.assertEqual((len(slurs), len(ties)), (1, 0))

    def test_same_pitch_but_positions_differ_is_a_slur(self):
        edges = [_edge("c1", "right", "g/0/1", 2390.0), _edge("c2", "left", "g/1/0", 650.0)]
        (slurs, ties), _ = self._call(edges, self._measures(), positions={"g/0/1": 3, "g/1/0": 5})
        self.assertEqual((len(slurs), len(ties)), (1, 0))

    def test_two_candidates_is_not_written(self):
        edges = [_edge("c1", "right", "g/0/1", 2390.0), _edge("c2", "left", "g/1/0", 650.0), _edge("c3", "left", "g/1/0", 655.0)]
        (slurs, ties), c = self._call(edges, self._measures(), positions={"g/0/1": 3, "g/1/0": 3})
        self.assertEqual((len(slurs), len(ties)), (0, 0))
        self.assertEqual(c["arc_across_systems_ambiguous"], 1)

    def test_an_end_inside_its_run_is_not_joined(self):
        edges = [_edge("c1", "right", "g/0/1", 1500.0), _edge("c2", "left", "g/1/0", 650.0)]      # trace ends 900 px (56 sp) before the system's edge
        (slurs, ties), c = self._call(edges, self._measures(), positions={"g/0/1": 3, "g/1/0": 3})
        self.assertEqual((len(slurs), len(ties)), (0, 0))
        self.assertEqual(c["arc_across_systems_end_inside_its_run"], 1)

    def test_no_pickup_is_counted(self):
        edges = [_edge("c1", "right", "g/0/1", 2390.0)]
        (slurs, ties), c = self._call(edges, self._measures())
        self.assertEqual((len(slurs), len(ties)), (0, 0))
        self.assertEqual(c["arc_across_systems_no_pickup"], 1)

    def test_a_later_note_in_the_first_run_makes_it_a_slur(self):
        m = self._measures()
        m[1]["detections"].append(_note("g/0/extra", 2300, "G4"))        # a note follows the arc's start in its own run
        edges = [_edge("c1", "right", "g/0/1", 2390.0), _edge("c2", "left", "g/1/0", 650.0)]
        (slurs, ties), _ = self._call(edges, m, positions={"g/0/1": 3, "g/1/0": 3})
        self.assertEqual((len(slurs), len(ties)), (1, 0))


if __name__ == "__main__":
    unittest.main()
