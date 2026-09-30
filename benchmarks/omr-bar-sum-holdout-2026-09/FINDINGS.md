# A bar that does not add up is held out — ROADMAP 2.8

Sean, 2026-09-23 (docs/DECISIONS.md): **"hold out — I don't care about print
right now — I want to know what we are getting correct."** A bar whose event
durations do not sum to the meter in force is a bar we could not read, so
EXPORT writes it as the same marked empty bar a bar we read NOTHING in gets,
and counts every notehead and rest in it under a new named refusal
`bar_does_not_add_up`. Nothing pads, trims or re-times a bar to fit.

Branch `claude/bar-sum-holdout-2.8`, off `259773e5`. Base and arm are the SAME
tree and the SAME three saved records; 2.8 is an EXPORT-only change, so
re-exporting a committed record prices it exactly (CLAUDE.md §6b — no
re-gather is needed and none was done).

---

## 1. The rule as implemented

`export._bar_holds_out` (`tools/omr/staged/export.py`). A bar is held out when
**any voice's duration units differ from the meter in force**, where:

| question | the rule | why |
|---|---|---|
| **units** | the `<duration>` integers the file itself holds — `_event_units(ev, divisions)`, the SAME function `_measure_events_xml` accumulates its `<backup>` figure from | one copy of the arithmetic; the check and the file cannot come apart |
| **voices** | **per voice, and EVERY voice must fill** | `<backup>` returns the cursor to the head of the bar, so a reader sees each voice's own timeline. Stricter than the acceptance control, which takes the max — deliberately: the strict side is the one that cannot let a wrong bar through |
| **chords** | a chord is **ONE** event; only the first `<note>` advances the cursor | CLAUDE.md §10's double-counting trap, the fault that made the last staged bar-sum arithmetic wrong |
| **tuplets** | the ratio scales the time, the written value is untouched | three triplet eighths occupy one quarter |
| **dots** | already inside `duration_beats`; nothing here re-derives them | the max(type-prefix, dots) rule lives in `_place_notes` |
| **whole rests** | a **LONE** `measure_rest` event **IS the bar, whatever the meter** | CLAUDE.md §10. A measure rest carries no note value to measure. **LONE**: one sharing its voice with anything else is summed and judged like any other event — two events cannot both occupy the whole bar |
| **meter** | `_bar_quarters` = `_legacy._measure_rest_beats`, with its 4.0 fallback REFUSED | no meter, no verdict: rule 8, in the direction that is easy to get wrong |
| **which meter** | the meter **in force in the FILE** — this bar's own if `Q.METER` filed one, else the last `<time>` this part declared | see §2 |
| **pickups / final bars** | **held out like any other short bar**, NOT special-cased by position | see §3 |

The bar then takes `_legacy._mxl_empty_measure` — the eventless branch's own
path — so it is a measure rest sized to the meter, and its dynamics and words
are still written. Its own counter is `bars_held_out_sum`; it is **never**
folded into `empty_bars_padded`, because *the detector found no event here* and
*we found events and they do not add up* have opposite repairs.

## 2. The meter in force is the FILE's, not the record's — and it cost 3,105 bars

The first cut judged each bar against `meter_at(run.meter, i)`, i.e. what
`Q.METER` filed for that bar's own system, and treated a bar with no such
verdict as UNASSESSABLE. The independent control then said Brahms still held
**3,132 bars that do not add up**, on an arm that had just held out 1,455.

The cause: **MusicXML has no way to un-declare a meter.** `<time>` is written
only where it CHANGES, so once a part has declared one it is in force for every
later bar — to music21, to Verovio and to a human. On Breitkopf Brahms 1,
`Q.METER` reaches only 1,977 of 5,803 bars-with-events; the other **3,826** were
being written into a file that was quietly asserting a length for every one of
them, while the exporter believed it had assessed nothing.

So `_part_xml` tracks `in_force` — the last meter it actually WROTE into an
`<attributes>` block, including one a LEADING tacet pad declared
(`_pad_tacet_span` now returns it) — and a bar with no meter of its own is
judged against that. Where the part has declared no `<time>` at all there is no
claim to hold the bar to, `in_force` is None, and nothing is held out.

**Two consequences that are 2.8's doing rather than its subject**, both in
`export.py`, named here so they are not read as part of Sean's rule:

1. An **eventless** bar on a meterless system used to be written as a
   four-quarter whole rest (`_measure_rest_beats(None)` is 4.0) into a part the
   file had already declared to be in 6/8. That is **232 bars on Brahms**, and
   after the hold-out they were the ENTIRE residue the control still saw. They
   are now sized by the carried meter (`empty_bars_sized_by_a_carried_meter`;
   `empty_bars_padded_without_meter` falls accordingly). This is not inventing
   a meter — it is refusing to write a length that contradicts the one the file
   already carries.
2. A **held-out** bar is likewise sized by the carried meter, for the same
   reason.

## 3. Pickups and final bars — held out, and why that is not a special case

A pickup bar and a final bar are legitimately short, and **nothing in the
record marks either**. Checked: `data/dossiers/*.json` carries
`total_measures`, `starting_meter`, `meter_changes`, `constant_meter`, `parts`,
`clefs_used`, `written_fifths_used` — and no anacrusis field; a recursive grep
for "pickup" and "anacrusis" over `tools/` and `data/` hits only
`tools/omr/training/musicxml_truth.py`, `training/orchestral_eval.py` and two
tests — nothing in `tools/omr/staged/`, no `Q.*`, nothing in the works rows.

So a genuine pickup is held out with the rest. Special-casing the first or last
bar BY POSITION would be the exporter deciding, from arithmetic alone, that a
short bar it cannot read is a short bar the engraver printed — and on a scanned
conductor's page the first bar of a SYSTEM is not the first bar of the piece.
The repair is a quantity that says *this bar is a pickup*, not a rule here.

## 4. No head is counted twice

`duration_narrowed` fires in `_place_notes`, **before a note ever reaches a
cell** — a narrowed note is refused there and is not among the events 2.8
measures. The ordering is therefore structural rather than checked: every event
2.8 sees is DECIDED, and no head can land in two buckets. Pinned from both
sides:

* one DECIDED quarter + one NARROWED quarter in 2/4 → held out; 1 under
  `duration_narrowed`, 1 under `bar_does_not_add_up`, total 2, `balanced: True`;
* two DECIDED quarters + one NARROWED in 2/4 → the two fill the bar, 2.8 does
  not fire, and the missing note is reported under `duration_narrowed`, which
  is where it belongs.

A **condensed staff's doubled Contrabass copy** (ROADMAP 2.1b) is held out
where its own events do not add up and is deliberately **NOT** counted: the log
holds that ink ONCE and the written side already subtracts it under
`notes_doubled_to_condensed_slot`. Counting it would charge the balance for a
row that does not exist. Litolff: 91 such bars
(`bars_held_out_sum_on_a_doubled_staff`). The two copies can genuinely disagree
— `_condensed_double` strips `glyph`, so `_voice_split` cannot place the copy's
notes into streams and judges it as ONE voice — which is recorded in the code
rather than papered over.

## 5. What it cost, per document

`python3 -m tools.omr.staged.export <record> --out <xml> --coverage <json>`;
base = `259773e5`'s `export.py`, arm = this branch, same tree, same records.
Full numbers in `out/compare.txt` and `out/arm-*.summary.json`.

| | engraved (Beethoven 5, 3 pages) | Litolff Beethoven 5 (whole mvt) | Breitkopf Brahms 1 (whole mvt) |
|---|---|---|---|
| staff-bars with events | 449 | 4,463 | 5,803 |
| **bars held out by 2.8** | **38 (8.5%)** | **1,879 (42.1%)** | **4,560 (78.6%)** |
| ...short / overfull | 34 / 4 | 1,027 / 761 | 3,716 / 844 |
| ...on a doubled staff (not counted) | 0 | 91 | 0 |
| ...judged by a CARRIED meter | 0 | 0 | 3,105 |
| ...two-voice bars | 0 | 111 | 637 |
| heads+rests into `bar_does_not_add_up` | 48 | 5,389 | 18,802 |
| `<note>` before -> after | 676 -> 666 | 12,375 -> 8,588 | 22,922 -> 7,814 |
| `written.notes` before -> after | 358 -> 329 | 7,878 -> 3,627 | 13,952 -> 1,136 |
| `written.rests` before -> after | 103 -> 84 | 1,980 -> 565 | 8,013 -> 1,161 |
| `measure_rests_read` | 214 -> 214 | 1,040 -> 1,040 | 355 -> 355 |
| `empty_bars_padded` | 1 -> 1 | 883 -> 883 | 455 -> 455 |
| balance `balanced` | True -> True | True -> True | True -> True |
| census `unaccounted` | empty | empty | empty |
| articulation / ornament / wedge / fermata / direction balance | all True | all True | all True |

**The Brahms figure is the finding, not a side effect.** 78.6% of its bars do
not add up, 3,105 of them against a meter the file carries rather than reads.
2.8 did not make that file worse; it made it stop claiming to be right.

## 6. The control that must hold

`probe/bar_sum_check.py` — a plain `xml.etree` reader of the FILE that imports
nothing from the exporter (CLAUDE.md §2 rule 7: a number that is exactly
another number is a computation, not a measurement). Per voice, chord members
skipped, grace notes skipped, `measure="yes"` treated as the bar, the meter in
force taken from each part's own last `<time>`.

| | base | arm |
|---|---|---|
| engraved | 450 assessed, **38 wrong** (34 short, 4 overfull) | 450 assessed, **0 wrong** |
| Litolff | 5,940 assessed, **1,879 wrong** (1,078 short, 801 overfull) | 5,940 assessed, **0 wrong** |
| Brahms | 6,405 assessed, **4,587 wrong** (3,717 short, 870 overfull) | 6,405 assessed, **0 wrong** |

**It can fail, and it did** — it is what caught the carried-meter hole of §2
(3,132 wrong bars on an arm that thought it had assessed nothing) and the
232-bar eventless-rest residue after that.

**One residue, named.** With `--strict-measure-rest` (a `measure="yes"` rest
judged by its `<duration>` rather than by the convention) Brahms shows **42
bars** where a READ measure rest carries 4.0 in a 3.0 bar; Litolff and the
engraved page show 0. A reader renders those as full-bar rests, so the FILE is
right and the `<duration>` is not. The repair is
`consequences.size_measure_rest`, upstream of this rule, and is not done here.
`acceptance.bars_add_up_control` uses that strict reading (it is
`bar_fill.bar_total`), which is why it reports Brahms 6,363 of 6,405 rather
than 6,405 of 6,405 — the two differ in exactly those 42 bars, and the
difference is the measure-rest convention, not a hole in the hold-out.

## 7. The count page: the roadmap's 68

`probe/count_page.py`, bars 49-82 of the Litolff export (the manifest's count
page, pdf index 3):

* **base: 408 staff-bars, 68 do not add up** — 40 short, 28 overfull; Violin 20,
  Contrabass 9, Cello 8, Flute 7, Viola 6, Clarinet 5, Horn 4, Bassoon 3,
  Trumpet 3, Oboe 2, Timpani 1. This reproduces the roadmap's figure AND its
  per-part breakdown exactly, which is what makes the before and the after one
  measurement rather than two.
* **arm: 408 staff-bars, 0 do not add up.** Not one is still wrong.
* `probe/window_diff.py`: **68 bars changed, all 68 became a marked empty bar,
  0 changed in any other way** — every one of the 68 was held out, and nothing
  else in the window moved.
* The export report NAMES 59 of them
  (`out/held-bars-litolff-count-page.json`). The nine missing are the condensed
  Contrabass doubles of §4 — held out, deliberately not named twice, because
  the log holds that ink once.

## 8. What is held out that a musician might have salvaged — the cost Sean accepted

* **A bar short by one note is thrown away whole.** 1,027 of Litolff's 1,879 and
  3,716 of Brahms's 4,560 held bars are SHORT — many will be a correct bar
  minus one missed notehead, and a musician would have kept what is there and
  added the one that is missing. After 2.8 there is nothing to add to.
  **5,389 heads and rests on Litolff and 18,802 on Brahms** are no longer in
  the file.
* **An overfull bar is usually right plus one spurious head** — 761 on Litolff,
  844 on Brahms — and the spurious head takes the bar with it.
* **The two-voice bars are the worst of it** — 111 on Litolff, 637 on Brahms —
  because a bar is held out when EITHER voice fails, so a correctly read upper
  voice goes out with a mis-split lower one.
* **On Brahms, 3,105 bars are held out against a meter no reader of that system
  ever confirmed.** If the carried meter is wrong there, we are discarding bars
  that were right. The lever is `Q.METER`'s reach, not this rule, and it is now
  the highest-value open thing on that document.
* **A genuine pickup or final bar is discarded** (§3); on these three documents
  that is a handful of bars and is not separable today.

What is NOT lost: nothing is invented, nothing is padded, no bar is re-timed,
every head is accounted for by name, the export report names each held bar by
(page, system, staff, cell), and `to_musicxml` still RAISES rather than
returning an unbalanced report.

## 9. The proxy it retired

CLAUDE.md §6a's machine proxy *bars that add up to the meter in force* is 100%
by construction after 2.8. In `tools/omr/acceptance.py`:

* `bars_add_up_to_the_meter_in_force` is **renamed** `bars_add_up_control`
  (same arithmetic, same function, NOT deleted). It is now a CONTROL on the
  EXPORTER rather than a proxy for the reading. It is not simply looser: it
  takes the MAX over voices where the exporter requires every voice to fill
  (looser), and judges a `measure="yes"` rest by its `<duration>` where the
  exporter applies the whole-rest convention (stricter) — which is the whole of
  its Brahms 42 (§6).
* **`bars_held_out_sum`** takes the proxy slot: count, fraction of bars with
  events, noteheads and rests moved, bars on a doubled staff, bars judged by a
  carried meter, and how many are named in the export report. Read as *what to
  fix next* (CLAUDE.md §6a), never as *are we winning* — driving it to zero by
  emitting fewer symbols would improve it and make the file worse.

## 10. Gates

* **Full suite** `python3 -m pytest tools/omr/tests -q`: **5,051 passed, 15
  skipped, 0 failed** (`out/pytest-full.txt`). The fast tier alone is 2,847
  passed / 3 skipped. The fast tier does **not** cover `test_staged_export.py`
  (slow tier, `durations.json` 7.83 s), and three of its fixtures had to be
  corrected because their bars never added up (two quarters declared 4/4; a
  two-quarter chord in 4/4). A fast-tier-only gate would have shipped that.
* `python3 -m tools.omr.staged.check` — **255 open findings**, identical to
  `259773e5` (`out/staged-check.txt`).
* `python3 -m tools.omr.acceptance --no-write` — runs end to end in this
  worktree in 30 s, all three documents `status=ok` (`out/acceptance.txt`).
* `tools/omr/tests/test_staged_bar_sum_holdout.py` run RED first against
  `259773e5`'s `export.py`: `out/tests-RED.txt`. Most of those failures are a
  `KeyError` on a report key the old exporter does not write, which is weaker
  evidence than it looks; the test file says so, and each positive control (a
  bar that DOES add up, a lone whole rest, a chord, a meterless bar) has a
  sibling asserting the refusal on a fixture differing by exactly one fact.

## 11. Files

```
probe/bar_sum_check.py   the independent control (§6)
probe/count_page.py      the count-page window (§7)
probe/window_diff.py     what changed in that window, and how
probe/compare.py         base vs arm, per document
probe/summarise.py       trims an arm report to something that belongs in the tree
out/arm-*.summary.json   counts, balances and a 40-row sample per document
out/held-bars-litolff-count-page.json   every held bar of the count page
out/compare.txt  out/count-page.txt  out/staged-check.txt
out/tests-RED.txt  out/pytest-full.txt  out/acceptance.txt
```

`out/.gitignore` keeps the exported `.musicxml` and the full `.report.json`
out of the tree — the Brahms report is 2.3 MB because it names all 4,560 held
bars, which is the right size for the artefact and the wrong size for git. Both
regenerate from the committed records with one command.

## 12. The engraved document's outside measures, base vs arm

`python3 -m tools.omr.acceptance --no-write --doc beethoven5-engraved`, run
once with `259773e5`'s `export.py` and once with this branch's, same tree, same
record (`out/acceptance-base-engraved.txt`, `out/acceptance.txt`):

| | base | arm |
|---|---|---|
| reading pooled F1 (page truth) | 0.947 | **0.947** |
| OMR-NED (against the encoding) | 0.1519 | **0.1629** |
| LilyPond barcheck failures | 3 | **0** |
| notes reaching file | 358 / 371 | 329 / 371 |
| bars add up [control] | 412 / 450 | **450 / 450** |

Three things worth saying plainly:

* **Reading F1 does not move at all.** It scores the READING against the page
  truth (`page_truth.py`), which is upstream of EXPORT — so 2.8 is invisible to
  it by construction, exactly as it should be. That it is unchanged is the
  control that 2.8 touched nothing but the file.
* **OMR-NED gets WORSE, and that is the expected direction.** It is symmetric
  and rewards emitting FEWER symbols only when the symbols removed were wrong;
  here 29 notes left the file, some of them right, and the metric charges for
  them. CLAUDE.md §6b: it is the engraved control only, and it must never be
  quoted as the reason a note-deleting rule is safe. **It is not evidence for
  or against 2.8** — Sean's decision is not a metric question.
* **LilyPond barcheck failures 3 -> 0** is a genuine downstream consequence: a
  held-out bar is a correct-length measure rest, so the bars that used to fail
  LilyPond's own `|` check no longer exist.

## 13. § funnel — why 78% of Brahms bars do not add up (2026-09-28, record c19cbca7)

