"""lane-arcs-claim-1029: the arc claim and the kind from the two end heads (pure parts). Each guard has a twin that goes red without it."""
import numpy as np

from tools.omr.staged import arc_claim as AC
from tools.omr.staged import stroke_owner as SO


def _tn(rel, between=False, acc="unchanged"):
    return {"evaluated": True, "relation": rel, "between": between, "accidental": acc}


def test_tie_needs_two_adjacent_same_pitch_heads():
    assert AC.kind_from_ends(_tn("same"), None, None)[0] == "tie"
    assert AC.kind_from_ends(_tn("different"), None, None)[0] == "slur"


def test_more_than_two_notes_is_a_slur_even_when_the_ends_match():
    assert AC.kind_from_ends(_tn("same", between=True), None, None)[0] == "slur"


def test_same_pitch_with_an_unread_accidental_abstains():
    k, rule, _ = AC.kind_from_ends(_tn("same", acc="unknown"), None, None)
    assert k is None and rule == "same_pitch_accidental_unread"


def test_unread_ends_abstain_and_never_fall_back_on_a_detector_class():
    assert AC.kind_from_ends({"evaluated": False}, None, None) == (None, AC.ENDS_UNREAD, None)
    assert AC.kind_from_ends(None, None, "end_unanchored")[0] is None


def test_system_curve_anchors_stand_in_when_the_local_search_is_blind():
    assert AC.kind_from_ends({"evaluated": False}, None, "two_heads_one_position_adjacent")[0] == "tie"
    assert AC.kind_from_ends({"evaluated": False}, None, "two_positions")[0] == "slur"
    assert AC.kind_from_ends({"evaluated": False}, None, "one_position_heads_between")[0] == "slur"


def test_stacked_arcs_the_nearer_is_the_tie():
    assert AC.kind_from_ends(_tn("same"), {"role": "nearer"}, None)[0] == "tie"
    assert AC.kind_from_ends(_tn("same"), {"role": "farther"}, None)[0] is None      # a slur over two same-pitch notes: abstain (rule 8)
    assert AC.kind_from_ends(_tn("different"), {"role": "nearer"}, None)[0] == "slur"


def test_flags_default_off(monkeypatch):
    for n in (AC.ENV_CLAIM, AC.ENV_KIND, AC.ENV_SLUR):
        monkeypatch.delenv(n, raising=False)
    assert not (AC.claim_enabled() or AC.kind_enabled() or AC.slur_enabled())
    monkeypatch.setenv(AC.ENV_KIND, "1")
    assert AC.kind_enabled()


def test_a_stroke_along_the_trace_is_claimed_and_a_crossing_stem_is_not():
    # reduced frame == page frame at scale 1, up 1, cell origin 0,0
    arc = np.zeros((4, 40), dtype=bool)
    arc[1:3, :] = True                                  # a thin horizontal stroke along y 1..2
    stem = np.zeros((40, 3), dtype=bool)
    stem[:, :] = True                                   # a vertical stroke crossing it
    trace = {x: (1.0, 2.0) for x in range(0, 40)}
    assert AC.on_trace_share(arc, 0, 0, 1.0, (0, 0, 100, 100), 1.0, trace, 10.0) > 0.9
    assert AC.on_trace_share(stem, 10, 0, 1.0, (0, 0, 100, 100), 1.0, trace, 10.0) < 0.5


def test_the_claim_outranks_a_box_on_the_same_stroke():
    s = SO.Ink(0, "curve", (0, 0, 40, 4), 2.0, 0.2, 0.5, 10.0)
    head = SO.Claim("h", "head", "noteheadBlack", (0,), ())
    arc = SO.Claim("c", "arc_trace", "arc", (0,), (), "c", area=True)
    assert SO.own_strokes([s], [head, arc])[0].family == "arc_trace"
    assert SO.own_strokes([s], [head])[0].family != "arc_trace"          # the twin: without the claim the head's box stands
