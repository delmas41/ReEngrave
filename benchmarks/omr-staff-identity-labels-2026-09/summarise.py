#!/usr/bin/env python3
"""The Phase-1 table: every unresolved staff in exactly one class, with counts.

Joins `classified.json` (the reader/lexicon outcome per staff) to
`margin-ink.json` (was any ink printed there at all), producing the split the
workstream was opened to produce:

    (a)  no label printed        — a wall; no reader change reaches it
    (b)  printed, crop misses it — a crop fix
    (b') printed ONCE for a braced group, claimed by one staff — a match-rule fix
    (c)  crop right, OCR empty   — a reader question
    (d)  OCR read it, lexicon refused it     — lexicon work
    (e)  lexicon resolved it WRONG           — lexicon work

(b') is not in the brief's five. It was found, not posited: `Sechs Hörner in F`
is engraved once across a braced pair and `staff_labels`' matching rule gives it
to whichever staff's band its centre lands in.

The (d) strings are grouped by CAUSE, because "37 refusals" is not actionable
and "three missing aliases, on four staves of every Breitkopf system" is.

════════════════════════════════════════════════════════════════════════════
MEASURED 2026-09-05 on `24911c35` (origin/main). 20 scan-benchmark rows,
407 staves, 5 publishers, 6 works. The findings file this would normally
accompany could not be written (harness refusal); the record is here and in
the commit message.

    resolved (agrees with printed truth)          120
    resolved (row has no hand-read truth)         137
    (a) NO LABEL PRINTED AT ALL                   115      <- 77% of the shortfall
    (b) printed, the crop misses it                 0      <- ZERO
    (b') printed once for a braced group            1
    (c) crop right, OCR empty                       1
    (d) OCR read it, lexicon refused it            29
    (e) lexicon resolved it WRONG                   4
                                                  ---
                                                  407

    coverage, all staves          257/407 = 0.631
    coverage, REACHABLE staves    257/292 = 0.880

⚠️ Not comparable to the audit's 0.710 — that scored 155 staves over the 11
rows with committed fixtures; this scores all 20 rows, adding nine
continuation pages, which is exactly where labels stop being printed.

THE CROP IS NOT THE PROBLEM. Every continuation system is edge-clipped
(x_ref < 30·spacing, so x0 = 0) and that is a SYMPTOM: a page printing no
margin names begins its music nearer the page edge. Breitkopf is
edge-clipped on all six of its systems and resolves 10-13 of 14 each.

(a) IS PROVEN BY INK, NOT ASSERTED. Blank Litolff/Simrock margins measure 0
ink px over bands of 100k-260k; a printed `Tr.` measures thousands. 115 of
146 unresolved staves read 0 or 30. All 31 with real ink were looked at.

(d)/(e) ARE FOUR DEFECTS, NOT 33. `Hr.`, `Trpt.`, `Contrafagott` are absent
from the lexicon while `Cor. (Es)`, `Tpt.`, `Kontrafagott` resolve — so they
are omissions, not ambiguities. `K-Fag.` resolves to **Bassoon** (substring
`fag` beating the compound; the `Tr. Alt.` shape). The remaining 13 are
GROUP-LABEL FRAGMENTS — `(Es)`, `I`, `III` — where the name is engraved once
across a bracket and no lexicon entry can reach them; that is a match-rule
question (`MAX_STAFF_DISTANCE_FRAC`), not a lexicon one.

THE CEILING. Even a perfect lexicon and a perfect match rule take coverage
from 0.631 to 0.713 here, because 115 staves are unreachable. And the paid
vision rung cannot help: its own prompt tells it to return null for an
unlabelled staff, which is the correct answer on all 115.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

# Hand-adjudicated, from the images in `ink-suspects/` — the only two staves
# where the margin carries ink and no rung read a label.
HAND = {
    ("mahler-sym5-mvt1-local-p2", 0, 6):
        ("b_prime_BRACE_SHARED",
         "'Sechs Hörner in F' is printed once across the braced horn pair and "
         "claimed by pos5; pos6 gets nothing"),
    ("mahler-sym5-mvt1-local-p5", 0, 12):
        ("c_OCR_EMPTY",
         "'Kl.Tr.' is printed and legible; Surya returned 1 label on this whole "
         "page and Tesseract missed this one"),
}

# ── why a refusal happened ──────────────────────────────────────────────────
# Every string below was checked against `instruments.lookup` on THIS tree.
#
# GAP_TOKENS are complete, ordinary abbreviations the lexicon simply lacks. The
# test is not "did it fail" but "is this a name a reader would recognise" —
# `Hr.` is Horn and `Trpt.` is Trompete in every German edition; `Cor. (Es)`
# and `Tpt.` already resolve, so these are omissions and not ambiguities.
GAP_TOKENS = ("hr", "trpt", "trp", "contrafagott", "k-fag", "kfg", "tromb")

# A DISCRIMINATOR is what a staff carries when the instrument NAME is printed
# once across a bracketed or braced group and only the part's key or number is
# engraved beside the individual staff: `(Es)` under a shared `Hr.`, `III` under
# a shared `Violino`. No lexicon entry can fix these — the name is not there.
import re as _re
_DISCRIM = _re.compile(r"^[\s|«(\[]*((in\s+)?[A-H](es|is|s|b)?|[IVX]+|\d+"
                       r"|\\frac\{\d\}\{\d\})[\s|)\].,]*$", _re.I)


def _cause(reads: dict) -> str:
    low = [t.lower() for t in reads.values()]
    for t in low:
        for g in GAP_TOKENS:
            if g in t:
                return "lexicon_gap"
    for t in reads.values():
        s = t.replace("\\frac{1}{2}", "").replace("\\frac{3}{4}", "").strip()
        if _DISCRIM.match(s) or _DISCRIM.match(t):
            return "group_label_fragment"
    return "ocr_misread"


def main() -> int:
    cl = json.loads((HERE / "classified.json").read_text())
    ink = {(r["row_id"], r["system"], r["position"]): r
           for r in json.loads((HERE / "margin-ink.json").read_text())}

    final = []
    for s in cl["staves"]:
        key = (s["row_id"], s["system"], s["position"])
        c = s["class"]
        note = ""
        if c in ("bc_EMPTY", "d_REFUSED"):
            if key in HAND:
                c, note = HAND[key]
            elif ink.get(key, {}).get("verdict") == "a_NO_INK":
                # Includes staves a rung answered with a `|` or a stray digit:
                # there is no ink to have read, so the string came off the
                # bracket. A refusal over a blank margin is class (a).
                c, note = "a_NO_LABEL_PRINTED", (
                    "0 ink px in the margin band"
                    + (f"; spurious read {list(s['reads'].values())}"
                       if s["reads"] else ""))
            elif c == "bc_EMPTY":
                c = "UNADJUDICATED"
        final.append({**s, "final_class": c, "note": note})

    (HERE / "phase1.json").write_text(json.dumps(final, indent=1))

    order = ["RESOLVED_OK", "RESOLVED_no_truth", "a_NO_LABEL_PRINTED",
             "b_CROP_MISSES", "b_prime_BRACE_SHARED", "c_OCR_EMPTY",
             "d_REFUSED", "e_WRONG", "UNADJUDICATED"]
    tot = Counter(s["final_class"] for s in final)
    scored = [s for s in final if s["truth_instrument"]]
    tsc = Counter(s["final_class"] for s in scored)

    print(f"{'class':26} {'all 407':>9} {'truth-scored':>13}")
    for k in order:
        if tot[k] or tsc[k]:
            print(f"{k:26} {tot[k]:>9} {tsc[k]:>13}")
    print(f"{'TOTAL':26} {sum(tot.values()):>9} {sum(tsc.values()):>13}")
    print()
    resolved = tot["RESOLVED_OK"] + tot["RESOLVED_no_truth"]
    print(f"label coverage, all staves:     {resolved}/{sum(tot.values())} "
          f"= {resolved / sum(tot.values()):.3f}")
    print(f"label coverage, truth-scored:   {tsc['RESOLVED_OK']}/{sum(tsc.values())} "
          f"= {tsc['RESOLVED_OK'] / sum(tsc.values()):.3f}")
    reach = sum(tot.values()) - tot["a_NO_LABEL_PRINTED"]
    print(f"REACHABLE (a label is printed): {reach}, of which resolved "
          f"{resolved} = {resolved / reach:.3f}")
    print()

    print("== (d) refusals by cause  (only staves where the margin HAS ink)")
    by_cause = Counter()
    ex = defaultdict(Counter)
    for s in final:
        if s["final_class"] != "d_REFUSED":
            continue
        c = _cause(s["reads"])
        by_cause[c] += 1
        ex[c][max(s["reads"].values(), key=len)] += 1
    for c, n in by_cause.most_common():
        print(f"  {n:>3}  {c}")
        for t, k in ex[c].most_common():
            print(f"          {k:>2}x {t!r}")
    print()

    print("== per row: reachable staves and what happened to them")
    per = defaultdict(Counter)
    for s in final:
        per[s["row_id"]][s["final_class"]] += 1
    hdr = ["RESOLVED_OK", "RESOLVED_no_truth", "a_NO_LABEL_PRINTED",
           "b_prime_BRACE_SHARED", "c_OCR_EMPTY", "d_REFUSED", "e_WRONG"]
    print(f"{'row':38} " + " ".join(f"{h[:9]:>9}" for h in hdr))
    for rid in sorted(per):
        c = per[rid]
        print(f"{rid:38} " + " ".join(f"{c[h]:>9}" for h in hdr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
