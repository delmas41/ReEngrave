"""Generate scores whose contents are known exactly, and render them to PDF.

The point of these is to measure whether the pipeline gets the NOTES right —
which nothing in this repo has ever measured. Every existing quality number is
symbol-level on hand-labeled cells (the F1 98.8% figure), or coverage rather
than accuracy: `benchmarks/omr-real-world` reports "100% pitch coverage",
meaning every detected notehead was assigned a pitch, not that the pitch is
correct.

The truth here costs nothing to obtain because we author it. music21 writes the
MusicXML, `musicxml2ly` and LilyPond render it to PDF, and the pipeline is then
asked to recover what we started with.

Three layouts, chosen to match the material the corpus actually contains:

  melody       one staff, quarter and half notes        — the simplest case
  keyboard     two staves braced, independent hands     — WTC, Handel reduction
  ensemble     four staves, mixed densities             — Boléro, Mahler, Beet 5

`ensemble` exists because single-staff scores are not merely easier, they are
DIFFERENT: barline detection votes across staves, so a lone staff has nothing to
corroborate with and its note stems get read as barlines. A benchmark built only
from melodies would report a problem that no real orchestral page has.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from music21 import clef, key, layout, metadata, meter, note, stream


BENCH_DIR = Path("benchmarks/omr-end-to-end")


def _measure(pitches: list[str], quarter_lengths: list[float]) -> stream.Measure:
    m = stream.Measure()
    for name, ql in zip(pitches, quarter_lengths):
        m.append(note.Note(name, quarterLength=ql))
    return m


def _part(the_clef, bars: list[tuple[list[str], list[float]]]) -> stream.Part:
    p = stream.Part()
    for index, (pitches, qls) in enumerate(bars):
        m = _measure(pitches, qls)
        if index == 0:
            # Clef, key and meter go INSIDE the first measure rather than at
            # part level. At part level music21 cannot resolve the meter when
            # beaming measure 1, and that measure silently comes out unbeamed —
            # which quietly removed the beams from the one fixture that has its
            # eighth-note run in the first bar.
            m.insert(0, the_clef)
            m.insert(0, key.KeySignature(0))
            m.insert(0, meter.TimeSignature("4/4"))
        p.append(m)
    p.makeBeams(inPlace=True)
    return p


Q = [1.0, 1.0, 1.0, 1.0]
H = [2.0, 2.0]
E = [0.5] * 8


def build_melody() -> stream.Score:
    s = stream.Score()
    s.insert(0, _part(clef.TrebleClef(), [
        (["C4", "D4", "E4", "F4"], Q),
        (["G4", "A4", "B4", "C5"], Q),
        (["C5", "B4", "A4", "G4"], Q),
        (["F4", "E4"], H),
        (["D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5"], E),
        (["C5", "G4"], H),
    ]))
    return s


def build_keyboard() -> stream.Score:
    s = stream.Score()
    right = _part(clef.TrebleClef(), [
        (["E5", "D5", "C5", "B4"], Q),
        (["C5", "D5", "E5", "F5", "G5", "F5", "E5", "D5"], E),
        (["C5", "E5"], H),
        (["G4", "A4", "B4", "C5"], Q),
    ])
    left = _part(clef.BassClef(), [
        (["C3", "G3"], H),
        (["C3", "E3", "G3", "E3"], Q),
        (["C3"], [4.0]),
        (["G2", "G3"], H),
    ])
    s.insert(0, right)
    s.insert(0, left)
    s.insert(0, layout.StaffGroup([right, left], symbol="brace", barTogether=True))
    return s


def build_ensemble() -> stream.Score:
    """Four staves at different densities, the way an orchestral page is set."""
    s = stream.Score()
    parts = [
        _part(clef.TrebleClef(), [          # busy top line
            (["G5", "F5", "E5", "D5", "C5", "D5", "E5", "F5"], E),
            (["E5", "D5", "C5", "B4"], Q),
            (["C5", "G4"], H),
            (["A4", "B4", "C5", "D5"], Q),
        ]),
        _part(clef.TrebleClef(), [          # moderate
            (["C5", "B4", "A4", "G4"], Q),
            (["A4", "C5"], H),
            (["E4", "F4", "G4", "A4"], Q),
            (["G4"], [4.0]),
        ]),
        _part(clef.AltoClef(), [            # sparse, and a C clef on purpose
            (["C4", "E4"], H),
            (["G4"], [4.0]),
            (["F4", "E4", "D4", "C4"], Q),
            (["E4"], [4.0]),
        ]),
        _part(clef.BassClef(), [            # bass, long notes
            (["C3"], [4.0]),
            (["G2", "C3"], H),
            (["C3", "D3", "E3", "F3"], Q),
            (["G3"], [4.0]),
        ]),
    ]
    for p in parts:
        s.insert(0, p)
    return s


FIXTURES = {
    "melody": build_melody,
    "keyboard": build_keyboard,
    "ensemble": build_ensemble,
}


def render(name: str, out_dir: Path, staff_size: int = 20) -> tuple[Path, Path]:
    """Write `<name>.musicxml` (the truth) and `<name>.pdf` (the input)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    score = FIXTURES[name]()
    score.metadata = metadata.Metadata(title="", composer="")
    xml = out_dir / f"{name}.musicxml"
    score.write("musicxml", fp=str(xml))

    ly = out_dir / f"{name}.ly"
    subprocess.run(["musicxml2ly", "-o", str(ly), str(xml)],
                   check=True, capture_output=True)
    src = ly.read_text()
    # No tagline, no title block, and a staff size in the range real scans sit
    # at once rasterised.
    src = src.replace("\\header {", "\\header {\n  tagline = ##f")
    src = f"#(set-global-staff-size {staff_size})\n" + src
    ly.write_text(src)
    subprocess.run(["lilypond", "-s", "-o", name, f"{name}.ly"],
                   cwd=out_dir, check=True, capture_output=True)
    return xml, out_dir / f"{name}.pdf"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=BENCH_DIR / "fixtures")
    args = ap.parse_args()
    for fixture in FIXTURES:
        xml, pdf = render(fixture, args.out_dir)
        print(f"{fixture:10s} -> {xml.name}, {pdf.name} ({pdf.stat().st_size} bytes)")
