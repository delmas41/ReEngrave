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


# ---- (a) the old tie pairing's refusals: the REAL arc report of the 20261123-night Litolff record (8 counted pages)
LIT_NIGHT = {
    "arcs_not_written": {"old_box_path_retired": 601, "replaced_by_page_arc": 789, "not_an_arc:ink_is_a_staff_line": 306, "kind_arc_ends_unread": 9,
                         "not_an_arc:claimed_by:key_signature": 5, "kind_stack_slur_over_two_same_pitch_notes": 1, "tie_pitch_contradiction": 10,
                         "tie_ends_in_two_voices": 1, "slur_bound_end_not_in_file": 19, "tie_pair_no_start_head": 41, "tie_pair_no_stop_head": 30,
                         "tie_pair_enters_from_previous_system": 26, "tie_pair_no_pair_at_one_position": 22, "tie_pair_no_head_near_the_arc": 40,
                         "tie_pair_runs_off_the_system": 11, "tie_pair_not_adjacent": 37, "tie_pair_spans_a_whole_bar": 3, "tie_end_not_in_file": 7,
                         "arc_ends_in_one_chord": 2},
    "written": {"page_arc_runs": 664, "page_arc_runs_not_witnessed": 134, "page_arc_runs_abstained": 250, "page_arc_runs_kind_unread_nothing_written": 11,
                "page_arc_slurs_in_file": 55, "page_arc_slurs_not_in_file": 4, "page_arc_ties_in_file": 187, "page_arc_ties_not_in_file": 7},
    CM.ON_RUNS_KEY: {"written": {"tie_pair_no_head_near_the_arc": 10, "tie_pair_not_adjacent": 13, "tie_pair_no_start_head": 4, "tie_pair_no_pair_at_one_position": 5},
                     "run_counted": {"tie_pair_no_stop_head": 16, "tie_pair_enters_from_previous_system": 12, "tie_pair_no_head_near_the_arc": 15,
                                     "tie_pair_no_pair_at_one_position": 7, "tie_pair_runs_off_the_system": 7, "tie_pair_not_adjacent": 16, "tie_pair_no_start_head": 23}},
}


def test_old_tie_pairing_refusals_are_named_apart_and_every_real_loss_still_counts():
    a = CM.arcs_count(LIT_NIGHT)
    # OLD (2.316): 120 old-box refusals + 261 page runs not written = 381 (the committed ranking's Litolff TAG figure)
    assert a["old_box_refusals"] + a["old_tie_pairing_refusals"] == 120
    assert a["old_tie_pairing_refusals"] == 82
    # NEW: the 82 are named apart; what the file really lost stays: the page runs read and not written (261) and the 38 refusals of the arc rules
    assert a["old_box_refusals"] == 38
    assert a["page_runs_not_written"] == 261
    assert a["not_written_total"] == 299
    assert a["with_unwitnessed_and_old_pairing"] == 299 + 134 + 82       # nothing dropped: the upper bound still holds every named-apart candidate
    assert "tie_pitch_contradiction" in a["old_box_refusals_by_reason"]       # a real refusal of a decided tie still counts


# ---- (c) one arc across a system break: REAL abstained system-edge runs of Litolff page 16 (staff 3, system 0 right edge / system 1 left edge) and page 2 (a lone half)
def _run(row, home, edge):
    return {"row": row, "status": "abstained", "why": "system_edge", "home": home, "edge": edge}


BREAK_RECORD = {"verdicts": [
    {"quantity": "page_arc_binding", "subject": "page/16", "detail": {"runs": [_run("obs:663435", "staff/16/0/3", "right"), _run("obs:663379", "staff/16/1/3", "left")]}},
    {"quantity": "page_arc_binding", "subject": "page/2", "detail": {"runs": [_run("obs:057646", "staff/2/1/0", "right")]}}]}


def test_the_two_halves_of_an_arc_across_a_system_break_are_counted_once():
    h = CM.system_break_halves(BREAK_RECORD, [2, 16])
    assert h == {"pairs": 1, "halves": 3}                       # page 2's half has no partner on the next system: it stays counted
    base = CM.arcs_count(LIT_NIGHT)
    rep = dict(LIT_NIGHT, **{CM.HALVES_KEY: h})
    new = CM.arcs_count(rep)
    assert base["page_runs_not_written"] == 261 and new["page_runs_not_written"] == 260      # OLD counts the arc twice, NEW once
    assert new["not_written_total"] == base["not_written_total"] - 1
    assert new["arc_halves_counted_once"] == 1 and base["arc_halves_counted_once"] is None  # no list filed: nothing changes, and it says so
    # a lone half, or a pair whose page is not counted, is never merged
    assert CM.system_break_halves(BREAK_RECORD, [2])["pairs"] == 0
    assert CM.system_break_halves(BREAK_RECORD, [16])["pairs"] == 1


def test_without_the_page_pass_no_halves_are_merged():
    a = CM.arcs_count({"arcs_not_written": {"tie_end_not_in_file": 2}, "written": {}, CM.HALVES_KEY: {"pairs": 1, "halves": 2}})
    assert a["not_written_total"] == 2


def test_without_the_page_pass_the_old_pairing_is_the_only_tie_path_and_its_refusals_still_count():
    a = CM.arcs_count({"arcs_not_written": {"tie_pair_no_start_head": 3}, "written": {}})
    assert a["not_written_total"] == 3 and a["old_tie_pairing_refusals"] == 0
