# Handoff — the boundary case is measured, and a `C` was being detected and dropped

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-bars-name-a-length.md](handoff-2026-09-09-bars-name-a-length.md)
as the entry point. That file's redirect still governs — **the metric is not
the goal, the staged pipeline is** — and its §5 task **1** is what this session
did.

⚠️ Its §3 and §4 stand unamended and are still the honest account of what
`OMR_METER_CARRY` / `OMR_METER_FROM_BARS` rest on. **One claim in them is now
superseded and only one**: *"the case that separates them — a movement
boundary on a page that READS WELL — is unmeasured"*. It is measured. Nothing
else changed.

---

## 1. WHAT LANDED

**A measurement**, and **one fix it found**.

* `benchmarks/omr-staged-meter-boundary-2026-09/` — two engraved fixtures
  carrying a REAL meter change, the four arms over each, the reports, the
  controls, and `FINDINGS.md`.
* `rhythm._meter_from_letter` — **no flag**, because it adds a reading where
  there was none. A meter change engraved as a common-time `C` was DETECTED on
  every staff and proposed nothing.

## 2. THE MEASUREMENT — the bars discriminate by 14.0

`beethoven-sym5-mvt4` (4/4 → **3/4 at bar 155** → 4/4 at bar 209) rendered
through LilyPond at 23 parts, so the ink is clean and a bar that fails to sum
is the reader's fault. An engraver prints a time signature at the CHANGE and at
nothing after it, so a system lying wholly inside the new meter prints none,
abstains honestly, and is exactly what both mechanisms are for. **Nothing was
suppressed to produce that.**

Page 3 of the forward fixture (m172+, 3/4, no meter printed), asked twice — the
runs differ ONLY in which earlier page is in the window:

| candidate offered | bars | support | outcome |
|---|---|--:|---|
| **3/4**, the true meter | 7 fit / 2 not | **+6.0** | **`carried` 3/4 — CORRECT** |
| **4/4**, across the boundary | 0 fit / 9 not | **−8.0** | **refused** |

On the *Andante* the true meter scored −1.0 and the false one −1.0. Here they
are +6.0 and −8.0 **on the same nine bars**. `OMR_METER_FROM_BARS` reaches the
same page independently (length 3.0 at +5.0; `derived_from_bars` **3/4** where
a 3/4 is available to borrow the spelling from, and
`bars_name_a_length_without_a_form` with `['3/4','6/8','12/16']` where only a
`C` precedes — the truth in the shortlist).

**In the file** (exported from the saved records, no re-transcription): whole
rests written at 4.0 ql inside a 3.0 ql bar **196 → 38**, proper measure rests
**305 → 463**, quarter and half rests untouched, and the CARRY and BARS exports
**byte-identical**. All 38 residuals are bars holding more than one note, which
`size_measure_rest` refuses by design.

## 2b. ⚠️⚠️ A SECOND DOCUMENT AND PUBLISHER — the result SPLITS

Done in the same session. `brahms-sym1-mvt1` prints `6/8`, ONE bar of `9/8` at
m8, then `6/8` — and the **Breitkopf scan of that music is already in the scan
gate with a hand-verified window** (`works.json`; Sean against the print). So
the same 22 bars run ENGRAVED and SCANNED and the arms differ **only in the
printing**. A third fixture, `brahms-sym1-mvt4`, changes `C` → `¢` at m392,
where **both meters are 4.0 quarter notes** and the bars are blind by
construction.

| fixture | printed changes | proposed | found | FALSE |
|---|--:|--:|--:|--:|
| Brahms 1 i **engraved** | 1 | 2 | **1** | 1 |
| Brahms 1 i **Breitkopf scan** *(same 22 bars)* | 1 | **8** | **0** | **8** |
| Brahms 1 iv engraved (`C` → `¢`) | 1 | 1 | **1** | 0 |
| Beethoven 5 iv engraved ×2 | 1 | 1 | **1** | 0 |
| Beethoven 5 Litolff scan | 1 | 2 | **1** | 1 |

