"""Is PROMOTING a per-system lineup to a flat page map sound, or forced?

`systems_as_printed._purpose` says these rows carry no `staves` map because
"system counts 11 vs 8 make export stitching refuse, so predicted parts stay
per-system and a single positional map cannot pair them".  That is a real cost,
and it reads like a judgement that promotion is unsound.  This asks the
consumer directly instead of re-reading the note.

THE ARGUMENT THE NOTE'S REASONING DOES NOT REACH: `page_normalise` never pairs
anything.  It consumes the map to MERGE REFERENCE PARTS into a derived truth
whose parts are the page's staves — the prediction is not an input to it, and
`musicdiff` does the pairing afterwards, on parts, as it always did.  So
"predicted parts stay per-system and cannot be paired positionally" is a
statement about the PREDICTION side; it prices into the row's OMR-NED either
way and is untouched by whether the truth is normalised.

⚠️ WHAT THIS PROBE DOES NOT SHOW: that promotion IMPROVES the number.  A
normalised figure is a new benchmark era (`page_normalise` rule 5) and may not
be differenced against the un-normalised 0.8444 in either direction.  This
shows only that the transform is well-defined on these maps and accounts for
every reference part.

    python3 benchmarks/omr-staves-map-2026-09/probe_promotion_is_sound.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
from build_cache import SCAN, default_cache, find_fixture  # noqa: E402

sys.path.insert(0, str(SCAN))


def main() -> int:
    import page_normalise

    idx = json.loads((default_cache() / "index.json").read_text())
    print("Does page_normalise ACCEPT the flat collapse of a per-system "
          "lineup?\n")
    bad = 0
    for r in idx["rows"]:
        rid = r["row_id"]
        m = [{"name": s["name"], "parts": s["parts"]}
             for s in r["proposal"]["staves"]]
        truth, _ = find_fixture(rid, ".truth.musicxml")
        try:
            _, rep = page_normalise.normalise(truth, m)
            print(f"  ACCEPT {rid:34} {rep['n_source_parts']:>2} parts -> "
                  f"{rep['n_output_parts']:>2} staves   "
                  f"exact-dup {rep['exact_duplication_share']:<6} "
                  f"divisi {rep['divisi_share']}")
        except Exception as exc:                      # noqa: BLE001
            bad += 1
            print(f"  REFUSE {rid:34} {type(exc).__name__}: {exc}")
    print(f"\n{len(idx['rows']) - bad} of {len(idx['rows'])} accepted.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
