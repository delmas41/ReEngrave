"""Where does the part-correspondence charge actually land? — read-only.

Asks ONE question of the stored scan transcriptions, per row:

    At the moment the exporter decides how many `<part>` elements to emit,
    is the answer it needs already on the record?

and one question of the comparison itself:

    Does the part list we emit have the same LENGTH, in the same ORDER, as
    the part list musicdiff will pair it against?

musicdiff pairs parts **by index**, with surplus parts assumed to be at the
END of the shorter score (`comparison.py:1596-1633`). So a length mismatch is
not merely N unpaired parts at the tail: every part after the first
condensation is paired with the wrong reference part, and the cost of that
lands in `entire measure` and `wrong note`, not only in `entire staff`.

Reads only committed artefacts. Runs no pipeline. Writes nothing but stdout
and, with --json, a report file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def _bench_root() -> Path:
    """`benchmarks/omr-scan-e2e-2026-09` — in THIS checkout or the main one.

    The fixtures are gitignored build products and live in the main checkout;
    a worktree has the harness and none of the artefacts. Same escape
    `tools.library.score_library.library_root()` makes, for the same reason.
    """
    here = REPO / "benchmarks/omr-scan-e2e-2026-09"
    if (here / "fixtures").is_dir():
        return here
    main = Path(os.environ.get(
        "REENGRAVE_MAIN", "/Users/seanjohnson/Desktop/ReEngrave"))
    return main / "benchmarks/omr-scan-e2e-2026-09"


BENCH = _bench_root()
FIXTURES = BENCH / "fixtures"
WORKS = BENCH / "works.json"


def _systems(result: dict) -> list[list[dict]]:
    return [s["staves"] for p in result.get("pages", [])
            for s in p.get("systems", []) if s.get("staves")]


def _default_parts(systems: list[list[dict]]) -> tuple[int, str]:
    """How many <part> elements `export.to_musicxml` emits today.

    Mirrors `export._stitch_slots` + the per-system fallback. Deliberately a
    RESTATEMENT rather than an import, so that a divergence between this probe
    and the exporter shows up as a disagreement rather than as agreement by
    construction. Verified against the exporter for the rows below.
    """
    if len(systems) == 1:
        return len(systems[0]), "per-system (one system: no join question)"
    sizes = {len(s) for s in systems}
    if len(sizes) == 1:
        return sizes.pop(), "ordinal join"
    return sum(len(s) for s in systems), "REFUSED -> per-system fragments"


def _slot_parts(systems: list[list[dict]]) -> tuple[int | None, str]:
    """What `_stitch_slots_by_slot` would emit, and why it abstains if it does."""
    if len(systems) < 2:
        return None, "not reached (fewer than 2 systems)"
    rows = []
    for staves in systems:
        row = [st.get("slot_index", -1) for st in staves]
        if any(v is None or v < 0 for v in row):
            return None, f"abstains: {sum(1 for v in row if v is None or v < 0)} staff/staves carry no slot"
        if len(set(row)) != len(row):
            return None, "abstains: a system repeats a slot"
        rows.append(row)
    return len({v for r in rows for v in r}, ), "slot join"


def _truth_parts(path: Path) -> int:
    root = ET.parse(path).getroot()
    return len(root.findall(".//part-list/score-part"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="restamp-composed",
                    help="fixture arm suffix (default: the current stamped arm)")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if not FIXTURES.is_dir():
        print(f"FATAL: no fixtures at {FIXTURES}", file=sys.stderr)
        return 2
    if not WORKS.is_file():
        print(f"FATAL: no works.json at {WORKS}", file=sys.stderr)
        return 2

    preds = sorted(FIXTURES.glob(f"*.{args.arm}.omr.json"))
    if not preds:
        print(f"FATAL: no stored transcriptions for arm {args.arm!r} in {FIXTURES}",
              file=sys.stderr)
        return 2

    hand = {}
    for row in json.load(WORKS.open())["rows"]:
        rid = row.get("row_id") or row.get("id")
        st = row.get("staves")
        if isinstance(st, list) and st and isinstance(st[0], dict):
            hand[rid] = st

    out = []
    for f in preds:
        rid = f.name.split(f".{args.arm}.")[0]
        result = json.load(f.open())
        systems = _systems(result)
        n_default, how = _default_parts(systems)
        n_slot, why = _slot_parts(systems)
        truth_file = f.parent / f"{rid}.truth.musicxml"
        n_truth = _truth_parts(truth_file) if truth_file.is_file() else None
        printed = len(hand[rid]) if rid in hand else None
        staves = [st for s in systems for st in s]
        out.append({
            "row": rid,
            "system_sizes": [len(s) for s in systems],
            "staves_detected": len(staves),
            "staves_printed_hand": printed,
            "parts_default": n_default,
            "join_rule": how,
            "parts_slot_join": n_slot,
            "slot_join_note": why,
            "staves_without_slot": sum(
                1 for st in staves if (st.get("slot_index") is None
                                       or st.get("slot_index", -1) < 0)),
            "staves_named": sum(1 for st in staves if st.get("instrument")),
            "truth_parts_raw": n_truth,
            "truth_parts_page_normalised": printed,
        })

    if not out:
        print("FATAL: probe produced no rows", file=sys.stderr)
        return 2

    w = max(len(r["row"]) for r in out)
    print(f"{'row':{w}s}  sizes            det  prn  parts  truth  norm  slot?")
    for r in out:
        print(f"{r['row']:{w}s}  {str(r['system_sizes']):16s} "
              f"{r['staves_detected']:3d}  {str(r['staves_printed_hand']):>3s}  "
              f"{r['parts_default']:5d}  {str(r['truth_parts_raw']):>5s}  "
              f"{str(r['truth_parts_page_normalised']):>4s}  "
              f"{r['slot_join_note']}")

    have = [r for r in out if r["staves_printed_hand"] is not None]
    print()
    print(f"rows with a hand-read staff map: {len(have)} of {len(out)}")
    print("  detected staff count == printed staff count : "
          f"{sum(1 for r in have if r['staves_detected'] == r['staves_printed_hand'] or (len(set(r['system_sizes'])) == 1 and r['system_sizes'][0] == r['staves_printed_hand']))}")
    print("  parts emitted == raw truth parts            : "
          f"{sum(1 for r in have if r['parts_default'] == r['truth_parts_raw'])}")
    print("  parts emitted == page-normalised truth parts: "
          f"{sum(1 for r in have if r['parts_default'] == r['truth_parts_page_normalised'])}")
    print("  staves carrying no slot_index (all rows)    : "
          f"{sum(r['staves_without_slot'] for r in out)} of "
          f"{sum(r['staves_detected'] for r in out)}")

    if args.json:
        args.json.write_text(json.dumps(out, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
