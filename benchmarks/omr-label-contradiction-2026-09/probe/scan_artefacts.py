"""Sweep every committed contextual artefact for label contradictions.

A CONTRADICTION is a staff whose own margin label the reader read on THAT page
and whose exported instrument name is something else. The evidence is the
`absent_instrument_veto` summary block, which carries `label_evidence`
(per-staff, confidence-filtered), `staff_slots` and `slot_instruments` — so this
needs no re-transcription.

⚠️ Do NOT use `staff["instrument_label"]`: it is slot-carried, one raw text per
SLOT stamped onto every staff of that slot, and a check on it cannot disagree.
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def artefacts() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.json"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    keep = []
    for rel in out:
        p = ROOT / rel
        try:
            txt = p.read_text()
        except Exception:
            continue
        if '"absent_instrument_veto"' in txt:
            keep.append(p)
    return keep


def contradictions(doc: dict) -> tuple[list[dict], int]:
    """`(rows, n_labelled_staff_records)` for one artefact."""
    a = doc["contextual"]["absent_instrument_veto"]
    ev = {(r["page_index"], r["staff_index"]): r["instrument"]
          for r in a["label_evidence"]}
    slot_name = {r["slot"]: r["instrument"] for r in a["slot_instruments"]}
    slot_src = {r["slot"]: r.get("source", "label")
                for r in a["slot_instruments"]}
    vetoed = ({(r["page_index"], r["system_index"], r["staff_index"])
               for r in a.get("vetoes", [])}
              if a.get("mode") == "apply" else set())
    rows, labelled = [], 0
    for r in a["staff_slots"]:
        key = (r["page_index"], r["system_index"], r["staff_index"])
        slot = r["slot"]
        if slot is None or slot < 0:
            continue
        read = ev.get((r["page_index"], r["staff_index"]))
        if read is None:
            continue
        exported = None if key in vetoed else slot_name.get(slot)
        if exported is None:
            continue
        labelled += 1
        if read != exported:
            rows.append({"page_index": r["page_index"],
                         "system_index": r["system_index"],
                         "staff_index": r["staff_index"], "slot": slot,
                         "read": read, "exported": exported,
                         "source": slot_src.get(slot, "label")})
    return rows, labelled


def main() -> None:
    out = []
    for p in sorted(artefacts()):
        doc = json.loads(p.read_text())
        rows, labelled = contradictions(doc)
        by_src = Counter(r["source"] for r in rows)
        out.append({
            "artefact": str(p.relative_to(ROOT)),
            "pdf": Path(doc.get("source_pdf", "?")).name,
            "pages": len(doc.get("pages", [])),
            "mode": doc["contextual"]["absent_instrument_veto"].get("mode"),
            "spans": doc.get("movement_reference"),
            "labelled_records": labelled,
            "contradictions": len(rows),
            "by_source": dict(by_src),
            "rows": rows,
        })
    dest = ROOT / "benchmarks/omr-label-contradiction-2026-09/out/scan.json"
    dest.write_text(json.dumps(out, indent=1))
    hdr = f"{'artefact':76} {'pg':>3} {'lab':>5} {'contra':>6}  by source"
    print(hdr)
    print("-" * len(hdr))
    for r in out:
        print(f"{r['artefact']:76} {r['pages']:3d} {r['labelled_records']:5d} "
              f"{r['contradictions']:6d}  {r['by_source']}")


if __name__ == "__main__":
    main()
