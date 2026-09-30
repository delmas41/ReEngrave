"""ROADMAP 2.40 part 2: per-bar chord count, reference vs our export,
Beethoven 5 mvt 1 bars 49-82, condensed wind families (Litolff prints two
players per staff for winds -- the condensed count is an encoding property,
CLAUDE.md Sec.10, but the CHORD EVENT it produces on the page is real ink a
single staff carries when both players sound different pitches together)."""
import xml.etree.ElementTree as ET
from collections import defaultdict

REF = "/tmp/scratch_2_40/score.xml"
OURS = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/benchmarks/acceptance/out/beethoven5-litolff/beethoven5-litolff.musicxml"

BAR_LO, BAR_HI = 49, 82

FAMILIES = {
    "Flute": ["P1", "P2"],
    "Oboe": ["P3", "P4"],
    "Clarinet": ["P5", "P6"],
    "Bassoon": ["P7", "P8"],
    "Horn": ["P9", "P10"],
    "Trumpet": ["P11", "P12"],
}


def _notes(measure):
    """[(onset, duration, pitch_key or None-for-rest, voice, is_chord)]"""
    out = []
    onset = 0
    for el in measure:
        if el.tag == "note":
            dur_el = el.find("duration")
            dur = int(dur_el.text) if dur_el is not None else 0
            is_chord = el.find("chord") is not None
            voice_el = el.find("voice")
            voice = voice_el.text if voice_el is not None else "1"
            rest = el.find("rest") is not None
            pitch = None
            if not rest:
                p = el.find("pitch")
                if p is not None:
                    step = p.find("step").text
                    alter_el = p.find("alter")
                    alter = alter_el.text if alter_el is not None else "0"
                    octave = p.find("octave").text
                    pitch = f"{step}{alter}{octave}"
            this_onset = onset if not is_chord else out[-1][0] if out else onset
            out.append((this_onset, dur, pitch, voice, is_chord))
            if not is_chord:
                onset += dur
        elif el.tag == "backup":
            dur_el = el.find("duration")
            if dur_el is not None:
                onset -= int(dur_el.text)
        elif el.tag == "forward":
            dur_el = el.find("duration")
            if dur_el is not None:
                onset += int(dur_el.text)
    return out


def _part_measures(path, part_id):
    t = ET.parse(path)
    root = t.getroot()
    p = root.find(f"part[@id='{part_id}']")
    if p is None:
        return {}
    out = {}
    for m in p.findall("measure"):
        num = m.get("number")
        out[num] = _notes(m)
    return out


def onsets_with_pitch(notes):
    """{onset: set(pitch_key)} -- rests contribute nothing."""
    d = defaultdict(set)
    for onset, dur, pitch, voice, is_chord in notes:
        if pitch is not None:
            d[onset].add(pitch)
    return d


def main():
    report = []
    candidates = []
    comparable_bars = 0
    total_bars_checked = 0
    for fam, (pa, pb) in FAMILIES.items():
        ref_a = _part_measures(REF, pa)
        ref_b = _part_measures(REF, pb)
        ours = _part_measures(OURS, fam and _our_part_id(fam))
        for bar in range(BAR_LO, BAR_HI + 1):
            key = str(bar)
            total_bars_checked += 1
            na = ref_a.get(key, [])
            nb = ref_b.get(key, [])
            no = ours.get(key, [])
            if not (na or nb) or not no:
                continue  # not comparable -- one side has nothing here
            comparable_bars += 1
            ra = onsets_with_pitch(na)
            rb = onsets_with_pitch(nb)
            ro = onsets_with_pitch(no)
            all_onsets = sorted(set(ra) | set(rb))
            for on in all_onsets:
                pitches_ref = ra.get(on, set()) | rb.get(on, set())
                is_ref_dyad = bool(ra.get(on)) and bool(rb.get(on)) \
                    and ra.get(on) != rb.get(on)
                if not is_ref_dyad:
                    continue
                # nearest our onset within a small window (rounding across
                # divisions differences between the two files)
                our_here = None
                for oo in ro:
                    if abs(oo - on) <= 4:
                        our_here = ro[oo]
                        break
                n_our = len(our_here) if our_here else 0
                if n_our <= 1:
                    candidates.append(dict(
                        family=fam, bar=bar, onset=on,
                        ref_pitches=sorted(pitches_ref),
                        our_pitches=sorted(our_here) if our_here else [],
                    ))
        report.append((fam, pa, pb))
    print("comparable_bars(fam-bars)", comparable_bars, "of", total_bars_checked)
    print("candidates", len(candidates))
    for c in candidates:
        print(c)
    import json
    json.dump({"comparable_bars": comparable_bars,
               "total_bars_checked": total_bars_checked,
               "candidates": candidates},
              open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/dyad_candidates.json", "w"),
              indent=1)


_OUR_ID = {"Flute": "P1", "Oboe": "P2", "Clarinet": "P3", "Bassoon": "P4",
          "Horn": "P5", "Trumpet": "P6"}


def _our_part_id(fam):
    return _OUR_ID[fam]


if __name__ == "__main__":
    main()
