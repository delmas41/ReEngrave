"""ROADMAP 2.202f -- the four causes behind Sean's round-3 right->gone / right->narrowed heads (FINDINGS shared-ink-map 5i). STAGED ADJUDICATE.

Constructed cells in canonical px, staff space 100. Every rule that fires has a twin that must not.
"""
from tools.omr.staged import beam_strokes as B
from tools.omr.staged import stroke_owner as SO

SP = 100.0


def sv(o, kind, box, *, length=None, thick=0.6, touches=(), ends=()):
    x, y, w, h = box
    L = length if length is not None else (max(w, h) / SP)
    return B.StrokeView(o, kind, tuple(map(float, box)), L, thick, None, 0.0, tuple((j, 0.2) for j in touches), SP, "", (), tuple(map(float, ends)))


# ── cause 1: the head's own ink is never its beam (tile 1, Litolff p6 0/1/10/2) ────────────────────────────────────────────────────────

def _cell_head_fused():
    # stem 1 up from a head at y 400-540; beam 0 at its tip; stroke 2 = the head fused with a neighbour, touching stems 1 and 3
    beam = sv(0, "horizontal", (0, 0, 700, 60), touches=(1, 3), thick=0.6)
    stem = sv(1, "vertical", (100, 30, 30, 480), touches=(0, 2))
    fused = sv(2, "horizontal", (0, 110, 400, 430), touches=(1, 3), thick=0.9)
    other = sv(3, "vertical", (330, 30, 30, 480), touches=(0, 2))
    return [beam, stem, fused, other]


def test_head_own_ink_is_not_a_level():
    v = _cell_head_fused()
    r = B.roles(v)
    assert r[2]["role"] == "beam"                         # the map's role alone calls it a beam
    tr = B.tip_reading(v, r, v[1], "up", head_box=(10, 400, 150, 140))
    assert tr["beams"] == [0] and tr["own_head"] == [2]


def test_head_own_ink_twin_without_head_box_counts_two():
    v = _cell_head_fused()
    tr = B.tip_reading(v, B.roles(v), v[1], "up")
    assert tr["beams"] == [0, 2]                          # the old reading, byte-identical without the argument


def test_second_level_not_holding_the_head_is_kept():
    v = _cell_head_fused()
    v[2] = sv(2, "horizontal", (0, 90, 400, 60), touches=(1, 3), thick=0.6)   # a real second beam, nowhere near the head
    tr = B.tip_reading(v, B.roles(v), v[1], "up", head_box=(10, 400, 150, 140))
    assert tr["beams"] == [0, 2] and tr["own_head"] == []


# ── cause 3: the thickness trough abstains (tile 8, Brahms p12 0/12/12/6, 0.49) ────────────────────────────────────────────────────────

def _span(thick):
    return [sv(0, "horizontal", (0, 0, 300, 60), touches=(1, 2), thick=thick), sv(1, "vertical", (0, 0, 30, 400), touches=(0,)),
            sv(2, "vertical", (270, 0, 30, 400), touches=(0,))]


def test_trough_is_beam_doubt():
    v = _span(0.49)
    assert B.roles(v, trough=True)[0]["role"] == "beam_doubt"
    tr = B.tip_reading(v, B.roles(v, trough=True), v[1], "up")
    assert tr["beams"] == [] and tr["doubt"] == [0]


def test_trough_twins():
    assert B.roles(_span(0.49))[0]["role"] == "span_thin"                 # off: as before
    assert B.roles(_span(0.40), trough=True)[0]["role"] == "span_thin"    # below the trough: a slur / tie remnant
    assert B.roles(_span(0.55), trough=True)[0]["role"] == "beam"


# ── cause 4: the beam covers its notes' stems though the erase broke the contact (Sean 2026-10-28) ─────────────────────────────────────

def _covered(gap_px, between=None, piece=None):
    # beam 0 above, centre line y 30, thick 0.6 (face at 60); stems hang below it with their tops `gap_px` short of the face
    beam = sv(0, "horizontal", (0, 0, 700, 60), touches=(2,), thick=0.6, ends=(0, 30, 700, 30))
    s1 = sv(1, "vertical", (100, 60 + gap_px, 30, 400))
    s2 = sv(2, "vertical", (400, 60, 30, 400), touches=(0,))
    out = [beam, s1, s2]
    if between is not None:
        out.append(sv(3, "blob", between))
    if piece is not None:
        out.append(sv(4, "blob", piece))
    return out


def test_stem_short_of_the_beam_is_joined():
    v = _covered(25)
    r = B.roles(v, face_join=True)
    assert r[0]["role"] == "beam" and r[0]["stems_by_face"] == [1]
    tr = B.tip_reading(v, r, v[1], "up", face_join=True)
    assert tr["beams"] == [0] and tr["joined"] == [0]


def test_cover_twins():
    v = _covered(25)
    assert B.roles(v)[0]["role"] == "beam_stub"                               # off: one stem touches, as before
    assert B.tip_reading(v, B.roles(v), v[1], "up")["beams"] == []
    far = _covered(150)                                                       # 1.5 sp of paper: not this beam's stem
    assert B.roles(far, face_join=True)[0]["stems_by_face"] == []
    blocked = _covered(40, between=(60, 65, 120, 30))                         # another mark's ink (wider than the column) between
    assert B.roles(blocked, face_join=True)[0]["stems_by_face"] == []


def test_broken_stem_piece_is_not_paper():
    # 1.1 sp to the face, 0.5 of it the stem's own piece in its column: 0.6 of paper -> joined (Brahms p0 0/4/9)
    v = _covered(110, piece=(100, 90, 30, 50))
    assert B.roles(v, face_join=True)[0]["stems_by_face"] == [1]
    assert B.roles(_covered(110), face_join=True)[0]["stems_by_face"] == []   # the same gap all paper: no


def test_down_stem_joins_a_beam_below():
    beam = sv(0, "horizontal", (0, 500, 700, 60), touches=(2,), thick=0.6, ends=(0, 530, 700, 530))
    s1 = sv(1, "vertical", (100, 0, 30, 470))             # bottom at 470: 30 px short of the face at 500
    s2 = sv(2, "vertical", (400, 0, 30, 500), touches=(0,))
    v = [beam, s1, s2]
    r = B.roles(v, face_join=True)
    assert r[0]["role"] == "beam"
    assert B.tip_reading(v, r, s1, "down", face_join=True)["joined"] == [0]
    assert B.tip_reading(v, r, s1, "up", face_join=True)["joined"] == []    # the beam is not beyond an up-stem's tip


# ── cause 2: an accidental's bar is printed clear of the note (tile 5, Litolff p6 1/8/10/5) ────────────────────────────────────────────

def _ink(L):
    return SO.Ink(0, "horizontal", (0, 0, L * SP, 120), L, 1.18, L * 1.1, SP)


def test_long_acc_bar_into_a_note_refused():
    fit, why = SO.shape_fit("accidental", _ink(3.6), touches_a_note=True, acc_bar_clear_of_note=True)
    assert fit == "no" and why.startswith("acc_bar_runs_into_a_note")


def test_acc_bar_twins():
    assert SO.shape_fit("accidental", _ink(3.6), touches_a_note=True)[0] == "could"                              # off: as landed
    assert SO.shape_fit("accidental", _ink(3.6), touches_a_note=False, acc_bar_clear_of_note=True)[0] == "could"  # clear of the note
    assert SO.shape_fit("accidental", _ink(1.2), touches_a_note=True, acc_bar_clear_of_note=True)[0] == "clear"   # a sharp's own bar
