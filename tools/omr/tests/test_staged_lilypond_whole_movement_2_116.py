"""ROADMAP 2.116. MACHINE-LOCAL whole-movement guard: the STAGED LilyPond
export of the 2026-10-13 overnight records (`library/_shared-records`,
gitignored) is balanced and LilyPond compiles it. A record is absent on a
cloud checkout, so this SKIPS there -- a skip, never a pass.

It failed before 2.116: `lilypond.to_lilypond`'s equality lacked the
unboxed-rest term `to_musicxml` carries (125 on Litolff, 450 on Brahms)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pytest

LIB = Path(os.environ.get("REENGRAVE_LIBRARY_DIR")
           or "/Users/seanjohnson/Desktop/ReEngrave/library") / "_shared-records"
RECORDS = {
    "beethoven5-litolff": (LIB / "beethoven5-litolff-mvt1-whole-20261020-night.record.json", 125),
    "brahms1-breitkopf": (LIB / "brahms1-breitkopf-mvt1-whole-20261020-night.record.json", 450),
}


@pytest.mark.slow
class TestWholeMovementLilypond(unittest.TestCase):
    def _export(self, name):
        path, _ = RECORDS[name]
        if not path.exists():
            self.skipTest(f"{path} is not on this machine")
        from tools.omr.staged import lilypond as LY
        from tools.omr.staged.record_io import load_record
        return LY.to_lilypond(load_record(str(path)))

    def _check(self, name):
        text, rep = self._export(name)
        bal = rep["balance"]
        self.assertTrue(bal["balanced"], bal)
        self.assertEqual(bal["unboxed_rests_placed"], RECORDS[name][1])
        self.assertEqual(
            bal["events_in_log"] + bal["unboxed_rests_placed"],
            bal["events_written"] + bal["events_not_written"])
        return text

    def test_litolff_balanced(self):
        self._check("beethoven5-litolff")

    def test_brahms_balanced(self):
        self._check("brahms1-breitkopf")

    def test_litolff_compiles(self):
        if not shutil.which("lilypond"):
            self.skipTest("lilypond is not installed")
        text = self._check("beethoven5-litolff")
        with tempfile.TemporaryDirectory() as d:
            ly = Path(d) / "m.ly"
            ly.write_text(text)
            r = subprocess.run(["lilypond", "-o", str(Path(d) / "m"), str(ly)],
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stderr[-500:])
            self.assertTrue((Path(d) / "m.pdf").exists())


if __name__ == "__main__":
    unittest.main()
