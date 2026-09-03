"""The reference-driven pre-fill: a transcription, a truth MusicXML and a
window row become verdict files the annotate server and the YOLO converter
read unchanged — and every join abstains where it should."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr.training import mxl_verdicts as mv
from tools.omr.training.musicxml_truth import load_truth
from tools.omr.training.verdicts_to_yolo_labels import (
    CellArtifacts,
    _is_filled,
    convert_cell,
    load_class_names,
    name_to_first_index,
)

pytestmark = pytest.mark.omr_training

# Two parts on two staves, one system, one page. Reference measures 1-3.
TRUTH = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Flute</part-name></score-part>
    <score-part id="P2"><part-name>Oboe</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>2</divisions><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><type>half</type></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <note><rest measure="yes"/><duration>8</duration></note>
    </measure>
    <measure number="3">
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><type>half</type></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><type>half</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes><divisions>2</divisions><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>8</duration><type>whole</type></note>
    </measure>
    <measure number="2">
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><type>half</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><type>half</type></note>
    </measure>
    <measure number="3">
      <note><rest measure="yes"/><duration>8</duration></note>
    </measure>
  </part>
</score-partwise>
"""

LINES = [100, 200, 300, 400, 500]


def _det(cls: str, pitch: str | None, x: int, y: int, *, dur: float | None = 1.0,
         dtype: str | None = "quarter") -> dict:
    d = {"class": cls, "category": "rest" if cls.startswith("rest") else "notehead",
         "bbox": [x, y, 40, 40], "bbox_page": [x, y, 40, 40], "confidence": 0.8,
         "pitch": pitch}
    if dur is not None:
        d["duration_beats"] = dur
        d["duration_type"] = dtype
        d["dots"] = 0
    return d


def _measure(idx: int, dets: list[dict]) -> dict:
    # bbox_page_px is [x0, y0, x1, y1] — the measure's page box, not [x, y, w, h].
    return {"measure_index": idx, "bbox_page_px": [idx * 1000, 0, idx * 1000 + 1000, 600],
            "staff_line_ys_canonical": LINES, "upscale_factor": 1.0, "clef": "treble",
            "detections": dets}


def _transcription(n_measures_staff0: int = 3) -> dict:
    # Staff 0 = Flute, staff 1 = Oboe. Canonical == page frame (upscale 1.0).
    s0 = [
        _measure(0, [
            _det("noteheadBlackInSpace", "C5", 200, 230),         # truth half → WRONG_CATEGORY
            _det("noteheadBlackOnLine", "E5", 500, 130),          # TP
            _det("noteheadBlackInSpace", "A5", 800, -20),         # not in the reference
        ]),
        _measure(1, [_det("restWhole", None, 400, 150, dur=4.0, dtype="whole")]),
        _measure(2, [
            _det("noteheadHalfInSpace", "D5", 300, 180, dur=2.0, dtype="half"),   # TP
            _det("noteheadBlackInSpace", "D5", 700, 180, dur=None, dtype=None),   # stemless orphan
        ]),
    ][:n_measures_staff0]
    s1 = [
        _measure(0, [_det("noteheadBlackInSpace", "A4", 400, 330, dur=4.0, dtype="whole")]),
        _measure(1, [_det("noteheadBlackOnLine", "B4", 300, 280, dur=2.0, dtype="half"),
                     _det("noteheadHalfInSpace", "C5", 700, 230, dur=2.0, dtype="half")]),
        _measure(2, []),
    ]
    return {"pages": [{"page_index": 3, "systems": [{"system_index": 0, "staves": [
        {"staff_index": 0, "clef": "treble", "n_measures": len(s0), "measures": s0},
        {"staff_index": 1, "clef": "treble", "n_measures": 3, "measures": s1},
    ]}]}]}


