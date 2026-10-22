#!/usr/bin/env python3
"""Can a roster be ACQUIRED at all? — library-wide, per DOCUMENT.

MEASUREMENT ONLY. No transcription: one staff detection plus one Surya read per
probed page, ~5 s. That is the whole point of running it before anything else —
transcribing the same page costs ~280 s, and this workstream has already paid
once for having that order backwards.

WHY PER DOCUMENT AND NOT PER PAGE. The roster procedure needs a roster ONCE per
document; a roster acquired on page 40 still serves pages 41+. So "page 1 has
no labels" is not a failure — the failure is NO PAGE having them. Pages are
probed in the order a reader would try them and the first hit stops the search.

⚠️ REPORT THE DISTRIBUTION, NOT A MEAN. "70% of editions" and "every edition at
70%" are different worlds and only the first supports the procedure. This
workstream already measured that yield is NOT uniform: five Breitkopf plates
print no labels anywhere, one of them inside the very series the "Breitkopf
labels everything" claim was measured on.

⚠️ dpi 300 is used deliberately: measured identical to 600 on a known page
(10/12 named either way) at 0.3 s of detection instead of 0.8 s.

Resumable — one cache file per document, so a run that is interrupted loses
nothing and a re-run costs only the unprobed documents.

    python3 .../probe_roster_availability.py --plan
    python3 .../probe_roster_availability.py --limit 120
    python3 .../report_roster_availability.py      # read the cache, probe nothing

── FINAL RESULT 2026-09-05, ALL 234 DOCUMENTS ────────────────────────────────

    documents probed       234
    roster ACQUIRED        172   (0.735)
    no page yielded one     62   (0.265)

DISTRIBUTION of best yield (named labels / staves) — NOT a mean, and it is
BIMODAL, which is the finding:

         0.00    33   0.141   <- hard zeros: the page prints no names at all
    0.01-0.24     4   0.017
    0.25-0.49    25   0.107
    0.50-0.74    80   0.342
    0.75-0.99    78   0.333
         1.00    14   0.060

⭑ 14 of the 172 rosters (0.081) were acquired ONLY BEYOND THE FIRST THREE PAGES
(pages 3, 5, 8, 12). **"Page 1" is the wrong unit**, confirmed at full scale: a
per-page measurement would have written those documents off as unservable.

BY HOUSE — the spread is wide and no house-level prior is safe:
    Eulenburg 15/15 · Litolff 10/10 · Universal 9/9  (all 1.000)
    other/unknown 57/73 · Simrock 9/12 · Peters 13/18 · Bote 2/3
    **Breitkopf 45/69 = 0.652** · Durand 8/13 · Novello 3/7 · Ricordi 1/3
    Schott 0/1 · Augener 0/1

⚠️⚠️ BREITKOPF IS BELOW AVERAGE, on the largest sample in the set (69
documents). The house whose "labels every staff" observation this workstream's
entire measurement design was built on acquires a roster in under two thirds of
its own documents. That is the final refutation of the house prior, and it
comes from the house that inspired it.

BY COMPOSER, which does NOT track the house axis:
    mahler 10/10 · bruckner 9/9 · strauss 8/8 · beethoven 16/17 · brahms 11/12
    tchaikovsky 11/14 · haydn 10/14 · mendelssohn 4/7
    **mozart 15/26 = 0.577** · bach 5/10 · dvorak 3/7 = 0.429

⚠️ Dvorak 3/7 against Simrock 9/12; Mozart 0.577 against Breitkopf 0.652.
Composer and publisher are separate axes and neither predicts the other — the
per-EDITION rule, now from a third direction and at full scale.

⚠️ 0.735 IS A FLOOR, NOT A MEASUREMENT OF WHAT EDITIONS PRINT. See
`probe_zero_population_split.py`: of the 62 misses, 29 are PARTIAL reads failed
by this probe's own 0.50 `HIT_YIELD` bar and only 30 are genuine edition
limits. """
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
CATALOG = Path("/Users/seanjohnson/Desktop/ReEngrave/data/score-library/catalog.json")
CACHE = Path(os.getenv("ROSTER_CACHE", str(HERE / "roster-availability-cache")))

