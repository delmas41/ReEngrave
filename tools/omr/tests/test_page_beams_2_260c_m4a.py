"""ROADMAP 2.260c M4a: the page beam reader (`page_beams`, flag `OMR_PAGE_BEAMS`, default OFF), on SYNTHETIC page strokes of known geometry: a two-stem
beam (role beam, both tips one level, one group), a beam the carved barline column cut in two (one group, counted as crossing; the control: the same
pair 12 px out of line is two groups), a stub on ONE stem (beam_stub, never a beam, no group), a flag (hook), and the position grid against brute force.
Nothing here reads a raster."""
import os
import unittest
from unittest import mock

from tools.omr.staged import page_beams as PB
from tools.omr.staged.beam_strokes import StrokeView

SP = 20.0


def vert(o, x, y0, y1, touches=()):
    return StrokeView(ordinal=o, kind="vertical", box=(x - 1.5, y0, 3.0, y1 - y0), length=(y1 - y0) / SP, thickness=0.15, sagitta=None, angle=90.0,
                      touches=tuple(touches), space_px=SP, ends=(x, y0, x, y1))


def horiz(o, x0, x1, y, thick=0.65, touches=(), y1=None):
    y1 = y if y1 is None else y1
    h = thick * SP
    return StrokeView(ordinal=o, kind="horizontal", box=(x0, min(y, y1) - h / 2, x1 - x0, abs(y1 - y) + h), length=(x1 - x0) / SP, thickness=thick,
                      sagitta=0.0, angle=0.0, touches=tuple(touches), space_px=SP, ends=(x0, y, x1, y1))


def stem_row(v, row):
    return dict(box=v.box, row=row)


def two_stem_beam(dx=0.0, dy=0.0, o0=0):
    a = vert(o0, 100 + dx, 100 + dy, 160 + dy, touches=[(o0 + 2, 1.0)])
    b = vert(o0 + 1, 200 + dx, 100 + dy, 160 + dy, touches=[(o0 + 2, 1.0)])
    beam = horiz(o0 + 2, 100 + dx - 1.5, 200 + dx + 1.5, 106 + dy, touches=[(o0, 1.0), (o0 + 1, 1.0)])
    return [a, b, beam]


class TwoStemBeam(unittest.TestCase):
    def test_a_beam_with_two_stems(self):
        vs = two_stem_beam()
        res = PB.read_page(vs, [stem_row(vs[0], "s0"), stem_row(vs[1], "s1")], SP)
        roles = {b["ordinal"]: b["role"] for b in res["beams"]}
        self.assertEqual(roles[2], "beam")
        self.assertEqual(sorted(res["beams"][0]["stems"]), [0, 1])
        tops = [t for t in res["tips"] if t["end"] == "top"]
        self.assertEqual([len(t["beams"]) for t in tops], [1, 1])
        self.assertTrue(all(t["stem_beamed"] for t in tops))
        self.assertEqual(res["census"]["groups"], 1)
        self.assertEqual(res["census"]["two_bar_reading_errors"], 0)

    def test_the_bottom_end_of_an_up_stem_is_not_a_beam_tip(self):
        vs = two_stem_beam()
        res = PB.read_page(vs, [stem_row(vs[0], "s0")], SP)
        bottom = [t for t in res["tips"] if t["end"] == "bottom"][0]
        self.assertEqual(len(bottom["beams"]), 0)

    def test_a_stub_on_one_stem_is_not_a_beam(self):
        a = vert(0, 100, 100, 160, touches=[(1, 1.0)])
        stub = horiz(1, 98, 112, 106, touches=[(0, 1.0)])         # thick, one stem, 0.7 sp long
        res = PB.read_page([a, stub], [stem_row(a, "s0")], SP)
        self.assertEqual(res["beams"][0]["role"], "beam_stub")
        self.assertEqual(res["census"]["groups"], 0)
        top = [t for t in res["tips"] if t["end"] == "top"][0]
        self.assertEqual(top["beams"], [])
        self.assertEqual(len(top["stubs"]), 1)

    def test_a_thin_short_stroke_on_one_stem_is_a_hook(self):
        a = vert(0, 100, 100, 160, touches=[(1, 1.0)])
        hook = horiz(1, 98, 118, 106, thick=0.3, touches=[(0, 1.0)])
        res = PB.read_page([a, hook], [stem_row(a, "s0")], SP)
        self.assertEqual(res["beams"][0]["role"], "hook")

    def test_a_stem_with_no_stroke_under_it_is_counted_not_guessed(self):
        vs = two_stem_beam()
        res = PB.read_page(vs, [dict(box=(900.0, 100.0, 3.0, 60.0), row="nowhere")], SP)
        self.assertEqual(res["census"]["stem_rows_unmatched"], 1)
        self.assertEqual(res["tips"], [])


