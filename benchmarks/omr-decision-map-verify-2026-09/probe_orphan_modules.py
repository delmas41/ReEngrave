"""Which tools/omr modules have no production IMPORTER?

Production = tools/omr/**/*.py excluding tests/, plus backend/** and the other
tools/ packages. Reports modules imported only by tests and/or benchmarks.

⚠️ AN IMPORT GRAPH IS NOT A CONSUMPTION GRAPH, and this probe is wrong in four
known ways. Every hit needs a human before it is called an orphan:

  * `_surya_worker`   — invoked as a SUBPROCESS by path
                        (`staff_labels_surya.py:68`), never imported.
  * `run_pipeline`    — a `python3 -m tools.omr.run_pipeline` CLI entry point.
  * `_omrned_worker`  — runs INSIDE `.venv-omrned` and must not import tools.*
  * `page_truth`, `score_reading`, `score_translation`
                      — measurement modules that belong to
                        `benchmarks/omr-reading-vs-reproduction-2026-09/`.

DO NOT READ THE OUTPUT AS A DELETE LIST. The genuine findings as of 2026-09-07
were `bracket_reader` (390 lines), `hairpin_detection` (344) and
`condensed_parts` (127) — see FINDINGS.md E10 and E9.
"""
import pathlib
import re

ROOT = pathlib.Path(".")
OMR = ROOT / "tools" / "omr"

mods = sorted(p.stem for p in OMR.glob("*.py") if p.stem != "__init__")

prod = [p for p in OMR.rglob("*.py") if "tests" not in p.parts]
prod += [p for p in (ROOT / "backend").rglob("*.py") if "tests" not in p.parts]
prod += [p for p in (ROOT / "tools").glob("*.py")]
prod += [p for p in (ROOT / "tools" / "library").rglob("*.py")] if (ROOT / "tools" / "library").exists() else []
prod += [p for p in (ROOT / "tools" / "dashboard").rglob("*.py")] if (ROOT / "tools" / "dashboard").exists() else []

texts = {p: p.read_text(errors="ignore") for p in prod}

bench = [p for p in (ROOT / "benchmarks").rglob("*.py")]
btexts = {p: p.read_text(errors="ignore") for p in bench}
tests = [p for p in OMR.rglob("*.py") if "tests" in p.parts]
ttexts = {p: p.read_text(errors="ignore") for p in tests}

for m in mods:
    pat = re.compile(
        r"(from\s+\.{0,2}" + m + r"\s+import|import\s+\.{0,2}" + m + r"\b"
        r"|from\s+tools\.omr\." + m + r"\s+import|tools\.omr\." + m + r"\b)"
    )
    prod_imp = [str(p) for p, t in texts.items() if p.stem != m and pat.search(t)]
    if prod_imp:
        continue
    t_imp = [str(p) for p, t in ttexts.items() if pat.search(t)]
    b_imp = [str(p) for p, t in btexts.items() if pat.search(t)]
    n_lines = len((OMR / (m + ".py")).read_text(errors="ignore").splitlines())
    print(f"NO PRODUCTION IMPORTER: {m:<32} {n_lines:>5} lines "
          f"| tests={len(t_imp)} bench={len(b_imp)}")
    for x in (t_imp + b_imp)[:4]:
        print("      ", x)
