#!/usr/bin/env python3
"""Which prong admitted each barline, and what a connectivity filter would cull.

⚠️ **THE POINT OF THIS PROBE IS THAT IT RE-RUNS NOTHING.** An auditor measured
exactly this on 2026-09-06 by instrumenting `detect_barlines` in-process,
because the numbers existed only for the length of a run: `types.Barline`
carried the evidence and `transcribe` serialised no barline at all. Asking the
question therefore cost a full pipeline run, which is the exact cost recording
was meant to remove. This reads stored result JSON.

It answers, per page and per regime:

  * how many barlines were admitted on VOTES ALONE (`vote_open_score`,
    `vote_small_system`) versus with connectivity in the conjunction
    (`vote_and_connectivity`) versus by rescue (`connectivity_rescue`,
    `span_rescue_small_system`);
  * what a naive `connectivity >= 0.4` filter — the obvious "clean up the
    barlines" idea, and the threshold `detect_barlines` itself uses inside the
    regime where it is valid — would cull if applied across pages;
  * whether that differs between an engraved page and a scan.

⚠️ **READ THE REGIME BEFORE THE NUMBER.** `barlines_cross_gaps` False means
the page was read as an open score and connectivity gated nothing there; a
`connectivity` of 0.0 on such a row is not a measurement of a bad barline. The
table prints the regime in its own column for that reason.

    python3 probe_barline_prongs.py <arm-dir> [<arm-dir> ...]

Each arm dir holds `<name>.json` written by `run_arm.py`. Inputs are named on
the command line and every one is checked: a directory with no result JSON in
it is a NON-ZERO EXIT, not an empty table at exit 0.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path


def _load(path: Path) -> dict:
    """A result JSON, plain or gzipped.

    The committed arm artefacts are `.json.gz` — 110 KB against 1.6 MB, and
    the DECOMPRESSED bytes are the pipeline's own output unmodified, which a
    projection or a trimmed copy would not be. A probe that had to read a
    hand-reduced file would not be demonstrating that the record reaches disk.
    """
    if path.name.endswith(".gz"):
        return json.loads(gzip.decompress(path.read_bytes()).decode())
    return json.loads(path.read_text())

VOTES_ONLY = {"vote_open_score", "vote_small_system"}
RESCUE = {"connectivity_rescue", "span_rescue_small_system"}
CULL_AT = 0.4          # the threshold detect_barlines uses in prong A


def rows(doc: dict):
    for page in doc.get("pages", []):
        for sys_ in page.get("systems", []):
            for r in sys_.get("barlines", []):
                yield page.get("page_index"), sys_.get("system_index"), r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+")
    args = ap.parse_args()

    docs: list[tuple[str, dict]] = []
    for arm in args.arms:
        d = Path(arm)
        found = sorted([*d.glob("*.json"), *d.glob("*.json.gz")])
        if not found:
            print(f"REFUSING: no *.json / *.json.gz under {d} — a probe that "
                  f"globs nothing prints a clean zero and exits 0, which is the "
                  f"failure this guard exists to prevent.", file=sys.stderr)
            return 3
        for f in found:
            docs.append((f.name.split(".json")[0], _load(f)))

    total_rows = 0
    print(f"{'page':30} {'regime':10} {'n':>4} {'votes':>6} {'vote+conn':>10} "
          f"{'rescue':>7} {'conn range':>14} {'culled@0.4':>11}")
    print("-" * 100)
    grand = Counter()
    for name, doc in docs:
        rs = list(rows(doc))
        if not rs:
            print(f"{name:30} {'-':10} {0:>4}   (no barline record — pre-fix JSON?)")
            continue
        total_rows += len(rs)
        by_regime: dict[object, list] = {}
        for _p, _s, r in rs:
            by_regime.setdefault(r.get("barlines_cross_gaps"), []).append(r)
        for regime in sorted(by_regime, key=str):
            group = by_regime[regime]
            prongs = Counter(r.get("accept_prong") for r in group)
            votes = sum(v for k, v in prongs.items() if k in VOTES_ONLY)
            vandc = prongs.get("vote_and_connectivity", 0)
            resc = sum(v for k, v in prongs.items() if k in RESCUE)
            conns = [r["connectivity"] for r in group
                     if r.get("connectivity") is not None]
            crange = (f"{min(conns):.3f}-{max(conns):.3f}" if conns
                      else "not measured")
            culled = sum(1 for r in group
                         if r.get("connectivity") is not None
                         and r["connectivity"] < CULL_AT)
            label = {True: "cross-gap", False: "open-score",
                     None: "unrecorded"}[regime]
            print(f"{name:30} {label:10} {len(group):>4} {votes:>6} {vandc:>10} "
                  f"{resc:>7} {crange:>14} {culled:>7}/{len(group):<3}")
            grand[("n", label)] += len(group)
            grand[("culled", label)] += culled
            grand[("votes", label)] += votes

    if not total_rows:
        print("\nREFUSING: every input carried a barline record of zero rows.",
              file=sys.stderr)
        return 3

    print("\nFINDING")
    for label in ("cross-gap", "open-score"):
        n = grand[("n", label)]
        if not n:
            continue
        print(f"  {label:11} n={n:<4} admitted on votes alone "
              f"{grand[('votes', label)]:<4} "
              f"a naive connectivity>={CULL_AT} filter would cull "
              f"{grand[('culled', label)]} of {n}")
    print("\n  ⚠️ The cull column is what makes the two regimes incomparable. "
          "In the\n     open-score regime connectivity gated NOTHING — the "
          "votes were the whole\n     of the evidence — so a number read out "
          "of it is not a measurement of\n     barline quality. Read "
          "`barlines_cross_gaps` first, always.")

    # ── Second table: the cell pad, same question, other record ────────────
    #
    # Folded in here rather than given its own file because it answers the
    # SAME question — can this be asked from disk — and because it is a
    # CROSS-CHECK rather than a new measurement: `types.MeasureCell`'s
    # docstring states these two distributions, taken in-process on
    # 2026-09-06. If the numbers below disagree with it, one of the two is
    # wrong and that is the finding.
    print("\nPAD PER CELL, PER SIDE  (above, below) -> n cells")
    pad_refusals = 0
    pad_ok = 0
    for name, doc in docs:
        cells = Counter(
            (m.get("pad_above_staff_lines"), m.get("pad_below_staff_lines"))
            for page in doc.get("pages", [])
            for sys_ in page.get("systems", [])
            for staff in sys_.get("staves", [])
            for m in staff.get("measures", []))
        # ⚠️ THE EMPTY-COUNTER HOLE, found in review. A document with systems
        # and ZERO cells yields `Counter()`, whose key set is `set()` — which
        # is not `{(None, None)}`, so it slipped past the pre-fix check below
        # and printed a confident `(n=0)` at exit 0. That is the exact shape
        # the barline half refuses and that this file's own docstring warns
        # about one table up: a probe reporting nothing, cleanly.
        if not cells:
            print(f"  {name:30} REFUSING — no measure cells at all", flush=True)
            print(f"REFUSING: {name} carries no measure cell, so its pad table "
                  f"would be a confident zero.", file=sys.stderr)
            pad_refusals += 1
            continue
        if set(cells) == {(None, None)}:
            print(f"  {name:30} REFUSING — no pad record (pre-fix JSON)")
            print(f"REFUSING: {name} carries no pad record.", file=sys.stderr)
            pad_refusals += 1
            continue
        shown = "  ".join(f"{k}x{v}" for k, v in sorted(cells.items(), key=str))
        print(f"  {name:30} {shown}   (n={sum(cells.values())})")
        pad_ok += 1
    print("  ⚠️ A cell grown to the ceiling on BOTH sides records (6.0, 6.0) "
          "under either\n     padding mode, so those rows are true and "
          "UNDECIDABLE about which cutter\n     ran. That is why "
          "`annotate/recut_cells` still derives the mode by re-cutting.")
    if pad_refusals or not pad_ok:
        print(f"\nREFUSING: {pad_refusals} document(s) could not supply a pad "
              f"table, {pad_ok} could.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
