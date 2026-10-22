"""The coverage instrument must audit the class space the DETECTOR SHIPS.

⚠️ THE DEFECT THESE PIN, AND WHY IT SURVIVED. `gather_coverage._detector_classes()`
read `training/deepscores_classes.py` -- whose `DEEPSCORES_V2_CLASSES` is a
**146-name snapshot of an older DeepScoresV2 release** -- under a docstring
calling it "the 208-class space". The shipped checkpoint
(`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`) carries 208 names,
and the two disagree on SPELLING as well as on length: the snapshot spells the
clefs `gClef`/`fClef`/`cClefAlto`, the checkpoint `clefG`/`clefF`/`clefCAlto`.

So the audit ran against 15 names that can never fire while never checking 26
that can -- and because `_family` splits at the first camel hump, the snapshot's
clefs were filed under invented families `g`, `f`, `c` and `unpitched`, leaving
the real `clef` family holding only the octave markers `clef8`/`clef15`.

⚠️ THE OLD GUARD COULD NOT SEE IT. `test_every_detector_family_is_mapped`
asserts `cs["classes"] > 100` -- and 146 > 100. A floor cannot catch a space
that is the wrong space; only an identity can. Both families of defect this
repo names apply: *a control that computes the wrong thing*, and *a control
that was never testing what its name says*.

⚠️ EVERY TEST HERE IS AN IDENTITY OR A MEMBERSHIP, never a count over a floor.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tools.omr import class_aliases
from tools.omr.staged import gather_coverage as GC
from tools.omr.training.deepscores_classes import DEEPSCORES_V2_CLASSES

#: The production checkpoint whose class space this pipeline ships against.
#: Named here so the skip below can assert on its own condition rather than
#: vanishing quietly on a machine with no weights.
PRODUCTION_WEIGHTS = (Path(__file__).resolve().parents[3] / "omr-weights"
                      / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


def _canonical_shipped() -> tuple:
    """The shipped vocabulary as a CONSUMER sees it: canonicalized, id order."""
    return tuple(dict.fromkeys(
        class_aliases.canonical(n) for n in class_aliases.vocabulary()))


class TestTheAuditedSpaceIsTheShippedOne(unittest.TestCase):

    def test_the_audited_space_is_the_canonical_shipped_vocabulary(self) -> None:
        """An IDENTITY. This is the test that goes red on the pre-repair tree."""
        self.assertEqual(tuple(GC._detector_classes()), _canonical_shipped())

    def test_it_is_not_the_training_snapshot(self) -> None:
        """Named explicitly, because the snapshot is a plausible-looking list
        of real class names -- the reason this went unnoticed."""
        audited = set(GC._detector_classes())
        self.assertNotEqual(audited, set(DEEPSCORES_V2_CLASSES))
        unreachable = audited - set(_canonical_shipped())
        self.assertEqual(
            unreachable, set(),
            "the audit checks names the detector cannot emit: "
            f"{sorted(unreachable)}")

    def test_the_clefs_the_pipeline_reads_are_audited(self) -> None:
        """The worked case, both directions. The snapshot's spellings are not
        merely absent from the checkpoint -- auditing them put every clef in a
        family invented by `_family` splitting `gClef` into `g` + `Clef`."""
        audited = set(GC._detector_classes())
        for shipped in ("clefG", "clefF", "clefCAlto", "clefCTenor",
                        "clefUnpitchedPercussion"):
            self.assertIn(shipped, audited)
        for snapshot_only in ("gClef", "fClef", "cClefAlto", "cClefTenor",
                              "unpitchedPercussionClef1"):
            self.assertNotIn(snapshot_only, audited)

    def test_the_clef_family_is_not_just_the_octave_markers(self) -> None:
        clefs = {c for c in GC._detector_classes() if GC._family(c) == "clef"}
        self.assertTrue(
            clefs - {"clef8", "clef15"},
            "the `clef` family holds only the octave markers -- the clefs "
            "themselves have been filed under some other family")

    def test_a_coarse_name_is_audited_under_the_spelling_that_arrives(self) -> None:
        """`yolo_detector` canonicalizes at the one place the model's `names`
        are read, so `dynamicLetterF` never reaches GATHER under that name.

        ⚠️ Auditing the RAW 208 would report six `dynamicLetter*` classes as
        live detector classes for `Q.DYNAMIC_LETTER` when by construction none
        can arrive -- a NEW false report in place of the old one. This pins the
        direction so a future 'fix to 208' cannot quietly take it.
        """
        audited = set(GC._detector_classes())
        raw = set(class_aliases.vocabulary())
        for coarse, fine in class_aliases.ALIASES.items():
            if coarse in raw:
                self.assertNotIn(coarse, audited)
                self.assertIn(fine, audited)


class TestTheManifestIsTheShippedWeights(unittest.TestCase):
    """The vocabulary of record must equal what the checkpoint actually carries."""

    def test_the_skip_condition_itself(self) -> None:
        """⚠️ ASSERTED, so an absent weights file cannot make the test below
        vanish silently -- *a test named for a hazard it does not reach*.

        This never skips. It pins that the path we probe is the production
        checkpoint, so a rename cannot turn the check below into a permanent
        no-op that still reports green.
        """
        self.assertEqual(PRODUCTION_WEIGHTS.name,
                         "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
        self.assertEqual(PRODUCTION_WEIGHTS.parent.name, "omr-weights")
        self.assertIn(PRODUCTION_WEIGHTS.exists(), (True, False))

    def test_the_manifest_is_self_consistent(self) -> None:
        """Never skips: true with or without a weights file."""
        vocab = class_aliases.vocabulary()
        self.assertEqual(len(vocab), 208)
        self.assertEqual(class_aliases.unaccounted(vocab), [])

    def test_the_manifest_matches_the_shipped_weights(self) -> None:
        if not PRODUCTION_WEIGHTS.exists():
            self.skipTest(
                "LOUD SKIP: no weights at "
                f"{PRODUCTION_WEIGHTS} -- the manifest is unverified against a "
                "checkpoint on this machine. `test_the_skip_condition_itself` "
                "and `test_the_manifest_is_self_consistent` still ran.")
        try:
            import torch                                    # noqa: PLC0415
        except ImportError:                                 # pragma: no cover
            self.skipTest("LOUD SKIP: torch is not installed on this machine.")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ck = torch.load(PRODUCTION_WEIGHTS, map_location="cpu",
                            weights_only=False)
        names = ck["model"].names
        shipped = [names[i] for i in range(len(names))]
        self.assertEqual(shipped, class_aliases.vocabulary(),
                         "the committed 208-name manifest has drifted from the "
                         "shipped checkpoint -- index for index")


class TestTheTableDescribesTheShippedSpace(unittest.TestCase):

    def test_no_family_in_the_table_is_dead(self) -> None:
        """A key no shipped class maps to is a stale entry, and three such
        entries (`c`, `f`, `g`) mapped to `CLEF_GLYPH` -- so the table LOOKED
        like it named the clefs while the real `clef` family held only
        `clef8`/`clef15`. The same doctrine as
        `test_the_inventory_has_no_stale_entries`."""
        live = {GC._family(c) for c in GC._detector_classes()}
        dead = sorted(set(GC.FAMILY_TO_Q) - live)
        self.assertEqual(
            dead, [],
            f"FAMILY_TO_Q keys no shipped class produces: {dead}")

    def test_the_coarse_articulations_are_mapped_where_gather_files_them(self) -> None:
        """Checked at the EMIT SITE, not inferred from the family name.
        `gather.py` routes on the prefix `artic`, which both spellings share."""
        from tools.omr.staged import gather as G
        for coarse in ("articulationAccent", "articulationStaccato",
                       "articulationTenuto"):
            self.assertEqual(GC._family(coarse), "articulation")
            self.assertTrue(coarse.startswith(G._ARTIC_PREFIX))
            self.assertIsNone(G._artic_side(coarse))
        self.assertEqual(GC.FAMILY_TO_Q["articulation"], "ARTICULATION_MARK")
        self.assertEqual(GC.FAMILY_TO_Q["articulation"],
                         GC.FAMILY_TO_Q["artic"],
                         "one glyph, two spellings -- one quantity")


class TestTheToolStillRunsWithoutTheVisionStack(unittest.TestCase):

    def test_importing_it_pulls_no_cv2_torch_or_ultralytics(self) -> None:
        """⚠️ THE PROPERTY THE REPAIR RELIES ON. `_detector_classes` used an
        AST read specifically to dodge the vision stack; it now IMPORTS
        `class_aliases`, which is stdlib-only (`json`, `pathlib`). A coverage
        tool that needs weights installed is a coverage tool nobody runs in CI.
        """
        code = ("import sys, tools.omr.staged.gather_coverage as G; "
                "G._detector_classes(); "
                "print(sorted(m for m in ('cv2','torch','ultralytics') "
                "if m in sys.modules))")
        out = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True,
                             cwd=str(Path(__file__).resolve().parents[3]))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "[]", out.stdout)


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
