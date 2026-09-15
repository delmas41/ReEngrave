"""REACH FIRST: how many staves read each proposed meter change, TRUE vs FALSE.

⚠️ **THIS IS THE INSTRUMENT THAT SIZES THE GUARD, AND IT PRINTS REACH BEFORE
ANYTHING ELSE.** A corroboration rule that reaches zero changes is a clean
no-op indistinguishable from a rule that works, so this exits **non-zero**
when it finds no change segments at all -- declaring itself DEAD rather than
reporting an empty table as a result.

WHAT IT READS
-------------
The COMMITTED reductions in `benchmarks/omr-staged-meter-boundary-2026-09/out/
*.meter.json` -- no weights, no library, no gather. Every `meter` verdict's
`value["segments"][1:]` is a proposed CHANGE (segment 0 is the system's
opening, which is not a change and has no `staves_reading_it`); a
`change_only` verdict's segments are ALL changes, which is
`report_boundary.tally`'s own rule, imported rather than restated.

⚠️ **TRUE / FALSE IS NOT ADJUDICATED HERE.** It comes from
`report_boundary.TRUTH_CHANGES`, the hand-read print truth committed by the
boundary session, keyed on `(fixture, page[, system])`. Re-deciding which
changes are real inside the probe that scores the guard is how a truth table
drifts toward its own data; the boundary session's own `--tally` is keyed the
same way and this reuses it.

⚠️ **DEDUPE IS LOAD-BEARING.** `out/` holds SEVEN run generations of the same
six fixtures (`m2`..`m7` plus the unprefixed first). Pooling them multiplies
every count by however many times a fixture was re-measured. The census keys on
`(fixture, page, system, from_cell, raw)` -- the fixture, never the run tag --
and reports how many generations it collapsed so the dedupe cannot be silent.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
ROOT = BENCH.parents[1]
BOUNDARY = ROOT / "benchmarks" / "omr-staged-meter-boundary-2026-09"


def _load_report_boundary():
    """Import the boundary session's own truth table and segment rule.

    ⚠️ By PATH, not by package: `benchmarks/` is not importable and the two
    dirs are siblings. Importing it is the point -- a copied truth table is a
    second copy of a fact this repo paid a human to read off a print.
    """
    spec = importlib.util.spec_from_file_location(
        "_report_boundary", BOUNDARY / "report_boundary.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_RB = _load_report_boundary()


def _tag_to_fixture(rb) -> dict:
    """Run tag stem -> `(fixture, label)`, from the boundary `TALLY_SET`.

    ⚠️ The run generation is a PREFIX (`m7full`) and the truth is keyed on the
    FIXTURE, which is exactly the distinction `report_boundary.tally --prefix`
    exists to preserve.
    """
    out = {}
    for name, fixture, label in rb.TALLY_SET:
        stem = name.split("-", 1)[0].lstrip("m0123456789")
        out[stem] = (fixture, label)
    return out


def _fixture_of(path: Path, table):
    """`out/m7brahms1scan-OFF.meter.json` -> the Brahms-scan fixture."""
    stem = path.name.split(".")[0].split("-", 1)[0].lstrip("m0123456789")
    for key in (stem, stem[:-3] if stem.endswith("fix") else stem):
        if key in table:
            return table[key]
    return None


def changes(record_path: Path):
    """Every proposed change segment of one run, as dicts.

    Mirrors `report_boundary.tally`'s segment rule exactly: a `change_only`
    verdict's segments are all changes; otherwise segment 0 is the opening.
    """
    for v in _RB.meters(record_path):
        parts = str(v["subject"]).split("/")
        page, system = int(parts[1]), int(parts[2])
        val = v.get("value") or {}
        segs = val.get("segments") or []
        segs = segs if v.get("reason") == "change_only" else segs[1:]
        for s in segs:
            yield {
                "page": page, "system": system,
                "from_cell": s.get("from_cell"),
                "raw": s.get("raw"),
                "support": s.get("support"),
                "staves": list(s.get("staves_reading_it") or []),
                "bars_fit": s.get("bars_fit"),
                "bars_contradict": s.get("bars_contradict"),
            }


def census(out_dir: Path):
    table = _tag_to_fixture(_RB)
    seen: dict = {}
    generations: dict = {}
    files = 0
    skipped = []
    for f in sorted(out_dir.glob("*.meter.json")):
        got = _fixture_of(f, table)
        if got is None:
            skipped.append(f.name)
            continue
        fixture, label = got
        files += 1
        for c in changes(f):
            key = (fixture, c["page"], c["system"], c["from_cell"], c["raw"])
            want = _RB.TRUTH_CHANGES.get(
                (fixture, c["page"], c["system"]),
                _RB.TRUTH_CHANGES.get((fixture, c["page"]), "?"))
            verdict = ("UNKNOWN" if want == "?" else
                       "TRUE" if want is not None
                       and (c["from_cell"], c["raw"]) == want else "FALSE")
            row = dict(c, fixture=fixture, label=label, verdict=verdict,
                       n_staves=len(c["staves"]))
            prev = seen.get(key)
            if prev is None:
                seen[key] = row
            elif row["n_staves"] < prev["n_staves"]:
                # ⚠️ Two generations disagreeing about the same segment is a
                # real fact about detector jitter, not a fault here. Keep the
                # SMALLER -- it is the harder case for a corroboration rule,
                # so the guard is sized against the worst reading available.
                seen[key] = row
            generations.setdefault(key, set()).add(f.name.split(".")[0])
    for key, row in seen.items():
        row["generations"] = len(generations[key])
    return list(seen.values()), files, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(BOUNDARY / "out"))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    rows, files, skipped = census(Path(a.out_dir))

    print("=" * 76)
    print("REACH -- proposed meter changes on the committed boundary records")
    print("=" * 76)
    print(f"  records read           : {files}"
          + (f"   ({len(skipped)} unmapped, skipped)" if skipped else ""))
    print(f"  DISTINCT change segments (fixture, page, system, cell, raw): "
          f"{len(rows)}")
    if not rows:
        print("\n  INSTRUMENT DEAD: no change segments found. A guard measured "
              "here would\n  report a clean zero that means NOTHING. "
              "Exiting non-zero.")
        return 2
    gens = sum(r["generations"] for r in rows)
    print(f"  run-generation copies collapsed by dedupe: {gens} -> {len(rows)}")
    print()

    order = {"TRUE": 0, "FALSE": 1, "UNKNOWN": 2}
    rows.sort(key=lambda r: (order[r["verdict"]], -r["n_staves"], r["fixture"]))
    print(f"{'verdict':8s} {'staves':>6} {'support':>8} {'fit':>4} {'cont':>5}"
          f"  {'raw':6s} {'cell':>4}  fixture / page / system")
    print("-" * 76)
    for r in rows:
        print(f"{r['verdict']:8s} {r['n_staves']:>6} {str(r['support']):>8} "
              f"{str(r['bars_fit']):>4} {str(r['bars_contradict']):>5}  "
              f"{str(r['raw']):6s} {str(r['from_cell']):>4}  "
              f"{r['fixture']} p{r['page']} s{r['system']}")

    print()
    for verdict in ("TRUE", "FALSE", "UNKNOWN"):
        sel = sorted(r["n_staves"] for r in rows if r["verdict"] == verdict)
        if sel:
            print(f"  {verdict:8s} n={len(sel):<3} staves_reading_it = {sel}")
    t = sorted(r["n_staves"] for r in rows if r["verdict"] == "TRUE")
    f_ = sorted(r["n_staves"] for r in rows if r["verdict"] == "FALSE")
    if t and f_:
        overlap = max(f_) >= min(t)
        print(f"\n  widest empty interval between the populations: "
              f"{max(f_)} .. {min(t)}"
              + ("   THEY OVERLAP -- no threshold separates them"
                 if overlap else ""))
        print("  ⚠️ An empty interval on n=1 document supports EVERY value "
              "inside it equally.\n     The rule below takes the WEAKEST "
              "(>= 2), not a value fitted to this gap.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")
        print(f"\n  wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
