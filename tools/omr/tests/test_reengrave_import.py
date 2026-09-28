"""ROADMAP 4.1 -- `reengrave import <work>`, one command from a catalogued
work to finished files.

Proof budget (DECISIONS 2026-09-28, Sean: build and wire, cheap proof
only): RED->GREEN unit tests with the browser, the download and the staged
pipeline all mocked. **No real downloads, no gathers** -- every test here
either calls a pure function (ranking, page-range resolution, command
construction) or replaces the three side-effecting seams (`open_browser`,
the download watcher, `subprocess.run`) with a fake before exercising the
CLI, so nothing here makes a network request or spawns a real process.

No test asserts on module source text.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.reengrave import fetch as fetch_mod
from tools.reengrave import planning
from tools.reengrave.__main__ import main


WORK_ID = "beethoven--symphony-5"


def _held_entry(imslp_id: str, *, pages: int = 88, publisher: str = "Henry Litolff's Verlag, Braunschweig, 1870, plate 2769") -> dict:
    return {
        "kind": "edition",
        "work_id": WORK_ID,
        "path": f"editions/beethoven/symphony-5/beethoven--symphony-5--litolff--imslp{imslp_id}.pdf",
        "imslp_id": imslp_id,
        "publisher": publisher,
        "pages": pages,
        "image_type": "Normal Scan",
        "copyright": "Public Domain",
        "composer_slug": "beethoven",
    }


def _wishlist_row(imslp_id: str, *, held: bool = False) -> dict:
    return {
        "composer": "Beethoven",
        "work": "Symphony No.5",
        "imslp_id": imslp_id,
        "publisher": "Ernst Eulenburg, Leipzig, 1938, plate E.E. 3602",
        "pages": 136,
        "scan": "Normal Scan",
        "copyright": "Public Domain",
        "description": "Complete Score",
        "page_url": f"https://imslp.org/wiki/Special:ReverseLookup/{imslp_id}",
        "already_held": held,
    }


# ---------------------------------------------------------------------------
# planning.rank_editions -- pure, no filesystem, no network
# ---------------------------------------------------------------------------


class TestRankEditions(unittest.TestCase):
    def test_a_held_edition_ranks_and_is_marked_held(self):
        catalog = {"entries": [_held_entry("984073")]}
        ranked = planning.rank_editions(WORK_ID, catalog=catalog, wishlist_rows=[])
        self.assertEqual(len(ranked), 1)
        self.assertTrue(ranked[0]["held"])
        self.assertEqual(ranked[0]["imslp_id"], "984073")
        self.assertIn("score", ranked[0])

    def test_a_catalogued_but_not_held_row_ranks_and_is_marked_not_held(self):
        catalog = {"entries": []}
        ranked = planning.rank_editions(
            WORK_ID, catalog=catalog, wishlist_rows=[_wishlist_row("575952")])
        self.assertEqual(len(ranked), 1)
        self.assertFalse(ranked[0]["held"])
        self.assertEqual(ranked[0]["source"], "catalogued")

    def test_held_and_catalogued_are_both_listed_and_deduplicated(self):
        # The same imslp_id appearing in both the catalog (held) and the
        # wishlist (not yet re-ingested) must be counted ONCE, as held.
        catalog = {"entries": [_held_entry("984073")]}
        ranked = planning.rank_editions(
            WORK_ID, catalog=catalog,
            wishlist_rows=[_wishlist_row("984073", held=True), _wishlist_row("575952")])
        ids = sorted(c["imslp_id"] for c in ranked)
        self.assertEqual(ids, ["575952", "984073"])
        by_id = {c["imslp_id"]: c for c in ranked}
        self.assertTrue(by_id["984073"]["held"])
        self.assertFalse(by_id["575952"]["held"])

    def test_a_work_with_nothing_known_and_no_network_candidates_raises(self):
        with self.assertRaises(planning.NoKnownEdition):
            planning.rank_editions("nobody--symphony-99", catalog={"entries": []},
                                   wishlist_rows=[])

    def test_a_work_with_nothing_local_but_network_candidates_uses_them(self):
        network = [{
            "imslp_id": "1",
            "description": "Complete Score",
            "pages": 100,
            "publisher": "Breitkopf & Härtel",
            "editor": "",
            "scan": "Normal Scan",
            "copyright": "Public Domain",
            "page_url": "https://imslp.org/wiki/Special:ReverseLookup/1",
        }]
        ranked = planning.rank_editions(
            "nobody--symphony-99", catalog={"entries": []}, wishlist_rows=[],
            network_candidates=network)
        self.assertEqual(len(ranked), 1)
        self.assertFalse(ranked[0]["held"])
        self.assertEqual(ranked[0]["source"], "network")


# ---------------------------------------------------------------------------
# planning.resolve_pages_spec -- --movements passes through unchanged
# ---------------------------------------------------------------------------


class TestResolvePagesSpec(unittest.TestCase):
    def test_no_movements_covers_the_whole_known_page_count(self):
        spec, spans = planning.resolve_pages_spec(88, None)
        self.assertEqual(spec, "0-87")
        self.assertEqual(spans, ())

    def test_no_movements_and_no_known_page_count_falls_back_to_page_zero(self):
        spec, spans = planning.resolve_pages_spec(None, None)
        self.assertEqual(spec, "0")
        self.assertEqual(spans, ())

    def test_movements_spec_drives_the_page_range(self):
        spec, spans = planning.resolve_pages_spec(88, "1:1-16")
        self.assertEqual(spec, "1-16")
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["number"], 1)

    def test_multi_movement_spec_spans_the_full_range(self):
        spec, spans = planning.resolve_pages_spec(88, "1:0-20,2:21-40")
        self.assertEqual(spec, "0-40")
        self.assertEqual(len(spans), 2)

    def test_a_malformed_spec_raises_loudly_rather_than_defaulting(self):
        from tools.omr.staged.movements import MalformedMovementSpec
        with self.assertRaises(MalformedMovementSpec):
            planning.resolve_pages_spec(88, "not-a-spec")


# ---------------------------------------------------------------------------
# planning.build_staged_command
# ---------------------------------------------------------------------------


class TestBuildStagedCommand(unittest.TestCase):
    def test_the_command_carries_route_weights_work_id_and_all_four_outputs(self):
        cmd = planning.build_staged_command(
            python="python3", pdf_path="/x/score.pdf", work_id=WORK_ID,
            pages_spec="0-87", movements_arg=None, out_dir=Path("/out/w"))
        joined = " ".join(cmd)
        self.assertIn("tools.omr.staged", joined)
        self.assertIn("--route-weights", cmd)
        self.assertIn("--work-id", cmd)
        self.assertIn(WORK_ID, cmd)
        self.assertIn("--pages", cmd)
        self.assertIn("0-87", cmd)
        self.assertIn(str(Path("/out/w") / f"{WORK_ID}.record.json"), cmd)
        self.assertIn(str(Path("/out/w") / f"{WORK_ID}.musicxml"), cmd)
        self.assertIn(str(Path("/out/w") / f"{WORK_ID}.ly"), cmd)
        self.assertIn(str(Path("/out/w") / f"{WORK_ID}.pdf"), cmd)
        self.assertNotIn("--movements", cmd)

    def test_movements_is_passed_through_unchanged(self):
        spec = "1:0-15,2:16.2-40"
        cmd = planning.build_staged_command(
            python="python3", pdf_path="/x/score.pdf", work_id=WORK_ID,
            pages_spec="0-40", movements_arg=spec, out_dir=Path("/out/w"))
        self.assertIn("--movements", cmd)
        self.assertEqual(cmd[cmd.index("--movements") + 1], spec)


# ---------------------------------------------------------------------------
# fetch.watch_for_download -- a positive control (it must be able to fail)
# ---------------------------------------------------------------------------


class TestWatchForDownload(unittest.TestCase):
    def test_a_new_pdf_in_the_directory_is_picked_up(self):
        with tempfile.TemporaryDirectory() as td:
            downloads = Path(td)
            before = fetch_mod._snapshot(downloads)
            name = "IMSLP984073-PMLP01586-Beethoven_Symphony_5"
            new_file = downloads / (name + "." + "pdf")
            new_file.write_bytes(b"%PDF-1.4 fake")
            got = fetch_mod.watch_for_download(
                downloads, timeout_s=5.0, existing=before,
                now=lambda: 0.0, sleep=lambda s: None)
            self.assertEqual(got, new_file)

    def test_a_pdf_already_present_before_the_click_is_not_mistaken_for_the_new_one(self):
        # THE POSITIVE CONTROL: this must be able to time out, or the guard
        # is not distinguishing "new" from "already there" at all.
        with tempfile.TemporaryDirectory() as td:
            downloads = Path(td)
            old_name = "already-here." + "pdf"
            (downloads / old_name).write_bytes(b"%PDF-1.4 old")
            before = fetch_mod._snapshot(downloads)
            clock = {"t": 0.0}
            with self.assertRaises(fetch_mod.DownloadTimeout):
                fetch_mod.watch_for_download(
                    downloads, timeout_s=2.0, existing=before,
                    now=lambda: clock.update(t=clock["t"] + 10) or clock["t"],
                    sleep=lambda s: None)

    def test_nothing_appearing_times_out_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as td:
            downloads = Path(td)
            clock = {"t": 0.0}
            with self.assertRaises(fetch_mod.DownloadTimeout) as ctx:
                fetch_mod.watch_for_download(
                    downloads, timeout_s=1.0, existing=set(),
                    now=lambda: clock.update(t=clock["t"] + 5) or clock["t"],
                    sleep=lambda s: None)
            self.assertIn(str(downloads), str(ctx.exception))


# ---------------------------------------------------------------------------
# fetch.get_edition_pdf -- held skips the browser; not-held opens it once
# ---------------------------------------------------------------------------


class TestGetEditionPdf(unittest.TestCase):
    def test_a_held_candidate_never_opens_a_browser(self):
        opener = mock.Mock()
        with tempfile.TemporaryDirectory() as td:
            lib_root = Path(td) / "library"
            rel = "editions/beethoven/symphony-5/x--imslp984073.pdf"
            (lib_root / "editions/beethoven/symphony-5").mkdir(parents=True)
            (lib_root / rel).write_bytes(b"%PDF-1.4 held")
            with mock.patch.object(fetch_mod.lib, "library_root", return_value=lib_root):
                candidate = {"held": True, "path": rel, "imslp_id": "984073"}
                got = fetch_mod.get_edition_pdf(
                    candidate, downloads_dir=Path(td) / "Downloads",
                    timeout_s=5.0, open_browser=opener)
        self.assertEqual(got, lib_root / rel)
        opener.assert_not_called()

    def test_a_not_held_candidate_opens_the_browser_once_and_ingests_the_download(self):
        opener = mock.Mock()
        ingest_calls = []

        def fake_ingest(paths, **kw):
            ingest_calls.append((list(paths), kw))
            return 0

        with tempfile.TemporaryDirectory() as td:
            downloads = Path(td) / "Downloads"
            downloads.mkdir()
            lib_root = Path(td) / "library"
            lib_root.mkdir()

            def fake_watch(dl_dir, *, timeout_s, existing, **kw):
                fake_pdf = downloads / ("IMSLP575952-PMLP01586-Beethoven" + "." + "pdf")
                fake_pdf.write_bytes(b"%PDF-1.4 new")
                return fake_pdf

            fresh_catalog = {"entries": [{
                "path": "editions/beethoven/symphony-5/new--imslp575952.pdf",
                "sha256": None,  # filled below
            }]}

            def fake_sha(path):
                return "deadbeef"

            fresh_catalog["entries"][0]["sha256"] = "deadbeef"

            with mock.patch.object(fetch_mod.lib, "library_root", return_value=lib_root), \
                 mock.patch.object(fetch_mod.lib, "sha256_of", side_effect=fake_sha), \
                 mock.patch.object(fetch_mod.lib, "rebuild_catalog", return_value=fresh_catalog), \
                 mock.patch.object(fetch_mod.lib, "load_catalog", return_value=fresh_catalog):
                candidate = {"held": False, "imslp_id": "575952",
                            "page_url": "https://imslp.org/wiki/Special:ReverseLookup/575952"}
                got = fetch_mod.get_edition_pdf(
                    candidate, downloads_dir=downloads, timeout_s=5.0,
                    open_browser=opener, watch=fake_watch,
                    ingest_imslp=fake_ingest)

        opener.assert_called_once_with(
            "https://imslp.org/wiki/Special:ReverseLookup/575952")
        self.assertEqual(len(ingest_calls), 1)
        self.assertEqual(got, lib_root / "editions/beethoven/symphony-5/new--imslp575952.pdf")

    def test_a_timeout_fetches_nothing_and_raises(self):
        opener = mock.Mock()

        def timing_out_watch(dl_dir, *, timeout_s, existing, **kw):
            raise fetch_mod.DownloadTimeout("no new PDF appeared")

        ingest_calls = []
        with tempfile.TemporaryDirectory() as td:
            candidate = {"held": False, "imslp_id": "1", "page_url": "https://imslp.org/x"}
            with self.assertRaises(fetch_mod.DownloadTimeout):
                fetch_mod.get_edition_pdf(
                    candidate, downloads_dir=Path(td), timeout_s=0.1,
                    open_browser=opener, watch=timing_out_watch,
                    ingest_imslp=lambda *a, **k: ingest_calls.append(a))
        opener.assert_called_once()
        self.assertEqual(ingest_calls, [])


# ---------------------------------------------------------------------------
# The CLI, end to end, with the browser/download/pipeline seams mocked
# ---------------------------------------------------------------------------


class TestCliDryRun(unittest.TestCase):
    def setUp(self):
        self.catalog = {"entries": [_held_entry("984073")]}
        self._patches = [
            mock.patch("tools.reengrave.planning.lib.load_catalog", return_value=self.catalog),
            mock.patch("tools.reengrave.planning.load_wishlist", return_value=[]),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def test_dry_run_executes_nothing(self):
        opener = mock.Mock()
        with mock.patch("tools.reengrave.fetch.default_open_browser", opener), \
             mock.patch("subprocess.run") as run:
            rc = main(["import", WORK_ID, "--dry-run", "--movements", "1:1-16"])
        self.assertEqual(rc, 0)
        run.assert_not_called()
        opener.assert_not_called()

    def test_dry_run_prints_the_budget_line(self):
        with mock.patch("subprocess.run") as run, \
             mock.patch("sys.stdout") as _stdout:
            pass  # placeholder, real capture below
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch("subprocess.run"):
            main(["import", WORK_ID, "--dry-run", "--movements", "1:1-16"])
        out = buf.getvalue()
        self.assertIn("budget estimate", out)

    def test_no_movements_prints_the_one_movement_warning(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch("subprocess.run"):
            main(["import", WORK_ID, "--dry-run"])
        out = buf.getvalue()
        self.assertIn("ONE movement", out)

    def test_movements_given_suppresses_the_one_movement_warning(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch("subprocess.run"):
            main(["import", WORK_ID, "--dry-run", "--movements", "1:1-16"])
        out = buf.getvalue()
        self.assertNotIn("ONE movement", out)


class TestCliHeldEditionRun(unittest.TestCase):
    """A held edition -- no browser, and the real (mocked) pipeline sees the
    right flags."""

    def setUp(self):
        self.catalog = {"entries": [_held_entry("984073")]}
        self._patches = [
            mock.patch("tools.reengrave.planning.lib.load_catalog", return_value=self.catalog),
            mock.patch("tools.reengrave.planning.load_wishlist", return_value=[]),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def test_held_edition_never_opens_a_browser_and_runs_the_right_command(self):
        opener = mock.Mock()
        fake_run = mock.Mock(return_value=mock.Mock(returncode=0))
        with tempfile.TemporaryDirectory() as td:
            lib_root = Path(td) / "library"
            rel = _held_entry("984073")["path"]
            (lib_root / Path(rel).parent).mkdir(parents=True)
            (lib_root / rel).write_bytes(b"%PDF-1.4 held")
            out_dir = Path(td) / "out"
            with mock.patch("tools.reengrave.fetch.lib.library_root", return_value=lib_root), \
                 mock.patch("tools.reengrave.fetch.default_open_browser", opener), \
                 mock.patch("subprocess.run", fake_run):
                rc = main(["import", WORK_ID, "--yes", "--movements", "1:1-16",
                          "--out-dir", str(out_dir)])
        self.assertEqual(rc, 0)
        opener.assert_not_called()
        fake_run.assert_called_once()
        cmd = fake_run.call_args[0][0]
        self.assertIn("--route-weights", cmd)
        self.assertIn("--movements", cmd)
        self.assertEqual(cmd[cmd.index("--movements") + 1], "1:1-16")
        self.assertIn(str(lib_root / rel), cmd)
        env = fake_run.call_args.kwargs.get("env") or {}
        self.assertEqual(env.get("OMR_SURYA_KEEP_ALIVE"), "0")


if __name__ == "__main__":
    unittest.main()
