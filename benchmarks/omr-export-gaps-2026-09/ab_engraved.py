"""A/B the OMR_ARC_RECLASS veto on the engraved 11-work benchmark.

Both arms score the SAME stored transcriptions — the flag lives entirely at
export time — so the baseline `orchestral_eval --omr-ned` run's fixtures are
re-exported here rather than re-transcribed:

    OFF arm: export with the flag off, and assert BYTE-EQUAL to the
             `.omr.musicxml` the eval wrote — which is both the baseline
             score's provenance and the flag-off no-op proof, per work.
    ON arm:  export with OMR_ARC_RECLASS=1, score with the same musicdiff
             harness, and record every veto firing by rule.

Usage (after a plain `orchestral_eval --omr-ned` run has filled fixtures/):

    OMRNED_PYTHON=... python3 benchmarks/omr-export-gaps-2026-09/ab_engraved.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import export as export_mod  # noqa: E402
from tools.omr import omr_ned  # noqa: E402
from tools.omr.accuracy_record import BENCHMARK_WORKS  # noqa: E402

FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"

_TIE_START = re.compile(r'<tie type="start"/>')
_SLUR_START = re.compile(r'<slur number="\d+" type="start"/>')


def _counts(xml: str) -> dict[str, int]:
    return {"ties": len(_TIE_START.findall(xml)),
            "slurs": len(_SLUR_START.findall(xml))}


def main() -> int:
    rows = []
    pooled = {"off": [0, 0, 0], "on": [0, 0, 0]}  # ed, pred_syms, truth_syms
    for work in BENCHMARK_WORKS:
        json_path = FIXTURES / f"{work}.omr.json"
        truth_path = FIXTURES / f"{work}.musicxml"
        stored = FIXTURES / f"{work}.omr.musicxml"
        if not (json_path.is_file() and truth_path.is_file()):
            print(f"{work}: fixtures missing — run orchestral_eval first")
            return 1

        result = json.loads(json_path.read_text())
        os.environ["OMR_ARC_RECLASS"] = "0"
        off_xml = export_mod.to_musicxml(result)
        identical = stored.is_file() and stored.read_text() == off_xml
        if not identical:
            print(f"{work}: FLAG-OFF EXPORT != the eval's own musicxml — "
                  "the baseline score does not describe this tree")

        os.environ["OMR_ARC_RECLASS"] = "1"
        export_mod.reset_arc_reclass_stats()
        on_xml = export_mod.to_musicxml(result)
        firings = dict(export_mod.ARC_RECLASS_STATS)
        os.environ["OMR_ARC_RECLASS"] = "0"

        on_path = FIXTURES / f"{work}.arcon.musicxml"
        on_path.write_text(on_xml)

        row = {"work": work, "off_identical_to_eval": identical,
               "firings": firings,
               "off_counts": _counts(off_xml), "on_counts": _counts(on_xml),
               "truth_counts": _counts(truth_path.read_text())}
        for arm, path in (("off", stored), ("on", on_path)):
            s = omr_ned.score_pair(pred=str(path), truth=str(truth_path),
                                   name=f"{work}.{arm}")
            row[arm] = {k: s.get(k) for k in
                        ("omr_ned", "omr_ed", "pred_symbols", "truth_symbols")}
            row[arm]["categories"] = {
                k: v for k, v in (s.get("categories") or {}).items()
                if "slur" in k or "tie" in k}
            pooled[arm][0] += s["omr_ed"]
            pooled[arm][1] += s["pred_symbols"]
            pooled[arm][2] += s["truth_symbols"]
        rows.append(row)
        print(f"{work}: off {row['off']['omr_ned']:.4f}/{row['off']['omr_ed']}"
              f" -> on {row['on']['omr_ned']:.4f}/{row['on']['omr_ed']}"
              f"  firings={firings or '{}'}  identical_off={identical}")

    out = {}
    for arm in ("off", "on"):
        ed, ps, ts = pooled[arm]
        out[arm] = {"omr_ed": ed, "pred_symbols": ps, "truth_symbols": ts,
                    "omr_ned": ed / (ps + ts)}
        print(f"pooled {arm}: {out[arm]['omr_ned']:.4f} / {ed} edits "
              f"({ps} pred + {ts} truth symbols)")
    (BENCH / "ab_engraved.json").write_text(
        json.dumps({"pooled": out, "rows": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