def _windows(first: int = 1, last: int | None = 3, n_staves: int = 2) -> list[dict]:
    staves = [{"name": "Flute", "parts": [0]}, {"name": "Oboe", "parts": [1]}][:n_staves]
    return [{"row_id": "fx-p3", "page": {"pdf_page_index": 3},
             "window": {"first_ref_measure": first, "last_ref_measure": last},
             "staves": staves}]


def _cell(cid: str, staff: int, meas: int, *, lines=LINES, w=1000, h=600) -> dict:
    return {"cell_id": cid, "pdf": "/nowhere.pdf", "page": 3, "system_index": 0,
            "staff_index": staff, "measure_index": meas,
            "cell_png_path": f"cells/{cid}.png", "staff_line_ys_canonical": lines,
            "clef": "treble", "source_tag": "fx-p4", "cell_canonical_w": w,
            "cell_canonical_h": h, "n_staves_on_page": 2}


def _batch_det(i: int, cls: str, x: int, y: int, w: int = 40, h: int = 40) -> dict:
    return {"id": f"D{i}", "smufl_name": cls, "category": "rest" if cls.startswith("rest") else "notehead",
            "x": x, "y": y, "w": w, "h": h, "x_center": x + w / 2, "y_center": y + h / 2,
            "confidence": 0.7, "pitch": None}


@pytest.fixture
def bench(tmp_path: Path) -> Path:
    b = tmp_path / "bench"
    for d in ("cells", "detections", "verdicts"):
        (b / d).mkdir(parents=True)
    cells = [
        _cell("fx-p4-sys0-s0-m0", 0, 0),          # batch has detections over 3 of them
        _cell("fx-p4-sys0-s0-m1", 0, 1),          # rest
        _cell("fx-p4-sys0-s0-m2", 0, 2),          # draw-from-scratch, with an orphan head
        _cell("fx-p4-sys0-s1-m0", 1, 0, lines=[200, 400, 600, 800, 1000], w=2000, h=1200),
        _cell("fx-p4-sys0-s1-m1", 1, 1),
    ]
    (b / "cells.json").write_text(json.dumps(cells))
    dets = {
        "fx-p4-sys0-s0-m0": [_batch_det(0, "noteheadBlackInSpace", 205, 235),
                             _batch_det(1, "noteheadBlackOnLine", 498, 126),
                             _batch_det(2, "noteheadBlackInSpace", 803, -17),
                             _batch_det(3, "accidentalSharp", 150, 230, 20, 60)],
        "fx-p4-sys0-s0-m1": [_batch_det(0, "restWhole", 400, 150, 40, 20)],
        "fx-p4-sys0-s0-m2": [],
        "fx-p4-sys0-s1-m0": [_batch_det(0, "noteheadBlackInSpace", 800, 660, 80, 80)],
        "fx-p4-sys0-s1-m1": [_batch_det(0, "noteheadBlackOnLine", 300, 280)],
    }
    for cid, ds in dets.items():
        (b / "detections" / f"{cid}.json").write_text(json.dumps({"cell_id": cid, "detections": ds}))
    return b


@pytest.fixture
def truth(tmp_path: Path):
    p = tmp_path / "truth.musicxml"
    p.write_text(TRUTH)
    return load_truth(p)


