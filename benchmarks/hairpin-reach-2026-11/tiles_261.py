"""ROADMAP 2.261: the 12 blind tiles over the three fixes (+ controls), cut by the lane report's own `cut_tiles` (one orange box, nothing else
drawn, 600 dpi, the key OUTSIDE the tile folder). Items come from the three lane-report keys and the ON arm's written file.

    python3 benchmarks/hairpin-reach-2026-11/tiles_261.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR  # noqa: E402


def key(n):
    return {t["tile"]: t for t in json.load(open(ROOT / ("out/2.261-fix%d/key.json" % n)))}


k1, k2, k3 = key(1), key(2), key(3)
hosts_on = {h["rg"]: h for h in json.load(open(ROOT / "out/2.261-fix2/work/litolff.on.symbols.json"))["hosts"]}
fix2_target = hosts_on["glyph/6/1/9/10/4"]["box"]
items = [
    # fix 1: where the beam was read as a crescendo (the wedge's old box), and its note
    dict(plate="litolff", page=3, box=[939.0, 1124.0, 968.0, 1136.0], role="case", fix=1, what="beam where a crescendo was read, refused ON",
         rg="glyph/3/0/4/2/100000"),
    dict(k1[5], fix=1, what="eighth again ON (2.78 tile 7)"),
    # fix 1 control: a Brahms hairpin on a detector beam box that must be KEPT
    dict(plate="brahms", page=8, box=[2178.0, 2193.0, 2329.0, 2226.0], role="control", fix=1, what="hairpin kept ON (Brahms p8, on a beam box)",
         rg="glyph/8/0/5/3/100003"),
    # fix 2
    dict(plate="litolff", page=6, box=fix2_target, role="case", fix=2, what="head refused claimed_by:word OFF (2.154 tile 8)", rg="glyph/6/1/9/10/4"),
    dict(k2[11], fix=2, what="note gained"),
    dict(k2[8], fix=2, what="bar 25: written quarter chord OFF, unread bar ON (third head released)"),
    # fix 3
    dict(k3[5], fix=3, what="note gained (pitched in the bass clef)"),
    dict(k3[12], fix=3, what="note gained, half"),
    dict(k3[11], fix=3, what="accidental gained"),
    dict(k3[4], fix=3, what="'clef?' mark lost"),
    # controls
    dict(k2[3], fix=2, what="control beam unchanged"),
    dict(k3[7], fix=3, what="control note unchanged"),
]
out = ROOT / "out" / "print"
out.mkdir(parents=True, exist_ok=True)
LR.cut_tiles(items, out, tile_dir_name="2.261-tiles")
pathlib.Path(out / "2.261-tiles-key.json").write_text(pathlib.Path(out / "key.json").read_text())
(out / "key.json").unlink()
print("12 tiles in", out / "2.261-tiles", "key", out / "2.261-tiles-key.json")
