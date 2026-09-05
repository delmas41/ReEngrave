"""Carve a single-symbol training corpus out of labels that already exist.

A per-symbol detector needs cells where THAT symbol is completely labelled and
does not care about anything else — for a tie-only model an unboxed rest is
genuinely background. That is the exact inverse of the 208-class model's
requirement, and it is why the campaign's single-symbol passes are already the
right shape: filter a label file to one family, keep only the cells whose
stamped passes swept that family, and you have a valid corpus with no new
labeling.

⚠️ **A cell NOT swept for the family is excluded, not included empty.** Its
instances of the family are unlabelled, so keeping it would train the specialist
that its own symbol is background — the exact defect this whole round is about,
reproduced one class at a time.

⚠️ **v1-v4 are excluded by default** (`--include-triage` adds them). They are
old TRIAGE batches: the human ruled on every box the 2026-05 model proposed, so
they are complete for what THAT model saw and silent about what it missed. For
the general model that was good enough; for a specialist whose entire signal is
one family, an undetected-and-therefore-unboxed instance is a false negative
taught at full weight.

The head stays **nc=208** so the result can be grafted row-wise into a
generalist (`merge_class_head.py`). Every other class collapses during training
and that does not matter: those rows are thrown away.

    python3 .../build_specialist_versions.py --list
    python3 .../build_specialist_versions.py --family ties --out data/specialist-ties
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import shutil
from pathlib import Path

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"

# A family is what a labeling PASS covers, because that is the unit coverage is
# recorded in. Splitting finer would claim sweep coverage nobody recorded.
FAMILIES: dict[str, list[str]] = {
    "hollow": ["noteheadHalfOnLine", "noteheadHalfInSpace",
               "noteheadWholeOnLine", "noteheadWholeInSpace"],
    "ties": ["tie"],
    "slurs": ["slur"],
    "rests": ["restWhole", "restHalf", "restQuarter", "rest8th", "rest16th",
              "restHBar"],
    "accidentals": ["accidentalFlat", "accidentalNatural", "accidentalSharp"],
    "keysig": ["keyFlat", "keyNatural", "keySharp"],
    "clefs": ["clefG", "clefF", "clefC", "clefCAlto", "clefCTenor"],
    "dots": ["augmentationDot"],
    "dynamics": ["dynamicP", "dynamicF", "dynamicM", "dynamicS",
                 "dynamicCrescendoHairpin", "dynamicDiminuendoHairpin"],
    "black": ["noteheadBlackOnLine", "noteheadBlackInSpace"],
}

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
    ap.add_argument("--family", choices=sorted(FAMILIES))
    ap.add_argument("--root", type=Path, default=REPO / "data" / "user-labeled")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--include-triage", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--min-positives", type=int, default=40,
                    help="refuse to write a corpus with fewer positive boxes "
                         "than this — a specialist trained on a handful is not "
                         "a specialist, and writing it anyway invites a run "
                         "whose result means nothing.")
    a = ap.parse_args()

    names = json.loads(CLASS_NAMES_JSON.read_text())
    palettes = load_palettes()
    stamps = stamp_index()
    versions = [ln.split("#", 1)[0].strip()
                for ln in (a.root / "catalog-versions.txt").read_text().splitlines()
                if ln.split("#", 1)[0].strip()]
    triage = {v for v in versions if v.startswith(("v1-", "v2-", "v3-", "v4-"))}

    def build(fam: str, write: bool):
        want = set(FAMILIES[fam])
        # every INDEX whose name is in the family — the 208-space has 40
        # duplicated names and a specialist that keeps one index of a name
        # would be trained on half its own symbol.
        keep_ids = {i for i, n in enumerate(names) if n in want}
        cells = pos = neg_cells = 0
        per_version: dict[str, int] = {}
        for v in versions:
            is_triage = v in triage
            if is_triage and not a.include_triage:
                continue
            n_v = 0
            for lab in sorted((a.root / v / "labels").glob("*.txt")):
                cid = lab.stem
                covered: set[str] = set()
                for s in stamps.get(cid, ()):
                    covered |= palettes.get(s, set())
                if not is_triage and not (want & covered):
                    continue        # never swept for this family — exclude
                rows = []
                for line in lab.read_text().splitlines():
                    parts = line.split()
                    if len(parts) == 5 and int(parts[0]) in keep_ids:
                        rows.append(line.strip())
                cells += 1
                n_v += 1
                pos += len(rows)
                if not rows:
                    neg_cells += 1
                if write:
                    od = a.out / v
                    (od / "labels").mkdir(parents=True, exist_ok=True)
                    (od / "images").mkdir(parents=True, exist_ok=True)
                    (od / "labels" / f"{cid}.txt").write_text(
                        "\n".join(rows) + ("\n" if rows else ""))
                    src = a.root / v / "images" / f"{cid}.png"
                    dst = od / "images" / f"{cid}.png"
                    if src.exists() and not dst.exists():
                        shutil.copy2(src, dst)   # follows v2-v4's symlinks
            if n_v:
                per_version[v] = n_v
        return cells, pos, neg_cells, per_version

    if a.list or not a.family:
        print(f"{'family':14s}{'cells':>8s}{'positives':>11s}{'empty cells':>13s}")
        for fam in sorted(FAMILIES):
            c, p, n, _ = build(fam, write=False)
            flag = "" if p >= a.min_positives else "   << thin"
            print(f"{fam:14s}{c:8d}{p:11d}{n:13d}{flag}")
        return 0

    c, p, n, per_version = build(a.family, write=False)
    print(f"family {a.family}: {c} cells, {p} positive boxes, {n} empty "
          f"({n/c:.0%} negatives)" if c else f"family {a.family}: EMPTY")
    if p < a.min_positives:
        print(f"REFUSING: {p} positives < --min-positives {a.min_positives}")
        return 1
    if not a.out:
        print("no --out, nothing written")
        return 0
    if a.out.exists():
        shutil.rmtree(a.out)
    build(a.family, write=True)
    (a.out / "catalog-versions.txt").write_text(
        "\n".join(per_version) + "\n")
    (a.out / "specialist.json").write_text(json.dumps(
        {"family": a.family, "classes": FAMILIES[a.family], "cells": c,
         "positive_boxes": p, "empty_cells": n,
         "include_triage": a.include_triage,
         "source_root": str(a.root), "per_version": per_version}, indent=1) + "\n")
    print(f"wrote -> {a.out}  ({len(per_version)} versions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
