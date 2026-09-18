"""IS THE CONVENTION'S EXCEPTION REALLY THE MULTI-VOICE BAR? Split and see.

Sean states the rule and its exception in one breath: *"very consistent unless
there are multiple voices per staff"*. `probe_position_rule.py` measures the
bare convention at 0.787 against the directions a STEM decided, which is far
below "very consistent" -- so either the exception is doing all of that work,
or the convention is weaker here than the engraving tradition says, or the
reference this is scored against is itself wrong often.

This splits the same population three ways to tell those apart.

⚠️⚠️ `Q.VOICES` IS USED HERE AS A DIAGNOSTIC AND COULD NEVER BE THE GATE. It
is ORDER 22 against `stem_direction`'s 17, and it is DERIVED FROM the stem
directions -- so reading it in production would be both too late and circular.
It is legitimate OFFLINE, on a finished record, purely to ask *where do the
disagreements live*.

⚠️ AND IT IS NOT A TRUTH EITHER. Every figure here is scored against our own
`stem_projection`, so a bar whose stems were misread scores the convention
wrong for a fault that is not the convention's.
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

from tools.omr.staged.record import Kind, Subject              # noqa: E402

MIDDLE_LINE = 4.0


def position_says(pos):
    if pos < MIDDLE_LINE:
        return "down"
    if pos > MIDDLE_LINE:
        return "up"
    return "down"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "voice-split.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    pos_of = {}
    for o in rec["observations"]:
        if o["quantity"] == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    decided = {v["subject"]: v["value"] for v in verdicts
               if v["outcome"] == "decided"}
    disagree = {v["subject"] for v in verdicts if v["reason"] == "stems_disagree"}

    voices = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "voices" and v["outcome"] == "decided":
            voices[v["subject"]] = int((v["value"] or {}).get("n_voices") or 0)

    def cell(k):
        return Subject.from_key(k).at(Kind.CELL).to_key()

    split = collections.defaultdict(collections.Counter)
    for sub, want in decided.items():
        pos = pos_of.get(sub)
        if pos is None:
            continue
        c = cell(sub)
        nv = voices.get(c)
        key = ("bar not split" if nv is None
               else f"{nv}-voice bar")
        split[key]["right" if position_says(pos) == want else "wrong"] += 1

    print("── the convention, by what `Q.VOICES` says about the bar")
    print(f"{'population':<22} {'right':>7} {'wrong':>7} {'accuracy':>9}")
    print("-" * 50)
    out = {}
    for key in sorted(split):
        r, w = split[key]["right"], split[key]["wrong"]
        out[key] = {"right": r, "wrong": w,
                    "accuracy": round(r / max(1, r + w), 4)}
        print(f"{key:<22} {r:>7} {w:>7} {r / max(1, r + w):>9.3f}")

    # ⚠️ A SECOND CUT THAT NEEDS NO VOICE VERDICT AT ALL: a bar holding heads
    # at ONE x with DIFFERENT decided directions is two-voiced by inspection.
    by_cell = collections.defaultdict(list)
    for sub, want in decided.items():
        by_cell[cell(sub)].append((sub, want))
    mixed = {c for c, items in by_cell.items()
             if len({d for _, d in items}) > 1}
    cut = collections.defaultdict(collections.Counter)
    for sub, want in decided.items():
        pos = pos_of.get(sub)
        if pos is None:
            continue
        key = "bar mixes directions" if cell(sub) in mixed else "bar is uniform"
        cut[key]["right" if position_says(pos) == want else "wrong"] += 1
    print("\n── and by whether the bar's own decided directions MIX")
    for key in sorted(cut):
        r, w = cut[key]["right"], cut[key]["wrong"]
        out[key] = {"right": r, "wrong": w,
                    "accuracy": round(r / max(1, r + w), 4)}
        print(f"{key:<22} {r:>7} {w:>7} {r / max(1, r + w):>9.3f}")

    # ⚠️ AND THE CONTROL ON THE REFERENCE ITSELF. `stems_disagree` marks ink
    # this pipeline could not read; if the convention's failures cluster in
    # bars that also hold those, the reference is the suspect and not the
    # rule.
    bad_bars = {cell(s) for s in disagree}
    ctrl = collections.defaultdict(collections.Counter)
    for sub, want in decided.items():
        pos = pos_of.get(sub)
        if pos is None:
            continue
        key = ("bar holds a stems_disagree" if cell(sub) in bad_bars
               else "bar holds none")
        ctrl[key]["right" if position_says(pos) == want else "wrong"] += 1
    print("\n── and by whether the bar holds a head the stems CONTRADICT")
    for key in sorted(ctrl):
        r, w = ctrl[key]["right"], ctrl[key]["wrong"]
        out[key] = {"right": r, "wrong": w,
                    "accuracy": round(r / max(1, r + w), 4)}
        print(f"{key:<22} {r:>7} {w:>7} {r / max(1, r + w):>9.3f}")

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
