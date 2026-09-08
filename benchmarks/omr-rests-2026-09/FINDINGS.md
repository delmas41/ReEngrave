# Step 3 — rests

⚠️⚠️ **§1–§5 WERE WRITTEN FIRST AND TWO OF THEIR CLAIMS ARE WRONG.** The
assessability figure in §1 (9.8%, 2 of 11 rows) came from invoking the ledger
without its part-join input, and §3/§5's cause (`_measure_rest_beats` fed
`None`) is not the mechanism — that function is never called for these bars.
**Read §7 onward.** The sections are kept rather than rewritten because the
corrections are the finding. ⚠️ **And §11 is wrong too — see §13**: the
missing meters are a fixture artefact (the gate transcribes one page at a
time, so the meter carry has no previous page), and the §9 fix is worth MORE
in production than the benchmark can show.

## The first look, and 80% of it is one mechanism

Step 3 as the handoff sets it: *"476 rests carry a wrong duration against 235
notes — 55% of the duration mass, and every duration analysis in this repo is
note-level and therefore blind to the larger half. Nobody has looked."*

Instrument: `tools/omr/symbol_ledger`, over the 11 committed scan-gate
pred/truth MusicXML pairs already on disk (no re-transcription).

---

## 1. ⚠️ STEP 3 IS BLOCKED BY STEP 4, AND THE NUMBER SAYS SO

Of **4,239 rest rows, only 416 are assessable — 9.8%** — and they come from
**2 of 11 rows, both Dvořák**. On the other nine the part join fails
(`part_join: unresolved`), so every symbol is `uncorresponded` with reason
`part_unresolved` and nothing can be compared to anything.

That is Step 4's bucket (`entire staff` / no part correspondence) sitting
**upstream** of Step 3, exactly as the handoff predicts: *"8 of 20 rows have NO
part correspondence — 51% of symbols. Larger than everything about notes, and
upstream of all of it."*

⚠️ **So every figure below is TWO DVOŘÁK PAGES.** It is not a corpus result and
must not be quoted as one.

## 2. The handoff's ratio holds on this slice

On the assessable rows, attribute errors split **rests 174 / notes 123**. Rests
are the larger half here too — a different slice from the one that produced the
476/235 figure, agreeing in direction.

## 3. ⚠️ 139 of 173 rest duration errors are ONE mechanism

|  ours (type, ql) | truth (type, ql) | n |
|---|---|--:|
| **`whole`, 4.0** | **`None`, 2.0** | **139** |
| `32nd`, 0.125 | `16th`, 0.4375 | 8 |
| `half`, 3.0 | `None`, 2.0 | 5 |
| everything else | | ≤3 each |

**We emit a whole-measure rest as a literal whole note — 4.0 quarter-lengths —
regardless of the meter.** Dvořák 9 mvt 1 is in **4/8**, so a bar holds 2.0;
we write 4.0 and the bar comes out twice over-full.

⚠️ **THE SIZING CODE IS CORRECT AND IS SIMPLY NOT FED.**
`export._measure_rest_beats` computes `num * 4.0 / den` — 4/8 → 2.0 — and
`_dotted_duration_for_beats(2.0)` returns `('half', 0)`. The fault is the
argument: both call sites resolve `m_time = measure.get("time_signature") or
<staff/part fallback>`, and when neither carries a meter the value is `None`,
where `_measure_rest_beats` falls back to **4.0 (a whole rest)** by documented
design. That fallback is right for an unknown meter and wrong here, because
the meter is NOT unknown.

⚠️⚠️ **THE FILE CONTRADICTS ITSELF, WITHIN ONE PART.** Measured on every part
of the Dvořák p5 export:

    part P1: divisions=8  time=4/8  bar_ql=2.0  rests=7  whole-rests-too-long=5
    part P2: divisions=8  time=4/8  bar_ql=2.0  rests=9  whole-rests-too-long=5
    part P3: divisions=8  time=4/8  bar_ql=2.0  rests=9  whole-rests-too-long=6

