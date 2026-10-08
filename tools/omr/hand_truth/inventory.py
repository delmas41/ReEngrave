"""The generated inventory of every hand label in the tree, and the weights lineage.

    python3 -m tools.omr.hand_truth.inventory            # writes data/hand-truth/INVENTORY.json
    python3 -m tools.omr.hand_truth.inventory --check    # exit 1 if the committed file is stale
    python3 -m tools.omr.hand_truth.inventory --verify-checkpoints omr-weights/
                                                          # compare the declared lineage with
                                                          # each .pt's own train_args (needs torch)

Every count here is DERIVED from files in the tree and the output carries no
timestamp, so two runs on one tree are byte-identical and ``--check`` can
fail. Two things are DECLARED, with their evidence, because no file in the
tree states them: the completeness tier of each label version (``TIERS``)
and the weights lineage (``data/hand-truth/weights-lineage.json``).

WHO JUDGED is read from each adjudication file itself: its ``adjudicator``
field, else its own text ("not Sean's"). A file that names nobody is
``unrecorded`` — never guessed as Sean's (rule 7: ask who says it's right).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from tools.omr.hand_truth import completeness, store
from tools.omr.hand_truth.export_yolo import held_out_pages
from tools.omr.hand_truth.store import REPO, edition_key

OUT_PATH = REPO / "data" / "hand-truth" / "INVENTORY.json"
LINEAGE_PATH = REPO / "data" / "hand-truth" / "weights-lineage.json"
LABELED = REPO / "data" / "user-labeled"
BENCH = REPO / "benchmarks"

#: The completeness tier of each label version — a JUDGMENT, so declared here
#: with its basis (plan §1a), never inferred from a palette.
TIERS: Dict[str, Tuple[str, str]] = {}
for _v in ("v22-2026-09-04-simrock-dense",):
    TIERS[_v] = ("1-drawn-palette-recorded", "inspected_passes 'draw-rich' on every cell")
for _v in ("v3-2026-06-09-mahler5", "v4-2026-06-10-la-mer"):
    TIERS[_v] = ("1b-drawn-palette-unrecorded", "n_tp=0, every box human-added; no inspected_passes")
TIERS["v18-2026-09-03-complete-breitkopf"] = ("2-completion-pass", "inspected_passes 'completion' (completion-full palette)")
for _v in ("v13-2026-09-03-complete-v7-beet5-bolero", "v14-2026-09-03-complete-litolff",
           "v15-2026-09-03-complete-peters", "v16-2026-09-03-complete-eulenburg",
           "v17-2026-09-03-complete-simrock", "v19-2026-09-03-complete-mahler1",
           "v20-2026-09-03-complete-elgar1", "v21-2026-09-03-complete-lamer"):
    TIERS[_v] = ("3-hand-for-some-families", "ROUND3_COMPLETENESS.md: human hollow/rests/accidentals/clefs; model dynamics/slurs/ties spot-checked")
for _v in ("v1-2026-05-18-orchestral", "v2-2026-06-08-beet5"):
    TIERS[_v] = ("4-verdicts-on-model-boxes", "TP/FP on an older model's detections plus a few added")
for _v in ("v5-2026-07-12-clef", "v6-2026-07-13-clef-diverse"):
    TIERS[_v] = ("single-family:clef", "clef batches; excluded from the catalog")
for _v in ("v7-2026-09-02-hollow", "v8-2026-09-02-hollow2-5pub", "v9-2026-09-03-hollow3-mahler1",
           "v10-2026-09-03-hollow3-elgar1", "v11-2026-09-03-hollow3-lamer",
           "v12-2026-09-03-hollow3-tchaikovsky1-lowres"):
    TIERS[_v] = ("single-family:hollow", "hollow-notehead passes; superseded by v13-v21 or never admitted")
TIERS["v23-2026-09-04-arcs-reconcile"] = ("single-family:arcs", "inspected_passes 'ties+slurs-reconcile' only")


def _rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(REPO))


def _json(p: Path):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _vkey(name: str) -> int:
    m = re.match(r"v(\d+)-", name)
    return int(m.group(1)) if m else 10 ** 6


def _manifest_rows(d) -> List[dict]:
    rows = d if isinstance(d, list) else (d.get("cells") if isinstance(d, dict) else None)
    return [r for r in rows or [] if isinstance(r, dict) and "cell_id" in r]


def cell_pages() -> Dict[str, Tuple[str, int]]:
    """cell_id -> (edition, pdf_page_index), from every committed cell manifest."""
    out: Dict[str, Tuple[str, int]] = {}
    for f in sorted(BENCH.glob("**/*cells*.json")):
        for r in _manifest_rows(_json(f)):
            pdf, page = r.get("pdf"), r.get("page")
            if pdf and page is not None and r["cell_id"] not in out:
                out[r["cell_id"]] = (edition_key(pdf), int(page))
    return out


def _label_lines(p: Path) -> List[str]:
    return [l.strip() for l in p.read_text().splitlines() if l.strip()]


def _admitted() -> Set[str]:
    f = LABELED / "catalog-versions.txt"
    return {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")}


def _pass_union(cell_ids: Set[str]) -> Dict[str, Set[str]]:
    """cell_id -> union of inspected_passes over every verdict file in benchmarks/."""
    out: Dict[str, Set[str]] = defaultdict(set)
    for f in BENCH.glob("**/*.json"):
        parts = f.parts
        if not any("verdict" in s or "merged" in s for s in parts[-3:-1]):
            continue
        v = _json(f)
        if isinstance(v, dict) and v.get("cell_id") in cell_ids and v.get("inspected_passes"):
            out[v["cell_id"]] |= set(v["inspected_passes"])
    return out


def _version_origin(meta: dict) -> Dict[str, int]:
    keys = ("n_fn_added", "n_tp", "n_wrong_cat", "n_wrong_bbox")
    tot = Counter()
    for pc in meta.get("per_cell", []):
        for k in keys:
            tot[k] += int(pc.get(k, 0) or 0)
    return {"human_drawn": tot["n_fn_added"],
            "model_box_kept": tot["n_tp"] + tot["n_wrong_cat"] + tot["n_wrong_bbox"]}


def label_versions(pages_of: Dict[str, Tuple[str, int]], kept_means: Dict[str, str]) -> List[dict]:
    admitted = _admitted()
    vdirs = sorted((d for d in LABELED.glob("v*-*") if d.is_dir()), key=lambda d: _vkey(d.name))
    all_ids = {p.stem for d in vdirs for p in (d / "labels").glob("*.txt")}
    passes = _pass_union(all_ids)
    out = []
    for d in vdirs:
        labels = sorted((d / "labels").glob("*.txt"))
        ids = [p.stem for p in labels]
        meta = _json(d / "metadata.json") or {}
        pages = Counter(f"{pages_of[i][0]}:{pages_of[i][1]}" for i in ids if i in pages_of)
        pc = Counter()
        for i in ids:
            for p in passes.get(i, ()):
                pc[p] += 1
        n_boxes = sum(len(_label_lines(p)) for p in labels)
        origin = _version_origin(meta)
        tier, basis = TIERS.get(d.name, ("undeclared", "no TIERS entry"))
        out.append({
            "version": d.name,
            "tier": tier,
            "tier_basis": basis,
            "in_catalog": d.name in admitted,
            "cells": len(ids),
            "boxes": n_boxes,
            "box_origin": {**origin, "model_box_kept_means": kept_means.get(d.name, "n/a" if not origin["model_box_kept"] else "undeclared"),
                           "unreconciled": n_boxes - origin["human_drawn"] - origin["model_box_kept"]},
            "cells_with_recorded_passes": sum(1 for i in ids if passes.get(i)),
            "inspected_passes": dict(sorted(pc.items())),
            "cells_unmapped_to_a_page": sum(1 for i in ids if i not in pages_of),
            "pages": dict(sorted(pages.items())),
            "labeler": meta.get("labeler") or "unrecorded",
        })
    return out


def _source_dirs() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = defaultdict(list)
    for d in LABELED.glob("v*-*"):
        m = _json(d / "metadata.json") or {}
        src = (m.get("source") or {}).get("verdicts_dir")
        if src:
            out[str(Path(src))].append(d.name)
    return out


_HUMAN_VERDICTS = {"FP", "WRONG_CATEGORY", "WRONG_BBOX", "unsure", "UNSURE"}


def verdict_sets(version_cell_ids: Set[str]) -> List[dict]:
    """Every cell-verdict directory under benchmarks/, with how much a HUMAN did in it."""
    sources = _source_dirs()
    out = []
    for d in sorted({p.parent for p in BENCH.glob("**/verdicts*/*.json")}):
        cells = reviewed = added = 0
        verdicts = Counter()
        ids: Set[str] = set()
        for f in sorted(d.glob("*.json")):
            v = _json(f)
            if not isinstance(v, dict) or "cell_id" not in v:
                continue
            cells += 1
            ids.add(v["cell_id"])
            # Schema 2 keeps `detections` (a TP there may be a PRE-FILL); schema 1
            # keeps `verdicts` + `fn_noteheads`, where any non-empty verdict was typed
            # by a person (the pre-fill queue did not exist yet).
            schema1 = "detections" not in v and "verdicts" in v
            dets = v.get("detections") if not schema1 else v.get("verdicts")
            dets = list(dets.values()) if isinstance(dets, dict) else (dets or [])
            vs = [str(x.get("verdict") or "") for x in dets if isinstance(x, dict)]
            verdicts.update(x or "pending" for x in vs)
            n_add = len(v.get("added_detections") or []) + len(v.get("fn_noteheads") or [])
            added += n_add
            human = (any(vs) if schema1 else any(x in _HUMAN_VERDICTS for x in vs))
            if v.get("labeled_at_utc") or v.get("inspected_passes") or n_add or human:
                reviewed += 1
        if not cells:
            continue
        rel = _rel(d)
        out.append({
            "dir": rel,
            # A port, backup or merge of another set's verdicts says so in its
            # NAME; its cells are not new human work.
            "copy_by_name": bool(re.search(r"ported|backup|merged|_pre|-pre", rel)),
            "source_of_versions": sorted(sources.get(rel, [])),
            "cells": cells,
            "cells_with_human_action": reviewed,
            "cells_no_human_action": cells - reviewed,
            "human_added_boxes": added,
            "detection_verdicts": dict(sorted(verdicts.items())),
            "cells_also_in_a_version": len(ids & version_cell_ids),
        })
    return out


def _who(d, text: str) -> Tuple[str, str]:
    if isinstance(d, dict) and str(d.get("adjudicator", "")).strip():
        a = str(d["adjudicator"])
        if "sean" in a.lower():
            return "sean", f"adjudicator: {a[:60]}"
        if re.search(r"claude|session|manager", a, re.I):
            return "claude", f"adjudicator: {a[:60]}"
        return "unrecorded", f"adjudicator: {a[:60]}"
    if re.search(r"not sean'?s", text, re.I):
        return "claude", "file says it is not Sean's"
    return "unrecorded", "the file names no adjudicator"


def adjudications() -> List[dict]:
    out = []
    for f in sorted(BENCH.glob("**/*.json")):
        name = f.name.lower()
        if "adjudicat" not in name or "readjudicat" in name:
            continue
        d = _json(f)
        text = f.read_text(errors="ignore")[:400000]
        who, basis = _who(d, text)
        rows = None
        if isinstance(d, list):
            rows = len(d)
        elif isinstance(d, dict):
            for k in ("verdicts", "rows", "crops", "fires"):
                if isinstance(d.get(k), (list, dict)):
                    rows = len(d[k])
                    break
        out.append({"file": _rel(f), "labeler": who, "basis": basis, "rows": rows})
    return out


def structure_truth() -> List[dict]:
    d = _json(BENCH / "omr-scan-e2e-2026-09" / "works.json") or {}
    out = []
    for r in d.get("rows", []):
        page = r.get("page") if isinstance(r.get("page"), dict) else {}
        win = r.get("window") if isinstance(r.get("window"), dict) else {}
        m = re.search(r"-(\d{5,7})-p\d+$", r.get("row_id", ""))
        out.append({
            "row_id": r.get("row_id"),
            "edition": f"imslp{m.group(1)}" if m else None,
            "pdf_page_index": page.get("pdf_page_index"),
            "systems": page.get("n_systems"),
            "staves": page.get("n_staves"),
            "bars": [win.get("first_ref_measure"), win.get("last_ref_measure")],
        })
    return out


# ---------------------------------------------------------------- lineage
def _corpus_cells(c: dict) -> List[Tuple[str, Path, Optional[Path]]]:
    """(version, label file, matching human label file or None) for one corpus."""
    if not c.get("in_tree"):
        return []
    root = REPO / c["root"]
    if c.get("versions_from"):
        txt = (REPO / c["versions_from"]).read_text().splitlines()
        versions = [l.strip() for l in txt if l.strip() and not l.startswith("#")]
    else:
        versions = list(c.get("versions", []))
    human = REPO / c["human_root"] if c.get("human_root") else None
    out = []
    for v in versions:
        for p in sorted((root / v / "labels").glob("*.txt")):
            out.append((v, p, (human / v / "labels" / p.name) if human else None))
    return out


def lineage(pages_of: Dict[str, Tuple[str, int]]) -> Dict:
    decl = _json(LINEAGE_PATH)
    weights = decl["weights"]
    seen_direct: Dict[str, Counter] = {}
    summary: Dict[str, Dict] = {}
    for name, w in weights.items():
        pages = Counter()
        corp = []
        for c in w.get("corpora", []):
            cells = _corpus_cells(c)
            human_lines = teacher_lines = 0
            for v, p, h in cells:
                lines = Counter(_label_lines(p))
                if h is not None and h.exists():
                    hl = Counter(_label_lines(h))
                    human_lines += sum(hl.values())
                    teacher_lines += sum((lines - hl).values())
                else:
                    human_lines += sum(lines.values())
                if p.stem in pages_of:
                    e, i = pages_of[p.stem]
                    pages[f"{e}:{i}"] += 1
            corp.append({"name": c["name"], "in_tree": bool(c.get("in_tree")),
                         "cells": len(cells),
                         "boxes_from_label_files": human_lines,
                         "boxes_added_by_teacher_model": teacher_lines})
        seen_direct[name] = pages
        summary[name] = {"parents": w.get("parents", []), "corpora": corp, "evidence": w.get("evidence")}

    def ancestors(n: str, acc: Optional[Set[str]] = None) -> Set[str]:
        acc = set() if acc is None else acc
        for p in weights.get(n, {}).get("parents", []):
            if p not in acc:
                acc.add(p)
                ancestors(p, acc)
        return acc

    for name in weights:
        seen = Counter(seen_direct[name])
        for a in ancestors(name):
            seen.update(seen_direct.get(a, {}))
        summary[name]["pages_seen_in_training"] = dict(sorted(seen.items()))
        summary[name]["ancestors"] = sorted(ancestors(name))
    return summary


def pages_seen(lin: Dict, weights_name: str) -> Set[Tuple[str, int]]:
    out = set()
    for k in lin[weights_name]["pages_seen_in_training"]:
        e, i = k.rsplit(":", 1)
        out.add((e, int(i)))
    return out


def hand_truth_pages() -> List[dict]:
    out = []
    for p in store.load_all():
        fam = completeness.family_status(p)
        out.append({
            "edition": p.edition, "pdf_page_index": p.pdf_page_index, "state": p.state,
            "cells": len(p.cells), "boxes": len(p.boxes),
            "box_origin": dict(sorted(Counter(b.origin for b in p.boxes).items())),
            "queue": len(p.queue),
            "families_complete": sorted(f for f, s in fam.items() if s["complete"]),
            "whole_ink": completeness.page_complete(p),
        })
    return out


def build() -> Dict:
    pages_of = cell_pages()
    kept = {}
    decl = _json(LINEAGE_PATH)
    for meaning, spec in decl.get("kept_box_means", {}).items():
        if isinstance(spec, dict):
            for v in spec.get("versions", []):
                kept[v] = meaning
    versions = label_versions(pages_of, kept)
    version_ids = {p.stem for d in LABELED.glob("v*-*") for p in (d / "labels").glob("*.txt")}
    lin = lineage(pages_of)
    production = next(n for n, w in decl["weights"].items() if w.get("production") == "scan")
    held = held_out_pages()
    seen = pages_seen(lin, production)
    return {
        "_what": "GENERATED by `python3 -m tools.omr.hand_truth.inventory` — never edit by hand (ROADMAP 1.7).",
        "label_versions": versions,
        "verdict_sets": verdict_sets(version_ids),
        "adjudications": adjudications(),
        "structure_truth": structure_truth(),
        "weights_lineage": lin,
        "production_scan_weights": production,
        "held_out_pages": sorted(f"{e}:{i}" for e, i in held),
        "held_out_pages_seen_by_production": sorted(f"{e}:{i}" for e, i in held & seen),
        "hand_truth_pages": hand_truth_pages(),
    }


def render(inv: Dict) -> str:
    return json.dumps(inv, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def verify_checkpoints(weights_dir: Path) -> int:
    """Read each declared checkpoint's own train_args and compare. Exit 0/1/2."""
    try:
        import torch
    except ImportError:
        print("torch is not installed: cannot read checkpoints", file=sys.stderr)
        return 2
    decl = _json(LINEAGE_PATH)["weights"]
    bad = found = 0
    for name, w in decl.items():
        p = Path(weights_dir) / name
        if not p.exists():
            print(f"MISSING   {name}")
            continue
        found += 1
        ck = torch.load(str(p), map_location="cpu", weights_only=False)
        args = (ck.get("train_args") or {}) if isinstance(ck, dict) else {}
        data, model = str(args.get("data", "")), str(args.get("model", ""))
        hint = w.get("train_data_hint")
        parent = (w.get("parents") or [None])[0]
        ok_data = hint is None or hint.lower() in data.lower()
        ok_parent = parent is None or Path(parent).name in model
        verdict = "MATCH" if ok_data and ok_parent else "MISMATCH"
        bad += verdict == "MISMATCH"
        print(f"{verdict:9} {name}\n          data={data!r} model={model!r} "
              f"epochs={args.get('epochs')} imgsz={args.get('imgsz')}")
    if not found:
        print("no declared checkpoint found under", weights_dir, file=sys.stderr)
        return 2
    return 1 if bad else 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed inventory is stale")
    ap.add_argument("--verify-checkpoints", type=Path, metavar="WEIGHTS_DIR")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.verify_checkpoints:
        return verify_checkpoints(a.verify_checkpoints)
    text = render(build())
    if a.check:
        cur = a.out.read_text() if a.out.exists() else ""
        if cur != text:
            print(f"{_rel(a.out)} is stale: re-run python3 -m tools.omr.hand_truth.inventory", file=sys.stderr)
            return 1
        return 0
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text)
    print(f"wrote {_rel(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
