"""One row per (regime, arm): does the flag reach this page set at all?

⚠️ **THREE REGIMES, NOT TWO** — this repo learned it the hard way on 2026-09-06,
when a whole-work run contradicted every single-page measurement that shipped
the feature. A change can measure exactly zero in two of them and matter in the
third:

  narrow-at-the-front   `--pages 0-4`, which is what the web app does
                        (`OMR_MAX_PAGES=5`);
  narrow-anywhere       a window CROSSING a lineup boundary, which is the run a
                        reader makes by hand and the one `movement_reference`
                        records as its worst case;
  whole-work            what `_align_by_span` was built for.

Reports, per blob: spans taken, whether `_align_by_span` was reached, the
impossible-name count under the work's own rule, and the self-contradiction
count (a staff whose own margin label was read and which is exported as
something else — free evidence, no truth file).

Usage: regime_report.py --finale-page 45 --impossible Trombone,Tuba LABEL=BLOB ...
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def read(path):
    r = json.loads(Path(path).read_text())
    b = r["contextual"]["absent_instrument_veto"]
    slot = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
            for s in b["staff_slots"]}
    name = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    vet = {(v["page_index"], v["system_index"], v["staff_index"])
           for v in b["vetoes"]}
    ev = collections.defaultdict(dict)
    for e in b["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    return r, slot, name, vet, ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--finale-page", type=int, required=True)
    ap.add_argument("--impossible", required=True)
    ap.add_argument("blobs", nargs="+")
    args = ap.parse_args()
    bad_names = set(args.impossible.split(","))

    print(f"{'label':34s} {'staves':>7s} {'slots':>6s} {'IMPOSS':>7s} "
          f"{'IMPOSS+veto':>12s} {'contra':>7s}   slot fingerprint")
    for spec in args.blobs:
        label, path = spec.split("=", 1)
        r, slot, name, vet, ev = read(path)
        imp = imp_v = contra = 0
        for k, s in slot.items():
            nm = name.get(s) if s >= 0 else None
            if k[0] < args.finale_page and nm in bad_names:
                imp += 1
                if k not in vet:
                    imp_v += 1
            own = ev.get(k[0], {}).get(k[2])
            if own and nm and own != nm:
                contra += 1
        fp = hash(tuple(sorted(slot.items()))) & 0xFFFFFF
        print(f"{label:34s} {len(slot):7d} "
              f"{len(r['contextual']['reference'] or []):6d} {imp:7d} "
              f"{imp_v:12d} {contra:7d}   {fp:06x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
