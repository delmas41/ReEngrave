"""Per-INSTANCE matching version of probe_spec_residual.py.

The original probe (benchmarks/omr-labeling-survey-2026-09/probe_spec_residual.py)
computed unboxed = max(0, sum(teacher_family_detections) - sum(human_family_boxes))
across the WHOLE corpus -- a bulk arithmetic difference, not a per-cell,
per-instance match. This script instead:

  1. Loads the FULL human label file for each cell (all 208-class boxes, not
     just the family-filtered subset) from data/user-labeled/<version>/labels,
     so a key-signature box (keyFlat/keySharp/keyNatural) is visible even
     though it is out of scope for the "accidentals" specialist corpus.
  2. Runs the teacher and keeps only its family-class detections.
  3. Greedily matches each teacher detection to the nearest human box (any
     class) by center distance (in units of average box diagonal), recording:
       - matched to a human box of the SAME family class -> not a miss
       - matched to a human box of a KEY-SIG class (accidentals family only)
         -> key-signature confusion, not a specialist-corpus miss
       - matched to a human box of a DIFFERENT, unrelated class -> other
       - no human box within the match radius -> truly unboxed candidate
  4. Reports the corrected % unboxed next to the original bulk-diff %.

Read-only: does not touch the labels or the corpus, just measures. Requires
the two specialist corpora to exist first:

    python3 benchmarks/omr-labeling-survey-2026-09/build_specialist_versions.py --family rests --out data/specialist-rests
    python3 benchmarks/omr-labeling-survey-2026-09/build_specialist_versions.py --family accidentals --out data/specialist-accidentals
    python3 benchmarks/omr-labeling-survey-2026-09/probe_spec_residual_matched.py rests
    python3 benchmarks/omr-labeling-survey-2026-09/probe_spec_residual_matched.py accidentals

Writes <out_dir>/unmatched_<family>.json and
<out_dir>/keysig_matched_<family>.json (default out_dir /tmp, override with a
second argv) for downstream crop sampling — see UNBOXED-AUDIT.md.
"""
import json, sys, os, glob, math
sys.path.insert(0, os.getcwd())
import cv2
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
# the exact teacher round 6 used (probe_spec_residual.py's own W). Absolute
# path matches that script's own convention: omr-weights/ is gitignored and
# not one of the four assets a worktree symlinks (§5a), so it is only ever
# resolved from the main checkout.
names = json.load(open("tools/omr/training/deepscoresv2_208_classes.json"))

