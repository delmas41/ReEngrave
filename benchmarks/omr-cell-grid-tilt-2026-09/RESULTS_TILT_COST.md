# What the tilted cell grid costs on scanned input — measured, and the answer is "not on this benchmark, because this benchmark hasn't got the defect"

**Question.** `FINDINGS.md` established that `Staff.line_ys` models a staff as
five ideal horizontal rows, that `measure_extractor._build_measure_cell` copies
those five constants into every cell of the staff, and that on scans the
printed staff tilts far enough (0.3–0.65 spaces at the ends) to name the wrong
half-step slot — with `pitch_resolver` reading exactly those per-cell rows. That
section closed asking for the production cost to be measured before a fix was
designed. This is that measurement.

**Answer, in one line: the fix is real and the instrument is blind.** Localizing
each cell's grid onto its own ink recovers every displacement the page probe
measured by hand, to within 0.04 staff spaces on all seven flagged cells — and
moves the scan e2e benchmark by **2 edits out of 7894** (pooled 0.7517 →
0.7509). Not because the defect is small, but because that benchmark reads
**page 1 of five works**, and page 1 of a bound book is where the paper is
flattest: **0.4% of its 1143 cells** sit past the quarter-space parity-flip
line, against **16.0%** on the pages the labeling campaign flagged and **8.3%**
across 26 pages sampled deeper into the same editions. *A corpus that cannot
express a fault cannot price it.*

```bash
# the mechanism, against FINDINGS §1's hand-traced residuals
python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_localization.py
# the population: how many cells carry a displaced grid, per page
python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_scan_corpus_offsets.py
python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_library_tilt_population.py
# the A/B (baseline first, then the arm) — fixtures land under separate tags
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --force \
    --out benchmarks/omr-cell-grid-tilt-2026-09/results-baseline.json
OMR_CELL_LINE_TRACE=1 python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py \
    --tag tilt --out benchmarks/omr-cell-grid-tilt-2026-09/results-localized.json
```

---

## 1. The mechanism: a comb, slid — and why not five lines followed separately

`measure_extractor._cell_line_offset` scores the staff's five rows as ONE rigid
comb against the per-row ink profile of the cell's own columns, over integer
shifts bounded below one line spacing, and takes the argmax. The staff-level
model is untouched: `Staff.line_ys` stays the one description of the whole
staff, and only the per-cell copy moves. The crop, the upscale factor and the
cell's pixels are identical either way — a slide of the stored rows, not a
re-cut — which is what keeps every box in every labeled batch where it was.

⚠️ **The obvious mechanism is following each line to its own nearest ink, and
it fails on the largest case in the corpus.** `header_ink.trace_staff_line`,
re-seeded to extend its ~⅓-space reach, agrees with the hand-traced residual
to within 0.08 spaces on six of the seven flagged cells. On the seventh —
Dvořák 9 p.8 staff 4, the −0.55-space case — it **aliases**: past half a space
the nearest printed line to a modeled row is the row *below* it, some of the
five lock onto their neighbours and some do not, and the five offsets it
returns spread **20.5 px against 0.5–2.0 px** on every coherent case. It
answered **+0.32 where the truth is −0.55** — a correction 0.87 spaces the
wrong way, worse than leaving the grid alone. Sliding the whole comb cannot
alias inside a bound smaller than one spacing, because moving a five-line comb
by a spacing leaves only four of its rows on a printed line.

**Measured against FINDINGS §1's hand-traced residuals** (`probe_localization.json`):

