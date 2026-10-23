"""ROADMAP 2.191 -- the speed-ups must not change a value. Each fast routine is held against the slow routine it replaced
(copied here as the reference), on random input; a reference that disagreed would fail these."""
import numpy as np

from tools.omr.staged import gather as G
from tools.omr.annotate import head_template as HT


def _old_runs(col):
    d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
    return list(zip(np.where(d == 1)[0].tolist(), np.where(d == -1)[0].tolist()))


def _old_median(a, k):
    k |= 1
    h = k // 2
    pad = np.pad(a, h, mode="edge")
    return np.array([np.median(pad[i:i + k]) for i in range(len(a))])


def _old_best(slab, off, lo_v, hi_v):
    out = []
    for cx in range(slab.shape[1]):
        best, bov = None, 0.0
        for s, e in _old_runs(slab[:, cx]):
            ov = min(e + off, hi_v) - max(s + off, lo_v)
            if ov > bov:
                best, bov = (s, e), ov
        if best is not None:
            out.append((cx,) + best)
    return out


def test_best_overlap_runs_picks_the_run_the_loop_picked():
    rng = np.random.default_rng(191)
    for _ in range(1500):
        R, C = int(rng.integers(0, 40)), int(rng.integers(0, 30))
        slab = rng.random((R, C)) < rng.choice([0.2, 0.5, 0.8])
        off = int(rng.integers(0, 50))
        lo = float(rng.integers(0, 60)) + float(rng.choice([0, 0.5, 0.2]))
        hi = lo + float(rng.integers(0, 15)) + float(rng.choice([0, 0.5]))
        c, s, e = G._best_overlap_runs(slab, off, lo, hi)
        assert list(zip(c.tolist(), s.tolist(), e.tolist())) == _old_best(slab, off, lo, hi)


def test_ink_runs_and_median_filter_are_the_old_values():
    rng = np.random.default_rng(7)
    for _ in range(300):
        col = rng.random(int(rng.integers(0, 50))) < 0.5
        assert G._ink_runs(col) == _old_runs(col)
    for _ in range(300):
        n, k = int(rng.integers(1, 60)), int(rng.integers(1, 15))
        for a in (rng.random(n) * 10, rng.integers(0, 20, n).astype(float), rng.integers(0, 20, n)):
            x, y = _old_median(a, k), G._median_filter_1d(a, k)
            assert x.dtype == y.dtype and (x == y).all()


def test_the_control_can_fail():
    """A reference that is off by one run would be caught: perturb the loop's threshold and the comparison breaks."""
    rng = np.random.default_rng(3)
    slab = rng.random((30, 20)) < 0.5
    c, s, e = G._best_overlap_runs(slab, 0, 5.0, 15.0)
    mine = list(zip(c.tolist(), s.tolist(), e.tolist()))
    assert mine != _old_best(slab, 0, 5.0, 14.0)


def test_masked_ncc_memo_is_the_same_number():
    rng = np.random.default_rng(5)
    mask = rng.random((12, 9)) < 0.6
    memo = {}
    for _ in range(50):
        t = rng.random((12, 9)).astype(np.float32)
        c = (rng.random((12, 9)) < 0.5).astype(np.float32)
        a = HT._masked_ncc(t, c, mask)
        assert HT._masked_ncc(t, c, mask, memo) == a
        assert HT._masked_ncc(t, c, mask, memo) == a        # a second ask is served from the memo
    assert HT._masked_ncc(t, c, np.zeros_like(mask), memo) is None
