"""Which axis the scan `entire staff` deficit actually lies on.

Addendum 3 of the vs-industry findings split the 10 scored scan rows by PAGE
POSITION — five first pages (bucket identical, 2,676 both) against five added
p2/p3 pages (ours 5,491, its 2,900). This re-cuts the same numbers by the
structural property the exporter actually branches on: HOW MANY SYSTEMS the
page holds. `export._stitch_slots` takes a different path for one system, for
several systems that agree on staff count, and for several that do not.

Reads the committed baselines only. Writes nothing but stdout / --json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ES = "entire staff insert/delete"
EM = "entire measure insert/delete"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ownership", required=True,
                    help="ownership.json from probe_staff_ownership.py")
    ap.add_argument("--audiveris", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    own = {r["row"]: r for r in json.loads(Path(args.ownership).read_text())
           if "error" not in r}
    audi = json.loads(Path(args.audiveris).read_text())

    # Bach is not in the Audiveris arm at all (its 5.11 dies with an internal
    # NPE on that page), so it is excluded from every comparison here rather
    # than being silently scored as zero.
    scored = [r for r in own.values() if r["row"] in audi]
    print(f"comparable rows: {len(scored)} (Bach excluded — Audiveris cannot "
          f"process it)\n")

    hdr = (f"{'row':<34} {'shape':<12} {'ES ours':>7} {'ES aud':>7} {'ΔES':>6} "
           f"{'EM ours':>7} {'EM aud':>7} {'ΔEM':>6} {'Δstruct':>8}")
    print(hdr)
    print("-" * len(hdr))

    def shape(r: dict) -> str:
        n = r["n_systems"]
        if n == 1:
            return "1 system"
        return f"{n} systems"

    groups: dict[str, list] = {}
    for r in sorted(scored, key=lambda r: (r["n_systems"], r["row"])):
        a = audi[r["row"]]
        des = r[ES.replace(" ", "_") if False else "entire_staff_ours"] - a.get(ES, 0)
        dem = r["entire_measure_ours"] - a.get(EM, 0)
        print(f"{r['row']:<34} {shape(r):<12} "
              f"{r['entire_staff_ours']:>7} {a.get(ES,0):>7} {des:>+6} "
              f"{r['entire_measure_ours']:>7} {a.get(EM,0):>7} {dem:>+6} "
              f"{des+dem:>+8}")
        groups.setdefault(shape(r), []).append((r, a))

    print("\nby page shape:")
    print(f"  {'shape':<12} {'rows':>4} {'ES ours':>8} {'ES aud':>8} {'ΔES':>7} "
          f"{'EM ours':>8} {'EM aud':>8} {'ΔEM':>7}")
    out = {}
    for sh, rs in sorted(groups.items()):
        eo = sum(r["entire_staff_ours"] for r, _ in rs)
        ea = sum(a.get(ES, 0) for _, a in rs)
        mo = sum(r["entire_measure_ours"] for r, _ in rs)
        ma = sum(a.get(EM, 0) for _, a in rs)
        print(f"  {sh:<12} {len(rs):>4} {eo:>8} {ea:>8} {eo-ea:>+7} "
              f"{mo:>8} {ma:>8} {mo-ma:>+7}")
        out[sh] = {"rows": len(rs), "es_ours": eo, "es_audiveris": ea,
                   "em_ours": mo, "em_audiveris": ma}

    print("\nfor contrast, the same rows cut by PAGE POSITION (Addendum 3's axis):")
    print(f"  {'slice':<12} {'rows':>4} {'ES ours':>8} {'ES aud':>8} {'ΔES':>7}")
    for label, sel in (("first page", False), ("later page", True)):
        rs = [(r, audi[r["row"]]) for r in scored if r["second_page"] is sel]
        eo = sum(r["entire_staff_ours"] for r, _ in rs)
        ea = sum(a.get(ES, 0) for _, a in rs)
        print(f"  {label:<12} {len(rs):>4} {eo:>8} {ea:>8} {eo-ea:>+7}")
        out[label] = {"rows": len(rs), "es_ours": eo, "es_audiveris": ea}

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
