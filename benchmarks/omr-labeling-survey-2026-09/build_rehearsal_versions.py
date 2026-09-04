"""Rehearsal labels: let the TEACHER speak where no labeling pass ever looked.

**The measurement this exists for.** On the 5-page scan benchmark the round-4
checkpoint emits **967 raw detections against production's 3204**
(`probe_confidence_shift.py`), and its median confidence is HIGHER (0.693 vs
0.604) — so nothing merely slipped under the 0.25 threshold, the detections are
gone. The classes are gone whole: production reads restWhole 396, tie 249, slur
184, augmentationDot 150, ledgerLine 288, beam 188; round-4 reads none of them
in its top fifteen. That is catastrophic forgetting of class families, and it is
what "the fine-tune suppresses detection" has meant all along.

**Why completing the labels did not fix it, and this might.** Round 4 completed
the cells and moved the number 3%. It could not have done more: a labeling pass
sweeps ONE symbol kind over a cell set, and the campaign's own stamps say what
was swept — 603 cells for hollow noteheads, 409 for rests+accidentals, 255 for
grace, 46 for clefs, and only 109 + 55 under a rich or full palette. Slurs,
ties, dynamics, beams and ledger lines were never swept on most cells, so on
most cells they are BACKGROUND, and the loss teaches exactly that.

Rehearsal is the standard remedy — mix the old task back so it is refreshed
rather than overwritten — and DeepScoresV2 is not on this machine (destroyed
2026-08-28, `tools/omr/training/data/README-RESTORE.md`; re-preparing it is a
many-hour download). But rehearsal does not need the old IMAGES, it needs the
old BEHAVIOUR, and the teacher can supply that on the images we already have.
So the production checkpoint reads each training cell and its confident
detections are appended as labels — **only for classes that cell's own passes
never looked for.**

⚠️ **Coverage is per CELL, not per corpus.** The corpus-level version of this
rule is wrong and would have kept the worst case: v22 draws 37 slurs, so `slur`
is "used in the corpus", so a corpus rule stays silent on slurs — in the 640
cells that were never swept for one, where their silence is the whole defect.
A class is covered for a cell if the cell holds a human box of it, or if a pass
stamped in that cell's `inspected_passes` had it in its palette.

⚠️ **A cell with no pass stamps at all is treated as fully covered.** v1-v4 are
old TRIAGE batches: the human ruled on every model detection, including `beam`,
`ledgerLine`, `staff` and `stem` boxes that later policy stopped drawing. Their
silence is a decision, so the teacher does not overrule it.

⚠️ **Never over a human box** — a teacher detection overlapping one is dropped
whatever its class, so the human's class wins on contested ink.

⚠️ **`beam` and `ledgerLine` ARE rehearsed, and that reverses a labeling-policy
assumption.** CLAUDE.md tells a human to skip them because a human cannot bbox a
thin line — true, and it silently became "they may train as background". But the
pipeline CONSUMES both: `rhythm.resolve_rhythms_for_cell` keeps a YOLO beam
wherever no CV beam overlaps it (worth pooled 0.1917 -> 0.1861), and
`transcribe`'s ledger-ladder arbitration reads `ledgerLine` detections directly
(worth 0.1506 -> 0.1431). Round-4 emits 14 ledger lines where production emits
288, so on those checkpoints the ladder rule is dead. The teacher can draw what
a human cannot. Only `staff`/`staffLine` stay out — a full-cell box is
degenerate as a training target.

⚠️ This is DISTILLATION and inherits the teacher's false positives. That is the
trade being measured, not a defect being hidden: the arm is gated against
production on both axes like every other one.

    python3 .../build_rehearsal_versions.py --dry-run --report /tmp/reh.json
    python3 .../build_rehearsal_versions.py --out data/user-labeled-rehearsal
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

REPO = Path.cwd()
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
TEACHER = MAIN / "omr-weights" / "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"
PASS_CONFIGS = REPO / "benchmarks" / "omr-labeling-survey-2026-09" / "pass-configs"

# A full-cell box is a degenerate training target; everything else the teacher
# reads is rehearsed. See the module docstring for why beam/ledgerLine are IN.
NEVER_REHEARSE = {"staff", "staffLine", "staffline"}

# Passes stamped in verdicts that have no config file. Each palette is the
# classes that pass was looking for — deliberately narrow, because a class
# wrongly listed here silences the teacher on it.
EXTRA_PALETTES = {
    "hollow noteheads": {"noteheadHalfOnLine", "noteheadHalfInSpace",
                         "noteheadWholeOnLine", "noteheadWholeInSpace"},
    "grace noteheads": {"noteheadBlackOnLineSmall", "noteheadBlackInSpaceSmall",
                        "noteheadHalfOnLineSmall", "noteheadHalfInSpaceSmall"},
    "clefs": {"clefG", "clefF", "clefC", "clefCAlto", "clefCTenor",
              "clefG8vb", "clefG8va", "clefF8vb", "clefUnpitchedPercussion"},
}


def palette_from_config(path: Path) -> tuple[str, set[str]]:
    d = json.loads(path.read_text())
    out: set[str] = set()
    for slot in (d.get("classes") or d.get("active_classes") or []):
        if isinstance(slot, str):
            out.add(slot)
        else:
            for k in ("name", "on_line", "in_space"):
                if slot.get(k):
                    out.add(slot[k])
    return d.get("pass_name") or path.stem, out


def load_palettes() -> dict[str, set[str]]:
    palettes = dict(EXTRA_PALETTES)
    for p in sorted(PASS_CONFIGS.glob("*.json")):
        name, classes = palette_from_config(p)
        palettes[name] = classes
    # the round-3 stamp is "completion"; its palette is completion-full's
    if "completion-full" in palettes:
        palettes.setdefault("completion", palettes["completion-full"])
    return palettes


def iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    return inter / (aw * ah + bw * bh - inter)


def stamp_index() -> dict[str, set[str]]:
    """cell_id -> every pass ever stamped on it, from ANY batch on disk.

    ⚠️ The merged verdict trees a version is BUILT from (`phase3-merged/`,
    `phase4-merged/`) carry only `cell_id` + boxes — the merge scripts rebuild a
    minimal file and `inspected_passes` does not survive it. The stamps live in
    the batch the cells were labeled in. Reading only the version's own
    `verdicts_dir` therefore finds zero stamps on all 591 cells and silently
    turns this whole tool into a no-op, which is exactly what it did on the
    first run. So the index is global and unioned across every batch.
    """
    import glob
    out: dict[str, set[str]] = collections.defaultdict(set)
    pats = ["benchmarks/*/verdicts/*.verdict.json",
            "benchmarks/*/*/verdicts/*.verdict.json",
            "benchmarks/*/*/*/verdicts/*.verdict.json"]
    for pat in pats:
        for f in glob.glob(pat):
            try:
                v = json.loads(Path(f).read_text())
            except Exception:
                continue
            cid = v.get("cell_id") or Path(f).name.split(".verdict")[0]
            for s in (v.get("inspected_passes") or []):
                out[cid].add(s)
    return out


def read_versions_manifest(root: Path) -> list[str]:
    out = []
    for line in (root / "catalog-versions.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def load_labels(p: Path):
    rows = []
    if not p.exists():
        return rows
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) == 5:
            rows.append((int(parts[0]), *(float(x) for x in parts[1:])))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=REPO / "data" / "user-labeled")
    ap.add_argument("--out", type=Path,
                    default=REPO / "data" / "user-labeled-rehearsal")
    ap.add_argument("--teacher", type=Path, default=TEACHER)
    ap.add_argument("--conf", type=float, default=0.50,
                    help="teacher confidence floor — the floor the labeling "
                         "pre-filter and residual_background both use.")
    ap.add_argument("--iou", type=float, default=0.20)
    ap.add_argument("--scope", choices=("pass", "all"), default="pass",
                    help="'pass' (default) keeps a teacher box only for a "
                         "class this cell has no human box of AND no stamped "
                         "pass looked for — the conservative reading, in which "
                         "a human's silence inside a class they swept is a "
                         "decision. 'all' keeps every teacher box no human box "
                         "already claims, on every cell including the "
                         "unstamped v1-v4: full distillation with human "
                         "corrections layered on top. The two differ in what "
                         "they assume a blank patch of a swept cell MEANS, "
                         "which is exactly the open question — so they are "
                         "separate arms and not a tuning knob.")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", type=Path, default=None)
    a = ap.parse_args()

    names = json.loads(CLASS_NAMES_JSON.read_text())
    name_to_id = {n: i for i, n in enumerate(names)}
    palettes = load_palettes()
    stamps_by_cell = stamp_index()
    versions = read_versions_manifest(a.root)
    print(f"versions: {len(versions)}   palettes: {sorted(palettes)}")
    print(f"cells with a pass stamp somewhere on disk: {len(stamps_by_cell)}")
    unknown = {s for ss in stamps_by_cell.values() for s in ss} - set(palettes)
    if unknown:
        print(f"  ⚠️ stamped passes with NO palette (treated as covering "
              f"nothing, so the teacher speaks freely there): {sorted(unknown)}")

    from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell
    import cv2

    class _Cell:  # imgsz_for_cell / detect read only these two
        def __init__(self, ys, image):
            self.staff_line_ys_canonical = ys
            self.image = image

    det = YoloDetector(str(a.teacher), device=a.device)

    added = collections.Counter()
    silenced = collections.Counter()
    over_human = collections.Counter()
    n_cells = n_human = n_nostamp = 0
    per_version: dict[str, dict] = {}

    for v in versions:
        vdir = a.root / v
        meta = json.loads((vdir / "metadata.json").read_text())
        src = meta.get("source", {})
        man_path = REPO / (src.get("manifest") or "")
        manifest = ({e["cell_id"]: e for e in json.loads(man_path.read_text())}
                    if man_path.exists() else {})
        vpath = REPO / (src.get("verdicts_dir") or "")
        if not manifest:
            print(f"  WARN {v}: manifest missing ({man_path}) — auto imgsz")

        odir = a.out / v
        if not a.dry_run:
            (odir / "images").mkdir(parents=True, exist_ok=True)
            (odir / "labels").mkdir(parents=True, exist_ok=True)

        v_added = v_cells = v_nostamp = 0
        for img_path in sorted((vdir / "images").glob("*.png")):
            cid = img_path.stem
            human = load_labels(vdir / "labels" / f"{cid}.txt")
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            h, w = img.shape[:2]
            n_cells += 1
            v_cells += 1
            n_human += len(human)

            # --- what did a pass look for in THIS cell? --------------------
            stamps = sorted(stamps_by_cell.get(cid, ()))
            # ⚠️ In 'all' scope the human-class rule comes off too, not just
            # the palette. Leaving it on made the two scopes near-identical
            # (v14: +68 vs +70 boxes) — because most silencing came from "this
            # cell already has a box of that class", not from the palette — and
            # two arms that measure the same thing are one arm.
            covered = ({names[c] for c, *_ in human if 0 <= c < len(names)}
                       if a.scope == "pass" else set())
            if a.scope == "pass":
                for st in stamps:
                    covered |= palettes.get(st, set())
            no_stamp = not stamps and a.scope == "pass"
            if no_stamp:
                n_nostamp += 1
                v_nostamp += 1

            extra = []
            if not no_stamp:
                ys = (manifest.get(cid) or {}).get("staff_line_ys_canonical") or []
                cell = _Cell(ys, img)
                dets = det.detect(cell, conf_threshold=a.conf,
                                  imgsz=imgsz_for_cell(cell))
                human_boxes = [((cx - bw / 2) * w, (cy - bh / 2) * h, bw * w, bh * h)
                               for _c, cx, cy, bw, bh in human]
                for d in dets:
                    cls = d.smufl_name
                    if cls in NEVER_REHEARSE:
                        continue
                    if cls in covered:
                        silenced[cls] += 1
                        continue
                    cnum = name_to_id.get(cls)
                    if cnum is None:      # outside the nc=208 head
                        continue
                    box = (d.x_canonical, d.y_canonical,
                           d.width_canonical, d.height_canonical)
                    # Overlap OR centre-inside, the same "covered" test
                    # residual_background.py uses — a teacher box the human has
                    # already claimed never becomes a second label, whatever
                    # the two call it.
                    bcx, bcy = box[0] + box[2] / 2, box[1] + box[3] / 2
                    if any(iou(box, hb) > a.iou
                           or (hb[0] <= bcx <= hb[0] + hb[2]
                               and hb[1] <= bcy <= hb[1] + hb[3])
                           for hb in human_boxes):
                        over_human[cls] += 1
                        continue
                    extra.append((cnum,
                                  (box[0] + box[2] / 2) / w,
                                  (box[1] + box[3] / 2) / h,
                                  box[2] / w, box[3] / h))
                    added[cls] += 1
                    v_added += 1

            if not a.dry_run:
                lines = [f"{c} {x:.6f} {y:.6f} {bw:.6f} {bh:.6f}"
                         for c, x, y, bw, bh in human + extra]
                (odir / "labels" / f"{cid}.txt").write_text(
                    "\n".join(lines) + ("\n" if lines else ""))
                dst = odir / "images" / img_path.name
                if not dst.exists():
                    shutil.copy2(img_path, dst)

        per_version[v] = {"cells": v_cells, "teacher_boxes": v_added,
                          "cells_without_pass_stamps": v_nostamp}
        print(f"  {v}: {v_cells} cells ({v_nostamp} unstamped), "
              f"+{v_added} teacher boxes")

        if not a.dry_run:
            meta = dict(meta)
            meta["rehearsal"] = {
                "teacher": str(a.teacher), "conf": a.conf,
                "iou_vs_human": a.iou, "teacher_boxes_added": v_added,
                "scope": a.scope,
                "rule": {
                    "pass": "per-cell: a teacher box is kept only for a class "
                            "this cell has no human box of AND no stamped pass "
                            "looked for; unstamped cells untouched.",
                    "all": "every teacher box no human box overlaps, on every "
                           "cell — full distillation with human corrections "
                           "layered on top.",
                }[a.scope] + " staff/staffLine never.",
            }
            (odir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

    report = {
        "teacher": str(a.teacher), "conf": a.conf, "iou_vs_human": a.iou,
        "scope": a.scope,
        "versions": versions, "cells": n_cells,
        "cells_without_pass_stamps_left_untouched": n_nostamp,
        "human_boxes": n_human, "teacher_boxes": sum(added.values()),
        "teacher_by_class": dict(added.most_common()),
        "silenced_because_a_pass_covered_the_class": dict(silenced.most_common()),
        "dropped_because_over_a_human_box": dict(over_human.most_common()),
        "per_version": per_version,
    }
    print(json.dumps({k: report[k] for k in
                      ("cells", "cells_without_pass_stamps_left_untouched",
                       "human_boxes", "teacher_boxes")}, indent=1))
    print("teacher classes:", json.dumps(dict(added.most_common(25)), indent=1))
    if a.report:
        a.report.write_text(json.dumps(report, indent=1) + "\n")
        print("report ->", a.report)
    if not a.dry_run:
        shutil.copy2(a.root / "catalog-versions.txt", a.out / "catalog-versions.txt")
        print("wrote ->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
