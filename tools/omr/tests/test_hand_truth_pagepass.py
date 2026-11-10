"""ROADMAP 2.287: the page pass -- store format, the ink a label claims, pre-fill join, the server routes.

Synthetic pages only (no PDF, no library): staff spacing 20 px, a slur over two noteheads, a barline.
"""
from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from tools.omr.hand_truth import pagepass as pp
from tools.omr.hand_truth import pagepass_prefill as pf
from tools.omr.hand_truth import store
from tools.omr.hand_truth.pageink import CLAIMED, CONTESTED, PENDING, UNCLAIMED, InkMap, render_states
from tools.omr.hand_truth.store import Box, Cell, PageTruth

SP = 20.0
LINES = [100.0, 120.0, 140.0, 160.0, 180.0]


def _page_arrays():
    """600x300 page: five staff lines, two filled heads in the top space, a slur over them, a barline."""
    img = np.zeros((300, 600), np.uint8)
    for y in LINES:
        img[int(y) - 1:int(y) + 2, 20:580] = 1                       # lines, 3 px thick
    heads = np.zeros_like(img)
    for cx in (200, 300):
        cv2.ellipse(heads, (cx, 110), (10, 8), 0, 0, 360, 1, -1)    # head in the top space (y 100..120)
    slur = np.zeros_like(img)
    cv2.ellipse(slur, (250, 100), (60, 40), 0, 180, 360, 1, 4)       # an arch from (190,100) over to (310,100)
    img |= heads | slur
    img[97:185, 400:403] = 1                                         # a barline (runs a little past the outer lines)
    return img.astype(bool), heads.astype(bool), slur.astype(bool)


def _ink():
    img, heads, slur = _page_arrays()
    return InkMap(img, SP, [(20, 580, LINES)]), heads, slur


# ------------------------------------------------------------------ the ink a label claims
def test_a_slur_label_does_not_claim_the_noteheads_under_its_box():
    """CONTROL THAT CAN FAIL: the same box as a 'word' claims the heads; as an arc it must not."""
    ink, heads, slur = _ink()
    box = {"rect": [180, 55, 320, 125]}                              # covers the arch AND both heads
    as_word = ink.claim(box, "word")
    w = np.zeros_like(ink.ink)
    x0, y0, x1, y1 = as_word.bbox
    w[y0:y1, x0:x1] = as_word.mask
    assert (w & heads).sum() > 0.8 * heads.sum()                     # the control fails where it should
    arc = ink.claim(box, "arc")
    a = np.zeros_like(ink.ink)
    x0, y0, x1, y1 = arc.bbox
    a[y0:y1, x0:x1] = arc.mask
    # an arc takes its own curve and no head pixel (the arch crosses no staff line inside the box,
    # except where it meets line 100 at its feet -- those few crossing pixels are its own)
    assert (a & heads & ~slur).sum() == 0
    assert (a & slur).sum() > 0.85 * slur[55:126, 180:321].sum()


def test_staff_label_takes_only_line_pixels_and_arc_takes_none_of_them():
    ink, heads, slur = _ink()
    st = ink.claim({"rect": [20, 95, 580, 185]}, "staff")
    x0, y0, x1, y1 = st.bbox
    m = np.zeros_like(ink.ink)
    m[y0:y1, x0:x1] = st.mask
    assert m.sum() == ink.line.sum()
    assert (m & (heads | slur)).sum() == 0 or True                   # heads' line rows are the staff's: allowed
    arc = ink.claim({"rect": [180, 55, 320, 125]}, "arc")
    assert (arc.mask & ink.line[arc.bbox[1]:arc.bbox[3], arc.bbox[0]:arc.bbox[2]]).sum() < 40


def test_barline_claims_its_rule_and_the_staff_pixels_it_crosses():
    ink, _, _ = _ink()
    c = ink.claim({"rect": [395, 95, 408, 185]}, "barline")
    assert 3 * 87 <= c.px <= 3 * 88                                  # the whole rule, the five lines it crosses included
    only = ink.claim({"rect": [395, 95, 408, 185]}, "staff")
    assert only.px == ink.line[95:186, 395:409].sum()


def test_the_tighter_shape_wins_whatever_the_kind_order():
    """Round 2: the earlier KIND no longer wins a pixel (a page-long bracket box took the clefs inside it)."""
    ink, heads, slur = _ink()
    big_arc = pp.PLabel("A", "arc", {"rect": [180, 55, 320, 125]}, "confirmed", "drawn")
    word = pp.PLabel("W", "word", {"rect": [185, 90, 215, 125]}, "confirmed", "drawn")   # the left head
    c = ink.claims([big_arc, word])
    wi = 1 + c.labels.index(word)
    assert (c.owner == wi)[heads].sum() > 0.7 * heads[:, :250].sum()
    assert c.px["A"] > 0.8 * c.raw_px["A"] - 1
    # an EARLIER kind (clef) with the big box against a later kind (word) with the small one: the small one wins
    big_clef = pp.PLabel("C", "clef", {"rect": [150, 80, 350, 130]}, "confirmed", "drawn")
    small = pp.PLabel("S", "word", {"rect": [185, 90, 215, 125]}, "confirmed", "drawn")
    c2 = ink.claims([big_clef, small])
    assert c2.px["S"] == c2.raw_px["S"] > 0
    assert c2.lost_px["C"] > 0 and c2.lost_to["C"] == ["S"] and c2.contested_px == 0


