"""Inspect a movement-boundary gather and report the movement_start cues per
system, plus the exact subjects/bboxes needed for crops.

Regenerate the record this reads with (CLAUDE.md §5b, §5a's worktree
symlinks):

    python3 -m tools.omr.staged \\
        library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \\
        --pages 16-17 --dpi 600 \\
        --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \\
        --route-weights --work-id beethoven--symphony-5 \\
        --out <scratch>/litolff-boundary.record.json --progress

then set RECORD_PATH below to that --out path (run from the repo root, or
adjust the sys.path.insert to point at it).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import record_io
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.record import Kind, Log, Q, Subject

RECORD_PATH = "<scratch>/litolff-boundary.record.json"  # see docstring above


def load_log(result: dict) -> Log:
    log = Log()
    rec = result.get("record") or {}
    for o in rec.get("observations") or ():
        sub = Subject.from_key(o["subject"])
        log.observe(sub, o["quantity"], o["value"], reader=o["reader"],
                    frame=o["frame"], score=o.get("score"),
                    **(o.get("detail") or {}))
    for a in rec.get("abstentions") or ():
        sub = Subject.from_key(a["subject"])
        log.abstain(sub, a["quantity"], reader=a["reader"], frame=a["frame"],
                    reason=a["reason"], **(a.get("detail") or {}))
    return log


def main():
    result = record_io.load_record(RECORD_PATH)
    log = load_log(result)
    log.freeze()

    systems = log.subjects(Kind.SYSTEM)
    print("SYSTEMS:", [s.to_key() for s in systems])

    for sys_sub in systems:
        print(f"\n=== {sys_sub.to_key()} ===")
        staves = sorted({r.subject.to_key() for r in log.rows(
            Q.STAFF_LINES, sys_sub, scope=adjudicate.Scope.SELF_AND_DESCENDANTS)})
        print(f"  staves: {staves}")

        dw = log.rows(Q.DIRECTION_WORD, sys_sub, scope=adjudicate.Scope.SELF_AND_DESCENDANTS)
        for r in dw:
            print(f"  DIRECTION_WORD subj={r.subject.to_key()} cell={r.subject.cell} "
                 f"value={r.value!r} category={r.detail.get('category')} "
                 f"reader={r.reader} bbox={r.detail.get('bbox_page_px')}")

        mg = log.rows(Q.METER_GLYPH, sys_sub, scope=adjudicate.Scope.SELF_AND_DESCENDANTS)
        at0 = [r for r in mg if r.frame == "cell:0"]
        print(f"  METER_GLYPH total={len(mg)} at_cell0={len(at0)}")
        for r in at0[:20]:
            print(f"    staff={r.subject.to_key()} value={r.value} x={r.detail.get('x')} "
                 f"y_center={r.detail.get('y_center')}")

        ml = log.rows(Q.MARGIN_LABEL, sys_sub, scope=adjudicate.Scope.SELF_AND_DESCENDANTS)
        for r in ml:
            print(f"  MARGIN_LABEL staff={r.subject.to_key()} value={r.value!r} "
                 f"reader={r.reader} y_center_px={r.detail.get('y_center_px')}")

        se = log.rows(Q.STAFF_EXTENT, sys_sub, scope=adjudicate.Scope.SELF_AND_DESCENDANTS)
        for r in se:
            if r.subject.staff == 0:
                print(f"  STAFF_EXTENT (top staff) {r.subject.to_key()} value={r.value}")

    print("\n\n=== RUNNING ADJUDICATE movement_start ===")
    verdicts = adjudicate.run(log, order=(Q.MOVEMENT_SPANS,))
    for v in verdicts:
        print(f"outcome={v.outcome} reason={v.reason} value={v.value}")
        print(json.dumps(v.detail, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
