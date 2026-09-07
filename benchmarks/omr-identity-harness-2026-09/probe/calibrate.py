#!/usr/bin/env python3
"""Can identity CALIBRATE now that the corpus exists?  MEASUREMENT ONLY.

    python3 probe/calibrate.py [--arm-beet5 ARM] [--arm-brahms ARM]

⚠️ THIS PROBE MAY NOT SHIP A PROBABILITY, and the standard it is held to was
pre-registered by `claude/staff-identity-layer-2026-09-05`:

    AN UNCALIBRATED PROBABILITY IS WORSE THAN NONE, because it launders a
    guess into something that reads as evidence.

That branch measured P(name) ECE 0.1277 and P(set) ECE 0.1301 at n=197 and
emitted nothing.  Its DIAGNOSIS was that the failure is the CORPUS, not the
estimator — specifically that the `derived` tier, the one whose calibration
would actually decide an admission, had **zero records**.  The corpus is now
8x larger.  This asks whether the diagnosis was right.

## The estimator is the earlier one, deliberately unchanged

Hierarchical empirical frequency with Laplace smoothing, cell -> tier ->
global, so every emitted number is auditable back to "staves that looked like
this were right N of M times".  Changing the estimator at the same time as the
corpus would make the answer unattributable.

## Held out by ENGRAVING, not by row

Two scans of one plate are ONE engraving.  Here there are two engravings
(Litolff/Beethoven, Breitkopf/Brahms), so leave-one-engraving-out is
two folds and each fold trains on ONE WORK.  ⚠️ Publisher is perfectly
confounded with composer, exactly as at n=197 and worse: no prior of the form
"this house's pages carry these instruments" may be drawn from this, and a
fold-to-fold difference is a work difference.

## Features, and why these

All page-derived; none is the join's own output about this staff.

    tier        `instrument_source` — label / roster / score_order /
                score_order_ambiguity.  This is the field §7 makes
                load-bearing for the provenance rule.
    label_seen  did the margin reader resolve a label on THIS staff.  Read
                off the page, independent of the slot join.
    size_bucket the system's staff count relative to the document's maximum —
                a full system vs a reduced one is a different evidence regime.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arms as arms_mod          # noqa: E402
import load as load_mod          # noqa: E402
import score as score_mod        # noqa: E402

MIN_BIN = 10
BINS = [(0.0, 0.7), (0.7, 0.9), (0.9, 0.98), (0.98, 1.01)]
PRIOR_STRENGTH = 2.0
FEATURES = ("tier", "label_seen", "size_bucket")


def build(arms: list[str]) -> list[dict]:
    out = []
    for arm in arms:
        work, path, regime, _ = arms_mod.ARMS[arm]
        r = score_mod.score(load_mod.load(path, work, arm), regime)
        biggest = max((x["n_staves"] for x in r.records), default=0)
        for x in r.records:
            if x["emitted"] is None:
                continue          # an abstention has no name to be right about
            out.append({
                "engraving": x["engraving"], "publisher": x["publisher"],
                "work": x["work"],
                "tier": x["source"] or "(none)",
                "label_seen": x["label_read"] is not None,
                "size_bucket": "max" if x["n_staves"] == biggest else "reduced",
                "correct": bool(x["correct"]),
            })
    return out


def estimate(train, feats, target="correct"):
    glob = [0, 0]
    tier = collections.defaultdict(lambda: [0, 0])
    cell = collections.defaultdict(lambda: [0, 0])
    for r in train:
        k = tuple(r[f] for f in feats)
        for acc in (glob, tier[r["tier"]], cell[k]):
            acc[0] += bool(r[target])
            acc[1] += 1
    g = (glob[0] + 1) / (glob[1] + 2) if glob[1] else 0.5

    def p(r):
        k = tuple(r[f] for f in feats)
        th, tn = tier[r["tier"]]
        t = (th + PRIOR_STRENGTH * g) / (tn + PRIOR_STRENGTH) if tn else g
        ch, cn = cell[k]
        return (ch + PRIOR_STRENGTH * t) / (cn + PRIOR_STRENGTH) if cn else t
    return p


def reliability(pairs):
    """[(p, correct)] -> per-bin (n, predicted, observed), ECE, Brier."""
    rows = []
    ece_num = ece_den = 0.0
    for lo, hi in BINS:
        b = [(p, c) for p, c in pairs if lo <= p < hi]
        if not b:
            continue
        pred = sum(p for p, _ in b) / len(b)
        obs = sum(c for _, c in b) / len(b)
        thin = len(b) < MIN_BIN
        rows.append((f"[{lo:.2f},{hi:.2f})", len(b), pred, obs, thin))
        if not thin:
            ece_num += len(b) * abs(pred - obs)
            ece_den += len(b)
    ece = ece_num / ece_den if ece_den else float("nan")
    brier = sum((p - c) ** 2 for p, c in pairs) / len(pairs) if pairs else float("nan")
    return rows, ece, brier


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-beet5", default="beet5/shipped")
    ap.add_argument("--arm-brahms", default="brahms1/fit=search,spans=on")
    ap.add_argument("--json", help="write the record table")
    args = ap.parse_args()

    recs = build([args.arm_beet5, args.arm_brahms])
    print(f"CORPUS: {len(recs)} named judgeable staff records, "
          f"{len({r['engraving'] for r in recs})} engravings")
    print(f"        arms: {args.arm_beet5} + {args.arm_brahms}")
    print()

    print("TIER CENSUS — the n=197 probe's diagnosis was that the tier which "
          "would decide an admission had ZERO records.")
    tier = collections.Counter(r["tier"] for r in recs)
    tier_ok = collections.Counter(r["tier"] for r in recs if r["correct"])
    tier_work = collections.defaultdict(collections.Counter)
    for r in recs:
        tier_work[r["tier"]][r["work"]] += 1
    for t, n in tier.most_common():
        print(f"  {t:24s} n={n:5d}  correct {tier_ok[t]:5d} = "
              f"{tier_ok[t] / n:.4f}   works={dict(tier_work[t])}")
    print()

    print("FEATURE CELLS — a cell with no variance in the target cannot "
          "separate anything, whatever its n.")
    cells = collections.defaultdict(lambda: [0, 0])
    for r in recs:
        k = tuple(r[f] for f in FEATURES)
        cells[k][0] += r["correct"]
        cells[k][1] += 1
    degenerate = 0
    for k, (ok, n) in sorted(cells.items(), key=lambda kv: -kv[1][1]):
        rate = ok / n
        deg = rate in (0.0, 1.0)
        degenerate += n if deg else 0
        print(f"  {str(k):58s} n={n:5d}  correct={rate:.4f}"
              f"{'   <- degenerate (0 or 1)' if deg else ''}")
    print(f"  records in a degenerate cell: {degenerate}/{len(recs)} = "
          f"{degenerate / len(recs):.1%}")
    print()

    print("HELD OUT BY ENGRAVING (leave one out)")
    engs = sorted({r["engraving"] for r in recs})
    pooled = []
    for e in engs:
        train = [r for r in recs if r["engraving"] != e]
        test = [r for r in recs if r["engraving"] == e]
        p = estimate(train, FEATURES)
        pairs = [(p(r), r["correct"]) for r in test]
        rows, ece, brier = reliability(pairs)
        print(f"  fold held out: {e}   n_test={len(test)}  "
              f"train={len(train)}  ECE={ece:.4f}  Brier={brier:.4f}")
        for tag, n, pred, obs, thin in rows:
            print(f"      {tag:14s} n={n:5d}  predicted {pred:.3f}  "
                  f"observed {obs:.3f}   {obs - pred:+.3f}"
                  f"{'   (thin, excluded from ECE)' if thin else ''}")
        pooled += pairs
    rows, ece, brier = reliability(pooled)
    print()
    print(f"  POOLED   n={len(pooled)}   ECE={ece:.4f}   Brier={brier:.4f}")
    for tag, n, pred, obs, thin in rows:
        print(f"      {tag:14s} n={n:5d}  predicted {pred:.3f}  "
              f"observed {obs:.3f}   {obs - pred:+.3f}"
              f"{'   (thin, excluded from ECE)' if thin else ''}")
    print()
    print(f"  n_distinct predicted values: "
          f"{len({round(p, 6) for p, _ in pooled})}")

    # ── ⚠️ DISCRIMINATION: a low ECE on a monoculture is not calibration ─────
    print()
    print("⚠️ DISCRIMINATION — is the estimator doing anything the base rate "
          "does not?  A low ECE over a population that is 96% one bin is a "
          "property of the POPULATION, not of the model.")
    const_pairs = []
    for e in engs:
        train = [r for r in recs if r["engraving"] != e]
        test = [r for r in recs if r["engraving"] == e]
        base = ((sum(r["correct"] for r in train) + 1) / (len(train) + 2))
        const_pairs += [(base, r["correct"]) for r in test]
    _, c_ece, c_brier = reliability(const_pairs)
    print(f"  featureful  ECE={ece:.4f}  Brier={brier:.4f}")
    print(f"  constant    ECE={c_ece:.4f}  Brier={c_brier:.4f}   "
          "(predict the training base rate for everything)")
    print(f"  Brier skill vs constant: {1 - brier / c_brier:+.4f}")
    top = [(p, c) for p, c in pooled if p >= 0.98]
    print(f"  mass in the top bin: {len(top)}/{len(pooled)} = "
          f"{len(top) / len(pooled):.1%}   "
          f"promised {sum(p for p, _ in top) / len(top):.3f}, "
          f"delivered {sum(c for _, c in top) / len(top):.3f}")

    print()
    print("⚠️ HELD-OUT REACH PER TIER — a tier a fold never SAW in training "
          "cannot be calibrated by it, whatever the pooled number says.")
    for e in engs:
        train = [r for r in recs if r["engraving"] != e]
        test = [r for r in recs if r["engraving"] == e]
        p = estimate(train, FEATURES)
        seen = collections.Counter(r["tier"] for r in train)
        by = collections.defaultdict(list)
        for r in test:
            by[r["tier"]].append((p(r), r["correct"]))
        print(f"  fold {e}")
        for t, prs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            pred = sum(x for x, _ in prs) / len(prs)
            obs = sum(c for _, c in prs) / len(prs)
            print(f"      tier {t:24s} n_test={len(prs):5d}  "
                  f"n_train={seen.get(t, 0):5d}  predicted {pred:.3f}  "
                  f"observed {obs:.3f}"
                  f"{'   <- UNSEEN IN TRAINING' if not seen.get(t) else ''}")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"n": len(recs), "features": FEATURES,
             "tiers": dict(tier), "records": recs}, indent=1))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
