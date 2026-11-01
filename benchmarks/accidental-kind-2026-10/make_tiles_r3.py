"""2.247 r3: one blind tile per OTHER place whose written sign the r3 fix moves (b -> natural vs r2), besides Sean's r2 tile 12.
usage: make_tiles_r3.py TYPE_CONTROL_R2.json OUT_DIR SUBJECT [SUBJECT ...] (plate:subject)"""
import json
import pathlib
import sys

sys.path.insert(0, ".")
from tools.omr.staged import lane_report as LR  # noqa: E402

QUESTION = "Is the mark in the orange box a sharp, a flat or a natural? (Or part of one -- say which -- or not an accidental at all.)"


def main(tc_path, out_dir, *subjects):
    tc = {(c["plate"], c["subject"]): c for c in json.load(open(tc_path))}
    items = []
    for ps in subjects:
        plate, s = ps.split(":")
        c = tc[(plate, s)]
        items.append(dict(plate=plate, page=c["page"], box=[round(v, 1) for v in c["page_box"]], role="r3-moved", subject=s, cls=c["cls"],
                          r2_written=c["alt_on"], r3_written="natural", features_r2=c["features_on"]))
    out = pathlib.Path(out_dir)
    print(LR.cut_tiles(items, out))
    (out / "tiles" / "README.md").write_text(
        "# 2.247 round 3: blind tiles\n\nEach picture is a piece of a scanned score page with ONE thin orange box and nothing else drawn. "
        "The box only says where to look.\n\n**Question, for every tile:** " + QUESTION + "\n\nAnswer by tile number.\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