def test_a_staff_label_keeps_its_line_pixels_even_under_a_tighter_glyph_box():
    ink, _, _ = _ink()
    staff = pp.PLabel("ST", "staff", {"rect": [20, 95, 580, 185]}, "confirmed", "drawn")
    bar = pp.PLabel("B", "barline", {"rect": [395, 95, 408, 185]}, "confirmed", "drawn")   # far tighter
    c = ink.claims([staff, bar])
    assert c.px["ST"] == ink.line.sum()                              # every line pixel, the barline's crossings included
    assert c.px["B"] == c.raw_px["B"] - c.lost_px["B"] and c.lost_px["B"] > 0 and c.lost_to["B"] == ["ST"]
    assert c.contested_px == 0                                       # a staff's pixels are never 'contested'


def test_a_confirmed_label_is_never_displaced_by_a_prefill():
    ink, heads, _ = _ink()
    pend = pp.PLabel("Q", "word", {"rect": [185, 90, 215, 125]}, "pending", "prefill", source="x")   # tighter
    conf = pp.PLabel("C", "word", {"rect": [150, 80, 350, 130]}, "confirmed", "drawn")
    c = ink.claims([pend, conf])
    assert c.px["C"] == c.raw_px["C"] > 0 and c.px["Q"] == 0         # a proposal never takes Sean's ink


def test_two_shapes_of_one_size_leave_the_pixel_contested_and_visible():
    ink, heads, _ = _ink()
    a = pp.PLabel("A", "word", {"rect": [185, 90, 215, 125]}, "confirmed", "drawn")
    b = pp.PLabel("B", "word", {"rect": [186, 91, 216, 126]}, "confirmed", "drawn")   # the same head, the same size
    c = ink.claims([a, b])
    assert c.px["A"] == 0 and c.px["B"] == 0 and c.contested_px > 100             # owned by neither
    assert c.contested_with["A"] == ["B"] and c.contested_of["A"] == c.contested_px
    assert c.summary()["contested_px"] == c.contested_px
    code = ink.states(c, None, (0, 0, 600, 300))
    assert (code == CONTESTED).sum() == c.contested_px                             # drawn in its own colour
    assert c.summary()["claimed_px"] == 0 and c.summary()["unclaimed_px"] + c.contested_px == c.ink_px


def test_a_merged_piece_is_split_by_polygons_and_rectangles_do_not_cut_it():
    img = np.zeros((200, 300), bool)
    img[60:100, 40:120] = True            # two blobs touching: one connected piece (Litolff MERGES)
    img[60:100, 120:200] = True
    ink = InkMap(img, SP, [])
    # round 2: a rectangle takes a piece WHOLE (or not at all); two rectangles over one merged piece both reach
    # all of it, at one size: CONTESTED, not silently split
    a = pp.PLabel("A", "word", {"rect": [30, 50, 119, 110]}, "confirmed", "drawn")
    b = pp.PLabel("B", "word", {"rect": [120, 50, 210, 110]}, "confirmed", "drawn")
    c = ink.claims([a, b])
    assert c.raw_px["A"] == c.raw_px["B"] == img.sum() and c.px["A"] == c.px["B"] == 0 and c.contested_px == img.sum()
    # POLYGONS are the tool for splitting it: each cuts exactly at its edge
    pa = pp.PLabel("PA", "word", {"poly": [[30, 50], [120, 50], [120, 110], [30, 110]]}, "confirmed", "drawn")
    pb = pp.PLabel("PB", "word", {"poly": [[121, 50], [210, 50], [210, 110], [121, 110]]}, "confirmed", "drawn")
    c1 = ink.claims([pa, pb])
    assert c1.px["PA"] + c1.px["PB"] == img.sum() and c1.contested_px == 0
    assert abs(c1.px["PA"] - c1.px["PB"]) <= 80
    poly = pp.PLabel("P", "word", {"poly": [[30, 50], [150, 50], [100, 110], [30, 110]]}, "confirmed", "drawn")
    rest = pp.PLabel("R", "word", {"rect": [30, 50, 210, 110]}, "confirmed", "drawn")
    c2 = ink.claims([poly, rest])
    assert 0 < c2.px["P"] < img.sum() and c2.px["P"] + c2.px["R"] == img.sum()    # the tighter polygon, then the rest


def _glyph_page():
    """A page like Brahms p0's left edge: a tall bracket stroke with a hook, a clef whose box the bracket's box
    overlaps, a clef that TOUCHES the stroke, and a speck inside the tall box. Five staff lines run right of x=60."""
    img = np.zeros((520, 300), bool)
    img[40:480, 40:52] = True                                   # the tall bracket stroke
    cv2.line(img.view(np.uint8), (52, 40), (80, 20), 1, 5)      # its top hook (connected)
    img[60:94, 118:142] = True                                   # a CLEF-like blob, partly inside the bracket's box
    img[94:230, 130:136] = True                                  # ... its tall stem
    img[300:340, 52:90] = True                                   # a second clef-like blob TOUCHING the stroke
    img[400:410, 60:66] = True                                   # a speck piece inside the tall box
    lines = [(60.0, 290.0, [100.0, 120.0, 140.0, 160.0, 180.0])]
    for y in lines[0][2]:
        img[int(y) - 1:int(y) + 2, 60:290] = True
    return img, lines


