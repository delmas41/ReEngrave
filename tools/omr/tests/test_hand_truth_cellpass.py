"""ROADMAP 2.287 round 3: the cell pass (pass 2) -- store, pre-fill import and auto-resolve, the ink rule per kind
(each with a control that can fail), bulk confirm + undo, the queue percentages, "pass 2 never takes pass-1 ink".

Synthetic pages only (no PDF, no library): staff space 32 px, staff lines 7 px thick, two beamed notes, a ledger-line
note, a sharp (own piece with tall strokes), a dot, a speck, a barline claimed by pass 1.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import cv2
import numpy as np
import pytest

from tools.omr.hand_truth import cellink, cellpass as cpm
from tools.omr.hand_truth import pagepass as pp
from tools.omr.hand_truth.pageink import InkMap
from tools.omr.hand_truth.store import Box, Cell, PageTruth

SP = 32.0
LINES = [150.0, 182.0, 214.0, 246.0, 278.0]
W, H = 700, 420


def _page():
    """ink (bool) and named element masks."""
    el = {}

    def m():
        return np.zeros((H, W), np.uint8)

    lines = m()
    for y in LINES:
        lines[int(y) - 3:int(y) + 4, 20:680] = 1
    el["lines"] = lines
    heads = m()
    for cx in (200, 310):
        cv2.ellipse(heads, (cx, 262), (19, 13), -20, 0, 360, 1, -1)     # filled heads in the bottom space
    el["heads"] = heads
    stems = m()
    stems[170:262, 217:222] = 1
    stems[170:262, 327:332] = 1
    el["stems"] = stems
    beam = m()
    beam[160:176, 215:334] = 1                                           # a 16 px beam between the stems
    el["beam"] = beam
    ledger = m()
    ledger[307:314, 470:530] = 1                                         # a ledger line under the staff
    head3 = m()
    cv2.ellipse(head3, (500, 310), (19, 13), -20, 0, 360, 1, -1)         # its head, on the line
    el["ledger"] = ledger
    el["head3"] = head3
    dot = m()
    cv2.circle(dot, (255, 262), 5, 1, -1)
    el["dot"] = dot
    sharp = m()
    sharp[190:254, 392:396] = 1                                          # two TALL strokes (64 px >= 1.5 sp) ...
    sharp[190:254, 402:406] = 1
    sharp[208:213, 388:410] = 1                                          # ... and two crossbars: a piece with no head
    sharp[230:235, 388:410] = 1
    el["sharp"] = sharp
    speck = m()
    speck[100:103, 600:603] = 1
    el["speck"] = speck
    fringe = m()
    fringe[141:144, 100:300] = 1                                         # a 3 px sliver beside line 1, outside its band: the fringe
    el["fringe"] = fringe
    bar = m()
    bar[140:292, 590:594] = 1                                            # a barline: pass 1 claims it
    el["bar"] = bar
    ink = np.zeros((H, W), np.uint8)
    for k, v in el.items():
        ink |= v
    return ink.astype(bool), {k: v.astype(bool) for k, v in el.items()}


class _PS:
    """The page-pass service as far as pass 2 reads it: truth, lock, ink(), claims() (pass 1 = the staff + barline)."""

    def __init__(self, tmp: Path, page_labels=None):
        self.lock = threading.RLock()
        self.page_store = tmp / "pages" / "imslp1" / "0.json"
        self.truth = PageTruth(edition="imslp1", pdf_page_index=0, dpi=600, width=W, height=H)
        self.truth.add_cell(Cell(id="c0", kind="measure", rect=(0, 100, 350, 340), canonical_w=350, canonical_h=240,
                                 system=0, staff=0, measure=0, staff_line_ys=[y - 100 for y in LINES]))
        self.truth.add_cell(Cell(id="c1", kind="measure", rect=(350, 100, 700, 340), canonical_w=350, canonical_h=240,
                                 system=0, staff=0, measure=1, staff_line_ys=[y - 100 for y in LINES]))
        ink, self.el = _page()
        self._ink = InkMap(ink, SP, [(20, 680, LINES)])
        pg = pp.PagePass(edition="imslp1", pdf_page_index=0, dpi=600, width=W, height=H, sp=SP)
        pg.draw("staff", pp.rect_shape([15, 140, 685, 290]))
        pg.draw("barline", pp.rect_shape([585, 135, 598, 295]))
        self.page = pg
        self._cl = self._ink.claims(pg.claimers())

    def ink(self):
        return self._ink

    def claims(self):
        return self._cl


def _service(tmp_path, boxes=()):
    from tools.omr.annotate.cellpass_server import CellPassService

    ps = _PS(tmp_path)
    for i, (cls, r, cell) in enumerate(boxes):
        ps.truth.boxes.append(Box(id=f"b{i}", cls=cls, rect=r, origin="drawn", labeler="sean", cell_id=cell))
    return CellPassService(ps, cellpass_file=tmp_path / "0.cellpass.json"), ps


def _ci(ps=None):
    ps = ps or _PS(Path("."))
    pc = ps.claims()
    ink = ps.ink()
    lut = np.zeros(len(pc.labels) + 1, bool)
    for i, lab in enumerate(pc.labels):
        lut[i + 1] = lab.state == "confirmed"
    p1 = lut[pc.owner] & ink.ink
    return cellink.CellInk(ink.ink & ~p1, SP, ink.line, ink.line_thickness, ink.hb), p1, ps.el


def _taken(ci, shape, kind):
    c = ci.claim(shape, kind)
    out = np.zeros((H, W), bool)
    if c.mask.size:
        x0, y0, x1, y1 = c.bbox
        out[y0:y1, x0:x1] = c.mask
    return out


# ------------------------------------------------------------------ the ink rule per kind (each with a control)
def test_a_head_box_takes_the_head_and_not_the_stem_beside_it_and_the_control_fails_where_it_should():
    ci, p1, el = _ci()
    box = {"rect": [170, 195, 232, 280]}                           # the first head AND the lower part of its stem
    head = _taken(ci, box, "notehead")
    assert (head & el["heads"] & ~p1).sum() > 0.8 * (el["heads"][:, :260] & ~p1[:, :260]).sum() / 2
    assert (head & el["stems"] & ~el["heads"]).sum() == 0          # never the stem
    # CONTROL: `noise` takes every free pixel in the same box, stem included: the test above can fail
    noise = _taken(ci, box, "noise")
    assert (noise & el["stems"] & ~el["heads"] & ~p1).sum() > 0


def test_a_stem_box_takes_the_stem_and_neither_the_head_nor_the_beam():
    ci, p1, el = _ci()
    box = {"rect": [205, 150, 232, 285]}                           # head's right edge, the stem, and the beam's end
    stem = _taken(ci, box, "stem")
    assert stem.sum() > 0
    assert (stem & el["stems"] & ~p1).sum() > 0.9 * stem.sum()      # all stem
    # (the joint: one pixel column either side of the stem's edge, a few pixels, never a head or a beam)
    assert (stem & (el["heads"] | el["beam"]) & ~el["stems"]).sum() <= 0.05 * stem.sum()
    assert (stem & el["heads"] & ~el["stems"]).sum() <= 0.03 * el["heads"].sum()
    # CONTROLS: the same box as a notehead takes the head (none of the stem); as a beam it takes the beam
    assert (_taken(ci, box, "notehead") & el["stems"] & ~el["heads"]).sum() == 0
    assert (_taken(ci, {"rect": [205, 150, 345, 185]}, "beam") & el["beam"]).sum() > 0.8 * el["beam"].sum()
    # a stem box over a head alone (no stem in it) takes nothing
    assert _taken(ci, {"rect": [185, 250, 215, 276]}, "stem").sum() == 0


def test_a_beam_box_takes_the_beam_whole_and_a_box_mostly_outside_does_not_cut_it():
    ci, p1, el = _ci()
    b = _taken(ci, {"rect": [210, 155, 340, 180]}, "beam")
    assert (b & el["beam"]).sum() >= 0.9 * el["beam"].sum()
    assert (b & el["heads"]).sum() == 0
    small = _taken(ci, {"rect": [215, 155, 250, 180]}, "beam")      # holds ~30% of the beam: not cut
    assert small.sum() == 0
    # CONTROL: a polygon DOES cut at its edge -- the same small region as a polygon takes that part
    poly = _taken(ci, {"poly": [[215, 155], [250, 155], [250, 180], [215, 180]]}, "beam")
    assert 0 < (poly & el["beam"]).sum() < 0.5 * el["beam"].sum()


def test_a_ledger_box_takes_the_stubs_either_side_of_the_head_and_the_head_box_takes_none_of_it():
    ci, p1, el = _ci()
    box = {"rect": [465, 285, 535, 335]}
    led = _taken(ci, box, "ledger")
    assert led.sum() > 0 and (led & el["head3"] & ~el["ledger"]).sum() == 0
    assert (led & el["ledger"]).sum() > 0.9 * led.sum()
    head = _taken(ci, box, "notehead")
    assert (head & el["head3"]).sum() > 0.5 * (el["head3"] & ~p1).sum()
    # CONTROL: the ledger rule is the stubs only -- it never claims the middle of the head
    assert (led & el["head3"] & ~el["ledger"]).sum() == 0


def test_a_sharps_tall_strokes_are_not_stems_and_the_dot_is_its_own_piece():
    ci, p1, el = _ci()
    box = {"rect": [385, 185, 413, 258]}
    assert _taken(ci, box, "stem").sum() == 0                      # no head in the piece: no stem
    acc = _taken(ci, box, "accidental")
    assert (acc & el["sharp"] & ~p1).sum() > 0.95 * (el["sharp"] & ~p1).sum()
    # CONTROL: the same strokes WITH a head in their piece would be a stem: the stem rule is what is being tested
    assert (_taken(ci, {"rect": [205, 150, 232, 285]}, "stem")).sum() > 0
    dot = _taken(ci, {"rect": [244, 251, 266, 273]}, "dot")
    assert (dot & el["dot"]).sum() > 0.9 * el["dot"].sum()


def test_noise_takes_a_speck_and_the_staff_fringe_is_its_own_role():
    ci, p1, el = _ci()
    n = _taken(ci, {"rect": [595, 95, 608, 108]}, "noise")
    assert (n & el["speck"]).sum() == el["speck"].sum()
    # the 2 px sliver beside staff line 1 is `edge`, taken by staffedge (clipped at its box), by no head / stem
    strip = {"rect": [90, 136, 310, 156]}
    e = _taken(ci, strip, "staffedge")
    assert (e & el["fringe"]).sum() > 0.9 * el["fringe"].sum()
    assert _taken(ci, strip, "stem").sum() == 0 and _taken(ci, strip, "notehead").sum() == 0
    half = _taken(ci, {"rect": [90, 136, 200, 156]}, "staffedge")   # a box on part of a strand takes what it holds
    assert 0 < (half & el["fringe"]).sum() < 0.7 * el["fringe"].sum()


def test_pass_two_never_takes_pass_one_ink():
    """CLAIMED INK IS FINAL: whatever the kind and the shape, a pass-2 claim holds no pixel pass 1 owns."""
    ci, p1, el = _ci()
    assert (p1 & el["bar"]).sum() > 0 and (p1 & el["lines"]).sum() > 0
    for kind in cellink.KIND_ROLES:
        for shape in ({"rect": [0, 0, W, H]}, {"rect": [580, 130, 600, 300]},
                      {"poly": [[10, 10], [690, 10], [690, 410], [10, 410]]}):
            assert (_taken(ci, shape, kind) & p1).sum() == 0, (kind, shape)
    # CONTROL: pass-1 ink does exist inside those boxes, so the zero above is not an empty page
    assert _taken(ci, {"rect": [0, 0, W, H]}, "noise").sum() == ci.free.sum() < _page()[0].sum()


# ------------------------------------------------------------------ the store
def test_cell_kinds_follow_the_class_and_a_page_wide_class_belongs_to_pass_one():
    k = cpm.cell_kind_of_class
    assert k("noteheadHalfInSpace") == "notehead" and k("stem") == "stem" and k("beam") == "beam"
    assert k("flag8thDown") == "flag" and k("ledgerLine") == "ledger" and k("augmentationDot") == "dot"
    assert k("accidentalSharp") == "accidental" and k("restWhole") == "rest" and k("tremolo1") == "tremolo"
    assert k("articStaccatoAbove") == "articulation" and k("tuplet3") == "tuplet" and k("noise") == "noise"
    for page_wide in ("slur", "tie", "barlineSingle", "clefG", "keyFlat", "timeSig8", "text", "dynamicF", "brace"):
        assert k(page_wide) is None, page_wide


def test_the_old_boxes_become_pending_prefills_and_page_wide_boxes_are_dropped(tmp_path):
    svc, ps = _service(tmp_path, [("noteheadBlackInSpace", (180, 245, 222, 280), "c0"), ("stem", (216, 170, 223, 262), "c0"),
                                  ("slur", (100, 50, 300, 90), "c0"), ("barlineSingle", (588, 140, 596, 290), "c1"),
                                  ("clefG", (30, 140, 60, 290), "c0")])
    cp = svc.cp
    pend = [l for l in cp.labels if l.source == "hand-p0"]
    assert [l.kind for l in pend] == ["notehead", "stem"]
    assert all(l.state == "pending" and l.origin == "prefill" and l.pass_ == "cell" for l in pend)
    assert cp.truth() == []                                         # a pre-fill is never truth by itself
    edges = [l for l in cp.labels if l.source == "staff-edge"]
    assert len(edges) == 2 and {l.cell_id for l in edges} == {"c0", "c1"}


def test_a_prefill_whose_ink_pass_one_already_claimed_is_resolved_and_counted_not_left_waiting(tmp_path):
    svc, ps = _service(tmp_path, [("noteheadBlackInSpace", (180, 245, 222, 280), "c0"),
                                  ("stem", (588, 140, 596, 290), "c1")])        # a 'stem' drawn on the barline pass 1 owns
    st = svc.state_payload()
    by = {l["cls"]: l for l in st["labels"]}
    assert by["stem"].get("auto_pct", 0) >= 90 and "auto_pct" not in by["noteheadBlackInSpace"]
    assert st["totals"]["auto_resolved"] == 1
    assert next(c for c in st["cells"] if c["id"] == "c1")["waiting"] == 0       # resolved: not waiting for him
    assert st["totals"]["empty"] >= 1                                              # c1's staff-edge strip has no fringe to take
    # CONTROL: take pass 1's barline away and the same box is NOT resolved
    svc2, _ = _service(tmp_path / "x", [("stem", (588, 140, 596, 290), "c1")])
    ps2 = svc2.ps
    ps2.page.labels[:] = [l for l in ps2.page.labels if l.kind != "barline"]
    ps2._cl = ps2._ink.claims(ps2.page.claimers())
    svc2._src = None
    assert svc2.state_payload()["totals"]["auto_resolved"] == 0


def test_the_store_round_trips_and_refuses_a_confirmed_bare_prefill(tmp_path):
    cp = cpm.CellPass(edition="imslp1", pdf_page_index=0, dpi=600, width=W, height=H, sp=SP)
    q = cp.add_prefill("notehead", "noteheadHalfOnLine", pp.rect_shape([1, 2, 30, 40]), "hand-p0", cell_id="c0", box_id="b1")
    assert q.state == "pending" and cp.truth() == [] and len(cp.claimers()) == 1
    cp.confirm(q.id)
    assert cp.label(q.id).origin == "prefill-confirmed" and len(cp.truth()) == 1
    q2 = cp.add_prefill("stem", "stem", pp.rect_shape([1, 2, 30, 40]), "k")
    cp.edit(q2.id, shape=pp.rect_shape([5, 5, 50, 50]))              # fixing a pre-fill confirms it AS FIXED
    assert cp.label(q2.id).origin == "prefill-fixed"
    q3 = cp.add_prefill("beam", "beam", pp.rect_shape([0, 0, 9, 9]), "k")
    cp.reject(q3.id)
    assert q3.id not in [l.id for l in cp.claimers()]
    d = cp.draw("noise", None, pp.rect_shape([0, 0, 9, 9]), cell_id="c1")
    assert d.cls == "noise" and d.origin == "drawn" and d.pass_ == "cell"
    path = cp.save(tmp_path / "0.cellpass.json")
    raw = json.loads(path.read_text())
    assert raw["labels"][0]["pass"] == "cell" and "pass_" not in raw["labels"][0]
    assert [l.to_json() for l in cpm.load(path).labels] == [l.to_json() for l in cp.labels]
    bad = cpm.CLabel(id="x", kind="notehead", cls="stem", shape={"rect": [0, 0, 1, 1]}, state="confirmed", origin="prefill")
    with pytest.raises(Exception):
        bad.validate()


def test_a_cellpass_file_beside_a_page_is_not_loaded_as_a_page(tmp_path):
    from tools.omr.hand_truth import store

    t = PageTruth(edition="imslp1", pdf_page_index=0, dpi=600, width=W, height=H)
    t.save(tmp_path)
    cp = cpm.CellPass(edition="imslp1", pdf_page_index=0, dpi=600, width=W, height=H)
    cp.save(cpm.cellpass_path("imslp1", 0, tmp_path))
    assert [p.pdf_page_index for p in store.load_all(tmp_path)] == [0] and len(store.load_all(tmp_path)) == 1


def test_the_real_page_file_gives_the_prefill_counts_sean_was_told():
    from tools.omr.hand_truth import store

    f = Path(__file__).resolve().parents[3] / "data/hand-truth/pages/imslp317803/0.json"
    if not f.exists():
        pytest.skip("no page file in this checkout")
    t = store.load(f)
    before = f.read_bytes()
    cp, counts = cpm.build(t)
    assert counts["imported"] == 1232 and counts["dropped_page_wide"] == len(t.boxes) - 1232
    assert counts["staff_edge"] == sum(1 for c in t.cells if c.kind == "measure" and c.staff_line_ys)
    assert f.read_bytes() == before                                  # reading the page file never writes it


# ------------------------------------------------------------------ the service: bulk, undo, queue, done
def _boxes():
    return [("noteheadBlackInSpace", (178, 247, 222, 278), "c0"), ("noteheadBlackInSpace", (288, 247, 332, 278), "c0"),
            ("stem", (213, 168, 226, 250), "c0"), ("stem", (323, 168, 336, 250), "c0"),
            ("beam", (212, 156, 337, 180), "c0"), ("augmentationDot", (244, 251, 266, 273), "c0"),
            ("accidentalSharp", (385, 185, 413, 258), "c1"), ("ledgerLine", (465, 303, 535, 318), "c1"),
            ("noteheadBlackOnLine", (478, 295, 522, 326), "c1")]


def test_bulk_confirm_takes_one_kind_in_one_cell_and_undo_gives_it_back(tmp_path):
    svc, ps = _service(tmp_path, _boxes())
    before = {l["id"]: l["state"] for l in svc.state_payload()["labels"]}
    out = svc.mutate(lambda p: p.bulk_confirm(svc.bulk_ids("c0", "notehead")["ids"]))
    after = {l["id"]: l for l in out["labels"]}
    heads_c0 = [l for l in out["labels"] if l["kind"] == "notehead" and l["cell_id"] == "c0"]
    assert len(heads_c0) == 2 and all(l["state"] == "confirmed" and l["px"] > 0 for l in heads_c0)
    # NEVER across kinds, NEVER across cells
    assert all(l["state"] == "pending" for l in out["labels"] if l["kind"] != "notehead")
    assert all(l["state"] == "pending" for l in out["labels"] if l["kind"] == "notehead" and l["cell_id"] == "c1")
    assert out["totals"]["confirmed"] == 2
    undone = svc.undo()
    assert {l["id"]: l["state"] for l in undone["labels"]} == before and undone["totals"]["confirmed"] == 0
    # the bulk selection refuses a kind with nothing waiting, and an unknown kind
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        svc.bulk_ids("c0", "violin")
    assert svc.bulk_ids("c1", "stem") == {"ids": [], "empty": []}


def test_a_head_prefill_claims_the_head_and_a_stem_prefill_the_stem_so_confirming_both_separates_them(tmp_path):
    svc, ps = _service(tmp_path, _boxes())
    svc.mutate(lambda p: p.bulk_confirm(svc.bulk_ids("c0", "notehead")["ids"]))
    out = svc.mutate(lambda p: p.bulk_confirm(svc.bulk_ids("c0", "stem")["ids"]))
    c = svc.claims()
    owner = c["owner"]
    el = ps.el
    ids = {l.id: i + 1 for i, l in enumerate(c["labels"])}
    head_ids = [ids[l["id"]] for l in out["labels"] if l["kind"] == "notehead" and l["cell_id"] == "c0"]
    stem_ids = [ids[l["id"]] for l in out["labels"] if l["kind"] == "stem"]
    heads_px = np.isin(owner, head_ids)
    stems_px = np.isin(owner, stem_ids)
    assert heads_px.sum() > 0 and stems_px.sum() > 0
    assert (heads_px & stems_px).sum() == 0
    assert (heads_px & el["stems"] & ~el["heads"]).sum() == 0          # the head label did not take the stem
    assert (stems_px & el["heads"] & ~el["stems"]).sum() <= 0.03 * el["heads"].sum()   # not the head (a rim at its foot)


def test_a_twin_box_from_the_next_cell_is_covered_once_one_is_confirmed_and_never_left_waiting(tmp_path):
    twin = ("augmentationDot", (244, 251, 266, 273), "c0"), ("augmentationDot", (245, 252, 267, 274), "c1")
    svc, ps = _service(tmp_path, list(twin))
    st = svc.state_payload()
    assert st["totals"]["pending"] >= 2 and not any(l.get("covered") for l in st["labels"])
    first = svc.bulk_ids("c0", "dot")["ids"]
    assert len(first) == 1
    out = svc.mutate(lambda p: p.bulk_confirm(first))
    dots = [l for l in out["labels"] if l["kind"] == "dot"]
    assert sorted(l["state"] for l in dots) == ["confirmed", "pending"]
    waiting_twin = next(l for l in dots if l["state"] == "pending")
    assert waiting_twin.get("covered") and out["totals"]["covered"] == 1       # its ink is owned: not waiting
    assert svc.bulk_ids("c1", "dot") == {"ids": [], "empty": []}
    assert next(c for c in out["cells"] if c["id"] == "c1")["waiting"] == 0


def test_the_queue_percentages_and_done(tmp_path):
    svc, ps = _service(tmp_path, _boxes())
    st = svc.state_payload()
    cells = {c["id"]: c for c in st["cells"]}
    assert [c["id"] for c in st["cells"]] == ["c0", "c1"] and [c["order"] for c in st["cells"]] == [0, 1]
    assert cells["c0"]["pct"] > 0 and cells["c0"]["unclaimed_px"] > 0 and cells["c0"]["waiting"] >= 6
    t0 = st["totals"]
    assert t0["page_pct"] > 0 and not t0["done"]
    # confirm every kind in both cells: the unclaimed share of c0 falls, the page total follows, nothing is invented
    for cid in ("c0", "c1"):
        for kind in cpm.KINDS:
            sel = svc.bulk_ids(cid, kind)
            if sel["ids"]:
                svc.mutate(lambda p, ids=sel["ids"]: p.bulk_confirm(ids))
    t1 = svc.state_payload()
    assert t1["cells"][0]["pct"] < cells["c0"]["pct"] and t1["totals"]["unclaimed_pct"] < t0["unclaimed_pct"]
    tt = t1["totals"]
    assert abs(tt["page_pct"] + tt["cell_pct"] + tt["noise_pct"] + tt["unclaimed_pct"] - 100.0) < 1e-6
    assert not tt["done"]                                              # the speck and anything unlabelled keep it open
    # the speck: draw `noise` over it; then nothing is left once the rest is claimed or marked noise
    svc.mutate(lambda p: p.draw("noise", None, pp.rect_shape([595, 95, 608, 108]), cell_id="c1"))
    left = svc.state_payload()["totals"]["unclaimed_px"]
    assert 0 < left < t0["unclaimed_px"]
    # mark the whole remainder noise by polygon boxes: DONE means unclaimed == 0 and nothing waiting
    svc.mutate(lambda p: p.draw("noise", None, pp.rect_shape([0, 0, W, H]), cell_id="c0"))
    fin = svc.state_payload()
    assert fin["totals"]["unclaimed_px"] == 0 and fin["totals"]["done"]
    assert all(c["unclaimed_px"] == 0 for c in fin["cells"])


def test_confirmed_label_beats_prefill_and_the_tighter_shape_wins_between_confirmed_ones(tmp_path):
    svc, ps = _service(tmp_path, [("beam", (212, 156, 337, 180), "c0")])
    pre = next(l for l in svc.cp.labels if l.kind == "beam")
    wide = svc.mutate(lambda p: p.draw("noise", None, pp.rect_shape([205, 150, 345, 185]), cell_id="c0"))["label"]
    c = svc.claims()
    assert c["px"][wide["id"]] > 0 and c["px"].get(pre.id, 0) == 0     # the confirmed noise box owns the beam; the pre-fill waits
    svc.mutate(lambda p: p.draw("beam", None, pp.rect_shape([212, 156, 337, 180]), cell_id="c0"))
    c = svc.claims()
    tight = [l for l in c["labels"] if l.kind == "beam" and l.state == "confirmed"][0]
    assert c["px"][tight.id] > 0 and c["px"][wide["id"]] < c["px"][tight.id] or c["px"][wide["id"]] == 0


# ------------------------------------------------------------------ routes and files
def test_routes_state_draw_bulk_undo_render_owned_and_the_other_files_are_never_written(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tools.omr.annotate.cellpass_server import mount

    page_file = tmp_path / "pages" / "imslp1" / "0.pagepass.json"
    page_file.parent.mkdir(parents=True)
    pp.PagePass(edition="imslp1", pdf_page_index=0, dpi=600, width=W, height=H, sp=SP).save(page_file)
    guard = page_file.read_bytes()
    svc, ps = _service(tmp_path, _boxes())
    app = FastAPI()
    mount(app, svc)
    c = TestClient(app)
    st = c.get("/api/cp/state").json()
    assert st["meta"]["kinds"][0] == "notehead" and st["totals"]["pending"] >= 8
    r = c.post("/api/cp/bulk", json={"cell_id": "c0", "kind": "stem"}).json()
    assert r["bulk"]["confirmed"] == 2 and r["totals"]["confirmed"] == 2
    assert c.post("/api/cp/bulk", json={"cell_id": "c0", "kind": "stem"}).status_code == 400   # nothing left of it
    d = c.post("/api/cp/label", json={"kind": "dot", "cls": "augmentationDot", "shape": {"rect": [244, 251, 266, 273]},
                                      "cell_id": "c0"}).json()
    assert d["label"]["state"] == "confirmed" and d["label"]["pass"] == "cell" and d["label"]["ink_ref"]["px"] > 0
    assert c.post("/api/cp/label", json={"kind": "clef", "shape": {"rect": [0, 0, 5, 5]}}).status_code == 400
    img = c.get("/api/cp/render?x0=0&y0=0&x1=700&y1=420&w=700")
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    # the picture: pass-1 ink blue, a confirmed pass-2 label green, ink under a waiting pre-fill purple
    im = cv2.imdecode(np.frombuffer(img.content, np.uint8), cv2.IMREAD_COLOR)[..., ::-1]
    assert (im == (0, 114, 178)).all(-1).sum() > 0 and (im == (0, 158, 115)).all(-1).sum() > 0
    assert (im == (204, 121, 167)).all(-1).sum() > 0
    assert c.get(f"/api/cp/owned/{d['label']['id']}").status_code == 200
    assert c.get("/api/cp/owned/nope").status_code == 404
    assert sum(c.get("/api/cp/roles").json().values()) > 0
    u = c.post("/api/cp/undo", json={}).json()
    assert u["totals"]["confirmed"] == 2
    saved = json.loads(svc.file.read_text())
    assert all(l["pass"] == "cell" for l in saved["labels"])
    assert page_file.read_bytes() == guard                            # pass 2 never writes the page-pass file


def test_sean_page_pass_labels_stay_byte_for_byte_through_a_whole_pass_two_session(tmp_path):
    """Sean's pass-1 file is truth: a pass-2 session on a COPY of it (and of the page file) leaves both unchanged."""
    from tools.omr.hand_truth import store

    root = Path(__file__).resolve().parents[3] / "data/hand-truth/pages/imslp317803"
    if not (root / "0.pagepass.json").exists():
        pytest.skip("no page-pass file in this checkout")
    import shutil

    (tmp_path / "imslp317803").mkdir()
    for n in ("0.json", "0.pagepass.json"):
        shutil.copy(root / n, tmp_path / "imslp317803" / n)
    snap = {n: (tmp_path / "imslp317803" / n).read_bytes() for n in ("0.json", "0.pagepass.json")}
    t = store.load(tmp_path / "imslp317803" / "0.json")
    cp, _ = cpm.build(t)
    for lab in list(cp.labels)[:50]:
        cp.confirm(lab.id)
    cp.save(cpm.cellpass_path(t.edition, t.pdf_page_index, tmp_path))
    assert {n: (tmp_path / "imslp317803" / n).read_bytes() for n in snap} == snap
    assert pp.load(tmp_path / "imslp317803" / "0.pagepass.json").to_json()["labels"] == \
        json.loads((root / "0.pagepass.json").read_text())["labels"]
