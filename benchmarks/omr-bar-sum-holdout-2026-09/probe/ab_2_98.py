"""ROADMAP 2.98 base vs arm on ONE tree, from ONE saved night record.

    python3 .../ab_2_98.py REC.record.json OUTDIR LABEL

REC is a whole-movement night record (it holds its GATHER rows). The record is
rebuilt to its GATHER rows ONCE per decision arm and re-decided with today's
tree (ADJUDICATE..INFER), then exported once per export arm.

  * decision arms:  twin OFF / ON  -- `consequences._whole_rest_ink_twin`
                    (part 2, the second box on the rest's own ink)
  * export arms:    lone OFF / ON  -- `export._lone_whole_rest_is_the_bar`
                    (part 1, a lone whole rest sized by the file's meter)

Four cells: base (off,off), twin only, lone only, both. Per cell: held bars
(the list), `of_bars_with_events`, notes / rests / measure rests in the file,
`bars_add_up` (acceptance's control: short/overfull must not rise), balanced.
Writes OUTDIR/LABEL-<arm>.json (+ .musicxml for base and both).
"""
import gc
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import export as EXPORT  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402
from tools.omr.acceptance import bars_add_up  # noqa: E402

rec_path, out, label = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
# `export-only`: do not re-decide (a 6 GB Brahms record); the saved verdicts
# are exported as they stand, twin arm skipped. Part 1 (EXPORT) is unaffected.
EXPORT_ONLY = len(sys.argv) > 4 and sys.argv[4] == "export-only"
out.mkdir(parents=True, exist_ok=True)
T0 = time.time()


def say(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


doc = load_record(rec_path)
rec = doc["record"]
real_twin = C._whole_rest_ink_twin
real_lone = EXPORT._lone_whole_rest_is_the_bar
fired_twin = []


def counting_twin(log, standing, rest):
    got = real_twin(log, standing, rest)
    if got is not None:
        fired_twin.append(standing.subject.to_key())
    return got


def decide(twin):
    log, _ = rerun.rebuild_gather(rec)
    C._whole_rest_ink_twin = counting_twin if twin else (lambda *a, **k: None)
    fired_twin.clear()
    try:
        rerun.run_stages(log)
    finally:
        C._whole_rest_ink_twin = real_twin
    result = {k: v for k, v in doc.items() if k != "record"}
    result["record"] = log.to_json()
    result["summary"] = log.summary()
    return result, list(fired_twin)


def export(result, lone):
    EXPORT._lone_whole_rest_is_the_bar = (
        real_lone if lone else (lambda *a, **k: None))
    try:
        xml, report = EXPORT.to_musicxml(result)
    finally:
        EXPORT._lone_whole_rest_is_the_bar = real_lone
    return xml, report


summary = {}
for twin in ((False,) if EXPORT_ONLY else (False, True)):
    result, fired = (doc, []) if EXPORT_ONLY else decide(twin)
    say(f"decided twin={twin} twin_fires={len(fired)}")
    for lone in (False, True):
        arm = f"twin{int(twin)}_lone{int(lone)}"
        xml, report = export(result, lone)
        held = (report.get("bars_held_out_sum") or {})
        w = report.get("written") or {}
        add = bars_add_up(xml)
        row = {
            "arm": arm,
            "twin_fires": len(fired),
            "held": held.get("bars"),
            "of_bars_with_events": held.get("of_bars_with_events"),
            "held_on_doubled": held.get("bars_on_a_doubled_staff"),
            "held_list": [(h["page"], h["system"], h["staff"], h["cell"],
                           h["part"], h["measure"])
                          for h in (held.get("held") or [])],
            "notes": w.get("notes"), "rests": w.get("rests"),
            "measure_rests_read": w.get("measure_rests_read"),
            "empty_bars_padded": w.get("empty_bars_padded"),
            "sized_by_file_meter": w.get("measure_rests_sized_by_the_file_meter"),
            "sized_by_carried": w.get("measure_rests_sized_by_a_carried_meter"),
            "bars_add_up": add,
            "balanced": report.get("balanced"),
            "notes_not_written_total": report.get("notes_not_written_total"),
        }
        summary[arm] = row
        (out / f"{label}-{arm}.json").write_text(json.dumps(row, default=str))
        if arm in ("twin0_lone0", "twin1_lone1", "twin0_lone1"):
            (out / f"{label}-{arm}.musicxml").write_text(xml)
        say(f"{arm}: held {row['held']}/{row['of_bars_with_events']} "
            f"notes {row['notes']} rests {row['rests']} "
            f"measure_rests {row['measure_rests_read']} "
            f"sized_by_file {row['sized_by_file_meter']} "
            f"add_up short={add.get('short')} over={add.get('overfull')} "
            f"balanced={row['balanced']}")
        del xml, report
        gc.collect()
    if not EXPORT_ONLY:
        del result
    gc.collect()
(out / f"{label}-summary.json").write_text(json.dumps(summary, default=str))