| cell | hand | comb fit | Δ | min row coverage |
|---|--:|--:|--:|--:|
| dvorak9-p8-sys0-s4-m12 | −0.55 | **−0.554** | −0.004 | 0.974 |
| mahler1-p3-sys0-s7-m5 | +0.36 | +0.336 | −0.024 | 1.000 |
| mahler1-p4-sys0-s0-m9 | +0.25 | +0.264 | +0.014 | 0.991 |
| mahler1-p4-sys0-s1-m9 | +0.33 | +0.343 | +0.013 | 1.000 |
| brahms1-p2-sys1-s21-m6 | −0.40 | −0.440 | −0.040 | 1.000 |
| schehe-p4-sys0-s3-m0 | +0.28 | +0.273 | −0.007 | 0.856 |
| beet5hr-p48-sys0-s14-m0 | −0.11 | −0.098 | +0.012 | 0.991 |

All seven within 0.04 spaces, on two independent rasters and two independent
methods. **That chain reaches the human labels**: FINDINGS §1 showed the
ink-measured parity reproduces Sean's class on **8 of 8** geometry cases (the
9th being a click-vs-head-centre artifact), and this fit reproduces the ink
measurement.

⚠️ **The two SILENT wrong labels were then measured directly rather than
inferred from that chain, and the first attempt got one of them wrong.** They
are the cases this work exists to have prevented, so "it would have caught
them" is a claim that has to be run, not reasoned:

| label (FINDINGS §3) | hand | comb fit | rows covered |
|---|--:|--:|--:|
| `brahms1-p2-sys1-s20-m6` | −0.40 | −0.436 | 4 of 5 |
| `lamer-p5-sys0-s2-m0` | −0.45 | −0.407 | 5 of 5 |

Both now reproduce — but under the first gate set, requiring all five rows to
be inked, **`brahms1-p2-sys1-s20-m6` abstained**, and the abstention was the
gate's fault rather than the fit's: it fits at −0.436 with coverage
`[1.00, 1.00, 0.374, 1.00, 1.00]`, because that staff's own MODELED rows are
unevenly spaced (gaps 27, 22, 33, 28 px at spacing 27.5) so one comb row cannot
sit on the print at any shift. Phase 1's fit is distorted there, not merely
displaced, and a rigid comb inherits the distortion. Hence
`CELL_LINE_MIN_ROWS_COVERED = 4` — four rows agreeing at 1.00 is overwhelming
evidence of a staff, a beam still covers one, and the narrow-cell alias is
untouched because it passes coverage on all five rows and is refused by width.

### Three gates, each earned by something that went wrong

| gate | value | what it refuses |
|---|--:|---|
| `CELL_LINE_MAX_SHIFT_SPACES` | 0.75 | a full-spacing alias — bounded **below** one spacing on purpose, which is what makes aliasing unreachable rather than merely unlikely |
| `CELL_LINE_MIN_ROW_COVERAGE` / `_MIN_ROWS_COVERED` | 0.45 / 4 of 5 | a cell with no staff-line comb under it — one strong row (a beam, a chord) is not a staff |
| `CELL_LINE_MIN_WIDTH_SPACES` | 4.0 | a cell too narrow to have horizontal evidence |
| `CELL_LINE_MIN_SHIFT_SPACES` | 0.05 | its own quantization — the comb is scored at integer page rows |

⚠️ **The width gate is not defensive tidying; it was found firing.** Run with
the shift bound deliberately raised past a spacing, every cell that then
answered beyond half a space was **2.2–3.7 staff spaces wide**, clustered within
a few percent of **±1.0 spacing**, at row coverage **1.00** — so the coherence
test cannot see it. It is the comb sliding a whole line: four of its five rows
still land on a printed line and in a narrow cell nothing else votes. Six of
them are Dvořák's brace cells, the system furniture
`benchmarks/omr-scan-e2e-2026-09/RESULTS.md` §1 measures at 2.2 spaces. With
the gate in, that page's largest offset falls **0.760 → 0.364**.

The positive side has the same margin: the seven cells whose displacement was
traced by hand are **9.03, 10.32, 12.23, 12.34, 16.18, 21.98 and 28.82 staff
spaces** wide, so the narrowest real case clears a 4.0-space gate by 2.25×.
Nothing in 3.7–9.0 spaces has been observed either way, which is a gap to sit
in rather than a threshold to tune.

