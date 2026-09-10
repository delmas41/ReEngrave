"""Can a system's OWN BARS choose between its voted meter and the CAUTIONARY
that the previous system printed for it?

⚠️ THE QUESTION BEFORE THE MECHANISM. Brahms 1 / Breitkopf p.1 votes `9/4`
where the print says `9/8`, and the cautionary one system earlier reads `9/8`
on nine staves. Two readings of ONE printed fact, from two independent readers.
Nothing in this repository may pick between them by confidence, and n = 1 is
far too little to fit a rule — but Sean's ordering says arithmetic that checks
itself outranks what can only be read, and `9/4` is 9.0 quarter notes against
`9/8`'s 4.5. So: ASK THE BARS, in the carry's own existing currency.

If the bars cannot separate 9.0 from 4.5 on this system, the route is dead and
no amount of design saves it. This probe exists to find that out first.

⚠️ Drives the real pipeline and builds a real `Evidence`, so the bars it
reports are exactly the bars `_corroborate` would see — nothing is re-derived.
"""
import argparse
import sys

sys.path.insert(0, __file__.rsplit("/benchmarks/", 1)[0])

from tools.omr.staged import adjudicate, gather, pipeline            # noqa: E402
from tools.omr.staged.adjudicate import Evidence, REGISTRY           # noqa: E402
from tools.omr.staged.adjudicators import rhythm                     # noqa: E402
from tools.omr.staged.record import Kind, Outcome, Q                 # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="0,1")
    ap.add_argument("--weights", required=True)
    ap.add_argument("--candidates", default="9/4,9/8",
                    help="the two readings to put to the bars")
    a = ap.parse_args()

    pages = [int(x) for x in a.pages.split(",")]
    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(a.weights)
    prepared = pipeline.prepare_pages(a.pdf, pages, dpi=600)
    log = gather.gather(prepared, detector=det)
    adjudicate.run(log)

    spec = REGISTRY[Q.METER]
    cands = []
    for raw in a.candidates.split(","):
        n, d = raw.split("/")
        cands.append((raw, int(n), int(d)))

    for sysj in sorted(log.subjects(Kind.SYSTEM)):
        ev = Evidence(log, sysj, spec)
        bars = rhythm._bar_lengths_for(ev)
        v = log.verdict(Q.METER, sysj)
        got = (v.value or {}).get("raw") if v and v.outcome is Outcome.DECIDED else None
        print(f"\n{sysj.to_key()}  voted={got}  assessable bars={len(bars)}")
        for raw, n, d in cands:
            expected = n * 4.0 / d
            scored = rhythm._score_bars(bars, expected)
            if "terms" not in scored:
                print(f"   {raw:>5} ({expected:4.1f} ql): {scored.get('state')} "
                      f"— {scored.get('bars_assessable', 0)} assessable")
                continue
            support = sum(t.weight for t in scored["terms"])
            print(f"   {raw:>5} ({expected:4.1f} ql): support {support:+6.1f}  "
                  f"{scored['bars_agree']}+/{scored['bars_disagree']}-  "
                  f"seen={scored['bar_lengths_seen']}")


if __name__ == "__main__":
    main()
