# ROADMAP 2.47 -- extra/missing bars in Q.MEASURE_PARTITION: two distinct
# mechanisms, both rare on this sample, neither caught by anything that runs

STAGED path. `measure_extractor._measure_x_boundaries` cuts the per-system
measure cells; `gather.gather_measures` turns the per-staff cell count into
`Q.BARLINE_COLUMN`; `adjudicate_measure_partition` (`structure.py`) reads
that single geometry observation as `Q.MEASURE_PARTITION` with `reason=read`
-- there is exactly one witness, so a mistake here never gets a second
opinion from inside the stage.

## 0. The two known pages, mechanism found and crop-verified

### 0a. Brahms 1/i, Breitkopf 317803, PDF page 0 -- EXTRA bar (8 decided, 7
verified)

`_measure_x_boundaries` (measure_extractor.py:1084) keeps a barline column
only if it is strictly between `x_lo + edge_margin` and `x_hi - edge_margin`
-- the two filtered-out columns are "the rule closing the system, and the
one opening it," which divide no measure. Whatever is left over after the
last kept barline (the "tail") is either absorbed into the previous cell or
kept as its own cell, decided by one rule: `tail_width >= median_measure_width
* 0.20` keeps it as its own cell.

Measured on this page (system 0, 14 staves, all voting 13-14/14 on every
barline): kept barlines `[2112, 2671, 3101, 3554, 4107, 4684, 5388]`,
`x_hi=5501`, median measure width **559px**, tail **113px**, threshold
**111.8px**. The tail clears the threshold by **1.2px -- a 1% margin** --
and is kept as its own 8th cell.

Crop (`out/print/2.47/brahms-p0-sys0-tail-barline-x5388-x5501.png`, 600dpi,
red=the barline at x=5388 the geometry voted 14/14 for, blue=the staff's own
measured `x_end`=5501): the 113px strip between them is not a short last
measure. It is a **cautionary clef + time signature**, printed after the
system's final barline, announcing what opens the next system -- CLAUDE.md
section 10's "a cautionary meter after a system's last barline governs no
bar," except here it is not a meter being misread, it is the measure
PARTITION itself promoting that signature block to a phantom bar 8 because
its width (113px) narrowly failed to read as "blank tail" against this
system's own measure-width scale.

### 0b. [WITHDRAWN 2026-09-30, manager review -- see section 6] Beethoven
5/i, Litolff 984073, PDF page 2, system 1 -- MISSING bar (15 decided where
16 is needed to reach 32 across the page; 31 vs 32 verified)

**This whole subsection's conclusion is WRONG and is kept only so the
correction in section 6 is visible against what it corrects.** I originally
wrote: "System 0 on this page is clean and crop-confirmed: 16 cells ...
That is bars 17-32, 16 bars, exactly matching `works.json`" and concluded
the plate's own numbering skips 33 (no bug on our side). The manager refuted
this by reference content: our exported bars 32/33/34 match the
REFERENCE's bars 33/34/35 (a one-bar lag already present by bar 33), so
**system 0 really holds 17 bars (17-33), not 16, and `works.json`'s "32
verified" is correct.** The printed "34" at system 1's start that I read as
evidence of a plate numbering slip is in fact exactly what a CORRECT
17-bar system 0 should produce (17+17=34) -- I had the arithmetic backwards.
The actual deficit is a barline DROPPED somewhere inside system 0's own 16
decided cells. See section 6 for where I narrowed it and section 4's
question, which is now a different, narrower one.

## 1. How widespread -- 6 more systems, all pages with a `works.json` window

Beyond the 2 known pages, every other Litolff/Brahms page with a verified
`works.json` window was re-gathered fresh (`--weights auto --route-weights
--pages N`, `OMR_DIRECTION_TEXT_SCAN_GATE=1`) and its decided
`measure_partition` total compared against the verified count:

| row | pdf page | systems | decided total | verified | match |
|---|---|---|---|---|---|
| beethoven-sym5-mvt1-984073-p1 | 1 | 1 | 16 | 16 | match |
| beethoven-sym5-mvt1-984073-p2 | 2 | 2 | 31 (16+15) | 32 | MISMATCH missing 1, sys 1 |
| beethoven-sym5-mvt1-984073-p3 | 3 | 2 | 34 (16+18) | 34 | match |
| beethoven-sym5-mvt1-984073-p4 | 4 | 2 | 30 (15+15) | 30 | match |
| brahms-sym1-mvt1-317803-p1 | 0 | 1 | 8 | 7 | MISMATCH extra 1 |
| brahms-sym1-mvt1-317803-p2 | 1 | 2 | 15 (7+8) | 15 | match |
| brahms-sym1-mvt1-317803-p3 | 2 | 2 | 15 (6+9) | 15 | match |
| brahms-sym1-mvt1-317803-p4 | 3 | 2 | 21 (10+11) | 21 | match |

(Brahms p3/p4 totals cross-checked two ways: the full staged gather's
decided `measure_partition`, and an independent direct recomputation of
`_measure_x_boundaries` from `pws.barlines`/`pws.staves` -- both agree.)

**8 pages, 15 systems, 2 miscounted -- both the ones already known, neither
new.** A direct tail/threshold survey (recomputing `_measure_x_boundaries`'
own numbers for every system on all 8 pages) found exactly **one** system
within 20% of the absorb threshold on either side: Brahms p0/sys0 itself
(1% margin). Every other system's tail ratio was nowhere close (margins
252%-551% away from the 20% line in both directions) -- this specific
near-miss brittleness is not quietly present elsewhere in this sample, it
got unlucky once. The Litolff deficit's cause (section 0b) doesn't
correlate with tail geometry at all, so it isn't an instance of the same
class and there is no second example of IT either.

**This is a small sample (8 pages of 2 scores) and says nothing about the
other 287 editions in the library** -- only that the specific tail-threshold
mechanism is not pervasive on the two scores already flagged, and the
plate-numbering question is page-specific until Sean says otherwise.

## 2. Where it bites

- **Every later bar on the miscounted system** -- `measure_index` keys
  every downstream cell, note, duration, and the EXPORT's bar numbering for
  that system. On Brahms p0 this is exactly what broke roadmap 2.44c's
  ledger truth-set: every far-head geometry score on that page was compared
  against the wrong reference bar until `truth_set_2_44c.py` was patched to
  exclude pages whose own gather disagrees with their own verified window
  (section 15 of
  `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md`).
- **Meter carry** (CLAUDE.md section 10) is weighed by the bars; a system
  with a phantom bar reports one more bar than the print has, which is
  exactly the kind of "bar sum is a LENGTH, not a meter" case the carry
  logic was built to be skeptical of, but the carry logic trusts
  `Q.MEASURE_PARTITION` itself as ground truth for where bars start -- it
  has no way to know this partition is one of the inputs that can be wrong.
