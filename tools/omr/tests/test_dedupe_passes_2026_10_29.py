"""ROADMAP 2.220c: duplicate passes removed from STAGED GATHER. Results must be identical; these pin the helpers."""
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr.staged import gather as G
from tools.omr import yolo_detector as Y


def test_page_memo_builds_once_and_reraises_the_same_error():
    pws = SimpleNamespace()
    calls = []
    assert G._page_memo(pws, "k", lambda: calls.append(1) or 7) == 7
    assert G._page_memo(pws, "k", lambda: calls.append(1) or 8) == 7
    assert len(calls) == 1

    def boom():
        calls.append(2)
        raise ValueError("x")
    for _ in range(2):
        with pytest.raises(ValueError):
            G._page_memo(pws, "e", boom)
    assert calls.count(2) == 1


def test_raw_page_ink_is_cached_and_equals_the_old_threshold():
    import cv2
    rgb = (np.random.RandomState(0).rand(40, 50, 3) * 255).astype(np.uint8)
    pws = SimpleNamespace(page=SimpleNamespace(rgb=rgb))
    a = G._raw_page_ink(pws)
    assert a is G._raw_page_ink(pws)
    gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
    assert (a == cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1]).all()
    assert G._raw_page_ink(SimpleNamespace(page=SimpleNamespace(rgb=None))) is None


class _Boxes:
    def __init__(self, xyxy, conf, cls):
        self.xyxy, self.conf, self.cls = np.array(xyxy, float), np.array(conf, float), np.array(cls, float)

    def __len__(self):
        return len(self.conf)


def _detector(calls):
    det = Y.YoloDetector.__new__(Y.YoloDetector)
    det.weights_path, det.device, det._model = "w", "cpu", object()
    det._class_names = {0: "noteheadBlack"}
    ALL = [([0, 0, 10, 10], 0.9), ([20, 0, 30, 10], 0.2), ([40, 0, 50, 10], 0.07), ([60, 0, 70, 10], 0.04)]

    def predict(**kw):
        calls.append(kw["conf"])
        sel = [(b, c) for b, c in ALL if c > kw["conf"]]
        if not sel:
            return [SimpleNamespace(boxes=None)]
        return [SimpleNamespace(boxes=_Boxes([b for b, _ in sel], [c for _, c in sel], [0] * len(sel)))]
    det._predict = predict
    det._ensure_loaded = lambda: None
    return det


def test_floor_memo_runs_once_and_serves_each_floor_as_a_direct_run_would():
    cell = SimpleNamespace(image=np.zeros((20, 80), np.uint8))
    calls_memo, calls_plain = [], []
    d1, d2 = _detector(calls_memo), _detector(calls_plain)
    d1_out = {f: d1.detect(cell, conf_threshold=f, imgsz=64, floor_memo=True) for f in (0.10, 0.03, 0.05)}
    assert len(calls_memo) == 1 and calls_memo[0] == Y.FLOOR_MEMO_FLOOR
    for f, got in d1_out.items():
        want = d2.detect(SimpleNamespace(image=np.zeros((20, 80), np.uint8)), conf_threshold=f, imgsz=64)
        key = lambda ds: [(d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical, d.confidence) for d in ds]
        assert key(got) == key(want), f
    assert len(calls_plain) == 3


def test_rescue_detect_falls_back_for_a_double_without_floor_memo():
    seen = {}

    class Double:
        def detect(self, cell, conf_threshold=0.25, imgsz=None):
            seen["a"] = (conf_threshold, imgsz)
            return ["x"]
    assert G._rescue_detect(Double(), object(), 0.1, 64) == ["x"] and seen["a"] == (0.1, 64)
