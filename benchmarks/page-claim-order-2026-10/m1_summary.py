"""m1 numbers from out/lane-report/2.221-m2/work: per plate and arm, notes/rests written, bars held out, red bars, blue marks, colour counts."""
import json
import re
D = "out/lane-report/2.221-m2/work/"
for pl in ("litolff", "brahms"):
    for arm in ("off", "on"):
        s = json.load(open(D + f"{pl}.{arm}.symbols.json"))
        xml = open(D + f"{pl}.{arm}.musicxml").read()
        cols = {}
        for m in re.finditer(r'color="(#[0-9A-Fa-f]{6})"', xml):
            cols[m.group(1)] = cols.get(m.group(1), 0) + 1
        print(pl, arm, "hosts", len(s["hosts"]), "red_bars", s["red_bars"], "held_out", s["bars_held_out"], "not_written", s["notes_not_written"],
              "blue", s["blue_marks"], "measures", xml.count("<measure "), "colours", cols)
