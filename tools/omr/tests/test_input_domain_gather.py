"""WHICH PRINTING this is, and the one-sided rule the key signature reads it by.

Sean, 2026-09-22: *"if a page is engraved or a scan along with the publisher
info and year -- whatever we have -- should be gathered in the first stage --
then we need to make sure that the key signature is determined based on that
info."*

⚠️⚠️ **THE TWO ROWS ARE SEPARATE BECAUSE A MEASUREMENT SAYS SO, NOT BECAUSE
THE TAXONOMY IS TIDIER**, and `test_the_catalog_is_SILENT_where_the_container_
ANSWERS` is that measurement in one assertion: the engraved fixture the
key-signature rule is proven on is a RENDER, in no catalog, so
`gather_document_identity` abstains `not_in_catalog` on it while
`gather_input_domain` answers `engraved`. A domain filed as a FIELD of the
catalog row would have a reach of ZERO on the one input that matters.

⚠️ **THE CONSUMER IS ONE-SIDED** and four inputs must fall through to the
shipped precedence unchanged: a scan, a classifier abstention, a document with
no identity row, and the flag off. Each has its own test, and each is paired
with the ENGRAVED case as a positive control -- a battery of fall-through
tests passes by falling through always.
"""

from __future__ import annotations

import os
import unittest

import fitz

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import header as H
from tools.omr.staged.record import DOCUMENT, Log, Q, READERS, ABSTAIN

#: ⚠️ FOUR LEVELS: tests -> omr -> tools -> repo. Three landed on `tools/`,
#: every path test `skipTest`ped, and 5 of 18 assertions silently did not run
#: -- a green suite measuring its own path arithmetic. Asserted below rather
#: than trusted, because a skip is the one outcome that looks like a pass.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
assert os.path.isfile(os.path.join(REPO, "CLAUDE.md")), REPO
SCAN = os.path.join(
    REPO, "library/editions/beethoven/symphony-5-op67/"
          "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
          "imslp984073.pdf")
RENDER = os.path.join(
    REPO, "benchmarks/omr-staged-engraved-2026-09/out/fixture/"
          "beethoven-sym5-mvt1-m1-24.pdf")

STAFF = R.staff(0, 0, 0)


def _blank_pdf(path: str) -> str:
    """A page with neither a raster nor drawings -- the abstaining case."""
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


class _FlagCase(unittest.TestCase):
    FLAGS = (G.DOCUMENT_IDENTITY_ENV, H.ENGRAVED_KEYSIG_ENV)

    def setUp(self) -> None:
        self._old = {f: os.environ.get(f) for f in self.FLAGS}

    def tearDown(self) -> None:
        for f, v in self._old.items():
            if v is None:
                os.environ.pop(f, None)
            else:
                os.environ[f] = v


# ─────────────────────────────────────────────────────────────────────────────
# GATHER
# ─────────────────────────────────────────────────────────────────────────────

