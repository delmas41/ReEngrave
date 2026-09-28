"""GATHER ONCE, ADJUDICATE TWICE -- ROADMAP 2.12d's own base-vs-arm.

    python3 benchmarks/omr-shape-role-2026-09/price_2_12d.py <record.json> \
        --label brahms1-breitkopf --out-dir benchmarks/omr-shape-role-2026-09/out/2.12d \
        --control

    python3 .../price_2_12d.py <record.json> --label brahms1-breitkopf \
        --out-dir .../out/2.12d --arm base
    python3 .../price_2_12d.py <record.json> --label brahms1-breitkopf \
        --out-dir .../out/2.12d --arm arm

Modelled on `benchmarks/omr-key-majority-2026-09/readjudicate.py` (2.9c's own
tool): rebuild GATHER once from the saved record's observations+abstentions,
re-run ADJUDICATE -> EVALUATE -> INFER -> EVALUATE (the second pass
`readjudicate.py` itself was once missing, see its own note), then EXPORT.

⚠️ BASE IS "your change disabled by an explicit parameter, NOT a new env
flag" (the roadmap item's own instruction): `--arm base` sets
`rhythm.METER_CHANGE_GATES_OWN_SYSTEM = False` before ADJUDICATE runs, which
is a plain module constant this tree already reads directly
(`test_staged_meter_system_agreement.py` sets it the same way). `--arm arm`
leaves it at its shipped default, `True`.

⚠️ THE RECORD PRE-DATES 2.12d, so BASE reproduces exactly what is already
committed: `--control` rebuilds with the gate OFF and diffs every `Q.METER`
verdict against the record's own -- if that is not N/N identical, every
number below is a measurement of this harness, not of the change.

⚠️ BLIND TO GATHER, like every tool of this shape: a change to what GATHER
files (the METER_GLYPH rows themselves) is invisible here. This item made no
GATHER change (its own ROADMAP line and code comments say so), which is
exactly why this instrument is the right one and no re-gather is needed.

⚠️ READ ONLY where the brief says so. This script never opens its input
record for writing and never writes into the directory a record was read
from -- `--out-dir` is always a path this script creates itself.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate, evaluate, infer            # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged import export as EXPORT                        # noqa: E402
from tools.omr.staged.adjudicators import rhythm as rhythm_mod       # noqa: E402
from tools.omr.staged.record import Log, Subject, meter_at           # noqa: E402
from tools.omr.staged.record_io import load_record                   # noqa: E402

# ⚠️ LOADED BY PATH, NOT IMPORTED -- `rerun.py`'s own rule: a benchmark
# directory's name is not a Python identifier, so `spec_from_file_location`
# is the sanctioned way to reuse another benchmark's script rather than
# coupling `tools/` (or one benchmark) to another benchmark's package layout.
import importlib.util as _ilu
_bsc_path = (ROOT / "benchmarks" / "omr-bar-sum-holdout-2026-09"
             / "probe" / "bar_sum_check.py")
_bsc_spec = _ilu.spec_from_file_location("bar_sum_check", _bsc_path)
_bsc = _ilu.module_from_spec(_bsc_spec)
_bsc_spec.loader.exec_module(_bsc)
bar_sum_check = _bsc.check


def rebuild(rec: dict) -> Log:
    """GATHER, replayed -- verdicts are NOT carried over; the point is to
    re-decide them. Identical shape to `readjudicate.py`'s own `rebuild`."""
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


def run_pipeline(log: Log) -> None:
    """ADJUDICATE -> EVALUATE -> INFER -> EVALUATE, in the order
    `staged/pipeline.py` runs it and `readjudicate.py` replays it."""
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    evaluate.run_over(log, infer.inferred_verdicts(log))


def verdicts_of(log: Log, quantity: str) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == quantity}


def meter_histogram(log: Log) -> collections.Counter:
    """(numerator, denominator) -> how many STAFF-BARS it governs, over every
    staff this record has a bar count for -- the same population unit 2.8's
    `bars_held_out_sum` counts in (page, system, staff, cell).

    ⚠️ READS `Q.METER` AND `Q.MEASURE_PARTITION` DIRECTLY, not the export
    report -- a census over EVERY bar, held out or not, is what "meters in
    force, base -> arm" asks for, and the exporter does not report it as one
    number.
    """
    data = log.to_json()
    meter_by_system: dict = {}
    for v in data["verdicts"]:
        if v["quantity"] != "meter" or v["outcome"] != "decided":
            continue
        meter_by_system[v["subject"]] = v["value"]
    n_cells_by_staff: dict = {}
    for v in data["verdicts"]:
        if v["quantity"] != "measure_partition" or v["outcome"] != "decided":
            continue
        if not isinstance(v["value"], int):
            continue
        n_cells_by_staff[v["subject"]] = v["value"]
    hist: collections.Counter = collections.Counter()
    unassessable = 0
    for staff_key, n_cells in n_cells_by_staff.items():
        parts = staff_key.split("/")            # staff/<page>/<system>/<staff>
        sys_key = "/".join(["system"] + parts[1:3])
        mv = meter_by_system.get(sys_key)
        if mv is None:
            unassessable += n_cells
            continue
        for c in range(n_cells):
            seg = meter_at(mv, c)
            if seg is None or seg.get("numerator") is None:
                unassessable += 1
                continue
            hist[(seg["numerator"], seg["denominator"])] += 1
    hist["UNASSESSABLE"] = unassessable
    return hist