**ENGRAVED 4 printed / 4 found / 1 false. SCANNED 2 printed / 1 found / 9
false.** ⚠️ **The result holds on a second DOCUMENT and does not hold on a
second PUBLISHER'S SCAN, and the Brahms pair says the block is READING.** On
the same bars the engraved arm votes `9/8` and finds the change to `6/8` at the
exact bar (support 60.0); the scan votes **`9/4`**, misses the change, and
proposes **five spurious `4/4` changes at cells 2-6**, all at support 3.5-4.0
against a floor of 3.0. Its bar segmentation is right (7 and 8 cells, matching
the hand-verified window) — the meter GLYPHS fail.

⚠️ **The one engraved false positive is a CAUTIONARY signature** printed after
page 0's final barline, and BOTH printings show it (segment@6 support 57.0
engraved, segment@7 support 26.5 scanned). It governs no bar on its page. A
courtesy signature at a line end is standard engraving, and `_meter_changes`
has no notion of one: any glyph past the first cell is a change. ⚠️ The
Beethoven fixture hid this because its cautionary page holds ONE cell.

⚠️⚠️ **AND THE LENGTH-BLIND CHANGE IS THE DESIGNED LIMIT, OBSERVED.** The `¢`
is read at the exact bar on **24 staves of 24, support 74.0** — then the next
systems are carried `C` (+2.0, +8.0) and derived `4/4` (+7.0), with the bars
AGREEING, because `C` and `¢` are the same 4.0 quarters. Right length, wrong
engraving, and musicdiff charges `symbol=` at three edits per staff. Scored
`LEN-OK/FORM-WRONG`, not OK.

## 3. ⚠️ WHAT IS *NOT* ESTABLISHED

* ✅ **The one-document caveat is retired** — see §2b, and read it before
  quoting §2 as a general result.
* ✅ **Every figure was RE-MEASURED on the merged tree.** `origin/main` moved
  27+ commits under this branch, including **221 changed lines of `rhythm.py`
  and 404 of `gather.py`** — where the rows these decisions read come from.
  Identical on every arm.
* **n = 4 systems**; the discrimination result is ONE page asked twice.
* ⚠️ **`METER_CARRY_MIN_BARS = 2` refused a CORRECT carry here** — the
  one-bar fermata system, truth 4/4, its single bar reading 4.0. First time
  that constant's cost has been seen rather than only its benefit.
* ⚠️ **Bar assessability falls with DENSITY, not with print quality**: over the
  four systems asked, 100% / 100% / 78% / **33%** against 1.0 / 1.5 / 3.1 /
  **4.5** events per bar. A dense bar needs every duration right to sum, so
  these mechanisms are strongest where the music is SPARSE — which is also
  where the measure-rest payoff is largest. n = 4; suggestive, not established.
* **Neither flag is flipped.** For the carry, objections (1) AND (2) of its
  knobs-table entry are now closed; (3) — weights that are asserted rather
  than measured — stands, and §2b adds a new one: **on a scanned second
  publisher the meter is misread badly enough that the weighing never gets a
  fair candidate.**

## 4. ⚠️ THE FIX — a `C` change was detected on 23 staves of 23 and dropped

`_meter_from_digits` needs two stacked digits and says so in its own comment
(*"timeSigCommon and friends: no pair"*), so a system whose meter changes to
common time formed no candidate at all. Measured at the 3/4 → 4/4 change of bar
209: **`timeSigCommon` on 23 staves of 23, unanimous, and nothing proposed.**
Detected then dropped, inside the meter.

⚠️ **`Q.METER_GLYPH` already carries `letter=True`, written by GATHER and read
by NOTHING.** It cannot be the input either — a boolean cannot tell a `C` from
a `¢`. ⚠️ **And the change detector had NO unit tests at all**: `grep -c
METER_GLYPH tools/omr/tests/*.py` was zero across the suite while
`_meter_changes`, `_change_only` and the whole `segments` mechanism shipped
default-on. `TestAMeterChangeIsReadFromTheInk` (10 tests, **8 mutation arms,
all red**) is that gap closed.