Diagnosis lane, no pipeline code changed (a separate worktree; the record
below was read but never written to, and nothing in the concurrent Litolff
gather running alongside it was touched). Brief: START HERE item 5, *"the
lever is the meter/bar-sum funnel."* Read on tonight's fresh whole-movement
gather, `brahms1-breitkopf-whole-movement-20260928T110702Z.record.json`
(1.1 GB), provenance `{commit: c19cbca7b733, dirty: True}`, loaded exactly
ONCE via `record_io.load_record` and pickled to scratch (CLAUDE.md §4b: the
one sanctioned reader; a naive read of `considered`/`correlated`/`basis`
would silently see a pool reference, but neither field was read here).

**Reproduced, not trusted, against the record's own `.coverage.json`**:
4,513 of 5,792 bars-with-events held out = **77.9%** (the brief's "~78%" and
"4,513 of 5,792" both check out exactly), 18,629 noteheads+rests held,
**965** pitched notes reach the file (`written.notes`), and
`bars_judged_by_a_carried_meter` = **3,948** — not the brief's 3,105, which
is ROADMAP's own line from the 2026-09-23 gather; tonight's is 843 higher.
**Assume every number in a brief is stale until reproduced — this one was.**

The dossier (`data/dossiers/brahms-sym1-mvt1.json`, `source_kind: encoding`,
diagnosis only here, never a pipeline input): `starting_meter` 6/8,
`meter_changes` has exactly ONE entry, measure 8 → 9/8, back to 6/8 at
measure 9, `constant_meter: False`. **The brief's own line needed checking,
and checking it mattered**: the movement is 6/8 throughout with one
exceptional bar, not "6/8 in the introduction and the Allegro" as if those
were two agreements to verify separately.

### A fact independent of any classification choice below

Of the 4,513 held bars, the meter they are JUDGED against
(`bars_held_out_sum.held[*].want_quarters`) is **4.0 on 4,126 of them
(91.4%)** — a 4/4 the plate does not print anywhere near this movement
outside measure 8's single 9/8 bar — against 361 at 3.0 (the true 6/8) and
26 at 9.0 (a misread `9/4`, the same failure mode `omr-meter-carry-brahms
-2026-09/FINDINGS.md` named on a 4-page slice three weeks ago, now measured
whole-movement). This holds regardless of how a bar's own reading is scored.

### The partition

Per held bar: most-specific-first. `duplicate_rest_detection` (below) is
checked first — it is a record-level contradiction, not a numeric
coincidence. Then `meter_wrong`: the bar's own voice sum(s) agree EXACTLY
with the TRUE meter (3.0q, or 4.5q at measure 8) while the judged meter does
not — the reading was right, the judgment wasn't. Then `dots`: short by a
plausible dot deficit (0.125/0.25/0.375/0.5/0.75q) — but ONLY kept here if
the cell's own `Q.AUG_DOT`/`Q.DOT_ROLE` verdicts are absent or ABSTAINED;
where a dot IS filed and DECIDED, the numeric match is a coincidence and the
bar falls through to the rules below. Then a clean ≥2x multiple
(`voices_merged_or_chord_split`), then short/over by ≥0.5q
(`missing_events`/`extra_events`), then a 3:2 correction that lands exactly
(`tuplet`), then `other`.

| cause | whole movement | count page (pdf idx 1) |
|---|--:|--:|
| `missing_events` | 2,315 (51.3%) | 38 |
| `meter_wrong` | 859 (19.0%) | 20 |
| `extra_events` | 652 (14.4%) | 41 |
| `dots` | 281 (6.2%) | 13 |
| `duplicate_rest_detection` | 240 (5.3%) | 19 |
| `other` | 133 (2.9%) | 1 |
| `voices_merged_or_chord_split` | 33 (0.7%) | 2 |
| **total** | **4,513** | **134** |

⚠️ The count page's own total here is 134, not 68 — 2.8's ROADMAP line
quotes 68 of 408 on the **Litolff** count page, a different document; this
Brahms count page has not been separately adjudicated by Sean under
`omr-cleanup-count-2026-09/CATEGORIES.md`, and this funnel is not that
count. `dots` is reported net of the coincidence check above: the raw
numeric match fires on 701 bars; 420 of those (60%) have a DECIDED
`dot_role` in the cell and are reclassified away — mostly into
`missing_events`.

### Top 3 causes, what corroborates each, what it would release

