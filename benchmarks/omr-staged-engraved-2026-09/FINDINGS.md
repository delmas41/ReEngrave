# The ENGRAVED staged record — the first reading accuracy the staged pipeline has ever had

**2026-09-22, Lane A.** `tools/omr/staged/trace.py` shipped on 2026-09-18 saying
in terms: *"WHAT IT CANNOT SEE: ACCURACY. Both records are SCANS and
`page_truth` exists only for a page we RENDER, so this funnel says where
symbols are LOST and never whether the survivors are RIGHT — **it needs one
ENGRAVED staged record.**"* This is that record, and the answers it made
possible. **`git diff -- tools/` on the lane is EMPTY.**

⚠️ **PROVENANCE.** The harness blocks subagents from writing `.md` report files
— the **seventh** time in this repo. This file is the measuring session's own
report transposed at integration. `[mgr]` marks a managing-session check.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED** — that a Verovio render from MusicXML is a fair test of the READING
stages, so a failure on it is a failure of the RULE and not of the print; and
that the ordinal part join *is* the layout here, because the renderer prints
every part on every system and suppresses none.

**WHAT WOULD FALSIFY IT** — a failure that is a property of *Verovio's*
engraving rather than of engraving in general. ⚠️ **One is live in §5**: its
mechanism depends on Verovio's key-signature spacing. **The same measurement on
a LilyPond render or a real plate would settle it, and it was not run.**

**NOT CONFIRMED WITH SEAN.** Nothing is proposed for any constant, flag or
default. Four items are put to a human in §11.

---

## 0. [mgr] What I checked against the tree before believing the report

| claim | check | result |
|---|---|---|
| branch pushed, `tools/` untouched | `git diff --stat origin/main...<branch> -- tools/` | **empty** |
| §5's key-signature table | **re-tallied myself** from the committed `out/locator-vs-template-p0.json` | **template 18 right / 0 wrong; locator 2 right / 9 wrong**, and the verdict takes the locator on 10 staves, 8 of them wrong — confirms the report |
| §9's `score_reading` defect | read `detections_in_page_px` / `staff_space_px` directly | **CONFIRMED, and worse**: the first returns `[]` and the second returns **1.0**, so a missing page yields a full table of zeros *and* rescales every tolerance ~20× |

**[mgr] §9 is now REPAIRED** (`dcdff9f2`) — the lane correctly did not touch
`tools/`, so the managing session did: `_page_of` looks a page up by its own
`page_index` field and RAISES, on both the result and the truth side.

## 1. The premise check (run before anything was built)

| the brief's claim | verdict |
|---|---|
| no ENGRAVED staged record exists on this machine | **TRUE.** All three of `library/_shared-records/` are scans. `omr-staged-meter-engraved-2026-09` *did* render engraved pages and run the staged pipeline, but committed only the `Q.METER` verdicts (228–2,347-byte files) — **no record, so nothing else could ever be asked of it.** Its `render_meter_change.py` is the excerpt recipe and was reused. |
| `omr-reading-vs-reproduction-2026-09` already scores reading against page truth | **TRUE**, on the LEGACY path. ⚠️ **Its scorer, `tools/omr/score_reading.py`, is called here UNCHANGED** — an adapter, not a second scorer, so staged and legacy numbers come out of one code path. |
| the `accidental` caveat needs thought | **TRUE and it fires.** `render_fidelity` reads `drawn 100, encoded_as_printed 20, agrees false` and declares the family unreliable. Excluded from every pooled figure, reported apart. |

⚠️ **A FOURTH FACT THE BRIEF DID NOT NAME: the staged CLI does NO weight
routing.** `staged/__main__.py` hands `--weights` straight to `YoloDetector`;
`input_domain` is imported nowhere under `staged/`. This PDF classifies
**engraved on all 3 pages** (1,188/1,356/1,655 drawings, raster coverage
0.000), so every arm pins the engraved-side checkpoint routing *would* have
chosen — but on the staged path **an engraved PDF gets whatever weights are
typed.**

## 2. The fixture

Beethoven 5 mvt 1 **bars 1–24** — the same music as the Litolff shared record —
rendered by Verovio through `page_truth.py` at dpi 300. **18 parts, 3 pages,
one system of 18 staves per page, 7 / 9 / 8 bars**, staff space 22.5 px. The
fixture and the records are committed (37 MB), so everything reproduces without
the score library.

## 3. THE READING SCORE — the number that has never existed

Pooled over three engraved pages, tolerance 0.5 staff spaces:

