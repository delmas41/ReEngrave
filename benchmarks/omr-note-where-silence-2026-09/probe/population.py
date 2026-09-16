"""THE POPULATION, re-derived from the exported FILE alone.

Sean, 2026-09-11, reading the file against the print: *"in bars where it should
be just whole note rest in two four. It's showing an actual quarter note, not a
quarter note rest."*  This finds the bars that claim to be that: a bar whose
ENTIRE content is one PITCHED note.

⚠️ IT PROPOSES CANDIDATES AND NOTHING MORE. "the page prints silence" is a fact
about the PRINT, and neither the file nor the record is the print. What this can
say is which bars are underfull and what stands in them -- i.e. where to crop.

⚠️ POSITIVE CONTROL FIRST. A prior probe of this very question returned n=0 on
both arms because it guessed a schema -- a dead instrument wearing a clean zero.
This prints the total bar count, the full-bar count and the note total BEFORE
any filtered figure, and exits non-zero if it parsed no bars at all.

    python3 .../population.py --xml FILE [--map system-map.json] [--json OUT]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET


def bars(xml_path):
    out = []
    for part in ET.parse(xml_path).getroot().findall("part"):
        pid = part.get("id")
        div, beats, btype = None, None, None
        for m in part.findall("measure"):
            at = m.find("attributes")
            if at is not None:
                if at.find("divisions") is not None:
                    div = int(at.find("divisions").text)
                t = at.find("time")
                if t is not None:
                    beats = int(t.find("beats").text)
                    btype = int(t.find("beat-type").text)
            events, used = [], 0
            for n in m.findall("note"):
                chord = n.find("chord") is not None
                d = n.find("duration")
                dur = int(d.text) if d is not None else 0
                p = n.find("pitch")
                pitch = None
                if p is not None:
                    alt = p.find("alter")
                    pitch = "%s%s%s" % (
                        p.find("step").text,
                        {None: "", "1": "#", "-1": "b", "2": "##", "-2": "bb"}.get(
                            alt.text if alt is not None else None, ""),
                        p.find("octave").text)
                r = n.find("rest")
                events.append({
                    "pitch": pitch,
                    "rest": r is not None,
                    "measure_rest": r is not None and r.get("measure") == "yes",
                    "duration": dur,
                    "type": (n.find("type").text if n.find("type") is not None
                             else None),
                    "chord": chord,
                    "grace": n.find("grace") is not None,
                })
                if not chord:
                    used += dur
            out.append({"part": pid, "measure": int(m.get("number")),
                        "divisions": div, "beats": beats, "beat_type": btype,
                        "bar_ql": (None if not (beats and btype and div)
                                   else div * 4 * beats / btype),
                        "sum": used, "events": events})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--map")
    ap.add_argument("--json")
    a = ap.parse_args()

    rows = bars(a.xml)
    if not rows:
        print("PARSED NO BARS -- dead instrument, refusing to report", file=sys.stderr)
        return 2

    notes = sum(1 for r in rows for e in r["events"] if e["pitch"])
    rests = sum(1 for r in rows for e in r["events"] if e["rest"])
    full = sum(1 for r in rows if r["bar_ql"] and r["sum"] == r["bar_ql"])
    print("=== POSITIVE CONTROL (unfiltered) ===")
    print(f"  bars parsed                 {len(rows)}")
    print(f"  pitched <note> elements     {notes}")
    print(f"  <rest> elements             {rests}")
    print(f"  bars that sum to their time {full}")
    print(f"  bars with a declared time   {sum(1 for r in rows if r['bar_ql'])}")
    print()

    lone = [r for r in rows
            if len(r["events"]) == 1 and r["events"][0]["pitch"]
            and not r["events"][0]["grace"]]
    print("=== THE POPULATION ===")
    print(f"  bars whose ENTIRE content is one PITCHED note   {len(lone)}")
    under = [r for r in lone if r["bar_ql"] and r["sum"] < r["bar_ql"]]
    print(f"    ...UNDERFULL against the declared <time>      {len(under)}")
    q24 = [r for r in under
           if (r["beats"], r["beat_type"]) == (2, 4)
           and r["sum"] * 2 == r["bar_ql"]]
    print(f"    ...a lone QUARTER in a 2/4 bar                {len(q24)}")
    print()
    tc = collections.Counter(r["events"][0]["type"] for r in lone)
    print("  written <type> of the lone note:")
    for k, v in tc.most_common():
        print(f"    {str(k):<10} {v}")
    print()
    print("  the named instances from the handoff:")
    named = {("P1", 45), ("P1", 85), ("P1", 88), ("P1", 89), ("P2", 49), ("P2", 87)}
    for r in sorted(lone, key=lambda r: (r["part"], r["measure"])):
        if (r["part"], r["measure"]) in named:
            e = r["events"][0]
            print(f"    {r['part']} m{r['measure']:<4} {e['pitch']:<4} "
                  f"duration={e['duration']} of {int(r['bar_ql'])}  type={e['type']}")

    if a.json:
        smap = None
        if a.map:
            smap = {}
            for s in json.load(open(a.map))["systems"]:
                for st in s["staves"]:
                    for n in range(st["first_measure"], st["last_measure"] + 1):
                        smap[(st["part_id"], n)] = {
                            "page": s["page"], "system": s["system"],
                            "staff": st["staff"], "part_name": st["part_name"],
                            "cell": n - st["first_measure"],
                            "clef": st.get("clef"), "fifths": st.get("fifths")}
        payload = []
        for r in lone:
            row = dict(r)
            row["underfull"] = bool(r["bar_ql"] and r["sum"] < r["bar_ql"])
            row["lone_quarter_in_2_4"] = r in q24
            if smap is not None:
                row["where"] = smap.get((r["part"], r["measure"]))
            payload.append(row)
        json.dump(payload, open(a.json, "w"), indent=1)
        print(f"\nwrote {len(payload)} rows -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
