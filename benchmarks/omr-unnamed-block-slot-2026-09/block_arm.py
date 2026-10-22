"""ONE GATHER, SLOT_INDEX DECIDED THREE WAYS — and scored against the PRINT.

The arm for `adjudicate_slot_index`'s family-block branch and the INFER rule
that finishes it. Three arms over one saved record, so nothing here carries
detector jitter:

    OFF    the branch disabled, reproducing the committed record exactly.
           ⚠️ THIS IS THE CONTROL AND IT RUNS FIRST. A re-adjudication that
           does not reproduce the verdicts the pipeline wrote is measuring
           the harness, and every number after it would be meaningless.
    ON     the branch live: a block that fills the reference's trailing
           family run is DECIDED, one that falls a slot short is NARROWED.
    INFER  + `collapse_slot_index_to_family_block`, which applies the
           condensed-at-the-foot convention to the narrowings.

⚠️ THE TRUTH IS THE PRINT. `printed-lineups.json` is a human reading the
plate, keyed on `(page, system)` exactly as the record's subjects are, so the
join needs no geometry and cannot suffer the page-pixel frame error that has
bitten three probes in this repository. Our own reading is never the truth
here, which is what makes a GRAFT visible at all.

⚠️ WHAT THIS IS BLIND TO. It isolates ADJUDICATE (and then INFER) over a
FIXED gather, so it cannot see a GATHER change -- and it holds every OTHER
decision at the value the committed run reached, `part_partition` included.
So it measures the slot rule and says nothing about what the exporter would
then do with a changed join. That is a separate arm and is not claimed here.
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
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))

import reinfer                                                   # noqa: E402
from tools.omr.staged import adjudicate, evaluate, infer          # noqa: E402
from tools.omr.staged import adjudicators, inferences             # noqa: E402,F401
from tools.omr.staged.adjudicators import identity                # noqa: E402
from tools.omr.staged.record import Q, Subject                    # noqa: E402

#: The hand-read print truth for the LITOLFF BEETHOVEN 5 pages, and for
#: nothing else.
#:
#: ⚠️⚠️ IT IS KEYED ON `(page, system)` AND SO IS EVERY OTHER RECORD, WHICH IS
#: A COLLISION AND NOT A JOIN. The first run of this arm scored a BREITKOPF
#: BRAHMS record against these rows and reported **21 grafts** -- one document's
#: staves read against another document's lineup, in exactly the id-space
#: collision `--work-id` already costs this project on the scan gate. Scoring
#: is therefore OPT-IN per record (`--truth`), and an arm with none reports
#: REACH and refuses to classify anything.
LITOLFF_LINEUPS = ROOT / "benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json"

#: Printed name -> the reference slot NAME our own opening system reads for it.
#: ⚠️ THIS IS A SPELLING BRIDGE AND NOTHING ELSE. The plate prints `Violino I`
#: and our lexicon resolves it to `Violin`; scoring one against the other
#: without saying so would charge every correct placement as a graft. It maps
#: PRINT -> OUR VOCABULARY, never the other way, so it cannot turn a wrong
#: reading into a right one: a staff placed on a slot whose printed name is
#: not in this row's list is a graft whatever we call it.
EQUIV = {
    "Violino I": {"Violin"}, "Violino II": {"Violin"},
    "Viola": {"Viola"}, "Violoncello": {"Cello"},
    "Basso": {"Contrabass"},
    # ⚠️ A CONDENSED STAFF IS *BOTH*, and that is a third class rather than a
    # right or a wrong answer. `Violoncello e Basso` is one printed staff
    # carrying two reference parts, so placing it on either is defensible and
    # placing it on neither is not.
    "Violoncello e Basso": {"Cello", "Contrabass"},
}


def printed_lineups(path):
    if path is None:
        return None
    raw = json.loads(Path(path).read_text())
    return {(r["page"], r["system"]): r["lineup"] for r in raw["systems"]}


def classify(printed, ref_name):
    """`ok` / `condensation` / `graft` / `unknown_print`."""
    if printed is None:
        return "unknown_print"
    want = EQUIV.get(printed)
    if want is None:
        return "unknown_print"
    if ref_name in want:
        return "condensation" if len(want) > 1 else "ok"
    return "graft"


def slot_rows(log, lineups, ref_names):
    """Every STAFF's current slot verdict, scored against the print."""
    out = []
    for v in log.to_json()["verdicts"]:
        if v["quantity"] != Q.SLOT_INDEX:
            continue
        sub = Subject.from_key(v["subject"])
        cur = log.verdict(Q.SLOT_INDEX, sub)
        if cur is None or cur.id != v["id"]:
            continue                      # superseded; the current one wins
        lineup = ((lineups or {}).get((sub.page, sub.system)) or [])
        printed = lineup[sub.staff] if sub.staff < len(lineup) else None
        slot = v.get("value")
        ref_name = ref_names[slot] if isinstance(slot, int) \
            and slot < len(ref_names) else None
        out.append({
            "subject": v["subject"], "printed": printed,
            "outcome": v["outcome"], "reason": v["reason"], "slot": slot,
            "ref_name": ref_name,
            "candidates": [c["value"] for c in (v.get("candidates") or ())],
            "inferred": bool((v.get("detail") or {}).get("inferred")),
            # ⚠️ `None` WHERE THERE IS NO TRUTH, never a default class. A
            # record with no hand-read lineup is UNSCORED, which is a
            # different fact from scoring clean, and the tallies below keep
            # them apart.
            "class": (classify(printed, ref_name)
                      if lineups is not None and isinstance(slot, int)
                      else None),
        })
    return out


