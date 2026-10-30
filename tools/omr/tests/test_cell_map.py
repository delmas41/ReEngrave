"""ROADMAP 2.231 -- the master cell map: build, load, equivalence, every mismatch RAISES, and the moved listing.

A synthetic page (two five-line staves, one system, barlines) stands in for the pdf: `render_page` is replaced by
one that draws it, so these run with no library, no weights and no venv. The real-plate proof (Litolff p9-10) is in
benchmarks/master-cell-map-2026-10/FINDINGS.md.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from tools.omr.staged import cell_map as CM
from tools.omr.types import PageImage

BARS = (480, 860)


def _draw(page_index: int, bars=BARS, shift: int = 0) -> PageImage:
    h, w = 900, 1300
    g = np.full((h, w), 255, np.uint8)
    for top in (200, 420):
        for i in range(5):
            y = top + i * 20 + shift
            g[y:y + 2, 100:1200] = 0
    for x in (100,) + tuple(bars) + (1198,):
        g[200 + shift:502 + shift, x:x + 3] = 0          # through both staves and the gap: a system barline
    g[250:262, 300:316] = 0                             # a notehead-ish blob, so cells carry ink
    rgb = np.stack([g, g, g], axis=-1)
    return PageImage(pdf_path=Path("synthetic.score"), page_index=page_index, dpi=600, rgb=rgb, binary=g.copy())


@pytest.fixture
def plate(tmp_path, monkeypatch):
    """A fake score file + a `render_page` that draws the synthetic page; `state` lets a test change the drawing."""
    from tools.omr import preprocessing
    src = tmp_path / "plate.score"
    src.write_bytes(b"synthetic plate v1")
    state = {"bars": BARS, "shift": 0}
    monkeypatch.setattr(preprocessing, "render_page",
                        lambda path, p, dpi=600: _draw(p, state["bars"], state["shift"]))
    return src, tmp_path / "maps", state


def _fresh(src, pages):
    from tools.omr.staged.pipeline import prepare_pages
    return prepare_pages(str(src), pages)


def test_synthetic_page_has_cells(plate):
    src, _, _ = plate
    [(pws, cells)] = _fresh(src, [3])
    assert len(pws.staves) == 2 and len(cells) >= 4, (len(pws.staves), len(cells))


def test_build_then_load_equals_a_fresh_cut(plate):
    src, root, _ = plate
    man = CM.build(src, [3, 4], root=root)
    assert man["version"].startswith("cm-") and set(man["pages"]) == {"3", "4"}
    assert man["built"]["cutting_sources"], "the builder names the code that cut"
    loaded = CM.load_prepared(src, [3, 4], root=root)
    fresh = _fresh(src, [3, 4])
    for (lp, lc), (fp, fc) in zip(loaded, fresh):
        assert CM.snapshot_page(lp, lc) == CM.snapshot_page(fp, fc)
        assert len(lc) == len(fc)
        for a, b in zip(lc, fc):
            assert a.bbox_page_px == b.bbox_page_px
            assert a.staff_line_ys_canonical == b.staff_line_ys_canonical
            assert np.array_equal(a.image, b.image) and np.array_equal(a.image_no_staff, b.image_no_staff)
        assert vars(lp).keys() == vars(fp).keys() and lp.deletion_counts == fp.deletion_counts
    assert CM.loaded()[-1]["version"] == man["version"]


def test_loading_ignores_a_changed_cutter_upstream(plate, monkeypatch):
    """The point of the master: a staff/barline change upstream does NOT move the loaded cells."""
    src, root, state = plate
    CM.build(src, [3], root=root)
    master = CM.snapshot_page(*CM.load_prepared(src, [3], root=root)[0])
    from tools.omr import measure_extractor as ME
    real = ME.detect_barlines

    def drop_one(pws):                                   # a "barline lane": loses the middle barline
        out = real(pws)
        pws.barlines = [b for b in pws.barlines if abs(b.x - BARS[1]) > 6]
        return out
    monkeypatch.setattr(ME, "detect_barlines", drop_one)
    recut = CM.snapshot_page(*_fresh(src, [3])[0])
    assert recut != master, "the control must be able to fail: the re-cut arm moves"
    again = CM.snapshot_page(*CM.load_prepared(src, [3], root=root)[0])
    assert again == master, "the loaded arm keeps the master's cells"
    man, rows = CM.moved(src, [3], root=root)
    kinds = {r["what"] for r in rows}
    assert "barlines" in kinds and "cell" in kinds
    assert any(r["what"] == "barlines" and r["removed"] for r in rows)
    assert "NOTHING MOVED" not in CM.render_moved(man, rows)


def test_moved_is_empty_on_the_same_tree(plate):
    src, root, _ = plate
    CM.build(src, [3], root=root)
    man, rows = CM.moved(src, [3], root=root)
    assert rows == [] and "NOTHING MOVED" in CM.render_moved(man, rows)


def test_mismatches_raise(plate):
    src, root, state = plate
    CM.build(src, [3], root=root)
    with pytest.raises(CM.CellMapError, match="no page"):
        CM.load_prepared(src, [5], root=root)
    with pytest.raises(CM.CellMapError, match="dpi"):
        CM.load_prepared(src, [3], root=CM.master_dir(root, CM.sha256_file(src), 600), dpi=300)
    other = src.parent / "other.score"
    other.write_bytes(b"a different plate")
    with pytest.raises(CM.CellMapError):
        CM.load_prepared(other, [3], root=root)              # no master for this file at all
    with pytest.raises(CM.CellMapError, match="is for pdf"):
        CM.load_prepared(other, [3], root=CM.master_dir(root, CM.sha256_file(src), 600))
    state["shift"] = 2                                       # the render moved: never re-cut around it
    with pytest.raises(CM.CellMapError, match="renders to other pixels"):
        CM.load_prepared(src, [3], root=root)


def test_a_perturbed_master_is_detected(plate):
    src, root, _ = plate
    CM.build(src, [3], root=root)
    mdir = CM.master_dir(root, CM.sha256_file(src), 600)
    f = mdir / "pages" / "p003.json.gz"
    snap = json.loads(gzip.decompress(f.read_bytes()))
    # 1. edited without re-hashing: the stored hash catches it
    snap["cells"][0]["v"]["bbox_page_px"]["$t"][0] += 7
    f.write_bytes(gzip.compress(json.dumps(snap).encode()))
    with pytest.raises(CM.CellMapError, match="edited or corrupt"):
        CM.load_prepared(src, [3], root=root)
    # 2. edited AND re-hashed (a forged master): the re-cut does not reproduce it
    snap["geometry_hash"] = CM.geometry_hash(snap)
    f.write_bytes(gzip.compress(json.dumps(snap).encode()))
    man = json.loads((mdir / "manifest.json").read_text())
    man["pages"]["3"] = snap["geometry_hash"]
    (mdir / "manifest.json").write_text(json.dumps(man))
    with pytest.raises(CM.CellMapError, match="other cells"):
        CM.load_prepared(src, [3], root=root)


def test_rebuild_is_deliberate(plate):
    src, root, state = plate
    CM.build(src, [3], root=root)
    state["bars"] = (480,)
    with pytest.raises(CM.CellMapError, match="--force"):
        CM.build(src, [3], root=root)
    man = CM.build(src, [3], root=root, force=True)
    assert man["pages"]["3"] == CM.snapshot_page(*_fresh(src, [3])[0])["geometry_hash"]


def test_encoding_is_lossless():
    v = {"a": (1, 2.5, None), 0: [True, {"$x": 1}], "n": np.int64(3), "f": np.float32(0.5)}
    back = CM.dec(CM.enc(v))
    assert back == v and isinstance(back["a"], tuple) and type(back["n"]) is np.int64


def test_tile_position_from_key():
    from tools.omr.staged.lane_report import tile_position
    assert tile_position({"rg": "glyph/9/1/3/4/12", "box": [1, 2, 3, 4]}) == dict(
        page=9, system=1, staff=3, cell=4, page_box=[1, 2, 3, 4])
    assert tile_position({"rg": "something-else"}) is None


def test_judged_rows_carry_master_only_when_given(tmp_path):
    from tools.omr.staged import judged
    g = tmp_path / "gallery"
    g.mkdir()
    key = [{"tile": 1, "plate": "litolff", "rg": "glyph/9/0/2/3/5", "subject": "glyph/9/0/2/3/5", "written": "quarter",
            "box": [1, 2, 3, 4], "cell_map": "cm-abc", "position": {"page": 9, "system": 0, "staff": 2, "cell": 3}},
           {"tile": 2, "plate": "litolff", "rg": "glyph/9/0/2/3/6", "subject": "glyph/9/0/2/3/6", "written": "half",
            "box": [1, 2, 3, 4]}]
    (g / "key.json").write_text(json.dumps(key))
    (g / "answers.json").write_text(json.dumps({"1": "4", "2": "2", "date": "2026-10-29"}))
    rows = {r["tile"]: r for r in judged.item_rows(g / "answers.json", tmp_path)}
    assert rows["1"]["cell_map"] == "cm-abc" and rows["1"]["position"]["cell"] == 3
    assert "cell_map" not in rows["2"] and "position" not in rows["2"]
