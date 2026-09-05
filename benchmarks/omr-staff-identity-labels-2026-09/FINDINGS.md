# Staff identity via labels — what the unresolved 29% actually is

**Phase 1, 2026-09-05.** Written by the coordinating session from the workstream
agent's report; its harness refuses it `.md` writes, so the primary record is
its commit message and `summarise.py`'s docstring. This file is the conventional
location, **not** a second source — where it disagrees with the committed data,
the data wins.

Branch: `claude/staff-identity-labels-2026-09-05`.

## Method

20 scan-benchmark rows, **407 staves**, 5 publishers, 6 works. Every rung of the
ladder was run on every page (its early exit deliberately defeated), then the
page itself was asked whether there was anything to read at all.

⚠️ **Computed from pages re-detected on `origin/main`, never from the committed
`..graft09` fixtures** — and that distinction is load-bearing: re-detection does
**not** reproduce those fixtures' staff structure on 3 of 15 rows (Bach p1
`[12,12]` vs `[12,3,3,3,1,2]`; Mahler p2/p3 19/15 vs 17/13). Phase 1 has moved
since the fixtures were stamped, so the audit's 155 staves and these 407 are not
the same staves on those rows.

## The table

| class | n | fix |
|---|--:|---|
| resolved, agrees with printed truth | 120 | — |
| resolved, row has no hand-read truth | 137 | — |
| **(a) no label printed at all** | **115** | **nothing — a wall** |
| **(b) printed, the CROP misses it** | **0** | crop |
| (b′) printed once for a braced group, claimed by one staff | 1 | match rule |
| (c) crop right, OCR empty | 1 | reader |
| **(d) OCR read it, LEXICON refused it** | **29** | lexicon / match rule |
| **(e) lexicon resolved it WRONG** | **4** | lexicon |

```
coverage, all staves        257/407 = 0.631
coverage, REACHABLE staves  257/292 = 0.880
```

⚠️ **0.631 is not a regression from the audit's 0.710.** That scored 155 staves
over 11 fixture rows; this adds nine continuation pages, which is precisely
where labels stop being printed. Different denominator — **do not difference
them.**

## The crop is not the problem, and that is a result

**(b) = 0 across 407 staves and 5 publishers.** Every continuation system *is*
edge-clipped (25/25, `x0 = 0`), but that is a SYMPTOM rather than a cause:
`x_ref` is the median staff `x_start`, so a page printing no names begins its
music nearer the edge. Breitkopf is edge-clipped on all six systems and still
resolves 10–13 of 14 each. A weaker investigation would have "fixed" the crop
and measured nothing.

## Class (a) is publisher convention, proved by ink

Ink was counted in the band beside each unresolved staff **with the
bracket/brace excluded** (otherwise the test is vacuous) and trusted **only in
the negative**. Blank Litolff/Simrock margins measure **0 px** over bands of
100k–260k; a printed `Tr.` measures thousands. 115 of 146 read 0 or 30; all 31
with real ink were rendered and looked at, two adjudicated by hand, and five
pages spot-checked at 600 dpi.

- **Simrock** labels the movement's first page only — Dvořák p6/p7 print nothing
  (44 staves).
- **Litolff** labels winds and brass on every system and **strings never** after
  p1.
- **Breitkopf** labels every staff — 0 in class (a).

**This is the ceiling on label-based identity, and it is not a reader problem.**

## 33 actionable staves, four defects

- `Hr.`, `Trpt.`, `Contrafagott` are absent from the lexicon while `Cor. (Es)`,
  `Tpt.`, `Kontrafagott` resolve — **omissions, not ambiguities**.
- `K-Fag.` → **Bassoon** is the `Tr. Alt.` shape again (the substring `fag`
  beating the compound). The only class-(e) case, on the same staff of every
  Breitkopf system.
- The other 12 are **group-label fragments** (`(Es)`, `I`, `III`) where the name
  is engraved once across a bracket. No lexicon entry reaches them; this is
  `MAX_STAFF_DISTANCE_FRAC`, a MATCH-RULE problem, and must be priced separately
  from the lexicon fix.

⚠️ **Phase 2's ceiling: perfect lexicon + perfect match rule take coverage
0.631 → 0.713 on this corpus.** Anything claiming more is measuring something
else.

## The paid vision rung is CLOSED, with the number

Widening it cannot be justified here: **115 of 149 unresolved staves print no
label**, and `staff_labels_vision`'s own prompt instructs the model to return
`null` for an unlabelled staff — so Claude would correctly answer nothing and
the cent buys nothing. Reader work generally is near-nil ((c) = 1). Surya
collapsed to 1 label on two Mahler pages that Tesseract carried, which is an
argument for **keeping both free rungs**, not for a better one.

## Independent corroboration of the structural agent's silent mis-join

The labels confirm it from the other side, on **both** editions of Beethoven 5
p.4:

| row | system 1, position 6 | system 2, position 6 |
|---|---|---|
| `beethoven-sym5-mvt1-984073-p4` | *(no label printed)* | `Tp.` → **Timpani** ⚠️ CONTESTED |
| `beethoven-sym5-mvt1-575951-p4` | *(no label printed)* | `Tp.` → **Timpani** |

⚠️ **The 984073 row is CONTESTED and unresolved as of 2026-09-05.** The
structural workstream, reading the transcription for the same page, finds
position 6 resolving as `Trumpet` via `score_order_ambiguity` — i.e. **no label
reached `contextual` at that position in either system** — while 575951 reads
`Timpani` with `instrument_source: "label"`. Two possibilities, not yet
separated: the raw reader here held a `Tp.` that the ladder discarded before
`contextual` saw it (which would be a finding in its own right), or this table
generalised from the 575951 edition. **Neither workstream has asserted the other
is wrong**, and the 575951 half is not in doubt. Recorded as contested rather
than silently averaged, because two sessions confirming each other on one page
is exactly how this repo lost hours on 2026-09-04 —
see [[feedback_corroboration_is_not_evidence]].

Positions 0–5 read `Fl. Ob. Cl. Fag. Cor. Tr.` identically in both systems.
Nothing in the ladder failed. **The margin already says the two systems are not
the same eleven staves, for free — and `export._stitch_slots` does not read
it.** This join is by printed position within a system and never touches a slot,
so it is independent corroboration rather than a restatement.

⚠️ Any join check built on this must **abstain where labels are absent**, not
refuse: with 115 of 407 staves printing nothing, a rule that refuses on missing
labels would kill stitching on Litolff and Simrock outright. The fix belongs to
the structural workstream.
