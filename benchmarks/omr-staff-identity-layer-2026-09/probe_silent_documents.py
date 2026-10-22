#!/usr/bin/env python3
"""The documents that print nothing beside their staves — two hypotheses.

MEASUREMENT ONLY. Uses the PDF TEXT LAYER first (free) and never spends OCR.

The sweep's 27 "PRINTS NOTHING" documents are staves-found, margin-text-zero.
Two proposals for what they actually are:

H1 — STANDARD LINEUPS FOR EARLIER MUSIC. An engraver omits what every reader
     knows; the Mozart orchestra was stable. Consistent with the sweep's own
     mozart 15/26 = 0.577 and bach 5/10.
     ⚠️ THIS IS NOT THE ERA PRIOR THAT WAS RETRACTED. That retraction was on
     PREDICTING A STAFF'S IDENTITY FROM ERA — a population tendency standing in
     for evidence about this page. Here era supplies a DEFAULT LINEUP THE USER
     CONFIRMS AT IMPORT: user-supplied provenance, traceable, overridden by
     anything the page actually says. Different mechanism, different origin
     tag, opposite direction of authority.

H2 — THE ROSTER EXISTS BUT NOT BESIDE THE STAVES. Splits in two, and only one
     half is lost:
     (a) FRONT MATTER PRESENT AND INVISIBLE TO US. Our reader looks for labels
         in the MARGINS BESIDE STAVES. A title page or a dedicated
         "Besetzung" / "Orchestra" / "Strumenti" list is NEVER EXAMINED. Such a
         document reads as "prints nothing" while the answer sits on page one
         in running prose. ⇒ A NEW ACQUISITION CHANNEL, not a harder version of
         the existing one.
     (b) FRONT MATTER GENUINELY ABSENT from the scan. Lost.

⚠️ If (a) is a real population it changes the LADDER: front-matter reading goes
ABOVE vision, being free and reading the publisher's own explicit statement
rather than inferring from a damaged abbreviation. Hence: measure the
population before building the reader.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_silent_documents.py

── RESULT 2026-09-05, all 27 silent documents ────────────────────────────────

H1 — SUPPORTED, AND IT IS THE LARGER POPULATION. 10 of 27 are pre-1830
composers: mozart 5, bach 3, haydn 2.

    bach   concerto-3 (Peters) · concerto-5 (Breitkopf) · WTC I
    haydn  symphony-101 · symphony-102          (both Breitkopf)
    mozart die-zauberflöte (Simrock) · don-giovanni · le-nozze-di-figaro
           · requiem-in-d-minor · symphony-33   (rest Breitkopf)

⚠️ BUT "STANDARD ORCHESTRA" IS THE WRONG DEFAULT FOR MOST OF THEM. Four of the
five Mozart entries are OPERA or REQUIEM — Zauberflöte, Don Giovanni, Figaro,
the Requiem — which carry VOICES and a chorus, and WTC I is solo keyboard. So
the population is real but it is not one lineup: a selector would need
"Classical symphony", "opera/choral", and "solo keyboard" as separate options,
and the keyboard case needs no instrument identity at all. Genuine
standard-symphony cases here: haydn 101, haydn 102, mozart 33 — THREE.

H2 — THE FRONT-MATTER CHANNEL IS TOO SMALL TO BUILD AS A RUNG.

    silent documents WITH a PDF text layer         8/27
    ...whose text names >=4 distinct instruments   4      <- H2(a) candidates
    ...with an explicit Besetzung/Orchestra head   1      <- wagner Meistersinger

⚠️⚠️ NINETEEN OF TWENTY-SEVEN HAVE NO TEXT LAYER AT ALL, so the FREE channel
cannot reach them; front matter there would need OCR, which is not free and is
what the rung was supposed to undercut. The free channel is worth at most 4
documents of 234 (0.017), and exactly ONE is a confirmed instrumentation list
(wagner--die-meistersinger, 15 distinct nouns under a Besetzung heading).

⇒ FRONT-MATTER READING SHOULD NOT GO ABOVE VISION IN THE LADDER on this
evidence. It is cheap enough to add for the text-layer case as an opportunistic
first look, but it is not a population worth engineering for, and the ladder's
shape does not change.

⚠️ 4/27 is a LOWER BOUND on H2(a): the 19 documents without a text layer may
carry an image-only front-matter list this probe cannot see. What is bounded is
the FREE channel, which is the thing the "above vision" argument rested on.

⚠️ >=4 distinct instrument nouns is a CANDIDATE signal, not a confirmed roster —
a title page, a publisher's catalogue of other editions, or a preface can trip
it. Only the Wagner entry pairs it with an explicit heading.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from probe_roster_availability import CACHE, LIB          # noqa: E402
from probe_zero_population_split import classify          # noqa: E402

CATALOG = Path("/Users/seanjohnson/Desktop/ReEngrave/data/score-library/catalog.json")

# Composer -> "pre-1830 standard-lineup era" is an APPROXIMATION BY COMPOSER,
# not a per-work date. Said plainly: a late Beethoven or Schubert work is not a
# Classical-orchestra work, and this map cannot tell.
EARLY = {"bach", "handel", "vivaldi", "haydn", "mozart", "gluck", "boccherini",
         "corelli", "telemann", "pergolesi", "cimarosa", "salieri", "clementi"}

# Words an edition uses to head an instrumentation list, across the houses in
# this library.
BESETZUNG = re.compile(
    r"\b(besetzung|orchesterbesetzung|instrumentation|instrumente|"
    r"orchestra|orchestre|strumenti|organico|instruments?)\b", re.I)
# Instrument nouns in running text, in the languages these editions use.
NOUNS = re.compile(
    r"\b(flaut|flöt|flote|flute|oboe|hoboe|clarinett|klarinett|clarinet|"
    r"fagott|bassoon|basson|corn|horn|tromb|trompet|tuba|timpani|pauken|"
    r"violin|violon|viola|bratsch|violoncell|cello|contrabass|kontrabass|"
    r"basso|harfe|harp)\w*", re.I)


def text_of(pdf, n_pages=6):
    try:
        import fitz
    except ImportError:
        return None
    try:
        doc = fitz.open(pdf)
    except Exception:
        return None
    out = []
    for i in range(min(n_pages, doc.page_count)):
        try:
            out.append(doc[i].get_text())
        except Exception:
            pass
    doc.close()
    return "\n".join(out)


def main():
    cat = {e["path"]: e for e in json.loads(CATALOG.read_text())["entries"]
           if e.get("kind") == "edition"}
    by_work = {}
    for e in cat.values():
        by_work.setdefault(e["work_id"], []).append(e)

    rows = [json.loads(p.read_text()) for p in sorted(CACHE.glob("*.json"))]
    silent = [r for r in rows if not r.get("acquired")
              and classify(r).startswith("PRINTS NOTHING")]
    print(f"documents cached {len(rows)}   PRINTS NOTHING {len(silent)}")
    if not silent:
        raise SystemExit("REFUSING to report: no silent documents.")

    # ── H1 ──────────────────────────────────────────────────────────────────
    early = [r for r in silent if (r.get("composer") or "") in EARLY]
    print(f"\n{'='*72}\nH1 — EARLIER MUSIC WITH A STANDARD LINEUP\n{'='*72}")
    print(f"  silent documents by composer: "
          f"{dict(Counter(r.get('composer') for r in silent).most_common())}")
    print(f"\n  of the {len(silent)} silent, composers in the pre-1830 set: "
          f"**{len(early)}**")
    for r in sorted(early, key=lambda r: str(r.get("work_id"))):
        print(f"    {str(r.get('composer')):12s} {str(r.get('work_id')):36s}"
              f" {str(r.get('house'))}")
    print(f"\n  ⚠️ APPROXIMATION BY COMPOSER, not by work date — a late"
          f" Schubert or Beethoven\n     work is not a Classical-orchestra"
          f" work and this map cannot tell. A count\n     and a list, as asked,"
          f" not a rate.")

    # ── H2 ──────────────────────────────────────────────────────────────────
    print(f"\n{'='*72}\nH2 — IS THE ROSTER IN FRONT MATTER WE NEVER LOOK AT?"
          f"\n{'='*72}")
    print(f"  {'composer':12s} {'work':32s} {'txt':>4s} {'hdr':>4s} "
          f"{'nouns':>6s}  verdict")
    have_text = with_header = with_nouns = 0
    hits = []
    for r in sorted(silent, key=lambda r: str(r.get("work_id"))):
        eds = by_work.get(r.get("work_id"), [])
        pdf = None
        for e in eds:
            p = LIB / e["path"]
            if p.exists():
                pdf = p
                break
        if pdf is None:
            continue
        txt = text_of(pdf)
        has_text = bool(txt and txt.strip())
        hdr = bool(txt and BESETZUNG.search(txt))
        nouns = len(set(m.group(0).lower() for m in NOUNS.finditer(txt or "")))
        have_text += has_text
        with_header += hdr
        if nouns >= 4:
            with_nouns += 1
        verdict = ("FRONT-MATTER LIST (a)" if (hdr and nouns >= 4)
                   else "nouns, no header" if nouns >= 4
                   else "header, few nouns" if hdr
                   else "no text layer" if not has_text
                   else "text, no roster")
        if nouns >= 4:
            hits.append((r, nouns, hdr))
        print(f"  {str(r.get('composer'))[:12]:12s} "
              f"{str(r.get('work_id'))[:32]:32s} "
              f"{'Y' if has_text else '-':>4s} {'Y' if hdr else '-':>4s} "
              f"{nouns:6d}  {verdict}")

    print(f"\n  silent documents WITH a PDF text layer:      {have_text}"
          f"/{len(silent)}")
    print(f"  ...whose text names >=4 distinct instruments: {with_nouns}"
          f"   <- H2(a) candidates")
    print(f"  ...with an explicit Besetzung/Orchestra head: {with_header}")
    print(f"""
  ⚠️ >=4 DISTINCT INSTRUMENT NOUNS IN THE TEXT LAYER is a CANDIDATE signal, not
     a confirmed roster: a title page naming the work, a publisher's catalogue
     of other editions, or a preface can all trip it. What it bounds is how big
     the H2(a) population COULD be — and if that bound is near zero, the
     front-matter reader is not worth building, which is the decision this
     measurement exists to make.""")


if __name__ == "__main__":
    main()
