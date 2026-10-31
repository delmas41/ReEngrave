"""ROADMAP 2.237: Sean's 12 blind tiles on the boxes where an old pair rule and the stroke owner DISAGREE.

    python3 benchmarks/rule-page/rule_tiles.py PARITY.json SLICE_TAG OUT_DIR

One tile per place, one staff each (no two tiles on one staff), a thin orange box sized to the box the OLD RULE refused and ownership would
keep (the `examples` in PARITY.json: boxes ownership OWNS alone), nothing else drawn. Question for every tile: "which box is the note?" for a
head/rest rule, "what is this ink?" for an accidental. key.json (rule, plate, ownership's reading) is written OUTSIDE the tile folder
by `lane_report.cut_tiles`. Seed 2237; the quota is by rule family, biggest disagreeing rules first.
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.staged import lane_report as LR  # noqa: E402

#: (rule key in PARITY.json examples, plate, how many tiles)
QUOTA = [
    ("notehead_is_not_a_notehead|stacked_head_duplicate", "litolff", 1),
    ("notehead_is_not_a_notehead|notehead_is_a_duplicate_box", "litolff", 1),
    ("notehead_is_not_a_notehead|on_a_dynamic_letter", "litolff", 1),
    ("notehead_is_not_a_notehead|on_a_dynamic_letter", "brahms", 1),
    ("rest_is_not_a_rest|rest_stroke_into_a_head", "litolff", 1),
    ("rest_is_not_a_rest|rest_stroke_into_a_head", "brahms", 1),
    ("rest_is_not_a_rest|rest_is_a_duplicate_box", "brahms", 1),
    ("notehead_is_not_a_notehead|is_a_rest_shape", "litolff", 1),
    ("accidental_owner|on_a_rest", "brahms", 1),
    ("notehead_is_not_a_notehead|belongs_to_a_nearer_staff", "brahms", 1),
    ("notehead_is_not_a_notehead|head_cut_piece", "brahms", 1),
    ("notehead_is_not_a_notehead|on_a_rest", "brahms", 1),
]


def staff_of(key):
    p = key.split("/")
    return (p[1], p[2], p[3])


def main():
    parity = json.load(open(sys.argv[1]))
    tag = sys.argv[2]
    out = pathlib.Path(sys.argv[3])
    rng = random.Random(2237)
    pick = []
    used = set()
    for rule, plate, n in QUOTA:
        pool = list(parity[plate]["examples"].get(rule, []))
        rng.shuffle(pool)
        got = 0
        for k in pool:
            st = (plate,) + staff_of(k)
            if st in used:
                continue
            used.add(st)
            pick.append((rule, plate, k))
            got += 1
            if got == n:
                break
        if got < n:
            print("short of examples for", rule, plate, file=sys.stderr)
    boxes = {}
    for plate in ("litolff", "brahms"):
        want = {k for _r, p, k in pick if p == plate}
        d = LR.slice_dir(plate, tag)
        with open(d / "observations.jsonl") as fh:
            for line in fh:
                if '"glyph/' not in line:
                    continue
                o = json.loads(line)
                if o.get("subject") in want and o.get("quantity") == "glyph_box":
                    b = (o.get("detail") or {}).get("bbox_page_px")
                    if isinstance(b, list) and len(b) == 4:
                        boxes[(plate, o["subject"])] = dict(box=[float(x) for x in b], cls=(o["value"][0] if o.get("value") else None))
    items = []
    for rule, plate, k in pick:
        b = boxes.get((plate, k))
        if not b:
            print("no box for", plate, k, file=sys.stderr)
            continue
        items.append(dict(plate=plate, page=LR.page_of(k), box=b["box"], rg=k, kind=b["cls"], role="case", rule=rule,
                          question="which box is the note?" if not rule.startswith("accidental") else "what is this ink?",
                          ownership="the stroke owner keeps this box (it owns ink the old rule refused)"))
    rng.shuffle(items)
    print(json.dumps(LR.cut_tiles(items, out)))


if __name__ == "__main__":
    main()
