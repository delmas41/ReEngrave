# Re-pricing `OMR_SLOT_STITCH` against the page-normalised truth

Backlog item **A0b**, commissioned by Sean and queued since 2026-09-07:

> *"I am not fully convinced about the slot stitch — something feels off, like
> maybe it needs something else solved first."*

Measured on `e9a0a577`, transform `page_normalise` **v1.2.0**.
Harness: `reprice_arm.py`; data: `results-reprice.json`.

**No pipeline code was changed.** This arm exports an existing flag two ways and
scores it against two truths.

---

## 0. The answer in five lines

1. **The recorded reason in CLAUDE.md is wrong, and always was.** The knob table
   says *"It is OFF because it still costs OMR-NED"*. The FINDINGS it cites
   records the opposite — **−216 edits and −0.0048 pooled NED, an improvement**.
   The real recorded reason is **n=1**, which is a different and much better one.
2. **This arm reproduces the original's STRUCTURAL figures exactly** — Brahms
   p2 `entire staff` **715 → 1632** and parts **27 → 14** — **and its net to
   within two edits** (−214 against the recorded −216, on a tree two months of
   commits later). *Not* "to the edit": the structure is, the net is not.
   Emitted per field as `exact` / `close` in
   `results-reprice.json → reproduces_recorded_n1_measurement`.
3. **The raw truth understates the flag by ~9.5×.** Pooled, ON is **−240 edits**
   raw and **−2,278 edits** page-normalised.
4. **On the normalised truth `entire staff` goes to ZERO on every reached row**
   (2,238 → 0). The stitched output pairs 1:1 with the page's staves, which is
   what "structurally correct" was supposed to mean.
5. **n is now 3 rows / 2 distinct pages, not 1** — and every reached row
   improves in **both** columns. The original's stated blocker has moved.

---

## 1. Arm design, and why the two arms share one transcription

`OMR_SLOT_STITCH` is read inside `to_musicxml`. It is an **export** decision and
touches no detection. So this arm **transcribes once and exports twice**: both
predictions come from one stored transcription per row, and the delta is exactly
the flag with the detector's documented ±6-edit noise floor removed from the
comparison entirely.

| | |
|---|---|
| OFF arm | `scan_eval --tag=-stitchoff --page-normalised`, 20 rows, `OMR_SLOT_STITCH=0` |
| ON arm | the same 20 `.omr.json` re-exported with `OMR_SLOT_STITCH=1` |
| scoring | all four cells, **78 pairs in ONE musicdiff batch**, `AllObjects` |

**Wall clocks.**

| stage | wall clock |
|---|--:|
| OFF arm — transcribe 20 rows + score raw & normalised | **1,846.4 s** (30.8 min) |
| ON arm — re-export 20 rows (+ normalise) | **1.3 s** |
| four-cell musicdiff batch, 78 pairs | **596.9 s** (10.0 min) |

### ⚠️ The ON arm has no transcription wall clock, and that is BY DESIGN — not the cache trap

The documented hazard is that `scan_eval.run_pipeline` returns early on an
existing fixture, so a second arm **silently never runs** and reports a flawless
*"identical on every bucket and every row"*. That failure mode is *an arm that
did not execute*. Here the sharing is deliberate, and execution is **proven by a
pattern a cache accident cannot produce**:

* the fixtures directory was verified **empty (0 files)** before the OFF arm —
  recorded at the top of the run;
* the two prediction files' sha256 must **differ on every reached row and be
  identical on every unreached one**. Measured: **20/20 rows match that
  prediction exactly, 0 mismatches.** A cache collision gives identical
  *everywhere*; this gives identical in exactly the 17 places the flag provably
  cannot act.

---

## 2. Reach — the finding that may matter more than the number

**The flag reaches 3 of 20 rows.** It is consulted *only* where the ordinal join
returns `None`, and it then abstains unless every staff of every system carries a
contextual slot.

| why a row is unreachable | rows |
|---|--:|
| single system — nothing to stitch | 9 |
| ordinal join **succeeds** — flag never consulted | 8 |
| **REACHED** — ordinal refused, slot join supplies it | **3** |

Reached: `beethoven-sym5-mvt1-984073-p3`, `beethoven-sym5-mvt1-575951-p3`,
`brahms-sym1-mvt1-317803-p2`.

### Reach is gated by contextual slot completeness BY CONSTRUCTION — though no current row is lost to it

⚠️ **Stated carefully, because the strong form over-asserts.** In the current 20
rows, **not one** row is unreached for slot incompleteness: the 17 are
single-system (9) or ordinal-succeeds (8). The gate is real in the *code*, and
the only page ever observed losing to it is a historical transcription. So this
is a **mechanism** claim with one archival instance, not a measured rate.

