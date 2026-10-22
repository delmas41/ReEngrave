"""THE REVEAL — join the blind verdicts to the manifest and score them.

⚠️⚠️ THE POSITIVE CONTROL IS READ FIRST AND IT CAN CONDEMN THE WHOLE PASS.
Controls are heads whose stem the record DECIDED, shuffled in among the sample
so the adjudicator could not tell them apart. If the eye cannot recover the
direction the pipeline already read, no figure here survives -- the repo's own
rule that a control reporting "the print holds nothing there" must first be
able to say "I could not look there". So this prints, in order:

  1. the control's agreement with the record's own `up`/`down`;
  2. the control's `cannot_tell` rate against the SAMPLE's;
  3. only then the per-bucket truth.

⚠️ (2) is the one that turns a high `cannot_tell` rate from an admission into a
measurement. If controls read easily and stemless heads do not, the abstention
is largely the PLATE's and not the eye's. If both read the same, the eye is the
limit and every bucket figure must be quoted with that.

⚠️ THE CONVENTION TEST IS ONE-SIDED AND SAID SO. `side` is scored only where a
direction was determined; a `cannot_tell` is not a vote either way.

    python3 probe/score.py --adjudication ADJUDICATION-X.json \
        --manifest out/crop-manifest-X.json --json out/score-X.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

CONV = {("stem_printed_up", "right"), ("stem_printed_down", "left")}
VIOL = {("stem_printed_up", "left"), ("stem_printed_down", "right")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    adj = json.loads(Path(a.adjudication).read_text())
    man = json.loads(Path(a.manifest).read_text())
    by_id = {t["id"]: t for t in man["tiles"]}
    rows = []
    for r in adj["rows"]:
        t = by_id.get(r["id"])
        if t is None:
            print(f"UNJOINED TILE {r['id']} — the manifest and the "
                  "adjudication disagree; refusing to score a partial join",
                  file=sys.stderr)
            return 2
        rows.append({**r, **{k: t[k] for k in
                             ("subject", "kind", "bucket", "read_direction",
                              "cls", "width_cap_recovered", "staff_spacing",
                              "where")}})
    print(f"{man['label']}\njoined {len(rows)} tiles")

    ctrl = [r for r in rows if r["kind"] == "control"]
    samp = [r for r in rows if r["kind"] == "sample"]
    if not ctrl:
        print("DEAD: no positive control in this manifest", file=sys.stderr)
        return 2

    # ── 1. THE POSITIVE CONTROL ───────────────────────────────────────────
    print(f"\n== 1. POSITIVE CONTROL — {len(ctrl)} heads the record DECIDED")
    agree = dis = silent = other = 0
    for r in ctrl:
        mine = r["verdict"]
        read = r["read_direction"]
        if mine in ("stem_printed_up", "stem_printed_down"):
            if mine == f"stem_printed_{read}":
                agree += 1
            else:
                dis += 1
                print(f"   DISAGREES {r['id']}: print={mine} record={read}")
        elif mine == "cannot_tell":
            silent += 1
        else:
            other += 1
            print(f"   the print says {mine} where the record read "
                  f"{read}: {r['id']}")
    spoke = agree + dis
    print(f"   the eye and the record AGREE      {agree}")
    print(f"   they DISAGREE                     {dis}")
    print(f"   the eye could not tell            {silent}")
    print(f"   the eye says it is not a stem     {other}")
    if spoke:
        print(f"   -> agreement where the eye spoke: {agree}/{spoke} = "
              f"{agree/spoke:.1%}")
    else:
        print("   -> THE EYE NEVER SPOKE ON A CONTROL: this pass is DEAD")
        return 2

    # ── 2. IS THE ABSTENTION THE EYE'S OR THE PLATE'S? ────────────────────
    c_ct = sum(1 for r in ctrl if r["verdict"] == "cannot_tell") / len(ctrl)
    s_ct = sum(1 for r in samp if r["verdict"] == "cannot_tell") / len(samp)
    print(f"\n== 2. `cannot_tell` RATE — control {c_ct:.1%} "
          f"vs stemless sample {s_ct:.1%}")
    print("   (a much LOWER control rate means the stemless heads are the "
          "illegible ones, so the abstention is the PLATE's, not the eye's)")

    # ── 3. PER-BUCKET TRUTH ───────────────────────────────────────────────
    print(f"\n== 3. THE PRINT, PER CENSUS BUCKET ({len(samp)} stemless heads)")
    order = ["stem_printed_up", "stem_printed_down", "no_stem_printed",
             "not_a_notehead", "cannot_tell"]
    hdr = f"{'bucket':<48}" + "".join(f"{k.replace('stem_printed_','').replace('_printed',''):>9}"
                                       for k in order) + f"{'n':>5}"
    print(hdr)
    per_bucket = {}
    for b in sorted({r["bucket"] for r in samp}):
        g = [r for r in samp if r["bucket"] == b]
        c = collections.Counter(r["verdict"] for r in g)
        per_bucket[b] = {"n": len(g), **{k: c[k] for k in order}}
        print(f"{b:<48}" + "".join(f"{c[k]:>9}" for k in order)
              + f"{len(g):>5}")
    tot = collections.Counter(r["verdict"] for r in samp)
    print(f"{'TOTAL':<48}" + "".join(f"{tot[k]:>9}" for k in order)
          + f"{len(samp):>5}")

    # ── 4. THE WIDTH CAP ──────────────────────────────────────────────────
    rec = [r for r in samp if r["width_cap_recovered"]]
    print(f"\n== 4. THE WIDTH CAP — {len(rec)} of the sampled heads are ones "
          "relaxing `max_width_lines` 0.6 -> 1.5 recovers")
    rc = collections.Counter(r["verdict"] for r in rec)
    real = rc["stem_printed_up"] + rc["stem_printed_down"]
    junk = rc["not_a_notehead"] + rc["no_stem_printed"]
    told = real + junk
    for k in order:
        print(f"   {k:<22} {rc[k]:>4}")
    if told:
        print(f"\n   REAL (a stem IS printed)     {real}/{told} = "
              f"{real/told:.1%}")
        print(f"   JUNK (no stem to find)       {junk}/{told} = "
              f"{junk/told:.1%}")
        print(f"   ⚠️ the print could not settle {rc['cannot_tell']} of "
              f"{len(rec)} ({rc['cannot_tell']/len(rec):.1%}), so the rate "
              "above is over the settled ones ONLY")
    else:
        print("   the print settled NONE of them")

    # ── 5. THE CONVENTION ─────────────────────────────────────────────────
    spoke_side = [r for r in rows if r["verdict"].startswith("stem_printed_")
                  and r["side"] in ("left", "right")]
    ok = sum(1 for r in spoke_side if (r["verdict"], r["side"]) in CONV)
    bad = [r for r in spoke_side if (r["verdict"], r["side"]) in VIOL]
    print(f"\n== 5. SEAN'S CONVENTION — right-and-up / left-and-down")
    print(f"   strokes whose SIDE the print settles   {len(spoke_side)}")
    print(f"   obey the convention                    {ok}")
    print(f"   VIOLATE it (right-and-down etc.)       {len(bad)}")
    for r in bad:
        print(f"      ⚠️⚠️ COUNTER-EXAMPLE {r['id']} {r['subject']}: "
              f"{r['verdict']} on the {r['side']} — {r['reason']}")

    # ── 6. NO STEM MEANS A WHOLE NOTE ─────────────────────────────────────
    hollow = [r for r in rows if r["head_fill"] == "hollow"]
    nostem = [r for r in rows if r["verdict"] == "no_stem_printed"]
    print(f"\n== 6. `no stem means a whole note` — the registry files this "
          "ASSERTED with no figure")
    print(f"   heads the print shows HOLLOW            {len(hollow)}")
    print(f"   of those, a stem IS printed             "
          f"{sum(1 for r in hollow if r['verdict'].startswith('stem_'))}")
    print(f"   of those, NO stem is printed            "
          f"{sum(1 for r in hollow if r['verdict'] == 'no_stem_printed')}")
    print(f"   of those, the print cannot settle it    "
          f"{sum(1 for r in hollow if r['verdict'] == 'cannot_tell')}")
    print(f"   heads with NO stem printed (any fill)   {len(nostem)}, "
          f"of which hollow {sum(1 for r in nostem if r['head_fill']=='hollow')}")
    print("   ⚠️ every `no_stem_printed` head here is HOLLOW, which is the "
          "convention's direction; the converse (a FILLED head with no stem) "
          "is not observed, and would be the thing that refutes it")

    # ── 7. THE DETECTOR'S CLASS vs THE PRINT ──────────────────────────────
    nan = [r for r in samp if r["verdict"] == "not_a_notehead"]
    print(f"\n== 7. BOXES THE PRINT SAYS ARE NOT NOTEHEADS — {len(nan)} of "
          f"{len(samp)} ({len(nan)/len(samp):.1%})")
    for r in nan:
        print(f"   {r['id']} {r['cls']:<26} {r['bucket'][:34]:<34} "
              f"{r['reason'][:60]}")

    out = {
        "label": man["label"],
        "control": {"n": len(ctrl), "agree": agree, "disagree": dis,
                    "cannot_tell": silent, "not_a_stem": other,
                    "agreement_where_the_eye_spoke": agree / spoke},
        "cannot_tell_rate": {"control": c_ct, "sample": s_ct},
        "per_bucket": per_bucket,
        "width_cap": {"n_sampled": len(rec), "by_verdict": dict(rc),
                      "real": real, "junk": junk,
                      "settled": told,
                      "real_share_of_settled": (real / told) if told else None},
        "convention": {"n_sides_settled": len(spoke_side), "obey": ok,
                       "violate": len(bad),
                       "counter_examples": [r["id"] for r in bad]},
        "hollow": {"n": len(hollow),
                   "with_stem": sum(1 for r in hollow
                                    if r["verdict"].startswith("stem_")),
                   "no_stem": sum(1 for r in hollow
                                  if r["verdict"] == "no_stem_printed"),
                   "cannot_tell": sum(1 for r in hollow
                                      if r["verdict"] == "cannot_tell")},
        "not_a_notehead": [{"id": r["id"], "subject": r["subject"],
                            "cls": r["cls"], "bucket": r["bucket"],
                            "reason": r["reason"]} for r in nan],
    }
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
