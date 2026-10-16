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
## 21. ROADMAP 2.45 — a rest between two staves belongs to the staff whose voice would otherwise be missing (2026-09-30)

Sean, DECISIONS 2026-09-30, on Brahms 1/i Breitkopf p1 system 0, printed
bar 13 (`Q.PRINTED_BAR_NUMBER` at `system/1/0` = 8, this bar is cell index
5), three printed eighth rests between staves 2 and 3, each detected once
per staff (`glyph/1/0/2/5/{0,3,10}` and `glyph/1/0/3/5/{0,1,2}`, one
physical rest per pair), all six refused `rest_outside_its_staff` by
2.33's per-class vertical window:

> "They belong to the lower staff. I was able to determine that based on
> the amount of voices in each of the staffs. The one above has 2 voices
> and both the voices are accounted for. The one below has a voice that
> crosses as they both jump up higher. If the 8th note rests didn't belong
> to the lower staff then it would be missing a voice."

⚠️ **Manager correction, 2026-09-30, to the FIRST build of this item.** The
first build fired zero times on Sean's own case, for two design faults plus
one page-specific blocker it had mis-stated. All three are fixed/named
below.

⚠️ **Second manager correction, 2026-09-30**, after the first fix's A/B was
correctly diagnosed as blocked by the meter (§21c) but the fix itself still
carried a FOURTH fault (§21a.4): the candidate staff was required to be
COMPLETE, when it only needs to be unable to explain the SAME group.

### 21a. What was wrong, and the fix

1. **A staff's expected total is VOICES × bar length, not one bar length.**
   Sean reasons per voice: a staff carrying two simultaneous voices must
   sum to TWICE the bar, because each voice independently spans the whole
   bar. New helper `_voice_count(log, cell_subject)` reads `Q.VOICES`
   where DECIDED (its own `n_voices` field), else counts DECIDED
   `Q.STEM_DIRECTION`s exactly as `adjudicate_voices` counts them at its
   own first rule (ROADMAP 2.21) — two that disagree is two voices, one
   direction only is one voice, neither decided is UNDECIDED and this rule
   abstains (rule 8) rather than assume one.
2. **The contested rests are ONE GROUP per bar against one neighbour
   staff, not independent per-rest tests.** New helper `_contest_group`
   collects every glyph in a cell that is ALSO refused
   `rest_outside_its_staff` against the SAME neighbour staff; a staff's
   shortfall must equal the GROUP's own total length (`_group_length`),
   never one rest's own duration. Sean's three eighth rests are one group
   of 1.5 beats.
3. **The meter read is whatever `Q.METER` DECIDED, never a better guess**
   — unchanged in principle from the first build, but the first build's
   own report mis-stated the bar as generically "9/4" without naming which
   known defect that is. Named precisely below (§21c): it is ROADMAP
   2.12h/2.12l/2.29's own still-unrepaired chain on this exact system.
4. **The candidate staff need not be COMPLETE, only unable to explain the
   SAME group** (second correction). The first fix required the candidate's
   own shortfall to be exactly zero; Sean's own upper staff carries a
   separate, unrelated ~1-beat gap in this same bar (§21c), and that gap
   must never block the lower staff's own exact match. The candidate test
   now compares the candidate's own shortfall to the GROUP's length, not
   to zero — a candidate whose shortfall equals the group's length too is
   ambiguous (refused, rule 8); any OTHER shortfall on the candidate is not
   evidence either way and does not block.

`_bar_total_excluding` (renamed from `_bar_total_excluding_refused`) now
takes a `force_exclude` set so a GROUP is excluded as one group,
order-independently: this rule runs once per glyph, so a group's members
are visited one at a time within the same EVALUATE pass, and
`_left_the_bar` alone would report a growing total mid-pass once an
earlier group member is reinstated. Naming every group member up front
(from the ORIGINAL ADJUDICATE state, never from what this rule has
written so far this pass) keeps every member's own test answering the
same question regardless of visit order.

`Q.REST_IS_NOT_A_REST` stays in `evaluate.DOWNHILL` after `Q.DURATION`
(cause `Q.METER`), for the same reason as before: whether a rest is
reinstated follows from a fact about the BAR, which only exists once
ADJUDICATE has settled duration, ownership and refusals. It deliberately
still does not read `Q.VOICES`'s own grouping for the TOTAL (only for the
COUNT) — `adjudicate_event` reads `Q.REST`, never `Q.REST_IS_NOT_A_REST`,
so a rest's refusal never leaves that grouping at all; `_bar_total_
excluding` is the one reader that does respect it.

### 21b. Tests — RED→GREEN, 15 tests, no gathers

`tools/omr/tests/test_staged_rest_between_staves_2_45.py`, rebuilt around
Sean's actual shape: 2 voices per staff (`Q.VOICES` DECIDED), a 6/8 meter
(bar length 3.0), one group of three eighth rests (1.5 beats total).

- **`TestSeansCase`** (4 tests): the WHOLE GROUP reinstates on the lower
  staff; the upper staff's own three copies of the same group stay refused
  (already complete at 2×3.0=6.0 without them); **the candidate need not
  be complete, only unable to match (second correction) — the lower staff
  is short exactly the group's length (1.5), the upper staff has its OWN
  unrelated shortfall of 1.0 (not 0, not 1.5), and the group still
  resolves to the lower staff**; the identical mechanism resolved via the
  `Q.STEM_DIRECTION` fallback where neither cell has `Q.VOICES` at all.
- **`TestControls`** (11 tests): not refused at all; refused for a
  different reason; no contest at all; voice count undecided on the own
  staff; **both staves match the group EQUALLY (genuinely ambiguous,
  rule 8 — re-shaped from the first correction's "candidate not complete"
  control, which the second correction makes moot)**; a shortfall that
  does not match the GROUP's own length on the own staff; an undecided
  candidate bar; no meter; a whole-rest twin kept on its own staff; the
  rest's own duration undecided.

RED confirmed twice: moving `reinstate_rest_between_staves`,
`_bar_total_excluding`, `_contest_group`, `_group_length` and
`_voice_count` out of `consequences.py` fails all 15; reverting only the
candidate-shortfall comparison to its first-correction form (`shortfall ==
0` instead of `shortfall == group_len`) fails exactly the one new test and
none of the other 14. Restored both ways → 15 passed. `pytest -m "not
slow" tools/omr/tests`: 4158 passed (+15 over the `origin/main` baseline),
0 failed. `python3 -m tools.omr.staged.check`: TOTAL **245, unchanged**.

### 21c. A/B through EVALUATE, Brahms p1 — reach is STILL zero, and now precisely diagnosed

Base = `origin/main` (`ed389862f`, a separate `git worktree`). Arm = this
branch. `python3 -m tools.omr.staged <pdf> --pages 1 --weights auto
--route-weights --through evaluate --out <rec>`.

**The voice-count fault is confirmed FIXED and is NOT the blocker on this
page.** `Q.VOICES` is DECIDED on both cells of this exact bar: `cell/1/0/2/5`
(upper) `n_voices=2` (`two_voices_same_beat`), `cell/1/0/3/5` (lower)
`n_voices=2` (`two_voices_same_beat`) — exactly matching Sean's own count.
`_voice_count` reads both correctly; the rule reaches the meter/bar-sum
test on every one of the six glyphs.

**CORRECTED (manager, third round): the DECIDED `9/4` was an artefact of
gathering page 1 ALONE, and is NOT what the pipeline decides once the
meter/key carry has the context to read.** `Q.PRINTED_BAR_NUMBER` at
`system/1/0` is DECIDED `8`, so the bar in question (cell index 5) is
**printed measure 13** and cell index 1 is measure 9 — ROADMAP 2.12h/
2.12i/2.12l/2.29's own "m. 8 hemiola" / "m. 9 return to 6/8" system. Two
independent checks, neither a single-page artefact:

- Re-gathered with `--pages 0-1` (the movement's own first two pages, so
  the carry has SOME context): `Q.METER` at `system/1/0` is now
  **ABSTAINED**, `reason="meter_return_not_read"` — NOT `9/4`.
- Read directly (no re-gather) from the committed whole-movement record
  `library/_shared-records/brahms1-breitkopf-mvt1-whole-20260930b.
  record.json`: the SAME single verdict, `Q.METER` at `system/1/0`
  **ABSTAINED**, `reason="meter_return_not_read"`, value `null`.

So `9/4` was never the pipeline's real answer on this system — it is what
a context-starved single page falls back to, and every wider gather
correctly ABSTAINS instead (2.12l's own unread mid-system return, still
open). The manager's own cited "4,283 bars judged against 3.0 quarters
(6/8)" is the ACCEPTANCE FUNNEL's *external reference-encoding* target
(FINDINGS §2, "the meter in force is the FILE's, not the record's"), not
`Q.METER`'s own DECIDED value — this pipeline never asserts 6/8 here at
all. **Zero reinstated**, correctly: `evaluate._pass` skips a subject
whose cause is ABSTAINED (`cause_abstained`), so this rule never even
reaches the bar-sum test — exactly rule 8's own shape, not a computed
mismatch.

**If `Q.METER` were DECIDED 6/8 here (it is not — it ABSTAINS), the case
WOULD resolve to the lower staff.** Manager correction (second round): the
candidate staff need not be COMPLETE, only unable to explain the SAME
group — its own shortfall must not also equal the group's length.
Hand-checked with 6/8 substituted for the ABSTAINED meter, using the real
gathered totals (unchanged across every re-gather of this bar — single
page, two pages, and the whole-movement record all measure the same ink):
bar length 3.0, 2 voices on both cells. Lower staff — expected
`2 × 3.0 = 6.0`, actual (excluding the group) 4.5, shortfall **1.5,
exactly the group's length: a match.** Upper staff — expected 6.0, actual
(excluding its own copies of the group) 5.0, shortfall **1.0 — NOT 1.5, so
it cannot explain this group** (its own, unrelated ~1-beat gap, most
plausibly an undetected GATHER-side miss in this same bar, named not
diagnosed here). One match, one non-match: **the corrected rule would
resolve the group to the LOWER staff**, exactly as Sean read it. This
remains a hand check only — this rule never substitutes a meter itself,
and reading the m. 9 return to 6/8 (`meter_return_not_read`) is
2.12h/2.12i/2.12l/2.29's own open follow-up; this item's own rule needs no
further change once that lands.

**Litolff p3 is unchanged from the first build**: zero between-staff rest
contests exist on that page at all (not re-run this round — nothing in
the mechanism touches contest DETECTION, only how a found contest is
resolved, and Litolff has none).

**Per CLAUDE.md §6b** ("an arm prints its population first and exits
non-zero declaring itself DEAD at zero"): population = 1 contest (one
group of 3 rests); resolved = 0; blocked by (1) a known, named,
unrepaired meter misread on this exact bar and (2) a second, independent,
undiagnosed ~1-beat gap on the candidate staff. The mechanism itself is
demonstrated correct by the 14 unit tests, which inject the correct meter
directly and show the exact resolution Sean describes.

### 21d. Print check

`out/print/2.45/brahms-p1-bar5-between-staves.png` (1095×1813, 600 dpi,
frame control passed: staff 2 contrast 134.2, staff 3 contrast 205.5).
Staff 2's five lines drawn in blue, staff 3's in green, the three rests
boxed in red. Caption states Sean's reading (the rests belong to the
lower/green staff), and both blockers in words with the exact numbers
above. Script:
`benchmarks/omr-bar-sum-holdout-2026-09/probe/crop_between_staves_2_45.py`.

### 21e. Convention registry

`docs/engraving-conventions.md` `C94` — "A rest between two staves belongs
to the staff whose voice would otherwise be missing" — filed under *Rests &
bar filling* (73 MEASURED HERE, 121 registry entries total). `python3 -c
"from tools.omr import conventions as CV; assert not CV.load().problems()"`
passes. (Not re-edited this round — the convention's own text already
states the rule in voice terms and needs no correction.)

### 21f. What this item leaves open, named not built

