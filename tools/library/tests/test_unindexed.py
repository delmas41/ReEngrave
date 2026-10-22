"""`unindexed()` — the mirror of `verify`, and the direction 54 editions went.

⚠️ EVERY TEST HERE IS A STATE THE GUARD MUST DISTINGUISH, because the fault it
exists to catch produced NO symptom at all: the store and the catalog
disagreed, nothing failed, and it survived 54 files
(`benchmarks/omr-catalog-gap-2026-09/FINDINGS.md`).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.library import score_library as lib


class _Store:
    """A throwaway store: files, sidecars and a catalog under one temp root."""

    def __init__(self, stack):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))

    def add(self, rel: str, *, sidecar: bool = True) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-1.4 not really")
        if sidecar:
            lib.sidecar_path(p).write_text(json.dumps(
                {"kind": "edition", "source": "imslp", "work_id": "w"}))
        return p

    def catalog(self, *rels: str) -> dict:
        return {"entries": [{"path": r} for r in rels]}


class TestItFiresWhenTheCatalogIsBehind(unittest.TestCase):
    """THE POSITIVE CONTROL. A guard that has never been seen to fire is
    indistinguishable from one that cannot."""

    def test_a_file_with_a_sidecar_and_no_entry_is_reported(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            s = _Store(stack)
            s.add("editions/a/w/a--w--pub--imslp1.pdf")
            s.add("editions/a/w/a--w--other--imslp2.pdf")
            got = lib.unindexed(
                s.catalog("editions/a/w/a--w--pub--imslp1.pdf"), s.root)
        self.assertEqual(got["with_sidecar"],
                         ["editions/a/w/a--w--other--imslp2.pdf"])
        self.assertEqual(got["without_sidecar"], [])

    def test_the_two_answers_are_kept_APART_because_the_repairs_differ(self):
        """A sidecar-less file must never be reported as *rebuild the
        catalog*: `rebuild_catalog` refuses to invent an entry from a filename,
        so a rebuild would REPORT it and the repair is to fetch provenance."""
        import contextlib
        with contextlib.ExitStack() as stack:
            s = _Store(stack)
            s.add("editions/a/w/has-side.pdf")
            s.add("editions/a/w/no-side.pdf", sidecar=False)
            got = lib.unindexed(s.catalog(), s.root)
        self.assertEqual(got["with_sidecar"], ["editions/a/w/has-side.pdf"])
        self.assertEqual(got["without_sidecar"], ["editions/a/w/no-side.pdf"])


class TestItIsSilentWhenItShouldBe(unittest.TestCase):

    def test_a_catalog_that_lists_everything_reports_nothing(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            s = _Store(stack)
            s.add("editions/a/w/one.pdf")
            s.add("reference/a/w/two.mxl")
            got = lib.unindexed(
                s.catalog("editions/a/w/one.pdf", "reference/a/w/two.mxl"),
                s.root)
        self.assertEqual(got, {"with_sidecar": [], "without_sidecar": []})

    def test_an_ABSENT_store_reports_NOTHING_rather_than_everything(self):
        """⚠️ THE EMPTY STATE IS THE OPPOSITE OF `verify`'S, which is why the
        two are separate functions. On a fresh clone `library/` does not exist:
        `verify` correctly reports every entry missing, and this must report
        nothing — reporting the whole catalog as unindexed would be exactly
        backwards."""
        import contextlib
        with contextlib.ExitStack() as stack:
            s = _Store(stack)
            got = lib.unindexed(s.catalog("editions/a/w/gone.pdf"),
                                s.root / "does-not-exist")
        self.assertEqual(got, {"with_sidecar": [], "without_sidecar": []})

    def test_a_sidecar_is_not_itself_a_store_file(self):
        """`iter_store_files` excludes `.json`; if it ever stopped, every
        sidecar would be reported as an unindexed score."""
        import contextlib
        with contextlib.ExitStack() as stack:
            s = _Store(stack)
            s.add("editions/a/w/one.pdf")
            got = lib.unindexed(s.catalog("editions/a/w/one.pdf"), s.root)
        self.assertEqual(got["with_sidecar"], [])
        self.assertEqual(got["without_sidecar"], [])


class TestTheCommandExitsNonZero(unittest.TestCase):
    """The guard is only a guard if `verify` FAILS on it."""

    def test_verify_reports_and_exits_non_zero(self):
        import contextlib
        import io
        from unittest import mock
        from tools.library import ingest
        with contextlib.ExitStack() as stack:
            s = _Store(stack)
            s.add("editions/a/w/late.pdf")
            gap = lib.unindexed(s.catalog(), s.root)
            buf = io.StringIO()
            with mock.patch.object(ingest.lib, "verify",
                                   return_value={"present": [], "missing": [],
                                                 "changed": []}), \
                 mock.patch.object(ingest.lib, "unindexed", return_value=gap), \
                 mock.patch.object(ingest.sys, "argv",
                                   ["ingest", "verify"]), \
                 contextlib.redirect_stdout(buf):
                rc = ingest.main()
        self.assertEqual(rc, 1)
        self.assertIn("UNINDEXED", buf.getvalue())
        self.assertIn("late.pdf", buf.getvalue())

    def test_a_clean_store_still_exits_zero(self):
        """The negative control: without it, an always-failing guard passes
        every assertion above."""
        import contextlib
        import io
        from unittest import mock
        from tools.library import ingest
        buf = io.StringIO()
        with mock.patch.object(ingest.lib, "verify",
                               return_value={"present": ["x"], "missing": [],
                                             "changed": []}), \
             mock.patch.object(ingest.lib, "unindexed",
                               return_value={"with_sidecar": [],
                                             "without_sidecar": []}), \
             mock.patch.object(ingest.sys, "argv", ["ingest", "verify"]), \
             contextlib.redirect_stdout(buf):
            rc = ingest.main()
        self.assertEqual(rc, 0)
        self.assertNotIn("UNINDEXED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
