"""ROADMAP 2.360 -- the ranking counts only real losses. COUNTING only (tools/omr/staged/counted_marks.py); no reader, adjudicator or exporter behaviour.

Every fixture row is a REAL row of the 20261123-night record (Brahms, Breitkopf) or of its exporter fates, copied by value; no library/, no weights, no PDF.
Each test shows the OLD count and the NEW count for a handful of real cases, and a real loss that must STILL count."""
from tools.omr.staged import counted_marks as CM

# ---- (b) too-narrow / clipped boxes: real heads of the night record (page, box, exporter fate)
H_WRITTEN_DOTTED = ("glyph/0/0/6/1/11", 0, [2192.96, 3957.92, 2231.68, 3990.88], "written")           # a written dotted note
H_DOT = ("glyph/0/0/6/1/18", 0, [2281.92, 3966.56, 2296.64, 3980.32], "not_a_notehead:too_narrow")      # Sean's hand page 0: labelled a notehead AND an augmentationDot (q751/q752)
H_REST = ("glyph/4/0/0/2/7", 4, [1746.51, 562.47, 1766.49, 582.1725], "not_a_notehead:too_narrow")     # sits on an eighth rest the file writes
H_NOTHING = ("glyph/0/0/4/6/0", 0, [4731.4375, 3153.125, 4753.78125, 3174.78125], "not_a_notehead:too_narrow")   # no dot, no rest the record knows: stays a candidate
H_VALUE = ("glyph/0/0/10/1/0", 0, [2601.2799999999997, 5517.68, 2642.24, 5554.48], "duration_narrowed")   # a real head the value was not read for
DOT_19 = (0, [2281.92, 3965.6, 2296.32, 3980.0])        # the augmentationDot box glyph/0/0/6/1/19 (obs:018861), used by the duration of glyph/0/0/6/1/11
REST_8TH = (4, [1747.065, 564.69, 1782.03, 617.415])    # the rest8th box glyph/4/0/0/2/10 the file writes as a rest


def _heads():
    return {k: {"page": p, "box": b, "fate": f} for k, p, b, f in (H_WRITTEN_DOTTED, H_DOT, H_REST, H_NOTHING, H_VALUE)}


def test_too_narrow_old_and_new_counts_real_cases():
    heads, written = _heads(), [H_WRITTEN_DOTTED[0]]
    old = CM.note_census(heads, written)
    new = CM.note_census(heads, written, dot_boxes=[DOT_19], rest_boxes=[REST_8TH])
    # OLD: all four unwritten boxes are candidate-lost notes (three too_narrow, one undecided value)
    assert old["notes"]["candidate_lost"] == 4
    assert old["notes"]["candidate_lost_by_cause"]["too_narrow"] == 3
    # NEW: the dot of a written dotted note and the rest the file writes are named apart as ink that is not a note ...
    assert new["notes"]["candidate_lost"] == 2
    assert new["boxes"]["non_note_ink_by_kind"] == {"dot_of_a_written_note": 1, "rest_the_file_writes": 1}
    # ... and the real losses still count: the too-narrow box nothing explains, and the head whose value was not read
    assert new["notes"]["candidate_lost_by_cause"]["too_narrow"] == 1
    assert new["notes"]["candidate_lost_by_cause"]["value_undecided"] == 1
    assert new["identity"]["ok"] and old["identity"]["ok"]
    assert new["notes"]["written"] == old["notes"]["written"] == 1


def test_a_value_undecided_head_is_never_moved_by_a_dot_or_rest_box():
    """The split is for the two mixed refusals only: a head on the dot's ink whose fate is another refusal keeps its fate."""
    heads = {"glyph/0/0/6/1/18": {"page": 0, "box": H_DOT[2], "fate": "duration_narrowed"}}
    c = CM.note_census(heads, [], dot_boxes=[DOT_19])
    assert c["notes"]["candidate_lost"] == 1 and c["notes"]["candidate_lost_by_cause"]["value_undecided"] == 1


def test_a_dot_on_another_page_is_no_witness():
    heads, written = _heads(), [H_WRITTEN_DOTTED[0]]
    c = CM.note_census(heads, written, dot_boxes=[(7, DOT_19[1])], rest_boxes=[])
    assert c["notes"]["candidate_lost"] == 4


# ---- attached_dot_boxes: real aug_dot observations and duration verdicts of Brahms page 0, system 0, staff 6, cell 1
OBS = [
    {"id": "obs:018858", "subject": "glyph/0/0/6/1/6", "quantity": "aug_dot", "value": [569, 15]},
    {"id": "obs:018859", "subject": "glyph/0/0/6/1/9", "quantity": "aug_dot", "value": [553, 551]},
    {"id": "obs:018861", "subject": "glyph/0/0/6/1/19", "quantity": "aug_dot", "value": [553, 652]},
]
VERDICTS = [
    {"id": "vrd:1900026", "subject": "glyph/0/0/6/1/2", "quantity": "duration", "outcome": "decided", "supersedes": None,
     "used": ["obs:002185", "obs:002183", "vrd:1831660", "obs:009937", "obs:020528", "obs:016879", "obs:018859"]},
    {"id": "vrd:1900030", "subject": "glyph/0/0/6/1/11", "quantity": "duration", "outcome": "decided", "supersedes": None,
     "used": ["obs:002207", "obs:002205", "vrd:1831664", "obs:009937", "obs:020528", "obs:016879", "obs:018861"]},
]
BOXES = {"glyph/0/0/6/1/6": {"page": 0, "box": [2287.68, 3764.0, 2300.48, 3773.6]},
         "glyph/0/0/6/1/9": {"page": 0, "box": [2281.6, 3933.6, 2296.64, 3947.36]},
         "glyph/0/0/6/1/19": {"page": 0, "box": DOT_19[1]}}


def test_attached_dot_boxes_are_the_dots_a_written_duration_used():
    rec = {"observations": OBS, "verdicts": VERDICTS}
    got = CM.attached_dot_boxes(rec, BOXES, ["glyph/0/0/6/1/2", "glyph/0/0/6/1/11"])
    # dot 9 and dot 19 fed a written note's duration; dot 6 (decided "augmentation", fed no duration) is not evidence of anything
    assert sorted(b for _p, b in got) == sorted([BOXES["glyph/0/0/6/1/9"]["box"], DOT_19[1]])
    # the note of dot 19 not in the file: that dot is not "of a written note"
    got2 = CM.attached_dot_boxes(rec, BOXES, ["glyph/0/0/6/1/2"])
    assert [b for _p, b in got2] == [BOXES["glyph/0/0/6/1/9"]["box"]]
