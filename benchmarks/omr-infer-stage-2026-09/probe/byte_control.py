"""The control for a DURATION change — and the obvious one is WRONG.

⚠️⚠️ "STRIP THE ELEMENTS AND COMPARE THE REST" DOES NOT WORK HERE, and saying
why is the point. That control fits a change that ADDS a kind of element
(`<slur>`, `<wedge>`): remove them and the rest must be byte-identical. INFER
collapses a NARROWED duration, and a note whose duration was narrowed **was
not written at all** — the exporter refuses to argmax — so the arms differ by
whole `<note>` elements, their `<duration>`, their `<type>`, and every
`<duration>` offset after them in the bar. There is nothing to strip.

The arc-export session already learned the general form the expensive way: its
own strip-and-compare control FAILED, and *rather than widen the strip until
it passed*, it was replaced with a STRUCTURAL one. This is that move, for this
family.

So the control here is an ACCOUNTING IDENTITY and a CONTAINMENT:

  1. Parts and measures are IDENTICAL. INFER writes no structure.
  2. Every note the OFF arm wrote is still in the ON arm, in order, in the
     same bar — ON ⊇ OFF, per (part, measure). INFER may only ADD.
  3. The exact partition, as an EQUALITY and never a `<=`:

         notes(ON) − notes(OFF)  ==  Δ duration_narrowed − Δ no_pitch

     A narrowing INFER collapsed either becomes a written note, or is held
     back again because that note has no PITCH — and those are the only two
     destinations. ⚠️ A `<=` here is what let TEN decided hairpins be
     accounted for NOWHERE while the balance reported `True`; this file's own
     lesson, one family over.

    python3 .../probe/byte_control.py out/export-off.musicxml out/export-on.musicxml
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def read(path: str):
    root = ET.parse(path).getroot()
    parts = {}
    for p in root.findall("part"):
        bars = {}
        for m in p.findall("measure"):
            seq = []
            for n in m.findall("note"):
                if n.find("rest") is not None:
                    seq.append("rest")
                    continue
                pitch = n.find("pitch")
                if pitch is None:
                    seq.append("?")
                    continue
                step = pitch.findtext("step") or ""
                octv = pitch.findtext("octave") or ""
                alt = pitch.findtext("alter") or "0"
                seq.append(f"{step}{alt}/{octv}")
            bars[m.get("number")] = seq
        parts[p.get("id")] = bars
    return parts


def is_subsequence(small, big) -> bool:
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("off")
    ap.add_argument("on")
    a = ap.parse_args()

    off, on = read(a.off), read(a.on)
    fails = []

    if sorted(off) != sorted(on):
        fails.append(f"part ids differ: {sorted(off)} vs {sorted(on)}")
    for pid in sorted(set(off) & set(on)):
        if sorted(off[pid]) != sorted(on[pid]):
            fails.append(f"{pid}: measure numbers differ")

    n_off = sum(len(s) for b in off.values() for s in b.values())
    n_on = sum(len(s) for b in on.values() for s in b.values())
    added = collections.Counter()
    for pid in sorted(set(off) & set(on)):
        for mno, seq in off[pid].items():
            other = on[pid].get(mno, [])
            if not is_subsequence(seq, other):
                fails.append(f"{pid} m{mno}: the OFF arm's notes are not all "
                             f"still present, in order, in the ON arm")
            added[pid] += len(other) - len(seq)

    print(f"parts   {len(off)} -> {len(on)}")
    print(f"measures {sum(len(b) for b in off.values())} -> "
          f"{sum(len(b) for b in on.values())}")
    print(f"note+rest elements {n_off} -> {n_on}  ({n_on - n_off:+d})")

    # ── the accounting identity ─────────────────────────────────────────────
    def cov(path):
        p = Path(path + ".coverage.json")
        return json.loads(p.read_text()) if p.is_file() else {}

    c_off, c_on = cov(a.off), cov(a.on)
    d_off = (c_off.get("notes_not_written") or {})
    d_on = (c_on.get("notes_not_written") or {})
    if d_off or d_on:
        keys = sorted(set(d_off) | set(d_on))
        print("\nnotes_not_written:")
        for k in keys:
            print(f"  {k:<32} {d_off.get(k, 0):>6} -> {d_on.get(k, 0):>6}"
                  f"  ({d_on.get(k, 0) - d_off.get(k, 0):+d})")
        d_narrow = d_off.get("duration_narrowed", 0) - d_on.get("duration_narrowed", 0)
        d_nopitch = d_on.get("no_pitch", 0) - d_off.get("no_pitch", 0)
        expect = d_narrow - d_nopitch
        got = n_on - n_off
        print(f"\nIDENTITY  notes(ON)-notes(OFF) == Δnarrowed - Δno_pitch")
        print(f"          {got:+d} == {d_narrow:+d} - {d_nopitch:+d} = {expect:+d}"
              f"   {'HOLDS' if got == expect else '⚠️ BROKEN'}")
        if got != expect:
            fails.append("the accounting identity does not hold")

    if fails:
        print("\n⚠️ CONTROL FAILED:", file=sys.stderr)
        for f in fails[:20]:
            print("   " + f, file=sys.stderr)
        return 1
    print("\ncontrol holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
