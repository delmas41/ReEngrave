"""Tests for `tools.omr.acceptance` — the acceptance harness, ROADMAP.md
Phase 1 item 1.3 / CLAUDE.md Sec.6a.

Kept fast and synthetic on purpose: none of these tests needs OMR weights,
a real staged record, or the score library. They exercise the manifest
schema, the receipt mechanism, the machine-proxy arithmetic on a tiny
hand-built MusicXML string + report dict, the `skipped`/`absent`/`error`
distinction from a real numeric value, and the dirty-tree write refusal —
mirroring `test_staged_check.py`'s pattern for that last one.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.omr import acceptance as A

_SYNTHETIC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Staff p1-s0-0</part-name></score-part>
    <score-part id="P2"><part-name>Violin</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>2</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <note><rest/><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>2</beats><beat-type>4</beat-type></time>
        <transpose><diatonic>0</diatonic><chromatic>0</chromatic><octave-change>-1</octave-change></transpose>
      </attributes>
      <note><rest/><duration>2</duration><type>half</type></note>
    </measure>
  </part>
</score-partwise>
"""

_SYNTHETIC_REPORT = {
    "written": {
        "notes": 5,
        "empty_bars_padded": 1,
        "empty_bars_padded_without_meter": 0,
        "tacet_bars_not_padded_without_meter": 0,
    },
    "balance": {
        "noteheads_in_log": 10,
        "notes_doubled_to_condensed_slot": 0,
        "balanced": True,
    },
    "notes_not_written": {
        "duration_narrowed": 2,
        "no_pitch": 1,
        "staff_not_identified": 3,
        "owned_by_another_staff": 0,
        "ink_is_a_whole_rest": 0,
    },
}


# ── manifest validation ─────────────────────────────────────────────────

class TestManifestValidation(unittest.TestCase):
    def test_the_real_manifest_loads_with_three_documents(self):
        manifest = A.load_manifest(A.MANIFEST_PATH)
        ids = [d["id"] for d in manifest["documents"]]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3, "document ids must be unique")
        kinds = {d["kind"] for d in manifest["documents"]}
        self.assertEqual(kinds, {"scan", "engraved"})

    def test_the_real_manifest_names_the_three_acceptance_documents(self):
        """docs/DECISIONS.md 2026-09-22: Litolff scan, Breitkopf scan,
        one engraved render — never a fourth or a substitute."""
        manifest = A.load_manifest(A.MANIFEST_PATH)
        publishers = sorted((d.get("publisher") or "") for d in manifest["documents"])
        self.assertEqual(publishers, ["", "Breitkopf", "Litolff"])

    def _write(self, tmp, payload):
        p = Path(tmp) / "manifest.json"
        p.write_text(json.dumps(payload))
        return p

    def test_missing_required_key_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, {"documents": [{"id": "x", "kind": "scan"}]})
            with self.assertRaises(A.AcceptanceError):
                A.load_manifest(path)

    def test_duplicate_ids_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = {"id": "x", "kind": "scan", "record": {"root": "repo", "path": "a"},
                  "count_page": {"pdf_page_index": 0}}
            path = self._write(tmp, {"documents": [doc, dict(doc)]})
            with self.assertRaises(A.AcceptanceError):
                A.load_manifest(path)

    def test_bad_kind_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = {"id": "x", "kind": "audio", "record": {"root": "repo", "path": "a"},
                  "count_page": {"pdf_page_index": 0}}
            path = self._write(tmp, {"documents": [doc]})
            with self.assertRaises(A.AcceptanceError):
                A.load_manifest(path)

    def test_select_documents_refuses_an_unknown_id(self):
        manifest = {"documents": [
            {"id": "a", "kind": "scan", "record": {}, "count_page": {}},
        ]}
        with self.assertRaises(A.AcceptanceError):
            A.select_documents(manifest, ["nope"])

    def test_select_documents_with_no_filter_returns_all(self):
        manifest = {"documents": [
            {"id": "a", "kind": "scan", "record": {}, "count_page": {}},
            {"id": "b", "kind": "scan", "record": {}, "count_page": {}},
        ]}
        self.assertEqual([d["id"] for d in A.select_documents(manifest, None)],
                         ["a", "b"])


# ── receipts ─────────────────────────────────────────────────────────────

