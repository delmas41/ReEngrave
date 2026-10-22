"""ROADMAP 2.189 -- read the page once: a cache of the detector's RAW output, below NMS.

WHAT IS CACHED. Ultralytics `predict` = letterbox -> forward -> `nms.non_max_suppression` -> `scale_boxes`.
The forward pass is the cost (~30 min/arm on Litolff). This module stores what the forward pass produced
(the head tensor `(B, 4+nc, N)`), reduced to its CANDIDATES -- every anchor whose best class score is
above the conf floor the caller asked for (the exact set NMS starts from when `multi_label=False`, which
is what `predict` uses): anchor index, box (cx, cy, w, h in network pixels), best class, its score. On a
hit the tensor is rebuilt (zeros elsewhere, which `xc = amax > conf` drops again), run through the SAME
`non_max_suppression` with the CALLER's `iou` / `agnostic_nms`, and scaled with the SAME `scale_boxes`.
So a lane that changes NMS (IoU, class-agnostic within a family, `max_det`) or anything after it is served
from the cache; the answer equals a fresh read (controls in benchmarks/lane-report/FINDINGS.md 2.189).

WHAT IT CANNOT SERVE. A lane that changes (a) the conf floor (a different floor is a different key: a
miss, never a reuse), (b) the crop the model is shown (different pixels, `imgsz`, view, shifts,
anti-aliasing), (c) the weights, (d) multi-label NMS (only the best class per anchor is stored). Those
re-read the page.

THE KEY MAKES A STALE HIT IMPOSSIBLE. sha256 of: format version, ultralytics + torch versions, the
weights FILE hash (so the model and the route that picked it), the device, conf, imgsz, and for every
image of the call its shape, dtype and a hash of its pixels (the dpi and the view are in the pixels).
`iou` and `agnostic_nms` are deliberately NOT in the key: they act only on the stored candidates, at serve
time, with the caller's values. A hit whose manifest does not match, a truncated file, a bad payload
checksum, an unreadable file: `DetectorCacheError` -- RAISED, never recomputed silently (CLAUDE rule 8).

Activated by `OMR_DETECTOR_CACHE=<dir>` (or `--detector-cache DIR` on `tools.omr.staged`); unset = no
cache, the code path is the original `self._model.predict(...)`.
"""
from __future__ import annotations

import atexit
import contextlib
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

FORMAT = 1
ENV = "OMR_DETECTOR_CACHE"
MAX_DET = 300                       # ultralytics' default; `predict` here never overrides it


class DetectorCacheError(RuntimeError):
    """A cache entry that exists but cannot be trusted. Never swallowed."""


_STATS = {"hits": 0, "misses": 0, "bytes_written": 0, "bytes_read": 0, "miss_s": 0.0, "hit_s": 0.0, "plain_s": 0.0, "calls_plain": 0}
_WEIGHT_HASH: Dict[Any, str] = {}
_USED_WEIGHTS: set = set()
_LOCK = threading.Lock()


def stats() -> Dict[str, int]:
    return dict(_STATS)


def cache_dir() -> Optional[Path]:
    d = os.environ.get(ENV)
    return Path(d) if d else None


def weights_hash(path: str) -> str:
    st = os.stat(path)
    ck = (os.path.abspath(path), st.st_size, st.st_mtime_ns)
    with _LOCK:
        h = _WEIGHT_HASH.get(ck)
    if h is None:
        m = hashlib.sha256()
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(1 << 22), b""):
                m.update(blk)
        h = m.hexdigest()
        with _LOCK:
            _WEIGHT_HASH[ck] = h
    return h


def _images_of(source: Any) -> List[np.ndarray]:
    if isinstance(source, np.ndarray):
        return [source]
    if isinstance(source, (list, tuple)) and all(isinstance(a, np.ndarray) for a in source):
        return list(source)
    raise DetectorCacheError("detector cache serves numpy images / lists of them only, got %r" % type(source))


def make_key(*, weights_path: str, source: Any, conf: float, imgsz: int, device: Optional[str]) -> Dict[str, Any]:
    import torch
    import ultralytics
    imgs = _images_of(source)
    return dict(
        format=FORMAT, ultralytics=ultralytics.__version__, torch=torch.__version__,
        weights=weights_hash(weights_path), device=str(device), conf=float(conf), imgsz=int(imgsz),
        images=[dict(shape=list(a.shape), dtype=str(a.dtype),
                     pixels=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()) for a in imgs])


