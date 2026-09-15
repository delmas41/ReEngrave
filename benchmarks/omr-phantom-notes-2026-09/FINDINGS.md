# A pitched note where the page prints silence — opened, and it is TWO faults

2026-09-14. Sean's observation 3, the last unanswered of the seven he gave on
the first cleanup artefact, and the one the previous attempt answered the wrong
question about. **No code shipped.** Everything below is measured on committed
artefacts; this container has no `omr-weights/` and no `library/`, so nothing
here was re-gathered and nothing could be.

> *"in bars where it should be just whole note rest in two four. It's showing
> an actual quarter note, not a quarter note rest."* — Sean, 2026-09-11

---

## 0. THE SHORT VERSION

⚠️⚠️ **THE BRIEF'S MECHANISM IS REAL AND IS THE SMALLER HALF: of the 25 phantom
notes measured against the print, 8 stand at the whole rest's own slot and 14
stand OUTSIDE THE STAFF ALTOGETHER, where no whole rest can be.** The second
population cannot be a misread rest by construction — the bar's own ink is one
rest — so that ink entered through the measure cell's PADDING from a
neighbouring staff. Two faults, one symptom.

⚠️⚠️ **AND THE HANDOFF'S POPULATION IS THE WRONG SHAPE IN BOTH DIRECTIONS.**
*"118 bars whose entire content is one pitched note, 44 underfull, 26 a lone
quarter"* is defined by OUR OUTPUT. Measured against the PRINT on the one
system where the whole population is adjudicable:

| | |
|---|--:|
| bars the print shows as one rest-shaped mark and nothing else (p4/s0) | **27** |
| …of those, bars we write pitched notes into | **11** |
| …of those 11, bars the handoff's "one pitched note" filter catches | **3** |
| underfull lone-pitched bars on that system | 13 |
| …of those 13, bars the print actually shows as silent | **3** |

**The filter misses 8 of 11 offending bars and mis-attributes 10 of its own
13.** Seven of the eleven hold TWO OR THREE pitched notes, which no "one
pitched note" filter can ever see.

---

## 1. REACH, FIRST

⚠️ **This container cannot run GATHER.** `omr-weights/` and `library/` are
gitignored and absent (`docs/cloud-session-capabilities-2026-09-09.md`), and
the 132 MB shared record the Phase 2 sessions used
(`library/_shared-records/beethoven5-p1-p4.record.json`) is not here either. So
no arm on this branch re-adjudicates or re-exports anything.

What IS here, and is all this work rests on:

| artefact | what it gives |
|---|---|
| `benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4.musicxml` | **the file Sean read** — 12 parts, 1,183 measures, 1,793 pitched notes |
| `…/out/system-map-p1-p4.json` | the exporter's OWN map, asserted measure-for-measure against that XML when it was built |
| `…/out/side-by-side-p1-p4.html` | **seven data-URI PNGs, one per printed system — the only copy of the Litolff plate that reaches this session** |

⚠️ **The print reaches this container only because somebody embedded it in an
HTML artefact.** `probe/extract_crops.py` pulls the seven system crops back out
(2,085-2,419 px wide, ~15.6 px staff spacing) and exits non-zero if it finds
none.

⚠️⚠️ **THE ARTEFACT PREDATES THE DEDUPE REPAIR AND THAT IS LOAD-BEARING.** It
carries exactly **1,793** pitched notes, which CLAUDE.md records as the count
*before* `A CONTEST is RESOLVED, not relocated` took it to 1,618 by refusing
**176 notes as `owned_by_another_staff`**. The 14 outside-the-staff phantoms
below are exactly that repair's target population. **Some of them may already
be gone on main and this session could not check.** See §7.

---

## 2. THE POPULATION, REPRODUCED — and it is 117/43/26, not 118/44/26

`probe/population.py`, over the artefact alone:

```
bars whose ENTIRE content is one PITCHED note : 117
  ...of which UNDERFULL                       : 43
  ...of which a lone QUARTER in a 2/4 bar     : 26
the handoff's six named bars, found here      : 6/6
```

