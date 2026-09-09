# A meter change on a page that READS WELL — the measurement two mechanisms could not be told apart without

**The ranked task 1 of
[docs/handoff-2026-09-09-bars-name-a-length.md](../../docs/handoff-2026-09-09-bars-name-a-length.md)
§5**, and it is answered. It also found a live *detected-then-dropped* hole in
the meter path, which is fixed here with tests.

## 0. The question, and why it was blocking

Two shipped-but-default-off mechanisms both act where a system reads no meter:

* **`OMR_METER_CARRY`** hands it the last meter that was **READ**, as a
  candidate its own bars then confirm or refuse;
* **`OMR_METER_FROM_BARS`** lets its own bars name a **LENGTH**, and borrows
  the spelling from a system that read one of that length.

Everything measured about either rested on Beethoven 5 / Litolff `984073`, a
scan. On that document the only movement boundary is page 17, whose bars are
noise — so the carry's refusal there is **SAFE but NOT DISCRIMINATING**: scored
against `3/8`, the meter that page actually PRINTS, it refuses that too. A
mechanism that refuses everything is indistinguishable from a mechanism that
refuses the wrong thing, and the two mechanisms were indistinguishable from
each other.

`benchmarks/omr-staged-meter-carry-2026-09/FINDINGS.md` §11 named the route out
and it was unspent: **render a real meter change ENGRAVED**, so reading quality
is not the confound.

## 1. The fixture — a real meter change, rendered

`beethoven-sym5-mvt4` encodes **4/4 → 3/4 at bar 155 → 4/4 at bar 209**. Two
excerpts are rendered through `musicxml2ly` + LilyPond at 23 parts on a3
(`render_boundary.py`, reusing `orchestral_eval`'s paper sizing and its
`_apply_indent_override`, but **not** its shrink-to-one-page loop — this
fixture wants several systems):

| fixture | measures | pages | what each page prints |
|---|---|--:|---|
| `boundary-m150-180` | 150-180 | 4 | p0 `C` (4/4) · p1 the fermata bar · **p2 `3/4` at the change** · **p3 m172+, 3/4, NO meter printed** |
| `boundary-m204-232` | 204-232 | 6 | p0 `3/4` · **p1 the change to `C` mid-system** · **p2 m215+, 4/4, NO meter printed** |

⚠️ **THE STRUCTURE IS AN ENGRAVING CONVENTION, NOT AN ABLATION.** An engraver
— and LilyPond — prints a time signature at the CHANGE and at nothing after
it. So a system lying wholly inside the new meter prints no meter, abstains
honestly, and is exactly the system both mechanisms exist for. Nothing was
suppressed to produce it.

Weights: `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` — the engraved-routing
target. The staged CLI does no weight routing, so the choice is made in
`run_arms.py` and recorded there.

## 2. ⚠️⚠️ THE RESULT: the bars DISCRIMINATE, by 14.0 in the carry's own currency

`boundary-m150-180` page 3 (m172+, 3/4, no meter printed), asked twice. The two
runs differ **only in which earlier page is in the window**, so the candidate
offered differs and the page itself does not:

