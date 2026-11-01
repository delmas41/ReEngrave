"""2.247: 12 blind tiles for Sean -- "is this a sharp, a flat or a natural?" -- one thin orange box on the accidental-family box, nothing else.
Drawn from: (a) the 2.242 r2 tile 1 place (detector 'flat', strokes 'natural'); (b) every box whose WRITTEN alteration the flag changes; (c) the
accidental boxes in front of the notes the flag turned blue; (d) the rest from places where the detector class and the stroke type disagree on
the night census (Brahms natural->flat stubs, sharp->flat, Litolff flat->natural), seed 2247. Key OUTSIDE the tile folder.
usage: make_tiles.py TYPE_CONTROL.json UNJUDGED_KEY.json CENSUS.json OUT_DIR"""
import json
import pathlib
import random
import sys

sys.path.insert(0, ".")
from tools.omr.staged import lane_report as LR  # noqa: E402

QUESTION = "Is the mark in the orange box a sharp, a flat or a natural? (Or part of one -- say which -- or not an accidental at all.)"


def main(tc_path, unj_path, census_path, out_dir):
    tc = json.load(open(tc_path))
    unj = json.load(open(unj_path))
    cen = json.load(open(census_path))
    items, used = [], set()

    def add(plate, page, box, role, **kw):
        key = (plate, page, round(box[0] / 8), round(box[1] / 8))
        if key in used or len(items) >= 12:
            return
        used.add(key)
        items.append(dict(plate=plate, page=page, box=[round(v, 1) for v in box], role=role, **kw))

    add("litolff", 2, [1025.67, 2519.15, 1038.11, 2567.82], "2.242r2-tile1", subject="glyph/2/1/3/4/5", cls="accidentalFlat", strokes="natural")
    for c in tc:
        if c["alt_off"] != c["alt_on"] and c["page_box"]:
            add(c["plate"], c["page"], c["page_box"], "written-changed", subject=c["subject"], cls=c["cls"], off=c["alt_off"], on=c["alt_on"])
    for u in unj:
        nb = u["box"]
        u_unit = LR.PLATES["litolff"]["unit"]
        near = [c for c in tc if c["plate"] == "litolff" and c["page"] == u["page"] and c["page_box"]
                and -0.5 * u_unit <= nb[0] - c["page_box"][2] <= 3 * u_unit and c["page_box"][3] > nb[1] - 2 * u_unit and c["page_box"][1] < nb[3] + 2 * u_unit]
        if near:
            c = near[0]
            add("litolff", u["page"], c["page_box"], "blue-gained", subject=c["subject"], cls=c["cls"], note=u["rg"], on_why=c["on_why"])
    rng = random.Random(2247)
    # (b2) boxes the flag turned from 'flat' to unclear (written value unchanged, now GUESSED flat/natural): 3 of them, one per plate first
    now_unclear = [c for c in tc if c["alt_off"] == c["alt_on"] and c["page_box"]]
    rng.shuffle(now_unclear)
    for c in sorted(now_unclear, key=lambda c: c["plate"] != "brahms")[:1] + [c for c in now_unclear if c["plate"] == "litolff"][:2]:
        add(c["plate"], c["page"], c["page_box"], "now-unclear", subject=c["subject"], cls=c["cls"], on_why=c["on_why"])
    pools = [("brahms", "natural", "flat"), ("brahms", "sharp", "flat"), ("litolff", "flat", "natural"), ("litolff", "natural", "flat"),
             ("brahms", "flat", "natural")]
    by = {p: [r for r in cen if (r["plate"], r["dt"], r["t"]) == p and r.get("page_box")] for p in pools}
    for p in by:
        rng.shuffle(by[p])
    i = 0
    while len(items) < 12 and any(by.values()):
        p = pools[i % len(pools)]
        if by[p]:
            r = by[p].pop()
            add(r["plate"], r["page"], r["page_box"], "class-vs-strokes", subject=r["subject"], cls=r["cls"], strokes=r["t"])
        i += 1
    rng.shuffle(items)
    out = pathlib.Path(out_dir)
    info = LR.cut_tiles(items, out)
    (out / "tiles" / "README.md").write_text(
        "# 2.247 accidentals by their shape: 12 blind tiles\n\nEach picture is a piece of a scanned score page with ONE thin orange box and "
        "nothing else drawn. The box only says where to look.\n\n**Question, for every tile:** " + QUESTION +
        "\n\nAnswer by tile number (e.g. `1 natural, 2 flat, 3 part of a natural ...`).\n")
    print(info, [(k["tile"], k["role"]) for k in json.load(open(out / "key.json"))])


if __name__ == "__main__":
    main(*sys.argv[1:])
