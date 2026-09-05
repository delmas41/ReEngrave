"""Census of library pages whose PRINTED LINEUP CHANGES between systems.

A page can separate two competing structural designs only if the thing that
differs between its systems is the lineup itself.  This probe finds candidate
pages without spending one minute of human time and without reading any ground
truth.

## The three screens

1. **counts** — two systems on the page report a different staff count.
   Catches tacet suppression directly.
2. **clefs** — every system reports the SAME staff count, but the CLEF SEQUENCE
   differs.  This is the screen that matters: the highest-value known page
   (Beethoven 5 p.4, where system 1 prints no Timpani and system 2 re-condenses
   `Violoncello`+`Basso` into `Bassi`) has 11 staves in both systems and is
   completely invisible to screen 1.
3. **blocks** — the bracket-block shape differs between systems.  ⚠️ RANKING
   ONLY, NEVER TRUTH.  `system_grouping`'s block boundary recall is 0.523 and
   unevenly distributed; it reads two identical Brahms systems as
   `[0x5,1x3,2x6]` against `[0x9,1x5]`.  Recorded, never believed.

## Screen 2's own false-positive source

A differing clef sequence can mean a real lineup change **or a clef misread**.
End-to-end clef accuracy is ~92% and degraded scans fall back to a positional
default of treble.  So every screen-2 firing also records, per differing slot,
which `clef_source` each side had -- a difference where either side is
`positional_default` (or absent) is a WEAK firing and is tiered down.

## No ground truth is an input

`works.json`, the dossiers and the reference encodings are barred.  Nothing
here selects or ranks on them.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- constants

# A conductor's page whose widest system has this many staves cannot honestly
# also print a system of 1-3 staves: that is a phase-1 failure (the known Bach
# p1 shape), not a lineup change.
DOUBTFUL_WIDE_SYSTEM = 6
DOUBTFUL_NARROW_SYSTEM = 3

# Clef sources that mean "nobody read a clef here" -- a difference resting on
# one of these is not evidence of a lineup change.
WEAK_CLEF_SOURCES = {None, "", "positional_default", "default", "fallback"}


# ---------------------------------------------------------------- signatures


def system_signature(system: dict[str, Any]) -> dict[str, Any]:
    staves = system.get("staves") or []
    return {
        "n_staves": len(staves),
        "clefs": [s.get("clef") for s in staves],
        "clef_sources": [s.get("clef_source") for s in staves],
        "blocks": [s.get("group_index") for s in staves],
    }


def _blocks_shape(blocks: list[Any]) -> tuple | None:
    """`[0,0,0,1,1]` -> `((0,3),(1,2))`.  None when no block info was carried."""
    if not blocks or all(b is None for b in blocks):
        return None
    out: list[tuple] = []
    for b in blocks:
        if out and out[-1][0] == b:
            out[-1] = (b, out[-1][1] + 1)
        else:
            out.append((b, 1))
    return tuple(out)


def screen_page(page: dict[str, Any]) -> dict[str, Any]:
    """Run all three screens over one page dict from an omr.json result."""
    systems = [system_signature(s) for s in (page.get("systems") or [])]
    rec: dict[str, Any] = {
        "page_index": page.get("page_index"),
        "n_systems": len(systems),
        "staff_counts": [s["n_staves"] for s in systems],
        "clef_sequences": [s["clefs"] for s in systems],
        "screens": [],
        "abstain": None,
        "doubtful": False,
        "doubtful_reason": None,
        "screen2_slots": [],
        "screen2_weak_slots": [],
    }

    if len(systems) < 2:
        rec["abstain"] = "fewer than two systems -- nothing to compare"
        return rec

    counts = rec["staff_counts"]
    widest, narrowest = max(counts), min(counts)
    if widest >= DOUBTFUL_WIDE_SYSTEM and narrowest <= DOUBTFUL_NARROW_SYSTEM:
        rec["doubtful"] = True
        rec["doubtful_reason"] = (
            f"a system of {narrowest} staves beside one of {widest} -- "
            "phase 1 probably failed on this page"
        )

    # ---- screen 1: differing staff counts
    if len(set(counts)) > 1:
        rec["screens"].append("counts")

    # ---- screen 2: equal counts, differing clef sequence
    if len(set(counts)) == 1:
        seqs = [tuple(s["clefs"]) for s in systems]
        if len(set(seqs)) > 1:
            rec["screens"].append("clefs")
            n = counts[0]
            for i in range(n):
                vals = [s["clefs"][i] for s in systems]
                if len(set(vals)) == 1:
                    continue
                srcs = [s["clef_sources"][i] for s in systems]
                slot = {"slot": i, "clefs": vals, "clef_sources": srcs}
                rec["screen2_slots"].append(slot)
                if any(s in WEAK_CLEF_SOURCES for s in srcs):
                    rec["screen2_weak_slots"].append(slot)

    # ---- screen 3: differing bracket-block shape (RANKING ONLY)
    shapes = [_blocks_shape(s["blocks"]) for s in systems]
    if all(sh is not None for sh in shapes) and len(set(shapes)) > 1:
        rec["screens"].append("blocks")
    rec["block_shapes"] = [list(sh) if sh else None for sh in shapes]

    rec["tier"] = _tier(rec)
    return rec


def _tier(rec: dict[str, Any]) -> str:
    """Confidence tier.  Screen 3 never raises a tier on its own."""
    if rec["abstain"]:
        return "abstain"
    if rec["doubtful"]:
        return "doubtful"
    screens = rec["screens"]
    if "counts" in screens:
        return "A"  # a differing staff count is not a clef misread
    if "clefs" in screens:
        strong = [s for s in rec["screen2_slots"] if s not in rec["screen2_weak_slots"]]
        return "B" if strong else "C"
    if "blocks" in screens:
        return "D"  # screen 3 only -- noise-dominated, ranking bait
    return "none"


def screen_result(result: dict[str, Any], label: str) -> list[dict[str, Any]]:
    pages = result.get("pages") or []
    assert pages, f"{label}: transcription carries no pages"
    out = []
    for page in pages:
        rec = screen_page(page)
        rec["label"] = label
        out.append(rec)
    return out


# ---------------------------------------------------------------- validation

# Pre-registered BEFORE the screens were run.  `expect` is whether ANY screen
# that is allowed to count (1 or 2 -- never 3 alone) must fire.
VALIDATION: list[tuple[str, bool, str, str]] = [
    ("beethoven-sym5-mvt1-984073-p4", True, "clefs",
     "system 1 has no Timpani; system 2 condenses Vcl+Basso to Bassi -- counts EQUAL"),
    ("beethoven-sym5-mvt1-575951-p4", True, "clefs",
     "same page, the other Litolff scan (a RE-PRINT, not a replication)"),
    ("beethoven-sym5-mvt1-984073-p3", True, "counts", "genuine tacet suppression, 11 vs 8"),
    ("beethoven-sym5-mvt1-575951-p3", True, "counts", "same page, other scan"),
    ("brahms-sym1-mvt1-317803-p2", True, "counts", "system 2 suppresses the Trumpets, 14 vs 13"),
    ("brahms-sym1-mvt1-317803-p3", False, "", "identical lineups -- NOISE CONTROL (screen 3 fires and is wrong)"),
    ("brahms-sym1-mvt1-317803-p4", False, "", "identical lineups -- NOISE CONTROL"),
    ("beethoven-sym5-mvt1-984073-p2", False, "", "identical lineups"),
    ("beethoven-sym5-mvt1-575951-p2", False, "", "identical lineups"),
    ("dvorak-sym9-mvt1-405834-p7", False, "", "identical lineups"),
]


def run_validation(fixtures: Path) -> dict[str, Any]:
    files = sorted(fixtures.glob("*.reconciliation.omr.json"))
    assert files, f"no .reconciliation.omr.json under {fixtures} -- WRONG FIXTURE TREE"
    assert len(files) == 20, (
        f"expected the 20-row reconciliation gate, found {len(files)} files in "
        f"{fixtures} -- the main checkout's stale 11-row ..graft09 set has been "
        "mistaken for it three times"
    )

    per_row: dict[str, dict[str, Any]] = {}
    n_staves = 0
    for f in files:
        row = f.name.split(".")[0]
        result = json.loads(f.read_text())
        recs = screen_result(result, row)
        assert len(recs) == 1, f"{row}: expected one page, got {len(recs)}"
        rec = recs[0]
        n_staves += sum(rec["staff_counts"])
        per_row[row] = rec

    assert n_staves == 396, (
        f"the 20-row gate is 396 staves; this tree has {n_staves} -- wrong fixtures"
    )

    table = []
    passed = 0
    for row, expect, why_screen, why in VALIDATION:
        assert row in per_row, f"validation row {row} absent from {fixtures}"
        rec = per_row[row]
        fired = [s for s in rec["screens"] if s in ("counts", "clefs")]
        ok = bool(fired) == expect
        if expect and why_screen:
            ok = ok and why_screen in fired
        passed += ok
        table.append({
            "row": row,
            "expect_fire": expect,
            "expect_screen": why_screen or None,
            "why": why,
            "fired": fired,
            "screen3_also": "blocks" in rec["screens"],
            "staff_counts": rec["staff_counts"],
            "tier": rec["tier"],
            "screen2_slots": rec["screen2_slots"],
            "pass": ok,
        })

    return {
        "fixtures": str(fixtures),
        "n_files": len(files),
        "n_staves": n_staves,
        "n_passed": passed,
        "n_rows": len(VALIDATION),
        "table": table,
        "all_rows": per_row,
    }


# ---------------------------------------------------------------- entry point


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument(
        "--fixtures",
        default="/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
        "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures",
    )
    ap.add_argument("--omr-json", nargs="*", default=[],
                    help="score arbitrary transcription JSON files")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    payload: dict[str, Any] = {}
    if args.validate:
        payload["validation"] = run_validation(Path(args.fixtures))
        v = payload["validation"]
        print(f"validation: {v['n_passed']}/{v['n_rows']} rows pass "
              f"({v['n_files']} files, {v['n_staves']} staves)")
        for r in v["table"]:
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"  {mark}  {r['row']:<34} expect="
                  f"{r['expect_screen'] or 'no fire':<7} fired={r['fired'] or '[]'} "
                  f"counts={r['staff_counts']} tier={r['tier']}"
                  + ("  [screen3 also fired]" if r["screen3_also"] else ""))

    if args.omr_json:
        recs = []
        for p in args.omr_json:
            recs += screen_result(json.loads(Path(p).read_text()), Path(p).stem)
        assert recs, "no pages screened"
        payload["pages"] = recs
        print(Counter(r["tier"] for r in recs))

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=1))
        print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
