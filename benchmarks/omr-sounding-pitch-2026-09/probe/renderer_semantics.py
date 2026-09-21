"""What a RENDERER does with `<alter>`, `<accidental>` and `<beam>`.

⚠️ WHY THIS EXISTS. Two claims stood behind this lane's repair list and
NEITHER had been measured:

  1. "an E-flat exported as <step>E</step> + <accidental>flat</accidental>
     prints right and sounds wrong"
  2. "in MusicXML no beam IS a flag, so every beamed note comes out flagged"

Both are claims about what a CONSUMER does, and this repo's own rule is that a
mechanism must be measured rather than asserted. A renderer is the only thing
that can answer either. So: build minimal files that differ in exactly one
element, put them through Verovio (the renderer this project already ships and
uses in `claude_vision.py`) and through music21, and report what each does.

⚠️⚠️ THE FIRST VERSION OF THIS PROBE MEASURED ITSELF. It scraped glyph names
with `xlink:href="#(\\w+?)-"` and `class="([a-z]+)"`, found NOTHING in any
arm, and duly reported "no accidental drawn" and "no flags" for every input --
a clean, symmetric, completely empty result that reads exactly like a real
negative. Verovio 5.x names glyphs by SMuFL CODEPOINT (`E0A4`), not by name.
So every extractor here now has a POSITIVE CONTROL: it asserts it can find a
glyph it KNOWS is on the page (the notehead, the clef) before it is allowed to
report an absence. `_require` raises rather than returning a quiet zero.

Run:  python3 benchmarks/omr-sounding-pitch-2026-09/probe/renderer_semantics.py
Exits non-zero if any control fails.
"""
from __future__ import annotations

import re
import sys

# SMuFL codepoints Verovio emits as <use xlink:href="#E0A4-xxxx">.
SMUFL = {
    "E050": "gClef",
    "E0A4": "noteheadBlack",
    "E0A2": "noteheadWhole",
    "E240": "flag8thUp",
    "E241": "flag8thDown",
    "E242": "flag16thUp",
    "E243": "flag16thDown",
    "E260": "accidentalFlat",
    "E261": "accidentalNatural",
    "E262": "accidentalSharp",
}
FLAG_CPS = {"E240", "E241", "E242", "E243"}
ACCID_CPS = {"E260", "E261", "E262"}

HDR = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
 "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
 <part-list><score-part id="P1"><part-name>T</part-name></score-part></part-list>
 <part id="P1"><measure number="1">
  <attributes><divisions>4</divisions>
   <key><fifths>{fifths}</fifths></key>
   <time><beats>4</beats><beat-type>4</beat-type></time>
   <clef><sign>G</sign><line>2</line></clef></attributes>
