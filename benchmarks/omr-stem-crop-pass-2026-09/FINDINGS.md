# The stem CROP PASS — the print, on two publishers

**No code outside `benchmarks/`.** `git diff` against the integration base for
`tools/ backend/ CLAUDE.md docs/` is **empty** — verified at integration.

⚠️ **PROVENANCE.** The measuring session was a subagent and the harness refused
it a findings file (both `Write` and a Bash heredoc), so its record is the five
commit messages of `claude/stem-crop-pass-2026-09` plus the committed JSON.
This file is that record transposed at integration, and everything marked
**[mgr]** was re-derived by the managing session from the committed data rather
than relayed. `probe/score.py` re-derives every table.

The debt paid is
[docs/handoff-2026-09-17-the-ink-is-fused.md](../../docs/handoff-2026-09-17-the-ink-is-fused.md)
§6: *"**No note has been checked against the print in any stem arm** … the crop
pass is owed and has never been done for stems."*

---

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED**: `[C9 + L10]` — a stem attaches on the RIGHT going UP or the LEFT
going DOWN. Also touched: *no stem means a whole note* (`[C15]`, which the
registry files as ASSERTED with **no figure**).
**FALSIFIED BY**: a printed right-and-down stem. **None was found in 96.**
**NOT CONFIRMED WITH SEAN**: nothing here was put to him. The beam-mate
default, the width cap and the box-width test are all **his call**.

## The sample — pre-registered in its own commit BEFORE any crop existed

Commit `cc24eaad`, seed 20260918, one RNG per publisher, rows sorted by
subject, both row files md5-receipted. **Commit order is the only form of that
claim a later reader can check.**

| bucket | Litolff pop / drawn | Breitkopf pop / drawn |
|---|--:|--:|
| too WIDE (oversampled — it IS the width-cap population) | 237 / **30** | 358 / **30** |
| too SHORT | 199 / 12 | 298 / 12 |
| NO component overlaps | 167 / 12 | 197 / 12 |
| pair rule dropped one | 73 / 12 | 178 / 12 |
| at a CELL EDGE | 70 / 12 | 22 / 12 |
| too TALL | 47 / 12 | **476** / 12 |
| **positive control** (disjoint `decided` population) | 1,443 / **16** | 1,791 / **16** |

Added mid-pass at the manager's direction, **reported apart and never pooled**:
the 26-head standoff (a census, not a sample) and 31 whole-note contradictions.

`probe/census_rows.py` **imports** `rejection_census.census` rather than
restating it and reproduces both published tables exactly (0 cells drifted),
plus the width-cap 217 — two published figures reproduced independently.

---

## 1. ⚠️⚠️ THE 26-HEAD STANDOFF BREAKS 16-0 TO THE ATTACHMENT READER, AND THE SHIPPED TIER SCORES ZERO

`omr-stem-attachment-2026-09` refused to ship its tier partly because it could
not tell which of two mechanisms was wrong: *"The beam-mate's 0.984 is
Litolff-only, leave-one-out, and has NEVER been measured on Breitkopf. One of
the two is wrong 15% of the time and no instrument here can say which."*

**The print can.** Of the 26 Breitkopf heads where the raster attachment
convention and the **SHIPPED, default-on** beam-mate tier disagree:

| | n |
|---|--:|
| settled by the print | **16** |
| of those, print agrees with **ATTACHMENT** | **16** |
| of those, print agrees with **BEAM-MATE** | **0** |
| `cannot_tell` | 8 |
| **not a notehead at all** (both readers gave a direction to a DOT) | 2 |

⚠️ **[mgr] Re-derived independently from `ADJUDICATION-standoff.json`: settled
16, attachment 16, beam-mate 0.** ⚠️ **[mgr] And the protocol was genuinely
BLIND** — the file records that *"tiles carried an opaque id; which reader said
what was in the manifest and was NOT opened until every verdict here was
written"*, which is the standard the pre-fill Phase C pass set.

⚠️ **That tier's 0.984 had only ever been measured on Litolff, leave-one-out.
This is its first second-publisher contact.**

