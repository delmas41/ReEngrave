"""The same three runs as `run_scan.sh`, in ONE process and without the
half-gigabyte intermediates.

    python3 benchmarks/omr-key-majority-2026-09/run_scan_lean.py <record> <tag>

⚠️ WHY IT EXISTS, MEASURED. `readjudicate.py --out` serialises the whole Log,
UNPOOLED: on the Beethoven 5 / Litolff whole-movement record that is a 460 MB
file, written twice and read back twice by the exporter. On the Breitkopf
record the process reached 7 GB resident and the CONTROL alone had not
finished in 38 minutes. This rebuilds the log, adjudicates, and hands the
result STRAIGHT to `export.to_musicxml` in memory, so only the MusicXML and
the coverage census touch the disk — which are the artefacts the FINDINGS
actually cite.

⚠️ IT IS THE SAME ARITHMETIC, NOT A SHORTCUT PAST THE CONTROL. The control
half is identical to `readjudicate.py --control` and runs first; the numbers
it prints are comparable with the Litolff run made the other way, which is the
point of keeping both scripts.
"""
from __future__ import annotations

import argparse
import collections
import gc
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from tools.omr.staged import adjudicate, evaluate, infer          # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged import export as EX                        # noqa: E402
from tools.omr.staged.record_io import load_record               # noqa: E402
from tools.omr.staged.adjudicators import header as H            # noqa: E402

from readjudicate import rebuild, _disable, verdicts_of          # noqa: E402

_LIVE = (H._marker_run, H._concert)


def _restore() -> None:
    H._marker_run, H._concert = _LIVE


def _one(rec: dict, *, off: str | None):
    if off:
        _disable(off)
    else:
        _restore()
    log = rebuild(rec)
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    return log


def _summarise(log, name: str) -> dict:
    keys = verdicts_of(log, "key_signature")
    sysk = verdicts_of(log, "system_key")
    out = {
        "arm": name,
        "outcomes": dict(collections.Counter(v["outcome"] for v in keys.values())),
        "reasons": dict(collections.Counter(v.get("reason") for v in keys.values())),
        "system_key": dict(collections.Counter(v.get("reason")
                                               for v in sysk.values())),
    }
    print(f"-- {name}: {out['outcomes']}")
    print(f"   reasons {out['reasons']}")
    print(f"   system_key {out['system_key']}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("tag")
    a = ap.parse_args()
    out_dir = HERE / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    rec = load_record(a.record)["record"]
    print(f"loaded {a.record} in {time.time() - t0:.0f}s")

    # ── the control ────────────────────────────────────────────────────────
    log = _one(rec, off="all")
    bad = 0
    for quantity in ("clef", "key_signature"):
        got = verdicts_of(log, quantity)
        want = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == quantity}
        same = diff = 0
        moved: collections.Counter = collections.Counter()
        kinds: collections.Counter = collections.Counter()
        for key, w in want.items():
            g = got.get(key)
            if g is None:
                diff += 1
                kinds["absent from the rebuild"] += 1
                continue
            if g["outcome"] == w["outcome"] and g.get("value") == w.get("value"):
                same += 1
                if g.get("reason") != w.get("reason"):
                    moved[f"{w.get('reason')} -> {g.get('reason')}"] += 1
            else:
                diff += 1
                kinds[f"{w.get('value')}({w['outcome']}) -> "
                      f"{g.get('value')}({g['outcome']})"] += 1
        print(f"CONTROL {quantity}: {same} of {len(want)} reproduced "
              f"(outcome+value), {diff} differ, {len(got) - len(want):+d} extra")
        if kinds:
            print("   differ:", kinds.most_common(6))
        if moved:
            print("   reason moved (value unchanged):", moved.most_common(6))
        bad += diff
    report = {"control_clean": bad == 0, "arms": []}

    # ── the base file, straight out of the control's own log ───────────────
    report["arms"].append(_summarise(log, "base"))
    _write(log, out_dir, f"{a.tag}-base")
    del log
    gc.collect()

    # ── the arm ────────────────────────────────────────────────────────────
    log = _one(rec, off=None)
    report["arms"].append(_summarise(log, "arm"))
    _write(log, out_dir, f"{a.tag}-arm")
    (out_dir / f"{a.tag}-lean-report.json").write_text(
        json.dumps(report, indent=1, default=str))
    print(f"total {time.time() - t0:.0f}s")
    return 0


def _write(log, out_dir: pathlib.Path, stem: str) -> None:
    result = {"record": log.to_json()}
    xml, written = EX.to_musicxml(result)
    (out_dir / f"{stem}.musicxml").write_text(xml)
    (out_dir / f"{stem}.coverage.json").write_text(
        json.dumps(EX.coverage(result, written), indent=1, default=str))
    print(f"   wrote {stem}.musicxml")


if __name__ == "__main__":
    raise SystemExit(main())
