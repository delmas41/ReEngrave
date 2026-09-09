"""What do the assessable bar-length RUNS look like, per system?

Reads the pipeline's OWN substrate: it drives prepare -> gather -> adjudicate
and then builds a real `Evidence` over the live `Log`, so the bars it reports
are exactly the bars `_corroborate` and `_bar_run` see. Nothing is re-derived
from an exported file.
"""
import argparse, json, sys
from collections import Counter

from tools.omr.staged import gather, adjudicate, pipeline
from tools.omr.staged.adjudicate import Evidence, REGISTRY
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Kind, Outcome, Q


def modal(lengths):
    mode, n = Counter(lengths).most_common(1)[0]
    return mode, n, len(lengths)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="0")
    ap.add_argument("--weights", required=True)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    pages = []
    for part in args.pages.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))

    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(args.weights)
    prepared = pipeline.prepare_pages(args.pdf, pages, dpi=600)
    log = gather.gather(prepared, detector=det)
    adjudicate.run(log)

    spec = REGISTRY[Q.METER]
    out = []
    systems = log.subjects(Kind.SYSTEM)

    for sysct in systems:
        ev = Evidence(log, sysct, spec)
        bars = rhythm._bar_lengths_for(ev)
        v = log.verdict(Q.METER, sysct)
        row = {"system": sysct.to_key(),
               "page": sysct.page, "sys": sysct.system,
               "meter_outcome": None if v is None else v.outcome.value,
               "meter_reason": None if v is None else v.reason,
               "meter_value": None if v is None else v.value,
               "bars": {}}
        assessable = []
        for cell in sorted(bars):
            lengths = bars[cell]
            mode, n, tot = modal(lengths)
            ok = tot >= rhythm.METER_CARRY_MIN_STAVES_PER_BAR and n / tot >= 0.5
            row["bars"][cell] = {"mode": mode, "n_agree": n, "n_staves": tot,
                                 "assessable": ok,
                                 "all": sorted(Counter(lengths).items())}
            if ok:
                assessable.append((cell, mode))
        row["assessable"] = assessable
        out.append(row)

        print(f"\n=== {sysct.to_key()}  meter={row['meter_reason']} "
              f"{(v.value or {}).get('raw') if v is not None and v.value else None}")
        print(f"    cells with any bar length: {len(bars)}   assessable: {len(assessable)}")
        for cell in sorted(bars):
            b = row["bars"][cell]
            mark = "*" if b["assessable"] else " "
            print(f"   {mark} cell {cell:3d}  mode={b['mode']:7.3f} "
                  f"{b['n_agree']}/{b['n_staves']}  {b['all'][:8]}")
        # maximal runs of consecutive assessable cells at one value
        runs = []
        for cell, mode in assessable:
            if runs and runs[-1]["value"] == mode and runs[-1]["last"] == cell - 1:
                runs[-1]["last"] = cell
                runs[-1]["n"] += 1
            else:
                runs.append({"value": mode, "first": cell, "last": cell, "n": 1})
        row["runs"] = runs
        if runs:
            print("    RUNS (consecutive assessable cells at one length):")
            for r in runs:
                print(f"       {r['value']:7.3f} x{r['n']}  cells {r['first']}..{r['last']}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(out, fh, indent=2, default=str)
        print(f"\nwrote {args.json_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
