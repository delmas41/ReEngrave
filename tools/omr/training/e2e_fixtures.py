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

from music21 import clef, key, layout, metadata, meter, note, spanner, stream


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


def _slur_bars(part: stream.Part, spans: list[tuple[int, int, int, int]]) -> None:
    """Slur `(bar, note) -> (bar, note)` for each span, 0-indexed, in place."""
    bars = list(part.getElementsByClass(stream.Measure))
    for b0, n0, b1, n1 in spans:
        start = list(bars[b0].notes)[n0]     # n = -1 means the bar's last note
        stop = list(bars[b1].notes)[n1]
        part.insert(0, spanner.Slur([start, stop]))


def build_systems() -> stream.Score:
    """Four staves over EIGHT bars, so the page carries TWO systems.

    Every other fixture here is one system, which is the whole reason this one
    exists: a part is the same staff on every system, and a slur is allowed to
    run from the last bar of one system into the first bar of the next. Nothing
    in the corpus measured that, because `orchestral_eval` keeps its excerpts to
    a single page AND a conductor's page of 18-38 staves holds exactly one
    system. So the case was invisible rather than rare.

    Four staves rather than one on purpose. A single staff makes "is this two
    systems or one system of two staves" genuinely ambiguous — the question
    `staff_detector` has to answer by connectivity — and a fixture should not
    rest on the answer being right. Four staves per system, twice, is
    unambiguous.

    ⚠️ SLURS ARE KEPT SPARSE, AND THE NOTES THEY JOIN ARE LONG. The first cut of
    this fixture slurred every barline of the top part, so that a slur crossed
    the break wherever LilyPond put it. That made the fixture measure something
    else: with an arc over every barline the bars stopped summing to four
    (6.00, 5.00, 6.00, 2.00 against a truth of 4.00 everywhere), because
    `line_detection` reads a beam as ink that stems run into and a slur drawn
    between two noteheads looks like one — the hazard
    `test_line_detection_beams` already names. A slur whose notes are misread is
    charged as a wrong slur by musicdiff, which prices a slur by the DURATION it
    spans, so the confound lands squarely on the thing under test.

    So the notes on either side of the break are HALF notes: unbeamable by
    construction, and unambiguous to read. The break is expected after bar 4 —
    `SYSTEM_COUNT` asks LilyPond for two systems and eight equal bars split
    evenly — and the harness should CHECK that rather than assume it.
    """
    s = stream.Score()
    parts = [
        _part(clef.TrebleClef(), [
            (["G4", "A4", "B4", "C5"], Q),
            (["D5", "C5"], H),
            (["G4", "A4", "B4", "C5"], Q),
            (["D5", "E5"], H),              # bar 4 ends on a half note
            (["F5", "E5"], H),              # bar 5 opens on a half note
            (["B4", "A4", "G4", "F4"], Q),
            (["E4", "F4"], H),
            (["G4"], [4.0]),
        ]),
        _part(clef.TrebleClef(), [
            (["C4", "D4", "E4", "F4"], Q),
            (["G4", "F4"], H),
            (["E4", "F4", "G4", "A4"], Q),
            (["B4", "C5"], H),              # bar 4 ends on a half note
            (["D5", "C5"], H),              # bar 5 opens on a half note
            (["G4", "F4"], H),
            (["E4", "D4", "C4", "D4"], Q),
            (["E4"], [4.0]),
        ]),
        _part(clef.AltoClef(), [
            (["C4", "E4"], H),
            (["G4"], [4.0]),
            (["F4", "E4", "D4", "C4"], Q),
            (["E4", "G4"], H),
            (["A4"], [4.0]),
            (["G4", "F4", "E4", "D4"], Q),
            (["C4", "E4"], H),
            (["C4"], [4.0]),
        ]),
        _part(clef.BassClef(), [
            (["C3"], [4.0]),
            (["G2", "C3"], H),
            (["C3", "D3", "E3", "F3"], Q),
            (["G3"], [4.0]),
            (["F3", "E3"], H),
            (["G2"], [4.0]),
            (["C3", "G3"], H),
            (["C3"], [4.0]),
        ]),
    ]
    # Bar 4 is the last of system 1 and bar 5 the first of system 2, so a
    # (3, last) -> (4, 0) span is the case under test. Two parts carry one, so
    # a single detection failure does not empty the measurement; the viola
    # carries only an ordinary across-barline slur and the bass only a
    # within-bar one, so a rule that over-merges at the break shows up as a
    # slur those parts should not have.
    _slur_bars(parts[0], [(0, 0, 0, 3), (3, -1, 4, 0)])
    _slur_bars(parts[1], [(2, 3, 3, 0), (3, -1, 4, 0)])
    _slur_bars(parts[2], [(2, 0, 2, 3), (5, 0, 5, 3)])
    _slur_bars(parts[3], [(2, 0, 2, 3)])
    for p in parts:
        s.insert(0, p)
    # A BRACKET WITH BARLINES RUN THROUGH IT, because that is how an ensemble
    # score is set and because system grouping depends on it: `staff_detector`
    # decides what belongs to one system by CONNECTIVITY — a column of ink
    # through the gap vetoes a break — and without a StaffGroup LilyPond draws
    # each staff its own barlines that stop at its own five lines. Rendered
    # without this the second system came back as four one-staff systems, and
    # `_stitch_slots` refuses to join systems of unequal size, so the stitched
    # path never engaged and the fixture tested nothing.
    s.insert(0, layout.StaffGroup(parts, symbol="bracket", barTogether=True))
    return s


FIXTURES = {
    "melody": build_melody,
    "keyboard": build_keyboard,
    "ensemble": build_ensemble,
    "systems": build_systems,
}

# Fixtures that must occupy a known number of SYSTEMS. `musicxml2ly` emits no
# `|` separators, so a `\break` cannot be placed by counting barlines in its
# output; `system-count` asks LilyPond for the layout directly and lets it pick
# the break, which is why the slurs above do not depend on where that is.
SYSTEM_COUNT = {"systems": 2}


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
    n_systems = SYSTEM_COUNT.get(name)
    if n_systems is not None:
        src = src.replace("\\paper {", f"\\paper {{\n  system-count = #{n_systems}", 1) \
            if "\\paper {" in src else (
                f"\\paper {{ system-count = #{n_systems} }}\n" + src)
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
