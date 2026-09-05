"""Order-conditioned evidence: does POSITION make clef / transposition sharp?

Sean's second point, tested 2026-09-05.  Score order is essentially fixed
(winds -> brass -> percussion -> strings), so the candidate set at any position
is short, and clef / transposition / range are being asked to choose within a
short list rather than across the whole lexicon.  The R&D lead's phrase:
*a signal too weak to name a staff can be strong enough to match it.*

Specifically for transposition, which is the source with a recorded death
certificate (benchmarks/omr-staff-identity-2026-09/FINDINGS.md killed S3 as an
ABSOLUTE identity signal: natural horns and trumpets print no key signature in
this repertoire, so it spoke on 2 of 36 brass staves, and "treat unread as
empty" took precision 0.645 -> 0.407).  The retest is NOT of the bare offset.
It scores

    (implied fifths offset, admissible instruments at this score-order position)

and the INTERSECTION is the evidence.  A transposing staff between the horns
and the trombones is a trumpet whatever else the offset alone would permit.

Three constraints, honoured explicitly:

 1. The admissible set comes from `score_layouts.fit_layouts` -- the ten
    standard orders already in the tree -- not from an order invented here.
    The winning layout and its agreement are reported per system, so nobody has
    to take on trust that the page was assigned to an order before the answer
    was known.
 2. Position is the staff's ordinal WITHIN ITS OWN SYSTEM.  `fit_layouts` is
    keyed by that ordinal by construction.  No `slot_index`, no
    `staff["instrument"]`, no `instrument_source` is read anywhere in this file
    -- those are assigned BY the join under test, and reading them is how
    instrument-sequence comparison went blind on the very page this is about.
 3. Coverage is reported BEFORE precision.  Position can sharpen a signal where
    it speaks; it cannot make it speak where the page prints nothing.

⚠️ A CORRECTION THIS PROBE EXISTS TO CARRY.  The first pass of
`probe_lineup_evidence.py` reported "R3 key signature: fires on 0/20" -- a clean
negative produced by an EMPTY INPUT.  It read `staff["key_signature"]["fifths"]`
and the fixtures carry `{"sharps": n, "flats": n, "alterations": {...}}` with no
`fifths` key at all, so every staff compared None to None.  The real reading is
present on 194 of 396 staves and 223 of them carry a non-empty signature.  This
is the exact failure the labels workstream's own audit note warns about, one
file over: *any audit that can return "nothing found" must first prove it looked
at something.*  Coverage is asserted here before any verdict.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave")

from tools.omr import score_layouts as sl
from tools.omr.instruments import lookup

RECON = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation/"
    "benchmarks/omr-scan-e2e-2026-09/fixtures"
)
LADDER = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a844d0d7ab60d639c/"
    "benchmarks/omr-staff-identity-labels-2026-09/ladder.json"
)
MUST_FIRE = {"beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"}
MUST_BE_SILENT = {"brahms-sym1-mvt1-317803-p3", "brahms-sym1-mvt1-317803-p4"}


def fifths(ks):
    """Signed fifths from the fixture's key-signature dict."""
    if not isinstance(ks, dict):
        return None
    return ks.get("sharps", 0) - ks.get("flats", 0)


def offset_of(name):
    m = lookup(name)
    if m is None:
        return None
    inst = getattr(m, "instrument", m)
    return getattr(inst, "default_fifths_offset", None)


def load():
    rows = {}
    paths = sorted(RECON.glob("*.reconciliation.omr.json"))
    assert paths, RECON
    for p in paths:
        assert p.name.endswith(".reconciliation.omr.json"), p
        row = p.name[: -len(".reconciliation.omr.json")]
        d = json.loads(p.read_text())
        systems = []
        for page in d["pages"]:
            for s in page["systems"]:
                systems.append(
                    [
                        {
                            "clef": st.get("clef"),
                            "ks": st.get("key_signature"),
                            "ks_read": bool(st.get("key_signature_read")),
                            "fifths": fifths(st.get("key_signature")),
                        }
                        for st in s["staves"]
                    ]
                )
        rows[row] = systems
    lab = json.loads(LADDER.read_text())
    labels = {}
    for r in lab["rows"]:
        by_sys = defaultdict(dict)
        for st in r["staves"]:
            if st.get("ladder_resolved"):
                by_sys[st["system"]][st["position"]] = st["ladder_resolved"]
        labels[r["row_id"]] = dict(by_sys)
    return rows, labels, lab["meta"]


