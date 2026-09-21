"""The SHIPPED decision, re-adjudicated — and the control is that NO KEY MOVED.

`adjudicate_key_signature` now reads `Q.KEYSIG_MARKER`, which it has declared
in `wants` AND `composed_from` since it was written and read nowhere. The
change is a REASON split and nothing else: where the run reader could not
speak but the detector saw key accidentals, the abstention says
`markers_without_a_run` instead of `no_evidence`.

⚠️ SO THE CONTROL IS SHARPER THAN "nothing moved". Something IS meant to move
— some abstention reasons — and the thing that must NOT move is any DECIDED
key. An arm that only checked for global identity would pass a change that had
quietly started counting markers, which is the rule this repair exists NOT to
be (`_marker_ink`'s docstring: the legacy count-the-markers fallback cost
seven spurious key flips). So:

  * every DECIDED verdict: same value, same reason, on every staff — asserted;
  * abstentions: only `no_evidence -> markers_without_a_run` is permitted, and
    any other movement fails the arm;
  * and a POSITIVE control — the split must actually have happened somewhere,
    or "no decided key moved" is also what a change that never ran looks like.

⚠️ AN ADJUDICATE CHANGE, so `readjudicate`'s isolation is the right instrument
and not a blind one: `Q.KEYSIG_MARKER` rows are GATHER rows a saved record
already carries. It would be blind to a GATHER change and this is not one.

⚠️ IT ALSO CHECKS THE PROBE'S RESTATED CONSTANT. `probe_records.py`
deliberately does not import the tree; this imports `gather._KEYSIG_CLASSES`
and compares, so a drift between them is caught rather than silently making
the two instruments measure different populations.

    python3 check_arm.py <record.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.gather import _KEYSIG_CLASSES              # noqa: E402
from tools.omr.staged.record import Log, Subject                 # noqa: E402

HERE = Path(__file__).resolve().parent
PERMITTED = ("no_evidence", "markers_without_a_run")


def rebuild(rec: dict) -> Log:
    """Lifted unchanged from `omr-staged-duration-beams-2026-09`."""
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


def _keys(verdicts):
    return {v["subject"]: v for v in verdicts
            if v["quantity"] == "key_signature"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()

    # ── the probe's restated constant, checked against the tree ────────────
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_probe", HERE / "probe_records.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    if tuple(probe.KEYSIG_CLASSES) != tuple(_KEYSIG_CLASSES):
        print(f"REFUSED: the probe restates {probe.KEYSIG_CLASSES} and the "
              f"tree declares {_KEYSIG_CLASSES} — the two instruments would "
              f"be measuring different populations")
        return 3
    print(f"CLASSES  probe and tree agree: {_KEYSIG_CLASSES}")

    rec = json.load(open(a.record))["record"]
    was = _keys(rec["verdicts"])
    if not was:
        print("DEAD: the record holds no key_signature verdict")
        return 2

    log = rebuild(rec)
    adjudicate.run(log)
    now = _keys(log.to_json()["verdicts"])

    print(f"RECORD   {Path(a.record).name}")
    print(f"REACH    {len(was)} key verdicts in the record, {len(now)} rebuilt")

    # ── CONTROL 1: no DECIDED key moved ───────────────────────────────────
    moved, missing = [], []
    for subj, w in was.items():
        g = now.get(subj)
        if g is None:
            missing.append(subj)
            continue
        if w["outcome"] != "decided":
            continue
        if g["outcome"] != "decided" or g.get("value") != w.get("value") \
                or g["reason"] != w["reason"]:
            moved.append((subj, w.get("value"), w["reason"],
                          g.get("value"), g["reason"]))
    n_decided = sum(1 for w in was.values() if w["outcome"] == "decided")
    print(f"CONTROL  decided keys: {n_decided}; MOVED {len(moved)}; "
          f"absent from the rebuild {len(missing)}")
    for row in moved[:10]:
        print(f"   ⚠️ {row[0]}: {row[1]}/{row[2]} -> {row[3]}/{row[4]}")

    # ── CONTROL 2: only the permitted abstention split ────────────────────
    split, illegal = collections.Counter(), []
    for subj, w in was.items():
        g = now.get(subj)
        if g is None or w["outcome"] == "decided":
            continue
        if g["reason"] == w["reason"]:
            continue
        if w["reason"] in PERMITTED and g["reason"] in PERMITTED:
            split[f"{w['reason']} -> {g['reason']}"] += 1
        else:
            illegal.append((subj, w["reason"], g["reason"]))
    print(f"SPLIT    {dict(split)}")
    for subj, a_, b_ in illegal[:10]:
        print(f"   ⚠️ ILLEGAL abstention move {subj}: {a_} -> {b_}")

    # ── CONTROL 3 (POSITIVE): the split must have happened ────────────────
    n_split = sum(split.values())
    if n_split == 0:
        print("DEAD: no abstention split at all — 'no decided key moved' is "
              "also exactly what a change that never ran looks like")

    # what the new detail says, read back off the rebuilt verdicts
    ink = collections.Counter()
    for g in now.values():
        d = g.get("detail") or {}
        if "keysig_marker_ink" in d:
            ink["carries the detail"] += 1
            if d["keysig_marker_ink"]:
                ink["and ink was there"] += 1
    print(f"DETAIL   {dict(ink)}")

    if a.tag:
        out = HERE / "out" / f"{a.tag}.json"
        out.write_text(json.dumps(
            {"record": Path(a.record).name, "decided": n_decided,
             "decided_moved": len(moved), "absent": len(missing),
             "abstention_split": dict(split), "illegal_moves": illegal,
             "detail": dict(ink)}, indent=1, default=str))
        print(f"wrote {out}")

    ok = not moved and not missing and not illegal and n_split > 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
