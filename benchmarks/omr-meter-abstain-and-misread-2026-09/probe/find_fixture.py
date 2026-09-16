#!/usr/bin/env python3
"""Find a document that ABSTAINS on its meter *and* MISREADS it.

⚠️ WHY THIS IS THE QUESTION. `OMR_METER_CARRY`'s cost side has never been
priced, and the 2026-09-16 pricing arm explained why: the carry only fires on a
system whose own meter reading FAILED, so a document that abstains nowhere has
no domain for it. Litolff Beethoven 5 abstains on 6 of 7 systems and reads its
one meter CORRECTLY, so the carry is never handed a wrong candidate. Breitkopf
Brahms 1 misreads badly and abstains nowhere. **The hazard needs both halves in
one document and no such document has been named.**

⚠️ THIS PROBE READS COMMITTED RECORDS ONLY. It cannot gather, so it cannot
discover a fixture that has never been run; what it CAN do is ask whether one
of the ~100 committed meter records already holds both halves, which is the
cheap question nobody asked. A negative here is a statement about the COMMITTED
CORPUS, never about the repertoire.

⚠️ GENERATION. `out/` holds several generations of the same fixtures (`m2`…`m7`)
and the cautionary + meter-in-force fixes landed BETWEEN them. Pooling them as
repeat runs of one tree is the exact error `omr-meter-corroboration-2026-09`
records costing a session its reach figures. So every row NAMES its generation
and the default is the NEWEST per (fixture, arm).
"""
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
#: ⚠️ EVERY committed meter record, not one directory. A first run globbed the
#: boundary dir alone and reported 68 of 105 records -- the Litolff carry and
#: from-bars records, i.e. the ABSTAINING document, live in their own
#: benchmark dirs and were invisible. A reach figure that silently covers two
#: thirds of the corpus is the "control that computes the wrong thing" shape.
OUT_DIRS = sorted({p.parent for p in ROOT.glob("benchmarks/*/out/*.meter.json")})

#: The OPENING meter each fixture's page actually prints, hand-read and sourced.
#: ⚠️ A fixture absent here ABSTAINS rather than being scored — an unknown truth
#: must never be converted into a definite answer, and a wrong entry here would
#: manufacture the very finding the probe is looking for.
OPENING_TRUTH = {
    # Litolff Beethoven 5 mvt 1 is 2/4 throughout pp.1-4 (CLAUDE.md, the rest
    # sizing and duration arms both state it; pp.61-63 are the 3/4 stretch).
    "lit012": ("2/4", "CLAUDE.md: Litolff Beethoven 5 mvt1 pp.1-4, 2/4 throughout"),
    "p012": ("2/4", "same document, --pages 0-2"),
    "lit6162": ("3/4", "CLAUDE.md: the printed 3/4 of p.62, hand-read off the print"),
    # Brahms 1 mvt 1 prints 6/8, one bar of 9/8 at m8, then 6/8.
    "brahms1eng": ("6/8", "CLAUDE.md: truth read off the encoding, 6/8 + one 9/8"),
    "brahms1scan": ("6/8", "same music, Breitkopf scan of the same 22 bars"),
    "p0p3": ("6/8", "Breitkopf Brahms 1 mvt1 pdf p0-3, 6/8"),
    # Brahms 1 finale: C -> cut C at m392, so the excerpt opens in C.
    "brahms4eng": ("C", "CLAUDE.md: Brahms 1 iv prints C then the cut C at m392"),
    # Beethoven 5 mvt 4 engraved boundary fixture: 4/4 -> 3/4 at 155, back at 209.
    "e209A": ("3/4", "boundary fixture at m209: the 3/4 stretch precedes the change"),
    "e209B": ("3/4", "same"),
    "e209C": ("3/4", "same"),
}