⚠️ **The minimum-shift gate is what makes the engraved control provable.** On
the engraved Beethoven fixture — a LilyPond page straight by construction — 32
of 144 cells answered a non-zero shift and the largest was 0.024 spaces, which
is exactly **1 px** at that spacing. Sub-pixel noise, not signal. Refusing it
takes the engraved side to **0 of 291 cells moved**, so the flag-on run is
bit-identical to the flag-off run rather than merely close to it.

---

## 2. The A/B on the scan benchmark: 2 edits of 7894

Same tree, one variable, both arms transcribed and scored here — **not
differenced against the committed 0.7960**, which was measured on an older tree
(that tree's Dvořák row scored 0.5873; this one scores 0.4381, so differencing
across it would have attributed ~275 edits of other people's work to this
change).

| row | baseline | localized | Δ edits |
|---|--:|--:|--:|
| Beethoven 5 / 984073 | 0.6925 (1225) | 0.6894 (1221) | **−4** |
| Beethoven 5 / 575951 | 0.7660 (1375) | 0.7643 (1375) | 0 |
| Dvořák 9 | 0.4381 (680) | 0.4386 (682) | +2 |
| Brahms 1 | 0.9209 (3436) | 0.9209 (3436) | 0 |
| Mahler 5 | 0.7122 (1178) | 0.7122 (1178) | 0 |
| **pooled** | **0.7517 (7894)** | **0.7509 (7892)** | **−2** |

Three of the five rows do not move by a single edit. Category-level, only three
buckets move at all: `entire measure insert/delete` 2731 → 2734, `wrong keysig`
143 → 139, `wrong slur` 56 → 55. **Do not read those as a wash of real
effects** — at two net edits over 1143 cells of which five are past the flip
line, this is noise around zero, and the honest summary is "no measurable
change on this corpus."

⚠️ **The arm was re-measured after the gates were added and got SMALLER**, from
−4 edits to −2 (Mahler's −2 was a pre-gate sub-pixel move, and it was
noise: the gate that removed it is the one that makes the engraved side
provable). Both figures round to "nothing", which is the point — but the
committed number is the one the committed code produces.

---

## 3. Why: the benchmark reads the flattest pages in the book

This is the finding, and it is a fact about the corpus rather than about the
pipeline. Share of five-line cells whose grid sits **past the 0.25-space
parity-flip line** — the point where the nearest half-step slot becomes a
different slot, so every note in the cell can resolve one step off:

| corpus | pages | cells | past flip | share |
|---|--:|--:|--:|--:|
| scan e2e benchmark | 6 | 1143 | 5 | **0.4%** |
| pages the campaign flagged (control) | 6 | 1116 | 179 | **16.0%** |
| sampled deeper into the same editions | 26 | 4097 | 340 | **8.3%** |

**It is per-page, and adjacent pages disagree wildly** — which is what warp in a
bound scan looks like, and is why sampling page 1 is not sampling the domain:

