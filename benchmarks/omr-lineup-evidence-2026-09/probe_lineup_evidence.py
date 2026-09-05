"""Do two equal-count systems on one page hold DIFFERENT instruments?

Sean's idea, tested 2026-09-05.  `export._stitch_slots` joins staves across
systems by ORDINAL, which is right on the overwhelming majority of pages and
silently wrong when a publisher drops one instrument and adds another while
keeping the staff count equal.  The worked case is the 1870 Litolff plate of
Beethoven 5 p.4, in two independent scans:

    system 1   ... Corni, Trombe | Violino I, Violino II, Viola, Violoncello, Basso   = 11
    system 2   ... Corni, Trombe, Timpani | Violino I, Violino II, Viola, Bassi       = 11

Equal counts, different lineup: position 6 is Violino I in one system and
Timpani in the other, and everything below shifts.

THE GAP THIS TESTS.  `slots._pair_score` scores a label match only when BOTH
sides are named:

    if label is not None and slot.instrument is not None:
        score += SCORE_LABEL_MATCH if label == slot.instrument else SCORE_LABEL_CONFLICT

so an ABSENT label contributes exactly zero -- "a staff that prints nothing is
silent, not contradictory".  Sean's proposal: an absence WHERE THE PUBLISHER'S
CONVENTION EXPECTS A LABEL is itself evidence.  Litolff labels winds and brass
on every system and strings never
(benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md), so timpani is in
the labelled class and "labelled here, absent there" is a real conflict.

-------------------------------------------------------------------------------
PRE-REGISTERED KILL CRITERIA -- written before the probe was first run.
-------------------------------------------------------------------------------
  MUST fire   on beethoven-sym5-mvt1-984073-p4 and beethoven-sym5-mvt1-575951-p4
  MUST be silent on brahms-sym1-mvt1-317803-p3 and brahms-sym1-mvt1-317803-p4
      (Breitkopf labels every staff, so no expected-absence exists there; these
       are the rows where the clef screen (precision 2/6), the bracket-shape
       detector (precision 0.500) and arm C all produced false positives)
  Every other firing row of the 20-row gate is a FALSE POSITIVE unless a real
      lineup change can be shown.

-------------------------------------------------------------------------------
INPUTS -- both asserted before any comparison is trusted.
-------------------------------------------------------------------------------
  structure : benchmarks/omr-scan-e2e-2026-09/fixtures/*.reconciliation.omr.json
              in the `reconciliation` WORKTREE.  The main checkout's fixtures/
              holds the stale 11-row `..graft09` set; this probe asserts the
              `.reconciliation.omr.json` suffix and asserts a count of 20 rows.
  labels    : benchmarks/omr-staff-identity-labels-2026-09/ladder.json from the
              labels workstream -- RAW per-(row, system, position) reader output
              plus the lexicon's answer.  `ladder_resolved` is the reader ladder's
              own verdict, BEFORE `contextual.resolve_ambiguous_label` and before
              any slot assignment: on the worked case it holds Timpani at
              (984073-p4, sys 1, pos 6) where the fixture's slot-assigned
              `instrument` says Trumpet.  The slot-assigned field is NEVER read
              -- it is assigned BY the join under test and using it would be
              circular, the fault that made "instrument sequence as a screen"
              blind on both p4 rows.

-------------------------------------------------------------------------------
THE RULES, scored separately so each source's contribution is visible.
-------------------------------------------------------------------------------
For every unordered pair of systems (A, B) on one page with EQUAL staff counts:

  R0  NAMED CONFLICT (the incumbent's reach): a position labelled in both, with
      different instruments.  Scored for reference -- `_pair_score` already sees
      this shape.

  R1  EXPECTED ABSENCE (Sean's proposal).  Let L_A be the positions of A that
      carry a resolved label.  A is in "prefix convention" when L_A is exactly
      {0 .. |L_A|-1} -- labels run contiguously from the top staff and stop,
      which is what a publisher that labels winds+brass and never strings
      produces, and is NOT what an edition labelling everything with scattered
      OCR misses produces.  Under prefix convention a position p >= |L_A| is
      BEYOND A's labelled region: A asserts that staff is not of a labelled
      family.  If B labels p, the two systems disagree about what sits there.
      FIRE.  Requires both systems in prefix convention (else abstain), and
      requires |L_A| != |L_B| (else there is nothing to disagree about).

  R2  CLEF.  Position p where the two systems read different clefs.  Reported
      raw and gated (see below).

  R3  KEY SIGNATURE.  Position p where the two systems read a different number
      of accidentals.  Known killed as an ABSOLUTE identity signal
      (benchmarks/omr-staff-identity-2026-09/FINDINGS.md: natural horns and
      trumpets print none, so it spoke on 2 of 36 brass staves).  Retested here
      only as a SAME-OR-DIFFERENT matcher, which is the weaker question --
      "a signal too weak to name a staff can be strong enough to match it".

Every rule reads only per-system evidence.  Nothing reads `staff["instrument"]`,
`slot_index`, or `instrument_source`.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

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


# ---------------------------------------------------------------- inputs

def load_structure():
    """Per row: [n_staves per system], plus per (system, position) clef/key.

    Asserts the `.reconciliation.omr.json` suffix -- the main checkout's
    fixtures/ holds a stale 11-row `..graft09` set and confusing the two has
    produced wrong numbers four times in two days.
    """
    paths = sorted(RECON.glob("*.reconciliation.omr.json"))
    assert paths, f"no .reconciliation.omr.json fixtures under {RECON}"
    out = {}
    for p in paths:
        assert p.name.endswith(".reconciliation.omr.json"), p
        row = p.name[: -len(".reconciliation.omr.json")]
        d = json.loads(p.read_text())
        systems = []
        for page in d["pages"]:
            for s in page["systems"]:
                staves = []
                for st in s["staves"]:
                    ks = st.get("key_signature")
                    if isinstance(ks, dict):
                        ks = ks.get("fifths")
                    staves.append(
                        {
                            "clef": st.get("clef"),
                            "clef_source": st.get("clef_source"),
                            "key": ks,
                        }
                    )
                systems.append(staves)
        out[row] = systems
    return out


def load_labels():
    """Per (row, system, position): the reader ladder's own resolved name."""
    d = json.loads(LADDER.read_text())
    rows = {}
    for r in d["rows"]:
        by_sys = defaultdict(dict)
        for st in r["staves"]:
            by_sys[st["system"]][st["position"]] = st.get("ladder_resolved")
        rows[r["row_id"]] = {
            "systems": dict(by_sys),
            "structure_here": r.get("structure_here"),
            "publisher": r.get("publisher"),
        }
    return d["meta"], rows


