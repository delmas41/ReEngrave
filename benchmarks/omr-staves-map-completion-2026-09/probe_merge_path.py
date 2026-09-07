"""Would a CONFIRMED map actually merge? Asked of `merge_additions.check_row`.

The confirmation UI is worth nothing if the thing it produces cannot be written,
so the whole chain is exercised before Sean is asked for a keystroke: a
simulated `done` additions row per candidate, put through the reviewed merge
tool's own validation, on a SCRATCH copy of works.json.

⚠️ RUN BOTH WAYS. `merge_additions` proves a map by running
`page_normalise.normalise` on it, and two of these rows make the shipped
transform raise (see `normalise_patched.py`). So the unpatched arm is the
BLOCKER report and the patched arm is what the merge would do once the two
one-line faults are fixed.

    python3 probe_merge_path.py              # both arms
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-staves-map-2026-09"))
sys.path.insert(0, str(HERE))

import candidate_maps                                    # noqa: E402
import merge_additions                                   # noqa: E402


def additions_doc() -> dict:
    rows = {}
    for rid in candidate_maps.CANDIDATES:
        rows[rid] = {
            "row_id": rid, "status": "done",
            "staves": [{"name": s["name"], "parts": s["parts"]}
                       for s in candidate_maps.flat_sorted(rid)],
        }
    return {"rows": rows}


def run(patched: bool) -> list[dict]:
    if patched:
        import normalise_patched
        normalise_patched.apply()
    else:
        try:
            import normalise_patched
            normalise_patched.restore()
        except ImportError:
            pass
    works = json.loads((MAIN / "benchmarks/omr-scan-e2e-2026-09"
                        "/works.json").read_text())
    by_id = {r["row_id"]: r for r in works["rows"]}
    add = additions_doc()
    out = []
    for rid, a in add["rows"].items():
        res = merge_additions.check_row(rid, by_id[rid], a)
        out.append({"row_id": rid, "ok": not res["problems"],
                    "problems": res["problems"],
                    "n_staves": res["n_staves"],
                    "normalised": res["normalised"]})
    return out


def main() -> int:
    doc = {}
    for label, patched in (("shipped page_normalise", False),
                           ("with the two one-line fixes", True)):
        print("=" * 72)
        print(label)
        res = run(patched)
        doc[label] = res
        for r in res:
            mark = "OK  " if r["ok"] else "FAIL"
            n = r["normalised"] or {}
            print(f"  {mark} {r['row_id']:34s} {r['n_staves']:>3d} entries  "
                  f"{n.get('n_source_parts', '-')} -> "
                  f"{n.get('n_output_parts', '-')} parts")
            for p in r["problems"]:
                print(f"        {p}")
    (HERE / "merge-path.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print("\nwrote", HERE / "merge-path.json")
    # a scratch copy is made but never written to, so nothing here can touch
    # the real works.json — proved by leaving --write out entirely
    with tempfile.TemporaryDirectory() as td:
        shutil.copy2(MAIN / "benchmarks/omr-scan-e2e-2026-09/works.json",
                     Path(td) / "works.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
