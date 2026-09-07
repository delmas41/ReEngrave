"""Assert the harness's report and file-write live inside `main()`.

⚠️ WHY THIS EXISTS. A module-level `def` written into the middle of a function
TERMINATES that function's body, and the result is valid Python that
`ast.parse` accepts without complaint. That happened here on 2026-09-07: two
helper `def`s were text-inserted into `main()`, everything after them — the
pooling, the `doc` literal, the file write and the entire report — silently
became the body of the second helper, and `main()` fell off its end returning
`None`. `sys.exit(None)` exits **0**. The run printed nothing, wrote nothing,
and did it AFTER 615 s of musicdiff.

A syntax check cannot see this. This asks where the code IS.

    python3 benchmarks/omr-slot-stitch-reprice-2026-09/check_harness_structure.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "reprice_arm.py"

#: Each must appear inside `main`'s own source segment, not merely in the file.
REQUIRED_IN_MAIN = {
    "writes the results file": "write_text(json.dumps(doc",
    "builds the doc": "    doc = {",
    "calls transform_accounting": "transform_accounting(norml",
    "calls reproduces_recorded": "reproduces_recorded(entries)",
    "prints the accounting": "transform accounting (rule 4)",
    "scores one batch with an explicit timeout": "timeout_s=3600",
}
REQUIRED_MODULE_LEVEL = {"transform_accounting", "reproduces_recorded",
                         "main", "reach", "export_with_flag"}


def main() -> int:
    src = TARGET.read_text()
    tree = ast.parse(src)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    ok = True
    missing = REQUIRED_MODULE_LEVEL - set(fns)
    print(f"{'PASS' if not missing else 'FAIL'}  every helper is module-level"
          + (f" (missing {sorted(missing)})" if missing else ""))
    ok &= not missing

    if "main" not in fns:
        print("FAIL  no module-level main()")
        return 1
    seg = ast.get_source_segment(src, fns["main"]) or ""
    for label, needle in REQUIRED_IN_MAIN.items():
        hit = needle in seg
        print(f"{'PASS' if hit else 'FAIL'}  main() {label}")
        ok &= hit
    ends = seg.rstrip().endswith("return 0")
    print(f"{'PASS' if ends else 'FAIL'}  main() ends in an explicit `return 0` "
          "(a fall-through returns None, which exits 0 and looks like success)")
    ok &= ends
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
