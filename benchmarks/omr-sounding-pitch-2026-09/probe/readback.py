"""Read both arms back with music21 and ask whether the alterations are RIGHT.

⚠️ PARSING IS NOT THE CHECK. "music21 reads the file" would pass on a file
whose every note moved the wrong way. So this asks three things the element
counts cannot:

  1. the note SEQUENCE is unchanged (same count, same order, same letters and
     octaves) -- an alteration must not add, drop or re-letter a note;
  2. every note whose MIDI moved, moved by exactly ONE semitone, and
  3. it moved in the direction that part's OWN key signature names, and its
     letter is one the key actually alters.

(3) is the one that can fail for a correct-looking file: an exporter that
folded the alteration in with the wrong sign would pass (1) and (2).

Run:
  .venv-omrned/bin/python benchmarks/omr-sounding-pitch-2026-09/probe/readback.py \\
      out/beet5-before.musicxml out/beet5-after.musicxml
"""
from __future__ import annotations

import collections
import sys

SHARPS = ("F", "C", "G", "D", "A", "E", "B")


def altered_letters(fifths: int):
    if fifths > 0:
        return set(SHARPS[:fifths]), +1
    if fifths < 0:
        return set(tuple(reversed(SHARPS))[:abs(fifths)]), -1
    return set(), 0


def read(path):
    """Every note, with the key signature IN FORCE where it stands.

    ⚠️⚠️ THE FIRST VERSION TOOK THE PART'S *FIRST* KEY SIGNATURE AND REPORTED
    19 FALSE FAULTS. The staged exporter writes a key per STAFF-RUN, and a
    part spans several systems whose key readings can differ -- measured on
    this artefact, 5 of 12 parts carry more than one, and part 8 goes -3 then
    +1. Judging a note in the second half of a part against the first half's
    key is the frame error this repo keeps paying for, arriving in a probe.
    A key is a fact about a RANGE OF BARS, so it is tracked as one.
    """
    import music21
    s = music21.converter.parse(path)
    out = []
    for pi, part in enumerate(s.parts):
        ks = None
        for m in part.getElementsByClass("Measure"):
            for e in m.recurse().getElementsByClass("KeySignature"):
                ks = e.sharps
                break
            for n in m.recurse().notes:
                for p in (n.pitches if n.isChord else [n.pitch]):
                    out.append((pi, ks, p.step, p.octave, p.midi))
    return out


def main(before_path, after_path):
    b, a = read(before_path), read(after_path)
    fails = []

    print(f"  notes parsed: before {len(b)}  after {len(a)}")
    if len(b) != len(a):
        fails.append("note COUNT changed")

    # (1) sequence: letter+octave must be untouched
    seq_b = [(p, st, oc) for p, _k, st, oc, _m in b]
    seq_a = [(p, st, oc) for p, _k, st, oc, _m in a]
    print(f"  letter+octave sequence identical: {seq_b == seq_a}")
    if seq_b != seq_a:
        fails.append("letter/octave sequence changed")

    # ⚠️⚠️ THE DELTA CHECK IS DEAD UNDER music21 AND THAT IS THE FINDING, NOT
    # A BUG IN THIS PROBE. music21 INFERS the alteration from `<accidental>`,
    # so it reads the BEFORE file -- which carries a drawn flat and no
    # `<alter>` -- as already sounding E-flat, and the two arms come out
    # identical in MIDI. Verovio does NOT: on the same two files it reports
    # `accid.ges` 0 before and 221 after. So the two readers DISAGREE about
    # what the before-file sounds like, which is a stronger reason to repair
    # it than either reader alone -- a file whose meaning depends on the
    # consumer's leniency is a file that is wrong. The delta is therefore
    # reported, and NOT asserted on.
    moved = [(x, y) for x, y in zip(b, a) if x[4] != y[4]]
    deltas = collections.Counter(y[4] - x[4] for x, y in moved)
    print(f"  notes whose music21 MIDI moved: {len(moved)}  deltas {dict(deltas)}")
    print("    (0 is EXPECTED: music21 reads <accidental> as an alteration.")
    print("     Verovio, which does not, is the sounding oracle -- see")
    print("     probe/renderer_semantics.py and FINDINGS §3.)")
    if any(abs(d) != 1 for d in deltas):
        fails.append("a note moved by something other than one semitone")

    # ⚠️ THE REAL CHECK IS ABSOLUTE, ON THE AFTER FILE. Every note music21
    # reads as altered must carry a letter that part's own key signature
    # alters, in the direction it names. This can fail on a file that passes
    # every count above -- an exporter that folded the alteration in with the
    # wrong SIGN would produce exactly as many <alter> elements.
    checked = bad_dir = bad_letter = 0
    for _pi, ks, step, _oc, midi in a:
        import music21
        nat = music21.pitch.Pitch(f"{step}4").pitchClass
        alt = (midi % 12) - nat
        alt = alt + 12 if alt < -6 else (alt - 12 if alt > 6 else alt)
        if alt == 0:
            continue
        checked += 1
        if ks is None:
            bad_letter += 1
            continue
        letters, sign = altered_letters(ks)
        if step not in letters:
            bad_letter += 1
        elif sign and alt != sign:
            bad_dir += 1
    print(f"  AFTER: notes carrying an alteration: {checked}")
    print(f"    whose LETTER the key does not alter: {bad_letter}")
    print(f"    altered AGAINST the key's direction: {bad_dir}")
    if bad_letter:
        fails.append(f"{bad_letter} altered a letter the key does not")
    if bad_dir:
        fails.append(f"{bad_dir} altered the wrong way")
    # positive control: an absolute check over zero altered notes proves
    # nothing at all.
    if not checked:
        fails.append("DEAD: no note in the AFTER file is altered")

    print()
    if fails:
        print("  FAILED:", "; ".join(fails))
        return 1
    print("  all checks pass, over a non-empty population (positive control).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
