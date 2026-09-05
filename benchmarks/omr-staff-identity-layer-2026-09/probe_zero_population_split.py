#!/usr/bin/env python3
"""The 0.00-yield documents are THREE populations, not one.

MEASUREMENT ONLY, read-only over the sweep cache — no probing.

⚠️ WHY THIS MATTERS. `probe_roster_availability.py` reports "roster acquired
0.746", and it is tempting to read the complement as "a quarter of editions
omit instrument names". It does not follow. Instrument names are printed on the
first page of the WORK, not of every movement, so a document that is an
EXCERPT may simply not contain the roster page — an artifact of what was
downloaded, not of what the publisher printed. Three populations want three
different responses:

    LACKS THE PAGE     the roster page is not in this PDF (excerpt, single
                       movement, a part-book). ⇒ get the right PDF. NOT a
                       limit on the procedure.
    PRINTS NOTHING     staves were found and read, and no instrument name is
                       there. ⇒ a real limit; the fallback path serves these.
    READ AND FAILED    text WAS found in the margin and the lexicon could not
                       resolve it. ⇒ wants a better READER or a wider lexicon,
                       not another source.

⚠️ THE THIRD IS NOT HYPOTHETICAL AND IT IS EXPENSIVE. On brahms-317803's roster
page the two Horn staves read `in C 1 2` and `in Es 3 4` — the transposition
qualifier WITHOUT the instrument noun — so the lexicon resolved nothing, `Horn`
left the roster vocabulary entirely, and eight staves downstream were misnamed
(`probe_real_acquisition.py`). Text-but-no-instrument is the failure that
looks smallest and costs most.

SEPARATION, from what the sweep already recorded per document:
  · every probed page had ZERO staves            -> LACKS THE PAGE (no music)
  · staves found, zero label TEXT anywhere       -> PRINTS NOTHING
  · label text found, none of it resolved        -> READ AND FAILED

⚠️ The first is a LOWER BOUND on "lacks the page": a PDF whose probed pages are
all music can still be an excerpt that begins after the roster page, and this
probe cannot tell that from an edition that prints nothing. Said plainly rather
than papered over.

    python3 .../probe_zero_population_split.py

── RESULT 2026-09-05, 215 of 234 documents ───────────────────────────────────
    acquired 159/215 = 0.740     NOT acquired 56

    25  0.446  PRINTS NOTHING   staves found, zero margin text
    25  0.446  partial          some names read, below the 0.50 bar
     3  0.054  LACKS THE PAGE   no staves on any probed page
     3  0.054  READ AND FAILED  text found, lexicon resolved none

⚠️⚠️ THE EXCERPT HYPOTHESIS IS REFUTED. The expectation was that a large share
of the zeros would be documents that simply do not CONTAIN the roster page —
excerpts, single movements — since names are printed at the head of the WORK.
It is **3 of 56 (0.054)**: Beethoven's Missa Solemnis, Nielsen 5, Smetana's
Prodaná nevěsta, all with zero staves on every probed page. The misses are
overwhelmingly real.

⚠️⚠️ AND THE BIGGEST CORRECTION IS TO MY OWN INSTRUMENT. Twenty-five documents
— as many as the genuine silences — DID read names and were failed by the 0.50
`HIT_YIELD` bar I chose. That is a threshold artifact, not an edition property,
and it is the largest single population in the miss column. With a lower bar
plus the hole-healing measured in `probe_real_acquisition.py` (which recovers
half of an incomplete roster), availability would be up to
(159+25)/215 = **0.856**, not 0.740.

    ⇒ so 0.746/0.740 is a FLOOR twice over: once for the 3 wrong-PDF cases,
      and much more importantly for the 25 partial reads my own threshold
      discarded. The EDITION is the limit on only 28/215 = 0.130.

Bach and keyboard works dominate the genuine silences (`bach--concerto-5`,
`das-wohltemperierte-klavier`, `bach--concerto-3`), which is unsurprising: a
keyboard score has no instruments to name, and that is the genre selector's
case rather than a reading failure.

⚠️ `LACKS THE PAGE` remains a LOWER BOUND: a PDF whose probed pages are all
music can still begin after the roster page, and this probe cannot separate
that from an edition that prints nothing.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from probe_roster_availability import CACHE  # noqa: E402


def classify(rec):
    tried = rec.get("tried") or []
    if not tried:
        return "no pages probed"
    staves = sum(t.get("staves", 0) or 0 for t in tried)
    labels = sum(t.get("labels", 0) or 0 for t in tried)
    named = sum(t.get("named", 0) or 0 for t in tried)
    if staves == 0:
        return "LACKS THE PAGE (no staves on any probed page)"
    if labels == 0:
        return "PRINTS NOTHING (staves, no margin text)"
    if named == 0:
        return "READ AND FAILED (text found, lexicon resolved none)"
    return "partial (some names, below the 0.50 bar)"


def main():
    rows = []
    for p in sorted(CACHE.glob("*.json")):
        try:
            rows.append(json.loads(p.read_text()))
        except Exception:
            pass
    if not rows:
        raise SystemExit(f"REFUSING to report: no cached documents in {CACHE}")
    got = [r for r in rows if r.get("acquired")]
    miss = [r for r in rows if not r.get("acquired")]
    print(f"documents cached {len(rows)}   acquired {len(got)}"
          f"   NOT acquired {len(miss)}")

    print(f"\n{'='*72}\nTHE NON-ACQUIRING DOCUMENTS, SPLIT\n{'='*72}")
    cls = Counter(classify(r) for r in miss)
    for k, v in cls.most_common():
        print(f"  {v:4d}  {v/len(miss):6.3f}  {k}")

    print(f"\n  ⚠️ Only 'PRINTS NOTHING' and 'READ AND FAILED' are limits on"
          f" the procedure.\n     'LACKS THE PAGE' is a property of the PDF"
          f" that was downloaded.")

    real = sum(v for k, v in cls.items()
               if k.startswith(("PRINTS NOTHING", "READ AND FAILED")))
    lacks = sum(v for k, v in cls.items() if k.startswith("LACKS"))
    print(f"\n  documents where the EDITION is the limit: {real}"
          f"  ({real/len(rows):.3f} of all cached)")
    print(f"  documents where the PDF is the limit:     {lacks}"
          f"  ({lacks/len(rows):.3f} of all cached)")
    print(f"\n  ⇒ ROSTER AVAILABILITY {len(got)}/{len(rows)} = "
          f"{len(got)/len(rows):.3f} IS A FLOOR on what editions print,"
          f"\n    not a measurement of it — up to {lacks} of the misses are"
          f" the wrong PDF\n    rather than a silent edition.")

    print(f"\n{'='*72}\nTHE NON-ACQUIRING DOCUMENTS, NAMED\n{'='*72}")
    for r in sorted(miss, key=lambda r: (classify(r), r.get("work_id", ""))):
        tried = r.get("tried") or []
        staves = sum(t.get("staves", 0) or 0 for t in tried)
        labels = sum(t.get("labels", 0) or 0 for t in tried)
        print(f"  {str(r.get('house'))[:12]:12s} {str(r.get('work_id'))[:32]:32s}"
              f" pages={r.get('pages')} staves_seen={staves:3d}"
              f" text={labels:3d}  {classify(r).split(' (')[0]}")


if __name__ == "__main__":
    main()
