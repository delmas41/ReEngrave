#!/usr/bin/env python3
"""Phase 1 classification: why does a staff's identity resolve to nothing?

Reads `ladder.json` (written by `probe_ladder.py`, which runs EVERY reader rung
on EVERY page) and the scan benchmark's `works.json` truth, and puts each staff
in exactly one class:

    RESOLVED_OK   a rung read a string, the lexicon resolved it, and it agrees
                  with the printed truth
    (e) WRONG     resolved, and it DISAGREES with the printed truth
    (d) REFUSED   a rung returned a non-empty string and the lexicon refused it
    (bc) EMPTY    no rung returned anything for this staff — (a) no label
                  printed / (b) crop misses it / (c) crop right, OCR empty.
                  These three are not separable without looking at the page, so
                  they are emitted as one class with the crop file named, and
                  split by hand in FINDINGS.

⚠️ THE JOIN IS BY PRINTED POSITION WITHIN A SYSTEM, never by pipeline slot.
The coordinating session reports a confirmed live case (`*-p4` rows) where the
readers read the margin correctly and `export._stitch_slots` filed the reading
under the wrong slot — a JOIN defect that would masquerade as (e) if identity
were compared slot-wise. Comparing reader-read-for-staff-i against
printed-truth-for-position-i is immune to it, and the mis-join is reported
separately rather than scored here.

⚠️ TRUTH IS JOINED ONLY WHERE THE COUNTS AGREE. A row whose detected staff
count differs from the printed truth's is reported `count_mismatch` and its
staves are classed for READING (which needs no truth) but excluded from (e).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                       # noqa: E402

WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"


def truth_for_row(row: dict, rows_by_id: dict):
    """-> (per-system list of staff dicts | flat list, provenance)."""
    st = row.get("staves")
    if isinstance(st, str) and st.startswith("same-as:"):
        return truth_for_row(rows_by_id[st.split(":", 1)[1]], rows_by_id)
    if isinstance(st, list):
        return ("flat", st, "works.json:staves")
    sysp = row.get("systems_as_printed")
    if isinstance(sysp, list):
        return ("per_system", sysp, "works.json:systems_as_printed")
    cond = row.get("condensation") or {}
    sap = cond.get("staves_as_printed")
    if isinstance(sap, list):
        return ("flat", sap, "works.json:condensation.staves_as_printed")
    return (None, None, "none")


def _names(block):
    out = []
    for e in block:
        if isinstance(e, dict):
            out.append(e.get("name"))
        else:
            out.append(e)
    return out


def main() -> int:
    lad = json.loads((HERE / "ladder.json").read_text())
    works = json.loads(WORKS.read_text())
    rows_by_id = {r["row_id"]: r for r in works["rows"]}

    per_staff = []
    row_notes = []

    for r in lad["rows"]:
        rid = r["row_id"]
        kind, truth, prov = truth_for_row(rows_by_id[rid], rows_by_id)
        by_sys = defaultdict(list)
        for s in r["staves"]:
            by_sys[s["system"]].append(s)

        # truth per system, only where the counts agree
        truth_by_sys = {}
        for sysi, staves in sorted(by_sys.items()):
            block = None
            if kind == "flat" and truth is not None:
                block = truth
            elif kind == "per_system" and truth is not None and sysi < len(truth):
                block = truth[sysi]
            if block is not None and len(block) == len(staves):
                truth_by_sys[sysi] = _names(block)
        row_notes.append({
            "row_id": rid, "truth_provenance": prov,
            "systems_with_truth": sorted(truth_by_sys),
            "systems": {si: len(v) for si, v in sorted(by_sys.items())},
            "structure_mismatch_vs_fixture": r["structure_mismatch"],
            "structure_here": r["structure_here"],
            "structure_fixture": r["structure_fixture"],
        })

        for sysi, staves in sorted(by_sys.items()):
            tnames = truth_by_sys.get(sysi)
            for i, s in enumerate(staves):
                tname = tnames[i] if tnames and i < len(tnames) else None
                tinst = None
                if tname:
                    h = lookup(tname)
                    tinst = h.instrument.name if (h and h.instrument) else None
                reads = {k: v for k, v in s["reads"].items() if v}
                resolved = s["resolved"]
                if resolved:
                    if tinst is None:
                        cls = "RESOLVED_no_truth"
                    elif resolved == tinst:
                        cls = "RESOLVED_OK"
                    else:
                        cls = "e_WRONG"
                elif reads:
                    cls = "d_REFUSED"
                else:
                    cls = "bc_EMPTY"
                per_staff.append({
                    **{k: s[k] for k in ("row_id", "system", "staff_index",
                                         "position")},
                    "reads": reads, "resolved": resolved,
                    "resolved_by": s["resolved_by"],
                    "truth_name": tname, "truth_instrument": tinst,
                    "class": cls,
                    "crop": r["crops"].get(sysi) or r["crops"].get(str(sysi)),
                })

    (HERE / "classified.json").write_text(json.dumps(
        {"rows": row_notes, "staves": per_staff}, indent=1))

    # ── report ──────────────────────────────────────────────────────────────
    tot = Counter(s["class"] for s in per_staff)
    print("ALL STAVES (20 rows):", dict(tot), "n =", len(per_staff))
    scored = [s for s in per_staff if s["truth_instrument"]]
    print("WITH TRUTH:", dict(Counter(s["class"] for s in scored)),
          "n =", len(scored))
    print()
    print(f"{'row':38} {'sys':>3} {'n':>3}  " + "  ".join(
        f"{c:>14}" for c in ("RESOLVED_OK", "e_WRONG", "d_REFUSED", "bc_EMPTY",
                             "RESOLVED_no_truth")))
    bysys = defaultdict(Counter)
    for s in per_staff:
        bysys[(s["row_id"], s["system"])][s["class"]] += 1
    for k in sorted(bysys):
        c = bysys[k]
        print(f"{k[0]:38} {k[1]:>3} {sum(c.values()):>3}  " + "  ".join(
            f"{c[x]:>14}" for x in ("RESOLVED_OK", "e_WRONG", "d_REFUSED",
                                    "bc_EMPTY", "RESOLVED_no_truth")))
    print()
    print("== (d) REFUSED — the strings the lexicon would not take")
    ref = Counter()
    for s in per_staff:
        if s["class"] == "d_REFUSED":
            for k, v in s["reads"].items():
                ref[(v, k)] += 1
    for (t, k), n in ref.most_common():
        print(f"  {n:>3}  [{k:9}] {t!r}")
    print()
    print("== (e) WRONG")
    for s in per_staff:
        if s["class"] == "e_WRONG":
            print(f"  {s['row_id']} sys{s['system']} pos{s['position']}: "
                  f"read {s['reads']} -> {s['resolved']}  TRUTH {s['truth_name']!r}"
                  f" ({s['truth_instrument']})")
    print()
    print("== (b/c) EMPTY — no rung returned anything")
    e = defaultdict(list)
    for s in per_staff:
        if s["class"] == "bc_EMPTY":
            e[s["row_id"]].append((s["system"], s["position"], s["truth_name"]))
    for rid, v in sorted(e.items()):
        print(f"  {rid}: {len(v)}")
        for sysi, pos, tn in v:
            print(f"      sys{sysi} pos{pos}  truth={tn!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