def reference_names(log):
    """Our own names on the widest system -- the reference `slot_index` uses."""
    by_sys = collections.defaultdict(dict)
    for v in log.to_json()["verdicts"]:
        if v["quantity"] != Q.INSTRUMENT or not isinstance(v.get("value"), dict):
            continue
        sub = Subject.from_key(v["subject"])
        by_sys[(sub.page, sub.system)][sub.staff] = v["value"].get("name")
    if not by_sys:
        return []
    key = max(by_sys, key=lambda k: (len(by_sys[k]), -k[0], -k[1]))
    row = by_sys[key]
    return [row.get(i) for i in range(max(row) + 1)]


def tally(rows):
    t = collections.Counter()
    for r in rows:
        if r["outcome"] == "decided":
            t[("decided", r["class"])] += 1
        else:
            t[(r["outcome"], r["reason"])] += 1
    return t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "block-arm.json"))
    ap.add_argument("--truth", default=None,
                    help="the hand-read printed lineup for THIS record; "
                         "without it the arm reports reach and scores nothing")
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")
    lineups = printed_lineups(a.truth)
    if lineups is None:
        print("⚠️ NO --truth: this arm will report REACH and will not "
              "classify a single placement. A record scored against another "
              "document's lineup reports grafts that are the instrument's.",
              file=sys.stderr)

    committed = {v["subject"]: v for v in rec["verdicts"]
                 if v["quantity"] == Q.SLOT_INDEX}
    print(f"\ncommitted record: {len(committed)} slot_index verdicts, "
          f"{collections.Counter(v['outcome'] for v in committed.values())}")

    # ── CONTROL ─────────────────────────────────────────────────────────────
    off = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    real = identity._place_in_family_block
    identity._place_in_family_block = lambda *args, **kw: None
    try:
        adjudicate.run(off, order=(Q.SLOT_INDEX,))
    finally:
        identity._place_in_family_block = real
    got = {v["subject"]: v for v in off.to_json()["verdicts"]
           if v["quantity"] == Q.SLOT_INDEX}
    same = sum(1 for k, w in committed.items()
               if k in got and got[k]["outcome"] == w["outcome"]
               and got[k].get("value") == w.get("value")
               and got[k]["reason"] == w["reason"])
    print(f"CONTROL (branch disabled): {same} of {len(committed)} slot_index "
          f"verdicts reproduced exactly")
    if same != len(committed) or len(got) != len(committed):
        print("⚠️ THE REBUILD IS NOT THE RECORD — every number below would be "
              "a measurement of the harness.", file=sys.stderr)
        return 2

    ref_names = reference_names(off)
    print(f"reference lineup: {ref_names}")

    # ── ARM: the branch on ──────────────────────────────────────────────────
    on = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    adjudicate.run(on, order=(Q.SLOT_INDEX,))
    rows_on = slot_rows(on, lineups, ref_names)

    # ── ARM: + INFER ────────────────────────────────────────────────────────
    report = infer.run(on, evaluate.Report(fired=[], skipped=[], stubs=[]))
    rows_infer = slot_rows(on, lineups, ref_names)

    out = {"control_reproduced": same,
           "reference": ref_names,
           "truth": a.truth,
           "off": tally(slot_rows(off, lineups, ref_names)),
           "on": tally(rows_on),
           "infer": tally(rows_infer),
           "infer_reach": report.reach,
           "inferred": len(report.inferred),
           "by_rule": collections.Counter(i[0] for i in report.inferred),
           "rows": rows_infer}

    for name in ("off", "on", "infer"):
        print(f"\n── {name.upper()} " + "─" * 55)
        for k, n in sorted(out[name].items(), key=lambda kv: -kv[1]):
            print(f"   {n:4d}  {k[0]:<10} {k[1]}")
    print(f"\nINFER: reach={report.reach} inferred={len(report.inferred)} "
          f"by_rule={dict(out['by_rule'])}")

    for name in ("off", "on", "infer"):
        out[name] = {f"{k[0]}/{k[1]}": n for k, n in out[name].items()}
    Path(a.json).write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