#: ⚠️ A SYSTEM WHOSE LEGITIMATE OPENING IS NOT THE DOCUMENT'S. Brahms 1 mvt 1
#: prints ONE bar of 9/8 at m8, and on the engraved render that bar opens
#: system 1 -- so `system/1/0` reading `9/8` is CORRECT, and the per-document
#: truth above calls it a misread. Sourced from
#: `omr-staged-meter-boundary-2026-09/report_boundary.TRUTH_CHANGES`, which
#: records `("brahms1-m1-22", 1): (1, "6/8")` -- a change back to 6/8 at cell
#: 1, which only makes sense if the system OPENS in 9/8.
#: This is the probe's own false positive, found by opening the candidate
#: rather than by counting, and it is the reason `brahms1eng` is NOT the
#: answer. An entry here EXCUSES a reading; it never creates one.
SYSTEM_TRUTH = {
    ("brahms1eng", "system/1/0"): "9/8",
    ("brahms1scan", "system/0/0"): "6/8",   # its 9/8 is a cautionary segment
}

LENGTH = {"C": 4.0, "common": 4.0, "C|": 4.0, "cut": 4.0}


def length_of(raw):
    """A meter's length in quarter notes. `C` and `C|` are BOTH 4.0."""
    if not raw:
        return None
    if raw in LENGTH:
        return LENGTH[raw]
    try:
        n, d = raw.split("/")
        return float(n) * 4.0 / float(d)
    except Exception:
        return None


def parse_name(path):
    """-> (generation, fixture, arm). Generation 1 means unprefixed (oldest)."""
    stem = path.name[: -len(".meter.json")]
    m = re.match(r"^m(\d+)(.*)$", stem)
    gen, rest = (int(m.group(1)), m.group(2)) if m else (1, stem)
    if "-" in rest:
        fixture, arm = rest.rsplit("-", 1)
    else:
        fixture, arm = rest, "?"
    return gen, fixture, arm


