"""2.279 r3: per-bar losses and the bar's say on the new blue values, from the two arms' written MusicXML (lane_report work dir).

usage (repo root): python3 probe/2.279r3/bars.py out/lane-report/2.279-r3/work [litolff brahms]

For each bar (part, measure number) in OFF and ON:
  state   red   = the bar carries the unread red (#D00000: a word, a bracket, a note colour) -- the reader said "cannot read this"
          blue  = no red, at least one blue (#1F6FEB) note/rest
          clean = neither
  voices  per voice, sum of <duration> of chord-leading notes/rests (+forward, -backup handled by voice) against the bar length of the
          time signature in force -- 'exact' / 'over' / 'under'
Reports the transition table, every clean -> red/blue bar (listed), and, for the NEW blue notes (blue in ON at a place that was not
blue in OFF, same part/measure/onset/pitch), whether their bar lands exactly on the meter (the value is CONFIRMED by the bar),
is overfull (CONTRADICTED), or is still short (the bar cannot judge).
"""
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

RED = "#D00000"
BLUE = "#1F6FEB"


def bars(path):
    root = ET.parse(path).getroot()
    out = {}
    for part in root.iter("part"):
        pid = part.get("id")
        beats, bt, divisions = 4, 4, 1
        for m in part.findall("measure"):
            for a in m.findall("attributes"):
                if a.findtext("divisions"):
                    divisions = int(a.findtext("divisions"))
                t = a.find("time")
                if t is not None:
                    beats, bt = int(t.findtext("beats")), int(t.findtext("beat-type"))
            length = beats * 4 * divisions / bt
            red = blue = False
            per_voice = collections.defaultdict(int)
            notes = []
            pos = collections.defaultdict(int)
            for el in m.iter():
                if el.get("color") == RED or (el.tag == "words" and el.get("color") == RED):
                    red = True
                if el.tag == "note":
                    v = el.findtext("voice") or "1"
                    if el.get("color") == BLUE:
                        blue = True
                    if el.find("grace") is None and el.find("chord") is None:
                        d = int(el.findtext("duration") or 0)
                        onset = pos[v]
                        pos[v] += d
                        per_voice[v] += d
                    else:
                        onset = pos[v]
                    p = el.find("pitch")
                    if p is not None and el.find("grace") is None:
                        notes.append(dict(voice=v, onset=onset, pitch="%s%s%s" % (p.findtext("step"), p.findtext("alter") or "", p.findtext("octave")),
                                          blue=el.get("color") == BLUE, type=el.findtext("type")))
                elif el.tag == "forward":
                    d = int(el.findtext("duration") or 0)
                    v = el.findtext("voice") or "1"
                    pos[v] += d
                    per_voice[v] += d
                elif el.tag == "backup":
                    pass
            # backup handling: voices are written one after another; each voice's own sum is what is compared
            state = "red" if red else ("blue" if blue else "clean")
            fill = {v: ("exact" if s == length else "over" if s > length else "under") for v, s in per_voice.items()}
            out[(pid, m.get("number"))] = dict(state=state, fill=fill, notes=notes, length=length,
                                               unread_heads=len([n for n in m.findall("note") if n.find("grace") is not None
                                                                 and (n.findtext("notehead") or "") == "x"]))
    return out


def main(work, plates):
    work = pathlib.Path(work)
    summary = {}
    for plate in plates:
        off, on = bars(work / ("%s.off.musicxml" % plate)), bars(work / ("%s.on.musicxml" % plate))
        trans = collections.Counter()
        worse = []
        for k in sorted(set(off) | set(on)):
            a, b = off.get(k), on.get(k)
            if a is None or b is None:
                trans["bar_missing_in_" + ("off" if a is None else "on")] += 1
                continue
            trans["%s->%s" % (a["state"], b["state"])] += 1
            if a["state"] == "clean" and b["state"] != "clean":
                worse.append((k, b["state"], b["unread_heads"], [n for n in b["notes"] if n["blue"]][:3]))
        # the bar's say on the new blue notes
        new_blue = []
        for k, b in on.items():
            a = off.get(k)
            if a is None:
                continue
            offblue = {(n["voice"], n["onset"], n["pitch"]) for n in a["notes"] if n["blue"]}
            offany = {(n["voice"], n["onset"], n["pitch"]) for n in a["notes"]}
            for n in b["notes"]:
                if n["blue"] and (n["voice"], n["onset"], n["pitch"]) not in offblue:
                    gained = (n["voice"], n["onset"], n["pitch"]) not in offany
                    new_blue.append((k, n, b["fill"].get(n["voice"], "?"), gained, b["state"]))
        say = collections.Counter(f for _, _, f, g, _ in new_blue)
        say_gained = collections.Counter(f for _, _, f, g, _ in new_blue if g)
        summary[plate] = dict(transitions=dict(trans), clean_to_worse=len(worse), new_blue_notes=len(new_blue),
                              new_blue_gained_notes=sum(1 for x in new_blue if x[3]), bar_says_all=dict(say), bar_says_gained=dict(say_gained),
                              red_heads_written=sum(b["unread_heads"] for b in on.values()))
        print("== %s ==" % plate)
        print(json.dumps(summary[plate], indent=1))
        print("clean -> worse bars (every one):")
        for w in worse:
            print("  ", w)
    return summary


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["litolff", "brahms"])