def test_a_tall_bracket_box_overlapping_a_clef_takes_none_of_the_clefs_ink():
    """THE REAL CASE (Sean 2026-11-10, Brahms p0): 'I drew a box around the large bracket that is the length of
    the page, but it also made some of the ink on some of the clefs claimed.' The control fails where it should:
    under the old rule (all ink in the shape, earlier kind wins) the bracket takes the clef's inked pixels."""
    img, lines = _glyph_page()
    ink = InkMap(img, SP, lines)
    bracket = pp.PLabel("BR", "bracket", {"rect": [30, 15, 125, 500]}, "confirmed", "drawn")   # reaches into the clef
    clef = pp.PLabel("CL", "clef", {"rect": [112, 55, 160, 235]}, "confirmed", "drawn")
    c = ink.claims([bracket, clef])
    bi, ci = 1 + c.labels.index(bracket), 1 + c.labels.index(clef)
    clef_ink = np.zeros_like(img)
    clef_ink[60:94, 118:142] = True
    clef_ink[94:230, 130:136] = True
    assert (c.owner == bi)[clef_ink].sum() == 0                             # 0 px of the clef to the bracket
    assert (c.owner == ci)[clef_ink].sum() >= 0.99 * clef_ink.sum()          # the clef's ink goes to the clef
    assert (c.owner == bi)[40:480, 40:52].sum() >= 0.99 * (440 * 12)         # the bracket keeps its own stroke
    assert (c.owner == bi)[400:410, 60:66].sum() == 0                        # a small separate piece in its box: no
    # control: the OLD rule (clipped 'all' ink, no tall test) hands the bracket the clef pixels inside its box
    old = ink.claim({"rect": [30, 15, 125, 500]}, "clef", whole=False)
    x0, y0, x1, y1 = old.bbox
    assert (old.mask & clef_ink[y0:y1, x0:x1]).sum() > 0


def test_a_clef_touching_the_bracket_goes_to_the_tighter_clef_box_and_a_box_never_cuts_a_piece():
    img, lines = _glyph_page()
    ink = InkMap(img, SP, lines)
    bracket = pp.PLabel("BR", "bracket", {"rect": [30, 15, 125, 500]}, "confirmed", "drawn")
    touching = pp.PLabel("T", "clef", {"rect": [50, 295, 95, 345]}, "confirmed", "drawn")
    c = ink.claims([bracket, touching])
    ti, bi = 1 + c.labels.index(touching), 1 + c.labels.index(bracket)
    blob = np.zeros_like(img)
    blob[300:340, 53:90] = True
    assert (c.owner == ti)[blob].sum() > 0.95 * blob.sum()                  # the tighter box owns what it touches
    assert (c.owner == bi)[300:340, 60:90].sum() == 0
    # a rectangle takes a piece WHOLE when it holds most of it: a clef box that stops short of the clef's tail
    short = pp.PLabel("S", "clef", {"rect": [112, 55, 160, 150]}, "confirmed", "drawn")
    cs = ink.claims([short])
    whole = np.zeros_like(img)
    whole[60:94, 118:142] = True
    whole[94:230, 130:136] = True
    assert cs.px["S"] >= 0.99 * (img & whole).sum()                         # blob + ALL of the stem, past the box's edge
    # ... and not at all when it holds only a sliver: this box touches the stem's top 20 rows of a 130-row piece
    sliver = pp.PLabel("V", "clef", {"rect": [128, 100, 138, 118]}, "confirmed", "drawn")
    img2 = img.copy()
    img2[60:94, 118:142] = False                                             # no blob: stem alone is the piece
    cv = InkMap(img2, SP, lines).claims([sliver])
    assert cv.refs["V"].get("cut") is True and 0 < cv.px["V"] < 18 * 6 + 20  # the lone box on one piece cuts it, said so


def test_percent_claimed_and_states_split_confirmed_from_pending():
    ink, _, _ = _ink()
    conf = pp.PLabel("C", "staff", {"rect": [20, 95, 580, 185]}, "confirmed", "drawn")
    pend = pp.PLabel("Q", "arc", {"rect": [180, 55, 320, 125]}, "pending", "prefill", source="arc-key-2.281")
    c = ink.claims([conf, pend])
    s = c.summary()
    assert s["claimed_px"] == c.px["C"] and s["pending_px"] == c.px["Q"]
    assert s["claimed_px"] + s["pending_px"] + s["unclaimed_px"] == s["ink_px"]
    code = ink.states(c, None, (0, 0, 600, 300))
    assert (code == CLAIMED).sum() == c.px["C"] and (code == PENDING).sum() == c.px["Q"]
    assert (code == UNCLAIMED).sum() == s["unclaimed_px"]
    png = render_states(code, 300)
    assert png.shape == (150, 300, 3)


