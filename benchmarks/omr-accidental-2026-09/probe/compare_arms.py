"""ROADMAP 2.7 — the controls and the arm, off `regather_accidentals.py`'s
outputs. Writes one derived JSON per document.

Three comparisons, each able to fail:

  CONTROL  origin/main re-decided  vs  merged tree with the stage DISABLED
           (`--mode base`, no `Q.ACCIDENTAL_STAFF_POSITION` rows). Must be
           byte-identical MusicXML and N/N standing verdicts: the merge
           changed nothing but what reads the new quantity.
  ARM      merged base  vs  merged arm. Every verdict that differs must be
           an accidental quantity (`accidental_owner` is new; `accidental`
           is superseded where a printed glyph wins); `<note>` count must be
           equal; `<accidental>`/`<alter>` are what moved.
  (break)  `--break-control` perturbs one row by +3 positions and the ARM
           comparison against the unbroken arm must show a difference.

    python3 benchmarks/omr-accidental-2026-09/probe/compare_arms.py \\
        --label litolff --main-dir <..>/acc/main --new-dir <..>/acc/new --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

ACC_Q = {"accidental_owner", "accidental"}


def _load(d, label, mode):
    d = Path(d)
    return (json.loads((d / f"{label}-{mode}-summary.json").read_text()),
            json.loads((d / f"{label}-{mode}-verdicts.json").read_text()),
            (d / f"{label}-{mode}.musicxml").read_text())


def _vdiff(a, b):
    keys = set(a) | set(b)
    diff = [k for k in keys if a.get(k) != b.get(k)]
    by_q = collections.Counter(k.split("|", 1)[1] for k in diff)
    return len(keys), diff, dict(by_q)


def _alter_changes(xa, xb):
    """`<alter>` value transitions, note by note, in document order."""
    def notes(x):
        out = []
        for m in re.finditer(r"<note>.*?</note>", x, re.S):
            n = m.group(0)
            if "<rest" in n:
                out.append(None)
                continue
            al = re.search(r"<alter>(-?\d+)</alter>", n)
            ac = re.search(r"<accidental[^>]*>([^<]+)</accidental>", n)
            out.append((al.group(1) if al else "0", ac.group(1) if ac else None))
        return out
    na, nb = notes(xa), notes(xb)
    if len(na) != len(nb):
        return {"note_count_differs": [len(na), len(nb)]}
    trans = collections.Counter()
    acc = collections.Counter()
    for p, q in zip(na, nb):
        if p is None:
            continue
        if p[0] != q[0]:
            trans[f"{p[0]} -> {q[0]}"] += 1
        if q[1]:
            acc[q[1]] += 1
    return {"alter_transitions": dict(trans), "accidental_elements_by_kind":
            dict(acc), "notes_compared": len(na)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--main-dir", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ms, mv, mx = _load(a.main_dir, a.label, "base")
    bs, bv, bx = _load(a.new_dir, a.label, "base")
    as_, av, ax = _load(a.new_dir, a.label, "arm")

    n, diff, by_q = _vdiff(mv, bv)
    control = {
        "musicxml_identical": mx == bx,
        "musicxml_md5": [ms["musicxml_md5"], bs["musicxml_md5"]],
        "standing_verdicts": n, "verdicts_identical": n - len(diff),
        "differing_by_quantity": by_q,
        "PASS": mx == bx and not diff,
    }
    n2, diff2, by_q2 = _vdiff(bv, av)
    non_acc = {q: c for q, c in by_q2.items() if q not in ACC_Q}
    arm = {
        "standing_verdicts": [len(bv), len(av)],
        "differing_by_quantity": by_q2,
        "differing_outside_accidental_quantities": non_acc,
        "notes_in_file": [bs["notes_in_file"], as_["notes_in_file"]],
        "accidental_elements": [bs["accidental_elements"],
                                as_["accidental_elements"]],
        "alter_elements": [bs["alter_elements"], as_["alter_elements"]],
        **_alter_changes(bx, ax),
        "status_census_balanced": [
            (bs.get("status_census") or {}).get("balanced"),
            (as_.get("status_census") or {}).get("balanced")],
        "status_census_unaccounted": [
            (bs.get("status_census") or {}).get("unaccounted"),
            (as_.get("status_census") or {}).get("unaccounted")],
        "notes_not_written": [bs.get("notes_not_written"),
                              as_.get("notes_not_written")],
        "accidental_reading": as_.get("accidental_reading"),
        "recompute": as_.get("recompute"),
        "decide_seconds": [ms.get("decide_seconds"), bs.get("decide_seconds"),
                           as_.get("decide_seconds")],
    }
    out = {"label": a.label, "record": as_["record"],
           "record_md5": as_["record_md5"], "CONTROL": control, "ARM": arm}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
