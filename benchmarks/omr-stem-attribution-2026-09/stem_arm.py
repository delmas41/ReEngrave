"""GATHER ONCE, ADJUDICATE TWICE — the stem-attribution A/B.

⚠️ THE CONTROL IS THE POINT, and for THIS quantity it cannot be the obvious
one. `readjudicate.py`'s control re-adjudicates unchanged and requires the
record's own verdicts back. That works for `duration`; it CANNOT work for
`stem_direction`, because **both shared records predate the beam-mate tier**
(handoff 2026-09-18 §3.2), so today's tree answers `beam_mate` where the
record says `no_stem` -- by design, not by drift. A control that demanded
equality there would fail for a reason that is not the rule under test.

So the faithfulness of the rebuild is proved on a quantity that HAS not moved:

  CONTROL 1 (REBUILD)  -- `duration` verdicts must reproduce the record
                          EXACTLY. This is the precedent's own control, and it
                          is what licenses every number below.
  CONTROL 2 (BASELINE) -- the record-vs-base `stem_direction` diff must be
                          ONLY `no_stem -> beam_mate`. Any other transition is
                          drift and is reported, not absorbed.
  ARM                  -- base vs rule, re-adjudicated from the SAME rebuilt
                          Log in the SAME process, so the two arms differ only
                          in the rule.

⚠️ BLIND TO A GATHER CHANGE, like its precedent: it rebuilds from saved rows,
so a new quantity or a changed frame never enters. The rule under test is an
ADJUDICATE change, which is why this instrument is the right one.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate                # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH           # noqa: E402


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order."""
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def verdicts_of(log: Log, quantity: str) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == quantity}


def _run(rec: dict) -> Log:
    log = rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    return log


def _summarise(vs: dict) -> Counter:
    c = Counter()
    for v in vs.values():
        if v["outcome"] == "decided":
            c[f"decided:{v.get('value')}"] += 1
        else:
            c[f"{v['outcome']}:{v.get('reason')}"] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    print(f"loading {a.record} ...", flush=True)
    rec = json.load(open(a.record))["record"]

    # ---------------- CONTROL 1: the rebuild is faithful ------------------
    os.environ.pop("OMR_STEM_ENDS", None)
    base_log = _run(rec)
    got_dur = verdicts_of(base_log, "duration")
    want_dur = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == "duration"}
    same = sum(1 for k, w in want_dur.items()
               if (g := got_dur.get(k)) is not None
               and g["outcome"] == w["outcome"]
               and (g.get("value") or {}).get("beats")
               == (w.get("value") or {}).get("beats"))
    c1_ok = (same == len(want_dur) and len(got_dur) == len(want_dur))
    print(f"CONTROL 1 (REBUILD): {same} of {len(want_dur)} duration verdicts "
          f"reproduced exactly, {len(got_dur) - len(want_dur):+d} extra "
          f"-> {'OK' if c1_ok else 'FAILED'}", flush=True)

    # ---------------- CONTROL 2: base vs the record ------------------------
    base = verdicts_of(base_log, "stem_direction")
    rec_sd = {v["subject"]: v for v in rec["verdicts"]
              if v["quantity"] == "stem_direction"}
    moves = Counter()
    for k, w in rec_sd.items():
        g = base.get(k)
        if g is None:
            moves["absent from rebuild"] += 1
            continue
        wk = (w.get("reason") if w["outcome"] != "decided"
              else f"decided:{w.get('value')}")
        gk = (g.get("reason") if g["outcome"] != "decided"
              else f"decided:{g.get('value')}")
        if wk != gk:
            moves[f"{wk} -> {gk}"] += 1
    expected_only = all(m.startswith("no_stem -> ") for m in moves)
    print(f"CONTROL 2 (BASELINE): {len(rec_sd)} record verdicts, "
          f"{sum(moves.values())} move -> "
          f"{'only no_stem transitions (expected: pre-tier record)' if expected_only else 'UNEXPECTED DRIFT'}")
    for m, n in moves.most_common(12):
        print(f"           {m}: {n}")

    # ---------------- ARM: base vs the rule --------------------------------
    os.environ["OMR_STEM_ENDS"] = "1"
    arm_log = _run(rec)
    arm = verdicts_of(arm_log, "stem_direction")
    os.environ.pop("OMR_STEM_ENDS", None)

    delta = Counter()
    changed = []
    for k, b in base.items():
        g = arm.get(k)
        if g is None:
            delta["absent from arm"] += 1
            continue
        bk = (b.get("reason") if b["outcome"] != "decided"
              else f"decided:{b.get('value')}")
        gk = (g.get("reason") if g["outcome"] != "decided"
              else f"decided:{g.get('value')}")
        if bk != gk:
            delta[f"{bk} -> {gk}"] += 1
            changed.append({"subject": k, "base": bk, "arm": gk})

    print(f"\nARM: {len(base)} base verdicts, {len(arm)} arm verdicts, "
          f"{sum(delta.values())} change")
    for m, n in delta.most_common(30):
        print(f"     {m}: {n}")

    print("\nBASE census:", dict(_summarise(base).most_common()))
    print("ARM  census:", dict(_summarise(arm).most_common()))

    if a.out:
        Path(a.out).write_text(json.dumps({
            "label": a.label or Path(a.record).name,
            "record": a.record,
            "control_1_rebuild": {"reproduced": same, "of": len(want_dur),
                                  "extra": len(got_dur) - len(want_dur),
                                  "ok": c1_ok},
            "control_2_baseline": {"n_record_verdicts": len(rec_sd),
                                   "moves": dict(moves),
                                   "only_expected": expected_only},
            "base_census": dict(_summarise(base)),
            "arm_census": dict(_summarise(arm)),
            "delta": dict(delta),
            "changed": changed,
        }, indent=1))
        print(f"wrote {a.out}")

    # A run whose rebuild is not faithful has measured its own harness.
    return 0 if c1_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