# ---------------------------------------------------------------- rules

def is_prefix(labelled, n):
    """True when the labelled positions run contiguously from the top and stop."""
    k = len(labelled)
    return k > 0 and k < n and labelled == set(range(k))


def screen_pair(labA, labB, stA, stB):
    """All four rules on one equal-count system pair.  Returns dict of hits."""
    n = len(stA)
    LA = {p for p, v in labA.items() if v}
    LB = {p for p, v in labB.items() if v}

    r0 = [
        (p, labA[p], labB[p])
        for p in sorted(LA & LB)
        if labA[p] != labB[p]
    ]

    r1 = []
    if is_prefix(LA, n) and is_prefix(LB, n) and len(LA) != len(LB):
        lo, hi = (LA, LB) if len(LA) < len(LB) else (LB, LA)
        lo_is_A = lo is LA
        for p in sorted(hi - lo):
            if p >= len(lo):
                name = (labB if lo_is_A else labA)[p]
                r1.append((p, name, "A" if lo_is_A else "B"))

    r2 = [
        (p, stA[p]["clef"], stB[p]["clef"])
        for p in range(n)
        if stA[p]["clef"] and stB[p]["clef"] and stA[p]["clef"] != stB[p]["clef"]
    ]
    r3 = [
        (p, stA[p]["key"], stB[p]["key"])
        for p in range(n)
        if stA[p]["key"] is not None
        and stB[p]["key"] is not None
        and stA[p]["key"] != stB[p]["key"]
    ]
    return {"R0": r0, "R1": r1, "R2": r2, "R3": r3}


# ---------------------------------------------------------------- main

