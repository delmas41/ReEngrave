#!/usr/bin/env python3
"""Ask BOTH key-signature readers the same question on the same header crops.

    python3 benchmarks/omr-keysig-truth-2026-09/probe_readers.py
    python3 benchmarks/omr-keysig-truth-2026-09/probe_readers.py --clef truth

⚠️ WHY THIS IS NOT A RE-GATHER. Everything the key signature is read from is
detector-free: `prepare_pages` renders, detects staves and cuts cells, and
`header_cells_for_page` crops each staff's header. No YOLO, no Surya, no
132 MB record — four pages in about fifteen seconds. What it CANNOT reproduce
is `occupied_boxes`, which GATHER passes from the detector's own boxes, so the
probe prints how faithfully it reproduces the shipped artefact's verdicts as
its own control, and that number is the honest bound on everything below it.

⚠️ `--clef truth` REMOVES THE CLEF FROM THE EXPERIMENT. The slot table is
chosen by the clef, so a key reader scored on a page whose clefs are wrong is
being scored for two things at once. Run both: `--clef read` is the shipped
configuration, `--clef truth` is the key reader alone. On these four pages
they very nearly coincide, which is itself the finding.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

PDF = ("library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
       "imslp984073.pdf")
PAGES = [1, 2, 3, 4]
#: The four clefs `key_signature_geometry` has a slot table for — the same
#: tuple GATHER walks, imported rather than restated so the two cannot drift.


def run(clef_source: str) -> list[dict]:
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _SLOT_TABLE_CLEFS, _system_local
    from tools.omr.staff_header import header_cells_for_page
    from tools.omr.key_signature_locator import locate_key_signature
    from tools.omr.key_signature_template import read_key_signature

    truth = json.loads((HERE / "truth.json").read_text())
    by_sys = {(t["page"], t["system"]): t for t in truth["systems"]}
    graded = json.loads((HERE / "grade-before.json").read_text())
    read_clef = {(g["page"], g["system"], g["staff"]): g["read_clef"]
                 for g in graded}

    out: list[dict] = []
    for pws, _cells in prepare_pages(str(ROOT / PDF), PAGES):
        p = pws.page.page_index
        local = _system_local(pws.staves)
        header = header_cells_for_page(pws)
        for st in pws.staves:
            sys_idx, st_idx = local[st.staff_index]
            spec = by_sys.get((p, sys_idx))
            if spec is None or st_idx >= len(spec["lineup"]):
                continue
            inst = spec["lineup"][st_idx]
            t = truth["instruments"][inst]
            clef = (t["clef"] if clef_source == "truth"
                    else read_clef.get((p, sys_idx, st_idx)))
            row = {"page": p, "system": sys_idx, "staff": st_idx,
                   "instrument": inst, "truth_fifths": t["fifths"],
                   "clef_used": clef,
                   "loc_fifths": None, "loc_n": None, "loc_acc": None,
                   "loc_decided_by": None, "loc_inferred": 0,
                   "tpl_fifths": None, "tpl_acc": None,
                   "fits": []}
            crop = header.get(st.staff_index)
            if crop is None or clef is None:
                out.append(row)
                continue
            # Which clefs' slot tables the run fits at all — GATHER's own
            # question, and the input `adjudicate_key_signature` matches on.
            for cand in _SLOT_TABLE_CLEFS:
                try:
                    f = locate_key_signature(crop, cand)
                except Exception:                             # noqa: BLE001
                    continue
                if f is not None:
                    row["fits"].append(cand)
            try:
                found = locate_key_signature(crop, clef)
            except Exception:                                 # noqa: BLE001
                found = None
            if found is not None:
                row["loc_fifths"] = found.read.fifths
                row["loc_n"] = len(found.boxes)
                row["loc_acc"] = found.accidental
                row["loc_decided_by"] = found.decided_by
                row["loc_inferred"] = len(found.read.inferred_slots)
            try:
                tpl = read_key_signature(crop, clef)
            except Exception:                                 # noqa: BLE001
                tpl = None
            if tpl is not None:
                row["tpl_fifths"] = tpl.fifths
                row["tpl_acc"] = tpl.accidental
            out.append(row)
    return out


def grade(rows: list[dict], field: str) -> dict[str, int]:
    t: dict[str, int] = {"correct": 0, "wrong": 0, "abstained": 0}
    for r in rows:
        v = r[field]
        if v is None:
            t["abstained"] += 1
        elif v == r["truth_fifths"]:
            t["correct"] += 1
        else:
            t["wrong"] += 1
    return t


def main(argv: list[str]) -> int:
    src = "truth" if "--clef" in argv and "truth" in argv else "read"
    rows = run(src)
    print(f"clef source: {src}    rows: {len(rows)}\n")

    print(f"{'pg/sy':>6} {'#':>2} {'instrument':<20} {'clef':<7} {'tru':>4} "
          f"{'LOC':>4} {'n':>2} {'acc':>3} {'by':<8} {'inf':>3}  {'TPL':>4} "
          f"fits")
    for r in rows:
        print(f"{r['page']}/{r['system']:<4} {r['staff']:>2} "
              f"{r['instrument']:<20} {str(r['clef_used']):<7} "
              f"{r['truth_fifths']:>4} {str(r['loc_fifths']):>4} "
              f"{str(r['loc_n']):>2} {str(r['loc_acc']):>3} "
              f"{str(r['loc_decided_by']):<8} {r['loc_inferred']:>3}  "
              f"{str(r['tpl_fifths']):>4} {','.join(r['fits'])}")

    print("\nLOCATOR  (what GATHER uses today):", grade(rows, "loc_fifths"))
    print("TEMPLATE (ASSUMPTIONS.md D20)     :", grade(rows, "tpl_fifths"))

    # ── The probe's own control ──────────────────────────────────────────────
    # A probe that cannot reproduce the artefact is measuring something else.
    # It cannot pass `occupied_boxes`, so agreement is expected to be high and
    # not perfect, and the number is printed rather than assumed.
    graded = json.loads((HERE / "grade-before.json").read_text())
    ship = {(g["page"], g["system"], g["staff"]): g["read_fifths"]
            for g in graded}
    same = sum(1 for r in rows
               if ship.get((r["page"], r["system"], r["staff"]))
               == r["loc_fifths"])
    print(f"\nCONTROL — probe locator vs the SHIPPED artefact's verdicts: "
          f"{same}/{len(rows)} identical")
    if same == 0:
        print("DEAD INSTRUMENT: the probe reproduces nothing.")
        return 2

    name = f"readers-{src}.json"
    json.dump(rows, (HERE / name).open("w"), indent=1)
    print(f"wrote {HERE / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
