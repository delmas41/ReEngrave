"""Re-run the 20-row scan gate with `OMR_CONTEST_DUMP=1` and keep only the
contest records.

`_dedupe_cross_staff_detections` already carries reach instrumentation that
records, per contested pair, both detections' CONFIDENCES and the tier that
actually decided it. The range-veto session used it and its dumps are gone, so
this regenerates them -- and unlike that session it keeps the confidences, which
is what the additive-vs-gated question needs.

⚠️ Nothing here changes a verdict: `OMR_CONTEST_DUMP` is documented at
`transcribe.py:2789` as "REACH INSTRUMENTATION ONLY ... it changes no verdict".
The transcriptions are written to this benchmark's own out/ dir, never to the
gate's fixtures.

    OMR_SURYA_KEEP_ALIVE=0 python3 <this> --rows 11    # the 11 committed rows
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[1]))

os.environ["OMR_CONTEST_DUMP"] = "1"
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

from tools.omr.transcribe import transcribe, DEFAULT_WEIGHTS  # noqa: E402

WORKS = MAIN / "benchmarks/omr-scan-e2e-2026-09/works.json"
LIB = MAIN / "library"
OUT = HERE / "out/contests"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma list of row_ids")
    ap.add_argument("--committed-only", action="store_true",
                    help="only rows that already have a .graft09 fixture")
    args = ap.parse_args()

    spec = json.loads(WORKS.read_text())
    rows = spec["rows"]
    proto = spec["protocol"]
    fixtures = MAIN / "benchmarks/omr-scan-e2e-2026-09/fixtures"
    if args.only:
        want = set(args.only.split(","))
        rows = [r for r in rows if r["row_id"] in want]
    if args.committed_only:
        rows = [r for r in rows
                if (fixtures / f"{r['row_id']}..graft09.omr.json").is_file()]
    OUT.mkdir(parents=True, exist_ok=True)

    for row in rows:
        dest = OUT / f"{row['row_id']}.contests.json"
        if dest.is_file():
            print(f"skip {row['row_id']} (have it)", flush=True)
            continue
        pdf = LIB / row["edition"]["catalog_path"]
        t0 = time.time()
        result = transcribe(
            pdf_path=pdf,
            pages=[row["page"]["pdf_page_index"]],
            weights=str(DEFAULT_WEIGHTS),
            dpi=proto["dpi"],
            conf_threshold=proto["conf_threshold"],
            imgsz=proto["imgsz"],
            dossier=None,
            read_direction_text=False,   # irrelevant to the dedupe; saves OCR
            progress=False,
        )
        pages = []
        for page in result.get("pages", []):
            staves = {}
            for sysm in page.get("systems", []):
                for st in sysm.get("staves", []):
                    staves[st.get("staff_index")] = {
                        "clef": st.get("clef"),
                        "clef_source": st.get("clef_source"),
                        "instrument": st.get("instrument"),
                        "instrument_source": st.get("instrument_source"),
                    }
            pages.append({
                "page_index": page.get("page_index"),
                "staves": staves,
                "contests": page.get("contested_notehead_pairs", []),
                "n_cross_staff_duplicates_removed":
                    page.get("n_cross_staff_duplicates_removed"),
            })
        dest.write_text(json.dumps(
            {"row_id": row["row_id"], "seconds": round(time.time() - t0, 1),
             "pages": pages}, default=str) + "\n")
        n = sum(len(p["contests"]) for p in pages)
        print(f"{row['row_id']}: {n} contests  {time.time()-t0:.0f}s",
              flush=True)


if __name__ == "__main__":
    main()