def main():
    struct = load_structure()
    meta, labels = load_labels()

    # An audit that can return "nothing found" must first prove it looked at
    # something.  Assert both inputs before any comparison is trusted.
    print("=== INPUT ASSERTIONS ===")
    print(f"structure fixtures  : {len(struct)} rows from {RECON}")
    print(f"                      suffix .reconciliation.omr.json (asserted)")
    print(f"labels ladder.json  : {len(labels)} rows, meta={meta}")
    n_staves_struct = sum(len(s) for sys in struct.values() for s in sys)
    n_lab_records = sum(
        len(v) for r in labels.values() for v in r["systems"].values()
    )
    n_lab_resolved = sum(
        1
        for r in labels.values()
        for v in r["systems"].values()
        for x in v.values()
        if x
    )
    print(f"staves in structure : {n_staves_struct}")
    print(f"label records       : {n_lab_records}  (resolved: {n_lab_resolved})")
    assert len(struct) == 20, f"expected the 20-row gate, got {len(struct)}"
    assert len(labels) == 20, f"expected 20 label rows, got {len(labels)}"
    assert n_lab_resolved > 0
    common = set(struct) & set(labels)
    assert len(common) == 20, sorted(set(struct) ^ set(labels))
    print(f"rows in both        : {len(common)}")

    # Structure agreement between the two inputs.  ladder.json's staves were
    # re-detected on origin/main; the fixtures were stamped by the
    # reconciliation run.  Where they disagree the label positions do not
    # describe the fixture's staves and the row must ABSTAIN, not be guessed at.
    print("\n=== STRUCTURE AGREEMENT (fixture vs ladder re-detection) ===")
    usable = []
    for row in sorted(common):
        a = [len(s) for s in struct[row]]
        b = labels[row]["structure_here"]
        ok = a == b
        if ok:
            usable.append(row)
        print(f"{'ok ' if ok else 'MISMATCH'} {row:38s} fixture={a}  ladder={b}")
    print(f"\nusable rows: {len(usable)}/20")

    print("\n=== EQUAL-COUNT SYSTEM PAIRS ===")
    fired = {}
    per_row = {}
    for row in sorted(common):
        sysd = struct[row]
        counts = [len(s) for s in sysd]
        pairs = [
            (i, j)
            for i in range(len(sysd))
            for j in range(i + 1, len(sysd))
            if counts[i] == counts[j]
        ]
        abstain = row not in usable
        rec = {
            "counts": counts,
            "n_equal_pairs": len(pairs),
            "abstained_structure_mismatch": abstain,
            "pairs": [],
        }
        for (i, j) in pairs:
            labA = labels[row]["systems"].get(i, {})
            labB = labels[row]["systems"].get(j, {})
            if abstain:
                continue
            hits = screen_pair(labA, labB, sysd[i], sysd[j])
            LA = sorted(p for p, v in labA.items() if v)
            LB = sorted(p for p, v in labB.items() if v)
            rec["pairs"].append(
                {
                    "systems": [i, j],
                    "n": counts[i],
                    "labelled_A": LA,
                    "labelled_B": LB,
                    "prefix_A": is_prefix(set(LA), counts[i]),
                    "prefix_B": is_prefix(set(LB), counts[i]),
                    **hits,
                }
            )
        per_row[row] = rec
        r1 = [h for pr in rec["pairs"] for h in pr["R1"]]
        r0 = [h for pr in rec["pairs"] for h in pr["R0"]]
        r2 = [h for pr in rec["pairs"] for h in pr["R2"]]
        r3 = [h for pr in rec["pairs"] for h in pr["R3"]]
        fired[row] = {"R0": bool(r0), "R1": bool(r1), "R2": bool(r2), "R3": bool(r3)}
        flag = "ABSTAIN(structure)" if abstain else ""
        print(
            f"{row:38s} counts={str(counts):16s} equal-pairs={len(pairs)}  "
            f"R0={len(r0)} R1={len(r1)} R2={len(r2)} R3={len(r3)} {flag}"
        )

    print("\n=== PRE-REGISTERED VERDICT (R1, expected-absence, alone) ===")
    ok = True
    for row in sorted(MUST_FIRE):
        got = fired[row]["R1"]
        ok &= got
        print(f"MUST FIRE   {row:38s} -> {'FIRE  PASS' if got else 'silent  FAIL'}")
    for row in sorted(MUST_BE_SILENT):
        got = fired[row]["R1"]
        ok &= not got
        print(f"MUST SILENT {row:38s} -> {'silent  PASS' if not got else 'FIRE  FAIL'}")
    others = sorted(set(fired) - MUST_FIRE - MUST_BE_SILENT)
    fp = [r for r in others if fired[r]["R1"]]
    print(f"\nother rows firing R1 (candidate false positives): {len(fp)}/{len(others)}")
    for r in fp:
        print(f"   {r}")
    print(f"\nPRE-REGISTERED TEST: {'PASS' if ok else 'FAIL'}")

    print("\n=== PER-SOURCE FIRING over all 20 rows ===")
    for rule, what in [
        ("R0", "named conflict (incumbent's reach)"),
        ("R1", "expected absence (Sean)"),
        ("R2", "clef differs at a position"),
        ("R3", "key signature differs at a position"),
    ]:
        f = sorted(r for r in fired if fired[r][rule])
        print(f"{rule} {what:38s} fires on {len(f):2d}/20")
        for r in f:
            mark = (
                "TRUE"
                if r in MUST_FIRE
                else ("FALSE-POS(preregistered)" if r in MUST_BE_SILENT else "?")
            )
            print(f"      {r:38s} {mark}")

    out = Path(__file__).with_name("lineup-evidence.json")
    out.write_text(
        json.dumps(
            {
                "inputs": {
                    "structure_dir": str(RECON),
                    "structure_suffix": ".reconciliation.omr.json",
                    "n_structure_rows": len(struct),
                    "labels": str(LADDER),
                    "labels_meta": meta,
                    "n_label_records": n_lab_records,
                    "n_label_resolved": n_lab_resolved,
                },
                "usable_rows": usable,
                "fired": fired,
                "per_row": per_row,
                "preregistered": {
                    "must_fire": sorted(MUST_FIRE),
                    "must_be_silent": sorted(MUST_BE_SILENT),
                    "pass": bool(ok),
                },
            },
            indent=2,
        )
    )
    print(f"\nwrote {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