The exporter writes `<time>4/8</time>` into the part's own `<attributes>` and
then writes a 4.0-quarter rest into that part's 2.0-quarter bars. **It had the
meter in hand and did not use it** — the same shape as this project's recurring
detected-then-dropped family, one level down: *known-then-not-consulted*.

Secondary, same rows: truth marks these `<rest measure="yes"/>` and we emit a
plain `<rest/>`.

## 4. ⚠️ I NEARLY REPORTED THIS EXACTLY INVERTED

The ledger emits a row per symbol **on both sides**, and all 174 of these rows
are the **`truth`** side — so `attrs` is TRUTH and `partner_attrs` is OURS. The
first cut of this analysis read `attrs` as ours and produced the table
backwards, concluding that *we* omitted `<type>` and *truth* said `whole`. The
raw XML is what caught it: our rest carries `<type>whole</type>` and truth's
carries none.

**Check `side` before reading `attrs` on any ledger row.** Nothing in the
column names says which way round they are.

## 5. What to do next, and how to price it

Feed the meter to the empty-measure path — the sizing function already does the
arithmetic. ⚠️ **Do not ship it unmeasured**, and note the pricing problem
before starting: the scan gate can assess only 9.8% of its own rest rows, so it
is a poor instrument for this. The engraved benchmark pairs 1:1 by construction
and can see all of them; that is where the A/B belongs, with the scan gate as a
secondary check.

⚠️ And the deeper question this raises is Step 4's, not Step 3's: **why does the
staff carry no `time_signature` on these pages** when the page-level reader
found 4/8 and wrote it into `<attributes>`?

## 6. Reproduce

```bash
M=benchmarks/omr-scan-e2e-2026-09/fixtures
for t in "$M"/*.truth.musicxml; do b=$(basename "$t" .truth.musicxml)
  python3 -m tools.omr.symbol_ledger \
      "$M/$b.restamp-composed.omr.musicxml" "$t" --json "led/$b.json"; done
python3 benchmarks/omr-rests-2026-09/probe_rest_durations.py led/
```

---

# Step 3, second pass (2026-09-08 later): the diagnosis above is WRONG, and the fix is a convention

Everything above §5 stands as a description of the symptom. §5's *cause* does
not, and neither does §1's assessability figure. Both are corrected here, with
what replaced them.

## 7. ⚠️⚠️ `_measure_rest_beats` IS NOT "correct and simply not fed". IT IS NEVER REACHED.

§3 says the fault is that both call sites resolve `m_time` to `None`. Checked
against the transcription rather than the code path:

    dvorak-sym9-mvt1-405834-p5.restamp-composed.omr.json
      staff time_signature   {'numerator': 4, 'denominator': 8, 'raw': '4/8'}
      measure 0..3 time_sig  {'numerator': 4, 'denominator': 8, 'raw': '4/8'}
      measure 0 detections   ['clefG','timeSig8','flag16thUp','timeSig4','restWhole','staff']

**Every measure of that page carries its meter**, which is exactly why
`<time>4/8</time>` reaches `<attributes>` — the exporter reads the same dict
one line above. `_measure_rest_beats` is not being fed `None`; it is not
CALLED. The bar holds a detected `restWhole`, so `events` is non-empty and the
empty-measure branch — the only caller — is never taken. The rest is written
by `_mxl_voice_events` at the glyph's nominal value.

**So the fault is the CONVENTION, not the plumbing.** ⚠️ A whole-rest glyph is
not four quarters of silence. An engraver fills an otherwise silent bar with
one centred whole rest **whatever the meter**, and the glyph stands for the
bar; the reference files say so with `<rest measure="yes"/>` and no `<type>`
at all. We were reading the glyph correctly and applying the wrong rule to it.

The self-contradiction §3 records is real and this explains it: the same
measure dict supplies `<time>4/8</time>` to the attributes and a whole-rest
glyph to the note stream, and only one of the two consumers knew about the
other.

## 8. Measured properly: 90.3% is the convention, on 7 rows not 2

