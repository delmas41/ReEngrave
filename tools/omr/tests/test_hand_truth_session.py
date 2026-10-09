"""ROADMAP 1.7 (plan C1, C5): cut a page, label it cell by cell in the real
annotate server, and every save lands in the page store in page pixels.

The page is SYNTHETIC (drawn here) so the test needs no score PDF, but it is
cut by the product path's own staff detector and measure extractor.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("fastapi")
cv2 = pytest.importorskip("cv2")

from fastapi.testclient import TestClient

from tools.omr.annotate.server import create_app
from tools.omr.hand_truth import bench as bench_mod
from tools.omr.hand_truth import checks, completeness, store
from tools.omr.hand_truth.session import build_page, propose_deduped
from tools.omr.types import PageImage

SP = 20  # staff space of the synthetic page, px


def synth_page():
    H, W = 1800, 2400
    img = np.full((H, W), 255, np.uint8)
    bars = [300, 900, 1500, 2200]
    for top in (300, 1000):
        tops = [top + k * 9 * SP for k in range(3)]
        for t in tops:
            for i in range(5):
                cv2.line(img, (bars[0], t + i * SP), (bars[-1], t + i * SP), 0, 2)
        for x in bars:
            cv2.line(img, (x, tops[0]), (x, tops[-1] + 4 * SP), 0, 3)
        for k, t in enumerate(tops):
            for j, x in enumerate((500, 1100, 1700)):
                cy = t + (k + j) % 4 * SP + SP // 2
                cv2.ellipse(img, (x, cy), (13, 10), -20, 0, 360, 0, -1)
        cv2.putText(img, "Fl.", (120, tops[0] + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, 0, 3)
    cv2.putText(img, "SYMPHONY", (900, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 0, 5)
    cv2.putText(img, "7", (1190, 1720), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 3)
    return PageImage(pdf_path=Path("synthetic"), page_index=0, dpi=600,
                     rgb=cv2.cvtColor(img, cv2.COLOR_GRAY2RGB), binary=img.copy())


@pytest.fixture(scope="module")
def cut():
    return build_page(synth_page(), edition="synthetic", pdf="synthetic")


def test_the_page_is_cut_into_measure_cells_and_every_other_bit_of_ink(cut):
    page, images, _ = cut
    kinds = [c.kind for c in page.cells]
    assert kinds.count("measure") == 18 and len(page.staves) == 6
    assert "top" in kinds and "bottom" in kinds and "margin" in kinds
    # The title, the page number and the instrument name each live in a region cell.
    title = next(c for c in page.cells if c.kind == "top")
    assert title.rect[0] < 900 < title.rect[2] and title.rect[3] < 300
    names = [c for c in page.cells if c.kind == "margin" and c.rect[2] < 300]
    assert len(names) == 2  # "Fl." on each system
    for c in page.cells:
        assert images[c.id].shape[:2] == (c.canonical_h, c.canonical_w)


def test_measure_cell_frames_are_the_product_paths_own(cut):
    page, _, mcells = cut
    by = {f"s{m.system_index}-st{m.staff_index}-m{m.measure_index}": m for m in mcells}
    for c in page.cells:
        if c.kind == "measure":
            assert c.rect == tuple(float(v) for v in by[c.id].bbox_page_px)
            assert (c.canonical_h, c.canonical_w) == by[c.id].image.shape[:2]


# ------------------------------------------------------------------ the server, end to end
def _overlap_pair(page):
    a, b = page.cell("s0-st0-m0"), page.cell("s0-st1-m0")
    assert a.rect[3] > b.rect[1], "padded cells of neighbouring staves must overlap"
    y = (b.rect[1] + a.rect[3]) / 2
    return a, b, (600.0, y - 8, 620.0, y + 8)


@pytest.fixture()
def live(tmp_path, cut):
    page, images, _ = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))  # a private copy
    a, b, rect = _overlap_pair(page)
    propose_deduped(page, "noteheadBlackOnLine", rect, source="detector:test", score=0.7)
    page_path = tmp_path / "page.json"
    page_path.write_text(json.dumps(page.to_json()))
    bench = bench_mod.write_bench(page, images, tmp_path / "bench")
    app = create_app(bench, on_saved=lambda cid: bench_mod.on_saved(page_path, bench, cid),
                     extra_classes=tuple(bench_mod.PAGE_TRUTH_CLASSES))
    return TestClient(app), page_path, bench, a.id, b.id


def _state(client, cid):
    return client.get(f"/api/cell/{cid}/verdict").json()["state"]


def _save(client, cid, state):
    r = client.post(f"/api/cell/{cid}/verdict", json=state)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_confirmed_prefill_becomes_one_page_box_seen_from_both_cells(live):
    client, page_path, bench, a, b = live
    st = _state(client, a)
    (q,) = [d for d in st["detections"] if d["id"].startswith("q")]
    q["verdict"] = "TP"
    out = _save(client, a, st)
    assert b in out["synced_cells"]
    page = store.load(page_path)
    assert [x.origin for x in page.boxes] == ["prefill-confirmed"] and page.queue == []
    seen_in_b = {d["id"]: d["verdict"] for d in _state(client, b)["detections"]}
    assert seen_in_b[page.boxes[0].id] == "TP"


def test_a_drawn_box_is_stored_once_and_a_resave_does_not_draw_it_twice(live):
    client, page_path, bench, a, b = live
    st = _state(client, a)
    st["added_detections"] = [{"id": "A0", "human_class": "restQuarter", "bbox": {"x": 100, "y": 100, "w": 40, "h": 90}}]
    _save(client, a, st)
    _save(client, a, st)  # the UI autosaves
    page = store.load(page_path)
    drawn = [x for x in page.boxes if x.origin == "drawn"]
    assert len(drawn) == 1 and drawn[0].ref == f"{a}#A0"
    assert drawn[0].rect == pytest.approx(page.cell(a).to_page((100, 100, 140, 190)))
    # In its own cell it is Sean's added box, never ALSO a detection (it would show twice).
    assert drawn[0].id not in {d["id"] for d in _state(client, a)["detections"]}


def test_rejecting_a_neighbours_drawing_removes_it_everywhere(live):
    client, page_path, bench, a, b = live
    a_cell = store.load(page_path).cell(a)
    _, _, rect = _overlap_pair(store.load(page_path))
    cx0, cy0, cx1, cy1 = a_cell.to_cell(rect)
    st = _state(client, a)
    st["added_detections"] = [{"id": "A1", "human_class": "accidentalSharp",
                               "bbox": {"x": int(cx0), "y": int(cy0), "w": int(cx1 - cx0), "h": int(cy1 - cy0)}}]
    _save(client, a, st)
    box_id = store.load(page_path).box_by_ref(f"{a}#A1").id
    st_b = _state(client, b)
    det = next(d for d in st_b["detections"] if d["id"] == box_id)
    assert det["verdict"] == "TP"
    det["verdict"] = "FP"
    _save(client, b, st_b)
    assert store.load(page_path).box_by_ref(f"{a}#A1") is None
    assert _state(client, a)["added_detections"] == []  # or the next save of A would redraw it


def test_staff_lines_and_the_all_ink_pass_reach_the_page(live):
    client, page_path, bench, a, b = live
    st = _state(client, a)
    lines = [d for d in st["detections"] if d["id"].startswith("L")]
    assert len(lines) == 5
    for d in lines:
        d["verdict"] = "TP"
    st["inspected_passes"] = ["all-ink"]
    _save(client, a, st)
    page = store.load(page_path)
    assert page.staff(0, 0).lines_right is True
    assert completeness.families_covered(page.cell(a).inspected) is None
    lines[2]["verdict"] = "FP"  # the control: one wrong line and the staff is not right
    _save(client, a, st)
    assert store.load(page_path).staff(0, 0).lines_right is False


def test_a_text_box_waits_for_its_words(live):
    client, page_path, bench, a, b = live
    st = _state(client, a)
    st["added_detections"] = [{"id": "T0", "human_class": "text", "bbox": {"x": 10, "y": 10, "w": 80, "h": 30}}]
    _save(client, a, st)
    page = store.load(page_path)
    assert page.box_by_ref(f"{a}#T0") is None
    assert [f.kind for f in page.open_flags()] == ["text_without_words"]
    st["added_detections"][0]["notes"] = "Flauti"
    _save(client, a, st)
    assert store.load(page_path).box_by_ref(f"{a}#T0").text == "Flauti"


def test_text_and_noise_are_in_the_picker_only_in_page_store_mode(tmp_path, cut, live):
    client = live[0]
    names = {c["name"] for c in client.get("/api/classes").json()}
    assert {"text", "noise"} <= names
    page, images, _ = cut
    plain = TestClient(create_app(bench_mod.write_bench(page, images, tmp_path / "plain")))
    assert not {"text", "noise"} & {c["name"] for c in plain.get("/api/classes").json()}


def test_a_failed_sync_is_loud(tmp_path, cut):
    page, images, _ = cut
    bench = bench_mod.write_bench(page, images, tmp_path / "bench")

    def boom(cid):
        raise RuntimeError("disk full")

    client = TestClient(create_app(bench, on_saved=boom))
    cid = page.cells[0].id
    r = client.post(f"/api/cell/{cid}/verdict", json=_state(client, cid))
    assert r.status_code == 500 and "did not take it" in r.text


# ------------------------------------------------------------------ the fixed checks (C5)
def _check_page():
    p = store.PageTruth(edition="e", pdf_page_index=0, dpi=600, width=1000, height=400)
    # One staff: lines at y 100..180 (space 20) in page px; canonical == page here.
    p.add_cell(store.Cell(id="s0-st0-m0", kind="measure", rect=(0, 0, 1000, 400), canonical_w=1000,
                          canonical_h=400, system=0, staff=0, measure=0,
                          staff_line_ys=[100, 120, 140, 160, 180]))
    return p


def test_each_fixed_check_fires_on_its_case_and_not_on_its_control():
    p = _check_page()
    d = lambda cls, r: p.draw("s0-st0-m0", cls, r)  # noqa: E731
    d("clefG", (10, 80, 40, 200))
    h1 = d("noteheadBlackInSpace", (100, 125, 126, 145))
    d("augmentationDot", (132, 130, 138, 136))                  # control: has its head
    lone_dot = d("augmentationDot", (400, 130, 406, 136))       # no head to its left
    far = d("noteheadBlackInSpace", (600, 30, 626, 50))         # 3+ spaces above, no ledger
    far_ok = d("noteheadBlackInSpace", (700, 30, 726, 50))
    d("ledgerLine", (695, 58, 731, 62))                          # control: has a ledger
    d("ledgerLine", (695, 78, 731, 82))
    h2 = d("noteheadBlackOnLine", (300, 150, 326, 170))
    t = d("tie", (126, 150, 300, 165))                           # joins h1 (y 135) and h2 (y 160)
    dup = d("noteheadBlackInSpace", (101, 125, 127, 145))
    new = checks.run_all(p)
    kinds = {(f.kind, tuple(f.box_ids)) for f in new}
    assert ("dot_without_head", (lone_dot.id,)) in kinds
    assert ("far_head_no_ledger", (far.id,)) in kinds
    assert not any(k == "far_head_no_ledger" and far_ok.id in ids for k, ids in kinds)
    assert ("duplicate_box", tuple(sorted((h1.id, dup.id)))) in {(k, tuple(sorted(i))) for k, i in kinds}
    assert any(k == "tie_heads_differ" and t.id in ids for k, ids in kinds)
    assert not any(k == "staff_starts_without_clef" for k, _ in kinds)


def test_a_resolved_flag_is_never_raised_again():
    p = _check_page()
    p.draw("s0-st0-m0", "augmentationDot", (400, 130, 406, 136))
    (f,) = [x for x in checks.run_all(p) if x.kind == "dot_without_head"]
    p.resolve_flag(f.id, "rejected")
    assert [x for x in checks.run_all(p) if x.kind == "dot_without_head"] == []
    assert any(x.kind == "staff_starts_without_clef" for x in p.flags)


# ------------------------------------------------------------------ pre-fills (C2), arithmetic only
def test_old_labels_are_reprojected_exactly_and_a_wrong_frame_is_refused(monkeypatch):
    """The real old labels of the Brahms count page, through a stand-in re-cut.

    The re-cut needs the score, so it is replaced by one that returns each
    manifest entry's frame at a KNOWN page rectangle — except one entry, which
    it reports as a wrong frame. That cell's boxes must not be queued at all.
    """
    from types import SimpleNamespace

    from tools.omr.annotate import recut_cells
    from tools.omr.hand_truth import session

    found = session.old_label_entries("imslp317803", 1)
    assert len(found) == 39
    refused_id = found[0][1]["cell_id"]

    def fake_cut(pdf, page, entries, *, dpi, log=print, **kw):
        a = recut_cells.SourceAssessment()
        for e in entries:
            if e["cell_id"] == refused_id:
                a.mismatched.append((e, "width 1 != manifest 2"))
                continue
            k = recut_cells.entry_key(e)
            x0, y0 = 1000 * k[2], 500 * k[1]  # a page rectangle per (staff, measure)
            w, h = int(e["cell_canonical_w"]), int(e["cell_canonical_h"])
            a.matched.append((e, SimpleNamespace(bbox_page_px=(x0, y0, x0 + w // 2, y0 + h // 2),
                                                 width=w, height=h, **dict(zip(
                                                     ("system_index", "staff_index", "measure_index"), k)))))
        return "pipeline", a

    monkeypatch.setattr(recut_cells, "choose_mode_and_cut", fake_cut)
    page = store.PageTruth(edition="imslp317803", pdf_page_index=1, dpi=600, width=20000, height=20000)
    rep = session.prefill_old_labels(page, Path("unused"), log=lambda *a: None)
    assert [r["cell_id"] for r in rep["cells_refused"]] == [refused_id] * sum(
        1 for _, e, _ in found if e["cell_id"] == refused_id)
    assert rep["boxes_queued"] == len(page.queue) > 0
    assert all(q.source.startswith("sean-v") for q in page.queue)
    assert not any(refused_id in q.source for q in page.queue)
    # One line by hand: cell at half scale, so a box's page size is half its canonical size.
    v, e, lab = next(x for x in found if x[1]["cell_id"] != refused_id and x[0].startswith("v18"))
    k = recut_cells.entry_key(e)
    cls, cx, cy, bw, bh = lab.read_text().split()[:5]
    w, h = int(e["cell_canonical_w"]), int(e["cell_canonical_h"])
    # page = rect origin + canonical * (page size / canonical size), the page size being w // 2
    want = (1000 * k[2] + (float(cx) - float(bw) / 2) * (w // 2),
            500 * k[1] + (float(cy) - float(bh) / 2) * (h // 2))
    assert any(abs(q.rect[0] - want[0]) < 1e-6 and abs(q.rect[1] - want[1]) < 1e-6 for q in page.queue)


def test_a_detector_box_on_an_old_human_box_is_dropped(monkeypatch, cut):
    from types import SimpleNamespace

    import tools.omr.yolo_detector as yd
    from tools.omr.hand_truth import session

    page, images, mcells = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))
    c = page.cell("s0-st0-m1")
    human = c.to_page((100, 100, 140, 130))
    page.propose("noteheadBlackInSpace", human, source="sean-v18")

    class FakeDetector:
        def __init__(self, *a, **k):
            pass

        def detect(self, mc, conf_threshold=0.25):
            if (mc.system_index, mc.staff_index, mc.measure_index) != (0, 0, 1):
                return []
            return [SimpleNamespace(x_canonical=101, y_canonical=101, width_canonical=40, height_canonical=30,
                                    smufl_name="noteheadBlackOnLine", confidence=0.9),
                    SimpleNamespace(x_canonical=500, y_canonical=300, width_canonical=20, height_canonical=60,
                                    smufl_name="restQuarter", confidence=0.8)]

    monkeypatch.setattr(yd, "YoloDetector", FakeDetector)
    regions = {x.id: images[x.id] for x in page.cells if x.kind != "measure"}
    rep = session.prefill_detector(page, mcells, regions, Path("w.pt"))
    assert rep == {"boxes_queued": 1, "boxes_dropped_as_duplicates": 1}
    assert sorted(q.source.split(":")[0] for q in page.queue) == ["detector", "sean-v18"]
    rest = next(q for q in page.queue if q.cls == "restQuarter")
    assert rest.rect == pytest.approx(c.to_page((500, 300, 520, 360)))


def test_a_staff_line_is_never_queued_it_is_confirmed_per_staff(monkeypatch, cut):
    # Sean 2026-10-08: the detector's own "staff" boxes landed in the queue on
    # every cell; staff lines are confirmed on the L* boxes, never boxed.
    from types import SimpleNamespace

    import tools.omr.yolo_detector as yd
    from tools.omr.hand_truth import session

    page, images, mcells = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))

    class FakeDetector:
        def __init__(self, *a, **k):
            pass

        def detect(self, mc, conf_threshold=0.25):
            if (mc.system_index, mc.staff_index, mc.measure_index) != (0, 0, 1):
                return []
            return [SimpleNamespace(x_canonical=0, y_canonical=80, width_canonical=900, height_canonical=200,
                                    smufl_name="staff", confidence=0.9),
                    SimpleNamespace(x_canonical=500, y_canonical=300, width_canonical=20, height_canonical=60,
                                    smufl_name="restQuarter", confidence=0.8)]

    monkeypatch.setattr(yd, "YoloDetector", FakeDetector)
    regions = {x.id: images[x.id] for x in page.cells if x.kind != "measure"}
    rep = session.prefill_detector(page, mcells, regions, Path("w.pt"))
    assert [q.cls for q in page.queue] == ["restQuarter"]  # the control: a real mark still queues
    assert rep["boxes_not_proposed"] == {"staff": 1}


# ------------------------------------------------------------------ perfect eyes (C6)
def test_the_stand_in_detector_returns_the_truth_boxes_a_cell_holds(cut):
    from tools.omr.hand_truth.perfect_eyes import PageTruthDetector

    page, _, mcells = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))
    mc = next(m for m in mcells if (m.system_index, m.staff_index, m.measure_index) == (0, 0, 1))
    c = page.cell("s0-st0-m1")
    head = page.draw(c.id, "noteheadBlackInSpace", (200, 300, 240, 330))
    page.draw(c.id, "noise", (10, 10, 20, 20))
    page.draw(c.id, "text", (30, 10, 90, 40), text="dolce")
    (d,) = PageTruthDetector(page).detect(mc)
    assert d.smufl_name == "noteheadBlackInSpace" and d.confidence == 1.0
    assert (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical) == pytest.approx(
        (200, 300, 40, 30), abs=1)
    other = next(m for m in mcells if (m.system_index, m.staff_index, m.measure_index) == (1, 5, 2))
    assert PageTruthDetector(page).detect(other) == []  # the control: a cell far away sees none
    assert head.id


def test_the_product_path_runs_end_to_end_on_perfect_eyes(cut, tmp_path):
    from tools.omr.hand_truth import perfect_eyes as pe
    from tools.omr.measure_extractor import extract_measures
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_line_removal import remove_staff_lines

    page, _, _ = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))
    c = page.cell("s0-st0-m0")
    page.draw(c.id, "noteheadBlackInSpace", (900, 500, 940, 530))
    pi = synth_page()
    pws = detect_staves(pi)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    res = pe.run_on_prepared(page, [(pws, cells)])
    assert res["provenance"]["detector"]["kind"] == "hand-truth (perfect eyes)"
    assert res["provenance"]["detector"]["detect_calls"] >= 18
    paths = pe.write_outputs(res, tmp_path, "synthetic", pdf=False)
    assert "<score-partwise" in Path(paths["musicxml"]).read_text()
    assert "\\score" in Path(paths["lilypond"]).read_text()
    assert pe.write_outputs(res, tmp_path / "g", "synthetic", through="adjudicate").keys() == {"record"}


# ------------------------------------------------------------------ the bar review (C6b)
def _score(parts):
    """A tiny score-partwise: {part_id: [measure xml bodies]}."""
    pl = "".join(f'<score-part id="{p}"><part-name>{p}</part-name></score-part>' for p in parts)
    body = "".join(f'<part id="{p}">' + "".join(f'<measure number="{i + 1}">{m}</measure>'
                                                for i, m in enumerate(ms)) + "</part>" for p, ms in parts.items())
    return f'<score-partwise version="3.1"><part-list>{pl}</part-list>{body}</score-partwise>'


def test_a_bar_slice_carries_clef_key_and_time_and_never_guesses_a_short_part():
    import xml.etree.ElementTree as ET

    from tools.omr.hand_truth.review import slice_bar

    att = "<attributes><divisions>4</divisions><key><fifths>-3</fifths></key><clef><sign>F</sign></clef></attributes>"
    xml = _score({"P1": [att + "<note/>", "<note/>", "<note/>"], "P2": ["<note/>", "<note/>"]})
    sl, aligned, not_aligned = slice_bar(xml, 3, 3)
    assert aligned == ["P1"] and not_aligned == ["P2 (2 bars in the file, 3 printed)"]
    m = ET.fromstring(sl).find("part/measure")
    assert m.get("number") == "1" and m.findtext("attributes/key/fifths") == "-3"
    assert m.findtext("attributes/clef/sign") == "F"


def test_bars_are_read_in_print_order_and_a_review_is_of_one_set_of_labels(cut, tmp_path):
    from tools.omr.hand_truth import review

    page, _, _ = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))
    cols = review.bar_columns(page)
    assert [(c["system"], c["measure"]) for c in cols] == [(s, m) for s in (0, 1) for m in (0, 1, 2)]
    pp = tmp_path / "p.json"
    pp.write_text(json.dumps(page.to_json()))
    for k in range(1, 7):
        review.mark(pp, page, k, "ok")
    assert review.verdict(pp, page)["verified"] is True
    page.draw("s0-st0-m0", "restQuarter", (10, 10, 30, 60))   # a label edited after the review
    v = review.verdict(pp, page)
    assert v["verified"] is False and v["stale"] is True
    review.mark(pp, page, 1, "reader wrong", "beam read as two flags")
    v = review.verdict(pp, page)
    assert v["not_ok"] == [1] and v["unmarked"] == [2, 3, 4, 5, 6] and not v["stale"]


def test_the_review_page_serves_and_records_marks(cut, tmp_path):
    from tools.omr.hand_truth import review

    page, _, _ = cut
    pp = tmp_path / "p.json"
    pp.write_text(json.dumps(page.to_json()))
    xml = _score({"P1": ["<note/>"] * 6})
    bars = review.build(page, synth_page().rgb, xml, tmp_path / "rv")
    assert len(bars["bars"]) == 6 and all(b["print"] for b in bars["bars"])
    # No lilypond in this container: every bar says so instead of showing nothing.
    assert all(b["lilypond"] or b["not_rendered_because"] for b in bars["bars"])
    client = TestClient(review.create_app(pp, tmp_path / "rv"))
    assert "bar 6" in client.get("/").text
    assert client.post("/api/mark", json={"bar": 2, "mark": "label wrong", "note": "missing tie"}).json()["ok"]
    assert client.post("/api/mark", json={"bar": 2, "mark": "fine"}).status_code == 400
    assert review.load_review(pp)["marks"]["2"]["mark"] == "label wrong"


def test_verified_needs_every_bar_ok(cut, tmp_path):
    from tools.omr.hand_truth import review, session

    page, _, _ = cut
    page = store.PageTruth.from_json(json.loads(json.dumps(page.to_json())))
    page.advance("checked")
    pp = tmp_path / "p.json"
    pp.write_text(json.dumps(page.to_json()))
    for k in range(1, 6):
        review.mark(pp, page, k, "ok")
    with pytest.raises(SystemExit, match="not verified"):
        session.main(["advance", str(pp), "--to", "verified"])
    review.mark(pp, page, 6, "ok")
    assert session.main(["advance", str(pp), "--to", "verified"]) == 0
    assert store.load(pp).state == "verified"


def test_claudes_visual_pass_files_flags_and_sean_resolves_them(cut, tmp_path):
    from tools.omr.hand_truth import session

    page, _, _ = cut
    pp = tmp_path / "p.json"
    pp.write_text(json.dumps(page.to_json()))
    assert session.main(["raise", str(pp), "--cell", "s0-st0-m1", "--kind", "missed_symbol",
                         "--message", "a staccato dot above the second head has no box"]) == 0
    (f,) = store.load(pp).open_flags()
    assert f.by == "claude:visual" and f.cell_id == "s0-st0-m1"
    assert session.main(["flag", str(pp), f.id, "rejected"]) == 0
    assert store.load(pp).open_flags() == []
    with pytest.raises(store.StoreError):
        session.main(["raise", str(pp), "--cell", "no-such-cell", "--kind", "k", "--message", "m"])
