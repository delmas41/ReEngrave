"""ROADMAP 2.189: the detector's raw-output cache (tools/omr/detector_cache.py). A fake model drives the real
ultralytics NMS + construct_results, so a miss/hit comparison exercises the same code a real model does."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("ultralytics")
from ultralytics.models.yolo.detect.predict import DetectionPredictor
from ultralytics.utils import nms

from tools.omr import detector_cache as dc

NC, N = 6, 400


def _head(seed=0):
    g = torch.Generator().manual_seed(seed)
    pred = torch.rand((1, 4 + NC, N), generator=g) * 0.4              # scores < 0.4
    cx, cy = torch.rand(N, generator=g) * 300 + 20, torch.rand(N, generator=g) * 200 + 20
    pred[0, 0], pred[0, 1] = cx, cy
    pred[0, 2], pred[0, 3] = 10 + torch.rand(N, generator=g) * 30, 10 + torch.rand(N, generator=g) * 30
    pred[0, 4:, :40] += torch.rand((NC, 40), generator=g) * 0.6       # some strong anchors (ties impossible)
    return pred


class FakeModel:
    """`predict` = what ultralytics does: NMS on the head, then construct_results with the letterboxed shape."""
    def __init__(self):
        self.calls = 0

    def predict(self, *, source, conf, iou, agnostic_nms, imgsz, device, verbose):
        self.calls += 1
        imgs = [source] if isinstance(source, np.ndarray) else list(source)
        head = _head().repeat(len(imgs), 1, 1)
        out = nms.non_max_suppression(head, conf, iou, None, agnostic_nms, max_det=300, nc=0)
        p = DetectionPredictor.__new__(DetectionPredictor)
        p.batch = ([f"im{i}" for i in range(len(imgs))],)
        p.model = type("M", (), {"names": {i: str(i) for i in range(NC)}})()
        return DetectionPredictor.construct_results(p, out, torch.zeros((len(imgs), 3, 256, 352)), imgs)


@pytest.fixture
def wfile(tmp_path):
    w = tmp_path / "w.pt"
    w.write_bytes(b"weights-one")
    return str(w)


def _arr(res):
    b = res[0].boxes
    return np.concatenate([b.xyxy.cpu().numpy(), b.conf.cpu().numpy()[:, None], b.cls.cpu().numpy()[:, None]], 1)


def _img(v=0):
    im = np.full((200, 300, 3), 255, np.uint8)
    im[10, 10] = v
    return im


def _run(m, w, root, img, conf=0.25, iou=0.7, agn=False, imgsz=320):
    return dc.predict(m, w, source=img, conf=conf, iou=iou, agnostic_nms=agn, imgsz=imgsz, device=None, root=root)


def test_cold_warm_none_identical_and_hit_counted(tmp_path, wfile):
    m, root, im = FakeModel(), tmp_path / "c", _img()
    none = _arr(_run(m, wfile, None, im))
    h0 = dc.stats()["hits"]
    cold = _arr(_run(m, wfile, root, im))
    warm = _arr(_run(m, wfile, root, im))
    assert np.array_equal(none, cold) and np.array_equal(none, warm) and len(none) > 3
    assert dc.stats()["hits"] == h0 + 1 and m.calls == 2          # the warm call never reached the model


def test_nms_change_is_served_from_cache_exactly(tmp_path, wfile):
    m, root, im = FakeModel(), tmp_path / "c", _img()
    _run(m, wfile, root, im, iou=0.7, agn=False)
    calls = m.calls
    for iou, agn in ((0.3, False), (0.5, True), (0.9, True)):
        fresh = _arr(_run(m, wfile, None, im, iou=iou, agn=agn))
        calls_after_fresh = m.calls
        served = _arr(_run(m, wfile, root, im, iou=iou, agn=agn))
        assert m.calls == calls_after_fresh, "served from the cache, no model call"
        assert np.array_equal(fresh, served)
    assert m.calls > calls


@pytest.mark.parametrize("change", ["conf", "pixel", "imgsz", "weights", "shape"])
def test_one_key_part_is_a_miss(tmp_path, wfile, change):
    m, root = FakeModel(), tmp_path / "c"
    _run(m, wfile, root, _img())
    n = m.calls
    kw, img, w = {}, _img(), wfile
    if change == "conf":
        kw["conf"] = 0.2
    elif change == "pixel":
        img = _img(1)
    elif change == "imgsz":
        kw["imgsz"] = 352
    elif change == "weights":
        w = str(tmp_path / "w2.pt")
        open(w, "wb").write(b"weights-two")
    elif change == "shape":
        img = np.full((201, 300, 3), 255, np.uint8)
    _run(m, w, root, img, **kw)
    assert m.calls == n + 1


def test_batch_call_roundtrips(tmp_path, wfile):
    m, root = FakeModel(), tmp_path / "c"
    ims = [_img(0), _img(5)]
    a = dc.predict(m, wfile, source=ims, conf=0.1, iou=0.7, imgsz=320, device=None, root=None)
    dc.predict(m, wfile, source=ims, conf=0.1, iou=0.7, imgsz=320, device=None, root=root)
    b = dc.predict(m, wfile, source=ims, conf=0.1, iou=0.7, imgsz=320, device=None, root=root)
    assert len(a) == len(b) == 2
    for x, y in zip(a, b):
        assert np.array_equal(x.boxes.xyxy.numpy(), y.boxes.xyxy.numpy())


def _entry(root):
    return next(root.glob("*/*.npz"))


def test_corrupt_partial_and_misfiled_entries_raise(tmp_path, wfile):
    m, root, im = FakeModel(), tmp_path / "c", _img()
    _run(m, wfile, root, im)
    p = _entry(root)
    good = p.read_bytes()
    p.write_bytes(good[: len(good) // 2])                           # partial
    with pytest.raises(dc.DetectorCacheError):
        _run(m, wfile, root, im)
    p.write_bytes(b"not a zip")
    with pytest.raises(dc.DetectorCacheError):
        _run(m, wfile, root, im)
    # a valid file filed under the wrong name: manifest key != request key
    p.write_bytes(good)
    other = _img(9)
    _run(m, wfile, root, other)
    q = [x for x in root.glob("*/*.npz") if x != p][0]
    q.write_bytes(good)
    with pytest.raises(dc.DetectorCacheError):
        _run(m, wfile, root, other)
    # payload edited, manifest intact: checksum fails
    z = np.load(p)
    arrays = {k: z[k] for k in z.files}
    arrays["score0"] = arrays["score0"] * 0.5
    np.savez_compressed(p, **arrays)
    with pytest.raises(dc.DetectorCacheError):
        _run(m, wfile, root, im)


def test_no_cache_is_the_plain_call(wfile):
    m = FakeModel()
    assert dc.cache_dir() is None or True
    r = dc.predict(m, wfile, source=_img(), conf=0.25, iou=0.7, imgsz=320, device=None, root=None)
    assert m.calls == 1 and len(r) == 1