class TestReceipts(unittest.TestCase):
    """`resolve_path` accepts an already-ABSOLUTE `path` regardless of
    `root`, which is what lets these tests point a document at a temp
    file without touching the real library or git tree."""

    def _doc(self, record_path, md5=None):
        return {"id": "x", "kind": "scan",
               "record": {"root": "repo", "path": str(record_path), "md5": md5},
               "count_page": {"pdf_page_index": 0}}

    def test_first_run_records_a_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "r.json"
            record.write_text('{"hello": "world"}')
            manifest = {"documents": [self._doc(record)]}
            docs = manifest["documents"]
            ok, messages, changed = A.verify_receipts(manifest, docs)
            self.assertTrue(ok)
            self.assertTrue(changed)
            self.assertIsNotNone(docs[0]["record"]["md5"])
            self.assertEqual(docs[0]["record"]["md5"], A._md5(record))
            self.assertTrue(any("recorded" in m for m in messages))

    def test_a_verified_receipt_does_not_mutate_the_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "r.json"
            record.write_text('{"hello": "world"}')
            real_md5 = A._md5(record)
            manifest = {"documents": [self._doc(record, md5=real_md5)]}
            docs = manifest["documents"]
            ok, messages, changed = A.verify_receipts(manifest, docs)
            self.assertTrue(ok)
            self.assertFalse(changed)
            self.assertTrue(any("verified" in m for m in messages))

    def test_a_mismatched_receipt_refuses_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "r.json"
            record.write_text('{"hello": "world"}')
            manifest = {"documents": [self._doc(record, md5="deadbeef" * 4)]}
            docs = manifest["documents"]
            ok, messages, changed = A.verify_receipts(manifest, docs)
            self.assertFalse(ok)
            self.assertFalse(changed)
            self.assertTrue(any("MISMATCH" in m for m in messages))

    def test_run_refuses_the_whole_batch_on_one_mismatch(self):
        """The refusal happens BEFORE any document is processed — a receipt
        check is cheap and must gate every expensive step (Sec.6a)."""
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "r.json"
            record.write_text('{"hello": "world"}')
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(
                {"documents": [self._doc(record, md5="not-the-real-one")]}))
            with mock.patch.object(A, "process_document") as fake_process:
                with self.assertRaises(A.AcceptanceError):
                    A.run(manifest_path, None, 60.0)
                fake_process.assert_not_called()

    def test_an_absent_record_is_reported_not_crashed_on(self):
        doc = self._doc(Path("/no/such/file/anywhere.json"))
        doc["record"]["md5"] = None
        block = A.process_document(doc, step_timeout_s=5.0)
        self.assertEqual(block["status"], A._ABSENT)
        self.assertIn("reason", block)


# ── machine proxies ──────────────────────────────────────────────────────

class TestMachineProxies(unittest.TestCase):
    def test_parts_named(self):
        out = A.parts_named(_SYNTHETIC_XML)
        # P1's name matches the coordinate default and is not "named";
        # P2 ("Violin") is.
        self.assertEqual(out["n"], 1)
        self.assertEqual(out["of"], 2)
        self.assertAlmostEqual(out["fraction"], 0.5)

    def test_transpose_parts(self):
        out = A.transpose_parts(_SYNTHETIC_XML)
        self.assertEqual(out["n"], 1)
        self.assertEqual(out["of"], 2)

    def test_bars_add_up_hand_computed(self):
        # P1 m1: two quarters in a 2/4 bar -> EXACT.
        # P1 m2: one quarter rest, meter carried forward -> SHORT.
        # P2 m1: one half-note rest in a 2/4 bar -> EXACT.
        out = A.bars_add_up(_SYNTHETIC_XML)
        self.assertEqual(out["exact"], 2)
        self.assertEqual(out["short"], 1)
        self.assertEqual(out["overfull"], 0)
        self.assertEqual(out["empty"], 0)
        self.assertEqual(out["unassessable"], 0)
        self.assertEqual(out["of"], 3)
        self.assertEqual(out["n"], 2)
        self.assertAlmostEqual(out["fraction"], 2 / 3)

    def test_bars_add_up_reports_unassessable_apart_from_short(self):
        xml = _SYNTHETIC_XML.replace(
            "<time><beats>2</beats><beat-type>4</beat-type></time>", "")
        out = A.bars_add_up(xml)
        # every bar now has divisions but no meter at all -> unassessable,
        # never counted as SHORT/OVERFULL (the brief's own distinction).
        self.assertEqual(out["exact"] + out["short"] + out["overfull"], 0)
        self.assertGreater(out["unassessable"], 0)

    def test_machine_proxies_end_to_end_on_the_synthetic_pair(self):
        out = A.machine_proxies(_SYNTHETIC_XML, _SYNTHETIC_REPORT)
        self.assertEqual(out["notes_reaching_file"],
                         {"n": 5, "of": 10, "fraction": 0.5})
        self.assertEqual(out["held_out"]["staff_not_identified"], 3)
        self.assertEqual(out["held_out"]["of_noteheads_in_log"], 10)
        self.assertAlmostEqual(out["held_out"]["fraction"], 0.3)
        self.assertEqual(out["unread_bars"]["empty_bars_padded"], 1)
        self.assertEqual(out["notes_doubled_to_condensed_slot"], 0)
        self.assertEqual(out["named_drop_reasons"],
                         {"duration_narrowed": 2, "no_pitch": 1,
                          "staff_not_identified": 3,
                          "owned_by_another_staff": 0,
                          "ink_is_a_whole_rest": 0})
        self.assertTrue(out["balanced"])
        self.assertEqual(out["parts_named"]["n"], 1)

    def test_a_zero_denominator_reports_none_not_a_zero_fraction(self):
        """A fraction with nothing to divide by must not read as 0.0 —
        that would be indistinguishable from "0% reached" rather than
        "there was nothing to measure"."""
        self.assertIsNone(A._fraction(0, 0))
        report = json.loads(json.dumps(_SYNTHETIC_REPORT))
        report["balance"]["noteheads_in_log"] = 0
        out = A.machine_proxies(_SYNTHETIC_XML, report)
        self.assertIsNone(out["notes_reaching_file"]["fraction"])
        self.assertIsNone(out["held_out"]["fraction"])


