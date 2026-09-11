"""ONE gather, ADJUDICATED and EXPORTED twice — before and after the repair.

    python3 benchmarks/omr-staged-dedupe-2026-09/ab_arm.py \
        --record benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json \
        --out-dir benchmarks/omr-staged-dedupe-2026-09/out

⚠️ BOTH HALVES OF THE REPAIR ARE BEHIND ONE PREDICATE, WHICH IS WHY ONE ARM
PRICES BOTH. `adjudicate_dynamic` (ADJUDICATE) and `export._place_notes`
(EXPORT) both read `adjudicate.is_relocated_copy`. A re-EXPORT alone would
price only the notes — the dynamic verdicts are already baked into the saved
record — so this rebuilds the Log and re-runs ADJUDICATE and EVALUATE too, the
`readjudicate.py` move.

⚠️⚠️ ITS BLIND SPOT, STATED BECAUSE A GREEN RESULT HERE HAS ALREADY BEEN ABOUT
TO BE QUOTED FOR SOMETHING IT CANNOT TEST: it rebuilds from a SAVED record, so
a GATHER change never enters. The two gather-side divergences FINDINGS §6 ranks
(`agnostic_nms` / `iou` at the detect call, and `CONTEST_IOU` restating the
legacy 0.3 as 0.5) are STRUCTURALLY INVISIBLE to this arm and are NOT priced by
it. Only two full re-gathers can answer those.

⚠️ THE CONTROL RUNS FIRST AND CAN FAIL. `--control` compares the BASE arm's
verdicts against the ones the pipeline itself wrote; a rebuild that does not
reproduce the record is not a control, and a silent mismatch would make every
number below a measurement of this harness.

⚠️ The base arm is restored IN PROCESS by monkeypatching the one predicate,
not by a checkout of the tree — a checkout would move the adjudicators too and
the delta would stop being attributable to this change alone.

⚠️⚠️ **IT DID NOT PRODUCE THE FIGURES IN FINDINGS §4, AND SAYING SO MATTERS.**
On the four-page Litolff record its BASE arm alone had not finished after 55
minutes of wall clock at 99% CPU, so it was stopped. §4 is measured by the two
SPLIT instruments instead — `export_only_arm.py` (the notes, ~1 minute) and
`dynamics_arm.py` (the dynamics, seconds, with a 1148/1148 control) — each of
which covers exactly what the other is blind to. This file is kept because the
joint measurement is the right instrument on a smaller record, and because both
split arms import their helpers from it. **Do not quote a number from it that
it has not been run to produce.**
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate as A                 # noqa: E402
from tools.omr.staged import adjudicators, consequences      # noqa: E402,F401
from tools.omr.staged import evaluate                        # noqa: E402
from tools.omr.staged import export as sx                    # noqa: E402
from tools.omr.staged.adjudicators import text as TEXT       # noqa: E402
from tools.omr.staged.record import Log, Subject             # noqa: E402


def rebuild(rec):
    """One Log holding exactly the saved record's GATHER rows, in order."""
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


def _patch(relocate):
    """`relocate=True` restores 'honour the owner by MOVING' everywhere."""
    if not relocate:
        return lambda: None
    real = A.is_relocated_copy
    stub = lambda *a, **k: False                              # noqa: E731
    A.is_relocated_copy = stub
    sx.A.is_relocated_copy = stub
    TEXT.is_relocated_copy = stub

    def undo():
        A.is_relocated_copy = real
        sx.A.is_relocated_copy = real
        TEXT.is_relocated_copy = real
    return undo


def run_arm(rec, *, relocate, progress=False):
    undo = _patch(relocate)
    try:
        log = rebuild(rec)
        log.freeze()
        A.run(log, progress=progress)
        evaluate.run(log)
        result = {"record": log.to_json()}
        xml, report = sx.to_musicxml(result)
        return xml, report, result
    finally:
        undo()


def dynamics_histogram(xml):
    out = collections.Counter()
    for d in ET.fromstring(xml).iter("dynamics"):
        for child in d:
            out[child.tag] += 1
    return out


def chord_stats(xml):
    """(chord events, events with a repeated pitch, excess <note> elements)."""
    root = ET.fromstring(xml)
    n_ev = n_rep = excess = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            events, cur = [], []
            for n in meas.findall("note"):
                if n.find("chord") is not None and cur:
                    cur.append(n)
                else:
                    if cur:
                        events.append(cur)
                    cur = [n]
            if cur:
                events.append(cur)
            for ev in events:
                if len(ev) < 2:
                    continue
                n_ev += 1
                ps = []
                for n in ev:
                    p = n.find("pitch")
                    ps.append(None if p is None else
                              (p.findtext("step"), p.findtext("alter"),
                               p.findtext("octave")))
                if len(set(ps)) != len(ps):
                    n_rep += 1
                    excess += len(ps) - len(set(ps))
    return n_ev, n_rep, excess


