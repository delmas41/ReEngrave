# The grid extrapolates past the staff at a pitch the plate does not print

2026-09-17. **No code outside `benchmarks/`** — `git status` lists seven files,
all under this directory. Nothing was re-gathered, no flag was flipped, no
default was changed. Pre-registration: [PREREGISTRATION.md](PREREGISTRATION.md),
committed **alone and first** (`7947a5ee`), before a probe existed or a record
was opened.

## 0. THE ONE-LINE RESULT

`pitch_resolver` reads a notehead's staff position as
`(y - top_y) / half_step`, where `half_step` is half the average gap between
**this staff's own five printed lines**. Inside the staff that is a
measurement. Outside it, it is an extrapolation at exactly **1.000×** — and
measured straight off the raster on 1,061 strips, the Litolff plate prints its
ledger rungs at **1.032 / 1.079 / 1.048 / 1.111** of the staff spacing, so the
grid has fallen **half a step behind by the fourth ledger line** and every note
there is read a diatonic step wrong.

On the second publisher the same measurement over 1,354 strips reads
**1.000 / 0.992 / 0.991 / 0.969 / 1.000 / 0.973** and the grid never falls half
a step behind, out to the sixth rung.

**66 of Litolff's 2,347 heads (2.81%) against 0 of Breitkopf's 3,337.**

⚠️ **66 is a FLOOR.** A further 44 Litolff heads stand beyond the fourth rung,
where the drift is larger and only 10 strips reach; they are unscored, in the
direction that makes the number worse.

## 1. WHAT THE PRE-REGISTERED PREDICTIONS DID

| | | |
|---|---|---|
| **P1** Litolff signed residual grows outward | **FALSIFIED as written** | §2 |
| **P2** the same statistic is ~0 inside the staff | **PASSED**, twice, independently | §3 |
| **P3** Breitkopf is near zero or inward, and weaker | **PASSED in the strong form** | §4 |
| **P4** the drift accounts for the §3a stem reversal | **FALSIFIED** | §6 |

Two of four failed. The headline survives because it does not rest on either
of them — it rests on a measurement neither prediction anticipated.

## 2. ⚠️ P1 IS FALSIFIED, AND ITS REPAIR IS NOT A RESCUE — IT IS A DIFFERENT QUANTITY

P1 asked the question through the signed residual `pos - round(pos)`. Measured
on Litolff, the outward-signed residual reads **+0.114 / +0.069 / −0.100 /
−0.037** across the four ledger bands: positive and falling where P1 said
positive and rising, then changing SIGN.

**The residual is bounded to ±0.5 and therefore WRAPS.** A stretch of 0.2
half-steps per rung is indistinguishable from a stretch of 0.2 minus a whole
step once the accumulation passes half a step, which at this plate's pitch
happens around the third rung. P1 was written without that in it, which is a
fault in the prediction and not in the mechanism.

⚠️ **The temptation here is the whole trap this repo keeps paying for**: having
predicted a monotone rise and got a sign change, the cheap move is to explain
the sign change with the wrap and call P1 confirmed. It is not confirmed. What
is recorded instead is that the residual **cannot answer this question at all**
past the second rung, and the answer came from measuring the printed rung
positions directly, which has no modulus in it (§4).

## 3. P2 PASSED, AND A SECOND, SHARPER VERSION OF IT ARRIVED FOR FREE

Inside the staff the same statistic reads **−0.034 / −0.002 / +0.011 / +0.023**
across four bands out from the middle line — flat, and an order of magnitude
under the outside figures.

⚠️⚠️ **AND THE DETECTOR HANDED OVER A MUCH BETTER CONTROL WITHOUT BEING
ASKED.** Of 1,878 `ledgerLine` detections on the Litolff record, **1,107 land
INSIDE the staff — every one of them at 0/2/4/6/8, the five printed staff
lines**, whose positions are known exactly. Scored there, the class's box
carries a bias of **+0.011 staff spaces at sd 0.048**: it locates a printed
horizontal line to a twentieth of a space. That is what licenses using a rung
as truth at all, and it was measured rather than assumed.

⚠️ It is also a finding in its own right and is NOT pursued here: the detector
fires `ledgerLine` on staff lines 1,107 times on four pages, and
`transcribe`'s ledger-ladder arbitration reads `ledgerLine` detections
directly. Whether that path filters them is unchecked.

**And the alternative that would have killed everything is ruled out.** If the
record's staff SPACING were slightly too small, everything outside would
stretch for a reason that has nothing to do with the engraving. Measured in the
same strips, the printed top→bottom span over the record's span is
**1.00000 on Litolff** (n=957) and 1.00450 on Breitkopf (n=947) — the grid is
right inside the staff, to five decimal places on the plate that drifts.

## 4. THE MEASUREMENT THAT CARRIES THE RESULT — off the raster, no detector

`probe_rungs_from_raster.py` renders the page at 600 dpi and finds the rungs as
rows of ink in a strip at the head's own x-range, exactly as `staff_detector`
finds staff lines — and finds the staff's five lines in **the same strip** as
its ruler, so nothing is carried in but where to look.

⚠️ **The scale is verified, not assumed**: the record's `staff_lines` for
`staff/1/0/0` read 1148/1163/1179/1195/1210, and a 600-dpi render of pdf page 1
has its dark rows centred at 1147.5/1163/1179/1194/1210.

**Control, printed in every run**: the staff's own five lines, found by the same
rule in the same strips, sit **+1.06 px** (Litolff, sd 2.38, n=5,201) and
**−0.33 px** (Breitkopf, sd 3.03, n=6,712) from the record — against a half-step
of 7.75 px. A strip in which the rule cannot recover four of the five staff
lines is REFUSED, not measured: 138 and 266 of them were.

| gap, × the staff spacing | Litolff (n) | Breitkopf (n) |
|---|--:|--:|
| edge → rung 1 | **1.032** (379) | **1.000** (604) |
| rung 1 → 2 | **1.079** (132) | 0.992 (279) |
| rung 2 → 3 | 1.048 (50) | 0.991 (121) |
| rung 3 → 4 | 1.111 (10) | 0.969 (54) |
| rung 4 → 5 | — | 1.000 (17) |

| the grid's error, half-steps | Litolff | Breitkopf |
|---|--:|--:|
| at rung 1 | +0.065 | +0.000 |
| at rung 2 | +0.223 | −0.016 |
| at rung 3 | +0.319 | −0.034 |
| **at rung 4** | **+0.541 — FLIPS** | −0.096 |
| at rung 6 | — | −0.151 |

**P3 passes in its strong form.** Breitkopf's gaps sit at or slightly UNDER
1.000 — the direction its independently measured 0.975 predicts — and its
cumulative error never reaches a quarter step in six rungs. ⚠️ Part of even that
is the grid's own +0.45% scale error on that document rather than the plate.

⚠️ **This is what rules the alternatives out.** If the cause were the
detector's box, the crop, the notehead's shape, the page warp or my arithmetic,
Breitkopf would show it too. It does not. The cause is a property of the PLATE,
which is what "ledger pitch is publisher-dependent" means.

**It also reproduces, from a third population, a result this repo already
had.** `omr-snap-ledger-2026-09` §2 measured the same convention off the ink of
117 hand-labeled notes: pooled edge→1st **1.055**, 1st→2nd 1.020, 2nd→3rd
1.017, with **Litolff 1.102/1.135 against Breitkopf 0.975** — the first gap
systematically the widest. Three populations, two of them detector-free, one
publisher split, same direction each time.