`_stitch_slots_by_slot` abstains on **a single** staff with `slot_index = -1`,
deliberately — placing the staves that resolved and dropping the rest would lose
music. On the *previous* (graft09-era) transcription of Bach Brandenburg 3, the
ordinal join refused across 6 systems of `[1, 2, 3, 12]` and the slot join
**still abstained**, because the contextual pass resolved only **3 of 12 staves
in system 0** (`slot_index = [-1 ×9, 0, 1, 2]`). That page was structurally the
most fragmented in the corpus and the flag could not touch it.

**So the identity layer is UPSTREAM of this structural gain, not parallel to
it** — in the weaker, surviving form: *where* a page is lost to slot
incompleteness, only the contextual pass can recover it, and no amount of work
on the stitcher itself can. That is a scheduling conclusion about the dependency
direction; it is **not** a claim that slot incompleteness is currently costing
this corpus anything measurable, because on these 20 rows it costs exactly
nothing.

⚠️ *Caveat recorded honestly*: at `e9a0a577` Bach's ordinal join now **succeeds**
(its segmentation changed with the bracket/choir work), so Bach is no longer an
example of this failure — but the abstention rule that produced it is unchanged
and still gates reach.

---

## 3. The four cells

Per-row edits. `d` is ON − OFF; negative is better.

| row | reach | parts off/on | RAW off | RAW on | d | NRM off | NRM on | d |
|---|:--:|--:|--:|--:|--:|--:|--:|--:|
| beethoven-984073-p1 | – | 12/12 | 1273 | 1273 | 0 | 644 | 644 | 0 |
| beethoven-984073-p2 | – | 11/11 | 4347 | 4347 | 0 | 2390 | 2390 | 0 |
| **beethoven-984073-p3** | **YES** | **19/11** | 3034 | 3017 | **−17** | 1903 | 1315 | **−588** |
| beethoven-984073-p4 | – | 11/11 | 4673 | 4673 | 0 | 2700 | 2700 | 0 |
| beethoven-575951-p1 | – | 12/12 | 1354 | 1354 | 0 | 680 | 680 | 0 |
| beethoven-575951-p2 | – | 11/11 | 4408 | 4408 | 0 | 1942 | 1942 | 0 |
| **beethoven-575951-p3** | **YES** | **19/11** | 3172 | 3163 | **−9** | 1763 | 1170 | **−593** |
| beethoven-575951-p4 | – | 11/11 | 4714 | 4714 | 0 | 2579 | 2579 | 0 |
| dvorak-p5 | – | 15/15 | 661 | 661 | 0 | 661 | 661 | 0 |
| dvorak-p6 | – | 15/15 | 2582 | 2582 | 0 | 2582 | 2582 | 0 |
| dvorak-p7 | – | 15/15 | 5687 | 5687 | 0 | 5687 | 5687 | 0 |
| brahms-p1 | – | 14/14 | 3431 | 3431 | 0 | 1737 | 1737 | 0 |
| **brahms-p2** | **YES** | **27/14** | 6547 | 6333 | **−214** | 5506 | 4409 | **−1097** |
| brahms-p3 | – | 14/14 | 4571 | 4571 | 0 | 2943 | 2943 | 0 |
| brahms-p4 | – | 14/14 | 7013 | 7013 | 0 | 3843 | 3843 | 0 |
| mahler-p2 | – | 17/17 | 1115 | 1115 | 0 | *un-normalised* | | |
| mahler-p3 | – | 13/13 | 3066 | 3066 | 0 | 2142 | 2142 | 0 |
| mahler-p4 | – | 18/18 | 4149 | 4149 | 0 | 3209 | 3209 | 0 |
| mahler-p5 | – | 17/17 | 2968 | 2968 | 0 | 2301 | 2301 | 0 |
| bach-p1 | – | 12/12 | 6148 | 6148 | 0 | 6148 | 6148 | 0 |

**CONTROL: all 17 unreached rows are identical to the edit in BOTH columns.**
The only rows that move are the rows the flag can act on. PASS.

### Pooled

