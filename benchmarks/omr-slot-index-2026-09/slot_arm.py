"""GATHER ONCE, ADJUDICATE TWICE — the slot rule, against hand-read print truth.

⚠️⚠️ THIS IS AN ADJUDICATE CHANGE, SO A RE-EXPORT IS STRUCTURALLY BLIND TO IT.
Replaying a saved record replays the verdicts already in it; the exporter would
produce the same 12 parts on either tree. This rebuilds a `Log` from ONE saved
record's GATHER rows and re-runs ADJUDICATE over it twice -- so the two arms
differ only in `adjudicate_slot_index`, and no detector jitter enters.

⚠️ WHAT IT IS BLIND TO. It isolates ADJUDICATE over a FIXED gather: a GATHER
change never enters the rebuild. This change makes none -- it reads
`Q.INSTRUMENT`, `Q.STAFF_ORDINAL` and `Q.SYSTEM_STAFF_COUNT`, all already
gathered and adjudicated -- and `--control` says so before any arm is read.

⚠️ REACH FIRST. A record gathered without `--surya` reads ZERO margin labels on
this 1870 scan, and the new rule would then abstain on every short-system staff
and produce a clean, meaningless result. This exits non-zero declaring itself
DEAD when the record carries no `Q.MARGIN_LABEL` observation.

⚠️ THE TRUTH IS HAND-READ AND IS NOT OURS. `printed-lineups.json` names which
instrument each printed staff of each printed system carries, from a human on
the print, corroborated by the page's own margin labels. Counting slots cannot
see a relocation; only NAMING the staves can, which is why every table here is
per staff and not a total.

    python3 benchmarks/omr-slot-index-2026-09/slot_arm.py OUT/record-labels.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.adjudicate import REGISTRY, Ruling, _ensure_decisions  # noqa: E402
from tools.omr.staged.record import Kind, Log, Outcome, Q, Subject  # noqa: E402

TRUTH = json.loads(
    (REPO / "benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json")
    .read_text())


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order.

    Lifted unchanged in shape from
    `benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py`; kept here
    rather than imported because that module's path is not a package name.
    """
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


def _old_slot_index(ev):
    """`adjudicate_slot_index` EXACTLY as it stood before 2026-09-11.

    The staff's own ordinal on every path, under two reasons that differ only
    in what they cite. Kept verbatim so the BEFORE arm is the shipped rule and
    not a paraphrase of it.
    """
    ordinal = ev.verdict(Q.STAFF_ORDINAL)
    if ordinal is None or ordinal.value is None:
        return Ruling.abstain("no_ordinal")
    count = ev.verdict(Q.SYSTEM_STAFF_COUNT, subject=ev.subject.at(Kind.SYSTEM))
    instrument = ev.verdict(Q.INSTRUMENT)
    if count is None or count.value is None:
        return Ruling.abstain("no_reference")
    if instrument is not None and instrument.value is not None:
        return Ruling(value=int(ordinal.value), reason="named",
                      used=(ordinal.id, instrument.id))
    return Ruling(value=int(ordinal.value), reason="full_lineup",
                  used=(ordinal.id, count.id))


def _arm(rec, old: bool):
    _ensure_decisions()
    spec = REGISTRY[Q.SLOT_INDEX]
    log = rebuild(rec)
    if old:
        REGISTRY[Q.SLOT_INDEX] = spec.__class__(**{**spec.__dict__,
                                                   "fn": _old_slot_index})
    try:
        adjudicate.run(log)
    finally:
        REGISTRY[Q.SLOT_INDEX] = spec
    return log


def _truth_lineup():
    """`{(page, system): [instrument as PRINTED, by staff ordinal]}`."""
    return {(s["page"], s["system"]): s["lineup"] for s in TRUTH["systems"]}


def _slot_names():
    """`{slot index: instrument as PRINTED}` for the reference lineup."""
    return dict(enumerate(TRUTH["full"]))