- **EXPORT's accounting EQUALITY** (every gathered notehead written or
  counted under a named refusal) is NOT violated by this bug -- the phantom
  Brahms bar 8 holds the real cautionary-signature glyphs (clef, time sig),
  which get gathered, adjudicated, and either exported as a markless extra
  bar or refused as owned-by-nothing; either way nothing goes unaccounted,
  it is just accounted under the WRONG bar number.
- **`measure_count_across_staves`** (the only existing cross-check named in
  the brief) cannot catch this by construction: `gather_measures` computes
  ONE set of barline x-positions per SYSTEM and stamps the SAME resulting
  cell count onto every staff in it -- the "across staves" group is checking
  14-way agreement with itself, not with the page. It was unanimous on both
  known pages (confirmed: `GROUPS measure_count_across_staves: ... {'none':
  0, 'single': 0, 'unanimous': 1, ...}` on the Brahms p0 run above).
- **Nothing in `tools.omr.staged.check` reads `works.json` or
  `Q.PRINTED_BAR_NUMBER` against `Q.MEASURE_PARTITION`.** The only place
  that comparison exists at all is the ad-hoc `truth_set_2_44c.py` script
  built for a different lane's ledger measurement, not a derived check.

## 3. What was built

**Nothing.** Per the brief's own step 4 gate: a fix is only in scope here if
the mechanism is a CONNECTION -- an already-gathered fact not being read.
Neither mechanism is that:

- The Brahms tail-threshold miss is a measured CALIBRATION
  (`_measure_x_boundaries`' 20%-of-median rule), not an unread fact, and its
  docstring records that the alternative (discard a narrow tail outright)
  is already a REFUTED fix -- it deleted real notes on WTC p.6 system 2. The
  right repair (if any) is a shape/content read of the tail cell itself --
  does it look like a signature block (clef+time-sig glyphs, no notehead-
  width ink) vs. a genuine short last measure -- which is a new GATHER
  question, not a wiring fix, and needs its own roadmap item per CLAUDE.md
  rule 9.
- The Litolff deficit may not be a bug at all (section 0b) -- it is a
  convention/calibration question about which side (the plate's own
  numeral, or `works.json`'s verified window) is right, which is rule 3's
  "ask first," not rule 6's "connect."

## 4. One question for Sean [REVISED after section 6's correction]

**Superseded.** The original question here (whether the plate skips bar 33)
was based on the now-withdrawn section 0b and had the arithmetic backwards
-- see section 6. The live question is narrower: on Litolff 984073 page 2
system 0, bars 19-31 (by our own, now-known-short numbering) are a
crescendo build-up with dense tremolo/chord figuration where our own
duration reader mostly abstains (exports as rests) and where I could find
no candidate column, among the barline detector's own rejects, that shows
real inter-staff ink under a 4x zoom (section 6a; crops
`out/print/2.47/litolff-p2-sys0-x838-gap-zoom.png`,
`-x838-x918-strings-gap-zoom.png`, `-x1147-gap-zoom.png`,
`-full-bars18-21-candidates.png`). **Can Sean place the missing barline by
eye in that span on the original plate** -- is there a thin/broken rule
visible there that bitonal scanning lost, or is the true bar boundary
somewhere I haven't marked at all?

## 5. What I could not verify

- Exactly which single barline inside Litolff p2 system 0 (bars 19-31) is
  missing -- narrowed to "somewhere in this 7-bar crescendo span," not to a
  specific x. Every geometric candidate I found and checked failed a direct
  ink-gap zoom (section 6a).
- Whether the Brahms tail-threshold near-miss recurs anywhere in the other
  287 library editions -- the survey here covers 8 pages of 2 works only,
  per the brief's scope.
- Whether the dropped-barline mechanism (ink loss before any candidate
  forms) recurs elsewhere in Litolff's dense tutti passages beyond this one
  confirmed instance -- section 7's printed-number cross-check found no
  second case in this 8-page sample, but a 1870 bitonal scan's ink loss is
  plausibly correlated with dynamic level (f/ff passages), which this
  sample under-represents.

## 6. RETRACTION (manager review) -- "system 0 is clean" was WRONG

The manager refuted section 0b's "system 0, confirmed clean, 16 bars" by
reference content: our export's bar 32/33/34 (E4 G4 C5 C5 / C5 half / B4 B4
B4 D5) match the REFERENCE's bar 33/34/35, a one-bar lag that starts at or
before bar 33, not at system 1. **The printed "34" at system 1's start is
correct AND consistent with system 0 holding 17 bars (17-33), not 16.**
`works.json`'s window is right; my section 0b was wrong and is withdrawn.

### 6a. Narrowing the missing barline inside system 0

Printed-number cross-check (new, see section 7): system 0 opens at printed
"17" (crop-confirmed, unchanged) and system 1 opens at printed "34"
(crop-confirmed) -- so system 0 is 17 bars by the plate's own numbers,
against our 16 decided. Content alignment against the reference (Violin I,
`P8` in our export vs `P14` in the reference .mxl) confirms bars 17-18 are
NOT shifted (our bar 18 = `D5 G5 F4 F4`, reference bar 18 = `D5 G5 G5 F5` --
same 4-note chord shape, two pitch misreads, no bar offset). Bars 19-31 in
our export are mostly exported as `R` (rest) for Violin I -- the
duration/rhythm reader abstains through this whole passage (a crescendo
buildup with dense tremolo/chord figuration in the lower strings, "cresc...
f...ff" per the print), which makes content-matching unusable there; the
shift is confirmed again only once clean content resumes at bar 32→33.

**I could not visually confirm which single barline inside bars 19-31 is
missing.** `measure_extractor`'s own candidate-cluster log for this system
(reconstructed by calling `_detect_barlines_per_staff` + the same
clustering/voting code standalone) lists every REJECTED column with
votes>=4: `x=838 (9/11 votes, connectivity 0.000)`, `x=918 (7/11,
connectivity 0.200)`, `x=1147 (6/11, connectivity 0.500)`, `x=712 (5/11,
connectivity 0.400)`, `x=1050 (6/11, connectivity 0.000)`. x=838 carries
almost as many votes as a real accepted barline (the real ones run 8-11/11
on this system) -- the single strongest-by-vote candidate for a missed
barline. But a tight 4x zoom directly on the inter-staff GAP at x=838, at
two different staff pairs (flute/oboe gap and the two violin staves' own
gap, `out/print/2.47/litolff-p2-sys0-x838-gap-zoom.png`), shows clean white
paper -- no connecting ink at all, at either gap. The same zoom check on
x=1147 (`out/print/2.47/litolff-p2-sys0-x1147-gap-zoom.png`) shows a beam
crossing the column on both staves it was checked against -- a stem/beam
alignment, not a barline. None of the five rejected candidates survives a
direct look at the print.

**My honest conclusion: the missing barline's ink did not survive page
preparation at all** -- it never fired as a per-staff candidate on enough
staves even to form a weak cluster, rather than firing and being wrongly
filtered by vote/connectivity. That is a THIRD class, distinct from both
Brahms's tail-threshold miscalibration (section 0a, a correctly-detected
column mis-classified) and a vote/connectivity misfire (section 0b's
original, now-wrong hypothesis) -- a genuine non-detection, most likely tied
to Litolff's known bitonal ink loss in dense figuration (CLAUDE.md section
10: "Litolff MERGES... ink components are not marks on the plate," 46 of
180 sampled "notehead" boxes were not noteheads). **I do not have a crop
that shows the missing barline's own ink**, because by this reading there
isn't any left to show -- only crops showing where it should be and isn't.
This needs Sean's eye on the original PDF at this location
(`out/print/2.47/litolff-p2-sys0-full-bars18-21-candidates.png`, the full
615-1220 span with all five rejects marked) more than it needs another
automated pass.

