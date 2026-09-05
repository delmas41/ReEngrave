#!/usr/bin/env python3
"""The roster READ, not handed over — replacing the oracle-roster ceiling.

⚠️ THIS IS THE ARM THAT MATTERS. `probe_page1_roster.py` reached coverage 1.000
at precision 0.903, but it was handed the HAND-READ page-1 roster, so it
measured the JOIN with acquisition held perfect. Every figure from it is a
ceiling. This probe reads the roster page the way the pipeline actually would —
the full label ladder, no hand truth in the loop — and reports the two steps
SEPARATELY:

    ACQUISITION  did we get the roster off the page, and was it right?
    JOIN         given whatever acquisition ACTUALLY produced, errors and all,
                 how do coverage and precision hold up on later pages?

⚠️ THE JOIN IS FED THE ACQUIRED ROSTER, NEVER THE HAND-READ ONE. A wrong roster
is the failure mode the ceiling arms cannot see, and the prediction under test
is that a MISSING entry is survivable (order still constrains) while a MISNAMED
one poisons its neighbours.

⚠️ An acquired roster is PARTIAL by nature — Litolff labels winds and brass and
never the strings — so a roster read from the page has holes. Two ways to use
one, measured separately, because they are different claims:

    DENSE   the read entries in order, as the whole reference. Holes are simply
            absent, so the DP has fewer parts than the page has staves.
    SPARSE  the read entries pinned at their OWN ordinals, with unread
            positions left as wildcards that match anything.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_real_acquisition.py

── RESULT 2026-09-05: THE CEILING IS REPLACED. THE HONEST FIGURE IS 0.876. ───

ACQUISITION — the roster read with the real ladder, against hand-read truth:

    beethoven-575951  12/12 named, 12/12 correct   (text layer)
    beethoven-984073  12/12 named, 12/12 correct   (Surya)
    brahms-317803     12/14 named, 12/12 correct   (Surya) — ords 5,6 UNREAD
    dvorak-405834     15/15 named, 15/15 correct   (Surya)

⭑ ACQUISITION PRECISION IS 1.000 — 51 of 51 named positions correct, ZERO
misnamed. Coverage 51/53 = 0.962. The reader either names a staff correctly or
says nothing; it does not invent.

JOIN, fed the ACQUIRED roster (n=145 staves on pages after the roster page):

    ORACLE roster (the ceiling)              cov 1.000   prec 0.903
    ACQUIRED, holes DROPPED                  cov 1.000   prec 0.848
    ACQUIRED, holes KEPT as wildcards        cov 1.000   prec 0.841   REFUTED
    ACQUIRED, holes HEALED by layout prior   cov 1.000   prec 0.876

⚠️ SO THE COST OF REAL ACQUISITION IS 0.903 -> 0.876, and every 0.903 quoted
before this probe did not include it.

⚠️⚠️ THE PREDICTION WAS HALF RIGHT AND NEEDS SHARPENING. It was that a MISSING
roster entry is survivable (order still constrains) while a MISNAMED one
poisons its neighbours. This corpus produced ZERO misnamed entries, so that
half is untested. And missing entries were NOT survivable: 2 holes cost 8 join
errors. All 8 are Brahms, all 8 are the two HORN staves, and all 8 come out
`Trumpet` — because ords 5 and 6 are the ONLY Horn entries in that roster, so
failing to read them removed HORN FROM THE VOCABULARY ENTIRELY. No amount of
order recovers a name the roster does not contain.

    THE SHARPER RULE: a missing roster entry is survivable IFF that instrument
    still appears elsewhere in the roster. When every instance of an instrument
    goes unread, the roster loses the vocabulary item and every staff of that
    instrument is misnamed.

⚠️ THE WILDCARD FIX IS REFUTED (0.848 -> 0.841). I predicted that preserving the
roster's LENGTH — the page's staff count is observed, so keeping unread
positions as neutral placeholders costs nothing — would recover the loss. It
does not, and is slightly worse. A placeholder is not the missing NAME, and the
length was never what was lost.

✅ HEALING THE HOLES FROM THE SCORE-ORDER PRIOR RECOVERS HALF (0.848 -> 0.876,
4 of the 8). This is the layout prior in its proper, narrow role: filling a gap
BETWEEN two read names in an otherwise-known lineup, not selecting a lineup.
The 4 it cannot recover are the second Horn staff — the layouts hold ONE `Horn`
entry and Brahms prints two, which is the multiplicity finding again.

⚠️⚠️ HEALING IS CLOSED — NOT STAGED, NOT DEFERRED (Sean, 2026-09-05). It is not
being built, and this measurement stands only as the record of what it was
worth. The reasoning, so it is not re-proposed as an obvious idea:

  · THE CATALOG TIER SUBSUMES IT. The Brahms failure was that `Horn` dropped
    out of the roster's VOCABULARY — the label read `in Es 3 4`, a key
    qualifier with no noun, so nothing resolved. Healing INFERS "a Horn belongs
    in this gap" from the gap's position. IMSLP STATES the instrumentation for
    223 of 223 held works and says four horns outright. That is EVIDENCE rather
    than inference, at near-total coverage, arriving at download time with the
    file.
  · THE DIVISION OF LABOUR IS CLEANER: the catalog supplies WHICH instruments
    exist, order supplies WHERE they sit. Healing was a way of guessing the
    first from the second.
  · AND IT COULD NEVER FIX THE HALF THAT MATTERED. Four of the eight Brahms
    errors are the SECOND Horn staff, where the layouts hold one `Horn` entry
    against two printed staves. **Healing tops out exactly where multiplicity
    begins**; a catalog roster saying `4 horns` has no such ceiling.

The residual — a document with no catalog entry AND a partial page read (a work
not on IMSLP, or an arrangement whose work roster is wrong anyway) — is thin
and deliberately gets no mechanism.

⚠️ n = 4 editions, 3 engravings, 145 staves. Acquisition precision 1.000 rests
on 51 positions.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                     # noqa: E402
from tools.omr.score_layouts import ScoreLayout, fit_layouts  # noqa: E402

IDENT = HERE / "heldout-identity.json"
FIX = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
       "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
CACHE = HERE / "acquired-rosters.json"


def read_roster(rid):
    """Read the roster page's margin with the real ladder. Cached."""
    from tools.omr.assist import Assist
    from tools.omr.contextual import _labels_for_page
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves

    d = json.loads(Path(f"{FIX}/{rid}.reconciliation.omr.json").read_text())
    pdf = Path(d["source_pdf"])
    pi = d["pages"][0]["page_index"]
    pws = detect_staves(render_page(pdf, pi, dpi=d["dpi"]))
    tiers = [0, 0, 0, 0, 0]
    labs = _labels_for_page(pws, pdf, pi, assist=Assist("none"), budget=[0],
                            surya_fallback=True, ocr_fallback=True, tiers=tiers)
    sysof = defaultdict(list)
    for st in pws.staves:
        sysof[st.system_index].append(st)
    for k in sysof:
        sysof[k].sort(key=lambda s: s.line_ys[0])
    idx = {}
    for si, sts in sysof.items():
        for i, s in enumerate(sts):
            idx[s.staff_index] = (si, i)
    out = defaultdict(dict)
    for l in labs:
        si, i = idx.get(l.staff_index, (None, None))
        if si is None:
            continue
        out[si][i] = {"text": l.text,
                      "instrument": l.instrument.name if l.instrument else None,
                      "confidence": l.confidence}
    first = min(out) if out else None
    return {"page_index": pi, "tiers": tiers,
            "n_staves": len(sysof[first]) if first is not None else 0,
            "read": {str(k): v for k, v in (out.get(first) or {}).items()}}