# The order a reader tries: the movement's first page is usually early but is
# not always the PDF's first page (front matter, title plates, a collection).
PROBE_PAGES = [1, 2, 0, 3, 5, 8, 12]
MIN_STAVES = 4          # below this it is not an orchestral system
HIT_YIELD = 0.50        # named labels / staves that counts as a usable roster


def house(pub):
    for h in ("Breitkopf", "Litolff", "Simrock", "Peters", "Eulenburg",
              "Kalmus", "Universal", "Durand", "Schott", "Ricordi",
              "Novello", "Augener", "Bote", "Steingraber"):
        if h.lower() in (pub or "").lower():
            return h
    return "other/unknown"


def editions():
    cat = json.loads(CATALOG.read_text())
    out = []
    for e in cat["entries"]:
        if e.get("kind") != "edition":
            continue
        if (e.get("pages") or 0) < 8:
            continue                      # fragments, single movements
        p = LIB / e["path"]
        if not p.exists():
            continue
        out.append(e)
    return out


def probe_document(e, dpi, pages):
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import staff_labels_surya as S

    pdf = LIB / e["path"]
    tried = []
    for pi in pages:
        if pi >= (e.get("pages") or 0):
            continue
        try:
            pws = detect_staves(render_page(pdf, pi, dpi=dpi))
            n = len(pws.staves)
            if n < MIN_STAVES:
                tried.append({"page": pi, "staves": n, "named": 0,
                              "reason": "too few staves"})
                continue
            labs = S.read_staff_labels_surya(pws)
            named = sum(1 for l in labs if l.instrument)
            tried.append({"page": pi, "staves": n, "labels": len(labs),
                          "named": named, "yield": named / n})
            if named / n >= HIT_YIELD:
                return {"acquired": True, "hit_page": pi,
                        "hit_yield": named / n, "hit_staves": n,
                        "hit_named": named, "tried": tried}
        except Exception as exc:
            tried.append({"page": pi, "error": repr(exc)[:120]})
    best = max((t.get("yield", 0.0) for t in tried), default=0.0)
    return {"acquired": False, "best_yield": best, "tried": tried}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--pages", type=int, nargs="*", default=PROBE_PAGES)
    args = ap.parse_args()

    eds = editions()
    # Order so publisher diversity accumulates first: an interrupted run then
    # still spans houses rather than exhausting one.
    by_house = defaultdict(list)
    for e in eds:
        by_house[house(e.get("publisher"))].append(e)
    ordered, i = [], 0
    while len(ordered) < len(eds):
        for h in sorted(by_house):
            if i < len(by_house[h]):
                ordered.append(by_house[h][i])
        i += 1
    if args.limit:
        ordered = ordered[: args.limit]

    print(f"editions with >=8 pages present on disk: {len(eds)}")
    print(f"  houses: {dict(Counter(house(e.get('publisher')) for e in eds))}")
    print(f"probing {len(ordered)} documents, pages {args.pages} "
          f"(first hit stops), dpi {args.dpi}")
    if args.plan:
        return 0

    CACHE.mkdir(parents=True, exist_ok=True)
    from tools.omr import staff_labels_surya as S
    if not S.available():
        raise SystemExit("Surya unavailable — every document would report a "
                         "false negative. Refusing.")

    rows = []
    for k, e in enumerate(ordered, 1):
        key = f"{e['work_id']}--{e.get('imslp_id') or e['sha256'][:8]}"
        cpath = CACHE / f"{key}.json"
        if cpath.exists():
            rec = json.loads(cpath.read_text())
        else:
            t0 = time.time()
            rec = probe_document(e, args.dpi, args.pages)
            rec.update(work_id=e["work_id"], house=house(e.get("publisher")),
                       publisher=(e.get("publisher") or "")[:60],
                       composer=e.get("composer_slug"), pages=e.get("pages"),
                       seconds=round(time.time() - t0, 1))
            cpath.write_text(json.dumps(rec))
            print(f"  [{k}/{len(ordered)}] {rec['house']:12s} "
                  f"{e['work_id']:34s} "
                  f"{'ROSTER p' + str(rec['hit_page']) if rec['acquired'] else 'none'}"
                  f"  {rec.get('hit_yield', rec.get('best_yield', 0)):.2f}"
                  f"  {rec['seconds']}s", flush=True)
        rows.append(rec)

    report(rows)
    return 0


