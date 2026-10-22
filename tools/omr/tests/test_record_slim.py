"""`record_slim`: rewrite a pre-roadmap-1.1 record's `Q.INK` rows into the
per-cell summary `gather_ink` now emits by default.

⚠️ Requires `ijson` (a soft dependency of `record_slim` alone, not of the
staged package) -- the whole module is skipped where it is absent rather
than failing the suite, matching how this repo treats other optional
readers (Surya, Tesseract).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

try:
    import ijson  # noqa: F401
    HAVE_IJSON = True
except ImportError:
    HAVE_IJSON = False

if HAVE_IJSON:
    from tools.omr.staged import record_slim as RS


def _two_component_record():
    return {
        "record": {
            "observations": [
                {"id": "obs:1", "subject": "glyph/0/0/0/0/200000",
                 "quantity": "ink", "value": "ink", "reader": "cv_ink",
                 "frame": "cell:0", "score": None,
                 "detail": {"ink_bbox_canonical": [0, 0, 10, 10],
                            "ink_area_px": 40, "ink_fill": 0.4,
                            "ink_n_components": 2, "ink_share_of_cell": 0.4,
                            "ink_detector_coverage": 0.1,
                            "ink_explained_by": ["notehead"],
                            "cell_staff_space_px": 100.0},
                 "basis": []},
                {"id": "obs:2", "subject": "glyph/0/0/0/0/200001",
                 "quantity": "ink", "value": "ink", "reader": "cv_ink",
                 "frame": "cell:0", "score": None,
                 "detail": {"ink_bbox_canonical": [20, 20, 30, 30],
                            "ink_area_px": 60, "ink_fill": 0.6,
                            "ink_n_components": 2, "ink_share_of_cell": 0.6,
                            "ink_detector_coverage": 0.3,
                            "ink_explained_by": ["barline"],
                            "cell_staff_space_px": 100.0},
                 "basis": []},
                {"id": "obs:3", "subject": "glyph/0/0/0/0/5",
                 "quantity": "glyph_box",
                 "value": ["noteheadBlackInSpace", 0, 0, 10, 10],
                 "reader": "detector", "frame": "cell:0", "score": 0.9,
                 "detail": {}, "basis": []},
            ],
            "abstentions": [
                {"id": "abs:1", "subject": "cell/0/0/1/0", "quantity": "ink",
                 "reader": "cv_ink", "frame": "cell:0", "reason": "no_ink",
                 "detail": {}},
            ],
            "verdicts": [
                {"id": "vrd:1", "subject": "glyph/0/0/0/0/5",
                 "quantity": "duration", "outcome": "decided", "value": 1.0,
                 "decider": "adjudicate_duration", "reason": "ok",
                 "basis": ["obs:3"], "considered": ["obs:3"],
                 "candidates": [], "correlated": None, "declined": [],
                 "excluded": [], "margin": None, "missing": [],
                 "supersedes": None, "used": ["obs:3"], "detail": {}},
            ],
            # ⚠️ NOT EVERY SIBLING OF `observations` IS AN ARRAY -- the real
            # shared records carry `record.counts` as a MAP, which broke the
            # first version of this converter (it assumed `_copy_array`
            # unconditionally for anything that was not `observations`).
            "counts": {"ink": 2, "glyph_box": 1, "duration": 1},
        },
        "summary": {"n": 3},
        "adjudication": {"decided": 1, "abstained": 1},
        "agreement": {"nested": [1, 2, {"three": 3}]},
        "evaluation": {"fired": 0},
        "stubs": {"decisions": [], "consequences": []},
        "provenance": {"commit": "deadbeef", "dirty": False},
    }


@unittest.skipUnless(HAVE_IJSON, "record_slim needs ijson")
class TestRecordSlim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.inp = os.path.join(self.tmp, "in.json")
        self.outp = os.path.join(self.tmp, "out.json")

    def _convert(self, doc):
        with open(self.inp, "w") as f:
            json.dump(doc, f, indent=2)
        stats = RS.convert(self.inp, self.outp)
        with open(self.outp) as f:
            return json.load(f), stats

    def test_ink_rows_collapse_to_one_summary_per_cell(self):
        doc = _two_component_record()
        out, stats = self._convert(doc)
        ink_rows = [o for o in out["record"]["observations"]
                   if o["quantity"] == "ink"]
        self.assertEqual(len(ink_rows), 1)
        self.assertEqual(stats["ink_observations_in"], 2)
        self.assertEqual(stats["ink_cells_out"], 1)
        d = ink_rows[0]["detail"]
        self.assertEqual(d["ink_n_components"], 2)
        self.assertEqual(d["ink_total_area_px"], 100)
        self.assertAlmostEqual(d["ink_largest_share"], 0.6)
        self.assertAlmostEqual(d["ink_detector_coverage_max"], 0.3)
        self.assertEqual(set(d["ink_explained_by_union"]),
                         {"notehead", "barline"})
        self.assertEqual(d["cell_staff_space_px"], 100.0)

    def test_non_ink_rows_pass_through_unchanged(self):
        doc = _two_component_record()
        out, _ = self._convert(doc)
        non_ink = [o for o in out["record"]["observations"]
                  if o["quantity"] != "ink"]
        self.assertEqual(non_ink, [doc["record"]["observations"][2]])
        self.assertEqual(out["record"]["abstentions"],
                         doc["record"]["abstentions"])
        self.assertEqual(out["record"]["verdicts"],
                         doc["record"]["verdicts"])

    def test_a_map_sibling_of_observations_survives(self):
        """The regression the real Beethoven/Brahms records exposed:
        `record.counts` is a dict, not a list."""
        doc = _two_component_record()
        out, _ = self._convert(doc)
        self.assertEqual(out["record"]["counts"], doc["record"]["counts"])

    def test_sibling_top_level_keys_survive_including_nested_structure(self):
        doc = _two_component_record()
        out, _ = self._convert(doc)
        for key in ("summary", "adjudication", "agreement", "evaluation",
                   "stubs", "provenance"):
            self.assertEqual(out[key], doc[key], key)

    def test_numbers_round_trip_as_numbers_not_strings(self):
        """⚠️ THE BUG THIS PINS: ijson parses JSON numbers as `Decimal` by
        default, which `json.dumps` cannot serialise and silently stringifies
        under a `default=str` fallback -- caught the first time this module
        was run on a real fixture, where `0.9` came back as `"0.9"`."""
        doc = _two_component_record()
        out, _ = self._convert(doc)
        glyph_box = [o for o in out["record"]["observations"]
                    if o["quantity"] == "glyph_box"][0]
        self.assertIsInstance(glyph_box["score"], float)
        self.assertIsInstance(out["record"]["verdicts"][0]["value"], float)
        ink = [o for o in out["record"]["observations"]
              if o["quantity"] == "ink"][0]
        self.assertIsInstance(ink["detail"]["cell_staff_space_px"], float)

    def test_no_ink_at_all_is_a_no_op_on_the_other_two_arrays(self):
        doc = _two_component_record()
        doc["record"]["observations"] = [doc["record"]["observations"][2]]
        out, stats = self._convert(doc)
        self.assertEqual(stats["ink_observations_in"], 0)
        self.assertEqual(stats["ink_cells_out"], 0)
        self.assertEqual(out["record"]["observations"],
                         doc["record"]["observations"])

    def test_two_cells_of_ink_produce_two_summary_rows(self):
        doc = _two_component_record()
        doc["record"]["observations"][1]["subject"] = "glyph/0/0/1/0/200000"
        out, stats = self._convert(doc)
        ink_rows = [o for o in out["record"]["observations"]
                   if o["quantity"] == "ink"]
        self.assertEqual(len(ink_rows), 2)
        self.assertEqual(stats["ink_cells_out"], 2)
        # ⚠️ The summary subject already has NO ordinal (it names a cell, not
        # a component), so it is compared directly rather than re-truncated.
        subjects = {o["subject"] for o in ink_rows}
        self.assertEqual(subjects, {"glyph/0/0/0/0", "glyph/0/0/1/0"})
        for row in ink_rows:
            self.assertEqual(row["detail"]["ink_n_components"], 1)

    def test_a_component_with_no_cell_prefix_is_reported_not_dropped_silently(self):
        doc = _two_component_record()
        doc["record"]["observations"][0]["subject"] = "document"
        out, stats = self._convert(doc)
        self.assertEqual(stats.get("unattributable"), 1)
        ink_rows = [o for o in out["record"]["observations"]
                   if o["quantity"] == "ink"]
        self.assertEqual(len(ink_rows), 1)  # only the second component's cell


if __name__ == "__main__":
    unittest.main()