## 7. Generality, using printed bar numbers + content alignment

Printed-number cross-check at every system boundary readable across the
8-page sample (`Q.PRINTED_BAR_NUMBER`, compared against the RUNNING total
from the previous system's decided count):

| page | sys0 start (printed) | sys0 decided | expected sys1 start | sys1 start (printed) | match |
|---|---|---|---|---|---|
| litolff p1 | (none printed, bar 1) | 16 | -- | -- | n/a (1 system) |
| litolff p2 | 17 (confirmed) | 16 | 33 | **34** | **MISMATCH -- the dropped-barline case** |
| litolff p3 | 49 (confirmed) | 16 | 65 | 65 (confirmed) | match |
| litolff p4 | abstained | 15 | 98 | 98 (confirmed) | match |
| brahms p0 | abstained (bar 1) | 8 | -- | -- | n/a (1 system) |
| brahms p1 | 8 (confirmed) | 7 | 15 | abstained | can't confirm (but total matched independently) |
| brahms p2 | abstained | 6 | 29 | 29 (confirmed) | match |
| brahms p3 | 38 (confirmed) | 10 | 48 | "8" (misread of 48, digit-drop class) | consistent once corrected |

**6 of 7 checkable system-to-system transitions match exactly; the one
mismatch is the Litolff p2 case already known.** This matters beyond the
earlier (weaker) total-sum check in section 1: a total-sum match per PAGE
cannot rule out two offsetting per-system errors (e.g. sys0 short by one,
sys1 long by one) -- litolff p3 and p4's per-system printed numbers now
positively CONFIRM both systems' individual counts are correct, not just
their sum. **Both mechanisms -- the Brahms phantom-tail and this Litolff
dropped-barline -- occur in exactly 1 of 15 systems checked, each
independently confirmed by the plate's own printed numbers.** Neither
recurs elsewhere in this 8-page sample once checked this way.

### What makes each happen

- **Phantom tail (Brahms p0):** a correctly-DETECTED column (the real final
  barline, 14/14 votes) is followed by a narrow-but-non-blank strip (a
  cautionary signature) whose width (113px) clears
  `_measure_x_boundaries`' 20%-of-median absorb floor by 1%. Triggered by
  width ARITHMETIC on a correctly-read page.
- **Dropped barline (Litolff p2):** no column was ever detected with enough
  staff agreement to be a candidate at all, inside a dense tremolo/chord
  build-up on a bitonal scan already known to lose ink (CLAUDE.md section
  10). Triggered by INK LOSS before any threshold logic runs.

These are different failure classes with different likely rates elsewhere:
the tail-threshold miss is a reproducible arithmetic coincidence (any score
whose final cautionary signature happens to sit near 20% of that system's
own median bar width); the dropped barline is tied to a specific plate's
scan quality in a specific dense passage and is much harder to predict from
geometry alone.

## 8. (Sean confirmed) FOUND IT -- `prefer="leftmost"` dedup, not ink loss

Sean placed the real barline at page x~870. Measuring the binary render at
that column confirms it: on every staff of system 0, a vertical ink run of
59-65px (>= the 51-52px height gate) and 6-8px wide survives
`_detect_barlines_in_window`'s shape filter cleanly (e.g. staff 0:
`w=7 h=59 aspect=8.4`, comfortably clears height/width/aspect). So the
column IS detected per-staff -- section 6a's "ink never survived
binarisation" conclusion is WRONG and withdrawn.