⚠️ **READ IT WITH THE INDEPENDENCE LIMIT (§6).** What makes it more than a
count: in **5 of the 16** the stem ends in a printed FLAG or runs into a BEAM —
**the beam-mate's own kind of evidence agreeing with the attachment reader** —
which would put the tier's error in its **GROUPING** rather than in its
convention. **Hypothesis, instances named.**

⚠️⚠️ **THE DEFAULT IS SEAN'S CALL AND NOTHING WAS FLIPPED.**

## 2. ⚠️⚠️ THE BIGGEST FINDING IS NOT ABOUT STEMS: 46 OF 180 BOXES ARE NOT NOTEHEADS

**15.6% Litolff, 35.6% Breitkopf.** And **Breitkopf's largest census bucket is
BARLINES**: `too TALL` is 476 heads / **31.1%** there — the handoff's own
headline inversion — and it is **12 of 12 not noteheads** in this sample, every
one a box **0.40–0.45 spaces wide** on a vertical rule. `at a CELL EDGE` is 11
of 12 the same way.

⚠️ **[mgr] Re-derived from `out/score-breitkopf.json`:** bucket `too TALL`
reads `n: 12`, `not_a_notehead: 12`, `stem_printed_up: 0`,
`stem_printed_down: 0`, `no_stem_printed: 0`, `cannot_tell: 0`.

⚠️⚠️ **THIS QUALIFIES §2's FOUNDATION**, which is the premise a within-blob
reader rests on: *"the ink is there and forms components; they are simply not
stem-shaped."* **A within-blob stem reader has nothing to recover in a
barline** — so a large part of the Breitkopf population is not a notehead
missing its stem but a **barline the detector called a notehead**. Qualified,
not refuted: Litolff's WIDE 237 is unaffected.

The rest are **read off the plate, not inferred**: two **whole rests**, a
printed capital **B**, the `e` of the printed word **cresc**, a **bass clef**, a
**trill wavy line**, eighth rests, an augmentation dot, a repeat-barline dot, a
system's **final barline**, and one box holding almost no ink at all.

⚠️ **A notehead is ~1.3 spaces wide**, and a floor at **width < 1.0 spaces
catches 39 of the 46 at a cost of 0 of 63 real stems** — measured and
**NOT proposed**: it is a GATHER change, and it is measured only on heads the
census already abstains on.

## 3. ⚠️⚠️ THE WIDTH CAP'S RECOVERIES ARE REAL — 33 OF 33, ZERO JUNK

Against the handoff's convention-vs-convention estimate of *"roughly 73% real
and 27% junk"*, which it explicitly declined to trust. One-sided 95%
Clopper-Pearson lower bound **0.913**. Litolff 9/9, Breitkopf 24/24.

⚠️ **[mgr] Re-derived from `out/score-breitkopf.json`: `width_cap.real: 24`,
`width_cap.junk: 0`, `real_share_of_settled: 1.0` over 28 sampled / 24
settled.**

⚠️ **NOT a recommendation to move `max_width_lines`**: the print settles only
**33 of 55 (60% pooled, 33% on Litolff)**, and that subset is **by construction
the legible one**. It removes the junk worry; it does not price the cap.

⚠️ **A NEW FACT: the width cap recovers 345 heads on Breitkopf.**
`width_cap_check.py` had only ever run on Litolff, so the published **217 is a
Litolff figure.**

## 4. ⚠️⚠️ SEAN'S STEM CONVENTION IS 96 OF 96 AGAINST THE PRINT

**67 down-and-LEFT, 29 up-and-RIGHT, ZERO right-and-down**, across two
publishers — where the registry records it supported only by reading-vs-reading
agreement (95.9 / 98.2).

⚠️⚠️ **Three tiles appeared to REFUTE it and all three dissolved at 1.8× zoom**
— the inverted-U below the head is two spaces lower and attached to nothing.
**A convention this repo has refuted before deserved the zoom rather than the
headline.**

## 5. ⚠️⚠️ `no stem means a whole note` — the population is a CLASS failure, not a convention failure

Of 31 heads the record calls WHOLE and still gives a direction, **17 are
adjudicated and not one is a whole note whose DIRECTION is the false claim**:

- **8 are the two round counters of a printed time-signature digit 8** — three
  of them on one cautionary `9/8` after a system's final double barline;
