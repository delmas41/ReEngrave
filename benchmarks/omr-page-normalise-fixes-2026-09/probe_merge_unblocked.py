"""Does the reviewed merge tool still REFUSE the four Mahler rows? No.

`merge_additions.check_row` proves a map by running `page_normalise.normalise`
on it before anything is written, so the two faults were not merely a probe
inconvenience: they were a hard block on writing a map a human had confirmed.
This asks the shipped tool, unmodified, with a SIMULATED `done` additions row
per candidate — and writes nothing at all.

⚠️ THIS IS NOT A MERGE AND MUST NOT BE READ AS ONE. `works.json` is
hand-verified truth, the real additions file for these rows is still
`status: "in_progress"` (Sean's 57-slot confirmation pass has not been run),
and `merge_additions` REFUSES to overwrite a row that already carries a map —
so writing an unconfirmed map now would lock Sean's own reading out of the
file it belongs in. The command to run afterwards is printed at the end.

⚠️ AND IT ASSERTS WHICH `page_normalise` IT LOADED. `merge_additions` resolves
its imports through `build_cache.MAIN`, which is the hard-coded MAIN CHECKOUT —
so a naive run from a worktree proves the map against MAIN's copy of the module
and would report the fix as working (or not) on the wrong file entirely.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_merge_unblocked.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
sys.path.insert(0, str(SCAN))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-staves-map-completion-2026-09"))

import page_normalise                                    # noqa: E402

# Bind THIS tree's module before merge_additions can bind the main checkout's.
assert Path(page_normalise.__file__).resolve() == (SCAN / "page_normalise.py"), \
    f"loaded {page_normalise.__file__}, not this worktree's module"
sys.modules["page_normalise"] = page_normalise

sys.path.insert(0, str(ROOT / "benchmarks" / "omr-staves-map-2026-09"))
import candidate_maps                                    # noqa: E402
import merge_additions                                   # noqa: E402

MAHLER = [r for r in candidate_maps.CANDIDATES if r.startswith("mahler")]


def main() -> int:
    works = json.loads((SCAN / "works.json").read_text())
    by_id = {r["row_id"]: r for r in works["rows"]}

    rows = []
    for rid in candidate_maps.CANDIDATES:
        add = {"row_id": rid, "status": "done",
               "staves": [{"name": s["name"], "parts": s["parts"]}
                          for s in candidate_maps.flat_sorted(rid)]}
        res = merge_additions.check_row(rid, by_id[rid], add)
        rows.append({"row_id": rid, "ok": not res["problems"],
                     "problems": res["problems"], "n_staves": res["n_staves"],
                     "n_parts_named": res["n_parts_named"],
                     "normalised": res["normalised"]})
        mark = "OK  " if not res["problems"] else "REFUSE"
        n = res["normalised"] or {}
        print(f"  {mark} {rid:34s} {res['n_staves']:>3d} entries, "
              f"{res['n_parts_named']:>3d} parts named  "
              f"{n.get('n_source_parts', '-')} -> {n.get('n_output_parts', '-')}")
        for p in res["problems"]:
            print(f"          - {p}")

    blocked = [r["row_id"] for r in rows
               if r["row_id"] in MAHLER and not r["ok"]]
    doc = {
        "generated_by": "benchmarks/omr-page-normalise-fixes-2026-09/"
                        "probe_merge_unblocked.py",
        "page_normalise_file": str(page_normalise.__file__),
        "transform_version": page_normalise.TRANSFORM_VERSION,
        "wrote_works_json": False,
        "additions_status_on_disk": "in_progress (the maps here are SIMULATED "
                                    "done — Sean's confirmation pass has not "
                                    "been run)",
        "mahler_rows_still_blocked": blocked,
        "rows": rows,
    }
    (HERE / "merge-unblocked.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print()
    print("still blocked:", blocked or "none — all four Mahler rows validate")
    print("NOTHING WAS WRITTEN. After the confirmation pass marks the rows "
          "'done', the merge is:\n"
          "  python3 benchmarks/omr-staves-map-2026-09/merge_additions.py \\\n"
          "      --additions benchmarks/omr-scan-e2e-2026-09/"
          "works.staves-additions-completion.json          # dry run\n"
          "  … then the same command with --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