What actually happens: on most staves there is a SECOND valid component
only ~35px to its left (x~832, the forte chord's stem: `w=2 h=52
aspect=26`, also clears every shape gate). `_dedup_barline_candidates`
collapses any two candidates on one staff closer than
`BARLINE_MIN_DISTANCE_PX=60`, and `_detect_barlines_per_staff` calls it with
no `prefer` argument -- the default, `prefer="leftmost"`, keeps the STEM
and throws away the barline. This is the EXACT failure the function's own
docstring names ("prefer=tallest exists because the leftmost rule loses a
real barline to a note stem... measured on Beethoven 5 p.2 system 0") --
the fix already exists and is wired into `resegment_fused_measures`'s local
re-segmentation, but never into the global per-staff pass that
`gather_measures`/`Q.MEASURE_PARTITION` actually reads. On this staff
`prefer="tallest"` recovers x~870 correctly (h=59 > 52). Only 2 of 11
staves (4, 10) voted for the real barline because the other 9 lost it to
their own local stem.

### Generality

`n_barline_candidates_dropped_too_close_on_staff` page-wide for Litolff p2
alone: 244 (both systems) -- the ingredient (two valid shapes within 60px on
one staff) is common. I did not have time to classify all 244 against print
truth; only the one Sean confirmed is verified as a real barline actually
lost. The counter says the OPPORTUNITY for this exact class is not rare;
the CONFIRMED rate is 1 instance.

### Fix: question, not a patch

This is a CONNECTION (the height/width discriminator distinguishing a
barline from a stem is already computed, already proven correct elsewhere
in this file, and discarded here by an unargued kwarg) -- but
`prefer="tallest"` is a GLOBAL per-staff default used by every page on both
pipelines (CLAUDE.md section 3), and the function's own docstring explains
WHY leftmost was kept as the global default (cheap, thins consistently) --
I have not measured what `prefer="tallest"` does to the many OTHER
close-candidate pairs in this page or elsewhere, several of which may be
real dedups where the stem is legitimately taller than a worn/thin real
barline. Flipping a shared default without that measurement is exactly
what rule 5 and rule 9 forbid. **Question for Sean: authorize a `--through
adjudicate` A/B of `prefer="tallest"` on the per-staff pass (scoped to this
one call site) against the acceptance set, or is there a narrower condition
(e.g. only override leftmost when the discarded candidate's height margin
over the kept one exceeds some bound) you'd rather see first?**

## 9. (Sean authorised) BUILT: `prefer="spanning"` -- RED-first, A/B'd

### 9a. The fix

`_dedup_barline_candidates` gained `prefer="spanning"`: among a group of
candidates within `BARLINE_MIN_DISTANCE_PX`, those whose `top_gap` and
`bottom_gap` (pixels short of the staff's OWN top/bottom line) are each
<= `SPAN_TOUCH_TOLERANCE_PX=6` are "spanning"; height decides among those;
if none spans, falls back to `leftmost` (never `tallest`) so the narrower
claim invents no winner. `_detect_barlines_per_staff` (the global pass
`Q.MEASURE_PARTITION` reads) now passes `prefer="spanning"`; the LOCAL
resegmentation path (`_find_internal_barline_candidates`) is untouched,
still `prefer="tallest"`.

`prefer="tallest"` alone was checked and REJECTED by the required control:
a stem that runs long past its notehead can be taller, in raw px, than a
genuine but shorter barline while reaching only ONE staff line, not both.

RED-first: `tools/omr/tests/test_span_touch_dedup_2_47.py` -- Sean's exact
measured geometry (barline 59px/top_gap6/bottom_gap0 beside a stem
52px/top_gap6/bottom_gap7, 35px apart) and the control (a 74px non-spanning
stem must not beat a 71px spanning barline) both FAILED against the
pre-fix tree (confirmed by temporarily restoring `measure_extractor.py`
from HEAD and re-running) and pass after the fix. A third test pins the
no-candidate-spans fallback to leftmost. 66 + 44 pre-existing tests
unaffected.

### 9b. A/B, GATHER+ADJUDICATE, all 8 pages (base=origin/main worktree,
arm=this branch, `--through adjudicate --weights auto --route-weights`)

| page | system | base | arm | truth | match (arm) |
|---|---|--:|--:|--:|---|
| litolff p1 | 0 | 16 | 16 | 16 (window) | yes |
| litolff p2 | 0 | 16 | **17** | 17 (pbn 17->34, content) | **yes -- FIXED** |
| litolff p2 | 1 | 15 | 15 | 15 | yes |
| litolff p3 | 0 | 16 | 16 | pbn 49->65 confirms 16 | yes |
| litolff p3 | 1 | 18 | 18 | (49+16=65 printed) | yes |
| litolff p4 | 0 | 15 | 15 | (98-15=83 start) | yes |
| litolff p4 | 1 | 15 | 15 | pbn 98 confirms | yes |
| brahms p0 | 0 | 8 | 8 | 7 verified -- still UNFIXED (different bug, section 0a) | n/a, other mechanism |
| brahms p1(idx1) | 0 | 7 | 7 | pbn 8 confirms | yes |
| brahms p1(idx1) | 1 | 8 | 8 | (7+8=15 window) | yes |
| brahms p2(idx2) | 0 | 6 | 6 | pbn 29 confirms (23+6) | yes |
| brahms p2(idx2) | 1 | 9 | 9 | window 15 total | yes |
| brahms p3(idx3) | 0 | 10 | 10 | pbn 38 confirms | yes |
| brahms p3(idx3) | 1 | 11 | 11 | window 21 total | yes |

**Every system matches base except Litolff p2 system 0, which moves 16->17
-- exactly and only the confirmed fix, no new phantom bars anywhere.**
Brahms p0 is untouched (expected: that page's bug is the tail-threshold
miscalibration in `_measure_x_boundaries`, section 0a -- a different
mechanism this fix does not touch).

`printed_bar_number` readings are byte-identical base vs arm on every page
(the fix changes which barline COLUMN is kept, not how digits are read).

### 9c. Readout diff, Litolff p2 (full page, both systems)

`n_barline_candidates_dropped_too_close_on_staff`: base 244, arm **244**
(unchanged -- this counts COLLISIONS, not which side of each collision is
kept). `n_barline_clusters_rejected_no_prong` (the system-level vote/
connectivity gate, downstream of the per-staff fix): base 55, arm **48** --
7 fewer system-level rejections, consistent with more of the per-staff
candidate pool now being the real barline rather than a competing stem.

Classified 10 of the arm's 200 remaining per-staff collision groups on this
page (`random.seed(42)`), by their recorded geometry rather than a fresh
crop for each (time): **0 of 10 are a lost barline.** 2 of 10 dropped a
non-spanning stem (gaps like `(4,7)`, `(0,8)`) -- correctly excluded. 8 of 10
dropped a SECOND spanning candidate 14-56px from the kept one -- too close
for either to be a distinct measure (the page's own real bars run
100-300px) given the already-confirmed accurate system totals above, so
these are the same physical rule read as two (or three) thin components
(anti-aliasing splitting one stroke, or a close double-bar), correctly
merged to one barline either way.

### 9d. What this does not establish

- Only Litolff p2 and the 8-page sample were A/B'd; `prefer="spanning"`'s
  effect on the other 287 editions, or even the rest of these two movements,
  is unmeasured.
- The 10-sample classification used recorded geometry, not a fresh print
  crop per case -- consistent with section 1's totals already matching, not
  independently crop-verified here.
- Not merged anywhere; scoped to this branch per Sean's authorization.

## 10. ROADMAP 2.47b -- a cautionary clef/key/meter is not a bar, generalised

Section 0a (above) diagnosed one page by width calibration and stopped:
*"the right repair ... is a shape/content read of the tail cell itself ...
which is a new GATHER question ... and needs its own roadmap item."* This
item is that read, placed where the brief required: ADJUDICATE, after the
detector has already run, so looking inside the cell is a CONNECTION (rule
6) over an already-gathered fact (`Q.GLYPH_BOX`), never a new GATHER
mechanism.

### 10a. Where the rule lives

`structure.adjudicate_measure_partition` is the only decision that reads
`Q.BARLINE_COLUMN` (a per-staff cell COUNT, nothing about content --
`gather.gather_measures`). It now also declares `Q.GLYPH_BOX` and, when the
staff has at least two cells (a real barline exists before the candidate
tail), asks `_trailing_cell_is_cautionary_only(ev, system_sub,
last_cell_index)`:

- reads `Q.GLYPH_BOX` at `Scope.SELF_AND_DESCENDANTS` from the STAFF's own
  SYSTEM ancestor -- every staff of the system, not just the one being
  decided, because CLAUDE.md section 10's "printed at one bar on every
  staff of the system" cuts the other way too: one staff with a genuine
  short final bar or a pickup means the SYSTEM has not yet closed, and the
  tail is real for everyone;
- restricted to rows filed in the exact trailing cell (`subject.cell ==
  last_cell_index`);
- demotes (`value = n_cells - 1`, `reason = "cautionary_tail_not_a_bar"`)
  only when every one of those rows, across every staff, reads as
  `_is_signature_glyph_class` -- `clef*` / `key{Flat,Sharp,Natural}` /
  `timeSig*`, explicitly EXCLUDING `keyboard*` (the one `"key"`-prefix
  collision in the 208-class space: `keyboardPedalPed`/`Up`, which must
  never pass as a key signature);
- an EMPTY cell (the detector found nothing there at all) answers False,
  not True -- rule 8, "we found nothing" is not evidence either way, so
  today's geometry-only count stands;
- `n_cells < 2` (no barline read at all for this system) is never touched
  -- there is no "last barline" for a tail to follow.

### 10b. RED-first tests

`tools/omr/tests/test_staged_measure_partition_2_47b.py`, 9 tests + a
dedicated classifier unit-test class. RED confirmed by `git stash` of
`structure.py` alone and re-running: 3 of 9 fail (the headline synthetic
case, 8 decided cells -> 7, plus both `_is_signature_glyph_class` unit
tests, since the function does not exist pre-fix) -- the 6 CONTROLS pass
unchanged on both trees, as rule 7 requires:

- a real note/rest anywhere in the trailing cell, on ANY staff, keeps the
  WHOLE system's tail a bar (both a notehead and a rest tested separately);
- a system with no barline at all (`n_cells == 1`) is untouched;
- an EMPTY trailing cell (no `Q.GLYPH_BOX` row) keeps today's behaviour;
- a `keyboardPedalPed` box alone in the tail does NOT pass as a key
  signature (the one classifier collision, pinned as its own regression);
- no `Q.BARLINE_COLUMN` row still abstains `no_barline`, unchanged.

`pytest -m "not slow" tools/omr/tests`: 4,199 passed (base tree re-measured
at 4,190 + the 9 new), 0 failed, 3 skipped, 2 xfailed.
`python3 -m tools.omr.staged.check`: TOTAL 245, unchanged from the base
tree.

### 10c. A/B, GATHER+ADJUDICATE, `--weights auto --route-weights`

Base = a dedicated detached worktree at `8f1b2228` (the 2.47 merge commit
this brief named). ⚠️ The shared `/private/tmp/base-check-2a9f` another
session was already using for the SAME purpose was deleted out from under
this one mid-run (`ModuleNotFoundError: tools.omr.staged.record_io` on a
tree that plainly has the file -- the checkout itself was gone, CLAUDE.md
section 13's shared-checkout collision, hit again) -- recreated privately
via `git worktree add --detach`, never touching the shared one again.

**Litolff pp.1-4, all 7 systems, 75 staves: 0 diffs.** Every system's
`measure_partition` value is byte-identical base vs arm and matches 2.47's
own printed-truth table exactly (p2/sys0 stays 17, etc.) -- the fix is
INERT exactly where 2.47 already measured no cautionary-tail defect.

**Brahms pp.0-3, all 7 systems, 97 staves: p0/sys0 stays 8, NOT 7.** The
one case this item was built to fix does not flip on a real re-gather.
Diagnosed, not shrugged off:

The trailing cell's own `Q.GLYPH_BOX` output (46 rows across 14 staves,
today's auto-routed weights) is not the clean "clef + time signature" a
human crop-read expects. On staves 3 and 4 the SAME ink is boxed as BOTH
`timeSig8` and `noteheadWholeInSpace` at IoU 0.94-0.96 -- measured with a
small standalone IoU script, not eyeballed. On staves 5, 9, 11, 13 the
strip holds standalone `noteheadWholeInSpace`/`ledgerLine` boxes with no
`timeSig` or `clef` row at all. No staff in this cell gets a `clef*` class.

**Crop-verified at 600 dpi** (`out/print/2.47b/brahms-p0-sys0-staff3-tail-
dup.png`, 1211x240; `-staff11-tail-noclef.png`, 1211x160 -- both >=1000px
wide, rendered directly from the PDF via PyMuPDF at the gather's own 600
dpi, double barline plus the tail visible in frame): BY EYE both staves
show the system's final (double) barline followed by nothing but a
cautionary **"9/8"** meter change -- no clef, because the clef does not
change into the next system (CLAUDE.md section 10 names a cautionary METER
and a cautionary CLEF as separate facts; only the one that changes is
printed). The `noteheadWholeInSpace`/`ledgerLine` boxes on staff 11 sit at
the SAME x position as the "9/8" digits, not beside them -- they are the
digits' own round loops and serifs read under a second, wrong class guess.
This is the exact duplicate-detection shape `gather.py`'s own
`gather_detections` docstring already names and explicitly declines to fix
there ("NOT CHANGED HERE, because changing it changes the DETECTION SET
... only two full re-gathers can price it" -- 284 same-cell notehead pairs
measured on the committed Litolff record, IoU 0.91-0.96).

So **by print, Brahms p0 IS the mechanism this item targets** -- the
connection built here is reading the evidence correctly and refusing,
correctly, to demote past contamination it cannot itself deduplicate. The
remaining gap is the detector's pre-existing, already-documented
duplicate-class defect on tiny high-contrast ink (a digit's round bowl
reading as a notehead), which is a GATHER/detection-level fault out of this
item's scope (rule 6: connect, never guess past it; a detection-set change
needs two full re-gathers to price, section 6b) -- not a flaw in
`adjudicate_measure_partition`'s own logic. `readout diff` on this page:
`measure_partition` unchanged (97 decided both arms, identical values
per-subject); no other quantity touched (the decision reads one new input,
writes the one it always wrote).

### 10d. Generality

`ijson`-streamed directly over `library/_shared-records/{beethoven5-
litolff-mvt1-whole-20260930b,brahms1-breitkopf-mvt1-whole-20260930b}
.record.json` -- `record.verdicts.item` and `record.observations.item`
read one row at a time, no pool expansion, so the 3.4 GB Brahms record
never exceeded ~220 MB RSS (confirmed with `ps` during the run). For every
staff with a DECIDED `measure_partition`, its own last cell's `Q.GLYPH_BOX`
classes are collected and bucketed PER STAFF -- this is an approximation of
the real decision, which additionally requires every OTHER staff of the
system to agree; it does not re-run that cross-staff check, so it over-
counts "signature-only" candidates relative to what the real decision would
actually demote.

| record | staves decided | signature-only (candidate) | mixed (Brahms-p0 shape, left alone) | real final bar | empty tail |
|---|--:|--:|--:|--:|--:|
| Litolff whole mvt1 (47 pages) | 331 | 1 | 11 | 318 | 1 |
| Brahms whole mvt1 (53 pages) | 691 | 9 | 49 | 632 | 1 |

The one Litolff "signature-only" candidate, inspected: `page/15 system/0
staff/4`, classes `{timeSig8, timeSig1}` -- a plausible real instance (not
crop-checked, time budget), and a reminder that this item is not Brahms-
only: Litolff's own tail-threshold geometry was never near the 20% line
anywhere in section 1's 8-page survey, yet a signature-only trailing cell
still occurs 36 pages outside that sample.

So the mechanism is not rare across the two whole movements (10 signature-
only candidates total, beyond the one page measured in section 0a), but
roughly 4-5x as many trailing cells land in the contaminated "mixed"
bucket this fix correctly declines to touch -- consistent with section
10c's finding that the duplicate-class defect, not the cautionary-strip
shape itself, is the dominant obstacle to this item actually firing on
real pages.

### 10e. What could not be verified

- Whether the other 9 Brahms / the 1 Litolff "signature-only" candidates
  named in 10d are real (no crop budget beyond the two in 10c).
- Whether the duplicate-class detector defect is specific to a cell this
  narrow (113px, pushed through the same canonical upscale as a full-width
  bar) or recurs at any tail width -- not measured.
- Whether a dedup pass ahead of this decision (same-region, cross-class)
  would let Brahms p0 actually flip -- plausible from 10c's IoU numbers,
  but building it is explicitly out of this item's scope (a GATHER-
  adjacent change, needs two full re-gathers to price) and is not
  attempted here.

## 11. Verification lane (lane-2.47b-verify) -- the real cross-staff rule

fires ZERO times on real data; section 10d's "10 signature-only candidates"
were a per-staff approximation artifact

Manager-dispatched verification of the branch built in section 10, against
CLAUDE.md rule 7 ("a control must be able to fail"). Rebased cleanly onto
`main` (`fd396df0`) with no conflicts (`CLAUDE.md`/`DECISIONS.md` edits
this branch carried were already superseded upstream) -- head is `de50e63d`.

### 11a. Tests and check, unchanged

`pytest tools/omr/tests -m "not slow" -q`: **4,199 passed, 3 skipped, 2
xfailed, 0 failed** -- matches section 10b's own claim exactly, re-measured
on the rebased tree. `python3 -m tools.omr.staged.check`: **TOTAL 245**,
unchanged.

### 11b. The real decision is CROSS-STAFF, and that changes the headline count

Section 10d's generality streamer approximated the rule PER STAFF (its own
last cell's glyphs alone) and said so explicitly ("does not itself re-run
the cross-staff ALL-of-system check the real decision makes... over-counts
signature-only candidates"). This lane built the REAL check: two-pass
`ijson` streamer (no full-record expand; Brahms 3.47 GB stayed under 250 MB
RSS) that, per system, pools every staff's `Q.GLYPH_BOX` rows filed at the
shared last-cell index -- exactly what
`_trailing_cell_is_cautionary_only`'s `Scope.SELF_AND_DESCENDANTS` query
over the SYSTEM does -- before classifying.

Run over **both whole movements, both available gather generations**
(`library/_shared-records/{beethoven5-litolff,brahms1-breitkopf}-mvt1-
whole-{20260930b,20261001}.record.json` -- 20261001 is the current overnight
run named in ROADMAP's 10-01 start-here):

| record | staves decided | **demoted (candidates)** | mixed (sig+note, left alone) | real final bar (left alone) | empty (left alone) |
|---|--:|--:|--:|--:|--:|
| Litolff 20260930b (47 pp) | 331 | **0** | 84 | 247 | 0 |
| Litolff 20261001 (47 pp) | 331 | **0** | 95 | 236 | 0 |
| Brahms 20260930b (53 pp) | 691 | **0** | 395 | 296 | 0 |
| Brahms 20261001 (53 pp) | 691 | **0** | 408 | 283 | 0 |

**Zero demotions, on either document, on either gather.** Every one of
section 10d's 10 "signature-only" per-staff candidates (the Litolff
`page/15 system/0 staff/4` instance named there and 9 unnamed Brahms ones)
dissolves once the OTHER staves of its own system are pooled in, exactly as
section 10d itself warned it might. Confirmed directly against the real
branch code (not the reimplementation) by loading the raw observations for
two sample pages into an actual `Log` and calling
`adjudicate.adjudicate_one(..., REGISTRY[Q.MEASURE_PARTITION], ...)`:
`staff/15/0/4` (the named Litolff candidate) decides `22, "read"` -- not
demoted -- and all 14 Brahms p0/sys0 staves decide `8, "read"`, matching
section 10c's own finding on the newer gather too.

### 11c. Crop-verified, both directions, on the CURRENT (20261001) gather

- **`out/print/2.47b/brahms-p0-sys0-tail-20261001.png`** (2027x5527, 600
  dpi, all 14 staves, cell 7 boxed): BY EYE every staff's final cell is
  still unambiguously a cautionary "9/8" and nothing else -- confirming
  section 10c's diagnosis is still current on the newest gather -- but the
  same duplicate-class contamination persists (`timeSig8, timeSig5` /
  `ledgerLine, note...` captions on several staves, the identical
  same-ink-two-classes shape), so the system-wide all-signature-only test
  still correctly declines to fire. The detector defect named out-of-scope
  in section 10c has NOT been fixed by any work since.
- **`out/print/2.47b/litolff-p15-sys0-tail.png`** (1100x1826, 600 dpi, all
  11 staves, cell 21 boxed): a genuine real final bar -- four staves hold
  only a `restWhole` (the shortest possible content short of silence) and
  the rest hold real noteheads/articulations/ties -- correctly decided
  `22, "read"` on every staff. This doubles as the brief's "a real short
  final bar is NOT demoted" control: the `restWhole`-only staves are as
  minimal as a real bar gets and are rightly left alone.

### 11d. What could NOT be verified: a true positive on real data

Per CLAUDE.md rule 7, a control must be able to fail; the brief also asked
to confirm at least one demotion actually fires on real data. **None does,
anywhere in the measured acceptance set, on either gather generation** --
11b is exhaustive over both whole movements. The only verified firing
remains the committed synthetic RED-first unit test
(`test_cautionary_tail_is_not_counted_as_a_bar`). This is a genuine gap
against the brief, not a success to report quietly: **as shipped, this
connection has fired zero times on real data in six months of corpus and
cannot yet be said to help**, though it has also never produced a false
positive across 1,022 staff-decisions measured twice over. Its entire
payoff is gated on the pre-existing, separately-scoped detector
duplicate-class defect (section 10c, `gather.py`'s own documented
same-ink-two-classes behaviour) -- a GATHER-level fix, needs two full
re-gathers to price (rule 6b), out of this item's scope.

### 11e. Recommendation

Merge-safe on the evidence measured: tests and `check` unchanged, zero
false positives across both documents and both gather generations, the
connection is correctly scoped (cross-staff, abstains on empty, leaves
`n_cells < 2` alone) and fully covered by RED-first tests. Flag for
ROADMAP: this item earns nothing until the duplicate-class detector defect
is fixed, which is a GATHER change and its own roadmap item, not a
follow-up inside 2.47b.

## 12. ROADMAP 2.47c -- the duplicate-class defect itself, refused

Section 10c/11c both named the same cause and left it out of scope: the
detector draws a SECOND box on a meter digit's own ink, correctly classed
`timeSig*` once and misclassed `noteheadWholeInSpace` a second time, at IoU
0.94-0.96. `notehead_precision._notehead_duplicate_box_refusal` (2.30)
never compares across families, so nothing refused it. This item builds
that cross-family rule: `_timesig_digit_duplicate_refusal`, a notehead-
classed box at IoU > 0.9 against a `timeSig*` box in the SAME cell is that
digit's own ink, reason `is_a_time_signature_digit`. IoU alone is the gate
(no centre test, unlike 2.30) -- a `timeSig*` box and a real nearby head
are two independently-drawn boxes that do not share 90% of their area by
chance; `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §21b and this
file's own §10c/§11c crops are the print evidence, not a fresh guess.

### 12a. Tests and check

`tools/omr/tests/test_staged_timesig_digit_duplicate.py`, 6 tests. RED
confirmed by reverting `notehead_precision.py` to `origin/lane-2.47b-
verify`'s own tree and re-running: 3 of 6 fail (the duplicate-refusal unit
test, the positive control's own kept-case regresses to the SAME "notehead"
reason by coincidence rather than the floor doing the work -- caught
because the test also asserts the fixture's IoU clears/misses the floor
independently of the verdict -- and the ordering-gap test's own "refused"
half); the 3 CONTROLS (no `timeSig*` in the cell, a `timeSig*` box is never
itself a subject, and -- separately pinned -- the measure_partition
ordering-gap finding) pass on both trees. `pytest -m "not slow"`: 4,205
passed (base 4,199 + 6), 0 failed, 3 skipped, 2 xfailed. `check`: TOTAL
245, unchanged.