| pool | cell | OMR-NED | edits | entire staff | entire measure |
|---|---|--:|--:|--:|--:|
| all 20 rows | off raw | 0.8439 | 74,913 | 17,520 | 29,633 |
| | **on raw** | **0.8416** | **74,673** | 20,384 | 26,908 |
| 19 normalisable | off raw | 0.8469 | 73,798 | 16,871 | 29,450 |
| | on raw | 0.8444 | 73,558 | 19,735 | 26,725 |
| | off norm | 0.6465 | 51,360 | 3,596 | 14,640 |
| | **on norm** | **0.6181** | **49,082** | **1,358** | 13,094 |
| **3 reached rows** | off raw | 0.9088 | 12,753 | 892 | 8,113 |
| | on raw | 0.8939 | 12,513 | 3,756 | 5,388 |
| | off norm | 0.7424 | 9,172 | 2,238 | 2,926 |
| | **on norm** | **0.5596** | **6,894** | **0** | 1,380 |

⚠️ **The RAW and NORMALISED columns are SEPARATE BENCHMARK ERAS.** OMR-NED is
symmetric, so merging truth parts moves the denominator too. Neither normalised
figure may be differenced against any un-normalised one, historical or
otherwise. The valid comparison is **ON vs OFF within one column** — both cells
there share a truth, a tree and a transcription.

---

## 4. Buckets, on the reached rows

| bucket | RAW off | RAW on | d | NRM off | NRM on | d |
|---|--:|--:|--:|--:|--:|--:|
| entire measure insert/delete | 8113 | 5388 | **−2725** | 2926 | 1380 | **−1546** |
| entire staff insert/delete | 892 | 3756 | **+2864** | 2238 | **0** | **−2238** |
| wrong note | 2717 | 2249 | −468 | 2988 | 3745 | +757 |
| wrong note head | 520 | 624 | +104 | 362 | 668 | +306 |
| wrong clef | 50 | 26 | −24 | 8 | 12 | +4 |
| wrong timesig | 106 | 86 | −20 | 92 | 96 | +4 |
| wrong dot | 43 | 68 | +25 | 39 | 97 | +58 |
| wrong keysig | 82 | 95 | +13 | 70 | 113 | +43 |

**The two columns tell opposite stories about the same output, and that is the
whole point.**

* On the **raw** truth the flag *buys* `entire staff` (+2,864) and *pays* in
  `entire measure` (−2,725). 19 or 27 fragments pair with more of the 18/21
  truth parts than 11 or 14 continuous parts do — so fragmenting is rewarded by
  a truth that has more parts than the page has staves. Net −240.
* On the **normalised** truth, where the truth has exactly one part per printed
  staff, **`entire staff` collapses to zero**. Every part we emit pairs. Net
  −2,278.

⚠️ **The normalised gain is a TRADE, not a free win.** With the parts finally
paired, the aligner can compare note-by-note, and `wrong note` **rises** (+757)
along with `wrong note head` (+306) and most small buckets. Structural charge
becomes elementwise charge. It is still −2,278 net, but the flag is not making
those notes more correct — it is exposing them to being scored at all.

---

## 5. What the transform ADDED vs what it REMOVED (rule 4)

Raw → normalised, within one arm, over the 19 normalisable rows. **All four
figures below are emitted by the harness** into
`results-reprice.json → transform_accounting`; none is derived in prose.
Structural guard: `check_harness_structure.py` (see §6b).

⚠️ **TWO DENOMINATORS AND TWO SCOPES, AND THE SCOPE FLIPS THE OFF-vs-ON SIGN.**

* **denominator** — the headline percentage is `added ÷ (added + removed)`,
  the share of *gross movement* that is manufactured. The other reading,
  `added ÷ removed`, is a larger number (20.5% for OFF).
* **scope** — `pool_net` pools each bucket over the rows *first* and then takes
  the raw→norm delta, so within-bucket movement in opposite directions on
  different rows cancels. `row_gross` sums per-(row, bucket) positives and
  negatives separately and cancels nothing.

| arm | scope | removed | added | added ÷ (a+r) | added ÷ removed |
|---|---|--:|--:|--:|--:|
| OFF | **pool_net** | 28,215 | 5,777 | **17.0%** | 20.5% |
| ON | **pool_net** | 32,080 | 7,604 | **19.2%** | 23.7% |
| OFF | row_gross | 30,207 | 7,769 | 20.5% | 25.7% |
| ON | row_gross | 32,309 | 7,833 | 19.5% | 24.2% |

⚠️ **Two of those cells are 20.5% and they are different quantities** — OFF's
`pool_net` *added ÷ removed* and OFF's `row_gross` *added ÷ (a+r)*. Quote the
scope and the denominator together or the number does not identify itself.