def count_notes(musicxml_path: pathlib.Path) -> int:
    """Pitched `<note>` elements -- independent of the exporter's own
    counters, an `ElementTree` read like `bar_sum_check.py`'s."""
    root = ET.parse(str(musicxml_path)).getroot()
    n = 0
    for note in root.iter("note"):
        if note.find("pitch") is not None:
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--arm", choices=["base", "arm"], default=None)
    a = ap.parse_args()

    out_dir = pathlib.Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"loading {a.record} via record_io.load_record ...", file=sys.stderr)
    data = load_record(a.record)
    rec = data.get("record", data)
    print(f"loaded in {time.time() - t0:.1f}s: "
          f"{len(rec.get('observations') or [])} observations, "
          f"{len(rec.get('verdicts') or [])} verdicts", file=sys.stderr)
    prov = data.get("provenance")
    if prov:
        print(f"record provenance: commit={prov.get('commit')} "
              f"dirty={prov.get('dirty')}", file=sys.stderr)

    if a.control:
        rhythm_mod.METER_CHANGE_GATES_OWN_SYSTEM = False
        t1 = time.time()
        log = rebuild(rec)
        run_pipeline(log)
        print(f"control rebuild+adjudicate in {time.time() - t1:.1f}s",
              file=sys.stderr)
        got = verdicts_of(log, "meter")
        want = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == "meter"}
        same = diff = 0
        kinds: collections.Counter = collections.Counter()
        for key, w in want.items():
            g = got.get(key)
            if g is None:
                diff += 1
                kinds["absent from the rebuild"] += 1
                continue
            if g["outcome"] == w["outcome"] and g.get("value") == w.get("value"):
                same += 1
            else:
                diff += 1
                kinds[f"{w.get('reason')} -> {g.get('reason')}"] += 1
        extra = len(got) - len(want)
        print(f"CONTROL meter (gate OFF, reproduces the pre-2.12d record): "
              f"{same} of {len(want)} reproduced, {diff} differ, "
              f"{extra:+d} extra")
        if kinds:
            print("   differ:", kinds.most_common(10))
        return 0 if (diff == 0 and extra == 0) else 1

    if a.arm is None:
        ap.error("pass --control or --arm base|arm")

    rhythm_mod.METER_CHANGE_GATES_OWN_SYSTEM = (a.arm == "arm")
    print(f"arm={a.arm}  METER_CHANGE_GATES_OWN_SYSTEM="
          f"{rhythm_mod.METER_CHANGE_GATES_OWN_SYSTEM}", file=sys.stderr)

    t1 = time.time()
    log = rebuild(rec)
    run_pipeline(log)
    print(f"rebuild+adjudicate+evaluate+infer in {time.time() - t1:.1f}s",
          file=sys.stderr)

    hist = meter_histogram(log)
    print(f"meters in force (staff-bars): {hist.most_common()}")

    t2 = time.time()
    xml, report = EXPORT.to_musicxml({"record": log.to_json()})
    print(f"export in {time.time() - t2:.1f}s", file=sys.stderr)

    xml_path = out_dir / f"{a.label}-{a.arm}.musicxml"
    xml_path.write_text(xml)
    cov_path = out_dir / f"{a.label}-{a.arm}.coverage.json"
    cov_path.write_text(json.dumps(report, indent=2, default=str))
    hist_path = out_dir / f"{a.label}-{a.arm}.meter_histogram.json"
    hist_path.write_text(json.dumps(
        {"%d/%d" % k if isinstance(k, tuple) else k: v
         for k, v in hist.items()}, indent=2))
    print(f"wrote {xml_path}, {cov_path}, {hist_path}")

    bars_held = report.get("bars_held_out_sum") or {}
    bars_held_summary = {k: v for k, v in bars_held.items() if k != "held"}
    print(f"bars_held_out_sum (summary): {bars_held_summary}")
    print(f"bars_held_out_sum: {len(bars_held.get('held') or [])} bars named "
          f"(full list in the coverage json)")
    n_notes = count_notes(xml_path)
    print(f"pitched <note> count: {n_notes}")

    ctrl = bar_sum_check(str(xml_path))
    print(f"2.8 INDEPENDENT control (exported file, no exporter import): "
          f"assessed={ctrl['assessed']} exact={ctrl['exact']} "
          f"wrong={ctrl['wrong']} unassessable={ctrl['unassessable']}")
    if ctrl["wrong"]:
        print(f"  !! {ctrl['wrong']} exported bars do not sum to their "
              f"meter -- 2.8's own control has FAILED on this arm")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