def _windows_file(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "windows.json"
    p.write_text(json.dumps(rows))
    return p


def _run(bench: Path, truth, rows, **kw) -> dict:
    windows = mv.load_windows(_windows_file(bench.parent, rows))
    return mv.run(bench, _transcription(kw.pop("n0", 3)), truth, windows, **kw)


def _verdict(bench: Path, cid: str) -> dict:
    return json.loads((bench / "verdicts" / f"{cid}.verdict.json").read_text())


# ---------------------------------------------------------------- verdicts


def test_matched_heads_become_verdicts_on_the_batch_ids(bench, truth) -> None:
    summary = _run(bench, truth, _windows(), write=True)
    v = _verdict(bench, "fx-p4-sys0-s0-m0")
    by = {d["id"]: d for d in v["detections"]}
    assert by["D0"]["verdict"] == "WRONG_CATEGORY"
    assert by["D0"]["human_corrected_class"] == "noteheadHalfInSpace"
    assert by["D0"]["human_corrected_category"] == "notehead"
    assert by["D1"]["verdict"] == "TP" and by["D1"]["human_corrected_class"] is None
    # The A5 the reference does not contain stays PENDING, annotated.
    assert by["D2"]["verdict"] is None and "no match" in by["D2"]["notes"]
    # An accidental is not a notehead; untouched.
    assert by["D3"]["verdict"] is None and by["D3"]["notes"] == ""
    assert v["added_detections"] == []
    assert v["schema_version"] == 2 and v["inspected_passes"] == []
    assert all(d["notes"].startswith("mxl_prefill") for d in (by["D0"], by["D1"]))
    cell = next(c for c in summary["cells"] if c["cell_id"] == "fx-p4-sys0-s0-m0")
    assert cell["measure_number"] == 1 and cell["status"] == "prefilled"
    assert (cell["n_tp"], cell["n_wrong_category"]) == (1, 1)


def test_missing_and_extra_notes_become_hints(bench, truth) -> None:
    _run(bench, truth, _windows(), write=True)
    pre = json.loads((bench / "prefill" / "fx-p4-sys0-s0-m0.json").read_text())
    kinds = {h["kind"]: h for h in pre["hints"]}
    missing = kinds["missing"]
    assert missing["pitch"] == "G5" and missing["class"] == "noteheadBlackInSpace"
    # y from the pitch on the treble staff: G5 is the space ABOVE the top line.
    assert missing["bbox"]["y"] + missing["bbox"]["h"] / 2 == pytest.approx(50, abs=1)
    # the frame test's page-1 whole note: A4 sits in the second space (pos 5)
    assert missing["x_estimated"] is True
    assert kinds["extra"]["label"] == "read A5"


def test_rests_are_confirmed_too(bench, truth) -> None:
    _run(bench, truth, _windows(), write=True)
    v = _verdict(bench, "fx-p4-sys0-s0-m1")
    assert v["detections"][0]["verdict"] == "TP"


def test_draw_from_scratch_cell_gets_added_boxes_including_the_orphan(bench, truth) -> None:
    _run(bench, truth, _windows(), write=True)
    v = _verdict(bench, "fx-p4-sys0-s0-m2")
    assert v["detections"] == []
    added = v["added_detections"]
    assert [a["id"] for a in added] == ["M0", "M1"]
    assert {a["human_class"] for a in added} == {"noteheadHalfInSpace"}
    # The stemless second D5 (no duration) still reaches the reference.
    xs = sorted(a["bbox"]["x"] for a in added)
    assert xs == [300, 700]
    assert all(a["notes"].startswith("mxl_prefill") for a in added)


def test_frame_is_mapped_through_the_staff_lines(bench, truth) -> None:
    # Staff 1 measure 0's batch cell is cut at twice the scale; its one batch
    # detection sits where the whole note lands in THAT frame.
    _run(bench, truth, _windows(), write=True)
    v = _verdict(bench, "fx-p4-sys0-s1-m0")
    d = v["detections"][0]
    assert d["verdict"] == "WRONG_CATEGORY"
    assert d["human_corrected_class"] == "noteheadWholeInSpace"
    pre = json.loads((bench / "prefill" / "fx-p4-sys0-s1-m0.json").read_text())
    assert pre["decisions"][0]["bbox"] == {"x": 800, "y": 660, "w": 80, "h": 80}


# ---------------------------------------------------------------- abstentions


def test_no_window_row_abstains(bench, truth) -> None:
    rows = _windows()
    rows[0]["page"]["pdf_page_index"] = 99
    s = _run(bench, truth, rows, write=True)
    assert s["totals"]["abstained"] == 5 and s["totals"]["written"] == 0
    assert not list((bench / "verdicts").glob("*.json"))


def test_staff_count_mismatch_abstains(bench, truth) -> None:
    s = _run(bench, truth, _windows(n_staves=1), write=True)
    assert s["totals"]["abstained"] == 5
    assert all("staves" in c["reason"] for c in s["cells"])


def test_measure_count_disagreement_abstains_unless_trusted(bench, truth) -> None:
    rows = _windows(first=1, last=4)   # window says 4 bars, staff 0 reads 3
    s = _run(bench, truth, rows, write=True)
    st0 = [c for c in s["cells"] if "-s0-" in c["cell_id"]]
    assert all(c["status"] == "abstained" and "window has 4" in c["reason"] for c in st0)
    s2 = _run(bench, truth, rows, write=True, trust_measure_counts=True)
    st0 = [c for c in s2["cells"] if "-s0-" in c["cell_id"]]
    assert all(c["status"] == "prefilled" for c in st0)


def test_weak_alignment_abstains(bench, truth) -> None:
    # Shift the window so staff 0 measure 0 is compared to reference m3
    # (D5 D5): nothing lines up with C5 E5 A5 by position either.
    s = _run(bench, truth, _windows(first=3, last=None), write=True)
    c = next(c for c in s["cells"] if c["cell_id"] == "fx-p4-sys0-s0-m0")
    assert c["status"] == "abstained" and "weak alignment" in c["reason"]
    assert c["alignment"]["geometry"]["width_ratio"] == pytest.approx(1.0)


def test_reading_with_no_notes_yields_hints_only(bench, truth) -> None:
    _run(bench, truth, _windows(), write=True)
    # Oboe m3 is a whole-measure rest in the truth; the reading has nothing.
    pre_path = bench / "prefill" / "fx-p4-sys0-s1-m1.json"
    assert pre_path.exists()
    # Oboe m2 has two truth halves; both read, one as black → relabel.
    v = _verdict(bench, "fx-p4-sys0-s1-m1")
    assert v["detections"][0]["verdict"] == "WRONG_CATEGORY"


# ---------------------------------------------------------------- safety


def test_dry_run_writes_nothing(bench, truth) -> None:
    s = _run(bench, truth, _windows(), write=False)
    assert s["totals"]["prefilled"] >= 4 and s["totals"]["written"] == 0
    assert not (bench / "prefill").exists()
    assert not list((bench / "verdicts").glob("*.json"))


def test_human_work_is_never_overwritten_without_force(bench, truth) -> None:
    cid = "fx-p4-sys0-s0-m0"
    human = {"cell_id": cid, "schema_version": 2, "detections": [],
             "added_detections": [{"id": "H0", "human_class": "noteheadHalfInSpace",
                                   "human_category": "notehead",
                                   "bbox": {"x": 200, "y": 230, "w": 40, "h": 40}, "notes": ""}],
             "inspected_passes": []}
    (bench / "verdicts" / f"{cid}.verdict.json").write_text(json.dumps(human))
    s = _run(bench, truth, _windows(), write=True)
    c = next(c for c in s["cells"] if c["cell_id"] == cid)
    assert c["status"] == "skipped" and not c["written"]
    assert _verdict(bench, cid)["added_detections"][0]["id"] == "H0"
    s = _run(bench, truth, _windows(), write=True, force=True)
    assert next(c for c in s["cells"] if c["cell_id"] == cid)["written"]


def test_score_against_human_verdicts(bench, truth) -> None:
    cid = "fx-p4-sys0-s0-m2"
    # A human drew the first half note where the pre-fill puts M0, and a
    # whole note the pre-fill will not produce.
    human = {"cell_id": cid, "schema_version": 2, "detections": [],
             "added_detections": [
                 {"id": "H0", "human_class": "noteheadHalfInSpace", "human_category": "notehead",
                  "bbox": {"x": 296, "y": 176, "w": 44, "h": 44}, "notes": ""},
                 {"id": "H1", "human_class": "noteheadWholeOnLine", "human_category": "notehead",
                  "bbox": {"x": 900, "y": 100, "w": 40, "h": 40}, "notes": ""}],
             "inspected_passes": ["hollow noteheads"]}
    (bench / "verdicts" / f"{cid}.verdict.json").write_text(json.dumps(human))
    (bench / "batch_config.json").write_text(json.dumps({"pass_name": "hollow noteheads", "classes": [
        {"on_line": "noteheadHalfOnLine", "in_space": "noteheadHalfInSpace", "click_box": True},
        {"on_line": "noteheadWholeOnLine", "in_space": "noteheadWholeInSpace", "click_box": True}]}))
    s = _run(bench, truth, _windows(), write=False, score=True)
    sc = s["score"]
    assert sc["cells_scored"] == 1
    assert (sc["n_prefill"], sc["n_human"]) == (2, 2)
    assert sc["matched_exact"] == 1
    assert sc["precision_exact"] == 0.5 and sc["recall_exact"] == 0.5
    assert s["pass_classes"] == ["noteheadHalfInSpace", "noteheadHalfOnLine",
                                 "noteheadWholeInSpace", "noteheadWholeOnLine"]


# ---------------------------------------------------------------- downstream


def test_converter_reads_prefilled_verdicts_unchanged(bench, truth) -> None:
    _run(bench, truth, _windows(), write=True)
    names = load_class_names(None, Path("tools/omr/training/deepscoresv2_208_classes.json"))
    index = name_to_first_index(names)
    v = _verdict(bench, "fx-p4-sys0-s0-m0")
    assert _is_filled(v)
    lines, summ = convert_cell(cell_id=v["cell_id"], verdict_state=v,
                               artifacts=CellArtifacts(cell_id=v["cell_id"], cell_png=Path("x.png"),
                                                       canonical_w=1000, canonical_h=600,
                                                       detections={}),
                               class_index=index)
    # TP keeps the model class, WRONG_CATEGORY takes the corrected one, the
    # pending A5 and the untouched accidental emit nothing.
    assert len(lines) == 2
    assert summ.n_tp == 1 and summ.n_wrong_cat == 1
    classes = {int(l.split()[0]) for l in lines}
    assert index["noteheadHalfInSpace"] in classes and index["noteheadBlackOnLine"] in classes
    v2 = _verdict(bench, "fx-p4-sys0-s0-m2")
    lines2, summ2 = convert_cell(cell_id=v2["cell_id"], verdict_state=v2,
                                 artifacts=CellArtifacts(cell_id=v2["cell_id"], cell_png=Path("x.png"),
                                                         canonical_w=1000, canonical_h=600,
                                                         detections={}),
                                 class_index=index)
    assert len(lines2) == 2 and summ2.n_fn_added == 2


def test_windows_accept_the_scan_benchmark_file() -> None:
    path = Path("benchmarks/omr-scan-e2e-2026-09/works.json")
    # Several editions share a page index: the file must be narrowed.
    with pytest.raises(ValueError):
        mv.load_windows(path)
    rows = mv.load_windows(path, row_ids=["beethoven-sym5-mvt1-984073-p1"])
    assert list(rows) == [1]
    row = rows[1]
    assert row.first_ref_measure == 1 and row.last_ref_measure == 16
    assert len(row.staves) == 12 and row.staves[0].parts == [0, 1]
    # `same-as:` references resolve to the row they name.
    both = mv.load_windows(path, work_id="beethoven--symphony-5")
    assert all(r.staves for r in both.values())


# ---------------------------------------------------------------- the UI


def test_server_serves_prefilled_verdicts_and_hints(bench, truth) -> None:
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tools.omr.annotate.server import create_app

    _run(bench, truth, _windows(), write=True)
    # The server wants a PNG per cell; a placeholder is enough for the API.
    for cid in json.loads((bench / "cells.json").read_text()):
        (bench / "cells" / f"{cid['cell_id']}.png").write_bytes(b"")
    client = TestClient(create_app(bench))

    cells = {c["cell_id"]: c for c in client.get("/api/cells").json()}
    c = cells["fx-p4-sys0-s0-m0"]
    assert c["prefill_status"] == "prefilled"
    assert c["n_hints"] == 2 and c["n_hints_missing"] == 1
    assert c["n_decided"] == 2 and c["n_pending"] == 2

    detail = client.get("/api/cell/fx-p4-sys0-s0-m0").json()
    assert detail["prefill"]["measure_number"] == 1
    assert [h["kind"] for h in detail["prefill"]["hints"]] == ["extra", "missing"]

    # The pre-filled state survives the server's own reconciliation …
    state = client.get("/api/cell/fx-p4-sys0-s0-m0/verdict").json()["state"]
    by = {d["id"]: d for d in state["detections"]}
    assert by["D0"]["verdict"] == "WRONG_CATEGORY"
    assert by["D0"]["human_corrected_class"] == "noteheadHalfInSpace"
    assert by["D0"]["notes"].startswith("mxl_prefill")
    # … and a human save keeps the provenance notes and the M-boxes.
    state2 = client.get("/api/cell/fx-p4-sys0-s0-m2/verdict").json()["state"]
    assert [a["id"] for a in state2["added_detections"]] == ["M0", "M1"]
    r = client.post("/api/cell/fx-p4-sys0-s0-m2/verdict", json=state2)
    assert r.status_code == 200, r.text
    saved = _verdict(bench, "fx-p4-sys0-s0-m2")
    assert saved["added_detections"][0]["notes"].startswith("mxl_prefill")

    # A batch with no prefill directory reports nothing, as before.
    other = cells["fx-p4-sys0-s1-m1"]
    assert "prefill_status" in other


def test_write_hints_leaves_verdicts_untouched(bench, truth) -> None:
    s = _run(bench, truth, _windows(), write=True, hints_only=True)
    assert s["hints_only"] is True and s["totals"]["written"] == 0
    assert (bench / "prefill" / "fx-p4-sys0-s0-m0.json").exists()
    assert not list((bench / "verdicts").glob("*.json"))


def test_two_systems_number_measures_across_the_page(bench, truth) -> None:
    """A second system's staves are numbered after the first's on the page;
    their measure numbers continue from the first system's bar count."""
    tr = _transcription()
    page = tr["pages"][0]
    first = page["systems"][0]
    # Split staff 0's three measures: measures 0-1 in system 0, measure 2
    # alone in system 1 as page-level staff 2.
    s0 = first["staves"][0]
    tail = s0["measures"][2:]
    s0["measures"] = s0["measures"][:2]
    s0["n_measures"] = 2
    s1 = first["staves"][1]
    s1["measures"] = s1["measures"][:2]
    s1["n_measures"] = 2
    for m in tail:
        m["measure_index"] = 0
    page["systems"].append({"system_index": 1, "staves": [
        {"staff_index": 2, "clef": "treble", "n_measures": 1, "measures": tail},
        {"staff_index": 3, "clef": "treble", "n_measures": 1,
         "measures": [_measure(0, [])]},
    ]})
    cells = json.loads((bench / "cells.json").read_text())
    cells.append(dict(_cell("fx-p4-sys1-s2-m0", 2, 0), system_index=1))
    (bench / "cells.json").write_text(json.dumps(cells))
    (bench / "detections" / "fx-p4-sys1-s2-m0.json").write_text(
        json.dumps({"cell_id": "fx-p4-sys1-s2-m0", "detections": []}))
    windows = mv.load_windows(_windows_file(bench.parent, _windows()))
    s = mv.run(bench, tr, truth, windows, write=True)
    c = next(c for c in s["cells"] if c["cell_id"] == "fx-p4-sys1-s2-m0")
    assert c["status"] == "prefilled" and c["measure_number"] == 3
    v = _verdict(bench, "fx-p4-sys1-s2-m0")
    assert {a["human_class"] for a in v["added_detections"]} == {"noteheadHalfInSpace"}


def test_staff_disagreeing_with_its_system_abstains(bench, truth) -> None:
    tr = _transcription()
    st = tr["pages"][0]["systems"][0]["staves"][1]
    st["measures"] = st["measures"][:2]
    st["n_measures"] = 2                      # staff 1 reads 2 bars, the system 3
    windows = mv.load_windows(_windows_file(bench.parent, _windows()))
    s = mv.run(bench, tr, truth, windows, write=False)
    by = {c["cell_id"]: c for c in s["cells"]}
    assert by["fx-p4-sys0-s1-m0"]["status"] == "abstained"
    assert "its system reads 3" in by["fx-p4-sys0-s1-m0"]["reason"]
    assert by["fx-p4-sys0-s0-m0"]["status"] == "prefilled"


BASS_TRUTH = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Cello</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>2</divisions><clef><sign>F</sign><line>4</line></clef></attributes>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><type>half</type></note>
      <note><pitch><step>B</step><octave>3</octave></pitch><duration>4</duration><type>half</type></note>
    </measure>
  </part>
</score-partwise>
"""


def test_a_misread_clef_still_confirms_the_boxes(tmp_path: Path) -> None:
    """The scan's cello staff was read as treble: G3 and B3 came out as B4
    and D5. Their boxes are right, and the reference clef says where G3 and
    B3 sit — so by position both heads are confirmed and relabelled hollow."""
    b = tmp_path / "bench"
    for d in ("cells", "detections", "verdicts"):
        (b / d).mkdir(parents=True)
    (b / "cells.json").write_text(json.dumps([_cell("fx-p4-sys0-s0-m0", 0, 0)]))
    (b / "detections" / "fx-p4-sys0-s0-m0.json").write_text(
        json.dumps({"cell_id": "fx-p4-sys0-s0-m0", "detections": []}))
    tp = tmp_path / "bass.musicxml"
    tp.write_text(BASS_TRUTH)
    truth = load_truth(tp)
    d1 = _det("noteheadBlackOnLine", "B4", 200, 130, dur=1.0)   # cy 150 → pos 1 = G3 in bass
    d2 = _det("noteheadBlackInSpace", "D5", 600, 30, dur=1.0)   # cy 50 → pos -1 = B3 in bass
    tr = {"pages": [{"page_index": 3, "systems": [{"system_index": 0, "staves": [
        {"staff_index": 0, "clef": "treble", "n_measures": 1, "measures": [_measure(0, [d1, d2])]}]}]}]}
    rows = [{"row_id": "fx", "page": {"pdf_page_index": 3},
             "window": {"first_ref_measure": 1, "last_ref_measure": 1},
             "staves": [{"name": "Violoncell", "parts": [0]}]}]
    windows = mv.load_windows(_windows_file(tmp_path, rows))
    s_step = mv.run(b, tr, truth, windows, write=False, match="step")
    assert s_step["cells"][0]["status"] == "abstained"
    s_pos = mv.run(b, tr, truth, windows, write=True)
    c = s_pos["cells"][0]
    assert c["status"] == "prefilled" and c["n_wrong_category"] == 2 and c["n_added"] == 2
    v = _verdict(b, "fx-p4-sys0-s0-m0")
    assert [a["human_class"] for a in v["added_detections"]] == ["noteheadHalfOnLine", "noteheadHalfInSpace"]


def test_percussion_part_falls_back_to_step_keys_on_both_sides(tmp_path: Path) -> None:
    xml = BASS_TRUTH.replace("<sign>F</sign><line>4</line>", "<sign>percussion</sign>")
    tp = tmp_path / "perc.musicxml"
    tp.write_text(xml)
    truth = load_truth(tp)
    assert truth.part(0).measures[0].notes[0].clef is None
    b = tmp_path / "bench"
    for d in ("cells", "detections", "verdicts"):
        (b / d).mkdir(parents=True)
    (b / "cells.json").write_text(json.dumps([_cell("fx-p4-sys0-s0-m0", 0, 0)]))
    (b / "detections" / "fx-p4-sys0-s0-m0.json").write_text(
        json.dumps({"cell_id": "fx-p4-sys0-s0-m0", "detections": []}))
    d1 = _det("noteheadBlackOnLine", "G3", 200, 130, dur=2.0, dtype="half")
    d2 = _det("noteheadBlackInSpace", "B3", 600, 30, dur=2.0, dtype="half")
    tr = {"pages": [{"page_index": 3, "systems": [{"system_index": 0, "staves": [
        {"staff_index": 0, "clef": "bass", "n_measures": 1, "measures": [_measure(0, [d1, d2])]}]}]}]}
    rows = [{"row_id": "fx", "page": {"pdf_page_index": 3},
             "window": {"first_ref_measure": 1, "last_ref_measure": 1},
             "staves": [{"name": "Pauken", "parts": [0]}]}]
    windows = mv.load_windows(_windows_file(tmp_path, rows))
    s = mv.run(b, tr, truth, windows, write=False)
    c = s["cells"][0]
    assert c["status"] == "prefilled" and c["alignment"]["match"] == "step"
    assert c["alignment"]["truth_keys"] == ["G3", "B3"] and c["alignment"]["pairs"] == [(0, 0), (1, 1)]
    assert c["alignment"]["geometry"]["width_ratio"] == pytest.approx(1.0)


def test_neighbour_staff_heads_do_not_sink_the_alignment(bench, truth) -> None:
    """A flute bar of 3 reference notes read with 12 extra heads from the
    staves above and below (positions far outside the staff): the 3 real
    heads still confirm, the 12 stay pending as extra hints."""
    tr = _transcription()
    m0 = tr["pages"][0]["systems"][0]["staves"][0]["measures"][0]
    m0["detections"] = [d for d in m0["detections"] if d["pitch"] != "A5"]
    extra = []
    for k in range(6):
        extra.append(_det("noteheadBlackOnLine", "C3", 100 + 120 * k, 780))    # cy 800 → P14
        extra.append(_det("noteheadBlackInSpace", "C7", 120 + 120 * k, -520))  # cy -500 → P-12
    m0["detections"].extend(extra)
    windows = mv.load_windows(_windows_file(bench.parent, _windows()))
    s = mv.run(bench, tr, truth, windows, write=True)
    c = next(c for c in s["cells"] if c["cell_id"] == "fx-p4-sys0-s0-m0")
    assert c["status"] == "prefilled"
    assert c["alignment"]["matched"] == 2 and c["alignment"]["n_truth"] == 3
    assert c["alignment"]["n_pred"] == 14 and c["alignment"]["n_pred_in_range"] == 2
    assert c["n_hints_extra"] == 12
    v = _verdict(bench, "fx-p4-sys0-s0-m0")
    by = {d["id"]: d for d in v["detections"]}
    assert by["D0"]["verdict"] == "WRONG_CATEGORY" and by["D1"]["verdict"] == "TP"


def test_an_empty_reading_yields_hints_not_an_abstention(bench, truth) -> None:
    """Flute staff condensed to parts [0, 1]: truth m2 is B4 C5 (part 1) with
    the rests dropped; the reading of that bar is one whole rest, which a
    condensed bar ignores. Nothing to align — the two notes become hints."""
    tr = _transcription()
    rows = [dict(_windows()[0], staves=[{"name": "Fl", "parts": [0, 1]}, {"name": "Ob", "parts": [1]}])]
    windows = mv.load_windows(_windows_file(bench.parent, rows))
    s = mv.run(bench, tr, truth, windows, write=True)
    c = next(c for c in s["cells"] if c["cell_id"] == "fx-p4-sys0-s0-m1")
    assert c["status"] == "prefilled" and "hints only" in c["reason"]
    assert c["n_hints_missing"] == 2 and c["n_tp"] == 0