### 12b. Real data, re-adjudicated off the committed `20261001` records

`ijson`-streamed, never the whole record in memory (a standalone IoU-only
counting pass, then a second, authoritative pass that loads ONE page's own
observations into a real `Log` and calls the actual branch code via
`adjudicate.subjects_for`/`adjudicate.adjudicate_one` -- `lane-2.47b-
verify`'s own §11b technique, reused):

| record | population | refused (`is_a_time_signature_digit`) | max candidate IoU where NOT refused |
|---|---|--:|--:|
| Litolff whole mvt1 (47 pp, 486 MB) | 137 notehead boxes sharing a cell with a `timeSig*` box | **0** | 0.736 |
| Brahms pp.0-1 (3.47 GB whole record, read to page 1 only) | 188 such boxes | **4** | -- |

Litolff's own maximum (0.736, a real notehead a hair under a `timeSig2` box
in a crowded bar) sits comfortably below the 0.9 floor with margin on both
sides, matching this item's own module comment. Brahms's 4: two at the
OPENING 6/8 (page 0 system 0 cell 0, staves 1), IoU 0.972/0.928, and the
two already crop-verified at the cautionary 9/8 tail (cell 7, staves 3/4),
IoU 0.963/0.944 -- `glyph/0/0/3/7/3` is the identical glyph
`omr-bar-sum-holdout-2026-09/FINDINGS.md` §21b traced end to end and
print-verified 1 of 1.