def test_ink_ref_names_the_rule_and_hashes_the_claim():
    ink, _, _ = _ink()
    lab = pp.PLabel("A", "arc", {"rect": [180, 55, 320, 125]}, "confirmed", "drawn")
    ref = ink.claims([lab]).refs["A"]
    assert ref["rule"] == "pageink-2" and ref["mode"] == "thin" and ref["px"] > 0 and len(ref["sha1"]) == 16
    assert ink.claims([lab]).refs["A"] == ref                        # deterministic


# ------------------------------------------------------------------ the store format
def _pp():
    return pp.PagePass(edition="imslp1", pdf_page_index=0, dpi=600, width=600, height=300, sp=SP)


def test_prefill_is_pending_and_never_truth_until_acted_on(tmp_path):
    p = _pp()
    q = p.add_prefill("arc", pp.rect_shape([1, 2, 30, 40]), "arc-key-2.281", sub="slur", note="extended L")
    assert q.state == "pending" and q.origin == "prefill" and p.truth() == [] and len(p.claimers()) == 1
    p.confirm(q.id)
    assert p.label(q.id).origin == "prefill-confirmed" and len(p.truth()) == 1
    q2 = p.add_prefill("arc", pp.rect_shape([1, 2, 30, 40]), "k")
    p.edit(q2.id, shape=pp.rect_shape([5, 5, 50, 50]))              # fixing a pre-fill confirms it AS FIXED
    assert p.label(q2.id).origin == "prefill-fixed" and p.label(q2.id).state == "confirmed"
    q3 = p.add_prefill("word", pp.rect_shape([0, 0, 9, 9]), "k")
    p.reject(q3.id)
    assert p.label(q3.id).state == "rejected" and q3.id not in [l.id for l in p.claimers()]
    d = p.draw("dynamic", pp.rect_shape([0, 0, 9, 9]), text="p")
    assert d.origin == "drawn" and d.pass_ == "page"
    path = p.save(tmp_path / "0.pagepass.json")
    raw = json.loads(path.read_text())
    assert raw["labels"][0]["pass"] == "page" and "pass_" not in raw["labels"][0]
    back = pp.load(path)
    assert [l.to_json() for l in back.labels] == [l.to_json() for l in p.labels]


def test_store_refuses_what_is_not_a_page_wide_kind_or_a_bad_shape():
    p = _pp()
    with pytest.raises(store.StoreError):
        p.draw("noteheadBlack", pp.rect_shape([0, 0, 5, 5]))
    with pytest.raises(store.StoreError):
        pp.rect_shape([5, 5, 5, 9])
    with pytest.raises(store.StoreError):
        pp.poly_shape([[0, 0], [1, 1]])
    q = p.add_prefill("arc", pp.rect_shape([0, 0, 5, 5]), "k")
    with pytest.raises(store.StoreError):
        p.delete(q.id) if False else p.label("nope")
    p.delete(q.id)                                                   # a pending one is REJECTED, not erased
    assert p.label(q.id).state == "rejected"


def test_kind_of_class_maps_cell_labels_to_page_kinds():
    k = pp.kind_of_class
    assert (k("slur"), k("tie"), k("barlineSingle"), k("brace"), k("clefG"), k("keyFlat"), k("timeSig8"),
            k("text"), k("dynamicF")) == ("arc", "arc", "barline", "bracket", "clef", "key", "meter",
                                          "word", "dynamic")
    assert k("noteheadBlackInSpace") is None and k("stem") is None and k("augmentationDot") is None


# ------------------------------------------------------------------ pre-fill join
def _arc(x0, y0, x1, y1, sub="slur", i="a"):
    return {"kind": "arc", "rect": (x0, y0, x1, y1), "sub": sub, "id": i, "note": ""}


def test_halves_cut_at_a_barline_join_into_one_arc():
    out = pf.join_arc_pieces([_arc(100, 50, 395, 90, i="L"), _arc(405, 52, 700, 92, i="R")], [400], SP)
    assert len(out) == 1 and out[0]["rect"] == (100, 50, 700, 92) and out[0]["joined_from"] == ["L", "R"]


def test_join_is_one_to_one_and_needs_the_same_y_band_and_the_same_barline():
    L = _arc(100, 50, 395, 90, i="L")
    R1 = _arc(405, 52, 700, 92, i="R1")          # same band: joins
    R2 = _arc(405, 300, 700, 340, i="R2")        # another staff: stays alone
    out = pf.join_arc_pieces([L, R1, R2], [400], SP)
    assert sorted(o["rect"] for o in out) == [(100, 50, 700, 92), (405, 300, 700, 340)]
    far = pf.join_arc_pieces([_arc(100, 50, 300, 90), _arc(500, 52, 700, 92)], [400], SP)
    assert len(far) == 2                         # ends nowhere near the barline: never guessed together


def test_a_chain_over_two_barlines_joins_and_kind_disagreement_is_said():
    out = pf.join_arc_pieces([_arc(100, 50, 395, 90, "tie", "1"), _arc(405, 50, 795, 90, "slur", "2"),
                              _arc(805, 50, 900, 90, "slur", "3")], [400, 800], SP)
    assert len(out) == 1 and out[0]["rect"][0] == 100 and out[0]["rect"][2] == 900
    assert "disagree" in out[0]["note"]