`probe_measure_rests.py` — which builds the ledger the way `run_ledger.py`
does, from `works.json`, and asks the question the confusion table cannot:
**was our rest the only event in its bar?**

    7 rows joined (not 2)   rest rows 1826   ASSESSABLE 1817 (99.5%)

| ours (type, ql) | truth (type, ql) | n | our bar held ONLY this rest |
|---|---|--:|--:|
| **`whole`, 4.0** | **`None`, 2.0** | **543** | **530 (98%)** |
| `whole`, 4.0 | `quarter`, 1.0 | 10 | 10 (100%) |
| `whole`, 4.0 | `None`, 3.0 | 9 | 9 (100%) |
| `whole`, 4.0 | `eighth`, 0.5 | 10 | 4 |
| `half`, 3.0 | `None`, 2.0 | 5 | 5 (100%) |
| `32nd`, 0.125 | `16th`, 0.4375 | 8 | 0 |

**558 of 618 wrong rest durations — 90.3% — are a bar of ours holding exactly
one rest and nothing else**, and `truth type = None` is the measure-rest
signature.

⚠️ **The first cut of this table said 55%, and the error was a FRAME error of
the kind the last session paid for.** On a `truth`-side ledger row
`part_index` is the **truth** part index, not ours — a condensed staff makes
those different numbers — and mapping it straight onto our part list said a
Beethoven bar holding no rest at all held one. Same shape as
`clef_located` (cell frame) versus `staff_extent` (page frame). Fixed, with
the reason written at the call site.

## 9. The fix, and ⚠️ THE GLYPH IS PART OF THE RULE

`export._is_lone_measure_rest` + routing both MusicXML emitters and both
LilyPond branches through the existing `_mxl_empty_measure` /
`_lily_measure_rest`, which already do the arithmetic. `_mxl_note` gains
`measure_rest`, emitting `<rest measure="yes"/>` and **no `<type>`/`<dot>`** —
a measure rest names no note value.

⚠️ `measure="yes"` is withheld where the meter is UNKNOWN. `_measure_rest_beats`
falls back to 4.0 there, and asserting "this bar is exactly 4.0 long" on a page
whose meter we never read would be a guess dressed as a fact.

⚠️⚠️ **THE FIRST CUT ACCEPTED ANY LONE REST AND COST 34 EDITS ON
`brahms-sym4-mvt1`** (pooled engraved 0.1214 → 0.1225). It was turning bars
holding a single detected **quarter** rest into full-bar rests — 1.0 quarters
becoming 4.0. Those bars are not silent; they are bars we read one symbol of.
A measure rest is the **whole-rest glyph** in every meter, so a lone quarter or
eighth rest is a partial reading and inflating it is a guess. Restricting to
`duration_type == "whole"`, no dots, keeps 553 of the 558 rows and gives back
every engraved edit.

## 10. ⚠️ PRICED ON THE ENGRAVED BENCHMARK, WHICH CANNOT SEE IT — AND THE CONTROL PROVES THAT

Export-only A/B over the eleven stored engraved transcriptions
(`benchmarks/omr-hairpins-2026-09/score_export_arm.py`, so the detector never
re-runs):

| | OMR-NED | edits |
|---|--:|--:|
| before | 0.12138 | 2532 |
| after | **0.12138** | **2532** |

**Identical to the edit, in every one of 23 categories.** ⚠️ A zero is a
suspect, so the positive control: the change reaches **all eleven** exported
files — 953 measure rests where there were none — and **six works have rest
`<duration>` values that MOVED** (beethoven 3: 188 lines, tchaikovsky 4: 246,
beethoven 5: 178, tchaikovsky 6: 72, brahms 1: 36, bruckner 5 and mahler 5: 2).
Beethoven 3 is in 3/4: a whole rest at 4.0 became 3.0, matching its truth.
**musicdiff charged nothing either way.**

That is §2 of the handoff arriving on the real corpus rather than in a mutation
matrix: *"musicdiff can score ZERO for a real duration error — blind, not
merely imprecise."*