class TestTheContainerIsRead(_FlagCase):

    def test_a_library_scan_measures_SCANNED(self):
        if not os.path.isfile(SCAN):
            self.skipTest("score library not present on this machine")
        log = Log()
        G.gather_input_domain(log, SCAN, [0, 1, 2])
        rows = log.rows(Q.INPUT_DOMAIN, DOCUMENT)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].value, "scanned")
        self.assertEqual(rows[0].reader, READERS.CONTAINER)
        self.assertEqual(rows[0].detail["source_kind"], "container")

    def test_an_engraved_render_measures_ENGRAVED(self):
        if not os.path.isfile(RENDER):
            self.skipTest("engraved fixture not built")
        log = Log()
        G.gather_input_domain(log, RENDER, [0, 1, 2])
        rows = log.rows(Q.INPUT_DOMAIN, DOCUMENT)
        self.assertEqual([r.value for r in rows], ["engraved"])
        # the evidence travels with the verdict, so a later reader can check it
        self.assertEqual(rows[0].detail["max_raster_coverage"], 0.0)
        self.assertGreater(rows[0].detail["max_drawings"], 50)

    def test_the_catalog_is_SILENT_where_the_container_ANSWERS(self):
        """⚠️⚠️ THE WHOLE REASON THESE ARE TWO QUANTITIES, in one assertion."""
        if not os.path.isfile(RENDER):
            self.skipTest("engraved fixture not built")
        log = Log()
        G.gather_document_identity(log, RENDER)
        G.gather_input_domain(log, RENDER, [0, 1, 2])
        self.assertEqual(log.rows(Q.DOCUMENT_IDENTITY, DOCUMENT), ())
        self.assertEqual(
            [a.reason for a in log.refusals(Q.DOCUMENT_IDENTITY, DOCUMENT)],
            [ABSTAIN.NOT_IN_CATALOG])
        self.assertEqual(
            [r.value for r in log.rows(Q.INPUT_DOMAIN, DOCUMENT)], ["engraved"])

    def test_a_page_with_no_ink_source_ABSTAINS_and_does_not_default(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            log = Log()
            G.gather_input_domain(log, _blank_pdf(os.path.join(d, "b.pdf")))
        self.assertEqual(log.rows(Q.INPUT_DOMAIN, DOCUMENT), ())
        self.assertEqual(
            [a.reason for a in log.refusals(Q.INPUT_DOMAIN, DOCUMENT)],
            [ABSTAIN.NO_DOMAIN_SIGNAL])

    def test_no_pdf_path_is_OUT_OF_SCOPE_not_a_domain(self):
        log = Log()
        G.gather_input_domain(log, None)
        self.assertEqual(
            [a.reason for a in log.refusals(Q.INPUT_DOMAIN, DOCUMENT)],
            [ABSTAIN.OUT_OF_SCOPE])

    def test_flag_OFF_writes_NOTHING_AT_ALL(self):
        """Not an abstention: flag-off must be byte-identical to a tree with
        no rung, or the rung perturbs every A/B in the repo by existing."""
        os.environ[G.DOCUMENT_IDENTITY_ENV] = "0"
        log = Log()
        G.gather_input_domain(log, RENDER, [0])
        self.assertEqual(len(log._obs) + len(log._abs), 0)

    def test_it_files_ONCE_PER_DOCUMENT_including_when_it_ABSTAINS(self):
        """⚠️ BOTH ROW TYPES. `rows()` does not return abstentions, so a guard
        asking only for observations lets four of them through on a 4-page
        run -- the ABSENT/DECLINED distinction biting the guard written to
        respect it."""
        log = Log()
        for _ in range(4):                      # a four-page run
            G.gather_input_domain(log, None)    # the ABSTAINING path
        self.assertEqual(len(log.refusals(Q.INPUT_DOMAIN, DOCUMENT)), 1)
        log2 = Log()
        if os.path.isfile(RENDER):
            for _ in range(4):
                G.gather_input_domain(log2, RENDER, [0])
            self.assertEqual(len(log2.rows(Q.INPUT_DOMAIN, DOCUMENT)), 1)

    def test_unnameable_pages_fall_back_to_the_DEFAULT_not_to_an_EMPTY_LIST(self):
        """⚠️ An empty `page_indices` classifies NOTHING and returns `unknown`
        -- a clean, believable abstention meaning *this document has no
        domain* when it means *we could not name its pages*."""
        self.assertIsNone(G._run_page_indices([]))
        self.assertIsNone(G._run_page_indices([(object(), [])]))

        class _P:
            page_index = 2

        class _PWS:
            page = _P()
        self.assertEqual(G._run_page_indices([(_PWS(), [])]), [2])


class TestTheCatalogRowCarriesWhatSeanAskedFor(unittest.TestCase):

    def test_the_year_the_plate_and_the_text_layer_are_filed(self):
        if not os.path.isfile(SCAN):
            self.skipTest("score library not present on this machine")
        log = Log()
        G.gather_document_identity(log, SCAN)
        d = log.rows(Q.DOCUMENT_IDENTITY, DOCUMENT)[0].detail
        self.assertEqual(d["publisher_year"], "1870")
        self.assertEqual(d["plate"], "2769")
        self.assertIn("has_text_layer", d)
        # ⚠️ IMSLP's LABEL IS STILL FILED, beside the measurement and never
        # instead of it: two witnesses, and a disagreement is a fact.
        self.assertEqual(d["image_type"], "Normal Scan")

    def test_the_two_catalog_LOOKUPS_cannot_drift_apart(self):
        """⚠️ `edition_facts` (by path) and `edition_for_pdf` (by basename)
        each hand-listed the same field tuple, so a field added for one
        reached the other only if somebody remembered."""
        from tools.omr.positional_store import edition_facts, edition_for_pdf
        if not os.path.isfile(SCAN):
            self.skipTest("score library not present on this machine")
        by_name = edition_for_pdf(SCAN)
        self.assertTrue(by_name)
        self.assertEqual(edition_facts(by_name["path"]), by_name)


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE — the one-sided consumer
# ─────────────────────────────────────────────────────────────────────────────

def _contested(log: Log, domain: str | None) -> None:
    """A staff where BOTH readers answer and they DISAGREE.

    The shipped precedence takes the locator's -1; the engraved tier takes the
    template's -3. That is the real shape on the fixture: every wrong verdict
    there is `-1` where `-3` is printed.
    """
    log.observe(STAFF, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                frame="cell:0", score=0.95)
    log.observe(STAFF, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                frame="header_window", n_accidentals=1, fifths=-1)
    log.observe(STAFF, Q.KEYSIG_TEMPLATE_FIT, "treble", reader=READERS.TEMPLATE,
                frame="header_window", n_accidentals=3, fifths=-3)
    if domain is not None:
        log.observe(DOCUMENT, Q.INPUT_DOMAIN, domain,
                    reader=READERS.CONTAINER, frame="page",
                    tier="container", source_kind="container")


class TestTheEngravedTier(_FlagCase):

    def _verdict(self, domain, flag):
        os.environ[H.ENGRAVED_KEYSIG_ENV] = flag
        log = Log()
        _contested(log, domain)
        adjudicate.run(log)
        return log.verdict(Q.KEY_SIGNATURE, STAFF)

    def test_ENGRAVED_and_flag_ON_takes_the_TEMPLATE(self):
        v = self._verdict("engraved", "1")
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "fitted_by_template_engraved")

    def test_a_SCAN_is_UNCHANGED(self):
        v = self._verdict("scanned", "1")
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "fitted")

    def test_NO_IDENTITY_ROW_is_UNCHANGED(self):
        """A record gathered before this rung existed, or a PDF the
        classifier abstained on."""
        v = self._verdict(None, "1")
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "fitted")

    def test_the_FLAG_OFF_is_UNCHANGED_even_on_engraved_input(self):
        v = self._verdict("engraved", "0")
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "fitted")

    def test_the_gaps_only_tier_still_answers_where_the_locator_is_SILENT(self):
        """⚠️ The shipped behaviour this change must not disturb: with no
        locator fit the template answers under its OWN reason, on any
        domain."""
        for domain, flag in (("scanned", "1"), ("engraved", "0"), (None, "1")):
            os.environ[H.ENGRAVED_KEYSIG_ENV] = flag
            log = Log()
            log.observe(STAFF, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                        frame="cell:0", score=0.95)
            log.observe(STAFF, Q.KEYSIG_TEMPLATE_FIT, "treble",
                        reader=READERS.TEMPLATE, frame="header_window",
                        n_accidentals=3, fifths=-3)
            if domain:
                log.observe(DOCUMENT, Q.INPUT_DOMAIN, domain,
                            reader=READERS.CONTAINER, frame="page")
            adjudicate.run(log)
            v = log.verdict(Q.KEY_SIGNATURE, STAFF)
            self.assertEqual((v.value, v.reason), (-3, "fitted_by_template"),
                             f"{domain}/{flag}")

    def test_an_engraved_row_with_NO_TEMPLATE_FIT_falls_through(self):
        os.environ[H.ENGRAVED_KEYSIG_ENV] = "1"
        log = Log()
        log.observe(STAFF, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        log.observe(STAFF, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=1, fifths=-1)
        log.observe(DOCUMENT, Q.INPUT_DOMAIN, "engraved",
                    reader=READERS.CONTAINER, frame="page")
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, STAFF)
        self.assertEqual((v.value, v.reason), (-1, "fitted"))

    def test_a_template_fit_for_ANOTHER_CLEF_is_not_taken_on_engraved_input(self):
        os.environ[H.ENGRAVED_KEYSIG_ENV] = "1"
        log = Log()
        log.observe(STAFF, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        log.observe(STAFF, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=1, fifths=-1)
        log.observe(STAFF, Q.KEYSIG_TEMPLATE_FIT, "bass",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, fifths=-3)
        log.observe(DOCUMENT, Q.INPUT_DOMAIN, "engraved",
                    reader=READERS.CONTAINER, frame="page")
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, STAFF)
        self.assertEqual((v.value, v.reason), (-1, "fitted"))