| window | candidate offered | bars | support | outcome |
|---|---|---|--:|---|
| `--pages 0-3` | **3/4** (from p2, the true meter) | 7 fit / 2 not | **+6.0** | **`carried` 3/4 — CORRECT** |
| `--pages 0,3` | **4/4** (from p0's `C`, across the boundary) | 0 fit / 9 not | **−8.0** | **`carry_outweighed_by_the_bars` — REFUSED** |

`--pages 2,3` reproduces the first row to the unit (+6.0, 7/2), so the swing is
the candidate's and not the window's.

✅ **RE-MEASURED TWICE ON MERGED TREES AND IDENTICAL BOTH TIMES** — the second
time after a SIBLING session's `_meter_fallbacks` landed on main, which reorders
what a REFUSED carry does and is therefore the branch two of these fixtures sit
on. ⚠️ **That merge also gave this benchmark a cross-session corroboration it
did not set out to produce**: with both flags on, `--pages 0,3` used to abstain
`carry_outweighed_by_the_bars` — the bar reader unreachable behind the refusal
it had caused — and now reports `bars_name_a_length_without_a_form` at +5.0
with the truth in its shortlist. Their fix, measured on a page they never ran. `origin/main` moved 27+
commits under this branch while these arms ran, including **221 changed lines
of `staged/adjudicators/rhythm.py` and 404 of `staged/gather.py`** — and
`gather.py` is where the `Q.EVENT` / `Q.DURATION` rows these decisions read
come from. Every arm was re-run after merging rather than assumed to survive
it (`m2*` runs): the +6.0 / −8.0 pair, the same `bar_lengths_seen`, the same
reasons, the same §4b tally to the row, and the `C`-change fix still reading
23 staves of 23 at support 66.0.

**That is the measurement that was missing.** On the *Andante* the true meter
scored −1.0 and the false one −1.0; here the true one scores +6.0 and the false
one −8.0, on the same nine bars.

**And `OMR_METER_FROM_BARS` reaches the same page independently:**

| window | what the bars name | outcome |
|---|---|---|
| `--pages 0-3` | length **3.0**, support **+5.0** (7+/2−) | **`derived_from_bars` 3/4**, form borrowed from p2 |
| `--pages 0,3` | length **3.0**, support **+5.0** | `bars_name_a_length_without_a_form`, forms **`['3/4','6/8','12/16']`** |

The truth is in the shortlist. The +6.0 / +5.0 gap is exactly `W_METER_CARRIED`
= 1.0, as it should be — the same bars, one mechanism carrying a prior reading
as an extra term.

### What it is worth in the FILE

Exported from the saved records with `export_arms.py` (no re-transcription, so
the export cannot disagree with the arm that was measured). 23 continuous
parts, `--pages 0-3`:

| | OFF | CARRY | BARS |
|---|--:|--:|--:|
| whole rests written at **4.0 ql inside a 3.0 ql bar** | **196** | **38** | **38** |
| proper measure rests (`measure="yes"`, no `<type>`, 3.0 ql) | 305 | **463** | **463** |
| quarter rests / half rests | 236 / 1 | 236 / 1 | 236 / 1 |

⚠️ **The CARRY and BARS exports are BYTE-IDENTICAL.** Two mechanisms with
different reach reach the same file on this page.

⚠️ **All 38 residual whole rests are in bars holding MORE than one note**
(21 under a known 3/4, 17 under a known 4/4). `size_measure_rest` refuses a
whole rest standing beside other events, deliberately — so zero lone whole
rests in a known meter were left mis-sized. Whether those 38 are misreads is a
different question and nothing here claims they are not.

### And the same fact seen from the durations

⚠️⚠️ **A DURATION-LEVEL A/B ACROSS METER ARMS IS INVALID BY CONSTRUCTION, and
reaching for one first is the trap.** A decided meter is CONSUMED —
`size_measure_rest` and `reconcile_duration` rewrite durations from it. Page 3,
carry off vs on: **159 of 314 duration verdicts differ** — 157 whole rests
re-sized 4.0 → 3.0 as `whole_rest_means_the_bar`, plus **2 notes re-read by
`meter_reconciliation`**. That is the fix working.

So the valid cross-arm control is **`bar_lengths_seen`**, which
`adjudicate_meter` writes from the durations as they stood BEFORE any
consequence ran. It is `{'3.0': 7, '5.0': 2}` in every arm and every window
that reaches page 3 (`report_boundary.py --control bars`), and the raw duration
verdicts are identical between arms whose meter outcome is the same
(`--control durations`, 314 vs 314).

## 3. ⚠️ WHAT IS *NOT* ESTABLISHED

* ✅ **NO LONGER ONE DOCUMENT — §4b adds Brahms 1 (two movements) and the
  Breitkopf scan of one of them.** The result splits: it holds on a second
  ENGRAVED document and does NOT hold on a second publisher's SCAN. Read §4b
  before quoting §2 as a general result.
* **n is four systems.** Two exercise the deciding branch, two the abstaining
  one; the discrimination result rests on ONE page asked twice.
* **The `--pages 0,3` adjacency is a page WINDOW.** It is a real use of the
  CLI and the reverse fixture supplies an unmanufactured wrong carry (§4), but
  in the natural `--pages 0-3` run the carry was right anyway. Both are
  reported.
* ⚠️ **`METER_CARRY_MIN_BARS = 2` REFUSED A CORRECT CARRY HERE, and this is the
  first time that constant's COST has been observed rather than only its
  benefit.** `boundary-m150-180` page 1 is a single bar (m154, the fermata),
  its truth is 4/4, its one assessable bar reads 4.0 — and the carry declines
  `carry_not_corroborated` because one bar is not a system's worth of
  evidence. The guard is doing what it was written to do; the price is now
  measured and it is not zero.
* **The bars are not independent witnesses** (`A-DUR-6`). Unchanged from the
  last handoff and still unmeasured.

## 4. ⚠️⚠️ THE REVERSE BOUNDARY — and the hole it opened

`boundary-m204-232`, `--pages 0-2`, carry on. Here the wrong carry arrives with
no page window at all, because the intervening system reads `change_only`
rather than `voted` and so is not a carry source:

| system | truth | candidate | bars | support | outcome |
|---|---|---|---|--:|---|
| `system/0/0` m204+ | 3/4 | — | — | — | `voted` **3/4** ✓ |
| `system/1/0` m206+ | 3/4 → 4/4 | 3/4 | 0 / 7 | **−6.0** | refused |
| `system/2/0` m215+ | **4/4** | **3/4 (wrong)** | 0 / 2 | **−1.0** | **refused** ✓ |

The wrong carry is refused, unmanufactured. But **on a barely-adequate basis**:
only **2 of 6 bars** on that page were assessable at all, and one of the two
read 4.5. `OMR_METER_FROM_BARS` produces nothing there (`no_evidence`): two
bars at 4.5 and 4.0 tie, and the tie scores 0 against a floor of 4.0.

### ⚠️ Bar assessability falls with DENSITY, not with print quality

Every system these mechanisms were asked about, on clean engraving:

| system | bars | assessable | events per bar | lengths read |
|---|--:|--:|--:|---|
| fwd `system/1/0` m154 | 1 | 1 (100%) | 1.0 | `{4.0: 1}` ✓ |
| fwd `system/3/0` m172+ | 9 | 9 (100%) | 1.5 | `{3.0: 7, 5.0: 2}` |
| rev `system/1/0` m206+ | 9 | 7 (78%) | 3.1 | `{3.5: 3, 2.0: 2, 4.0: 1, 6.0: 1}` |
| rev `system/2/0` m215+ | 6 | **2 (33%)** | 4.5 | `{4.5: 1, 4.0: 1}` |

Monotone over these four, and it inverts the intuition that more staves
playing means more evidence: a dense bar needs every one of its durations right
to sum, so **the bar-sum mechanisms are strongest exactly where the music is
sparse** — which is also where `size_measure_rest`'s payoff is largest. ⚠️ n =
4 systems on one document; suggestive, not established. `rev system/1/0`
legitimately holds two meters, so its 7 "assessable" bars have no single right
answer.

### ⚠️⚠️ A METER CHANGE PRINTED AS A `C` WAS DETECTED AND DROPPED

`rev system/1/0` should have proposed the change to 4/4 at its bar 3. It
proposed nothing — and the reason is not evidence:

```
meter_glyph  page 1  timeSigCommon  ×23     # every staff of the system
meter_template page 1                       # nothing
```

**Detected on 23 staves of 23, unanimous, maximal agreement, and no candidate
was formed.** `_meter_from_digits` requires two stacked digits and says so in
its own comment — *"timeSigCommon and friends: no pair"* — so `readings` came
back empty and `_meter_changes` skipped the bar. `4/4` and `C` are one bar
length and two engravings, which `adjudicate_meter`'s own docstring insists on,
and the change reader could read only one of them.

⚠️ **`Q.METER_GLYPH` already carries `letter=True/False`, written by GATHER and
read by NOTHING** — the "value existed and nothing read it" pattern again,
inside the meter. It cannot be the input either: a boolean cannot tell a `C`
from a `¢`, and those are different meters. The class NAME is the evidence.

⚠️ **The change detector had NO unit tests at all.** `grep -c METER_GLYPH
tools/omr/tests/*.py` returned zero across the suite while `_meter_changes`,
`_change_only` and the whole `segments` mechanism were shipping default-on.

**FIXED** (`rhythm._meter_from_letter`, no flag — it adds a reading where there
was none):

* digits first, the letter only after, so a bar printing digits is never
  re-read as a letter by a stray detection;
* the reading key carries the printed FORM, so `C` and `4/4` are counted apart
  exactly as `adjudicate_meter` demands;
* it earns `W_CHANGE_GLYPH_PAIR`, not `W_CHANGE_GLYPH_LOOSE` — that constant
  is worth what it is because the staff read a COMPLETE meter, and a letter
  meter is complete in one glyph;
* a staff carrying BOTH a `timeSigCommon` and a `timeSigCutCommon` at one bar
  abstains: contradictory ink is loose ink;
* ⚠️ **`raw` travels here, and that is the OPPOSITE of the borrowing rule.**
  `_form_for_length` refuses to copy a letter because the borrowing system
  printed nothing we could read; this system's own staves read the `C`, so
  `symbol="common"` reaching the file is a claim the page supports.

### What the fix does, measured on all four pages that could reach it

| run | before | after |
|---|---|---|
| `boundary-m204-232` p1 (23 staves print the `C` at m209) | `no_evidence` | **`change_only`, `C` at cell 3 — the exact bar, 23/23 staves, support 66.0** |
| `boundary-m150-180`, all 4 pages | — | **identical** (no letter stands at a non-zero cell) |
| Litolff `984073` `--pages 0-2` | — | **identical on every subject, outcome, reason and value** |
| Litolff `984073` `--pages 61-62` | p62 `change_only` `3/4` @ cell 8 | p62 **unchanged**; p61 **NEW** `change_only` `C` @ cell 3 |

The previous session's headline — the printed `3/4` found on the exact bar the
reference names — is preserved to the unit.

⚠️⚠️ **AND THE NEW p61 SEGMENT IS A FALSE POSITIVE. Reported, not smoothed
over.** Litolff p.61 prints bar 140 and **no time signature anywhere** (the
page was rendered and looked at). The segment comes from ONE `timeSigCommon`
detection on one staff of seventeen at confidence **0.377**. It names 4/4,
which IS the meter of those bars, so the record got better here — but by
accident of which meter the false glyph named.

⚠️ **The hazard is `METER_CHANGE_FLOOR`, not the letter path, and the previous
session's headline rests on the same property.** One staff reading a complete
meter clears the floor by design (*"a printed time signature IS the biggest
sign"*), and p.62's celebrated `3/4` is **also one staff of seventeen** at
support 3.0. What the letter path adds is that a letter is **cheaper to fake
than a digit pair** — one glyph, against two detections that must separate into
two heights. That asymmetry is real, the constants do not express it, and
nothing in this corpus can price it.

⚠️ **The bars refused the OTHER false letter, which is the layering working.**
Litolff `--pages 0-2` also carries two `timeSigCommon` detections (0.454, 0.560)
— both on ONE staff, at cell 4 of a system that VOTED `2/4`. Its own bars
contradict a 4/4 from cell 4 onward and sink it under the floor; the export is
unchanged. p.61 escaped only because its system's opening is unknown and its
bars offer 1 fit and 0 contradictions. *The glyph opens the question and the
math settles it* — where there is math.

**Confidence separates these cleanly and is deliberately NOT gated on:**

| | n | min | median | max |
|---|--:|--:|--:|--:|
| engraved, real (`boundary-m204-232` p1, cell 3) | 23 | 0.887 | 0.908 | 0.920 |
| engraved, real (`boundary-m150-180` p0, cell 0) | 23 | 0.899 | 0.921 | 0.927 |
| Litolff scan, false (p1 cell 4) | 2 | 0.454 | 0.507 | 0.560 |
| Litolff scan, false (p61 cell 3) | 1 | 0.377 | 0.377 | 0.377 |

`Q.METER_GLYPH` already carries `score` and nothing reads it. A gate here would
be a threshold fitted to four rows on two documents, which is what this
repository refuses; it is recorded as an observation for a corpus that could
price it.

`TestAMeterChangeIsReadFromTheInk` (10 tests) pins it, and **eight mutation
arms were run** — remove the letter fallback (8 red), remove the digit path,
accept ambiguous letters, admit cell 0, admit a restatement, force `raw` to
digits, downgrade the weight, map `¢` to 4/4 — each turns a test red. ⚠️ The
three *refusal* tests carry their positive control INSIDE the test, because
without it each passes for free the moment the letter path stops working at
all.

## 4b. ⚠️⚠️ A SECOND DOCUMENT AND PUBLISHER — and the answer splits

§3's top open item, done. Two more works, and the decisive one is a **pair**:
`brahms-sym1-mvt1` prints `6/8`, ONE bar of `9/8` at m8, then `6/8` again — and
the Breitkopf scan of that music is already in the scan gate with a
**hand-verified window** (`works.json`, Sean against the print: page 1 opens at
m8 printing 9/8 with 6/8 at its second bar; systems of 7 and 8 bars). So the
same 22 bars can be read ENGRAVED and SCANNED, and the two arms differ **only
in the printing**.

⚠️ **The LilyPond render reproduces the Breitkopf engraving's own conventions**,
including the CAUTIONARY `9/8` printed after page 0's final barline — a fact
`works.json` records Sean verifying on the 1880s plate. That is what makes the
pair a control rather than two loosely related runs.

A third work isolates a different claim: `brahms-sym1-mvt4` is `4/4` printed
`C` to m391 and `2/2` printed `¢` from m392. ⚠️ **BOTH ARE 4.0 QUARTER NOTES**,
so the bars are blind to that change by construction.

### The tally — printed meter changes against proposed ones

`report_boundary.py --tally out/`, counting SEGMENTS (a `voted` system can hold
the right opening and a wrong change, which a system-level pass/fail hides):

| fixture | printed | proposed | found | FALSE |
|---|--:|--:|--:|--:|
| Brahms 1 i **engraved** | 1 | 2 | **1** | 1 |
| Brahms 1 i **Breitkopf scan** *(the same 22 bars)* | 1 | **8** | **0** | **8** |
| Brahms 1 iv engraved (`C` → `¢`) | 1 | 1 | **1** | 0 |
| Beethoven 5 iv engraved (fwd) | 0 | 0 | 0 | 0 |
| Beethoven 5 iv engraved (rev) | 1 | 1 | **1** | 0 |
| Beethoven 5 Litolff scan | 1 | 2 | **1** | 1 |

**ENGRAVED: 4 printed changes, 4 found, 1 false. SCANNED: 2 printed, 1 found,
9 false.**

⚠️⚠️ **SO THE BOUNDARY RESULT GENERALISES TO A SECOND DOCUMENT AND NOT TO A
SECOND PUBLISHER'S SCAN — and the Brahms pair says the block is READING, not
the weighing.** On the same 22 bars the engraved arm votes `9/8`, finds the
change to `6/8` at the exact bar (support 60.0) and refuses a wrong carry;
the Breitkopf scan votes **`9/4`** (the denominator misread), misses the real
change entirely, and proposes **five spurious `4/4` changes at cells 2-6**,
every one of them at support 3.5-4.0 — just over `METER_CHANGE_FLOOR` = 3.0 —
plus two more on the page's second system. Its bar SEGMENTATION is right (7 and
8 cells, matching the hand-verified window); it is the meter GLYPHS that fail.

### ⚠️ THE ONE ENGRAVED FALSE POSITIVE IS A CAUTIONARY, AND BOTH PRINTINGS SHOW IT

Page 0 of both arms votes the correct `6/8` and then proposes a change out of
the courtesy `9/8` printed after the final barline — **segment@6 at support
57.0 engraved, segment@7 at 26.5 on the scan**. The cautionary announces the
NEXT system's meter and governs no bar on this page, so the segment would
re-size m7. A courtesy signature at a line end is standard engraving practice,
not an exotic case, and `_meter_changes` has no notion of it: any glyph in a
cell after the first is a change.

⚠️ The Beethoven forward fixture hid this — its cautionary page holds ONE cell,
so the glyph landed at cell 0 and was read as an opening. **A one-cell page
cannot exercise the rule that a page with seven cells breaks.**

### ⚠️⚠️ THE LENGTH-BLIND CHANGE: right length, wrong engraving, and no arithmetic could help

`brahms-sym1-mvt4`, `C` → `¢` at m392. My `_meter_from_letter` reads the `¢` at
the exact bar on **24 staves of 24, support 74.0** — the cut-common branch
firing on real data for the first time. Then, on the systems after it:

| arm | system 1 (m393+) | system 2 |
|---|---|---|
| CARRY | `carried` **C**, support +2.0 (3 bars fit / 2 not) | `carried` **C**, support +8.0 (7/0) |
| BARS | `no_evidence` | `derived_from_bars` **4/4**, support +7.0, length 4.0, form borrowed |

Truth is `¢` (2/2) in every one of those bars. Both mechanisms get the **length
right and the engraving wrong**, and the bars *agree* with the wrong answer
because `C` and `¢` are the same 4.0 quarter notes. `report_boundary.py` scores
this as `LEN-OK/FORM-WRONG` rather than OK, because musicdiff charges a wrong
`symbol=` at **three edits per staff**.

**This is the designed limit observed, not a defect** — *the bars name the
length, only ink names the engraving* is this mechanism's own claim. What makes
it actionable is that the right answer WAS on the record: the `¢` segment, read
on all 24 staves, one system earlier.

## 5. ⚠️⚠️ THREE GAPS, ONE PIECE OF WORK — the segments are read and nothing downstream uses them

Found by the measurements above, all three confirmed by `grep`, and **none
built here**: they are one design decision needing its own measurement pass,
and the request this session answered was for a second document and publisher.

1. ⚠️⚠️ **THE EXPORT IGNORES `segments` ENTIRELY, so a meter change cannot
   reach a file.** `staged/export.py:210` takes `rec.value(Q.METER, system)`
   and uses that one meter for the whole run;
   **`record.meter_at` — whose own docstring says *"`record.meter_at` is how a
   bar's meter is read"* — is called by NOTHING but its own tests**
   (`grep -rn meter_at tools/` → `record.py`, `ASSUMPTIONS.md`, a comment, and
   `test_staged_header_rhythm.py`). Measured on Brahms 1 iv: the `¢` segment
   sits on the record at `from_cell 6` with `staves_reading_it` = all 24 and
   support 74.0, and the exported file declares `<time>` exactly once per part,
   `4/4 symbol="common"`, at measure 1. **The entire mid-system change
   machinery the last two sessions built cannot currently produce a file.**
2. **A carry takes the source system's OPENING, not the meter in force at its
   END.** `carried = {k: v for k, v in found.value.items() if k != "segments"}`
   (`rhythm.py:1246`). Measured twice: Brahms 1 i system 2 was handed `9/8` —
   the one-bar meter that opens the source system — instead of the `6/8`
   governing seven of its eight bars; and Brahms 1 iv was handed `C` instead of
   the `¢` the same system had just read on 24 staves.
3. **A system that READ a change cannot be a carry source** (`found.reason !=
   "voted"`, `rhythm.py:1206` and `:1321`).

**They are one fix: carry, borrow from, and EXPORT the meter in force at each
bar, using the `segments` that already exist.** ⚠️ It needs a corpus that can
show it going wrong first — §4 and §4b record **nine false segments on two
scanned pages**, and every one of them would propagate forward under (2) and
(3) instead of staying on its own system.

## 6. Reproducing

```bash
ln -sfn <main>/library library
ln -sfn <main>/tools/omr/training/data/weights tools/omr/training/data/weights
B=benchmarks/omr-staged-meter-boundary-2026-09
PYTHONPATH=$PWD python3 $B/render_boundary.py --first 150 --last 180 --tag boundary-m150-180
PYTHONPATH=$PWD python3 $B/render_boundary.py --first 204 --last 232 --tag boundary-m204-232
python3 $B/run_arms.py --pages 0-3 --tag full --arms OFF,CARRY,BARS,BOTH
python3 $B/run_arms.py --pages 0,3 --tag p0p3 --arms OFF,CARRY,BARS
python3 $B/run_arms.py --pdf $B/fixtures/boundary-m204-232.pdf --pages 0-2 --tag rev
PYTHONPATH=$PWD python3 $B/report_boundary.py $B/out/full-*.json
PYTHONPATH=$PWD python3 $B/report_boundary.py --control bars $B/out/full-CARRY.json $B/out/p0p3-CARRY.json
python3 $B/export_arms.py $B/out/full-OFF.json $B/out/full-CARRY.json
python3 $B/summarize.py            # the committed extracts + REPORT.txt
```

⚠️ **The records are gitignored build products** (2-10 MB each). What is
committed is `out/*.meter.json` and `out/REPORT.txt`, which is what every
figure above is read off.

⚠️ **`env $VARS python3 ...` in zsh does not word-split.** `run_arms.py` hands
`subprocess` an environment dict and sets BOTH flags explicitly in every arm,
including to `"0"`, so an arm can neither inherit a flag from the shell nor
lose one to word-splitting. The 2026-09-09 handoff §4.1 records what that cost
the last time.
