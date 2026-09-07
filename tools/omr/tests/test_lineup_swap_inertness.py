"""Flag-off is identical by CONSTRUCTION, on the shapes that could hide a drift.

`test_lineup_swap.py` asserts it on a clean fixture. The two shapes that could
differ without that noticing are the ones `lineup_spans` handles specially:
pages with NO STAVES (front matter), which `_readmit_empty` places, and a
`page_systems` sequence that is not in page order, which the refusal path
returns verbatim while `_readmit_empty` sorts.
"""
from __future__ import annotations

import random

from tools.omr import movement_reference as mr

LINEUP = ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
          "Violin", "Violin", "Viola", "Cello"]


def _doc(n_pages, *, empties=(), shuffle=False, seed=0):
    ps, pl = [], []
    for p in range(n_pages):
        systems = [] if p in empties else [len(LINEUP)]
        labels = [] if p in empties else [list(LINEUP)]
        ps.append((p, systems))
        pl.append((p, labels))
    if shuffle:
        rng = random.Random(seed)
        order = list(range(n_pages))
        rng.shuffle(order)
        ps = [ps[i] for i in order]
        pl = [pl[i] for i in order]
    return ps, pl


def _both(ps, pl):
    return mr.lineup_spans(ps), mr.lineup_spans(ps, pl)


def test_off_is_identical_with_front_matter(monkeypatch):
    monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "0")
    ps, pl = _doc(20, empties=(0, 1, 19))
    a, b = _both(ps, pl)
    assert a == b


def test_off_is_identical_when_the_pages_arrive_out_of_order(monkeypatch):
    monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "0")
    for seed in range(5):
        ps, pl = _doc(20, empties=(3,), shuffle=True, seed=seed)
        a, b = _both(ps, pl)
        assert a == b, seed


def test_off_is_identical_on_a_run_too_short_to_prove_anything(monkeypatch):
    monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "0")
    for n in range(1, 6):
        ps, pl = _doc(n)
        a, b = _both(ps, pl)
        assert a == b, n


def test_on_but_evidence_free_is_identical_too(monkeypatch):
    """The flag alone must not move anything: the split needs BOTH."""
    monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "1")
    for seed in range(5):
        ps, _pl = _doc(20, empties=(0, 7), shuffle=True, seed=seed)
        monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "0")
        off = mr.lineup_spans(ps)
        monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "1")
        assert mr.lineup_spans(ps) == off, seed
        assert mr.lineup_spans(ps, None) == off, seed
