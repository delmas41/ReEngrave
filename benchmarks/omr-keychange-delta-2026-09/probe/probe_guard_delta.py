"""STEP 2 — what would a DELTA condition do to the shipped guard?

`key_signature_corroboration.drop_uncorroborated_key_changes` keeps a
mid-staff key change where `>= MIN_WITNESSES` staves of the same system change
at the same MEASURE INDEX. Sean's observation says the VALUE is corroborable
too: every staff's written key moves by the same delta. So the candidate
second condition is *same bar AND same delta*.

This replays both rules over the stored transcriptions — no detector, no
weights, seconds — and reports what each would keep and revert. It reads the
same fixtures `probe_key_signature_flips.py` reads and fails loud on an empty
set.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_AUDIT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))),
    "omr-pipeline-audit-2026-09", "probe")
sys.path.insert(0, _AUDIT)
from _fixtures import fixtures, SCAN, ENGRAVED     # noqa: E402  fail-loud

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def fifths(key):
    """A key summary's position on the circle of fifths, or None.

    The pipeline stores `sharps` and `flats` separately; a signature is one or
    the other, never both, so the signed count IS the fifths.
    """
    if not key:
        return None
    s, f = key.get("sharps"), key.get("flats")
    if s is None and f is None:
        return None
    if (s or 0) and (f or 0):
        return None            # mixed — not a circle-of-fifths signature
    return (s or 0) - (f or 0)


def changes_in_staff(staff):
    out = []
    prev = None
    for i, m in enumerate(staff.get("measures", [])):
        cur = m.get("key_signature")
        idx = m.get("measure_index", i)
        cf, pf = fifths(cur), fifths(prev)
        if cur is not None and prev is not None:
            same = ((cur.get("sharps"), cur.get("flats"))
                    == (prev.get("sharps"), prev.get("flats")))
            if not same:
                out.append({"ordinal": i, "measure_index": idx,
                            "before": pf, "after": cf,
                            "delta": None if cf is None or pf is None
                            else cf - pf})
        if cur is not None:
            prev = cur
    return out


def main() -> int:
    rows = []
    for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                       ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
        for f in files:
            d = json.load(open(f))
            name = os.path.basename(f).split(".")[0]
            for pi, pg in enumerate(d["pages"]):
                for si, sy in enumerate(pg["systems"]):
                    staves = sy.get("staves", [])
                    per = {j: changes_in_staff(st)
                           for j, st in enumerate(staves)}
                    bar_n: Counter = Counter()
                    bar_delta: dict[int, Counter] = defaultdict(Counter)
                    for ch in per.values():
                        for c in ch:
                            bar_n[c["measure_index"]] += 1
                            bar_delta[c["measure_index"]][c["delta"]] += 1
                    for j, ch in per.items():
                        for c in ch:
                            mi = c["measure_index"]
                            rows.append({
                                "family": fam, "work": name, "page": pi,
                                "system": si,
                                "staff_index": staves[j].get("staff_index"),
                                "instrument": staves[j].get("instrument"),
                                "measure_index": mi,
                                "before": c["before"], "after": c["after"],
                                "delta": c["delta"],
                                "n_staves": len(staves),
                                "witnesses_same_bar": bar_n[mi],
                                "witnesses_same_bar_and_delta":
                                    bar_delta[mi][c["delta"]],
                            })

    if not rows:
        sys.stderr.write("FATAL: no mid-staff key changes found in any "
                         "fixture — refusing to report a clean zero.\n")
        return 2

    print("=" * 72)
    print(f"mid-staff key changes in the stored transcriptions: {len(rows)}")
    for fam in ("scan", "engraved"):
        sub = [r for r in rows if r["family"] == fam]
        print(f"  {fam}: {len(sub)}")
    print()
    print("--- each change, with both witness counts")
    print(f"  {'work':34s} {'staff':>5s} {'bar':>4s} {'Δ':>4s} "
          f"{'W2(bar)':>8s} {'W2+Δ':>6s}  instrument")
    for r in rows:
        print(f"  {r['work'][:34]:34s} {r['staff_index']:>5} "
              f"{r['measure_index']:>4} {str(r['delta']):>4s} "
              f"{r['witnesses_same_bar']:>8} "
              f"{r['witnesses_same_bar_and_delta']:>6}  {r['instrument']}")
    print()
    kept_bar = [r for r in rows if r["witnesses_same_bar"] >= 2]
    kept_delta = [r for r in rows if r["witnesses_same_bar_and_delta"] >= 2]
    print(f"  KEPT by the shipped rule (>=2 same bar)      : {len(kept_bar)}")
    print(f"  KEPT by same bar AND same delta             : {len(kept_delta)}")
    print(f"  REVERTED by the shipped rule                : "
          f"{len(rows) - len(kept_bar)}")
    print(f"  REVERTED by same bar AND same delta         : "
          f"{len(rows) - len(kept_delta)}")
    print()
    print("  => the delta condition changes "
          f"{len(kept_bar) - len(kept_delta)} decision(s).")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "guard-delta.json"), "w") as fh:
        json.dump({"rows": rows,
                   "kept_same_bar": len(kept_bar),
                   "kept_same_bar_and_delta": len(kept_delta)}, fh, indent=1)
    print(f"\nwrote {OUT}/guard-delta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
