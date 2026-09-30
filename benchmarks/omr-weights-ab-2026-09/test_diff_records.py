"""Unit tests for `diff_records.py`, on tiny synthetic records shaped
exactly like a real `--out` file (the CLI's whole result dict, `record`
nested one level down) -- no real weights, no real gather, no machine-
local paths.

Run: `python3 -m pytest benchmarks/omr-weights-ab-2026-09/test_diff_records.py`
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_BENCH = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "diff_records", _BENCH / "diff_records.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["diff_records"] = mod
    spec.loader.exec_module(mod)
    return mod


def _obs(oid, subject, quantity, value, **detail):
    return {"id": oid, "subject": subject, "quantity": quantity,
            "value": value, "reader": "detector", "frame": "canonical",
            "score": 1.0, "detail": detail, "basis": []}


def _verdict(vid, subject, quantity, outcome, value, decider, reason,
            **extra):
    row = {"id": vid, "subject": subject, "quantity": quantity,
           "outcome": outcome, "value": value, "decider": decider,
           "reason": reason, "considered": [], "used": [], "missing": [],
           "declined": [], "excluded": [], "correlated": [], "candidates": [],
           "basis": [], "margin": None, "supersedes": None, "detail": {}}
    row.update(extra)
    return row


def _cli_result(observations, verdicts, abstentions=()):
    """Mimics what `tools.omr.staged.__main__` actually writes to `--out`
    (the bug this whole module exists to guard against: the real file
    nests `observations`/`verdicts`/`abstentions` under `"record"`, not at
    the top level)."""
    return {
        "record": {"observations": list(observations),
                   "abstentions": list(abstentions),
                   "verdicts": list(verdicts),
                   "counts": {"observations": len(observations),
                              "abstentions": len(abstentions),
                              "verdicts": len(verdicts)}},
        "summary": {},
        "adjudication": {},
        "stopped_after": "adjudicate",
    }


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return p


class DiffRecordsTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_load_unwraps_the_cli_shaped_file(self):
        """The bug this whole tool was almost shipped with: reading
        `rec["observations"]` on a real `--out` file silently sees `[]`."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            data = _cli_result(
                [_obs("obs:1", "glyph/0/0/0/0/0", "rest", "restQuarter")],
                [])
            p = _write(tmp, "rec.json", data)
            rec = self.mod.load(str(p))
            self.assertEqual(len(rec["observations"]), 1)

    def test_identical_records_diff_to_zero(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            obs = [_obs("obs:1", "glyph/0/0/0/0/0", "rest", "restQuarter")]
            vs = [_verdict("v:1", "glyph/0/0/0/0/0", "rest_is_not_a_rest",
                           "decided", False, "adjudicate_rest_is_not_a_rest",
                           "rest")]
            a = _write(tmp, "a.json", _cli_result(obs, vs))
            b = _write(tmp, "b.json", _cli_result(obs, vs))
            rec_a, rec_b = self.mod.load(str(a)), self.mod.load(str(b))
            glyphs_a = self.mod.family_glyph_subjects(rec_a, "rest")
            glyphs_b = self.mod.family_glyph_subjects(rec_b, "rest")
            gather_diff = self.mod.diff_gather(
                self.mod.gather_counts(rec_a, "rest"),
                self.mod.gather_counts(rec_b, "rest"))
            self.assertTrue(all(d["delta"] == 0 for d in gather_diff.values()))
            census_diff = self.mod.diff_census(
                self.mod.adjudicate_census(rec_a, glyphs_a),
                self.mod.adjudicate_census(rec_b, glyphs_b))
            any_delta = any(r["delta"] for d in census_diff.values()
                            for r in d["verdicts"] + d["abstentions"])
            self.assertFalse(any_delta)

    def test_a_real_difference_is_not_hidden(self):
        """B reads one MORE rest8th than A, and refuses it as a duplicate
        box where A does not -- both must show up as a nonzero delta."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            obs_a = [_obs("obs:1", "glyph/0/0/0/0/0", "rest", "rest8th")]
            obs_b = [_obs("obs:1", "glyph/0/0/0/0/0", "rest", "rest8th"),
                     _obs("obs:2", "glyph/0/0/0/0/1", "rest", "rest8th")]
            vs_a = [_verdict("v:1", "glyph/0/0/0/0/0", "rest_is_not_a_rest",
                            "decided", False, "d", "rest")]
            vs_b = vs_a + [_verdict("v:2", "glyph/0/0/0/0/1",
                                    "rest_is_not_a_rest", "decided", True,
                                    "d", "rest_is_a_duplicate_box")]
            a = _write(tmp, "a.json", _cli_result(obs_a, vs_a))
            b = _write(tmp, "b.json", _cli_result(obs_b, vs_b))
            rec_a, rec_b = self.mod.load(str(a)), self.mod.load(str(b))
            gather_diff = self.mod.diff_gather(
                self.mod.gather_counts(rec_a, "rest"),
                self.mod.gather_counts(rec_b, "rest"))
            self.assertEqual(gather_diff["rest8th"]["delta"], 1)

    def test_surviving_rests_excludes_a_decided_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            obs = [_obs("obs:1", "glyph/1/0/0/1/0", "rest", "rest8th"),
                   _obs("obs:2", "glyph/1/0/0/1/1", "rest", "rest8th")]
            vs = [_verdict("v:1", "glyph/1/0/0/1/1", "rest_is_not_a_rest",
                          "decided", True, "d", "rest_is_a_duplicate_box")]
            rec_inner = _cli_result(obs, vs)["record"]
            glyphs = {o["subject"]: o for o in obs}
            survivors = self.mod.surviving_rests(rec_inner, glyphs)
            self.assertEqual(list(survivors), ["glyph/1/0/0/1/0"])

    def test_cross_reference_reads_sean_verdicts_by_cell_address(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cells_json = _write(tmp, "cells.json", [{
                "cell_id": "fake-p1-sys0-s0-m1",
                "pdf": "/somewhere/fake.pdf",
                "page": 1, "system_index": 0, "staff_index": 0,
                "measure_index": 1,
            }])
            verdicts_dir = tmp / "verdicts"
            verdicts_dir.mkdir()
            (verdicts_dir / "fake-p1-sys0-s0-m1.verdict.json").write_text(
                json.dumps({
                    "cell_id": "fake-p1-sys0-s0-m1",
                    "detections": [
                        {"verdict": "TP", "model_predicted_class": "rest8th",
                         "human_corrected_class": None},
                        {"verdict": "FP", "model_predicted_class": "rest8th",
                         "human_corrected_class": None},
                    ],
                    "added_detections": [],
                }))
            vindex = self.mod.load_verdicts_index(verdicts_dir, cells_json)
            addr = ("fake.pdf", 1, 0, 0, 1)
            self.assertEqual(vindex[addr]["TP"]["rest8th"], 1)
            self.assertEqual(vindex[addr]["FP"]["rest8th"], 1)

            obs = [_obs("obs:1", "glyph/1/0/0/1/0", "rest", "rest8th")]
            rec = _cli_result(obs, [])["record"]
            glyphs = {o["subject"]: o for o in obs}
            xr = self.mod.cross_reference(rec, glyphs, "fake.pdf", vindex)
            self.assertEqual(xr["totals"]["record_surviving"], 1)
            self.assertEqual(xr["totals"]["sean_tp"], 1)
            self.assertEqual(xr["totals"]["best_case_matched"], 1)


if __name__ == "__main__":
    unittest.main()
