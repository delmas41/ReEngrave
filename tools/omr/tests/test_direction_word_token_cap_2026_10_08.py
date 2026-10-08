"""The direction-word Surya call has an output ceiling (2026-10-08).

A crop that makes Surya's decoder loop generated up to 12,288 tokens (Litolff
p2: two `cresc.` crops, 101 s and 291 s, both returning nothing). Only the
direction-word reader passes a cap; margin labels must not.
"""
from __future__ import annotations

import importlib
import sys
import types

import numpy as np

from tools.omr import direction_text as DT
from tools.omr import staff_labels_surya as SU

CROP = np.full((20, 60, 3), 255, np.uint8)


def _record(monkeypatch, reply=None):
    jobs = []

    def fake(job, *, timeout_s=None, keep_alive=None, **kw):
        jobs.append((job, timeout_s, kw))
        n = len(job.get("crops", []))
        if reply is not None:
            return reply(job)
        return {"crops": [{"text": "cresc."}] * n}
    monkeypatch.setattr(SU, "_dispatch", fake)
    return jobs


def test_cap_is_sent_when_asked(monkeypatch):
    jobs = _record(monkeypatch)
    SU.read_crops_text([CROP], max_tokens=64)
    assert jobs[0][0]["max_tokens"] == 64


def test_default_call_has_no_cap(monkeypatch):
    """Positive control: the uncapped path is exactly as before."""
    jobs = _record(monkeypatch)
    SU.read_crops_text([CROP])
    assert "max_tokens" not in jobs[0][0]


def test_the_direction_reader_passes_its_cap_and_guard(monkeypatch):
    jobs = _record(monkeypatch)
    out = DT._surya_word_reader([CROP, CROP])
    assert out == ["cresc.", "cresc."]
    assert DT.DIRECTION_WORD_MAX_TOKENS <= 128
    assert len(jobs) == 2                                  # one job per crop
    for job, timeout, kw in jobs:
        assert job["max_tokens"] == DT.DIRECTION_WORD_MAX_TOKENS
        assert timeout == DT.DIRECTION_CROP_TIMEOUT_S
        assert kw.get("one_shot_fallback") is False


def test_the_registered_surya_rung_is_the_capped_reader(monkeypatch):
    monkeypatch.setattr(SU, "available", lambda: True)
    monkeypatch.delenv("OMR_DIRECTION_READERS", raising=False)
    named = dict(DT.default_readers())
    assert named["surya"] is DT._surya_word_reader


def test_margin_labels_are_not_capped(monkeypatch):
    jobs = []

    def fake(job, **kw):
        jobs.append(job)
        return {"systems": []}
    monkeypatch.setattr(SU, "_dispatch", fake)
    crop = types.SimpleNamespace(png=b"x", staff_indices=[0], tick_ys=[1.0],
                                 gutter_px=0)
    SU.read_crops_surya([crop])
    assert "max_tokens" not in jobs[0]


def test_a_slow_crop_reads_as_empty_and_the_rest_go_on(monkeypatch):
    calls = {"n": 0}

    def reply(job):
        calls["n"] += 1
        if calls["n"] == 2:
            raise SU.SuryaLabelError("silent")
        return {"crops": [{"text": "dim."}]}
    _record(monkeypatch, reply)
    assert SU.read_crops_text([CROP, CROP, CROP], max_tokens=64,
                              crop_timeout_s=5) == ["dim.", "", "dim."]


def test_worker_lowers_the_ceiling_for_the_job_only(monkeypatch):
    settings = types.SimpleNamespace(SURYA_MAX_TOKENS_FULL_PAGE=12288,
                                     SURYA_MAX_TOKENS_BLOCK_CEILING=8192)
    mod = types.ModuleType("surya.settings")
    mod.settings = settings
    monkeypatch.setitem(sys.modules, "surya", types.ModuleType("surya"))
    monkeypatch.setitem(sys.modules, "surya.settings", mod)
    W = importlib.import_module("tools.omr._surya_worker")
    seen = []

    def fake_read(predictor, Image, crops):
        seen.append((settings.SURYA_MAX_TOKENS_FULL_PAGE,
                     settings.SURYA_MAX_TOKENS_BLOCK_CEILING))
        return [{"text": ""}]
    monkeypatch.setattr(W, "_read_crops", fake_read)
    W._handle({"crops": ["x"], "max_tokens": 64}, None, None)
    W._handle({"crops": ["x"]}, None, None)
    assert seen == [(64, 64), (12288, 8192)]
    assert (settings.SURYA_MAX_TOKENS_FULL_PAGE,
            settings.SURYA_MAX_TOKENS_BLOCK_CEILING) == (12288, 8192)
