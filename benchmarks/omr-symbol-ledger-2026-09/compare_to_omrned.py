"""Where the ledger and OMR-NED disagree about what KIND of error we have.

⚠️ **THIS IS NOT AN A/B AND THE TWO NUMBERS ARE NOT COMPARABLE AS TOTALS.**
An OMR-NED edit is an operation in an edit script; a ledger row is a printed
symbol. One symbol can cost six edits (measured — see `mutation_matrix.py`) and
one edit can stand for a whole bar. Anyone differencing 74,956 against 29,519
is comparing an edit count to a symbol count.

What IS comparable is the SHAPE of the attribution: given the same 20 pairs,
what does each instrument say the errors are ABOUT, and how much of each
instrument's mass is in a bucket that names nothing.

The musicdiff side is read from `benchmarks/omr-wrongnote-decomposition-
2026-09/arm-allobjects.csv` — committed data at the benchmark's own detail
level, not re-measured here, so this script cannot drift from the figure the
project already reports.

    python3 benchmarks/omr-symbol-ledger-2026-09/compare_to_omrned.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
MD_CSV = (ROOT / "benchmarks" / "omr-wrongnote-decomposition-2026-09"
          / "arm-allobjects.csv")

#: musicdiff buckets that name no specific symbol attribute — the ones that
#: say "these did not pair" rather than "this is wrong in this way".
UNNAMED = {"wrong note", "entire measure insert/delete",
           "entire staff insert/delete", "bad kern syntax"}


def musicdiff_by_row(path: Path) -> dict[str, dict[str, int]]:
    rows = list(csv.reader(path.open()))
    hdr = [h.strip() for h in rows[0]]
    cols = {h[: -len(" OMR-ED")]: i for i, h in enumerate(hdr)
            if h.endswith("OMR-ED")}
    out: dict[str, dict[str, int]] = {}
    for r in rows[1:]:
        if len(r) < 3 or not r[1].strip():
            continue
        name = Path(r[1].strip()).stem
        if name == "gtpath":
            continue
        d = {}
        for k, i in cols.items():
            v = r[i].strip()
            if v.lstrip("-").isdigit() and int(v):
                d[k] = int(v)
        out[name] = d
    return out


def ledger_by_row(csv_path: Path) -> tuple[dict[str, Counter], dict[str, Counter]]:
    outcomes: dict[str, Counter] = defaultdict(Counter)
    attrs: dict[str, Counter] = defaultdict(Counter)
    with csv_path.open() as fh:
        for r in csv.DictReader(fh):
            rid = r["row_id"]
            key = r["outcome"]
            if key == "uncorresponded":
                key = f"uncorresponded:{r['reason']}"
            outcomes[rid][key] += 1
            if r["attrs_wrong"]:
                for a in r["attrs_wrong"].split("+"):
                    tag = f"{r['family']}.{a}"
                    if r["basis_strength"] == "single_key":
                        tag += " (single-key)"
                    attrs[rid][tag] += 1
    return outcomes, attrs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger-csv", type=Path, default=BENCH / "out" / "ledger-rows.csv")
    ap.add_argument("--md-csv", type=Path, default=MD_CSV)
    ap.add_argument("--summary", type=Path, default=BENCH / "out" / "ledger-summary.json")
    ap.add_argument("--out", type=Path, default=BENCH / "out" / "comparison.json")
    a = ap.parse_args(argv)

    md = musicdiff_by_row(a.md_csv)
    outcomes, attrs = ledger_by_row(a.ledger_csv)
    joined_rows: set[str] = set()
    if a.summary.is_file():
        s = json.loads(a.summary.read_text())
        joined_rows = set(s.get("pooled", {}).get("join_resolved_rows", []))

    md_tot: Counter = Counter()
    for v in md.values():
        md_tot.update(v)
    led_tot: Counter = Counter()
    for v in outcomes.values():
        led_tot.update(v)
    attr_tot: Counter = Counter()
    for v in attrs.values():
        attr_tot.update(v)

    md_unnamed = sum(v for k, v in md_tot.items() if k in UNNAMED)
    md_all = sum(md_tot.values())
    led_unaccounted = sum(v for k, v in led_tot.items()
                          if k.startswith("uncorresponded") or k == "ambiguous")
    led_all = sum(led_tot.values())

    print("=" * 74)
    print("SHAPE OF THE ATTRIBUTION — the same 20 scan-gate pairs")
    print("=" * 74)
    print(f"\nmusicdiff (AllObjects): {md_all} edits")
    print(f"  in a bucket that names NO specific error   "
          f"{md_unnamed:>7}  {md_unnamed/md_all:6.1%}")
    print(f"  naming a specific symbol attribute         "
          f"{md_all - md_unnamed:>7}  {1 - md_unnamed/md_all:6.1%}")
    print(f"\nsymbol ledger: {led_all} symbol rows")
    print(f"  declared uncorresponded or ambiguous       "
          f"{led_unaccounted:>7}  {led_unaccounted/led_all:6.1%}")
    print(f"  corresponded and accounted for             "
          f"{led_all - led_unaccounted:>7}  {1 - led_unaccounted/led_all:6.1%}")
    print("\n  ⚠️ The two percentages LOOK alike and are not the same quantity. "
          "musicdiff's\n     unnamed mass is what it CHARGED without diagnosing; "
          "the ledger's is what it\n     DECLINED to charge because the "
          "correspondence was not established.")

    print("\n" + "-" * 74)
    print("WHAT EACH SAYS THE ERRORS ARE ABOUT")
    print("-" * 74)
    print("\nmusicdiff buckets")
    for k, v in md_tot.most_common(12):
        mark = "  ← names nothing" if k in UNNAMED else ""
        print(f"  {k:<36}{v:>7}{mark}")
    print("\nledger outcomes")
    for k, v in led_tot.most_common(12):
        print(f"  {k:<36}{v:>7}")
    print("\nledger named attribute errors")
    for k, v in attr_tot.most_common(16):
        print(f"  {k:<36}{v:>7}")

    print("\n" + "-" * 74)
    print("PER ROW — where the join resolved, and where it did not")
    print("-" * 74)
    print(f"{'row':<38}{'join':>6}{'md edits':>10}{'md unnamed':>12}"
          f"{'ledger rows':>13}{'uncorresp':>11}")
    for rid in sorted(outcomes):
        m = md.get(rid, {})
        me = sum(m.values())
        mu = sum(v for k, v in m.items() if k in UNNAMED)
        lt = sum(outcomes[rid].values())
        lu = sum(v for k, v in outcomes[rid].items()
                 if k.startswith("uncorresponded"))
        j = "yes" if rid in joined_rows else "NO"
        print(f"{rid:<38}{j:>6}{me:>10}{mu/me if me else 0:>11.0%}"
              f"{lt:>13}{lu/lt if lt else 0:>10.0%}")

    report = {
        "musicdiff_total_edits": md_all, "musicdiff_unnamed": md_unnamed,
        "musicdiff_buckets": dict(md_tot.most_common()),
        "ledger_total_rows": led_all, "ledger_unaccounted": led_unaccounted,
        "ledger_outcomes": dict(led_tot.most_common()),
        "ledger_named_attributes": dict(attr_tot.most_common()),
        "per_row": {rid: {"musicdiff": md.get(rid, {}),
                          "ledger": dict(outcomes[rid]),
                          "ledger_named": dict(attrs.get(rid, {})),
                          "part_join_resolved": rid in joined_rows}
                    for rid in sorted(outcomes)},
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