| family | truth | pred | match | prec | rec | F1 |
|---|--:|--:|--:|--:|--:|--:|
| **notehead** | 354 | 359 | 354 | 0.986 | **1.000** | 0.993 |
| **rest** | 316 | 317 | 316 | 0.997 | **1.000** | 0.998 |
| key_accidental | 132 | 133 | 132 | 0.992 | 1.000 | 0.996 |
| time_signature_digit | 36 | 36 | 36 | 1.000 | 1.000 | 1.000 |
| clef | 54 | 57 | 54 | 0.947 | 1.000 | 0.973 |
| beam *(CV)* | 58 | 60 | 58 | 0.967 | 1.000 | 0.983 |
| flag | 4 | 6 | 4 | 0.667 | 1.000 | 0.800 |
| tie | 59 | 65 | 32 | 0.492 | 0.542 | 0.516 |
| dynamic_letter | 58 | 106 | 52 | 0.491 | 0.897 | 0.634 |
| accidental *(RENDER)* | 100 | 21 | 20 | 0.952 | 0.200 | — |
| **POOLED (scoreable)** | **1016** | **1087** | **981** | **0.902** | **0.966** | **0.933** |

⚠️⚠️ **NOTEHEAD RECALL IS 1.000 ON ALL THREE PAGES** — 73/73, 74/74, 207/207 —
on an 18-staff conductor's page. **A fact about engraved ink, saying nothing
about a scan.**
⚠️ **The tie column is tolerance-sensitive**: page 2 reads F1 **0.000 at 0.5
spaces and 0.938 at 1.5**. The arcs are found and loosely localised — the
pattern `score_reading` itself flags as *found and loosely placed, not missed.*
⚠️ **`dynamic_letter` precision 0.491 is the one real hole**, survives the
ownership arm, and recall is 0.897 — **over-emission, not blindness.**
Measured and undiagnosed.

**The control that could have made all of this junk:** `--shift-spaces 2` moves
every detection 2 staff spaces in y. **Pooled F1 0.947 → 0.058.** It collapses,
so the score measures POSITION and not counts.

## 4. Where the staged path's extra ink comes from — and the hypothesis was wrong

The obvious candidate was the NMS divergence CLAUDE.md records at
`gather.py:292` (0.7/False against `transcribe`'s 0.5/True). **Measured, it is
almost none of it.** Page 0's 24 extras: **10 cross-staff RESOLVED** (the row's
own `Q.GLYPH_OWNER` verdict names another staff), 8 not contested (twin at IoU
0.3–0.5, where legacy dedupes at 0.3 and `CONTEST_IOU` is 0.5), 3 kept, **2
NMS** (both `beam`, a CV family excluded from the pool), 1 unexplained. Page 2's
67: 32 resolved, 20 kept, 9 not contested, **4 NMS**, 2 unexplained.

⚠️⚠️ **So the staged/legacy precision gap is the cross-staff decision living in
a different STAGE, not a worse reading.** `transcribe` deletes the loser in
`_dedupe_cross_staff_detections`; the staged path keeps the row and files a
verdict the exporter honours as `owned_by_another_staff`.

⚠️ **The two notehead-precision filters the staged path does not run cost it
NOTHING on page 0 and 2 noteheads on page 2.** Those filters can only *remove*
noteheads, so a delta of zero bounds what they could have done. **This does not
clear them on a scan**, where the fault they were measured on lives.

## 5. ⚠️⚠️ THE HEADLINE: the key signature's correct answer is on the record and is not read

50 decided staff-systems, truth = the excerpt's own `<key><fifths>`:

