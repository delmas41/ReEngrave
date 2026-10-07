"""ROADMAP 2.58 A/B: GATHER order (286289dd^ vs 286289dd), GATHER+ADJUDICATE only.

    python3 benchmarks/gather-order-ab-2026-10/ab_compare.py OUTDIR

Reads OUTDIR/<tag>.<arm>.json records (written by run.sh next to it) and
prints, per tag: (1) raw row-count deltas by (kind, quantity, reader/outcome,
reason) for base-vs-base (the A/A noise) and base-vs-arm, listing every cell
that moves beyond noise; (2) `readout diff` population counts; (3) bars with
a rest-search row; (4) wall times.

Counts only. Nothing here decides who is right -- the sheet does that.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from tools.omr.staged import readout as RD
from tools.omr.staged.record import Q


def counts(run):
    c = collections.Counter()
    for o in run.observations:
        v = o.get("value")
        extra = ""
        if o["quantity"] == Q.EMPTY_BAR_REST_SEARCH:
            extra = f"found={v.get('found') if isinstance(v, dict) else v}"
        c[("obs", o["quantity"], o.get("reader"), extra)] += 1
    for a in run.abstentions:
        c[("abst", a["quantity"], a.get("reader"), a.get("reason"))] += 1
    for v in run.verdicts:
        c[("verdict", v["quantity"], v["outcome"], v.get("reason"))] += 1
    return c


def delta(a, b):
    keys = set(a) | set(b)
    return {k: b[k] - a[k] for k in keys if a[k] != b[k]}


def rest_rows(run):
    out = {}
    for o in run.observations:
        if o["quantity"] == Q.EMPTY_BAR_REST_SEARCH:
            out.setdefault(o["subject"], []).append(o.get("value"))
    return out


def census(run):
    """Headline quantities of one record (counts only): what a stage summary would print, flattened."""
    c = collections.Counter()
    for g in run.glyphs.values():
        c["glyph boxes gathered"] += 1
        c[f"  family {g.family or 'class:' + str(g.cls)}"] += 1
    for o in run.observations:
        if o["quantity"] == Q.EMPTY_BAR_REST_SEARCH:
            v = o.get("value")
            found = bool(v.get("found")) if isinstance(v, dict) else bool(v)
            c["rest-search rows: found" if found else "rest-search rows: not found"] += 1
    for v in run.verdicts:
        if v["decider"].startswith("adjudicate") or True:
            if v["quantity"] in (Q.EMPTY_BAR_WHOLE_REST, Q.DURATION, Q.GLYPH_OWNER, Q.METER, Q.CLEF, Q.KEY_SIGNATURE,
                                 Q.NOTEHEAD_IS_A_WHOLE_REST):
                c[f"verdict {v['quantity']}: {v['outcome']}"] += 1
    return c


def main(out):
    out = Path(out)
    tags = sorted({p.name.split(".")[0] for p in out.glob("*.base.json")})
    print("WALL TIMES (s):")
    print((out / "times.txt").read_text() if (out / "times.txt").exists() else "(none)")
    aa = {}
    if (out / "lit6.base.json").exists() and (out / "lit6B.base.json").exists():
        a = RD.load_run(str(out / "lit6.base.json"))
        b = RD.load_run(str(out / "lit6B.base.json"))
        aa = delta(counts(a), counts(b))
        print("\n=== A/A (base twice, Litolff p6): row-count cells that differ:", len(aa))
        for k, d in sorted(aa.items(), key=lambda kv: -abs(kv[1]))[:30]:
            print(f"   {d:+d}  {k}")
        print("   readout diff n_differences:", RD.diff_runs(a, b)["n_differences"])
    for tag in tags:
        if tag.endswith("B") or not (out / f"{tag}.arm.json").exists():
            continue
        base = RD.load_run(str(out / f"{tag}.base.json"))
        arm = RD.load_run(str(out / f"{tag}.arm.json"))
        d = delta(counts(base), counts(arm))
        print(f"\n=== {tag}: ARM vs BASE row-count cells that differ: {len(d)}")
        for k, v in sorted(d.items(), key=lambda kv: -abs(kv[1])):
            note = f"   [A/A {aa[k]:+d}]" if k in aa else ""
            print(f"   {v:+d}  {k}{note}")
        cb, ca = census(base), census(arm)
        print("   census (base -> arm):")
        for k in sorted(set(cb) | set(ca)):
            print(f"      {k}: {cb[k]} -> {ca[k]}" + ("   <-- CHANGED" if cb[k] != ca[k] else ""))
        diff = RD.diff_runs(base, arm)
        print("   readout diff n_differences:", diff["n_differences"])
        for f, s in diff["families"].items():
            ch_a = {q: r["changed"] for q, r in s["adjudicate"].items() if r["changed"]}
            ch_g = {q: r["changed"] for q, r in s["gather"].items() if r["changed"]}
            if s["only_a"] or s["only_b"] or ch_a or ch_g:
                print(f"   family {f}: gathered {s['gathered_a']}->{s['gathered_b']}, "
                      f"only_base {s['only_a']}, only_arm {s['only_b']}, adj {ch_a}, gather {ch_g}")
        print("   structure changed:",
              {q: r["changed"] for q, r in diff["structure"].items() if r["changed"]})
        rb, ra = rest_rows(base), rest_rows(arm)
        new = [k for k in ra if k not in rb]
        print(f"   bars with a rest-search row: base {len(rb)}, arm {len(ra)}; only in arm {len(new)}")
        (out / f"{tag}.diff.json").write_text(json.dumps(
            {"counts": {str(k): v for k, v in d.items()},
             "changed_pairs": diff["changed_pairs"],
             "structure": diff["structure"], "rest_new": new},
            default=str, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
