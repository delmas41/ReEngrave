"""2.279 r3: blind tiles from the lane report's own cutter, restricted to (a) the NEW BLUE notes (12) and (b) the NEW RED pitch-read heads
(up to 4), from the arms already in out/lane-report/2.279-r3/work (--reuse).

usage (repo root): PYTHONPATH=. python3 probe/2.279r3/tiles.py blue|red
Tiles: a page crop with ONE thin orange box and nothing of ours drawn; the key (outside the tile folder) holds what we wrote.
Questions (README): blue "What is the value of the boxed note?"; red "Is this a note, and can you read its value?"
"""
import json
import pathlib
import shutil
import sys

import tools.omr.staged.lane_report as L

KIND = sys.argv[1]
OUT = pathlib.Path("out/print/2.279-r3") / KIND
orig = L.pick_tiles


def pt(ac, asame, seed, n_cases=9, n_controls=3):
    def keep(c):
        if c["kind"] != "note" or c.get("side") != "gained":
            return False
        return (c.get("value") == "unread-value") == (KIND == "red")
    ac = {p: [c for c in v if keep(c)] for p, v in ac.items()}
    return orig(ac, {p: [] for p in asame}, seed, 12 if KIND == "blue" else 4, 0)


L.pick_tiles = pt
tmp = pathlib.Path("out/lane-report/2.279-r3-tiles-" + KIND)
shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir(parents=True)
(tmp / "work").symlink_to(pathlib.Path("out/lane-report/2.279-r3/work").resolve())      # --reuse reads OUT/work
sys.argv = ["lane_report", "--flag", "OMR_VALUE_OPEN_WRITTEN", "--tag", "20261104-night", "--reuse", "--out", str(tmp),
            "--seed", "2279"]
L.main()
OUT.mkdir(parents=True, exist_ok=True)
shutil.rmtree(OUT / "tiles", ignore_errors=True)
shutil.copytree(tmp / "tiles", OUT / "tiles")
shutil.copy(tmp / "key.json", OUT / "key.json")
q = ("What is the value of the boxed note? (quarter, eighth, half, ...; with dots; or: it is not a note)" if KIND == "blue" else
     "Is the boxed mark a note, and can you read its value? (a note and its value, or: not a note)")
(OUT / "tiles" / "README.md").write_text(
    "# 2.279 r3 tiles (%s)\n\nEach picture is a piece of a scanned score page with ONE thin orange box on it and nothing else drawn. "
    "The orange box only says where to look; it means nothing about what we read.\n\n**Question, for every tile:** %s\n\nAnswer by tile number.\n"
    % (KIND, q))
print(json.dumps({"kind": KIND, "tiles": len(json.loads((OUT / "key.json").read_text()))}))