- **5 are the white GAP between two thick staff lines**;
- **2 are a dotted HALF note with a printed up-stem** (class false, direction
  RIGHT);
- 1 is a hairpin wedge.

**In 16 of 17 the CLASS is false**, so `[C15]` is neither contradicted nor
confirmed by this population. 11 Breitkopf heads not reached, ranked, cheapest
first: `V010`, then `V003 V007 V008 V012 V013 V014 V016 V020 V021 V023`.

⚠️⚠️ **AND THE METHOD WARNING IS THE REAL PRODUCT OF §5: at tile magnification
the adjudicator read two of these WRONG and the wide strip corrected both** — a
numeral and a dotted half note each read as *a hollow head with no stem*.
**A crop centred on a head cannot tell you the head is a NUMERAL.** Use a
full-width strip.

## 6. ⚠️ THE INDEPENDENCE LIMIT, stated by the session against its own result

**The adjudicating eye is NOT independent of the attachment reader** — it
measures ink beside the head, and so does the convention. So §1's 16-0 and §4's
96/96 are properly *"the ink beside the head behaves as the convention says"*,
which is weaker than *"the beam-mate is wrong"*. **One adjudicator, so there is
no inter-rater figure.**

## 7. ⚠️⚠️ `cannot_tell` REFUSES THE READING ITS AUTHOR WANTED

**62.5% for Litolff CONTROLS against 58.9% for its stemless SAMPLE** — the
same. So *"the stemless heads are the illegible ones"* is **FALSE**: on that
plate ~60% of noteheads cannot have their stem adjudicated by eye **whether the
pipeline read them or not**, and every Litolff figure here carries that.
Breitkopf: **12.5% / 17.8%**.

⚠️ Litolff's raster is **`bpc: 1`, genuinely BITONAL**, and 600 dpi is
**exactly** its native resolution (2897×3813 on 347.64 pt) — so **a fused blob
is fused ON THE PLATE**, and §3's *"the ink is FUSED"* arrives from the print
side. Breitkopf's native is 531 dpi, so rendering at 600 buys nothing. **There
is nothing better available for Litolff.**

## 8. ⚠️ THE FRAME CONTROL REFUSED ONE STAFF, AND THAT IS A FINDING

`--require-frame` passed every page of both samples (**+86.7 to +234.1** grey
levels) and **refused** Litolff `staff/3/1/7` at **−5.4**. Diagnosed with a
full-width strip: **the staff is there and it TILTS, while `Q.STAFF_LINES`
stores one constant comb**, so mid-page the claimed rows sit half a space off
the print — the 8–17 px warp `OMR_CELL_LINE_TRACE` corrects per CELL, showing
up in the record's own page-level rows. Three heads excluded, **and the strip
was NOT widened until the test passed.**

---

## Crops — all tracked (nothing under an ignored path)

`out/print/`. ⚠️ Deliberately **not** `crops/`, which `.gitignore:112` excludes
and which a previous session's commit message claimed to have committed when it
had not. 112 crops tracked, verified.

Most decision-relevant: `wholenotes/EVIDENCE-timesig-digit-8.png`,
`wholenotes/EVIDENCE-dotted-half-not-whole.png`,
`wholenotes/EVIDENCE-strip-that-corrected-the-tile.png`,
`wholenotes/EVIDENCE-litolff-staffline-gaps.png`,
`frame-refusal-staff-3-1-7.png`, `standoff/sheet-S-0*.png`, `sheet-L-04.png`
(textbook beam + up-stems on the right), `sheet-B-24.png` (the printed capital
**B**), `zoom/sheet-L-zoom-L095.png` (the near-refutation, dissolved).

## WHAT IS NOT ESTABLISHED

n = **2 publishers, 8 pages**. **One adjudicator, no inter-rater figure.** The
eye is not independent of the attachment reader (§6). The Litolff
`cannot_tell` rate is the eye's and not the population's. §2's width
discriminator is measured **only on heads the census already abstains on**. §5
is 17 of 31. **No OMR-NED, deliberately.** Nothing was re-gathered. And
**nothing is proposed for any constant, flag or default** — the beam-mate
default, the width cap and the box-width test are all put to Sean.
