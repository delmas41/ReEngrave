"""2.248 r3: 12 blind tiles. 6 are in-staff heads r2 moved (box centre vs ink centre), 6 are far heads whose ledger count abstained and
whose box-centre and ink-centre steps differ (now written blue). One neutral orange box on the print, nothing of ours drawn; the key
(which centre is which, and what each answer implies) is outside the tiles folder."""
import collections
import json
import pathlib
import random

from tools.omr.staged import lane_report as LR

W = pathlib.Path("out/2.248-r3")
OUT = pathlib.Path("out/print/2.248-r3-tiles")
rng = random.Random(248)


def load(p):
    r = json.load(open(p))
    return r.get("record", r)


def step_name(pos, clef="treble"):
    from tools.omr.pitch_resolver import _pitch_from_position
    return _pitch_from_position(int(round(pos)), clef)


r2_items, r3_items = [], []
for plate in ("litolff", "brahms"):
    rec = load(str(W / "r2/work") + "/%s.on.gathered.record.json" % plate)
    boxes = LR.glyph_boxes(rec["observations"])
    for o in rec["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] == "notehead_staff_position" and "from_head_ink" in d and o["subject"] in boxes:
            b = boxes[o["subject"]]
            r2_items.append(dict(plate=plate, page=b["page"], box=b["box"], subject=o["subject"], role="case", group="r2_in_staff",
                                 box_centre_position=round(d["detector_position_float"], 2), ink_centre_position=round(o["value"], 2)))
rec_by = {}
for plate in ("litolff", "brahms"):
    rec = load(str(W / "far2b/work") + "/%s.on.gathered.record.json" % plate)
    boxes = LR.glyph_boxes(rec["observations"])
    written = collections.defaultdict(list)
    for v in rec["verdicts"]:
        if v["quantity"] == "pitch":
            written[v["subject"]].append(v)
    for s, vs in written.items():
        v = vs[-1]
        d = v.get("detail") or {}
        if v["reason"] == "position_and_clef_ledger_unread" and d.get("ink_position") is not None \
                and d.get("ink_position") != d.get("box_position") and s in boxes:
            b = boxes[s]
            r3_items.append(dict(plate=plate, page=b["page"], box=b["box"], subject=s, role="case", group="r3_far_unread_blue",
                                 box_centre_position=d["box_position"], ink_centre_position=d["ink_position"],
                                 written_pitch=v["value"], candidates=[c["value"] for c in v["candidates"]]))
print("r2 moved heads", len(r2_items), "r3 far unread (differing)", len(r3_items))
# 6 + 6; r2 spread over both plates
rng.shuffle(r2_items)
rng.shuffle(r3_items)
byp = collections.defaultdict(list)
for it in r2_items:
    byp[it["plate"]].append(it)
pick2 = byp["brahms"][:3] + byp["litolff"][: 6 - min(3, len(byp["brahms"]))]
pick3 = r3_items[:6]
items = (pick2 + pick3)[:12]
rng.shuffle(items)
OUT.mkdir(parents=True, exist_ok=True)
LR.cut_tiles(items, OUT)
(OUT / "tiles" / "README.md").write_text(
    "# 2.248 round 3 -- 12 tiles\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn.\n\n"
    "**One question, for every tile:** is the notehead in the orange box sitting ON a line (or a ledger line) or IN a space?\n\n"
    "Answer by tile number: `line` or `space` (and `not a note` if it is not a head).\n")
print("tiles", len(items), collections.Counter(i["group"] for i in items))
