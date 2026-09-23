"""REACH FIRST — what is there to infer about, before anything is built.

⚠️⚠️ THIS RUNS BEFORE THE RULE EXISTS AND THAT IS THE POINT. This repository
has burned a session on a clean zero that meant nothing: `rest_dot_arm.py`
moved zero verdicts and its whole dynamic range turned out to be ONE verdict,
so *"the change is inert"* and *"the page holds nothing to move"* were the
same number. Measure the population first, pick the rule the evidence can
speak about, and make the arm exit non-zero when it is dead.

It reads a saved staged record and answers, for the two populations the
exporter holds back:

    duration_narrowed   a duration the reader NARROWED -- "it is one of
                        these" -- which the exporter refuses to argmax
    no_pitch            a notehead with no pitch, because its staff's clef
                        abstained and `restate_pitch` correctly produced none

and then, for each, WHAT SIDEWAYS EVIDENCE EXISTS -- the thing EVALUATE
structurally cannot look at.

    python3 benchmarks/omr-infer-stage-2026-09/probe/reach.py <record.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def load(path: str) -> dict:
    from tools.omr.staged.record_io import load_record
    doc = load_record(path)
    return doc["record"] if "record" in doc else doc


def _sub(key: str) -> dict:
    parts = key.split("/")
    names = ("page", "system", "staff", "cell", "glyph")
    out = {"kind": parts[0]}
    for n, v in zip(names, parts[1:]):
        out[n] = int(v)
    for n in names:
        out.setdefault(n, None)
    return out


def _system_of(key: str) -> str:
    s = _sub(key)
    return f"system/{s['page']}/{s['system']}"


def _cell_of(key: str) -> str:
    s = _sub(key)
    if s["cell"] is None:
        return ""
    return f"cell/{s['page']}/{s['system']}/{s['staff']}/{s['cell']}"


def _bar_of(key: str) -> str:
    """The BAR across the whole system — page, system, cell. Never the staff.

    ⚠️ The sideways question is *"what do the OTHER staves say about this
    stretch of time"*, so the key must drop the staff. And a cell index
    RESTARTS per system, which is the `(page, cell)` defect that made a
    sibling session's bar figures wrong on its first publication, so page and
    system both stay in.
    """
    s = _sub(key)
    if s["cell"] is None:
        return ""
    return f"bar/{s['page']}/{s['system']}/{s['cell']}"


def closure(rows: dict, row_id: str) -> frozenset:
    out, stack = set(), [row_id]
    while stack:
        rid = stack.pop()
        if rid in out:
            continue
        out.add(rid)
        stack.extend(rows.get(rid, ()))
    return frozenset(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", help="write the figures here")
    a = ap.parse_args()

    rec = load(a.record)
    verdicts = rec["verdicts"]
    obs = rec["observations"]

    # basis map over EVERY row, for the independence closure
    basis = {r["id"]: tuple(r.get("basis") or ()) for r in verdicts}
    for r in obs:
        basis[r["id"]] = tuple(r.get("basis") or ())
    for r in rec.get("abstentions", []):
        basis[r["id"]] = ()

    superseded = {v["supersedes"] for v in verdicts if v.get("supersedes")}
    live = [v for v in verdicts if v["id"] not in superseded]

    dur = {}
    for v in live:
        if v["quantity"] == "duration":
            dur[v["subject"]] = v
    pitch = {v["subject"]: v for v in live if v["quantity"] == "pitch"}
    onset = {v["subject"]: v for v in live if v["quantity"] == "onset_column"}
    heads = {o["subject"] for o in obs if o["quantity"] == "notehead_class"}

    out: dict = {"record": a.record}

    # ── POPULATION 1: narrowed durations ────────────────────────────────────
    narrowed = {k: v for k, v in dur.items() if v["outcome"] == "narrowed"}
    decided = {k: v for k, v in dur.items() if v["outcome"] == "decided"}
    abstained = {k: v for k, v in dur.items() if v["outcome"] == "abstained"}
    out["duration"] = {
        "decided": len(decided), "narrowed": len(narrowed),
        "abstained": len(abstained), "total": len(dur),
        "narrowed_on_a_notehead": sum(1 for k in narrowed if k in heads),
        "n_candidates": collections.Counter(
            len(v.get("candidates") or ()) for v in narrowed.values()),
    }

    # ── POPULATION 2: noteheads with no pitch ───────────────────────────────
    no_pitch = [k for k in heads
                if k not in pitch or pitch[k]["outcome"] != "decided"]
    out["pitch"] = {
        "noteheads": len(heads),
        "with_a_decided_pitch": len(heads) - len(no_pitch),
        "no_pitch": len(no_pitch),
        # ⚠️ WHY it has no pitch decides whether anything could infer one.
        "clef_state_of_those_staves": collections.Counter(),
    }
    clef = {v["subject"]: v for v in live if v["quantity"] == "clef"}
    for k in no_pitch:
        s = _sub(k)
        st = f"staff/{s['page']}/{s['system']}/{s['staff']}"
        c = clef.get(st)
        out["pitch"]["clef_state_of_those_staves"][
            c["outcome"] if c else "no_clef_verdict"] += 1

    # ── THE SIDEWAYS EVIDENCE, for the narrowed durations ───────────────────
    #
    # ⚠️ Reported as a FUNNEL, because each step is a different repair. A
    # single "reach" number would hide which of them is the binding one.
    onset_systems = {k for k, v in onset.items() if v["outcome"] == "decided"}
    by_bar_decided: dict = collections.defaultdict(set)
    for k in decided:
        b = _bar_of(k)
        if b:
            by_bar_decided[b].add(_sub(k)["staff"])

    funnel = collections.Counter()
    witness_groups = collections.Counter()
    for k, v in narrowed.items():
        funnel["narrowed"] += 1
        if _system_of(k) not in onset_systems:
            funnel["no_onset_column_on_its_system"] += 1
            continue
        funnel["system_has_onset_columns"] += 1
        bar = _bar_of(k)
        others = by_bar_decided.get(bar, set()) - {_sub(k)["staff"]}
        if not others:
            funnel["no_other_staff_decided_in_this_bar"] += 1
            continue
        funnel["other_staves_decided_in_this_bar"] += 1
        witness_groups[min(len(others), 6)] += 1

    out["sideways_funnel"] = dict(funnel)
    out["other_staves_per_narrowed_bar"] = dict(witness_groups)

    # ── INDEPENDENCE: do two staves' duration verdicts share provenance? ────
    #
    # ⚠️⚠️ THE HAZARD-(b) QUESTION, ASKED OF THE RECORD RATHER THAN ARGUED.
    # If every staff's duration verdict reaches a shared row, then N agreeing
    # staves are ONE witness and the rule is dead before it is written.
    pairs = shared = 0
    for bar, staves in by_bar_decided.items():
        if len(staves) < 2:
            continue
        ids = []
        for k, v in decided.items():
            if _bar_of(k) == bar:
                ids.append(v["id"])
            if len(ids) >= 8:
                break
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pairs += 1
                if closure(basis, ids[i]) & closure(basis, ids[j]):
                    shared += 1
        if pairs > 4000:
            break
    out["independence"] = {
        "duration_verdict_pairs_sampled": pairs,
        "pairs_sharing_a_provenance_row": shared,
        "note": "a pair sharing a row is ONE witness, not two",
    }

    print(json.dumps(out, indent=2, default=str))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, default=str))

    # ⚠️ DEAD-INSTRUMENT CHECK. A probe that reports zero because the document
    # holds nothing must SAY SO rather than read as a clean result.
    if not narrowed:
        print("\n⚠️ DEAD: this record holds NO narrowed durations. Nothing "
              "here can measure a rule about them.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