**Scored with the ledger, on the same eleven engraved works** (they pair 1:1 by
construction, so the join is positional and every rest row is assessable):

| | before | after |
|---|--:|--:|
| **`rest.type`** | **933** | **10** |
| **`rest.duration_ql`** | **328** | **4** |
| `matched_exact` | 3,154 | **4,077** |
| `matched_attribute_error` | 1,039 | 116 |
| `note.pitch` / `note.duration_ql` / `note.type` | 26 / 25 / 22 | **26 / 25 / 22** |
| `clef.clef` / `dynamic.text` / `key.fifths` / `articulation.mark` / `time.beats` | 7 / 5 / 5 / 5 / 1 | **identical** |
| `uncorresponded` / `ambiguous` / `missing` / `spurious` | 674 / 356 / 293 / 169 | **identical** |

**1,251 attribute errors corrected, nothing else moved by a single row, and
OMR-NED did not notice.**

Scan gate, secondary, the 7 rows whose part join resolves:

| | before | after |
|---|--:|--:|
| `rest.type` | 600 | **277** |
| `rest.duration_ql` | 576 | **354** |
| `rest.dots` | 17 | 12 |
| `matched_exact` | 1,470 | **1,717** |
| every non-rest family | — | **identical** |

⚠️ **AND THE SCAN GATE'S OMR-NED IS ALSO IDENTICAL — 34,963 edits, all
eleven rows unchanged to the edit.** So the metric is blind to this on BOTH
families, engraved and scanned, while the ledger records 1,251 + 545 corrected
attribute errors. Direction still comes from an A/B; this is what "attribution
is VOID" costs when the change is a duration.

Controls on the new output: `self_check_identity` and the music21
cross-parser are clean on **22 of 22** re-exported files, so the absent
`<type>` is not a parse problem.

## 11. ⚠️ THE RESIDUAL IS A METER PROBLEM, AND IT IS THE NEXT LEVER

354 wrong rest durations survive on the scan gate. **435 lone whole rests were
NOT converted, and 405 of them (93%) sit in an exported part that carries no
`<time>` ANYWHERE.** Control: **only 86 of 159 exported parts carry a `<time>`
at all.**

So the handoff's closing question — *"why does the staff carry no
`time_signature`?"* — has a real answer, and it is not the one it assumed.
On Dvořák p5 the staff DOES carry it (§7). On Beethoven 5 p2, Mahler 5 p2/p3
and Brahms 1 p2, **46% of the parts we emit have no meter at all**, so
`_measure_rest_beats` legitimately falls back to 4.0 and no rest rule can
help. That is a meter-reading problem — `time_signature_locator`, the vote,
and meter carry across systems — and it is where the rest of Step 3's mass
lives.

## 12. Reproduce

```bash
python3 benchmarks/omr-rests-2026-09/probe_measure_rests.py \
    --pairs benchmarks/omr-part-join-2026-09/pairs-restamp-composed.json
OMRNED_PYTHON=/…/.venv-omrned/bin/python \
python3 benchmarks/omr-hairpins-2026-09/score_export_arm.py --label after
```

---

## 13. ⚠️⚠️ §11 IS WRONG: "only 86 of 159 parts carry a `<time>`" IS A FIXTURE ARTEFACT

§11 concluded that the residual is a meter-READING gap and named it the next
lever. Checked before acting on it, and it is not. Broken out per row instead
of pooled:

| row | parts with `<time>` | staves with a meter | source |
|---|--:|--:|---|
| beethoven p1 (both scans) | **12/12** | 12/12 | `header_reader` |
| brahms p1 | **14/14** | 14/14 | `header_reader` |
| dvorak p5 | **15/15** | 15/15 | — |
| beethoven 984073 **p2** | 2/11 | **2/22** | — |
| beethoven 575951 **p2** | 1/11 | **0/22** | — |
| mahler **p3** | 2/13 | 1/13 | — |
| dvorak **p6** | 5/15 | 2/15 | — |