'''
FTR = '  </measure></part></score-partwise>\n'


def note(step, octv, alter=None, accidental=None, typ="eighth", dur=2,
         beams=None):
    out = ["   <note>", "    <pitch>", f"     <step>{step}</step>"]
    if alter is not None:
        out.append(f"     <alter>{alter}</alter>")
    out += [f"     <octave>{octv}</octave>", "    </pitch>",
            f"    <duration>{dur}</duration>", "    <voice>1</voice>",
            f"    <type>{typ}</type>"]
    if accidental:
        out.append(f"    <accidental>{accidental}</accidental>")
    for n, s in sorted((beams or {}).items()):
        out.append(f'    <beam number="{n}">{s}</beam>')
    out.append("   </note>")
    return "\n".join(out) + "\n"


def build(fifths, notes):
    return HDR.format(fifths=fifths) + "".join(notes) + FTR


def render(xml):
    import verovio
    tk = verovio.toolkit()
    tk.setOptions({"adjustPageHeight": True, "breaks": "none"})
    if not tk.loadData(xml):
        raise RuntimeError("verovio refused the file")
    return tk.getMEI(), tk.renderToSVG(1)


def codepoints(svg):
    """Every SMuFL codepoint Verovio drew."""
    return [m.split("-")[0]
            for m in re.findall(r'xlink:href="#([0-9A-F]{4}-[^"]*)"', svg)]


def _require(cond, what):
    if not cond:
        raise SystemExit(f"CONTROL FAILED: the probe cannot see {what}; "
                         f"every 'absent' below would be a fact about this "
                         f"extractor, not about the renderer.")


FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"    [{'ok ' if ok else 'FAIL'}] {label}: {got!r}"
          + ("" if ok else f"  (expected {want!r})"))
    if not ok:
        FAIL.append(label)


def main():
    import music21

    print("=" * 76)
    print("EXPERIMENT 1 — <accidental> without <alter>: what sounds, what draws")
    print("=" * 76)
    # E-flat major (3 flats). An E there SOUNDS E-flat: midi 63 at octave 4.
    today = build(-3, [note("E", 4, alter=None, accidental="flat",
                            typ="quarter", dur=4)])
    fixed = build(-3, [note("E", 4, alter=-1, accidental=None,
                            typ="quarter", dur=4)])
    bare = build(-3, [note("E", 4, alter=None, accidental=None,
                           typ="quarter", dur=4)])

    print("\n  SOUND (music21, MIDI number — E-natural 64, E-flat 63):")
    for label, xml in (("today  (accidental, no alter)", today),
                       ("fixed  (alter, no accidental)", fixed),
                       ("bare   (neither)            ", bare)):
        ns = [(n.nameWithOctave, n.pitch.midi)
              for n in music21.converter.parseData(
                  xml, format="musicxml").recurse().notes]
        print(f"    {label}: {ns}")

    print("\n  DRAW (Verovio SMuFL glyphs):")
    for label, xml in (("today", today), ("fixed", fixed), ("bare ", bare)):
        _, svg = render(xml)
        cps = codepoints(svg)
        _require("E0A2" in cps or "E0A4" in cps, f"a notehead in the {label} arm")
        acc = [SMUFL.get(c, c) for c in cps if c in ACCID_CPS]
        print(f"    {label}: accidental glyphs = {acc or 'none'}")

    print()
    print("=" * 76)
    print("EXPERIMENT 2 — does an ABSENT <beam> produce a FLAG?")
    print("=" * 76)
    with_beam = build(0, [
        note("C", 5, beams={1: "begin"}), note("D", 5, beams={1: "continue"}),
        note("E", 5, beams={1: "continue"}), note("F", 5, beams={1: "end"})])
    no_beam = build(0, [note("C", 5), note("D", 5), note("E", 5), note("F", 5)])

    res = {}
    for label, xml in (("WITH <beam>", with_beam), ("NO <beam>", no_beam)):
        mei, svg = render(xml)
        cps = codepoints(svg)
        _require(cps.count("E0A4") == 4, f"four noteheads in the {label!r} arm")
        flags = [SMUFL.get(c, c) for c in cps if c in FLAG_CPS]
        beamed = svg.count('class="beam"')
        res[label] = (beamed, len(flags))
        print(f"  {label:12}: SVG beams drawn = {beamed}   "
              f"flag glyphs drawn = {len(flags)} {flags}")

    print("\n  music21 beam read-back:")
    for label, xml in (("WITH <beam>", with_beam), ("NO <beam>", no_beam)):
        s = music21.converter.parseData(xml, format="musicxml")
        bs = [len(n.beams.beamsList) for n in s.recurse().notes]
        print(f"    {label:12}: beams per note = {bs}")

    print("\n  VERDICT on the two claims:")
    check("absent <beam> draws flags instead (the dossier's claim)",
          res["NO <beam>"][1] > 0, True)
    check("present <beam> draws a beam",
          res["WITH <beam>"][0] > 0, True)

    print()
    if FAIL:
        print(f"  {len(FAIL)} claim(s) REFUTED: {FAIL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