**I quote `pool_net`, and the choice is deliberate**: the claim it supports is a
*pooled* one, and pooling before differencing is the same operation the pooled
edit counts elsewhere in this file use. ⚠️ **A reader who re-derives the ratio
per row gets the opposite ordering** — `row_gross` says OFF carries the larger
artefact share (20.5% vs 19.5%, or 25.7% vs 24.2% on the other denominator),
while `pool_net` says ON does (17.0% vs 19.2%). The reversal holds on **both**
denominators, so it is a property of the scope and not of the ratio. Both are
emitted so the disagreement is visible rather than latent.

The transform manufactures real artefacts and they are not negligible: ~1 edit in
5 of the gross movement is **added**, led by `wrong note` +3,661, `wrong
flag/beam` +486, `wrong direction` +430, `wrong accidental` +221, `wrong tie`
+214 and `wrong lyric` +201 (6 → 249, the artefact the commission flagged).

⚠️ **On `pool_net` the ON arm carries MORE added artefact than OFF** (7,604 vs
5,777), so on that scope the normalised comparison is **not** flattering ON with
a cleaner truth. ⚠️ **On `row_gross` that reverses** (24.2% vs 25.7%), so this
is a statement about the pooled scope and not a scope-free fact. What does not
depend on the choice: the added artefact is **roughly 1 edit in 5 of gross
movement on either scope and either arm** (17.0-20.5%), i.e. of the same order
for both arms — far too similar between them to manufacture the −2,278, which is
4.4% of the OFF arm's normalised total.

---

## 6. Controls

| control | result |
|---|---|
| fixtures dir empty before the run | **0 files** |
| predictions differ **iff** reached | **20/20, 0 mismatches** |
| 17 unreached rows identical to the edit, both columns | **PASS** |
| export deterministic (same flag, fresh load) | **byte-identical** |
| reproduces the recorded n=1 figures | `entire staff` **715 → 1632 EXACT**, parts **27 → 14 EXACT**, net **−214 vs −216 (close, differs by +2)** |
| **dilution** — is ON just emitting fewer symbols? | **No.** pred symbols 38,919 → 38,884 (**−35, 0.09%**) while edits fall 240 (raw) / 2,278 (norm). Both `omr_ed` and the ratio fall together, which is the opposite of the symmetry artefact. |
| OFF/normalised cell agrees with `scan_eval`'s own run | **0.6465 / 51,360, exact** (same derived-truth files reused, not regenerated) |

**`Could not import wedge` (music21)** appears while parsing the truth. It is
pre-existing, applies to both arms identically, and therefore cannot affect any
delta reported here.

---

## 6b. Two harness faults found while emitting the above — both silent, one expensive

Recorded because each produced a **clean-looking exit** and neither would have
been caught by the checks that were being run.

**(1) `ast.parse` validates syntax, not STRUCTURE — and a `def` at column 0 ends
the function it is written inside.** Adding `transform_accounting` and
`reproduces_recorded` by text-insertion put two module-level `def`s in the middle
of `main()`. That is *valid Python*: it terminated `main()`'s body, and the 150
lines after it — the pooling, the `doc` literal, **the file write** and the whole
report — silently became the body of `reproduces_recorded`. `main()` then fell
off its end returning `None`, so `sys.exit(None)` **exited 0**, printed nothing,
wrote nothing, and burned **615 s of musicdiff first**. `ast.parse` passed
throughout.

The replacement check asks where the code *is*, not whether it parses — it walks
the AST, extracts `main`'s own source segment, and asserts the write, the return
and each call site are inside it. It fails RED against the broken revision.

**(2) The musicdiff batch sits at a 0.5% margin against its own default
timeout.** `omr_ned.score_batch` defaults to **600 s**; this 78-pair batch took
**596.9 s** on the run that produced the committed numbers and **timed out at
exactly 600.0 s** on the very next run of the identical pairs. A timeout raises
rather than returning a wrong number, so no result was ever corrupted — but the
arm was reproducible by luck. `timeout_s=3600` is now passed explicitly.

⚠️ **Anyone scoring a batch this size on scans should pass `timeout_s`.** The
default was set for smaller batches and 78 dense orchestral pairs is over it.

---

## 7. ⚠️ The evidence base is n=3 rows but n=2 DISTINCT PAGES

`beethoven-984073-p3` and `beethoven-575951-p3` are **the same music** — window
mm 49–82 of the same Litolff plate, in two different scans (`works.json` records
the plate fingerprint: every system boundary matched, max normalised
disagreement 0.0013).

So the reached population is **Beethoven 5 p.3, measured twice, and Brahms 1
p.2**. The twin agreeing (−588 / −593 normalised, `entire staff` → 0 on both) is
a **reproducibility** signal across two rasters, not independent evidence about
a second piece of music.