| edition | page | share past flip |
|---|--:|--:|
| Brahms 1 / Breitkopf | **0** (the benchmark's row) | **0.0%** |
| Brahms 1 / Breitkopf | 1 | 14.4% |
| Beethoven 5 / Litolff 575951 | 5 | 18.2% |
| Beethoven 5 / Litolff 575951 | 17 | 16.6% |
| Beethoven 5 / Litolff 575951 | 31 | 0.0% |
| Mahler 1 / 1906 | 2 | 41.1% |

The benchmark's Brahms row is page 0 at 0.0%; the page **next to it** is 14.4%.
Nothing about the edition, the publisher or the print separates them — only
where the sheet sat when it was scanned.

---

## 4. The engraved control — identical to the edit, on all eleven works

LilyPond pages are straight, so this must be a no-op, and it is one **by
construction** before it is one by measurement: `_cell_line_offset` returns None
for all **291** five-line cells of the engraved fixtures, so `local_ys` takes
the identical code path it takes with the flag off.

`orchestral_eval --omr-ned` with `OMR_CELL_LINE_TRACE=1` then reproduces the
recorded figure exactly — **pooled 0.1306, 2745 edits over 10665 truth + 10361
predicted symbols**, against `current-accuracy.json`'s 0.13055264910111292 /
2745 / 10665 / 10361 — and every per-work row matches CLAUDE.md's table to the
edit: Mahler 5 0.0272/52, Tchaikovsky 4 0.0580/90, Beethoven 5 0.0595/77,
Bruckner 5 0.0941/187, Brahms 1 0.1196/494, Beethoven 3 0.1294/215, Mozart 41
0.1447/425, Mozart 40 0.1772/273, Tchaikovsky 6 0.1916/274, Brahms 4
0.2238/419, Dvořák 9 0.3380/239.

That is a stronger result than the control needed to be, and it happens to
settle a second question: the recorded figure was measured at `44a1745` and
nothing on main since has moved it.

⚠️ **No figure here is written into `current-accuracy.json` or CLAUDE.md's
`accuracy:begin` block.** This run is a control, not a measurement of the
pipeline, and `--record` was deliberately not passed.

---

## 5. What this says about designing the fix

- **The mechanism is settled.** A rigid comb, bounded below a spacing, with the
  three gates above, reproduces hand measurement on every case available and is
  a proven no-op on engraved input. It is behind `OMR_CELL_LINE_TRACE`
  (default off) and pinned by `tools/omr/tests/test_cell_line_localization.py`,
  including the flag-off contract.
- **⚠️ Do not ship it on the strength of the scan-benchmark A/B, in either
  direction.** −4 edits is not evidence for it and it is not evidence against
  it; that corpus has five affected cells. Shipping on a null result would be
  as unfounded as refusing on one.
- **The missing measurement is a scored page that actually tilts**, and the
  cheapest one is already half-built: **Beethoven 5 / Litolff 984073 p.5 or
  p.17** (18.2% and 16.6% past flip). That edition is *already* a benchmark row,
  so its reference, its protocol and its hand-read staff map exist — only the
  measure window has to be established, and `draft_windows.py` chains a window
  page by page from a verified base row of the same edition, which is exactly
  the situation. The benchmark's own rule stands: the window is input, verified
  by a probe that does not use the pipeline, or the pooled figure is withheld.
- **A second instrument needs no window at all.** The labeling campaign's
  inside-staff labels are human truth about the grid at a known point, on
  affected pages; §1's chain already uses them qualitatively (8 of 8), and
  scoring parity-agreement over all 225 would quantify the fix where it bites.
  The prior session's `audit_labels_vs_measured_grid.py` is the harness.
- **⚠️ A rigid comb has a ceiling, and one flagged cell is already at it.**
  FINDINGS §1 found the staff DISPLACED rather than distorted, which is what
  justifies a single offset, and that holds for the seven cells it traced. But
  `brahms1-p2-sys1-s20-m6`'s modeled rows are `[5506, 5533, 5555, 5588, 5616]`
  — gaps 27, 22, 33, 28 at spacing 27.5, irregular by up to 11 px. **That is a
  phase-1 defect underneath the tilt defect**: the five-row fit is itself
  distorted, so no rigid slide can put all five rows on the print, and the same
  bound applies to `refine_staff_lines_in_cell`'s single-offset shape. Four of
  five rows is enough to LOCATE such a staff, so it is not a blocker — and
  **measured, it is rare enough not to motivate the richer fix**. Over 93
  five-line staves on four warped pages of four editions, modeled row spacing
  is regular: irregularity (max deviation of a gap from the staff's mean gap,
  as a fraction of it) has median **0.037** and p90 **0.065**, seven staves
  (7.5%) exceed 0.10, exactly **one** exceeds 0.15 — and that one, at 0.200, is
  brahms1 s20 itself. So the per-cell *slope* or per-row fit FINDINGS §4
  floated would be buying a 1%-of-staves case that four-of-five already
  locates. Not worth it on this evidence; revisit if a publisher turns up whose
  staves fit irregularly as a rule.
- **`Staff.line_wander_px` is a usable per-staff flag but understates**, as
  FINDINGS §2 noted: it saturates near a third of a space because that is the
  trace window. `probe_library_tilt_population.py` records it per page beside
  the measured offsets, so its calibration can be read off rather than assumed.
### ⚠️ `recut_cells` — measured, and it needs neither of the two options on the table

`recut_cells.frame_mismatch` compares three things: `cell_canonical_w`,
`cell_canonical_h`, and `staff_line_ys_canonical`. Localization moves only the
third, so a batch cut before the flag would abort on re-cut after it — which is
why this was raised as a decision between *recording the localization mode per
batch* and *keeping the cutting frame unlocalized*.

**Measured on the worst page in the corpus** (Dvořák 9 p.8, 19.4% of cells past
the flip line), cutting it twice with the flag off and on:

| | identical |
|---|--:|
| cell image, byte for byte | **360 / 360** |
| `bbox_page_px` | 360 / 360 |
| `(width, height)` | 360 / 360 |
| `upscale_factor` | 360 / 360 |
| `staff_line_ys_canonical` | 133 / 360 (**227 differ**) |

So **the cutting frame is already unlocalized** — the second option is what the
implementation does, by construction: the crop bounds and the scale come from
`staff.line_ys` and `staff.span_px`, which localization never touches, and only
the stored grid moves. This is asserted by
`test_the_crop_and_the_span_are_unchanged_by_localizing`.

That makes the per-batch mode record unnecessary. **The narrow fix is for
`frame_mismatch` to compare the UNLOCALIZED grid** — the ys check is there to
say "this is the frame the boxes were drawn on", and the image the boxes were
drawn on is provably independent of the grid, so the check is currently reading
metadata as if it were frame. No batch needs re-cutting and no bookkeeping is
added. (`cell_canonical_h` already distinguishes the two padding modes that
check exists to derive, since a different pad is a different crop height.)

Existing verdicts stay valid either way — every saved box is in canonical image
coordinates and those are unchanged. What *does* change is the labeling UI's
snap suggestion, which reads the grid, and that is the point: it is the defect
FINDINGS §3 traced two shipped wrong labels to. Snap behaviour itself is
untouched and stays pinned by `test_ledger_snap.py` — the geometry moved, not
the snapping.

### One trap, recorded because it silently emptied a test

⚠️ **The localization reads `page.binary` and the header refiner reads
`cell.image`.** A synthetic fixture that inks only the binary makes
`refine_staff_lines_in_cell` see blank paper and return 0 — which is
indistinguishable from "the refiner agrees with localization", and is really
"the refiner was handed nothing." The first version of the composition test in
`test_cell_line_localization.py` passed its flag-on arm and was vacuous on its
flag-off arm for exactly that reason. `_page` now derives the RGB from the
binary, and the invariant it was written to pin does hold: the two compose
without double-correcting, because the refiner scores absolute ink at the rows
the cell currently carries rather than a delta from the staff-level model.

---

## 6. Files

| file | what |
|---|---|
| `probe_localization.py` / `.json` | the comb fit against FINDINGS §1's hand-traced residuals |
| `probe_scan_corpus_offsets.py` / `.json` | per-cell offsets over the scan benchmark's own pages |
| `probe_library_tilt_population.py` / `.json` | the population question: 6 control + 26 sampled pages |
| `results-baseline.json` | the A/B's baseline arm, measured on this tree |
| `results-localized.json` | the A/B's localized arm, same tree |