**Every movement-OPENING page reads its meter on 100% of staves. Every
CONTINUATION page reads almost none** — which is correct: a time signature is
printed at the start of a movement and nowhere else. CLAUDE.md has recorded the
answer since 2026-08-31: `transcribe` carries the previous page's meter forward
as `source="carried_from_previous_page"`.

⚠️ **The scan-gate fixtures are transcribed ONE PAGE AT A TIME, so a
continuation page has no previous page to carry from.** The pooled 86/159 is a
property of how the benchmark is cut.

### Measured, not argued: pages 1-2 of the same PDF in ONE `transcribe` call

    python3 -m tools.omr.transcribe <litolff-984073>.pdf --pages 1-2 \
        --no-direction-text --out carry-p1p2.json     # 65.5 s

| | single-page fixture | one two-page run |
|---|--:|--:|
| page 2 staves with a meter | **0 of 22** | **20 of 22**, `carried_from_previous_page` 2/4 |
| exported parts with `<time>` | 12 of 34 | **34 of 34** |
| lone whole rests sized **2.0** (the true 2/4 bar) | 0 | **218** |
| lone whole rests sized 4.0 | all of them | 37 |
| lone rests not converted | — | 2 (`quarter`, correctly refused) |

**The carry works and the fix is already in the tree.** So the meter lever
largely dissolves — and the corollary is the better half of this finding:
**the §9 rest fix is worth MORE in production than the benchmark can show.**
The web app runs `OMR_MAX_PAGES=5` (pages 0-4 in one call), so a continuation
page DOES get its meter there, the conversion fires, and **218 of 255 lone
whole rests (85%) come out at the printed bar length** where the one-page
fixture sized 100% of them at 4.0. The benchmark could not see the fix (§10)
and cannot see most of its reach either, for the same structural reason.

### ⚠️ What IS left is small, real, and differently shaped

The 37 rests still at 4.0 are not missing meters — they are **staves whose
meter reads 4/4 (and one 1/4) on a 2/4 movement**: 3 of 12 staves on p1 and 2
of 22 on p2, all `source: None`, i.e. neither the header reader nor the carry.
So the residual is a staff **disagreeing with its own system's majority** and
keeping the disagreement, which is what `rhythm.drop_uncorroborated_meter_changes`
and the half-the-staves page vote exist to prevent. **4 staves of 34, costing
37 wrongly-sized measure rests on two pages.** That is the next meter question,
and it is a vote/override question rather than a reading one.

### ⚠️ The standing hazard this exposes, worth more than the number

**The scan gate's one-page-per-row cut silently disables every mechanism that
spans pages.** The meter carry is one; anything else keyed on "the previous
page" is equally invisible to it, and will read as a pipeline gap. Check
whether a mechanism is page-spanning before pricing it on that corpus.

---

## 14. §13's residual, opened: THREE causes, one shipped and two parked

§13 left "4 staves of 34 reading 4/4 or 1/4 on a 2/4 movement" as the next
meter question. Opened, and it is not one question. Exact readings from the
two-page run:

    page 1, one system of 12 staves
      inferred_time_signature: 2/4, source detected_propagated, votes 9 of 12
        ('2/4', header_reader)  x7
        ('4/4', None)           x3     <- dissent, and it CORROBORATES ITSELF
        ('2/4', None)           x2
    page 2, system 1 of 11 staves
        ('2/4', carried_from_previous_page)  x9
        ('4/4', None)                       x1   <- a lone dissenter
        ('1/4', None)                       x1   <- not a meter at all

**The mechanism is one line.** `backfill_page_time_signatures` fills only
staves whose meter is *empty* — *"Genuine detected meters are never
overwritten"*, deliberately. So the page decides 2/4 by a 9-of-12 vote,
records it as `inferred_time_signature`, and a dissenting staff keeps its own
reading regardless.

### (a) SHIPPED — a meter the module's own predicate calls garbage

⚠️ **`_is_propagatable_meter` names `1/4` IN ITS OWN DOCSTRING** — *"Rejects
garbage that could survive upstream filtering (6/6, 6/66, 1/1, 1/4)"* — and it
was consulted only to decide who may VOTE, never whether a staff may KEEP a
reading. **The code knew and nothing asked it. Class C, again.**

