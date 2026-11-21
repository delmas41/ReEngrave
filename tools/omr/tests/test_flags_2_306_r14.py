"""ROADMAP 2.306 r14 -- THREE FLAG RULES, default ON (Sean 2026-11-16 approved landing them alone) -- controls built from REAL judged marks (rule 7).

1. (Retired by 2.319: the EXPORT flag exception went with the bar-crop beam grouping; Sean's r14 labels on Brahms p0 are re-pinned on
   the one beam count's ink in `test_one_beam_reader_2_319.py`.)
2. A flag hangs from its own stem's tip to the right: a flag wholly left of a stem is the note before's (Sean's r14 tile 2, "quarter note").
3. A stem carries as many flags as hooks hang from its tip; the detector's class name never adds one (Sean's r14 tile 8, "definitely just an 8th
   note, not a 16th note").
"""

from tools.omr.staged.adjudicators.rhythm import flag_hangs_right_of, flag_levels_by_hooks



def test_tile2_the_flag_of_the_note_before_is_not_this_stems():
    # Sean's r14 tile 2 (Brahms p0 glyph/0/0/9/3/5, his label q1011): "quarter note". The detector's flag box glyph/0/0/9/3/37 (flag8thDown)
    # hangs right of the stem of the note before (glyph/0/0/9/3/2, his tile 1: "an eighth note ... it does have a flag"). Page px, 2026-11-16 gather.
    flag = (3268.06, 5127.99, 3297.73 - 3268.06, 5220.23 - 5127.99)
    assert not flag_hangs_right_of((3322.0, 5000.0, 8.0, 234.0), flag)     # never this stem's
    assert flag_hangs_right_of((3254.0, 5000.0, 6.0, 234.0), flag)         # the note before keeps its own flag


def test_hooks_the_class_never_adds_a_flag():
    # Real readings, 2026-11-16 gathers: the detector's class `flag16thUp` / `flag16thDown` (two levels) against the stem tip's own count of ONE
    # hook. Sean's r14 tile 8 (Litolff p10 glyph/10/0/9/0/2): "definitely just an 8th note". Also Litolff p10 glyph/10/1/9/0/2 and Brahms p0
    # glyph/0/0/11/6/14 (our look: one flag each).
    for counted in (1,):
        assert flag_levels_by_hooks(2, counted) == 1


def test_hooks_never_raise_and_no_count_changes_nothing():
    # The boundary: the tip reader saw no hook or could not count (None) -> today's reading, the class's level. Brahms p4 glyph/4/1/13/8/1 is a real
    # case where the tip counted 2 on an EIGHTH (a slur starting at the tip, our look) with no flag box: the rule never raises a level.
    assert flag_levels_by_hooks(2, None) == 2
    assert flag_levels_by_hooks(1, 2) == 1
    assert flag_levels_by_hooks(2, 2) == 2          # a 16th whose tip shows two hooks stays a 16th
    assert flag_levels_by_hooks(2, 0) == 2          # "no hook" is not a count of hooks: never zero flags from here
