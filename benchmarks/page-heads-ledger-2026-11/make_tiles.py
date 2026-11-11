"""ROADMAP 2.290 r1 -- Sean's 12 BLIND tiles on head boxes (one thin orange box, nothing else drawn; the key one level above the tiles folder).

    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/make_tiles.py OUTDIR FATES_DIR [SEED=2290]

SELECTION RULE (stated, seeded): from the head boxes the replay (`replay_head_fates.py`) found on the frozen-sample pages Litolff 2,4,6,10 and Brahms 0,5 (the
`*.twin.json` files in FATES_DIR), `random.Random(SEED)` draws, per stratum in the order below, from the boxes of that stratum, sorted by (plate, page, glyph key):
  9 CASES  Litolff refused `claimed_by:page_claim` x2 | Litolff `owned_by_another_staff` with no written box on the ink x1 | Brahms the same x1 |
           Litolff `clipped_fragment` x1 | Brahms `clipped_fragment` x1 | Litolff twin-type drop (`mark_group_duplicate` / `stacked_head_duplicate` /
           `notehead_is_a_duplicate_box`) whose nearest written box has IoU 0.1-0.5 x1 | Litolff `too_narrow` x1 | Brahms `claimed_by:barline` x1
  3 CONTROLS  boxes WRITTEN (plain), Litolff x2, Brahms x1.
The orange box is the detector's own head box, as it stands (thin, never wider than the tile); nothing of ours is drawn. The key (fate, class, strata, glyph key) is
written to OUTDIR/key.json, one level above OUTDIR/tiles/. QUESTION for every tile: is the boxed mark ONE notehead? Filled or hollow? Is there a second head touching it?
"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
UNIT = {"litolff": 15.75, "brahms": 32.0}
TWINISH = ("mark_group_duplicate", "stacked_head_duplicate", "notehead_is_a_duplicate_box")


def load(d, plate, names):
    out = []
    for n in names:
        for r in json.load(open(os.path.join(d, n))):
            out.append(dict(r, plate=plate))
    return sorted(out, key=lambda r: (r["plate"], int(r["sub"].split("/")[1]), r["sub"]))


def main(out, d, seed):
    from tools.omr.preprocessing import render_page
    L = load(d, "litolff", ["fates_lit_2_10.twin.json", "fates_lit_4_6.twin.json"])
    B = load(d, "brahms", ["fates_brh_0.twin.json", "fates_brh_5.twin.json"])
    strata = [
        ("page_claim", L, lambda r: "claimed_by:page_claim" in r["fate"], 2),
        ("owned_orphan", L, lambda r: r["fate"] == "owned_by_another_staff" and r.get("_best_iou", 1) < 0.1, 1),
        ("owned_orphan", B, lambda r: r["fate"] == "owned_by_another_staff" and r.get("_best_iou", 1) < 0.1, 1),
        ("clipped_fragment", L, lambda r: "clipped_fragment" in r["fate"], 1),
        ("clipped_fragment", B, lambda r: "clipped_fragment" in r["fate"], 1),
        ("twin_low_iou", L, lambda r: any(t in r["fate"] for t in TWINISH) and 0.1 <= r.get("_best_iou", 1) < 0.5, 1),
        ("too_narrow", L, lambda r: "too_narrow" in r["fate"], 1),
        ("claimed_by_barline", B, lambda r: "claimed_by:barline" in r["fate"], 1),
        ("control_written", L, lambda r: r["fate"] == "written", 2),
        ("control_written", B, lambda r: r["fate"] == "written", 1),
    ]
    rng = random.Random(seed)
    picks = []
    for name, pool_all, pred, k in strata:
        pool = [r for r in pool_all if pred(r)]
        for r in rng.sample(pool, k):
            picks.append((name, len(pool), r))
    rng.shuffle(picks)                       # tile order carries no information
    tdir = os.path.join(out, "tiles")
    os.makedirs(tdir, exist_ok=True)
    for f in os.listdir(tdir):
        os.remove(os.path.join(tdir, f))
    cache, key = {}, []
    for n, (name, npool, r) in enumerate(picks, 1):
        pg = int(r["sub"].split("/")[1])
        k = (r["plate"], pg)
        if k not in cache:
            cache.clear()
            cache[k] = Image.fromarray(render_page(PDF[r["plate"]], pg, dpi=600).rgb).convert("RGB")
        im = cache[k]
        u = UNIT[r["plate"]]
        b = r["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        x0, y0, x1, y1 = max(0, int(cx - 6 * u)), max(0, int(cy - 3.2 * u)), int(cx + 6 * u), int(cy + 3.2 * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=max(1, int(u / 12)))
        crop = crop.resize((600, int(600 * crop.height / crop.width)))
        crop.save(os.path.join(tdir, "tile_%02d.png" % n))
        key.append(dict(tile=n, stratum=name, stratum_pool=npool, plate=r["plate"], page=pg, glyph=r["sub"], fate=r["fate"],
                        detector_class=r["cls"][0] if isinstance(r["cls"], list) else r["cls"], conf=r.get("conf"), page_box=r["box"],
                        nearest_written_iou=r.get("_best_iou"), crop_origin=[x0, y0], seed=seed))
    json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1, default=str)
    open(os.path.join(tdir, "README.md"), "w").write(
        "# 2.290 r1 -- head boxes\n\nEach picture is a piece of a scanned score with ONE thin orange box on it and nothing else drawn. The box is a place to look; it "
        "says nothing about what we read.\n\n**Question, for every tile:** is the boxed mark ONE notehead? If yes, filled or hollow? Is there a second head touching it? "
        "If it is not a notehead, what is it (part of a letter, a barline, a piece of a head, a beam, ...)?\n\nAnswer by tile number.\n")
    print("tiles", len(key), "->", tdir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2290)
