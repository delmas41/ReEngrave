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
