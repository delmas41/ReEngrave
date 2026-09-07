"""Price the veto on the committed Brahms blob, with NO re-transcription.

The rule is a PURE function of things the blob already records — each slot's
name, its source, and which staff record sits in which slot — so applying it
offline is the same computation the pipeline would do, not an approximation.
The output is a blob identical to its input except for the `vetoes` list, which
`score_brahms_lineups.py --veto both` then prices against the hand-read truth.

⚠️ The roster is passed in as a set of names, exactly as the production seam
passes it: this probe does not read `catalog.json` and neither does
`offroster_name.py`. The names below are transcribed from the work's IMSLP
`InstrDetail` (`source_kind: catalog`) and the string section, which that
catalog's parse drops as a section word.

Usage:  price_offline.py IN.json OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.offroster_name import find_offroster_vetoes, summarise  # noqa

BRAHMS1_ROSTER = {"Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                  "Horn", "Trumpet", "Trombone", "Timpani",
                  "Violin", "Viola", "Cello", "Contrabass"}


def main(src: str, dst: str) -> None:
    doc = json.loads(Path(src).read_text())
    b = doc["contextual"]["absent_instrument_veto"]
    si = {s["slot"]: s for s in b["slot_instruments"]}
    names = {k: v["instrument"] for k, v in si.items()}
    source = {k: v["source"] for k, v in si.items()}
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in b["staff_slots"]}
    evidence: dict[int, dict[int, str]] = {}
    for e in b["label_evidence"]:
        evidence.setdefault(e["page_index"], {})[e["staff_index"]] = \
            e["instrument"]

    v = find_offroster_vetoes(
        staff_keys=list(slot_by_staff), slot_by_staff=slot_by_staff,
        instrument_name_by_slot=names, instrument_source=source,
        admissible=BRAHMS1_ROSTER, evidence=evidence)
    s = summarise(v, BRAHMS1_ROSTER, "brahms--symphony-1")
    read = sorted({r["read"] for r in v if r["read"]})
    print(f"  vetoed staves whose OWN margin contradicts the name: "
          f"{sum(1 for r in v if r['read'])} — reading {read}")
    print(f"{src}")
    print(f"  slots vetoed: {s['slots_vetoed']}  by instrument: "
          f"{s['by_instrument']}")
    print(f"  staff records vetoed: {s['staff_records_vetoed']} of "
          f"{len(slot_by_staff)}")

    # The scorer reads `vetoes`; everything else is carried through untouched
    # so the two arms share one staff-record key set (it asserts on that).
    doc["contextual"]["absent_instrument_veto"]["vetoes"] = v
    Path(dst).write_text(json.dumps(doc, sort_keys=True))
    print(f"  -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
