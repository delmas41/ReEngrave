"""2.251 carry: the PRINT witness for the carry. For every head on a staff whose clefs I looked at on the print (TRUTH below: the header
clef and every clef printed inside the system, page px, from the 2.251 count crops and the 2026-11-02 carry crops), the pitch the
print's clef gives that head's own staff position (`pitch_resolver._pitch_from_position`, the position the record decided) against
the pitch each arm wrote: right / wrong / unread (no pitch). Only heads whose print clef is NOT the header clef (where a carry matters)
and heads after the first clef inside the system are counted (`after`), plus all heads on these staves (`all`).

python3 work-2.251/clefwit.py PLATE OFF.record.json ON.record.json     (record_io-readable records or mini-records with verdicts)
"""
import json, re, sys
from collections import Counter

sys.path.insert(0, ".")
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402

# (page, system, staff local) -> (header clef, [(x page px, clef), ...])  -- print-confirmed
TRUTH = {
    "litolff": {
        (2, 1, 3): ("bass", [(707, "tenor"), (973, "bass")]),
        (4, 0, 9): ("tenor", [(1982, "bass")]),
        # bar 111's bass clef: the eighth whose head (2314-2338) overlaps its body is printed BEFORE it (Sean, carry r2 tile 2)
        (4, 1, 3): ("bass", [(992, "tenor"), (1678, "bass"), (2167, "tenor"), (2340, "bass")]),
        (6, 0, 3): ("bass", [(606, "tenor")]),
        (6, 0, 8): ("tenor", [(1890, "bass")]),
        (6, 1, 3): ("tenor", [(599, "bass")]),
        (8, 0, 3): ("bass", [(879, "tenor")]),
        (8, 1, 3): ("tenor", [(548, "bass")]),
        (10, 0, 3): ("tenor", [(1643, "bass")]),
        (11, 0, 2): ("bass", [(549, "tenor"), (1800, "bass"), (2328, "tenor")]),
        (11, 1, 3): ("tenor", [(704, "bass")]),
        (11, 1, 9): ("bass", [(1741, "tenor")]),
        (16, 0, 3): ("tenor", [(942, "bass"), (1866, "tenor")]),
        (16, 1, 3): ("tenor", [(2313, "bass")]),
    },
    "brahms": {
        (4, 1, 3): ("bass", [(3030, "tenor"), (4018, "bass")]),
        (5, 0, 3): ("bass", [(1693, "tenor")]),
        (5, 1, 3): ("tenor", [(1004, "bass"), (2020, "tenor"), (5418, "bass")]),
    },
}


def load(path):
    from tools.omr.staged import judged as J
    import pathlib
    p = pathlib.Path(path)
    pitch, pos, box = {}, {}, {}
    for v in J.iter_array(p, "verdicts"):
        q = v.get("quantity")
        if q == "pitch" and v.get("outcome") == "decided":
            pitch[v["subject"]] = v
        elif q == "notehead_position" and v.get("outcome") == "decided" and v.get("value") is not None:
            pos[v["subject"]] = int(v["value"])
    for o in J.iter_array(p, "observations"):
        q = o.get("quantity")
        if q == "notehead_staff_position":
            pos.setdefault(o["subject"], int(round(float(o["value"]))))
        elif q == "glyph_box":
            bb = (o.get("detail") or {}).get("bbox_page_px")
            if bb and str(o["value"][0]).startswith("notehead"):
                box[o["subject"]] = (float(bb[0]) + float(bb[2])) / 2.0
    return pitch, pos, box


def step_oct(name):
    m = re.match(r"([A-G])[#b♯♭x]*(-?\d+)", str(name))
    return (m.group(1) + m.group(2)) if m else str(name)


def main():
    plate, off_p, on_p = sys.argv[1:4]
    T = TRUTH[plate]
    arms = {"off": load(off_p), "on": load(on_p)}
    tally = {a: {"after": Counter(), "all": Counter()} for a in arms}
    places = []
    heads = set()
    for a, (pitch, pos, box) in arms.items():
        for subj in box:
            p = subj.split("/")
            key = (int(p[1]), int(p[2]), int(p[3]))
            if key in T:
                heads.add(subj)
    for subj in sorted(heads):
        p = subj.split("/")
        key = (int(p[1]), int(p[2]), int(p[3]))
        header, chg = T[key]
        x = arms["on"][2].get(subj, arms["off"][2].get(subj))
        po = arms["on"][1].get(subj, arms["off"][1].get(subj))
        if x is None or po is None:
            continue
        clef = header
        after = False
        for cx, k in chg:
            if cx < x:
                clef, after = k, True
        truth = step_oct(_pitch_from_position(po, clef))
        for a, (pitch, pos, box) in arms.items():
            v = pitch.get(subj)
            res = "unread" if v is None else ("right" if step_oct(v["value"]) == truth else "wrong")
            tally[a]["all"][res] += 1
            if after:
                tally[a]["after"][res] += 1
        if after:
            places.append((subj, clef, truth, *[(pitch.get(subj) or {}).get("value") for pitch, _p, _b in arms.values()]))
    for a in arms:
        print(plate, a, "after a clef inside the system:", dict(tally[a]["after"]), "| all heads on these staves:", dict(tally[a]["all"]))
    if len(sys.argv) > 4:
        json.dump(places, open(sys.argv[4], "w"), indent=0)


main()