⚠️⚠️ **THE FIX PRODUCES A FALSE POSITIVE ON A SCAN AND IT IS REPORTED, NOT
SMOOTHED OVER.** Litolff p.61 prints bar 140 and no time signature anywhere
(rendered and looked at); one `timeSigCommon` at confidence **0.377** on one
staff of seventeen now proposes a change. It names 4/4, which IS that page's
meter, so the record got better *here* — by accident of which meter the false
glyph named. **The hazard is `METER_CHANGE_FLOOR`, not the letter path**, and
the previous session's headline `3/4` on p.62 rests on the identical
one-staff-clears-the-floor property. What a letter adds is that it is cheaper
to fake than a digit pair. The bars refused the OTHER false letter on the same
document. Confidence separates the four populations cleanly (0.887-0.927
engraved, 0.377-0.560 scan) and is deliberately **not** gated on: four rows on
two documents is not a threshold.

Everything else is unchanged: the forward fixture identical on all 4 pages,
Litolff `--pages 0-2` identical on every subject, outcome, reason and value,
and p.62's `3/4` at cell 8 preserved to the unit.

## 5. THE NEXT WORK, RANKED

### 1. ⚠️⚠️ THE SEGMENTS ARE READ AND NOTHING DOWNSTREAM USES THEM — three gaps, ONE fix

All three confirmed by `grep`, none built here (each needs its own measurement
and the session's request was the second document):

1. ⚠️⚠️ **THE EXPORT IGNORES `segments`, so a meter change cannot reach a
   file.** `staged/export.py:210` takes one meter per system run, and
   **`record.meter_at` — whose docstring says it *is* how a bar's meter is
   read — is called by nothing but its own tests.** Measured: the `¢` sits on
   the record at `from_cell 6`, 24 of 24 staves, support 74.0, and the file
   declares `<time>` once per part, `4/4 symbol="common"`, at measure 1. **The
   whole mid-system change machinery cannot currently produce a file.**
2. **The carry takes the source's OPENING, not the meter in force at its END**
   (`rhythm.py:1246`) — measured twice: Brahms 1 i handed `9/8` (a one-bar
   meter) instead of the `6/8` governing seven of eight bars, and Brahms 1 iv
   handed `C` instead of the `¢` the same system had just read.
3. **A system that READ a change cannot be a carry source** (`found.reason !=
   "voted"`, `rhythm.py:1206`, `:1321`).

**One fix: carry, borrow from, and EXPORT the meter in force at each bar, off
the `segments` that already exist.** ⚠️ Price the false positives first — §4
and §2b record **nine false segments on two scanned pages**, and each would
propagate forward under (2) and (3) instead of staying put.

### 2. ✅ THE SCAN SIDE — OPENED, and half of it was NOT a reading problem

Done. Of the nine false segments on the two scanned pages, **five were one
system proposing the SAME meter at five consecutive bars**: `_meter_changes`
compared every candidate against the system's OPENING and never against the
segment already accepted. ⚠️ The same comparison was **losing a real change in
the other direction** — a movement going `3/4 → 4/4 → 3/4` recorded the
departure and dropped the RETURN, which Beethoven 9's finale does repeatedly.
Fixed by comparing against the meter IN FORCE; no threshold.
**False segments across the two scans 9 → 4, no true change lost, every
engraved row identical.**

⚠️ **Two geometric hypotheses were measured and REFUTED first** — "a stack is
two digits aligned in x and adjacent in y" (TRUE `dy` 32-548 vs FALSE 26-555,
complete overlap) and "the false ones sit at `x_canonical == 0`" (1 of 110 TRUE,
4 of 50 FALSE once restricted to clean two-digit stacks). The first table that
made the second look decisive was pooling contaminated groups and reporting
their min.

**What the scan still gets wrong**, measured and not fixed:
* the opening `9/8` is voted **`9/4`** — the header template reader returns
  `[9, 4]` on 10 staves at **0.500-0.531** against a `min_score` of 0.50, where
  page 0's correct `6/8` reads 0.656-0.750 on 14 of 14;
