"""ROADMAP 2.7b — base (a5f7cf58) vs arm (the 2.7b tree), off
`regather_accidentals.py`'s outputs, every changed verdict ATTRIBUTED.

  CONTROL  base vs base re-run (`--control-dir`): must be N/N identical
           standing verdicts and byte-identical MusicXML, or nothing below is
           a difference between trees.
  ARM      every `notehead_is_not_a_notehead` verdict that changed must have
           changed TO `belongs_to_a_nearer_staff`; every `accidental_owner`
           that changed must be `is_a_key_signature_marker` or
           `head_belongs_to_a_nearer_staff`; every OTHER changed verdict is
           listed by quantity and tested for whether its subject is a newly
           refused head (or lies in a bar that holds one) — anything outside
           that is `unexplained`, and must be 0.

    python3 benchmarks/omr-accidental-2026-09/probe/compare_2_7b.py \\
        --label litolff --base-dir <base> --arm-dir <arm> \\
        [--control-dir <base2>] --out <json>
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


def _load(d, label, mode="arm"):
    d = Path(d)
    return (json.loads((d / f"{label}-{mode}-summary.json").read_text()),
            json.loads((d / f"{label}-{mode}-verdicts.json").read_text()),
            (d / f"{label}-{mode}.musicxml").read_text())


def _count_page(xml, page_first_bar, page_last_bar):
    """<note>/<accidental> inside a bar-number window, per part."""
    notes = acc = 0
    for m in re.finditer(r'<measure number="(\d+)"[^>]*>(.*?)</measure>',
                         xml, re.S):
        n = int(m.group(1))
        if page_first_bar <= n <= page_last_bar:
            notes += m.group(2).count("<note")
            acc += m.group(2).count("<accidental")
    return notes, acc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--base-dir", required=True)
    ap.add_argument("--arm-dir", required=True)
    ap.add_argument("--control-dir")
    ap.add_argument("--mode", default="arm",
                    help="the harness mode both sides were run in")
    ap.add_argument("--bars", default=None,
                    help="first-last bar of the count page, e.g. 49-82")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    bs, bv, bx = _load(a.base_dir, a.label, a.mode)
    as_, av, ax = _load(a.arm_dir, a.label, a.mode)
    out = {"label": a.label}
    if a.control_dir:
        cs, cv, cx = _load(a.control_dir, a.label, a.mode)
        diff = [k for k in set(bv) | set(cv) if bv.get(k) != cv.get(k)]
        out["control"] = {
            "standing_verdicts": [len(bv), len(cv)],
            "differing": len(diff),
            "musicxml_identical": hashlib.md5(bx.encode()).hexdigest()
            == hashlib.md5(cx.encode()).hexdigest()}

    keys = set(bv) | set(av)
    diff = sorted(k for k in keys if bv.get(k) != av.get(k))
    by_q = collections.Counter(k.split("|", 1)[1] for k in diff)
    refused = set()
    npv_bad = []
    for k in diff:
        sub, q = k.split("|", 1)
        if q != "notehead_is_not_a_notehead":
            continue
        new = json.loads(av[k]) if k in av else None
        if new and new[1] is True and new[2] == "belongs_to_a_nearer_staff":
            refused.add(sub)
        else:
            npv_bad.append([k, bv.get(k), av.get(k)])
    acc_reasons = collections.Counter()
    acc_bad = []
    for k in diff:
        sub, q = k.split("|", 1)
        if q != "accidental_owner":
            continue
        new = json.loads(av[k]) if k in av else None
        r = new[2] if new else None
        acc_reasons[r] += 1
        if r not in ("is_a_key_signature_marker",
                     "head_belongs_to_a_nearer_staff"):
            acc_bad.append([k, bv.get(k), av.get(k)])
    bars = {"/".join(s.split("/")[1:5]) for s in refused}
    heads_of_bar = collections.Counter()
    other = collections.Counter()
    unexplained = []
    for k in diff:
        sub, q = k.split("|", 1)
        if q in ("notehead_is_not_a_notehead", "accidental_owner"):
            continue
        parts = sub.split("/")
        if sub in refused:
            other[f"{q} (on a refused head)"] += 1
        elif len(parts) >= 5 and "/".join(parts[1:5]) in bars:
            other[f"{q} (same bar as a refused head)"] += 1
        elif q in ("accidental",):
            other[f"{q} (carry/respell)"] += 1
        else:
            unexplained.append([k, bv.get(k), av.get(k)])
    out.update({
        "standing_verdicts": [len(bv), len(av)],
        "differing": len(diff),
        "differing_by_quantity": dict(by_q),
        "refused_belongs_to_a_nearer_staff": len(refused),
        "npv_changes_not_to_the_new_reason": npv_bad,
        "accidental_owner_changes_by_new_reason": dict(acc_reasons),
        "accidental_owner_changes_unexpected": acc_bad[:20],
        "other_changes_attributed": dict(other),
        "unexplained": len(unexplained),
        "unexplained_sample": unexplained[:20],
        "notes_in_file": [bs["notes_in_file"], as_["notes_in_file"]],
        "accidental_elements": [bs["accidental_elements"],
                                as_["accidental_elements"]],
        "alter_elements": [bs["alter_elements"], as_["alter_elements"]],
        "notes_not_written_new_reason": (as_.get("notes_not_written") or {})
        .get("not_a_notehead:belongs_to_a_nearer_staff"),
        "accidental_census": {k: [(bs.get("accidental_reading") or {}).get(k),
                                  (as_.get("accidental_reading") or {}).get(k)]
                              for k in ("gathered", "owner_decided", "applied",
                                        "no_candidate", "is_a_key_signature_marker",
                                        "head_belongs_to_a_nearer_staff",
                                        "heads_balanced", "unaccounted")},
        "status_census_unaccounted": [
            ((bs.get("status_census") or {}).get("unaccounted")),
            ((as_.get("status_census") or {}).get("unaccounted"))],
        "refused_heads": sorted(refused),
    })
    if a.bars:
        f, l = (int(x) for x in a.bars.split("-"))
        out["count_page_bars"] = [f, l]
        out["count_page_notes"] = [_count_page(bx, f, l)[0],
                                   _count_page(ax, f, l)[0]]
        out["count_page_accidentals"] = [_count_page(bx, f, l)[1],
                                         _count_page(ax, f, l)[1]]
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in (
        "refused_heads", "unexplained_sample")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
