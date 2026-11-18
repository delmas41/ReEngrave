"""ROADMAP 2.314 r2 -- controls cut from REAL judged marks, read off a `lane_report` work dir (OFF and ON arms of the same tree).

    python3 benchmarks/plain-stemmed-2026-11/controls_r2.py out/lane-report/2.314-r2/work

Each control can fail: run it on the round-1 work dir (flag ON before the r2 rules) and the `f`-curl rows and the overfull-voice count FAIL; on the r2 work dir they pass.
  * Sean's 2.311 beam tiles (answers-2.311-beams.json): 2 quarter, 4 half, 5 half, 12 (Brahms) dotted quarter -- OFF refuses, ON writes his value; tile 1 (a sharp and a natural, not a note) stays unwritten.
  * the `f`-curl heads round 1 found (our look, crops in out/print/2.314-r1): NOT written ON.
  * (B) a voice never counted longer than the bar: the number of bars written red whose words say a voice counted MORE than the bar holds (a rest written into a full voice), OFF vs ON.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

W = sys.argv[1].rstrip("/")
HEAD = {"litolff": {"glyph/2/0/10/2/1": ("quarter", False), "glyph/16/0/0/0/24": ("half", False), "glyph/6/1/3/2/4": ("half", False)},
        "brahms": {"glyph/8/0/1/5/3": ("quarter", True)}}
NOT_A_NOTE_WRITTEN = {"litolff": ["glyph/6/1/2/10/3"],
                      "brahms": []}
F_CURLS = {"litolff": ["glyph/4/0/0/11/7", "glyph/4/1/7/4/18", "glyph/6/1/0/10/9", "glyph/4/1/5/4/5", "glyph/4/1/3/4/8", "glyph/6/1/10/10/7", "glyph/6/1/6/10/6"],
           "brahms": ["glyph/12/1/11/3/9"]}
bad = 0


def hosts(plate, arm):
    return {h["rg"]: h for h in json.load(open("%s/%s.%s.symbols.json" % (W, plate, arm)))["hosts"] if h.get("rg")}


def overfull(plate, arm):
    n = 0
    for m in ET.parse("%s/%s.%s.musicxml" % (W, plate, arm)).getroot().iter("words"):
        t = m.text or ""
        if t.startswith("does not add up"):
            want = float(re.search(r"hold ([\d.]+)", t).group(1))
            counted = [float(x) for x in re.search(r"counted ([\d./ ]+)", t).group(1).split("/")]
            if any(c > want + 1e-6 for c in counted):
                n += 1
    return n


def check(ok, line):
    global bad
    bad += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + line)


import os
for plate in ("litolff", "brahms"):
    if not os.path.exists("%s/%s.on.symbols.json" % (W, plate)):
        print("SKIP %s: no arm files in %s" % (plate, W))
        continue
    off, on = hosts(plate, "off"), hosts(plate, "on")
    for k, (typ, dotted) in HEAD[plate].items():
        h = on.get(k)
        ok = h is not None and h["type"] == typ and (len(h["sub"].get("dot", [])) > 0) == dotted
        check(ok, "%s %s written ON as %s%s (OFF: %s)" % (plate, k, typ, " dotted" if dotted else "", "written" if k in off else "refused"))
    for k in NOT_A_NOTE_WRITTEN[plate]:
        check(k not in on, "%s %s (not a note) stays unwritten ON" % (plate, k))
    for k in F_CURLS[plate]:
        check(k not in on, "%s %s (curl of an f) not written ON (OFF: %s)" % (plate, k, "written" if k in off else "not written"))
    o0, o1 = overfull(plate, "off"), overfull(plate, "on")
    check(o1 <= o0, "%s bars with a voice counted LONGER than the bar: OFF %d ON %d" % (plate, o0, o1))
print("FAILED %d" % bad)
sys.exit(1 if bad else 0)
