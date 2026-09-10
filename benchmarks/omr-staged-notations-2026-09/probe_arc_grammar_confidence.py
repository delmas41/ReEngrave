"""Is the arc grammar SILENT exactly where the reading is weakest?

⚠️ THE QUESTION IS NOT MINE. It comes from the meter/boundary session's
finding, stated as a principle: **the case that most needs an arbiter is the
case where the arbiter is silent.** A page whose meter the reader mangles is a
page whose ink is degraded, and the same degradation stops its bars from
summing -- on the Breitkopf system that misreads 9/8 as 9/4, NOT ONE of its
seven bars clears the cross-staff quorum
(`benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md` §4c).

`arc_kind` has the same shape: the position grammar needs two detected heads
under the arc, and it is available on only 40.7% of arcs. If the missing 59.3%
are the weakly-read arcs, the grammar is absent precisely where a reading most
needs checking -- and any future pricing of the tie/slur veto has to know that
before it reads an agreement rate as reassurance.

Confidence is the ink-quality proxy. It is the same proxy the meter letter
path uses (0.887-0.927 engraved vs 0.377-0.560 scan) and is deliberately NOT
gated on there; the same restraint applies here.

    python3 benchmarks/omr-staged-notations-2026-09/probe_arc_grammar_confidence.py RECORD.json
"""
import json
import statistics as st
import sys


def main(path):
    rec = json.load(open(path))["record"]
    v = [x for x in rec["verdicts"]
         if x["quantity"] == "arc_kind" and x["outcome"] == "decided"]
    have = [x for x in v if x["detail"]["grammar"]["says"]]
    none = [x for x in v if not x["detail"]["grammar"]["says"]]
    ag = [x for x in have if x["detail"]["grammar"]["agrees_with_reading"]]
    dis = [x for x in have if not x["detail"]["grammar"]["agrees_with_reading"]]

    def row(name, xs):
        c = sorted(x["detail"]["confidence"] for x in xs
                   if x["detail"].get("confidence") is not None)
        if not c:
            print(f"  {name:<24} n=0")
            return
        print(f"  {name:<24} n={len(c):3d}  median={st.median(c):.3f}  "
              f"q1={c[len(c)//4]:.3f} q3={c[3*len(c)//4]:.3f}")

    # ⚠️ MISSING FIRST, then AVAILABLE and ITS OWN SPLIT. The first version
    # printed AVAILABLE, MISSING, "...and AGREES", "...and DISAGREES", so the
    # two `...and` lines read as children of MISSING when they are a split of
    # AVAILABLE (42 + 39 = 81, not 118). The label carries it now, not the
    # order, so a reader cannot get the finding backwards from either this
    # output or the table it feeds.
    print(f"arcs decided: {len(v)}")
    row("grammar MISSING", none)
    row("grammar AVAILABLE", have)
    row("  of available, AGREES", ag)
    row("  of available, DISAGREES", dis)
    assert len(ag) + len(dis) == len(have), "the split must partition AVAILABLE"
    for nm, xs in (("available", have), ("missing", none)):
        f = [x["detail"]["grammar"]["flanked_heads"] for x in xs]
        print(f"  flanked heads, {nm:<10} mean={st.mean(f):.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
