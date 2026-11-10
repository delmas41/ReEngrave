"""ROADMAP 2.285 -- an accidental claims its own ink where the detector drew no accidental box (`staged/page_accidental_ink.py`, flag `OMR_ACCIDENTAL_OWN_INK`).

Pure tests on hand-built strokes (no PDF, no library): the finder reads a sharp / natural / flat from its own strokes and files nothing for what is not one.
The controls can fail: a down-stem note (a stem and a head) is not a flat, two bare stems are not a sharp, a key signature's sharp and a boxed accidental are not this reader's.
"""
from types import SimpleNamespace

from tools.omr.staged import accidental_family as AF
from tools.omr.staged import claim_order as CO
from tools.omr.staged import page_accidental_ink as PAI

SP = 20.0


def stroke(kind, x, y, w, h, touches=(), fill=0.9):
    """A page stroke as `stroke_map.Stroke` shows it to the reader: box (x, y, w, h) page px, length / area in spaces, `touches` page ordinals."""
    length = max(w, h) / SP if kind in ("vertical", "horizontal") else max(w, h) / SP
    return SimpleNamespace(kind=kind, box=(x, y, w, h), length_sp=length, touches=[(int(o), 0.3) for o in touches], parts=[], staff_space_local=SP, fill=fill,
                           area_sp2=fill * w * h / (SP * SP))


def sharp_at(x, y, base=0):
    """A sharp: two level uprights 2.9 sp tall, 0.6 sp apart, joined by two short bars (ordinals base .. base+3)."""
    return [stroke("vertical", x, y, 3, 58, touches=(base + 2, base + 3)), stroke("vertical", x + 12, y, 3, 58, touches=(base + 2, base + 3)),
            stroke("horizontal", x, y + 18, 15, 3, touches=(base, base + 1)), stroke("horizontal", x, y + 36, 15, 3, touches=(base, base + 1))]


def note_head_beside(x0, y0, conf=0.8):
    return PAI.Head((x0, y0, x0 + 26, y0 + 20), conf, "head")


def test_default_off():
    import os
    os.environ.pop(PAI.ENV, None)
    assert PAI.enabled() is False
    os.environ[PAI.ENV] = "1"
    try:
        assert PAI.enabled() is True
    finally:
        os.environ.pop(PAI.ENV, None)


def test_a_sharp_with_a_note_beside_is_claimed_guessed():
    strokes = sharp_at(100, 100)
    found, why = PAI.read_page(strokes, SP, [note_head_beside(132, 119)], [], [])
    assert len(found) == 1 and why["claimed"] == 1
    c = found[0]
    assert c["type"] == "sharp" and c["standing"] == "GUESSED"           # nothing is READ on a sharp (accidental_family.reads)
    assert c["members"] == [0, 1, 2, 3] and c["box"] == [100.0, 100.0, 115.0, 158.0]


def test_a_natural_at_its_read_margin_is_read():
    # the right stem hangs 0.9 sp lower than the left: a natural, margin 0.9 - 0.45 above the 2.263b bar
    s = [stroke("vertical", 100, 100, 3, 50, touches=(2, 3)), stroke("vertical", 112, 118, 3, 50, touches=(2, 3)),
         stroke("horizontal", 100, 120, 15, 3, touches=(0, 1)), stroke("horizontal", 100, 140, 15, 3, touches=(0, 1))]
    found, _ = PAI.read_page(s, SP, [note_head_beside(132, 120)], [], [])
    assert len(found) == 1 and found[0]["type"] == "natural" and found[0]["standing"] == "READ"
    assert AF.reads(found[0]["margin"], "natural")


def test_a_flat_is_claimed_guessed():
    s = [stroke("vertical", 100, 100, 3, 50, touches=(1,)), stroke("curve", 103, 128, 12, 22, touches=(0,), fill=0.5)]
    found, _ = PAI.read_page(s, SP, [note_head_beside(130, 125)], [], [])
    assert len(found) == 1 and found[0]["type"] == "flat" and found[0]["standing"] == "GUESSED"


def test_no_note_beside_no_claim():
    found, why = PAI.read_page(sharp_at(100, 100), SP, [note_head_beside(400, 119)], [], [])
    assert found == [] and why.get("no_note_beside") == 1


def test_a_note_far_above_is_not_the_note_it_is_by():
    found, why = PAI.read_page(sharp_at(100, 300), SP, [note_head_beside(132, 100)], [], [])
    assert found == [] and why.get("no_note_beside") == 1