Measured over 21 stored scan transcriptions: **4 of 227 staves and 45 of 2,538
measures carry a meter the predicate rejects, and every one is `1/4`** — on
Beethoven 5 / Litolff, Brahms 1 / Breitkopf, Mahler 5 / Peters and the two-page
run, i.e. three works and three publishers rather than one page's accident.

`rhythm._drop_implausible_meters` clears them before the back-fill, so the
page's decided meter takes over. ⚠️ Only READINGS are tested — re-testing this
module's own propagated output would be circular. ⚠️ **Clearing beats keeping
even when the page decides nothing**: `None` means "unknown", which the
exporter renders as no `<time>` and `_measure_rest_beats` treats as the
documented 4.0 fallback, whereas a kept `1/4` writes `<time>1/4</time>` into
the part and sizes its measure rests at ONE QUARTER — a confident wrong answer.
⚠️ **It cannot harm a polymetric page**: a page that genuinely prints different
meters per staff prints plausible ones. `test_rhythm_implausible_meter.py`, run
RED against two mutants.

### (b) PARKED — a lone plausible dissenter

Page 2's `4/4` staff is alone among nine, which is the exact shape of the
`OMR_KEYSIG_CORROBORATION` guard shipped the day before: *a meter is printed on
one bar of one system, on every staff of that system, so the BAR is the shared
fact.* The weak form — revert a reading no other staff of the system
corroborates — reaches it. **Not shipped here** because it is one staff and the
corpus that could price it is the same corpus §13 shows cannot see page-spanning
behaviour.

### (c) PARKED, and it needs the STRONGER claim — corroborated dissent

⚠️ **Page 1's three `4/4` staves CORROBORATE EACH OTHER**, so the weak guard in
(b) does not reach them and would be wrong to claim it did. Only *"the page's
decided meter overrides a staff-opening meter that contradicts it"* reaches
these, and that is a materially stronger rule with a real cost: it would
overwrite a genuinely polymetric staff. **Parked with the risk named rather
than shipped on three staves of one page.**

⚠️ The split (b)/(c) is the finding, not the count: **a corroboration guard and
a vote-override are different rules with different risks, and the four staves
that looked like one bucket need one each.** Same shape as §Step-4's four
causes, one level down.

### ⚠️ Measured end to end, and the 37 rests belong to (b) and (c) — NOT to (a)

Re-transcribed the same two pages with (a) in the tree. Attributing every
wrongly-sized measure rest to the part that holds it:

| part | its meter | 4.0-quarter rests | case |
|---|---|--:|---|
| Trumpet (p1) | 4/4 | 13 | **(c)** corroborated dissent |
| Contrabass (p1) | 4/4 | 12 | **(c)** |
| Viola (p1) | 4/4 | 5 | **(c)** |
| Flute (p2) | 4/4 | 7 | **(b)** lone dissenter |
| | | **37** | |

**Not one of the 37 belongs to the `1/4` staff**, so the shipped guard (a)
fixes **zero** of them: 30 need the vote-override (c) and 7 need the
corroboration guard (b). An earlier draft of this section implied otherwise by
quoting the 37 under all three cases together.

⚠️ **(a)'s payoff arrived through a channel I was not measuring.** Its 16
cleared records on page 2 change the export by 24 lines, and only one of those
is the `<time>2/4</time>` the guard is nominally about. The rest is RHYTHM:
**four notes go from `16th` to `eighth`**, because giving the staff its true
meter lets `transcribe._reconcile_measure_to_meter` re-read a beam level — the
meter→rhythm feedback loop this project built in 2026-08-28 — and page 2's
**`rhythm_sum_warnings` fall 48 → 39**, nine bars that now sum to their own
meter.

So the honest summary of (a) is: **0 rests, 4 durations, 9 bar-sum warnings.**
It was shipped because the predicate already called the value garbage, not
because of a predicted number — and the number it did produce was in a
different bucket from the one that motivated it.