All six named bars reproduce exactly (`P1 m45 C5`, `P1 m85 D5`, `P1 m88 D5`,
`P1 m89 D5`, `P2 m49 F5`, `P2 m87 A5` — each `duration=96` of `192`). The
handoff's 118/44 are one higher than this probe's 117/43 on the same file; the
26 agrees to the unit. Not chased — the discrepancy is one bar and the 26 is
the number the observation is about.

⚠️ **The 117 is not one population.** It splits by written length:

| | n |
|---|--:|
| a lone HALF note filling the 2/4 bar exactly | 74 |
| a lone QUARTER (underfull) | 26 |
| a lone EIGHTH | 16 |
| a lone 16th | 1 |

The 74 full-length ones are not underfull and are **not** what Sean described.

---

## 3. THE FIRST TEST NEEDS NO PRINT: WHERE ON THE STAFF DOES THE NOTE STAND?

A whole rest hangs under the fourth line from the bottom, and the engraver has
no freedom about it: with the bottom line step 0 and one step per half space,
its body occupies steps 5-6 — `C5` or `D5` in treble, and the transposed
equivalent under any other clef. If Sean's notes are whole rests read as
noteheads, their staff step must pile up there. `probe/steps.py` asks the
exported file, using its own `<clef>` and the exporter's system map; **the null
is the file's own other 1,672 notes**, which is what makes a pile-up mean
anything.

| population | n | at step 5-6 | share |
|---|--:|--:|--:|
| every other note in the file (the null) | 1672 | 223 | **0.133** |
| lone-pitched bar, FULL length | 74 | 6 | **0.081** |
| lone-pitched bar, UNDERFULL | 40 | 15 | **0.375** |
| lone QUARTER in a 2/4 bar | 25 | 8 | **0.320** |

⚠️ **A 2.4× enrichment, and only a third of the population.** So the brief's
mechanism is real and cannot be the whole story — and the 74 full-length lone
half notes sit *below* the null, which is the result agreeing with itself:
those are real held notes, not misread rests.

⚠️ This is a NECESSARY condition, not a sufficient one — 13.3% of all notes
stand there because that is where `C5` and `D5` live.

---

## 4. THE DECIDING TEST: ASK THE PRINT, WITH THE PRINT AS THE DENOMINATOR

⚠️⚠️ **THIS IS THE QUESTION THE WIP BRANCH NEVER ASKED.** Everything so far is
defined by our output, and a bar we UNDER-READ looks identical from the file to
a bar we invented a note in. The population the fault is about is defined by
the PRINT: *a bar whose only mark is one rest*.

`probe/silent_bars.py` walks every bar of every staff of one printed system,
counts the ink the print holds there, keeps the bars whose only mark is
rest-shaped, and reports what our file wrote in each.

⚠️ **It refuses unless the crop's own staff and barline grids agree with the
exporter's system map** — a bar index read off a grid that disagrees names the
wrong bar, which is worse than no crop. Of the seven committed crops, **two
reach agreement**: `p4/s0` (11 staves, 15 bars) and `p3/s0` (11, 16). The other
five are reported and refused.

### p4/s0 — 165 staff-bars

```
bars the PRINT shows as ONE REST-SHAPED MARK and nothing else: 27
   1 rest(s)                 13
   2 PITCHED NOTES            5   <-- a note where the page prints silence
   PITCHED NOTE               4   <-- a note where the page prints silence
   3 PITCHED NOTES            2   <-- a note where the page prints silence
   1 note(s) + 1 rest(s)      2
   2 note(s) + 1 rest(s)      1
```

### p3/s0 — 176 staff-bars

```
bars the PRINT shows as ONE REST-SHAPED MARK and nothing else: 67
   1 rest(s)                 61
   1 note(s) + 1 rest(s)      2
   4 PITCHED NOTES            1   <-- a note where the page prints silence
   PITCHED NOTE               1   <-- a note where the page prints silence
   3 rest(s)                  1
   2 rest(s)                  1
```

**Pooled: 94 print-silent bars, 13 of them holding pitched notes (13.8%).**
⚠️ **And the two systems are wildly different — 11 of 27 against 2 of 67.**
p4/s0 is the crescendo into the `ff`, where the three resting staves (Flute,
Oboe, Trumpet) sit directly around staves whose music carries four-ledger-line
notes into the gaps. p3/s0 is sparse. **So this fault is a property of what
stands NEXT to a resting staff, not of the resting staff.**

### The partition, which is the result