* the CAUTIONARY is read as a change on the system that prints it, on both
  printings;
* the real change to `6/8` is missed — one `timeSig1` detected, no pair.

⚠️⚠️ **The first two have the SAME repair available and it is §1's**: the
cautionary at the end of page 0 is the same meter as page 1's opening, and the
DETECTOR reads it correctly as `9` over `8` on 10 and 20 staves. **The document
holds the right answer one system earlier and nothing carries it forward.**
Feeding a cautionary to the next system's opening is carry/borrow — so it lands
naturally in the segments session, not in a new reader.

### 3. UNCHANGED FROM THE LAST HANDOFF

`A-DUR-6` items 6 and 7 — beat subdivision, and `A-DUR-5`'s **unclassified
ink**, Sean's standing request, still needing a RASTER pass in GATHER. Unify
the two chord groupings (export consuming `Q.EVENT`). `arc_kind` / `arc_owner`
still stubs (843 arcs). Calibration from the score library, which bar sums make
possible with no truth files and which nothing has built.

⚠️ The double barline is still **not** the cheap win `A-DUR-6` calls it — see
the previous handoff.

## 6. OPERATIONAL

* Four symlinks in a worktree: `library`, `tools/omr/training/data/weights`,
  `.venv-surya`, `.venv-omrned`. The staged pipeline needs only the weights;
  the SUITE needs `.venv-surya` or a direction-text test FAILS rather than
  skipping.
* ⚠️ **`omr-weights/` does not exist in a worktree.** Use
  `tools/omr/training/data/weights/...`; the CLAUDE.md examples use the other
  path and fail with `FileNotFoundError` inside ultralytics.
* ⚠️ **The staged CLI does no weight routing.** Engraved fixtures want
  `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`, scans want the hollow graft;
  `run_arms.py` takes `--weights` and records the choice.
* ⚠️ **A duration-level A/B across meter arms is invalid by construction** — a
  decided meter is consumed by `size_measure_rest` and `reconcile_duration`
  (159 of 314 duration verdicts move on one page). Control on the meter
  decision's own `bar_lengths_seen` instead.
* ⚠️ Do not edit a source file while the suite runs (`inspect.getsource` reads
  through `linecache`); markdown is safe.
* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  `llama-server`.**


## 7. ⚠️ COORDINATION — a sibling session is in the same two files

`claude/reengraved-meter-range-9814dc` was working the same thread in parallel
and has **uncommitted** changes to `staged/adjudicators/rhythm.py` and
`tools/omr/tests/test_staged_header_rhythm.py`. **We did not duplicate the
measurement**, and the split is worth recording:

* **that session** hunted the SCAN side — it located all three movement starts
  on the Litolff Beethoven, measured that **none reads well**, and concluded
  *"the remaining route is the ENGRAVED one"*. It also found a real bug this
  session did not: **a refused carry was blocking the rungs behind it**
  (`_meter_fallbacks`).
* **this session** took that engraved route and did it, plus the second
  document and publisher.

So its conclusion and this session's work compose; its §5 item naming the
engraved route as outstanding is now satisfied. ⚠️ **The two branches touch
different functions in the same two files** — `_meter_from_letter` /
`_meter_changes` here, `_meter_fallbacks` / `adjudicate_meter`'s dispatch there
— so the merge is mechanical but not automatic, and both append test classes to
the same file. ✅ **THAT MERGE HAS NOW HAPPENED AND THE ARMS WERE RE-RUN** (`m3*`): every
figure in §2 and §2b is identical after it, and the `BOTH` arm now shows their
fix working on a fixture they never ran — `--pages 0,3` used to abstain
`carry_outweighed_by_the_bars` and now reports
`bars_name_a_length_without_a_form` at +5.0 with the truth in the shortlist.
The two test classes coexist green (56 passing in that file). ⚠️ Three files
conflicted and were resolved **keeping both sessions' work**: both test classes
in full, their new `OMR_METER_FROM_BARS` knobs row with this session's edits
re-applied to the `OMR_METER_CARRY` row, and both `version_memory.md` blocks
with a note that they are independent.