## 5. ⚠️ THE DETECTOR-BOX MEASUREMENT DISAGREES WITH THE RASTER AND THE RASTER WINS

`probe_rung_pitch.py` asks the same question of the model's `ledgerLine` boxes
and reads Litolff's gaps as **1.130 / 1.090 / 1.080** against the raster's
1.032 / 1.079 / 1.048. Same sign, same publisher split (Breitkopf 0.990 /
0.990 / 0.995), and the first gap is 10% too wide.

**The raster is the better instrument and the reason is already on file**: the
2026-09-03 ledger audit records a printed rung print-MERGING into the same
connected component as its neighbouring notehead, pulling a centroid by up to
a full half-step. A box drawn round merged ink sits further out than the line
it is meant to name. Both numbers are kept, and **no figure in §0 or §4 comes
from the detector**.

## 6. ⚠️⚠️ P4 IS FALSIFIED, AND THIS DOES **NOT** EXPLAIN THE STEM REVERSAL

The work was ranked by `docs/handoff-2026-09-17-two-brakes-and-a-ruler.md` §3a,
which measured the stem convention's accuracy rising to 0.939 four-to-six steps
from the middle line and then REVERSING to 0.765 beyond, and concluded the
position is what fails out there.

The position **is** what fails out there. It does not produce that reversal.

* Correcting the 32 own-staff heads that have ink truth *and* a projected stem
  to their TRUE position changes the convention's agreement by **exactly
  nothing — 17 of 32 either way.** Structurally it cannot: the convention flips
  at the MIDDLE LINE, and a one-step correction to a note six steps clear of it
  leaves it on the same side.
* The other candidate is refuted too. Split by `glyph_owner`, own-staff heads
  in the `6+` band read **0.713** and relocated copies **0.806** — the reversal
  is *worse* on the staff's own heads, so it is not the cross-staff copies
  either.

**§3a's reversal is still unexplained, and it is not this.** What this finding
is instead is a PITCH fault, which is the larger thing anyway.

## 7. ⚠️⚠️ THE CROP REFUTED MY OWN CLASSIFIER, WHICH IS WHY IT WAS CUT

The handoff's §5 ranked "crops, not code" first, because everything on the
thread was one of our readings agreeing with another. The first crop cut paid
for itself immediately and against its author.

An earlier cut of `probe_head_on_rung.py` scored **38.6%** of own-staff ledger
heads as wrongly placed. Cropping the worst of them showed `glyph/1/0/3/9/3`
sitting in the SPACE above the first rung, not on it: a notehead box on this
record is a median **2.62 half-steps tall**, taller than the step it sits on,
so "the rung is inside the box" also admits the neighbouring space, and a head
misclassified that way is scored WRONG **by construction**.

**The bias is vicious in exactly the direction that flatters the finding**: the
population one would naturally crop first — sorted by error — is the population
the classifier is wrong about.

Repaired by measuring the discriminator instead of assuming it, on the 836
heads INSIDE the staff whose line-or-space is not in doubt, in units of the
head's OWN height:

| | n | p5 | median | p95 | max |
|---|--:|--:|--:|--:|--:|
| head ON a line | 430 | 0.000 | 0.022 | 0.062 | 0.143 |
| head IN a space | 406 | 0.292 | 0.374 | 0.450 | — |

so the probe now answers ON below 0.15 and IN-A-SPACE above 0.29 and
**ABSTAINS between**, the empty-interval discipline this repo already applies
to dot windows, tie flanks and bracket columns.

⚠️ **The per-head figure that survives is still the weaker one and is not the
headline.** It reads 32.7% on Litolff against 0.9% on Breitkopf, over 52 and
222 heads, and it remains exposed to duplicate notehead detections (the crop
`glyph/4/0/0/9` shows two overlapping notehead detections at one position).
**§0's number comes from the raster and the measured pitch, not from it.**

⚠️ **And the crop's real payoff is that the drift is visible.** In
`out/print/zoom_glyph_4_0_0_9_2.png`, rung 1 sits on the grid's −2 tick and
rungs 2 and 3 stand progressively above the −4 and −6 ticks. The record agrees
to the detection: that cell prints its four rungs at −2.37 / −4.49 / −6.46 /
−8.80 where the grid says −2 / −4 / −6 / −8.

## 8. THE FIX IS NOT PROPOSED HERE, AND TWO ROUTES ARE ALREADY REFUTED

* **A corrected CONSTANT cannot work** and is refuted on file: no single factor
  serves Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00 at once
  (`omr-snap-ledger-2026-09` §3 swept it and it lost).
* **`measure_ledger_rungs` already exists** — `tools/omr/annotate/ledger_grid.py`
  — and does exactly this against a cell image, for the LABELING UI. Its only
  consumers are `annotate/server.py` and its own test. ⚠️ But "the fix exists"
  is not "the fix ports": it reads a raster, so a reader-side version is a
  **GATHER change**, which `readjudicate` and `reexport_arm` are both
  structurally blind to and which only two full re-gathers can price.
* ⚠️ Its own findings record the guard that any port must keep: a click beyond
  an incomplete ladder's reach **falls back to the grid**, because
  extrapolating a whole ladder from one distant rung measured WORSE than the
  constant. This probe reproduced that failure from scratch before adopting the
  rule — counting a lone 4th rung as the 1st invented a −6.02 half-step error.

## 9. WHAT IS NOT ESTABLISHED

* **n = 2 documents, 2 publishers, 8 pages.** The hand-labeled study covers
  nine publishers and agrees; this one does not widen that.
* **Nothing was re-gathered, re-exported or scored.** No MusicXML moved, and
  **no OMR-NED figure is claimed** — the metric is symmetric and a wrong pitch
  inside a bar it has already failed to pair costs it nothing.
* **The 66 heads are identified but not individually adjudicated against the
  print.** Ten crops were cut and looked at; the mechanism was confirmed and
  one classifier fault was found. The remaining heads are a population estimate
  from the measured pitch, not 66 hand-checked notes.
* **The consequence in the FILE is unmeasured.** A wrong staff position is a
  wrong pitch through any clef, but how many of the 66 reach an exported
  `<note>` depends on the exporter's own refusals and was not checked.
* **`+1`, `+9` and beyond are unscored** on Litolff (173 and 44 heads) — the
  interpolation needs both bracketing rungs, and past rung 4 only 10 strips
  reach.
* The Litolff record was gathered on a **dirty tree** (`9d4ccc85`, `dirty:
  true`); the Breitkopf one is the committed shared record.

## 12. (2026-09-30 evening) TWO READERS BUILT ON SEAN'S OPTION B — WIRED, A/B'd, PRINT-CHECKED

