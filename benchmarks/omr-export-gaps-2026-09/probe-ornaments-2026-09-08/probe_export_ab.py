"""Before/after on a REAL transcription, scored with the SYMBOL LEDGER.

⚠️ NOT WITH OMR-NED, deliberately. `docs/handoff-2026-09-08-next-steps.md` §2
measured that musicdiff's amplification differs 6x to 2x by error kind and that
one changed `<type>` scores ZERO on 10 of 20 files — bucket totals cannot rank
work and attribution through it is void. `tools/omr/symbol_ledger.py` gives one
row per symbol addressed part/bar/beat, is pure stdlib, and already emits an
`ornament` family with the mark's element name. It is the right instrument and
it runs with no venv.

WHAT THE ARMS ARE.

  BEFORE  the stored transcription, exported by this tree.
  AFTER   the same transcription with `ornaments` written onto the detection
          dicts the probe's page-pixel attach places, exported by this tree.

⚠️ The attach is `probe_ornament_reach`'s page-pixel re-implementation, because
the shipped pass runs at transcribe time in a canonical cell frame that cannot
be reconstructed without the detector. So this arm prices the EXPORT half on
real detections; the unit tests price the attach half. Said plainly rather than
blurred: the substitution is the frame, not the rule.

A SYNTHETIC TREMOLO ARM runs beside it, because the repository contains no
`tremolo1`-`tremolo5` detection at any confidence and the engraved benchmark's
whole `<ornaments>` population is tremolo. Nothing else can exercise that path.

    python3 benchmarks/omr-export-gaps-2026-09/probe-ornaments-2026-09-08/probe_export_ab.py
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.export import to_musicxml                       # noqa: E402
from tools.omr.symbol_ledger import extract_symbols            # noqa: E402
from probe_ornament_reach import (                             # noqa: E402
    TRANSCRIPTION, attach_in_page_pixels)


def ledger_ornaments(xml: str) -> Counter:
    """`{mark: n}` for the `ornament` family, straight out of the ledger."""
    with tempfile.NamedTemporaryFile("w", suffix=".musicxml", delete=False) as f:
        f.write(xml)
        path = f.name
    symbols, _ = extract_symbols(path)
    Path(path).unlink()
    return Counter(s.attrs.get("mark") for s in symbols
                   if s.family == "ornament"), len(symbols)


def with_ornaments(result: dict) -> tuple[dict, int]:
    after = copy.deepcopy(result)
    placed = 0
    for page in after.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                for meas in staff.get("measures", []):
                    dets = meas.get("detections", [])
                    for _mark, kind, strokes, best in attach_in_page_pixels(dets):
                        if best is None:
                            continue
                        entry = {"kind": kind}
                        if strokes is not None:
                            entry["strokes"] = strokes
                        best[1].setdefault("ornaments", []).append(entry)
                        placed += 1
    return after, placed


def synthetic_tremolo(result: dict) -> dict:
    """One notehead in the document given a 3-stroke tremolo.

    The tremolo export path has no other way to be exercised: zero `tremolo1`-
    `tremolo5` detections exist in this repository.
    """
    after = copy.deepcopy(result)
    for page in after.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                for meas in staff.get("measures", []):
                    for d in meas.get("detections", []):
                        if d.get("category") == "notehead" and d.get("pitch"):
                            d["ornaments"] = [{"kind": "tremolo", "strokes": 3}]
                            return after
    raise AssertionError("no pitched notehead to mark — the arm is vacuous")


def main() -> int:
    result = json.loads(TRANSCRIPTION.read_text())

    before_xml = to_musicxml(result)
    before, n_before = ledger_ornaments(before_xml)

    after_result, placed = with_ornaments(result)
    after_xml = to_musicxml(after_result)
    after, n_after = ledger_ornaments(after_xml)

    trem_xml = to_musicxml(synthetic_tremolo(result))
    trem, _ = ledger_ornaments(trem_xml)

    print(f"transcription        {TRANSCRIPTION.relative_to(ROOT)}")
    print(f"POSITIVE CONTROLS    ledger rows BEFORE {n_before}, AFTER {n_after} "
          f"(a document with symbols in it, both arms)")
    print(f"                     <ornaments> in BEFORE xml: "
          f"{before_xml.count('<ornaments>')}, AFTER: "
          f"{after_xml.count('<ornaments>')}")
    print(f"marks attached       {placed}")
    print(f"\nledger `ornament` rows")
    print(f"  BEFORE             {dict(before) or 'NONE — the gap'}")
    print(f"  AFTER              {dict(after)}")
    print(f"  synthetic tremolo  {dict(trem)}")

    ok = True
    if placed and not after:
        print("\nFAIL: marks were attached and no ledger row came out")
        ok = False
    if before:
        print("\nFAIL: the BEFORE arm already had ornaments — not a gap")
        ok = False
    if trem.get("tremolo") != 1:
        print("\nFAIL: the synthetic tremolo did not reach the file")
        ok = False

    # The rest of the document must be untouched: an export gap fix that also
    # moved notes would be priced against a mixture.
    b_rows = [s for s in extract_all(before_xml) if s.family != "ornament"]
    a_rows = [s for s in extract_all(after_xml) if s.family != "ornament"]
    print(f"\nnon-ornament rows    BEFORE {len(b_rows)}  AFTER {len(a_rows)}  "
          f"{'identical' if len(b_rows) == len(a_rows) else 'CHANGED'}")
    if len(b_rows) != len(a_rows):
        ok = False
    print("\nOK" if ok else "\nNOT OK")
    return 0 if ok else 1


def extract_all(xml: str):
    with tempfile.NamedTemporaryFile("w", suffix=".musicxml", delete=False) as f:
        f.write(xml)
        path = f.name
    symbols, _ = extract_symbols(path)
    Path(path).unlink()
    return symbols


if __name__ == "__main__":
    raise SystemExit(main())
