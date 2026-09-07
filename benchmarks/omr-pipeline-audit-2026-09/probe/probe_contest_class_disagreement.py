#!/usr/bin/env python3
"""Agent I, round 1 — what the cross-staff ownership decision never forms.

Read-only over the committed `OMR_CONTEST_DUMP` artefacts of the 20-row scan
gate (`benchmarks/omr-additive-vs-gated-2026-09/out/contests/`). Those dumps
are verdict-neutral instrumentation (`transcribe.py:2789`) and reproduced that
gate's recorded 4,521 contested pairs exactly.

Asks one question the dump can answer and no decision site forms:

    when two staves claim ONE piece of ink, how often do their two readings
    disagree about WHAT IT IS?

`_dedupe_cross_staff_detections` gates on `category` equality and never
compares `class`, so a `beam`-vs-`tie` pair or a `flag8thUp`-vs-`flag16thUp`
pair is deduplicated exactly like an agreeing one, and the fact that the two
readers contradicted each other is never recorded.

⚠️ SUBSTRATE: these are the same dumps the additive-vs-gated survey measured
its 0.617 ladder-agreement figure on. This is a different COLUMN of the same
table, not independent corroboration of that figure.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_contest_class_disagreement.py
"""
from __future__ import annotations
import collections, glob, json, statistics as s, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ── OMR_AUDIT_GUARD ─────────────────────────────────────────────────────────
# ⚠️ A probe that prints a clean all-zero table when it means "I looked in the
# wrong place" is this audit's own recurring failure — it produced the round-2
# N4 retraction. Inputs are resolved from THIS FILE's location (never the CWD),
# `OMR_FIXTURE_ROOT` names the checkout for anything gitignored, and a missing
# or empty input set is a NON-ZERO EXIT, never a result.
import os as _os

FIXTURE_ROOT = Path(_os.environ.get(
    "OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave"))


def _require(paths, what):
    """Abort with exit 2 unless every named input exists and the set is non-empty."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if not paths or missing:
        print(f"FATAL: {len(missing) or 'all'} {what} missing "
              f"(set OMR_FIXTURE_ROOT if these are gitignored inputs)",
              file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)
        raise SystemExit(2)
    return list(paths)
# ────────────────────────────────────────────────────────────────────────────
PAT = str(ROOT / "benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json")


def main() -> int:
    files = _require(sorted(glob.glob(PAT)), "contest dumps")
    tab, dis, pairs = collections.Counter(), collections.Counter(), collections.Counter()
    gaps = collections.defaultdict(lambda: {"agree": [], "disagree": []})
    pitch_same = pitch_diff = 0
    for f in files:
        for pg in json.load(open(f)).get("pages", []):
            for c in pg.get("contests", []):
                key = (c.get("category"), c.get("decided_by"))
                tab[key] += 1
                d = c.get("class_i") != c.get("class_j")
                if d:
                    dis[key] += 1
                    pairs[tuple(sorted((str(c.get("class_i")), str(c.get("class_j")))))] += 1
                a, b = c.get("conf_i"), c.get("conf_j")
                if a is not None and b is not None:
                    gaps[c.get("category")]["disagree" if d else "agree"].append(abs(a - b))
                pi, pj = c.get("pitch_i"), c.get("pitch_j")
                if pi and pj:
                    pitch_same += pi == pj
                    pitch_diff += pi != pj

    n, nd = sum(tab.values()), sum(dis.values())
    print(f"rows {len(files)}  contested pairs {n}  class-disagreeing {nd} = {nd/n:.4f}")
    print(f"\n{'category':16s}{'tier':10s}{'n':>6s}{'disagree':>10s}{'rate':>8s}")
    for k in sorted(tab, key=lambda k: -tab[k]):
        print(f"{str(k[0]):16s}{str(k[1]):10s}{tab[k]:6d}{dis[k]:10d}{dis[k]/tab[k]:8.3f}")
    print("\ntop disagreeing class pairs:")
    for k, v in pairs.most_common(12):
        print(f"   {k}  {v}")
    print(f"\ncontested NOTEHEADS whose two readings give the SAME pitch: "
          f"{pitch_same} / {pitch_same+pitch_diff}")
    print(f"\n{'category':14s}{'n_agree':>8s}{'med|dc|':>9s}{'n_dis':>7s}{'med|dc|':>9s}")
    for cat, v in sorted(gaps.items(), key=lambda kv: -(len(kv[1]['agree']) + len(kv[1]['disagree']))):
        A, D = v["agree"], v["disagree"]
        ma = f"{s.median(A):.3f}" if A else "  -  "
        md = f"{s.median(D):.3f}" if D else "  -  "
        print(f"{str(cat):14s}{len(A):8d}{ma:>9s}{len(D):7d}{md:>9s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