def counts(xml):
    root = ET.fromstring(xml)
    return {
        "notes_pitched": sum(1 for n in root.iter("note")
                             if n.find("pitch") is not None),
        "rests": sum(1 for n in root.iter("note")
                     if n.find("rest") is not None),
        "slur": len(list(root.iter("slur"))),
        "tied": len(list(root.iter("tied"))),
        "dynamics_elements": len(list(root.iter("dynamics"))),
        "words": len(list(root.iter("words"))),
        "fermata": len(list(root.iter("fermata"))),
        "wedge": len(list(root.iter("wedge"))),
        "articulations": len(list(root.iter("articulations"))),
        "measures": len(list(root.iter("measure"))),
        "parts": len(root.findall("part")),
    }


def control(rec, arm_result):
    """Does the BASE arm reproduce the verdicts the pipeline itself wrote?"""
    saved, rebuilt = {}, {}
    for v in rec["verdicts"]:
        saved[(v["quantity"], v["subject"])] = (v["outcome"],
                                                json.dumps(v["value"],
                                                           sort_keys=True))
    for v in arm_result["record"]["verdicts"]:
        rebuilt[(v["quantity"], v["subject"])] = (v["outcome"],
                                                  json.dumps(v["value"],
                                                             sort_keys=True))
    keys = set(saved) | set(rebuilt)
    agree = sum(1 for k in keys if saved.get(k) == rebuilt.get(k))
    by_q = collections.Counter(k[0] for k in keys if saved.get(k) != rebuilt.get(k))
    return agree, len(keys), by_q


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = json.load(open(args.record))
    rec = result["record"]
    prov = result.get("provenance")
    print(f"record provenance: {prov}")
    if not prov or prov.get("dirty") is not False:
        print("⚠️ the record was gathered on a DIRTY or unstamped tree. Both "
              "arms inherit that equally, so the DELTA stands; the ABSOLUTE "
              "figures carry the caveat.")

    print("\n=== BASE ARM: honour the owner by MOVING (pre-repair) ===")
    base_xml, base_rep, base_res = run_arm(rec, relocate=True,
                                           progress=args.progress)
    agree, total, by_q = control(rec, base_res)
    print(f"\nCONTROL — base arm vs the pipeline's own verdicts: "
          f"{agree} of {total} identical")
    if by_q:
        print("  ⚠️ differing quantities (the rebuild is NOT the pipeline "
              "here; read every number below against this):")
        for k, n in by_q.most_common(12):
            print(f"    {k:<24} {n}")

    print("\n=== FIX ARM: honour the owner by RESOLVING (this change) ===")
    fix_xml, fix_rep, _fix_res = run_arm(rec, relocate=False,
                                         progress=args.progress)

    (out / "base.musicxml").write_text(base_xml)
    (out / "fix.musicxml").write_text(fix_xml)
    (out / "base-coverage.json").write_text(json.dumps(base_rep, indent=1))
    (out / "fix-coverage.json").write_text(json.dumps(fix_rep, indent=1))

    print("\n" + "=" * 68)
    print("SEAN'S TWO SYMPTOMS")
    print("=" * 68)
    b = chord_stats(base_xml)
    f = chord_stats(fix_xml)
    print(f"{'':<36} {'base':>10} {'fix':>10}")
    for label, i in (("chord events (2+ on one stem)", 0),
                     ("... with a REPEATED pitch", 1),
                     ("excess <note> in those chords", 2)):
        print(f"{label:<36} {b[i]:>10} {f[i]:>10}")

    bh, fh = dynamics_histogram(base_xml), dynamics_histogram(fix_xml)
    print("\n<dynamics> children (Sean: the page prints only `ff`):")
    for k in sorted(set(bh) | set(fh), key=lambda k: -(bh[k] + fh[k])):
        print(f"  {k:<8} {bh[k]:>6} {fh[k]:>6}")

    print("\n" + "=" * 68)
    print("EVERYTHING ELSE IN THE FILE")
    print("=" * 68)
    bc, fc = counts(base_xml), counts(fix_xml)
    for k in bc:
        flag = "" if bc[k] == fc[k] else "   <-- moved"
        print(f"  {k:<22} {bc[k]:>8} {fc[k]:>8}{flag}")

    print("\nACCOUNTING CONTROL (an EQUALITY on both arms, or to_musicxml "
          "would have raised):")
    for name, rep in (("base", base_rep), ("fix", fix_rep)):
        bal = rep["balance"]
        print(f"  {name}: balanced={bal['balanced']}  "
              f"in_log={bal['events_in_log']} written={bal['events_written']} "
              f"not_written={bal['events_not_written']}")
    print("\nnotes_not_written, base:", base_rep["notes_not_written"])
    print("notes_not_written, fix :", fix_rep["notes_not_written"])
    for name, rep in (("base", base_rep), ("fix", fix_rep)):
        cen = rep.get("status_census") or {}
        print(f"status_census.unaccounted ({name}): {cen.get('unaccounted')}")

    (out / "ab-summary.json").write_text(json.dumps({
        "provenance": prov,
        "control": {"agree": agree, "total": total, "differing": dict(by_q)},
        "chords": {"base": list(b), "fix": list(f)},
        "dynamics": {"base": dict(bh), "fix": dict(fh)},
        "counts": {"base": bc, "fix": fc},
        "notes_not_written": {"base": base_rep["notes_not_written"],
                              "fix": fix_rep["notes_not_written"]},
    }, indent=1))
    print(f"\nwrote {out}/ab-summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
