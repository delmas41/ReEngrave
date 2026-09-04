"""Pick training cells BECAUSE they contain the symbols the fine-tune suppresses.

Round 3 measured the failure precisely: on the Simrock/Dvorak benchmark page the
fine-tuned model emitted **0 slurs, 0 ties, 0 accidentals, 0 augmentation dots**
against a truth holding 36 slurs and 7 accidentals, and 94 rests against 152 —
while production got the accidentals exactly right. The cause is in our own
labeling table: Simrock's 13 cells contributed **1 accidental box and 0 rests**,
because the hollow batches selected SPARSE, hollow-notehead-bearing cells, i.e.
sustained passages that contain almost no rests or accidentals by construction.
So the fine-tune learned "on pages like this, those symbols do not occur."

⚠️ THE OBVIOUS NEXT BATCH REPRODUCES THE BUG. Cutting more cells by position
gave 354 noteheads / 6 rests / 1 accidental / 0 slurs over 60 Simrock cells —
more notehead-only data, which would drive the suppressed classes to zero
HARDER. The selection criterion has to invert.

This ranks a wide candidate pool by how much SUPPRESSED-CLASS content each cell
holds (rests, accidentals, slurs, ties, dots, dynamics), with noteheads counted
only as a tie-break, and keeps the richest N. It is the same "rank a pool, keep
the useful tail" move `rank_and_trim.py` makes for sparse cells, pointed the
other way.

⚠️ Ranking uses the CURRENT PRODUCTION detector, so it inherits that detector's
blind spots: a class production cannot see cannot be ranked for. It biases the
batch toward symbols production finds, which is acceptable here because the
regression is precisely that the FINE-TUNE stopped finding what production
finds. It would NOT be acceptable as a way to choose cells for a class the
detector has never read.

    python3 .../rank_by_suppressed.py --pool /tmp/pool-simrock --keep 60 \
        --out benchmarks/omr-labeling-simrock-2026-09
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, collections
from pathlib import Path
sys.path.insert(0, os.getcwd())
from tools.omr.yolo_detector import YoloDetector
from tools.omr.annotate.build_template import _load_cell_from_manifest

W = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
     "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt")
SUPPRESSED = ("rest", "accidental", "key", "slur", "tie", "augmentationdot", "dynamic")

def norm(n): return "".join(c for c in (n or "").lower() if c.isalnum())

def score(dets):
    s = collections.Counter()
    for d in dets:
        k = norm(getattr(d, "smufl_name", ""))
        if "notehead" in k: s["notehead"] += 1
        elif any(t in k for t in SUPPRESSED): s["suppressed"] += 1
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", type=int, default=60)
    ap.add_argument("--conf", type=float, default=0.45)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()
    pool = Path(a.pool); out = Path(a.out)
    man = json.loads((pool / "cells.json").read_text())
    det = YoloDetector(W, device=a.device); root = Path.cwd()
    scored = []
    for i, e in enumerate(man):
        try:
            cell = _load_cell_from_manifest(e, root)
            dets = det.detect(cell, conf_threshold=a.conf, imgsz=None)
        except Exception:
            continue
        s = score(dets)
        scored.append((s["suppressed"], s["notehead"], e))
        if (i + 1) % 50 == 0:
            print(f"  scored {i+1}/{len(man)}", flush=True)
    scored.sort(key=lambda t: (-t[0], -t[1]))
    keep = scored[:a.keep]
    print(f"\npool {len(scored)} cells -> keeping {len(keep)}")
    print(f"  suppressed-class boxes in kept: {sum(k[0] for k in keep)} "
          f"(pool total {sum(s[0] for s in scored)})")
    print(f"  noteheads in kept:              {sum(k[1] for k in keep)}")
    print(f"  cells with ZERO suppressed:     {sum(1 for k in keep if k[0]==0)} of {len(keep)}")
    for sub in ("cells", "verdicts", "detections"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    entries = []
    for supp, nh, e in keep:
        cid = e["cell_id"]
        for src_key, suffix in (("cell_png_path", ""), ("nostaff_png_path", "_nostaff")):
            src = e.get(src_key)
            if src and Path(src).exists():
                shutil.copyfile(src, out / "cells" / f"{cid}{suffix}.png")
        e = dict(e)
        e["cell_png_path"] = f"{out}/cells/{cid}.png"
        if (out / "cells" / f"{cid}_nostaff.png").exists():
            e["nostaff_png_path"] = f"{out}/cells/{cid}_nostaff.png"
        e["_suppressed_score"] = supp
        entries.append(e)
    (out / "cells.json").write_text(json.dumps(entries, indent=1))
    print(f"wrote {out}/cells.json")

if __name__ == "__main__":
    main()