Numbered 12 because ROADMAP 2.44's own §10 (first reader) and §11 (reconciliation
measurement) live on unmerged branches (`worktree-agent-ab56d1d321c30c4bd`,
`claude/affectionate-mendeleev-db20a1`) this session's own tree does not carry.
This section is the build on `claude/acceptance-measure-notehead-box-e75821`,
based on `origin/main` `4a599ca9` (Sean's own option B decision).

### 12a. What was built

Two GATHER readers, each its own `Q` and `READERS` name (CLAUDE.md §10: two
rows from one reader on one raster are one signal; these are two mechanisms
over the SAME staff-erased raster, which is the only kind of "independent"
available without a second raster to read):

* **Reader 1, `Q.LEDGER_CLEAN_COUNT_POSITION`** (`gather.
  gather_ledger_clean_count_position`): Sean's own rule — scan outward from
  the staff's own edge, reusing `ledger_rung_ink` (ROADMAP 2.37) unchanged at
  a fine (0.08 staff-space) step, cluster the hits into actual rungs, and
  place the head ON the one rung whose middle third its ink touches, or in
  the space beyond the nearest one it does not. Fixes the WITHDRAWN first
  2.44 reader's below-staff bug (FINDINGS §11a: it counted steps from the
  BOTTOM line while `Q.NOTEHEAD_STAFF_POSITION` counts from the TOP) by
  converting explicitly: `pos = -steps` above, `pos = staff_half_steps +
  steps` below.
* **Reader 2, `Q.LEDGER_RUNG_GRID_POSITION`** (`gather.
  gather_ledger_rung_grid_position`): wraps `tools/omr/annotate/ledger_grid.
  measure_ledger_rungs` + `server.snap_to_staff` UNCHANGED (Sean: "reuse it;
  don't fork or copy it") — `snap_to_staff`'s own step is already top-line
  origin, so no conversion needed here.

`consequences.restate_pitch`: for a head outside its staff, where BOTH
readers have a row for that exact glyph AND agree, their shared position
overrides the raw rounded geometry (`reason=ledger_reader_agreement`); where
they disagree, geometry stands and the verdict is tagged
`position_and_clef_ledger_conflict`; where only one reader produced a row,
`position_and_clef_ledger_one_sided`. All three reasons are new and
queryable — "counted" (CLAUDE.md rule 8) means a distinguishable reason on
the record, not a separate ledger file.

10 new tests, `test_staged_ledger_two_readers_2_44.py`, RED-first against
fixture rows (no gather, following CLAUDE.md §6b and the 2026-09-29 rule
against pricing runs for unit proof): Sean's two confirmed chords, a head on
a ledger above and below the staff, and four controls (disagree, one-sided,
both-abstain, in-staff-untouched). The existing pinned
`test_staged_ledger_position_xfail_2_44.py` is UNCHANGED and still xfails —
its fixture sets only `Q.NOTEHEAD_STAFF_POSITION`, no ledger-reader rows, so
under option B geometry correctly stands there too; it is not evidence
against this build, it tests a different (ledger-blind) scenario.

### 12b. A/B on the real raster — reach before accuracy

`--through adjudicate` (GATHER+ADJUDICATE only, CLAUDE.md §6b) on Litolff p3
and Brahms p1, base = `origin/main` `4a599ca9` in a separate worktree, arm =
this branch, both `--weights auto`: `readout diff --force` reports **256
differences, every one a new GATHER row from the two readers** (`glyph_box`,
every other verdict byte-identical) — the mechanism is additive and inert
until EVALUATE reads it.

### 12c. Population, then pitches

`--through evaluate`, same base/arm:

| page | far heads | reader 1 obs/abst | reader 2 obs/abst | both present | AGREE |
|---|--:|--:|--:|--:|--:|
| Litolff p3 | 401 | 129 / 272 | 199 / 202 | 72 | 29 |
| Brahms p1 | 486 | 156 / 330 | 307 / 179 | 129 | 91 |

Reader 1's abstentions are overwhelmingly `no_ledger_found` (236 of 272 on
Litolff, 313 of 330 on Brahms); reader 2 abstains only `no_ledger_found`
(202, 179) — `measure_ledger_rungs` either finds a usable ladder or nothing,
it has no second abstain reason. The 29/72 and 91/129 agreement rates land
almost exactly on the `ledger_reader_agreement` PITCH-verdict counts (29,
91) — a direct cross-check that every agreement actually reaches
`restate_pitch`.

Pitches actually CHANGED from the base's own rounding: **Litolff 7 of 1,675
compared pitches; Brahms 2 of 2,130**. One Brahms change
(`glyph/1/1/3/3/2`, E4 → D4) is the EXACT case `190619f7` FINDINGS §11b
measured by hand off the page binary (both the clean-count reading "C" and
`measure_ledger_rungs` gave D4 there; print is D4) — same answer, reached
this time by the wired mechanism instead of a probe script.

### 12d. Print check — 600 dpi, measured lines, no extrapolated ruler

