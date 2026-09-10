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
| `--pages 0-3` | **3/4** (from p2, the true meter) | 8 fit / 1 not | **+8.0** | **`carried` 3/4 — CORRECT** |
| `--pages 0,3` | **4/4** (from p0's `C`, across the boundary) | 0 fit / 9 not | **−8.0** | **`carry_outweighed_by_the_bars` — REFUSED** |

`--pages 2,3` reproduced the first row to the unit, so the swing is the
candidate's and not the window's.

⚠️ **THE TRUE ROW MOVED, UPWARD, AND THE REASON IS A DEPENDENCY THIS DESIGN
PREDICTS.** It was **+6.0 (7 fit / 2 not)** until a sibling session's DURATION
work landed — stems joined to beams by the STEM rather than by the notehead's
centre, and marks attached to their notehead. Bar sums are this mechanism's
second witness, so better durations make the bars speak more clearly: the same
page now reads `{3.0: 8, 5.0: 1}` where it read `{3.0: 7, 5.0: 2}`. The false
candidate is unchanged at −8.0, so the SWING widened 14.0 → **16.0**. The
figure below is the current one; the earlier pair is left as measured in
`version_memory.md`, per this repo's rule that a recorded transition is a
frozen fact.

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
it (`m2*`, `m3*` and `m7*` runs): the discriminating pair, the same `bar_lengths_seen`, the same
reasons, the same §4b tally to the row, and the `C`-change fix still reading
23 staves of 23 at support 66.0.

**That is the measurement that was missing.** On the *Andante* the true meter
scored −1.0 and the false one −1.0; here the true one scores +8.0 and the false
one −8.0, on the same nine bars.

**And `OMR_METER_FROM_BARS` reaches the same page independently:**

| window | what the bars name | outcome |
|---|---|---|
| `--pages 0-3` | length **3.0**, support **+5.0** (7+/2−) | **`derived_from_bars` 3/4**, form borrowed from p2 |
| `--pages 0,3` | length **3.0**, support **+5.0** | `bars_name_a_length_without_a_form`, forms **`['3/4','6/8','12/16']`** |

The truth is in the shortlist. The carry's support exceeds the bars' own by
exactly `W_METER_CARRIED` = 1.0, as it should be — the same bars, one mechanism
carrying a prior reading as an extra term.

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
consequence ran. It is the same in every arm and every window
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

✅ **A MECHANISM FOR THIS WAS DIAGNOSED INDEPENDENTLY THE SAME DAY** and is
worth reading beside it: `benchmarks/omr-staged-meter-engraved-2026-09/` finds
that `_bar_lengths_for` consumes a NARROWED duration verdict by taking
`candidates[0]`, which `Ruling.narrow` orders by support — so a verdict saying
*"it is one of these"* is spent as if it had decided, always on the longer
note, inflating the bar. ⚠️ It also measures that *"take the lowest"* is **not**
the repair (it fixes one page and breaks another) and locates the honest one
upstream, in beam detection. That is a cause of the density effect below, not
a competitor to it.

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

✅ **FIXED — read §4c's cautionary section before quoting the table above.**
The diagnosis below stands; the behaviour it describes no longer ships.

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

## 4c. THE SCAN SIDE, OPENED — and one fault was a bookkeeping bug, not a reading one

§4b said the second-publisher block is READING. Opening it found that **more
than half of the damage was not**: of the nine false segments on the two
scanned pages, **five were one system proposing the SAME meter at five
consecutive bars.**

### ⚠️ TWO HYPOTHESES WERE MEASURED AND REFUTED FIRST, both by looking at the right population

The false `timeSig4` rows *looked* separable, and neither candidate survived
contact with a clean comparison:

* **"a stack is two digits aligned in x and adjacent in y."** Over 130
  per-staff pairs the two populations overlap completely — TRUE `dy` 32-548
  against FALSE 26-555, TRUE `dx` 0-13 against FALSE 0-16. There is no gap.
* **"the false ones sit flush at the cell's left edge" (`x_canonical == 0`).**
  A per-cell table made this look decisive. Restricted to *clean two-digit
  stacks* — the population the rule would actually run on — it is **1 of 110
  TRUE and 4 of 50 FALSE**. The apparent split came from pooling contaminated
  groups of three and four digits and reporting their min.

⚠️ Both were killed by asking the same question of a *comparable* population.
The first table was not wrong about its numbers; it was wrong about what they
were numbers OF.

### ⚠️⚠️ THE ACTUAL FAULT: a change was compared against the OPENING, never against the meter IN FORCE

`_meter_changes` tested every candidate against `opening` alone, so once a
change to `4/4` was accepted at cell 2, cells 3, 4, 5 and 6 proposing `4/4`
each differed from the (misread) opening `9/4` and were appended too. **A
system does not change meter five times to the meter it is already in.**

⚠️ **And the same comparison was losing a real change in the other direction**:
a movement going `3/4 → 4/4 → 3/4` recorded the departure and dropped the
RETURN, because the return equals the opening. Beethoven 9's finale does that
repeatedly (`3/4 → 2/4 → 3/4 → 4/4 → 3/4 …`, 17 changes), and nothing in this
corpus would have shown it.

**Fixed** — compare against the meter in force, which is the opening until a
segment supersedes it. No threshold, nothing to tune: a segment identical to
its predecessor changes nothing, by the definition of `record.meter_at`.

| | printed | proposed | found | FALSE |
|---|--:|--:|--:|--:|
| Brahms 1 i **Breitkopf scan**, before | 1 | 8 | 0 | **8** |
| Brahms 1 i **Breitkopf scan**, after | 1 | 3 | 0 | **3** |
| every engraved row, before and after | — | — | — | **unchanged** |
| Beethoven 5 Litolff scan, before and after | 1 | 2 | 1 | **1** |

**False segments across the two scans 9 → 4. No true change lost. The engraved
arms are identical to the row**, which is the control that says this is a
bookkeeping repair and not a tightening.

`TestAChangeIsAgainstTheMeterInFORCE` pins it — 5 tests, **4 mutation arms all
red** (revert to comparing against the opening; never advance the in-force
meter; drop the check; ignore the opening as the seed). ⚠️ Its first harness
gave both digits the same `y_center` AND the same subject, so no pair formed
and every assertion failed for a reason unrelated to the rule — the harness is
now commented with that, because a test that fails for the wrong reason is one
edit away from being "fixed" by weakening the assertion.

### ⚠️⚠️ AND THE CAUTIONARY: a courtesy signature is not a change

The other false positive — the only one the ENGRAVED arms produced, and the
same one on both printings of the same music. An engraver announcing a new
meter prints it **twice**: once after the final barline of the system that is
ending, once at the head of the system that begins. **The first governs no
bar.** `_meter_changes` had no notion of one; any glyph past cell 0 was a
change, so both printings proposed one at page 0's last cell (support **57.0**
engraved, 19 staves; **26.5** scanned) and the segment would re-size a bar the
cautionary does not govern.