**1. `missing_events`, 2,315 bars (51.3%).** Short by ≥0.5q against the TRUE
meter. Corroborated against the record for all 2,315 cells (not a sample —
every held cell's glyph-level `Q.DURATION`/`Q.GLYPH_OWNER`/
`Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdicts were read): the dominant refusal by
a wide margin is `owned_by_another_staff` (6,008 `glyph_owner` verdicts
across those cells deciding OUT to a neighbouring staff — 2.6's contest,
which "DROPS THE LOSER, never relocates it," CLAUDE.md §10), then
`duration_narrowed:beams_ambiguous` (2,472 — the beam-level reader could not
tell how many flags/beams, so the note contributes nothing), then
`not_a_notehead:too_narrow`/`clipped_fragment` (1,486 combined — 2.4a's
width-floor refusal). ⚠️ **This is evidence about SCALE, not about which
side of the contest is right.** 2.6's own FINDINGS say plainly *"Not one of
the 161 [Litolff near-neighbour contests] has been read against a
print"* — and Breitkopf (the SHATTERING plate, CLAUDE.md §10) was never
sampled there at all. 6,008 refusal instances on ONE document, tonight, is
the strongest argument yet that 2.6's own open question is overdue, but
releasing it does not by itself fix 2.8: a note correctly relocated to its
true staff still has to pass THAT staff's own beam/width checks.

**2. `meter_wrong`, 859 bars (19.0%).** The bar's own sum agrees with the
TRUE meter but is judged against a carried or misread 4.0q — the reading is
already right. This is 2.12d's own premise (*"a mid-staff `timeSig*` states
a meter only where the system agrees"*), priced whole-movement for the
first time tonight: `want_quarters` is 4.0 on 91.4% of ALL held bars (see
above) and `meter_carried_in_file` is True on 3,948 of 4,513 — once ONE
system states an uncorroborated 4/4, `in_force` (§2 above) hands it to
every later bar that never declares its own `<time>`, and 2.9's
header-box reading never gets a second chance mid-document. Releasing this
bucket needs no notehead-level fix — the 859 bars' own readings are already
correct.

**3. `extra_events`, 652 bars (14.4%).** Over the TRUE meter by ≥0.5q, not
matching the duplicate-rest signature. ⚠️ **Not reduced to one mechanism**:
`glyph_owner` verdicts inside these cells split almost evenly between
confirming this staff (1,752) and moving away (1,663) — unlike
`missing_events`, this is not dominantly a cross-staff GAIN. Deltas range
0.5q (one plausible extra event, the cleanest cases) to 7.0q (something
closer to two bars' worth of ink read into one cell — crop
`extra_events-1-0-0-5`, measure 14, a dense system-start bar). Releasing it
needs per-bar attention, not one rule; not further reduced in this pass.

### The clean find: `duplicate_rest_detection`, 240 bars (5.3%) — not asked for, cheapest lever in the funnel

240 held bars — 189 of them exactly 2 duplicates, the rest 3–8 — carry TWO
OR MORE independently **DECIDED** `Q.DURATION` rest verdicts in the SAME
cell with IDENTICAL `beats` (201 of 240 at 4.0 — a whole rest counted
twice; 24 at 1.0; 13 at 0.5; 2 at 2.0), spread across **14 of the
document's parts** and staves 0–13 — not one instrument, not one page.
`_bar_holds_out`'s own "a LONE measure rest IS the bar" rule (§1/§3 above)
fires only when `len(stream) == 1`; with two rest events the stream is not
lone, so both are summed literally and the bar reads double or worse.
Named example, verified on the record: `cell/2/1/0/7` (page 2, system 1,
staff 0, cell 7, measure 37) carries `glyph/2/1/0/7/0` and
`glyph/2/1/0/7/1`, BOTH decided `{beats: 4.0, is_rest: True, reason:
rest_class}` — the same physical whole rest, boxed twice, and nothing at
GATHER or ADJUDICATE collapses the pair before EXPORT sums them. This is
the one cause in this funnel that is fully mechanical — no reading
ambiguity, no cross-staff judgment call — and it needs no print check to
act on: a crop would only confirm there is one rest on the page where the
record already holds two contradictory verdicts about it.

### Crops

12 crops, 4 per top-3 cause,
`benchmarks/omr-bar-sum-holdout-2026-09/out/print/funnel-2026-09-28/`, each
with the staff drawn (the SAME `Q.STAFF_LINES` row the reader used), the
bar's own `Q.CELL_BOX` frame bracketed in red, and `judged meter / true
meter / read sum` written in the margin. Sidecars are `VERDICT_none_yet:
null`. Script and bar list: `probe/crop_funnel.py` +
`probe/funnel_bars.json` — self-contained, reads the record ONCE for
geometry only (`cell_box`/`staff_lines`/`staff_spacing`), renders pages
straight off the PDF (no detector, no re-gather, no re-adjudication).

| cause | file | measure | judged | true | read sum |
|---|---|--:|--:|--:|---|
| meter_wrong | `funnel-brahms1-breitkopf-meter_wrong-1-0-0-6.png` | 15 | 4.0 | 3.0 | [3.0] |
| meter_wrong | `funnel-brahms1-breitkopf-meter_wrong-1-1-0-2.png` | 18 | 4.0 | 3.0 | [3.0] |
| meter_wrong | `funnel-brahms1-breitkopf-meter_wrong-2-0-0-1.png` | 25 | 4.0 | 3.0 | [3.0] |
| meter_wrong | `funnel-brahms1-breitkopf-meter_wrong-2-0-0-4.png` | 28 | 4.0 | 3.0 | [3.0] |
| missing_events | `funnel-brahms1-breitkopf-missing_events-0-0-0-1.png` | 2 | 3.0 | 3.0 | [0.625] |
| missing_events | `funnel-brahms1-breitkopf-missing_events-0-0-0-5.png` | 6 | 3.0 | 3.0 | [0.25] |
| missing_events | `funnel-brahms1-breitkopf-missing_events-1-0-0-4.png` | 13 | 4.0 | 3.0 | [1.031] |
| missing_events | `funnel-brahms1-breitkopf-missing_events-2-0-0-2.png` | 26 | 4.0 | 3.0 | [0.625] |
| extra_events | `funnel-brahms1-breitkopf-extra_events-1-0-0-5.png` | 14 | 4.0 | 3.0 | [5.5] |
| extra_events | `funnel-brahms1-breitkopf-extra_events-2-0-0-5.png` | 29 | 4.0 | 3.0 | [4.5] |
| extra_events | `funnel-brahms1-breitkopf-extra_events-2-1-0-0.png` | 30 | 4.0 | 3.0 | [3.5] |
| extra_events | `funnel-brahms1-breitkopf-extra_events-3-0-0-4.png` | 43 | 4.0 | 3.0 | [3.5] |

Each PNG has a sidecar `.json` naming the subject, the refusal evidence
found in that cell, and `VERDICT_none_yet: null` for Sean.

### Recommended next roadmap item

Not 2.12d (already `todo`, and it only reaches `meter_wrong`, 19% of this
funnel) and not a restatement of 2.6's open print-check (already named
there, and it would need Sean's eyes on crops 2.6 itself should cut, not
this lane's). The one NEW, fully-diagnosed, mechanically cheap finding this
funnel turned up is `duplicate_rest_detection` — added to ROADMAP.md as
**2.15** (next free Phase 2 number; 2.13 and 2.14 are taken).

### What contradicted this brief

The 3,105-carried-meter figure (stale by 843, §above); the count-page total
(134 here, not 68 — different document); the "6/8 in the introduction and
the Allegro" framing (one constant meter with one exceptional bar, not two
regions to separately confirm); and the working assumption that `dots`
would be a clean bucket — 60% of the raw numeric matches are coincidental
once checked against `Q.DOT_ROLE`.

⚠️ **One more, worth stating plainly rather than leaving implicit.**
ROADMAP's work-order item 5 (*"the lever is the meter/bar-sum funnel, not
the accidental reader"*) is about **Litolff**'s 2.7 gate (pdf-index 3, 18
owned heads sitting in bars 2.8 holds out) — this brief pointed a Litolff
sentence at a Brahms diagnosis. Everything measured above is Brahms only;
Litolff's own funnel has NOT been run and its shape need not match (Litolff
is the MERGING plate, Brahms the SHATTERING one — CLAUDE.md §10 — and
`omr-meter-carry-brahms-2026-09/FINDINGS.md` §10 already found the two
plates fail in opposite ways: Litolff has abstaining systems and no wrong
carried meter to serve them, Breitkopf the reverse). **2.15 (the duplicate
rest) and 2.12d (the meter_wrong lever) are recommended from Brahms
evidence and are not yet shown to move Litolff's 18 owned heads at all** —
that needs Litolff's own count-page funnel, not an assumption that one
document's partition transfers to the other.

## 14. ROADMAP 2.15 — one physical rest, boxed more than once

Branch `claude/duplicate-rest-2.15`. `adjudicators/family_precision.py`'s
`adjudicate_rest_is_not_a_rest` (ROADMAP 3.4g, HUMAN WITNESS ONLY until now)
grows a geometric rule that runs after the human one: two rest glyphs in one
cell whose `Q.GLYPH_BOX` boxes overlap (IoU) are the SAME physical mark.
Same class, same overlap → the higher-confidence box survives, the other is
refused `rest_is_a_duplicate_box`. Different class → NEITHER survives (rule
8: cannot tell is never converted into a pick), and the bar loses that
event's contribution; ROADMAP 2.8 holds it out if that now leaves it short.
`export._place_notes` already read `Q.REST_IS_NOT_A_REST` first, before
duration or placement, so no export-side change was needed — this is
GATHER-adjacent evidence (`Q.GLYPH_BOX`, `Q.REST`'s class) read at ADJUDICATE,
never a second rest-VALUE geometry (that stays lane 2.12b-cal's, `rhythm.py`).

### §14a. The work order's own claim did not survive contact with the record

ROADMAP 2.15 (and the funnel that produced it, §13 above) said the named
example's two boxes "overlap substantially." Measured on the record
(`glyph/2/1/0/7/0` / `.../1`, Brahms provenance c19cbca7): **IoU 0.16.**
Crop `r215-brahms-collapse-glyph-2-1-0-7-1.png` shows why the word was
wrong without the FINDING being wrong: one filled rectangle (a whole rest),
two detector boxes covering roughly the left and right half of it — the
SHATTERING plate (CLAUDE.md §10) fragmenting one mark's ink, not two boxes
drawn on top of each other. **"Substantially" describes the WRONG geometry**
(two near-identical boxes) for the RIGHT mechanism (one mark read twice).

### §14b. Why the mark is two glyphs — two DIFFERENT causes, not one

Cropped and visually confirmed both, across Litolff and Brahms (8 crops,
`out/print/r215-2026-09-28/`, `VERDICT_none_yet: null` for Sean):

* **Same class, moderate overlap (IoU 0.03–0.71 on both documents, never
  higher).** The SHATTERING/print-quality case: a filled rectangle (or a
  quarter/eighth rest's hook) breaks into two ink fragments and the
  detector boxes each one, both correctly classed. Crops at IoU 0.05, 0.16,
  0.37, 0.71 (Brahms) and 0.43 (Litolff) are all this shape.
* **Different class, high overlap (IoU 0.80–1.00 on Brahms; the Litolff
  disagree crop is lower but still a real overlap, §14d).** A role-twin
  read: one physical mark, two class guesses. One Brahms crop
  (`rest8th`/`rest16th`, IoU 0.98) is a single hook-shaped mark with both
  boxes drawn almost exactly on top of each other. **One Litolff crop
  (`glyph/2/1/6/13/5`/`.../8`, `restQuarter`/`restWhole`) turned out to be a
  THIRD cause the brief did not name**: a STAFF LINE crossing through a
  genuine quarter rest got its own box, misclassified `restHalf` (a
  horizontal rectangle sitting on a line reads like a half rest at a
  glance). Refusing both is still the right answer — one of the two boxes
  is not ink from a rest at all, and nothing at this stage can tell WHICH
  — but it is a different mechanism from the role-twin case, filed under
  the same reason because the record cannot yet tell them apart either.

Neither cause is "two detector boxes on one ink after NMS failed to merge
them" in the sense the brief's phrasing suggested (identical boxes, an NMS
threshold miss) — the record's own IoU distribution has **no population
near IoU 1.0 for a SAME-CLASS pair** (max measured 0.7113 on Brahms, 0.7211
on Litolff, on populations of 1,713 and 154 pairs respectively). The
IoU-near-1.0 cluster belongs entirely to DIFFERENT-class pairs.

⚠️ **Supersession must be resolved before any of this is measured.** A
naive scan of `outcome == "decided"` over every `Q.DURATION` verdict row —
what this lane's own first pass did, and what the ORIGINAL funnel's
`verdicts_by_cell` extraction (§13, `extract_from_record.py`) also did —
counts an EVALUATE-stage revision (`consequences.reconcile_duration`)
alongside the ADJUDICATE-stage reading it superseded as if they were two
glyphs. On the ENGRAVED control this manufactured **214 fake "duplicates,"
100% of them one subject counted twice**, before `export.Record`'s own
resolution rule (drop every row a later one SUPERSEDES, take the last of
what remains) was applied to the probe. After that fix, engraved shows
**zero** same-cell rest pairs of any kind — the clean control this
document is supposed to be.

### §14c. The IoU gap, and where it was cut

Every pair of rest glyphs with a STANDING decided `Q.DURATION` verdict in
one cell (supersession resolved), Brahms and Litolff:

| population | n pairs | shape |
|---|--:|---|
| same class, IoU exactly 0 | 1,284 / 83 | genuinely unrelated (two voices, or a stray misdetection elsewhere) |
| same class, IoU > 0 | 429 / 71 | ONE mark, smoothly 0.03–0.71, no internal gap |
| different class, IoU exactly 0 | 4,399 / 286 | unrelated |
| different class, IoU 0.80–1.00 | 79 / — | role-twin, one mark |
| different class, IoU 0.15–0.75 (sparse) | 13 / small | the third cause, §14b |

`REST_DUPLICATE_IOU_MIN = 0.02`: the smallest round value clearing the
Litolff noise floor (0.0019, 0.016 — two boxes ~1,000 canonical units
apart, not the same mark) while catching every crop-confirmed real pair
(0.028 and up). One threshold serves both same-class and different-class
comparisons because `Q.DURATION` has not run yet at this point in
`adjudicate.ORDER` — the rule reads the CLASS `Q.REST`/`Q.GLYPH_BOX` already
filed at GATHER, never a beats figure it cannot see.

### §14d. Per-document pricing (GATHER once, re-adjudicate `Q.REST_IS_NOT_A_REST` only, re-export)

Base = the saved record exactly as gathered (this rule never ran on it,
no flag exists to disable it). Arm = the SAME record with the newly-decided
refusals appended (`supersedes` set where an old verdict existed) — base
and arm differ in EXACTLY the rows this fix adds. `Q.REST_IS_NOT_A_REST` is
the only quantity re-adjudicated: nothing upstream of it in `ORDER` reads
it and nothing downstream except EXPORT does, so a full pipeline re-run
would price the same number at far higher cost.

| | engraved | Litolff | Brahms |
|---|--:|--:|--:|
| duplicates refused (collapse) | 0 | 87 | 693 |
| duplicates refused (disagree, both) | 0 | 24 | 189 |
| **total refused** | **0** | **111** | **882** |
| `bars_held_out_sum` base → arm | 36 → 36 | 1,879 → 1,867 | 4,513 → 4,424 |
| `<note>` written base → arm | 331 → 331 | 3,627 → 3,656 | 965 → 888 |
| `<rest>` written base → arm | 84 → 84 | 565 → 574 | 1,255 → 1,197 |
| measure rests base → arm | 214 → 214 | 1,040 → 1,040 | 348 → 348 |
| 2.8 control (bar_sum_check.py), base | 450/450 exact | 5,940/5,940 exact | 6,405/6,405 exact |
| 2.8 control, arm | 450/450 exact | 5,940/5,940 exact | 6,405/6,405 exact |

**2.8's independent control (mandatory, CLAUDE.md §6b) holds on all three
documents in BOTH arms: 0 exported bars whose sum ≠ meter.** This fix
changes WHICH bars are held out, never whether the control passes.

Engraved is the clean control end to end: 0 duplicates found, 0 refused,
nothing moves. This is the expected shape, not a null result — the
detector on a Verovio render does not fragment ink the way a scan does.

### §14e. Brahms: 129 of the ROADMAP-named 240 released, 111 still held for a DIFFERENT reason, 65 newly held elsewhere

The 240 count in ROADMAP 2.15's own line is itself the OLD (unresolved-
supersession) measurement, carried over from §13 without being
re-verified here — checked directly (`by_cause_bars2.pkl`, the funnel's
own saved bar list) rather than assumed correct:

* **0 of the 240 have the supersession artefact** (a repeated subject in
  one bar's `subjects` list) — §14b's fake-duplicate bug did not happen to
  reach this specific bucket, so the 240 figure itself is not inflated by
  it.
* **129 of 240 are RELEASED** — no longer held out once the duplicate
  collapses to one rest. Of the 153 bars in the 240 with exactly two
  subjects, 134 show the intended pattern (exactly one glyph refused, one
  survives); 19 disagree with my rule entirely (their two subjects are not
  geometrically overlapping under this measurement) and are left as-is.
* **111 of 240 are STILL held out** — the duplicate was real and is now
  collapsed, but the bar has a SECOND, independent problem (e.g.
  `cell/4/0/0/0`: want 3.0q, reads 4.0q even after the collapse — an extra
  event elsewhere in the same bar). The funnel's own "most-specific-first"
  classification named ONE cause per bar; a bar can have two.
* **65 bars NOT in the original 240 became NEWLY held out.** These are
  bars where a duplicate (usually a disagreeing pair, which removes BOTH
  readings rather than collapsing to one) was previously providing enough
  duration, by accident, to make the bar's sum match the meter it was
  being judged against. Removing the accidental padding reveals the bar
  does not actually add up — the check catching something the double-count
  was hiding, not a regression. `154 released − 65 newly held = 89 net`,
  matching `bars_held_out_sum`'s own base→arm delta.

This gate is NOT "0 of the 240 still hold out" (ROADMAP 2.15's own gate,
written before this measurement) — it is roughly half of them, because a
Brahms bar's held-out reasons compound (§13) and this item fixes exactly
one of them. The gate that DOES hold: **every one of the 882 refused
glyphs is a real duplicate box, confirmed by IoU and, for 8 of them, by a
printed crop**, and 2.8's control never breaks.

### §14f. Tests, RED → GREEN

`tools/omr/tests/test_staged_duplicate_rest.py`, run RED against
`family_precision.py` before this branch's edit (git-stashed, re-run,
restored): 4 of 8 fail — the two adjudicator tests that assert a REFUSAL
(same-class collapse, different-class both-refused), the 3-way cluster
test, and the `detail["duplicate_of"]` test. The other 4 (the disjoint
control, both export fixtures) pass unchanged, which is correct — they
exercise `export._place_notes`'s existing, already-shipped consumer of
`Q.REST_IS_NOT_A_REST`, not this branch's new rule. GREEN: 8/8. No test
asserts on module source text.

### §14g. Landing

`python3 -m pytest tools/omr/tests -m "not slow" -q`: **3,460 passed, 3
skipped**, 0 failed (`out/pytest-fast-r215.txt`). `python3 -m
tools.omr.staged.check`: **251 open findings**, identical to the tree
before this branch (`source_text_tests` moves 216→217 test files scanned,
`open=46` unchanged — the new test file adds no source-text assertion).

### §14h. What contradicted this brief

The named example's boxes do not "overlap substantially" (IoU 0.16, §14a).
The mechanism is not one NMS-miss on identical boxes but TWO geometrically
distinct causes (§14b), plus a third (a staff line crossing a rest,
misclassified) neither the brief nor this lane's first pass anticipated.
The 240-bar gate does not clear to 0 — 111 stay held for reasons this item
does not touch, and 65 bars elsewhere become newly (and correctly) held
out. The measurement instrument itself (verdict supersession) had to be
fixed before any of the above could be trusted — the same bug class
CLAUDE.md already names four times over, found a fifth time here on the
engraved control specifically because it is the one document clean enough
to show 214 fake findings as 214, not as noise inside a real signal.

## 15. ROADMAP 2.19 — why each held bar on Breitkopf p1 is held, after the 09-28/29 merges (2026-09-29)

PATH: STAGED. Branch `claude/held-bars-2.19`, off `origin/main` `1983a9a2`
(2.6c/2.6e ownership, 2.18/2.18b/2.18c durations, 3.2b ties and 2.15
duplicate rests are all in the tree — checked with `git log --merges`, not
with the ROADMAP lines, three of which still read "not merged").

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

CLAUDE.md §10: *a whole rest means the BAR whatever the meter*; a glyph box
that a DECIDED verdict has refused (not a notehead, not a rest, owned by
another staff) is not in the bar, which is exactly the rule
`export._place_notes` already applies. A crop where a box set aside that way
is actually a second note or rest of the bar would falsify it (crops #5–#7
are that check). The printed meter used for diagnosis (9/8 at bar 8, 6/8
from bar 9) was read off the page by eye (crops #1 and #3). It is never a
pipeline input. NOT CONFIRMED with Sean.

### §15a. The gather, and why the brief's "~67%" does not reproduce

One fresh gather of pdf idx 1 on `1983a9a2`: clean tree, 600 dpi, scan
weights, `--no-surya` (OCR/Tesseract ON, roster ON), 1.5 min. The brief's 67%
came from 3.2c's gather. 2.18's gather was `--no-surya --no-ocr --no-roster`,
and there system 1 had NO meter in force (103 bars unjudged). With OCR on,
system 1's bars are judged against the meter the FILE carries into them, so
this page holds **156 of 169 bars-with-events (92.3%)**, 71 of them judged
by a carried meter. `probe/held_funnel_2_19.py` re-decides the record with
the tree it sits in (`review.rerun`) and wraps `export._bar_holds_out` at run
time, so the rule is not restated. Its control (bars it captured ==
the report's `bars_held_out_sum`) passes, 156 = 156. Litolff pdf idx 3 was
gathered alone as the MERGING control and is DEAD for this question: a
single page carries no meter (254 of 254 bars `without_a_meter`;
`bar_sum_check` reports "INSTRUMENT DEAD"). The Litolff control below is
therefore the 4-page `_shared-records/beethoven5-p1-p4.record.json` (an
09-11 gather), re-decided on this tree.

### §15b. The fact that dominates everything: every held bar is judged against 9/4

**All 156 held bars are judged against 9.0 quarters.** The page prints **9/8**
at bar 8 (system 0's header) and a **6/8** change at bar 9 on every staff.
System 1 is 6/8 by carry. `Q.METER` on system 0 is DECIDED 9/4 by vote
(`share 1.0`, 10 staves). The header template reads **9/4 on all ten staves
it reads** (score ~0.51, runner-up 6/4, margins 0.04–0.09), so the Breitkopf
8 is being matched as a 4. The only 8 on the record is the detector's own
`timeSig8` at the header (staves 6 and 8, conf 0.29 and 0.36), and it sits on
staves where the template abstained. **Nothing reads** the bar-9 6/8 change.
Its digits are detected as hollow noteheads (crops #3 and #4), and 23 of the
26 held bars in cells 0–1 of system 0 carry such a "head". System 1's meter
correctly ABSTAINS (`carry_not_corroborated`: its one assessable bar summed
3.0 against 9/4). The FILE still carries 9/4 there (§2's `in_force`), so 2.8
judges system 1 against it too. **This is a READER failure (the template
reads the digit 8 as 4 on this plate) plus a DETECTOR failure (meter digits
boxed as noteheads, no mid-system meter read). It is not a connection, and
nothing is built for it here.**

### §15c. The minimal-cause partition (`probe/classify_held_2_19.py`)

A held bar is released under a fix set when every voice either IS the bar
or sums exactly to the PRINTED meter. Without `M`, a voice landing on the
wrong 9.0 is a wrong bar written, not a release. The fixes are SIMULATIONS:

- `M`: the printed meter.
- `W`: a lone, unmarked, dotless whole rest is the bar.
- `H`: drop hollow heads at the printed meter's x.
- `E`: drop a quarter rest within 60 units of the cell edge (a barline read
  as a rest).
- `V`: one voice (merge the streams).
- `N`: restore narrowed heads with one of their own candidates.
- `R`: restore `not_a_notehead` heads.
- `A`: restore an abstained rest.
- `D`: add or remove one dot on one event.
- `S`: merge two events less than 40 units apart.
- `B`: one note read one beam level off.

The table gives each bar's smallest releasing set, ties grouped. It closes.

| minimal set | bars (base) | what it is |
|---|--:|---|
| `W` | **32** | a lone whole rest that `size_measure_rest` did not mark (12 blocked by refused boxes in the cell, 20 on system 1 where the meter abstains) |
| `M` | **26** | the reading is already right; only the meter is wrong |
| `MV` | 8 | + one line split into two voices by stem direction alone |
| `MB`, `MD\|MB`, `MD` | 9 | + one note a beam level or a dot off |
| `MVB`, `MVN\|MVB`, `MVR\|MVB`, `MVNRD\|MVNRB` | 7 | + voice split and one more |
| `ME`, `WE` | 5 | + a barline read as a quarter rest at the cell edge |
| `MH`, `MHR`, `MHB`, `MHRD`, `MHVB`, `MHVNRB`, `MHR\|MHB\|MSB`, `MHN\|MHR\|MHB` | 9 | + the meter digits read as heads |
| `MN`, `MN\|MB`, `MN\|MD\|MB`, `MND\|MNB` | 6 | + a narrowed head restored |
| `MRB`, `MR\|MD\|MB`, `MDS\|MSB` | 3 | other pairs |
| `none_of_these` | **51** | no modelled combination releases them: 36 over-full, 13 short, 2 mixed; 18 hold a narrowed head; 9 are bar 8 (9/8, eighths read as 32nds) and 7 are bar 9 |
| **total** | **156** | |

**Single fixes that release a bar outright:** `W` **32** and `M` **26**.
Every other fix releases **0** alone, because every other repair also needs
the meter. **Necessary fixes** (present in every minimal set of a releasable
bar): `M` 71, `W` 34, `V` 17, `B` 13, `H` 8.

### §15d. The top CONNECTION class, built: `size_measure_rest` counted boxes that had already left the bar

The top class, `M`, is a reader and detector failure (§15b). The next class,
`W`, is a connection. `consequences.size_measure_rest` (EVALUATE) fires only
where the whole rest is the cell's ONE standing `Q.DURATION`. `_standing`
returned a duration for every glyph box the cell was cut with, including
boxes a DECIDED verdict had already taken out of the bar:

- the barline, boxed as `noteheadBlack` and refused `too_narrow` (crop #5);
- a second box on the same rest, refused `rest_is_a_duplicate_box` (#6);
- the next staff's whole rest seen through the pad, which `glyph_owner`
  DECIDED belongs to staff 8 (#7). EXPORT reports this one as
  `rest_duration_abstained` because its duration check runs first.

EXPORT writes none of these boxes, so the bar held one whole rest. The rule
still declined to mark it, 2.8 summed it as 4.0 against the meter, and the
bar was held out.

**The fix (EVALUATE; it FOLLOWS):** `_left_the_bar` names the DECIDED verdict
that removed a box: `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` True,
`Q.REST_IS_NOT_A_REST` True, or `Q.GLYPH_OWNER` naming another staff through
`adjudicate.is_relocated_copy` (imported, the same test EXPORT uses). Those
boxes are set aside before the "only one" test. The removing verdicts join
the new verdict's `basis`, and `detail.set_aside` lists the boxes, so the
marking can be traced. Only a DECIDED removal counts. An abstained refusal, a
narrowed head, an abstained rest of this staff, a head its own staff kept and
an undecided meter all still block (rule 8). The new reads are declared to
`evaluate.run_over` through `reads_beyond_cause`. No flag.

Tests are in `tools/omr/tests/test_staged_measure_rest_left_the_bar.py`. They
ran RED on the unrepaired tree first (`out/r219/tests-RED.txt`: 4 failed, 8
passed; the 8 are the positive and negative controls, including a real head
beside a refused twin) and are GREEN 12/12. No test reads source text.

### §15e. Priced on the same record: base tree (`git archive HEAD`) vs arm, re-decided in-process

| | Breitkopf p1 | engraved p0–p2 | Litolff p1–p4 (09-11 gather) | Litolff p3 alone |
|---|--:|--:|--:|--:|
| bars held (`bars_held_out_sum`) | **156 → 144** | 38 → 37 | **300 → 270** | 0 → 0 (no meter) |
| released / newly held | 12 / 0 | 1 / 0 | 30 / 0 | 0 / 0 |
| `measure_rests_read` | 11 → 23 | 214 → 215 | 278 → 308 | — |
| `<note>` elements, notes, rests | unchanged (186; 8; 10) | unchanged | unchanged | unchanged |
| `bar_does_not_add_up` rows | 856 → 844 | 47 → 46 | 794 → 764 | — |
| 2.8 control `bar_sum_check.py`, base / arm | 170/170 exact / 170/170 | 450/450 / 450/450 | 1,183/1,183 / 1,183/1,183 | dead / dead |

What was set aside in the released bars:

- **Breitkopf:** `too_narrow` 5, duplicate box 2, both 1, a neighbour-staff
  rest 4.
- **Litolff:** owner elsewhere 8 (+3 combined with another), duplicate box 5,
  `too_narrow` 4, `clipped_fragment` 4, `belongs_to_a_nearer_staff` 2 (+3
  combined). Three Litolff bars hold a NARROWED head that `glyph_owner`
  DECIDED belongs to staff 4. Checked on the record: set aside correctly.
- **Engraved:** one release, P6 Clarinet 2 m.8, a whole rest beside a
  `noteheadWholeOnLine` refused `clipped_fragment`. The Verovio truth
  (`out/fixture/beethoven-sym5-mvt1-m1-24.musicxml`) has a whole-bar rest
  there.

Notes and rests written do not move on any document, because the rule only
releases rest bars (its bound). **What it does NOT release:** the 20
system-1 `W` bars (the meter abstains, so they need `M`) and every other bar
on this page (all need `M`).

### §15f. What is next, ranked by what it would release on this page

1. **The meter reader** (`M`: necessary in 71 bars, releases 26 outright,
   and gates every class except `W`). Two failures: the template reads the
   Breitkopf 8 as a 4, and a system-wide mid-system meter change is read by
   nothing while its digits are boxed as noteheads. This is a GATHER and
   detector item, not a connection (crops #1–#4).
2. **Voice split by stem direction alone** (`V`: necessary in 17 bars).
   `voicing.split_events_into_voices` V1 makes two voices wherever an
   up-stem and a down-stem appear anywhere in the bar, so one melodic line
   crossing the middle line becomes two half-bars. This needs a convention
   answer from Sean first (rule 3): does a bar with no two simultaneous,
   opposite-stemmed events ever print two voices?
3. **Meter digits read as heads** (`H`: 8). This goes away with item 1 if
   the reader reads the change. Otherwise it needs a GATHER overlap test
   against the meter's position.

### §15g. Crops for Sean

Eight crops, `out/print/held-2026-09-29-*.png`, with manifest
`out/print/held-2026-09-29-manifest.json` (`VERDICT_none_yet: null`), cut by
`probe/crop_held_2_19.py` from the PDF at 600 dpi. The staff each bar is
filed on is a green band with its `Q.STAFF_LINES` drawn; a second staff (an
owner) is blue; the bar's `Q.CELL_BOX` x-span is two red verticals; the
subject boxes have red corners. The frame control
(`crop_losers_2_6b._frame_ok`) passed on all eight.

- #1–#2: the bar-8 9/8 read as a head.
- #3–#4: the bar-9 6/8 read as heads.
- #5–#7: released bars (barline junk, a duplicate box, staff 8's rest).
- #8: a system-1 whole-rest bar still held because the meter abstains.

### §15h. Gates

Fast tier: **3,713 passed** (main's 3,701 + 12 new), 3 skipped
(`out/r219/pytest-fast.txt`). `python3 -m tools.omr.staged.check`: **TOTAL
247**, unchanged (`out/r219/staged-check.txt`).

### §15i. What contradicted this brief

- "~67% held" comes from a different gather configuration (§15a); this
  gather holds 92.3%.
- Litolff p3 on its own cannot control a bar-sum question: without a carried
  meter nothing on it is judged.
- The top cause is not one of the brief's (a)–(d). It is (e), it applies to
  every bar, and it is a reader failure.

### §15j. Files

- `probe/held_funnel_2_19.py`: the dump and its control.
- `probe/classify_held_2_19.py`: the partition.
- `probe/crop_held_2_19.py`: the crops.
- `out/r219/`: base and arm dumps for Breitkopf p1, both partitions, pricing,
  the control log, tests RED and GREEN, and the check output.
- `tools/omr/staged/consequences.py`: `size_measure_rest` and
  `_left_the_bar`.
- `tools/omr/tests/test_staged_measure_rest_left_the_bar.py`: the tests.

## 16. ROADMAP 2.12l — a printed meter change's digits, boxed as noteheads (2026-09-29)

PATH: STAGED. Branch `claude/meter-digit-2.12l`, off `origin/main` `23f4fa9e`
(2.6f ownership-rung discount already in the tree). §15b named the cause;
this builds the fix: (1) REFUSE the digit boxes as noteheads, in
ADJUDICATE, backed by a cross-staff quorum; (2) FILE the refusal back as a
witness the meter chain can see, value unread, never guessed.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

A printed meter change sits at ONE x, just past a barline, on EVERY staff of
the system (CLAUDE.md §10). Measured on the fixture (crops #1-#3 below,
`probe`-free — cut straight off the re-decided record's own `bbox_page_px`):
the two digits box as `noteheadWhole*`/`noteheadBlack*`, at nearly the SAME
x (0.00-0.11 canonical staff spaces apart) and a narrow, SPECIFIC distance
apart in y (0.42-0.86 spaces, centre to centre), both within 0-2.2 spaces of
the cell's own left edge, on 13 of 14 staves. ⚠️ THE BRIEF'S OWN "~2 spaces
tall" HEIGHT SIGNATURE DID NOT SURVIVE CONTACT WITH THE PLATE: the
detector's box is drawn around the ROUNDED PART of each digit it pattern-
matches to a hollow notehead template, not the numeral's full extent, and
measures 0.94-1.94 spaces tall — statistically indistinguishable from a real
notehead on this fixture. Height carries no weight in the shipped rule; the
tight x-pairing, the narrow y-gap and the cross-staff repetition do all the
work. WHAT WOULD FALSIFY IT: a crop showing a real, same-interval chord
repeating at one x on most staves of a system (the brief's own named risk,
guarded but not excluded by construction — see §16b). NOT CONFIRMED WITH
SEAN.

### §16a. The refusal (`notehead_precision.adjudicate_notehead_is_not_a_notehead`)

New reason `is_a_meter_digit`. Two gates, both required, neither sufficient
alone:

1. `_meter_digit_pair_partner` — a second `notehead*` box on the SAME
   staff's SAME cell, within `METER_DIGIT_PAIR_X_TOL_SPACES` (0.25) in x and
   `METER_DIGIT_PAIR_Y_GAP_MIN/MAX_SPACES` (0.30-1.20) apart in y, both
   within `METER_DIGIT_X_MAX_SPACES` (3.0) of the cell's own left edge.
2. `_meter_digit_cross_staff_count` — the SAME stacked-pair test (not merely
   "some notehead near the barline" — see §16b) on a QUORUM of the
   system's OTHER staves at the same cell index (`_required_meter_digit_
   quorum`, the same `max(2, round(0.5·n))` shape `rhythm._required_
   corroboration` already uses, cited not imported).

### §16b. A control that failed, and what it cost

The first cross-staff test (`_meter_digit_cross_staff_count`) asked only
"does this OTHER staff have SOME notehead-classed box near the barline?" —
and on the actual fixture this fired on TWO cells (3 and 5) that print no
meter change at all: a lone staff's ORDINARY first note of the bar, sitting
near enough to a barline to look like half of nothing, borrowed the OTHER
13 staves' real cell-1 pattern to clear its own quorum. `probe`-free
measurement (`redecide2.py` in the files list) caught it: 35 raw hits, only
30 of them at the one cell the plate actually prints a change at. Fixed by
requiring the SAME stacked-pair test on the other staff's own cell
(`_has_a_stacked_pair`), not merely "ink near x" — 35 → 30, cells 3 and 5
gone, cell 1 (13 of 14 staves) unchanged. This is the control CLAUDE.md rule
7 asks for, run in a state where it failed before being trusted where it
passes.

### §16c. The witness (`rhythm.py`)

`_meter_digit_witness_cells(ev, total_staves)` — a SECOND control failure,
found the same way. A naive version read `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`
VERDICTS broadly (`scope=SELF_AND_DESCENDANTS` off the system) and broke
`tools/omr/tests/test_stage_review_evidence.py` TWICE
(`TestBelongsToAnotherStaff::test_an_owner_row_on_an_UNCONTESTED_glyph_
REFUSES_IT_HERE`, `TestAConfirmedBoxIsFiledAndChangesNothing::test_it_
reaches_the_FEEDBACK_FILE_and_is_HANDED_OVER_UNWEIGHED`): every verdict
`ev.verdicts()` returns is marked `considered` by the calling decision
(`Evidence._seen`), so `adjudicate_meter` ended up transitively citing a
human's confirm/refuse row on a glyph SIX staff spaces from any barline, in
a system printing no change at all — `basis_names_human` (the review
tooling that answers "which decisions would a human's correction touch")
reported `adjudicate_meter` for every notehead in the document, not the
handful near a bar's own head. Fixed by finding candidates from
OBSERVATIONS first (`Q.GLYPH_BOX`, `Q.CELL_STAFF_SPACE` — plain
detector/geometry rows, inert for that tracking), filtered to the SAME
near-barline x-window, and asking only the survivors' own verdict by EXACT
subject — a handful of glyphs per system, never the population. Both tests
pass again; `git stash`-verified against the un-narrowed version (2.12l-red-
check / 2.12l-base-price tags, dropped after use).

A THIRD bug, same family: the tail loop that files the witness into
`declined_changes` originally skipped any cell already present in `by_cell`
(built from raw `Q.METER_GLYPH` rows) — but a lone, unreadable stray
detection (measured: staff 9 fires one `timeSig1` at cell 1, no stacked
partner, on the Breitkopf fixture itself) puts a cell in `by_cell` without
the main loop ever producing a `readings` entry for it, silently shadowing
the far stronger 13-staff witness. Fixed by tracking `cells_with_a_
candidate` (cells the main loop actually evaluated, i.e. `readings` was
non-empty) and skipping on THAT set instead.

Two uses, both value-free (CLAUDE.md rules 6 and 8):

1. `_meter_changes` files the witness cell into `declined_changes` with
   `declined_reason=meter_change_digits_misread`, `numerator`/`denominator`
   both `None` — a witness, not a candidate. Never overrides a cell the main
   loop actually evaluated.
2. `_carry_meter` reads `src`'s own recorded witness back
   (`_carry_source_digit_misread`, off `found.value` already in hand — no
   second query) and, where the carry is refused by `src`'s own later bars,
   relabels the generic `carry_outweighed_by_the_bars`/`carry_not_
   corroborated` to `meter_change_digits_misread` — the SAME shape ROADMAP
   2.12k already uses to label a return the bars proved but the reader
   missed, applied to a different, specifically-known cause.

### §16d. Priced on the fresh gather: base tree vs arm, re-decided in-process

Fresh gather, Breitkopf `317803` pdf p1, `--no-surya` (OCR on), this
worktree's own tree (`23f4fa9e` + this branch, `dirty: true` — the record's
own provenance stamp). Base = `git stash` of the two production files only
(tests and record kept); arm = this branch. Re-decided in-process
(`RR.rebuild_gather` + `RR.run_stages`, the SAME technique 2.19 used), never
re-gathered.

| | value |
|---|--:|
| `is_a_meter_digit` refusals | 30 (13 of 14 staves at system/1/0 cell 1; staff 12 missed — a detection recall gap, not a shape miss) |
| `system/1/0` `Q.METER` | unchanged: `voted`, 9/4 (the header misread, 2.12h's own subject) — **never overwritten by the witness** |
| `system/1/0` `declined_changes` | +1 entry: `{from_cell: 1, numerator: None, denominator: None, declined_reason: "meter_change_digits_misread", staves_with_digit_witness: [0,1,2,3,4,5,6,7,8,9,10,11,13]}` |
| `system/1/1` `Q.METER` | abstain reason **`carry_not_corroborated` → `meter_change_digits_misread`** (base → arm); outcome stays ABSTAINED, value stays unset |
| `bars_held_out_sum` (2.8) | base 144 → arm **145**, of 169 bars-with-events |
| bars released | **0** |
| bars newly held | **1** (system/1/0 staff 8 cell 1 — crop #5) |
| engraved control (`engraved-p0p2-20260928.record.json`) | `is_a_meter_digit` refusals: **0**; `meter_change_digits_misread` verdicts: **0** |

**0 bars released, 1 newly held, and that is the honest number, not a
regression.** Staff 8's cell-1 bar previously WROTE the two fake noteheads
as real notes; their spurious duration happened to sum close enough to the
carried (wrong) 9/4 that the bar read as "adds up" by coincidence. Refusing
them removes that accidental agreement and the bar now correctly shows as
NOT matching 9/4 — which it never was going to, since this is exactly the
bar the plate changes to 6/8. This item's own scope (§ "The item") is
narrower than releasing bars: refuse the fake notes, file the witness. What
would actually release these bars is reading the meter VALUE at cell 1
(§15f's item 1, ranked but explicitly out of this item's reach — rule 6
forbids guessing "6/8" from the digit shape alone) — the witness now on the
record is the tool a later lane needs to do that, traceable by `trace
--subject system/1/1` down through `_carry_meter`'s own label rather than a
bare, uninformative refusal.

### §16e. Proof

RED → GREEN, `tools/omr/tests/test_staged_meter_digit_witness.py` (17
tests, new file): confirmed RED against the tree with the two production
files stashed out (`git stash push -m "2.12l-red-check" -- <two files>`,
verified, restored via `git stash apply <sha>` + `git stash drop` — never a
bare `stash pop`) — 12 of 17 fail on `AttributeError` (the constants/
functions do not exist), 5 pass as their own controls (a shape this item
does not touch must stay untouched on BOTH trees). GREEN 17/17 after
restore. Positive controls: a real two-note hollow chord on one staff alone
is kept (`test_CONTROL_a_lone_chord_on_ONE_staff_is_kept`); a repeating
tutti whole-note entrance with no stacked partner is kept
(`test_CONTROL_tutti_whole_notes_with_no_partner_are_kept`); a repeating
chord a THIRD apart (2.0 spaces, outside the digit pair's own window) is
kept (`test_CONTROL_a_wide_repeated_chord_is_kept`). `pytest tools/omr/tests
-m "not slow" -q`: **3,736 passed** (main's 3,719 + this file's 17), 3
skipped, 0 failed — confirmed clean on `test_stage_review_evidence.py` and
every existing meter/notehead-precision test file. `python3 -m tools.omr
.staged.check`: **TOTAL 247**, unchanged (10 inventory, 67 wiring — both
ONE LOWER than the broken intermediate state that had `Q.NOTEHEAD_IS_NOT_A_
NOTEHEAD` declared and never read; closed by threading `total_staves`-
shaped arguments the same way `_meter_changes` already does, never by
reaching for the quantity one frame too deep).

5 crops (`out/print/meter-digit-2.12l-*.png`, manifest `meter-digit-2.12l-
manifest.json`, `VERDICT_none_yet: null`), cut from the fresh gather's own
600 dpi render with the subject staff's own `Q.STAFF_LINES` drawn (green)
and the subject box red-bracketed:

- #1-#2: the refused "8" (staff 0, staff 8) — the "6" prints directly above
  it in both crops, visibly a stacked time signature.
- #3: staff 6's own refusal, wider window, for a THIRD staff of the 13.
- #4: staff 12 — the one staff of 14 the pair test did NOT catch (a
  detection recall gap: only one of the two digits boxed as a notehead at
  all on this staff).
- #5: staff 8's own bar, wide window — the "6/8" print and the bar's own
  (now correctly unmatched) content, the one newly-held bar from §16d.

### §16f. What contradicted this brief

- The height signature ("~2 spaces tall") does not survive contact with the
  plate — the detector boxes the digit's rounded PART, not its full extent,
  and measures the same height as a real notehead. Position (tight x-pair,
  narrow y-gap) and cross-staff repetition carry the whole claim instead.
- A loose cross-staff test ("some notehead near x") is NOT safe — it fired
  on two cells with no printed change at all, on the SAME fixture this item
  was built against. Tightened to the same stacked-pair test, both ways.
- Releasing bars was not this item's own effect: 0 released, 1 newly held.
  The count going up by one, on a page that also just shipped the FIRST
  correct labelling of WHY the next system's carry fails, is the honest
  price of no longer writing two fake notes as real ones.

### §16g. Files

- `tools/omr/staged/adjudicators/notehead_precision.py`: `is_a_meter_digit`
  and its module-level block comment.
- `tools/omr/staged/adjudicators/rhythm.py`: `_meter_digit_witness_cells`,
  `_carry_source_digit_misread`, `METER_CHANGE_DIGITS_MISREAD`, the
  `_meter_changes`/`_carry_meter` wiring.
- `tools/omr/tests/test_staged_meter_digit_witness.py`: the tests.
- `out/print/meter-digit-2.12l-*.png` + manifest: the crops.

## 17. ROADMAP 2.22 — what holds bars on the WHOLE movement (2026-09-29)

PATH: STAGED. Branch `claude/held-bars-mvt-2.22`, off `origin/main`
`baba1c76` (2.12l, 2.10b, 2.19 and 2.21's *question* are in the tree; 2.21's
BUILT branch `claude/voice-split-2.21` is not, and is only simulated here).

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

The printed meter used for diagnosis is the dossier's
(`data/dossiers/*.json` `meter_changes`): Beethoven 5/i 2/4 throughout,
Brahms 1/i 6/8 except the one 9/8 bar (printed m. 8). It is a diagnosis
table only, never a pipeline input. ⚠️ OUR file numbers the printed m. 8 as
**9** (one bar too many before it), so the 9/8 bar is keyed by
`page/system/cell` (`1/0/0`), not by measure number. The fix built (§17d)
assumes no new convention: a narrowed note has no reading of its own, and
the meter choosing among its candidates is `reconcile_duration`'s stated
purpose. What would falsify it: a bar the fix releases whose narrowed note
the print shows at a DIFFERENT candidate (none cropped yet). NOT CONFIRMED
with Sean. The Brahms question (§17e) is his.

### §17a. The records, and what was re-decided

Both 09-29 whole-movement records were gathered on `23f4fa9e` and carry
`dirty: true` in their own provenance: inputs, not baselines. Each was read
through `record_io.load_record`. `probe/held_funnel_mvt_2_22.py` is 2.19's
`held_funnel_2_19.py` at movement scale: it wraps `export._bar_holds_out`
(the exporter's own rule) and its control is again bars captured ==
`bars_held_out_sum` minus doubled copies. **PASS on every run below.**

- **Litolff (325 MB)**: re-decided in-process on `baba1c76`
  (`review.rerun`) in **23 min**, so 2.10b's clef collapse and 2.12l are in.
  Held **1,591** of 4,726 bars-with-events (78 on a doubled staff, 1,513
  locatable). The record's own verdicts gave 1,576 of 4,670: `no_pitch`
  471 → 135 is 2.10b, and the newly written heads land 15 more bars that do
  not add up.
- **Brahms (1.4 GB)**: the re-decision was **killed at ~27 min of
  `run_stages`** (Litolff's took 23 min, and Brahms is ~4x its size).
  **Brahms figures below are the record's OWN verdicts (made on
  `23f4fa9e`), exported with today's exporter**, so 2.12l's digit refusal is
  NOT in them (crop #2 of §17c shows the 6/8 still boxed as heads). Held
  **4,200 of 5,973** bars (15,110 heads held out).
- Record loads: Litolff 3 (dump; `reconcile_why`; arm), Brahms 2 (dump;
  crop geometry). That is more than the brief's "once": each later probe
  asked a question the first could not have known to ask.

**The meter's VALUE is right on every held bar of both movements** except
the 9/8 bar: Litolff judges all 1,513 against 2/4, Brahms all 4,200 against
6/8. 2.19's "the meter is wrong on every bar" was the single-page artefact
the brief suspected. **The meter VERDICT is another matter.** On Brahms,
3,058 of the 4,200 held bars sit on a system whose `Q.METER` ABSTAINS
(`carry_not_corroborated` 2,705, i.e. fewer than two bars that three staves
can sum; `carry_outweighed_by_the_bars` 263; `meter_return_not_read` 90),
while the FILE carries 6/8 into it (§2's `in_force`). Both EVALUATE rules
that could repair a bar (`size_measure_rest`, `reconcile_duration`) take
`Q.METER` as their cause, so on those systems neither runs. Litolff's meter
is DECIDED on every held bar's system.

### §17b. The partition (`probe/classify_held_mvt_2_22.py`)

This is 2.19's method: the minimal releasing fix set per bar, ties grouped,
each bar reported under its most SPECIFIC tied set. It adds letters that
one page did not need:

- `O`: restore an `owner_not_read` head.
- `P`: restore a `no_pitch` head.
- `X`: drop ONE event (a spurious head, rest or duplicate that nothing
  refused). It is structural too, so `WX` means "a whole rest plus one stray
  box".
- `G`: every flagged or beamed note of a voice one level off TOGETHER.
- 2.19's `B` is split in two. `B` is a beam or flag level, with both values
  a quarter or shorter. `F` is a head FILL or stem misread (quarter↔half,
  half↔whole). `reconcile_duration` cannot reach `F` by construction:
  `_admitted` never offers a level below 0.
- `V` is 2.21's gate: merge the streams unless an up-stem chord and a
  down-stem chord share an onset within 0.10 staff spaces of PAGE x. 2.21
  prefers `Q.ONSET_COLUMN`; this simulation uses its fallback everywhere.
- `H` is 2.12l's stacked-pair test WITHOUT its cross-staff quorum, so it is
  an upper bound.

The search stops at 4 letters. Both tables close.

**Litolff 1/i, re-decided on `baba1c76` (1,513 locatable held bars):**

| minimal set | bars | what it is |
|---|--:|---|
| `F` | **300** | one note's head fill or stem misread. 278 are a LONE quarter-valued chord in a 2/4 bar (crops `litolff-F-01..06`: hollow heads merged black on this MERGING plate) |
| `none_of_these` | 178 | 70% SHORT; see §17c |
| `X` | 155 | one spurious event (a rest, a stem, the neighbour's ink) |
| `B` | 116 | one note a beam or flag level off |
| `N` | 112 | one narrowed head, restored at a candidate |
| `G` | 73 | a whole beam group one level off |
| `V` | 64 | 2.21's voice merge |
| `D` | 53 | one dot |
| `WX` | 48 | a whole rest plus one stray box |
| `R` | 46 | a `not_a_notehead` head restored (`too_narrow` 41) |
| `W` | 44 | a lone whole rest not sized |
| `A` | 32 | an abstained rest |
| `WE` | 30 | a whole rest plus a barline read as a quarter rest |
| `O` | 21 | an `owner_not_read` head |
| 58 other combinations | 241 | |
| **total** | **1,513** | |

Single fixes that release a bar outright: `F` 405, `X` 253, `B` 223, `N`
114, `G` 102, `D` 70, `V` 64, `R` 52, `W` 44, `A` 40, `O` 27, `S` 18, `E`
15, `H` 11, `P` 6. Necessary fixes: `F` 298, `X` 282, `B` 132, `W` 110, `G`
108, `V` 58. The record's own `23f4fa9e` verdicts rank the same way (`F`
295, none 173, `X` 153, `N` 111, `B` 110, `G` 67, of 1,498).

**Brahms 1/i, the record's own verdicts (4,200 held bars):**

| minimal set | bars | what it is |
|---|--:|---|
| `W` | **706** | a lone whole rest not sized. **681 sit on a system whose meter abstains**, and 608 of those have nothing else in the bar (8 crops, §17e) |
| `none_of_these` | 504 | 90% SHORT; see §17c |
| `D` | 477 | one dot (6/8: dotted quarters) |
| `N` | 281 | one narrowed head |
| `V` | 234 | 2.21's merge. Its gate finds NO shared onset in 616 of the 672 two-stream held bars |
| `X` | 229 | one spurious event |
| `F` | 215 | one head fill or stem |
| `B` | 176 | one beam or flag level |
| `G` | 168 | a whole beam group one level off |
| `WX` | 118 | a whole rest plus one stray box (crops show a neighbour's stem tip boxed `restWhole`) |
| `R` | 78 | a `not_a_notehead` head (`too_narrow` is 210 of the R-set reasons) |
| `VD` | 63 | |
| `VB` | 51 | |
| `DB` | 46 | |
| 143 other combinations | 854 | |
| **total** | **4,200** | |

Single fixes that release a bar outright: `W` 706, `D` 578, `B` 514, `X`
453, `F` 355, `N` 282, `V` 234, `G` 221, `R` 92, `S` 28, `A` 27, `E` 23,
`H` 13, `O` 12. Necessary fixes: `W` 744, `X` 542, `V` 431, `D` 409, `F`
382, `G` 326, `B` 258, `N` 203, and `M` (the 9/8 bar) 12.

### §17c. The unmodelled remainder: 10 crops each

The crops are `out/print/held-mvt-2026-09-29-{brahms,litolff}-unmodelled-*.png`,
with manifests (`VERDICT_none_yet: null`). They were picked one per page
across the movement by `probe/pick_jobs_2_22.py` and cut at 600 dpi by
`probe/crop_held_mvt_2_22.py`, from geometry the probe saved, so no further
record load was needed. The frame control is `crop_losers_2_6b._frame_ok`.
**It REFUSED Litolff #3** (contrast −39), so there are 9 Litolff crops. The
"trace" is the record's own reading in each caption: the voice events and
the refusals in the cell. The readings below are mine, not Sean's.

Brahms:

- #1: heads above the staff on 3-ledger ladders, read as 16ths and 64ths.
  The ledger strokes are counted as beams.
- #2: the m. 9 bar. The printed 6/8 is boxed as heads (these own verdicts
  predate 2.12l), and three eighth rests are read as quarter notes.
- #3: a bar of 16ths read as 64ths throughout. Two hairpin lines and
  another staff's beams are counted.
- #4: two dotted quarters. One is read as a dotted 16th; the other is
  narrowed.
- #5: a lone whole rest, plus two flag tips of the staff below seen through
  the pad.
- #6: an eighth, two eighth rests and a dotted quarter. A rest is read as a
  note, a rest is missed, and the dotted quarter is narrowed.
- #7: two dotted-quarter chords read as a 32nd and a 16th (hairpins counted
  as beams).
- #8: two dotted-quarter chords read as a 16th plus a mis-valued 16th.
- #9: two dotted quarters read as plain eighths. Both the level and the dot
  are missed.
- #10: a two-voice bar (stems both ways) read as ONE stream of five
  quarters.

Litolff:

- #1: bar 2's fermata half note, read as an eighth.
- #2: two quarter rests boxed as heads, plus a head of the staff below.
- #4: ledger lines read as beams (16th, 64th), plus a narrowed head.
- #5: a two-head half-note chord whose EVENT is 2.0 but is WRITTEN as an
  eighth (see below).
- #6: heavily merged ink; one 16th read.
- #7: a tremolo, read as one eighth.
- #8: an eighth and three beamed eighths, read as a 16th and a 32nd; two
  heads narrowed.
- #9: a quarter rest under a fermata, boxed as a notehead.
- #10: a half note whose STEM is boxed as a quarter rest; its hollow head
  below the staff is unboxed.

**What the remainder is.** Compound faults, mostly of four kinds:

1. Strokes that are not beams counted as beams (ledger lines, hairpins,
   other staves' beams), leaving whole bars one or two levels short.
2. Rests boxed as heads, and heads or stems boxed as rests.
3. The neighbouring staff's ink seen through the cell pad, uncontested.
4. A narrowed head beside another fault.

None of these is a single connection.

**A connection finding inside it, not built.** 93 Litolff and 231 Brahms
held bars hold a CHORD whose members disagree about value. Typically it is
one head boxed twice, as `noteheadBlack` and `noteheadHalf` (2.12g's role
twins). The EVENT's `duration_beats` is the members' mode, but EXPORT writes
the first head's `<type>` and sums THAT. If the written units were the
event's, 54 Litolff and 41 Brahms bars would add up. Which member is right,
though, is the reading question 2.12g exists for, so this is recorded, not
built.

### §17d. Built: `reconcile_duration` sums the bar EXPORT will write (EVALUATE; it FOLLOWS)

`probe/reconcile_why_2_22.py` asked, for every Litolff held bar, what
`reconcile_duration` saw there through its own helpers:

| the rule's own view | bars | with 2.19's `_left_the_bar` set aside |
|---|--:|--:|
| no single re-reading lands | 999 | 1,017 |
| more than one lands (refused, correctly) | 231 | 225 |
| **the total ALREADY FITS the meter** | **283** | 221 |
| exactly ONE re-reading lands | **0** | **50** |

There were two disconnections from EXPORT. Both are closed in
`consequences.py`:

1. **It summed boxes that a DECIDED verdict had taken out of the bar.**
   This is 2.19's fault again, in the second rule that sums a cell. The rule
   now uses `_left_the_bar` (the same helper), cites the removing verdicts in
   `basis` and `detail.set_aside`, and declares the removals through
   `reads_beyond_cause` exactly as `size_measure_rest` does.
2. **A bar that fitted only THROUGH a narrowed note's best candidate counted
   as "already fits".** The note stayed NARROWED, EXPORT refused it
   (`duration_narrowed`), and 2.8 held the bar. A narrowed note has no
   reading of its own, so every candidate, including the one the total
   used, is now a re-reading. The bound is unchanged: one note, an exact
   landing, a UNIQUE answer. Two narrowed notes that both fit are two
   landings, and the rule refuses. `detail.bar_fit_only_through_this_narrowing`
   marks the case. Of the 221 set-aside "fits" bars, 37 hold exactly one
   narrowed head and nothing else refused.

A control failed first (rule 7). `_is_rest` read a NARROWED verdict's
`value`, which is `None`, so a narrowed REST counted as not-a-rest and the
widened loop re-read it. `test_a_narrowed_REST_is_still_not_re_read` caught
it, and `_is_rest` now reads a narrowed verdict's candidates.

One existing assertion changed on purpose. `test_staged_candidates.py`'s
`test_a_bar_that_already_fits_is_left_alone` (2.0 plus a narrowed {1.0,
0.5} in 3/4) is now `test_a_bar_that_fits_ONLY_through_the_narrowing_settles_it`,
because the old behaviour is exactly the disconnection. An all-DECIDED bar
that fits is still left alone (`test_staged_duration.py`, unchanged).

**RED → GREEN.** `tools/omr/tests/test_staged_reconcile_what_is_in_the_bar.py`
has 10 tests. On the unrepaired tree **3 failed and 7 passed**
(`out/r222/tests-RED.txt`). The 7 are the controls: an all-decided bar that
fits, the old repair, two narrowed notes that both fit, an ABSTAINED
refusal, a head its own staff kept, no meter, and a narrowed rest. On the
repaired tree all 10 pass.

**Priced base (`git archive HEAD`) vs arm, otherwise the same tree,
re-decided in-process** (`probe/run_arm_2_22.sh`, `probe/price_2_22.py`):

| | held (2.8) | released / newly held | `<note>` | `duration_narrowed` | 2.8 control `bar_sum_check`, base / arm |
|---|--:|--:|--:|--:|--:|
| engraved p0–p2 (control) | 37 → 37 | 0 / 0 | 658 → 658 | — | 450/450 / 450/450 exact |
| Litolff p1–p4 (09-11 record) | 270 → **260** | 10 / 0 | 1,855 → 1,878 | 152 → 138 | 1,183/1,183 / 1,183/1,183 |
| Brahms p0–p3 (shared record) | 570 → **566** | 4 / 0 | 1,322 → 1,334 | 235 → 232 | 818/818 / 818/818 |
| **Litolff 1/i whole movement** | 1,591 → **1,522** | **66 / 2** | 9,155 → 9,275 | 914 → 844 | 5,940/5,940 / 5,940/5,940 |

Litolff p1–p4 also gains 6 bars-with-events (1,015 → 1,021): bars whose
only heads were narrowed are now written, and they add up. On the whole
Litolff movement (23 min per arm) bars-with-events rise 4,726 → 4,758 and
written notes 4,521 → 4,722; `owned_by_another_staff` 989 → 982 and
`owner_not_read` 362 → 369 move by a handful (a decided duration changes
the events a contest sees). The 2 newly held bars: `14/0/9/8` is §17c's
chord-member disagreement (the record's event is 0.5, so the bar fits and
the rule decides; the file writes the first head's quarter and the bar is
2.5), and `5/0/1/2` holds three eighths (1.5) beside refused heads. Neither
was checked against the print. Brahms moves
little because its meter abstains on most systems (§17a). That is §17e.

### §17e. Asked, not built: does a carried meter HOLD where the bars cannot check it? (Brahms `W`, 608 bars)

The top Brahms class is `W` (706). In 608 of those bars a lone whole rest
stands with nothing else, on a system whose `Q.METER` abstains
(`carry_not_corroborated` 504, `carry_outweighed_by_the_bars` 85,
`meter_return_not_read` 19, across 34 systems). `size_measure_rest` needs a
DECIDED meter ("no meter, no assertion"), yet the FILE writes 6/8 there
anyway.

`METER_CARRY_FLOOR` (2.0) with `W_METER_CARRIED` (1.0) means a carry needs
at least one net agreeing bar, and `METER_CARRY_MIN_BARS` needs two
assessable ones. That gate was measured against the *Andante* (an unseen
movement start), before `--movements` (4.2) and before Sean's 09-28
decision ("a change holds until a printed change back"). Whether that
decision covers a system the bars cannot check is a convention question, so
it is asked, not built (rule 3):

> **Sean: on a system where no meter change is printed or read, does the
> meter carried from the previous system HOLD even when too few bars can
> check it (so a lone whole rest there is marked as the bar), or should it
> stay unknown?**

There are 8 banded crops, one per page across the movement:
`out/print/held-mvt-2026-09-29-W-*.png`, with manifest
`held-mvt-2026-09-29-W-manifest.json` (`question`, `answer_none_yet: null`,
and `VERDICT_none_yet: null` per crop). The frame control passed on all 8.
In my reading each shows one centred whole rest and nothing else in the
bar. #4 is on a `carry_outweighed_by_the_bars` system; the other 7 are
`carry_not_corroborated`. If the answer is yes, the upper bound is 608 bars
released by `size_measure_rest` alone, and `reconcile_duration` (§17d)
starts running on those 34 systems too.

### §17f. Ranked next

1. **Brahms: the meter-hold question (§17e).** 608 bars turn on one answer,
   and it unblocks both EVALUATE rules on the systems of 3,058 held bars.
2. **Litolff `F`** (300): merged hollow heads read black. This is a
   READER/DETECTOR item (head fill on a MERGING plate), not a connection.
3. **2.21's voice gate** (Brahms `V` 234 alone, necessary in 431): held for
   Sean. The simulation says his answer moves more Brahms bars than anything
   except `W`.
4. **Strokes counted as beams** (`G` 168 and 73, plus much of the
   remainder): ledger lines, hairpins and other staves' beams enter the beam
   count.
5. **Chord members that disagree** (§17c): 2.12g's twins, written by the
   first head's type.

### §17g. ROADMAP 2.22b — the manager applied Sean's 09-28 decision: a carried meter HOLDS where the bars are silent

PATH: STAGED. Branch `claude/meter-holds-2.22b`, off `origin/main`
`7f2e7898` (2.22 merged).

**Who decided.** §17e's question was NOT answered by Sean in this session.
The manager (coordinator) applied his RECORDED words: DECISIONS 2026-09-28,
"a meter change holds until the plate prints a change back; the return is
always printed", and CLAUDE.md §10, "the carry is WEIGHED by the bars, not
gated". The question stays open in `out/print/held-mvt-2026-09-29-W-manifest.json`
(`answer_none_yet: null`, plus a note saying it was applied this way) so he
can overturn it.

**The rule (`rhythm._carry_meter`, ADJUDICATE).** Where the bars are SILENT,
the carried meter is DECIDED with reason `carried_uncontested`, basis = the
carry source's verdict, and `margin` = `W_METER_CARRIED`. "Silent" is
defined narrowly, so three conditions must all hold:

1. `_corroborate` found too few assessable bars (the old
   `carry_not_corroborated` rung).
2. None of the bars that could be summed contradicts the carry
   (`bars_disagree == 0`). One bar that disagrees is not silence, so it
   still abstains `carry_not_corroborated`.
3. This system read NOTHING of its own (`instead_of == "no_evidence"`).
   A system whose staves read a meter-shaped thing (`too_few_staves_read_it`,
   `no_agreement`, `opening_disagrees_with_prior_cautionary`) still
   abstains.

It still ABSTAINS, unchanged, in these cases:

- The bars outweigh the carry (`carry_outweighed_by_the_bars`).
- 2.12k's cautionary return (`meter_return_not_read`).
- 2.12l's digit witness on the carry SOURCE (`meter_change_digits_misread`).
- A printed change witnessed unread on THIS system. The abstention stays
  `carry_not_corroborated` and gains
  `detail.unread_change_on_this_system_at_cell`.

A carry still never crosses a movement boundary (4.2). `carried_uncontested`
is not a carry SOURCE, so a carry still never chains onto a carry. The old
design comment ("a page with no assessable bar is exactly the page where a
movement may have started unseen") is the hazard this accepts. With
`--movements` declared it is closed. Without it, a movement start nobody
reads would now carry silently. That is Sean's rule taken at its word: the
new movement's printed meter is a printed change, and missing it is a
reading miss.

**RED → GREEN.** `tools/omr/tests/test_staged_meter_holds_where_bars_are_silent.py`
has 9 tests. On the unrepaired tree **4 failed and 5 passed**
(`out/r222/tests-RED-2.22b.txt`):

- The 4 RED tests: silent bars, where the carried meter is decided; one
  agreeing bar is still silence; an uncontested carry is not a source; the
  unread-change detail is named.
- The 5 controls: a contradicting bar; bars that outweigh; a system that
  read a meter shape; a witnessed unread change here; a movement boundary.

After the change, 181 of 181 pass across the seven meter test files
(`out/r222/tests-GREEN-2.22b.txt`). Two existing assertions in
`test_staged_header_rhythm.py` pinned the old gate and were changed on
purpose. `test_a_page_that_cannot_corroborate_does_not_carry` is now
`..._carries_UNCONTESTED`. `test_a_LONE_WHOLE_REST_MAY_NOT_CORROBORATE_ANYTHING`
still asserts that the rests corroborate nothing (`bars_agree == 0`,
`too_few_assessable_bars`), but the carry now holds. The constants test
keeps its assertion (a carry alone does not clear `METER_CARRY_FLOOR`),
with the message reworded.

**Priced: base (`git archive HEAD`) vs arm, re-decided in-process**
(`probe/run_price_2_22b.sh`, `probe/price_2_22.py`):

| | held (2.8) | released / newly held | `<note>` | `bar_sum_check`, base / arm |
|---|--:|--:|--:|--:|
| engraved p0–p2 (control) | 37 → 37 | 0 / 0 | 658 → 658 | 450/450 / 450/450 exact |
| Litolff p1–p4 | 260 → 260 | 0 / 0 | 1,878 → 1,878 | 1,183 / 1,183 |
| Brahms p0–p3 | 566 → 566 | 0 / 0 | 1,334 → 1,334 | 818 / 818 |

**⚠️ THE ARM IS DEAD ON BOTH PRICED RECORDS. REACH 0, NOT "SAFE".** Neither
record has a single `carry_not_corroborated` system on today's tree:

- Litolff p1–p4: 6 systems `carried`, 1 `voted`.
- Brahms p0–p3: 1 `voted`, 1 `carried`, 1 `meter_return_not_read`, and
  **4 `meter_change_digits_misread`**.

The Brahms figure is the finding. After 2.12l, every later system that
carries from `system/1/0` (the last `voted` source, whose m. 9 change is
witnessed but unread) is labelled by that witness, and it stays abstained
by design, because the value it would carry is the one the unread change
superseded. **Prediction, unmeasured:** on the whole Brahms movement most of
§17a's 2,705 `carry_not_corroborated` bars (counted on pre-2.12l verdicts)
are now `meter_change_digits_misread`, so 2.22b alone releases far fewer
than §17e's upper bound of 608. The lever for those bars is READING the m. 9
6/8 (2.12i's fixture). The whole-movement re-decide (>30 min) is left to
the manager's nohup run:

    sh benchmarks/omr-bar-sum-holdout-2026-09/probe/run_arm_2_22.sh <base tree> brahms-base <brahms whole record>
    sh benchmarks/omr-bar-sum-holdout-2026-09/probe/run_arm_2_22.sh <this tree> brahms-arm <brahms whole record>
    python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/price_2_22.py benchmarks/omr-bar-sum-holdout-2026-09/out/r222 brahms-base brahms-arm

**Gates.** Fast tier **3,770 passed** (main's 3,761 + 9 new), 3 skipped
(`out/r222/pytest-fast-2.22b.txt`). `check` **TOTAL 247**
(`out/r222/staged-check-2.22b.txt`).

### §17h. Gates (2.22)

Fast tier: **3,758 passed** (main's 3,748 + 10 new), 3 skipped
(`out/r222/pytest-fast.txt`). `python3 -m tools.omr.staged.check`: **TOTAL
247**, unchanged (`out/r222/staged-check.txt`).

### §17i. Files (2.22)

- `probe/held_funnel_mvt_2_22.py`, `probe/classify_held_mvt_2_22.py`,
  `probe/summarise_2_22.py`: the dump, the partition, the tables.
- `probe/reconcile_why_2_22.py`: the rule's own view per held bar, plus crop
  geometry (`--geometry-only`).
- `probe/pick_jobs_2_22.py`, `probe/pick_w_jobs_2_22.py`,
  `probe/crop_held_mvt_2_22.py`: the crops.
- `probe/run_mvt_2_22.sh`, `run_why_2_22.sh`, `run_arm_2_22.sh`,
  `price_2_22.py`: the unattended runs and the pricing.
- `out/r222/`: summaries, partitions, pricing, logs, tests RED and GREEN,
  and the check output. The held dumps, geometry and MusicXML (up to 11 MB
  each) are regenerable and not committed.
- `tools/omr/staged/consequences.py`: `reconcile_duration`, `_is_rest`.
- `tools/omr/tests/test_staged_reconcile_what_is_in_the_bar.py`, and the one
  renamed assertion in `test_staged_candidates.py`.

## 18. ROADMAP 2.24 — the augmentation dot: why one dot is off in 578 Brahms
bars (2026-09-29)

PATH: STAGED. Branch `claude/aug-dot-2.24`, off `origin/main` `a9bdec8a`
(2.22b merged). §17's own table (whole Brahms movement, `23f4fa9e`) names
class `D` necessary in 477 of 4,200 held bars and a single-fix release of
**578** — the brief this item was set to explain.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

`_in_augmentation_window`'s asymmetric window (`DOT_ABOVE_NOTE_MAX_SPACES`
0.75, `DOT_BELOW_NOTE_MAX_SPACES` 0.25, `rhythm.py:71-72`) is unchanged by
this item: nothing measured here falsifies it, and one real case (§18b
below) asks whether it should widen for a note immediately followed by a
tie. NOT CONFIRMED with Sean; the question is filed in the new manifest,
not answered here.

### §18a. Setup and the fresh page

Gathered Breitkopf Brahms 1/i pdf idx 1 fresh, this tree, `--no-surya`,
scan weights (`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`):
`out/r224/brahms-p1.record.json` (94 s). `held_funnel_mvt_2_22.py` (phase
`own`, no re-decide needed — the record is already on this tree): **145
held bars of 169** (control PASS). 2.22's own classifier,
`classify_held_mvt_2_22.py`, with `--truth '{"9": 4.5, "default": 3.0}'`
(the dossier's 6/8-except-bar-9-at-9/8, same table §17a used):

    single fix releases outright: {M: 25, W: 20}
    necessary (in every minimal set): {M: 100, X: 30, W: 26, V: 18, G: 7,
                                        B: 7, S: 3, N: 3, F: 2, D: 2, E: 1, R: 1}

**⚠️ This page is not a clean sample: `M` (judge against the TRUE meter
instead of the bar's own) is necessary in 100 of 145 held bars — the file's
own `want_quarters` reads 9.0 on the great majority of them, against a true
3.0 (or 4.5 at the printed change).** This is the SAME family §17a already
named on 26 whole-movement bars (`meter_change_digits_misread` / a `9`
misread) — this exact page prints the movement's one 6/8→9/8→6/8 change, so
a single-page, no-prior-context gather amplifies it far past the
whole-movement rate. `M` here is a diagnosis-only override (compare each
bar's own voice sum to the TRUE meter), exactly as `T` already meant in
§17's table — it does not add or remove anything from a voice, so a bar
tied `M`+`D` is asking the identical question §17 asked, just on a record
whose held population is dominated by an unrelated, already-tracked cause.

`D` itself is necessary in only **2 of 145** held bars, and appears
(necessary or tied) in **13** — the population actually available to
diagnose on this page.

### §18b. Every one of the 13 `D`-tied bars, read against `Q.AUG_DOT`/`Q.DOT_ROLE`

`classify_held_mvt_2_22.py` proposes `D` from the bar's numeric residual
alone — it never reads `Q.AUG_DOT` or `Q.DOT_ROLE` (§13's caution about this
exact coincidence was written against a DIFFERENT, page-scale partition
script; the movement-scale one this item was told to use has no such
safeguard). Reading every one of the 13 bars' own dot evidence directly
from the record:

| bars | what is actually there |
|--:|---|
| 7 | **zero `Q.AUG_DOT` rows anywhere in the cell.** No dot ink was gathered at all; `D` is a pure numeric coincidence. |
| 2 | one `Q.AUG_DOT` row, **ABSTAINED** `dot_role_ambiguous`, sitting beside the direction word `espr.` (`arco` beneath it), nowhere near a notehead. |
| 1 | two rows: one **DECIDED** augmentation (correctly paired), one **ABSTAINED**, sitting ~0.6 staff spaces BELOW its own note, right where a tie begins. |
| 1 | one row, **DECIDED** augmentation, well-evidenced (3 correlated observation groups) — removing it is one of several tied ways to hit the target sum; not a real fix. |
| 2 | two rows, **both DECIDED** — not part of a bare `D`; folded into a 4-letter tie (`MVDF`) that is really about something else. |

None of the 13 is the hypothesis this item was briefed to check first — a
dot printed and detected, but discarded for sitting outside the window on a
note where the level-vs-space-higher distinction (CLAUDE.md §10) should
have mattered. Three concrete, checked mechanisms instead:

**1. The classifier's own coincidence, 7 of 13 (the majority).** Two worked
in full: `glyph/1/1/12/4` (m.12 P14) is short 0.5q; the cell's only refused
glyph is a genuinely narrow notehead (page-px width 20.7 vs ~37.8 for this
staff's normal heads) refused `not_a_notehead:too_narrow` with **no
computed duration** — `classify`'s own `_extras` requires a decided/
candidate duration to propose `R`, so it silently has nothing to offer and
the search lands on `D` instead, purely because 0.5q happens to equal one
dot's worth on an eighth. `glyph/1/0/3/3` (m.4 P4) is the same shape: zero
`Q.AUG_DOT` rows, the residual explained by `duration_narrowed`/
`not_a_notehead:too_narrow` refusals, `D` chosen only because `MNG`/`MSB`/
`MDG`/`MDX`/`MBX` tie and `MSD` sorts first. Crops #05, #06.

**2. The detector boxes a direction-word PERIOD as `augmentationDot`, 2 of
13.** `glyph/1/0/10/3/32` and `glyph/1/0/11/3/26` are both small
(page-px ~10x8 and ~8x8) isolated dots sitting just right of the direction
word `espr.` ("espr" then, separately, a dot; `arco` printed beneath) on
two DIFFERENT staves, at closely matching relative positions — text ink,
not ink near any note. `adjudicate_dot_role` correctly abstains
`dot_role_ambiguous` on both (neither window admits a target this far from
every notehead/rest in the cell), so this is HARMLESS to the file — it only
pollutes the diagnostic count. Crops #03, #04.

**3. One real, ambiguous case: a genuine augmentation dot displaced BELOW
its note, next to a tie, 1 of 13.** `glyph/1/0/2/5/31` (m.6 P3): the note
(`noteheadBlackOnLine`) sits ON the staff's bottom line; its dot sits ~0.6
staff spaces below that line (56.5 of 92 canonical units, confirmed against
the page-pixel frame independently: 16.85 of ~27.5 px), immediately where a
tie to the next note begins. The SAME cell's other dot
(`glyph/1/0/2/5/18`) is correctly decided, LEVEL with its own (space) note,
by the identical window. `_in_augmentation_window`'s asymmetric gate (0.75
above / 0.25 below) is doing exactly the measured job it was built for; the
open question is whether the PRINT has a real exception here (a dot pushed
low to clear a tie beginning right at the notehead) or whether this box is
the tie's own ink, misboxed as a dot. Crops #01 (control), #02 (the
question).

**4. A correctly DECIDED dot, swept into a tied minimal set by the search,
1 of 13.** `glyph/1/1/11/6/5` (m.14 P13): well-evidenced (`used` cites 3
rows, `right_of_and_level_with_a_head`), sits in the space below the top
line for an in-space head — correct by the window and, on the crop, visibly
right. `classify`'s tie (`MDF`) offers removing it as ONE of several ways
to reach the target sum on a two-voice bar; the companion voice's own head
fill (`F`) is the far more likely real fix. Crop #07.

### §18c. No connection fix built

Per the item's own escape valve: **this is not a connection fault, and the
detector is not simply failing to box a printed dot** (case 3, the one bar
where a real, printed-looking dot is genuinely rejected by the window, is a
single ambiguous instance, not a pattern) — the DOMINANT causes (§18b
classes 1 and 2, 9 of 13) are (a) an unrelated refusal family the
diagnostic script cannot see because it never consults `Q.AUG_DOT`/
`Q.DOT_ROLE`, and (b) the detector confusing a text period for a musical
dot, which `adjudicate_dot_role` already renders harmless by abstaining.
Neither calls for an ADJUDICATE/EVALUATE change; `tools/` is untouched by
this item, and `pytest`/`check` run only as the landing sanity check (no
code moved, figures are the base tree's own).

**What this means for §17's 578-bar headline.** `classify_held_mvt_2_22.py`
has the exact blind spot §13's caution warned about, generalised: on this
page 7 of 13 (54%) of its `D` attributions have zero supporting dot
evidence and a further 2 (15%) are a text speck the pipeline already
discards. If this page's ratio holds at movement scale — untested here,
NOT extrapolated as a number — a large share of the whole-movement 477/578
figures would be the SAME coincidence rather than a dot-reading defect.
Hardening `classify_held_mvt_2_22.py` to require a `D`-tied bar's cell to
hold at least one `Q.AUG_DOT` row before naming `D` (the §13 script's own
safeguard, never ported to the movement-scale one) is the recommended next
step — a diagnostic-tool fix, not a pipeline one, so it is named here and
left for whoever re-runs 2.22's own numbers rather than built inside this
item's scope.

**Asked, not built** (case 3, §18b): does a note immediately followed by a
tie ever print its augmentation dot BELOW the line/space it would otherwise
take — or is a low, isolated dot-shaped box beside a tie's start always the
tie's own ink? Two crops (`out/print/dot24-01.png` control,
`dot24-02.png` the case), manifest `out/print/dot-2.24-manifest.json`,
`VERDICT_none_yet: null`.

### §18d. Gates

No `tools/` code changed. `python3 -m tools.omr.staged.check` on this tree:
**TOTAL 247**, identical to `origin/main` (inventory 10, health 0, wiring
67, gather_coverage 15, capture 18, reach 24, brakes 9, trace 3, conventions
0, no_producer 0, export_coverage 0, accuracy_record 0, producers 0,
source_text_tests 46, mutation_batteries_live 55) — expected, since nothing
in `tools/` moved. `pytest tools/omr/tests -m "not slow" -q`: **3,770
passed, 3 skipped** (716 s, slowed by other sessions' concurrent load on
this machine) — main's own count exactly, 0 new tests, as expected with
`tools/` untouched.

### §18e. Files

- `probe/dot_probe_2_24.py`: dumps `Q.AUG_DOT`/`Q.DOT_ROLE`/
  `Q.NOTEHEAD_CLASS`/`Q.REST` for a list of cells, straight off
  `record_io.load_record` — the one sanctioned reader.
- `probe/quick_crop_2_24.py`: a single-region 600 dpi crop, scratch tool for
  eyeballing a page-pixel bbox before committing a manifest crop.
- `probe/crop_dots_2_24.py`: the 7 committed, frame-controlled, staff-banded
  crops (`crop_losers_2_6b._frame_ok`'s precedent) + manifest.
- `out/r224/brahms-p1.record.json` (45 MB, fresh gather, this tree) and its
  `.held.json`/`-partition.json` siblings: regenerable, not committed
  (`out/.gitignore`).
- `out/print/dot24-0{1..7}.png`, `out/print/dot-2.24-manifest.json`:
  committed.

## 19. ROADMAP 2.30 — the spurious EXTRA event nothing refused (2026-09-29)

PATH: STAGED. Branch `claude/extra-event-2.30`, off `origin/main` `8c652d89`.
Per Sean's process decision (relayed 09-29): conceptual wiring, microscopic
RED→GREEN fixtures only, from already-committed FINDINGS text and probe
output — no gather, no record-scale run, no crop batch, no pricing.

### §19a. What the extra events ARE, ranked by what the evidence supports

§17's whole-movement funnel (class `X`, "drop ONE event... that nothing
refused") does not itself say what family or geometry the dropped event
is — it is a SIMULATION letter, blind to cause. The only per-bar readings
of what `X` (and its neighbours) actually contain are §17c's 19 unmodelled
crops and §15d/§14's already-CLOSED classes. Sorted by how many independent
crops support each:

1. **Same-family duplicate box (ink boxed twice by the SHATTERING plate,
   one class).** DIRECTLY MEASURED, not just crop-observed: ROADMAP 2.15
   (§14) put a number on it for RESTS — Litolff 111, Brahms 882 refused
   duplicate boxes, 8 crop-confirmed, IoU 0.03–0.71 for a real same-class
   pair with a clean gap to 0. **Structural fact, not a new measurement:
   `notehead_precision.py` (noteheads) had NO equivalent check** — its own
   `reasons=` tuple before this item was `is_a_clef, clipped_fragment,
   too_narrow, belongs_to_a_nearer_staff, is_a_meter_digit, notehead`, no
   duplicate-box reason anywhere, while `family_precision.py` (rests) has
   carried one since 2.15. CLAUDE.md §10's SHATTERING-plate fact is stated
   about ink in general, not about rests specifically, and a notehead is
   the most common filled black mark on the page — "the value existed [the
   IoU floor 2.15 measured] and nothing read it [for noteheads]." Strongest
   evidence of the ranked list, because it is a code-comparison fact, not
   an inference from a caption.
2. **Neighbouring staff's ink surviving into the bar sum after a DECIDED
   removal.** MEASURED AND ALREADY CLOSED by 2.19/2.22 (§15d, §17d):
   `size_measure_rest` and `reconcile_duration` were summing boxes a
   DECIDED verdict (`too_narrow`, `rest_is_a_duplicate_box`,
   `owned_by_another_staff`) had already taken out of the bar. Not
   reopened here — named so it is not mistaken for a live gap.
3. **A rest read as a head, and vice versa (single mis-boxing, no second
   box to compare against).** THIN EVIDENCE: 3 of 19 §17c captions
   ("two quarter rests boxed as heads... a quarter rest under a fermata,
   boxed as a notehead... a rest is read as a note") describe this, but
   each caption names ONE box of one wrong class, not two overlapping
   boxes — there is nothing on the record to CONNECT (no duplicate ink,
   no ownership contest, no ledger absence); telling a rest's shape from a
   notehead's would need new measured geometry, which is a GATHER-adjacent
   classification question, not an ADJUDICATE connection. NOT BUILT, and
   not the same class as class 1.
4. **A barline fragment, staff-line fragment, dynamic letter, tie/slur end
   or staccato dot boxed as a head.** NO SUPPORTING CROP in this
   benchmark's evidence at all — these are the work order's own
   brainstormed candidates (CLAUDE.md §10's "a third of Breitkopf's
   stemless heads are barlines" is about the ALREADY-SHIPPED `too_narrow`/
   `clipped_fragment` population, not a gap in it). THINNEST evidence of
   the list; no connection attempted.
5. **Cross-family duplicate (a rest box and a notehead box on ONE mark).**
   NOT OBSERVED anywhere in §14's or §17c's crops — every duplicate-box
   crop 2.15 confirmed is same-family (rest/rest); every "rest read as a
   head" caption (class 3) describes a single box, not a pair. Plausible
   by analogy to class 1, but building it would be a GUESS. Asked, not
   built — see §19c.

### §19b. Built: `notehead_precision.adjudicate_notehead_is_not_a_notehead` grows a duplicate-box rule (class 1)

CONVENTION ESTABLISHED (cites, does not restate, ROADMAP 2.15's own
measurement): two `Q.GLYPH_BOX` boxes in one cell with IoU at or above
`REST_DUPLICATE_IOU_MIN` (0.02) are one physical mark read twice, whichever
family the detector called them. `notehead_precision.py` grows
`_notehead_duplicate_box_refusal` (helpers `_notehead_box_iou`,
`_notehead_duplicate_priority`, `_cell_notehead_boxes`, constant
`NOTEHEAD_DUPLICATE_IOU_MIN = 0.02`, cited not imported — `family_precision`
already imports FROM `notehead_precision`, so the reverse import would
cycle) — the SAME geometry and threshold 2.15 measured and shipped for
rests, restated rather than reused across the module boundary for that
reason, with a test pinning the two constants equal so they cannot drift
apart. New reason `notehead_is_a_duplicate_box`, run in
`adjudicate_notehead_is_not_a_notehead` right after `too_narrow` (a shape
question, GATHER-only facts, no dependency on decision order) and before
the meter-digit / ownership rules (which ask what the ink MEANS).

**Deliberately SAME-CLASS ONLY**, unlike 2.15's rest rule (which also
refuses a DIFFERENT-class rest pair). A different-class notehead pair
(`noteheadBlack` vs `noteheadHalf`) is §17c's "2.12g's role twins" — a
chord member's VALUE disagreement, explicitly "recorded, not built" there
because which member is right is 2.12g's own open question. Refusing both
here, as 2.15 does for a class-disagreeing rest, would discard a real note
rather than settle a "cannot tell" (a rest's class disagreement leaves no
value worth protecting; a notehead's does). `test_overlapping_DIFFERENT_
class_boxes_are_left_alone` pins this scope decision.

**Zero further wiring needed downstream, by construction, not by
edit**: `consequences._LEAVES_THE_BAR` already reads
`Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` generically (any DECIDED `True`, any
reason), so `size_measure_rest`/`reconcile_duration` (2.19/2.22) already
exclude a duplicate-refused box from the bar sum with no new code; and
`export.py`'s accounting already buckets every notehead refusal as
`not_a_notehead:<reason>` (`export.py:826`), so the new reason surfaces in
`status_census` as `not_a_notehead:notehead_is_a_duplicate_box` with no
export-side change. This is the same "connect, don't restate" shape 2.15's
own rest rule had with `export._place_notes`.

**RED → GREEN.** `tools/omr/tests/test_staged_notehead_duplicate_box.py`,
now 6 tests. RED confirmed by swapping in `origin/main`'s
`notehead_precision.py` (not `git checkout` on the dirty file — copied
aside and restored): **2 of 4 fail** (the refusal itself, and the
constant-pin test); the 2 CONTROLS (no-overlap pair both kept; a
different-class pair left alone — proving the SAME-class restriction is a
choice, not an accident of the fixture) pass on both trees, unchanged.
GREEN: 4/4 after restoring the edit.

**Caught before merge (manager): IoU alone is a REST threshold and is
UNSAFE for noteheads.** A CHORD legitimately puts two same-class heads
with touching or overlapping boxes right beside each other — a second
(0.5 staff space apart vertically, displaced sideways onto opposite sides
of the stem) or a third (1.0 space apart) — and those are two real notes,
not one mark twice. Added `_same_mark_centres` as a SECOND, independent
gate that must ALSO agree: both boxes' centres within
`NOTEHEAD_DUPLICATE_MAX_DY_STAFF_SPACES` (0.25 — CONVENTION ASSUMED, the
midpoint between "one mark" and a second's 0.5-space interval) AND
`NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS` (0.5) of each other; NOT CONFIRMED
with Sean, falsified by a real duplicate crop whose fragment centres sit
farther apart than this in either axis. Two new tests
(`test_a_chord_SECOND_is_not_mistaken_for_a_duplicate`,
`..._THIRD_...`), RED confirmed against the pre-guard commit (both fail,
the other 4 stay green) → GREEN 6/6 after adding the guard.

### §19c. Asked, not built: the cross-family question (class 5)

**Sean: where a rest-class box and a notehead-class box in one cell
overlap at 2.15's measured IoU floor, is that the same one-mark-boxed-
twice mechanism (refuse both, CLAUDE.md rule 8), or does it need its own
measurement?** CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED:
no crop in this benchmark's evidence shows a rest box and a notehead box
overlapping on one mark; §17c's "rest read as a head" captions are single
mis-boxings with no second box to compare against, so they would NOT be
caught by this mechanism even if the question were answered yes. A future
gather that finds such a pair, or a crop that does not, settles it either
way. Not built here — see `notehead_precision.py`'s own module docstring
for the same question stated beside the code it would change.

### §19d. Gates

`tools/omr/tests/test_staged_notehead_duplicate_box.py`: 4/4 passed in
isolation. Fast tier: `python3 -m pytest tools/omr/tests -m "not slow" -q
-p no:cacheprovider`: **3,877 passed, 3 skipped** (base `8c652d89`'s 3,873 +
4 new, 0 failed). `python3 -m tools.omr.staged.check`: **TOTAL 245**,
unchanged — confirmed by swapping in the base module (copy-aside/restore,
never `git checkout` on the dirty tree) and re-running `check` on it
directly: 245 both ways. No gather, no crop, no pricing, per Sean's
2026-09-29 process decision for this item.

### §19e. Files

- `tools/omr/staged/adjudicators/notehead_precision.py`: the new rule,
  its helpers, and the module/decision docstrings (§19a's ranking, §19c's
  question).
- `tools/omr/tests/test_staged_notehead_duplicate_box.py`: the tests.

## 20. ROADMAP 2.33 — two rest placement refusals, a crop-clip refusal, and
§19c's cross-family question, narrowed and answered (2026-09-29)

PATH: STAGED. Branch `claude/rest-placement-2.33`, next to ROADMAP 2.15's
duplicate-box rule in `adjudicators/family_precision.py`'s
`adjudicate_rest_is_not_a_rest`. Per Sean's 2026-09-29 process decision:
wiring proved by microscopic RED→GREEN fixtures, no gathers, no
record-scale runs, no crop batches.

### §20a. What Sean said, in the order he said it, and how each answer
narrowed the last

1. *"whole and half [rests] will always be found geometrically near the
   horizontal middle of the bar — I saw some false whole and half rests
   far off to one side of the bar."* Read as a work order for BOTH whole
   and half rests, then narrowed by Sean himself once the design question
   ("what happens when another voice's notes explain a half rest's
   position") was put to him: *"the centring rule applies to WHOLE rests
   only — a whole rest = the bar, centred."* For half and smaller: *"based
   upon the other notes in a measure there will be a limited space
   geometrically where the rest can be"* — a BEAT-SLOT rule keyed on the
   bar's other events, not a bar-wide fraction. **Built: `rest_off_center`,
   restWhole only** (§20b). **Designed, not built: the beat-slot rule**
   (§20d) — `Q.EVENT`/`Q.VOICES`/`Q.ONSET_COLUMN` are not yet decided at
   this point in `adjudicate.ORDER`, so the full rule cannot run here
   without reordering the pipeline, which this item does not do.
2. *"I don't think rests are found as high as note heads on the ledger
   lines."* Read first as one number (2.5 spaces beyond the outer line),
   then corrected by Sean from his own observation: *"I did see some 8th
   note rests outside the staff but not nearly as far as note heads."*
   **Built: `rest_outside_its_staff`, a PER-CLASS window** (§20c) — tight
   (1.0 space) for whole/half/quarter/`restHNr`/`restHBar`, wide (2.5
   spaces) for 8th-and-smaller, CALIBRATED TO SEAN'S OBSERVATION, NOT
   MEASURED (no crop was pulled this pass).
3. A third, independent cause, from Sean's own crops: *"a notehead looked
   a little bit like a whole note rest when the notehead was cut in half
   by the image crop — all examples where the rests were in a staff above
   or below the main staff."* **Built: `rest_clipped_by_crop`** (§20e),
   reusing `notehead_precision.py`'s own 2.4a edge test
   (`CELL_EDGE_TOLERANCE_PAGE_PX`) rather than restating it.

### §20b. `rest_off_center` — restWhole only

`_rest_off_center_refusal`: a `restWhole` box's centre, compared against
`Q.CELL_BOX`'s own `[x0, x1]` (the bar's horizontal extent — the cell frame
has NO horizontal pad; `measure_extractor`'s own docstring names the
padding for the vertical band alone, so `Q.CELL_BOX` needs no second
measurement to stand in for "the bar"). Refused where the offset from the
bar's centre exceeds `REST_WHOLE_CENTER_MAX_OFFSET_FRACTION = 1/6` of the
FULL bar width — "the middle third" stated geometrically: the band
`[1/3, 2/3]` of the bar has half-width `1/6` around the centre. No event or
voice is read (none is decided yet at this point in `ORDER`, and per
Sean's own narrowing none is needed: a whole rest denoting one voice's
silence for the WHOLE bar is centred regardless of what another voice is
doing — a second voice's own rest is displaced VERTICALLY, never
horizontally, which is rule 2's job). CONVENTION ASSUMED / WHAT WOULD
FALSIFY IT / NOT CONFIRMED: no crop confirms 1/6 exactly; falsified by a
print crop showing a genuine, undisputed whole-bar rest centred outside
that band.

### §20c. `rest_outside_its_staff` — per-class vertical window

`_rest_vertical_window_refusal` reuses `_ledger_geometry`/`_beyond_spaces`
UNCHANGED — the SAME "how many spaces past line 1 or line 5" question the
ledger rule already answers about a different class of ink.

**RECALIBRATED on manager review before merge** (two problems in the first
cut): a QUARTER rest is displaced for a second voice exactly as an 8th
rest is and needs the same room, and a displaced WHOLE/HALF rest in a
two-voice bar hangs a full space clear of the staff, not merely to the
band's own edge. Now two tiers, one class moved and one number raised:

| tier | classes | max spaces beyond the band |
|---|---|---|
| MEDIUM | `restDoubleWhole`, `restWhole`, `restHalf`, `restHNr`, `restHBar` | 1.5 (was 1.0) |
| WIDE | `rest8th`, `rest16th`, `rest32nd`, `rest64th`, `rest128th`, `restQuarter` (moved from the tight/medium tier) | 2.5 |

MEDIUM is "a small margin over never observed leaving the staff, plus room
for a displaced whole/half rest hanging one space clear." WIDE admits a
genuinely displaced-voice rest (`REST_VOICE_DISPLACEMENT_MIN_STEPS` in
`rhythm.py`, ROADMAP 2.27c — a DIFFERENT, narrower convention about which
VOICE a rest belongs to, and one that never leaves the staff band at all:
its own reach is ±1.5 STEPS from the middle line, i.e. well inside the
0–8 step band this rule's window sits entirely outside of) and stops well
short of how far a note on a ledger line goes (CLAUDE.md §10's Brahms C
Horn 2, 4.5 spaces below its staff). CALIBRATED TO SEAN'S OBSERVATION, NOT
MEASURED — falsified by a print crop showing a MEDIUM-tier rest genuinely
printed beyond 1.5 spaces, or a WIDE-tier rest printed farther out than
2.5 spaces. Unlisted classes fall back to MEDIUM, the tightest tier still
named now that `restQuarter` has moved to WIDE.

⚠️ Both `rest_off_center` and `rest_outside_its_staff` run BEFORE
`Q.GLYPH_OWNER` structurally, not by any gate written in this file's code:
`adjudicate.ORDER` schedules `Q.REST_IS_NOT_A_REST` well before
`Q.GLYPH_OWNER` (the same slot `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` already
holds, for the same reason — a question about what a box IS must be
settled before the questions that assume the answer). So neither rule can
ever contradict a DECIDED owner verdict, because none exists yet when
either runs; no code here pretends to check for one.

### §20d. The beat-slot design for half-and-smaller rests — WRITTEN, NOT
BUILT

Sean's own words: *"based upon the other notes in a measure there will be
a limited space geometrically where the rest can be."* Stated as a design:
a non-whole rest occupies the horizontal GAP between its voice's
neighbouring events, at the onset its own preceding durations imply within
that voice, and — on a conductor's page — lines up with the OTHER staves'
onset columns (`Q.ONSET_COLUMN`, already gathered and voted). Checking it
in full needs `Q.EVENT` (which events precede and follow this one in the
same voice), `Q.VOICES` (which voice this rest is in) and `Q.DURATION`
(what those neighbours' onsets actually are) — all three decided AFTER
`Q.REST_IS_NOT_A_REST` in `adjudicate.ORDER`, so the full rule cannot run
inside `adjudicate_rest_is_not_a_rest` without moving it later in the
pipeline, which is a bigger change than this item's brief (no gathers, no
reordering) covers. Named as a ROADMAP follow-up, not scheduled.

### §20e. The decisive sub-rule that DOES follow, without waiting on
`Q.EVENT`/`Q.VOICES` — and §19c, answered

§20d's design reduces to one case decidable from GATHER-level facts alone:
this glyph's own ink cannot simultaneously BE a rest (an absence of ink at
that position) and sit on top of a notehead's ink, in ANY voice —
overlapping detector boxes on one cell are two readings of ONE mark
(§14's own argument for two REST boxes), never two symbols legitimately
sharing one spot regardless of which voice either belongs to. This is
exactly **§19c's cross-family question, asked and left unanswered in
ROADMAP 2.30** (*"where a rest-class box and a notehead-class box in one
cell overlap at 2.15's measured IoU floor, is that the same
one-mark-boxed-twice mechanism... or does it need its own measurement?"*):
the answer built here is YES, the same mechanism, at the SAME measured
floor (`REST_DUPLICATE_IOU_MIN`, reused as `REST_NOTEHEAD_OVERLAP_IOU_MIN`
— not a new measurement, since it is the SAME geometric fact, "two
detector boxes on one mark," applied to a different pair of classes).

`_rest_overlaps_notehead_refusal` (reason `rest_overlaps_a_notehead`):
over every `Q.NOTEHEAD_CLASS` glyph's `Q.GLYPH_BOX` in the same cell, an
overlap at or above the floor refuses this rest — UNLESS the overlapping
notehead's own `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdict is already DECIDED
refused, in which case the overlap proves nothing (a refused notehead's
ink might be the SAME misread mark this rest box also mis-boxed — CLAUDE.md
rule 8, cannot-tell is never converted into an answer). Reading that
verdict back is safe, not a guess, because `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`
is scheduled BEFORE `Q.REST_IS_NOT_A_REST` in `ORDER` (beside the ledger,
ahead of the accidental/rest/arc/dynamic/articulation block) — the one
quantity among this item's new checks that IS a real connection to an
already-decided verdict rather than one still in flight. §19c's own "not
built here" note in `notehead_precision.py` stands corrected by this entry.
The FULL beat-slot rule (§20d) remains the open item; this is the one
piece of it that needed no voice count and no onset column.

**RECALIBRATED on manager review before merge — the IoU floor alone was
UNSAFE.** `REST_DUPLICATE_IOU_MIN` (0.02) is a REST-DUPLICATE floor, tuned
for two boxes fragmenting ONE mark on a SHATTERING plate; it is unsafe for
a rest-vs-notehead pair because a displaced VOICE's rest can legitimately
sit right next to the OTHER voice's notehead, boxes touching, without
being one mark at all. Fixed the way ROADMAP 2.30 (§19a) fixed the same
shape of problem for a notehead/notehead pair: `_same_mark_centres`
(`notehead_precision.py`, imported not restated) is now a SECOND,
mandatory gate — both boxes' centres must sit within
`NOTEHEAD_DUPLICATE_MAX_DY_STAFF_SPACES` (0.25 space) vertically and
`NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS` (0.5 head widths) horizontally,
in addition to a raised, substantial IoU floor (`REST_NOTEHEAD_OVERLAP_
IOU_MIN` 0.02 → **0.3**). A control was added: a displaced voice-2 rest
touching a voice-1 notehead (IoU ≈0.05, centres a full staff space apart)
is kept on EITHER gate alone.

### §20f. `rest_clipped_by_crop`

Sean, from his own crops: *"a notehead looked a little bit like a whole
note rest when the notehead was cut in half by the image crop — all
examples where the rests were in a staff above or below the main staff."*
A notehead sliced by the cell's own top or bottom edge leaves a flat black
rectangle — a `restWhole`/`restHBar` silhouette by shape alone.
`_rest_clipped_by_crop_refusal` reuses (imports the CONSTANT, restates
nothing) `notehead_precision.CELL_EDGE_TOLERANCE_PAGE_PX` (1 page px) —
the SAME edge test `_clipped_fragment` uses for noteheads (2.4a) — against
this glyph's own `bbox_page_px` and `Q.CELL_BOX`. ⚠️ NOT the height gate
`_clipped_fragment` also carries: Sean's case is the opposite shape from a
notehead sliver (short, at the edge) — a notehead cut in HALF by the crop
can measure a perfectly ordinary rest height while still being pure crop
artefact, so a height gate would let the exact case through. The edge test
alone is what a `restWhole`/`restHBar`-shaped fragment shares with the
real thing being cut. Never relocated: the neighbour staff's own cell
holds its own detection of the same ink (CLAUDE.md §10's ledger-line rule
states this for cross-staff ink generally); this refuses ON THIS STAFF and
stops there. Checked FIRST among the four new rules (before `rest_off_
center` and `rest_outside_its_staff`) because it is the DIRECT, named
cause; the vertical window (§20c) usually catches the same fragments too
(a notehead cut off by the top/bottom crop edge is, ordinarily, also far
outside the staff band) — both are kept, one as the cause-level guard, one
as the geometric backstop for whatever the cause-level guard misses (e.g.
a fragment cut off by a LEFT/RIGHT crop edge on an unusually narrow cell,
which the vertical rule cannot see and the edge rule can).

### §20g. `inventory --check`'s AST blind spot, hit again and worked
around the established way

The first draft imported `notehead_precision._cell_box_page` directly
(`from .notehead_precision import _cell_box_page`) to read `Q.CELL_BOX`.
`inventory --check` reported `rest_is_not_a_rest declares 'cell_box' in
wants and never reads it` — `_never_read`'s AST walk follows a same-module
helper call, and (since ROADMAP 2.27c) one hop through a `from . import X`
MODULE import, but not a direct `from .module import name` NAME import.
Fixed the way `_cell_staff_space` already is between these same two
files: a one-line local `_cell_box_page_px` in `family_precision.py`,
duplicated rather than imported, so the AST walk sees a real read. Not a
new pattern — an existing one, applied a second time.

### §20h. Two more witnesses, and the overlap RESOLVED instead of always
refusing the rest (manager review, second round, both citing Sean)

Sean, `docs/DECISIONS.md` (2026-09-29, last entry on `origin/main` at the
time): *"it went both ways but a common mistake was a black notehead
called a whole or half rest. The rest should never touch 2 different
staff lines."* Asked what else helps tell the two readings apart: *"if
there is a stem attached or the bar sum needs the notehead then those
also help."* Three witnesses now, checked in this order (§REST-VS-NOTEHEAD
in `family_precision.py` has the full docstring):

1. **`rest_has_a_stem`** (every rest class, checked FIRST). A rest never
   has a stem. `_rest_has_a_stem_refusal` reuses `rhythm._stems_on`'s own
   box-overlap test — the SAME one `adjudicate_stem_direction` uses to
   find a notehead's stem — against `Q.STEM`'s boxes in this cell. Any
   overlap refuses the rest outright, whatever class it was boxed as.
2. **`rest_touches_two_staff_lines`** (`restWhole`/`restHalf` ONLY —
   quarter/8th/etc. legitimately span more than one line/space by their
   own printed shape, so the test says nothing about them).
   `_rest_line_shape` measures how many staff lines this box's ink
   TOUCHES (an edge within `ON_A_STAFF_LINE_TOL_SPACES` of a line — REUSED
   from the ledger's own tolerance, not a new number — OR a line running
   through the box's y-range, the half-rest shape): **two** touched lines
   is a box spanning a whole space, a notehead's own shape, refused;
   **one** is a genuine whole rest (top edge on a line) or half rest (one
   line through the middle), kept; **zero**, or no staff geometry at all,
   is `"cannot_tell"`, also kept (rule 8).
3. **The overlap RESOLUTION** — for `restWhole`/`restHalf` ONLY, where
   this box also overlaps a live notehead (§20e's own mechanism):
   `_rest_overlaps_notehead_refusal` now reads `_rest_line_shape`'s
   verdict instead of always refusing. `"two_lines"` cannot be read here
   in PRACTICE (witness 2 above runs earlier in the same ladder and would
   already have refused — the branch is written explicitly anyway, in
   case a future reordering changes that invariant, and is exercised
   directly by a unit test that pre-seeds `detail["line_shape"]`).
   `"one_line"` means the rest reading has POSITIVE shape evidence, so the
   rest STANDS (not refused) — `detail["notehead_reading_should_be_
   dropped"]` records which notehead rows a future consequence should
   revise. `"cannot_tell"` refuses NEITHER (rule 8). Every OTHER rest class
   keeps the OLD behaviour unconditionally: an overlap always refuses the
   rest, because witness 2 has no opinion on those classes at all.

⚠️⚠️ THE NOTEHEAD SIDE DOES NOT YET LEARN "ONE_LINE" ON ITS OWN — NAMED,
NOT BUILT, AND FOR THE SAME REASON THROUGHOUT THIS ITEM. `Q.NOTEHEAD_IS_
NOT_A_NOTEHEAD` runs BEFORE `Q.REST_IS_NOT_A_REST` in `adjudicate.ORDER`,
so by the time ADJUDICATE could say "the rest reading won, drop the
competing notehead" the notehead's own verdict is already frozen on the
log; only EVALUATE can revise an earlier ADJUDICATE verdict (the same
shape `move_glyph`/`respell_accidental` already use). Recorded on the
record (`notehead_reading_should_be_dropped`) so the connection point
exists even though nothing reads it yet.

### §20i. (d) — the bar sum as a fourth witness: named, not built

Sean's fourth witness — *"if... the bar sum needs the notehead then those
also help"* — belongs in EVALUATE, not ADJUDICATE (the bar sum is not
known until then). Assessed rather than built: wiring
`consequences.reconcile_duration` to try BOTH readings of a `"cannot_
tell"` mark (this glyph counted as a rest vs. counted as a pitched note)
and keep whichever makes the bar's own sum land exactly needs (1) a
Q.-level fact naming which glyphs are in this ambiguous state (today only
in `detail`, not a quantity `EVALUATE` can read), (2) a way for that
consequence to not just re-read a DURATION but flip a NOTEHEAD/REST
identity — reaching into `Q.EVENT`'s grouping and the export-side pitch
path, not merely a duration re-reading — and (3) a rule for what happens
to the LOSING reading's own verdict, which is the exact revise-an-earlier-
verdict problem §20h's `notehead_reading_should_be_dropped` is already
waiting on. This is materially MORE than a small connection (the explicit
bar this item's brief draws: build (c)/(a)/(b) now, name (d) if it is
more), so it is the next ROADMAP item, not built here.

### §20j. Tests and gates

`tools/omr/tests/test_staged_rest_placement_2_33.py`, grown across three
review rounds to **23 tests**: the original 12 (off-centre×3,
vertical-window×4, crop-clip×2, notehead-overlap×3, one of which —
`test_off_center_rule_does_not_apply_to_half_rests` — was re-shaped in
round 2 to a genuine one-line half-rest fixture once the two-staff-line
rule made its original geometry a real `two_lines` case), plus round 1's
window recalibration (`test_whole_rest_one_space_above_the_staff_is_kept`,
`test_quarter_rest_now_gets_the_wide_window_is_kept`, and the displaced-
voice-touches-a-notehead control, net +3), and round 2's stem witness (2),
two-staff-line witness (4, incl. the quarter-rest exclusion control), and
three-outcome overlap resolution (3, incl. one direct unit-level call for
the `"two_lines"` defensive branch the full ladder cannot reach) — net
+9 more. One refusal and one control per rule throughout; RED confirmed
at each round by swapping `family_precision.py` aside for `origin/main`'s
or the prior round's copy (copy-aside/restore, never `git checkout` on
the dirty tree). A genuine fixture collision was found and fixed along
the way, not papered over: `test_staged_family_refusals.py`'s shared
`_pair` helper placed every family's own test box at the SAME canonical
position as its "for the ledger's sake" notehead anchor, which the new
overlap rule (round 1) correctly read as one mark and refused — `_pair`
grew an `own_x_c` parameter (default unchanged, so the other nine
families are untouched) and the rest test alone passes a separated
position.

`python3 -m tools.omr.staged.check`: **TOTAL 245, status=ok** (unchanged
from the `origin/main` baseline this branch is off) at every round.
`inventory --check` and `wiring --check` both closed clean after §20g's
fix — no new entry on either, and no `KNOWN_GAPS` addition was needed.
`pytest tools/omr/tests -m "not slow"`: **3910 passed, 3 skipped, 0
failed** after all three rounds (base 3899 after round 1 + 11 net new
tests from rounds 2/3).

No gathers, no crop batches, no pricing runs, per Sean's 2026-09-29 process
decision for this item.

### §20k. Files

- `tools/omr/staged/adjudicators/family_precision.py`: the six refusals
  (§REST-PLACEMENT, §REST-VS-NOTEHEAD), their constants and helpers, and
  the updated `Q.REST_IS_NOT_A_REST` decision spec/docstring.
- `tools/omr/tests/test_staged_rest_placement_2_33.py`: the tests.
- `tools/omr/tests/test_staged_family_refusals.py`: the `_pair` fixture
  fix (§20j).
- `benchmarks/omr-owner-domain-2026-09/PLACEMENT-CONVENTIONS.md`: the
  Rests row, updated to point here.

## 21. ROADMAP 2.35 — the rest beat-slot connection, the part that FOLLOWS
(2026-09-29)

PATH: STAGED. Branch `claude/rest-beat-slot-2.35`, off `origin/main`
(5173d91c). Sean, 2026-09-29 (`docs/DECISIONS.md`, quoted in full at §20d
above): *"based upon the other notes in a measure there will be a limited
space geometrically where the rest can be."* §20d named this design and left
it WRITTEN, NOT BUILT because `Q.EVENT`/`Q.VOICES`/`Q.DURATION` are all
decided AFTER `Q.REST_IS_NOT_A_REST` in `adjudicate.ORDER` — this item builds
the part of it that FOLLOWS.

### §21a. Where it lives, and why

`consequences.rest_beat_slot` — a NEW **EVALUATE** rule
(`Consequence.REST_BEAT_SLOT`, cause `Q.VOICES`, effect
`Q.REST_IS_NOT_A_REST`), not an edit to `adjudicate_rest_is_not_a_rest`. The
three quantities the design needs are all EVALUATE-stage facts by the time
they exist on the record — ADJUDICATE has already frozen a False (`"rest"`)
verdict for every rest this rule might still refuse — so the only place a
change built FROM them can run is a stage that revises an earlier one.
`apply_printed_accidental` is the model: it supersedes `Q.ACCIDENTAL` from
EVALUATE exactly as this supersedes `Q.REST_IS_NOT_A_REST`. `Q.VOICES` and
`Q.REST_IS_NOT_A_REST` are new entries in `evaluate.DOWNHILL`, inserted
BEFORE `Q.METER`/`Q.DURATION` (not after) so `rest_beat_slot` fires earlier in
the SAME EVALUATE pass than `size_measure_rest`/`reconcile_duration` — a rest
this rule refuses is already out of the bar by the time either of those sums
it, the same ordering argument `_LEAVES_THE_BAR` makes for an ADJUDICATE
refusal, applied to one decided mid-EVALUATE instead.

### §21b. The two sub-rules built, and what is deliberately NOT

Two FORCED checks, either one refusing outright (reason word each):

1. **`rest_shares_a_beat_slot`** — this rest's own box shares horizontal
   space with ANOTHER event of its own voice (their canonical x-ranges
   overlap) — no gap exists there, so the "rest" reading is contradicted by
   the print itself.
2. **`rest_after_the_bar_ends`** — the events of this voice strictly BEFORE
   this rest (by print position, all DECIDED) already sum, in beats, to the
   bar's own METER — there is no time left in the bar for this rest to
   occupy, which is what "the onset order its events imply" forces once
   every input is DECIDED.

NOT built, and named rather than guessed at: `Q.ONSET_COLUMN` (the
cross-staff, already-gathered-and-voted witness §20d's design also names) and
any argmax between two readings that both fit — CLAUDE.md §4a reserves that
choice for INFER, which this item's brief keeps out of scope. Multi-voice
bars are ALSO out of scope, by a scope line rather than a gap left open:
ROADMAP 2.27c's own convention (`_rest_voice_side`, decided INSIDE
`Q.VOICES`) already owns which voice a rest belongs to and where a displaced
one may legitimately sit beside another voice's note; re-adjudicating that is
not this item's brief. `_rest_beat_slot_context` returns `None` — no verdict,
the rest stands — wherever `Q.VOICES` decided more than one stream.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: excluding
`restDoubleWhole`/`restHNr`/`restHBar` alongside `restWhole` (ROADMAP 2.33's
own scope) is READ OFF Sean's words rather than separately measured — these
three mean "the whole bar" in a longer or shorter meter exactly as
`restWhole` does. Falsified by a print crop showing one of the three sharing
a bar with other same-voice notes, which is the one case this scoping would
wrongly admit.

### §21c. Reaching EXPORT through the existing accounting

`export.py:838` already reads `Q.REST_IS_NOT_A_REST` through
`rec.verdict(...)` (supersession-resolved) and drops the glyph under
`f"not_a_rest:{reason}"` — the SAME accounting 2.33's six refusals already
use. No export-side change was needed: a rest `rest_beat_slot` refuses is
counted `not_a_rest:rest_shares_a_beat_slot` /
`not_a_rest:rest_after_the_bar_ends` and never reaches `to_musicxml`'s
`Unbalanced` equality as an unaccounted note, exactly like every other named
rest refusal.

### §21d. Tests, RED → GREEN

`tools/omr/tests/test_staged_rest_beat_slot_2_35.py`, 10 tests, one call per
test directly against `consequences.rest_beat_slot(log, glyph, voices)` (the
same style `test_staged_reconcile_what_is_in_the_bar.py` and
`test_staged_measure_rest_left_the_bar.py` use — no gather, no
`evaluate.run()`, hand-built `Log` fixtures via `record.glyph`/`cell`/
`system`):

- 2 RED→GREEN, one per sub-rule (`TestCheckA_Overlap`,
  `TestCheckB_OnsetOverflow`) — confirmed RED by copying `origin/main`'s
  `consequences.py`/`evaluate.py` over the working tree (copy-aside/restore,
  never `git checkout` on the dirty tree) and re-running: all 10 tests fail
  with `AttributeError: module 'tools.omr.staged.consequences' has no
  attribute 'rest_beat_slot'`, confirming the connection did not exist before
  this item, not merely that one assertion was wrong.
- 2 positive controls, Sean's own two named in the brief: a legitimate rest
  in a real gap with room left in the bar is KEPT; a displaced voice-2 rest
  touching a voice-1 note is KEPT (the multi-voice scope line, §21b).
- 3 abstain cases: an ABSTAINED `Q.VOICES` (the harness's own pre-filter,
  exercised directly); a NARROWED neighbour duration (check (B) cannot sum
  the bar and returns `[]` rather than guess); an ABSTAINED meter (same).
- 3 scope/supersession: an already-refused rest is left alone (never
  re-decided); a `restWhole` that WOULD overlap is out of scope even then
  (2.33 already owns it); the basis names the contest (`Q.VOICES`, `Q.EVENT`,
  the prior ADJUDICATE verdict).

### §21e. Gates

`pytest tools/omr/tests/test_staged_rest_beat_slot_2_35.py`: 10 passed.
`pytest -m "not slow" tools/omr/tests -q -p no:cacheprovider`: **3,933 passed,
3 skipped** on this branch, **3,923 passed, 3 skipped** on `origin/main`
(measured directly, copy-aside/restore) — the +10 is exactly this item's own
test file, run clean twice. `python3 -m tools.omr.staged.check`: **TOTAL 245**
both on `origin/main` and on this branch (same per-check breakdown:
inventory 10, health 0, wiring 67, gather_coverage 15, capture 18, reach 22,
brakes 9, trace 3, source_text_tests 46, mutation_batteries_live 55) —
unchanged. `inventory --check`/`wiring --check`: no new
entry — `rest_beat_slot` writes a raw `Verdict` (like `apply_printed_
accidental`) rather than an ADJUDICATE `Ruling`, so its two new reason words
are not read by `brakes._reasons_constructible`'s AST walk over
`family_precision.py` and were deliberately NOT added to `Q.REST_IS_NOT_A_
REST`'s own `reasons=` tuple there (adding them would make that check fail —
no `Ruling(reason=...)` site in that module constructs them).

### §21f. Asked, not built

Whether a print crop would confirm the `restDoubleWhole`/`restHNr`/
`restHBar` scoping (§21b's CONVENTION ASSUMED) — no crop was pulled this pass
per Sean's 2026-09-28/29 process decision (wiring proved by fixtures, no crop
batches). Whether `Q.ONSET_COLUMN`'s cross-staff witness should join this
connection on a conductor's page — named in §20d, not this item's brief.

### §21g. Files

- `tools/omr/staged/consequences.py`: `rest_beat_slot` and its helpers
  (`_rest_beat_slot_context`, `_rest_beat_slot_overlap`,
  `_rest_beat_slot_onset`, `_rest_beat_slot_also_reads`).
- `tools/omr/staged/evaluate.py`: `Consequence.REST_BEAT_SLOT`; `Q.VOICES`
  and `Q.REST_IS_NOT_A_REST` added to `DOWNHILL`.
- `tools/omr/tests/test_staged_rest_beat_slot_2_35.py`: the tests.