class TestTheDocumentRowIsReachableFromAStaff(_FlagCase):
    """⚠️⚠️ `Q.INPUT_DOMAIN` IS FILED ON THE **DOCUMENT** AND THIS DECISION IS
    `Kind.STAFF`. A bare `ev.rows(...)` at the default EXACT scope returns
    nothing on every page forever and fails SILENT -- reading exactly like an
    honest document with no identity. `adjudicate_instrument` records the same
    fault against `Q.ROSTER_ENTRY` in the same words."""

    def test_the_default_EXACT_scope_would_have_found_NOTHING(self):
        log = Log()
        _contested(log, "engraved")
        from tools.omr.staged.adjudicate import REGISTRY, Evidence
        from tools.omr.staged.record import Scope
        # the SHIPPED spec, so `wants` is the real declaration and this
        # cannot pass by asking with a permissive stand-in
        spec = REGISTRY[Q.KEY_SIGNATURE]
        ev = Evidence(log, STAFF, spec)
        self.assertEqual(ev.rows(Q.INPUT_DOMAIN), ())
        self.assertEqual(
            [r.value for r in ev.rows(Q.INPUT_DOMAIN,
                                      scope=Scope.SELF_AND_ANCESTORS)],
            ["engraved"])


class TestTheFlagDirection(_FlagCase):

    def test_the_consumer_flag_is_default_ON_and_a_DENY_list(self):
        # ⚠️⚠️ FLIPPED 2026-09-22 (evening) ON SEAN'S CALL, and the test's
        # DIRECTION flipped with it rather than being deleted. CLAUDE.md's
        # "A flag's OFF test must follow its DEFAULT", under which five
        # shipped flags had it backwards: a default-ON mechanism must be a
        # DENY-list, so an empty value or a typo leaves it ON rather than
        # silently restoring the precedence the measurement replaced.
        for word, on in (("0", False), ("", False), ("off", False),
                         ("false", False), ("no", False),
                         ("1", True), ("true", True), ("on", True),
                         ("yess", True), ("ON!", True)):
            os.environ[H.ENGRAVED_KEYSIG_ENV] = word
            self.assertEqual(H._engraved_keysig_enabled(), on, word)
        os.environ.pop(H.ENGRAVED_KEYSIG_ENV, None)
        self.assertTrue(H._engraved_keysig_enabled())


if __name__ == "__main__":
    unittest.main()
