# omr-bar-number-2026-09 — ROADMAP 2.13

PATH: STAGED. Read the PRINTED bar number off the plate (the small numeral
engravers print above a system's first bar) and file it, so the file's own
cumulative bar count has a second witness. Branch `claude/bar-number-2.13`
off `origin/main` `ae776515`.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (rule 3: nobody
was asked before code — no reply window in this lane): a printed bar number
sits above the SYSTEM's topmost staff, near its start, and is never confused
with a rehearsal letter printed in the same place on some editions. Section 1
below measures where, on the two gate pages; it has not been asked of Sean.

## 0. What was built

- GATHER (`tools/omr/staged/gather.py:gather_printed_bar_numbers`,
  `tools/omr/bar_number_text.py`): one crop per SYSTEM, directly above its
  topmost staff, OCRed with Tesseract only — a bar number is 1-4 ASCII
  digits, which is exactly Tesseract's digit-whitelist mode, and needs
  neither a Python 3.10 venv nor the Surya server. `--no-surya` is untouched
  by this reader; there is nothing in it to fall back from. Filed as
  `Q.PRINTED_BAR_NUMBER` (new quantity, `record.py`), an Observation with the
  raw OCR text plus its page-pixel box, or an Abstention with one of the same
  four states `gather_direction_words` already declares for its own OCR rung
  (`READER_UNAVAILABLE` / `NO_STAFF_GEOMETRY` / `NO_INK` / an Observation).
- ADJUDICATE (`tools/omr/staged/adjudicators/text.py:
  adjudicate_printed_bar_number`): interprets the raw text as an integer —
  "what does this ONE thing mean, on what evidence" — reusing the same `Q`
  name for the Verdict that `Q.MOVEMENT_SPANS` already reuses across GATHER
  and ADJUDICATE. Decides `read` (exactly one run of digits, 1..9999),
  abstains `not_numeric` (a rehearsal letter, or noise) or `no_reading` (no
  rung ran), or NARROWS `ambiguous_multiple_readings` if two readings of one
  system ever disagree. Never renumbers or inserts a bar — it names only
  what the numeral itself says.
- EXPORT (`tools/omr/staged/export.py:_printed_bar_number_check`, hung off
  the existing `measure_numbering` report at the exact point
  `_document_bar_offsets` returns): per system, the ADJUDICATED numeral
  against `offset + 1` (the file's own 1-based number for that system's
  first bar, off the SAME tally `_document_bar_offsets` already computes).
  Three states — `agree` / `disagree` (+signed `delta`) / `abstained` (named
  reason) — reported under `measure_numbering["printed_bar_check"]`, written
  even where every system abstains. Never renumbers, never writes into
  `offsets`/`numbering` itself (asserted by
  `test_it_never_writes_a_number_into_the_numbering_it_checks`), and honours
  the WHOLE-FILE refusal `_document_bar_offsets` already makes: if the
  document-wide count itself is undetermined (`scheme != "document"`), every
  system abstains `document_numbering_undetermined` rather than comparing
  the ones that happen to precede the break.

Registered in `adjudicate.ORDER` (reads GATHER only, depends on nothing,
placed beside `Q.DIRECTION`/`Q.DYNAMIC`). `record.CLAIMS["PRINTED_BAR_NUMBER"]
= CLAIM.IDENTIFICATION` (an OCR reading, same nature as `DIRECTION_WORD`).

## 1. Where the numeral actually sits — measured, and the first guess was wrong

The build's first geometry (0.4-3.0 staff spaces above the top staff line)
clipped the numeral's own TOP on both gate pages: Litolff read blank / "9"
where the plate prints 49 / 65 (only each digit's bottom half survived the
crop). Rendering both pages with a ruler overlay found the numeral at
0.8-6.2 staff spaces above the top staff's own top line, consistently on
both editions despite very different absolute staff-space sizes (15.5 px
@600dpi Litolff, 27.25 px Brahms) — a fixed pixel margin would not have
generalised, a spaces-relative one does. The x-range (`x_start` to
`x_start + 6` staff spaces — `x_start` already sits past the clef/key/meter
margin) needed no correction; the numeral is squarely inside it on both
plates.

FALSIFIER, NOT CONFIRMED BEYOND THESE TWO PAGES: a plate that boxes the
number above the barline rather than the margin, or prints it further from
the top line than this band, is missed by this crop and reads `NO_INK`
(never a wrong number — CLAUDE.md rule 8).

## 2. The upscale that made things WORSE, and the sweep that replaced a guess

The first draft copied `staff_labels_tesseract`'s own 3x/LANCZOS upscale.
Tested against a `pdf2image` (poppler) stand-in render it looked fine;
tested against the REAL pipeline raster (`preprocessing.render_page`,
PyMuPDF/fitz, not poppler — the two renderers are not pixel-identical at
this scale) it read only 2 of the 4 gate numerals, worse than reading the
crop at its native size. A swept grid — {1,2,3,4,5} x {LANCZOS, BICUBIC,
NEAREST} — over the four real crops found no configuration that reads all
four: Brahms p2's second numeral ("15") never resolves under any tested
preprocessing; Tesseract reads it as "4", "45", or nothing depending on
scale and filter, never "15", though it is unambiguous to a human eye (see
the crop). `UPSCALE = 1` (no resize at all) reads 3 of 4 and is the cheapest
config that does — it is the shipped default, in `tools/omr/bar_number_text.
py`. This is left as a MEASURED Tesseract limitation and reported, not
patched around with a heavier preprocessing guess that the sweep already
falsified.

## 3. The two gate pages, read against the plate

| document | system | printed (Sean's own convention row) | this reader read | crop |
|---|---|---|---|---|
| Litolff Beethoven 5, pdf index 3 | 0 | 49 | 49 -- DECIDED | litolff_984073_p3_sys0.png |
| Litolff Beethoven 5, pdf index 3 | 1 | 65 | 65 -- DECIDED | litolff_984073_p3_sys1.png |
| Breitkopf Brahms 1, pdf index 1 | 0 | 8  | 8 -- DECIDED | brahms_317803_p1_sys0.png |
| Breitkopf Brahms 1, pdf index 1 | 1 | 15 | ABSTAINED (no_reading) -- see section 2 | brahms_317803_p1_sys1.png |

3 of 4 read exactly right; the fourth abstains rather than guessing "4" or
"45" — the failure mode CLAUDE.md rule 8 asks for. All four crops (plus the
manifest) are under `out/print/`, `VERDICT_none_yet: null` — Sean has not
looked yet.

## 4. The export-time comparison, and why both Litolff systems "disagree"

Run on a single-page gather (`--pages 3`, per this item's own proof budget —
no whole-work run, per Sean's 2026-09-28 instruction), the file's own
cumulative bar count necessarily starts at bar 1 for that page's first
system, because pages 0-2 were never gathered. So
`measure_numbering["printed_bar_check"]` reports BOTH Litolff systems as
`disagree`, delta +48 on each — a constant offset, which is the signature of
"the document wasn't gathered from its own start", not of a per-system
reading error. This is NOT the dropped-barline defect the roadmap row itself
names ("the viewer shows 48 where the plate prints 49") — that comparison
only means something once pages 0-3 are gathered together as one document,
which is a whole-movement run this lane deliberately did not make. What IS
established: the mechanism computes the right numbers (49 vs file-number 1,
65 vs file-number 17 — both exactly 48 apart, both derived correctly from
`_document_bar_offsets`'s own tally) and reports them as a disagreement
rather than silently accepting or hiding the mismatch — the comparison is
wired correctly; pricing it against the KNOWN defect is a whole-work-run
question, out of THIS lane's proof budget.

On Brahms, system 0 abstains `document_numbering_undetermined` (the
whole-file numbering itself is undetermined on this single isolated page —
a pre-existing `_document_bar_offsets` behaviour, not something this lane
changed) and system 1 abstains on its own `no_reading` (sections 2/3). Both
are exercised by `TestPrintedBarNumberCheck` on synthetic input, including
the "never mutates what it reads" and "a whole-file refusal is never
partially compared" cases.

## 5. Tests and the derived check

- `tools/omr/tests/test_staged_printed_bar_number.py` — new, RED before the
  gather/adjudicate/export functions existed. Covers: digit-parsing
  (rehearsal letter refused, two digit runs refused as a guess CLAUDE.md
  rule 6 forbids, punctuation tolerated, the GATHER-side and ADJUDICATE-side
  copies of the parser asserted equal so they cannot drift); GATHER's four
  states (`READER_UNAVAILABLE`, `NO_STAFF_GEOMETRY`, `NO_INK`, an
  Observation), one row per SYSTEM never per staff; ADJUDICATE's four
  outcomes (`read`, `not_numeric`, `no_reading`, `ambiguous_multiple_readings`
  NARROWED); the EXPORT check's four states plus "never mutates the
  numbering it reads".
- One regression found and fixed while wiring the call into `gather()`:
  `test_staged_pipeline.py`'s `FakeStaff` fixture has `.line_ys` but no
  `.line_spacing_px` property (only the real `types.Staff` dataclass has
  it), so the new function's geometry read raised `AttributeError` on 17
  unrelated pipeline tests the moment it was wired in. Fixed by reusing
  `gather.py`'s own `_spacing()` helper (the same one `gather_geometry`
  uses), which both the fixture and the real dataclass can answer — not a
  new helper, not a fixture change.
- `pytest tools/omr/tests -m "not slow" -q`: full fast tier green (no
  regressions beyond the one found and fixed above).
- `python3 -m tools.omr.staged.check`: TOTAL 249, unchanged from
  `origin/main` `ae776515` alone (measured directly: stashed this lane's
  changes, ran `check` on the bare base commit, got 249, restored).
  `staged.wiring` briefly went to `broken` (2 new unaccounted DETAIL
  findings: `crop_box`, a redundant copy of `bbox_page_px` this lane removed
  rather than registered, and `page_staff_index`, which this lane removed
  entirely rather than adding a third `KNOWN_GAPS` copy of the existing
  `Q.STAFF_LINES.page_staff_index` reason) — both closed by REMOVING the
  unread detail key rather than by growing `KNOWN_GAPS`, so this lane adds
  zero net findings.

## 6. What was not done

- No whole-movement / whole-work run (Sean, 2026-09-28: no export runs yet
  this lane; the proof budget asked for one page each).
- No fix attempted for the Brahms "15" misread beyond the sweep in section 2
  — it is reported as a measured limitation, not patched around.
- The export-time comparison is not priced against the KNOWN Litolff
  dropped-barline defect (roadmap row's own "48 vs 49") — that needs pages
  0-3 gathered as one document, which this lane's proof budget excludes.
- No adjudicator-level CHECKABLE declaration for this quantity (it stays
  `Checkable.UNCHECKABLE`, `composed_from=(Q.PRINTED_BAR_NUMBER,)`): the real
  check — comparing against the file's own count — needs the document-wide
  join, which does not exist until EXPORT, so it is a report there
  (`_printed_bar_number_check`) rather than a `checked_by`/`implicates` pair
  on the ADJUDICATE decision. See that function's own docstring.

## 7. 2.13b (2026-10-11): the whole-movement census, and the Surya rung

STAGED. Raw data under `census-2026-10-11/`. The crops for Sean are in
`out/print/2.13b-bar-number/`.

### 7.1 The census: every 2.13 read on both acceptance movements

- **Records:** `*-mvt1-whole-20261010-night.record.json` (main `26fdb4d0`, clean tree). Brahms has 53 systems (p0-26), Litolff 31 (p1-16).
- **Frame control:** each system's crop was re-cut from its recorded `bbox_page_px` off `preprocessing.render_page` at 600 dpi. Tesseract re-read every crop exactly as the record says: 84 of 84.
- **Plate reading:** `plate_reading.json`, first read by me off each crop with its neighbours. **Sean confirmed all 84 tiles on 2026-10-11** (*"all of those tiles are correct and match the bar numbers"*), so it is print truth for this item. The numbers run in sequence, and each step matches a plausible system length.

Tesseract against the plate (decided verdicts):

| | right | WRONG | abstained on a printed numeral | spurious (nothing printed) |
|---|---|---|---|---|
| Brahms (52 numerals) | 13 | **22** | 16 | 0 |
| Litolff (28 numerals) | 21 | 5 | 2 | 2 |

**The "1 read as 4" is one of three causes on Breitkopf.**

1. **Bold "1" read as "4":** 149→449, 179→479, 188→488, 194→494, 421→424.
2. **A leading "1" lost into the bracket's curl:** 106→6, 124→24, 170→10. The curl sits at the crop's lower left.
3. **The crop clips the third digit.** On Breitkopf a 3-digit numeral ends about 7 staff spaces right of `x_start`, but the crop stops at 6. Results: 343→8, 351→5, 371→3, 434→3, 492→"493".

The 2.85 FINDINGS §5 table used Tesseract's reading as "printed" at 26/0. The plate prints **492**, not 493. Its "0" delta there is really −1, the same −1 it attributes to 2.86 on every other row after p13.

**Geometry misses (not a reader fault):** Brahms 7/0 and Litolff 4/0 and 14/0. On these systems the "topmost staff" is not the system's top staff, so the crop lands on notes and the numeral is outside it. Litolff 14/0's notes read "4". These are left to the staff detector.

### 7.2 Surya on the same crops, and the width

The arms were run on the same raster, as an offline grid: 3 widths × 2 upscales, plus 3 checks on token cap and padding. Surya is deterministic here: two identical runs gave identical text. At 60 px white padding and 16 tokens:

| arm | Brahms right / wrong / abstain | Litolff right / wrong / abstain / spurious |
|---|---|---|
| Tesseract, 6 spaces (shipped) | 13 / 22 / 16 | 21 / 5 / 2 / 2 |
| Tesseract, 7 spaces | 19 / 10 / 22 | 17 / 6 / 5 / 1 |
| Tesseract, 8 spaces | 16 / 14 / 21 | 16 / 5 / 7 / 1 |
| Surya 2x, 6 spaces | 23 / 2 / 26 | 23 / 0 / 5 / 0 |
| Surya 3x, 6 spaces | 25 / 3 / 23 | 24 / 0 / 4 / 0 |
| Surya 2x, 7 spaces | 30 / 1 / 20 | 26 / 0 / 2 / 0 |
| **Surya 2x, 8 spaces** | **34 / 0 / 17** | **27 / 0 / 1 / 0** |
| Surya 3x, 8 spaces | 24 / 2 / 25 | 26 / 0 / 2 / 0 |

- **Width:** every wrong Surya read at 6 or 7 spaces is a clipped numeral (263→26, 434→43, 303→30) or the bracket curl read as "7". So 8 spaces is the width the clipping argues for, not just the best cell.
- **Tuning caveat:** the grid was scored on the same 80 numerals it was chosen on. A third plate is where it could fail.
- **Remaining failure at 8 spaces:** a stray stroke next to the numeral ("179 1", "413 1"). That gives two digit runs, which `bar_number_from_text` already refuses, so it abstains and never becomes a wrong number.
- **Token cap:** 32 tokens read no more than 16. 1x upscale read fewer.

**No cascade, on measurement.** Where Surya at 8 spaces was silent, Tesseract on the same systems was **5 right / 7 wrong** (Brahms 4/5, Litolff 1/2). Filling those gaps with Tesseract would turn "cannot tell" into wrong numbers (rule 8). So Tesseract is the `--no-surya` / Surya-unavailable reader only.

### 7.3 What was built

- **`bar_number_text`:**
  - `surya_available()`
  - `read_crops_surya()`: 60 px white pad, 2x INTER_CUBIC, 16 tokens, one Surya job per page.
  - Constants: `SURYA_CROP_WIDTH_SPACES = 8.0`, `SURYA_PAD_PX`, `SURYA_UPSCALE`, `SURYA_MAX_TOKENS`.
- **`gather.gather_printed_bar_numbers(log, pws, surya=False)`:** when `surya` is set, the new `_printed_bar_numbers_surya` runs.
  - Every system gets exactly one `READERS.SURYA` row: an Observation (`score=None`, because Surya gives no confidence), `NO_INK`, or `NO_STAFF_GEOMETRY`.
  - If Surya is not installed or raises, each system gets a `READER_UNAVAILABLE` row under `READERS.SURYA`, and then the Tesseract rung runs unchanged.
- **`gather()`:** passes `surya=surya_fallback`, so the run's `--no-surya` governs it. There is no new flag.
- **Unchanged:** ADJUDICATE and EXPORT. The 2.85 files and the stem/flag/ledger/articulation code were not touched.

**Real-function proof, both movements, every system.** The shipped `gather_printed_bar_numbers` was run on the real raster, with staff geometry taken from each record's own `Q.STAFF_LINES` and `Q.STAFF_EXTENT`, then through `adjudicate.run` (`arm.py`, `arms_real_function.json`).

- **Control (`surya=False`):** matches the overnight record's rows **and** verdicts exactly, 84 of 84.
- **Surya arm:**
  - Brahms: **32 right / 0 wrong / 19 abstained**.
  - Litolff: **27 right / 0 wrong / 1 abstained / 0 spurious**.
  - The sweep's 34 differs from 32 because the shipped code measures the staff space from the line positions, not from the band height.

### 7.4 Against `measure_numbering.printed_bar_check`

Only the `printed_bar_number` verdicts in each overnight record were swapped for the arm's, then the record was exported (`pricecheck.py`). The exporter reads nothing else of this quantity, so this is equivalent to re-gathering it.

| | agree | disagree | abstained |
|---|---|---|---|
| Brahms base → arm | 7 → 8 | 28 → 24 | 18 → 21 |
| Litolff base → arm | 8 → 9 | 20 → 18 | 3 → 4 |

The counts barely move, and that is correct: the disagreements that remain are the FILE's. What changed is that every delta is now a clean step:

- **Brahms:**
  - 0 through system 10/1 (bar 188).
  - **−2 from 11/0 (194)**: the 1st/2nd ending, which 2.85 fixes.
  - **−3 from 12/0 (215)**: the courtesy key signature counted as a bar, 2.86.
- **Litolff:**
  - 0 through 6/1 (158).
  - **−1 from 7/0 (171)**.
  - **−2 from 15/0 (430)**.
  - These are two places where the file loses a bar. Each is now located to one system boundary. They are not chased here.

On the base side the Tesseract misreads made the deltas noise (−40, +300, −277…). They also produced two FALSE agrees: Brahms 22/1 "424" and 26/0 "493".

### 7.5 Not done

- Sean confirmed every tile in `out/print/2.13b-bar-number/*.png` (2026-10-11). The right/wrong counts in 7.1-7.3 therefore stand against print truth.
- Not done: the three geometry misses, a third plate, and an overnight re-gather.
- Brahms's 19 abstentions are clear numerals Surya returned empty on (8, 15, 29, 38, 48, 79, 87, 97, 161, 179, 188, 239, 251, 324, 330, 336, 362, 444, and 115, which is outside the box). That is coverage left on the table, not error.
