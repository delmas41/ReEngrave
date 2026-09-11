"""THE POPULATION, from the exported FILE and the system map.

⚠️ This instrument can only propose CANDIDATES. "The page prints silence" is a
fact about the print, and neither the record nor the file is the print -- the
same boundary `printed-staves.json` draws for itself. What it CAN say is which
bars are UNDERFULL and what stands in them, which is where to point a crop.

⚠️ POSITIVE CONTROL FIRST. The manager's own probe of this reported n=0 for
both arms because it guessed the record's schema; this one prints the total
bar count and the full-bar count before any filtered figure, so a dead
instrument cannot wear a clean zero.

    python3 .../population.py --xml <file> --map <system-map.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import xml.etree.ElementTree as ET


def bars(xml_path):
    """[{part, measure, divisions, beats, events:[...]}] -- one row per bar."""
    tree = ET.parse(xml_path)
    out = []
    for part in tree.getroot().findall("part"):
        pid = part.get("id")
        div = beats = beat_type = None
        for m in part.findall("measure"):
            at = m.find("attributes")
            if at is not None:
                if at.find("divisions") is not None:
                    div = int(at.find("divisions").text)
                t = at.find("time")
                if t is not None:
                    beats = int(t.find("beats").text)
                    beat_type = int(t.find("beat-type").text)
            evs = []
            for n in m.findall("note"):
                d = n.find("duration")
                p = n.find("pitch")
                evs.append({
                    "rest": n.find("rest") is not None,
                    "measure_rest": (n.find("rest") is not None
                                     and n.find("rest").get("measure") == "yes"),
                    "chord": n.find("chord") is not None,
                    "dur": int(d.text) if d is not None else 0,
                    "pitch": (p.find("step").text + str(p.find("octave").text))
                             if p is not None else None,
                    "type": n.find("type").text if n.find("type") is not None else None,
                })
            out.append({"part": pid, "measure": int(m.get("number")),
                        "divisions": div, "beats": beats, "beat_type": beat_type,
                        "events": evs})
    return out


def bar_len(b):
    """Quarter-note divisions the meter asks for, or None where unknown."""
    if b["divisions"] is None or b["beats"] is None:
        return None
    return b["divisions"] * 4 * b["beats"] // b["beat_type"]


def sounding(b):
    """Sum of non-chord durations -- the bar's own arithmetic."""
    return sum(e["dur"] for e in b["events"] if not e["chord"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--json", help="write the candidate rows here")
    a = ap.parse_args()

    rows = bars(a.xml)
    smap = json.load(open(a.map))
    where = {}
    for sysrow in smap["systems"]:
        for st in sysrow["staves"]:
            for n in range(st["first_measure"], st["last_measure"] + 1):
                where[(st["part_id"], n)] = (sysrow["page"], sysrow["system"],
                                             st["staff"])

    # ---- POSITIVE CONTROL: the denominators, before any filter ----
    print(f"bars in the file                      {len(rows)}")
    print(f"  with a known meter                  {sum(1 for b in rows if bar_len(b))}")
    print(f"  mapped to a printed system          "
          f"{sum(1 for b in rows if (b['part'], b['measure']) in where)}")
    full = [b for b in rows if bar_len(b) and sounding(b) == bar_len(b)]
    print(f"  arithmetically FULL                 {len(full)}")
    short = [b for b in rows if bar_len(b) and sounding(b) < bar_len(b)]
    over = [b for b in rows if bar_len(b) and sounding(b) > bar_len(b)]
    print(f"  SHORT                               {len(short)}")
    print(f"  OVERFULL                            {len(over)}")
    print()

    def pitched(b):
        return [e for e in b["events"] if not e["rest"]]

    def rests(b):
        return [e for e in b["events"] if e["rest"]]

    # ---- the partition Sean's words describe ----
    print("=== bars carrying PITCHED ink and NO rest ===")
    no_rest = [b for b in rows if pitched(b) and not rests(b)]
    print(f"  all such bars                       {len(no_rest)}")
    lone = [b for b in no_rest
            if len([e for e in b['events'] if not e['chord']]) == 1]
    print(f"  ...whose whole content is ONE note  {len(lone)}")
    lone_short = [b for b in lone if bar_len(b) and sounding(b) < bar_len(b)]
    print(f"  ......and the bar is UNDERFULL      {len(lone_short)}")
    lone_q = [b for b in lone_short
              if b["beats"] == 2 and b["beat_type"] == 4
              and sounding(b) == bar_len(b) // 2]
    print(f"  .........a QUARTER in a 2/4 bar     {len(lone_q)}")
    print()

    print("=== WIDER: any bar SHORT by at least half, carrying pitched ink ===")
    wide = [b for b in short if pitched(b) and sounding(b) <= bar_len(b) // 2]
    print(f"  bars                                {len(wide)}")
    print(f"  pitched notes standing in them      "
          f"{sum(len(pitched(b)) for b in wide)}")
    byfill = collections.Counter(f"{sounding(b)}/{bar_len(b)}" for b in wide)
    print(f"  fill ratios                         {dict(byfill.most_common(8))}")
    print()

    print("=== where they sit (page, system, staff) ===")
    loc = collections.Counter(where.get((b["part"], b["measure"]), ("?",) * 3)
                              for b in wide)
    for k, v in sorted(loc.items(), key=lambda t: str(t[0])):
        print(f"  page {k[0]} system {k[1]} staff {k[2]}   {v}")

    if a.json:
        outrows = []
        for b in wide:
            pg = where.get((b["part"], b["measure"]))
            outrows.append({
                "part": b["part"], "measure": b["measure"],
                "page": pg[0] if pg else None,
                "system": pg[1] if pg else None,
                "staff": pg[2] if pg else None,
                "sounding": sounding(b), "bar_len": bar_len(b),
                "lone": len([e for e in b['events'] if not e['chord']]) == 1,
                "events": b["events"],
            })
        json.dump(outrows, open(a.json, "w"), indent=1)
        print(f"\nwrote {len(outrows)} rows -> {a.json}")


if __name__ == "__main__":
    main()
