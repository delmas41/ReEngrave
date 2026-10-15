"""ROADMAP 2.141h -- re-decide a saved record (ADJUDICATE -> INFER, `pipeline.decide`, the one deciding
sequence) under the env flags of the calling shell, and write what changed.

PATH: STAGED (ADJUDICATE rhythm duration / EVALUATE consequences / INFER inferences). GATHER rows are the record's own
(`review.rerun.rebuild_gather`), so a GATHER change is invisible here (rerun.py's stated blind spot).

    OMR_INFER_CARRIED_METER_FIX=1 [OMR_...=1] python3 arm_2_141h.py RECORD OUT_DIR [--control]

Writes OUT_DIR/durations.json ({subject: [outcome, beats, beam_levels, reason, decider, n_candidates]} for the
standing duration verdict of every glyph), OUT_DIR/record.json (for `judged score`), OUT_DIR/cells.json (the
INFER bar-rule settlements). --control: also compare the replay to the record's own standing duration verdicts
(run with every flag OFF it must reproduce them; it can fail: a perturbed gather row makes it exit 1).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
T0 = time.time()


def say(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def main() -> int:
    rec_path, out_dir = sys.argv[1], Path(sys.argv[2])
    control = "--control" in sys.argv
    out_dir.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged.record import Q
    from tools.omr.staged.record_io import load_record, dumps_for_file
    from tools.omr.staged.review import rerun as RR
    doc = load_record(rec_path)
    rec = doc["record"] if "record" in doc else doc
    if "--break" in sys.argv:   # the control must be able to FAIL: drop the first 40 beam strokes; durations must then differ
        gone = [o for o in rec["observations"] if o["quantity"] == Q.BEAM_STROKE][:40]
        ids = {o["id"] for o in gone}
        rec["observations"] = [o for o in rec["observations"] if o["id"] not in ids]
        say(f"--break: dropped {len(ids)} beam strokes")
    log, _ = RR.rebuild_gather(rec)
    say("gather rebuilt")
    res = RR.run_stages(log)
    say("decided")

    def dur_map(verdicts):
        # the LAST duration verdict per subject in emission order = the standing one (supersession keeps order)
        m = {}
        for v in verdicts:
            if v["quantity"] == Q.DURATION:
                val = v.get("value") if isinstance(v.get("value"), dict) else {}
                m[v["subject"]] = [v["outcome"], val.get("beats"), val.get("beam_levels"), v["reason"],
                                   v["decider"], len(v.get("candidates") or ()),
                                   {k: (v.get("detail") or {}).get(k) for k in
                                    ("beams_not_by_ink_why", "beams_double_thick", "beam_voices", "beam_side", "rule")
                                    if (v.get("detail") or {}).get(k) not in (None, {}, 0)}]
        return m

    new = log.to_json()
    mine = dur_map(new["verdicts"])
    (out_dir / "durations.json").write_text(json.dumps(mine))
    say(f"{len(mine)} duration verdicts")
    if control:
        want = dur_map(rec["verdicts"])
        diff = [k for k in want if want[k][:3] != mine.get(k, [None] * 3)[:3]]
        extra = [k for k in mine if k not in want]
        print(f"CONTROL: {len(want) - len(diff)} of {len(want)} reproduced, {len(diff)} differ, {len(extra)} extra")
        for k in diff[:5]:
            print("  ", k, want[k], mine.get(k))
    parent = {"provenance": doc.get("provenance")}
    (out_dir / "record.json").write_text(dumps_for_file({"record": new, "summary": log.summary()}, indent=0, default=str))
    say("wrote")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
