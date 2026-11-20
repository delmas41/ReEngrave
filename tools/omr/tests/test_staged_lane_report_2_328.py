"""ROADMAP 2.328 -- the shared OFF reading of the frozen sample, and the refusals that keep it honest.

No library, pdf or weights: a throwaway git repo stands in for main and the lane, fake arm outputs stand in for readings.
Each refusal test starts from a case that is ACCEPTED and changes one thing, so a refusal cannot pass by accident.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest
import unittest.mock

from tools.omr.staged import lane_report as L

PAGES = [2, 4]
LOADED = [1, 2, 4]
FLAGS = [("OMR_NEW_THING", "0", "1")]


def host(rg, cx, cy, page, kind="note", typ="quarter", pitch="C4"):
    return dict(rg=rg, cx=cx, cy=cy, kind=kind, type=typ, pitch=pitch, page=page, sub={}, blue=False, onset=0, part="P1", measure=1)


def arm(hosts, loose=()):
    return dict(hosts=list(hosts), loose=list(loose), control=None, seconds=1.0)


class Repo:
    def __init__(self, root: pathlib.Path):
        self.p = root / "repo"
        self.p.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")

    def git(self, *a):
        r = subprocess.run(["git", "-C", str(self.p)] + list(a), capture_output=True, text=True)
        assert r.returncode == 0, (a, r.stderr)
        return r.stdout.strip()

    def commit(self, path, text, msg=None):
        f = self.p / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg or path)
        return self.git("rev-parse", "HEAD")


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._td.name)
        self.repo = Repo(self.tmp)
        self.base = self.repo.commit("tools/omr/reader.py", "x = 1\n")
        self.root = self.tmp / "baselines"
        self.work = self.tmp / "work"
        self.work.mkdir()
        self.off = arm([host("glyph/2/0/0/0/1", 10, 10, 2), host("glyph/4/0/0/0/1", 10, 10, 4)])
        for ext, body in (("symbols.json", json.dumps(self.off)), ("mini-record.json", "{}"), ("musicxml", "<x/>")):
            (self.work / ("litolff.off." + ext)).write_text(body)
        self.env = {"OMR_A": "1"}
        self.save()

    def tearDown(self):
        self._td.cleanup()

    def save(self, commit=None, **kw):
        a = dict(plate="litolff", work=self.work, commit=commit or self.base, pages=PAGES, loaded=LOADED, tag="T", cell_map="master",
                 cell_ver="v1", env=self.env, flags_off={}, repo=self.repo.p, root=self.root, date="2026-11-19 10:00:00")
        a.update(kw)
        return L.save_baseline(**a)

    def refusals(self, **kw):
        d = L.baseline_dir(self.base, "litolff", self.root)
        man = json.loads((d / "manifest.json").read_text())
        a = dict(man=man, d=d, plate="litolff", pages=PAGES, loaded=LOADED, tag="T", cell_map="master", cell_ver="v1",
                 env=dict(self.env), flags=FLAGS, repo=self.repo.p, main_ref="main")
        a.update(kw)
        return L.baseline_refusals(**a)

    def lane(self):
        self.repo.git("checkout", "-q", "-b", "lane")


class TestAcceptsAndRefuses(Base):
    def test_matching_lane_is_accepted_even_with_its_own_reader_change(self):
        self.lane()
        self.repo.commit("tools/omr/reader.py", "x = 2  # the change under test\n")
        self.assertEqual(self.refusals(), [])

    def test_refuses_a_different_page_list(self):
        self.lane()
        self.assertEqual(self.refusals(), [])
        self.assertTrue(any("page list differs" in w for w in self.refusals(pages=[2, 6])))

    def test_refuses_different_loaded_pages_plate_tag_cell_map_env(self):
        self.lane()
        self.assertTrue(any("loaded" in w for w in self.refusals(loaded=[2, 4])))
        self.assertTrue(any("manifest is for plate" in w for w in self.refusals(plate="brahms")))
        self.assertTrue(any("tag differs" in w for w in self.refusals(tag="U")))
        self.assertTrue(any("cell map differs" in w for w in self.refusals(cell_ver="v2")))
        self.assertTrue(any("cell map differs" in w for w in self.refusals(cell_map=None, cell_ver=None)))
        self.assertTrue(any("OMR_* environment differs" in w for w in self.refusals(env={"OMR_A": "1", "OMR_B": "1"})))

    def test_lane_flag_in_env_is_not_an_env_difference(self):
        self.assertEqual(L.omr_env({"OMR_A": "1", "OMR_NEW_THING": "1", "OMR_SURYA_KEEP_ALIVE": "0", "PATH": "x"}, ["OMR_NEW_THING"]), {"OMR_A": "1"})

    def test_refuses_a_commit_that_is_not_an_ancestor(self):
        self.repo.git("checkout", "-q", "-b", "side")
        side = self.repo.commit("tools/omr/side.py", "s\n")
        self.repo.git("checkout", "-q", "main")
        self.repo.git("checkout", "-q", "-b", "lane")
        self.save(commit=side)
        d = L.baseline_dir(side, "litolff", self.root)
        man = json.loads((d / "manifest.json").read_text())
        why = L.baseline_refusals(man, d, "litolff", PAGES, LOADED, "T", "master", "v1", dict(self.env), FLAGS, self.repo.p, "main")
        self.assertTrue(any("not an ancestor" in w for w in why))

    def test_refuses_a_later_main_commit_touching_tools_omr_merged_in(self):
        self.repo.commit("tools/omr/reader.py", "x = 3  # main moved a reader\n")   # on main, after the baseline
        self.repo.git("checkout", "-q", "-b", "lane", self.base)
        self.assertEqual(self.refusals(), [])           # not merged yet: fine
        self.repo.git("merge", "-q", "--no-edit", "main")
        why = self.refusals()
        self.assertTrue(any("merged 1 main commit" in w or "merged" in w for w in why), why)

    def test_a_later_main_commit_that_only_touches_docs_is_fine(self):
        self.repo.commit("docs/x.md", "doc\n")
        self.repo.git("checkout", "-q", "-b", "lane", self.base)
        self.repo.git("merge", "-q", "--no-edit", "main")
        self.assertEqual(self.refusals(), [])

    def test_refuses_when_main_cannot_be_read(self):
        self.lane()
        self.assertTrue(any("cannot tell" in w for w in self.refusals(main_ref="origin/nothing")))

    def test_refuses_a_missing_or_changed_file(self):
        self.lane()
        d = L.baseline_dir(self.base, "litolff", self.root)
        (d / "litolff.off.musicxml").write_text("<changed/>")
        self.assertTrue(any("changed since" in w for w in self.refusals()))
        (d / "litolff.off.musicxml").unlink()
        self.assertTrue(any("missing: litolff.off.musicxml" in w for w in self.refusals()))

    def test_flag_that_already_exists_on_the_baseline_tree_needs_its_off_value_recorded(self):
        self.repo.commit("tools/omr/reader.py", "import os\nos.environ.get('OMR_NEW_THING')\n")
        base2 = self.repo.git("rev-parse", "HEAD")
        self.save(commit=base2)
        self.repo.git("checkout", "-q", "-b", "lane")
        d = L.baseline_dir(base2, "litolff", self.root)
        man = json.loads((d / "manifest.json").read_text())
        args = (d, "litolff", PAGES, LOADED, "T", "master", "v1", dict(self.env), FLAGS, self.repo.p, "main")
        self.assertTrue(any("already exists on the baseline tree" in w for w in L.baseline_refusals(man, *args)))
        d2 = self.save(commit=base2, flags_off={"OMR_NEW_THING": "0"})
        man2 = json.loads((d2 / "manifest.json").read_text())
        self.assertEqual(L.baseline_refusals(man2, *args), [])
        self.assertTrue(any("was read at 0" in w for w in L.baseline_refusals(man2, d, "litolff", PAGES, LOADED, "T", "master", "v1", dict(self.env),
                                                                              [("OMR_NEW_THING", "5", "1")], self.repo.p, "main")))

    def test_manifest_names_what_it_was_made_from(self):
        man = json.loads((L.baseline_dir(self.base, "litolff", self.root) / "manifest.json").read_text())
        self.assertEqual((man["main_commit"], man["pages"], man["loaded_pages"], man["cell_map"], man["env"], man["date"]),
                         (self.base, PAGES, LOADED, "master", self.env, "2026-11-19 10:00:00"))
        self.assertEqual(man["tools_omr_tree"], self.repo.git("rev-parse", self.base + ":tools/omr"))
        self.assertEqual(len(man["files"]), 3)


class TestCheckPage(Base):
    def test_identical_page_is_equal(self):
        chk = arm([host("glyph/2/0/0/0/1", 10, 10, 2)])
        r = L.compare_check(self.off, chk, 2, tol=8)
        self.assertTrue(r["equal"], r)

    def test_a_difference_is_named_by_kind(self):
        chk = arm([host("glyph/2/0/0/0/1", 10, 10, 2, typ="half")])
        r = L.compare_check(self.off, chk, 2, tol=8)
        self.assertFalse(r["equal"])
        self.assertIn("value", r["differs"])

    def test_a_missing_note_differs(self):
        r = L.compare_check(self.off, arm([]), 2, tol=8)
        self.assertFalse(r["equal"])
        self.assertIn("note", r["differs"])

    def test_other_pages_do_not_count(self):
        chk = arm([host("glyph/2/0/0/0/1", 10, 10, 2)])       # page 4's note is in the baseline only
        self.assertTrue(L.compare_check(self.off, chk, 2, tol=8)["equal"])

    def test_a_page_with_no_mark_proves_nothing(self):
        r = L.compare_check(arm([host("g", 1, 1, 4)]), arm([]), 2, tol=8)
        self.assertFalse(r["equal"])
        self.assertTrue(r["empty"])

    def test_check_page_spec(self):
        sample = {"plates": {"litolff": {"pages": [2, 4]}, "brahms": {"pages": [4, 6]}}}
        self.assertEqual(L.resolve_check_page("litolff:2", ["litolff", "brahms"], sample), ("litolff", 2))
        self.assertEqual(L.resolve_check_page("6", ["litolff", "brahms"], sample), ("brahms", 6))
        with self.assertRaises(SystemExit):
            L.resolve_check_page("4", ["litolff", "brahms"], sample)      # on both plates
        with self.assertRaises(SystemExit):
            L.resolve_check_page("litolff:6", ["litolff", "brahms"], sample)


class TestResolveSharedOff(Base):
    def setUp(self):
        super().setUp()
        self.lane()
        self.sample = {"plates": {"litolff": {"pages": PAGES, "context_pages": [1]}}}
        self._cmv, self._lp = L.cell_map_version, L.CELL_MAP
        L.cell_map_version = lambda plate: "v1"
        L.CELL_MAP = L.CELL_MAP_ROOT
        self.out = self.tmp / "out"
        self.out.mkdir()

    def tearDown(self):
        L.cell_map_version, L.CELL_MAP = self._cmv, self._lp
        super().tearDown()

    def go(self, reading, page=2, **extra):
        b = dict(check_pages={"litolff": page}, repo=self.repo.p, root=self.root, main_ref="main", read_check=lambda *a: reading)
        b.update(extra)
        return L.resolve_shared_off("litolff", FLAGS, self.sample, "T", self.out, b, dict(self.env))

    def test_used_when_the_check_page_matches_and_files_are_copied_for_the_compare_step(self):
        info, sym = self.go(arm([host("glyph/2/0/0/0/1", 10, 10, 2)]))
        self.assertTrue(info["used"], info)
        self.assertEqual(info["commit"], self.base)
        self.assertEqual(sym["hosts"], self.off["hosts"])
        self.assertTrue((self.out / "litolff.off.mini-record.json").exists())
        self.assertIn(self.base[:9], "\n".join(L.baseline_lines("litolff", info)))
        self.assertIn("IDENTICAL", "\n".join(L.baseline_lines("litolff", info)))

    def test_refused_when_the_check_page_differs_and_the_report_says_so(self):
        info, sym = self.go(arm([host("glyph/2/0/0/0/1", 10, 10, 2, typ="half")]))
        self.assertFalse(info["used"])
        self.assertIsNone(sym)
        self.assertFalse((self.out / "litolff.off.symbols.json").exists())
        self.assertIn("DIFFERS", info["refused"][0])
        self.assertIn("REFUSED", "\n".join(L.baseline_lines("litolff", info)))

    def test_refused_without_a_check_page(self):
        info, sym = self.go(arm([]), page=None)
        self.assertIsNone(sym)
        self.assertIn("no --check-page", info["refused"][0])

    def test_refused_on_a_different_page_list(self):
        self.sample["plates"]["litolff"]["pages"] = [2, 4, 6]
        info, sym = self.go(arm([host("glyph/2/0/0/0/1", 10, 10, 2)]))
        self.assertIsNone(sym)
        self.assertTrue(any("page list differs" in w for w in info["refused"]))

    def test_refused_when_there_is_no_saved_reading(self):
        info, sym = self.go(arm([]), root=self.tmp / "empty")
        self.assertIsNone(sym)
        self.assertIn("no saved reading", info["refused"][0])

    def test_run_report_refusal_is_in_the_notes_and_reads_its_own_off_arm(self):
        seen = {}

        class Stop(Exception):
            pass

        def fake_read_arms(*a, **k):
            seen.update(k)
            raise Stop()
        orig = L.read_arms
        L.read_arms = fake_read_arms
        try:
            with self.assertRaises(Stop):
                L.run_report(FLAGS, ["litolff"], "gather", self.out, "T", 1, 1, self.sample, ["n"],
                             baseline=dict(check_pages={"litolff": 2}, repo=self.repo.p, root=self.tmp / "none", main_ref="main"))
        finally:
            L.read_arms = orig
        self.assertEqual(seen["preloaded"], {})        # nothing shared was used: both arms are read

    def test_run_report_with_a_good_baseline_reads_only_the_on_arm(self):
        seen = {}

        class Stop(Exception):
            pass

        def fake_read_arms(*a, **k):
            seen.update(k)
            raise Stop()
        orig = L.read_arms
        L.read_arms = fake_read_arms
        try:
            with unittest.mock.patch.dict("os.environ", {"OMR_A": "1"}, clear=True), self.assertRaises(Stop):
                L.run_report(FLAGS, ["litolff"], "gather", self.out, "T", 1, 1, self.sample, ["n"],
                             baseline=dict(check_pages={"litolff": 2}, repo=self.repo.p, root=self.root, main_ref="main",
                                           read_check=lambda *a: arm([host("glyph/2/0/0/0/1", 10, 10, 2)])))
        finally:
            L.read_arms = orig
        self.assertEqual(list(seen["preloaded"]), [("litolff", "off")])


class TestWithoutBaselineNothingChanges(unittest.TestCase):
    def test_run_report_without_baseline_reads_both_arms_and_resolves_nothing(self):
        calls = {}

        class Stop(Exception):
            pass

        def fake_read_arms(flags, plates, mode, work, tag, workers, sample, **k):
            calls.update(k)
            raise Stop()
        orig_r, orig_s = L.read_arms, L.resolve_shared_off
        L.read_arms = fake_read_arms
        L.resolve_shared_off = lambda *a, **k: (_ for _ in ()).throw(AssertionError("baseline code ran without --baseline"))
        try:
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(Stop):
                    L.run_report([], ["litolff"], "gather", pathlib.Path(td), "T", 1, 1, {"plates": {"litolff": {"pages": [2]}}}, [])
        finally:
            L.read_arms, L.resolve_shared_off = orig_r, orig_s
        self.assertEqual(calls.get("preloaded"), {})
        self.assertNotIn("arms", calls)

    def test_read_arms_defaults_to_both_arms(self):
        import inspect
        self.assertEqual(inspect.signature(L.read_arms).parameters["arms"].default, ("off", "on"))

    def test_cli_options_are_refused_when_misused(self):
        orig = L.check_tag
        L.check_tag = lambda *a, **k: None
        try:
            with tempfile.TemporaryDirectory() as td:
                base = ["--flag", "OMR_NEW_THING", "--allow-unknown-flag", "--from", "gather", "--plates", "litolff", "--out", td]
                with self.assertRaises(SystemExit):
                    L.main(base + ["--baseline", "shared"])                       # no cell map
                with self.assertRaises(SystemExit):
                    L.main(base + ["--check-page", "litolff:2"])                  # check page without --baseline
                with self.assertRaises(SystemExit):
                    L.main(base + ["--make-baseline"])                            # no cell map
        finally:
            L.check_tag = orig


class TestMakeBaselineRefusals(Base):
    def test_refuses_a_dirty_reader_tree(self):
        (self.repo.p / "tools/omr/reader.py").write_text("x = 99\n")
        with self.assertRaises(SystemExit) as c:
            L.make_baseline([], ["litolff"], self.tmp / "o", "T", 1, {"plates": {}}, repo=self.repo.p, root=self.root, main_ref="main")
        self.assertIn("uncommitted", str(c.exception))

    def test_refuses_a_head_that_is_not_on_main(self):
        self.repo.git("checkout", "-q", "-b", "lane")
        self.repo.commit("tools/omr/reader.py", "x = 5\n")
        with self.assertRaises(SystemExit) as c:
            L.make_baseline([], ["litolff"], self.tmp / "o", "T", 1, {"plates": {}}, repo=self.repo.p, root=self.root, main_ref="main")
        self.assertIn("not on main", str(c.exception))


if __name__ == "__main__":
    unittest.main()
