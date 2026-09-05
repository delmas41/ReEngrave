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

## ⚠️ Phase 1's coverage was OVERSTATED — corrected 2026-09-05

Phase 1 scored the **best rung**: it took the first rung that resolved, which
credits reach the pipeline does not have. `contextual._labels_for_page` merges
Tesseract on **raw label presence, not usable presence** — a staff for which
Surya returned `'(C)'` blocks Tesseract from supplying `'(C) Hr.'`. Re-scored on
**the ladder's own answer**, on current main (which also includes another
session's lexicon work):

| | Phase 1 as published | corrected baseline |
|---|--:|--:|
| coverage, all staves | 0.631 | **0.654** |
| coverage of reachable | 0.880 | 0.924 |
| (e) resolved WRONG | 4 | **0** |
| (d) refused | 29 | 16 |

The other session's derived contra- cross product and `hr`/`trpt` aliases closed
**all 13 lexicon-gap staves and all 4 class-(e) errors** (validated there over
1,422 margin labels). Conceded rather than re-verified.

⚠️ **The raw-vs-usable merge is a live defect and is NOT fixed**: the code's own
comment records the identical inconsistency for the *Surya* rung, fixed there in
September, still live on the Tesseract merge. The call site is `contextual.py`,
owned by the structural workstream, so the labels workstream flagged it and did
not touch it. Recorded here so it is not rediscovered.

## Phase 2 (ii-a) SHIPPED — a block centred between two ticks belongs to both

Measured before anything was written. 255 blocks lying between two ticks, 20
pages, 5 publishers, scored as off-centre distance **in the local gap**:

| population | centredness | n |
|---|---|--:|
| shared / brace-centred | 0.017–0.133 | 13 |
| *(empty band)* | 0.133–0.195 | 0 |
| ordinary one-staff labels | 0.431+ | rest |

`_SHARE_CENTREDNESS = 0.15` sits in the empty band — a constant read off a gap,
not tuned.

⚠️ **The UNIT is load-bearing and it changed the answer.** An engraver opens the
gap *between* families, so measured in mean spacings Brahms 1's `4 Hörner` sits
0.565 from its nearer tick and was **discarded by `_TOLERANCE` as belonging to
no staff**; in its own local gap it is 0.043 off centre. Two shared blocks were
being thrown away, not merely misassigned.

```
same 396 | GAINED 11 | LOST 0 | CHANGED 0 | new WRONG 0
coverage 0.654 -> 0.681      reachable 0.924 -> 0.955
```

8 of 11 truth-verified correct (5× Brahms `(Es)`/`(C)` → Horn; Mahler's
`Sechs Hörner in F` and `Vier Trompeten in B` lower staves); 3 on rows with no
hand-read truth. Brahms 1 p1 names **14 of 14**, `unresolved_labels` empty.
Class (b′) closed; (d) 16 → 8 fragments.

**The engraved figure cannot move, and that is proven rather than assumed:**
every `omr-orchestral-e2e` fixture's text layer names **100%** of its staves
(Brahms 21/21, Mahler 38/38, Beethoven 18/18), so `_well_covered` is True and
Surya is never called. 0.1122 / 0.1214 untouched.

## Phase 2 (ii-b) numeral-series inheritance — REFUSED, with the denominator

```
staves the rule could fire on   : 6
distinct rows                   : 1
distinct editions               : 1
of those 6, with hand-read truth: 0
```

All six are Bach Brandenburg p1, on a row whose phase-1 segmentation is a known
failure. It is *inference* where (ii-a) is geometry, and the donor is not always
above (Bach prints the name on the middle staff of a bracketed three) — the
freedom that would let a fragment cross a family boundary elsewhere. **Reopens
if** a second edition prints a group name once with per-staff numerals.

## ⚠️ (ii-a) does not buy clefs, and the workstream was opened on clefs

`clefs_applied: 0` on every completed row, for a structural reason: the staves
recovered are **horns and trumpets**, whose `default_clef` is `treble` — which
is exactly what the positional default already guessed. The audit's clef errors
are **bass and C-clef staves called treble**, a population this rule does not
touch. So (ii-a) buys identity, transposition and part naming; **it does not buy
the clef lever the workstream was opened on.** Reported as such rather than
claimed.

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

⚠️ **RESOLVED 2026-09-05, and the resolution is worth more than either
original claim.** The label WAS read, by both free rungs independently:

