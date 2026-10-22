"""What the THREE readers say about a narrowed duration, together.

⚠️ THE QUESTION IS THE MIX, NOT WHICH READER WINS. `adjudicate_duration`
counts beam strokes over a notehead and returns a RANGE when a stroke ends
within a notehead's width of the head -- "under it, possibly not". Three
independent things could settle that range and none of them is consulted
against the others today:

  1. the CLASSICAL-CV stroke  (`line_detection`, thin-line specialist)
  2. the DETECTOR's beam box  (YOLO, kept only where no CV stroke overlaps)
  3. the BAR SUM              (the meter, which the durations themselves voted)

`consequences.reconcile_duration` uses (3) already and is deliberately bounded
to changing ONE note per bar with a UNIQUE answer -- so on a page where a bar
holds several narrowed notes it refuses, which is most of them.

This probe measures, per bar, whether the admitted readings hold exactly one
combination that lands on the meter -- the strict generalisation of that bound
from one note to the bar. It DECIDES NOTHING and changes no file.

⚠️ IT ALSO REPORTS THE CONFOUND RATHER THAN HIDING IT: the staged record has
no voice decision, so a bar carrying two voices sums to about twice its meter
and no combination can land. Bars whose DECIDED notes alone already exceed the
meter are counted apart for that reason.

    python3 benchmarks/omr-staged-beam-mix-2026-09/probe_beam_mix.py RUN.json ...
"""
from __future__ import annotations

import collections
import itertools
import json
import sys
from pathlib import Path

#: A bar with more narrowed notes than this is not enumerated -- 2**14 is
#: already past the point where "unique" means anything.
MAX_ENUMERATED = 14
TOL = 1e-6


def load(path):
    r = json.loads(Path(path).read_text())
    V = r["record"]["verdicts"]
    standing = {}
    superseded = {v["supersedes"] for v in V if v.get("supersedes")}
    for v in V:
        if v["quantity"] != "duration" or v["id"] in superseded:
            continue
        standing[v["subject"]] = v
    meters = {v["subject"]: v["value"] for v in V
              if v["quantity"] == "meter" and v["outcome"] == "decided"}
    return r, standing, meters


def cell_of(glyph_key):
    p = glyph_key.split("/")
    return f"cell/{p[1]}/{p[2]}/{p[3]}/{p[4]}", f"system/{p[1]}/{p[2]}"


def main(argv):
    for path in argv:
        r, standing, meters = load(path)
        name = Path(path).stem
        print(f"\n{'=' * 72}\n{name}\n{'=' * 72}")

        # ── 1. the reader mix on every narrowed note ──────────────────────
        narrowed = [v for v in standing.values() if v["outcome"] == "narrowed"]
        decided = [v for v in standing.values() if v["outcome"] == "decided"]
        print(f"\n-- durations: {len(decided)} decided, {len(narrowed)} narrowed")
        if narrowed:
            mix = collections.Counter()
            for v in narrowed:
                d = v["detail"]
                cv, yolo = d.get("cv_beams", 0), d.get("yolo_beams", 0)
                mix[("cv>0" if cv else "cv=0", "yolo>0" if yolo else "yolo=0")] += 1
            print("   which reader saw a stroke at all:")
            for k, n in sorted(mix.items()):
                print(f"     {k[0]:6s} {k[1]:8s} {n:5d}  ({100*n/len(narrowed):.0f}%)")
            ev = collections.Counter(v["detail"].get("beam_evidence") for v in narrowed)
            print(f"   beam_evidence: {dict(ev)}")
            span = collections.Counter(
                (v["detail"].get("levels_certain"), v["detail"].get("levels_possible"))
                for v in narrowed)
            print("   (certain, possible) levels:")
            for k, n in sorted(span.items(), key=lambda kv: -kv[1])[:8]:
                print(f"     {k}  {n:5d}")

        # ── 2. could the BAR SUM settle them? ─────────────────────────────
        bars = collections.defaultdict(list)
        for key, v in standing.items():
            if not key.startswith("glyph/"):
                continue
            cell, system = cell_of(key)
            bars[(cell, system)].append(v)

        tally = collections.Counter()
        rescued = 0
        for (cell, system), notes in sorted(bars.items()):
            m = meters.get(system)
            if not m:
                tally["no_meter"] += 1
                continue
            target = float(m["numerator"]) * 4.0 / float(m["denominator"])
            nar = [v for v in notes if v["outcome"] == "narrowed"]
            fixed = sum(float(v["value"].get("beats") or 0.0)
                        for v in notes if v["outcome"] == "decided")
            if not nar:
                tally["already_fits" if abs(fixed - target) < TOL
                      else "no_narrowed_and_does_not_fit"] += 1
                continue
            if fixed - target > TOL:
                # ⚠️ the DECIDED notes alone already overflow the bar: this is
                # a multi-voice bar (or a real error) and no combination of the
                # narrowed ones can land. Reported apart, never as a failure of
                # the bar sum.
                tally["decided_already_overflow"] += 1
                continue
            if len(nar) > MAX_ENUMERATED:
                tally["too_many_to_enumerate"] += 1
                continue
            options = [[float(c["value"].get("beats") or 0.0)
                        for c in v["candidates"]] for v in nar]
            hits = sum(1 for combo in itertools.product(*options)
                       if abs(fixed + sum(combo) - target) < TOL)
            if hits == 1:
                tally["UNIQUE"] += 1
                rescued += len(nar)
            elif hits == 0:
                tally["none_fits"] += 1
            else:
                tally["several_fit"] += 1

        print(f"\n-- bars, by what the bar sum could do ({sum(tally.values())} bars)")
        for k, n in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f"     {k:28s} {n:5d}")
        print(f"   ⚠️ notes a UNIQUE bar-sum solution would settle: {rescued}"
              f" of {len(narrowed)} narrowed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
