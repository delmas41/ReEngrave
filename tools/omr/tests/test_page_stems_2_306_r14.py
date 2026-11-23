"""ROADMAP 2.306 r14 (flag `OMR_PAGE_STEMS`, default OFF) -- controls built from REAL judged marks (CLAUDE rule 7).

1. A note whose stem carries a flag is written flagged, never beamed (Sean 2026-10-22, page-facts "Beam, flag, slash": "if there is a flag it
   should be treated as a flag"). Fixture `fixtures/page_stems_2_306_r14_flags.json`: the beam-grouping input EXPORT builds on Brahms p0 (cut by
   `benchmarks/page-ledger-2026-11/2306/r14_cut_fixture.py` from a gather of today's branch). Sean's hand labels (data/hand-truth/pages/
   imslp317803/0.json, swept cells) put a FLAG on q264 / q266 / q272 (glyph/0/0/1/6/2, /4, /12: a slur over them was filed as a cell beam
   stroke) and q1178 / q1180 (glyph/0/0/10/2/5, /7), and BEAMS on q67-q75 (cell/0/0/0/3). The old grouping beams the flagged ones (the
   control fails there first); the rule keeps them flagged and groups the beamed bar exactly as before (the never).
2. An accidental's strokes end where the accidental ends: a vertical running out of the detector's accidental box is a stem, never held by it.
"""
from types import SimpleNamespace

from tools.omr.staged import page_stems as PS

# Part 1 (a flagged note is never regrouped under a stroke across its x: `export.flagged_outside_a_joined_beam`,
# `_value_from_its_own_flag`, `beam_stream_keeping_flags`) was retired on main by ROADMAP 2.319 step 2 (b784d3392: beam groups
# written from the one beam count's strokes; the flagged-note exception and the bar-crop grouping retired). Its four tests and
# their fixture were removed when batch 4 merged this file onto that main; parts 2 and 3 stand.


def test_r14_a_stem_running_out_of_the_accidental_box_is_not_held():
    # REAL marks, Brahms p0 (gather of 2026-11-16, page map stroke 1371; NOT judged by Sean -- the cell s0-st12-m1 is not swept; our look: an
    # eighth whose down stem and flag the detector boxed as `accidentalFlat` 0.35, glyph/0/0/12/1/13). The stem runs out of the box at both ends.
    acc = (2333.76, 6417.28, 2374.08, 6513.92)
    stem = SimpleNamespace(kind="vertical", box=(2334.0, 6394.0, 6.0, 136.0))
    assert PS.stem_runs_out_of_the_accidental(stem, acc, 32.0)
    # the never: a vertical lying inside the box (a flat's own upright) stays the accidental's; a curve is never freed
    assert not PS.stem_runs_out_of_the_accidental(SimpleNamespace(kind="vertical", box=(2336.0, 6420.0, 6.0, 90.0)), acc, 32.0)
    assert not PS.stem_runs_out_of_the_accidental(SimpleNamespace(kind="curve", box=(2334.0, 6394.0, 30.0, 136.0)), acc, 32.0)


def test_r14_tile2_the_flag_of_the_note_before_is_not_this_stems():
    # Sean's r14 tile 2 (Brahms p0 glyph/0/0/9/3/5, his label q1011): "quarter note, the entire stem". The detector's flag box glyph/0/0/9/3/37
    # (flag8thDown) hangs right of the stem of the note before (glyph/0/0/9/3/2, his tile 1: "an eighth note ... it does have a flag") and stops
    # short of this note's stem. Page px from the gather of 2026-11-16 (page stems' stem boxes, the detector's flag box).
    from tools.omr.staged.adjudicators.rhythm import flag_hangs_right_of
    flag = (3268.06, 5127.99, 3297.73 - 3268.06, 5220.23 - 5127.99)
    tile2_stem = (3322.0, 5000.0, 8.0, 234.0)
    tile1_stem = (3254.0, 5000.0, 6.0, 234.0)
    assert not flag_hangs_right_of(tile2_stem, flag)      # a flag wholly left of the stem is never this stem's
    assert flag_hangs_right_of(tile1_stem, flag)          # the never: the note before keeps its own flag
