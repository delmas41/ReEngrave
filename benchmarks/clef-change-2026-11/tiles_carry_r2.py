"""2.251 carry round 2: blind tiles for what round 2 newly STOPPED (the heads go red "clef?", no pitch written): heads after the bar-111
bass clef (Litolff p4 s1 bassoon; its dots fused with the heads, the F body alone stops the carry) and after the Vc bar-346 bass clef
(p12 s0 staff 10; two witnesses below READ, a strong candidate). Each tile one staff, from the clef in force to the head, one thin orange
box on the head; plus the bar-111 mark itself ("is this a clef? which?"). Heads from the night record's detector boxes (score >= 0.6),
right of the stop. Key outside tiles/.

python3 work-2.251/tiles_carry_r2.py BOXES.jsonl OUTDIR SEED
"""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import scan_claims as SC  # noqa: E402
import tiles_carry as TC  # noqa: E402  (draw)

# (place, page, system, staff, crop-from x (the clef in force), stop x, cells, what stops it)
PLACES = [
    ("bar 111", 4, 1, 3, 2300, 2390, (13, 14), "Fag: bass clef whose dots touch the heads; F body alone (0.73) -> candidate"),
    ("Vc bar 346", 12, 0, 10, 1440, 1495, (7, 8, 9, 10, 11, 12), "Vc: bass clef, dots + body 0.69 (below READ 0.70) -> strong candidate"),
]
CLEF_TILES = [dict(kind="clef", plate="litolff", page=4, system=1, staff=3, box=[2300, 2575, 2386, 2640],
                   note="bar 111: the mark the F body matched (no dots read) -- stops the carry")]


def main():
    bpath, out, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    rng = random.Random(seed)
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    boxes = SC.load_boxes(bpath)
    pick = list(CLEF_TILES)
    for name, pg, s, li, cx, stop, cells, why in PLACES:
        ly = TC.staff_lines("litolff", pg, s, li)
        sp = (ly[4] - ly[0]) / 4.0
        # the staff's OWN heads (a padded cell also boxes the neighbour staves' heads): centre within 1.5 sp of the staff
        heads = [b for b in boxes.get((pg, s, li), []) if b[0].startswith("notehead") and (b[2] or 0) >= 0.6 and b[3] in cells
                 and (b[1][0] + b[1][2]) / 2 > stop and ly[0] - 1.5 * sp <= (b[1][1] + b[1][3]) / 2 <= ly[4] + 1.5 * sp]
        seen, uniq = set(), []
        for h in sorted(heads, key=lambda b: b[1][0]):
            k = (round(h[1][0] / 10), round(h[1][1] / 10))
            if k not in seen:
                seen.add(k)
                uniq.append(h)
        for h in rng.sample(uniq, min(4, len(uniq))):
            pick.append(dict(kind="head", plate="litolff", page=pg, system=s, staff=li, cell=h[3], subject=h[4], place=name,
                             box=[round(float(v), 1) for v in h[1]], clef_x=cx, why=why, written="nothing (red clef?)"))
    rng.shuffle(pick)
    key = []
    for i, t in enumerate(pick, 1):
        if t["kind"] == "head":
            im = TC.draw(t["plate"], t["page"], t["system"], t["staff"], t["clef_x"], t["box"][2], t["box"])
        else:
            im = TC.draw(t["plate"], t["page"], t["system"], t["staff"], t["box"][0] - 64, t["box"][2] + 32, t["box"])
        im.save(os.path.join(out, "tiles", "%02d.png" % i))
        key.append(dict(tile=i, **t))
    json.dump({"seed": seed, "what": "2.251 carry round 2: heads newly STOPPED (written red 'clef?', no pitch) after bar 111 and Vc bar 346, "
               "plus the bar-111 mark", "tiles": key}, open(os.path.join(out, "key.json"), "w"), indent=1)
    with open(os.path.join(out, "QUESTION.txt"), "w") as fh:
        fh.write("Tiles with a box on a NOTE: What note is in the box (name and octave if you can), and which clef is it read in?\n"
                 "Tile with a box on a clef-sized mark: Is this a clef? Which one?\n"
                 "The orange box is the only thing drawn; everything else is the print.\n")


if __name__ == "__main__":
    main()
