"""Which single-symbol specialists can be trained from labels we ALREADY have?

A per-symbol detector needs cells where that symbol is COMPLETELY labelled — and
crucially it does not care about anything else, because for a hollow-notehead
model an unboxed rest genuinely IS background. That is the exact opposite of the
208-class model's requirement, and it means the campaign's single-symbol passes
are already in the right shape: a label file filtered to one class, on a cell
whose stamped passes cover that class, is a valid training example as it stands.

So this asks, per class: how many cells of the training corpus were swept for it,
and how many boxes does that give. A class with enough cells needs NO new
labeling. A class with few needs a pass — and now we know which, instead of
guessing.

⚠️ **v1-v4 are counted separately and are a weaker guarantee.** They are old
TRIAGE batches with no `inspected_passes`: the human ruled on every box the
2026-05 model proposed, which makes them complete for what THAT model detected
and silent about what it missed. Good enough to train on, not good enough to
call swept, so they are reported in their own column.

    python3 .../probe_specialist_corpora.py
    python3 .../probe_specialist_corpora.py --min-cells 40
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
from pathlib import Path

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"

EXTRA_PALETTES = {
    "hollow noteheads": {"noteheadHalfOnLine", "noteheadHalfInSpace",
                         "noteheadWholeOnLine", "noteheadWholeInSpace"},
    "grace noteheads": {"noteheadBlackOnLineSmall", "noteheadBlackInSpaceSmall",
                        "noteheadHalfOnLineSmall", "noteheadHalfInSpaceSmall"},
    "clefs": {"clefG", "clefF", "clefC", "clefCAlto", "clefCTenor",
              "clefG8vb", "clefG8va", "clefF8vb", "clefUnpitchedPercussion"},
}


def load_palettes() -> dict[str, set[str]]:
    out = dict(EXTRA_PALETTES)
    for p in sorted((SURVEY / "pass-configs").glob("*.json")):
        d = json.loads(p.read_text())
        names: set[str] = set()
        for slot in (d.get("classes") or d.get("active_classes") or []):
            if isinstance(slot, str):
                names.add(slot)
            else:
                for k in ("name", "on_line", "in_space"):
                    if slot.get(k):
                        names.add(slot[k])
        out[d.get("pass_name") or p.stem] = names
    if "completion-full" in out:
        out.setdefault("completion", out["completion-full"])
    return out


def stamp_index() -> dict[str, set[str]]:
    out: dict[str, set[str]] = collections.defaultdict(set)
    for pat in ("benchmarks/*/verdicts/*.verdict.json",
                "benchmarks/*/*/verdicts/*.verdict.json",
                "benchmarks/*/*/*/verdicts/*.verdict.json"):
        for f in glob.glob(pat):
            try:
                v = json.loads(Path(f).read_text())
            except Exception:
                continue
            cid = v.get("cell_id") or Path(f).name.split(".verdict")[0]
            for s in (v.get("inspected_passes") or []):
                out[cid].add(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=REPO / "data" / "user-labeled")
    ap.add_argument("--min-cells", type=int, default=30,
                    help="a specialist under this many swept cells is reported "
                         "as needing a pass.")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    names = json.loads(CLASS_NAMES_JSON.read_text())
    palettes = load_palettes()
    stamps = stamp_index()

    versions = [ln.split("#", 1)[0].strip()
                for ln in (a.root / "catalog-versions.txt").read_text().splitlines()
                if ln.split("#", 1)[0].strip()]
    triage_versions = {v for v in versions if v.startswith(("v1-", "v2-", "v3-", "v4-"))}

    swept_cells = collections.Counter()     # class -> cells swept for it
    swept_boxes = collections.Counter()
    triage_cells = collections.Counter()
    triage_boxes = collections.Counter()
    n_cells = n_swept_any = 0

    for v in versions:
        for lab in sorted((a.root / v / "labels").glob("*.txt")):
            cid = lab.stem
            n_cells += 1
            boxes = collections.Counter()
            for line in lab.read_text().splitlines():
                parts = line.split()
                if len(parts) == 5:
                    i = int(parts[0])
                    if 0 <= i < len(names):
                        boxes[names[i]] += 1
            covered: set[str] = set()
            for s in stamps.get(cid, ()):
                covered |= palettes.get(s, set())
            if covered:
                n_swept_any += 1
            is_triage = v in triage_versions
            for cls in (covered if not is_triage else set(names)):
                if is_triage:
                    triage_cells[cls] += 1
                    triage_boxes[cls] += boxes.get(cls, 0)
                else:
                    swept_cells[cls] += 1
                    swept_boxes[cls] += boxes.get(cls, 0)

    print(f"{n_cells} training cells; {n_swept_any} carry a pass stamp; "
          f"{len(triage_versions)} triage versions counted separately\n")
    hdr = (f"{'class':26s}{'swept cells':>12s}{'swept boxes':>12s}"
           f"{'triage cells':>13s}{'triage boxes':>13s}   verdict")
    print(hdr)
    print("-" * len(hdr))
    rows = sorted(set(swept_cells) | set(triage_cells),
                  key=lambda c: -(swept_cells[c] + triage_cells[c]))
    ready, needs = [], []
    for c in rows:
        sc, sb = swept_cells[c], swept_boxes[c]
        tc, tb = triage_cells[c], triage_boxes[c]
        if sb + tb == 0:
            continue
        ok = sc >= a.min_cells
        (ready if ok else needs).append(c)
        print(f"{c:26s}{sc:12d}{sb:12d}{tc:13d}{tb:13d}   "
              f"{'READY' if ok else 'needs a pass'}")

    print(f"\nspecialists trainable from existing labels ({len(ready)}): {ready}")
    print(f"specialists needing a pass ({len(needs)}): {needs[:25]}")
    if a.out:
        a.out.write_text(json.dumps(
            {"cells": n_cells, "min_cells": a.min_cells,
             "swept_cells": dict(swept_cells), "swept_boxes": dict(swept_boxes),
             "triage_cells": dict(triage_cells), "triage_boxes": dict(triage_boxes),
             "ready": ready, "needs_pass": needs}, indent=1) + "\n")
        print("->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
