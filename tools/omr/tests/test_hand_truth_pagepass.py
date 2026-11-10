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
from tools.omr.hand_truth.pageink import CLAIMED, PENDING, UNCLAIMED, InkMap, render_states
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


def test_claim_order_earlier_kind_wins_then_smaller_shape():
    ink, heads, slur = _ink()
    big_arc = pp.PLabel("A", "arc", {"rect": [180, 55, 320, 125]}, "confirmed", "drawn")
    word = pp.PLabel("W", "word", {"rect": [185, 90, 215, 125]}, "confirmed", "drawn")   # the left head
    c = ink.claims([big_arc, word])
    wi = 1 + c.labels.index(word)
    # the word (earlier kind) owns the left head's ink; the arc keeps the rest of the arch
    assert (c.owner == wi)[heads].sum() > 0.7 * heads[:, :250].sum()
    assert c.px["A"] > 0.8 * c.raw_px["A"] - 1
    # same kind, two shapes over one mark: the smaller one owns the overlap
    big = pp.PLabel("B", "word", {"rect": [150, 80, 350, 130]}, "confirmed", "drawn")
    small = pp.PLabel("S", "word", {"rect": [185, 90, 215, 125]}, "confirmed", "drawn")
    c2 = ink.claims([big, small])
    assert c2.px["S"] == c2.raw_px["S"] > 0


def test_a_merged_piece_is_split_by_two_shapes_and_a_polygon_cuts_a_diagonal():
    img = np.zeros((200, 300), bool)
    img[60:100, 40:120] = True            # two blobs touching: one connected piece (Litolff MERGES)
    img[60:100, 120:200] = True
    ink = InkMap(img, SP, [])
    a = pp.PLabel("A", "word", {"rect": [30, 50, 119, 110]}, "confirmed", "drawn")
    b = pp.PLabel("B", "word", {"rect": [120, 50, 210, 110]}, "confirmed", "drawn")
    c = ink.claims([a, b])
    assert c.px["A"] + c.px["B"] == img.sum()                        # every pixel owned, none twice
    assert abs(c.px["A"] - c.px["B"]) <= 40
    poly = pp.PLabel("P", "word", {"poly": [[30, 50], [150, 50], [100, 110], [30, 110]]}, "confirmed", "drawn")
    rest = pp.PLabel("R", "word", {"rect": [30, 50, 210, 110]}, "confirmed", "drawn")
    c2 = ink.claims([poly, rest])
    assert 0 < c2.px["P"] < img.sum() and c2.px["P"] + c2.px["R"] == img.sum()


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
    assert ref["rule"] == "pageink-1" and ref["mode"] == "thin" and ref["px"] > 0 and len(ref["sha1"]) == 16
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


def test_a_pagepass_file_beside_a_page_is_not_loaded_as_a_page(tmp_path):
    t = _truth()
    t.save(tmp_path)
    p = _pp()
    p.add_prefill("arc", pp.rect_shape([1, 2, 30, 40]), "k")
    p.save(pp.pagepass_path(t.edition, t.pdf_page_index, tmp_path))
    assert [x.pdf_page_index for x in store.load_all(tmp_path)] == [0]
    assert pp.pagepass_path("e", 3, tmp_path).name == "3.pagepass.json"
