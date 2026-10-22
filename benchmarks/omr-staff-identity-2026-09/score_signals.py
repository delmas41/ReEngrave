#!/usr/bin/env python3
"""Phase 2 of the staff-identity audit: the three scorecards.

    python3 benchmarks/omr-staff-identity-2026-09/score_signals.py

Reads `evidence.json` (Phase 1) and scores every signal for IDENTITY,
MULTIPLICITY and CONTINUITY. Per signal: coverage (how often it speaks),
precision when it speaks, and what it adds over the best cheaper signal.

Everything is conditioned on whether the clef was READ or DEFAULTED, because
S3 (key fitting is chosen by the clef) and S4 (pitch resolution consumes clef
and key) inherit S2's errors — the plan's dependency chain. Treating them as
independent votes would overstate any ensemble.

MEASUREMENT ONLY. Writes `scorecards.json`.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                     # noqa: E402


# ─────────────────────────────────────────── truth normalisation (scoring key)

def truth_instrument(row: dict) -> str | None:
    """The canonical instrument the hand-read printed label names.

    Uses `instruments.lookup`, i.e. the SAME lexicon S1 uses. That is the point:
    the truth is the printed string, and this maps it into the vocabulary every
    signal is scored in. It is a ceiling on S1 by construction (a perfect
    reader), which is exactly how the condensed-parts session isolated the
    rule's error from the reader's."""
    name = row.get("CEILING_hand_label")
    if not name:
        return None
    m = INST.lookup(name)
    return m.instrument.name if m else None


def truth_fifths_offset(row: dict) -> int | None:
    """The transposition the printed label implies (`Clarinetti in B` -> +2)."""
    name = row.get("CEILING_hand_label")
    if not name:
        return None
    m = INST.lookup(name)
    return m.fifths_offset if m else None


def family_of(instrument: str | None) -> str | None:
    if not instrument:
        return None
    for i in INST.INSTRUMENTS:
        if i.name == instrument:
            return i.family
    return None


# ──────────────────────────────────────────────────────────── scoring helpers

def score(rows, speaks, correct, name, note=""):
    spoke = [r for r in rows if speaks(r)]
    ok = [r for r in spoke if correct(r)]
    return {
        "signal": name, "n": len(rows), "spoke": len(spoke),
        "coverage": round(len(spoke) / len(rows), 4) if rows else None,
        "correct": len(ok),
        "precision": round(len(ok) / len(spoke), 4) if spoke else None,
        "note": note,
    }


def added_over(rows, base_speaks, base_correct, sig_speaks, sig_correct, name):
    """What the signal adds over a cheaper one: rows the base gets WRONG or is
    SILENT on, where the signal speaks and is right; minus rows the base gets
    right and the signal contradicts."""
    rescued = broken = 0
    for r in rows:
        base_ok = base_speaks(r) and base_correct(r)
        sig_ok = sig_speaks(r) and sig_correct(r)
        if not base_ok and sig_ok:
            rescued += 1
        if base_ok and sig_speaks(r) and not sig_correct(r):
            broken += 1
    return {"vs": name, "rescued": rescued, "contradicted_a_correct_base": broken,
            "net": rescued - broken}


# ────────────────────────────────────────────────────────── identity scorecard

def identity(E):
    rows = [r for r in E if truth_instrument(r) is not None]
    read_clef = [r for r in rows if not r["s2_defaulted"] and r["s2_source"]]
    def_clef = [r for r in rows if r["s2_defaulted"] or not r["s2_source"]]

    out = {"n_rows_with_identity_truth": len(rows),
           "n_clef_read": len(read_clef), "n_clef_defaulted": len(def_clef),
           "signals": [], "conditioned": {}, "added_value": [],
           "s8_block_purity": {}, "within_block_vs_pagewide": {}}

    S1 = (lambda r: r["s1_source"] == "label" and r["s1_instrument"],
          lambda r: r["s1_instrument"] == truth_instrument(r))
    S2 = (lambda r: bool(r["s2_source"]) and not r["s2_defaulted"],
          lambda r: r["s2_clef"] == r["TRUTH_clef"])
    # S2 as an IDENTITY signal: the clef narrows the family. Scored as "does the
    # clef the pipeline read agree with the clef the truth instrument's family
    # would print" — the narrowing, not the reading.
    S2fam = (lambda r: bool(r["s2_source"]) and not r["s2_defaulted"],
             lambda r: _clef_family_ok(r))
    S3 = (lambda r: r["s3_read"] and r["s3_implied_offset"] is not None,
          lambda r: truth_instrument(r) in (r["s3_candidates"] or []))
    S4 = (lambda r: (r["s4_n_notes"] or 0) >= 5,
          lambda r: truth_instrument(r) in (r["s4_range_compatible"] or []))
    S5 = (lambda r: bool(r["s5_exact_layouts"]),
          lambda r: truth_instrument(r) in _norm_set(r["s5_prediction_set"]))
    S5m = (lambda r: bool(r["s5_exact_layouts"]),
           lambda r: truth_instrument(r) == _norm(r["s5_prediction"]))
    S6 = (lambda r: r["s6_layout_instrument"] is not None,
          lambda r: _norm(r["s6_layout_instrument"]) == truth_instrument(r))

    defs = [("S1 margin label (pipeline reader)", *S1),
            ("S2 clef (reading accuracy)", *S2),
            ("S2 clef (family narrowing)", *S2fam),
            ("S3 key-signature offset (candidate set contains truth)", *S3),
            ("S4 pitch envelope (range admits truth)", *S4),
            ("S5 score-order prior (set contains truth)", *S5),
            ("S5 score-order prior (modal prediction exact)", *S5m),
            ("S6 slot/layout instrument (fused)", *S6)]

    for nm, sp, co in defs:
        out["signals"].append(score(rows, sp, co, nm))
        out["conditioned"].setdefault(nm, {})["clef_read"] = \
            score(read_clef, sp, co, nm)
        out["conditioned"][nm]["clef_defaulted"] = score(def_clef, sp, co, nm)

    # --- what each adds over the best CHEAPER signal ---------------------------
    # cheapest first: S5 (free, positional) < S8 (free, already computed)
    #   < S2 (clef, already read) < S3 (key, needs clef) < S4 (needs clef+key)
    #   < S1 (needs an OCR rung)
    out["added_value"] = [
        {"signal": "S3", **added_over(rows, S5[0], S5[1], S3[0], S3[1], "S5 set")},
        {"signal": "S3", **added_over(rows, S5m[0], S5m[1], S3[0], S3[1], "S5 modal")},
        {"signal": "S4", **added_over(rows, S5[0], S5[1], S4[0], S4[1], "S5 set")},
        {"signal": "S1", **added_over(rows, S5[0], S5[1], S1[0], S1[1], "S5 set")},
        {"signal": "S1", **added_over(rows, S5m[0], S5m[1], S1[0], S1[1], "S5 modal")},
    ]

    # --- THE KILL CRITERION: S3's transposition call vs the S5 prior alone -----
    out["kill_criterion_s3_vs_s5"] = _s3_vs_s5(rows)

    # --- S8 block purity ------------------------------------------------------
    blocks = defaultdict(list)
    for r in rows:
        blocks[(r["row_id"], r["page"], r["system"], r["s8_group_index"])].append(r)
    pure = total = 0
    detail = []
    for k, members in sorted(blocks.items(), key=lambda kv: str(kv[0])):
        fams = [family_of(truth_instrument(m)) for m in members]
        fams = [f for f in fams if f]
        if not fams:
            continue
        modal, cnt = Counter(fams).most_common(1)[0]
        total += 1
        if cnt == len(fams):
            pure += 1
        detail.append({"block": list(k), "size": len(members),
                       "families": dict(Counter(fams)), "modal": modal,
                       "purity": round(cnt / len(fams), 3)})
    out["s8_block_purity"] = {
        "n_blocks": total, "fully_pure_blocks": pure,
        "share_fully_pure": round(pure / total, 4) if total else None,
        "mean_purity": round(sum(d["purity"] for d in detail) / len(detail), 4)
        if detail else None,
        "detail": detail,
    }

    # --- within-block vs page-wide -------------------------------------------
    out["within_block_vs_pagewide"] = _within_block(rows)
    return out


_CLEF_FAMILY = {
    "treble": {"woodwind", "brass", "string", "voice", "keyboard", "percussion"},
    "bass": {"woodwind", "brass", "string", "keyboard", "percussion", "voice"},
    "alto": {"string"},
    "tenor": {"string", "brass", "woodwind"},
}


def _clef_family_ok(r) -> bool:
    fam = family_of(truth_instrument(r))
    allowed = _CLEF_FAMILY.get(r["s2_clef"])
    return bool(fam and allowed and fam in allowed)


_LAYOUT_ALIASES = {
    "Violin I": "Violin", "Violin II": "Violin", "Violin 1": "Violin",
    "Violin 2": "Violin", "Violoncello": "Cello", "Double bass": "Contrabass",
    "Contrabasses": "Contrabass", "Bass": "Contrabass",
}


def _norm(name):
    if not name:
        return None
    name = _LAYOUT_ALIASES.get(name, name)
    m = INST.lookup(name)
    return m.instrument.name if m else name


def _norm_set(names):
    return {_norm(n) for n in (names or [])}


def _s3_vs_s5(rows):
    """THE KILL CRITERION, stated in the plan: is S3's implied offset right more
    often than the score-order prior S5 alone?

    Framed as the crisp, decidable question rather than the candidate-set one
    (a candidate set that admits every key-dependent instrument trivially
    contains the truth): DOES THIS STAFF TRANSPOSE, and by how much?

      truth  = the fifths offset the printed label implies (`Clarinetti in B` +2)
      S3     = staff_fifths - page_modal_fifths, read off the page
      S5     = the offset of the instrument the score-order prior predicts here
    """
    s3_n = s3_ok = s3_sign_ok = 0
    s5_n = s5_ok = s5_sign_ok = 0
    both = both_s3 = both_s5 = 0
    confusion = Counter()
    for r in rows:
        t = truth_fifths_offset(r)
        if t is None:
            continue
        s3 = r["s3_implied_offset"] if r["s3_read"] else None
        pred5 = _norm(r["s5_prediction"]) if r["s5_exact_layouts"] else None
        s5 = None
        if pred5:
            for i in INST.INSTRUMENTS:
                if i.name == pred5:
                    s5 = i.default_fifths_offset
                    break
        if s3 is not None:
            s3_n += 1
            s3_ok += (s3 == t)
            s3_sign_ok += ((s3 != 0) == (t != 0))
            confusion[(t, s3)] += 1
        if s5 is not None:
            s5_n += 1
            s5_ok += (s5 == t)
            s5_sign_ok += ((s5 != 0) == (t != 0))
        if s3 is not None and s5 is not None:
            both += 1
            both_s3 += (s3 == t)
            both_s5 += (s5 == t)
    return {
        "s3": {"spoke": s3_n, "exact": s3_ok,
               "precision_exact": round(s3_ok / s3_n, 4) if s3_n else None,
               "transposes_yes_no": s3_sign_ok,
               "precision_transposes": round(s3_sign_ok / s3_n, 4) if s3_n else None},
        "s5": {"spoke": s5_n, "exact": s5_ok,
               "precision_exact": round(s5_ok / s5_n, 4) if s5_n else None,
               "transposes_yes_no": s5_sign_ok,
               "precision_transposes": round(s5_sign_ok / s5_n, 4) if s5_n else None},
        "head_to_head_where_both_speak": {
            "n": both, "s3_exact": both_s3, "s5_exact": both_s5},
        "s3_confusion_truth_to_predicted": {f"{k[0]}->{k[1]}": v
                                            for k, v in sorted(confusion.items())},
    }


def _within_block(rows):
    """Does scoring the other signals WITHIN an S8 bracket block beat scoring
    them page-wide?

    Page-wide: predict the modal family of every staff on the page (the best a
    page-level prior can do with no structure).
    Within-block: predict the modal family of the staff's own bracket block.
    Both use the SAME truth and the SAME oracle for the modal value, so this
    isolates what the block partition buys."""
    by_page = defaultdict(list)
    by_block = defaultdict(list)
    for r in rows:
        by_page[(r["row_id"], r["page"], r["system"])].append(r)
        by_block[(r["row_id"], r["page"], r["system"], r["s8_group_index"])].append(r)

    def modal_family_accuracy(groups):
        ok = n = 0
        for members in groups.values():
            fams = [family_of(truth_instrument(m)) for m in members]
            fams = [f for f in fams if f]
            if not fams:
                continue
            modal = Counter(fams).most_common(1)[0][0]
            ok += sum(1 for f in fams if f == modal)
            n += len(fams)
        return ok, n

    pw_ok, pw_n = modal_family_accuracy(by_page)
    bl_ok, bl_n = modal_family_accuracy(by_block)

    # the same comparison for the S5 order prior: restricted to the block's own
    # span vs the page's whole span
    return {
        "family_from_modal_pagewide": {
            "correct": pw_ok, "n": pw_n,
            "accuracy": round(pw_ok / pw_n, 4) if pw_n else None},
        "family_from_modal_within_block": {
            "correct": bl_ok, "n": bl_n,
            "accuracy": round(bl_ok / bl_n, 4) if bl_n else None},
        "delta": round((bl_ok / bl_n) - (pw_ok / pw_n), 4) if pw_n and bl_n else None,
    }


# ────────────────────────────────────────────────────── multiplicity scorecard

def multiplicity(E):
    rows = [r for r in E if r["TRUTH_n_parts"]]
    out = {"n": len(rows), "truth_distribution": dict(Counter(
        r["TRUTH_n_parts"] for r in rows)), "rules": [], "per_row": {}}

    def rule(name, fn, note=""):
        exact = over = under = 0
        per = defaultdict(lambda: [0, 0, 0])
        for r in rows:
            p = fn(r)
            if p is None:
                continue
            t = r["TRUTH_n_parts"]
            if p == t:
                exact += 1; per[r["row_id"]][0] += 1
            elif p > t:
                over += 1; per[r["row_id"]][1] += 1
            else:
                under += 1; per[r["row_id"]][2] += 1
        n = exact + over + under
        out["rules"].append({
            "rule": name, "spoke": n, "exact": exact, "over": over, "under": under,
            "accuracy": round(exact / n, 4) if n else None,
            "per_row_exact_over_under": {k: v for k, v in sorted(per.items())},
            "note": note})

    rule("always 1 (the shipped default — one part per printed staff)",
         lambda r: 1,
         "This is what the pipeline does today and what Audiveris does on every "
         "single-system row. It is the baseline every rule must beat.")

    rule("S7 texture: >=1 dyad or divisi bar => 2 parts",
         lambda r: 2 if (r["s7_dyad_bars"] or r["s7_divisi_bars"]) else 1)

    rule("S7 texture, stricter: >=25% of note bars carry a dyad => 2",
         lambda r: 2 if (r["s7_note_bars"] and
                         r["s7_dyad_bars"] / max(r["s7_note_bars"], 1) >= 0.25) else 1)

    rule("S8 block: a staff in a block of size 1 => 1, else 2",
         lambda r: 1 if (r["s8_group_size"] or 1) <= 1 else 2)

    rule("S8 brace: a brace detected on this staff => 1 (divisi across staves)",
         lambda r: 1 if r["s8_brace_detections"] else None,
         "abstains where no brace fires; 18 brace detections corpus-wide")

    rule("S9 placement: a dynamic printed in the gap nearer the NEIGHBOUR => 2",
         lambda r: 2 if r.get("s9_dyn_ambiguous", 0) else 1)

    # ⚠️ There is no PIPELINE-reader arm here: the transcription retains the
    # RESOLVED instrument, not the raw margin string the reader returned, and
    # `players_for_label` needs the string ("2 Flöten" -> 2 is invisible once
    # the string has become `Flute`). The reader's own accuracy was measured
    # separately by the condensed-parts session (`probe_real_labels.py`,
    # 12/12 on Beethoven 984073 p1) and is not re-derived here.

    rule("S1 label plurality (CEILING: hand-read printed string)",
         lambda r: _label_count(r["CEILING_hand_label"]),
         "This is the `label_ideal` arm of the condensed-parts session — the "
         "rule with a perfect reader, so its error is the RULE's.")

    rule("S7+S8+S9+S1-plurality combined (any says >1 => 2)",
         lambda r: 2 if any([
             r["s7_dyad_bars"] or r["s7_divisi_bars"],
             (r["s8_group_size"] or 1) > 1 and False,   # block size is not evidence
             r.get("s9_dyn_ambiguous", 0),
             (_label_count(r["CEILING_hand_label"]) or 1) > 1,
         ]) else 1,
         "The page-side ensemble Sean asked about. Block size is deliberately "
         "excluded: every orchestral block has >1 staff, so it fires everywhere.")

    rule("S7 AND S1-plurality (both must agree on >1)",
         lambda r: 2 if ((r["s7_dyad_bars"] or r["s7_divisi_bars"]) and
                         (_label_count(r["CEILING_hand_label"]) or 1) > 1) else 1)

    return out


_COND = None


def _label_count(label):
    global _COND
    if not label:
        return None
    if _COND is None:
        try:
            from tools.omr import condensed_parts as C
            _COND = C
        except Exception:
            _COND = False
    if not _COND:
        return None
    return _COND.players_for_label(label)


# ──────────────────────────────────────────────────────── continuity scorecard

def continuity(E):
    multi = [r for r in E if (r["n_systems_on_page"] or 1) > 1 and r["system"]]
    out = {"n_rows_on_a_later_system": len(multi), "rows": {}}
    by_row = defaultdict(list)
    for r in multi:
        by_row[r["row_id"]].append(r)
    for rid, rs in sorted(by_row.items()):
        cont = sum(1 for r in rs if r["s6_continuous_with_prev"])
        out["rows"][rid] = {
            "staves_on_later_systems": len(rs),
            "slot_continuous_with_previous_system": cont,
            "share": round(cont / len(rs), 4) if rs else None,
        }
    return out


def main():
    doc = json.loads((HERE / "evidence.json").read_text())
    E = doc["evidence"]
    cards = {
        "identity": identity(E),
        "multiplicity": multiplicity(E),
        "continuity": continuity(E),
    }
    (HERE / "scorecards.json").write_text(json.dumps(cards, indent=1) + "\n")

    I = cards["identity"]
    print(f"\n=== IDENTITY  (n={I['n_rows_with_identity_truth']}, "
          f"clef read {I['n_clef_read']} / defaulted {I['n_clef_defaulted']}) ===")
    print(f"{'signal':58s} {'cov':>6s} {'prec':>6s}  {'spoke':>5s}")
    for s in I["signals"]:
        print(f"{s['signal']:58s} {s['coverage'] or 0:6.3f} "
              f"{s['precision'] if s['precision'] is not None else float('nan'):6.3f} "
              f"{s['spoke']:5d}")
    print("\n-- conditioned on the clef --")
    for nm, c in I["conditioned"].items():
        a, b = c["clef_read"], c["clef_defaulted"]
        print(f"{nm:58s} read {a['precision']} ({a['spoke']})  "
              f"defaulted {b['precision']} ({b['spoke']})")
    print("\n-- what each ADDS over a cheaper signal --")
    for a in I["added_value"]:
        print(f"  {a['signal']} vs {a['vs']:12s} rescued {a['rescued']:3d}  "
              f"broke {a['contradicted_a_correct_base']:3d}  net {a['net']:+d}")
    print("\n-- KILL CRITERION: S3 vs S5 --")
    print(json.dumps(I["kill_criterion_s3_vs_s5"], indent=1))
    print("\n-- S8 block purity --")
    p = I["s8_block_purity"]
    print(f"  blocks {p['n_blocks']}, fully family-pure {p['fully_pure_blocks']} "
          f"({p['share_fully_pure']}), mean purity {p['mean_purity']}")
    print("\n-- within-block vs page-wide --")
    print(json.dumps(I["within_block_vs_pagewide"], indent=1))

    M = cards["multiplicity"]
    print(f"\n=== MULTIPLICITY  (n={M['n']}, truth {M['truth_distribution']}) ===")
    print(f"{'rule':62s} {'spoke':>5s} {'exact':>5s} {'over':>4s} {'under':>5s} {'acc':>6s}")
    for r in M["rules"]:
        print(f"{r['rule']:62s} {r['spoke']:5d} {r['exact']:5d} {r['over']:4d} "
              f"{r['under']:5d} "
              f"{r['accuracy'] if r['accuracy'] is not None else float('nan'):6.3f}")

    print(f"\n=== CONTINUITY ===")
    print(json.dumps(cards["continuity"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
