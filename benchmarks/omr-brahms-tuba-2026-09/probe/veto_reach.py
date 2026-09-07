"""Should `absent_instrument.find_vetoes` have caught the `Tuba`? Measure it.

Two candidate reasons it did not, and they are INDEPENDENT — so widening the
first alone would change nothing:

1. `VETOABLE_SOURCES == ("label",)`, and slot 9's name is `score_order`;
2. the rule is an ATTESTATION-LOCALITY test, and `Tuba` is attested on ZERO
   pages, so `find_vetoes`' `if not pages: continue` guard fires regardless.

This replays the committed blob's own recorded `label_evidence` through
`find_vetoes` in four arms (sources x anchored-exemption) and counts how many
vetoes land on the Tuba slot.

Usage:  veto_reach.py BLOB.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import absent_instrument as ai  # noqa: E402


def main(path: str) -> None:
    b = (json.loads(Path(path).read_text())
         .get("contextual", {})["absent_instrument_veto"])
    si = {s["slot"]: s for s in b["slot_instruments"]}
    name_by_slot = {k: v["instrument"] for k, v in si.items()}
    source = {k: v["source"] for k, v in si.items()}
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in b["staff_slots"]}
    keys = list(slot_by_staff)
    evidence: dict[int, dict[int, str]] = {}
    for e in b["label_evidence"]:
        evidence.setdefault(e["page_index"], {})[e["staff_index"]] = \
            e["instrument"]

    tuba_slots = {k for k, v in name_by_slot.items() if v == "Tuba"}
    attested = ai.attested_pages(evidence)
    print(f"{path}\n  Tuba slots: {sorted(tuba_slots)}  "
          f"source: {[source[s] for s in sorted(tuba_slots)]}")
    print(f"  pages attesting a printed `Tuba` label anywhere in 86 pages: "
          f"{sorted(attested.get('Tuba', set()))}   <- the second reason")
    print(f"  pages attesting `Trombone`: "
          f"{sorted(attested.get('Trombone', set()))[:12]} ...")

    for sources in (("label",), ("label", "score_order")):
        for anchored in (True, False):
            v = ai.find_vetoes(
                staff_keys=keys, slot_by_staff=slot_by_staff,
                instrument_name_by_slot=name_by_slot,
                instrument_source=source, evidence=evidence,
                window=ai.DEFAULT_WINDOW, rule=ai.DEFAULT_RULE,
                anchored_exempt=anchored,
                reference_size=b["reference_size"])
            on_tuba = [r for r in v if r["slot"] in tuba_slots]
            print(f"  sources={sources!s:<26s} anchored_exempt={anchored!s:<6s}"
                  f" total_vetoes={len(v):4d}  on a Tuba slot={len(on_tuba)}")


if __name__ == "__main__":
    main(sys.argv[1])
