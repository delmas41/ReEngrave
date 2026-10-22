"""ONE GATHER, THE THREE AFFECTED QUANTITIES DECIDED TWICE, AND EXPORTED.

⚠️ THREE, NOT ONE. `Q.STEM_DIRECTION` is read by `Q.EVENT`'s divisi guard and
by `Q.VOICES`, both inside ADJUDICATE, so an arm that re-decided only the
stem direction would hold its own consumers at the value they reached WITHOUT
it and report a change of nothing.

⚠️ THE CONTROL RUNS FIRST: with the tier disabled, all three quantities must
come back exactly as the committed record has them. A rebuild that does not
reproduce the record measures the harness.

⚠️ BLIND TO A GATHER CHANGE, like every arm of its kind, and it holds every
OTHER decision at the committed value.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))

import reinfer                                                   # noqa: E402
from tools.omr.staged import adjudicate, export as EX             # noqa: E402
from tools.omr.staged import adjudicators                         # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH            # noqa: E402
from tools.omr.staged.record import Q                             # noqa: E402

REDECIDE = (Q.STEM_DIRECTION, Q.EVENT, Q.VOICES)


def arm(rec, *, enabled: bool):
    log = reinfer.rebuild(rec, skip_verdicts=frozenset(REDECIDE))
    real = RH._direction_from_a_beam_mate
    if not enabled:
        RH._direction_from_a_beam_mate = lambda *a, **k: None
    try:
        adjudicate.run(log, order=REDECIDE)
    finally:
        RH._direction_from_a_beam_mate = real
    return log


def tally(log):
    out = collections.Counter()
    for v in log.to_json()["verdicts"]:
        if v["quantity"] in REDECIDE:
            out[(v["quantity"], v["outcome"], v["reason"])] += 1
    return out


def voices_shape(log):
    n = collections.Counter()
    for v in log.to_json()["verdicts"]:
        if v["quantity"] == Q.VOICES and v["outcome"] == "decided":
            n[int((v["value"] or {}).get("n_voices") or 0)] += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "stem-arm.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")

    committed = {(v["subject"], v["quantity"]): v for v in rec["verdicts"]
                 if v["quantity"] in REDECIDE}

    off = arm(rec, enabled=False)
    got = {(v["subject"], v["quantity"]): v for v in off.to_json()["verdicts"]
           if v["quantity"] in REDECIDE}
    same = sum(1 for k, w in committed.items()
               if k in got and got[k]["outcome"] == w["outcome"]
               and got[k]["reason"] == w["reason"]
               and got[k].get("value") == w.get("value"))
    print(f"CONTROL (tier disabled): {same} of {len(committed)} verdicts "
          f"reproduced exactly across {', '.join(REDECIDE)}")
    if same != len(committed) or len(got) != len(committed):
        print("⚠️ THE REBUILD IS NOT THE RECORD.", file=sys.stderr)
        return 2

    on = arm(rec, enabled=True)
    out = {"control_reproduced": same}
    for name, log in (("off", off), ("on", on)):
        t = tally(log)
        out[name] = {"verdicts": {"/".join(k): n for k, n in t.items()},
                     "voices": {str(k): v for k, v in voices_shape(log).items()}}
        print(f"\n── {name.upper()}")
        for k, n in sorted(t.items()):
            print(f"   {n:6d}  {k[0]:<16} {k[1]:<10} {k[2]}")
        print(f"   voices per bar: {dict(sorted(voices_shape(log).items()))}")

        xml, report = EX.to_musicxml({"record": log.to_json()})
        (HERE / "out" / f"{name}.musicxml").write_text(xml)
        out[name]["file"] = {
            "pitched_notes": xml.count("<pitch>"),
            "backups": xml.count("<backup>"),
            "voice_2": xml.count("<voice>2</voice>"),
            "notes_not_written_total": report.get("notes_not_written_total"),
            "balanced": (report.get("balance") or {}).get("balanced"),
            "divisi_separated": None,
        }
        print(f"   file: {out[name]['file']}")

    print("\n── DELTA")
    for k in out["off"]["file"]:
        x, y = out["off"]["file"][k], out["on"]["file"][k]
        if isinstance(x, int) and isinstance(y, int) and x != y:
            print(f"   {k:<26} {x} -> {y}  ({y - x:+d})")
    Path(a.json).write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