FAM = {
    "rests": {"restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "restHBar"},
    "accidentals": {"accidentalFlat", "accidentalNatural", "accidentalSharp"},
}
KEYSIG = {"keyFlat", "keyNatural", "keySharp"}

det = YoloDetector(W, device="mps")


class Ctx:
    def __init__(s, ys, im):
        s.staff_line_ys_canonical = ys
        s.image = im


def load_full_labels(cid, root_versions):
    """Return list of (class_name, cx, cy, w, h) in NORMALIZED coords, from the
    FULL (unfiltered) data/user-labeled label file for this cell, searching
    every version dir until one has this cell."""
    for v in root_versions:
        p = f"data/user-labeled/{v}/labels/{cid}.txt"
        if os.path.exists(p):
            out = []
            for line in open(p):
                parts = line.split()
                if len(parts) != 5:
                    continue
                cls_id = int(parts[0])
                if cls_id >= len(names):
                    continue
                out.append((names[cls_id], float(parts[1]), float(parts[2]),
                            float(parts[3]), float(parts[4])))
            return out
    return []


def main():
    fam = sys.argv[1] if len(sys.argv) > 1 else "rests"
    cls = FAM[fam]
    root = f"data/specialist-{fam}"
    versions = [l.strip() for l in open(f"{root}/catalog-versions.txt") if l.strip()]

    mans = {}
    for m in glob.glob("benchmarks/**/*cells.json", recursive=True):
        try:
            for e in json.load(open(m)):
                mans.setdefault(e["cell_id"], e)
        except Exception:
            pass

    n_teacher = 0
    n_matched_same = 0
    n_matched_keysig = 0
    n_matched_other = 0
    n_unmatched = 0
    n_human_total = 0
    unmatched_records = []  # for sampling later
    keysig_matched_records = []

    for lab in sorted(glob.glob(f"{root}/*/labels/*.txt")):
        cid = os.path.basename(lab)[:-4]
        img_path = lab.replace("/labels/", "/images/")[:-4] + ".png"
        img = cv2.imread(img_path)
        if img is None:
            continue
        H, Wd = img.shape[:2]

        full_human = load_full_labels(cid, versions)
        n_human_total += sum(1 for (c, *_r) in full_human if c in cls)

        ys = (mans.get(cid) or {}).get("staff_line_ys_canonical") or []
        c = Ctx(ys, img)
        dets = [d for d in det.detect(c, conf_threshold=0.25, imgsz=imgsz_for_cell(c))
                if d.smufl_name in cls]

        # convert human boxes to pixel centers
        hum_px = []
        for (clsname, cx, cy, w, h) in full_human:
            hum_px.append((clsname, cx * Wd, cy * H, w * Wd, h * H))

        used = [False] * len(hum_px)
        for d in dets:
            n_teacher += 1
            dx = d.x_canonical + d.width_canonical / 2
            dy = d.y_canonical + d.height_canonical / 2
            dw = d.width_canonical
            dh = d.height_canonical
            best_i, best_dist, best_cls = -1, 1e9, None
            for i, (hcls, hx, hy, hw, hh) in enumerate(hum_px):
                if used[i]:
                    continue
                dist = math.hypot(dx - hx, dy - hy)
                diag = math.hypot((dw + hw) / 2, (dh + hh) / 2)
                norm = dist / max(diag, 1.0)
                if norm < best_dist:
                    best_dist, best_i, best_cls = norm, i, hcls
            MATCH_RADIUS = 0.6  # fraction of avg box diagonal
            if best_i >= 0 and best_dist <= MATCH_RADIUS:
                used[best_i] = True
                if best_cls in cls:
                    n_matched_same += 1
                elif best_cls in KEYSIG:
                    n_matched_keysig += 1
                    keysig_matched_records.append({
                        "cid": cid, "img": img_path, "cls": d.smufl_name,
                        "conf": float(d.confidence),
                        "bbox": [d.x_canonical, d.y_canonical,
                                 d.x_canonical + d.width_canonical,
                                 d.y_canonical + d.height_canonical],
                        "matched_human_cls": best_cls, "dist": best_dist,
                    })
                else:
                    n_matched_other += 1
            else:
                n_unmatched += 1
                unmatched_records.append({
                    "cid": cid, "img": img_path, "cls": d.smufl_name,
                    "conf": float(d.confidence),
                    "bbox": [d.x_canonical, d.y_canonical,
                             d.x_canonical + d.width_canonical,
                             d.y_canonical + d.height_canonical],
                    "nearby_human": hum_px[best_i][0] if best_i >= 0 else None,
                    "nearby_human_dist": best_dist if best_i >= 0 else None,
                })

    print(f"family={fam}")
    print(f"human boxes (family-scope, from FULL label files): {n_human_total}")
    print(f"teacher detections (family classes): {n_teacher}")
    print(f"  matched same-family human box:  {n_matched_same}")
    print(f"  matched KEY-SIG human box:       {n_matched_keysig}")
    print(f"  matched OTHER-class human box:   {n_matched_other}")
    print(f"  UNMATCHED (candidate miss):      {n_unmatched}")
    if n_teacher:
        print(f"corrected %% unboxed (unmatched/teacher): {n_unmatched/n_teacher*100:.0f}%")
        naive_bulk = max(0, n_teacher - n_human_total)
        print(f"naive bulk-diff %% unboxed (original probe formula): {naive_bulk/n_teacher*100:.0f}%")

    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp"
    out_json = f"{out_dir}/unmatched_{fam}.json"
    json.dump(unmatched_records, open(out_json, "w"), indent=1)
    print(f"wrote {len(unmatched_records)} unmatched records -> {out_json}")

    out_json2 = f"{out_dir}/keysig_matched_{fam}.json"
    json.dump(keysig_matched_records, open(out_json2, "w"), indent=1)
    print(f"wrote {len(keysig_matched_records)} keysig-matched records -> {out_json2}")


if __name__ == "__main__":
    main()