def test_CONTROL_a_down_stem_note_is_not_a_flat():
    """A stem and a head at its lower right is a flat's SHAPE (one upright, a piece low to its right). The solid head blob a confident box holds blocks the
    growth, so the stem reads as a lone stem. If the head were not blocked this would claim a flat and the test would fail."""
    stem = stroke("vertical", 100, 100, 3, 50, touches=(1,))          # 2.5 sp: a flat's stem length, so only the head's blocking separates it from a flat
    head = stroke("blob", 103, 130, 22, 20, touches=(0,), fill=0.95)
    for conf in (0.8, 0.3):                            # a confident box, and a weak one: the solid blob is a head either way (SOLID_HEAD_*)
        found, why = PAI.read_page([stem, head], SP, [PAI.Head((103, 130, 125, 150), conf, "h"), note_head_beside(160, 135)], [], [])
        assert found == [], (conf, why)


def test_CONTROL_the_head_control_can_fail(monkeypatch):
    """The same stem + head with the head's blocking switched off IS read as a flat: the control above is held by the blocking, not by luck."""
    stem = stroke("vertical", 100, 100, 3, 50, touches=(1,))
    head = stroke("blob", 103, 130, 22, 20, touches=(0,), fill=0.95)
    monkeypatch.setattr(PAI, "real_head_strokes", lambda *a, **k: [])
    found, _ = PAI.read_page([stem, head], SP, [PAI.Head((103, 130, 125, 150), 0.8, "h"), note_head_beside(160, 135)], [], [])
    assert len(found) == 1 and found[0]["type"] == "flat"


def test_CONTROL_a_hollow_half_head_on_a_stem_is_not_a_flat():
    stem = stroke("vertical", 100, 100, 3, 66, touches=(1,))
    head = stroke("curve", 103, 146, 26, 20, touches=(0,), fill=0.45)           # a hollow oval: wider than one accidental's size (INK_MAX_W_SP)
    found, why = PAI.read_page([stem, head], SP, [PAI.Head((103, 146, 129, 166), 0.3, "h"), note_head_beside(160, 150)], [], [])
    assert found == [], why


def test_CONTROL_two_bare_stems_are_not_a_sharp():
    """A chord's stem pair stands level like a sharp's uprights but nothing joins them: no cluster of two, so each stem alone reads `one_stem_no_bowl`."""
    s = [stroke("vertical", 100, 100, 3, 58), stroke("vertical", 112, 100, 3, 58)]
    found, why = PAI.read_page(s, SP, [note_head_beside(132, 119)], [], [])
    assert found == [], why


def test_bar_joins_stems_needs_a_piece_touching_both_stems():
    s = sharp_at(100, 100)
    assert PAI.bar_joins_stems(s, [0, 1, 2, 3]) is True
    assert PAI.bar_joins_stems(s[:2] + [stroke("horizontal", 100, 118, 15, 3)], [0, 1, 2]) is False        # a bar that touches neither stem
    assert PAI.bar_joins_stems(s[:2] + [stroke("horizontal", 100, 118, 15, 3, touches=(0,))], [0, 1, 2]) is False   # touches one
    assert PAI.bar_joins_stems(s[:2], [0, 1]) is False


def test_CONTROL_a_key_signature_sharp_is_not_this_readers():
    strokes = sharp_at(100, 100)
    found, _ = PAI.read_page(strokes, SP, [note_head_beside(132, 119)], [], [(90.0, 90.0, 125.0, 170.0)])      # an earlier page claim's rectangle holds it
    assert found == []
    found, _ = PAI.read_page(strokes, SP, [note_head_beside(132, 119)], [], [], held_ids=[0])                  # or an earlier claim names a stroke of it
    assert found == []


def test_CONTROL_a_boxed_accidental_is_not_this_readers():
    found, why = PAI.read_page(sharp_at(100, 100), SP, [note_head_beside(132, 119)], [(98.0, 96.0, 120.0, 162.0)], [])
    assert found == [], why                  # the box holds its strokes: they are its reader's, never seeds
    # a box that sits OFF its mark (2.247 r2: half the mark outside it) still stands on it
    found, why = PAI.read_page(sharp_at(100, 100), SP, [note_head_beside(132, 119)], [(100.0, 140.0, 118.0, 190.0)], [])
    assert found == [] and why.get("already_boxed") == 1


def test_CONTROL_a_dynamic_letter_is_not_this_readers():
    found, _ = PAI.read_page(sharp_at(100, 100), SP, [note_head_beside(132, 119)], [], [], reads=[(90.0, 90.0, 125.0, 170.0)])
    assert found == []


def test_a_sharp_boxed_as_a_head_is_still_claimed():
    """The five sharps of 2.282: the detector drew ONLY a notehead box over them, at 0.25-0.46. A weak head box does not block (its ink is no real head's), and the note
    it is by is the confident head to its right, not its own box."""
    strokes = sharp_at(100, 100)
    own = PAI.Head((98.0, 120.0, 118.0, 140.0), 0.37, "own")
    found, _ = PAI.read_page(strokes, SP, [own, note_head_beside(132, 119)], [], [])
    assert len(found) == 1 and found[0]["type"] == "sharp"


