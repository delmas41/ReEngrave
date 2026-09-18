"""EVERY TABLE IN FINDINGS.md, re-derived. Run this, do not quote the prose.

Joins the width rows to the three things whose denominators this job was sent
to clean:

  * the REJECTION CENSUS buckets (`omr-stem-crop-pass-2026-09/out/*-rows.json`),
    so the width of a `no_stem` head can be read against the reason the filter
    chain gave;
  * the CROP PASS's print verdicts (`out/score-*.json` and the crop manifests),
    which is the only truth about what a box actually is;
  * the BEAM-MATE standoff and the STROKE reader's reach, which are issues 1
    and 2 and are the reason Sean picked this job.

⚠️ POSITIVE CONTROLS FIRST, AND THEY CAN FAIL. Before any width is read the
probe reproduces four published figures from its own inputs -- the notehead
totals (2,347 / 3,337), the census bucket table, the decided/no_stem/disagree
partition, and that the three populations SUM to the notehead total. A drifted
join would otherwise attribute contamination with total confidence, which is
this thread's own recorded failure.

⚠️ THE JOIN IS ON THE SUBJECT ADDRESS, never on a box. Two pages superimpose
exactly in page pixels and a cell index restarts per system; both are frame
errors this repo has already paid for, in a measuring instrument.

⚠️ NOTHING HERE IS POOLED ACROSS PUBLISHERS. The contamination differs 7x
between the two plates and nothing says which is typical.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
BENCHMARKS = BENCH.parent
CROP = BENCHMARKS / "omr-stem-crop-pass-2026-09" / "out"
STROKE = BENCHMARKS / "omr-stem-stroke-2026-09" / "out"
ATTACH = BENCHMARKS / "omr-stem-attachment-2026-09" / "out"

# ⚠️ INHERITED UNCHANGED from the crop pass and NOT fitted here.
FLOOR = 1.0

PUBS = {
    "litolff": {
        "label": "Litolff Beethoven 5 pp.1-4",
        "n_heads": 2347, "n_decided": 1443, "n_no_stem": 793,
        "n_disagree": 111,
    },
    "breitkopf": {
        "label": "Breitkopf Brahms 1 pp.0-3",
        "n_heads": 3337, "n_decided": 1791, "n_no_stem": 1529,
        "n_disagree": 17,
    },
}


def q(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, int(p * len(s)))] if s else float("nan")


def fam(cls: str) -> str:
    return ("Whole" if "Whole" in cls
            else "Half" if "Half" in cls else "Black")


def band(rows, key="w_page"):
    v = [r[key] for r in rows if r[key] is not None]
    if not v:
        return None
    return {"n": len(v), "min": round(min(v), 3), "p5": round(q(v, .05), 3),
            "median": round(q(v, .50), 3), "p95": round(q(v, .95), 3),
            "max": round(max(v), 3),
            "under_floor": sum(1 for x in v if x < FLOOR)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pub", required=True, choices=sorted(PUBS))
    ap.add_argument("--json", required=True)
    a = ap.parse_args()
    meta = PUBS[a.pub]

    widths = json.loads((BENCH / "out" / f"{a.pub}-widths.json").read_text())
    rows = widths["rows"]
    W = {r["subject"]: r for r in rows}
    census = json.loads((CROP / f"{a.pub}-rows.json").read_text())
    bucket = {r["subject"]: r["bucket"] for r in census["rows"]}

    # ------------------------------------------------------------------ #
    # POSITIVE CONTROLS. Each can fail; each names a published figure.
    # ------------------------------------------------------------------ #
    ctl = {}
    ctl["notehead_total"] = [len(rows), meta["n_heads"]]
    by_out = collections.Counter(
        r["reason"] if r["outcome"] == "abstained" else "DECIDED" for r in rows)
    ctl["decided"] = [by_out["DECIDED"], meta["n_decided"]]
    ctl["no_stem"] = [by_out["no_stem"], meta["n_no_stem"]]
    ctl["stems_disagree"] = [by_out["stems_disagree"], meta["n_disagree"]]
    # the three populations must PARTITION the notehead total
    ctl["partition"] = [by_out["DECIDED"] + by_out["no_stem"]
                        + by_out["stems_disagree"], len(rows)]
    # the census must cover exactly the no_stem population
    ctl["census_covers_no_stem"] = [len(bucket), meta["n_no_stem"]]
    ctl["census_subjects_are_heads"] = [
        sum(1 for s in bucket if s in W), len(bucket)]
    # the two rulers must agree -- ⚠️ a FRAME-CONSISTENCY control, NOT an
    # independence claim: `bbox_page_px` is DERIVED from the canonical box by
    # `gather._page_box`, so what this proves is that both box CONVENTIONS
    # were read correctly (corner-box vs width-box), which is the hazard the
    # handoff records a session losing time to. See FINDINGS §0.
    dif = [abs(r["w_canon"] - r["w_page"]) for r in rows
           if r["w_canon"] is not None and r["w_page"] is not None]
    ctl["ruler_agreement_max"] = [round(max(dif), 4) if dif else None, "<0.02"]

    bad = [k for k, (got, want) in ctl.items()
           if k != "ruler_agreement_max" and got != want]
    if dif and max(dif) > 0.02:
        bad.append("ruler_agreement_max")
    print(f"== {meta['label']}")
    for k, (got, want) in ctl.items():
        print(f"   {'FAIL' if k in bad else 'ok  '} {k:<28} {got} (want {want})")
    if bad:
        print(f"DEAD: {len(bad)} positive control(s) failed -- the join has "
              f"drifted and no table below may be quoted", file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    out = {"label": meta["label"], "floor_staff_spaces": FLOOR,
           "controls": {k: {"got": g, "want": w} for k, (g, w) in ctl.items()},
           "n": len(rows)}

    # 1. THE FALSE-POSITIVE SIDE -- the open question the crop pass declared.
    dec = [r for r in rows if r["outcome"] == "decided"]
    out["decided"] = band(dec)
    out["decided"]["share_under_floor"] = round(
        out["decided"]["under_floor"] / len(dec), 4)
    out["decided_under_floor_subjects"] = sorted(
        r["subject"] for r in dec if r["w_page"] < FLOOR)

    # 2. THE POPULATIONS, side by side.
    pops = {"DECIDED": dec,
            "stems_disagree": [r for r in rows
                               if r["reason"] == "stems_disagree"],
            "no_stem": [r for r in rows if r["reason"] == "no_stem"]}
    for b in sorted(set(bucket.values())):
        pops["no_stem / " + b] = [W[s] for s, x in bucket.items() if x == b]
    out["populations"] = {k: band(v) for k, v in pops.items()}
    for k, v in out["populations"].items():
        if v:
            v["share_under_floor"] = round(v["under_floor"] / v["n"], 4)

    # 3. [L4] -- whole vs half vs black, on the DECIDED population (the one
    #    the pipeline reads correctly) and on ALL boxes.
    out["L4"] = {}
    for pop_name, pop in (("all", rows), ("decided", dec)):
        d = collections.defaultdict(list)
        for r in pop:
            d[fam(r["cls"])].append(r)
        out["L4"][pop_name] = {k: band(v) for k, v in sorted(d.items())}

    # 4. ISSUE 2 -- the stroke reader's reach over a cleaned denominator.
    #    Its own population is the `too WIDE` bucket.
    wide = [W[s] for s, x in bucket.items() if x.startswith("too WIDE")]
    tall = [W[s] for s, x in bucket.items() if x.startswith("too TALL")]
    out["issue2"] = {
        "too_WIDE_n": len(wide),
        "too_WIDE_under_floor": sum(1 for r in wide if r["w_page"] < FLOOR),
        "too_TALL_n": len(tall),
        "too_TALL_under_floor": sum(1 for r in tall if r["w_page"] < FLOOR),
        "no_stem_n": len(pops["no_stem"]),
        "no_stem_under_floor": sum(1 for r in pops["no_stem"]
                                   if r["w_page"] < FLOOR),
    }

    # 5. ISSUE 1 -- the beam-mate standoff, where a standoff file exists.
    sf = CROP / f"{a.pub}-standoff.json"
    if sf.exists():
        st = json.loads(sf.read_text())
        srows = st.get("rows", st if isinstance(st, list) else [])
        subj = [r.get("subject") for r in srows if isinstance(r, dict)]
        hit = [W[s] for s in subj if s in W]
        out["issue1"] = {
            "standoff_rows": len(subj),
            "joined_to_a_width": len(hit),
            "under_floor": sum(1 for r in hit if r["w_page"] < FLOOR),
            "band": band(hit),
            "under_floor_subjects": sorted(
                r["subject"] for r in hit if r["w_page"] < FLOOR),
        }

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")

    print(f"\n-- width in staff spaces, floor = {FLOOR}")
    print(f"   {'population':<46} {'n':>6} {'p5':>6} {'med':>6} {'p95':>6} "
          f"{'<1.0':>6} {'share':>7}")
    for k, v in out["populations"].items():
        if v:
            print(f"   {k:<46} {v['n']:>6} {v['p5']:>6.3f} {v['median']:>6.3f} "
                  f"{v['p95']:>6.3f} {v['under_floor']:>6} "
                  f"{v['share_under_floor']:>6.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
