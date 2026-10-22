"""A staff whose OWN margin label the reader read, exported as something else.

## Why this is worth computing

It is free. The margin reader has already run, `absent_instrument.label_evidence`
already turns its output into `{page: {staff: instrument}}` per staff, and the
slot names are already on the record. No detection, no reading, no second pass —
the contradiction is arithmetic over things the pipeline is holding anyway.

And it is the one identity check that needs **no truth file**. Every other way
of asking "did we name this staff right" needs a reference encoding, a dossier
or a hand-read page; this one asks the document to agree with itself.

## What it is evidence OF, and what it is not

A contradiction says the chain **staff -> slot -> name** disagrees with the page
at one of its links. It does **not** say which link. Measured over the two
whole-work corpora that exist (Beethoven 5 / Litolff 88 pages and Brahms 1 /
Breitkopf 86 pages, 158 contradictions, every one adjudicated against the
printed page in `benchmarks/omr-label-contradiction-2026-09/`):

    138 of 158 (0.873)  the EXPORT is wrong — the page prints what the label
                        says and the file says something else
     20 of 158 (0.127)  the LABEL is wrong — the reader lost a qualifier
                        (`Fl. pic.` -> Flute, `Tr. Bas.` -> Trumpet), or the
                        scan damaged the glyph (`Ob.` -> Cb.)
      0 of 158          both right

⚠️ **Nothing on the record predicts WHICH.** Three cheap side-signals were
measured and all three fail: whether the exported name is already carried by a
label-agreeing staff of the same system; the mirror of that for the read name
(13/13 `label_wrong` on Beethoven, 11/13 `export_wrong` on Brahms — it INVERTS);
and whether the contradiction has a neighbour. Each separates on one edition and
collapses or reverses on the other, which is this project's oldest lesson about
tuning on one publisher.

So this is **additive evidence, not a gate**: it changes no name, vetoes
nothing, and is recorded for a consumer to weigh. Zero of the 158 rows were a
legitimate disagreement, so a firing is always worth a human — but which half to
disbelieve is not derivable here.

## The structural false positive, which this corpus cannot show

A **condensed staff** carries more than one instrument (`Violoncello e Basso`,
`Fl. e Ott.`). Its margin names one and its slot may name the other, and BOTH
are right. Neither Litolff's Beethoven nor Breitkopf's Brahms condenses that way
— they print `Vcl.` and `K.-B.` on separate staves — so the rate of this class
here is 0 of 158, which is a fact about two editions and not about the check.
Page-vs-encoding condensation is the `omr-headline-validity-2026-09` workstream's
subject; a consumer that wants to act on a contradiction should ask it first.

## ⚠️ `staff["instrument_label"]` CANNOT ANSWER THIS

That field is **slot-carried**: `contextual` stamps one raw text per SLOT, taken
from the first page in the run that labelled it, onto every staff of that slot on
every page. An audit built on it is unable to disagree — the field says what the
name was derived from. The per-staff evidence is `label_evidence`, and it is
confidence-filtered exactly as the alignment filters, so a label too weak to
align on is too weak to contradict with.

## ⚠️ The SOURCE is a split to report, never a filter to apply

`instrument_source` separates the mechanisms and is worth reporting per bucket.
It is **not** an exclusion list. On the 88-page Beethoven the largest single
population is 93 staves printed `Tp.` (Timpani) and exported `Trumpet`, and its
source is `score_order_ambiguity` — the same source as the three correct
`Basso.` -> Contrabass overturns on the same document. Dropping the source
because three of its rows are known-good would hide ninety-three that are not.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def find_contradictions(*,
                        staff_keys: Iterable[tuple[int, int, int]],
                        slot_by_staff: dict[tuple[int, int, int], int],
                        instrument_name_by_slot: dict[int, str],
                        instrument_source: dict[int, str],
                        evidence: dict[int, dict[int, str]],
                        vetoed_keys: Iterable[tuple[int, int, int]] = (),
                        ) -> list[dict[str, Any]]:
    """One record per staff that contradicts its own label. Pure.

    `evidence` is `absent_instrument.label_evidence(...)`. A staff the veto
    removed the name from is skipped: it has no exported name to contradict,
    and by the veto's own first clause it never carried a label anyway.
    """
    vetoed = set(vetoed_keys)
    keys = list(staff_keys)
    by_system: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for key in keys:
        by_system.setdefault((key[0], key[1]), []).append(key)

    out: list[dict[str, Any]] = []
    for (page_index, system_index), system_keys in sorted(by_system.items()):
        # Names this system carries with its OWN label agreeing. Recorded as
        # context on each record, not used to decide anything — see the module
        # docstring on why it does not separate the two directions.
        agreeing: set[str] = set()
        for key in system_keys:
            slot = slot_by_staff.get(key)
            if slot is None or slot < 0 or key in vetoed:
                continue
            name = instrument_name_by_slot.get(slot)
            read = evidence.get(page_index, {}).get(key[2])
            if name is not None and read == name:
                agreeing.add(name)
        for key in sorted(system_keys):
            staff_index = key[2]
            if key in vetoed:
                continue
            slot = slot_by_staff.get(key)
            if slot is None or slot < 0:
                continue
            name = instrument_name_by_slot.get(slot)
            if name is None:
                continue
            read = evidence.get(page_index, {}).get(staff_index)
            if read is None or read == name:
                continue
            out.append({
                "page_index": page_index, "system_index": system_index,
                "staff_index": staff_index, "slot": slot,
                "read": read, "exported": name,
                "source": instrument_source.get(slot, "label"),
                # The exported name is already carried, with its own label
                # agreeing, by another staff of this system. Context only.
                "name_already_on_system": name in agreeing,
            })
    return out


def summarise(rows: list[dict[str, Any]], labelled_staff_records: int
              ) -> dict[str, Any]:
    """The reported figure. `rows` is `find_contradictions`'s output.

    `labelled_staff_records` is the denominator that makes the count readable —
    staff records that both carry a label of their own and have an exported
    name, i.e. the population where a contradiction is even possible.
    """
    return {
        "contradictions": len(rows),
        "labelled_staff_records": labelled_staff_records,
        "by_source": dict(sorted(Counter(r["source"] for r in rows).items())),
        "by_pair": dict(sorted(Counter(
            f"{r['read']} -> {r['exported']}" for r in rows).items())),
        "rows": rows,
    }


def contradictable(*,
                   staff_keys: Iterable[tuple[int, int, int]],
                   slot_by_staff: dict[tuple[int, int, int], int],
                   instrument_name_by_slot: dict[int, str],
                   evidence: dict[int, dict[int, str]],
                   vetoed_keys: Iterable[tuple[int, int, int]] = (),
                   ) -> int:
    """How many staff records COULD contradict — the denominator."""
    vetoed = set(vetoed_keys)
    n = 0
    for key in staff_keys:
        if key in vetoed:
            continue
        slot = slot_by_staff.get(key)
        if slot is None or slot < 0:
            continue
        if instrument_name_by_slot.get(slot) is None:
            continue
        if evidence.get(key[0], {}).get(key[2]) is None:
            continue
        n += 1
    return n


# ── CLI ─────────────────────────────────────────────────────────────────────
# `python3 -m tools.omr.label_contradiction <result.json> ...`
#
# Reads the report out of a transcription that has already been made, the way
# `export_coverage --all` reads an inventory. Works on a full transcription and
# on the trimmed `absent_instrument_veto` extracts the identity benchmarks
# commit, so every stored artefact in the repo can be asked the question.


def report_from_result(doc: dict) -> dict[str, Any] | None:
    """The summary block if the run recorded one; else recompute it from the
    `absent_instrument_veto` evidence, which older artefacts carry.
    """
    ctx = doc.get("contextual") or {}
    if isinstance(ctx.get("label_contradiction"), dict):
        return ctx["label_contradiction"]
    blob = ctx.get("absent_instrument_veto")
    if not blob:
        return None
    evidence: dict[int, dict[int, str]] = {}
    for e in blob["label_evidence"]:
        evidence.setdefault(e["page_index"], {})[e["staff_index"]] = \
            e["instrument"]
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in blob["staff_slots"]}
    names = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
    sources = {s["slot"]: s.get("source", "label")
               for s in blob["slot_instruments"]}
    vetoed = ({(v["page_index"], v["system_index"], v["staff_index"])
               for v in blob.get("vetoes", [])}
              if blob.get("mode") == "apply" else set())
    keys = list(slot_by_staff)
    rows = find_contradictions(
        staff_keys=keys, slot_by_staff=slot_by_staff,
        instrument_name_by_slot=names, instrument_source=sources,
        evidence=evidence, vetoed_keys=vetoed)
    return summarise(rows, contradictable(
        staff_keys=keys, slot_by_staff=slot_by_staff,
        instrument_name_by_slot=names, evidence=evidence, vetoed_keys=vetoed))


def main(argv: list[str] | None = None) -> int:
    import json
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        return 2
    worst = 0
    for path in args:
        with open(path) as fh:
            rep = report_from_result(json.load(fh))
        if rep is None:
            print(f"{path}: no contextual identity block — nothing to check")
            continue
        print(f"{path}: {rep['contradictions']} of "
              f"{rep['labelled_staff_records']} labelled staff records "
              f"contradict their own margin label")
        for src, n in rep["by_source"].items():
            print(f"    source {src:24} {n}")
        for pair, n in rep["by_pair"].items():
            print(f"    {pair:44} x{n}")
        worst = max(worst, rep["contradictions"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
