"""2.292 second witness for a FILLED CLEF that is not the same raster read: a clef-free RANGE check.
    python3 rangecheck.py X.json [X.json ...]
For each staff whose clef was filled by INFER, take every written head's CLEF-FREE staff position (the gathered `notehead_staff_position`, or the
decided far position) and ask, per candidate clef (treble/alto/tenor/bass), what share of the heads land inside the instrument's written range
(`tools/omr/instruments.py`, +-2 semitones). The fill is "agreed" where its clef has the top share (ties counted as agreed, listed).
The instrument comes from the record's own slot/instrument verdict; no pitch is invented.  Evidence ABOUT the fill, not a rule.
"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.instruments import instrument_named  # noqa
from tools.omr.pitch_resolver import _pitch_from_position, parse_pitch, NOTE_SEMITONE  # noqa

CLEFS = ("treble", "alto", "tenor", "bass")


def midi(name):
    p = parse_pitch(name)
    if p is None:
        return None
    letter, alt, octv = p
    return 12 * (octv + 1) + NOTE_SEMITONE[letter] + alt


def main():
    for path in sys.argv[1:]:
        d = json.load(open(path))
        for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
            if not (v["clef"] and v["clef"][0]["decider"].startswith("infer")):
                continue
            det = v["clef"][0].get("detail") or {}
            inst = instrument_named(det.get("instrument")) if det.get("instrument") else None
            if inst is None:
                print(path.split("/")[-1], k, "no instrument name -> range check cannot run")
                continue
            lo, hi = inst.written_range
            P = []
            for s in d["symbols"]:
                if s["is_rest"] or not s["sub"].startswith("glyph/%s/%s/%s/" % tuple(k.split("/")[1:4])):
                    continue
                pos = s["far_pos"] if s.get("far_pos") is not None else s.get("pos")
                if pos is not None:
                    P.append(int(round(float(pos))))
            share = {}
            for c in CLEFS:
                ok = 0
                for pos in P:
                    m = midi(_pitch_from_position(pos, c))
                    if m is not None and lo - 2 <= m <= hi + 2:
                        ok += 1
                share[c] = round(ok / max(1, len(P)), 3)
            fill = v["clef"][0]["value"]
            top = max(share.values())
            tops = [c for c, x in share.items() if x == top]
            print(path.split("/")[-1], k, inst.name, (lo, hi), "heads", len(P), share, "fill", fill,
                  "AGREE" if fill in tops else "DISAGREE", "(tie %s)" % tops if len(tops) > 1 else "")


main()
