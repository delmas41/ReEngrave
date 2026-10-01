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

### 0b. Beethoven 5/i, Litolff 984073, PDF page 2, system 1 -- MISSING bar
(15 decided where 16 is needed to reach 32 across the page; 31 vs 32
verified)

System 0 on this page is clean and crop-confirmed: 16 cells (15 interior +
a 150px tail against a 139px median, nowhere near the 27.8px absorb
threshold -- `out/print/2.47/litolff-p2-sys0-tail-end-x2300-2650.png` shows
the system's own closing double-bar sitting right at the measured `x_end`,
no spurious or swallowed content). That is bars 17-32, 16 bars, exactly
matching `works.json`.

System 1 is where the deficit is, and it is **not a tail/threshold
artefact** -- `dropped_at_edge=2` (a normal open+close pair), tail/threshold
margin 551% (nowhere near a near-miss). The printed bar number at this
system's own start, read directly off the plate
(`out/print/2.47/litolff-p2-sys1-printed-bar-number-zoom.png`, 600dpi,
4x zoom): **"34."** Not 33. System 0 ends at bar 32; this system's own
engraved numeral skips straight to 34 -- the plate itself has no bar 33
anywhere between them, by its own numbering, independent of anything our
barline geometry does. Our gather's own `printed_bar_number` adjudicator
misreads this as "4" (drops the leading digit; a known class, 2.46), which
is a separate, smaller bug (the OCR crop is too tight) and not why the
count is short.

**This is not clearly a partition bug.** The geometrically-detected bars on
this system are all normal width (109-293px against a page where 100-300px
is the typical range) and none looks doubled or halved. The most likely
explanation is that this 1870 Litolff plate has an engraving numbering slip
(32 to 34, no 33) that the modern reference encoding `works.json` was
verified against does not carry -- i.e. `works.json`'s "32 verified" may
itself be the thing that needs re-checking against the PLATE's own
numerals, not our partition. **I could not establish which side is wrong
without print access Sean already has and I don't** -- see section 4, the
one question.

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

## 4. One question for Sean

On Litolff 984073 page 2 (`out/print/2.47/litolff-p2-sys1-start-printed-bar-34.png`,
the whole system-1 opening, and
`out/print/2.47/litolff-p2-sys1-printed-bar-number-zoom.png`, a tight 4x zoom
on just the numeral): **the plate's own printed bar number at the start of
this system reads "34," with system 0 (confirmed clean, 16 bars) ending at
32 right before it -- no bar 33 anywhere on the page by the plate's own
count.** `benchmarks/omr-scan-e2e-2026-09/works.json` has this page verified
at 32 measures (continuous 17-48). Is this an original 1870 engraving slip
(the plate really skips from 32 to 34, and our 31-bar read is correct), or
is there a bar 33 I'm not seeing that the plate numbers differently? If it's
the former, the `works.json` window for this row needs re-verifying against
the plate rather than the reference encoding's continuous numbering.

## 5. What I could not verify

- Whether the Litolff "33" is truly absent from the plate or whether I am
  missing it (I looked at the full system-0-tail crop and the system-1-start
  crop and found no candidate bar between them, but I have not compared
  against a second Litolff-family copy or the Breitkopf/Gutmann editions of
  the same passage).
- Whether the Brahms tail-threshold near-miss recurs anywhere in the other
  287 library editions -- the survey here covers 8 pages of 2 works only,
  per the brief's scope.