```
984073-p4  sys2 pos6   surya 'Tp.'  tesseract 'Tp.'  -> Timpani     PRESENT
984073-p4  sys1 pos6   surya ''     tesseract ''     -> None
575951-p4  sys2 pos6   text 'Tp.'   surya 'Tp.'      -> Timpani
```

Both editions read `[11, 11]`, so this is not a structure difference. The two
workstreams were not in conflict — they held two halves of one mechanism:

> `Tp.` was read at that position and resolved to **Timpani**, and then
> `resolve_ambiguous_label` **overturned it to Trumpet** because the layout fit
> names that slot a trumpet.

`instrument_source = "score_order_ambiguity"` is set at exactly one place
(`contextual.py:287`), inside a loop over `staff_labels`, only for a staff that
**had** a label whose alias is ambiguous and only when the prior's choice
differs. It cannot be set for a staff with no label — so the structural
workstream's own reading proves the label was present, from the other side.
`lookup("Tp.")` → Timpani at high confidence; `candidates_for_alias("tp")` →
`('Timpani', 'Trumpet')`.

⚠️⚠️ **THE CIRCULARITY, and it is the real finding.** The layout fit is wrong at
that slot *because* system 1 prints no Timpani at position 6 and the ordinal
join forces both systems into one slot sequence. So:

> the mis-join corrupts the layout fit → the fit overturns a correctly-read
> label → the resulting wrong instrument then looks like independent evidence
> **for the wrong join**.

`575951` is the control: same label, same alias, a fit that is not corrupted,
and it keeps `Timpani` with `instrument_source: "label"`.

This is **not** the ordinary detected-then-lost shape — nothing is dropped, and
no component is buggy in isolation. A working mechanism is fed a corrupted
premise and its output corroborates the corruption. See the taxonomy's class 6.

**Jointly owned**: the reading is the labels workstream's, the fix is in
`contextual.resolve_ambiguous_label`, which belongs to the structural
workstream. Neither has touched it.

Positions 0–5 read `Fl. Ob. Cl. Fag. Cor. Tr.` identically in both systems.
Nothing in the ladder failed. **The margin already says the two systems are not
the same eleven staves, for free — and `export._stitch_slots` does not read
it.** This join is by printed position within a system and never touches a slot,
so it is independent corroboration rather than a restatement.

⚠️ Any join check built on this must **abstain where labels are absent**, not
refuse: with 115 of 407 staves printing nothing, a rule that refuses on missing
labels would kill stitching on Litolff and Simrock outright. The fix belongs to
the structural workstream.


## ⚠️ THE PREMISE IS CLOSED: more label reach cannot move the clef number here

`probe_clef_reach.py`, over every staff of the 20-row corpus, taking the
**printed truth** name (what the staff IS, not what was read), resolving it, and
cross-tabulating its conventional clef against whether the ladder resolved it:

| staff family (by printed truth) | resolved | unresolved | total |
|---|--:|--:|--:|
| alto-default | 8 | 7 | 15 |
| bass-default | 52 | 22 | 74 |
| treble-default | 95 | 33 | 128 |
| **total** | 155 | 62 | 217 |

29 unresolved staves are in a family whose conventional clef is **not** treble —
the entire population `clef_correction` could ever be handed by more reading.
Cross-tabulated against the Phase 1 classes:

```
29 of 29   a_NO_LABEL_PRINTED
```

**Every one is behind the wall.** Not one is a lexicon refusal, a group-label
fragment or an OCR miss: they are Litolff Beethoven's `Viola` and
`Violoncello e Basso` on continuation systems, and Simrock Dvořák's whole p6/p7
lineup — pages with 0 ink in the margin band.

So the opening premise is **true about the machinery and false about the
remedy**. `clef_correction` really is starved of instrument names; on the staves
that need them the names are **not printed**, not merely unread. That also
explains the pattern rather than leaving it a coincidence: the families labelled
on continuation systems are winds and brass (treble — already defaulted right),
and the families dropped are strings and low brass (bass/alto — the ones that
need help). (ii-a)'s `clefs_applied: 0` is not the rule falling short; it is the
shape of the whole opportunity.

⚠️ Three things this does NOT say, kept explicit:
1. it is 217 truth-carrying staves over 5 publishers — **an edition labelling
   its strings on every system would move it**;
2. it says nothing about whether `clef_correction` would get those staves RIGHT
   if handed them, only that it will not be handed them;
3. the **60 already-resolved non-treble staves are a separate question** —
   whether their labels actually REACH `clef_correction` is about the consumer,
   not about reach, and is unmeasured. That is the only remaining route from
   labels to clefs.