**Against the real branch code, not a reimplementation**: page 0 system
0's own 9,618 observations loaded into a fresh `Log`, `adjudicate.
subjects_for` (not a bare subject walk -- an earlier draft of this check
iterated every glyph regardless of `subjects_from=Q.NOTEHEAD_CLASS` and
produced 68 nonsense "refusals" on `timeSig*`-classed subjects that were
never notehead candidates at all; caught before being reported, matching
CLAUDE.md §13's own warning about an unverified lane claim). With the real
subject domain: all 4 glyphs above decide `True, is_a_time_signature_digit`
exactly as the standalone IoU pass found, and `Q.MEASURE_PARTITION` on
every one of the 14 staves in page 0 system 0 **still decides `8, "read"`
-- NOT 7**. Diagnosed, per the brief's own instruction to report rather
than reorder: `Q.MEASURE_PARTITION` sits at position 4 in `adjudicate.
ORDER`, `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` at position 76 (well after it), and
`structure._trailing_cell_is_cautionary_only` reads each glyph's raw
DETECTOR class (`Q.GLYPH_BOX`'s own `value[0]`) directly -- it has no way
to see a later-stage refusal verdict even if it ran after one, because a
refused glyph's `Q.GLYPH_BOX` class is left exactly as the detector wrote
it (REFUSED, never relabelled -- CLAUDE.md's own "the record keeps the
row"). Neither of the brief's two conditions for a safe reorder holds, so
this is reported, pinned as its own regression test
(`TestMeasurePartitionOrderingGap`), and NOT built.

This refusal's payoff is at EXPORT, not at `measure_partition`:
`export.py`'s own accounting buckets a refused glyph `not_a_notehead:
is_a_time_signature_digit` and drops it before duration or pitch is ever
derived from it, so the bar it sat in no longer carries a spurious
duration. Of `omr-bar-sum-holdout-2026-09/FINDINGS.md` §21b's "remaining 7
of 73 sampled bars" attributed to this exact mechanism, only ONE
(`glyph/0/0/3/7/3`'s own bar) was individually named by subject; the other
6 were counted but not enumerated in that pass and are not re-locatable
here without redoing its sampling -- not attempted (out of scope, time
budget).

### 12c. Crops

4 of 4 refused boxes, `out/print/2.47c/` (600 dpi, PyMuPDF, ≥1000 px wide,
red = the refused notehead box, blue = the `timeSig*` box it duplicates --
the two outlines sit nearly on top of each other, which IS the IoU > 0.9
claim):

- `brahms-p0-s0-staff1-cell0-glyph24.png` / `-glyph30.png` -- the movement's
  OPENING 6/8, both boxes landing on the open bowl of the "8".
- `brahms-p0-s0-staff3-cell7-glyph3.png` / `-staff4-cell7-glyph3.png` -- the
  cautionary 9/8 tail, same shape, same cell 2.47b's own §10c/§11c already
  crop-verified from the OTHER side (the `timeSig8` box, not its duplicate).

BY EYE, 4 of 4: every boxed region is unambiguously the lower loop of a
printed "8", never a notehead. No crop made for Litolff -- nothing was
refused there to look at.

### 12d. Recommendation

Merge 2.47b and 2.47c together. 2.47b is a correct, currently-inert
connection (FINDINGS §11e); 2.47c removes exactly the detector-level
contamination 2.47b's own §10c diagnosis named as the reason it stays
inert on Brahms p0 -- but, per §12b above, it does not and structurally
cannot make 2.47b's demotion fire on that same page, because
`measure_partition` decides before this refusal exists and reads the raw
class, not the verdict. The two items are complementary fixes to the same
diagnosed page, not a sequential unlock; both are safe on the evidence
measured here (tests, `check`, zero false positives on Litolff, 4
crop-confirmed true positives on Brahms).

## 13. ROADMAP 2.47b (majority) -- the all-staves quorum becomes a majority vote

DECISIONS 2026-10-01, Sean, on Brahms p0/system 0 still deciding 8 bars
after the 2.47b+2.47c merge (`deaa4fbc`): *"if most of the bars confirm the
time signature then it should run on all of the staves."* 2.47bc's own
FINDINGS §12/ROADMAP row already diagnosed why the headline page stays
inert: 4 of its 14 staves have no `timeSig` box in the tail cell at all
(a detector MISS, not a duplicate-ink pair), so the old unanimous
"every staff" test could never fire there.

### 13a. What changed

`structure._trailing_cell_signature_vote(ev, system_sub, last_cell_index)`
is a new helper: per staff with at least one `Q.GLYPH_BOX` row in the
system's shared trailing cell, decide signature-only exactly as before
(clef/key/timeSig class, or a notehead box that duplicates a `timeSig*`
box's ink per `geometry.is_timesig_digit_ink`, ROADMAP 2.47bc), and return
`(n_signature_only, n_with_trailing_cell)`. A staff with NO row at all in
the cell is counted in neither number (rule 8: "we found nothing" is not
evidence for or against the vote). `_trailing_cell_is_cautionary_only` now
demotes when `n_with_trailing_cell > 0` and `2 * n_signature_only >
n_with_trailing_cell` -- STRICTLY more than half, not `>=`, so an exact tie
does not demote. The vote is filed in the verdict's own
`detail["signature_only_vote"]` (e.g. `"9/14"`) rather than left for a
later lane to re-derive (`feedback_derive_dont_relist.md`).

### 13b. RED-first tests

`test_staged_measure_partition_2_47b.py`'s `TestCautionaryTailDemoted` was
rewritten at the real page's 14-staff scale (was a 3-staff shrink):

- Headline: 10/14 signature-only + 4 staves with stray
  `noteheadWholeInSpace`/`ledgerLine` boxes (no `timeSig` at all, the real
  page's own detector-miss shape) -> demoted on all 14, vote `"10/14"`.
- Control: 6/14 signature-only -> NOT demoted (well under half; the old
  unanimous rule and the new majority rule agree here).
- Control: exactly 7/14 (half) -> NOT demoted -- must be able to fail a
  `>=` bug.
- Control: a real notehead+rest tail on 9/14 staves (most staves) ->
  NOT demoted; the majority rule must cut both ways, never defaulting to
  "demote" on disagreement.

RED confirmed: reverted `structure.py` to `git show HEAD:...` (`main`
`deaa4fbc`, the pre-majority, unanimous-only tree) and re-ran this file --
`test_cautionary_tail_is_not_counted_as_a_bar` failed (asserted 7, got 8),
every other test (the three controls above plus the pre-existing
`TestControls`/`TestSignatureGlyphClassifier` suites) passed unchanged on
both trees, as required. Restored the fix: GREEN, 11/11 in this file.

`pytest -m "not slow"`: **4,209 passed** (base `3371dd78`'s 4,207 + 2 net
-- one old test (`test_RED_a_real_note_in_the_tail_on_ONE_staff_keeps_it_
a_bar_for_ALL`, a 3-staff test whose 2/3 vote IS a majority under the new
rule and would silently flip meaning if left in place) was replaced by
three new tests at the 14-staff scale), 0 failed, 3 skipped, 2 xfailed.
`python3 -m tools.omr.staged.check`: **TOTAL 245**, unchanged.

### 13c. Real data -- both whole movements, ijson-streamed, no full-record expand

Two-pass streamer (pass 1: `barline_column` per staff -> `n_cells`; pass 2:
`glyph_box` rows at each system's shared last-cell index), re-run through
the real per-staff classifier logic, then cross-checked on the one page
that moved by loading ONLY that page's observations into a real `Log` and
calling `adjudicate.adjudicate_one(..., REGISTRY[Q.MEASURE_PARTITION], ...)`
-- not a reimplementation. Brahms stayed under ~150 MB RSS throughout (the
record is 3.4+ GB on disk).

| record | systems with a trailing cell | changed (old != new) |
|---|--:|--:|
| `beethoven5-litolff-mvt1-whole-20261001.record.json` (47 pp, 31 systems) | 31 | **0** |
| `brahms1-breitkopf-mvt1-whole-20261001.record.json` (53 pp, 53 systems) | 53 | **1** |

The one Brahms change is page 0, system 0 -- vote **9/14** (not the 10/14
the 2.47bc diagnosis row estimated by eye off the per-staff classifier
alone; measured exactly here, not assumed), old verdict `8, "read"` on
every staff, new verdict `7, "cautionary_tail_not_a_bar"` on every staff,
confirmed via the real `adjudicate_one` call on all 14 staves of that
system (not the streamer's own reimplemented vote). **No other system on
either whole movement changes.**

### 13d. Crop

Brahms p0/system 0 is already crop-confirmed on the current (20261001)
gather by FINDINGS §12d/the 2.47bc lane: `out/print/2.47b/brahms-p0-sys0-
tail-20261001.png` (2027×5527, 600 dpi, all 14 staves, the dropped cell
boxed red) -- BY EYE every staff's tail cell is unambiguously a pure
cautionary "9/8" and nothing else. Since §13c found no OTHER system
changed on either movement, no new crop was needed for this lane.

### 13e. Recommendation

Merge-safe on the evidence measured: RED-first tests (including the
required "cuts both ways" controls), `check` unchanged, and the one real
firing in the acceptance set is the exact page Sean's 2026-10-01 decision
named, with the vote now recorded in the verdict's own detail rather than
re-derived by a later lane.