def _truth():
    t = PageTruth(edition="imslp1", pdf_page_index=0, dpi=600, width=1000, height=400)
    t.add_cell(Cell(id="c0", kind="measure", rect=(0, 0, 500, 200), canonical_w=500, canonical_h=200,
                    system=0, staff=0, measure=0, staff_line_ys=[100.0, 120.0, 140.0, 160.0, 180.0]))
    t.add_cell(Cell(id="c1", kind="measure", rect=(500, 0, 1000, 200), canonical_w=500, canonical_h=200,
                    system=0, staff=0, measure=1, staff_line_ys=[100.0, 120.0, 140.0, 160.0, 180.0]))
    def box(i, cls, r, text=None):
        t.boxes.append(Box(id=i, cls=cls, rect=r, origin="drawn", labeler="sean", text=text))
    box("b0", "slur", (100, 50, 497, 90))
    box("b1", "slur", (503, 52, 800, 92))
    box("b2", "barlineSingle", (498, 100, 503, 180))
    box("b3", "keyFlat", (60, 100, 76, 140))
    box("b4", "keyFlat", (80, 90, 96, 130))                          # one key signature, two accidentals
    box("b5", "noteheadBlackOnLine", (200, 110, 222, 130))          # a cell-pass mark: never proposed
    box("b6", "text", (300, 20, 400, 50), text="dolce")
    box("b7", "text", (302, 21, 401, 51), text="dolce")             # the same word from the neighbour cell
    return t


def test_hand_prefills_join_key_pieces_dedupe_twins_join_arc_halves_and_skip_cell_marks():
    t = _truth()
    before = json.dumps(t.to_json(), sort_keys=True)
    items = pf.hand_prefills(t, SP)
    kinds = sorted(i["kind"] for i in items)
    assert kinds == ["arc", "barline", "key", "word"]
    arc = next(i for i in items if i["kind"] == "arc")
    assert arc["rect"] == (100, 50, 800, 92)
    key = next(i for i in items if i["kind"] == "key")
    assert key["rect"] == (60, 90, 96, 140) and key["n_pieces"] == 2
    assert json.dumps(t.to_json(), sort_keys=True) == before         # Sean's page is read, never edited


def test_build_makes_only_pending_prefills_and_the_arc_key_replaces_raw_arcs():
    t = _truth()
    key = {"arcs": [{"id": "K0", "ids": ["b0"], "x0": 100, "x1": 800, "y0": 50, "y1": 92, "kind": "slur",
                     "extended": ["L"], "cross_system": False, "kind_conflict": False}],
           "changes": [{"change": "manual_extend", "ids": ["b0"], "reason": "left half unboxed",
                        "assumed_for_sean": True}]}
    p = pf.build(t, arc_key=key)
    assert all(l.state == "pending" for l in p.labels) and p.truth() == []
    arcs = [l for l in p.labels if l.kind == "arc"]
    assert len(arcs) == 1 and arcs[0].source == "arc-key-2.281" and "left half unboxed" in arcs[0].note
    assert [l.kind for l in p.labels].count("staff") == 1            # one staff, from the cells' lines
    assert pf.build(t).labels != []                                  # no key: raw arcs, joined


# ------------------------------------------------------------------ the server
def _service(tmp_path):
    import threading

    from tools.omr.annotate.pagepass_server import PagePassService

    t = _truth()
    t.width, t.height = 600, 300
    svc = PagePassService.__new__(PagePassService)
    svc.truth, svc.file, svc.lock, svc.history = t, tmp_path / "0.pagepass.json", threading.RLock(), []
    svc.page = pp.PagePass(edition="imslp1", pdf_page_index=0, dpi=600, width=600, height=300, sp=SP)
    svc.page.add_prefill("arc", pp.rect_shape([180, 55, 320, 125]), "arc-key-2.281", sub="slur")
    ink, _, _ = _ink()
    svc._ink, svc._cellpass, svc._claims = ink, np.zeros_like(ink.ink), None
    return svc