def main():
    rows, labels, meta = load()

    # ---------------------------------------------------------- coverage
    print("=== COVERAGE, ASSERTED BEFORE ANY VERDICT ===")
    n_staves = sum(len(s) for sysd in rows.values() for s in sysd)
    n_read = sum(
        1 for sysd in rows.values() for s in sysd for st in s if st["ks_read"]
    )
    n_nonzero = sum(
        1 for sysd in rows.values() for s in sysd for st in s if st["fifths"]
    )
    n_clef = sum(
        1 for sysd in rows.values() for s in sysd for st in s if st["clef"]
    )
    print(f"rows                          : {len(rows)}")
    print(f"staves                        : {n_staves}")
    print(f"staves with key_signature_read: {n_read}  ({n_read/n_staves:.3f})")
    print(f"staves with nonzero signature : {n_nonzero}  ({n_nonzero/n_staves:.3f})")
    print(f"staves with a clef read       : {n_clef}  ({n_clef/n_staves:.3f})")
    assert len(rows) == 20, len(rows)
    assert n_read > 0, "key-signature coverage is zero -- the earlier vacuous read"
    assert n_nonzero > 0

    # ------------------------------------------------- per-system layout fit
    print("\n=== LAYOUT FIT PER SYSTEM (score_layouts.fit_layouts, 10 std orders) ===")
    fits = {}
    fit_ok = 0
    n_sys = 0
    for row in sorted(rows):
        for i, staves in enumerate(rows[row]):
            n_sys += 1
            labs = labels.get(row, {}).get(i, {})
            clefs = {j: st["clef"] for j, st in enumerate(staves) if st["clef"]}
            fit = sl.fit_layouts(len(staves), labels=labs or None, clefs=clefs or None)
            fits[(row, i)] = fit
            if fit is not None:
                fit_ok += 1
                print(
                    f"  {row:38s} sys{i} n={len(staves):2d} -> {fit.layout.name:22s} "
                    f"score/staff={fit.score_per_staff:5.2f} "
                    f"named={sum(1 for a in fit.assignment if a)}/{len(staves)}"
                )
            else:
                print(f"  {row:38s} sys{i} n={len(staves):2d} -> NO FIT (abstained)")
    print(f"\nsystems with a layout fit: {fit_ok}/{n_sys}")

    # ---------------------------------------------- order-conditioned cells
    # A cell is (system, position).  It is USABLE for the transposition source
    # only when the page read a key signature there AND the layout fit offers a
    # candidate list there.  This is the coverage that decides whether the
    # source can speak at all.
    print("\n=== TRANSPOSITION SOURCE: COVERAGE OF THE ORDER-CONDITIONED CELL ===")
    cells = 0
    cells_ks = 0
    cells_ks_and_support = 0
    cells_offset_resolvable = 0
    for (row, i), fit in fits.items():
        staves = rows[row][i]
        for p, st in enumerate(staves):
            cells += 1
            if not st["ks_read"]:
                continue
            cells_ks += 1
            if fit is None or not fit.support or p >= len(fit.support):
                continue
            sup = [n for n in (fit.support[p] or {}) if n]
            if not sup:
                continue
            cells_ks_and_support += 1
            if any(offset_of(n) is not None for n in sup):
                cells_offset_resolvable += 1
    print(f"cells (system,position)                  : {cells}")
    print(f"  with a key signature READ              : {cells_ks}  ({cells_ks/cells:.3f})")
    print(f"  + a layout candidate list at that pos  : {cells_ks_and_support}"
          f"  ({cells_ks_and_support/cells:.3f})")
    print(f"  + at least one candidate with a known"
          f"\n    transposition                        : {cells_offset_resolvable}"
          f"  ({cells_offset_resolvable/cells:.3f})")

    # ------------------------------------------------------- the pair screen
    print("\n=== PAIR SCREEN on equal-count systems ===")
    verdict = {}
    detail = {}
    for row in sorted(rows):
        sysd = rows[row]
        counts = [len(s) for s in sysd]
        hits = {"R2_clef": [], "R3_raw": [], "R3p_ordered": []}
        cov = {"clef": 0, "ks": 0, "ordered": 0, "cells": 0}
        for a in range(len(sysd)):
            for b in range(a + 1, len(sysd)):
                if counts[a] != counts[b]:
                    continue
                A, B = sysd[a], sysd[b]
                fA, fB = fits[(row, a)], fits[(row, b)]
                # concert reference: the modal read signature of the system,
                # which on an orchestral page is what the non-transposing
                # majority prints.
                def concert(S):
                    vals = [x["fifths"] for x in S if x["ks_read"]]
                    return Counter(vals).most_common(1)[0][0] if vals else None

                cA, cB = concert(A), concert(B)
                for p in range(counts[a]):
                    cov["cells"] += 1
                    if A[p]["clef"] and B[p]["clef"]:
                        cov["clef"] += 1
                        if A[p]["clef"] != B[p]["clef"]:
                            hits["R2_clef"].append([p, A[p]["clef"], B[p]["clef"]])
                    if not (A[p]["ks_read"] and B[p]["ks_read"]):
                        continue
                    cov["ks"] += 1
                    if A[p]["fifths"] != B[p]["fifths"]:
                        hits["R3_raw"].append([p, A[p]["fifths"], B[p]["fifths"]])
                    # order-conditioned
                    if fA is None or fB is None or cA is None or cB is None:
                        continue
                    if p >= len(fA.support) or p >= len(fB.support):
                        continue
                    supA = [n for n in (fA.support[p] or {}) if n]
                    supB = [n for n in (fB.support[p] or {}) if n]
                    if not supA or not supB:
                        continue
                    offA = A[p]["fifths"] - cA
                    offB = B[p]["fifths"] - cB
                    CA = {n for n in supA if offset_of(n) == offA}
                    CB = {n for n in supB if offset_of(n) == offB}
                    if not CA or not CB:
                        continue
                    cov["ordered"] += 1
                    if not (CA & CB):
                        hits["R3p_ordered"].append(
                            [p, offA, sorted(CA), offB, sorted(CB)]
                        )
        verdict[row] = {k: bool(v) for k, v in hits.items()}
        detail[row] = {"counts": counts, "coverage": cov, **hits}
        if any(c for c in counts if counts.count(c) > 1):
            print(
                f"{row:38s} cells={cov['cells']:3d} covered(clef/ks/ordered)="
                f"{cov['clef']:3d}/{cov['ks']:3d}/{cov['ordered']:3d}  "
                f"R2={len(hits['R2_clef'])} R3raw={len(hits['R3_raw'])} "
                f"R3ord={len(hits['R3p_ordered'])}"
            )

    print("\n=== PRE-REGISTERED TEST, per source ===")
    for key, what in [
        ("R2_clef", "clef differs at a position"),
        ("R3_raw", "key signature differs (bare offset)"),
        ("R3p_ordered", "order-conditioned (offset x admissible set)"),
    ]:
        f = sorted(r for r in verdict if verdict[r][key])
        fire_ok = all(verdict[r][key] for r in MUST_FIRE)
        silent_ok = all(not verdict[r][key] for r in MUST_BE_SILENT)
        print(
            f"{key:12s} {what:42s} fires {len(f):2d}/20  "
            f"MUST-FIRE {'PASS' if fire_ok else 'FAIL'}  "
            f"MUST-SILENT {'PASS' if silent_ok else 'FAIL'}"
        )
        for r in f:
            tag = (
                "TRUE"
                if r in MUST_FIRE
                else ("FALSE-POS(prereg)" if r in MUST_BE_SILENT else "?")
            )
            print(f"        {r:38s} {tag}")

    out = Path(__file__).with_name("order-conditioned.json")
    out.write_text(
        json.dumps(
            {
                "coverage": {
                    "staves": n_staves,
                    "ks_read": n_read,
                    "ks_nonzero": n_nonzero,
                    "clef_read": n_clef,
                    "cells": cells,
                    "cells_ks": cells_ks,
                    "cells_ks_and_support": cells_ks_and_support,
                    "cells_offset_resolvable": cells_offset_resolvable,
                    "systems_with_layout_fit": fit_ok,
                    "systems": n_sys,
                },
                "layout_fits": {
                    f"{r}|sys{i}": (None if f is None else f.layout.name)
                    for (r, i), f in fits.items()
                },
                "verdict": verdict,
                "detail": detail,
                "labels_meta": meta,
            },
            indent=2,
        )
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