def _report(log, lineups, slot_names, label):
    """Per-staff: what slot it took, and whose part that is.

    A staff is GRAFTED when the slot it takes belongs to a different printed
    instrument. ⚠️ `Violoncello e Basso` against `Violoncello` is CONDENSATION,
    not a graft -- one printed staff carrying two reference parts -- and it is
    reported apart, because conflating them was already measured turning 12
    into 16.
    """
    rows, grafts, condensed, abstained = [], [], [], collections.Counter()
    for (page, system), printed in sorted(lineups.items()):
        for i, want in enumerate(printed):
            sub = Subject(Kind.STAFF, page=page, system=system, staff=i)
            v = log.verdict(Q.SLOT_INDEX, sub)
            if v is None or v.outcome is not Outcome.DECIDED:
                abstained[v.reason if v else "no_verdict"] += 1
                rows.append((page, system, i, want, None,
                             v.reason if v else "no_verdict"))
                continue
            got = slot_names.get(v.value, f"slot{v.value}")
            rows.append((page, system, i, want, v.value, got))
            if got != want:
                if want.startswith(got) or got.startswith(want) or " e " in want:
                    condensed.append((page, system, i, want, got))
                else:
                    grafts.append((page, system, i, want, got))
    return rows, grafts, condensed, abstained


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    d = json.loads(Path(args.record).read_text())
    rec = d["record"]
    print("provenance:", d.get("provenance"))

    # ── REACH, before anything else ─────────────────────────────────────────
    labels = [o for o in rec["observations"] if o["quantity"] == "margin_label"]
    staves = {o["subject"] for o in rec["observations"]
              if o["quantity"] == "staff_ordinal"}
    print("=" * 72)
    print("REACH")
    print("=" * 72)
    print("  staff-systems               : %d" % len(staves))
    print("  Q.MARGIN_LABEL observations : %d" % len(labels))
    if not labels:
        print("\nDEAD: no margin label on this record. Either the gather "
              "predates the\npdf_path forward or it ran without --surya. A "
              "zero from here would say\nnothing about the rule.")
        return 2

    lineups = _truth_lineup()
    slot_names = _slot_names()
    sizes = {k: len(v) for k, v in lineups.items()}
    widest = max(sizes.values())
    print("  printed systems             : %d  sizes %s"
          % (len(sizes), sorted(collections.Counter(sizes.values()).items())))
    print("  SHORT systems (< %d staves) : %d, holding %d staves"
          % (widest, sum(1 for n in sizes.values() if n < widest),
             sum(n for n in sizes.values() if n < widest)))

    out = {}
    for label, old in (("BEFORE", True), ("AFTER", False)):
        log = _arm(rec, old)
        out[label] = _report(log, lineups, slot_names, label)
        v = log.verdict(Q.PART_PARTITION, Subject(Kind.DOCUMENT))
        rows, grafts, condensed, abstained = out[label]
        decided = sum(1 for r in rows if r[4] is not None)
        print()
        print("=" * 72)
        print("%s" % label)
        print("=" * 72)
        print("  slot decided / staves : %d / %d" % (decided, len(rows)))
        print("  abstentions           : %s" % dict(abstained))
        print("  GRAFTS                : %d" % len(grafts))
        print("  condensation (apart)  : %d" % len(condensed))
        print("  part_partition        : %s  %s" % (v.reason, v.value))
        for page, system, i, want, got in grafts:
            print("      p%d/s%d staff %-2d  prints %-22s -> part %s"
                  % (page, system, i, want, got))

    if args.verbose:
        print()
        print("=" * 72)
        print("PER STAFF  (printed | before | after)")
        print("=" * 72)
        b = {(r[0], r[1], r[2]): r for r in out["BEFORE"][0]}
        for r in out["AFTER"][0]:
            k = (r[0], r[1], r[2])
            print("  p%d/s%d %-2d  %-22s  %-22s  %s"
                  % (r[0], r[1], r[2], r[3], b[k][5], r[5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
