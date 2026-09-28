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
