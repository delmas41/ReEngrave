"""The domain gate: skip the word reader where the page is PROVABLY a scan.

Measured 2026-09-16 (`benchmarks/omr-surya-staged-cost-2026-09/FINDINGS.md`):
on a scan this reader is the most expensive thing in a staged run -- ~267
s/page, against 93 s/page for the margin-label rungs it shares a model with --
and on Litolff Beethoven 5 p1-4 it bought SIX `<words>`, all of them `cresc.`
in three casings, with the exported file byte-identical once those are removed.

⚠️⚠️ THE RISK IS ENTIRELY ON THE OTHER SIDE, and that is what most of this
file is about. An ENGRAVED page wrongly called a scan loses a reader CLAUDE.md
measures at 144 edits, 18.8% of the pooled engraved figure -- and loses it
silently. So the gate must PROVE a scan rather than fail to prove an
engraving, and `page_is_scanned` is a separate function from
`not page_is_engraved` for exactly that reason.
"""
from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

from tools.omr import direction_text as DT
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q


def _pdf(tmp, name, *, drawings=0, images=(), pages=1):
    """A PDF with a chosen number of vector drawings and image rectangles.

    `images` is a list of coverage fractions of the sheet.
    """
    import fitz
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page(width=600, height=800)
        for i in range(drawings):
            page.draw_line(fitz.Point(10, 10 + i), fitz.Point(20, 20 + i))
        for cover in images:
            side = (cover * 600 * 800) ** 0.5
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 8, 8), False)
            pix.clear_with(255)
            page.insert_image(fitz.Rect(0, 0, side, side), pixmap=pix)
    path = os.path.join(tmp, name)
    doc.save(path)
    doc.close()
    return SimpleNamespace(pdf_path=path, page_index=0)


class TestPageIsScannedProvesItsOwnSide(unittest.TestCase):

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_one_sheet_covering_raster_is_a_scan(self):
        self.assertTrue(DT.page_is_scanned(
            _pdf(self.tmp, "scan.pdf", drawings=0, images=(0.9,))))

    def test_a_TILED_raster_is_a_scan_too(self):
        """The commonest residue, and the case `OMR_WEIGHT_ROUTING` already
        names: a printing cut into strips has no single big image."""
        self.assertTrue(DT.page_is_scanned(
            _pdf(self.tmp, "tiled.pdf", drawings=0,
                 images=(0.2,) * 5 + (0.1,))))

    def test_vector_art_is_NOT_a_scan(self):
        self.assertFalse(DT.page_is_scanned(
            _pdf(self.tmp, "eng.pdf", drawings=500, images=())))

    def test_a_HYBRID_is_not_proved_either_way(self):
        """Raster AND vector art. Neither proof holds, and the ambiguous band
        keeps the reader ON -- which costs money, not evidence."""
        page = _pdf(self.tmp, "hybrid.pdf", drawings=500, images=(0.9,))
        self.assertFalse(DT.page_is_scanned(page))
        self.assertFalse(DT.page_is_engraved(page))

    def test_a_blank_page_is_not_proved_either_way(self):
        page = _pdf(self.tmp, "blank.pdf", drawings=0, images=())
        self.assertFalse(DT.page_is_scanned(page))
        self.assertFalse(DT.page_is_engraved(page))

    def test_no_pdf_path_is_not_a_scan(self):
        self.assertFalse(DT.page_is_scanned(
            SimpleNamespace(pdf_path=None, page_index=0)))

    def test_an_unopenable_file_is_not_a_scan(self):
        self.assertFalse(DT.page_is_scanned(
            SimpleNamespace(pdf_path="/nope/missing.pdf", page_index=0)))

    def test_a_page_index_past_the_end_is_not_a_scan(self):
        page = _pdf(self.tmp, "short.pdf", images=(0.9,))
        page.page_index = 99
        self.assertFalse(DT.page_is_scanned(page))

    def test_THE_TWO_PROOFS_NEVER_BOTH_HOLD(self):
        """⚠️ If they ever did, one of them is wrong, and the gate would be
        skipping a page the other function calls engraved."""
        for name, kw in (("scan", dict(images=(0.9,))),
                         ("tiled", dict(images=(0.2,) * 5)),
                         ("eng", dict(drawings=500)),
                         ("hybrid", dict(drawings=500, images=(0.9,))),
                         ("blank", {})):
            page = _pdf(self.tmp, name + "2.pdf", **kw)
            with self.subTest(name):
                self.assertFalse(DT.page_is_scanned(page)
                                 and DT.page_is_engraved(page))


