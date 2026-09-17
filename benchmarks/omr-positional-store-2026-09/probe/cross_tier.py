#!/usr/bin/env python3
"""TRUE against OBSERVED — the control the pre-registered criterion demands.

`CRITERION.md` names the confound before looking: the OBSERVED tier's class is
the DETECTOR's, so a separation measured there is partly **the detector
agreeing with itself**, and the finding may only be stated as *"position
separates the detector's classes"* unless a tier free of that circularity says
otherwise.

This is that tier.  A Verovio render's label is what the renderer was ASKED to
draw and its position is where it drew it; neither passes through a
classifier.  Two questions:

1. Does position separate classes **in the TRUE tier**, against the same
   label-shuffle null?  A positive here is about the music.
2. Do the two tiers **agree about where each family falls**?  Agreement is
   what licenses reading the OBSERVED tier as measuring the page rather than
   the reader.

⚠️ `TRUE_TIER_CAVEAT`: a PAGE truth is not an ENCODING truth, so COUNTS across
the two tiers are not comparable and only POSITIONS are compared here.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.page_truth import SCORED_CLASSES            # noqa: E402
from tools.omr.positional_store import (                   # noqa: E402
    entries_from_record, entries_from_render, identity_of_record,
    publisher_label,
)
from tools.omr.score_reading import detector_family        # noqa: E402
from separation import (                                   # noqa: E402
    bucket_of, mutual_information, null_distribution, summarise,
)


def family_of(entry) -> str | None:
    """One vocabulary for both tiers.

    ⚠️ IMPORTED FROM BOTH SIDES RATHER THAN RESTATED.  `SCORED_CLASSES` is
    `page_truth`'s own renderer->family map and `detector_family` is
    `score_reading`'s own detector->family map; writing a third table here is
    how the three drift, and this repo has paid for that shape.
    """
    name = entry.primary
    if entry.tier == 'true':
        return SCORED_CLASSES.get(name)
    return detector_family(name)


def stats(vals):
    v = sorted(vals)
    return dict(n=len(v), median=round(v[len(v) // 2], 2),
                iqr=round(v[int(len(v) * .75)] - v[int(len(v) * .25)], 2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--record', action='append', default=[])
    ap.add_argument('--render', action='append', default=[],
                    help='LABEL=path.mxl')
    ap.add_argument('--render-pages', type=int, default=2)
    ap.add_argument('--seeds', type=int, default=25)
    ap.add_argument('--out')
    args = ap.parse_args()

    observed = defaultdict(list)
    true = defaultdict(list)

    for r in args.record:
        ident = identity_of_record(Path(r))
        pub = publisher_label(ident.get('publisher'))
        observed[pub].extend(
            e for e in entries_from_record(
                Path(r), publisher=pub,
                edition_path=ident.get('edition_path'))
            if e.staff_position is not None)
    for spec in args.render:
        label, _, path = spec.partition('=')
        true[label].extend(
            e for e in entries_from_render(
                Path(path), publisher=label, max_pages=args.render_pages)
            if e.staff_position is not None)

    print('REACH (printed before any result)')
    for k, v in sorted(observed.items()):
        print('  OBSERVED %-12s %6d positioned entries' % (k, len(v)))
    for k, v in sorted(true.items()):
        print('  TRUE     %-12s %6d positioned entries' % (k, len(v)))
    if not true:
        print('DEAD: no TRUE tier. The confound control did not run.')
        return 2
    if not observed:
        print('DEAD: no OBSERVED tier.')
        return 2

    res = {'reach': {'observed': {k: len(v) for k, v in observed.items()},
                     'true': {k: len(v) for k, v in true.items()}}}

    # ── 1. does position separate classes in the TRUE tier? ─────────────────
    print('\n1. SEPARATION IN THE TRUE TIER (no detector anywhere in it)')
    print('  %-14s %-7s %8s %8s %8s %9s'
          % ('render', 'width', 'I_obs', 'I_null', 'sd', 'margin_sd'))
    res['true_separation'] = {}
    for label, ents in sorted(true.items()):
        pos = [e.staff_position for e in ents]
        cls = [e.primary for e in ents]
        for w in (0.1, 0.25, 0.5):
            obs = mutual_information(
                list(zip([bucket_of(p, w) for p in pos], cls)))
            null = null_distribution(pos, cls, w, args.seeds)
            mean, sd, margin = summarise(obs, null)
            print('  %-14s %-7s %8.4f %8.4f %8.5f %9.1f'
                  % (label, w, obs, mean, sd, margin))
            res['true_separation'].setdefault(label, {})[str(w)] = dict(
                observed=round(obs, 4), null_mean=round(mean, 4),
                null_sd=round(sd, 5), margin_sd=round(margin, 1), n=len(pos))

    # ── 2. do the tiers agree about WHERE each family falls? ────────────────
    print('\n2. WHERE EACH FAMILY FALLS — TRUE against OBSERVED')
    print('  (positions only; counts are NOT comparable across tiers)')
    fam_true = defaultdict(list)
    for ents in true.values():
        for e in ents:
            f = family_of(e)
            if f:
                fam_true[f].append(e.staff_position)
    fam_obs = defaultdict(lambda: defaultdict(list))
    for pub, ents in observed.items():
        for e in ents:
            f = family_of(e)
            if f:
                fam_obs[f][pub].append(e.staff_position)

    pubs = sorted(observed)
    hdr = '  %-20s %16s' % ('family', 'TRUE med(IQR)')
    for p in pubs:
        hdr += ' %18s' % ('%s med(IQR)' % p[:9])
    hdr += ' %8s' % 'max|d|'
    print(hdr)
    res['families'] = {}
    agree = disagree = 0
    for f in sorted(fam_true, key=lambda k: -len(fam_true[k])):
        if len(fam_true[f]) < 10:
            continue
        t = stats(fam_true[f])
        row = '  %-20s %7.2f(%4.2f)n=%-4d' % (f, t['median'], t['iqr'], t['n'])
        deltas = []
        entry = {'true': t, 'observed': {}}
        for p in pubs:
            vals = fam_obs.get(f, {}).get(p, [])
            if len(vals) < 10:
                row += ' %18s' % '-'
                continue
            o = stats(vals)
            entry['observed'][p] = o
            deltas.append(abs(o['median'] - t['median']))
            row += ' %9.2f(%4.2f)n=%-4d' % (o['median'], o['iqr'], o['n'])
        if deltas:
            md = max(deltas)
            row += ' %8.2f' % md
            entry['max_abs_median_delta'] = round(md, 2)
            # ⚠️ ONE STAFF SPACE is the threshold, and it is a UNIT rather than
            # a tuned number: a family whose two tiers agree to within a space
            # is agreeing at the resolution an engraver works in.
            if md <= 2.0:
                agree += 1
            else:
                disagree += 1
        print(row)
        res['families'][f] = entry

    print('\n  families agreeing within one staff space (2 steps): %d of %d'
          % (agree, agree + disagree))
    res['agreement'] = {'within_one_space': agree,
                        'total_compared': agree + disagree}

    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=1))
        print('\nwrote %s' % args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