class CutByTheBarline(unittest.TestCase):
    """A beam crossing a rule loses the rule's width of ink to the carve: two strokes whose ends meet at the column, on one line."""

    def _two_halves(self, right_dy):
        left = two_stem_beam(0.0, 0.0, 0)                                  # stems at x=100, 200; beam 98.5..201.5
        right = two_stem_beam(150.0, right_dy, 3)                          # stems at 250, 350
        # the beams run to the column from both sides: the left beam's end and the right beam's start sit at x=224/226 around a column at 225
        left[2] = horiz(2, 98.5, 224.0, 106.0, touches=[(0, 1.0), (1, 1.0)])
        right[2] = horiz(5, 226.0, 351.5, 106.0 + right_dy, touches=[(3, 1.0), (4, 1.0)])
        return left + right

    def _columns(self):
        return [dict(system=0, slope=0.0, intercept=225.0, y0=0.0, y1=400.0, width_px=3.0)]

    def test_the_cut_beam_is_a_reading_error_never_one_group(self):
        vs = self._two_halves(0.0)
        stems = [stem_row(v, "s%d" % v.ordinal) for v in vs if v.kind == "vertical"]
        res = PB.read_page(vs, stems, SP, columns=self._columns(), system_of={v.ordinal: 0 for v in vs})
        self.assertEqual(res["census"]["column_cut_pairs"], 1)
        self.assertEqual(res["census"]["groups"], 2)                       # Sean 2026-11-04: every beam is within a bar: one group per bar, never one across
        self.assertEqual(res["census"]["two_bar_reading_errors"], 2)       # ... and the cut pair is counted (the two groups it touches)
        self.assertTrue(all(b["cut_by_column"] for b in res["beams"] if b["role"] == "beam"))
        self.assertEqual(len({b["group"] for b in res["beams"] if b["role"] == "beam"}), 2)

    def test_control_two_beams_out_of_line_are_two_groups(self):
        """The control that can fail: the same two halves, the right one 12 px lower (0.6 sp), do not continue each other: two groups, no error."""
        vs = self._two_halves(12.0)
        stems = [stem_row(v, "s%d" % v.ordinal) for v in vs if v.kind == "vertical"]
        res = PB.read_page(vs, stems, SP, columns=self._columns(), system_of={v.ordinal: 0 for v in vs})
        self.assertEqual(res["census"]["column_cut_pairs"], 0)
        self.assertEqual(res["census"]["groups"], 2)
        self.assertEqual(res["census"]["two_bar_reading_errors"], 0)

    def test_one_whole_beam_over_a_rule_is_the_same_error(self):
        a = vert(0, 100, 100, 160, touches=[(2, 1.0)])
        b = vert(1, 350, 100, 160, touches=[(2, 1.0)])
        beam = horiz(2, 98.5, 351.5, 106.0, touches=[(0, 1.0), (1, 1.0)])
        cols = [dict(system=0, slope=0.0, intercept=225.0, y0=0.0, y1=400.0, width_px=3.0)]
        res = PB.read_page([a, b, beam], [stem_row(a, "a"), stem_row(b, "b")], SP, columns=cols, system_of={0: 0, 1: 0, 2: 0})
        self.assertEqual(res["census"]["groups"], 0)
        self.assertEqual(res["census"]["two_bar_reading_errors"], 1)
        self.assertTrue(res["beams"][0]["two_bars"] and res["beams"][0]["group"] is None)

    def test_a_beam_with_a_rule_far_from_its_ends_does_not_pair(self):
        vs = self._two_halves(0.0)
        stems = [stem_row(v, "s%d" % v.ordinal) for v in vs if v.kind == "vertical"]
        far = [dict(system=0, slope=0.0, intercept=290.0, y0=0.0, y1=400.0, width_px=3.0)]      # a rule 64 px from either end
        res = PB.read_page(vs, stems, SP, columns=far, system_of={v.ordinal: 0 for v in vs})
        self.assertEqual(res["census"]["column_cut_pairs"], 0)


class TheGrid(unittest.TestCase):
    def test_query_equals_brute_force(self):
        import random
        rnd = random.Random(7)
        boxes = [(rnd.uniform(0, 2000), rnd.uniform(0, 1000), rnd.uniform(1, 400), rnd.uniform(1, 60)) for _ in range(300)]
        g = PB.Grid(boxes, 160.0)
        for _ in range(60):
            q = (rnd.uniform(0, 2000), rnd.uniform(0, 1000), rnd.uniform(1, 200), rnd.uniform(1, 200))
            want = [i for i, b in enumerate(boxes) if b[0] <= q[0] + q[2] and b[0] + b[2] >= q[0] and b[1] <= q[1] + q[3] and b[1] + b[3] >= q[1]]
            self.assertEqual(g.query(q), want)


class TheFlag(unittest.TestCase):
    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PB.ENV, None)
            self.assertFalse(PB.enabled())
        with mock.patch.dict(os.environ, {PB.ENV: "1"}):
            self.assertTrue(PB.enabled())
        with mock.patch.dict(os.environ, {PB.ENV: "garbage"}):
            self.assertFalse(PB.enabled())

    def test_off_files_nothing(self):
        class Log:
            def __getattr__(self, n):
                raise AssertionError("the flag is off: the log must not be touched (%s)" % n)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PB.ENV, None)
            self.assertIsNone(PB.gather_page_beams(Log(), None, [], {}, None, None))


if __name__ == "__main__":
    unittest.main()