def test_too_short_and_too_small_ink_is_not_an_accidental():
    tiny = [stroke("vertical", 100, 100, 3, 20, touches=(2, 3)), stroke("vertical", 112, 100, 3, 20, touches=(2, 3)),
            stroke("horizontal", 100, 105, 15, 3, touches=(0, 1)), stroke("horizontal", 100, 112, 15, 3, touches=(0, 1))]
    found, why = PAI.read_page(tiny, SP, [note_head_beside(132, 100)], [], [])
    assert found == [] and any(k.startswith("size:") for k in why)


def test_one_mark_one_claim_twins_fold():
    a = {"members": [0, 1, 2, 3, 4], "box": [100.0, 100.0, 118.0, 158.0]}
    b = {"members": [1, 2, 3, 4], "box": [101.0, 101.0, 119.0, 160.0]}
    far = {"members": [9, 10], "box": [300.0, 100.0, 318.0, 158.0]}
    kept = PAI.fold_twins([b, far, a])
    assert [k["members"] for k in kept] == [[0, 1, 2, 3, 4], [9, 10]]


def test_the_claim_is_a_layer_before_the_heads():
    assert CO.layer_of(PAI.OWNER) is not None
    assert CO.layer_of(PAI.OWNER) < CO.layer_of("head") < CO.layer_of("stem")


class _Row:
    def __init__(self, value, **detail):
        self.value, self.detail = value, detail


class _Log:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, *_a, **_k):
        return self._rows


def test_earlier_claims_reads_areas_and_named_strokes_and_not_its_own():
    rows = [_Row([1.0, 2.0, 3.0, 4.0], unit="area", standing="READ", owner="key_signature"),
            _Row([5.0, 6.0, 7.0, 8.0], unit="area", standing="GUESSED", owner="word"),
            _Row([], unit="page_ink", owner="tremolo", page_strokes=[4, 9]),
            _Row([9.0, 9.0, 9.0, 9.0], unit=PAI.UNIT, owner=PAI.OWNER, page_strokes=[77])]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    assert rects == [(1.0, 2.0, 3.0, 4.0)] and ids == [4, 9]


def test_TWINS_two_head_boxes_on_one_accidentals_ink_are_one_claim():
    """A sharp the detector boxed twice as a weak notehead (two boxes on one mark: Litolff merges, Breitkopf shatters) and a real note beside it: ONE claim."""
    strokes = sharp_at(100, 100)
    twins = [PAI.Head((98.0, 120.0, 118.0, 140.0), 0.37, "a"), PAI.Head((99.0, 122.0, 119.0, 142.0), 0.31, "b")]
    found, why = PAI.read_page(strokes, SP, twins + [note_head_beside(132, 119)], [], [])
    assert len(found) == 1 and why["claimed"] == 1 and found[0]["type"] == "sharp"


def test_TWINS_two_note_boxes_beside_one_accidental_are_still_one_claim():
    """Twin boxes on the NOTE it is by must not claim the accidental twice: the claim is the ink's, the note is only evidence."""
    found, why = PAI.read_page(sharp_at(100, 100), SP, [note_head_beside(132, 119), note_head_beside(133, 120)], [], [])
    assert len(found) == 1 and why["claimed"] == 1


def test_TWINS_two_seeds_of_one_mark_fold_even_when_the_growth_differs():
    a = {"members": [0, 1, 2, 3], "box": [100.0, 100.0, 115.0, 158.0]}
    b = {"members": [1, 3], "box": [112.0, 100.0, 115.0, 158.0]}        # the right stem alone, a different stop of the growth: inside a
    assert [k["members"] for k in PAI.fold_twins([b, a])] == [[0, 1, 2, 3]]


def test_CONTROL_the_twin_fold_can_fail():
    """Two marks side by side (a chord's two accidentals, one column apart) are NOT twins: both stay."""
    a = {"members": [0, 1, 2, 3], "box": [100.0, 100.0, 115.0, 158.0]}
    b = {"members": [4, 5, 6, 7], "box": [60.0, 130.0, 75.0, 188.0]}
    assert len(PAI.fold_twins([a, b])) == 2


def test_CONTROL_a_real_small_head_beside_a_stem_is_not_an_accidental():
    """An up-stem quarter note: a stem 2.9 sp long and a head at its lower LEFT. The solid blob is a head, so the stem stands alone: no claim."""
    stem = stroke("vertical", 120, 100, 3, 58, touches=(1,))
    head = stroke("blob", 100, 140, 22, 18, touches=(0,), fill=0.95)
    for conf in (0.9, 0.3):
        found, why = PAI.read_page([stem, head], SP, [PAI.Head((100, 140, 122, 158), conf, "h"), note_head_beside(160, 140)], [], [])
        assert found == [], (conf, why)
