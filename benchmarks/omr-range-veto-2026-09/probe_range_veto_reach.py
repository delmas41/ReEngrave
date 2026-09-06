"""How many contested glyphs would a roster-fed range veto actually speak on?

Reads the `.omr.json` files a `OMR_CONTEST_DUMP=1` scan_eval run wrote, joins
each contested pair to the instrument identity the contextual pass later wrote
onto the staff dicts, and asks the veto's own question of it.

    python3 benchmarks/omr-range-veto-2026-09/probe_range_veto_reach.py \
        --fixtures benchmarks/omr-scan-e2e-2026-09/fixtures --tag .contest

⚠️ REACH, NOT QUALITY. This says how many pairs the tier could speak on at all —
it does not say whether it would be right. That is the ordering the structural-
parts negative earned: a mechanism for a population that does not exist is worth
nothing however good its logic.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.instruments import lookup as lookup_instrument  # noqa: E402
from tools.omr.transcribe import _in_written_range  # noqa: E402


def identity_by_staff(page: dict) -> dict[int, dict]:
    """staff_index -> the identity the contextual pass wrote, if any."""
    out: dict[int, dict] = {}
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            idx = staff.get("staff_index")
            if idx is None or not staff.get("instrument"):
                continue
            out[idx] = {
                "instrument": staff["instrument"],
                "source": staff.get("instrument_source"),
                "family": staff.get("instrument_family"),
            }
    return out


def written_range(name: str) -> tuple[int, int] | None:
    match = lookup_instrument(name)
    rng = getattr(getattr(match, "instrument", None), "written_range", None)
    return tuple(rng) if rng else None


def analyse(path: Path) -> dict:
    doc = json.loads(path.read_text())
    stats = Counter()
    by_prov = Counter()
    speaks: list[dict] = []
    for page in doc.get("pages", []):
        ids = identity_by_staff(page)
        for c in page.get("contested_notehead_pairs", []):
            stats["contests_all_categories"] += 1
            stats[f"cat_{c.get('category')}"] += 1
            if c.get("category") != "notehead":
                continue
            stats["notehead_contests"] += 1
            if not (c.get("pitch_i") and c.get("pitch_j")):
                stats["notehead_no_pitch_both_sides"] += 1
                continue
            stats["notehead_with_both_pitches"] += 1
            id_i, id_j = ids.get(c["staff_i"]), ids.get(c["staff_j"])
            if not (id_i or id_j):
                stats["no_identity_either_staff"] += 1
                continue
            stats["identity_on_at_least_one"] += 1
            if not (id_i and id_j):
                # The veto compares two readings; one-sided identity cannot
                # separate them, because "inside its own range" is undefined
                # for the unnamed side.
                stats["identity_one_sided_only"] += 1
                continue
            rng_i, rng_j = written_range(id_i["instrument"]), written_range(
                id_j["instrument"])
            fit_i = _in_written_range(c["pitch_i"], rng_i)
            fit_j = _in_written_range(c["pitch_j"], rng_j)
            if fit_i is None or fit_j is None:
                stats["range_unknown"] += 1
                continue
            if fit_i == fit_j:
                stats["range_does_not_separate"] += 1
                continue
            stats["VETO_SPEAKS"] += 1
            prov = tuple(sorted({id_i["source"], id_j["source"]}))
            by_prov["+".join(prov)] += 1
            loser_is_i = not fit_i
            veto_loser = c["staff_i"] if loser_is_i else c["staff_j"]
            speaks.append({
                "staff_i": c["staff_i"], "staff_j": c["staff_j"],
                "inst_i": id_i["instrument"], "inst_j": id_j["instrument"],
                "src_i": id_i["source"], "src_j": id_j["source"],
                "pitch_i": c["pitch_i"], "pitch_j": c["pitch_j"],
                "decided_by": c["decided_by"],
                "veto_would_drop_staff": veto_loser,
                "distance_dropped_staff": c["loser_staff"],
                "agrees_with_current": veto_loser == c["loser_staff"],
            })
    return {"stats": stats, "by_prov": by_prov, "speaks": speaks}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=Path,
                    default=ROOT / "benchmarks/omr-scan-e2e-2026-09/fixtures")
    ap.add_argument("--tag", default=".contest")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    files = sorted(args.fixtures.glob(f"*{args.tag}.omr.json"))
    if not files:
        raise SystemExit(f"no {args.tag}.omr.json under {args.fixtures}")

    total = Counter()
    total_prov = Counter()
    all_speaks: list[dict] = []
    per_row: dict[str, dict] = {}
    print(f"{'row':<44} {'nh':>5} {'pitched':>8} {'ident':>6} {'SPEAKS':>7}")
    for f in files:
        row = f.name.replace(f"{args.tag}.omr.json", "")
        r = analyse(f)
        s = r["stats"]
        total.update(s)
        total_prov.update(r["by_prov"])
        for sp in r["speaks"]:
            sp["row"] = row
        all_speaks.extend(r["speaks"])
        per_row[row] = dict(s)
        print(f"{row:<44} {s['notehead_contests']:>5} "
              f"{s['notehead_with_both_pitches']:>8} "
              f"{s['identity_on_at_least_one']:>6} {s['VETO_SPEAKS']:>7}")

    print("\n─── funnel, pooled over all rows ───")
    order = ["contests_all_categories", "notehead_contests",
             "notehead_no_pitch_both_sides", "notehead_with_both_pitches",
             "no_identity_either_staff", "identity_on_at_least_one",
             "identity_one_sided_only", "range_unknown",
             "range_does_not_separate", "VETO_SPEAKS"]
    for k in order:
        print(f"  {k:<34} {total[k]:>6}")
    print("\n  contests by category:")
    for k, v in sorted(total.items()):
        if k.startswith("cat_"):
            print(f"    {k[4:]:<30} {v:>6}")
    print("\n  VETO_SPEAKS by identity provenance:")
    for k, v in total_prov.most_common():
        print(f"    {k:<30} {v:>6}")
    rows_with = sum(1 for v in per_row.values() if v.get("VETO_SPEAKS"))
    print(f"\n  rows with any reach: {rows_with} of {len(files)}")

    if args.out:
        args.out.write_text(json.dumps(
            {"pooled": dict(total), "by_provenance": dict(total_prov),
             "per_row": per_row, "rows_with_reach": rows_with,
             "n_rows": len(files), "speaks": all_speaks}, indent=1) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