Every phantom note, by where it stands on its own staff:

| | n | share |
|---|--:|--:|
| at the WHOLE REST's own slot (step 5-6) | **8** | 0.32 |
| **OUTSIDE the staff entirely (step < 0 or > 8)** | **14** | **0.56** |
| inside the staff, elsewhere | 3 | 0.12 |

The fourteen are not near misses: `A6`/`G6` at steps 16-17, `F6` at 15, `C6` at
12, `B5` at 11, `A5` at 10 — four or more ledger lines above a staff printing
one rest. **A whole rest cannot produce ink there.** The bar's own ink is one
rest, so that ink came from outside the bar, which on this pipeline means the
measure cell's 4-6 staff spaces of padding and the neighbour it reaches.

⚠️ **Do NOT read "outside the staff" as diagnostic on its own** — 43% of the
file's notes sit outside their staff, because ledger notes are ordinary and
because some clefs are wrong. The claim rests on the CENSUS: the print holds one
rest in that bar and nothing else.

### Adjudicated by eye as well as by census

Four of Sean's six named bars fall on `p4/s0`, where the bar grid is verified.
`probe/bar_crop.py` cut them and they were looked at:

* **P1 m85 / m88 / m89** (Flute, bars 3 / 6 / 7): the staff holds **one whole
  rest and nothing else**, hanging under the second line from the top. Our file
  writes `D5` quarter — **the line the rest hangs from**. The brief's mechanism,
  confirmed on the print.
* **P2 m87** (Oboe, bar 5): the staff holds one rest; a half note with a
  natural and a tie sits on a ledger line **above** it, in the gap. Our file
  writes `A5` — one ledger line above the Oboe staff. The padding, not the rest.

---

## 5. FOUR THINGS THIS SESSION'S OWN INSTRUMENTS GOT WRONG

⚠️ **(1) The first staff-line grouper found 9 staves of 11 and silently
renumbered the rest.** A greedy "take the next five rows whose gaps agree" scan
eats a row from the staff below the moment one line is faint, so every staff
after it is off by one — and every bar adjudicated after that names the wrong
instrument. Replaced by grouping on the GAP (a cliff, not a threshold) with a
four-row group's missing line RECONSTRUCTED rather than dropped: 11 of 11.

⚠️⚠️ **(2) Erasing fixed rows to remove the staff lines produced blobs SIX TO
SEVENTEEN STAFF SPACES WIDE and the first census read them as glyphs.**
CLAUDE.md prices this plate's warp at 8-17 page px across a staff's width, so a
constant comb leaves long horizontal fragments. The run-length rule (delete any
vertical ink run ≤ 6 px) is tilt-independent because it asks about one column
at a time. *A census that reports a "whole-rest-shaped" mark 9.6 spaces wide is
measuring its own comb.*

⚠️⚠️ **(3) THE ABSOLUTE STAFF STEP READ OFF THE CROP IS NOT USABLE, AND THE
DRIFT IS THE PROOF.** The same printed mark on the Flute staff reads step
**3.78, 4.03, 4.29, 4.54, 4.80, 5.06, 5.18** across seven consecutive bars —
monotonic, 1.4 steps left to right — and between staves the offsets are larger
still (the Oboe staff reads the same mark near step 0, the Trumpet near 6.5).
That is more than the gap between a whole rest (5.5) and a half rest (4.5), so
**the crop-side classifier does not use the step at all**; it uses SHAPE (a rest
of any value is a squat wide bar, a notehead is not) and the fact that the mark
repeats bar after bar. The step figures in §3 and §4's partition come from the
EXPORTED FILE's pitch and clef, which do not carry this error.

⚠️ **(4) The barline threshold is swept until the crop's grid matches the
exporter's map.** That is calibrating to an INDEPENDENT structural fact, not to
the answer — and the result is stable across the whole agreeing plateau
(`--bl-frac` 0.60 / 0.70 / 0.80 give identical counts on p4/s0).

---

## 6. WHAT WAS DONE WITH THE WIP BRANCH — SCOPED, NOT MERGED

