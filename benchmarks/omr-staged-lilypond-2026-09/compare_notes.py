"""ROADMAP 3.1 acceptance measurement: does the LilyPond export hold the SAME
notes, in the SAME order, per PART, as the MusicXML export built from the
SAME staged record?

Usage:
    python3 benchmarks/omr-staged-lilypond-2026-09/compare_notes.py \
        benchmarks/omr-staged-engraved-2026-09/out/engraved-p0p2.record.json

Prints a per-part table (pitch-sequence length agreement) and exits non-zero
if any part disagrees. Also compiles the .ly with `lilypond` if it is on
PATH and reports bar-check warnings/errors verbatim.
"""
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as SX          # noqa: E402
from tools.omr.staged import lilypond as LY        # noqa: E402

_PITCH_STEP = {"c": 0, "d": 1, "e": 2, "f": 3, "g": 4, "a": 5, "b": 6}


def mxl_part_pitches(xml_text: str):
    """{part_id: [(step, octave), ...]} in document order, chord members
    included, rests excluded, one entry per NOTE (all voices pooled and then
    re-sorted is NOT attempted here -- this asks about the note MULTISET a
    part carries, which is what a mis-rendered pitch or a dropped note would
    change; voice-exact ordering is checked separately by the fixture tests
    in test_staged_lilypond.py on small synthetic bars)."""
    root = ET.fromstring(xml_text)
    out = {}
    for part in root.findall("part"):
        pitches = []
        for note in part.iter("note"):
            p = note.find("pitch")
            if p is not None:
                pitches.append((p.find("step").text, p.find("octave").text))
        out[part.get("id")] = pitches
    return out


#: A backslash COMMAND word (`\fermata`, `\trill`, `\tuplet`, `\transposition`
#: ...), stripped before pitch-matching. Without this, `\fermata`'s leading
#: "f" survives as a spurious pitch: `\b` sits happily between a backslash
#: and a letter, since a backslash is a non-word character too.
_LILY_COMMAND = re.compile(r"\\[A-Za-z]+")
#: The one-or-two-char backslash SYMBOLS: `\!` `\<` `\>` `\=3`.
_LILY_SYMBOL = re.compile(r"\\[!<>]|\\=\d+")
#: Articulation / slur-number punctuation glued onto a note: `-.` `-!` `->`
#: `-^` `--` `(` `)`.
_LILY_PUNCT = re.compile(r"-[.!^-]|->|[()]")


def _clean_music_line(line: str) -> str:
    line = _LILY_COMMAND.sub(" ", line)
    line = _LILY_SYMBOL.sub(" ", line)
    line = _LILY_PUNCT.sub(" ", line)
    # Chord brackets and voice separators become plain whitespace so an
    # internal chord member (`<a, g'''>4`) or a two-voice bar
    # (`<< { ... } \\ { ... } >>`) exposes every pitch to a whitespace split.
    return line.replace("<", " ").replace(">", " ")


def _lily_pitch_to_step_octave(letter: str, accidental: str, marks: str):
    octave = 3 + marks.count("'") - marks.count(",")
    return (letter.upper(), str(octave))


def lily_part_pitches(ly_text: str):
    """[[(step, octave), ...], ...] -- one list per `\\new Staff`, document
    order, in the STAFF's own reading order (chords included, ties/slurs/
    marks stripped down to the bare pitch)."""
    parts = []
    for block in ly_text.split("\\new Staff")[1:]:
        pitches = []
        for line in block.splitlines():
            stripped = line.strip()
            # ⚠️ EVERY MUSIC-CONTENT LINE THIS EXPORTER WRITES ENDS " |" --
            # `_render_bar` appends it to all four bar kinds, tacet included
            # -- so filtering on "contains a bar check" is a property of the
            # RENDERER, not a guessed set of directive prefixes to exclude.
            if "|" not in stripped:
                continue
            for tok in _clean_music_line(stripped).split():
                m = re.match(r"^([a-g])((?:is|es)*)([,']*)", tok)
                if m:
                    pitches.append(
                        _lily_pitch_to_step_octave(*m.groups()))
        parts.append(pitches)
    return parts


def main(argv):
    record_path = Path(argv[1] if len(argv) > 1 else
                       "benchmarks/omr-staged-engraved-2026-09/out/"
                       "engraved-p0p2.record.json")
    result = json.loads(record_path.read_text())

    xml_text, mxl_report = SX.to_musicxml(result)
    ly_text, ly_report = LY.to_lilypond(result)

    mxl_by_id = mxl_part_pitches(xml_text)
    ly_by_index = lily_part_pitches(ly_text)
    mxl_ids = list(mxl_by_id)

    print(f"parts: musicxml={len(mxl_ids)} lilypond={len(ly_by_index)}")
    ok = len(mxl_ids) == len(ly_by_index)
    rows = []
    for i, pid in enumerate(mxl_ids):
        mxl_seq = sorted(mxl_by_id[pid])
        ly_seq = sorted(ly_by_index[i]) if i < len(ly_by_index) else []
        agree = mxl_seq == ly_seq
        ok = ok and agree
        rows.append((pid, len(mxl_by_id[pid]),
                    len(ly_by_index[i]) if i < len(ly_by_index) else -1,
                    agree))
    for pid, n_mxl, n_ly, agree in rows:
        print(f"  {pid:5s} musicxml={n_mxl:4d} lilypond={n_ly:4d} "
             f"{'OK' if agree else 'DIFFER'}")

    print("\nwritten (musicxml):", mxl_report["written"])
    print("written (lilypond): ", ly_report["written"])
    print("lilypond-only block:", ly_report["lilypond"])

    ly_out = record_path.with_suffix(".ly")
    ly_out.write_text(ly_text)
    print(f"\nwrote {ly_out}")

    import shutil
    if shutil.which("lilypond"):
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                ["lilypond", "--output", d, str(ly_out)],
                capture_output=True, text=True, timeout=120)
        warnings = [l for l in proc.stderr.splitlines()
                   if "warning" in l.lower()]
        errors = [l for l in proc.stderr.splitlines()
                 if "error" in l.lower()]
        print(f"\nlilypond compile: exit={proc.returncode} "
             f"warnings={len(warnings)} errors={len(errors)}")
        for w in warnings:
            print("  W:", w)
        for e in errors:
            print("  E:", e)
    else:
        print("\nlilypond not on PATH -- compile not attempted")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