The original's blocker was *"priced on exactly one page"*. It is now two pages,
both multi-system scans where a tacet staff is suppressed. That is a real but
**modest** widening, and it is the honest ceiling of what this corpus can offer:
only 3 of 20 rows have the structure the flag addresses.

---

## 8. Verdict on the hypothesis

**Sean's hypothesis was that the metric was charging for something other than
correctness. That is CONFIRMED — and the recorded justification turns out to be
worse than he thought, in a way that changes the decision.**

**(a) The stated reason never held.** CLAUDE.md's knob table says the flag is off
because *"it still costs OMR-NED"*. `omr-staff-structure-2026-09/FINDINGS.md`
§4 — the document that table cites — records **0.8283 → 0.8235 and 34,962 →
34,746 edits, an improvement**, and gives the real reason: *"−216 edits from
n=1 ... is not enough to change a default."* Somewhere between the measurement
and the summary, *"a real gain on too little evidence"* became *"a cost"*. This
is the project's recurring **documentation-drift** shape, in the direction that
suppresses a working mechanism.

**(b) The metric artefact is real and large.** The raw truth has 18 parts where
the page prints 11, and 21 where it prints 14 — so it rewards fragmentation
outright. Correcting only that, the same output on the same tree scores
**−2,278 instead of −240: the raw truth understates this flag by ~9.5×.**

**(c) But the vindication does NOT rest on the reshaped truth, and that matters.**
Per Sean's standing rule, a better score on a truth we reshaped proves nothing
on its own. The load-bearing fact is that **all three reached rows also improve
on the RAW, unreshaped truth** (−17, −9, −214), on a tree where 17 control rows
are byte-identical. The normalised column explains *why* the raw gain is small;
it is not what makes it a gain.

**So: which claim does the number support?** It supports *"the recorded reason
for keeping the flag off does not survive"* — decisively, on two independent
grounds (the reason was misrecorded, and the truth that produced it bills a
convention). It does **not** on its own support *"the mechanism is good"*; what
supports that is the structural result the original already established — 27
fragments → 14 continuous parts with the suppressed Trompeten slot correctly
short — now corroborated by `entire staff` reaching **exactly zero** against a
truth shaped like the page.

### Recommendation

**`OMR_SLOT_STITCH` is a legitimate candidate for default-ON, but the evidence
does not yet carry it** — and the reason is *n*, exactly as the original said,
not the score. Three of the four stated objections are now addressed: the score is better in both columns,
the named-bucket regression is an artefact of a truth with too many parts, and
n has moved from 1 to 2 pages. Before flipping it, someone should:

1. **Correct the CLAUDE.md knob entry** — it currently states a fact its own
   source contradicts. This arm changed no documentation; the correction is
   flagged, not made.
2. **Re-verify the engraved no-op.** The original measured 11/11 byte-identical
   because every engraved fixture is single-system. That should be re-confirmed
   on the current tree, not assumed.
3. **Accept that the `entire staff` bucket will get worse** on the raw headline
   (+2,864 on reached rows) while the pooled figure improves. Anyone attributing
   by that bucket alone will read a regression — the corollary the original
   already recorded, now with a second and third row behind it.

### The named blocker for default-ON, with its cost

**One multi-system scanned page from a different WORK and a different PUBLISHER
where the ordinal join refuses.**

That is the single piece of evidence this arm cannot supply and that would
settle the default. The reached population is 2 distinct pages of one structural
shape (multi-system scan, tacet staff suppressed), in two publishers — Litolff
and Breitkopf — but only two pieces of music. `OMR_MOVEMENT_REFERENCE` is the
precedent: a structural change that looked settled on a narrow set and needed a
second, differently-sourced page before it could be trusted.

⚠️ **Cost: this is CORPUS WIDENING, not a re-run.** The current 20-row gate
contains no further candidate — every other row is single-system or joins by
ordinal. A new row needs a scanned multi-system page located, its measure window
hand-verified against the print, and its `staves[i].parts` map hand-read, which
is the `works.json` row-verification protocol (`ROW_VERIFICATION_CHECKLIST`),
not a benchmark invocation. Until such a row exists, **the flag should stay off**
— not because it scores badly, which it does not, but because two pages of one
shape is the same evidentiary objection the original raised, merely doubled.

---

⚠️ **Not measured here, deliberately:** `OMR_CONDENSED_PARTS`. It composes with
this flag and is separately argued to be an anti-feature (it improves the metric
by making the output *less* faithful to the page). Confounding the two was
explicitly out of scope.
