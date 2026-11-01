"""2.247 r2: 12 blind tiles -- the places of Sean's r1 tiles 2, 3, 5, 6, 7, 8 (the box now drawn on the mark's INK extent the ON arm read,
where the reader grew it) and 6 places whose WRITTEN alteration the flag changes in the r2 control (type_control.py output), seed 2247.
One thin orange box, nothing else drawn; key OUTSIDE the tile folder. usage: make_tiles_r2.py R1_KEY.json TYPE_CONTROL.json WORK_DIR OUT_DIR"""
import json
import pathlib
import random
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/accidental-kind-2026-10")
from tools.omr.staged import lane_report as LR  # noqa: E402
import type_control as T  # noqa: E402

QUESTION = "Is the mark in the orange box a sharp, a flat or a natural? (Or part of one -- say which -- or not an accidental at all.)"


def main(r1_key, tc_path, work, out_dir):
    r1 = {k["tile"]: k for k in json.load(open(r1_key))}
    tc = json.load(open(tc_path))
    on = {p: T.fams(f"{work}/{p}.on.gathered.record.json") for p in ("litolff", "brahms")}
    items, used = [], set()

    def add(plate, page, box, role, **kw):
        key = (plate, page, round(box[0] / 10), round(box[1] / 10))
        if key in used or len(items) >= 12:
            return
        used.add(key)
        items.append(dict(plate=plate, page=page, box=[round(v, 1) for v in box], role=role, **kw))

    for n in (2, 3, 5, 6, 7, 8):
        k = r1[n]
        f = on[k["plate"]].get(k["subject"]) or {}
        fam = f.get("family") or {}
        add(k["plate"], k["page"], k["box"], "r1-tile-%d" % n, subject=k["subject"], cls=k.get("cls"), on_type=fam.get("type"),
            on_why=fam.get("why"), alt_on=f.get("alteration"), ink_offset=(fam.get("features") or {}).get("box_offset_sp"))
    rng = random.Random(2247)
    ch = [c for c in tc if c["alt_off"] != c["alt_on"] and c["page_box"]]
    rng.shuffle(ch)
    for c in sorted(ch, key=lambda c: c["plate"])[:0] + ch:
        add(c["plate"], c["page"], c["page_box"], "written-changed", subject=c["subject"], cls=c["cls"], off=c["alt_off"], on=c["alt_on"],
            on_why=c["on_why"])
    rng.shuffle(items)
    out = pathlib.Path(out_dir)
    info = LR.cut_tiles(items, out)
    (out / "tiles" / "README.md").write_text(
        "# 2.247 round 2: 12 blind tiles\n\nEach picture is a piece of a scanned score page with ONE thin orange box and nothing else "
        "drawn. The box only says where to look.\n\n**Question, for every tile:** " + QUESTION +
        "\n\nAnswer by tile number (e.g. `1 natural, 2 flat, 3 part of a natural ...`).\n")
    print(info, [(k["tile"], k["role"], k.get("on_type"), k.get("off"), k.get("on")) for k in json.load(open(out / "key.json"))])


if __name__ == "__main__":
    main(*sys.argv[1:])