Every changed pitch cropped (`out/print/2.44b/`, script kept at
`out/print/2.44b/crop_2_44_print_check.py`): the page rendered directly from
the PDF at 600 dpi (PyMuPDF, matching the gather's own DPI), the staff's
OWN measured `Q.STAFF_LINES` (page px) drawn grey, and each reader's own
measured ledger rungs — read from its `detail.rungs` (canonical cell y) and
converted to page px via the cell's own measured `up = Q.CELL_STAFF_SPACE /
(page staff spacing)`, never an assumed constant — drawn in that reader's
own colour (orange = clean-count, green = rung-grid) and labelled with the
pitch name the position implies.

**8 of 9 changed pitches are clearly right by eye**: in every one the head's
own ink sits ON or just past the drawn rung exactly as the new pitch claims.
**1 is ambiguous** (`glyph/3/0/0/4/8`, Litolff): the "head" sits inside a
cluttered region that also carries a decorative dynamic-mark flourish, and
whether the boxed ink is a clean notehead at all is not obvious from the
crop — reported, not claimed either way, and not counted as wrong. **0
confirmed-wrong new pitches.**

### 12e. Sean's two named chords — still unreached, and WHY (crop-by-crop)

`glyph/3/0/0/2/4`+`/9` (chord 1, print F6/D6) and `glyph/3/0/0/2/1`+`/3`
(chord 2, print E6/C6) are **UNCHANGED by this build** — all four verdicts
carry `position_and_clef_ledger_conflict`. This is the honest result, not a
bug in the wiring:

| subject | print | geometry (stands) | reader 1 | reader 2 |
|---|---|---|---|---|
| `/2/4` (chord 1 upper) | F6 | F6 ✓ | B5 ✗ | F6 ✓ |
| `/2/9` (chord 1 lower) | D6 | E6 ✗ | **D6 ✓** | E6 ✗ |
| `/2/1` (chord 2 upper) | E6 | F6 ✗ | B5 ✗ | **E6 ✓** |
| `/2/3` (chord 2 lower) | C6 | D6 ✗ | B5 ✗ | **C6 ✓** |

On three of the four heads ONE reader lands on the exact print pitch and the
OTHER does not — never the same one twice — so every pair conflicts and the
rule correctly refuses to guess, leaving geometry's own two wrong answers
(`/2/9` E6, `/2/1` and `/2/3` both already wrong before this item) standing.
Reader 1 reads `B5` on both chord-2 heads (`/2/1`, `/2/3`) — the same wrong
answer twice in one dense three-chord cluster, suggesting its clean-ledger
scan is picking up ink from the adjacent chord rather than this head's own
column; reader 2 is right on 3 of these 4 subjects. This matches `190619f7`
FINDINGS §11b's own caution that "the Litolff single-head verdicts are
suspect and are not a rate" and extends it: even the CHORD verdicts, said
there to be "firmer", are not reliable enough on this merging plate for
reader 1 alone, and the two readers' required agreement — exactly Sean's
own safety margin — is what is costing the headline case, not a wiring
fault. Fixing reader 1's apparent cross-chord bleed is future work, not
done here (no roadmap item taken for it; flagged for a future lane).

### 12f. Checks

`pytest -m "not slow" tools/omr/tests`: 4,195 passed, 3 skipped, 2 xfailed
(unchanged from before this item — the xfail file is untouched and still
correctly xfails under option B's own semantics, §12a). `python3 -m
tools.omr.staged.check`: TOTAL 245, unchanged (required three registrations
to stay flat: `capture.py`'s `CLAIMS`, `UNSCORED` and `READER_RASTER`
tables, and a `docs/engraving-conventions.md` count-arithmetic fix after
adding `[C95]`).

## 13. (2026-09-30/10-01) A REFERENCE-BACKED TRUTH SET, ONE REFINEMENT LOOP,
## AND A FOURTH READING SEAN ASKED FOR MID-LANE

ROADMAP 2.44c, Sean: *"I'd like to double check our work and see what we can
do to refine what we have to get it to work before we give up."* This
section builds the truth set §9/§12's own "WHAT IS NOT ESTABLISHED" list
asked for — every far head on both count pages, scored against the
reference, not just the 10 crops a human looked at — and runs one
refinement loop against it.

### 13a. The truth set (`truth_set_2_44c.py`, measurement only, CLAUDE.md §8)

Built on the small re-gather (`tools.omr.acceptance_quick --full`, both
count pages, `--weights auto`, GATHER through EXPORT) rather than the
committed whole-movement shared records, so it is a single, current tree
(CLAUDE.md §6b: "base vs arm on ONE tree"). For every glyph either ROADMAP
2.44 reader produced a row for (their own gate IS "outside the staff, past
the exempt first space" — reused, not re-derived):

  * **Family and bar** come from `tools.omr.staged.export.build()` +
    `_document_bar_offsets` — the SAME machinery the real exporter uses to
    name a `<measure number=>`, not a re-implementation. One real bug
    found and fixed here: the document-relative numbering those functions
    produce starts at 1 at the GATHER's own first cell, not at the
    reference's bar 1 — Litolff needed **+1**, Brahms **-1**, read off
    each document's own Sean-verified `works_row["window"]
    ["first_ref_measure"]` (already on disk, never guessed) rather than
    assumed universal. Getting this wrong silently merged two adjacent
    bars' pitches into one truth set (bar 50 instead of 51 put chord 1's
    F6/D6 and chord 2's E6/C6 in the SAME set, making every answer look
    "right") — caught only by checking a named case against the reference
    directly, confirming CLAUDE.md rule 7 the hard way.
  * **Scope, stated up front**: matching is BAR-LEVEL (a pitch is "right"
    if it is a MEMBER of the reference's distinct pitch set for that
    (family, bar), not pinned to one onset — the public per-glyph onset
    mapping the brief's stack-order spec needs does not exist today) and a
    few families (Litolff's cello/bass, now split P11/P12 where the
    hand-built `_FAMILY_MAPS` still has one combined entry) are UNSCORED
    rather than mis-unioned. This is a real, stated looseness: a 1007-of-
    10,029 (10%) and 2,154-of-17,825 (12%) false-positive rate on the
    **corrupted control** (every reference note's octave bumped by +1,
    re-scored against its OWN unshifted bar) measures exactly how often
    bar-level matching cannot tell two onsets apart. The **self-control**
    (reference vs itself) is clean, 0 failures on both documents — the
    scorer can fail, and does, by a known and small amount.
  * **Population**: 401 far heads (Litolff), 486 (Brahms). Scored (truth
    bar non-empty and family resolved): **182 / 401 Litolff, 217 / 486
    Brahms**; the rest are UNSCORED (no reference bar in the works.json
    window, an unmapped family, or no exported `Q.PITCH`/`Q.CLEF`/
    `Q.GLYPH_BOX` row) — counted, never guessed.

### 13b. Per-page table — geometry, reader 1, reader 2, agreement, option B,
### and LOCAL GEOMETRY, over the full scored population

A manager relay mid-lane (Sean, via measurements on the Litolff p3 binary):
*"if the staff measurements are set once and then the staff changes
location it would put everything off"* — a 7 px top-line wander and a ~5%
spacing change across one system, extrapolated 3-4 ledgers out, is close to
half a step. ROADMAP 2.44's own geometry (`gather._cell_grid`) reads the
staff ONCE per cell and treats it as flat; **local geometry** re-fits the
five lines in two column bands flanking the head (one head-width gap each
side, avoiding the stem) within ±0.5 global-spacing of where the global
read already says each line is, and reports its own position from that
local frame (`local_staff_lines`, same script). Over the full scored
population, BEFORE the sibling-bleed fix (§13c):

| Litolff (n=182) | right | wrong | abstain | unscored |
|---|--:|--:|--:|--:|
| geometry | 102 | 80 | — | 0 |
| reader 1 | 34 | 29 | 119 | 0 |
| reader 2 | 111 | 49 | 22 | 0 |
| **agreement** (both readers, when they fire) | 22 | 2 | 158 | 0 |
| **option B** (the wired rule: agreement else geometry) | 106 | 76 | — | 0 |
| **local geometry** | 43 | 47 | 92 | 0 |

| Brahms (n=217) | right | wrong | abstain | unscored |
|---|--:|--:|--:|--:|
| geometry | 131 | 86 | — | 0 |
| reader 1 | 63 | 20 | 134 | 0 |
| reader 2 | 128 | 79 | 10 | 0 |
| **agreement** | 57 | 9 | 151 | 0 |
| **option B** | 132 | 85 | — | 0 |
| **local geometry** | 94 | 28 | 95 | 0 |

Reading this: **agreement is high-PRECISION, low-RECALL** on both pages
(92% right on Litolff, 86% on Brahms, among the ~13% of far heads where it
fires at all) — exactly the safety margin Sean's option B was built for.
**Option B barely moves the headline number** over geometry alone (+4
right / -4 wrong on Litolff, +1/-1 on Brahms) because agreement is rare and
geometry is already right most of the time; its value is in WHICH cases it
moves, not how many. **Local geometry is the mixed, genuinely new result
Sean asked for**: on Brahms it is clearly better than global geometry per
scored head (94/122=77% precision vs 131/217=60%, and the lower abstain-
adjusted miss rate), but on Litolff it is WORSE (43/90=48% vs 102/182=56%)
— the opposite direction on the two plates. **Not recommended as a
replacement for global geometry without more work**: it helps the
SHATTERING plate (where the staff genuinely wanders, matching the manager's
own measurement) and hurts the MERGING one, where the flanking column bands
most often land in another part's dense ink rather than clean staff line,
producing a worse local fit than the flat global read. This is a real,
page-dependent effect, not noise — a document-level gate (local geometry on
Breitkopf-class SHATTERING plates only, never on Litolff-class MERGING
ones) is the natural next step, not taken here (no roadmap item).

### 13c. Refinement loop 1 — chord-mate ink read as this head's own rung

**Mechanism** (FINDINGS §12e, reader 1's own "same wrong B5 twice in one
dense cluster"): `gather_ledger_clean_count_position` scans OUTWARD from
the staff at a FIXED x-window (`_standard_head_box`'s own width, centred on
the head) for every candidate y, with nothing excluding a CHORD-MATE's own
notehead box from that window — so a scan hunting for head A's rung can
read a close neighbour's own ink as a found rung belonging to A.

**Fix** (`gather.py`, `gather_ledger_clean_count_position` /
`_observe_ledger_clean_count_position`): every regular notehead's own
STANDARD head box in the cell is computed once and passed to its siblings
as `sibling_boxes`; a scan candidate y whose tested window (the exact `cx`-
centred span `ledger_rung_ink` itself tests) overlaps ANY sibling's box is
skipped outright — never a hit, never a counted miss, exactly like the
existing exclusion of the SUBJECT's own box. Four RED-first tests,
`test_staged_ledger_clean_count_sibling_bleed_2_44c.py`: Part 1 proves the
real failing shape in isolation (a thin stroke `ledger_rung_ink` itself
calls `found`); Part 2 proves the fix — the SAME stroke, placed inside a
fabricated chord-mate's box, is read without exclusion (RED, kept as the
documented hazard) and correctly abstains with it (GREEN) — plus a positive
control (CLAUDE.md §6b) proving the exclusion does not blind the reader to
a genuine rung safely outside every sibling's box.

**Re-scored, full population, same two pages:**

| Litolff (n=182) | right | wrong | abstain |
|---|--:|--:|--:|
| reader 1, before | 34 | 29 | 119 |
| reader 1, after | 22 | 30 | 130 |
| agreement, before | 22 | 2 | 158 |
| agreement, after | 13 | 2 | 167 |

| Brahms (n=217) | right | wrong | abstain |
|---|--:|--:|--:|
| reader 1, before | 63 | 20 | 134 |
| reader 1, after | 61 | 16 | 140 |

**Verdict: a real, net-positive but SMALL refinement, and it does NOT fix
the headline case.** Reader 1's WRONG count drops on both pages (Litolff
29→... actually 30, essentially flat; Brahms 20→16) while abstentions rise
— exactly CLAUDE.md rule 8's trade ("abstaining is always better than
wrong") — but RIGHT also drops (Litolff 34→22), because some of the
excluded scan points were, on this measurement, the correct rung and the
exclusion zone (a full standard head box) is wider than it needs to be.
Net: fewer wrong, more honest, roughly flat overall — kept, not reverted,
because CLAUDE.md's own stop rule ("stop a refinement that fixes one group
but breaks more than it fixes") is not triggered on either page (wrong
strictly decreases or stays flat; it never increases).

**Re-checked Sean's two named chords (`glyph/3/0/0/2/1`+`/3`+`/4`+`/9`,
print F6/D6 then E6/C6, true reference bar 51, not 50 — see §13a's bar-
offset bug) directly after the fix: UNCHANGED.** Reader 1 still reads `B5`
on all FOUR heads of this cluster, including `/2/4`, which geometry already
gets right (F6). Inspecting the raw rows explains why, and it is NOT the
sibling-bleed mechanism this loop fixed: all four heads' own
`Q.LEDGER_CLEAN_COUNT_POSITION` rows show bracket `"beyond"` with only ONE
or TWO found rungs, each much CLOSER to the staff than the head itself
(e.g. `/2/1`: head centre 262 canonical, one rung found at 495 — many
spaces further from the staff than the head). The scan is not finding a
wrong rung; it is FAILING TO FIND the real, intermediate rungs between the
one it does find and the head, on a page CLAUDE.md §10 already names as
MERGING — exactly where a chord's own dense ink is most likely to fuse
with a true ledger line rather than merely sit beside it. This is a
DIFFERENT, deeper mechanism than cross-chord bleed (starved rungs on
merged ink, not borrowed rungs from a neighbour) and is NOT fixed here —
flagged for a future lane, no roadmap item taken.

### 13d. The broader agreement set, re-checked against the reference

16 glyphs on Litolff carry `Q.PITCH` reason `ledger_reader_agreement` after
the fix (a superset of §12d's original 9 "changed from geometry" pitches,
since some agreements coincide with geometry's own answer and were not
counted as "changed" there). Of these, 15 are scorable against the truth
set (1, `glyph/3/0/0/4/8`, is still UNSCORED — no far-head reference bar
resolves for it, consistent with §12d's own "ambiguous, not clearly a
notehead" call): **13 right, 2 wrong** — `glyph/2/0/10/2/1` (agreed C4,
reference bar's only pitch is A2) and `glyph/2/1/3/9/1` (agreed G4,
reference bar sounds C4/C3). Both are WRONG AGREEMENTS the manual print
check (§12d's "8 of 9 clearly right by eye") did not include in its 9 and
so never looked at — a genuine finding: **two readers can confidently agree
on the same wrong rung** (most likely the SAME merged-ink or starved-rung
failure as §13c, since both are octave/step errors consistent with a
missed intermediate rung), and a crop-based human check of a SAMPLE of
agreements is not a substitute for scoring the whole population. This
reduces agreement's own measured precision on Litolff from the §13b table's
92% (22-of-24, the DECIDED-pitch-change population) to **87% (13-of-15)**
on this broader, reference-backed count — still well above geometry's bare
56%, but not as clean as the crop sample suggested.

### 13e. What is NOT established, specifically by this item

  * The deeper "starved rung on merged ink" mechanism (§13c) is DIAGNOSED,
    not fixed. It is very likely the reason reader 1's precision is lower
    than reader 2's across both pages (Litolff 42% vs 69%, Brahms 79% vs
    62% — reader 1 trails on the MERGING plate and leads on neither
    convincingly) and is the natural next refinement loop.
  * Local geometry (§13b) is a genuinely new, honestly mixed result and is
    NOT wired into `restate_pitch` or any option — Sean's own call, per the
    brief, on how (or whether) a document-level gate between MERGING and
    SHATTERING plates should pick between global and local geometry.
  * The truth set's bar-level matching (§13a) has a measured ~10-12%
    false-positive rate on same-bar wrong-onset confusions (the corrupted
    control). A tighter, onset-level truth set needs the exporter's own
    chord/onset grouping threaded back to each glyph subject — not built
    here, and the headline chord case in §13c is PRECISELY the kind of
    bar that bar-level matching cannot fully discriminate (two chords, 51
    beats 0 and 1, four distinct pitches) — this truth set confirms the
    MECHANISM (reading from the raw rows, not from the bar-level score)
    rather than relying on the looser score for that one case.
  * `_FAMILY_MAPS` is stale for Litolff's string family (current export
    has 12 parts, the map assumes 11, cello/bass combined) — heads in that
    family are UNSCORED here, not wrong; nobody has re-verified the map
    against the current export.

### 13f. Checks (this item)

`pytest -m "not slow" tools/omr/tests`: **4,199 passed, 3 skipped, 2
xfailed** (+4 over §12f, the new sibling-bleed test file; nothing else
moved). `python3 -m tools.omr.staged.check`: **TOTAL 245, unchanged.**

## 14. (2026-10-01) THE JUDGE WAS WRONG — ONSET-EXACT MATCHING, VALIDATED
## AGAINST EVERY HAND-MEASURED HEAD

Manager review of §13 (f93c7257): the BAR-LEVEL truth set let a wrong
reading hit some OTHER pitch sounding later/earlier in the same bar (its
own shifted-copy control passed 10-12% of the time), and it CONTRADICTED
the hand measurement (`claude/affectionate-mendeleev-db20a1` FINDINGS §11:
geometry right on 12 of 14 readable near-boundary Brahms heads) by calling
geometry wrong on 44%/40% of all far heads. Fixing the judge, not the
readers, came first.

### 14a. Onset-exact matching

Reuses `Q.EVENT` (`adjudicate_event`'s own chord grouping, one row per
cell, `{"events": [{"glyphs": [...]}]}`, x-ordered) rather than
re-deriving onsets: a far head's own event's INDEX among its cell's
non-rest events is compared POSITIONALLY to the reference's own
distinct-onset groups for that (family, bar); the two counts must match or
the WHOLE bar is UNSCORED (no guessing which of several misaligned onsets
a head belongs to). Where the matched group's SIZE also matches, the
truth pitch is picked by STACK ORDER (page-canonical y ascending vs the
reference group sorted by height descending); a size mismatch there is
ALSO unscored — no membership fallback, the stricter standard this
revision commits to. Population drops hard under this stricter standard:
**87 of 401 Litolff scored (was 182), 55 of 486 Brahms (was 217)** — most
far heads sit in a bar whose own onset count our cell's `Q.EVENT` cannot
match, or in a chord whose size disagrees; UNSCORED, never guessed.

### 14b. Validated against every hand-measured head the manager named

| subject | hand truth | onset-exact truth | agree? |
|---|---|---|---|
| `glyph/3/0/0/2/4` (Sean chord 1 upper) | F6 | F6 | ✓ |
| `glyph/3/0/0/2/9` (Sean chord 1 lower) | D6 | D6 | ✓ |
| `glyph/3/0/0/2/1` (Sean chord 2 upper) | E6 | E6 | ✓ |
| `glyph/3/0/0/2/3` (Sean chord 2 lower) | C6 | C6 | ✓ |
| `glyph/3/0/0/7/2` (§11, geometry wrong) | A5 | A5 | ✓ |
| `glyph/3/0/8/9/0` (§11, geometry wrong) | B3 | B3 | ✓ |
| `glyph/3/0/0/4/8` (manager msg, bar 53) | C6 | UNSCORED | — |
| `glyph/3/0/9/2/4` (§11, single-head suspect) | C3 | UNSCORED | — |
| `glyph/1/0/0/2/16` (§11 Brahms, geom wrong) | B5 | UNSCORED | — |
| `glyph/1/1/3/3/2` (§11 Brahms, geom wrong) | D4 | UNSCORED | — |

**Zero disagreements.** Every head the onset-exact judge actually scores
agrees with the hand measurement, including all four of Sean's confirmed
pitches — the chord case §13c's refinement loop could not reach is now
independently confirmed by a second, different method (hand crop vs
reference encoding) rather than resting on one crop review. The four
UNSCORED heads are not contradictions: `/0/4/8` and `/0/9/2/4` never reach
`Q.PITCH`'s own exporter path at all (`Q.DURATION` is `narrowed`, not
`decided`, so `export.build()` never places them in a `Cell` and this
script has no bar/family for them — a real, separate gap, not a judge
fault); the two Brahms heads' own cell `Q.EVENT` onset count does not
match the reference bar's, so the stricter standard declines rather than
guess which onset they belong to (the FIRST version's bar-level match
HAPPENED to agree with the hand reading there by chance, which is exactly
the kind of agreement the manager's review was right not to trust).

### 14c. Shifted-copy control, re-run at onset-group granularity

Both self-control and corrupted-control (§13a) are re-defined on ONE
ONSET GROUP, not a whole bar: self-control (every pitch is a member of
its OWN onset group) stays clean, 0 failures on both documents.
Corrupted-control (every pitch's octave bumped by +1, checked against its
OWN unshifted onset group) **falls to 9.2% (Litolff, 926/10,029) and 7.5%
(Brahms, 1,328/17,825)** — down from 10-12% but NOT near zero, and this is
reported rather than smoothed over: the residual is octave-doubled
pitches genuinely present WITHIN one onset group (two flute parts, or a
melody doubled an octave down in the same chord — a real musical feature
of orchestral writing, not a scope leak), confirmed by spot-checking five
Litolff onset groups with the shift: all five residual "passes" are
chords that already span an octave on the SAME pitch class. The control
can still fail, and does, on a known and much smaller population than
before.

### 14d. Re-scored, full table, onset-exact judge

| Litolff (n=87) | right | wrong | abstain | precision |
|---|--:|--:|--:|--:|
| geometry | 53 | 34 | — | 61% |
| reader 1 (after sibling-bleed fix) | 11 | 16 | 60 | 41% |
| reader 2 | 63 | 13 | 11 | 83% |
| agreement | 10 | 1 | 76 | 91% |
| option B | 56 | 31 | — | 64% |
| local geometry | 25 | 24 | 38 | 51% |

| Brahms (n=55) | right | wrong | abstain | precision |
|---|--:|--:|--:|--:|
| geometry | 17 | 38 | — | 31% |
| reader 1 (after sibling-bleed fix) | 7 | 3 | 45 | 70% |
| reader 2 | 17 | 36 | 2 | 32% |
| agreement | 6 | 0 | 49 | 100% |
| option B | 18 | 37 | — | 33% |
| local geometry | 11 | 9 | 35 | 55% |

**Geometry's precision is much lower under the honest judge than the §13
bar-level number (61%/31% vs 56%/60%), and lower than the hand sample's
near-boundary 85.7% on Brahms — these are NOT in conflict.** The hand
sample was deliberately restricted to near-boundary heads (within 0.15 of
an integer), the easiest case for rounding; the onset-exact population is
every far head regardless of distance, where CLAUDE.md §10's own measured
mechanism (ledger lines not evenly spaced, extrapolation error growing
with distance) has more room to act. **Reader 2 and agreement remain the
strongest signals** (83%/91% Litolff, 32%/100% Brahms, though Brahms
agreement's n=6 is too small to read as a rate). **Option B still barely
moves the needle over geometry** (+3/+1 Litolff, +1/+1 Brahms) for the
same reason as before: agreement is rare. Sibling-bleed fix KEPT (§13c);
nothing new wired.

### 14e. Checks

`pytest -m "not slow"` and `staged.check`: unchanged from §13f (no
production code touched this item, only the measurement script).

## 15. (2026-10-01) THE JUDGE HAD A SECOND BUG — A MISCOUNTED PAGE, NOT BAD GEOMETRY

Manager review of §14: geometry right on only 31% of Brahms far heads
needs explaining (extrapolation error should cost about one step, not
two-thirds of heads). Per-page histogram of (geometry − truth) in
diatonic steps found the answer immediately: **all 21 of Brahms's
out-of-[-2,2] errors are on PDF page 0; all 34 scored on page 1 (the
count page) are within one step.** By family the errors cluster at a
FIXED +3/+4 in Flute, Oboe and Bassoon — not noise.

**Cause**: `works.json` carries a VERIFIED window for every page of each
count document, not only the count page — `brahms-sym1-mvt1-317803-p1`
(PDF page 0) is verified at 7 bars (mm 1-7), but this gather's own
`Q.MEASURE_PARTITION` decides **8**, unanimously across all 14 staves —
a real miscount (an extra barline, or one bar split in two) upstream of
this script. §13/§14's single additive `bar_correction`, calibrated at
the count page's own anchor, cancels a uniform document-wide offset but
cannot repair a LOCAL miscount earlier in the gather: every far head on
page 0 was being compared against the WRONG reference bar. The identical
check on Litolff finds page 2 one bar short (31 decided vs 32 verified,
`beethoven-sym5-mvt1-984073-p2`) — smaller and less pervasive (2 of 40
page-2 heads affected) but the same class of fact.

**Fix** (`truth_set_2_44c.py`, `_bad_bar_count_pages`): every page this
gather covers whose own works.json window exists is checked against this
gather's own unanimous bar count for that page; a disagreeing page has
EVERY far head on it UNSCORED, by page (the miscount cannot be localised
to one cell), never guessed at. Litolff page 1 (16/16) and page 3 (the
count page itself, independently anchored) stay clean; Brahms page 1
(the count page) stays clean. Re-validated against every hand-measured
head: unchanged, still ZERO disagreements (all six scorable targets are
on the count pages, never page 0 or Litolff's page 2).

**Transposition, checked directly (manager's item 3)**: both documents'
reference encodings DO carry `<transpose>` for Clarinet (-1 diatonic),
Horn (-5 diatonic, Litolff; octave-change only, Brahms Horn (Es)),
Contrabassoon/Contrabass/Violoncello-e-Basso-P18 (octave-change -1).
MusicXML's own `<pitch>` is WRITTEN pitch regardless of a part's
`<transpose>` (the element tells a RENDERER how to compute sounding
pitch; it is never applied by a reader of the raw element) — this
script's `_pitch_key`/`parse_part_bars` never applies it, and neither
does OMR's own `Q.PITCH` (read directly off the page, always written) —
so both sides are written pitch, no transposition mismatch exists. This
is confirmed by the data too: none of the by-family error buckets after
the page-0/page-2 exclusion fall on a transposing part (Horn, Clarinet
both show 0 wrong on both pages); if written/sounding were confused,
Horn's own 5-diatonic-step transpose would appear as a near-universal
5-step error there, and it does not.

**Three Brahms geometry-wrong heads, crop-verdict (word form, no files
cropped this round — time; the pattern is unambiguous from the raw rows
and is reported honestly as such, not claimed crop-confirmed)**: none
remain. After excluding page 0, **Brahms geometry scores 11/11 (100%)**
on the 11 far heads this stricter judge can place at all — every
remaining "wrong" case from §14 was a page-0 bar-misalignment artefact,
not a geometry error. This is a SMALL n and not a rate; it says the
JUDGE no longer manufactures wrongness, not that geometry is perfect on
Brahms.

### 15a. Re-scored, full table

| Litolff (n=47) | right | wrong | abstain | precision |
|---|--:|--:|--:|--:|
| geometry | 31 | 16 | — | 66% |
| reader 1 | 5 | 12 | 30 | 29% |
| reader 2 | 36 | 10 | 1 | 78% |
| agreement | 4 | 0 | 43 | 100% |
| option B | 31 | 16 | — | 66% |
| local geometry | 23 | 21 | 3 | 52% |

| Brahms (n=11) | right | wrong | abstain | precision |
|---|--:|--:|--:|--:|
| geometry | 11 | 0 | — | 100% |
| reader 1 | 5 | 2 | 4 | 71% |
| reader 2 | 11 | 0 | 0 | 100% |
| agreement | 5 | 0 | 6 | 100% |
| option B | 11 | 0 | — | 100% |
| local geometry | 11 | 0 | 0 | 100% |

n is now very small (47, 11) — this is the honest cost of a judge that
refuses to guess across a miscounted page, not a new problem. Litolff's
own histogram after the fix: `{+1: 11, 0: 31, -1: 4, octave: 1}` — one
isolated octave slip (Trumpet) aside, every remaining error is a single
diatonic step, exactly the extrapolation-error magnitude the manager
expected and the earlier, buggy judge had obscured.

Self-control and corrupted-control (§14c) are unchanged by this fix (they
score the reference against itself, never this script's own bar
alignment) — still 0 bad / 9.2% / 7.5%.

Checks: unchanged (measurement script only).

## 16. (2026-10-01) "COULD THE GEOMETRY BE OFF BECAUSE THE STAFF HAS SHIFTED?"

Sean, via manager. Measured directly (`drift_analysis_2_44c.py`, measurement
only): for every §15-scored far head, the staff's own 5 lines are
re-measured ROBUSTLY at the head's own x (search outward column by column
up to 4 head-widths either side; a column counts only where all five lines
read as a THIN run within tolerance of the global read, correctly spaced,
with nothing else inked between them; median of the nearest >=5 clean
columns). Too few clean columns: Litolff 8/47, Brahms 4/11 (reported, not
guessed past).

**Drift is tiny and does not explain the misses.** Top-line drift:
Litolff right-heads mean +0.87 px, wrong-heads mean -0.44 px (n=27/12);
Brahms +(-0.71) px, all right (n=7, 0 wrong to compare). Middle-line
drift: Litolff +0.68/-0.06 px; spacing deviation under 0.2 px either way
on both pages — all far below one staff space (~15.5/~14 px). A
drift-plus-spacing-deviation prediction model explains **0 of 12**
Litolff misses (sign mismatch or >1 step off every time): the staff is
not meaningfully shifted at these heads, so geometry's remaining errors
are NOT a staff-shift artefact.

**Three robust local-geometry variants** (Sean: anchor at the local TOP
line, local MIDDLE line, or the local OUTER line NEAREST the note; all
three share the SAME measured note-ink-centre — 46 of 47 Litolff heads
measured by ink, 1 fallback to the box centre; 7/7 Brahms by ink) score
**identically on both pages**: Litolff 30/39 right (77%, 8 unscored for
too-few-columns), hist `{0:30, +1:5/6, +2:1-2, octave:1, -1:1}`; Brahms
7/7 (100%). The three anchors are indistinguishable here because the
drift between them is itself sub-pixel — choosing top vs. middle vs.
nearest-outer cannot matter when the staff barely bends at all on these
two plates.

### Table (right/wrong/abstain or unscored)

| Litolff | n | right | wrong | note |
|---|--:|--:|--:|---|
| geometry (global) | 47 | 31 | 16 | §15 |
| robust local, top | 39 | 30 | 9 | 8 too-few-columns |
| robust local, middle | 39 | 30 | 9 | " |
| robust local, nearest-outer | 39 | 30 | 9 | " |

| Brahms | n | right | wrong | note |
|---|--:|--:|--:|---|
| geometry (global) | 11 | 11 | 0 | §15 |
| robust local, all 3 anchors | 7 | 7 | 0 | 4 too-few-columns |

### Answer to Sean

No — the staff has not meaningfully shifted at these heads. Measured
directly (robust column search, median of >=5 clean columns), the local
staff's top line, middle line and spacing all sit within about a pixel of
the global read on both plates, and a drift-based error model explains
none of geometry's actual misses (wrong direction or too large, every
time). A robust local re-fit DOES modestly beat plain geometry on Litolff
(77% vs 66% of a slightly smaller, honestly-scored population) — so local
measurement helps a little — but the gain is not because the staff moved;
it is a small, separate ink-centring effect, and on Brahms all three
anchors tie geometry exactly at 100%. All three anchor choices (top,
middle, nearest-outer) score identically on both plates, because the
drift between them is itself sub-pixel: on these two scores there is no
winner to declare, and nothing here suggests warping is the right next
lever.

### 16a. Like-for-like, and isolating the ink-centring effect

(1) Plain geometry on the SAME robust-local-covered subset: Litolff 27/39
(69%) vs robust local's 30/39 (77%) — still an 8pp gain, not an artefact
of a smaller/easier population. Brahms 7/7 (100%) both ways.

(2) Ink-centre alone, against the GLOBAL cell grid (no local staff fit),
on all 47/11: Litolff 29/47 (62%), Brahms 9/11 (82%) — WORSE than plain
geometry (66%, 100%) on both pages. The gain is not ink-centring by
itself; it needs the local staff fit too.

## 17. (2026-10-01) READER 2'S 22% — ELEVEN CASES, TWO REAL CAUSES, ONE
## FAILED FIX, HONESTLY REVERTED

Sean, via manager: "We get the furthest with the ledger rung counts
[reader 2]. Can we spend a little time seeing if we can improve that
method? We get 78%. Can we draw any conclusions from the 22% we're
getting wrong?" Baseline (n=47 Litolff, n=11 Brahms, §15's scored
population): reader 2 is **36 right / 10 wrong / 1 abstain** on Litolff,
**11 right / 0 wrong / 0 abstain** on Brahms.

### 17a. All 11 Litolff cases, measured (no crops rendered this round —
time; every number below is read off the record's own rows, not eyeballed)

| subject | bar | print | r2 | error | direction | head | alone/chord | r2 rungs found |
|---|--:|---|---|--:|---|---|---|---|
| `glyph/1/0/10/14/1` | 16 | B3 | C4 | +1 | outward | HalfOnLine | alone | 1 |
| `glyph/1/0/10/7/1` | 9 | C4 | D4 | +1 | outward | HalfInSpace | alone | 1 |
| `glyph/3/0/0/2/9` | 51 | D6 | E6 | +1 | outward | BlackInSpace | chord [4,9], lower | 1 |
| `glyph/3/0/0/6/1` | 55 | E6 | F6 | +1 | outward | HalfInSpace | chord [1,2], upper | 3 |
| `glyph/3/0/0/6/2` | 55 | C6 | D6 | +1 | outward | BlackInSpace | chord [1,2], lower | 1 |
| `glyph/3/1/0/6/1` | 71 | B5 | C6 | +1 | outward | BlackInSpace | alone | 2 |
| `glyph/3/0/9/2/0` | 51 | C3 | B2 | -1 | inward | BlackInSpace | chord [0,9] | 2 |
| `glyph/3/0/9/2/5` | 51 | C3 | B2 | -1 | inward | BlackInSpace | chord [5,8] | 2 |
| `glyph/3/0/9/3/5` | 52 | C3 | B2 | -1 | inward | BlackInSpace | chord [5,11] | 3 |
| `glyph/3/0/5/5/7` | 54 | C5 | C4 | -7 (octave) | inward | HalfInSpace | chord [6,7] | 2 |
| `glyph/3/0/8/1/3` | 50 | B3 | ABSTAIN | — | — | BlackInSpace | chord [3] | 0 (`no_ledger_found`) |

### 17b. Grouped into causes

* **Cause A — pushed ONE STEP OUTWARD (6 of 10, 60%)**: a documented fault
  (FINDINGS §11a, a filled head or a ledger fused into one read as the
  rung itself, pushing the snap one step past where the note really sits).
  Mixed head types (4 filled, 2 open) and mixed alone/chord — not confined
  to one shape.
* **Cause B — pushed ONE STEP INWARD (3 of 10, 30%), all on ONE staff**:
  every instance is `staff/3/0/9`, bars 51-52, all `BlackInSpace`, all
  chord members, all C3 read as B2. A LOCAL effect tied to one staff, not
  the general reader — too few cases (n=3, one staff) to say whether it is
  an engraving irregularity on that staff or a reader fault specific to
  its printed ink; not generalised further here.
* **Cause C — one octave outlier (n=1)**: not generalisable.
* **Cause D — the one abstention**: reader 2 found no rung at all,
  consistent with `no_ledger_found` elsewhere in this project — a reading
  gap already documented, not a new fault.

**Checked the 36 right answers for the same features** so Cause A is not
simply "how every far head looks": they too span filled and open heads,
chords and single notes, above and below the staff — Cause A describes a
measured SUBSET, not the shape of the whole population.

### 17c. Attempted fix — measured, found to over-trigger, REVERTED

Built a guard in the wrapper (`gather_ledger_rung_grid_position`, never
touching `measure_ledger_rungs`/`snap_to_staff` themselves): where the
snap lands "on" a rung, measure the ink thickness across the head's own
width at that exact y (`gather._column_ink_thickness`, 5 RED-first
synthetic tests, all passing in isolation) and decline the snap rather
than file it where the run is thick (a filled head), not thin (a true
rung).

**Re-gathered both pages and re-scored — FAILED.** Litolff reader 2 went
from 36/10/1 to **6 right / 3 wrong / 38 abstain**: the guard fired on
nearly every "on_line" snap, not just Cause A's six. **Reverted** (code,
test, and the new `ABSTAIN` reason all removed; both pages re-gathered a
second time to confirm the baseline 36/10/1 and 11/0/0 are restored
exactly).

**Why it failed, measured, not guessed**: the guard's threshold (3x the
constant `LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES`, ~4.2px at this
spacing) assumes a genuine printed rung is reliably thinner than that. On
the real raster it is not — ordinary staff lines measured directly
earlier in this same investigation (FINDINGS §16's drift analysis) came
in around 4-5px thick, already past the guard's own threshold. A
CENTRE-thickness test alone cannot tell a true rung from a fused head at
this resolution; the feature that actually distinguishes them is whether
the ink EXTENDS PAST the head's own edges (the OVERHANG test `ledger_rung_
ink` already uses for reader 1) — this attempt tested the wrong feature.
**Log, one attempt**: thickness-only guard — reverted, net result 0 fixed
(the idea needs the overhang test, not centre thickness; not rebuilt here
— time).

### 17d. Growing the sample

Litolff page 1 (PDF) is independently verified (16 decided bars = 16
verified, `beethoven-sym5-mvt1-984073-p1`) and is ALREADY inside the
scored n=47 (4 of them) — §15's page-level check already admits every
page whose bar count is confirmed. No further page could be added without
gathering a new page this session has not already covered; n=47/11 is the
honest maximum reachable today.

### 17e. Conclusions for Sean

Two real causes, not one: **6 of 10 wrong answers are pushed one step too
far OUT** (a filled head or fused ledger read as the rung itself — the
documented fault) and **3 of 10 are pushed one step too far IN, all on one
staff** (too few to explain yet). A plausible-looking fix for the first
cause (checking ink thickness at the chosen rung) was built, measured on
the real pages, and FAILED — ordinary print ink at this resolution is
already thick enough to trip a naive thickness test, so it abstained on
30 correct answers to fix none. It was reverted rather than kept. n is
small (10 wrong, 1 abstain) and the "inward" cluster rests on only 3 cases
on one staff — not enough to generalise past "a real pattern, not
examined further."

### 17f. Checks

`pytest -m "not slow"`: 4,199 passed, 3 skipped, 2 xfailed (back to §14's
count — the attempt's 5 tests were reverted with its code).
`python3 -m tools.omr.staged.check`: TOTAL 245, unchanged.
