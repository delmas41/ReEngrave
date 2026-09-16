"""THE PART JOIN, END TO END — one gather, adjudicated twice, EXPORTED twice.

`slot_arm.py` stops at the verdict. This carries the same two arms all the way
to the FILE, because the number Sean is waiting on is a PART COUNT and no
verdict states one: `adjudicate_part_partition` says `join: "slot"`, and how
many `<part>` elements that produces depends on the exporter's `stranded`
branch, which files every slot-less staff as its own fragment.

⚠️ REACH FIRST. A record gathered without `--surya` reads ZERO margin labels on
this 1870 scan and BOTH arms then abstain identically — a clean, meaningless
zero. This exits non-zero declaring itself DEAD when the record carries no
`Q.MARGIN_LABEL` observation.

⚠️ THE CONTROL IS THAT THE TWO ARMS DIFFER AT ALL. A replay harness that
reused one arm's output would report "identical" whatever the change did — the
shape this repo has recorded seven times. So the slot verdicts of the two arms
are compared BEFORE any part count is read, and a run where they agree on every
staff exits non-zero rather than reporting a clean equality.

⚠️ A GRAFT IS NAMED, NEVER COUNTED. Two parts of equal size can hold entirely
different music, so every table here is per staff-system against hand-read
print truth (`printed-lineups.json`), and `Violoncello e Basso` against
`Violoncello` is CONDENSATION, reported apart — conflating them was already
measured turning 12 into 16.

    python3 <this> OUT/record-labels.json
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate, evaluate                 # noqa: E402
from tools.omr.staged import adjudicators, consequences           # noqa: E402,F401
from tools.omr.staged import export as staged_export              # noqa: E402
from tools.omr.staged.adjudicate import REGISTRY, Ruling, _ensure_decisions  # noqa: E402
from tools.omr.staged.record import Kind, Log, Outcome, Q, Subject  # noqa: E402

TRUTH = json.loads(
    (REPO / "benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json")
    .read_text())


def rebuild(rec: dict) -> Log:
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
    """`adjudicate_slot_index` EXACTLY as it stood before 2026-09-11 — the
    staff's own ordinal on every path. Copied verbatim from `slot_arm.py` so
    the two arms of the two harnesses are the same two arms."""
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


def arm(rec: dict, old: bool) -> Log:
    _ensure_decisions()
    spec = REGISTRY[Q.SLOT_INDEX]
    log = rebuild(rec)
    if old:
        REGISTRY[Q.SLOT_INDEX] = spec.__class__(**{**spec.__dict__,
                                                   "fn": _old_slot_index})
    try:
        adjudicate.run(log)
        evaluate.run(log)
    finally:
        REGISTRY[Q.SLOT_INDEX] = spec
    return log


def lineups():
    return {(s["page"], s["system"]): s["lineup"] for s in TRUTH["systems"]}


def slot_names():
    return dict(enumerate(TRUTH["full"]))


def _same_instrument(printed: str, slot_name: str) -> str:
    """"ok" | "condensed" | "graft".

    ⚠️ NOT `slot_arm._report`'s split, and the difference is a DEFECT that
    harness's own run exposed. It asks
    `printed.startswith(slot) or slot.startswith(printed) or " e " in printed`,
    which is three string accidents rather than a claim about instruments:
    `Violino II` STARTSWITH `Violino I`, and ANY name containing ` e ` is
    excused against ANY slot — so `Violoncello e Basso` filed under
    `Violino I` reads as condensation. Both are grafts, and both were being
    reported as harmless.

    ⚠️ THE CORRECTED RULE IS EXACT MEMBERSHIP, NOT A LOOSER OR TIGHTER
    THRESHOLD: a printed staff condenses reference parts iff the slot's name
    is one of the ` e `-separated components it prints. Checked against two
    prior, independent measurements rather than chosen — it takes the BEFORE
    arm to `{p3/s1: 7, p4/s0: 5}` = 12, which is both
    `probe_rule_vs_print.py`'s 12 and the measure-math partition's named
    split in `benchmarks/omr-part-join-phase2-2026-09`. The shipped rule
    reports 10 and agrees with neither.
    """
    if printed == slot_name:
        return "ok"
    if slot_name in [p.strip() for p in printed.split(" e ")]:
        return "condensed"
    return "graft"


def per_staff(log):
    rows, grafts, condensed, abstained = [], [], [], collections.Counter()
    names = slot_names()
    for (page, system), printed in sorted(lineups().items()):
        for i, want in enumerate(printed):
            sub = Subject(Kind.STAFF, page=page, system=system, staff=i)
            v = log.verdict(Q.SLOT_INDEX, sub)
            if v is None or v.outcome is not Outcome.DECIDED:
                abstained[v.reason if v else "no_verdict"] += 1
                rows.append((page, system, i, want, None, None))
                continue
            got = names.get(v.value, f"slot{v.value}")
            rows.append((page, system, i, want, v.value, got))
            verdict = _same_instrument(want, got)
            if verdict == "graft":
                grafts.append((page, system, i, want, got))
            elif verdict == "condensed":
                condensed.append((page, system, i, want, got))
    return rows, grafts, condensed, abstained


def export(result: dict, log: Log):
    """The FILE. Returns (n parts, provenance, per-part printed instruments)."""
    r2 = copy.deepcopy(result)
    r2["record"] = log.to_json()
    xml, report = staged_export.to_musicxml(r2)
    prov = report.get("part_join") or {}
    n_parts = xml.count("<score-part ")
    return xml, report, prov, n_parts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--xml-dir", default=None)
    args = ap.parse_args()

    result = json.loads(Path(args.record).read_text())
    rec = result["record"]
    print("provenance:", result.get("provenance"))

    # ── REACH ───────────────────────────────────────────────────────────────
    labels = [o for o in rec["observations"] if o["quantity"] == "margin_label"]
    staves = {o["subject"] for o in rec["observations"]
              if o["quantity"] == "staff_ordinal"}
    print("=" * 72)
    print("REACH")
    print("=" * 72)
    print("  staff-systems               : %d" % len(staves))
    print("  Q.MARGIN_LABEL observations : %d" % len(labels))
    by_sys = collections.Counter()
    for o in labels:
        s = Subject.from_key(o["subject"])
        by_sys[(s.page, s.system)] += 1
    for k in sorted(by_sys):
        print("      p%d/s%d : %d labels" % (k[0], k[1], by_sys[k]))
    if not labels:
        print("\nDEAD: no margin label on this record. A zero from here would "
              "say nothing about the rule.")
        return 2

    # ── SEGMENTATION, before any slot is read ───────────────────────────────
    # ⚠️ THE PROBE'S SUBJECTS COME FROM THE PRINT AND THE RECORD'S FROM OUR
    # OWN READING, so a system we segment into a different number of staves
    # silently mis-keys every row below. The reference lineup the rule picks
    # is THE WIDEST SYSTEM WE READ, not the widest the page prints.
    ours = collections.Counter()
    for o in rec["observations"]:
        if o["quantity"] != "staff_ordinal":
            continue
        s = Subject.from_key(o["subject"])
        ours[(s.page, s.system)] += 1
    print()
    print("  SEGMENTATION   printed | ours")
    bad = 0
    for k, printed in sorted(lineups().items()):
        got = ours.get(k, 0)
        flag = "" if got == len(printed) else "   <-- DISAGREES"
        if got != len(printed):
            bad += 1
        print("      p%d/s%d : %2d | %2d%s" % (k[0], k[1], len(printed), got, flag))
    extra = sorted(set(ours) - set(lineups()))
    if extra:
        print("      systems we read that the truth does not name: %s" % (extra,))
    if bad or extra:
        print("  ⚠️ the per-staff tables below are keyed on the PRINT and "
              "our reading disagrees;\n     read the divergence as the result.")

    out = {}
    for label, old in (("BEFORE", True), ("AFTER", False)):
        log = arm(rec, old)
        rows, grafts, condensed, abstained = per_staff(log)
        pv = log.verdict(Q.PART_PARTITION, Subject(Kind.DOCUMENT))
        xml, report, prov, n_parts = export(result, log)
        out[label] = dict(rows=rows, grafts=grafts, condensed=condensed,
                          abstained=abstained, partition=pv, prov=prov,
                          n_parts=n_parts, report=report, xml=xml, log=log)
        if args.xml_dir:
            p = Path(args.xml_dir) / ("%s.musicxml" % label.lower())
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(xml)

    # ── THE CONTROL: can this comparison see a difference at all? ───────────
    b = {(r[0], r[1], r[2]): r[4] for r in out["BEFORE"]["rows"]}
    a = {(r[0], r[1], r[2]): r[4] for r in out["AFTER"]["rows"]}
    moved = [k for k in b if b[k] != a[k]]
    print()
    print("=" * 72)
    print("CONTROL — the two arms differ on %d of %d staff-systems"
          % (len(moved), len(b)))
    print("=" * 72)
    if not moved:
        print("DEAD: the arms are identical. Either the record predates the "
              "rule's inputs\nor the swap did not take. No part count read.")
        return 3

    for label in ("BEFORE", "AFTER"):
        o = out[label]
        decided = sum(1 for r in o["rows"] if r[4] is not None)
        print()
        print("=" * 72)
        print(label)
        print("=" * 72)
        named = collections.Counter()
        for (page, system), printed in sorted(lineups().items()):
            for i in range(len(printed)):
                v = o["log"].verdict(Q.INSTRUMENT,
                                     Subject(Kind.STAFF, page=page,
                                             system=system, staff=i))
                if v is not None and v.outcome is Outcome.DECIDED:
                    named[(page, system)] += 1
        print("  instrument decided    : %d  %s"
              % (sum(named.values()),
                 {"p%d/s%d" % k: n for k, n in sorted(named.items())}))
        print("  slot decided / staves : %d / %d" % (decided, len(o["rows"])))
        print("  abstentions           : %s" % dict(o["abstained"]))
        print("  GRAFTS                : %d" % len(o["grafts"]))
        print("  condensation (apart)  : %d" % len(o["condensed"]))
        print("  part_partition        : %s  %s"
              % (o["partition"].reason, o["partition"].value))
        print("  EXPORTED <part>s      : %d" % o["n_parts"])
        print("  join provenance       : %s" % o["prov"])
        for page, system, i, want, got in o["grafts"]:
            print("      p%d/s%d staff %-2d  prints %-22s -> part %s"
                  % (page, system, i, want, got))

    # ── the cross-tab ───────────────────────────────────────────────────────
    names = slot_names()
    cls = {}
    for label in ("BEFORE", "AFTER"):
        for r in out[label]["rows"]:
            k = (r[0], r[1], r[2])
            if r[4] is None:
                cls.setdefault(k, {})[label] = "abstain"
            else:
                cls.setdefault(k, {})[label] = (
                    "ok" if _same_instrument(r[3], r[5]) != "graft" else "wrong")
    tab = collections.Counter((v["BEFORE"], v["AFTER"]) for v in cls.values())
    print()
    print("=" * 72)
    print("CROSS-TAB   incumbent(ordinal) -> rule")
    print("=" * 72)
    for k in sorted(tab):
        print("  %-8s -> %-8s : %d" % (k[0], k[1], tab[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
