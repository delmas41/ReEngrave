"""ROADMAP 2.305 r4: Sean's p0 page-pass arcs that run OFF the system's right edge (his label's right edge within `EDGE_SP` of the page's last head), scored
against the written file's arcs that START on p0 and STOP on a later system (page 1, system 0): RIGHT when the written start note is within REACH of his label's left
edge (2.5 sp slur / 3.5 sp tie, x), within 6 sp of his band (y), and the kind agrees; OTHER_KIND when only the kind differs; NONE otherwise.

    python3 halfarc_score_2305.py WORKDIR      (WORKDIR: brahms.{off,on}.musicxml + brahms.on.gathered.record.json; pages 0 and 1 gathered)
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-arc-binding-2026-10"))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-arc-binding-2026-10" / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402
import arcs_combined as AC  # noqa: E402

SP = 32.0
EDGE_SP = 4.0
work = pathlib.Path(sys.argv[1])
boxes = AC.head_boxes(work / "brahms.on.gathered.record.json", 0)
right_x = max(b[2] for b in boxes.values())
keys = [k for k in AC.key_sean() if k["x1"] >= right_x - EDGE_SP * SP]
print("Sean's p0 arcs that run off the system's right edge (x1 >= %.0f): %d -- %s" % (right_x - EDGE_SP * SP, len(keys), [k["id"] for k in keys]))
for arm in ("off", "on"):
    arcs = [a for a in A.arcs_of_xml((work / ("brahms.%s.musicxml" % arm)).read_text())
            if a["start"].startswith("glyph/0/") and a["stop"].split("/")[1:3] != a["start"].split("/")[1:3]]
    res = []
    for k in keys:
        reach = (3.5 if k["kind"] == "tie" else 2.5) * SP
        got = None
        for a in arcs:
            b = boxes.get(a["start"])
            if not b:
                continue
            x, y = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if abs(x - k["x0"]) <= reach and AC.yd(y, k["y0"], k["y1"]) <= 6 * SP:
                got = ("right" if a["kind"] == k["kind"] else "other_kind", a)
                if got[0] == "right":
                    break
        res.append((k["id"], k["kind"], got[0] if got else "none", (got[1]["start"], got[1]["stop"], got[1]["kind"]) if got else None))
    print("%s: cross-system arcs from p0 %d | right %d other_kind %d none %d" % (arm, len(arcs), sum(1 for r in res if r[2] == "right"),
                                                                               sum(1 for r in res if r[2] == "other_kind"), sum(1 for r in res if r[2] == "none")))
    for r in res:
        print("   ", r)
