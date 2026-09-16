#!/usr/bin/env python3
"""TWO FULL RE-GATHERS — the only thing that can price a GATHER change.

⚠️⚠️ THIS CANNOT RUN IN A CLOUD CONTAINER AND IS NOT MEANT TO. It needs
`omr-weights/` and a PDF from `library/`, both gitignored, so it is written to
be handed to a machine that has them. Everything else in this benchmark
directory ran without weights and measures the READER; this measures the
PIPELINE, and nothing else can.

⚠️ WHY NOT `readjudicate.py` OR `reexport_arm.py`. CLAUDE.md is explicit and
both blind spots are structural: `readjudicate` rebuilds ADJUDICATE from a
SAVED record, so a quantity the gather did not write can never enter it — it
would report 0 moved and pass its own control at 100%, which is the
*"control that was never testing what its name says"* family. `reexport_arm`
has the mirror blind spot. **Only two full re-gathers answer a GATHER
question.**

WHAT IT DOES. One document, gathered twice — `OMR_METER_TEMPLATE_AT_BAR` off
then on — and compared on the meter verdicts: the per-system opening, the
`segments`, and which staves carried each change. The OFF arm must be
byte-identical to a plain run (there is no third arm: the flag off writes no
rows at all, so the OFF arm IS a plain run).

    python3 benchmarks/omr-meter-template-changes-2026-09/local_arm.py \\
        --pdf  "$HOME/Desktop/ReEngrave/library/editions/brahms/symphony-1/brahms--symphony-1--breitkopf--imslp317803.pdf" \\
        --weights "$HOME/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt" \\
        --pages 0-3 --out-dir /tmp/meter-at-bar

⚠️ BREITKOPF BRAHMS 1 p0-3 IS THE FIXTURE TO USE, and the reason is the
standing objection to the whole meter family: CLAUDE.md records that on that
scan the meter GLYPHS are misread badly enough that the weighing never gets a
fair candidate — `9/8` voted as `9/4`, the real change at m8 missed, and FIVE
spurious `4/4` changes just over `METER_CHANGE_FLOOR`. That is precisely the
document a better READER is supposed to help, so it is where the change is
worth something or is worth nothing.

⚠️ WHAT TO LOOK FOR, in order:
  1. **REACH.** How many candidate columns, how many windows asked, how many
     ANSWERED. A zero here means the arm is dead and nothing below it counts.
  2. **The `9/8` at m8.** Does a consensus of three or more staves read it at
     the right bar? That is the one true change this document prints on these
     pages.
  3. **The five spurious `4/4`.** Do they gain template staves — which would
     make them WORSE — or does the reader refuse those bars?
  4. **Every other system's opening.** It must not move: this pass files a
     SEPARATE quantity precisely so the opening vote cannot see it.

⚠️ RUN THE GATHER WITHOUT `--musicxml`. CLAUDE.md, measured the hard way:
`staged/__main__.py` imports the EXPORTER after the gather, so an edit made
during a long run reaches it and kills a finished gather on a NameError.
This arm exports nothing for that reason.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV_FLAG = "OMR_METER_TEMPLATE_AT_BAR"


def _gather(pdf, weights, pages, out, enabled, extra_env=None) -> float:
    env = dict(os.environ)
    env.pop(ENV_FLAG, None)
    if enabled:
        env[ENV_FLAG] = "1"
    env.update(extra_env or {})
    cmd = [sys.executable, "-m", "tools.omr.staged", str(pdf),
           "--pages", pages, "--weights", str(weights), "--out", str(out)]
    print(f"\n$ {ENV_FLAG}={'1' if enabled else '(unset)'} "
          + " ".join(cmd), flush=True)
    t0 = time.time()
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
    return time.time() - t0


def _record(record_path: pathlib.Path) -> dict:
    """`result["record"]` — `{observations, abstentions, verdicts}`.

    ⚠️ REFUSES rather than defaulting to an empty record. A parser that
    returns `{}` for an unrecognised file reports "nothing moved" for a run
    that never happened — the fallback that converts *cannot tell* into a
    definite answer.
    """
    doc = json.loads(record_path.read_text())
    rec = doc.get("record")
    if not isinstance(rec, dict) or "verdicts" not in rec:
        raise SystemExit(
            f"{record_path} is not a staged record (no `record.verdicts`). "
            f"Refusing rather than reporting an empty comparison.")
    return rec


def _meters(record_path: pathlib.Path) -> dict:
    """`{system_key: verdict}` for `Q.METER`."""
    return {v.get("subject"): v for v in _record(record_path)["verdicts"]
            if v.get("quantity") == "meter"}


def _bar_head_rows(record_path: pathlib.Path) -> list:
    """Observations AND abstentions — the flag-off claim is about both."""
    rec = _record(record_path)
    return [r for r in (rec.get("observations") or [])
            + (rec.get("abstentions") or [])
            if r.get("quantity") == "meter_template_at_bar"]


def _segments(verdict) -> list:
    return ((verdict or {}).get("value") or {}).get("segments") or []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--pages", default="0-3")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--skip-gather", action="store_true",
                    help="re-read records a previous run already wrote")
    args = ap.parse_args(argv)

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    off = out_dir / "arm-off.staged.json"
    on = out_dir / "arm-on.staged.json"

    if not args.skip_gather:
        t_off = _gather(args.pdf, args.weights, args.pages, off, False)
        t_on = _gather(args.pdf, args.weights, args.pages, on, True)
        print(f"\ngather wall clock: OFF {t_off:.0f}s, ON {t_on:.0f}s "
              f"(+{t_on - t_off:+.0f}s)")

    # ── 1. REACH, before anything else ──────────────────────────────────────
    rows_off = _bar_head_rows(off)
    rows_on = _bar_head_rows(on)
    answered = [r for r in rows_on if "value" in r]
    print("\n── REACH ──")
    print(f"  OFF arm `meter_template_at_bar` rows : {len(rows_off)}"
          "   (must be 0 — the flag writes nothing)")
    print(f"  ON  arm rows asked                   : {len(rows_on)}")
    print(f"  ON  arm rows ANSWERED                : {len(answered)}")
    if rows_off:
        print("  ⚠️ THE OFF ARM IS NOT CLEAN — flag-off must write nothing.")
    if not rows_on:
        print("\nDEAD: the ON arm asked nothing. Either the page carries no "
              "meter-shaped ink off the opening bar, or the flag did not "
              "reach the run. Nothing below this line means anything.",
              file=sys.stderr)
        return 2

    by_bar: dict = {}
    for row in answered:
        cell = (row.get("detail") or {}).get("cell")
        raw = (row.get("detail") or {}).get("raw")
        by_bar.setdefault((row.get("subject", "").rsplit("/", 1)[0], cell),
                          {}).setdefault(raw, 0)
        by_bar[(row.get("subject", "").rsplit("/", 1)[0], cell)][raw] += 1
    print("\n  answered bar heads, by (staff-run, bar) and printed form:")
    for key, forms in sorted(by_bar.items(), key=lambda kv: str(kv[0])):
        print(f"    {key}: {forms}")

    # ── 2. the meter verdicts, side by side ─────────────────────────────────
    m_off, m_on = _meters(off), _meters(on)
    print("\n── THE METER, PER SYSTEM ──")
    print(f"{'system':<18} {'OFF opening':<14} {'ON opening':<14} "
          f"{'OFF segments':<34} {'ON segments'}")
    moved = 0
    opening_moved = 0
    for key in sorted(set(m_off) | set(m_on)):
        a, b = m_off.get(key), m_on.get(key)

        def _open(v):
            val = (v or {}).get("value") or {}
            return f"{val.get('raw', '-')}({(v or {}).get('reason', '-')})"

        def _segs(v):
            return " ".join(f"{s.get('from_cell')}:{s.get('raw')}"
                            + (f"[+{s['staves_from_bar_head_template']}t]"
                               if s.get("staves_from_bar_head_template")
                               else "")
                            for s in _segments(v)) or "-"

        sa, sb = _segs(a), _segs(b)
        if sa != sb:
            moved += 1
        if _open(a) != _open(b):
            opening_moved += 1
        mark = "  <<<" if sa != sb else ""
        print(f"{key:<18} {_open(a):<14} {_open(b):<14} {sa:<34} {sb}{mark}")

    print(f"\n  systems whose SEGMENTS moved : {moved}")
    print(f"  systems whose OPENING moved  : {opening_moved}"
          "   (should be 0 — a separate quantity is why)")
    if opening_moved:
        print("  ⚠️ AN OPENING MOVED. That is the failure this quantity is "
              "separate to prevent; read `adjudicate_meter`'s row query.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
