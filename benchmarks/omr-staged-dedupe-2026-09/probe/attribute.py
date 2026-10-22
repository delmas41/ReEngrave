"""Attribute Sean's two complaints to the duplicate pairs — BY NAME.

Sean, on the first cleanup artefact:

  * *"there are a lot of doubled notes on a staff that dont make sense (2 of
    the same note next to each other connected to the same stem)"*
  * *"the score has only ff all the way down and ours has extra fs"*

⚠️ COUNTING CANNOT SEE A RELOCATION; ONLY NAMING THE NOTES CAN. This repo paid
for that lesson twice (the chord-tie relocation, the frame-error mutation that
every span count accepted). So this probe prints the actual `<pitch>` of each
doubled chord member, the actual page boxes of the letters behind each `fff` /
`ffff`, and their IoU — never a bare total.

Two INDEPENDENT arms, deliberately:
  1. read the EXPORTED MusicXML for the symptom (what Sean saw);
  2. read the RECORD for duplicate pairs (what the machine holds);
then join them. An arm that only read the record could not show the symptom
reaches the file; an arm that only read the file could not name the cause.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from reach import duplicate_pairs  # noqa: E402  (same directory)

sys.path.insert(0, str(Path(__file__).resolve().parent))


def pitch_of(note):
    p = note.find("pitch")
    if p is None:
        return "rest" if note.find("rest") is not None else None
    step = p.findtext("step")
    alt = p.findtext("alter")
    octv = p.findtext("octave")
    acc = {"-2": "bb", "-1": "b", "0": "", "1": "#", "2": "##"}.get(alt or "0",
                                                                   alt or "")
    return f"{step}{acc}{octv}"


def chord_events(measure):
    """Group a measure's <note> elements into chord events."""
    events, cur = [], []
    for n in measure.findall("note"):
        if n.find("chord") is not None and cur:
            cur.append(n)
        else:
            if cur:
                events.append(cur)
            cur = [n]
    if cur:
        events.append(cur)
    return events


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("musicxml")
    ap.add_argument("record")
    ap.add_argument("--limit", type=int, default=12)
    args = ap.parse_args(argv)

    tree = ET.parse(args.musicxml)
    root = tree.getroot()

    # ── SYMPTOM 1: a chord with two notes at the SAME pitch ────────────────
    print("=" * 72)
    print("SYMPTOM 1 — 'two of the same note next to each other on one stem'")
    print("=" * 72)
    dup_chords = []
    n_chord_events = 0
    for part in root.findall("part"):
        pid = part.get("id")
        for meas in part.findall("measure"):
            mno = meas.get("number")
            for ev in chord_events(meas):
                if len(ev) < 2:
                    continue
                n_chord_events += 1
                ps = [pitch_of(n) for n in ev]
                rep = [p for p, c in collections.Counter(ps).items() if c > 1]
                if rep:
                    dup_chords.append((pid, mno, ps, rep))
    print(f"chord events (2+ notes on one stem): {n_chord_events}")
    print(f"chord events with a REPEATED pitch:  {len(dup_chords)}"
          f"   ({len(dup_chords) / n_chord_events:.1%} of chords)"
          if n_chord_events else "")
    print("\nfirst examples, NAMED:")
    for pid, mno, ps, rep in dup_chords[:args.limit]:
        print(f"  {pid} m{mno:<5} chord = {ps}   repeated: {rep}")

    # How many notes would go if each repeated pitch kept one copy?
    extra = sum(len(ps) - len(set(ps)) for _p, _m, ps, _r in dup_chords)
    print(f"\nexcess <note> elements inside repeated-pitch chords: {extra}")

    # ── SYMPTOM 2: dynamics the page does not print ────────────────────────
    print()
    print("=" * 72)
    print("SYMPTOM 2 — 'the score has only ff and ours has extra fs'")
    print("=" * 72)
    dyn = collections.Counter()
    for d in root.iter("dynamics"):
        for child in d:
            dyn[child.tag] += 1
    print("<dynamics> children in the exported file:")
    for k, v in sorted(dyn.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<8} {v}")

    # ── THE RECORD SIDE ────────────────────────────────────────────────────
    obs = json.load(open(args.record))["record"]["observations"]
    subjects, family, pairs = duplicate_pairs(obs)

    letters = [p for p in pairs if p["family"] == "dynamic_letter"]
    print(f"\ndynamic_letter duplicate pairs in the record: {len(letters)}")
    same_cell = [p for p in letters if p["scope"] == "same_cell"]
    print(f"  of which SAME CELL (one staff holding the ink twice): "
          f"{len(same_cell)}")
    print("\nfirst SAME-CELL dynamic-letter pairs, with their boxes:")
    for p in same_cell[:args.limit]:
        print(f"  {p['a']}  {p['class_a']:<12} conf={p['conf_a']:.3f} "
              f"box={[round(v, 1) for v in p['box_a']]}")
        print(f"  {p['b']}  {p['class_b']:<12} conf={p['conf_b']:.3f} "
              f"box={[round(v, 1) for v in p['box_b']]}   IoU={p['iou']}")
        print()

    heads = [p for p in pairs
             if p["family"] == "notehead_class" and p["scope"] == "same_cell"]
    print(f"notehead SAME-CELL duplicate pairs: {len(heads)}")
    print("first examples, with their boxes:")
    for p in heads[:args.limit]:
        print(f"  {p['a']}  {p['class_a']:<22} conf={p['conf_a']:.3f} "
              f"box={[round(v, 1) for v in p['box_a']]}")
        print(f"  {p['b']}  {p['class_b']:<22} conf={p['conf_b']:.3f} "
              f"box={[round(v, 1) for v in p['box_b']]}   IoU={p['iou']}")
        print()

    # Do the duplicated copies agree about their CLASS? If they do, the
    # question is purely "which copy", and no reading is at stake.
    for fam in ("notehead_class", "dynamic_letter", "arc_box"):
        f = [p for p in pairs if p["family"] == fam]
        if not f:
            continue
        agree = sum(1 for p in f if p["same_class"])
        print(f"{fam:<18} pairs {len(f):>4}   same class {agree:>4} "
              f"({agree / len(f):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