def systems(path):
    """Per-system meter verdicts: (subject, outcome, reason, opening_raw)."""
    blob = json.load(open(path))
    # ⚠️ TWO COMMITTED REDUCTION SHAPES, AND THE SECOND HAS NO `quantity` KEY.
    # `omr-staged-meter-carry-2026-09` and its siblings commit a bare
    # {subject, outcome, reason, value, detail} list where every row IS a
    # meter verdict. A first version filtered on `quantity == "meter"` and
    # read 12 records -- including Litolff `p012`, THE ABSTAINING DOCUMENT --
    # as zero rows, then reported them in no bucket at all. The tell was not
    # the table: it was four fixtures carrying a truth and appearing in none
    # of the four answer buckets. A filter that silently empties a file looks
    # exactly like a file with nothing in it.
    quantified = any("quantity" in v for v in blob)
    rows = []
    for v in blob:
        if quantified and v.get("quantity") != "meter":
            continue
        val = v.get("value") or {}
        raw = val.get("raw") if isinstance(val, dict) else None
        rows.append({
            "subject": v.get("subject"),
            "outcome": v.get("outcome"),
            "reason": v.get("reason"),
            "opening": raw,
            "n_segments": len(val.get("segments") or []) if isinstance(val, dict) else 0,
            # ⚠️ REPORTED, NEVER SCORED AS A READING. `too_few_staves_read_it`
            # records what the vote WOULD have said; it is a suppressed
            # candidate, so counting it as a misread would score a reading the
            # pipeline correctly refused to make.
            "would_have_been": (v.get("detail") or {}).get("would_have_been"),
        })
    return rows


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    want_all_gens = "--all-generations" in argv

    paths = sorted(p for d in OUT_DIRS for p in d.glob("*.meter.json"))
    if not paths:
        print("DEAD: no committed meter records found under", OUT_DIRS)
        return 3

    parsed = [(parse_name(p), p) for p in paths]
    print("  source dirs:", len(OUT_DIRS))
    for d in OUT_DIRS:
        print("    %-58s %d" % (d.relative_to(ROOT), len(list(d.glob("*.meter.json")))))

    # ── REACH, before anything else ──────────────────────────────────────────
    fixtures = sorted({f for (_, f, _), _ in parsed})
    gens = sorted({g for (g, _, _), _ in parsed})
    print("=" * 74)
    print("REACH  (committed records only -- nothing was gathered)")
    print("=" * 74)
    print("  records   : %d" % len(paths))
    print("  fixtures  : %d  %s" % (len(fixtures), fixtures))
    print("  generations: %s" % gens)
    scored = [f for f in fixtures if f in OPENING_TRUTH]
    print("  fixtures with a hand-read OPENING truth: %d of %d  %s"
          % (len(scored), len(fixtures), scored))
    print("  fixtures ABSTAINED on (no truth entry): %s"
          % [f for f in fixtures if f not in OPENING_TRUTH])
    if not scored:
        print("\nDEAD: no fixture carries a truth, so nothing can be scored.")
        return 3

    # newest generation per (fixture, arm), unless asked for all
    newest = {}
    for (g, f, a), p in parsed:
        key = (f, a)
        if key not in newest or g > newest[key][0]:
            newest[key] = (g, p)
    chosen = (sorted(parsed, key=lambda t: (t[0][1], t[0][2], t[0][0]))
              if want_all_gens else
              sorted(((g, f, a), p) for (f, a), (g, p) in newest.items()))

    print()
    print("=" * 74)
    print("PER DOCUMENT: does it ABSTAIN, and does it MISREAD?")
    print("=" * 74)
    print("%-14s %-5s %-4s  %8s %8s  %-22s" %
          ("fixture", "arm", "gen", "systems", "abstain", "openings read"))
    print("-" * 74)

    verdict = collections.defaultdict(lambda: {"abstain": 0, "misread": 0,
                                               "systems": 0, "rows": []})
    for (gen, fixture, arm), path in chosen:
        rows = systems(path)
        if not rows:
            continue
        truth = OPENING_TRUTH.get(fixture)
        n_abstain = sum(1 for r in rows if r["outcome"] != "decided")
        openings = collections.Counter(r["opening"] for r in rows
                                       if r["outcome"] == "decided")
        n_misread = 0
        if truth:
            tl = length_of(truth[0])
            for r in rows:
                if r["outcome"] != "decided":
                    continue
                per_system = SYSTEM_TRUTH.get((fixture, r["subject"]))
                tl = length_of(per_system) if per_system else length_of(truth[0])
                rl = length_of(r["opening"])
                # A misread is a LENGTH disagreement OR a spelling one; both
                # are recorded, and a length disagreement is the harder fact.
                if rl is None or tl is None:
                    continue
                if abs(rl - tl) > 1e-9:
                    n_misread += 1
        mark = ""
        if truth and n_abstain and n_misread:
            mark = "  <<< ABSTAINS *AND* MISREADS"
        print("%-14s %-5s m%-3d  %8d %8d  %-22s%s" %
              (fixture, arm, gen, len(rows), n_abstain,
               ", ".join("%s x%d" % (k, v) for k, v in openings.most_common(3)),
               mark))
        v = verdict[fixture]
        v["abstain"] += n_abstain
        v["misread"] += n_misread
        v["systems"] += len(rows)
        v["rows"].append((arm, gen, n_abstain, n_misread))

    print()
    print("=" * 74)
    print("THE ANSWER")
    print("=" * 74)
    both, only_a, only_m, neither = [], [], [], []
    for f in scored:
        v = verdict.get(f)
        if not v:
            continue
        if v["abstain"] and v["misread"]:
            both.append(f)
        elif v["abstain"]:
            only_a.append(f)
        elif v["misread"]:
            only_m.append(f)
        else:
            neither.append(f)
    print("  ABSTAINS *and* MISREADS : %s" % (both or "NONE"))
    print("  abstains only           : %s" % (only_a or "none"))
    print("  misreads only           : %s" % (only_m or "none"))
    print("  neither                 : %s" % (neither or "none"))
    print()
    print("  ⚠️ POSITIVE CONTROL: the probe must be able to see BOTH halves")
    print("     somewhere, or a NONE above is the instrument. abstain>0 on %d"
          " fixture(s), misread>0 on %d fixture(s)."
          % (len(both) + len(only_a), len(both) + len(only_m)))
    if not (both or only_a) or not (both or only_m):
        print("     DEAD: one half is invisible to this probe.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