def report(rows):
    n = len(rows)
    got = [r for r in rows if r["acquired"]]
    print(f"\n{'='*72}\nROSTER AVAILABILITY, PER DOCUMENT\n{'='*72}")
    print(f"  documents probed              {n}")
    print(f"  roster ACQUIRED               {len(got)}  ({len(got)/n:.3f})")
    print(f"  no page yielded one           {n-len(got)}  ({(n-len(got))/n:.3f})")

    print(f"\n  ⚠️ DISTRIBUTION of best yield (named labels / staves), NOT a mean:")
    buckets = Counter()
    for r in rows:
        y = r.get("hit_yield", r.get("best_yield", 0.0))
        b = ("0.00" if y == 0 else "0.01-0.24" if y < .25 else
             "0.25-0.49" if y < .5 else "0.50-0.74" if y < .75 else
             "0.75-0.99" if y < .999 else "1.00")
        buckets[b] += 1
    for b in ("0.00", "0.01-0.24", "0.25-0.49", "0.50-0.74", "0.75-0.99", "1.00"):
        c = buckets.get(b, 0)
        print(f"    {b:>10s}  {c:4d}  {c/n:6.3f}  {'#' * int(40*c/n)}")

    print(f"\n  WHICH PAGE SUPPLIED IT (a roster on p.8 still serves p.9+):")
    for pg, c in sorted(Counter(r["hit_page"] for r in got).items()):
        print(f"    page {pg:<3d} {c:4d}  ({c/len(got):.3f} of acquired)")
    late = sum(1 for r in got if r["hit_page"] not in (0, 1, 2))
    print(f"    ⭑ acquired only BEYOND the first three pages: {late}"
          f"  ({late/len(got) if got else 0:.3f} of acquired)"
          f"  — 'page 1' is the wrong unit")

    print(f"\n  BY HOUSE (documents acquired / probed):")
    hh = defaultdict(lambda: [0, 0])
    for r in rows:
        hh[r["house"]][1] += 1
        if r["acquired"]:
            hh[r["house"]][0] += 1
    for h, (a, t) in sorted(hh.items(), key=lambda kv: -kv[1][1]):
        print(f"    {h:16s} {a:4d}/{t:<4d} = {a/t:.3f}")

    print(f"\n  BY COMPOSER (top 12 by document count):")
    cc = defaultdict(lambda: [0, 0])
    for r in rows:
        cc[r.get("composer")][1] += 1
        if r["acquired"]:
            cc[r.get("composer")][0] += 1
    for c, (a, t) in sorted(cc.items(), key=lambda kv: -kv[1][1])[:12]:
        print(f"    {str(c):16s} {a:4d}/{t:<4d} = {a/t:.3f}")

    (HERE / "roster-availability.json").write_text(json.dumps(
        {"n": n, "acquired": len(got), "rows": rows}, indent=1))
    print(f"\n  ⚠️ THE HEADLINE IS THE SHARE OF DOCUMENTS SERVED — "
          f"{len(got)}/{n} = {len(got)/n:.3f} —\n     not the yield on the ones"
          f" that work.")


if __name__ == "__main__":
    sys.exit(main())