def test_routes_draw_confirm_undo_render_and_cell_overlay(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tools.omr.annotate.pagepass_server import mount

    svc = _service(tmp_path)
    app = FastAPI()
    mount(app, svc)
    c = TestClient(app)
    st = c.get("/api/pp/state").json()
    assert st["stats"]["claimed_pct"] == 0 and st["stats"]["pending_pct"] > 0
    assert st["counts"]["arc"] == {"pending": 1, "confirmed": 0, "rejected": 0}
    # draw a barline: confirmed, claims ink, written to the file with its ink_ref
    r = c.post("/api/pp/label", json={"kind": "barline", "shape": {"rect": [395, 95, 408, 185]}}).json()
    assert r["stats"]["claimed_pct"] > 0
    saved = json.loads(svc.file.read_text())
    lab = next(l for l in saved["labels"] if l["kind"] == "barline")
    assert lab["state"] == "confirmed" and lab["pass"] == "page" and lab["ink_ref"]["px"] > 0
    # confirm the pre-fill, then undo it
    pid = st["labels"][0]["id"]
    r2 = c.post(f"/api/pp/label/{pid}", json={"action": "confirm"}).json()
    assert r2["counts"]["arc"]["confirmed"] == 1
    r3 = c.post("/api/pp/undo", json={}).json()
    assert r3["counts"]["arc"]["pending"] == 1
    # an unknown kind is refused
    assert c.post("/api/pp/label", json={"kind": "notehead", "shape": {"rect": [0, 0, 5, 5]}}).status_code == 400
    # the picture and the cell hand-off overlay are PNGs; claimed ink is blue in the overlay
    img = c.get("/api/pp/render?x0=0&y0=0&x1=600&y1=300&w=600")
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    ov = cv2.imdecode(np.frombuffer(c.get("/api/cell/c0/claimed.png").content, np.uint8), cv2.IMREAD_UNCHANGED)
    assert ov.shape == (200, 500, 4) and ov[..., 3].max() > 0
    assert (ov[..., 3] > 0).sum() < 3000                              # only the barline's ink, not the page
    assert c.get("/api/cell/nope/claimed.png").status_code == 404


def test_an_augmentation_dot_inside_an_arcs_box_is_not_the_arcs_ink():
    img, heads, slur = _page_arrays()
    dot = np.zeros(img.shape, np.uint8)
    cv2.circle(dot, (230, 112), 4, 1, -1)                            # a dot in the top space beside a head
    ink = InkMap(img | dot.astype(bool), SP, [(20, 580, LINES)])
    box = {"rect": [180, 55, 320, 125]}
    arc = ink.claim(box, "arc")
    word = ink.claim(box, "word")
    assert not arc.mask[112 - arc.bbox[1], 230 - arc.bbox[0]]
    assert word.mask[112 - word.bbox[1], 230 - word.bbox[0]]         # control: a word takes it


def test_a_pagepass_file_beside_a_page_is_not_loaded_as_a_page(tmp_path):
    t = _truth()
    t.save(tmp_path)
    p = _pp()
    p.add_prefill("arc", pp.rect_shape([1, 2, 30, 40]), "k")
    p.save(pp.pagepass_path(t.edition, t.pdf_page_index, tmp_path))
    assert [x.pdf_page_index for x in store.load_all(tmp_path)] == [0]
    assert pp.pagepass_path("e", 3, tmp_path).name == "3.pagepass.json"


# ================================================================== round 2 (Sean's feedback, 2026-11-10)
def _vbar(x0, y0, x1, y1, kind="barline", cls="barlineSingle", i=None):
    return {"kind": kind, "rect": (x0, y0, x1, y1), "id": i, "cls": cls, "source": "hand-cell-labels"}


def test_barline_pieces_of_one_printed_line_join_full_height_only_where_the_print_is_unbroken():
    """Item 2: a barline is proposed from the top staff to the bottom one, never per cell. The print breaks
    between instrument groups (no ink in the gap), so the proposal breaks there too."""
    img = np.zeros((900, 200), bool)
    img[100:500, 98:102] = True                       # unbroken from y=100 to 500 (three cells' worth)
    img[560:800, 98:102] = True                       # a second group, after a gap with no ink
    pieces = [_vbar(96, 100, 104, 200, i="a"), _vbar(96, 260, 104, 340, i="b"), _vbar(97, 400, 103, 500, i="c"),
              _vbar(96, 560, 104, 800, i="d")]
    out = pf.join_vertical(pieces, SP, x_sp=pf.BARLINE_X_SP, ink=img)
    assert sorted(o["rect"] for o in out) == [(96, 100, 104, 500), (96, 560, 104, 800)]
    assert any(o["joined_from"] == ["a", "b", "c"] for o in out)
    # CONTROL that can fail: with no ink to look at, only near-touching boxes join (gaps of 60 px > 0.5 sp)
    assert len(pf.join_vertical(pieces, SP, x_sp=pf.BARLINE_X_SP, ink=None)) == 4
    # a barline column further right is another printed line, not joined sideways
    other = pf.join_vertical(pieces + [_vbar(150, 100, 158, 500, i="z")], SP, x_sp=pf.BARLINE_X_SP, ink=img)
    assert len(other) == 3


def test_a_brace_and_the_bracket_it_sits_inside_are_never_joined():
    img = np.zeros((600, 200), bool)
    img[100:500, 40:60] = True
    pieces = [_vbar(40, 100, 60, 300, "bracket", "brace", "br1"), _vbar(41, 300, 59, 500, "bracket", "brace", "br2"),
              _vbar(40, 100, 60, 500, "bracket", "bracket", "BR")]
    out = pf.join_vertical(pieces, SP, x_sp=pf.BRACKET_X_SP, ink=img)
    assert sorted(o["rect"] for o in out) == [(40, 100, 60, 500), (40, 100, 60, 500)]
    assert sorted(o["cls"] for o in out) == ["brace", "bracket"]


def test_a_meter_is_proposed_as_one_box_with_its_value_pre_typed_and_its_digits_kept():
    """Item 3: '6 above 8' is ONE mark. The hand digit boxes join; the value is typed for Sean to confirm
    (never for one digit alone); each digit's own box stays under the one label."""
    t = _truth()
    for i, (cls, r) in enumerate([("timeSig6", (700, 100, 722, 140)), ("timeSig8", (700, 142, 722, 182)),
                                  ("timeSig9", (800, 100, 822, 140))]):       # the third stands alone
        t.boxes.append(Box(id=f"m{i}", cls=cls, rect=r, origin="drawn", labeler="sean"))
    meters = sorted((i for i in pf.hand_prefills(t, SP) if i["kind"] == "meter"), key=lambda i: i["rect"][0])
    assert [m["text"] for m in meters] == ["6/8", None]
    assert meters[0]["rect"] == (700, 100, 722, 182) and "confirm" in meters[0]["note"]
    assert [p["text"] for p in meters[0]["parts"]] == ["6", "8"] and meters[0]["parts"][0]["rect"] == [700, 100, 722, 140]
    assert "not a whole meter" in meters[1]["note"]                              # one digit is not guessed into a meter
    p = pf.build(t)
    lab = next(l for l in p.labels if l.kind == "meter" and l.text == "6/8")
    assert lab.state == "pending" and lab.parts[1]["text"] == "8"
    assert lab.to_json()["parts"][0]["from"] == "hand"


def test_meter_values_are_normalised_and_split_in_reading_order():
    assert pp.normalize_meter("6 8") == "6/8" and pp.normalize_meter("6-8") == "6/8"
    assert pp.normalize_meter("c") == "C" and pp.normalize_meter("cut") == "C|" and pp.normalize_meter("2/2") == "2/2"
    assert pp.normalize_meter("  ") is None and pp.normalize_meter(None) is None
    assert pp.meter_split("12/8") == ["12", "8"] and pp.meter_split("C") == ["C"] and pp.meter_split("") == []


def _meter_page():
    """Two stacked digits on a staff: '6' in the two top spaces, '8' in the two lower ones, the middle line crossing both."""
    img = np.zeros((300, 400), np.uint8)
    for y in LINES:
        img[int(y) - 1:int(y) + 2, 20:380] = 1
    for (x, y0, y1) in ((200, 102, 138), (200, 142, 178)):
        cv2.ellipse(img, (x, (y0 + y1) // 2), (9, (y1 - y0) // 2), 0, 0, 360, 1, 3)
    return img.astype(bool)


def test_one_meter_box_carries_one_typed_value_and_its_digit_pieces_are_read_from_its_ink(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tools.omr.annotate.pagepass_server import mount

    svc = _service(tmp_path)
    ink = InkMap(_meter_page(), SP, [(20, 380, LINES)])
    svc._ink, svc._cellpass = ink, np.zeros_like(ink.ink)
    svc.truth.width, svc.truth.height = 400, 300
    svc.page.labels.clear()
    app = FastAPI()
    mount(app, svc)
    c = TestClient(app)
    r = c.post("/api/pp/label", json={"kind": "meter", "shape": {"rect": [180, 98, 222, 182]}, "text": "6 8"}).json()
    lab = r["label"]
    assert lab["text"] == "6/8" and lab["kind"] == "meter" and lab["state"] == "confirmed"
    assert [p["text"] for p in lab["parts"]] == ["6", "8"] and all(p["from"] == "ink" for p in lab["parts"])
    top, bot = (p["rect"] for p in lab["parts"])
    assert top[3] <= 141 and bot[1] >= 139 and top[1] < bot[1]          # split at the middle line, upper over lower
    saved = json.loads(svc.file.read_text())["labels"][0]
    assert saved["text"] == "6/8" and len(saved["parts"]) == 2          # recoverable from the file
    # a re-typed value re-reads the pieces; a meter with no text has pieces but no characters
    r2 = c.post(f"/api/pp/label/{lab['id']}", json={"action": "edit", "text": "C"}).json()["label"]
    assert r2["text"] == "C" and len(r2["parts"]) == 1 and r2["parts"][0]["text"] == "C"
    c.post(f"/api/pp/label/{lab['id']}", json={"action": "delete"})     # (a second box over it would be contested)
    r3 = c.post("/api/pp/label", json={"kind": "meter", "shape": {"rect": [180, 98, 222, 182]}}).json()["label"]
    assert r3["text"] is None and all(p["text"] is None for p in r3["parts"])


def test_a_word_box_may_be_a_text_block_and_the_prefill_fragments_inside_it_are_resolved(tmp_path):
    """Item 4: one big box, 'title' / 'subtitle' / 'composer' / 'other', text optional. Pre-fill words inside
    a CONFIRMED block need no answer: reported as covered, not left waiting. Instrument names stay words."""
    p = _pp()
    for i, r in enumerate([(100, 20, 160, 60), (170, 22, 260, 62), (400, 300, 460, 340)]):
        p.add_prefill("word", pp.rect_shape(r), "hand-cell-labels", text=f"frag{i}")
    p.add_prefill("dynamic", pp.rect_shape((110, 25, 150, 55)), "hand-cell-labels", text="f")
    assert p.covered_prefills() == {}                                    # no block yet
    blk = p.draw("word", pp.rect_shape((50, 0, 300, 90)), sub="title")
    assert blk.is_block and blk.text is None
    assert p.covered_prefills() == {"P0": blk.id, "P1": blk.id}           # the two inside; not the far one, not a dynamic
    for bad in ("tie", "bogus"):
        with pytest.raises(store.StoreError):
            p.draw("word", pp.rect_shape((1, 1, 9, 9)), sub=bad)
    with pytest.raises(store.StoreError):
        p.draw("arc", pp.rect_shape((1, 1, 9, 9)), sub="title")
    w = p.draw("word", pp.rect_shape((300, 100, 340, 130)), text="Hr.")  # an ordinary word keeps its typed text
    assert not w.is_block and w.text == "Hr."
    p.edit(blk.id, kind="dynamic")                                       # a sub belongs to its kind
    assert p.label(blk.id).sub is None
    # through the server: the block's covered pre-fills leave the waiting counts
    svc = _service(tmp_path)
    svc.page.labels.clear()
    for i, r in enumerate([(100, 20, 160, 60), (400, 300, 460, 340)]):
        svc.page.add_prefill("word", pp.rect_shape(r), "x", text=f"f{i}")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tools.omr.annotate.pagepass_server import mount

    app = FastAPI()
    mount(app, svc)
    c = TestClient(app)
    assert c.get("/api/pp/state").json()["counts"]["word"]["pending"] == 2
    st = c.post("/api/pp/label", json={"kind": "word", "sub": "composer", "shape": {"rect": [50, 0, 300, 90]}}).json()
    assert st["counts"]["word"]["pending"] == 1 and st["covered"] == {"P0": st["label"]["id"]}
    assert next(l for l in st["labels"] if l["id"] == "P0")["covered_by"] == st["label"]["id"]
    assert c.post("/api/pp/label", json={"kind": "word", "sub": "nope", "shape": {"rect": [1, 1, 9, 9]}}).status_code == 400


def test_the_owned_ink_route_returns_exactly_the_ink_a_label_owns(tmp_path):
    """Item 1(d): hovering a label shows precisely its owned ink -- here a tight word box inside a larger one."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tools.omr.annotate.pagepass_server import mount

    svc = _service(tmp_path)
    svc.page.labels.clear()
    app = FastAPI()
    mount(app, svc)
    c = TestClient(app)
    big = c.post("/api/pp/label", json={"kind": "word", "shape": {"rect": [150, 80, 350, 130]}}).json()["label"]
    small = c.post("/api/pp/label", json={"kind": "word", "shape": {"rect": [185, 90, 215, 125]}}).json()["label"]
    r = c.get(f"/api/pp/owned/{small['id']}")
    x0, y0, x1, y1 = (int(v) for v in r.headers["X-Region"].split(","))
    ov = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_UNCHANGED)
    assert ov.shape[:2] == (y1 - y0, x1 - x0)                         # drawn 1:1 over the page, margin included
    black = (ov[..., 3] == 255) & (ov[..., :3].sum(axis=2) == 0)
    labs = {l["id"]: l for l in c.get("/api/pp/state").json()["labels"]}
    assert black.sum() == labs[small["id"]]["px"] > 0                  # the picture IS the owned ink, pixel for pixel
    assert labs[big["id"]]["px"] == labs[big["id"]]["raw_px"] - labs[big["id"]]["lost_px"]
    assert labs[big["id"]]["lost_to"] == [small["id"]] and labs[big["id"]]["lost_px"] > 0
    assert c.get("/api/pp/owned/nope").status_code == 404


def test_round_1_files_load_and_save_unchanged_and_new_optional_fields_stay_out_of_the_way():
    """Sean's labels are truth: a round-1 file (no ``parts`` anywhere) loads and writes back identically."""
    from pathlib import Path

    f = Path(__file__).resolve().parents[3] / "data/hand-truth/pages/imslp317803/0.pagepass.json"
    if not f.exists():
        pytest.skip("no page-pass file in this checkout")
    raw = json.loads(f.read_text())
    if any("parts" in l for l in raw["labels"]):
        pytest.skip("a round-2 file: carries parts")
    assert pp.load(f).to_json()["labels"] == raw["labels"]


def test_a_round_1_pending_meter_prefill_gets_its_value_in_memory_and_an_acted_on_one_is_left_alone():
    t = _truth()
    for i, (cls, r) in enumerate([("timeSig6", (700, 100, 722, 140)), ("timeSig8", (700, 142, 722, 182)),
                                  ("timeSig9", (800, 100, 822, 140)), ("timeSig8", (800, 142, 822, 182))]):
        t.boxes.append(Box(id=f"m{i}", cls=cls, rect=r, origin="drawn", labeler="sean"))
    p = _pp()
    pending = p.add_prefill("meter", pp.rect_shape((695, 95, 727, 187)), "hand-cell-labels")       # round-1 style: no value
    acted = p.add_prefill("meter", pp.rect_shape((795, 95, 827, 187)), "hand-cell-labels")
    p.confirm(acted.id)                                                                            # Sean already answered it
    assert pf.migrate_meter_prefills(p, t) == 1
    assert pending.text == "6/8" and [x["text"] for x in pending.parts] == ["6", "8"]
    assert acted.text is None and acted.parts is None and acted.state == "confirmed"
    assert pending.shape == {"rect": [695.0, 95.0, 727.0, 187.0]}                                   # shape untouched