def main():
    ident = json.loads(IDENT.read_text())
    by_sys = defaultdict(list)
    for r in ident["records"]:
        if r["TRUTH"]:
            by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])

    rosters = {}
    for (rid, sidx), g in by_sys.items():
        w = rid.rsplit("-p", 1)[0]
        p = int(rid.rsplit("-p", 1)[1])
        if w not in rosters or (p, sidx) < rosters[w][0]:
            rosters[w] = ((p, sidx), [r["TRUTH"] for r in g], rid)

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    for w, (_k, _lineup, rid) in sorted(rosters.items()):
        if rid not in cache:
            print(f"  reading roster page of {w} ({rid}) ...", flush=True)
            cache[rid] = read_roster(rid)
    CACHE.write_text(json.dumps(cache, indent=1))

    # ── ACQUISITION ─────────────────────────────────────────────────────────
    print(f"\n{'='*74}\nACQUISITION — the roster as READ, against the hand-read"
          f" truth\n{'='*74}")
    acquired = {}
    for w, (_k, hand, rid) in sorted(rosters.items()):
        rec = cache[rid]
        read = {int(i): v for i, v in rec["read"].items()}
        n = len(hand)
        got = {i: v["instrument"] for i, v in read.items() if v["instrument"]}
        right = sum(1 for i, nm in got.items()
                    if i < n and nm in
                    (ident["records"][0]["TRUTH_acceptable"] if False else [hand[i]])
                    or (i < n and nm == hand[i]))
        wrong = {i: (hand[i] if i < n else None, nm)
                 for i, nm in got.items() if i >= n or nm != hand[i]}
        acquired[w] = {"read": got, "n": n, "rid": rid,
                       "roster_staves": rec["n_staves"]}
        print(f"\n  {w}  ({rid}, page {rec['page_index']}, tiers {rec['tiers']})")
        print(f"    staves {rec['n_staves']}   positions NAMED {len(got)}/{n}"
              f" = {len(got)/n:.3f}   of those CORRECT {right}/{len(got)}"
              f" = {right/len(got) if got else 0:.3f}")
        if wrong:
            for i, (t, gname) in sorted(wrong.items()):
                print(f"      ⚠️ ord {i:2d}: truth {t} -> READ AS {gname}")
        missing = [i for i in range(n) if i not in got]
        print(f"    positions NOT named: {missing}")

    # ── JOIN, on the ACQUIRED roster ────────────────────────────────────────
    print(f"\n{'='*74}\nJOIN — fed the ACQUIRED roster, errors and holes"
          f" included\n{'='*74}")

    def run(mode):
        tot = named = right = 0
        for (rid, sidx), g in by_sys.items():
            w = rid.rsplit("-p", 1)[0]
            key, hand, src = rosters[w]
            if (int(rid.rsplit("-p", 1)[1]), sidx) == key:
                continue
            got = acquired[w]["read"]
            n_r = acquired[w]["n"]
            if mode == "oracle":
                parts = list(hand)
            elif mode == "healed":
                # HEAL THE HOLES FROM THE SCORE-ORDER PRIOR. The roster page's
                # staff COUNT and the read names are both page-derived; the
                # layouts supply only what sits BETWEEN two read names. This is
                # the layout prior in its proper, narrow role — filling a gap in
                # an otherwise-known lineup, not selecting a lineup.
                n_pos = acquired[w]["roster_staves"]
                fit_r = fit_layouts(n_pos, labels={i: v for i, v in got.items()},
                                    clefs=None)
                parts = [got.get(i) or (fit_r.assignment[i] if fit_r else None)
                         or f"__unread_{i}__" for i in range(n_pos)]
            elif mode == "dense":
                parts = [got[i] for i in sorted(got)]
            else:  # WILDCARD — read entries pinned at their OWN ordinals, and
                   # every unread position kept as a NEUTRAL placeholder so the
                   # roster's LENGTH survives.
                   #
                   # ⚠️ The length is page-derived, not truth: the roster page's
                   # staff COUNT is observed directly, so knowing "14 staves, 12
                   # named" costs nothing. DENSE throws that away and hands the
                   # DP a 12-part reference for a 14-staff page, which
                   # reintroduces exactly the skip/continue freedom ORDINAL
                   # avoids. A placeholder name is in no lexicon, so it
                   # contributes no clef term and matches nothing — a staff
                   # assigned one is an ABSTENTION, never a wrong name.
                n_pos = acquired[w]["roster_staves"]
                parts = [got.get(i) or f"__unread_{i}__" for i in range(n_pos)]
            if not parts:
                continue
            clefs = {i: r["clef_read"] for i, r in enumerate(g)
                     if r["clef_read"]}
            lay = (ScoreLayout("roster", tuple(parts), ""),)
            fit = fit_layouts(len(g), labels=None, clefs=clefs or None,
                              layouts=lay)
            for i, r in enumerate(g):
                tot += 1
                p = fit.assignment[i] if fit else None
                if p:
                    named += 1
                    if p in r["TRUTH_acceptable"]:
                        right += 1
        return tot, named, named / tot if tot else 0, right, (
            right / named if named else 0)

    print(f"  {'arm':34s} {'n':>4s} {'named':>6s} {'cov':>7s} {'right':>6s}"
          f" {'prec':>7s}")
    for mode, label in (("oracle", "ORACLE roster (the ceiling)"),
                        ("dense", "ACQUIRED, holes DROPPED"),
                        ("wildcard", "ACQUIRED, holes KEPT as wildcards"),
                        ("healed", "ACQUIRED, holes HEALED by layout prior")):
        tot, named, cov, right, prec = run(mode)
        print(f"  {label:34s} {tot:4d} {named:6d} {cov:7.3f} {right:6d}"
              f" {prec:7.3f}")
    print(f"\n  ⚠️ The acquired arm is the honest one. The gap between the two"
          f" IS the cost of\n     acquisition, and it is what every 0.903"
          f" quoted so far did not include.")


if __name__ == "__main__":
    main()