**The rule is the engraving convention, not a fitted threshold**: a change is
put at a system's START, and the cautionary exists precisely so that it can be.
So a meter standing in a system's **LAST cell** is the announcement — unless
the bar it would govern fits, which is the one thing that separates a genuine
last-bar change from a courtesy.

⚠️ **Measured over every change in this corpus before writing the rule**, which
is what makes it more than a story: **all four TRUE changes sit at a non-last
cell** (Litolff p.62 cell 8 of 13, Brahms 1 i cell 1 of 8, Beethoven 5 iv cell
3 of 9, Brahms 1 iv cell 6 of 8) and **both cautionaries sit at a last cell**,
6 of 7 and 7 of 8. The Litolff headline result is not at a last cell and is
untouched — checked before the rule was written, not after.

⚠️ **IT IS RECORDED, NOT DISCARDED**, on the meter's own value as
`cautionary`. That matters because it is the document's answer to the very
next thing this benchmark gets wrong:

| | reads | on | support |
|---|---|--:|--:|
| the cautionary ending page 0 | **`9/8`** | 9 staves | 26.5 |
| the opening it announces (page 1) | `9/4` ✗ | 10 staves | scores 0.500-0.531 |

⚠️ **A recorded cautionary is evidence, not an answer** — the same scan also
records one at support **3.5 on ONE staff**, out of the spurious `timeSig4`s.
The support and the staff count are exactly what tell the two apart, and a
consumer must weigh them rather than take the last one.

