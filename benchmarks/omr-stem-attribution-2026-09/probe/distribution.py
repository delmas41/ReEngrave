"""Does the head-along-stroke position SEPARATE, once chords are accounted for?

⚠️⚠️ THE POOLED DISTRIBUTION CANNOT ANSWER THIS, AND ASSUMING IT COULD IS THE
TRAP. A chord is several heads on ONE physical stem, and the INNER head of a
three-note chord sits legitimately MID-stroke -- so a naive *"the head must be
at an end"* rule refuses the middle note of every chord, which is the
documented double-stop regression arriving in a new form. The pooled trough is
therefore a MIXTURE of the fault (a head crossing a neighbour's stroke) and the
convention working normally (a chord).

So the population that can answer it is the SINGLE-HEAD stem: a stroke that
exactly one notehead claims, where no chord is possible. If the convention is
real, THAT distribution is bimodal with an empty middle, and the pooled trough
is chords.

⚠️ It also asks the question the other way -- for multi-head stems, is the
group CONTIGUOUS from one end? -- because that is what a chord must look like
and what a wrongly-crossed neighbour must not.

Nothing here is a rule. This is the measurement that decides whether there is
one.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, overlap  # noqa: E402


def _hist(vals, nbins, lo=0.0, hi=1.0):
    out = [0] * nbins
    for v in vals:
        out[min(nbins - 1, max(0, int((v - lo) / (hi - lo) * nbins)))] += 1
    return [[round(lo + (hi - lo) * i / nbins, 3),
             round(lo + (hi - lo) * (i + 1) / nbins, 3), out[i]]
            for i in range(nbins)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--standoff", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    stems, heads, _ = collect(args.record)

    # Invert: stem id -> the heads that claim it, with their frac positions.
    per_stem = defaultdict(list)
    head_box_of = {}
    head_stems = defaultdict(list)
    for c, hs in heads.items():
        for sid_box in stems.get(c, []):
            pass
        for subj, _hid, hb in hs:
            head_box_of[subj] = hb
            for sid, sb in stems.get(c, []):
                if overlap(sb, hb):
                    hcy = hb[1] + hb[3] / 2.0
                    f = (hcy - sb[1]) / sb[3] if sb[3] > 0 else 0.5
                    per_stem[sid].append((subj, f, hb))
                    head_stems[subj].append((sid, sb, f))

    singles, multis = [], []
    group_sizes = Counter()
    contiguous = Counter()
    for sid, members in per_stem.items():
        group_sizes[len(members)] += 1
        if len(members) == 1:
            singles.append(members[0][1])
        else:
            for _subj, f, _hb in members:
                multis.append(f)
            # Is the group anchored at ONE end -- i.e. does the member
            # closest to the near end actually REACH it?
            fs = sorted(f for _s, f, _h in members)
            near_top = fs[0]
            near_bot = 1.0 - fs[-1]
            contiguous["anchored_top" if near_top <= near_bot
                        else "anchored_bottom"] += 1

    def band(vals, m):
        return sum(1 for f in vals if m < f < 1.0 - m)

    def pcts(vals):
        v = sorted(vals)
        if not v:
            return {}
        return {f"p{int(p * 100):02d}": round(v[min(len(v) - 1,
                                                    int(p * len(v)))], 4)
                for p in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, .99)}

    out = {
        "label": args.label or Path(args.record).name,
        "stems_claimed_by_a_head": len(per_stem),
        "group_size_histogram": dict(sorted(group_sizes.items())),
        "single_head_stems": {
            "n": len(singles),
            "percentiles": pcts(singles),
            "inside_band": {f"{m:.2f}": band(singles, m)
                            for m in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40)},
            "histogram_25": _hist(singles, 25),
        },
        "multi_head_stems": {
            "n_pairs": len(multis),
            "percentiles": pcts(multis),
            "inside_band": {f"{m:.2f}": band(multis, m)
                            for m in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40)},
            "histogram_25": _hist(multis, 25),
            "anchored": dict(contiguous),
        },
    }

    if args.standoff:
        so = json.load(open(args.standoff))
        rows = []
        for r in so["rows"]:
            subj = r["subject"]
            hb = head_box_of.get(subj)
            rows.append({
                "id": r["id"], "subject": subj,
                "in_record_as_notehead": hb is not None,
                "n_overlapping_stems": len(head_stems.get(subj, [])),
                "fracs": [round(f, 4) for _s, _b, f in head_stems.get(subj, [])],
                "print_says": r.get("print_says"),
                "attachment_says": r.get("attachment_says"),
                "beam_mate_says": r.get("beam_mate_says"),
            })
        out["standoff"] = {
            "n": len(rows),
            "found_in_record": sum(1 for r in rows if r["in_record_as_notehead"]),
            "with_at_least_one_overlapping_stem":
                sum(1 for r in rows if r["n_overlapping_stems"] > 0),
            "settled_by_print_and_with_a_stem":
                sum(1 for r in rows
                    if r["print_says"] and r["n_overlapping_stems"] > 0),
            "rows": rows,
        }

    print(json.dumps(out, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
