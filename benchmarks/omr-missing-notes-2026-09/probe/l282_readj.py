#!/usr/bin/env python3
"""l282_readj: GATHER once, ADJUDICATE three ways -- the 2.82 rules priced on a FIXED gather (no detector jitter), with
every per-stroke ink refusal logged. ROADMAP 2.82. A reading probe built on `benchmarks/omr-staged-duration-beams-2026-09/
readjudicate.py`'s rebuild.

MODES (what is patched, so an arm differs from another by the rule under test and nothing else):
  base       the 2.74 tree: no core rescue, `one_stem` fires whenever fewer than two registered stems
  thin       2.82's THICKNESS finding only: a thin-median stroke with a thick core on two stems (a head at each stem's far
             end) is kept for the heads under the core; thick strokes are judged exactly as in `base`
  full       2.82 as built: `thin` + the core answers the stem tests of a thick stroke + `one_stem` needs POSITIVE evidence
             (fewer than two heads at the stroke)

CONTROL (it can fail): on a record produced by the `thin` tree (the arm records of this lane's first build), mode `thin`
must reproduce every `adjudicate_duration` verdict the record holds; `--control` prints the count of mismatches.

    python3 l282_readj.py --record R --modes base,thin,full --out DIR/tag [--control thin]
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate, adjudicators, consequences, evaluate    # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH                          # noqa: E402
from tools.omr.staged.record import Log, Subject                                  # noqa: E402

ORIG = {"core": RH._core_beam_on_two_stems, "second": RH._may_be_a_second_stem, "nab": RH._not_a_beam_by_ink}


def rebuild(rec):
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]] + [(r, "abs") for r in rec.get("abstentions", [])]
    # ONE counter numbers observations AND abstentions (ids run obs:000002, abs:000004, ...): sorting by the id STRING
    # puts every `abs:` first and renumbers every `obs:`, so `beam_row_id` (an obs id) no longer names its stroke.
    rows.sort(key=lambda t: int(t[0]["id"].split(":")[1]))
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"], frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **detail)
    return log


def set_mode(mode, reasons):
    RH._core_beam_on_two_stems = ORIG["core"]
    RH._may_be_a_second_stem = ORIG["second"]
    if mode == "base":
        RH._core_beam_on_two_stems = lambda d, heads=(), space=0.0: None
        RH._may_be_a_second_stem = lambda *a, **k: False
    elif mode == "thin":
        core = ORIG["core"]
        RH._core_beam_on_two_stems = (lambda d, heads=(), space=0.0:
                                      None if ((d or {}).get("thickness_ratio") or 0) >= RH.BEAM_THICKNESS_RATIO_MIN
                                      else core(d, heads, space))
        RH._may_be_a_second_stem = lambda *a, **k: False
    elif mode != "full":
        raise SystemExit(f"unknown mode {mode}")

    def wrapped(ev, cell, beams, stems, tol, head_x=None):
        kept, dropped, used = ORIG["nab"](ev, cell, beams, stems, tol, head_x=head_x)
        for sid, why in dropped.items():
            reasons[f"{ev.subject.to_key()}|{sid}"] = why
        return kept, dropped, used
    RH._not_a_beam_by_ink = wrapped


def summ(v):
    if v["outcome"] == "decided":
        return ["decided", (v.get("value") or {}).get("beats") if isinstance(v.get("value"), dict) else None, None, v.get("reason")]
    if v["outcome"] == "narrowed":
        c = sorted({(x.get("value") or {}).get("beats") for x in (v.get("candidates") or [])
                    if isinstance(x.get("value"), dict) and (x.get("value") or {}).get("beats") is not None})
        return ["narrowed", None, c, v.get("reason")]
    return [v["outcome"], None, None, v.get("reason")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--modes", default="base,thin,full")
    ap.add_argument("--out", required=True)
    ap.add_argument("--control", default=None, help="a mode that must reproduce the record's own verdicts")
    a = ap.parse_args()
    from tools.omr.staged.record_io import load_record
    rec = load_record(a.record)["record"]
    own = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "duration" and v["decider"] == "adjudicate_duration" and v["subject"].startswith("glyph/"):
            own[v["subject"]] = summ(v)
    for mode in a.modes.split(","):
        reasons = {}
        set_mode(mode, reasons)
        log = rebuild(rec)
        adjudicate.run(log)
        got = {}
        for v in log.to_json()["verdicts"]:
            if v["quantity"] == "duration" and v["decider"] == "adjudicate_duration" and v["subject"].startswith("glyph/"):
                got[v["subject"]] = summ(v)
        Path(f"{a.out}-{mode}.json").write_text(json.dumps({"verdicts": got, "reasons": reasons}))
        msg = f"mode {mode}: {len(got)} duration verdicts, {len(reasons)} (head, stroke) ink refusals"
        if a.control == mode:
            bad = [k for k in own if got.get(k) != own[k]]
            msg += f"  | CONTROL vs the record's own verdicts: {len(own) - len(bad)} of {len(own)} reproduced, {len(bad)} differ"
            for k in bad[:5]:
                msg += f"\n     {k}: record {own[k]} vs rebuild {got.get(k)}"
        print(msg, flush=True)


if __name__ == "__main__":
    main()