⚠️ **AND THE INVENTORY CAUGHT THE CALL CHAIN.** Declaring
`Q.MEASURE_PARTITION` in `wants` made `inventory._never_read` report it as an
INERT declaration — that check follows a decision's own helpers to depth 3, and
fetching the cell counts inside `_meter_changes` put the read one level too
deep. The report was right that the chain was one link longer than every other
fact the same function uses: `bars` is computed by the CALLER and passed in, so
`last_cell` now is too. **Behaviour-identical, verified by re-running both
cautionary arms and comparing every meter verdict field.** The fix was the one
the check was pointing at, not a workaround for it.

`TestACautionaryIsNotAChange` pins it — 8 tests, **6 mutation arms all red**.
⚠️ A seventh mutation (`any` staff at its last cell instead of `all`)
**survived**, so a test was written to distinguish them rather than leaving a
gate nobody had exercised: a cautionary is a SYSTEM-WIDE event, so a staff that
still has a bar after the glyph contradicts it, and the safe reading of a
contradiction keeps the change.

### ⚠️⚠️ THE `9/4`: DIAGNOSED IN FULL, THREE HYPOTHESES REFUTED, AND NOT FIXED

The last scan fault, opened. Brahms 1 / Breitkopf page 1 prints `9/8` on every
staff of its first system and the template reader votes **`9/4`**.

