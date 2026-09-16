"""BLAST RADIUS: what ELSE moved between two exported MusicXML files.

A meter arm is supposed to move rests. It also feeds `reconcile_duration`,
the pipeline's one sanctioned loop, which re-reads a beam level by +/-1 once a
bar has a meter to land on -- so note `<type>` values move too, and those are
NOT the change under test. This counts them apart so neither can hide in the
other.

⚠️ It reports, it does not judge: a moved `<type>` is a thing a human must
check against the print, never a win.
"""
from __future__ import annotations
import argparse, collections, xml.etree.ElementTree as ET
from pathlib import Path


def index(path):
    """{(part, measure_number, ordinal): (kind, type, duration_ql, pitch)}"""
    root = ET.parse(path).getroot()
    out = {}
    for part in root.findall("part"):
        pid = part.get("id")
        div = None
        for meas in part.findall("measure"):
            d = meas.find("./attributes/divisions")
            if d is not None:
                div = float(d.text)
            for i, note in enumerate(meas.findall("note")):
                dur = note.find("duration")
                t = note.find("type")
                r = note.find("rest")
                p = note.find("pitch")
                pitch = None
                if p is not None:
                    pitch = "%s%s%s" % (p.findtext("step", ""),
                                        p.findtext("alter", ""),
                                        p.findtext("octave", ""))
                out[(pid, meas.get("number"), i)] = (
                    "rest" if r is not None else "note",
                    t.text if t is not None else None,
                    (float(dur.text) / div) if (dur is not None and div) else None,
                    (r.get("measure") if r is not None else pitch),
                )
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("before"); ap.add_argument("after")
    a = ap.parse_args(argv)
    b, f = index(a.before), index(a.after)

    only_b = set(b) - set(f)
    only_f = set(f) - set(b)
    moved = {k for k in set(b) & set(f) if b[k] != f[k]}

    print("ELEMENTS: before %d, after %d" % (len(b), len(f)))
    print("  positions only in BEFORE : %d" % len(only_b))
    print("  positions only in AFTER  : %d" % len(only_f))
    print("  positions that CHANGED   : %d" % len(moved))

    kinds = collections.Counter()
    note_type_moves = collections.Counter()
    rest_moves = collections.Counter()
    pitch_moves = 0
    for k in moved:
        ob, of = b[k], f[k]
        if ob[0] != of[0]:
            kinds["kind changed (%s -> %s)" % (ob[0], of[0])] += 1
            continue
        if ob[0] == "note":
            if ob[3] != of[3]:
                pitch_moves += 1
            if ob[1] != of[1]:
                note_type_moves["%s -> %s" % (ob[1], of[1])] += 1
            if ob[1] == of[1] and ob[2] != of[2] and ob[3] == of[3]:
                kinds["note duration only"] += 1
        else:
            rest_moves["%s/%s -> %s/%s" % (ob[1], ob[2], of[1], of[2])] += 1

    print("\nNOTE <type> MOVES: %d" % sum(note_type_moves.values()))
    for k, n in note_type_moves.most_common():
        print("   %-24s x%d" % (k, n))
    print("NOTE PITCH MOVES : %d   (expected ZERO -- a meter cannot re-pitch)"
          % pitch_moves)
    print("\nREST MOVES (type/ql): %d" % sum(rest_moves.values()))
    for k, n in rest_moves.most_common(12):
        print("   %-34s x%d" % (k, n))
    for k, n in kinds.most_common():
        print("   %-34s x%d" % (k, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
