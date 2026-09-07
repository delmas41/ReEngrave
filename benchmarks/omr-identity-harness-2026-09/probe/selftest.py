#!/usr/bin/env python3
"""⚠️ THE GATE: a harness that cannot SEE today's known faults is not a harness.

    python3 probe/selftest.py            # exits non-zero on any failure

Three faults landed as flags on 2026-09-06, each of which can be switched back
ON.  For each, this asserts BOTH directions:

    RESTORED  with the fault switched back on the harness REPORTS it, at the
              magnitude and with the signature the diagnosing session recorded.
    FIXED     with the shipped default the harness does NOT report it.

The second half is what makes it falsifiable rather than a scorer that prints
numbers.  A metric that moves when the fault is restored but also moves when it
is not is measuring something else.

Plus two structural assertions that license the pooling everything else does:

    SHAPE     identity is recorded in two artefact shapes and they are the same
              fact one join apart — deriving each staff's provenance from
              `slot_instruments[slot].source` must reproduce the per-staff
              `instrument_source` exactly.
    KEYSET    the arms of one A/B must share a staff-record KEY SET, not merely
              a count, or a difference between them is not the flag.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arms as arms_mod          # noqa: E402
import corpus                    # noqa: E402
import load as load_mod          # noqa: E402
import score as score_mod        # noqa: E402

MAIN = load_mod.MAIN
FAILS: list[str] = []
LINES: list[str] = []


def check(ok: bool, what: str, detail: str = "") -> None:
    tag = "PASS" if ok else "**FAIL**"
    LINES.append(f"  [{tag}] {what}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILS.append(what)


def rep(arm: str):
    work, path, regime, _ = arms_mod.ARMS[arm]
    return score_mod.score(load_mod.load(path, work, arm), regime)


def conf(r, want: str, got: str) -> int:
    return r.confusion.get((want, got), 0)


# ─────────────────────────────────────────────────────────────────────────────
def test_1_group_map():
    """`OMR_SLOT_GROUP_MAP=ordinal` — a bracket ordinal compared as a family.

    Recorded (`benchmarks/omr-slot-alignment-2026-09/FINDINGS.md`): on the
    Beethoven whole work, spans OFF, impossible 89 -> 43 and correct 750 -> 756,
    with a 7-record residue `Violin -> Trombone` x4, `Viola -> Trombone` x2,
    `Timpani -> Trombone` x1 on p23 sys1, p31 sys1, p38 sys0.

    ⚠️ REGIME-DEPENDENT, and the harness has to say so: with spans ON the two
    arms are IDENTICAL — on this work the two fixes are redundant and spans get
    there first.  A harness reporting one number per work would call this fix
    worthless or priceless depending on which arm it happened to run.
    """
    LINES.append("\nSELF-TEST 1 — OMR_SLOT_GROUP_MAP=ordinal (Beethoven 5 / Litolff)")
    bad = rep("beet5/groupmap=ordinal,spans=off")
    good = rep("beet5/groupmap=map,spans=off")

    check(bad.impossible == 89 and good.impossible == 43,
          "RESTORED: impossible 89 with the fault, 43 with the fix",
          f"got {bad.impossible} / {good.impossible}")
    check(bad.correct == 750 and good.correct == 756,
          "RESTORED: identity 750 -> 756 correct of 807 judgeable",
          f"got {bad.correct} / {good.correct}")
    check(bad.rate < good.rate,
          "the identity RATE moves in the same direction as the fix",
          f"{bad.rate:.4f} -> {good.rate:.4f}")

    sig = {("Violin", "Trombone"): 4, ("Viola", "Trombone"): 2,
           ("Timpani", "Trombone"): 1}
    got = {k: conf(bad, *k) for k in sig}
    check(got == sig,
          "RESTORED: the recorded 7-record signature is visible EXACTLY",
          f"strings/timpani -> Trombone: {got}")
    check(conf(good, "Violin", "Trombone") == 0
          and conf(good, "Viola", "Trombone") == 0,
          "FIXED: the six STRING records are absent under the shipped default",
          f"Violin->Trombone {conf(good, 'Violin', 'Trombone')}, "
          f"Viola->Trombone {conf(good, 'Viola', 'Trombone')}")
    check(conf(good, "Timpani", "Trombone") == 1,
          "⚠️ RESIDUE the fix does NOT touch: 1 `Timpani -> Trombone` survives",
          "p31 sys1 — the 7th of the recorded 7, and only 6 of them are the "
          "group-map fault; the harness must not launder it away")
    check(bad.human > good.human,
          "human-cost axis moves too", f"{bad.human} -> {good.human} staves")

    on_bad = rep("beet5/groupmap=ordinal,spans=on")
    on_good = rep("beet5/groupmap=map,spans=on")
    check((on_bad.correct, on_bad.impossible) == (on_good.correct, on_good.impossible),
          "REGIME: with spans ON the flag does not reach the output at all",
          f"{on_bad.correct}/{on_bad.impossible} vs "
          f"{on_good.correct}/{on_good.impossible} — the harness reports the "
          "regime, so this null is legible rather than a silent zero")


# ─────────────────────────────────────────────────────────────────────────────
def test_2_span_reference_fit():
    """`OMR_SPAN_REFERENCE_FIT=off` — the span picks a reference the document
    cannot express.

    Recorded (`benchmarks/omr-span-composition-2026-09/FINDINGS.md` and
    `benchmarks/omr-brahms-lineup-2026-09/FINDINGS.md`): Brahms 1 pre-finale
    impossible names 36 (spans off) / 149 (spans on, fit off) / 36 (refuse) /
    0 (search), and identity 0.8403 -> 0.9712 (refuse) / 0.9699 (search).

    ⚠️ AND THE TWO COLUMNS DISAGREE about which repair is better.  `refuse`
    grades one staff higher on correct/wrong (742 vs 741) while leaving 36
    impossible names standing where `search` reads 0.  This test asserts the
    DISAGREEMENT, because a harness that averaged it away would have hidden the
    only interesting fact about the pair.
    """
    LINES.append("\nSELF-TEST 2 — OMR_SPAN_REFERENCE_FIT=off (Brahms 1 / Breitkopf)")
    off = rep("brahms1/fit=off,spans=on")
    refuse = rep("brahms1/fit=refuse,spans=on")
    search = rep("brahms1/fit=search,spans=on")
    base = rep("brahms1/fit=off,spans=off")

    check(off.impossible == 149,
          "RESTORED: 149 pre-finale impossible names", f"got {off.impossible}")
    check(base.impossible == 36 and refuse.impossible == 36,
          "RESTORED: the recorded 36 for spans-off and for `refuse`",
          f"got {base.impossible} / {refuse.impossible}")
    check(search.impossible == 0,
          "FIXED: the shipped `search` reads 0", f"got {search.impossible}")

    check(abs(off.rate - 0.8403) < 5e-4,
          "RESTORED: identity rate 0.8403 with the fault", f"got {off.rate:.4f}")
    check(abs(search.rate - 0.9699) < 5e-4,
          "FIXED: identity rate 0.9699 shipped", f"got {search.rate:.4f}")

    for w, g, n in (("Horn", "Trumpet", 33), ("Trumpet", "Trombone", 33),
                    ("Timpani", "Tuba", 28), ("Violin", "Tuba", 8)):
        check(conf(off, w, g) == n and conf(search, w, g) == 0,
              f"RESTORED/FIXED: `{w} -> {g}` x{n} with the fault, 0 shipped",
              f"got {conf(off, w, g)} / {conf(search, w, g)}")

    check(refuse.correct == 742 and search.correct == 741,
          "THE DISAGREEMENT: `refuse` grades ONE staff higher than `search`",
          f"{refuse.correct} vs {search.correct} correct, while impossible is "
          f"{refuse.impossible} vs {search.impossible} — neither column is a "
          "superset of the other and the harness prints both")
    check(off.human > search.human,
          "human-cost axis moves too", f"{off.human} -> {search.human} staves")

    resid = conf(search, "Trombone", "Tuba")
    check(resid == 17 and search.never == 23,
          "the harness also SEES what the fix does NOT touch: the finale's "
          "`Trombone -> Tuba` x17, invisible to the page-scoped impossible rule",
          f"conf={resid}, not-in-this-work={search.never}")


# ─────────────────────────────────────────────────────────────────────────────
def test_3_bracket_columns():
    """`OMR_BRACKET_COLUMNS` — bracket-group structure disagreeing with itself.

    A STRUCTURE fault, not an identity one, and it is in the gate because the
    bracket group term is what mis-slotted Beethoven's strings in test 1.  The
    measure is within-page: two systems on ONE page with the SAME staff count
    are the same printed lineup, so a disagreement is the detector disagreeing
    with itself about ink it read twice.

    Recorded (`benchmarks/omr-bracket-stability-2026-09/FINDINGS.md`): 0.384 ->
    0.055 over 144 pages of five publishers.
    """
    LINES.append("\nSELF-TEST 3 — OMR_BRACKET_COLUMNS (bracket-group stability, 5 publishers)")
    d = MAIN / "benchmarks/omr-bracket-stability-2026-09/out"
    arms = {}
    for tag, f in (("baseline (fault restored)", "rate-scan-baseline.json"),
                   ("columns", "rate-scan-columns.json"),
                   ("columns+evidence floor", "rate-scan-columns-floor.json")):
        p = d / f
        if not p.is_file():
            check(False, f"artefact present: {f}")
            return
        arms[tag] = json.loads(p.read_text())["summary"]["within_page"]

    base = arms["baseline (fault restored)"]
    floor = arms["columns+evidence floor"]
    cols = arms["columns"]
    for tag, v in arms.items():
        LINES.append(f"      {tag:26s} pairs={v['pairs']:3d} "
                     f"disagreeing={v['disagreeing']:3d} rate={v['rate']:.4f}")
    check(abs(base["rate"] - 0.3836) < 5e-4,
          "RESTORED: within-page disagreement 0.3836", f"got {base['rate']:.4f}")
    check(abs(floor["rate"] - 0.0548) < 5e-4,
          "FIXED: 0.0548 with the object-count rule + evidence floor",
          f"got {floor['rate']:.4f}")
    check(cols["rate"] < base["rate"] and floor["rate"] < cols["rate"],
          "both repair arms beat the fault, floor beats columns alone",
          f"{base['rate']:.4f} -> {cols['rate']:.4f} -> {floor['rate']:.4f}")
    check(base["pairs"] == floor["pairs"] == cols["pairs"] == 73,
          "all three arms share ONE denominator (73 same-count system pairs)",
          "a rate improvement bought by scoring fewer pairs would be invisible "
          "otherwise")


# ─────────────────────────────────────────────────────────────────────────────
def test_4_shape_agreement():
    """The two artefact shapes are one fact, one join apart."""
    LINES.append("\nSTRUCTURAL — the two artefact shapes agree")
    p = MAIN / arms_mod.ARMS["beet5/shipped"][1]
    r = json.loads(p.read_text())
    blob = r["contextual"]["absent_instrument_veto"]
    slot_src = {s["slot"]: s.get("source") for s in blob["slot_instruments"]}
    agree = dis = 0
    for pg in r["pages"]:
        for sy in pg["systems"]:
            for s in sy["staves"]:
                want = s.get("instrument_source")
                got = slot_src.get(s.get("slot_index"))
                agree += got == want
                dis += got != want
    check(dis == 0 and agree > 1500,
          "per-staff `instrument_source` is exactly slot_instruments[slot].source",
          f"{agree} agree, {dis} disagree — this is what licenses pooling the "
          "'compose' arms with the 'staff' one")


def test_5_key_sets():
    """Arms of one A/B must share a staff-record KEY SET, not just a count."""
    LINES.append("\nSTRUCTURAL — A/B arms share one staff-record key set")
    groups = {
        "beet5 groupmap, spans off": ["beet5/groupmap=ordinal,spans=off",
                                      "beet5/groupmap=map,spans=off"],
        "brahms1 fit, spans on": ["brahms1/fit=off,spans=on",
                                  "brahms1/fit=refuse,spans=on",
                                  "brahms1/fit=search,spans=on"],
    }
    for tag, names in groups.items():
        keys = None
        ok = True
        for n in names:
            work, path, _, _ = arms_mod.ARMS[n]
            d = load_mod.load(path, work, n)
            k = {(s.page, s.system, s.staff_index) for s in d.staves}
            if keys is None:
                keys = k
            elif k != keys:
                ok = False
        check(ok, f"{tag}: identical key sets ({len(keys)} records)",
              "" if ok else "the arms did not come off one read pass")


def test_6_coverage():
    """State the judgeable coverage out loud — it is a limit, not a detail."""
    LINES.append("\nSTRUCTURAL — judgeable coverage, stated rather than implied")
    b5 = rep("beet5/shipped")
    br = rep("brahms1/fit=search,spans=on")
    tot_j = b5.n_judgeable + br.n_judgeable
    tot_r = b5.n_records + br.n_records
    LINES.append(f"      beet5   {b5.n_judgeable}/{b5.n_records} "
                 f"({b5.n_judgeable / b5.n_records:.1%})")
    LINES.append(f"      brahms1 {br.n_judgeable}/{br.n_records} "
                 f"({br.n_judgeable / br.n_records:.1%})")
    LINES.append(f"      POOLED  {tot_j}/{tot_r} ({tot_j / tot_r:.1%}), "
                 f"2 works, 2 publishers, 2 engravings")
    check(b5.n_judgeable == 807 and br.n_judgeable == 764,
          "the graded corpus is the recorded 807 + 764 = 1571 staff records",
          f"got {b5.n_judgeable} + {br.n_judgeable} = {tot_j}")


def test_7_read_pass_floor():
    """⚠️ THE FLOOR: two whole-work READ PASSES of one PDF disagree by 50 of 807.

    Found by this harness, not by an earlier session.  `beet5/shipped` (the veto
    session's pass) and every arm off the slot-alignment / span-composition pass
    are the same PDF at the same dpi, and their identity differs by more than
    any flag under test on this work — 0.9913 vs 0.9368.

    The whole difference is ONE SLOT: pass A names slot 8 `Timpani` from a
    label, pass B names it `Trumpet` from `score_order_ambiguity`, and 50
    judgeable Timpani staves inherit it.

    ⚠️⚠️ AND THE EVIDENCE STANDS IN A STRICT SUPERSET RELATION THE WRONG WAY
    ROUND.  Pass B's margin evidence CONTAINS pass A's — 962 of 962 shared rows
    agree, zero contradictions, and B read 11 MORE labels, two of which are
    `Timpani` on exactly the staff position slot 8 covers (p50 s8, p52 s8).
    More correct evidence, no contradiction, worse answer.  **The identity join
    is not monotone in label evidence** — which is precisely the property
    §8b's additive-evidence design assumes and which nothing has ever checked.

    ⚠️ NOT ATTRIBUTED, deliberately.  The two passes also differ in CODE (A
    predates the group-map and span-composition fixes), and committed artefacts
    cannot separate "the extra evidence did it" from "the code drift did it".
    What they DO establish is the floor: **an identity figure from a different
    read pass is not a baseline**, the same lesson the scan gate learned as
    ±6 edits.  Settling the attribution costs one ~26-minute read pass at one
    commit, serving both arms off one cache — see FINDINGS.md.
    """
    LINES.append("\n⚠️ SELF-TEST 7 — the READ-PASS floor (found by this harness)")
    a = rep("beet5/shipped")
    b = rep("beet5/groupmap=map,spans=on")
    A, B = {}, {}
    for r, d in ((a, A), (b, B)):
        for x in r.records:
            d[(x["page"], x["system"], x["ordinal"])] = x
    moved = sum(1 for k in A if A[k]["emitted"] != B[k]["emitted"])
    LINES.append(f"      pass A (veto session)      {a.correct}/{a.n_judgeable}"
                 f" = {a.rate:.4f}")
    LINES.append(f"      pass B (slot-alignment)    {b.correct}/{b.n_judgeable}"
                 f" = {b.rate:.4f}")
    LINES.append(f"      staff records emitting a different name: {moved}")
    check(moved >= 50,
          "the harness SEES the read-pass difference at all",
          f"{moved} of {a.n_judgeable} judgeable records move")
    check(abs(a.rate - b.rate) > 0.05,
          "and it is LARGER than any single flag on this work",
          f"{a.rate:.4f} vs {b.rate:.4f}; the group-map flag moves 6 records")

    # the superset relation, straight out of the two artefacts
    ev = {}
    for tag, arm in (("A", "beet5/shipped"), ("B", "beet5/groupmap=map,spans=on")):
        blob = json.loads((MAIN / arms_mod.ARMS[arm][1]).read_text())
        blob = blob["contextual"]["absent_instrument_veto"]
        ev[tag] = {(e["page_index"], e["staff_index"]): e["instrument"]
                   for e in blob["label_evidence"]}
        ev[tag + "slot8"] = [s for s in blob["slot_instruments"] if s["slot"] == 8]
    shared = set(ev["A"]) & set(ev["B"])
    dis = [k for k in shared if ev["A"][k] != ev["B"][k]]
    check(set(ev["A"]) < set(ev["B"]) and not dis,
          "B's margin evidence STRICTLY CONTAINS A's, with 0 contradictions",
          f"{len(ev['A'])} ⊂ {len(ev['B'])} rows, {len(dis)} disagreeing")
    check(ev["Aslot8"][0]["instrument"] == "Timpani"
          and ev["Bslot8"][0]["instrument"] == "Trumpet",
          "yet slot 8 is Timpani(label) in A and Trumpet(ambiguity) in B",
          "more evidence, no contradiction, worse answer — the join is NOT "
          "monotone in evidence")
    check(a.by_source.get("score_order_ambiguity", (0, 0, 1))[0]
          / a.by_source.get("score_order_ambiguity", (0, 0, 1))[2] == 1.0
          and b.by_source["score_order_ambiguity"][0]
          / b.by_source["score_order_ambiguity"][2] == 0.5,
          "the PROVENANCE SPLIT localises the entire loss to one source",
          "score_order_ambiguity 51/51 = 1.000 in A, 51/102 = 0.500 in B, "
          "while `label` is 0.9907 / 1.0000 — the split is why this is "
          "diagnosable at all")


def main() -> int:
    for t in (test_1_group_map, test_2_span_reference_fit, test_3_bracket_columns,
              test_4_shape_agreement, test_5_key_sets, test_6_coverage,
              test_7_read_pass_floor):
        t()
    print("\n".join(LINES))
    print()
    if FAILS:
        print(f"THE GATE FAILS: {len(FAILS)} assertion(s)")
        for f in FAILS:
            print(f"   - {f}")
        return 1
    print("THE GATE PASSES: the harness reproduces every known fault, "
          "and reports none of them under the shipped defaults.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