`origin/claude/note-where-silence-is-printed` (`f72b035c`, 1,870 insertions)
builds `Q.NOTEHEAD_IS_A_WHOLE_REST`: a GLYPH-scope decision with two witnesses
(ink shape in staff spaces, and the staff step within ±1.0 of 5.5), consumed by
`export._place_notes` as a refusal to write a note. **It is the brief's
hypothesis, built.** Nothing from it is merged here.

**Its rule is probably right and its scope is a third of the fault.** Measured
against the 25 phantom notes:

* it can reach the **8** at the rest slot — the shape it asks for is what the
  print holds there (measured `h` 0.77 spaces, aspect 1.92-2.08, against its
  `< 0.85` and `1.8 < aspect < 3.5`);
* it **structurally cannot reach the 14 outside the staff**, and should not —
  they are not rest-shaped and not at the slot;
* on the 13 offending bars it would clear **at most 6** entirely, because
  `P6 m88` and `P6 m92` hold a slot note AND an outside-the-staff note, and
  dropping only the first leaves the bar still wrong.

⚠️ **Its own reported reach (20 flagged glyphs over three pages) was never
joined to a single BAR**, so nothing on that branch says whether it addresses
Sean's observation at all. That join is what this session did.

⚠️ **It was not verified here and could not be**: every one of its eleven
probes and its arm needs the staged record or the weights. Its unit tests
(`test_staged_whole_rest_ink.py`, 257 lines) are synthetic and would run — but
running them proves the fixture, not the page, which is this repo's recorded
`Q.METER_GLYPH` lesson.

**Recommendation, with the reason:** do not ship it yet. Ranking it first would
be fixing the smaller of two causes, and it would be measured against an
artefact that predates the dedupe repair.

---

## 7. THE RANKED NEXT WORK, AND EXACTLY WHICH ARM NEEDS A MACHINE

1. ⚠️⚠️ **RE-EXPORT THE SHARED RECORD ON CURRENT MAIN AND RE-RUN
   `probe/silent_bars.py`.** This needs a machine holding
   `library/_shared-records/beethoven5-p1-p4.record.json` (md5
   `d3620ba9cb70fc93f6b7ee91b6cbe40a`) — **no weights and no gather**:
   `python3 -m tools.omr.staged.export <record> --out new.musicxml`, then
   `probe/silent_bars.py --xml new.musicxml …` over the crops
   `probe/extract_crops.py` produces. **The dedupe repair refuses 176 notes as
   `owned_by_another_staff`, and the 14 outside-the-staff phantoms are its
   target population.** Until that runs, nobody knows how much of Sean's
   observation is already repaired. ⚠️ The system map has to be rebuilt with the
   file, since it is the exporter's own.
2. **Then, and only then, decide on the WIP.** If the 14 are gone, the rest-slot
   rule is the whole remainder and is worth shipping with §6's scoping. If they
   are not, the padding half is the bigger job and `Q.GLYPH_OWNER` is where it
   lives.
3. **Re-point the handoff's counters.** `118 / 44 / 26` should not be quoted as
   a measure of this fault again; `silent_bars.py`'s print-side denominator is
   the honest one.
4. **A second publisher.** Breitkopf Brahms 1, for the reason everything else in
   Phase 2 needs it.

---

## 8. WHAT IS NOT ESTABLISHED

* **n = 1 document, 1 publisher, 2 printed systems of 7.** The two disagree by
  an order of magnitude (11 of 27 against 2 of 67), so nothing here is a rate
  for the movement, let alone the corpus. Litolff `984073` is the *low-res
  bitonal* scan this repo already calls the pessimistic end.
* **The other five crops were refused, not measured.** Their barline grids do
  not agree with the map at any threshold swept; that is a limit of this
  session's crop-side reader, not a statement about those systems.
* **The census's "rest-shaped" label is not a rest CLASSIFIER.** It cannot tell
  a whole rest from a half rest (see §5.3), so "27 print-silent bars" means *27
  bars holding one rest of some value*, which is what the question needs and no
  more.
* **Nothing was re-gathered, re-adjudicated or re-exported.** Every figure is a
  property of the committed artefact and the committed crops.
* **No claim is made about the 74 full-length lone half notes** beyond §3.
* **The 176 notes the dedupe repair refuses were not inspected**, here or
  anywhere.
* **No mutation battery was run, because no rule shipped.** The probes' own
  controls are the grid-agreement refusal, the threshold plateau, and the null
  in §3.