| reason | right | wrong |
|---|--:|--:|
| **`fitted_by_template`** (`Q.KEYSIG_TEMPLATE_FIT`) | **20** | **0** |
| **`fitted`** (the locator's slot fit) | **6** | **24** |

Every wrong verdict is `-1` where `-3` is printed. **[mgr] Re-tallied on page 0
from the committed JSON: template 18/18 right, locator 2 right / 9 wrong.** The
6 right `fitted` answers are the clarinets (`-1`) and horns (`0`) — the locator
is right exactly where the answer is small, **because it under-counts.**

**The detector is not the problem: `key_accidental` reading recall is 1.000,
132 of 132 glyphs.**

`adjudicate_key_signature`'s own docstring states the precedence and its reason:

> *"the locator loses accidentals to broken ink, the template can match spurious
> ink and over-count — so the one that cannot invent a glyph goes first."*

⚠️⚠️ **THE INK IS NOT BROKEN — IT IS A VECTOR RENDER — AND THE LOCATOR LOSES
THE ACCIDENTALS ANYWAY, 24 TIMES IN 30. THE TEMPLATE OVER-COUNTS NOWHERE.**
That is the premise of a shipped refusal, refuted on the one input where it
cannot be blamed on the print: *A PREMISE ENCODED IN A REFUSAL OUTLIVES ITS
REASON* and *the value existed and nothing read it*, in one place.

**The mechanism, measured.** Staff 0, canonical staff space 100 px, staff lines
at y = 600/702/800/902/1000, every cluster in the key-signature window:

```
     x      y      w      h    w_sp   h_sp   verdict
   503    749     69    119    0.69   1.19   KEPT
   623    600     49     94    0.49   0.94   dropped: h < 1.10
   723    800     49     94    0.49   0.94   dropped: h < 1.10
```

The three flats are there, evenly spaced, at the right x. **Two are dropped by
`min_height_spaces = 1.10`.** The page truth measures each at 57.9 px / 22.5 px
= **2.57 spaces**; after `header_ink_mask` they measure **0.94 and 1.19** — the
erasure removes **54–63% of each flat's height**, and a floor written for a real
accidental rejects two of three.

⚠️ **The control that says x=503 is the signature and not furniture**: it
appears on every staff whose truth is `-3` or `-1` and on **neither horn staff,
whose truth is 0.** Other repeated x positions appear on the horn staves too.
⚠️ **An observation, not a mechanism**: the two dropped clusters begin at
y = 600 and 800, *exactly on a staff line*, and the kept one mid-space at 749.
**Not established** — the kept cluster also crosses the line at 800.

## 6. NOTE ACCURACY — are the notes we wrote the RIGHT notes?

| arm | part-bars exact | events truth / ours |
|---|--:|--:|
| page 0 alone (bars 1–7) | **123 of 126 (0.976)** | 174 / 174 |
| 3-page gather, bars 1–20 | **313 of 360 (0.869)** | 528 / 530 |
| 3-page gather, bars 1–24 | 335 of 432 (0.775) | 662 / 647 |

**Disagreements by kind, bars 1–20: 43 differ ONLY by an accidental**, 2 by
event count, 2 by pitch/rest. ⚠️⚠️ **So 91% of all note errors on 20 bars of an
18-part engraved orchestral page are §5's key signature.** Page 0's three errors
are all of it there: `E4` where the score prints `E-4`, on the two violin
staves, in the bars holding the symphony's answering half note.

⚠️ Read `events truth 174, ours 174` beside 123/126 — **a part we wrote nothing
for makes no error, so bar-exactness alone rewards silence.** Here nothing was
withheld and nothing invented.
⚠️ The bars 1–24 figure is **contaminated**: one spurious barline on page 2 (we
read 9 bars where the render prints 8; the export's own
`empty_bars_padded_without_meter: 1` names it) shifts every later bar. **Not
diagnosed.**

## 7. `<beam>` and `<alter>` — the 09-21 emission's first engraved contact

| | result |
|---|---|
| STRUCTURE — every `begin` has its `end` | **0 unbalanced levels** |
| COUNT — `<beam>` vs the truth ENCODING | **183 ours, 183 truth, delta 0** |
| SEQUENCE — the whole `(number, type)` list per part | **18 of 18 parts exact** |
| FLAGS — Verovio re-renders OUR file | **`{pages: 3, flag: 4, beam: 58}`** — *identical* to the truth file's own |

⚠️ **The beam emission is exact on engraved ink** — not a count agreeing over a
wrong distribution, but the whole per-part sequence, corroborated by an
independent renderer drawing exactly the printed number of beams and flags.

`<alter>`: **44 ours / 100 truth, 5 of 18 parts exact** — and it tracks §5
precisely. On the 10 staves with a **correct** key we write 38 of 55 alters
(69%); on the 8 with a **wrong** key, 6 of 45 (13%). Violin 1 writes 0 of 12.
**The alteration rule is right wherever the key it reads is right.** The
residual on correct-key staves is the in-bar accidental, which reaches no
quantity at all. One part (Contrabass) writes 8 against a truth of 6 —
over-alteration, unexamined.

⚠️ `<beam>` is an ENCODING unit (one per note per level) and the page-truth
`beam` family a PAGE unit (one stroke per group). §3's 58/60/58 and §7's 183/183
are **different questions; do not divide one into the other.**

## 8. THE FUNNEL — on engraved ink almost nothing is lost

| noteheads | Litolff (scan) | Breitkopf (scan) | **eng p0** | **eng p1** | **eng p2** |
|---|--:|--:|--:|--:|--:|
| population | 2,347 | 3,337 | 73 | 77 | 221 |
| `<note>` written | 965 (41%) | 2,513 (75%) | **73 (100%)** | **77 (100%)** | **208 (94%)** |
| `staff_not_identified` | 783 | 0 | **0** | **0** | **0** |
| `no_pitch` | 205 | 0 | **0** | **0** | **0** |
| `duration_narrowed` | 335 | **537** | **0** | **0** | **3** |
| `stem_direction` abstained | 904 (38.5%) | 1,546 (46.3%) | **0** | 9 | 25 |

⚠️⚠️ **Both dominant staged losses vanish.** Breitkopf's largest is
`duration_narrowed` — 537 notes, **INFER's entire population**. On engraved ink
it is 0 / 0 / 3, so **INFER has essentially no domain on engraved input.** That
is a statement about where that stage can ever pay.
⚠️ The **beam-mate tier** (default-on, whose 0.984 was Litolff-only) fires **8
times** on page 2 — its first engraved contact. Whether those 8 are right is
**not measured.**

⚠️⚠️ **THE FALSE `no_ink` CLAIMS REPRODUCE ON PERFECT INK: 421 of 439
contradicted on page 0, 428 of 446 on page 2**, with `Q.INK`'s own `no_ink`
firing zero times. Tonight's sibling lane measured 2,377 on Litolff and
repaired it at `gather.py`. **This removes the last excuse — it is not a
print-quality artefact**, and the two lanes reached it independently.

## 9. A live defect in a shipped instrument — and the same shape twice more

⚠️⚠️ **`tools/omr/score_reading.py` could not score any page but the first, and
the failure was a complete table of ZEROS.** See §0; **[mgr] repaired in
`dcdff9f2`.**

⚠️ **The lane's own adapter had the identical shape**, and only the REACH line
disagreeing with the report caught it. A third instance in
`attribute_extras.legacy_dets` was caught by its DEAD-at-zero-reach guard.
**Three instances of one bug in one night, in three files, each caught by a
control and by nothing else.**

## 10. ⚠️ A hazard the lane reproduced in its own first arm

Gathered **one page at a time**, page 0 decides `2/4` (`voted`) and pages 1 and
2 **abstain** `bars_name_a_length_without_a_form`. With no meter,
`size_measure_rest` never fires and every whole rest exports at the 4.0 fallback
in a 2.0 bar: **page 1 scores 30 of 162 part-bars**, 108 of 132 disagreements
literally `('rest', 4.0)` against `('rest', 2.0)`.

That is not a reading failure. It is CLAUDE.md's own recorded hazard — *"the
one-page cut silently disables every PAGE-SPANNING mechanism, which then reads
as a pipeline gap"* — **reproduced by this lane on itself.**

**In ONE three-page gather:** `system/0/0` votes `2/4`; systems 1 and 2 **CARRY
it at support +10.0 and +6.0**; `measure_rests_read` **85 → 214**;
`empty_bars_padded_without_meter` 1 → 0. ⚠️ **That is `OMR_METER_CARRY`'s first
engraved contact where the result can be checked against the actual encoding,
and it is correct on both carried systems.**

⚠️ Pages 0 and 2 of the combined record reproduce the single-page reading scores
**to the symbol** (0.947 and 0.903) — the determinism control for the whole lane.

## 11. FOR A HUMAN

1. **§5's precedence.** `adjudicate_key_signature` prefers the locator over the
   template and the reason it gives is refuted here: template 20/20, locator
   6/30. The refusal behind the precedence was priced on **scans**, so this is
   *evidence*, not a licence — but it is exactly the named new evidence the
   *PREMISE ENCODED IN A REFUSAL* rule asks for.
2. **§5's mechanism.** `min_height_spaces = 1.10` against flats measuring 0.94
   after the header erasure. **One LilyPond render would say whether that is
   Verovio's spacing or the erasure — and if it is the erasure, it is
   everywhere.**
3. **Whether the staged CLI should do weight routing** (§1). Today an engraved
   PDF gets whatever weights are typed.
4. The `dynamic_letter` precision hole (0.491) and the page-2 spurious barline.

## 12. What is NOT established

**n = 1 work, 1 movement, 24 bars, 3 pages, 1 renderer.** **A render is not a
scan**, and §5's mechanism in particular may be Verovio's key-signature spacing.
The `accidental` family is excluded and its 20-of-100 is **not** a notation
result. **No OMR-NED figure, deliberately** — every question here is a reading
question. **Nothing was checked against a print by eye; no crop was cut.** The 8
beam-mate firings and the single `notehead_is_a_whole_rest` deletion on page 2
are unverified. `dynamic_letter` precision and the spurious barline are measured
and undiagnosed. **Nothing is proposed for any constant, flag or default.**