# ─────────────────────────────────────────────────────────────────────────────
# The gate in GATHER
# ─────────────────────────────────────────────────────────────────────────────


def _cells():
    return [SimpleNamespace(page_index=0, system_index=0, staff_index=0,
                            measure_index=i, bbox_page_px=(0, 0, 10, 10),
                            upscale_factor=2.0) for i in range(2)]


def _pws(page):
    return SimpleNamespace(page=page, staves=[])


class _Env:
    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        self.old = {k: os.environ.get(k) for k in self.kw}
        for k, v in self.kw.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return False


class TestTheGate(unittest.TestCase):

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.scan = _pdf(self.tmp, "s.pdf", images=(0.9,))
        self.eng = _pdf(self.tmp, "e.pdf", drawings=500)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, page, gate):
        log = Log()
        with _Env(OMR_DIRECTION_TEXT_SCAN_GATE=gate, OMR_DIRECTION_TEXT="1"):
            G.gather_direction_words(log, _pws(page), _cells(), {0: (0, 0)}, {})
        return [a for a in log.to_json()["abstentions"]
                if a["quantity"] == Q.DIRECTION_WORD]

    def test_ON_a_proven_scan_is_skipped_as_OUT_OF_SCOPE(self):
        rows = self._run(self.scan, "1")
        self.assertTrue(rows)
        self.assertEqual({r["reason"] for r in rows},
                         {ABSTAIN.OUT_OF_SCOPE})
        self.assertTrue(any(r["detail"].get("gate") == "scan" for r in rows))

    def test_ON_it_is_NOT_reported_as_an_absent_reader(self):
        """⚠️ The rungs are installed and would run; we declined to spend
        them. `READER_UNAVAILABLE` would say this machine cannot read
        directions, which is false."""
        rows = self._run(self.scan, "1")
        self.assertNotIn(ABSTAIN.READER_UNAVAILABLE,
                         {r["reason"] for r in rows})

    def test_ON_an_ENGRAVED_page_is_not_gated(self):
        rows = self._run(self.eng, "1")
        self.assertFalse(any(r["detail"].get("gate") == "scan" for r in rows))

    def test_POSITIVE_CONTROL_off_by_default_the_scan_is_not_gated(self):
        for value in (None, "0"):
            with self.subTest(value=value):
                log = Log()
                with _Env(OMR_DIRECTION_TEXT_SCAN_GATE=value,
                          OMR_DIRECTION_TEXT="1"):
                    G.gather_direction_words(log, _pws(self.scan), _cells(),
                                             {0: (0, 0)}, {})
                rows = [a for a in log.to_json()["abstentions"]
                        if a["quantity"] == Q.DIRECTION_WORD]
                self.assertFalse(any(r["detail"].get("gate") == "scan"
                                     for r in rows))

    def test_the_flag_is_an_ALLOW_list_so_a_typo_leaves_it_OFF(self):
        for typo in ("", "yess", "ON!", "maybe"):
            with self.subTest(typo=typo):
                with _Env(OMR_DIRECTION_TEXT_SCAN_GATE=typo):
                    self.assertFalse(G._scan_gate_enabled())
        for on in ("1", "true", "yes", "on", "ON", " on "):
            with self.subTest(on=on):
                with _Env(OMR_DIRECTION_TEXT_SCAN_GATE=on):
                    self.assertTrue(G._scan_gate_enabled())


if __name__ == "__main__":
    unittest.main()