# ── skipped / absent / error are never a numeric 0 ───────────────────────

class TestStepOutcomesAreDistinctFromAValue(unittest.TestCase):
    def test_a_successful_step_carries_a_value_key(self):
        out = A._run_step("x", 60.0, lambda: 0)
        self.assertTrue(out["ok"])
        self.assertIn("value", out)
        self.assertEqual(out["value"], 0)

    def test_a_raised_exception_is_an_error_never_a_value(self):
        def boom():
            raise ValueError("nope")
        out = A._run_step("x", 60.0, boom)
        self.assertFalse(out["ok"])
        self.assertNotIn("value", out)
        self.assertIn("error", out)
        self.assertNotIn("skipped", out)

    def test_a_timeout_is_skipped_never_a_value_and_never_an_error_key(self):
        def slow():
            raise A.TimeBudgetExceeded("x exceeded 1s")
        out = A._run_step("x", 60.0, slow)
        self.assertFalse(out["ok"])
        self.assertNotIn("value", out)
        self.assertIn("skipped", out)
        self.assertNotIn("error", out)

    def test_time_budget_of_zero_disables_enforcement(self):
        # budget <= 0 means "no cap" (used for --step-timeout 0 / tests
        # that must not depend on wall-clock signal timing).
        with A._time_budget(0, "x"):
            pass  # must not raise regardless of how long this takes

    def test_a_real_alarm_fires_as_time_budget_exceeded(self):
        import time as _time
        with self.assertRaises(A.TimeBudgetExceeded):
            with A._time_budget(1, "slow-thing"):
                _time.sleep(3)


# ── the writer refuses a dirty tree ──────────────────────────────────────

class TestWriteCurrentRefusesADirtyTree(unittest.TestCase):
    @staticmethod
    def _current(dirty):
        return {"tree": "deadbeef00", "dirty": dirty, "date": "2026-09-22T00:00:00Z",
               "manifest_md5": "x", "wall_time_s": 0.1, "documents": {},
               "summary": {}}

    def test_refuses_and_writes_nothing_when_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "current.json"
            with self.assertRaises(A.AcceptanceError) as ctx:
                A.write_current(self._current(True), force=False, out_path=out_path)
            self.assertIn("DIRTY", str(ctx.exception))
            self.assertFalse(out_path.exists())

    def test_force_writes_on_a_dirty_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "current.json"
            path = A.write_current(self._current(True), force=True, out_path=out_path)
            payload = json.loads(path.read_text())
            self.assertTrue(payload["dirty"])

    def test_writes_without_force_on_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "current.json"
            path = A.write_current(self._current(False), force=False, out_path=out_path)
            payload = json.loads(path.read_text())
            self.assertFalse(payload["dirty"])
            self.assertEqual(path, out_path)


# ── the table and the summary never silently drop a document ────────────

class TestSummaryAndTable(unittest.TestCase):
    def test_summary_reports_a_non_ok_document_by_its_status_not_a_number(self):
        documents = {"missing-doc": {"status": A._ABSENT, "kind": "scan",
                                    "reason": "no record"}}
        summary = A.build_summary(documents)
        self.assertEqual(summary["missing-doc"]["status"], A._ABSENT)
        self.assertNotIn("notes_reaching_file", summary["missing-doc"])

    def test_render_table_mentions_every_document(self):
        documents = {
            "ok-doc": {"status": "ok", "kind": "scan",
                      "machine_proxies": {
                          "notes_reaching_file": {"n": 1, "of": 2, "fraction": 0.5},
                          "bars_add_up_to_the_meter_in_force":
                              {"n": 1, "of": 2, "unassessable": 0},
                          "parts_named": {"n": 1, "of": 1},
                          "held_out": {"staff_not_identified": 0},
                          "unread_bars": {"empty_bars_padded": 0},
                      },
                      "side_by_side": {"print": {"built": True}, "ours": {"built": False}}},
            "gone-doc": {"status": A._ABSENT, "kind": "scan", "reason": "no record"},
        }
        current = {"tree": "abc", "dirty": False, "date": "now", "wall_time_s": 1.0,
                  "documents": documents}
        text = A.render_table(current)
        self.assertIn("ok-doc", text)
        self.assertIn("gone-doc", text)
        self.assertIn("no record", text)


if __name__ == "__main__":
    unittest.main()
