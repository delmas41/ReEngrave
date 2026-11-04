"""ROADMAP 2.262 -- `merge_accidentals` must not scan the exclude boxes for a piece that is nowhere near the accidental box.
On the PAGE map (thousands of pieces, hundreds of accidental boxes, thousands of exclude rects) the old order cost ~1,380 s on Brahms p5."""
import numpy as np

from tools.omr.staged import stroke_map as SM


def _pieces(n):
    return [("blob", np.ones((4, 4), bool), 40 * (i % 50), 40 * (i // 50)) for i in range(n)]


def test_far_pieces_never_reach_the_exclude_scan(monkeypatch):
    calls = []
    real = SM._inside_share

    def counting(m, x0, y0, rects):
        calls.append(len(rects))
        return real(m, x0, y0, rects)
    monkeypatch.setattr(SM, "_inside_share", counting)
    pieces = _pieces(2000)
    exclude = [(5000.0 + 10 * i, 5000.0, 5004.0 + 10 * i, 5004.0) for i in range(500)]
    accs = [((40.0 * 3, 40.0 * 3, 40.0 * 3 + 4, 40.0 * 3 + 4), "accidentalsharp")] * 5
    SM.merge_accidentals(pieces, [], 8.0, accs, exclude, {})
    # only pieces inside an accidental's glyph-sized region may scan the excludes: far fewer than pieces x boxes
    assert len(calls) < 200, len(calls)


def test_result_unchanged_by_the_order():
    pieces = _pieces(60)
    exclude = [(0.0, 0.0, 4.0, 4.0)]
    accs = [((120.0, 80.0, 124.0, 84.0), "accidentalflat")]
    out, joins, parts = SM.merge_accidentals(pieces, [], 8.0, accs, exclude, {})
    assert len(out) == len(pieces) and not parts