- **`Q.METER` ABSTAINS on Brahms 1/i Breitkopf p1's `system/1/0`**
  (`meter_return_not_read` — confirmed identically on a `--pages 0-1`
  re-gather and on the committed whole-movement record, so the plate's
  6/8 is never a DECIDED value this pipeline can read here; a single-page
  gather's `9/4` was a context-starved artefact, not the real blocker) —
  a 2.12h/2.12i/2.12l/2.29 follow-up, not this item's scope. This item's
  rule will resolve Sean's exact case automatically once that meter reads
  correctly, with no further change needed here (demonstrated by §21b's
  tests and the §21c hand check).
- **The upper staff's own separate ~1-beat gap** in the same bar (§21c),
  likely a GATHER-side detection miss, undiagnosed — no longer a blocker
  to THIS item's own resolution (second correction), but still real and
  unexplained.
- `reads_beyond_cause` is not declared for this rule, so a second EVALUATE
  pass bounded to an INFER-produced verdict (`evaluate.run_over`) will not
  re-fire it even where a later-filled meter would newly unlock the
  equality. No test currently depends on that interaction; named here so
  a future INFER rule touching `Q.METER` does not assume this rule is
  reachable from it.

### 21g. Files

- `tools/omr/staged/evaluate.py`: `Consequence.REINSTATE_REST_BETWEEN_STAVES`,
  `DOWNHILL` (adds `Q.REST_IS_NOT_A_REST`).
- `tools/omr/staged/consequences.py`: `_bar_total_excluding`,
  `_contest_group`, `_group_length`, `_voice_count`,
  `reinstate_rest_between_staves`, `REST_BAR_SUM_EPS`.
- `tools/omr/tests/test_staged_rest_between_staves_2_45.py`: the 15 tests.
- `docs/engraving-conventions.md`: `C94` + bookkeeping.
- `benchmarks/omr-bar-sum-holdout-2026-09/probe/crop_between_staves_2_45.py`,
  `out/print/2.45/brahms-p1-bar5-between-staves.png`: the print check.
- `out/2.45/*.json`, `*.log`: the A/B records (arm/base × Brahms p1,
  `--through evaluate`, `--weights auto --route-weights`) plus scratch
  analysis scripts, not committed — `.gitignore`'s `out/2.45/` rule.


## 21. DIAGNOSIS — the +1.0-quarter bucket of Brahms's bar-sum hold-out (2026-09-30)

PATH: STAGED, diagnosis only. No code under `tools/` changed. Worked from
the whole-movement acceptance record `brahms1-breitkopf-mvt1-whole-
20260930b.record.json` (`benchmarks/acceptance/current.json`) plus a SMALL
re-gather of pages 0-1 (`tools.omr.acceptance_quick --doc
brahms1-breitkopf`, `--weights auto`, ~4 min) to get a live record to
`trace`. Brief: of 4,283 bars `bars_held_out_sum` holds out, the (voice
total − 3.0) distribution's single biggest bucket is **+1.0 quarter,
1,051 bars (24.5%)** — one quarter too many, uniformly. Per the manager's
2026-09-30 redirect, this names the ADJUDICATE-stage decision, not an
EXPORT fix.

### §21a. The dominant cause: `Q.METER` abstains, so `size_measure_rest` never fires (≈90% of the sample)

Sampling the +1.0 bucket restricted to single-event bars (957 of 1,051 —
the great majority), 66 of 73 checked have `Q.METER` **ABSTAINED** at their
system (`adjudicate_meter`, reasons `meter_return_not_read` or
`meter_change_digits_misread`), against a file that still carries 6/8 into
them (`meter_carried_in_file: True`, EXPORT's own separate carry-forward —
`bars_judged_by_a_carried_meter` is 4,225 of 4,283 held bars, i.e. nearly
none of this population sits on a system whose OWN `Q.METER` decided).
Traced four of these bars end to end (`glyph/1/0/1/4/2`,
`glyph/1/1/0/1/3`, `glyph/1/1/1/1/3`, `glyph/1/1/0/7/0`): each holds
exactly ONE standing duration in its bar, `adjudicate_duration` DECIDED it
`rest_class` → `restWhole`, `dots: 0`, `beats: 4.0` — the exact shape
`evaluate.consequences.size_measure_rest` exists to catch (a lone
undotted `restWhole`, meter DECIDED ⇒ rewrite to the bar's length). But
`evaluate._pass`'s `_cause_for` finds `Q.METER` ABSTAINED at the system and
skips the rule (`cause_abstained`) for every cell in it — `size_measure_
rest` never runs, so the glyph's raw "whole rest = 4 beats" reading
survives into export uncorrected. EXPORT judges the bar against 6/8
anyway (its own carried-forward `judged` value, computed independently of
`Q.METER`'s outcome), so the bar reads as 4.0 against a want of 3.0: **+1.0,
exactly the bucket**. This CONFIRMS finding §17's `W` bucket (2026-09-29,
706 bars, "a lone whole rest not sized", 681 on an abstaining system) still
holds on the 2026-09-30b re-gather and is by far its largest single
contributor to the +1.0 shape specifically.

Digging one level further, on `system/1/1` the abstention chains back to
`system/0/0`: that system's OWN meter reading recorded a `declined_changes`
entry at cell 3 (`meter_change_digits_misread`, 8 staves saw a digit
neither could read) — a printed change partway through system 0 that
nothing could read. `_carry_meter` (rhythm.py) treats ANY source with an
unread digit as untrustworthy for every later system, even a system whose
OWN one assessable bar agrees with the carry 1-for-1 (`bars_agree: 1,
bars_disagree: 0`, recorded in the abstained verdict's own `detail`) — it
is outvoted by `too_few_assessable_bars` combined with the tainted-source
penalty, not by disagreement. CLAUDE.md §10 / ROADMAP 2.22b already state
the opposite intent — *"too few assessable bars is not a vote against the
carry -- it is no vote"* — so this reads as the carry's own floor/taint
logic being MORE conservative here than that decided convention, not as a
new convention question. Named but not built (rule 9): a fix belongs to
whoever owns `_carry_meter`'s `digit_misread`/`too_few_assessable_bars`
interaction, and is a CONNECTION (reading facts already on the record:
`bars_agree`/`bars_disagree` from the system's own bars) rather than a
guess. **Print-verified 4 of 4** crops (`out/print/brahms-plus1/
A_rest_meter_return_not_read_m13_P2.png`, `B_rest_digits_misread_m17_P1.png`,
`C_rest_digits_misread_m17_P2.png`, `F_rest_digits_misread_m23_P1.png`, all
600 dpi, staff lines native to the print, the subject boxed red): every one
is a genuine centred whole-rest hanging alone in its bar, exactly the
convention CLAUDE.md §10 describes.

### §21b. A second, minor cause: a meter digit's ink boxed TWICE, once as a notehead (≈10% of the sample)

The remaining 7 of 73 sampled bars sit on `system/0/0`, whose `Q.METER` IS
decided (`voted`, 6/8) — a different mechanism. Traced `glyph/0/0/3/7/3`:
`adjudicate_duration` DECIDED it `head_and_marks` → `noteheadWholeInSpace`,
`beats: 4.0`, at detector confidence **0.267** (`stems_attached: 0,
dots_attached: 0` — an open head with nothing else read, the fallback
duration for that shape). Its box is `[5425.09, 2836.96, 5471.85, 2867.92]`
page-px. The SAME cell also carries `glyph/0/0/3/7/2`, box
`[5425.09, 2836.32, 5471.53, 2868.24]` — **the identical ink**, this time
correctly read as `timeSig8` at confidence 0.663 — and, above it,
`glyph/0/0/3/7/{0,1}` read `timeSig8`/`timeSig9`, together spelling the
`9/8` CAUTIONARY signature `system/0/0`'s own meter verdict already
records at this cell (`cautionary: {from_cell: 7, numerator: 9,
denominator: 8, ...}`). So this is a DUPLICATE box the detector drew twice
on one glyph's ink, one copy correctly classed `timeSig8` and the other
misclassed `noteheadWholeInSpace` — and the existing duplicate-box
refusals (`not_a_notehead:stacked_head_duplicate`,
`not_a_rest:rest_is_a_duplicate_box`, both seen elsewhere in this same
record) evidently compare only WITHIN a family, never against a `timeSig*`
box at the same location, so this cross-family duplicate is never refused.
It is a distinct pattern from ROADMAP 2.12l's fix (§16): 2.12l catches a
digit PAIR read as two noteheads near a cell's LEFT edge (an ordinary
change, just past a barline); this is a CAUTIONARY signature sitting near
a cell's RIGHT edge (just before the barline it warns ahead of), and only
ONE of the pair's two digits (`8`, not `9`) got the spurious second box.
GATHER-stage (the detector drew the extra box) meeting ADJUDICATE (nothing
refuses it as a duplicate of a same-position `timeSig*` verdict) — a
CONNECTION (the duplicate-box family already exists; it needs to look
across families at the SAME box, not a new mechanism). **Print-verified 1
of 1**: `out/print/brahms-plus1/E_wholenote_decided_meter_m8_P4.png` shows
the boxed "glyph" sitting exactly on the `9/8` cautionary signature at the
double barline, not a notehead of any kind.

### §21c. Sean's question

None needed to NAME the cause — both are connections, not conventions.
One open question if EITHER is picked up as the next roadmap item: for
§21a, does a system with exactly one assessable bar that agrees 1-for-1
with the carry (`bars_agree=1, bars_disagree=0`) count as sufficient
support under ROADMAP 2.22b's *"weighed by the bars, not gated"*, or is
the `too_few_assessable_bars` floor deliberately stricter than that for
some reason not written down? Crops A/B/C/F (`out/print/brahms-plus1/`):
red box = the print's whole-rest glyph; caption gives PRINT (what the bar
should sum to) vs OURS (what we currently read and why).

### §21d. Not verified / out of scope here

The remaining ~16% of the sampled +1.0 bucket (multi-event bars, 94 of
1,051 total) was not traced — CLAUDE.md's own `WX`/`WE` letters (§17b:
"a whole rest plus one stray box") suggest at least some of it is a THIRD
combination of the two causes above rather than a new one, but this was
not measured. No EXPORT or held-bar-accounting change is proposed
anywhere in this section, per brief.


---

## 2.79 — a whole-bar rest takes the meter in force at ITS bar, and a lone rest of any other length is never written (2026-10-10)

Branch `lane-2.79-rest-meter` off `6762622c`. Trigger: overnight `20261010-night`
(main `26fdb4d0`), acceptance control `bars_add_up` on Brahms 1/i Breitkopf
`317803`: **6,950 of 6,979 exact and 29 OVERFULL**, last night 6,669 of 6,669.
Every figure below is a proxy or a control, never an objective (CLAUDE.md §6a).
"Print" statements are by reading the crops in `out/print/2.79-review/` and are
**not Sean's**.

### 2.79a. The two meters, and which was wrong

There is ONE `Q.METER` verdict per SYSTEM on the staged path and no per-staff
meter, so the brief's hypothesis -- *a per-staff meter that did not take the
bar-9 return* -- is contradicted by the tree. `system/1/0` is decided
(`voted`) with `segments = [(0, 9/8), (1, 6/8, corroborated)]` and a top-level
`numerator/denominator` of **9/8** -- by `rhythm._with_segments`'s own
construction, the OPENING segment. The return was taken, on every staff (it is
a system fact), and `record.meter_at` answers 6/8 for cells 1..6.

| reader | what it reads | bars 10-14 (cells 2-6) |
|---|---|---|
| EXPORT's `<time>` (`export._part_xml`) | `meter_at(run.meter, i)` | **6/8** |
| EVALUATE's `size_measure_rest` | `meter.value["numerator"]` -- the top level | **9/8** (4.5 beats) |

`meter_at`'s docstring says exactly this to every consumer: the top level
*"describe[s] the FIRST segment ... deliberately NOT the thing consumers should
read -- a bar past a change would get the wrong answer -- which is why every
consumer goes through here and a test asserts it"*. Nothing tested it in
`consequences.py`. Three
EVALUATE rules read the top level (`size_measure_rest`, `reconcile_duration`,
`reinstate_rest_between_staves`) -- the only three; nothing else on the staged
path does (grep, whole tree).

Why 29 and why only some staves: `size_measure_rest` fires only where a whole
rest was actually READ. The parts whose rests in bars 10-14 are `R48` (Flute,
Bassoon, Violins, Viola, Cello) have no `size_measure_rest` verdict there --
their bars were read as nothing and took the eventless-bar branch, which sizes
by `judged` (the written meter) and was right. The 29 overfull bars are exactly
the 29 `size_measure_rest` verdicts on cells whose `meter_at` is not the
opening (staves 1, 2, 4-8, 13; record scan below).

The padded branch (`empty_bars_padded`, brief's candidate 2) is NOT involved.

### 2.79b. The hole

`export._bar_holds_out` treated a lone measure rest as the bar "whatever the
meter" and never compared its `<duration>` with anything. The CONVENTION is
right (CLAUDE.md §10: a whole rest means the BAR); the exemption was wider
than it. A measure rest stands for the bar, so its length IS the written
meter's, and "does it fill the bar" is answered by that equality. Three
fixtures pinned the hole -- `test_staged_bar_sum_holdout.py` (a 4.0 measure rest
in a 2/4 bar, asserted NOT held out), `test_staged_duplicate_rest.py` and
`test_staged_unread_bar_marks.py` (the same 4.0-in-2/4 shape inside `_bar()`) --
and are corrected to the meter's 2.0, with the reason in each. `size_measure_rest`
never leaves that shape (it sets `measure_rest` and the bar's length together).

### 2.79c. The fix, and its stage (§4a)

* **EVALUATE** (commit `373f4a2b`): `consequences._bar_beats_at(meter, subject)`
  reads `record.meter_at(meter.value, subject.cell)`; `size_measure_rest` uses
  it. The answer FOLLOWS (a whole rest is the bar; the bar's meter is decided),
  so it is EVALUATE's. A bar no segment covers gets NO meter and no assertion
  (rule 8) -- the old reading sized it by the top level, a meter nobody read.
* **EXPORT** (same commit): `_bar_holds_out`'s lone-measure-rest branch compares
  the rest's `_event_units` with the written meter's; a disagreement is held out
  and counted exactly as any bar that does not add up, with the voice entry
  `measure_rest_length_disagrees: true` in the held-bar detail. Shared by the
  MusicXML and LilyPond writers (`lilypond.py` calls the same function). **Held
  out, not sized**: a second sizer in the writer would be a second opinion about
  the bar, and a disagreement between EVALUATE's length and the file's meter is
  "cannot tell which" (rule 8). It is quiet on a correct run (0 flagged on every
  re-gather below; the whole-record re-export in 2.79f is the deliberate
  exception, run with EVALUATE's stale verdicts).
* **EVALUATE, separate commit** (`d04fd058`): `reconcile_duration` and
  `reinstate_rest_between_staves` read the same field the same wrong way and now
  use the same helper. Separate because it changes MORE than the rest sizing
  (2.79e) -- the manager can take `373f4a2b` alone (it is green by itself).

### 2.79d. Tests -- RED first, no source-text assertions

`test_staged_rest_meter_2_79.py` (21 tests) and
`test_staged_rest_meter_siblings_2_79.py` (2). Run against the UNREPAIRED tree
before any edit, as one file of 23 (split afterwards): **11 failed, 12 passed**
(the failures read
`4.5 != 3.0`, `unexpectedly None`, and the seam test `(4, 0) != (0, 0)`: 4
overfull, 0 short), then the EXPORT tests failed alone with the EVALUATE fix in
place (5 failed) -- each half is RED for its own reason. Positive controls: a
rest at cell 0 of the same system is still 4.5 (9/8); an unchanged meter and a
verdict with no `segments` key still size alike; a lone rest of the meter's
length is still written as the bar; the same 4.5-beat rest under a written 9/8
is NOT held; no written meter means no verdict; a rest not flagged
`measure_rest` is summed as before; the held bar is quiet when EVALUATE is
right. **The seam test** builds a real `Log` with the segmented meter, runs
`evaluate.run`, serialises it and writes the file: the two halves' own tests
passed together while the seam was broken, which is how this shipped.

### 2.79e. Measured -- small re-gather through export (pdf p0-1), three trees

`acceptance_quick --doc brahms1-breitkopf --full`, ~10 min each. Base =
`6762622c` (reproduces the overnight fault: same 29 bars, same `R18`=9/8 at
divisions 4).

| Brahms p0-1 | base | `373f4a2b` | + `d04fd058` |
|---|---|---|---|
| `bars_add_up` exact / short / **overfull** | 279 / 0 / **29** of 308 | 308 / 0 / **0** | 308 / 0 / **0** |
| bars held out (2.8) | 106 | 106 | 102 |
| empty bars padded | 7 | 7 | 7 |
| notes / rests reaching the file | 434 / 60 | 434 / 60 | 444 / 72 |
| `measure_rests_read` | 72 | 72 | 72 |
| `notes_not_written_total` | 1,296 | 1,296 | 1,274 |
| MusicXML bars changed vs base | -- | **29, only those** | 33 |
| held bars flagged `measure_rest_length_disagrees` | -- | 0 | 0 |

Commit 1 changes 29 of 308 bars (`R18[M]` -> `R12[M]`) and 29 verdicts
(`size_measure_rest` 4.5 -> 3.0); no other EVALUATE verdict moves. Litolff
p0-3, base vs both commits: `bars_add_up` 984 / 984, **0 bars changed**.

**Every other changed bar (commit 2 only), 4 bars -- all held out before, all
written after, each by `reconcile_duration` now landing on 3.0:**

| bar | before | after | print |
|---|---|---|---|
| Cello 10 | held out (`R12[M]`) | `n2 R2 R2 R2 n2 n2` | right |
| Cello 13 | held out | same | right |
| Cello 14 | held out | same | right |
| **Contrabass 13** | held out | `n4 R2 R4 R2` | **WRONG** |

Contrabass 13 prints an eighth note, two eighth rests, a quarter rest and an
eighth rest. The detector missed one eighth rest; the bar is then short by an
eighth and exactly ONE re-reading of one note lands it, so `reconcile_duration`
lengthens the eighth to a quarter. That is the rule's own known hazard (its
bound says "unique"; it does not say "and not a missing rest"), now reachable
here because it lands on the right length. The file is now a bar that adds up
to the wrong music, and the bar-sum control cannot say so. **That is what to
decide about commit 2.** It also removes 3 landings that were wrong-by-meter
(Oboe 11, Clarinet 14, staff 8 bar 9: landed on 4.5, all in bars EXPORT held
out anyway), and `reinstate_rest_between_staves` fires 3 times at
`glyph/1/0/3/5/{0,1,2}` -- Sean's own 2.45 anchor, 0 before (DECISIONS
2026-09-30, "they belong to the lower staff"). The Bassoon bar 13 it belongs to
stays held out: with the three eighth rests back the bar is 5.5 quarters as one
voice against 3.0 (no voice split there).

### 2.79f. Measured -- the whole movement, from the saved records

* **Footprint.** Verdict scan of the whole `20261010-night` records
  (`record_io.load_record`, once): **1 of 53 Brahms systems** carries a segment
  that differs from its opening -- `system/1/0` -- and **0 of 31 Litolff**. On
  Brahms the rules fire on those cells 29 times (`size_measure_rest`), 3
  (`reconcile_duration`), 1 (`reconcile_chord_duration`, which does not read the
  value). So neither commit can move any Litolff verdict, and on Brahms only
  system 1/0, which the small re-gather above covers completely. The
  whole-movement figure for the EVALUATE fix is therefore expected, NOT
  measured: it needs a re-gather.
* **The EXPORT guard on the real record.** `python3 -m tools.omr.staged.export`
  on `brahms1-breitkopf-mvt1-whole-20261010-night.record.json` (its EVALUATE
  verdicts still hold the 4.5-beat rests -- the exact fault state) with the
  guard: `bars_add_up` **6,950 + 29 overfull of 6,979 -> 6,979 of 6,979, 0
  overfull, 0 short**; bars held out 2,755 -> 2,784 (+29), `measure_rests_read`
  895 -> 866, notes reaching the file **7,189 unchanged**; `balanced`, and
  `status_census` `unaccounted` empty; 29 held bars flagged
  `measure_rest_length_disagrees`, **exactly the 29, and no other bar of 6,979
  changed** (per-measure XML diff against the overnight file). That is the
  guard working as the backstop on its own, with EVALUATE un-fixed.
* **Litolff**, same re-export of `beethoven5-litolff-mvt1-whole-20261010-night`:
  `bars_add_up` **6,060 of 6,060**; 0 of 6,060 measures changed; held 1,064,
  padded 708, notes 5,589, `measure_rests_read` 1,089 -- all as overnight.

### 2.79g. Print crops (for Sean's later look)

`out/print/2.79-review/` -- 7 tiles of Brahms pdf page 1, system 0, cut at the
gather's own 600 dpi from `render_page`'s frame, a red corner bracket on the
bar (following the staff, not the 4-space-padded cell, which on a conductor's
page frames three staves) and nothing of ours drawn. `manifest.json` holds our
reading of the bracketed bar under each of the three trees. Frame control: the
five staff lines the record filed must carry >= 2x the ink of the rows between
them (46-87x on the rest bars, 5.6-8x on the bars with notes), and the same
test shifted half a space (the NEGATIVE control) reads 0.01-0.17 and must fail
-- the script asserts both. Tiles 1-3 are whole-bar-rest bars the fix resized
(Contrabassoon 10, Oboe 12, Contrabass 14); 4-7 are the four commit-2 bars. The
question for Sean: *in the bracketed bar, is there one whole rest and nothing
else, and is the bar six eighths (the 6/8 printed at bar 9)?* -- and for 4-7,
*is what we now write what is printed?*

### 2.79h. Open, named, not built

* `reconcile_duration` cannot tell a lengthened note from a missed rest
  (Contrabass 13). A repair needs a witness it does not have; not attempted.
* The whole-movement EVALUATE effect (29 rests + commit 2's 4 bars + 3 reinstated
  rests, expected from the footprint scan) needs a re-gather to be measured.
* `lilypond.py`'s lone-measure-rest branch builds its bar from `meter`, not
  `judged`, so where a bar has no meter of its own but the part carries one it
  renders a 4.0 rest -- not touched, and not seen on either small re-gather
  (LilyPond's own bar-check failures: Brahms 0 / 0 / 0 across the three trees,
  Litolff 2 / 2 before and after, unchanged).

### 2.79i. Gate

Fast tier on the final head (`pytest tools/omr/tests -m "not slow"`): **6,973
passed, 11 skipped, 2 xfailed, 825 deselected**, exit 0 (a first run with `-x`
stopped at `test_staged_duplicate_rest` -- one of the three fixtures above -- and
is not the figure). `python3 -m tools.omr.staged.check`: **N = 192**, base 192,
no new open finding. Scratch (`l279-*`) was kept outside the tree.

### 2.79j. Files

`tools/omr/staged/consequences.py` (`_bar_beats_at` and its three callers),
`tools/omr/staged/export.py` (`_bar_holds_out`), `tools/omr/tests/
test_staged_rest_meter_2_79.py`, `test_staged_rest_meter_siblings_2_79.py`, the
three corrected fixtures named in 2.79b, `out/print/2.79-review/` (7 tiles +
`manifest.json`), and under `probe/`: `2.79_crops.py` (the tiles and their frame
control), `2.79_segment_footprint.py` (which verdicts sit on a cell whose
`meter_at` differs from the opening, from a saved record), `2.79_diff_musicxml.py`
(per-part, per-bar diff of two exports).

---

## 2.80 — a bar short by a MISSED REST is not a note one beam short (2026-10-11)

Branch `lane-2.80-missed-rest` off `origin/main` 2e286351, with `d04fd058`
(2.79's held sibling) cherry-picked as the base. STAGED. Not merged.

**CONVENTION CONFIRMED FOR CONTRABASS BAR 13, ASSUMED FOR THE REST:** Sean,
blind on tile 1 (the blue mark): *"It is an 8th note rest"* (DECISIONS
2026-10-11) -- the missed mark is an eighth rest, not a note one beam short.
The general convention -- a rest the detector never boxed is still printed ink
in the bar, so a bar's shortfall is evidence about a NOTE only where the bar
holds no ink that no standing glyph explains -- stays ASSUMED until the other
tiles are read. **WHAT WOULD FALSIFY IT:** a tile where
Sean sees the re-read note is right while the witness called ink unexplained
(over-refusal -- tiles 8-10 are exactly where to look), or a missed rest whose
ink a standing glyph box covers anyway (under-refusal). **NOT CONFIRMED** for
the general case -- tile 1 is the only tile judged.

### 2.80a. The case, on the record

Brahms pdf p1 system 0, Contrabass (staff 13) bar 13 (cell 5). Print (Sean,
2.79 tile 5): eighth note, eighth rest, eighth rest, quarter rest, eighth rest.
The detector boxed the first eighth rest, the quarter rest and the last eighth
rest, and boxed the SECOND eighth rest as `noteheadBlackInSpace` (box 4547-4566
x 3784-3802, 0.7 x 0.7 spaces); ADJUDICATE refused it `too_narrow`. The bar is
short by an eighth. `reconcile_duration`'s bound ("one note, exact landing,
unique") says nothing about a missing rest, so it lengthened the eighth note to a
quarter: the bar sums, the music is wrong, `bars_add_up` cannot see it.

### 2.80b. The mechanism

* GATHER `gather_cell_ink_pieces` (`Q.CELL_INK_PIECES`, reader `CV_INK_PIECES`,
  beside `gather_ink`, same erased raster, reads no row and no detection): one
  row per cell, `detail.pieces` = `[x0,y0,x1,y1,area_sp2]` in page px for each
  connected piece with area >= 0.10 sp^2, <= 8 sp wide, centre within 1.5 spaces
  of the staff. `Q.INK`'s default is a per-cell summary with no geometry and its
  per-piece form (`--ink-rows`) costs ~115 MB/page, so this is the middle form.
  A cell with no raster/staff unit/page frame gets an abstention, never an
  empty row. Staff-line erasure splits an eighth rest into a blob (0.65 x 1.2
  sp) and a tail (0.65 x 1.75 sp); that is why the reader names nothing.
* EVALUATE `consequences._missed_rest_witness`: a piece is EXPLAINED if >= 50%
  of its box is covered by a standing glyph box (not one a DECIDED
  `not_a_notehead`/`not_a_rest` took out, unless decided a whole rest; boxes
  wider than 8 spaces do not count) or a read direction word, or it is a merged
  piece (box > 3.5 sp^2) containing a standing glyph's centre; stem/barline
  crumbs (<= 0.3 wide, or >= 4.5 tall and <= 0.8 wide) are ignored. Answers
  `clear` / `unexplained` / `unread`.
* `reconcile_duration` asks it only when the unique landing LENGTHENS a note
  (landed beats > the note's current/best reading). Only `clear` lands. A
  shortening needs no witness. `unread` refuses (rule 8: a fallback never turns
  "cannot tell" into "clear").
* Part 2 (`reconcile_duration` / `reinstate_rest_between_staves` read `meter_at`
  their bar): `d04fd058`, cherry-picked unchanged.

### 2.80c. Tests (RED first)

`test_staged_missed_rest_2_80.py`, 8 tests. With `_missed_rest_witness` forced
to "clear" (the unrepaired rule) the 3 `*_RED` fail (ink nobody explains; a box
decided not-a-notehead does not explain its ink -- the Contrabass shape; no ink
reading) and 5 controls pass (explained ink still lands; a stem or crumb left
still lands; a clear bar lands; a box decided a whole rest explains; a
SHORTENING lands with unexplained ink and with no ink row at all). Four older
reconcile tests (all lengthenings) now file a clear ink row.

### 2.80d. Measured -- small re-gathers, base vs arm on ONE tree, ONE record

Gather: `--through adjudicate`, tree = branch + uncommitted witness, Brahms
pages 0-1 and Litolff pages 1-3 (the movement's first page through the count
page). Both arms re-run ADJUDICATE..INFER from the SAME gather rows
(`probe/2.80_ab.py`; the base arm answers "clear" for every bar).

| | Brahms p0-1 | Litolff p1-3 |
|---|---|---|
| `reconcile_duration` landings, base | 4 (2 lengthen, 1 shorten, 1 narrowed) | 24 (11 shorten, 13 narrowed) |
| witness asked (lengthenings) | 2: clear 1, unexplained 1 | 5: clear 5 |
| landings, arm | 3 | 24 |
| landings by the rest instead / abstained | 0 filled; 1 refused | 0 |
| MusicXML bars changed | **1: Contrabass 13 (P14 bar 13)** | **0** |
| bars held out (2.8) | 97 -> 98 | unchanged |

Contrabass 13: the arm leaves the eighth note an eighth; the bar is held out
(short by an eighth) instead of written as a quarter. Cello 13 (a flagged
eighth read as a sixteenth, three eighth rests and a beamed pair -- right by
eye) stays landed: its 'pizz.' word and its merged beamed group are explained.
Reach: of ALL cells with an ink row the witness answers clear 210/314 (67%) on
Brahms and 631/864 (73%) on Litolff, so it is not a blanket refusal (`probe/
2.80_witness_rates.py`). First builds refused Cello 13 too (7 unexplained
pieces: the word and the merged group) and two Litolff bars (a barline remnant
8 spaces tall); the direction-word, merged-piece and barline rules above are
the fixes, each found by reading the cell's own pieces against its boxes.

### 2.80e. Limits, named

* It REFUSES; it does not FILL. Where ink is found the bar is held out (2.8),
  not completed with the rest. Filling needs a rest subject for the ink (the
  refused `too_narrow` box at the second eighth rest is the obvious candidate);
  that is an ADJUDICATE question and is not built here.
* Over-refusal: tiles 8-10 are cells the witness calls unexplained that were
  never asked about -- a clef/key at a system's head, the lower fragment of a
  kept quarter rest, a slur fragment. Only lengthenings are gated, so the cost
  is a held bar, but the number of right lengthenings it loses is measured on
  two pages (0 of 6) and needs Sean's tiles and the overnight run to widen.
* The witness subtracts BOXES; a missed rest that overlaps a standing glyph's
  box is explained and slips through (under-refusal, unmeasured).
* GATHER changed, so only a full re-gather prices it on the whole movement.

### 2.80f. Gate

`staged.check` 192 = base 192. Fast tier: see the lane report. Print tiles:
`out/print/2.80-review/` (10; 1 refused, 6 landed, 3 unexplained-ink; blue
corners = the subject, red = the bar, nothing of ours on the image;
`manifest.json` holds our reading). Files: `consequences.py`, `gather.py`,
`record.py`, `capture.py`, `test_staged_missed_rest_2_80.py` (+ two edited
tests), `probe/2.80_ab.py`, `2.80_witness_rates.py`, `2.80_tiles.py`.

---

## 2.80b — the missed rest is READ, on its own ink (2026-10-11)

Same branch `lane-2.80-missed-rest`. STAGED. Not merged. Sean, blind on tile 1
of `out/print/2.80-review/`: *"It is an 8th note rest"* (DECISIONS 2026-10-11).
The coordinator's ruling on how to build it: ADJUDICATE on the mark's OWN
evidence; **a bar's shortfall is not a witness** (rule 8; two witnesses off one
raster fall silent together -- the bar sum is made of the same readings the mark
was refused out of); if the shape cannot tell, abstain and the bar stays held
out. Any ranking by the shortfall would live in INFER, labelled, or nowhere --
there is none: the shape admits one candidate (the eighth rest) here, and the
decision declares no meter/event/duration/voice quantity (a test asserts it
off the registry).

### 2.80b-a. The pipeline

* GATHER `gather_narrow_box_shape` -> `Q.NARROW_BOX_SHAPE`: one row per
  notehead-classed box narrower than `TOO_NARROW_MIN_SPACES` (1.0, imported):
  the ink pieces the box overlaps, plus pieces stacked against them (<= 0.25
  space gap; staff-line erasure splits an eighth rest into a blob and a tail),
  as width/height in spaces, the staff step of the centre, fill, whether it
  touches the cell's edge, and the OTHER detections overlapping it. Residue is
  excluded as a seed (a piece wider than 8 or taller than 3.5 spaces: the first
  build let a 22 x 8 space remnant under bar 13 swallow the whole bar and every
  box then read "claimed by another class"). No bar is read.
* ADJUDICATE `adjudicate_narrow_box_is_an_eighth_rest` (`Q.NOTEHEAD_IS_AN_EIGHTH_REST`,
  `adjudicators/narrow_rest.py`, in `ORDER` after `Q.NOTEHEAD_IS_A_WHOLE_REST`):
  speaks only on a box ALREADY refused `too_narrow`. `True`: width 0.9-1.6 x
  height 1.6-2.6 spaces, <= 3 pieces, centre within 1 step of the middle line
  (step 4), not touching the cell edge, and no standing glyph over the ink
  (windows measured off the 107 Brahms + 17 Litolff kept `rest8th` boxes:
  1.2-1.4 x 1.9-2.4, step median 3.9). `False`: decisively not a rest's size, or
  a STANDING rest/notehead box already reads the ink (a duplicate box).
  Abstain: another class (flag, beam) claims the ink, the size is in between,
  off the middle line, or no ink to measure.
* EVALUATE `size_reinstated_rest` (cause the verdict, `DOWNHILL` above `Q.METER`,
  so it runs before every bar-summing rule): writes `Q.DURATION` {0.5, is_rest}
  superseding the head reading. The length follows from the class, not the bar.
  `_left_the_bar` and the 2.80 witness treat a reinstated box as in the bar and
  as explaining its ink.
* EXPORT writes a reinstated box as a rest (`class` `rest8th`); the refusal
  `not_a_notehead` still stands -- it is not a head.

### 2.80b-b. Reach (small re-gathers, `--through gather`, base vs arm from ONE record)

| | Brahms p0-1 | Litolff p1-3 |
|---|---|---|
| `too_narrow` refusals | 243 | 20 |
| no ink the reader can measure (`no_ink_under_box`) | 224 | 15 |
| decided False: duplicate of a standing glyph | 5 | 1 |
| decided False: not rest-shaped | 5 | 1 |
| abstained: claimed by another class | 7 | 3 |
| **decided True: eighth rest** | **2** | **0** |
| MusicXML bars changed vs the decision off | **2** (P14 bars 13, 19) | 0 |
| bars held out (2.8) | 98 -> 96 | 122 -> 122 |

Almost all narrow boxes are crumbs the erased raster holds no rest-sized piece
for, or sit in a merged component: the reader refuses to guess (224 of 243).

**Contrabass bar 13 now adds up with no note changed:** `n2 R2 R2 R4 R2`
(divisions 4: eighth, eighth rest, the reinstated eighth rest, quarter rest,
eighth rest = 3.0 quarters, the 6/8 in force). Before (the 2.80 witness alone)
the bar was held out; before 2.80, a quarter. The second reinstated rest is
Contrabass bar 19 (`n2 n2 R2 R4 R2`, 3.0); both are print-checked below.

### 2.80b-c. Tests

`test_staged_narrow_rest_2_80b.py`, 20 tests, written RED (the quantity did not
exist on the tree without it): rest-shaped refused box -> True; the same ink
under a box refused for another reason -> abstain (positive control); a crumb,
a head with its stem and a quarter rest's height stay refused (False); a
barline-remnant at the cell edge, an off-middle position and an in-between size
abstain, each with its twin that decides True; a standing rest/notehead over the
same ink -> False, a REFUSED rest over it is no claim -> True, another class ->
abstain; EVALUATE: the rest takes 0.5, is idempotent, a False/abstained verdict
writes nothing, **with the rest the bar adds up and no note changes**, and
without it the old repair is what happens (the control that makes the previous
test mean something). `test_staged_evaluate_order` gains `size_reinstated_rest`.

### 2.80b-d. Limits

* Eighth rests only: the sixteenth and quarter shapes are not read here (a
  quarter's height is decisively "not an eighth"). Narrow boxes on a MERGED
  component abstain (`no_ink_under_box`): 224 of 243 on Brahms.
* The windows are measured on two pages; the 2 reinstated rests are the whole
  population there. `out/print/2.80-review-2/` holds the 2 plus controls (the
  duplicates, three real narrow non-rests, abstentions) for Sean.
* GATHER changed again: only a full re-gather prices it on the whole movement.
* The bar-13 reinstatement does not make the bar-sum control a witness: the
  bar adding up is the CONSEQUENCE checked, never the reason.

### 2.80b-e. Sean's judgement of the tiles (2026-10-11)

Blind, `out/print/2.80-review-2/` (`answers.json` holds his words and our
reading side by side; tile 1 is the earlier *"It is an 8th note rest"*). Scored
against `manifest.json`: **0 wrong of 10.**

| tiles | our reading | Sean | |
|---|---|---|---|
| 1, 2 | decided True, eighth rest | 8th rest, 8 rest | right (2 of 2 reinstated) |
| 3 | duplicate of a standing notehead, refused | dotted quarter, slur to two 16th notes | right |
| 4, 5 | duplicate over an already-read rest8th, refused | 8 rest, 8 rest | right: the rest still stands, the second box stays refused |
| 6, 7, 8 | real narrow non-rest, refused | stray ink, augmentation dot, text "arco" | right (3 of 3) |
| 9, 10 | abstained (another class claims the ink) | dot-2 with a tremolo slash, trill with its squiggle | right (2 of 2) |

So the reinstated population (2) is 2 of 2 right, every control that should
refuse refused, and nothing was decided True on a non-rest. n is small; the
shape windows remain measured on two pages.

## 2.97 -- narrowed notes whose own candidates land the bar are settled by the bar (2026-10-12)

PATH: STAGED, ADJUDICATE->INFER re-decided from the committed night records
(`library/_shared-records/*-whole-20261011-night.record.json`, `record_io.load_record`,
`probe/run_2_97.py`), base vs arm on one tree shape (copies of `tools/`, differing only
in the three staged files + env `OMR_NARROWED_BAR=1`). Branch `lane-2.97-narrowed-bars`
off `origin/main` `3fd59e2a`. NOT merged; Sean judges the tiles first.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a bar adds up to the PRINTED
meter, so a narrowed head's candidate that lands it is the likely value. Falsified by a bar
with a missed note/rest, a second voice or a wrong decided neighbour (each moves the sum
and the rule cannot see it). NOT CONFIRMED: Sean has not judged the 12 tiles
(`out/print/2.97-review/`).

### Why the 136 single-head bars were not landed (Litolff's 39 traced, `probe/chain_2_97.py`)
`reconcile_duration` was not blocked; the bars are not the case it was written for.
Each note's verdict chain: in 24 of 39 INFER's 2.81 rule had already settled the OTHER
narrowed heads of the bar, leaving one bare stem whose tip was not seen clean (Sean's 2.81
condition) -- the arithmetic forces it, the condition refuses it; in 10 of 39 EVALUATE's
single pass had re-read a DECIDED neighbour (the one landing at that moment) and left the
narrowed head consistent with the bar but unwritten (`duration_narrowed`); in 4 nothing ran.
`reconcile_duration` does not re-run after INFER. 8 more are refused by 2.80's ink witness
and should stay refused.

### What was built, and the stage
- EVALUATE, `reconcile_duration` (the answer FOLLOWS: same bound, unit = EVENT): a chord whose
  EVERY head is narrowed AND stands on ONE decided `Q.HEAD_STEM` changes together (one stem,
  one value, 2.78); and a landing made on a DECIDED note also settles the bar's narrowed
  events only where the JOINT search (narrowed events over their own candidates x at most one
  decided re-reading) is itself unique. Lengthening still needs 2.80's ink witness.
- INFER, `collapse_narrowed_by_bar`, flag `OMR_NARROWED_BAR` default OFF (best, not forced):
  2.81's solver widened (`any_reason`) to every narrowed head/chord, jointly over several
  columns, only where every landing agrees, on a meter that reaches the PRINTED reading (never
  a bar-chosen one); a bare stem whose tip was not clean needs the bar's ink wholly explained;
  any lengthening past the reader's best candidate needs the same witness. Where the meter
  verdict abstains the rule declines (Brahms ~214 bars stay held; no printed reading to use).

### A/B (re-decide of the night records)
| | before | after |
|---|--:|--:|
| Litolff bars_held_out_sum | 1,085 | 990 |
| Litolff notes in file | 5,894 | 6,022 |
| Litolff narrowed heads not written | 354 | 180 |
| Brahms bars_held_out_sum | 2,553 | 2,459 |
| Brahms notes in file | 8,198 | 8,555 |
| Brahms narrowed heads not written | 3,182 | 2,976 |

Bars settled by part (heads): Litolff single 38 (45) / chord 25 (52) / columns 39 (108);
Brahms single 13 (23) / chord 89 (178) / columns 3 (6). Of the held list: released Litolff 73,
Brahms 96; newly held 0 / 2. A settled value NOT among the head's own candidates: 0 / 0 (control,
can fail: it counts a verdict whose value is absent from its superseded verdict's candidates).
CAVEAT: the first Litolff base, run in the worktree, held 1,044 (notes 5,782); the copy-tree base
holds 1,085. Both arms of the A/B above are copy-trees; the 41-bar difference between tree
shapes is NOT explained (not a code difference).

### Control: Sean's hand truth (Brahms pdf 0, `probe/truth_2_97.py`, pages 0-1 re-decide)
Judged heads 334: base decided right 297 / WRONG 12 / narrowed 25; arm right 306 / WRONG 14 /
narrowed 14. 11 heads moved: 9 narrowed->right, 2 narrowed->WRONG. **Wrong rose by 2 -- the
brief's condition is NOT met.** (a) glyph 0/0/9/3/3: INFER's two-column joint lengthened both
(6/8, truth 0.5 for this head); the ink witness was clear; a missed rest or note is the likely
cause. (b) 0/0/6/2/2: the chord's heads share one stem, our candidates 0.75/1.5 and Sean's
derived truth 1.0 -- the scorer assigns the dot to one head only, so this may be a scoring
artefact; agent-read, to be cropped. An earlier draft without the one-stem condition wrote a
chord of two voices as one value; the condition was added after seeing it, so held-out tiles
are the real test.

### Tiles
`out/print/2.97-review/` 12 tiles (4 single, 4 chord, 4 columns; Litolff and Brahms), blue =
the settled heads, question "values of the bracketed notes?"; ours only in `manifest.json`;
`answers.template.json`.

### Gates
Fast tier 7,458 passed (serial; no xdist); `staged.check` 192 = main. 29 new tests
(`test_staged_narrowed_bar_2_97.py`), RED on the unrepaired tree.

### 2.97b. Settled bars that used another staff's head or a duplicate box (manager's check on the tiles, 2026-10-12)
`probe/clean_2_97.py` on the first arm's settled bars (before the guard): Litolff 32 of 102 settled bars
dirty (a head boxed twice 9 bars [chord 4, columns 5], another staff's kept box on the same ink 2, a head
beyond 1.6 staff spaces from its own lines 23); Brahms 33 of 105 dirty (off-staff 33, another staff's box 1).
No settled head had a DECIDED other owner (those leave the bar), so the faults are heads nobody contested:
a neighbour staff's note inside this cell's pad. Both hand-truth misses were of this kind or near it:
0/0/9/3 (INFER, two columns) used heads that stand on the staff ABOVE (crop `out/print/2.97-misses/tile_02`);
0/0/6/2 (chord) is shown in `tile_01` for Sean (candidates 0.75/1.5, derived truth 1.0, unresolved).
FIX (before anything else): `consequences._bar_heads_are_clean` -- every kept head of the bar is one box
(IoU <= 0.3 with the others), within 1.6 spaces of THIS staff's lines, and not boxed by another staff;
else the new paths (chord unit, settle-alongside, INFER rule) decline. 4 new tests, positive control included.
The same check on the re-run arms finds 0 dirty settled bars on both records.

Re-run with the guard (arm vs the same base): Litolff held 1,085 -> 1,015, notes 5,894 -> 5,892, narrowed not
written 354 -> 277; Brahms held 2,553 -> 2,494, notes 8,198 -> 8,422, narrowed 3,182 -> 3,049. Bars settled
(heads): Litolff single 27 (31) / chord 9 (18) / columns 22 (53); Brahms single 7 (13) / chord 60 (120) / columns 0.
Value outside own candidates 0. Hand truth, pages 0-1: right 297 -> 299, WRONG 12 -> 13 (the 0/0/6/2 chord,
whose candidates do not contain the derived truth). 12 tiles re-rendered (one bracket per settled event; unclean
bars dropped). Fast tier and `check` to be re-run on the final commit.

### 2.97c. Tuplet guard (manager, 2.101: a 3-quarter triplet's sum settles a quarter as an eighth)
`consequences._bar_has_tuplet` (a gathered `Q.TUPLET_MARKER` anywhere in the cell, or a duration carrying a
ratio): the chord unit, settle-alongside and `collapse_narrowed_by_bar` all abstain on such a bar
(`bar_holds_tuplet_evidence`). TODO: swap for 2.102's shared `bar_has_tuplet` when it lands. Of the settled
bars on the guarded arms: Litolff 58, Brahms 67 -- 0 hold tuplet evidence (`probe/tuplet_2_97.py`), so the guard
changes nothing on these two scans; it is for other publishers. 3 tests (positive control included).

### 2.97d. Sean's answers (2026-10-12) and what they removed
Verbatim in `out/print/2.97-review/answers.json`, `out/print/2.97-misses/answers.json`, DECISIONS 2026-10-12.
Scored against the manifests: **singles 1-4: 0/4** (each settled 0.5 by `reconcile_duration`; all quarters);
**chords 5-8: 4/4** (tile 6 dotted quarter = our 1.5); **columns 9-12: 4/4**. Misses: tile 1 (chord, we said 1.5)
**right** -- the hand-truth "miss" 0/0/6/2 was the scorer attaching a dot to one head, not our error; tile 2
(columns) the second head is an eighth, we said a quarter -- the staff above's heads (clean-heads guard).
Why the singles were wrong: all four were `reconcile_duration` verdicts with `settled_alongside` -- a DECIDED
neighbour was re-read by the old single-pass arithmetic (the only landing at that moment) and the bar's narrowed
bare stem was then settled to its best candidate because the joint search was unique. Unique arithmetic is not the
print (a bare stem is a quarter more often than the eighth the sum asked for). REMOVED (`_settle_alongside`,
`_narrowed_units`); the neighbour's re-read stays the old rule's, the narrowed head stays narrowed. Chords and
columns stay.

## 2.98 -- a lone whole rest is the bar, in the bar the file writes (2026-10-12)

PATH: STAGED. Branch `lane-2.98-whole-rest-bar`. CONVENTION (CLAUDE.md §10, Sean 2026-10-12 tiles 4-6, 3/3): a whole rest means the BAR whatever the meter. NOT CONFIRMED on the 12 new tiles (Sean has not judged them).

**The blockers, shown first.** (1) Brahms: 428 held bars = one `restWhole` left at 4.0 unmarked; 403 sit on systems whose `Q.METER` abstained, so `size_measure_rest` (cause: a DECIDED meter) never fires. (2) Litolff, exact blocker (`probe/ab_2_98.py` run, inspected on the record): the bar holds TWO duration verdicts -- the `restWhole` box and a notehead-class box on the same ink (boxes overlap 0.93-1.0) with `notehead_is_not_a_notehead` decided False and `notehead_is_a_whole_rest` decided True. EXPORT refuses that second box (`ink_is_a_whole_rest`) so the file holds one rest, but 2.19's `_left_the_bar` lists only not-a-notehead / not-a-rest / owner removals, so `_standing` kept its 1.0 and the bar was "two things". (The brief said "refused `ink_is_a_whole_rest`"; the verdict is `Q.NOTEHEAD_IS_A_WHOLE_REST`, the refusal is EXPORT's.)

**Stage.** (1) EXPORT: the length needed is the `<time>` in force in the exported part (`in_force`, carried across systems by `_part_xml`), which is not in the record; nothing is added to the record and nothing is decided that the file does not already say. (2) EVALUATE, because it follows from a decided verdict and sits where 2.19 put the same kind of removal. `_left_the_bar` is shared with INFER's duration rules (2.97's fence), so the set-aside is a separate helper `_whole_rest_ink_twin` used only by `size_measure_rest`: non-rest box, DECIDED True, the exporter's refusal flag on, overlapping the sized rest >= 0.8 of the smaller box. A twin elsewhere in the bar, a real head, an abstained verdict, `OMR_WHOLE_REST_INK=0` all keep the bar unsized (tests).

**Base vs arm, one tree** (`out/2.98/*.json`; pre-merge tree 3fd59e2a, Litolff re-decided from its GATHER rows, base reproduces 2.96's 1,044 exactly):

| | held | of bars with events | measure rests in file | notes | `bars add up` |
|---|---|---|---|---|---|
| Litolff base | 1,044 | 4,841 | 1,089 | 5,782 | exact 6,060, short 0, overfull 0 |
| (2) EVALUATE only (twin fires 29) | 1,013 | | 1,120 | 5,782 | same |
| (1) EXPORT only | 1,012 | | 1,121 | 5,782 | same |
| both | 1,012 | | 1,121 | 5,782 | same |
| Brahms base (export-only) | 2,553 | 5,955 | 974 | 8,198 | exact 6,988, short 0, overfull 0 |
| Brahms (1) | 2,125 | | 1,402 | 8,198 | same |

Released by part: Litolff (2) 29, (1) 30 (the 30 W bars; (1) subsumes (2) at the file; the extra one is page 16 sys 0 cell 14, whose second box is on another place in the bar and is dropped by EXPORT for a reason EVALUATE does not model -- a tile for it is in the set); Brahms (1) 428, 403 on a carried meter (`measure_rests_sized_by_a_carried_meter`). 2 more Litolff bars on a doubled staff are written, not in the held list. Notes and ordinary rests reaching the file are unchanged; the released bars were held-out events counted under `bar_does_not_add_up`, now `measure_rests_read`. Overfull stays 0: the rest takes the file's own `<time>` by construction, and `_bar_holds_out`'s lone-measure-rest equality still judges it. No released Brahms bar sits after a printed meter change (those systems declare their meter and EVALUATE sized them in 2.79), so the two change-adjacent tiles are controls, not releases. Engraved control (`acceptance --doc beethoven5-engraved`, base vs arm): identical (0 held, 432/432 add up, F1 0.951, OMR-NED 0.0806); inert there because EVALUATE already marks those rests. Brahms part (2) was not re-decided (5.9 GB record).

**Tiles** `out/print/2.98-review/` (12; phone-sized, rest bracketed blue, bar red, our reading in `manifest.json` only): 1-4 Litolff released, 5-6 Brahms controls right after the 9/8 -> 6/8 change, 7-12 Brahms released (5 on a carried meter). Question: is the bracketed rest a whole-bar rest, and what meter is this bar in? NOT CONFIRMED until Sean answers.

**Limit.** On a carried meter the file's `<time>` may itself be wrong (`carry_outweighed_by_the_bars`); the rest then agrees with a wrong `<time>`. The rest is the bar either way; the meter claim is a separate item.

### 2.98i. Sean's answer (2026-10-12, `out/print/2.98-review/answers.json`)

Verbatim: *"all of them are whole note rests"*. **12 of 12** bracketed rests are whole-bar rests (Litolff released 4/4, Brahms controls 2/2, Brahms released 6/6). No per-tile meter was given, so the meter the FILE wrote is confirmed by the print for none of them yet; see 2.98j.

### 2.98j. Sean on the meter (2026-10-12)

Shown full-system crops of tiles 7-12 and told the file writes 6/8 there: *"yes all 6/8"*. Tiles 7-12 are therefore confirmed whole-bar rests in a bar the print has in 6/8, equal to the `<time>` the file wrote, including the carried-meter ones (the carry was right on those six). Litolff tiles 1-4 (file: 2/4) and controls 5-6 were not asked about meter.

### 2.98k. Re-run on the MERGED tree (origin/main with 2.93-2.95, `out/2.98m/`)

Same harness, one tree, Litolff re-decided (twin off/on) and Brahms export-only. Litolff base moved to 1,085 held of 5,004 bars with events (main's 2.93 identifies the bottom staff, so more bars exist); the DELTAS are unchanged: (1) alone 1,085 -> 1,053 (-32), (2) alone 1,054 (twin fires 29), both 1,053; measure rests 1,139 -> 1,171; notes 5,897 and ordinary rests 797 unchanged. Brahms 2,553 -> 2,125 (-428, measure rests 974 -> 1,402; notes 8,198 and rests 2,602 unchanged). `bars add up` short=0 overfull=0 in every arm on both movements.
## 2.99 -- eighth and quarter rests the detector never boxed are read from the ink (2026-10-12)

PATH: STAGED, GATHER + ADJUDICATE + EVALUATE + EXPORT. Branch `lane-2.99-unboxed-rests`, NOT merged (Sean
judges the tiles first). Sean, 2026-10-12: *"Send out 1-3"* (2.96's third item: 448 held bars hold
eighth/quarter-rest shaped ink no box accounts for; 2.96's write-up is on `lane-2.96-held-funnel`).

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED.** A rest is read on its OWN ink: its size in
staff spaces, the local staff step of its centre, where its ink sits in its box, and the absence of a flat's
full-height left stroke -- and on NOTHING about the bar (rule 8; CLAUDE.md §10, two witnesses off one raster
fall silent together). A rest off the middle of the staff (a second voice) abstains. Falsified by a blind tile
where a decided rest is not a rest (2.96's tile 7 was a flat), or a decided rest in a bar that was already right
and is not printed. Sean has not read the 12 tiles.

### What was built
| stage | function | what |
|---|---|---|
| GATHER | `gather_unboxed_rest_ink` -> `Q.UNBOXED_REST_SHAPE` | clusters of staff-erased pieces (joined across 0.25 space, as 2.80b) of a rest's size (w 0.5-2.4, h 1.2-3.8 spaces, centre on the staff): width, height, LOCAL staff step, `coverage`/`covered_by` (standing detector boxes), tallest ink column in 6 slices (`column_profile`), `mass_y`, nearest notehead on the right, header flags. Glyph ordinal 350000+ (below the human-evidence base 400k, which `test_stage_review_evidence` guards: my first draft used 400k and failed there). Covered clusters are filed too, as controls. Names nothing, no bar. |
| ADJUDICATE | `adjudicate_unboxed_ink_is_a_rest` -> `Q.UNBOXED_INK_IS_A_REST` | `"eighth"` / `"quarter"` / False (already read by a standing box; a stem stroke) / abstain. `wants` is the shape row only; a test asserts no meter/event/duration/voice is declared. |
| EVALUATE | `size_unboxed_rest` | 0.5 / 1.0 quarters from the class; ranked beside `size_reinstated_rest`. |
| EXPORT | loop in `_place_notes` | writes the rest in its own bar; the accounting equality gained a named term (`unboxed_rests_placed`) and stays an equality. |

No new flag (rides `OMR_INK`). 30 tests, RED-first (the quantity does not exist on main), each refusal with its
positive control: a flat beside its head stays not-a-rest and the same size without the stroke is decided; a
dot/crumb and a head-with-stem stay undecided; an arpeggio zigzag abstains beside its chord and is a quarter
rest without one; export writes the rest, completes a short bar, and a rest in an already-right bar overfills it
and says so. `test_staged_evaluate_order` gained the new rule.

### Windows read off ink the detector already named (`probe/controls_2_99.py`, `out/2.99/controls-*.txt`)
The decision run over covered clusters with coverage zeroed, against what the standing box called the ink:

| | Litolff p1-3 | Brahms p0-1 |
|---|--:|--:|
| standing `rest8th` read eighth | 18 of 19 (+1 in header) | 88 of 111 (+4 header; 19 off-middle abstain) |
| standing `restQuarter` read quarter | 89 of 100 | 20 of 27 |
| standing flat/sharp/natural decided a rest | 0 of 8 | 0 of 44 (13 False, 31 abstain) |
| standing notehead/clef/key/meter/flag/slur decided a rest | 2 of 28 | 0 of 54 |

The 5 Litolff "negatives" (3 `accidentalDoubleSharp`, 2 `noteheadBlackOnLine`) sit on exactly eighth-rest ink
(1.3-1.5 x 2.2-2.35 spaces, step 3.9-4.1, upper-heavy): detector mislabels, one shown as a control (tile 6).
Features: an eighth rest is upper-heavy (`mass_y` 0.32-0.48, a flat 0.54-0.61) with no left slice above 0.65
(a flat's two left slices are 0.94-1.0); a quarter rest peaks in the middle slices and is thin on the right (a
sharp's right slices fill again). `max_column_share` alone cannot separate them: it is 1.0 for standing quarter
rests too. Heads stand 0.1-0.6 spaces right of 18 of 19 standing eighths, so a head beside the ink is a claim only
against a quarter-shaped zigzag (an arpeggio).

### Reach and A/B (`probe/2.99_ab.py`; one saved gather record, one tree; OFF = decision abstains)
Small re-gathers on the tree merged with main 3991579c; Brahms = PDF p0-1, Litolff = p1-3.

| | Litolff | Brahms |
|---|--:|--:|
| rest-sized clusters filed / with no box over them | 219 / 44 | 270 / 27 |
| decided eighth / quarter | 13 / 3 | 4 / 0 |
| decided stem stroke (not a rest) / abstained | 7 / 35 | 0 / 28 |
| decided rests' bars **released** | **10** | **1** |
| ... still held / **newly overfull** / bar had no events | 3 / **2** / 1 | 1 / **1** / 0 |
| bars held out, base -> arm | 122 -> 115 | 88 -> 88 |
| MusicXML bars changed | 12 | 2 |
| accounting equality | True | True |

The 2.96 whole-record population (332 eighth + 116 quarter evidenced bars) cannot be re-priced: a GATHER change
is invisible to `readjudicate`. The small pages are the price.

### The false-positive measure: 3 bars newly overfull, explained
A rest found in a bar that ALREADY added up is these 3 bars; none is a rest that is not printed -- each summed
correctly in base only by cancellation with a wrong event already there:
* Litolff p1 s0 staves 7 and 11, bar 0: base = `rest8th` + 3 eighths = 2.0, but that `rest8th` is the key
  signature's third flat, boxed as both `keyFlat` and `rest8th` (identical box); the real rest (blue, tile 7) was
  missing. Arm: 2.5, held out, on the spurious header rest it exposes. **4 of 30 `rest8th` boxes on Litolff p1-3
  are key flats (0 of 133 on Brahms)** -- a `rest_is_not_a_rest` refusal (2.33's family), not built here: see 2.100.
* Brahms p1 s0 staff 4 bar 1 (two rests found): the print (tile 2) is an eighth note, three eighth rests and a
  quarter rest = 3.0 in 6/8; base had a 1.0 chord (cross-staff whole heads from the padded cell) cancelling a
  missing rest; arm reads the rests the print shows and the same wrong chord leaves 4.0.
A rest added to an already-right bar that stays right: 0.

### Hand truth (Brahms pdf 0, swept cells; `probe/handtruth_2_99.py`)
Frame control 7 of 8 truth rests overlap a filed cluster (a Litolff record against this page reads 0 of 8 and the
script stops: it can fail). Ink alone: `rest8th` 5 of 5 read eighth, `restQuarter` 2 of 3 (the third is an 8 px
sliver). Decided unboxed rests invented: 0. Page 0 is partly labelled and every truth rest on it is a detector
pre-fill, so it can only fail the decision by inventing; it does not hold the unboxed population.

### Tiles: `out/print/2.99-review/` (12, blind)
900 px, 600 dpi, red = the bar, blue = the piece, big number, nothing of ours on the image; order shuffled;
`manifest.json` holds each tile's purpose and our reading. Kinds: decided eighth x6 (3 released, 2 cancelling,
1 still held), decided quarter x2, refused stem strokes x2, one abstention, one control (a double-sharp box over
eighth-rest ink). Frame control: filed staff lines fitted locally at the piece's x must carry 2x the gap ink and
fail half a space off; a tile that fails is skipped. My own look (rule 7, not evidence): tile 2 shows the three
printed eighth rests and quarter rest with blue on the last; tile 8 (abstained) brackets a natural sign.

### Limits
Eighth and quarter only. Windows from two plates and five pages; displaced rests abstain (Brahms 4 decided of
27 unboxed). `consequences._missed_rest_witness` does not yet count a decided unboxed rest as explaining its
ink (read by 2.97's `reconcile_duration`; left alone: a still-short bar keeps its lengthening refused). GATHER
changed: only a full re-gather prices the whole movement.

### 2.99 -- Sean's judgement of the 12 tiles (2026-10-12) and the repair

Verbatim: *"1. 8 rest 2. 8 rest 3. flat accidental 4. 4 rest 5. 8 rest 6. 8 rest 7. 8 rest 8. nat accidental 9. 8 rest 10. end of slur 11. key flat 12. 4 rest"* (`out/print/2.99-review/answers.json`).
Decided rests 1, 2, 4, 5, 7, 9, 12: **7 right**. Refusals 3 (flat) and 11 (key flat) right; 8 (natural) abstained, fine.
**Tile 10 WRONG: decided eighth, it is the end of a slur** (Brahms p1 s1 staff 3 bar 6: a thin diagonal stroke ending on a head).
Tile 6 is a real eighth rest refused `already_read_as_a_glyph` under a double-sharp box: a known MISS, not built (a standing
accidental box where no head follows could be re-read; the 3 such Litolff boxes are all eighth-rest ink).

Repair (decision only, no re-gather): the arc boxes the record holds do not reach that cluster (the nearest `tie` boxes
end 200 px away), so the evidence is the ink itself: no ink column is more than 39.5% of its height, and the thinnest of
the 140 standing Brahms rests is 49%. `THIN_STROKE_MAX_COLUMN_SHARE = 0.45` refuses such ink (`thin_stroke_not_a_rest`,
False). RED-first from tile 10's numbers, positive control a rest of the same size and place with a 62% column (stays an
eighth). Controls unchanged (standing rests read the same; 0 of 52 accidentals decided a rest). **Removed from the decided
rests on the two count pages: 1 (Brahms, tile 10 itself, a slur end), 0 on Litolff**; so no second tile set was cut. Decided
now: Litolff 13 eighth + 3 quarter, Brahms 3 eighth; bars released 10 / 1.

### 2.97e. Sean's evidence rule (2026-10-12, CLAUDE.md §10) -- final state of the lane
Rule: *"only when we see evidence of an eigth shoulf it be called that"*, refined: the bar may CONFIRM an
eighth that has positive evidence of its own, never SUPPLY one. `consequences._eighth_evidence` reads the narrowed
verdict's own detail: `flag_levels`/`flags_attached`/reasons `flags_disagree`, `hooks_counted`, `flag_ink_unread`
(= flag read), `beams_by_stem`, `levels_certain`, `levels_possible`. A candidate with beam levels and none of these
is unavailable to every bar-sum settlement (EVALUATE chord unit, INFER rule); the settled verdict cites
`eighth_evidence`. A REFUSED stroke (`beams_not_by_ink`, `too_thin`) is NOT evidence: Sean's singles 1-4 all had
1-2 of them and were all quarters (0/4; likelihood floor not met; revisit with more tiles). Settle-alongside is
removed (2.97d). 4 tests, positive control (flag read -> confirmed) and the longer candidate needs none.

Re-measured on merged main (arm vs base on the same tree, `probe/run_2_97.py`, base = the three staged files
from `origin/main`): Litolff held 1,026 -> 1,023 (released 14, newly held 11), notes 5,941 -> 5,973, narrowed
not written 352 -> 307; Brahms held 2,112 -> 2,067 (released 57, newly held 12), notes 8,224 -> 8,387, narrowed
3,180 -> 3,076. The newly-held bars (11 + 12) are NOT yet explained (a settled value makes a previously written
bar no longer add up?) -- open. Settlements that survive: Litolff chord 9 bars / 18 heads (all the longer
candidate), INFER single 15 / 19 (longer), columns 19 / 45 (41 longer; 4 eighths citing `beam_joined_to_stem` +
`beam_levels_possible`); Brahms chord 59 / 118 (116 longer; 2 eighths citing `beam_levels_possible`), INFER single
1, columns 0. Removed by the rule on Litolff (vs the arm before it): 16 heads, all eighths with no evidence (12
columns, 4 INFER singles); chords lost none. Hand truth pages 0-1: base wrong 12, arm 13 -- the one added is the
0/0/6/2 chord that Sean judged a dotted quarter = our value (scorer dot artefact), so true wrong = 12 = base.
Value outside own candidates 0. Fast tier 7,592 (2 failures from 2.9x's hook tests fixed by counting
`flag_ink_unread` as flag evidence); `check` 192.

### 2.97f. The newly held bars, traced (follow-up, Sean 2026-10-13; `probe/newheld_2_97.py`)
Litolff 11, Brahms 12 bars were written in base and held in the arm. Every one traces to ONE head:
- Litolff 11: base's OLD single-note rule (`reconcile_duration`, not mine) had decided a narrowed head to 0.5
  (an eighth) because it was the one landing. My evidence rule now filters `_admitted` for every bar-sum
  settlement, so that landing no longer exists and the head stays narrowed. 6 of the 11 are narrowings with
  reason `flag_ink_unread` (a flag was SEEN) -- FIXED by counting `flag_ink_unread` as flag evidence (the arm5
  run predates the fix); 5 are `beam_discounted_uncertain` bare stems with no evidence of an eighth.
- Brahms 12: 11 the same (a bare stem the old rule made an eighth), 1 (4/0/9/10) is the opposite -- the arm's
  chord settlement took two `beams_ambiguous` heads (candidates 1.5 / 0.75, `levels_possible` evidence) to 0.75
  and the exporter's voice-split bar check then disagrees with reconcile's single-stream sum; in base those
  heads were unwritten, so the bar "added up" only because two notes were missing.
So 16 bars lost a bare-stem eighth that base had written by arithmetic alone -- exactly what Sean's rule
forbids -- not a fault in the new rules. BUT the print can show a flag our reader missed: tile 3 of
`out/print/2.97-review-3/` (Brahms) is a flagged eighth the arm now leaves narrowed. Whether the old path should
keep writing such eighths is Sean's call (the rule says no; the cost is these bars).
Tiles: `out/print/2.97-review-3/` 6 tiles (2 surviving eighth settlements -- the third bar failed the frame
control -- and 4 newly held bars), blue = the bracketed heads, ours only in manifest.json.
Merged main (2.102): `bar_has_tuplet` is called beside the lane's own guard; main's `shortened_refused` check
is bypassed for the widened rule (its evidence rule is `_eighth_evidence`) and kept for the bare-stem rule.

---

## 2.96 -- why bars are held out NOW: the 2.19/2.22 funnel on the 2026-10-11 night records (2026-10-12)

PATH: STAGED, EXPORT-only (records loaded through `record_io.load_record`, exported
with today's exporter, never re-gathered, never re-decided; no product code
changed). Branch `lane-2.96-held-funnel` off `origin/main` `e671c4a7`. Records:
`beethoven5-litolff-mvt1-whole-20261011-night` and `brahms1-breitkopf-mvt1-whole-20261011-night`.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

The printed meter is the dossier's (Beethoven 5/i 2/4; Brahms 1/i 6/8, with the one
9/8 bar at page 1 / system 0 / cell 0, as 2.22 used). **Control that can fail:** the
file's judged meter equals it on EVERY held bar (0 mismatches), and a deliberately wrong
meter (+0.3 quarter) collapses the evidenced share from 43% to 3% (Litolff) and 75% to 17%
(Brahms; the 17% is exactly the 428 whole-rest bars, which are the bar WHATEVER the
meter). A "cause" is a SIMULATED fix whose arithmetic lands; what raises it to a
finding is (a) a record row that points at it, and (b) a print crop (15 tiles, not yet
read by Sean). Sean has judged none of them: NOT CONFIRMED.

### 2.96a. What was built

`probe/held_funnel_2_96.py` (reuses 2.22's `held_funnel_mvt_2_22.dump` whole -- its
control, bars captured == `bars_held_out_sum` minus doubled-staff bars, PASSES on both:
Litolff 988 + 56 = 1,044, Brahms 2,553 + 0) and adds, per held bar, from the record's own rows:
the cell's ink pieces no standing box explains (2.80's witness rule restated over dicts),
its `Q.AUG_DOT` rows with their `Q.DOT_ROLE`, the cell width against its system's median,
and per event the owner and duration verdicts with the beam-doubt counters.
`probe/classify_held_2_96.py` is 2.22's minimal-fix search with §18's lesson built in:
**every simulated fix is EVIDENCED (a record row points at it and says what) or ARITHMETIC
(the sum lands, nothing points at it).** Per bar: search evidenced fixes alone (size 1-3);
else evidenced + arithmetic (`arith_only`, a sum, not a diagnosis); else `unexplained`.
Exhaustive; the partition sums to the held total (asserted; it exits 3 otherwise).
`probe/summarise_2_96.py`, `probe/n_shape_2_96.py`, `probe/tiles_2_96.py`.
Results: `out/2.96/` (partitions per bar, the text of every run, `summary.md`).

### 2.96b. The partition (exhaustive)

| | Litolff 1,044 | Brahms 2,553 |
|---|--:|--:|
| evidenced, ONE cause | 409 (39.2%) | 1,692 (66.3%) |
| evidenced, 2-3 causes together | 37 (3.5%) | 224 (8.8%) |
| arithmetic only (a sum lands; no row points at it) | 517 (49.5%) | 633 (24.8%) |
| unexplained (nothing, at 3 fixes, lands it) | **25 (2.4%)** | **4 (0.2%)** |
| on a doubled staff (the exporter counts them, cannot locate them) | 56 (5.4%) | 0 |

"Unexplained" is tiny because the arithmetic tier is permissive; the honest figure for
"the record gives no reason" is the arithmetic-only row.

### 2.96c. Ranking -- bars released if that ONE cause alone were fixed

(overlapping: a bar can be released by two different single fixes)

| cause | tier | Litolff | Brahms | both |
|---|---|--:|--:|--:|
| narrowed head(s) whose own candidates land the bar (`duration_narrowed`, not written) | evidenced | 73 | 719 | **792** |
| a lone whole rest left at 4 beats (a bar rest in a 2/4 or 6/8 bar) | evidenced | 30 | 428 | **458** |
| unboxed eighth-rest-shaped ink + bar short by an eighth or so | evidenced | 45 | 287 | **332** |
| a head refused `too_narrow` whose value fills the gap | evidenced | 25 | 143 | 168 |
| unboxed quarter-rest-shaped ink | evidenced | 75 | 41 | 116 |
| a beam level at a note whose beam row carries doubt | evidenced | 73 | 114 | 187 |
| `chord_value_undecided` | evidenced | 14 | 41 | 55 |
| a dot (a row whose role is unsettled) | evidenced | 1 | 53 | 54 |
| a head boxed twice / a barline read as a rest / two voices (each) | evidenced | 12 / 18 / 9 | 21 / 15 / 20 | 33 / 33 / 29 |
| one head fill misread (quarter read, half printed) | ARITHMETIC | 311 | 229 | 540 |
| drop one event | ARITHMETIC | 188 | 335 | 523 |
| one beam level, one beam group | ARITHMETIC | 212+61 | 361+113 | 747 |
| ink of no rest shape + any rest value | ARITHMETIC | 328 | 876 | 1,204 |

The ARITHMETIC rows are not causes. They are listed because they are the large numbers a
sum-only classifier prints; 2.22's `F` (300 Litolff bars) is the head-fill row here.

Base rates (the control the ink witness needs; `out/2.96/controls.json`): unexplained ink
of ANY kind sits in 28% of Litolff cells that are NOT held (1,228 of 4,389) and 43% of
held ones (421 of 988); 35% (1,443 of 4,132) vs 51% (1,309 of 2,553) on Brahms. An
eighth-rest-shaped unexplained piece sits in 5% of Litolff and 7% of Brahms non-held
cells (218 of 4,389; 294 of 4,132), and the evidenced `I:eighth` fires on 12% and 23% of
held ones: a lift of about 2x and 3x, enough to be evidence, not proof. That is why only
SHAPED ink is evidenced and "ink of no rest shape" is arithmetic.

### 2.96d. What the top cause is made of (`probe/n_shape_2_96.py`)

Bars held because narrowed heads are not written, where the record's own candidates and the
meter land the bar UNIQUELY:

| | Litolff | Brahms |
|---|--:|--:|
| ONE narrowed head, system meter DECIDED -- `reconcile_duration` (EVALUATE: one note, unique landing) should land these and does not | 39 | 97 |
| ONE chord of 2-3 narrowed heads, meter decided (`reconcile_duration` "changes at most ONE note": a chord's heads are separate notes) | 21 | 175 |
| several narrowed columns, meter decided (a joint landing; the rule changes one note) | ~11 | ~190 |
| meter ABSTAINED on that system (`carry_not_corroborated` / `carry_outweighed_by_the_bars`; every consumer reads `Q.METER`) | 0 | ~214 |

INFER's `collapse_duration_to_barline` cannot reach them: it collapses from OTHER staves
at the same onset column, and refuses a witness whose length came from the meter.

### 2.96e. The whole-rest bars (second cause)

Brahms 428 bars, residual exactly -1.0 quarter (a 4-beat rest in a 3-quarter bar), 403 of
them on a system whose `Q.METER` ABSTAINS (205 `carry_not_corroborated`, 198
`carry_outweighed_by_the_bars`). CLAUDE.md §10: a whole rest means the BAR whatever the meter,
so this fix needs no meter reading, but `size_measure_rest` takes `Q.METER` as its cause and
does not run there. A control that holds: with the meter shifted 0.3 these 428 are exactly
the bars still released. Litolff 30 are on systems whose meter is DECIDED -- a different
cause: the record shows a SECOND box on the same ink refused `ink_is_a_whole_rest`, so the
rest may not count as lone. Not confirmed: tile 6 shows the rest, not the second box.

### 2.96f. Print check, 15 tiles for Sean (`out/print/2.96-review/`, `manifest.json`)

Phone-sized (900 px), 600 dpi, red corners = the bar (following the staff), blue
corners = the subject, big tile number, nothing of ours on the image. The frame control
(five staff lines carry >= 2x the ink of the gaps AND the same test shifted half a space
fails) REFUSED 4 candidates, so it can fail. Tiles 1-3 narrowed heads (2 Brahms, 1
Litolff), 4-6 whole rest (2 Brahms meter-abstained, 1 Litolff meter-decided), 7-9 unboxed
eighth-rest ink (2 Brahms, 1 Litolff), 10-12 a dot (Brahms), 13-15 one head fill
(Litolff; the ARITHMETIC-only row, shown to see whether the print backs it).

What I could see myself (the lane's own reading, rule 7: not evidence):
- tile 1: the print is a dotted quarter, a tied quarter and an eighth: the two blue
  heads are the narrowed ones and their candidates (1.5 and 1.0) land the bar.
- tiles 4 and 6: a lone whole rest in a bar -- the print agrees with the classifier.
- tile 7: two eighth rests sit in the bar and one has no box -- agrees.
- tiles 10-12 (the dot): **my eye-read here was WRONG; Sean is the evidence.** I wrote that the blue dots were another staff's or a letter's. Sean: 10 is a staccato belonging to the staff above (not this staff's); 11 and 12 ARE augmentation dots. So the dot cause is real on 2 of 3 (the evidenced `D`, 54 bars released alone, is small but not spurious); the one false positive (10) is the cross-staff dot the classifier cannot yet tell from its own.
- tile 13 (head fill): the head has the white slash of a hollow head (Sean: a half, tile 14 too).

### 2.96g. Recommended next items (not built here)

1. **Narrowed heads that the bar lands uniquely (792 bars; the largest evidenced cause).**
   Two connections, no new guess: (a) why `reconcile_duration` does not land the 136
   single-head, meter-decided bars it should (look at Litolff 9/1/0/0: it landed the
   OTHER note instead); (b) let it change one CHORD (all heads at one onset) together,
   then several columns jointly where exactly one joint assignment lands the bar.
2. **A lone whole rest needs no meter (458 bars; 403 on abstaining Brahms systems).**
   Exports as a measure rest of the file's bar. A connection (CLAUDE.md §10), plus the 30
   Litolff bars whose second `ink_is_a_whole_rest` box defeats "lone".
3. **The unboxed eighth/quarter rest (448 bars).** 2.80b reads a refused `too_narrow` box
   as an eighth rest; the 332 remaining are ink with no box at all. A reader on the
   unexplained piece (its shape and place on the staff), checked against the same 2.80
   base rate; tiles 7 and 9 say the ink is real.
4. **The head fill (540 arithmetic-only bars; Sean: tiles 13, 14 halves read as quarter, tile 15 a quarter).**
   2 of 3 are real, so it is a cause with print support but no record row; it needs a row of its own (2.23's
   hollow-ink reading, on the merged Litolff plate) before it is wired. Tile 15 is the warning: the sum lands on a
   correct quarter too.
Held back: beam levels (no row points at them except the doubt counters, present on 40% of bars).

### 2.96h. Limits

The dumps are the record's OWN verdicts exported by today's exporter; a GATHER change is
invisible here. The ink witness is 2.80's rule restated over dicts (the base-rate table is
its control). `U:`/`R:` refusal tokens are offered only for reasons that a refusal can
wrongly make; duplicate-box and non-note refusals (clef, digit, dynamic letter) are never
offered. K (a missed barline) is evidenced only where the cell is >= 1.6x its neighbours.

### 2.96i. Sean's answers (2026-10-12, `out/print/2.96-review/answers.json`)

Verbatim: *"1. dot4 , 4 2. 4 3. 4 4-6. whole note rest 7. 1st blue box is an accidental flat,t he secod blue box is a 8 rest 8-9. 8 rest 10. stacato mark belonging to the staff above 11-12. aug dots 13. 2 14. 2 15. 4"*

| cause | tiles | scored |
|---|---|---|
| narrowed heads (N) | 1-3 | **3/3**: his values (1.5 + 1.0; 1.0; 1.0) are inside our candidates |
| lone whole rest (W) | 4-6 | **3/3**: whole-note rest (the bar), including the Litolff meter-decided one |
| unboxed eighth-rest ink (I:eighth) | 7-9 | **3/3** hold an eighth rest; in tile 7 the FIRST blue box is a flat, the second the rest (the ink witness boxed an accidental too) |
| dot (D) | 10-12 | **2/3**: 11, 12 are this staff's augmentation dots; 10 is a staccato of the staff above |
| head fill (F~, arithmetic only) | 13-15 | **2/3** halves read as quarter (13, 14); 15 a quarter, our reading right |

Effect on the ranking: the three top evidenced causes (N 792, W 458, I:eighth 332, plus I:quarter 116) are
confirmed by the print on every tile. D moves from "not a finding" to "a real but small cause with a cross-staff
false-positive mode" (evidenced `D` alone releases 54; the 412 arithmetic-tier `D` are still unproven). The head fill
moves from "arithmetic" to "print-supported, no record row" (2 of 3), so the order of next items is unchanged
(narrowed heads, whole rest, unboxed rest ink) with the head fill added as item 4. The I:eighth ink box can also be a
flat or other accidental: a shape test alone over-counts, so the reader in item 3 must use position on the staff.

### 2.97g. Sean's answers on review-3 (2026-10-13) and the final re-measure
Verbatim in `out/print/2.97-review-3/answers.json` and DECISIONS 2026-10-13: *"1. Dot 8 2. 8, 8 3. 8 4.4 5. 8 rest 6. 4"*.
- Tiles 1-2 (eighths the rule still settles on weak beam evidence): **2 of 2 right** (dotted eighth; two eighths).
- Tiles 3-6 (bars newly held because base's arithmetic-only eighth is now refused): base was RIGHT on tile 3 (a real
  flagged eighth our reader missed -> ROADMAP 2.104), WRONG on 4 (a quarter), 5 (an eighth REST written as a note) and
  6 (a quarter). **The strict rule avoids 3 wrong notes for 1 lost correct eighth.** n is small; the direction is
  consistent with singles 0/4 in 2.97d.
- Sean's choice: land the STRICT eighth-on-evidence rule as built; missed flags are 2.104's job, not the bar's.

Re-measure with `flag_ink_unread` counted as flag evidence, Litolff night record
(`beethoven5-litolff-mvt1-whole-20261011-night`), base = origin/main tools (incl. 2.102), arm = this branch merged with
origin/main, `probe/run_2_97.py`, `probe/newheld_2_97.py` (the whole `held` list; the report's `bars` figure in brackets):
| | held bars (report) | held list | notes in file | narrowed not written |
|---|---|---|---|---|
| base | 1,027 | 953 | 5,937 | 362 |
| arm, `OMR_NARROWED_BAR=1` | 1,018 | 944 | 5,994 | 311 |
| arm as shipped (`OMR_NARROWED_BAR` default OFF) | 1,033 | -- | 5,916 | 368 |
ON vs base: released 14, **newly held 5** (was 11 before the `flag_ink_unread` fix), all 5 `beam_discounted_uncertain`
bare stems with no evidence of an eighth -- the refusal Sean's rule asks for. The shipped default (INFER columns rule OFF)
nets +6 held / -21 notes vs base on Litolff: the EVALUATE chord/joint settlement releases bars, the strict rule holds the
arithmetic-only eighths. Brahms was not re-measured (6 GB record; light-load rule); its last figures are 2.97e's.

## 2.134 -- the bar cascade, sized: why bars are held NOW, on the 20261014-night records (2026-10-15)

PATH: STAGED, EXPORT-only (records loaded once through `record_io.load_record`, exported with
today's exporter, never re-gathered, never re-decided; no product code, no flag). Branch
`lane-2.134-cascade` off `origin/main` `afdd39c2`. Records: `beethoven5-litolff-mvt1-whole-20261014-night`
and `brahms1-breitkopf-mvt1-whole-20261014-night` (tree `8b9eb97c`). Probes (all new, none in `tools/`):
`probe/held_funnel_2_134.py` (the 2.117 adaptation of `held_funnel_2_96.py`, which it reuses whole),
`probe/split_2_134.py`, `probe/classify_all_2_134.py` (runs `classify_held_2_96.py` UNCHANGED),
`probe/summarise_2_134.py`, `probe/dissect_2_134.py`, `probe/tiles_2_134.py`. Outputs: `out/2.134/`.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

Printed meter as 2.96 (Beethoven 5/i 2/4; Brahms 1/i 6/8 with the one 9/8 bar at 1/0/0). A "cause" is a
SIMULATED fix whose sum lands; it is evidenced only if a record row points at it. The file's judged
meter equals the printed one on every captured bar (0 mismatches, both movements). Sean has judged
none of this section's tiles: NOT CONFIRMED. Every landing-to-cause link in 2.134e is a HYPOTHESIS
unless it says READ.

### 2.134a. The 2.117 adaptation, and the controls

Since 2.117 `export._bar_holds_out` is called for EVERY bar that does not add up, but a bar with a
certain prefix/suffix is then written PARTIAL (blue notes + red `unread` bracket) and is NOT in
`bars_held_out_sum`. 2.22's `dump` captures both, so its own control reads FAIL by design. The probe
replaces it with a control that can fail: captured == held_sum - doubled + `partial_bars.written`, the
exporter's `held` list == held_sum - doubled, the rest == `partial_bars.written`.

| | Litolff | Brahms |
|---|--:|--:|
| `bars_held_out_sum` (the "699" / "975") | 699 (640 + 59 on a doubled staff) | 975 |
| partial bars (written, counted APART) | 161 | 742 |
| captured by `_bar_holds_out` | 801 (+59 doubled = 860) | 1,717 |
| control (captured == held - doubled + partial; held and partial each bar for bar) | PASS | PASS |
| partition sums to the total (asserted, per kind) | 699 PASS; 161 PASS | 975 PASS; 742 PASS |
| judged != printed meter | 0 | 0 |
| **wrong-meter run (+0.3 quarter)**: evidenced / arithmetic / unexplained | 0 / 0 / 640 (evidenced share 26.9% -> 0%) | 0 / 0 / 975 (46.5% -> 0%) |

The wrong-meter run is the control that has to fail, and it fails completely: no evidenced and no
arithmetic fix lands any bar. (2.96's run left 3% / 17% standing; by 2.96 that residue WAS the lone whole
rests, which the record no longer holds -- 2.134c.) HELD and PARTIAL are classified apart: a partial bar is
one the file already keeps part of, so only held is "still held out"; partial is the second population the
same causes also gate.

Sean's judged index (`judged score ... --doc litolff|brahms`, run first): Litolff 108 right / 11 wrong /
4 narrowed / 1 abstained / 13 not_found / 97 unscored; Brahms 70 / 10 / 18 / 1 / 7 / 133. The wrong ones sit
in `2.114-*` (second detector, OFF), `2.75`, `2.78`, `2.80-review-2`, `2.81`, `2.83`, `2.88`, `2.99`; none is a
narrowed-duration head of the kind the tiles below ask about. (`out/2.134/judged-*.json`.)

### 2.134b. The partition, against 2.96

HELD bars (the doubled-staff copies are the exporter's count and cannot be located):

| | 2.96 Litolff 1,044 | **2.134 Litolff 699** | 2.96 Brahms 2,553 | **2.134 Brahms 975** |
|---|--:|--:|--:|--:|
| evidenced, ONE cause | 409 (39.2%) | **167 (23.9%)** | 1,692 (66.3%) | **374 (38.4%)** |
| evidenced, 2-3 causes | 37 (3.5%) | 21 (3.0%) | 224 (8.8%) | 79 (8.1%) |
| arithmetic only (a sum lands, no row points at it) | 517 (49.5%) | **431 (61.7%)** | 633 (24.8%) | **520 (53.3%)** |
| unexplained | 25 (2.4%) | 21 (3.0%) | 4 (0.2%) | 2 (0.2%) |
| on a doubled staff | 56 (5.4%) | 59 (8.4%) | 0 | 0 |

Every bar that does not add up, held PLUS partial (the like-for-like figure against 2.96's total): Litolff
1,044 -> **860** (699 + 161), Brahms 2,553 -> **1,717** (975 + 742). Partial bars alone: Litolff 161 = evidenced
one 136 / two-three 8 / arithmetic 17; Brahms 742 = 593 / 81 / 66 / 2 unexplained. Held plus partial, evidenced
ONE cause: Litolff 303 (35%), Brahms 967 (56%).

The honest "record gives no reason" figure is still the arithmetic-only row, and it is now the MAJORITY of
held Litolff bars (431): 179 head fill misread (`F~`), 96 drop one event (`X~`), 59 one beam level (`B~`),
34 ink of no rest shape, 21 one beam group. Sums, not diagnoses (2.24's lesson); nothing in the record points at them.

### 2.134c. Bars released if ONE evidenced cause alone were fixed (held | partial)

| cause | Litolff held | Litolff partial | Brahms held | Brahms partial | 2.96 Lit / Brahms |
|---|--:|--:|--:|--:|--:|
| **narrowed head(s), candidates land the bar (N)** | 10 | 58 | **179** | **404** | 73 / 719 |
| unboxed eighth-rest-shaped ink (I:eighth) | 23 | 13 | 79 | 82 | 45 / 287 |
| a beam level at a doubted note (B) | 43 | 17 | 56 | 46 | 73 / 114 |
| unboxed quarter-rest-shaped ink (I:quarter) | 33 | 14 | 8 | 20 | 75 / 41 |
| refused `too_narrow`, value fills (R:too_narrow) | 6 | 12 | 26 | 61 | 25 / 143 |
| a dot the record saw and did not settle (D) | 1 | 0 | 33 | 21 | 1 / 53 |
| `chord_value_undecided` (Y) | 0 | 14 | 5 | 42 | 14 / 41 |
| a rest refused `rest_has_a_stem` (position only) | 17 | 3 | 2 | 0 | -- |
| one rest/head boxed twice (S) | 11 | 0 | 19 | 0 | 12 / 21 |
| **a lone whole rest left at 4 beats (W)** | **0** | 0 | **0** | 0 | **30 / 428** |

W is evidenced on ZERO bars in all four sets (READ off the data): no lone 4-beat rest is left, where 2.96 had 458.

### 2.134d. How many held bars hold because of ONE lost or narrowed NOTE, and which verdict lost it

Definition (`dissect_2_134.py`): the bar's minimal EVIDENCED cause is a single token naming a head the record
narrowed or refused (N, Y, O, P, Q, R:/U: on a head) whose own value fills the gap. Rests, beam-value doubt,
structure and the arithmetic tier are NOT counted.

| | Litolff held 640 | Brahms held 975 |
|---|--:|--:|
| ONE note-family cause | **21 (3.3%)** | **198 (20.3%)** |
| of which N (narrowed, `Q.DURATION`) | 10 | **179** |
| N shape: ONE head | 3 | **30** |
| N shape: ONE chord (2-3 heads at one onset, one stem) | 7 | 38 |
| N shape: two columns / three or more | 0 | 83 / 28 |
| N where the record's own candidates land the bar UNIQUELY | 10 of 10 | 165 of 179 |
| other note causes (Y chord undecided / R,U too_narrow / O / Q / P) | 11 | 19 |
| rest causes (I:*, rest_* refusals, A) | 68 | 76 |
| beam-value doubt (B, G) | 50 | 44 |
| structure (S, V, K) / dot | 26 / 1 | 30 / 26 |

**Which verdict lost the note (the record's own words):** ALL 189 N bars are `Q.DURATION` narrowed by the
ADJUDICATE duration reader. Head by head (404 narrowed heads on Brahms, 18 on Litolff) the reason is
`beam_discounted_uncertain` on 394 of 404 (Brahms) and 18 of 18 (Litolff): the reader saw beam strokes and
DISCOUNTED them, so the head stayed eighth-or-quarter. The two candidates are always the same pair across the
note-family bars: eighth(beam 1)|quarter(beam 0) on 218 Brahms heads, dotted eighth|dotted quarter on 191
(Litolff 18 plain eighth|quarter). The other 10 Brahms N heads: `dot_seen_beside_a_plain_note` 3,
`head_fill_from_ink` 3, `flag_ink_unread` 2, `beams_ambiguous` 2. Meter at the system: Brahms N bars sit on a
DECIDED meter in 121 of 179 (89 `carried`, 29 `carried_uncontested`, 3 `voted`) and an ABSTAINED one in 58
(38 `carry_not_corroborated`, 20 `carry_outweighed_by_the_bars`); Litolff 10 of 10 decided.

The non-N note causes are other verdicts: `chord_value_undecided` (Y, 4 Brahms bars), an `owned_by_another_staff`
abstention on a `too_narrow`/`clipped_fragment` box (R/U, 7 + 13 heads on Brahms; 7 on Litolff), `owner_not_read`
(O, 1 Brahms bar), `no_pitch` (P, 1 Litolff bar).

**Why these still hold (design, not a bug; the record and the ledger agree).** 2.97 lands, at ONE note, a narrowed
head the bar settles, but only where there is evidence of an eighth (Sean's strict rule, DECISIONS 2026-10-13: the
strict rule avoids 3 wrong notes for 1 lost correct eighth). The N bars are the ones whose beam evidence was
discounted: the bar would land them and the rule refuses to let the bar SUPPLY the eighth. Nothing in this probe says
the strict rule is wrong. It says the note is lost at the BEAM reading (is there an eighth beam on this stem or not),
not at the bar sum. The tiles put that question to Sean.

### 2.134e. Which of the 10-14 landings moved which cause (HYPOTHESES, except READ)

- **2.117 (partial bars)** READ: held fell 1,044 -> 699 and 2,553 -> 975 only partly because bars were fixed; 161 / 742
  of the held-type bars are now written partial. Bars that do not add up at all fell 1,044 -> 860 and 2,553 -> 1,717.
  Partial bars are mostly N / Y / R (Brahms 404 of 742 N alone, Litolff 58 of 161): the note-family cause is now
  mostly already written as a blue prefix + red bracket and counted apart.
- **2.98 (a lone whole rest is the bar)** READ: W evidenced on 0 bars (2.96: 458). Hypothesis: all of Brahms 428 and
  Litolff 30. The largest single change since 2.96.
- **2.99 (unboxed eighth/quarter rests read from ink)** hypothesis: I:eighth Brahms 287 -> 79 held (+82 partial);
  I:quarter Litolff 75 -> 33. The residue is ink with no box and can be a flat (2.96 tile 7).
- **2.97 (`OMR_NARROWED_BAR`) + 2.121 (bare stem takes the head's own unbeamed value, GUESSED)** hypothesis: N held
  Brahms 719 -> 179 alone (held + partial 583), Litolff 73 -> 10 (68). 2.121 is named because 19 of 24 twins split
  losses were quarters under a slur; the reason `refused_strokes_are_slurs_or_too_thin_for_a_beam` is READ on 70 Brahms
  and 2 Litolff single-head events in the held dump.
- **2.115 (head re-centred on the page raster)** hypothesis, small: R:too_narrow alone fell Litolff 25 -> 6 and Brahms
  143 -> 26; the N reason `head_fill_from_ink` survives on only 3 Brahms heads.
- **2.127/2.128 (dot role, dot staff position)** hypothesis: D alone Brahms 53 -> 33 held (+21 partial).
- **2.129/2.130/2.131 (stacked heads, whole->half, staccatissimo)**: no cause in this table is named for them; any
  effect would sit in the arithmetic-only `F~` row, which fell Litolff 311 -> 221 (alone) and Brahms 229 -> 69 --
  hypothesis, no row points at it.
- **B (beam level at a doubted note)** did not fall (Litolff 73 -> 43 + 17, Brahms 114 -> 56 + 46): no landing in the
  list worked beams.

### 2.134f. Print check, 14 blind tiles for Sean (`out/print/2.134-review/`, `manifest.json`)

11 tiles are ONE narrowed head (`Q.DURATION` narrowed, `beam_discounted_uncertain`; candidates eighth|quarter or
dotted eighth|dotted quarter; meter decided; the bar lands uniquely): 1 Litolff (tile 7), 10 Brahms (pages 5-26, both
candidate pairs). 3 CONTROLS are a head the record DECIDED, cut identically: tile 2 a dotted quarter with no beam over
it (Brahms), tile 3 a plain quarter with no beam (Litolff; dense bar, cluttered), tile 6 a beamed eighth the beam reader
READ (Brahms). Shuffled with a fixed seed (controls are not at the end); the key is `manifest.json` only. 900 px wide,
600 dpi, RED corners = the bar (following the staff), BLUE corners = the note asked about, big tile number, nothing of
ours drawn. Frame control (five staff lines >= 2x the ink of the gaps AND the half-space-shifted test must fail) REFUSED
4 candidates (Litolff 4/0/8/2 and 16/0/0/2, Brahms 9/0/11/0 and 12/0/5/0), so it can fail; the next candidate was taken.
System-start bars (clef and key in the way) are excluded from the controls. The lane has not judged the print
(rule 7): Sean is the evidence.

### 2.134g. Recommended next (not built here)

1. Sean's reading of tiles 1-14 decides it. If the blue notes are mostly UNBEAMED (quarter / dotted quarter), the
   lost note is a beam FALSE POSITIVE (the discounted strokes are slur ink or too short) and the fix is reading "no
   beam", which needs no bar. If mostly beamed eighths, the bar is right and the beam reader too timid; the fix is the
   beam evidence (tip, join), still no bar-supplied value.
2. The 83 two-column and 28 many-column Brahms N bars are the cascade's tail: they only land JOINTLY, which the
   one-note rule cannot do. Not sized for a fix until the single case says which way it goes.
3. Litolff's 431 arithmetic-only held bars (179 `F~`) have no record row; 2.96 item 4 (a head-fill row) is still the
   missing piece there.

### 2.134h. Limits

The dumps are the record's OWN verdicts exported by today's exporter (the 8b9eb97c tree); a GATHER change is invisible
here. Partial-bar cause tokens use the cell's full event list (the `_bar_holds_out` input), not the prefix/suffix the file
wrote. The landing-to-cause links in 2.134e are hypotheses: no 20261011 record was loaded here, so the two nights were
not compared bar by bar. The 59 doubled-staff bars are the exporter's count, not located.

### Sean's answers (2026-10-15)

11 of 11 narrowed heads land where the bar puts them (6 quarters, 4 dotted quarters, 1 eighth whose printed flag the tip
reader missed, tile 10), and 3 of 3 controls (tiles 2, 3, 6) are right. Tile 13 has a tremolo stem and a dot (Sean: "13 is
a dot 4"). Caveat: these are the bar-unique cases with a DECIDED meter only, so this is n=11 on one cause and not yet a
rule. Answers: `out/print/2.134-review/answers.json`.

## 2.136 (step 1) -- why `reconcile_duration` leaves a bar-unique narrowed head unsettled (2026-10-15)

PATH: STAGED EVALUATE (`consequences.reconcile_duration`) and, because it is the rule's twin, STAGED INFER
(`inferences.solve_bare_stem_bar`, flag `OMR_NARROWED_BAR`, ON). Diagnosis only: no product code, no flag, nothing in
`tools/` edited (the two counterfactuals below are in-process patches inside the probe). `lane-2.136-reconcile` off
`origin/main` `555e6f5f`, with `lane-2.134-cascade` merged for its data. Records `20261014-night`, loaded once each
via `record_io.load_record`, **as written** (GATHER rows rebuilt, the record's own verdicts inserted with their ids; not
re-decided, so there is no tree drift against 2.134). Probe `probe/reconcile_gates_2_136.py` (reusing the rule's own
helpers: `_standing`, `_left_the_bar`, `_event_totals`, `_narrowed_chords`, `_bar_heads_are_clean`, `_bar_has_tuplet`,
`_common_options`, `_admitted`, `_missed_rest_witness`, `_bar_beats_at`; only the ten-line landing loop is restated, it
is inline in the rule). Outputs `out/2.136/` (`*-gates.json`, `*-gates.cf2.json`, `*-gates.infer-cf.json`, logs).
Population: the 189 N bars of 2.134 (Litolff 10, Brahms 179), `partition_sums` true in both files.

### 2.136a. The partition (first gate that applies, in the rule's own order)

| gate that leaves the bar unsettled | Litolff | Brahms | all | share |
|---|--:|--:|--:|--:|
| G0 rule never called: the system's `Q.METER` is ABSTAINED (`carry_not_corroborated` 38, `carry_outweighed_by_the_bars` 20) | 0 | 58 | **58** | 31% |
| G4 zero landings (no admitted SINGLE event lands the bar) | 5 | 71 | **76** | 40% |
|   of which: lands only by moving TWO OR MORE narrowed events at once (every head's only evidence-admitted length is its unbeamed one; the bar lands only if all take it) | 1 | 50 | **51** | 27% |
|   of which: the bar ALREADY fits at the heads' best (eighth) candidates; the rule will not supply an eighth | 4 | 7 | 11 | 6% |
|   of which: no assignment of the heads' own candidates lands | 0 | 10 | 10 | 5% |
|   of which: two or more events AND an unevidenced eighth | 0 | 4 | 4 | 2% |
| G5 more than one landing (10 Brahms + 1 Litolff of these are a chord unit dropped by `_bar_heads_are_clean`, so its heads land one by one) | 1 | 21 | 22 | 12% |
| G6 one landing, a LENGTHENING, the 2.80 missed-rest witness reads unexplained ink (1-4 pieces) | 2 | 20 | 22 | 12% |
| G9 the rule DID fire in this bar, on a DECIDED neighbour (re-read to a beamed value); the narrowed head stays narrowed (2.97 removed the joint settle) | 2 | 9 | 11 | 6% |
| G1 no meter in force / G2 no valued note / G3 no event grouping / tuplet member skipped / G7 replay lands but nothing written | 0 | 0 | 0 | 0 |
| **sum** | 10 | 179 | **189** | |

Not gates here, read off the rows: 76 of the 189 bars hold a box a decided verdict set aside (the rule sums without it
and still refuses for the reasons above); no row has a tuplet member.

**Control (rule 7), and it failed first.** The same replay run on EVERY cell where the log holds a `reconcile_duration`
verdict, in the state the rule saw (its own revision undone, and where needed the later `infer:*` revisions undone):
Litolff 216 of 216 and Brahms 287 of 287 replay as "landed". The first version scored 215 of 216: its pre-state undid
only the rule's own revision, and the cell (12/0/2/3) had also been revised by INFER afterwards. The other direction: of
the 484 (Litolff) and 1,910 (Brahms) cells with a narrowed head and no reconcile verdict, the replay says "lands" on 6
and 31 and ALL 37 were settled by another decider (`infer:collapse_bare_stem_by_bar`, `infer:collapse_arc_ink_not_beam`,
`reconcile_unjoined_dots`, `size_reinstated_rest`): the final-state replay of an EVALUATE rule is not the EVALUATE-time
state for a cell INFER later touched, which is why each population row also carries `evaluate_time` (INFER undone). G0
reads the FINAL meter outcome, because the record does not store EVALUATE's skipped list.

Examples, `(page, system, staff, cell)`, measure, part:
- G0: Brahms (13,1,0,7) m259 P1 `carry_outweighed_by_the_bars`; (19,0,0,2) m354 P1 `carry_not_corroborated`.
- G4 two-or-more events: Brahms (3,1,0,6) m54 P1 (4 narrowed heads, sum 1.75 of 3.0); (13,0,0,9) m249 P1 (2 heads, 1.75
  of 3.0); Litolff (4,0,1,12) m95 P2.
- G4 eighth: Litolff (11,0,0,8) m312 P1 and (14,1,1,6) m421 P2 (two narrowed heads, the bar already 2.0 at the
  eighths); Brahms (11,0,1,3) m197 P2.
- G5: Brahms (4,1,0,8) m78 P1, (11,0,0,1) m195 P1 (a chord unit dropped by the clean guard, its two heads each land);
  (9,0,2,7) m168 P3 (chord vs head, 3 landings).
- G6: Litolff (9,1,0,0) m263 P1 (3 unexplained ink pieces) and (4,0,8,2) m85 P10; Brahms (16,0,0,11) m315 P1 (4 pieces).
- G9: Litolff (8,0,0,15) m222 P1 (the rule re-read decided glyph 4 from 2.0 to a beamed 1.0 and left the two narrowed
  heads); Brahms (3,0,1,2) m40 P2.

### 2.136b. Two upstream faults the partition exposed (both are WIRING, found by following G4's two-event bars)

The 51 two-event bars are not the rule's job: its bound is ONE event (2.97) and the joint case was given to INFER's
`collapse_narrowed_by_bar` ("several columns jointly, printed meter only", ON since 2026-10-13; Sean's 2.97 tiles:
columns 4 of 4). INFER declines every one of them, and not on the arithmetic:

1. **`_printed_meter_roots` reads the wrong segment.** A `carried` meter is compared with the top-level numerator of the
   system it was carried from, which is that system's FIRST segment (the hazard `_bar_beats_at`'s docstring and 2.79
   name). Brahms 1/i opens in 9/8, prints a return to 6/8 at bar 1, and every later system CARRIES 6/8 from it:
   (3,1) `carried` 6/8 from (1,0) `voted` whose top level reads 9/8, so the carry "changed" and INFER answers
   `meter_not_from_the_print`. 118 of the 179 Brahms N bars (89 `carried`, 29 `carried_uncontested`), including all 50
   two-event bars (`probe/meter_depth_2_136.py`, `meter_pair_2_136.py`; the hop limit of 40 is not the cause, max depth
   0).
2. **`_bar_heads_are_clean` ignores the ledger owner.** Its off-staff clause (a head beyond 1.6 staff spaces from the
   staff is "not this staff's own") fires on 127 off-staff head instances, 125 of which have a DECIDED
   `Q.GLYPH_OWNER` (the patch below requires it to name THIS staff; `ledger_note_first` 119, `ledger_direction` 3, `stem_toward_staff` 2,
   `ledger_owner_density` 1; median 2.6 spaces off). CLAUDE.md section 5: the ledger lines name the owner. The helper is
   shared: INFER `any_reason` declines 48 Brahms bars on it (`heads_not_this_staffs_own`) and `reconcile_duration` drops
   22 chord units on it (11 of the 22 G5 bars). The restatement in the probe agrees with the helper on 189 of 189 bars
   (`probe/clean_table_2_136.py`).

Counterfactual (in-process patch, `tools/` untouched): (W1) compare the carry with the source's LAST segment; (W2) the
off-staff clause stands down for a head whose DECIDED owner is this staff (the other two clauses, duplicate box and
another-staff-same-ink, unchanged). Control that can fail: over all 636 Litolff / 2,112 Brahms cells with a narrowed
head, W2 turns the helper False to True on 127 / 488 and True to False on 0 / 0.

| | Litolff 10 | Brahms 179 |
|---|--:|--:|
| today: INFER settles any of these bars | 0 | 0 (declines: 111 `meter_not_from_the_print`, 58 `no_decided_meter`) |
| W1 alone: bars INFER fully releases (heads) | 0 | 22 (52) |
| W1 + W2: bars INFER fully releases (heads) | 1 (2) | **46 (103)**: 34 of the 50 two-event bars + 12 of the G5 bars |
| W2 alone: bars the EVALUATE rule lands (single landing + clear witness) | 1 | 5 |

Everything W1 + W2 would settle is a bar-sum settlement of a narrowed head to one of its OWN candidates: GUESSED, blue,
candidates kept; the head's only admitted length is the unbeamed one (eighth evidence is empty on all of them), so the
bar CONFIRMS a no-beam-seen reading and supplies nothing. This is a count of what the code would do, not a claim that it
is right. Neither patch has been seen against the print; the tiles below are the print check.

### 2.136c. What it must not become (CLAUDE.md section 4, 2.80, 2.97)

- Not an eighth supplied by the bar: the 11 "already fits at the eighths" bars and the 4 "two events and an eighth" bars
  stay refused (section 4: a note is an eighth only on evidence; the bar confirms, never supplies). The evidence filter
  in `_admitted` is not touched.
- Not a lengthening past the missed-rest witness: the 22 G6 bars (and any bar W1/W2 newly exposes to it) keep 2.80
  (Brahms Contrabass bar 13: an eighth rest boxed as a narrow notehead, the bar adding up to the wrong music).
- Not the joint settle beside a DECIDED neighbour: the 11 G9 bars stay (2.97, Sean's tiles: singles 0 of 4, every one a
  bare stem settled to an eighth that prints a quarter).
- Not the meter arbitrated by the bars: the 58 G0 bars have an ABSTAINED meter (`carry_not_corroborated`,
  `carry_outweighed_by_the_bars`). Letting narrowed heads' bar sums corroborate the carry is the bars arbitrating the
  reading they depend on ("the bars fail together with the reading they would arbitrate", rules 7 and 8); not a change
  to be made inside either rule. If anything it is a separate meter question.
- Not READ: a settled note is GUESSED (blue, both candidates), never plain. Not a tuplet (2.102), not a chord that is
  not on one decided stem, not a head boxed twice or another staff's ink (the clean guard's other two clauses stay).
- The single-event bound of `reconcile_duration` is not widened: the 51 two-event bars are INFER's, by design.

### 2.136d. The narrow change this points at (NOT built; step 2 needs Sean's go)

Not a change to `reconcile_duration`'s bound. Two wiring connections, each a decision that is already DECIDED and not
read: W1 in `inferences._printed_meter_roots` (read the segment in force at the source's end) and W2 in
`consequences._bar_heads_are_clean` (an off-staff head with a DECIDED `Q.GLYPH_OWNER` naming this staff is this staff's
own). Each behind a flag, default OFF, tests that fail first on: a carried 6/8 after a 9/8-then-6/8 system, a head 2
spaces above the staff with a decided ledger owner, and the refusals above (Contrabass 13, 2.97's refused singles, a
head with an abstained or other-staff owner, an eighth with no eighth evidence). W2 touches a guard Sean's 2.97 tiles
built; it is the more cautious of the two, and the owner verdicts it would trust are ADJUDICATE's (are they right?
`judged score` has no item on a ledger owner of these heads).

### 2.136e. Blind tiles for Sean (`out/print/2.136-review/`, 12 tiles)

The bars are the top sub-gate (G4, two or more events at once), cut the 2.134 way: 600 dpi, big tile number, RED corners
= the bar, BLUE corners = each note asked about (two per tile, nothing of ours drawn). 10 refused two-head Brahms bars
(4 with an eighth|quarter first head, 6 with a dotted one, spread over pages 3-21) + 2 CONTROLS (two decided beamed
eighths in one bar; the quarter pool had no bar with two). Key in `manifest.json`: for every refused bar the sum at the
heads' best candidates plus both unbeamed lengths is the printed meter exactly. 8 of the 10 are bars W1 + W2 would
settle (both heads unbeamed); tiles 8 and 10 are bars whose missed-rest witness reads unexplained ink, which the rule
would KEEP refused, so Sean's answer on them tests the witness as well. Tile 5's first head is one Sean already
answered (2.81-review tile 17, dotted quarter), which agrees. Frame control (staff lines >= 2x gap ink AND the
half-space-shifted test must fail) can fail; no candidate was refused this time. The lane has not judged the print
(rule 7). Script `probe/tiles_2_136.py`.

### 2.136f. Limits

Final-state replay, not a re-decision (see the control); G0 is read from the final meter outcome. The counterfactuals
count what the patched code would do on these two movements, one edition each; W1 is evidenced on Brahms Breitkopf only
(Litolff has one bar it would release). The 189 are the bars where the head's candidates land the bar; bars held for
other reasons are untouched by both patches except as the clean-helper control counts. `judged score` run on the Brahms
record for the items already answered: 70 right, 10 wrong, 18 narrowed (`out/2.136/judged-brah.txt`).

### 2.136g. Sean's answers (2026-10-15)

Recorded in `out/print/2.136-review/answers.json`. 10/10 refused bars hold exactly the notes the W1/W2 joint landing
would write (each head takes its unbeamed candidate), including tiles 8 and 10, where the 2.80 missed-rest witness read
'unexplained'. Control 3 is right (two eighths). Control 4 is a DECIDED error: Brahms p18 sys1 staff12 cell7, two
eighths that are sixteenths, a missed second beam level. That is a wrong value written plain, so it goes to the
beam-level readers (2.126's family). Caveat: these are pairs on Brahms only, with carried meters; n=10; pairs compared
as multisets, order not compared.


## 2.136 step 2 -- the two wiring connections, behind `OMR_INFER_CARRIED_METER_FIX` (default OFF) (2026-10-15)

PATH: STAGED INFER (`inferences.solve_bare_stem_bar(any_reason=True)`, rule `collapse_narrowed_by_bar`, flag `OMR_NARROWED_BAR`, ON).
`lane-2.136-step2` off `origin/main` with `lane-2.136-reconcile` merged (step 1, the probe, Sean's answers). Sean said yes to step 2 on
2026-10-15 after 10 of 10 refused pairs held exactly the joint landing in which each head takes its UNBEAMED candidate (2.136g).

### 2.136-2a. What was built (fenced by function name)

One new flag `OMR_INFER_CARRIED_METER_FIX`, default OFF (allow-list: only 1/true/yes/on; a typo leaves it OFF), row in `docs/flags-2026-09.md`
marked pending Sean's tiles. It switches two connections, nothing else:
- **W1** `inferences._printed_meter_roots`: a CARRIED meter is compared with the segment in force at the END of the source system
  (`segments[-1]`), not its opening segment. A carry that really changed still returns None (tested both ways, including the mirror case
  that main wrongly ACCEPTS: a source that opens 6/8 and ends 9/8 carried as 6/8).
- **W2** `consequences._bar_heads_are_clean`, new keyword `ledger_owner_aware` (default False; only INFER's rule passes it, from the flag): the
  off-staff clause stands down for a head whose `Q.GLYPH_OWNER` is DECIDED and names THIS staff. The duplicate-box and another-staff-same-ink
  clauses are untouched; an abstained, absent or other-staff owner still fails it (an other-staff owner takes the head out of the bar entirely).
  `reconcile_duration` (EVALUATE) still calls the helper without the keyword, so its one-note bound and behaviour are unchanged; the fence said
  not to edit consequences.py, and the helper is the one named function in it that had to change (the keyword is the whole edit, no
  `reconcile_duration` line touched).
Nothing else changed: GUESSED (an INFER collapse, blue, both candidates carried forward), the reader's own candidates only, no eighth without a
flag or beam candidate (`_shortens_without_evidence`), no `support`, only where every landing agrees, 2.80 ink witness, 2.102 tuplet decline.

Tests `tools/omr/tests/test_staged_carried_meter_fix_2_136.py` (19). With the two logic edits reverted and the flag constant kept, 5 fail
(W1 settle, W1 default-OFF/typo, W1 changed-carry, W2 settle, a flagged eighth) and the other 14 pass (the OFF controls and the refusals, which
is what they must do on main). Kept refused with the flag ON: the 2.80 Contrabass shape (unexplained ink plus a lengthening), 2.97's refused
single (1 + 1.5 + x = 3 needs an eighth; the stem has no flag or beam), two different landings, a tuplet marker, a decided neighbour never
overturned, an ABSTAINED / absent / other-staff owner, a head boxed twice, a head the neighbour staff also boxed.

### 2.136-2b. What it settles on the saved records (in process, `probe/step2_2_136.py`)

The 20261014-night records, loaded once each via `record_io.load_record`, GATHER rows rebuilt and the record's OWN verdicts inserted as written,
frozen (step 1's way: not a re-decide, so no tree drift). For every cell the rule's own function ran with the flag OFF and with it ON; the ON
proposals were then admitted through INFER's own `_admit` (419 + 40 admitted, 0 skipped). Every admitted verdict is `infer:collapse_narrowed_by_bar`,
`inferred: true`, two candidates carried; each shorter-than-quarter value (Brahms 7 eighths, 1 dotted eighth and 2 sixteenths, Litolff 6 eighths and 2
sixteenths) carries eighth evidence (`beam_levels_certain/possible`, `beam_joined_to_stem`, `flag_read_on_stem`); no bare stem was shortened.

| | cells with a narrowed head | OFF: bars released / notes settled | ON: bars released / notes settled |
|---|--:|--:|--:|
| Litolff mvt 1 | 210 | 0 / 0 | **19 / 40** |
| Brahms 1 mvt 1 | 1,168 | 0 / 0 | **196 / 419** |

"Released" = every narrowed head of the bar settled (on both records every bar the rule settled at all was settled whole). OFF settles nothing:
the record's tree already ran the rule and these bars are the ones it declined. Changed-from-OFF: 0 (the fix only adds).
- Brahms values (value, beam levels): dotted quarter 267, quarter 142, eighth 7, dotted eighth 1, sixteenth 2. Freed from `meter_not_from_the_print`
  411 notes (W1), from `heads_not_this_staffs_own` 8 (W2). The OFF decline `meter_not_from_the_print` falls from 656 bars to 8; `heads_not_this_staffs_own` 10 to 16.
- Litolff values: quarter 32, eighth 6, sixteenth 2; all 40 freed from `heads_not_this_staffs_own` (W2 only, no carried segment change on that plate).
  Sean has seen NO Litolff bar under W2: that is the unproven half (tiles 6, 9, 10 below).
- This is wider than step 1's 46 Brahms bars: step 1 counted only the 179 evidenced N bars of 2.134; the rule also settles single-head bars and
  every other narrowed bar the carried meter had hidden. A count of what the code writes, not a claim that it is right.

Sean's 10 refused bars (`probe/summarise_step2_2_136.py`): **8 of 10 settle, each to exactly his values** (tiles 1, 2, 5, 6, 7, 9, 11, 12:
`4`+`dot4` or `4`+`4`). Tiles 8 and 10 stay REFUSED with the flag ON (their missed-rest ink witness reads unexplained ink and the lengthening
needs it clear); Sean's values on them agree with the unbeamed landing, so refusing them is safe and costs two settlements, not a wrong value.
**Control tile 4** (Brahms p18, two decided eighths that are sixteenths) is NOT changed: its heads are DECIDED, not narrowed, so the rule has no
member there (no row, 0 admitted verdicts on its glyphs); the wrong decided value is the beam-level readers' (2.126 family), not this rule's.
Control tile 3 is likewise untouched.

### 2.136-2c. `judged score ... --doc brahms`, OFF versus ON

Run on a small stand-in record (`probe/judged_overlay_2_136.py`: the record's own observations and verdicts for every subject the judged index
names, ON = plus the 7 admitted verdicts on judged subjects, each superseding its prior). Control: the OFF stand-in scores 70 right / 10 wrong /
18 narrowed / 1 abstained, the same as step 1's score on the full 6.8 GB record (`out/2.136/judged-brah.txt`).

| | right | wrong | narrowed | abstained |
|---|--:|--:|--:|--:|
| OFF | 70 | 10 | 18 | 1 |
| ON | **75** | 10 | 13 | 1 |

5 narrowed items become right (2.81-review control_2, tile_13, tile_17, tile_19, tile_28), 0 right lost, 0 new wrong. (Index not rebuilt: it
does not yet hold step 1's 12 tiles.) Outputs `out/2.136-step2/` (`*.json`, `*.new_verdicts.json`, `summary.txt`, `judged-brah.{off,on}.txt`).

### 2.136-2d. Blind tiles for Sean (`out/print/2.136-step2-review/`, 12 tiles, key hidden)

Cut the 2.134/2.136 way (600 dpi, 900 px, big tile number, RED corners = the bar, BLUE corners = each note asked about, nothing of ours drawn),
script `probe/tiles_step2_2_136.py`. 10 bars the flag settles that Sean has NOT seen (excluded: every cell of 2.136-review): 7 Brahms (4 freed by
W1, 3 by W2) and 3 Litolff (W2), spread over pages; 2 controls (two decided eighths, two decided quarters, Brahms). Blue boxes are 1 to 3 notes
a tile, so the question asks for each note left to right and allows a sixteenth. The key is `out/2.136-step2/tiles-key.json` (what the fix
writes, which fault freed the bar, the controls' readings), NOT beside the tiles. Frame control as in 2.136 (staff lines >= 2x the gap ink AND
the half-space-shifted test must fail): three candidates were refused by it and replaced. Shuffled (seed 21362). Not judged by the lane (rule 7).
Two tiles carry sixteenths the fix would settle (Brahms tile 2, Litolff tile 6) and two carry an eighth with evidence (Brahms 1, Litolff 10): the
evidence-backed shortening is the part step 1 could not test. Tiles 1 and 6 are crowded (a chord on ledger lines; a narrow Litolff bar).

### 2.136-2e. Limits

Brahms Breitkopf and Beethoven Litolff, mvt 1 each, one night's records; not a re-decide of the whole pipeline. W1 is evidenced on Brahms only (its
carried 6/8 after a 9/8 system); W2 is evidenced on Brahms by step 1's 12 tiles but on Litolff by nothing the print has shown. The owner verdicts W2
trusts are ADJUDICATE's, and `judged score` has no item on a ledger owner. The flag stays OFF until Sean has seen these tiles. Fast tier
`pytest -m "not slow" tools/omr/tests`: 8069 passed, 12 skipped, 2 xfailed; `staged.check` TOTAL open = 192.

### 2.136-2f. Sean's answers (2026-10-15)

Recorded in `out/print/2.136-step2-review/answers.json` (values compared as multisets against `tiles-key.json`). Brahms settled bars 7/7 right (tiles 1, 2,
3, 4, 5, 7, 12; W1 4/4, W2 3/3). Controls 8 and 11 right (2/2). Litolff settled bars 1/3 (tile 9 right; tiles 6 and 10 wrong); all three Litolff tiles
are W2. W1 is right on every tile where it fired (4/4 here, and 8 of Sean's earlier 10). W2 is 3/3 on Brahms but 1/3 on Litolff. Tile 6 is a bar sum
landing on the WRONG combination: we settled 16, 16, 4 and Sean reads 8, 8, 8, so the sum inherits a misread elsewhere in the bar. Tile 10 counted a
whole rest as a notehead and summed two voices as one: we settled quarter + eighth, Sean reads a whole rest and a quarter in different voices. The two
Litolff failures say W2 should not ship ON until those causes are understood; W1 has no failure on the print so far (Brahms only).

## 2.141 -- why W2 (`ledger_owner_aware`) failed on Litolff tiles 6 and 10 (2026-10-15, DIAGNOSIS ONLY)

PATH: STAGED INFER (`inferences.solve_bare_stem_bar(any_reason=True)`) reading ADJUDICATE's verdicts. No product code, no flag, no gather.
`lane-2.141-litolff-w2` off `lane-2.136-step2`. Records: the 20261014-night Litolff and Brahms records, loaded once via `record_io.load_record`,
verdicts inserted as written (probes `probe/causes_2_141.py`, `geom_2_141.py`, `tiles_2_141.py`; outputs `out/2.141/`). Control: the probe's as-written W2
settlements reproduce tiles 6 and 10 exactly, so the instrument sees the failures.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: ASSUMED that a whole rest printed under the staff in a bar whose notes stand above is the lower voice's
bar rest (Litolff displaces it; 3 bars; Sean's tile 10 answer agrees), and that one beam over eighths is one level. FALSIFIED BY Sean reading those bars otherwise.
NOT CONFIRMED: the fixes in 2.141d; nothing was built.

### 2.141a. Tile 6 (Litolff p5 sys0 staff0 cell6)

Human reading (600 dpi crop, nothing drawn): an eighth rest, then three beamed eighths, on one staff written as two voices in unison (stems up with the beam over
the heads, stems down with a beam under them); the voices agree. Sean: 8, 8, 8.

Record (cell 5/0/0/6): events rest8th (g6, decided 0.5), g1, g4 (g5 a refused duplicate box), g0; one voice. g1 and g4 narrowed {eighth 1 level, sixteenth 2 levels}
`beams_ambiguous`; g0 narrowed {quarter 0, sixteenth 2} `beam_certain_not_joined`. The bar is 2.0 = 0.5 + 1.5 and **8,8,8 adds up as well as 16,16,4**: no missed event,
no extra box, no dot, rest right, meter right. The rule landed on 16,16,4 only because g0 has NO eighth candidate, so the single landing is wrong. The error is in the
candidates; the bar sum can only inherit it.

Why the sixteenth candidates existed (beam-level reader, `rhythm.py` duration, the 2.75 per-voice path): g1/g4 `beam_voices` up [1,1] (the top beam) but **down [2,2]**.
The down count is two strokes: the real bottom beam (stroke 079966, 0.65 space thick) AND stroke 079965, a long stroke that on the page is the LEDGER LINE the heads stand on
(page x 1372-1452, y 448-454; its right end is the short tail past the third head), counted as a second level because strokes are counted by column. The thickness
measure (`Q.BEAM_STROKE_INK`: top beam 0.59, bottom 0.65, the ledger stroke 0.82 merged with the heads) is read and never checked against the level count.
g0 failed differently: `Q.HEAD_STEM_REACH` read `down` only (`up_ext` -0.02; the up stem stands at the head's right edge) while the CV head_stem verdict says a stem each way
(`unison_two_voices`). `_own_stem_side` takes the ruler's single direction, so side=down, the top beam is "far side", the down strokes count: certain 2, two certain
conflicts, candidates {0, 2}. Level 1, the truth, is not among them.

For 2.140 (a double beam read as one): this is the mirror and the same missing check. Levels are a count of strokes by column; nothing asks whether a stroke is a beam
(about one beam thick, a stem ends at it, not the ledger line under the head) or whether a thick stroke is two beams (about twice the thickness, 0.58-0.65 space for one here).

### 2.141b. Tile 10 (Litolff p3 sys1 staff0 cell8): two causes in the sum's inputs

Human reading: two quarters above the staff (stems up, a slur arriving on the first stem) and under the bottom line a whole rest, the lower voice's bar rest. Sean: whole rest, 4.

Record: g2 DECIDED eighth (0.5, 1 level), g1 narrowed {quarter, eighth}, g4 narrowed {half, quarter, whole}, g9 `restWhole` ABSTAINED. Bar 2/4.
1. **The whole rest stood as a notehead (cause W).** The detector boxed it twice: `restWhole` g9 and `noteheadBlackInSpace` g4, same ink. `notehead_is_a_whole_rest` on g4 is
   DECIDED true (`shape_and_position_agree`, witness the neighbouring bar). EXPORT honours it (`ink_is_a_whole_rest` refuses the box) and `size_measure_rest` honours it, but only
   when the bar's single decided rest has a decided twin; `consequences._left_the_bar` (`_LEAVES_THE_BAR` = not-a-notehead, not-a-rest) does not know it, so INFER's sum counts g4.
   g9 is ABSTAINED (`rest_stands_where_no_rest_hangs`: the displaced position is on neither the whole nor the half convention), which also defeats the twin test.
2. **A wrong DECIDED neighbour (cause S).** g2 is DECIDED an eighth from `yolo_kept 1, cv_beams 0`: the detector's `beam` box g7 is the slur's end (a thin arc);
   `beam_stroke_ink` and `stem` were declined, no ink witness read it, and no decided arc covers it. g1's eighth candidate comes from the same box.
The only landing is 0.5 + 1.0 (g4) + 0.5 (g1) = 2.0. "Two voices as one": `adjudicate_voices` says one voice (the second voice is a stemless rest it cannot see), and the sum never reads `Q.VOICES`.

Why W2 exposed it: main declined this bar (`heads_not_this_staffs_own`) because g1/g2 stand above the staff. They ARE this staff's (ledger lines name the owner), so W2's
stand-down was right, and the refusal had been hiding two older faults in the bar's other inputs. In-process what-if (`_left_the_bar` also taking a decided whole-rest-ink box out):
tile 10 becomes `bar_does_not_add_up`, a refusal, the safe answer.

### 2.141c. How many of W2's bars share each cause (record test, `out/2.141/causes-*.json`)

W = a sum member with DECIDED `notehead_is_a_whole_rest` true. U = an ABSTAINED standing duration in the bar (an element nobody sized; the sum skips it as zero time).
S = a DECIDED note whose only beam evidence is a detector box (`cv_beams 0`, `yolo_kept >= 1`). T6 = a member whose CV `head_stem` verdict says a stem each way and whose
beam levels were counted one-sided, or per voice with unequal counts.

| test | Litolff (19 W2 bars) | Brahms (4 W2 bars) | control: Sean's right bars (Brahms 1, 7, 12; Litolff 9) |
|---|---|---|---|
| W whole-rest ink counted | 1 (tile 10) | 0 | 0 of 4 flagged: passes |
| U abstained element skipped | 3 (tile 10, p11 cells 0/0/10 and 0/0/16) | 0 | 0 of 4: passes |
| T6 stem each way, levels one-sided or unequal | 3 (tile 6, p5 0/0/1, p7 0/3/12) | 0 | 0 of 4: passes |
| S yolo-only decided beam | 1 (tile 10) | 2 | flags Brahms tile 12 (right): FAILS, dropped |
| T6 first draft (reach ruler 'both', any stem each way) | 8 | 2 | flags Brahms 1 and 7 (right): FAILS, replaced by the CV head_stem condition |

6 of Litolff's 19 bars share an accepted cause (tile 10 W+U, tile 6 T6, two more U, two more T6); 0 of Brahms' 4. No cause covers more than 3 of the 19. 13 Litolff and 4 Brahms
bars are flagged by nothing; Sean saw one of those (Litolff 9, right). Crops: the two other U bars (p11 0/0/10, 0/0/16) print two quarters over the same displaced whole
rest and the record settles quarter, quarter: right, by luck of the unbeamed candidate, so U alone does not predict failure. The two other T6 bars are tiles, unjudged.

### 2.141d. Fixes of the CAUSE (proposed, not built; each general, none narrows W2 to a publisher)

1. **Count a beam level only from a stroke that is a beam** (`rhythm.py` duration; evidence from the page raster and head/stem geometry, a different source from the strokes).
   A stroke the head's own stem passes through, or lying under a ledger-line head and as thick as the ledger line, is not a level; a stroke about twice one beam is two.
   Falsifier: any bar Sean has judged right whose value changes. Also gives 2.140 its direction.
2. **`_own_stem_side` must not take the ruler's single direction when the CV head_stem verdict has a stem each way** (ADJUDICATE). Falsifier: a head with a CV stem each way
   whose one-sided ruler reading was right on a printed page.
3. **A decided `notehead_is_a_whole_rest` box leaves the bar for every consumer** (EVALUATE `_left_the_bar`, the verdict EXPORT already honours), and an ABSTAINED standing duration
   makes INFER's sum decline (rule 8: "cannot tell" is not zero time). Falsifier: a decided-true whole-rest-ink box that is a real note (none seen; 30 Litolff twins in 2.98).
   Cost: the two U bars above stop settling (they were right).
4. **A detector `beam` box with no CV stroke and no ink reading may narrow to an eighth but not DECIDE one.** Its test fails its control (Brahms tile 12), so it needs tiles first.

W2 itself stays OFF until 1-3 land: it is right in principle, and the refusal had been protecting these bars.

### 2.141e. Blind tiles for Sean (`out/print/2.141-review/`, 6 tiles, key hidden at `out/2.141/tiles-key.json`)

The 2.136 tile (RED corners = the bar, BLUE corners = each note W2 settles, nothing of ours drawn): 2 more T6 bars, 2 more U bars, 2 unflagged bars (stem each way by the ruler only) as
controls. Only 4 other bars share an accepted cause, so 4 shared-cause tiles, not 6 to 8. Not judged by the lane. The question also asks what a second voice holds.

### 2.141f. Limits

Litolff mvt 1 and Brahms mvt 1, one night's records; n = 3 per cause. The ledger-line reading of stroke 079965 is box geometry mapped to page pixels, not an ink test. W is Litolff-only
evidence. Every count is of what the record holds, not of what is right.

## 2.141h -- the three cause fixes, measured PARTIALLY (crash recovery, 2026-10-15)

CONVENTION ASSUMED: a beam level is a stroke at the stem's beam position (fix 1); both unison heads on one stem take the
stem's side (fix 2); whole-rest ink beside a bar's heads means the head left the bar (fix 3) -- Sean's 2.136 answers
(`out/print/2.136-step2-review/answers.json`, tile 6 = 8,8,8; tile 10 = whole rest + quarter). WHAT WOULD FALSIFY IT: a
judged-right bar that turns wrong under a flag, or a blind tile where Sean reads a changed note differently.
NOT CONFIRMED: fixes 2 and 3 and the all-ON arm are NOT measured; Brahms is NOT measured; no tiles were cut; the
coordinator stopped the whole-movement runs (Sean's rule: small runs by day, big runs overnight).

PATH: STAGED (ADJUDICATE rhythm / EVALUATE / INFER), saved 20261014-night records re-decided by
`probe/arm_2_141h.py` (GATHER rows are the record's; a GATHER change is invisible). Every arm has
OMR_INFER_CARRIED_METER_FIX=1 and OMR_INFER_LEDGER_OWNER_HEADS=1 (W2).

**The control, and why it shows 40.** Litolff `base` (W2 only, `--control`): 14,357 of 14,397 standing duration verdicts
reproduce the record, 40 differ, 0 extra; all 40 are `narrowed` in the record and `decided` in the replay by
`infer:collapse_narrowed_by_bar`. The record's provenance has no W2 flag (`env_overrides` = Surya keep-alive only; both
flags were OFF when the record was made; main has since turned CARRIED_METER_FIX ON by default), and §2.136 step 2 above counts exactly 40 Litolff values freed by W2 alone.
So the 40 are W2 itself, not harness drift. A W2-OFF whole-record control (expected 14,397/14,397) is NOT run.
(1 GB arm records kept in library/_shared-records/2.141h-arms/, not in git. Source: `out/2.141h/lit.log`, `arms/lit-base/durations.json`.)

**A restricted re-decide does not work.** `arm_2_141h.py --staves` (keep the glyph rows of the named systems only) fails
the control: 343 of 6,404 differ with W2 ON, 335 with W2 OFF (whole-record control: 40). ADJUDICATE reads document-wide
calibration from the glyph rows of other systems, so the small run is not the large run and no small-run number can be
trusted. The flag is left in the probe, labelled; it is not a valid shortcut. A valid small run needs `pipeline.decide`
to decide only chosen systems over the FULL gather, which is a code change.

**Fix 1 (`OMR_BEAM_LEVEL_STROKE_IS_A_BEAM`), Litolff, whole movement, vs base:** 13 cells, 22 standing verdicts change
state, 15 DECIDED values change (10 sixteenth->eighth, 3 eighth->quarter, 1 thirty-second->eighth, 1 quarter->eighth),
4 decided->narrowed, 3 narrowed->decided. Key bars: 2.136 tile 6 (5,0,0,6) goes from 16,16,4 to 0.5 on every note =
Sean's 8,8,8 (right). 2.136 tile 10, tile 9, and Sean's 2.141 tiles 1-6 are unchanged (so no judged-right bar moves).
`judged score` base vs f1 (litolff): identical totals (109/11/3/1/13/99), so no judged bar changes either way. The 12
other changed cells are not judged and no blind tile has been cut for them: 4,1,7,5 and 4,1,8,11 and 7,0,7,8 are
sixteenth->eighth and are the first to show Sean; 13,0,10,5, 14,0,10,0 and 14,1,8,4 are eighth->quarter.
(Source: `out/2.141h/summary-lit.json`, `judged-lit-*.txt`.)

Not run: fix 2, fix 3, all-ON (Litolff); every Brahms arm. Tile 10 and the expected fix-3 refusals (Litolff p11 cells
0/0/10 and 0/0/16) are therefore unmeasured. Run at the next overnight: `out/2.141h/run_arms.sh` (resumable, skips
finished arms), then `probe/summarise_2_141h.py` and `probe/tiles_2_141h.py`.

### 2.141g. Sean's answers (2026-10-15) -- 6/6 agree with W2

Raw: "1-4 quarter notes 5 and 6 8th notes". Key (`out/2.141/tiles-key.json`, `settled_beats_beamlevels`): W2 settled every note in tiles 1-4 as quarters and in tiles 5-6 as eighths.

| tiles | role | Sean | W2 settled | agree |
|---|---|---|---|---|
| 1, 3 | U (shared cause) | quarters | quarters | 2/2 |
| 5, 6 | T6 (shared cause) | eighths | eighths | 2/2 |
| 2, 4 | unflagged controls | quarters | quarters | 2/2 |

W2's settlements on the 4 shared-cause bars (2 U, 2 T6) were right, so the shared causes did not make these bars wrong; the controls also agree. Only 2.136 tiles 6 and 10 are known wrong. n = 4 shared-cause bars, one publisher (Litolff), so this does not show the causes harmless in general. W2 stays OFF until fixes 1-3 of 2.141d land and pass tiles on both publishers. Recorded in `out/print/2.141-review/answers.json` and `benchmarks/acceptance/judged-tiles.json`.