def key_digest(key: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()


def _path(root: Path, digest: str) -> Path:
    return root / digest[:2] / (digest + ".npz")


def _payload_sum(arrays: Dict[str, np.ndarray]) -> str:
    m = hashlib.sha256()
    for k in sorted(arrays):
        a = np.ascontiguousarray(arrays[k])
        m.update(k.encode())
        m.update(str(a.dtype).encode())
        m.update(str(a.shape).encode())
        m.update(a.tobytes())
    return m.hexdigest()


def _store(root: Path, digest: str, key: Dict[str, Any], meta: Dict[str, Any], arrays: Dict[str, np.ndarray]) -> None:
    p = _path(root, digest)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.dumps(dict(key=key, meta=meta, payload_sha256=_payload_sum(arrays)), sort_keys=True)
    tmp = p.with_name(p.name + ".tmp%d" % os.getpid())
    with open(tmp, "wb") as f:
        np.savez_compressed(f, manifest=np.frombuffer(manifest.encode(), np.uint8), **arrays)
    _STATS["bytes_written"] += tmp.stat().st_size
    os.replace(tmp, p)


def _load(root: Path, digest: str, key: Dict[str, Any]):
    p = _path(root, digest)
    if not p.exists():
        return None
    try:
        with np.load(p, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files if k != "manifest"}
            manifest = json.loads(bytes(z["manifest"]).decode())
    except Exception as e:                       # truncated zip, bad json, missing member...
        raise DetectorCacheError("corrupt detector-cache entry %s: %r" % (p, e)) from e
    if manifest.get("key") != key:
        raise DetectorCacheError("detector-cache entry %s does not match its key (a misfiled or colliding entry)" % p)
    if manifest.get("payload_sha256") != _payload_sum(arrays):
        raise DetectorCacheError("detector-cache entry %s fails its payload checksum" % p)
    _STATS["bytes_read"] += p.stat().st_size
    return manifest["meta"], arrays


# --------------------------------------------------------------------------- miss: run and record

@contextlib.contextmanager
def _capture(rec: Dict[str, Any]):
    """While active, record the head tensor `non_max_suppression` receives and the letterboxed input shape
    `construct_results` receives, passing both straight through (so a miss returns exactly what no cache would)."""
    from ultralytics.models.yolo.detect.predict import DetectionPredictor
    from ultralytics.utils import nms
    orig_nms, orig_cr = nms.non_max_suppression, DetectionPredictor.construct_results

    def nms_wrap(prediction, *a, **k):
        # `non_max_suppression` converts xywh -> xyxy IN PLACE on this tensor, so the candidates are taken
        # BEFORE it runs (a snapshot after it holds xyxy and the rebuilt NMS would convert them twice).
        p = prediction[0] if isinstance(prediction, (list, tuple)) else prediction
        c = a[0] if a else k["conf_thres"]
        rec["cand"] = _candidates(p.detach(), float(c))
        return orig_nms(prediction, *a, **k)

    def cr_wrap(self, preds, img, orig_imgs, *a, **k):
        rec["img_shape"] = tuple(int(v) for v in img.shape[2:])
        return orig_cr(self, preds, img, orig_imgs, *a, **k)

    nms.non_max_suppression, DetectionPredictor.construct_results = nms_wrap, cr_wrap
    try:
        yield
    finally:
        nms.non_max_suppression, DetectionPredictor.construct_results = orig_nms, orig_cr


def _candidates(pred, conf: float):
    """(B, 4+nc, N) -> per image the anchors NMS would start from (best class score > conf)."""
    import torch
    assert pred.ndim == 3
    nc = pred.shape[1] - 4
    arrays: Dict[str, np.ndarray] = {}
    for b in range(pred.shape[0]):
        sc = pred[b, 4:4 + nc]                              # (nc, N)
        best, cls = sc.max(0)
        idx = torch.nonzero(best > conf).flatten()
        arrays["idx%d" % b] = idx.cpu().numpy().astype(np.int32)
        arrays["box%d" % b] = pred[b, :4, idx].T.contiguous().cpu().numpy().astype(np.float32)
        arrays["cls%d" % b] = cls[idx].cpu().numpy().astype(np.int16)
        arrays["score%d" % b] = best[idx].cpu().numpy().astype(np.float32)
    return arrays, dict(batch=int(pred.shape[0]), nc=int(nc), n_anchors=int(pred.shape[2]),
                        pred_device=str(pred.device), pred_dtype=str(pred.dtype).replace("torch.", ""))


# --------------------------------------------------------------------------- hit: NMS + scale from candidates

class _Res:
    """What the three call sites read from a `Results`: `.boxes` with `.xyxy .conf .cls`, `len()`."""
    def __init__(self, boxes):
        self.boxes = boxes


def _serve(meta: Dict[str, Any], arrays: Dict[str, np.ndarray], images: Sequence[np.ndarray], conf: float,
           iou: float, agnostic: bool):
    import torch
    from ultralytics.engine.results import Boxes
    from ultralytics.utils import nms, ops
    dev = torch.device(meta["pred_device"])
    dt = getattr(torch, meta["pred_dtype"])
    B, nc, N = meta["batch"], meta["nc"], meta["n_anchors"]
    if B != len(images):
        raise DetectorCacheError("cached batch %d != call batch %d" % (B, len(images)))
    pred = torch.zeros((B, 4 + nc, N), dtype=dt, device=dev)
    for b in range(B):
        idx = torch.from_numpy(arrays["idx%d" % b].astype(np.int64)).to(dev)
        if idx.numel():
            pred[b, :4, idx] = torch.from_numpy(arrays["box%d" % b]).to(dev, dt).T
            pred[b, 4 + torch.from_numpy(arrays["cls%d" % b].astype(np.int64)).to(dev), idx] = \
                torch.from_numpy(arrays["score%d" % b]).to(dev, dt)
    out = nms.non_max_suppression(pred, conf, iou, None, agnostic, max_det=MAX_DET, nc=0, end2end=False,
                                  rotated=False, return_idxs=False)
    ishape = tuple(meta["img_shape"])
    res = []
    for p, im in zip(out, images):
        p = p.clone()
        p[:, :4] = ops.scale_boxes(ishape, p[:, :4], im.shape)
        res.append(_Res(Boxes(p[:, :6], im.shape[:2])))
    return res


# --------------------------------------------------------------------------- the one seam

def predict(model: Any, weights_path: str, *, source: Any, conf: float, iou: float = 0.7,
            agnostic_nms: bool = False, imgsz: int, device: Optional[str] = None, verbose: bool = False,
            root: Optional[Path] = None):
    """`model.predict(...)` with the cache in front of it. `root` None -> `$OMR_DETECTOR_CACHE`; neither -> the
    plain call, untouched."""
    root = Path(root) if root else cache_dir()
    kw = dict(source=source, conf=conf, iou=iou, agnostic_nms=agnostic_nms, imgsz=imgsz, device=device,
              verbose=verbose)
    if root is None:
        t0 = time.perf_counter()
        r = model.predict(**kw)
        _STATS["plain_s"] += time.perf_counter() - t0
        _STATS["calls_plain"] += 1
        return r
    t0 = time.perf_counter()
    images = _images_of(source)
    key = make_key(weights_path=weights_path, source=source, conf=conf, imgsz=imgsz, device=device)
    _USED_WEIGHTS.add(key["weights"][:12])
    digest = key_digest(key)
    hit = _load(root, digest, key)
    if hit is not None:
        _STATS["hits"] += 1
        r = _serve(hit[0], hit[1], images, conf, iou, agnostic_nms)
        _STATS["hit_s"] += time.perf_counter() - t0
        return r
    _STATS["misses"] += 1
    rec: Dict[str, Any] = {}
    with _capture(rec):
        results = model.predict(**kw)
    if "cand" not in rec or "img_shape" not in rec:
        raise DetectorCacheError("could not capture the raw detector output (ultralytics internals changed?)")
    arrays, meta = rec["cand"]
    meta["img_shape"] = list(rec["img_shape"])
    _store(root, digest, key, meta, arrays)
    _STATS["miss_s"] += time.perf_counter() - t0
    return results


def _report() -> None:
    if (_STATS["hits"] or _STATS["misses"]) and cache_dir():
        sys.stderr.write("detector-cache: %d hit, %d miss, %.1f MB written, %.1f MB read; detector seconds: %.1f on misses, "
                         "%.1f serving hits; weights %s (%s)\n" % (_STATS["hits"], _STATS["misses"], _STATS["bytes_written"] / 1e6,
                                                      _STATS["bytes_read"] / 1e6, _STATS["miss_s"], _STATS["hit_s"],
                                                      ",".join(sorted(_USED_WEIGHTS)), cache_dir()))
    elif _STATS["calls_plain"] and os.environ.get("OMR_DETECTOR_TIMING"):
        sys.stderr.write("detector (no cache): %d calls, %.1f s\n" % (_STATS["calls_plain"], _STATS["plain_s"]))


atexit.register(_report)


def summarize(logs: Sequence[str]) -> str:
    """One line for an unattended run: hits / misses summed over the runs' logs (the `detector-cache:` line each process
    prints on exit), and whether any run met a bad entry. A stale key cannot hit (the key holds the weights hash and the
    pixels); a bad entry raises and kills its run, which the log shows as `DetectorCacheError`."""
    import re
    h = m = bad = 0
    ws: set = set()
    secs = [0.0, 0.0]
    for lg in logs:
        try:
            txt = Path(lg).read_text(errors="replace")
        except OSError:
            continue
        bad += txt.count("DetectorCacheError")
        for g in re.finditer(r"detector-cache: (\d+) hit, (\d+) miss.*?([\d.]+) on misses, ([\d.]+) serving hits; weights ([0-9a-f,]*)", txt):
            h += int(g.group(1)); m += int(g.group(2)); secs[0] += float(g.group(3)); secs[1] += float(g.group(4))
            ws.update(x for x in g.group(5).split(",") if x)
    return ("detector-cache: %d hit / %d miss (%.0f s detector on misses, %.0f s serving hits); weights %s; "
            "bad or mismatched entries: %d%s" % (h, m, secs[0], secs[1], ",".join(sorted(ws)) or "-", bad,
                                                 "" if not bad else "  <-- A RUN DIED ON A BAD ENTRY"))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "summary":
        print(summarize(sys.argv[2:]))
    else:
        raise SystemExit("usage: python3 -m tools.omr.detector_cache summary LOG...")