**What the reader actually did** (`min_score=0.0`, the whole score table, from
the reader's own header crops rather than from the page):

| | winner | score | runner-up | `9/8` |
|---|---|--:|---|--:|
| page 0, the correct `6/8` | `6/8` | **0.656-0.750** | `9/8` at 0.53-0.63 | 2nd on 13 of 14 |
| page 1, the wrong `9/4` | `9/4` | **0.445-0.531** | `6/4` / `C` at 0.42-0.47 | **top-4 on only 3 of 14** |

The numerator is right and the denominator is wrong, and `9/8` is not even the
runner-up. ⚠️ **Page 1's WINNER scores below page 0's RUNNER-UP** — the
signature of matching noise rather than a meter.

**Hypothesis 1 — staff-line removal is tearing the digits apart. REFUTED.**
`locate_time_signature` deliberately reads `image_no_staff`, on a measured
ground (with the lines in, a barline matched as a `1` on two staves of twelve
of Beethoven 5 p.1), and the crop does look shredded: the `9` reads as a `U`
and the `8` as an `A`. **But scoring both variants of every header, page 1
still reads `9/4` with the lines INTACT**, at *lower* scores (0.416-0.463).
The erasure is not the cause.

**Hypothesis 2 — the recorded `score_margin` separates a good vote from a bad
one. REFUTED, and it is the more useful negative.** ⚠️ `score_margin` is
computed by the locator, written onto every `Q.METER_TEMPLATE` row by GATHER,
and **read by nothing** — the "value existed and nothing read it" pattern
again, so it looks like a free discriminator. Measured over 8 system votes on
4 documents: **TRUE 0.0681-0.3840, FALSE 0.0675.** A gap of **0.0006**. It does
not separate, and a gate built on it would have looked principled and done
nothing.

⚠️⚠️ **AND NO STRUCTURAL SIGNAL CATCHES IT EITHER: the wrong reading is
UNANIMOUS.** All 10 staves that spoke agree (`share` 1.0), so coverage and
agreement floors both pass. **Cross-staff agreement is not independent evidence
when every staff feeds the SAME reader the SAME typeface** — `A-DUR-6`'s
"the bars are not fully independent witnesses", arriving in the meter reader.

**What DOES separate is the absolute score, and its interval is empty:**

| | n | median score |
|---|--:|--:|
| TRUE system votes | 7 | 0.744-0.781 (min staff 0.656) |
| the FALSE one | 1 | **0.514** (max staff 0.531) |

Nothing lies between **0.531 and 0.656**, and `min_score` is **0.50**.

⚠️ **NOT SHIPPED, and the reason is scope rather than doubt.** `min_score`
belongs to `time_signature_locator`, which the LEGACY `transcribe` path shares;
its current value was set on an 11-source corpus, and the vote's agreement
floor was moved 0.5 → 0.70 on 12-correct/1-wrong evidence from that same
corpus. Raising it on **7 correct / 1 wrong over 4 documents** would be tuning
on a fraction of the evidence the constant was set with, and pricing it means
re-running the eleven-work engraved benchmark and the 20-row scan gate. That is
its own piece of work.

**Hypothesis 3 — the CAUTIONARY plus the BARS can settle it with no threshold.
REFUTED, and this is the one that was designed before it was tested.**

The cautionary one system earlier reads `9/8` on **9 staves**, from the
DETECTOR's digit pairs rather than from template correlation — an independent
reader agreeing with the print, already on the record. Two readings of ONE
printed fact. Nothing here may pick between them by confidence, and n = 1 is
far too little to fit a rule — **but Sean's ordering says arithmetic that
checks itself outranks what can only be read, and `9/4` is 9.0 quarter notes
against `9/8`'s 4.5.** So the design was: put both to the system's OWN BARS in
the carry's existing signed-term currency, reusing `_score_bars`; no new
constant, and fail safe when the bars cannot speak.

**Its precondition was measured first** (`probe_cautionary_arbiter.py`, driving
the real stages and building a real `Evidence`, so the bars are exactly the
ones `_corroborate` would see):

| system | voted | bars that reach the quorum | `9/4` | `9/8` |
|---|---|--:|---|---|
| p0 s0 | `6/8` ✓ | 2 | −2.0 | −2.0 |
| **p1 s0** | **`9/4`** ✗ | **0 of 7** | *cannot speak* | *cannot speak* |
| p1 s1 | `4/4` ✗ | 1 | *cannot speak* | *cannot speak* |

**On the exact system where the arbitration is needed, not one bar clears the
quorum.** The route is dead there, and no amount of design saves it.

⚠️⚠️ **AND THE GENERAL HAZARD IS WORTH MORE THAN THE DEAD ROUTE: the case that
most needs an arbiter is the case where the arbiter is silent.** A page whose
meter the template reader mangles is a page whose ink is degraded — and the
same degradation is what stops its bars from summing. The bars are not an
independent umpire over a bad reading; they fail together with it. This is the
*Andante*'s "when the page cannot speak, abstain" arriving from the other
direction, and it bounds every bar-arbitrated rule this benchmark has built.

⚠️ **The cautionary route is not dead in the OTHER case** — a system that
ABSTAINS needs no arbitration, because there is nothing to overturn, and a
cautionary is ink naming that system's meter. **Reach on this corpus: ZERO** —
no system that abstains here is preceded by a recorded cautionary — so it is
recorded as available and unbuilt rather than shipped untested.

### The two fixes together

| | printed | proposed | found | FALSE |
|---|--:|--:|--:|--:|
| **engraved**, before either fix | 4 | 5 | 4 | **1** |
| **engraved**, after both | 4 | 4 | 4 | **0** |
| **scanned**, before either fix | 2 | 11 | 1 | **10** |
| **scanned**, after the meter-in-force fix | 2 | 6 | 1 | **5** |
| **scanned**, after both | 2 | 5 | 1 | **4** |

⚠️ Counting the two scans together (Breitkopf 8 → 3 → 2, Litolff 1 → 1 → 1)
and both engraved cautionary rows: **false meter changes 10 → 3 across the six
fixtures, every true change still found, and the engraved arms are now clean.**

### What the scan side still gets wrong, measured and NOT fixed

1. ⚠️ **The opening `9/8` is voted `9/4`.** The header template reader returns
   `[9, 4]` on 10 staves at scores **0.500-0.531** — against `min_score` 0.50 —
   where page 0's correct `6/8` reads 0.656-0.750 on 14 of 14. The numerator is
   right and the denominator is wrong. ⚠️⚠️ **And the document contains the
   correct answer one system earlier**: the cautionary at the end of page 0 is
   the same meter, and the DETECTOR reads it as `9` over `8` on 10 and 20
   staves. Using it means feeding a cautionary forward — which is carry/borrow,
   and belongs with §5.
2. ✅ **The cautionary is FIXED** — see the section above. What remains of it is
   that nothing yet CONSUMES the recorded one.
3. **The real change to `6/8` at cell 1 is still missed** — the detector finds
   one `timeSig1` there and no pair. That one is genuinely a reading gap.

So of the ten false segments §4b reported across the six fixtures, **five were
bookkeeping, two were cautionaries, and three are detector false positives** —
and the one remaining reading fault that matters (`9/4`) has its answer sitting
on the record one system earlier.

## 4e. ⚠️ THE FRAME AUDIT — clean, and the analogous hazard is the CELL INDEX

Prompted by a finding from the staged-pipeline session: `gather_glyph_families`
was emitting CANONICAL coordinates only, so `arc_owner`'s declared input sat in
a frame that cannot answer a cross-staff question — and **`coverage()` reported
that family as `stub`, not `starved`, because the quantity WAS being gathered.**
A quantity can be gathered in the wrong frame and look fed.

**Audited against every meter rule this benchmark shipped, and they are clean.**
Only `_meter_from_digits` reads a coordinate at all (`y_center`, to tell a
numerator from a denominator) — and `_meter_changes` splits its rows **by staff
before calling it**, so the comparison is always within one staff's cell, where
canonical IS the right frame. `_meter_from_letter`, `_last_cell_per_staff`,
`_score_bars` and `_bar_lengths_for` read no coordinate.

⚠️ **BUT THE SAME HAZARD EXISTS HERE IN A DIFFERENT CURRENCY: the CELL INDEX is
a per-staff quantity used as a system-wide key.** `_score_bars` takes a
cross-staff majority of bar lengths keyed on `cell.cell`, and
`_last_cell_per_staff` exists precisely because *"the staves of one system do
not always agree about how many bars they hold"*. Where they disagree, cell `N`
on one staff and cell `N` on another are **different bars**, and the majority
would be mixing them — silently, exactly as a wrong coordinate frame does.

**Measured over all 16 systems of the five fixtures: every one is UNANIMOUS
about its cell count** (`{8: 14}`, `{7: 21}`, `{9: 23}` …). So the shared key
holds throughout this corpus and no result above is affected.

**And the JOIN that rule depends on was verified too, not inferred.**
`_last_cell_per_staff` keys off `Q.MEASURE_PARTITION` verdict subjects while
`_meter_changes` groups `Q.METER_GLYPH` rows by `subject.staff` — two dicts
built from different quantities and joined by staff index. Across all 10
systems that read a meter glyph: **every glyph-reading staff has a partition
entry, zero orphans.** (There was indirect evidence already — the cautionaries
fire 2 of 2, which cannot happen unless those lookups hit.)

⚠️ **If that join ever DID break it would fail CLOSED and SILENTLY**:
`last_cell.get(st)` returns `None`, the `all(...)` is False, no candidate is
ever classified a cautionary, and the rule degrades to exactly the behaviour it
replaced. Safe direction, no signal. Not guarded, for the same reason as
below — but worth knowing which way it falls.

⚠️⚠️ **THIS IS THE THIRD INSTANCE OF ONE PATTERN IN A DAY, and the third came
from another session**: a quantity gathered in CANONICAL coordinates answering
a cross-staff question (`arc_owner`), a per-staff CELL INDEX used as a
system-wide key (here), and `Subject.glyph`, which counts within its CELL and
is therefore wrong at `Kind.SYSTEM` (the onset-column work). **A per-container
ordinal used as a cross-container key** — and the reason it keeps happening is
that the wrong key still RESOLVES, so nothing raises. ⚠️ Of the three, the
frame at least announces itself in a field name; an ordinal does not.

⚠️ It is recorded as a bounded latent hazard rather than guarded, because
**there are zero observed instances to build a guard against** — and it is also
why the `all`-not-`any` distinction in the cautionary rule could only be pinned
by a synthetic test: on real data here the two are identical.

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
