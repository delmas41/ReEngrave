"""Grade staff IDENTITY on Brahms 1 / Breitkopf's FULL systems, against a
hand-read truth.

Sibling of `benchmarks/omr-absent-instrument-veto-2026-09/probe/
score_full_systems.py`, and the same discipline:

* only FULL systems are scored — a system carrying every staff its region
  prints, identified as "a system of exactly N staves in a region whose maximum
  is N".  Nothing can be added to a full lineup, so a full system IS the
  lineup, in printed order;
* REDUCED systems (tacet staves suppressed) are NOT scored, because which parts
  were dropped is a fact about the page this harness does not know;
* the names below are the canonical `instruments.Instrument.name` values a
  MUSICIAN would give, not what the lexicon returns — so a lexicon fault shows
  as an error instead of scoring correct against itself.

What differs is the INPUT.  `score_full_systems.py` reads a transcription whose
staff dicts carry `instrument`; this reads a `compose.py` blob, which records
the join instead — `staff_slots` maps (page, system, staff) to a slot and
`slot_instruments` names the slots.  That is the only artifact the
`OMR_SPAN_REFERENCE_FIT` arms were written to, and both arms come off ONE
shared read pass, so a difference between them is that flag and nothing else
(asserted below on the staff-record KEY SET, not just its size).

Truth provenance, and why it is admissible: read off the PRINTED PAGE at 600
dpi (`probe/margins.py`, crops in `out/crops/`).  Not from the reference
MusicXML — that is `source_kind: encoding` and the benchmarks score against it
— and not from an OMR output, which is what is being graded.  The work's IMSLP
roster (`data/score-library/catalog.json`, `source_kind: catalog`) corroborates
the inventory and is independent of the encoding: 2 fl, 2 ob, 2 cl, 2 bsn +
contrabassoon, 4 hn, 2 tpt, **3 trombones, 0 tuba**, timp, strings.

Usage:  score_brahms_lineups.py TAG=BLOB.json [TAG=BLOB.json ...] [--veto on|off|both]
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

#: (first_page, last_page, size) -> lineup, top to bottom.
#:
#: Every entry was read off the print.  The reading and the pages it was read
#: on are in FINDINGS.md; the crops are in `out/crops/`.
LINEUPS = {
    "brahms1": [
        # ── movement 1, FOURTEEN staves ──────────────────────────────────
        # Read in full at `p000-margin-all-sys0{,b}.png`, where Breitkopf sets
        # the whole name: 2 Flöten / 2 Oboen / 2 Klarinetten in B / 2 Fagotte /
        # Kontrafagott / 4 Hörner in C 1.2. / 4 Hörner in Es 3.4. /
        # 2 Trompeten in C / Pauken in C u. G / 1. Violine / 2. Violine /
        # Bratsche / Violoncell / Kontrabaß.
        # Corroborated on the abbreviated continuation systems p004 sy0,
        # p017 sy1 and p025 sy0 — same fourteen, same order.
        (0, 25, 14, ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                     "Horn", "Horn", "Trumpet", "Timpani", "Violin", "Violin",
                     "Viola", "Cello", "Contrabass"]),
        # ── movement 2, from the violin-solo entry, FOURTEEN staves ───────
        # A DIFFERENT lineup of the same size, and the reason the span bug
        # existed: SIX string staves (Viol. Solo above 1. and 2. Violine) and
        # ONE horn staff.  Read at `p033-margin-all-{C,D}.png` (bar 92) and
        # `p035-margin-all-{C,D}.png` (bar 120): Fl. / Ob. / Klar.(A) / Fag. /
        # K.-Fag. / Hr.(E) / Trpt.(E) / Pk. / Viol. Solo / 1.Viol. / 2.Viol. /
        # Br. / Vcl. / K.-B.
        # These are the ONLY two 14-staff systems on pages 26-44.
        (33, 35, 14, ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                      "Horn", "Trumpet", "Timpani", "Violin", "Violin",
                      "Violin", "Viola", "Cello", "Contrabass"]),
        # ── movement 3, TWELVE staves ────────────────────────────────────
        # `p036-margin-all-look.png` is the movement's opening system — "Un
        # poco Allegretto", full names, twelve staves: 2 Flöten / 2 Oboen /
        # 2 Klarinetten in B / 2 Fagotte / 4 Hörner in Es 1.2. / 4 Hörner in
        # H basso 3.4. / 2 Trompeten in H / 1. Violine / 2. Violine /
        # Bratsche / Violoncell / Kontrabaß.
        # ⚠️ NO Kontrafagott and NO Pauken — this movement uses neither, which
        # is why its full system is twelve staves and not fourteen.
        # Corroborated on p041 sy0 (bar 87): Fl./Ob./Klar.(B)/Fag./Hr.(Es)/
        # Hr.(H)/Trpt.(H)/…
        (36, 44, 12, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Horn",
                      "Trumpet", "Violin", "Violin", "Viola", "Cello",
                      "Contrabass"]),
        # ── finale, SIXTEEN staves ───────────────────────────────────────
        # Read in full at `p045-margin-all-{A,B,C}.png`, the finale opening:
        # 2 Flöten / 2 Oboen / 2 Klarinetten in B / 2 Fagotte / Kontrafagott /
        # 4 Hörner in C 1.2. / 4 Hörner in E 3.4. / 2 Trompeten in C /
        # **3 Posaunen braced over TWO staves** (alto C clef, then bass) /
        # Pauken in C u. G / 1. Violine / 2. Violine / Bratsche / Violoncell /
        # Kontrabaß.
        # Corroborated on p049 sy0, p076 sy0 and p084 sy0 (Fl./Ob./Klar./Fag./
        # K.-Fag./Hr./Trpt./Pos.×2/Pk./1.Viol./2.Viol./Br./Vcl./K.-B.).
        # ⚠️ Slot 9 is the SECOND TROMBONE staff, not a tuba — Brahms 1 has no
        # tuba (IMSLP `InstrDetail`: "3, 0" for trombones, tuba).
        (45, 85, 16, ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                      "Horn", "Horn", "Trumpet", "Trombone", "Trombone",
                      "Timpani", "Violin", "Violin", "Viola", "Cello",
                      "Contrabass"]),
    ],
}


def blob_of(path: str) -> dict:
    r = json.loads(Path(path).read_text())
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not b:
        raise SystemExit(f"REFUSING: {path} carries no absent_instrument_veto "
                         "block — it is not a compose.py `report` run")
    return b


def arm(blob):
    """(emitted-name-by-key, size-by-system, key-set), for one veto setting."""
    slot = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
            for s in blob["staff_slots"]}
    name = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
    vet = {(v["page_index"], v["system_index"], v["staff_index"])
           for v in blob["vetoes"]}
    return slot, name, vet


def score(work, blob, veto_on):
    slot, name, vet = arm(blob)
    size = collections.Counter()
    for (p, sy, _st) in slot:
        size[(p, sy)] += 1

    # group into systems, top to bottom by staff_index (page-wide, ascending)
    sysstaves = collections.defaultdict(list)
    for (p, sy, st) in slot:
        sysstaves[(p, sy)].append(st)
    for v in sysstaves.values():
        v.sort()

    def truth_for(page, n):
        for lo, hi, k, names in LINEUPS[work]:
            if lo <= page <= hi and n == k:
                return f"p{lo}-{hi}/{k}", names
        return None, None

    scored = []
    for (p, sy), stx in sorted(sysstaves.items()):
        tag, names = truth_for(p, len(stx))
        if names is not None:
            scored.append(((p, sy), stx, names, tag))

    correct = unnamed = wrong = 0
    conf = collections.Counter()
    by_size = collections.Counter()
    by_size_ok = collections.Counter()
    per_lineup = collections.Counter()
    per_lineup_ok = collections.Counter()
    per_lineup_sys = collections.Counter()
    for (p, sy), stx, names, ltag in scored:
        per_lineup_sys[ltag] += 1
        for i, st in enumerate(stx):
            key = (p, sy, st)
            got = None
            if not (veto_on and key in vet):
                s = slot[key]
                got = name.get(s) if s is not None and s >= 0 else None
            want = names[i]
            by_size[len(stx)] += 1
            per_lineup[ltag] += 1
            if got is None:
                unnamed += 1
                conf[(want, "(unnamed)")] += 1
            elif got == want:
                correct += 1
                by_size_ok[len(stx)] += 1
                per_lineup_ok[ltag] += 1
            else:
                wrong += 1
                conf[(want, got)] += 1
    n = correct + unnamed + wrong
    return dict(systems=len(scored), staves=n, correct=correct,
                unnamed=unnamed, wrong=wrong, conf=conf,
                by_size=by_size, by_size_ok=by_size_ok,
                per_lineup=per_lineup, per_lineup_ok=per_lineup_ok,
                per_lineup_sys=per_lineup_sys,
                all_systems=len(sysstaves), all_staves=len(slot),
                keys=set(slot))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="TAG=path/to/blob.json")
    ap.add_argument("--work", default="brahms1")
    ap.add_argument("--veto", default="off", choices=["off", "on", "both"])
    args = ap.parse_args()

    pairs = [a.split("=", 1) for a in args.arms]
    vetos = [False, True] if args.veto == "both" else [args.veto == "on"]

    keyset = None
    rows = []
    for tag, path in pairs:
        blob = blob_of(path)
        for veto_on in vetos:
            r = score(args.work, blob, veto_on)
            if keyset is None:
                keyset = r["keys"]
            elif r["keys"] != keyset:
                raise SystemExit(
                    "REFUSING: the arms do not share a staff-record key set "
                    f"({len(r['keys'] ^ keyset)} keys differ) — they did not "
                    "come off one read pass, so a difference between them is "
                    "not the flag under test")
            rows.append((tag, veto_on, r))

    r0 = rows[0][2]
    print(f"INPUT ASSERTION: systems-in-run={r0['all_systems']} "
          f"staff-records-in-run={r0['all_staves']}  ->  "
          f"FULL systems scored={r0['systems']} "
          f"staff-records-scored={r0['staves']} "
          f"({r0['staves'] / r0['all_staves']:.1%} of the document)")
    print("INPUT ASSERTION: every arm shares one staff-record key set "
          f"({len(keyset)} keys), so a difference below is the flag")
    print()
    print(f"{'arm':16s} {'veto':5s} {'judgeable':>10s} {'correct':>9s} "
          f"{'wrong':>7s} {'unnamed':>8s}   rate")
    for tag, veto_on, r in rows:
        print(f"{tag:16s} {'on' if veto_on else 'off':5s} {r['staves']:10d} "
              f"{r['correct']:9d} {r['wrong']:7d} {r['unnamed']:8d}   "
              f"{r['correct'] / r['staves']:.4f}")
    print()
    for tag, veto_on, r in rows:
        print(f"--- {tag}  veto={'on' if veto_on else 'off'}")
        for k in sorted(r["per_lineup"]):
            print(f"      lineup {k:12s} ({r['per_lineup_sys'][k]:2d} systems): "
                  f"{r['per_lineup_ok'][k]:4d}/{r['per_lineup'][k]:4d} = "
                  f"{r['per_lineup_ok'][k] / r['per_lineup'][k]:.4f}")
        print("    confusions (truth -> emitted), most common first:")
        for (want, got), c in r["conf"].most_common(30):
            print(f"      {c:5d}  {want:16s} -> {got}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
