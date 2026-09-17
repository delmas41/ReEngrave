#!/usr/bin/env python3
"""Does staff-relative POSITION separate classes?  The pre-registered test.

Criterion fixed in ``CRITERION.md``, committed alone and before any number
here was computed.  Read that first; this file must not be read as its own
justification.

⚠️ REACH IS PRINTED BEFORE ANY RESULT and the probe exits non-zero declaring
itself DEAD at zero, because a store measured on nothing and a store measured
on noise produce the same reassuring silence.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.positional_store import (  # noqa: E402
    entries_from_record, identity_of_record, publisher_label, vbucket,
)


# ─────────────────────────────────────────────────────────────────────────────
# Mutual information, and the null that is the only thing that may be quoted
# ─────────────────────────────────────────────────────────────────────────────

def mutual_information(pairs):
    """I(bucket ; class) in bits.

    ⚠️ BIASED UPWARD BY BUCKET COUNT.  A finer grid raises this number on pure
    noise, which is exactly why no absolute value here is reportable and only
    the margin over the label-shuffle null is.  The null carries the identical
    bias because it keeps both marginals.
    """
    n = len(pairs)
    if n == 0:
        return 0.0
    joint = Counter(pairs)
    pb = Counter(b for b, _ in pairs)
    pc = Counter(c for _, c in pairs)
    total = 0.0
    for (b, c), k in joint.items():
        pxy = k / n
        total += pxy * math.log2(pxy / ((pb[b] / n) * (pc[c] / n)))
    return total


def null_distribution(positions, classes, width, seeds, rng_seed=20260917):
    """Shuffle the CLASS labels, keep every position exactly where it is.

    This destroys only the association under test.  The position distribution,
    the class marginals and the bucket count are all preserved to the item, so
    a margin over this null cannot be an artefact of any of them.
    """
    rng = random.Random(rng_seed)
    out = []
    shuffled = list(classes)
    buckets = [bucket_of(p, width) for p in positions]
    for _ in range(seeds):
        rng.shuffle(shuffled)
        out.append(mutual_information(list(zip(buckets, shuffled))))
    return out


def bucket_of(pos_steps, width_spaces):
    """⚠️ POSITION IS IN STEPS, WIDTH IN SPACES, and the conversion is the
    store's own `vbucket` rather than a second copy of the arithmetic.  The
    criterion was pre-registered in staff SPACES; the record's unit is the
    STEP (half a space), and two spellings of one conversion is how they
    drift."""
    return vbucket(pos_steps, width_spaces)


def summarise(observed, null):
    mean = sum(null) / len(null)
    var = sum((v - mean) ** 2 for v in null) / max(1, len(null) - 1)
    sd = math.sqrt(var)
    margin = (observed - mean) / sd if sd > 0 else float('inf')
    return mean, sd, margin


# ─────────────────────────────────────────────────────────────────────────────

def load(records):
    """(publisher -> [entry]) plus the reach table, printed before any result.

    ⚠️ THE STATISTIC NEEDS ONE LABEL PER OBSERVATION AND THE STORE HOLDS A SET,
    so this view takes `Entry.primary` and says so.  On this corpus the
    reduction is a no-op -- every entry comes from `glyph_box` and carries
    exactly one `detector_class` membership -- and `several_memberships` below
    reports where that stops being true.  The day it is non-zero, mutual
    information over a primary label is the wrong instrument and this line is
    where to change it.
    """
    by_pub = defaultdict(list)
    reach = []
    for path in records:
        t0 = time.time()
        ident = identity_of_record(Path(path))
        pub = publisher_label(ident.get('publisher'))
        ents = list(entries_from_record(
            Path(path), publisher=pub,
            edition_path=ident.get('edition_path'),
            work_id=ident.get('work_id')))
        named = [e for e in ents if e.memberships]
        unknown = [e for e in ents if not e.memberships]
        multi = [e for e in ents if len(e.memberships) > 1]
        positioned = [e for e in ents if e.staff_position is not None]
        reach.append(dict(record=Path(path).name, publisher=pub,
                          entries=len(ents), named=len(named),
                          unknown=len(unknown),
                          several_memberships=len(multi),
                          positioned=len(positioned),
                          seconds=round(time.time() - t0, 1)))
        by_pub[pub].extend(positioned)
    return by_pub, reach


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('records', nargs='+')
    ap.add_argument('--seeds', type=int, default=25)
    ap.add_argument('--out')
    args = ap.parse_args()

    by_pub, reach = load(args.records)

    print('REACH (printed before any result)')
    for r in reach:
        print('  %-36s %-11s entries=%-6d named=%-6d NO-MEMBERSHIP=%-5d '
              'multi=%-4d positioned=%-6d %ss'
              % (r['record'], r['publisher'], r['entries'], r['named'],
                 r['unknown'], r['several_memberships'], r['positioned'],
                 r['seconds']))
    total = sum(len(v) for v in by_pub.values())
    print('  TOTAL positioned entries: %d across %d publishers'
          % (total, len(by_pub)))
    if total == 0:
        print('DEAD: zero positioned entries. Nothing was measured.')
        return 2
    if len(by_pub) < 2:
        print('DEAD: fewer than two publishers; the criterion requires two.')
        return 2

    widths = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0]
    results = {'reach': reach, 'by_width': {}, 'per_class': {}}

    print('\nSEPARATION vs the label-shuffle null, by bucket width')
    print('  %-7s %-12s %8s %8s %8s %9s' %
          ('width', 'publisher', 'I_obs', 'I_null', 'sd', 'margin_sd'))
    for w in widths:
        row = {}
        for pub, ents in sorted(by_pub.items()):
            pos = [e.staff_position for e in ents]
            cls = [e.primary for e in ents]
            obs = mutual_information(list(zip(
                [bucket_of(p, w) for p in pos], cls)))
            null = null_distribution(pos, cls, w, args.seeds)
            mean, sd, margin = summarise(obs, null)
            row[pub] = dict(observed=round(obs, 4), null_mean=round(mean, 4),
                            null_sd=round(sd, 5), margin_sd=round(margin, 1),
                            n=len(pos))
            print('  %-7s %-12s %8.4f %8.4f %8.5f %9.1f'
                  % (w, pub, obs, mean, sd, margin))
        results['by_width'][str(w)] = row

    # ── criterion clause 3: is it carried by ONE class? ──────────────────────
    w = 0.5
    print('\nCLAUSE 3 — drop the single highest-contributing class (width %s)'
          % w)
    for pub, ents in sorted(by_pub.items()):
        pos = [e.staff_position for e in ents]
        cls = [e.primary for e in ents]
        pairs = list(zip([bucket_of(p, w) for p in pos], cls))
        base = mutual_information(pairs)
        contrib = {}
        for c in set(cls):
            kept = [(b, k) for b, k in pairs if k != c]
            contrib[c] = base - mutual_information(kept)
        worst = max(contrib, key=contrib.get)
        kept_pos = [p for p, k in zip(pos, cls) if k != worst]
        kept_cls = [k for k in cls if k != worst]
        obs = mutual_information(list(zip(
            [bucket_of(p, w) for p in kept_pos], kept_cls)))
        null = null_distribution(kept_pos, kept_cls, w, args.seeds)
        mean, sd, margin = summarise(obs, null)
        print('  %-12s top class=%-24s without it: margin=%.1f sd (n=%d)'
              % (pub, worst, margin, len(kept_cls)))
        results['per_class'].setdefault('clause3', {})[pub] = dict(
            top_class=worst, margin_sd=round(margin, 1), n=len(kept_cls))

    # ── the per-class table, reported whatever the pooled number does ────────
    print('\nPER-CLASS concentration (width %s) — reported always' % w)
    print('  %-12s %-26s %6s %8s %8s %8s' %
          ('publisher', 'class', 'n', 'median', 'IQR', 'entropy'))
    for pub, ents in sorted(by_pub.items()):
        groups = defaultdict(list)
        for e in ents:
            groups[e.primary].append(e.staff_position)
        rows = []
        for c, ps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(ps) < 20:
                continue
            ps = sorted(ps)
            med = ps[len(ps) // 2]
            iqr = ps[int(len(ps) * .75)] - ps[int(len(ps) * .25)]
            bc = Counter(bucket_of(p, w) for p in ps)
            ent = -sum((k / len(ps)) * math.log2(k / len(ps))
                       for k in bc.values())
            rows.append((c, len(ps), med, iqr, ent))
        for c, n, med, iqr, ent in rows[:14]:
            print('  %-12s %-26s %6d %8.2f %8.2f %8.2f'
                  % (pub, c, n, med, iqr, ent))
        results['per_class'][pub] = [
            dict(cls=c, n=n, median=round(med, 2), iqr=round(iqr, 2),
                 entropy_bits=round(ent, 2)) for c, n, med, iqr, ent in rows]

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1))
        print('\nwrote %s' % args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
