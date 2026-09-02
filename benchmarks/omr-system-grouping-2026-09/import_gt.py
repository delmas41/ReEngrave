#!/usr/bin/env python3
"""Import every piece of existing FREE system-grouping ground truth into
gt/gt.json. Reads the source files directly (never transcribes from memory):

  1. benchmarks/omr-system-grouping-2026-08/eval_grouping.py
     -> imported as a live module (verified read-only: only glob/exists
     checks and list-building at import time; `main()` only runs under
     `__main__`, which import does not trigger). Gives the exact `CASES`
     list including its conditional `_B5`/`_WIDER` glob-gated entries —
     count-level truth (n_systems) per (pdf, page, dpi).

  2. benchmarks/omr-system-grouping-2026-08/probes/fulldist.py
     -> NOT imported. Its top-level code is unconditional (no `__main__`
     guard) and writes to /tmp/dist.json, which is outside this build
     agent's write scope. Instead we statically parse its source with `ast`
     and literal_eval the `CASES` assignment — partition-level truth (break
     INDICES, 0-based gap positions) at a hardcoded dpi=300, including
     B5 p47 (truth: 0 breaks), which is absent from eval_grouping.py.

  3. benchmarks/omr-phase1-baseline/ground-truth.json
     -> plain JSON. 3 hand-verified pages with full staves_per_system truth.
     Its "source" fields are prose, not machine paths; the mapping to actual
     PDF paths below was verified by hand against those descriptions (IMSLP
     id + composer + page index all cross-checked) and is re-verified with
     Path.exists() at run time, same as the other two sources.

Every path is verified to exist before its case is admitted; a case whose
PDF cannot be found is recorded under "missing" instead of failing the run.
Nothing here is invented or extrapolated beyond what these three files say.

Usage: python3 import_gt.py [--out gt/gt.json]
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]
sys.path.insert(0, str(WORKTREE_ROOT))

BENCH_08 = WORKTREE_ROOT / "benchmarks" / "omr-system-grouping-2026-08"
EVAL_GROUPING_PY = BENCH_08 / "eval_grouping.py"
FULLDIST_PY = BENCH_08 / "probes" / "fulldist.py"
PHASE1_GT_JSON = WORKTREE_ROOT / "benchmarks" / "omr-phase1-baseline" / "ground-truth.json"

DEFAULT_OUT = HERE / "gt" / "gt.json"

missing = []  # {source, identifier, path, reason}


def _slug(pdf: str) -> str:
    p = Path(pdf)
    stem = p.stem
    if stem in ("score",):  # symlink-farm PDFs are all literally "score.pdf"
        stem = f"{p.parent.name}-score"
    return stem


# ─── Source 1: eval_grouping.py (live import — verified side-effect-free) ───


def import_eval_grouping_cases():
    spec = importlib.util.spec_from_file_location("_eval_grouping_gt_import", EVAL_GROUPING_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # only glob()/exists() + list building run at import time
    rows = []
    for pdf, page, dpi, truth in mod.CASES:
        pdf = str(pdf)
        exists = Path(pdf).is_file()
        if not exists:
            missing.append({"source": "eval_grouping.py", "identifier": f"{pdf} p{page}", "path": pdf,
                             "reason": "does not exist on disk"})
            continue
        is_wider = any(pdf.endswith(name) for name, _, _ in getattr(mod, "_WIDER", [])) if hasattr(mod, "_WIDER") else False
        note = ("Widened past the Beethoven/Litolff-1870 GT to catch the next over-fitted rule; "
                 "hand-read the same way (left-margin crop, count brackets).") if is_wider else \
                ("Beethoven 9 imslp-516488 (Litolff 1870) or Beethoven 5 imslp984073 (Litolff 1870), "
                 "the original 14-case set (+ B5 p40, the set's first MERGE case, found by the LEGATO cross-check: "
                 "three brackets, measure numbers 229/243/256, instrument labels restarting at each).")
        rows.append({
            "case_id": f"evalgrouping-{_slug(pdf)}-p{page}-dpi{dpi}",
            "pdf": pdf,
            "page": page,
            "dpi": dpi,
            "n_systems": truth,
            "staves_per_system": None,
            "n_staves": None,
            "break_indices": None,
            "source": "benchmarks/omr-system-grouping-2026-08/eval_grouping.py",
            "method": "left-margin bracket count (hand-read); count-level truth only",
            "notes": note,
            "ambiguous": False,
        })
    return rows


# ─── Source 2: probes/fulldist.py (static AST parse — avoid its /tmp write) ─


def import_fulldist_cases():
    src = FULLDIST_PY.read_text()
    tree = ast.parse(src, filename=str(FULLDIST_PY))

    # Resolve the B9/B5 path constants the same way the module does, without
    # executing the module (which would also run its unconditional sweep +
    # /tmp/dist.json write). fulldist.py's B9 is a RELATIVE path with no
    # `__file__`-relative resolution of its own (unlike eval_grouping.py's
    # absolute B9) — it only resolves correctly against the MAIN CHECKOUT,
    # which is also where its hardcoded `sys.path.insert(0, ...)` points.
    # `tools/omr/training/data/imslp/` is a symlink farm that exists only in
    # the main checkout (confirmed: absent from this worktree), matching
    # PDFs being main-checkout-only per the build brief.
    MAIN_CHECKOUT_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
    b9_relative = "tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf"
    b9_abs = str(MAIN_CHECKOUT_ROOT / b9_relative)
    b5_abs = ("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
              "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")
    name_to_path = {"B9": b9_abs, "B5": b5_abs}

    cases_literal = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CASES" for t in node.targets
        ):
            cases_literal = node.value
            break
    if cases_literal is None:
        raise RuntimeError(f"could not find CASES assignment in {FULLDIST_PY}")

    rows = []
    for elt in cases_literal.elts:
        # Each element is a tuple (NAME, page, [break, indices, ...]).
        name_node, page_node, breaks_node = elt.elts
        pdf_name = name_node.id  # "B9" or "B5"
        pdf = name_to_path[pdf_name]
        page = ast.literal_eval(page_node)
        breaks = ast.literal_eval(breaks_node)

        if not Path(pdf).is_file():
            missing.append({"source": "probes/fulldist.py", "identifier": f"{pdf_name} p{page}", "path": pdf,
                             "reason": "does not exist on disk"})
            continue

        rows.append({
            "case_id": f"fulldist-{_slug(pdf)}-p{page}-dpi300",
            "pdf": pdf,
            "page": page,
            "dpi": 300,  # hardcoded in fulldist.py's render_page() call for every case
            "n_systems": len(breaks) + 1,
            "staves_per_system": None,
            "n_staves": None,
            "break_indices": sorted(breaks),
            "source": "benchmarks/omr-system-grouping-2026-08/probes/fulldist.py",
            "method": "left-margin bracket count -> break INDICES (partition-level, 0-based gap positions)",
            "notes": ("B5 p47: truth 0 breaks, a case absent from eval_grouping.py." if (pdf_name == "B5" and page == 47)
                      else "Partition-level GT: break_indices are 0-based gap positions between adjacent "
                           "top-to-bottom staves, valid against however many staves the pipeline detects on "
                           "this exact page today (score.py re-derives staves_per_system from these indices "
                           "at scoring time, rather than this file inventing a staff count)."),
            "ambiguous": False,
        })
    return rows


# ─── Source 3: phase1-baseline/ground-truth.json (plain JSON) ───────────────

# The JSON's "source" field is prose ("IMSLP932182 Well-Tempered Clavier I,
# PDF page index 5 ..."); this maps each of its 3 keys to the actual PDF path
# it describes. Verified by cross-checking IMSLP id + composer + described
# page against the file on disk; re-verified with Path.exists() below.
_SCORES_DIR = "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus"
PHASE1_PDF_MAP = {
    "wtc-p5": f"{_SCORES_DIR}/PDF Scores/IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf",
    "beet5-p10": f"{_SCORES_DIR}/IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf",
    "lamer-p25": f"{_SCORES_DIR}/PDF Scores/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf",
}
PHASE1_DPI = {"wtc-p5": 600, "beet5-p10": 600, "lamer-p25": 300}
# "PDF page index N" in the doc's own prose -> 0-based page index used by render_page.
PHASE1_PAGE = {"wtc-p5": 5, "beet5-p10": 10, "lamer-p25": 25}


def import_phase1_baseline_cases():
    doc = json.loads(PHASE1_GT_JSON.read_text())
    rows = []
    for key, page_gt in doc.get("pages", {}).items():
        pdf = PHASE1_PDF_MAP.get(key)
        if pdf is None:
            missing.append({"source": "omr-phase1-baseline/ground-truth.json", "identifier": key,
                             "path": None, "reason": "no known PDF path mapping for this GT key"})
            continue
        if not Path(pdf).is_file():
            missing.append({"source": "omr-phase1-baseline/ground-truth.json", "identifier": key,
                             "path": pdf, "reason": "does not exist on disk"})
            continue
        rows.append({
            "case_id": f"phase1baseline-{key}",
            "pdf": pdf,
            "page": PHASE1_PAGE[key],
            "dpi": PHASE1_DPI[key],
            "n_systems": page_gt["n_systems"],
            "staves_per_system": page_gt.get("staves_per_system"),
            "n_staves": page_gt.get("n_staves"),
            "break_indices": None,
            "source": "benchmarks/omr-phase1-baseline/ground-truth.json",
            "method": f"hand-verified ({page_gt.get('verified_by', 'unspecified')})",
            "notes": " ".join(page_gt.get("notes", [])) or None,
            "ambiguous": False,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    eg_rows = import_eval_grouping_cases()
    fd_rows = import_fulldist_cases()
    p1_rows = import_phase1_baseline_cases()
    cases = eg_rows + fd_rows + p1_rows

    ids = [c["case_id"] for c in cases]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise RuntimeError(f"duplicate case_ids, fix the slugging: {dupes}")

    out_doc = {
        "generated_by": "import_gt.py",
        "counts": {
            "eval_grouping.py": len(eg_rows),
            "fulldist.py": len(fd_rows),
            "phase1_baseline": len(p1_rows),
            "total": len(cases),
            "missing": len(missing),
        },
        "note": ("Rows from eval_grouping.py and fulldist.py often cover the SAME physical page "
                 "(count-level and partition-level truth for the same adjudication) — both are kept "
                 "as independent rows, not merged/deduped, since they are two distinct source files "
                 "as instructed. This means some physical pages are scored twice, from two angles."),
        "cases": cases,
        "missing": missing,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, indent=2) + "\n")

    print(f"eval_grouping.py : {len(eg_rows):3d} cases")
    print(f"fulldist.py      : {len(fd_rows):3d} cases")
    print(f"phase1_baseline  : {len(p1_rows):3d} cases")
    print(f"TOTAL            : {len(cases):3d} cases, {len(missing)} missing")
    for m in missing:
        print(f"  MISSING [{m['source']}] {m['identifier']}: {m['reason']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
