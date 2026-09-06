# ReEngrave — backlog / research notes

Forward-looking ideas. Not yet scoped, not yet scheduled. Surface these to Sean at the start of a ReEngrave session.

➡️ **START HERE: [docs/next-steps-omr-2026-09-01.md](docs/next-steps-omr-2026-09-01.md)**
— accuracy is measurable against an outside standard now (pooled OMR-NED; the
current figure lives in ONE place, [CLAUDE.md](CLAUDE.md)'s OMR-NED section,
and is deliberately not restated here — this block was one of the three copies
the `a271b1e` merge silently left stale). The metric's top-ranked item —
cross-staff attribution — landed 2026-09-01 as 81446a0, slurs, its #4, the
same day as bae93b1, and the rhythm bucket — dots and beam levels — the same
day again. The ranked residue plus the closed dead ends are in that file;
[PROJECT_STATUS.md](PROJECT_STATUS.md) is current through the 09-01 landing.

---

## 🔮 CAPTURED (Sean, 2026-09-05): the sonic fingerprint — score → recording, not prompt → music

Sean's framing, verbatim in substance: once transcription is solved, pair
**recordings** with the **notes on the page**, capture the sonic fingerprint that
matches what is written, and let a composer who wrote from scratch have their
score — notes, instruments, and *everything else printed on the page* — rendered
as a real orchestral recording. Explicitly **not** "ask an AI to write me
something in a style": the human supplies the music, the model supplies the
performance.

Far off, unscoped, unscheduled. Written down because the framing is right and
because two cheap things follow from it today (bottom of this entry).

### Why the framing is worth keeping

It is a **rendering** problem, not a generative one — the same category as a
sampler or a physical-modelling synth, one rung up. That distinction is not
just rhetoric; it decides the shape of everything downstream:

- **the input is fixed** (the composer's score), so the model is judged on
  fidelity to an intent that already exists, not on taste;
- **it is evaluable** — a rendering can be scored against the same score it
  came from, which is the property this project has spent a year buying for
  OMR (see the OMR-NED section of CLAUDE.md for how much that is worth);
- **the licensing story is cleaner than a generative one** on the output side,
  because nothing about the composition came from the training data. The input
  side is a different matter — see the risks below.

### The two halves, and only one is the hard one

The literature splits this cleanly, and it is worth adopting the split rather
than treating it as one problem:

| half | asks | state of the art (unverified — look these up before relying on any of it) |
|---|---|---|
| **performance rendering** | score → timing, dynamics, articulation, vibrato, balance | active research (VirtuosoNet-family work); mostly **piano**, because that is where aligned data exists |
| **synthesis** | performance → audio | DDSP, RAVE, neural audio codecs; strong on monophonic/solo, weak on 60-source tutti |

⚠️ **The instinct is that synthesis is the hard half. It probably is not.** The
hard half is **alignment and separation on the corpus side** — see below.

### What ReEngrave is actually positioned to contribute, and it is not the audio

The scarce asset here is not a synthesizer. It is a corpus of
**notation-level** score↔audio pairs for **orchestral** music. Existing aligned
datasets are overwhelmingly piano (MAESTRO, ASAP) or small chamber ensembles
(URMP, Bach10), and they align at the level of *notes*. What almost nothing
aligns at is the level of *marks* — this slur, this hairpin, this `legato`, this
staccato dot, on this staff, in this edition, against those 400 milliseconds of
audio.

**That is exactly and only what this project reads.** The nine
detected-then-dropped fixes of the last month were, almost without exception,
the expressive layer: hairpins, articulations, direction text, tuplets, slur
pairing across barlines and system breaks, dynamics band attribution. Those were
pursued because they were costing OMR-NED edits. They also happen to be the
entire input feature vector such a model would consume. That is a coincidence
worth banking.

### The asymmetry that decides sequencing

**The product half needs no OMR at all.** A composer writing from scratch hands
over MusicXML — there is no page to read. So the thing Sean wants to *use* sits
downstream of a problem this project has already solved for that input.

**The corpus half needs OMR at its very hardest** — historical scans, dense
conductor's pages, the 0.83 end of the scale, not the 0.11 end. Building the
score↔recording corpus from the recorded repertoire means reading exactly the
pages that are currently hardest.

So: the dataset is gated on the scan work; the product is not. If a corpus ever
arrives some other way (publisher MusicXML, engraving-house files, commissioned
sessions), the product could be attempted without waiting on OMR at all.

### Where it actually breaks, honestly

1. **Alignment in a tutti is the bottleneck.** Score-to-audio alignment by DTW
   over chroma/CQT is workable at the *measure* level and unreliable at the
   level of one inner voice inside a 60-piece texture. "Which 300 ms is the
   second bassoon's slurred descent" is not currently answerable from a stereo
   commercial recording.
2. **Orchestral source separation is far behind pop stems.** Four-stem pop
   separation is a solved commodity; "isolate the second horn from the third"
   is not, and no amount of model scale obviously fixes overlapping harmonics
   from identical instruments in one hall.
3. **You would not capture a fingerprint of an instrument. You would capture a
   fingerprint of a *recording*.** Hall, mic placement, section size, conductor,
   edition, and engineer are not separable from timbre without isolated
   sources. That may be a *feature* — "1963 Berlin" as a renderable target is a
   more interesting product than "a violin" — but it should be named as what it
   is, and it makes the copyright question sharper, not softer.
4. **Copyright is the live risk, and it is on the input side.** Training on
   commercial recordings in order to emulate them is the exact question
   currently being litigated. Narrower paths exist: public-domain recordings
   (acoustically poor, and poor *specifically* as timbre data, which is the one
   thing you'd want them for), explicit licensing, or recording your own
   sessions — which is expensive but produces isolated sources, which fixes
   problems 1–3 at the same time.
5. **The uncanny valley here is phrasing, not timbre.** Sample libraries already
   sound convincing on single sustained notes and unconvincing across a phrase.
   Anything that improves timbre while leaving phrasing flat lands in the same
   valley the libraries are already in.

### ⭐ The reframe worth arguing about

**Split timbre from interpretation, and go after interpretation first.**

Sample libraries have spent twenty years and a lot of money on timbre. What they
are conspicuously bad at is *phrasing* — the reason a mocked-up orchestral cue
sounds like a mock-up is almost never the sound of one note, it is the
articulation, the rubato, the way a crescendo is shaped, the fact that a slur
means something to a player and nothing to a sampler.

That suggests a much smaller and much nearer version of the same idea:

> **score marks → expressive performance parameters → drive an existing
> high-quality sample library.**

No neural audio synthesis. No source separation. No orchestral recording
corpus. The output is expressive MIDI/CC, and the timbre comes from a library
the composer already owns. It is testable with a single instrument and a single
library, and it attacks precisely the half nobody has solved. If it worked, the
"replacement for sample libraries" claim would be *half* true in a useful way —
not replacing them, but making them do the thing they can't.

The neural-synthesis version remains the endgame. This is the wedge that could
be attempted without a decade of data work, and it fails cheaply.

### Smallest experiment that would teach anything

One instrument. Monophonic. Solo repertoire with existing close-mic'd or
multitrack audio. Align, extract the performance-parameter curves against the
printed marks, and ask a single question: **does knowing the printed
articulation and dynamic marks predict the performance curves better than the
notes alone?** If the printed marks add nothing measurable over the notes, the
whole premise — that the *page* carries the information, which is this
project's entire thesis — is falsified cheaply, and that is worth knowing.

### 📌 Two cheap things to do now (the only actionable part)

1. **Do not discard the rich artifact.** `{stem}.omr.json` carries the
   expressive marks with page coordinates, per-staff attribution, edition
   provenance and detection confidence; the exported MusicXML carries strictly
   less (the exporter reads no confidence at all — see the probability-gates
   handoff). If a corpus is ever wanted, the `.omr.json` files are the corpus
   substrate and the MusicXML is not. They are already written; the note is to
   keep them, and to keep the score-library provenance attached.
2. **The score library is already the right shape for this.** 235 editions,
   1745 reference encodings, 27 works pairing a PDF with ground truth, joined on
   `work_id`. A recordings axis would be a third directory beside `editions/`
   and `reference/`, joined on the same key. Nothing needs building now — but
   any future change to the library's schema should not make that third axis
   harder to add.

---

## 🅿️ PARKED (Sean, 2026-09-03): re-try the template-read elements — time signatures first — under the new labeling system

Not urgent, but **must not get lost** (Sean asked for exactly that). The
labeling survey ranked time-signature digits LOW because the CV template
reader closed the gap the detector left (12 correct / 0 wrong / 3 missed / 40
correct abstentions corpus-wide — the detector reads **zero** meter digits on
real scans). That ranking predates two things: the **single-symbol pass UI
with click-to-box** (which makes a digit pass cheap and the boxes uniform),
and the **proven label→gate→ship loop** (hollow row: scan labels measurably
moved the detector for the first time). Sean wants the question re-opened at
some point with a larger, publisher-diverse digit labeling pass.

How to run it when picked up:
- A meter digit is a fixed-size glyph — numerator in the upper two staff
  spaces, denominator in the lower two — so `click_box` works with
  `height_spaces: 2.0` per slot; `select_timesig_cells.py` already exists as
  the cutter.
- The detector should enter as an **additional voter into the existing
  header-window vote**, never replacing the template reader — the reader's 12/0
  record and its abstention behavior are the floor to hold, and the 3 misses +
  40 abstentions are the headroom to win.
- Measurement is ready-made: `benchmarks/omr-timesig-2026-08/` +
  `benchmarks/omr-timesig-2026-09/FINDINGS.md` corpus (half its pages print no
  meter — abstention is scored, not just accuracy).
- Same logic later applies to the other template-read elements (key-signature
  accidentals; clefs — ⚠️ clef labels feed the SPECIALIST slot only, never the
  shared catalog: density-collapse precedent, `catalog-versions.txt` v5/v6).
- The symbol inventory (`benchmarks/omr-labeling-survey-2026-09/symbol_inventory.py`)
  carries a REVISIT flag on these rows so the list survives this file too.

## 🚨 NEXT: the same scan page, transcribed twice, gives two different scores (2026-09-02)

Found while measuring the `--direction-text` default, and it outranks what it
interrupted. Page 84 of the Litolff Beethoven 5 exports **485 lines differently
between two runs of the SAME configuration** — seven part names shifted by a
staff (Flute→Oboe, Timpani→Trumpet, Harp→Violin), one clef, and note content.

Four controls, in the order they were run:

| what varied | result |
|---|--:|
| the `--direction-text` flag | 485 lines |
| **nothing** (OFF vs OFF, resident Surya) | **485 lines** |
| **nothing** (OFF vs OFF, fresh Surya server per run) | **497 lines** |
| **nothing**, `--no-contextual` — no OCR anywhere | **identical** |

Row two says the flag never did it. Row three rules out state carried across
requests by the long-lived Surya server. Row four locates it exactly: with no
OCR in the pipeline two runs agree to the byte — 1302 detections, 640
noteheads, 238 measures, the same hash over every staff's geometry.

So it is `contextual._labels_for_page`, **which is on by default**
(`surya_fallback=True`, no flag). Surya resolves 10 margin labels in one run and
1 in the next; Tesseract fills what it drops, reads the margins differently, and
the part assignment slides a staff.

⚠️ **This is not "Surya is non-deterministic" yet, and the evidence cannot reach
that.** Every count above is downstream of the reader.
`SURYA_BAKEOFF_2026-08-31.md` measured 45 replays as a fixed function of its
input — with its own recorded caveat that replaying ONE image cannot see a
shared prompt cache. The test nobody has run is the tight one: **the same crops,
twice, in one process, compared directly.** Start there.

⚠️ **Second loose end, and it does not fit the story:** the **text-layer** tier
resolved 1 label in one run and 0 in the next. A PDF's text layer is a fixed
input and cannot move if the staves are stable — and row four says they are.

⚠️ **Every end-to-end scan figure this project holds came from ONE run**, and
none of them carries an error bar. The cheapest first step for any of them is to
run it twice.

**The lead worth following first**, narrowed after the tight Surya test came
back clean (20 crops, same order / shuffled / a second process — 0 of 20
differ, so the reader IS a fixed function of its input): if Surya is
deterministic and the layer beneath is byte-exact, what varies must be whether
Surya is CALLED SUCCESSFULLY. `contextual.py:386` is

```python
except Exception as exc:            # noqa: BLE001
    logger.warning("surya label fallback failed on page %s: %s", ...)
```

with nothing recorded in the result. An intermittent failure there is
indistinguishable from the reader legitimately finding nothing — `label_tiers`
shows `surya: 0` either way and the JSON carries no trace. That is precisely the
shape `_optional_pass_failure` was built for, and this call site does not use
it. **Hypothesis, not a finding** — the warning is not in any log I kept. The
test is cheap: route it through `_optional_pass_failure` (or log at ERROR) and
run page 84 twice.

⚠️ **The `label_tiers` counter is CONTRIBUTION, not production** — `tiers[0] = 0`
on line 408 zeroes the text layer's credit when Surya's read wins, the same way
line 525 does for the vision rung. So the "text layer 1 then 0" above is fully
explained by Surya's own yield moving, and there is nothing to hunt for in the
PDF text layer. That was a wrong lead and it is closed.

Full write-up with all four controls:
[benchmarks/omr-direction-text-2026-09/NONDETERMINISM_2026-09-02.md](benchmarks/omr-direction-text-2026-09/NONDETERMINISM_2026-09-02.md).

---

## ➡️ NEXT: the system-break rule is zero-tolerance (found 2026-08-31)

LEGATO's system detector, used as a **miner** over 47 pages, flagged exactly one
disagreement — and it is a real bug. Beethoven 5 (IMSLP984073) **p40 is three
systems of seven staves and we read one of twenty-one.** Adjudicated by looking:
three brackets, three measure numbers (229/243/256), labels restarting at each.

Cause is one line in `system_grouping.assign_systems`:

```python
elif bridging[i] == 0:
    system += 1
```

A break must be bridged **exactly zero**. On p40 the two true breaks are bridged
3 and 11, so neither fires. On the pages where we agree the break is bridged 0
exactly — the rule works whenever nothing crosses and fails silently the moment
a measure number or a margin label does.

Neither signal separates the cases alone (bridging 11 at a true break vs 11–14
at bracket-group boundaries; gap size was what connectivity replaced). The PAIR
does on these four pages — a large gap that is *nearly* unbridged.

✅ **UNBLOCKED 2026-08-31.** The Beethoven 9 scan (IMSLP 516488, 189 pp, 20 MB)
has been downloaded back into
`tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf`
(gitignored, like the rest of that corpus). `eval_grouping.py` runs and
reproduces its recorded baseline exactly: connectivity **12/14 (86%)**, gap
heuristic 5/14, 0 spurious single-staff systems. So a rule change can now be
regression-tested.

**The failure set is three adjudicated pages, and they are not all alike:**

| page | truth | ours | LEGATO | note |
|---|--:|--:|--:|---|
| B9 p25 | 2 | 1 | **1** | **LEGATO misses it too** |
| B9 p60 | 2 | 1 | 2 | LEGATO catches it |
| B5 p40 | 3 | 1 | 3 | LEGATO caught it; adjudicated on the margin |

Against the 12 hand-read B9 pages: ours 10/12, **LEGATO 11/12**. So the miner is
better than us here but is NOT an oracle — p25 is the standing counter-example,
and a page LEGATO agrees with is not thereby correct. Measure the fix against
`eval_grouping.py`, never against the miner.

❌ **FIVE FIXES TRIED 2026-08-31, ALL REJECTED.** Attempt 5 was
instrument-label continuity — semantic rather than typographic, so it should
have been immune to the engraving-convention problem. Best variant (score-order
rank decrease AND bracket-reach 0) scores TP=12 FN=3 **FP=5** against the
shipped rule's **3 page-level errors** on the same 23 pages. It fails because
labels are sparse where they are needed (La Mer p2: 2 labels / 20 staves;
Mahler p20: 1 / 16), because localization is off by one whenever the new
system's top staff is unlabelled, because the canonical rank averaged over the
repo's layouts puts Violin ahead of Timpani and so invents breaks on every
Mahler page — and because doing it properly with `align_to_layout` is circular,
that being monotone and per-SYSTEM.

**Recommendation: stop.** Five attempts across two families (ink in the gap;
labels beside it) all land well short of a rule that is already at 20/23, and
all three of its failures are the same narrow case — two systems printed so
close that their brackets nearly touch. Spend the effort elsewhere unless that
case starts costing real output.

The first four: — attempt 4 is the bracket,
retried against the WIDER set: perfect recall (all 15 true breaks read 0) but
`min(non-break) = 0` in **all 32 configurations** swept, because a system bracket
is a thin curved engraving rather than a printed rule and whether it clears an
ink test is itself an edition property. It died in ONE measurement, before any
code change — attempt 1 needed an implementation, a 14/14 score and a regression
sweep to be caught, so the wider set is already paying for itself. Keep one thing
from it: bracket-reach 0 is a NECESSARY condition (15/15, never misses), so it is
a cheap first filter for a future combined rule, just not sufficient alone.

The first three: —
[RULE_FIX_ATTEMPT_2026-08-31.md](benchmarks/omr-system-grouping-2026-08/RULE_FIX_ATTEMPT_2026-08-31.md).
Rightmost-reach-over-the-window separated 262 boundaries with ZERO overlap and
took `eval_grouping.py` to **14/14** — then over-split **12 pages** on the five
scores outside the two Beethoven editions it was measured on (La Mer 1 → 16
systems). Reach against the staves' own right end failed identically. The band
this module's docstring specifies does not separate at all.

**Mechanism: orchestral engraving breaks barlines between instrument families**,
so "what crosses this gap" is a property of the edition's convention, not of
whether a system ends. B9 and B5 happen to run barlines across group gaps, which
is why every signal looked perfect on them.

✅ **GROUND TRUTH WIDENED 2026-08-31 — 14 pages / 2 editions → 23 / 5.** Eight
pages hand-read off the left margin, chosen as the ones the rejected rule
over-split, so the next attempt fails fast instead of passing 14/14 and shipping:

| score | page | staves | systems | how it reads |
|---|--:|--:|--:|---|
| Mahler 5 | 2 | 15 | 1 | one bracket Fag.→Bässe, m.9 |
| Mahler 5 | 10 | 19 | 1 | Hoboen→Bässe, m.78 (20 printed; Kl.Tr. still missed) |
| Mahler 5 | 20 | 16 | 1 | Flöten→Bässe, m.171 |
| La Mer | 2 | 20 | 2 | two brackets, sub-brackets on the strings |
| La Mer | 20 | 16 | 1 | one outer bracket, 4 sub-groups |
| Boléro | 2 | 31 | 4 | m. 14 / 21 / 27 / 33 |
| Boléro | 10 | 34 | 2 | m.153 and m.159 |
| Boléro | 20 | 20 | 1 | m.219, Ptes Fl.→C.B. |

The staff counts are what the detector reports after the 08-31 one-line percussion fix; the eval asserts SYSTEMS, not staves.

All eight pass today: **connectivity 20/23 (87%)**, the three failures still the
known merges (B9 p25, B9 p60, B5 p40). Run `eval_grouping.py` AND the 54-page
cross-check; the latter is what caught the rejected rule.

⚠️ **Boléro p10 is a SECOND recorded LEGATO error** — it reports 3 systems on a
page that plainly has 2, via three overlapping boxes. With B9 p25 that is two
misses; the miner is a triage tool, not an oracle.

⚠️ Found in passing and NOT resolved: **`gap_bridging_counts` does not implement
its own docstring.** The prose says the band runs "from the top line of the upper
staff to the bottom line of the lower staff" and argues the gap-only version
fails on exactly B9 p25; the code measures the gap only. Implementing the
documented version does not fix anything either, so it is unclear whether the
code or the comment is wrong.

Full writeup + evidence:
[LEGATO_CROSSCHECK_2026-08-31.md](benchmarks/omr-system-grouping-2026-08/LEGATO_CROSSCHECK_2026-08-31.md).
Note LEGATO's raw box count is NOT a system count — it returned 3 overlapping
boxes for a 2-system Boléro page — so compare partitions, not counts.

---

## ~~the lexicon reads `Tr. Alt.` as a VOICE~~ — DONE (2026-08-31)

Wiring Surya in as the free margin reader put labels on a page that had none —
Beethoven 5 (IMSLP984073) p.48, no text layer, 0 labels before, **12 after, in
16 s, free**. Three of the twelve then resolved to the WRONG instrument, at high
confidence:

| printed | was | is now |
|---|---|---|
| `Tr. Alt.` | **Alto** (a voice), alias `alt`, conf **high** | Trombone |
| `Tr. Ten.` | **Tenor** (a voice), alias `ten`, conf **high** | Trombone |
| `Tr. Bas.` | **Trumpet**, alias `tr`, conf medium | Trombone |

**The page settles the ambiguity the lexicon could not.** `Tr.` is Tromba AND
Tromboni, and p.47 of that very edition prints both at once — `Tr.` over the
trumpets, `Timp.` below it, then `Tr. Alt. / Tr. Ten. / Tr. Bas.` over the three
trombones of the finale. So the abbreviation cannot separate them and the part
name beside it can: **a trombone section is scored by REGISTER and a trumpet
section by number and key** (`Tr. I`, `Trombe in C`), never the other way round.
A second, independent edition proves it for free — imslp-575951 p.59 carries a
text layer and prints exactly the same six labels, so this is the publishers'
convention rather than one scan's quirk. Trombone therefore gains `tr alt` /
`tr ten` / `tr bas` and spellings, which outrank the bare `tr`. NOT `tr b`:
that is a trumpet in B-flat, the same trap as `Cl. B.`.

**The second cause was the interesting one, and the fix is structural.**
`_prefer_instrument_over_voice` + `VOICE_QUALIFIERS` already existed for the
voice half, but the set was HAND-LISTED and held the spelled-out `alto` and
`tenor`, so an abbreviated `Alt.` / `Ten.` never reached it. It is now DERIVED
from the voice instruments' own aliases — a register word that can win the alias
index is by construction an alias of a voice — which closes the whole family at
once instead of one spelling at a time, and also fixes `Fl. Alt.` -> Flute,
`Cl. Alt.` -> Clarinet, `Trb. Tenore` -> Trombone.

Validated per the standing lexicon rule on **1380 margin labels from 10 editions**
(and 5507 part-name strings from 124 Gradus works, which move not at all): every
single changed resolution is a `Tr.`+register string moving to Trombone.
Beethoven 5 IMSLP984073 pp.47-49 export **11/17 -> 15/17** correct part names.
[LEXICON_TR_ALT_2026-08-31.md](benchmarks/omr-margin-labels-2026-08/LEXICON_TR_ALT_2026-08-31.md).

**Still open, found while measuring** (each is its own lexicon gap, none is this
bug): `Gr. Tr.` (Grosse Trommel, a bass drum) reads *Trumpet* and `Kl. Tr.`
(Kleine Trommel) reads *Clarinet*; `Altos` (French for violas, in Boléro) and
`Tromp.`, `Trbni.`, `Tbni.`, `Trbe.` resolve to nothing. And the score-order
LAYOUTS have no entry that puts the timpani between the trumpets and the
trombones, which is how this edition prints it — visible only when the page's
own `Timp.` is lost to OCR.

---

## ➡️ NEXT: Brahms — one of four fixed (2026-09-01)

Brahms carries **1768 of the 2140 pooled OMR-NED edits — 83%** — so the
orchestral headline is essentially a Brahms number. Attributed in
[BRAHMS_ATTRIBUTION_2026-09-01.md](benchmarks/omr-ned-2026-08/BRAHMS_ATTRIBUTION_2026-09-01.md);
unlike Beethoven (recall 1.000, all notation) this is genuine recognition
failure — recall 0.717 — but NOT the kind that argues for retraining.

✅ **The misaligned staff is FIXED** (`staff_detector` step 3d). Pooled OMR-NED
**0.3045 → 0.2716**, Brahms **0.4486 → 0.3899**, and the whole-measure bucket
collapsed 705 → 482 on its own — most of that 32% was one misplaced staff being
charged by the bar. ✅ **The augmentation dots are FIXED too** — and they were not spurious. The
dots are detected correctly and COUNTED TWICE on export: `_duration_to_lily_xml`
summed `duration_type` ("dotted_quarter") with the `dots` field (1), on a stated
assumption that only one is ever set. Brahms `wrong dot` **103 → 18**, pooled
**0.2716 → 0.2624**. An existing test had asserted the wrong behaviour and was
corrected in place. ✅ **Dynamics are exported now too** (0.2624 → **0.2595**).
✅ **Slurs are SHIPPED** (2026-09-01, `bae93b1`, 0.2263 → **0.2209**,
`wrong slur` 81 → 61, measured on top of the ledger fix `81446a0`). The pairing moved to the STAFF, in page pixels, which
rejoins the two arcs a barline cuts — the event model itself needed nothing,
since a MusicXML slur may already span measures. The half that mattered was
padding the arc box: a slur is drawn BETWEEN its noteheads, so unpadded it drops
the outer note at each end. Merging *without* the pad lowered the ratio while
RAISING the edit count — dilution, not recognition. See
`benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`. Still open: text expressions
and tempo marks, which need text detection we do not have.

**One misaligned staff produced two thirds of the pitch errors.** 65 notes are
replaced page-wide; **42 of them are part 20 alone** and **41 are exactly −4
semitones**. Part 20 is the Contrabass: truth 42 × `C3`, we read `A♭2`. Its
five-line window is fitted one space too high — the top "line" is a BEAM —
so every note lands a space low and the C-minor key signature flattens the A.

    line_ys_page      [9287, 9327, 9368, 9408, 9451]
    line_thickness_px [18.0,  5.0,  5.0,  5.0,  5.0]

**The detector for it is already in the JSON.** Line thickness is 4–5 px on 19
of 21 staves; the outliers are staff 20 (18 px, 3.6× median) and staff 8
(20 px, 4.0×), and no other staff exceeds 1.8×. A thickness outlier means the
comb locked onto something that is not a staff line. Evidence rendering:
`benchmarks/omr-ned-2026-08/brahms-staff20.png`.

The other three, in order of cheapness: **82 spurious augmentation dots**
(`dotdel` 82 vs `dotins` 16 — over-detection on an engraved page, 103 edits);
**whole-measure charges** (569 edits, 32%, but the pairs differ by one note plus
a missing slur — the same amplification as Beethoven's fermatas, so it should
mostly collapse when the others are fixed); and **slurs/directions never
exported** (124 + 70 edits, shared with Beethoven).

---

## 👁️ WATCH: LEGATO 2 weights (checked 2026-08-31 — not out, but its segmenter IS)

[arXiv:2607.05769](https://arxiv.org/abs/2607.05769), July 2026. Reads
**system by system** instead of whole-page, which is the axis dense conductor's
pages fail on, and halves OMR-NED against LEGATO 1 on multi-staff music (camera
string quartets 58.2 → 31.6). The paper says code and weights come "upon
publication" — **not released yet.** The socket already exists: the LEGATO 1
bridge on `claude/clef-time-signature-weights-6d6e38`
(`oemer_second_opinion.py --engine legato`), where LEGATO 1's clef-presence beat
the pipeline on both hand-verified Mahler pages while its meter was unreliable.

**Check on:** `huggingface.co/api/models/guangyangmusic/<name>` and
`github.com/guang-yng/legato`. As of 2026-08-31 the account holds `legato`
(0.1B, MIT), `legato-small`, and two from 2026-02-13 that postdate the July
research round:

- **`legato-1.5`** — 0.9B, nine times the LEGATO 1 the bridge was measured
  against. **Gated `manual`**, so it needs an access request before it can even
  be tried.
- **`legato-1.5-YOLO`** — ungated, one 52 MB file, and it is **the LEGATO 2
  system segmenter**: a single-class `system` detector, 25.9M params, matching
  the paper's "YOLOv8m, ~26M". Its own checkpoint reports P 0.997 / R 1.000 /
  mAP50-95 0.928.

**Measured here already, 6 pages of Beethoven 5 and 6 (300 dpi):**

| page | ReEngrave systems | staves | LEGATO systems |
|---|--:|--:|--:|
| B5 p10 | 2 | 20 | 2 |
| B5 p40 | 3 | 19 | 3 |
| B5 p59 | 1 | 17 | 1 |
| B6 p10 | 3 | 21 | 3 |
| B6 p40 | 2 | 18 | 2 |
| B6 p59 | 2 | 24 | 2 |

**Six for six.** So it is not a gain on these pages — it is independent
corroboration that the connectivity rebuild (`system_grouping.py`, 43% → 86%)
got the right answer, from a model trained on 1,024 annotated pages by people
who had never seen this repo. The use is as a **tiebreaker on the pages
connectivity still merges** (2 of 14), and as a cheap check when a new edition
looks wrong — not as a replacement.

⚠️ **It is AGPL-3.0**, inherited from ultralytics, and stated in the checkpoint
itself. Fine for personal and host-side use; a problem the day ReEngrave is
served to other people through the Stripe gate. Do not wire it into the backend
image without deciding that question first.

The checkpoint's pickle was checked before loading — 23 imports, all
torch/ultralytics detection classes, nothing that executes.

---

## A whole scan, start to finish, with nothing helping it (2026-08-31)

Every accuracy number here was measured one element at a time, or on pages this
project rendered itself from the truth it then scored against. So the obvious
question had never been asked: hand the pipeline a scan and see what comes out.

`benchmarks/omr-first-run-2026-08/` does it — Beethoven 5 page 1 of the IMSLP
scan, defaults, **no dossier**, scored against the Gradus reference, with the
page's 16 measures established independently of the pipeline.

**The components are far better than their composition.** Layout is perfect —
113 staves and 11 systems across six pages, all exact, including four pages
where the staff count changes between the two systems. Clefs 10/12. Three
quarters of noteheads on the right line (`step` recall 0.782). And the engraved
result is still not a transcription of Beethoven 5:

- ~~**meter never read**~~ — worse than that, and now **FIXED 2026-08-31**: the
  page reported common time on all twelve staves, propagated from barline
  fragments read as the digit 4. A header meter reader plus a corroboration
  guard take it to 2/4. See `benchmarks/omr-timesig-2026-08/FINDINGS.md`;
- ~~**4 of 17 barlines missed**~~ — three of sixteen, and **FIXED 2026-08-31**:
  the scan is warped and the connectivity probe assumed barlines are vertical.
  17/17 with 0 false. The fourth "miss" was an error in the benchmark's own
  ground truth, which counted the time signature as a barline;
- ~~**key signatures read on 2 of 12 staves**~~ — **IMPROVED 2026-08-31** to
  7/12 correct with 0 wrong (39% of staves over six pages), by matching the
  Bravura outlines instead of reassembling ink into components. The accidental
  gap halves. See `benchmarks/omr-first-run-2026-08/KEY_SIGNATURES.md`;
- **duration recall 0.360** — DIAGNOSED 2026-08-31 and not a rhythm bug: the
  page prints 68 half notes and the output has 8, because the scan's
  binarization closes the notehead's counter and the detector never sees a
  hollow head. Engraved control: 31 hollow found against 30 real, and duration
  recall equal to pitch recall at 0.926. Four fixes measured, none shippable —
  `benchmarks/omr-first-run-2026-08/DURATIONS.md`;
- 24 of 170 emitted notes sit on staves that print nothing but rests.

**The export part model is fixed (2026-08-31)** — `to_musicxml` joins staves
across systems and pages by ordinal, refusing where the systems disagree about
their height. WTC I Fugue 1: 20 parts of 3 bars → 2 parts of 27, OMR-NED 0.9819
→ 0.8668, dominant error `entire measure insert/delete` → `wrong note`. This
also lifts the one-page cap `orchestral_eval` put on its excerpts.

Two things this reframes. **OMR-NED is not yet a tracking number for scans**:
0.8706 here against 0.3164 on rendered pages, and 66% of the edits are
whole-measure/whole-staff inserts — the export's one-part-per-(page, system,
staff) model against an edition that condenses 18 parts onto 12 staves. And
**the dossier cannot engage**: eleven systems, eleven abstentions, because real
editions condense and suppress tacet staves, so the staff set changes *within a
page*. The join has to be per-system before external truth can help a real scan.

Ranked next steps at the end of `benchmarks/omr-first-run-2026-08/FINDINGS.md`.

---

## Clef accuracy, measured end to end (2026-08-29)

The three threads above all ended by pointing at the clef. It turns out to be in
much better shape than this repo's own notes say: **48/52 hand-read staves
correct (92%)**, the detector supplying 39 of them at 95%. The "~23% coverage /
every staff reads as treble" record is about the CV locator alone and predates
the `imgsz` fix. Every remaining error is a non-treble clef read as treble.

`benchmarks/omr-clef-geometry/eval_pipeline_clefs.py` is the harness;
`PIPELINE_CLEF_RESULTS.md` has the numbers, the one fix that landed (a part
keeps its clef between systems: 48/52 → 49/52), and two richer sources measured
and rejected — score-order identity driving clef correction, and the dossier
joined to condensed staves by alignment.

**What is left is three staves**, and they are hard in a specific way: the page
carries no evidence of the right answer in any form the pipeline can see, and
the dossier that does know cannot be told which staff to put it on. That join —
parts to condensed staves, with evidence independent of the clefs already read —
is the next real lever.

---

## ➡️ NEXT: pin the labelled slots in the part-to-staff join (2026-08-30)

The join is measured for the first time (`benchmarks/omr-part-staff-join-2026-08/`)
and its biggest failure is **structural, not evidence-starvation**: the part list
and the print can disagree about ORDER, and `align_to_layout` is monotone so it
cannot recover. On Beethoven 5 p.48 the page prints Timp. then the three trombones
while the part list has the trombones first — the trombones become unreachable and
return `None`, costing exactly the alto/tenor/bass clefs the dossier exists to
supply. Perfect labels do not fix it (13/17).

The route: **the margin labels know the PRINT's order.** A labelled slot should PIN
its part, and the aligner should run only between pins, which permits the
transposition a monotone path forbids. That is a different use of labels from
today's, where they score pairs and mark trust but never constrain the assignment.
Prompt and acceptance criteria in `docs/next-join-pinning-2026-08-30.md`.

## ➡️ START HERE — ranked next steps (2026-08-28)

**[docs/next-steps-omr-2026-08-29.md](docs/next-steps-omr-2026-08-29.md)** is the current
handoff. The four threads below are all CLOSED — the 2026-08-28 file is kept because how
each turned out is more useful than how it was posed; three of the four ended somewhere
other than where they started.

1. ~~**One-line percussion staves are invisible**~~ — **DONE 2026-08-28**, and
   **extended 2026-08-31**. A percussion part printed as one rule is now a staff, so
   the staves below it keep their slots (La Mer p.25: 20 staves on a 21-part page).
   `benchmarks/omr-phase1-baseline/`.
   The 08-31 extension: the clearance rule rejected EVERY row in a tight cluster, so a
   non-rule between two percussion parts took both real ones down with it — Mahler 5
   p10's wavy trill line between Gr.Tr. and Kl.Tr., and short fragments beside Boléro's
   `Tamb.` rule in every system. Candidates far shorter than the longest in their
   cluster are now dropped first (`SINGLE_LINE_CLUSTER_WIDTH_FRAC`). Boléro p5 26 → 29
   staves, p31 29 → 30, p2 27 → 31, p10 32 → 34, p20 19 → 20; La Mer p25 unchanged and
   still matching hand-verified truth.
   **The same ink was then charged a second time**, and that is closed too: once
   dropped as an interloper, the trill reappeared in `_has_the_rest_of_a_staff` as
   evidence of a five-line staff two spacings under Kl.Tr. (row 1743, run 1410 against
   a 929 threshold) and rejected it. Rows already judged not to be printed rules are
   now passed in as `ignore_rows`. **Mahler p10 is 20/20.** Nine pages across Mahler,
   La Mer and Boléro all match hand-read counts; the phase-1 set is untouched by this
   second step. (An earlier note here blamed the violin staff 75 px below — wrong; the
   gate never probes that far. Corrected in `ground-truth.json` → `known_gaps`.)
2. **Key signature** — the cause was found 2026-08-28 and it was neither detection nor
   reading: the staff's left edge was lost, so the header was cropped out of every cell.
   Fixed; clefs on Beethoven 5 p.15 went 0/23 -> 13/23 and the reader started firing.
   What is left is sharply scoped — 11 staves where the clef IS read and neither reader
   finds accidentals in the header. ⚠️ **The "detector is blind to those flats"
   half is WRONG — corrected 2026-08-29.** It detects them and labels them
   `accidentalFlat` instead of `keyFlat`, and every key-signature reader consumes
   only the `key*` classes, so a correctly-read signature is discarded on a
   technicality of class naming. Routing them in was implemented, measured, and
   NOT shipped: it costs beet5-p2 10 correct -> 9, because the accidental set is
   noisier and the vote's rejection path zeroes a staff instead of reverting it.
   `benchmarks/omr-keysig-blindspot-2026-08/`. `benchmarks/omr-key-signature/RESULTS.md`. Inference from
   the music stays parked while the printed signature sits unread.
3. ~~**Score-order prior**~~ — **DONE 2026-08-28.** `tools/omr/score_layouts.py`:
   ten standard layouts, monotone alignment, a continuation move for parts printed
   on several staves. An unlabelled orchestral page (Beethoven 5 p.15, no text
   layer) now names 10 of 12 staves, 8 correctly, where it had no identity at all.
   `Tp.` is settled from position. `benchmarks/omr-score-order/RESULTS.md`.
4. ~~**Re-read July's "domain gap" conclusion**~~ — **DONE 2026-08-28, and it did not
   survive.** The flood, the invisible meters and the mostly-treble clefs were all
   artefacts of `imgsz 2048`: same pages, same weights, same confidence, Boléro p.1
   goes from 0 time-signature digits and 13 clefs to 36 digits and 24/24 clefs.
   `benchmarks/omr-detection-probe-2026-08/findings.md`. A class-specific gap remains
   real — key-signature flats on Beethoven 5 p.15 are undetected at any threshold.

⚠️ **Any measurement predating 2026-08-28 went through an `imgsz` reporting 2–4× the notes
that exist.** Re-measure before building on one. `imgsz` is now derived per cell — see
`benchmarks/omr-detector-scale/RESULTS.md`, which also corrects the stated mechanism
(ultralytics scales the longest side to `imgsz`; it does not letterbox to `imgsz²`).

---

## 🧭 Contextual analysis roadmap (2026-08-28) — ACTIVE

**Sean wants all of these; they are ordered here on purpose.** The framing: a human
reading a large score deduces most of it from context — which staves are concert vs
transposing, what instrument order and groupings to expect, and once the key is known,
what the accidentals must mean.

> ✅ **2026-08-31: the pass is now IN the pipeline.** Until then
> `apply_contextual_analysis` was reachable only from benchmarks, so everything
> below — and the clef numbers this repo quotes — described a path no
> transcription ever took. `transcribe(contextual=True)` is the default,
> `--no-contextual` opts out, and the result carries a `contextual` block.
> The exporter now names parts by instrument, so a Beethoven 5 page with **no
> text layer** exports as `Flute / Oboe / Clarinet / Bassoon / Horn / Trumpet /
> Timpani / Violin / Viola / Cello` instead of `Staff p47-s0-N`. The paragraph
> below is kept because the framing still holds for what is left.

Every page re-derives clef and key from scratch, and the exporter used to name
parts `Page0-System1-merged` (`tools/omr/export.py`) because **there was no
persistent part identity anywhere in the pipeline.**

The four human deductions and where they stand:

| Human deduction | Repo status |
|---|---|
| *this staff is Clarinet in B♭* | nothing — no instrument identity at all |
| *…so it transposes, expects treble, lives in this range* | transposition math exists (`transcribe.py:1450`) but has nothing to attach it to; it guesses offsets |
| *staves run winds→brass→perc→strings in these groups* | bracket gaps are used only to split systems (`staff_detector.py:194`); the grouping is then discarded |
| *key is X, so these accidentals mean Y* | M4 re-rank does this, but off one global detected key, not per-staff |

### #1 — Persistent staff/part identity ("slots") — **IN PROGRESS**

**Step 1 DONE (2026-08-28): system grouping rebuilt on vertical connectivity.**
`tools/omr/system_grouping.py` + wired into `staff_detector.detect_staves`. Slots are
assigned per system, so correct systems are a hard prerequisite — and the gap-size
heuristic was badly wrong on exactly the scores that matter. Full writeup:
[benchmarks/omr-system-grouping-2026-08/findings.md](benchmarks/omr-system-grouping-2026-08/findings.md).

Measured on 14 pages (Beethoven 9 + Beethoven 5 p10 at 300 and 600 dpi), against
ground truth read off the **left brackets**:

| | gap heuristic | connectivity |
|---|--:|--:|
| system count correct | **6/14 (43%)** | **12/14 (86%)** |
| spurious single-staff "systems" | **19** | **0** |

The cause is named in the old code's own comment: its MAD rule deliberately split at
"a clearly-bigger-than-normal gap between bracketed sub-systems (winds vs brass vs
strings)" — but those blocks are *inside* one system. Signal used instead: **a system
break is a gap that no vertical ink crosses** (barlines and the bracket run through a
system; nothing crosses between two), the same fact
`measure_extractor._intersystem_connectivity` already uses one level downstream.

**Bonus: this also recovers the instrument-family grouping** as `Staff.group_index`.
Bridging counts are trimodal — `0` = system break, `~4-25` = bracket-group boundary
(only the bracket crosses), `~35-95` = inside a group. Visually verified on Beethoven 9
p70: two systems, each grouped **4 woodwinds | 2 horns | 5 strings**. That is direct
input to #3, and it means the old detector was finding the right *groups* and
mislabelling them as systems.

Remaining failures (2/14) are **merges** — a real break that something crosses. The old
heuristic fails the opposite way, shredding one system into as many as 12.

**Method warning, worth remembering.** Two attempts at ground truth were wrong before
the bracket crop settled it, and both produced confident numbers: a ground-truth-free
proxy ("instrumentation is constant, so staves-per-system should cluster tightly")
rewards merging everything into one system; and counting systems off a whole-page
thumbnail mislabels single 13-staff systems as 2, because at that scale the
brass-to-strings gap looks like a system break. Render the left margin and count
brackets.

Traps found, each costing a measurement, all documented in the module: `Staff.x_start`
is unusable as a scan window (p60 staff 3 reports 885 against ~275 for its neighbours);
the window must reach *past* the staff extent to see the bracket and the closing
barline; and coverage needs vertical gap-closing or it is resolution-sensitive
(B5 p10 grouped as 2 systems at 300 dpi and 4 at 600).

**RE-MEASURED after merging `recognition-improvement-next` (2026-08-28).** That branch's
comb pass recovers lightly printed staves the ink gates dropped — its headline is that
**Beethoven 5 p10 has 22 staves, not the 18 asserted for months**, because five wind
staves were losing all but one line each and the survivors were grouped into one
phantom. Every number below was re-run on the merged tree:

| | before merge | after |
|---|--:|--:|
| system-count accuracy | 12/14 (86%) | **12/14 (86%)** |
| slot label purity | 93/101 (92%) | **57/57 (100%)** |
| slots with no disagreement | 4/12 | **8/8** |
| staves assigned a slot | 191/207 | **198/217** |

Beethoven 5 p10 at 300 dpi now groups as `[11, 11]` where it read `[11, 7]` before the
recovered staves existed.

The merge also caught a half-built guard: `_looks_merged` spots a concatenation by
seeing an instrument repeat, so it is **blind without labels**, and staff recovery raised
the median system size until the size cap stopped excluding the one page connectivity
merges. The reference came out as 24 unlabelled slots. Fixed with the label-free half —
a merged "system" is a **one-off** while a real full system **recurs**, because the
orchestra is the same on every page.

**Step 2 DONE (2026-08-28): stable slot ids.** `tools/omr/slots.py` +
`Staff.slot_index`. Index matching does not work, because **a system omits the staves
of instruments tacet through it** (Beethoven 9 p65 carries systems of 7 and 11 staves
on one page — the same orchestra, four parts resting). Score order is monotone, so
this is a **sequence alignment**, not a matching problem: each system aligns against a
reference layout by DP, deletions allowed on the reference side, reordering
disallowed. Driven by, in descending strength, instrument labels (a label *conflict*
is the only hard constraint available), bracket group, then relative position.

Reference layout recovered on Beethoven 9 — exactly the real orchestra:

    Flute, Oboe, Clarinet, Bassoon | Horn, Horn, Trumpet, Trumpet | 5 strings

Measured over 12 pages / 207 staves (`benchmarks/omr-system-grouping-2026-08/eval_slots.py`):
**191/207 staves assigned a slot; label purity 92% (93/101)** — of every (slot, label)
observation, the fraction agreeing with that slot's modal instrument. No hand
labelling needed: the labels come from the text layer, and the question is only
whether the alignment keeps them consistent.

**One bad system boundary poisons the whole document**, so guard the reference. The
first run built it from p25 — one of the two pages `system_grouping` merges — and got
a 24-slot reference listing Flute..Trumpet *twice*, after which 20 of 24 slots had an
unstable bracket group. Fixed by rejecting a candidate whose label sequence repeats an
instrument non-adjacently (`_looks_merged`, the precise guard) plus a permissive size
cap for documents with no labels at all. Note the cap must stay permissive — an
earlier 1.5x-of-median cap threw away the genuine full system whenever most systems
were condensed.

Remaining: 16 unassigned staves, all on the two merged pages (a 24- or 18-staff
"system" cannot fit 13 slots), and 8 single-observation label disagreements
concentrated in one misaligned system.

**VERIFIED 2026-08-28 — single-line percussion staves are invisible.**
`_group_into_staves` only accepts five-peak evenly-spaced windows, so a one-line
percussion staff produces no `Staff` at all. Synthetic proof + consequence in
`tools/omr/tests/test_system_grouping.py::test_detect_staves_misses_a_single_line_percussion_staff`:
on a page of 3 five-line staves plus one 1-line staff, the detector returns 3, and
**every staff below the missing one carries a `staff_index` one lower than its true
slot**. Not yet fixed — fixing it means relaxing the 5-peak rule without regressing
staff detection. Track as a slot-numbering hazard for Step 2. (The old "Phase 1 has
no regression baseline" objection is retired — main's 9509990 / e6a4110 corrected
the Phase-1 expectations against the pages themselves.)

### #1 (original framing) — why slots are the keystone
Assign every staff a stable part id across all systems and pages. Signals available
today: y-order, staves-per-system, bracket/brace topology at the left edge
(`system_left_edge()` in `staff_header.py` on branch
`claude/key-signature-recognition-57ec0a` already measures where the bracket ends and
the staff begins), inter-staff spacing, header-window ink signature.

Hard case — **condensed systems**: page 4 has 11 staves, page 5 has 8 because the
winds are tacet, so index 3 is now a different instrument. Naive index-matching breaks
exactly here; this is where a human stops counting and reads the labels (#2b).

Unlocks: clef continuity across page breaks instead of the silent treble default
(`transcribe.py:519`); the dossier plan's `slot→staff` join without hand input;
per-instrument range priors; **and it is the absolute register anchor that #4 turned
out to require.**

### #4c — Clef from the instrument's written range — **SHIPPED 2026-08-28**
`tools/omr/clef_correction.py` + `tools/omr/contextual.py`. The retry of the #4
negative, now that #1 supplies the **absolute register anchor** every earlier
mechanism was missing. A clef hypothesis is a constant diatonic shift of the staff's
pitches (`pitch_resolver.clef_diatonic_shift`), so this is a post-pass over built page
dicts — no image, no re-detection.

Range fit alone is not decisive: a bassoon staff fits bass 1.00 and tenor 0.95 (both
real bassoon clefs), a viola fits alto 1.00 and treble 0.98. So the **instrument's own
default clef leads and the range vetoes it** — the same reasoning a reader uses
("violas read alto, unless what I see says otherwise"). That is sound exactly where
this may act, because it only applies where no reader read the clef, and there the
clef in effect is a positional guess carrying no evidence.

**Complementary with the clef-geometry layer, not overlapping.** Measured on
Beethoven 4 p59 after merging main: main's readers supplied 5 of 11 staves
(`clef_source=detector`), all correct; 6 stayed DEFAULTED to treble. This pass fixed 3
of those 6 — Bassoon→bass (fit 0.06→1.00), Viola→alto, Contrabass→bass — restating 84
noteheads, and touched nothing main had read.

**The integration trap, worth remembering:** the gate must consult
`staff["clef_source"]`, NOT a scan for a `category == "clef"` detection. `clef_locator`
/ `clef_geometry` read a clef by shape and by which staff line it sits on and emit **no
clef detection at all**, so a detection scan calls such a staff "silent" and this pass
would overwrite a confidently-read clef.

Limit: instrument identity comes from the text layer, so this is a no-op on the ~72% of
the corpus without one. That is the argument for finishing #2.

### #2 — Margin reading (instrument names) — **DONE 2026-08-28**
Both halves shipped.

**Text layer (free).** `tools/omr/staff_labels.py` + `instruments.py`. 18/65 IMSLP PDFs
carry an OCR text layer; on those it resolves **79%** of labelled staves (70%
high-confidence). The lexicon maps a printed label to instrument, family, default clef,
written range and transposition (`fifths_offset = -fifths(key_name)`).

**Vision (paid, opt-in).** `tools/omr/staff_labels_vision.py`, wired as
`contextual.apply_contextual_analysis(vision_fallback=True)`. Covers the other 72%.
Measured against the text layer as free ground truth
([benchmarks/omr-margin-labels-2026-08/findings.md](benchmarks/omr-margin-labels-2026-08/findings.md)):
8 systems / 76 staves / **$0.087** → **25 agree, 0 disagree, 30 recovered, 0 missed**,
21 correctly-silent unlabelled staves. **100% agreement where both resolve.**

Cost is bounded by design: identity is a property of the SCORE, and slots propagate one
reading across every system and page, so `vision_system_budget` (default 3) means a few
cents per work rather than per page.

Three design points worth keeping: one call per **system** (the running order makes a
smudged entry legible from its neighbours); the crop carries a **gutter of staff
indices** so the answer keys to our numbering instead of to order, which breaks whenever
strings go unlabelled; and the prompt demands **null** for an unlabelled staff, because
an invented instrument propagates into a wrong clef and wrong pitches.

Does **not** contradict the July VLM NO-GO — that measured symbol *counting* on degraded
cells (89.7% vs a 95% bar). Reading printed words in a clean margin is a different task,
which is why it got its own measurement.

**Still bounded by staff detection.** On Beethoven 4 p59 the crop shows a `Cor. (Es)`
label with no staff tick beside it — the detector missed that staff. Latent signal, not
yet used: *more labels than numbered staves is evidence of a missed staff.*

### #2 (original framing) — why margin reading matters
No OCR anywhere in the project (`backend/requirements.txt` has none). Two paths:
- **PDFs with a text layer — MEASURED 2026-08-28: 18/65 (28%) of the IMSLP corpus.**
  PyMuPDF is already imported (`preprocessing.py:18`) and used only to rasterize.
  `page.get_text()` returns the instrument abbreviations directly — sampled pages gave
  `Fl. / Ob. / Cl. / Fag. / Cor. / Tr. / Timp. / Vl. / Vla. / Vc. / Cb.`, and one gave a
  full instrumentation list: `2 Flauti / 2 Oboi / 2 Clarinetti in C / 2 Fagotti /
  2 Corni in C / 2 Trombe in C / Timpani in C.G / Violino I`. These are OCR'd text
  layers over scans (surrounding music glyphs come out as garbage), but the *labels*
  are clean. With bboxes they join to staves by y-position. **Free instrument identity
  on ~a quarter of the corpus** — do this before any OCR/VLM work.
- **Scans**: crop left of `system_left_edge` → OCR or a VLM call.

Then fuzzy-match a multilingual instrument lexicon (Flauti/Flöten/Fl., Clarinetti in
B, Corni in F, Vcl., Kb.) → canonical instrument → **transposition + expected clef +
range in one lookup**. That single join delivers three of the four deductions.

Caveat: `benchmarks/vlm-vqa-pilot-2026-07` found Claude tops out at 89.7% *counting
symbols in degraded crops*. Reading a printed word in a clean margin is an easier and
different task — but that is an assumption, not a result. The pilot harness is
reusable to test it for ~$1.

### #3 — Score-order prior as constrained alignment
Score order is **monotone** — instruments never appear out of family order. So "which
instrumentation is this?" is a dynamic-programming alignment of the observed staves
against a small library of standard layouts (Classical pairs / Romantic / large late
Romantic / string quartet / piano / lead sheet), **not** free classification. Cheap,
deterministic, and it fuses every weak signal at once: bracket groups, staff count,
margin text, detected clefs, observed register, key-signature offsets.

This is a better shape for the parked SmartScore ensemble idea above: vote on
**instrument identity**, from which clef falls out as a consequence, instead of voting
on clef directly.

### #4 — Key from the music — ⛔ **the clef half is DISPROVEN (2026-08-28)**
Sean's heuristic: *"I can determine a key signature because of the clear repetition of
a root note — it starts and ends on an A, so I look for no sharps and flats, or 3
sharps."* Proposed use: turn key-fit into a **clef** diagnostic (a tonal estimate built
on a wrong clef is confidently wrong).

**Measured and killed.** See `benchmarks/omr-clef-key-fit-2026-08/findings.md`. Four
mechanisms, none beating the trivial always-treble baseline (68.7%): per-staff KS key
fit is noise (median best-vs-2nd margin **0.0000**, 62/80 staves under 0.01);
accidental letters show no circle-of-fifths concentration under any clef hypothesis;
register-ordering scores **56.7%** (12 points *below* baseline); consensus-key fit
scores **exactly** baseline (46/67 both).

Root cause, now confirmed with numbers on real data rather than asserted: **a staff's
note geometry is clef-invariant.** Changing the clef relabels every note by the same
interval and preserves every interval between notes, so contour, interval content and
key-profile statistics all move with the hypothesis and cannot discriminate it. This
is exactly what `docs/dossier-verification-plan.md` §2 already claimed.

**So #4 is blocked on #1, not independent of it** — the absolute register anchor every
mechanism was missing is precisely what instrument identity supplies.

Two retry conditions:
- **Key-signature glyph positions** genuinely *are* clef-dependent (F# sits on the top
  line in treble, the fourth line in bass), but `main` stores only *counts* —
  `_detect_key_sig_from_cell` counts `keySharp`/`keyFlat` and discards positions
  (`transcribe.py:590`). Positional reading exists on branch
  `claude/key-signature-recognition-57ec0a`. **Retry there, not on main.**
- Notehead + accidental recall on dense orchestral pages improving enough that the
  tonal statistics stop being noise.

Still open and untouched by this result: using key context to *interpret accidentals*
once the key is known from elsewhere (that is M4's existing job, just fed a per-staff
key instead of a global one), and inferring the **key signature** itself — Beethoven 5
reads `0 sharps / 0 flats` on all 18 staves when it is in C minor.

### #4b — Infer the KEY SIGNATURE from the music — **OPEN, wanted (Sean, 2026-08-28)**
Untouched by the #4 negative, which killed only the *clef* half. Sean's heuristic:
*"the clear repetition of a root note — it starts and ends on an A, so I look for no
sharps and flats, or 3 sharps."*

Live evidence that this is a real, unflagged error class:
- **beethoven-5 p15 reads `0 sharps / 0 flats` on all 18 staves** — the movement is in
  C minor (3 flats), and there are 33 inline flat detections on the page.
- **ravel-bolero p10 reads five different signatures across 32 staves** (0,1,2,4,5
  sharps) for a piece in C major. The shipped check (b) catches only **1** of them.

Why it is a different problem from #4, and more tractable: the key signature is a
*global* property corroborated by many staves at once, so cross-staff voting applies
(check (b) already has the transposition machinery), whereas the clef is per-staff and
clef-invariant in the geometry. Candidate signals: inline-accidental letter statistics
aggregated over a whole page rather than one staff; a flat:sharp ratio far from
balanced implying the signature is missing accidentals; tonal frame of the lowest
staff. **Do not reuse per-staff KS profile fitting — measured as noise (#4).**

Prerequisite worth checking first: whether the failure is *reading* the signature or
*detecting* the glyphs at all (beethoven-5 has 1 `keySharp` detection on the whole
page, so it is likely detection, in which case the fix belongs with the positional
key-signature reader on `claude/key-signature-recognition-57ec0a`).

### #5 — Auto-populate the dossier
`docs/dossier-verification-plan.md` requires hand-input facts. #1–#3 make it
self-populating: derive the instrumentation from the score, ask Sean only to
confirm/correct — the same model-proposes / human-adjudicates loop as the annotate UI.
Plus title-page text → work lookup → measure counts and key plan (the parked GKB item).

### Training-side note — can YOLO be trained on context? Mostly no.
The pipeline feeds YOLO **canonical cells**: each measure sliced out and rescaled so
staff span is constant. That normalization buys scale invariance and 98.8% F1 and it
**destroys exactly the context in question** — margin label, neighbouring staves, page
position, everything before this bar. A per-cell detector cannot learn what it never
sees. Three fine-tune campaigns already failed (catalog training collapse; ScoreAug
worse than clean control; clef fine-tune cratering dense-page noteheads 2506 → 114).

What is *not* dead:
1. **A separate small model on a different input** — a header/margin reader trained on
   crops that actually contain context. Never touches production weights, so it
   structurally cannot cause forgetting. The clef-ft post-mortem already named this.
2. **Contextual re-scoring with the detector frozen** — everything below conf 0.25 is
   currently discarded and only the argmax class survives. Keep the pre-NMS candidates
   and let the contextual layer re-rank. M4 does this for pitch; extending to *class*
   is the same trick at zero training risk.
3. **End-to-end sequence models as a second opinion** (LEGATO / oemer / homr) — they
   read clef and meter contextually by construction. Host-side, not a replacement.

### Structural bugs noticed while surveying
- ~~five-line-only staff detection~~ — **VERIFIED, see #1 above.**
- Nothing excludes unpitched/percussion staves from the key and pitch checks
  (still unverified).

---

## ⏰ REVISIT — ensemble recognition for clef + detail prediction (2026-07-10)

> **PARTLY OVERTAKEN (2026-08-27).** The clef half of this turned out not to need
> an ensemble at all. Alto vs tenor (and soprano/mezzo/baritone) is not a
> recognition problem — they are the same glyph on different staff lines, so no
> number of classifiers voting on appearance can resolve it. Measuring the
> glyph's position does, exactly. Shipped as `tools/omr/clef_geometry.py` plus a
> classical-CV C-clef locator for scores where no model sees a clef at all;
> results in `benchmarks/omr-clef-geometry/RESULTS.md`. **Still open from this
> item:** the *time-signature* half, and clef/key/time state resets across pages
> (the continuation-page clef inheritance is handled by `_ClefContinuity`, but
> the underlying detection weakness is not).

**Sean flagged this and asked to be reminded to come back to it (dated reminder set ~2026-07-17).** **SmartScore 64 Professional** (Musitek) uses an **ensemble recognition tool** specifically to help predict **clefs and other details**. Investigate how it works and consider adopting the technique.

**Why it's worth doing:** the July 2026 audit found clef handling is a real ReEngrave weakness — clef/key/time state resets across pages and relies on the detector catching courtesy clefs; a missed continuation-page clef silently defaults to treble (or bass for staff 2 of 2), shifting every pitch on that staff. Time-sig digit detection is similarly unreliable. A voting/ensemble predictor for these fields would target both directly.

**Note the distinction:** this is an *internal* ensemble (several classifiers/heuristics voting on ONE field like clef), NOT the multi-*engine* OMR voting from the July research (Padilla et al. ISMIR 2015), which was skipped because ReEngrave has only 2 unequal engines.

**To resolve when we pick this up:**
- Research how SmartScore 64 Professional's ensemble recognition actually works before designing anything.
- Decide the cheapest ReEngrave adaptation: a per-staff clef-stability + key-signature-plausibility re-rank pass (no new model) vs an actual classifier ensemble; check whether the same voting extends to time-sig digits.

---

## ~~Staff detection on mixed text/music pages~~ — DONE (2026-08-28)

Body text was being detected as staves (147 of 1522 "staves" over 156 pages of
Nottebohm). Fixed in `staff_detector._line_ink_runs_per_space`: a staff line is
one continuous stroke (a handful of ink runs over its whole length, even
dashed), a text baseline is one run per letter. Music tops out at 1.39 runs per
staff-space, text starts at 2.02, medians 0.017 vs 2.59.

Every music-only score is byte-identical; prose pages now yield zero staves,
and p.92 went from 0 barlines / 12 cells to 10 / 26 because dropping the text
blocks let system grouping and barline voting work again.

**Two plausible discriminators that DON'T work** — don't re-propose them:
- *Ink coverage along the line.* Separates on clean pages, overlaps on real
  ones: notation ink interrupts the line, so genuine Beethoven 5 / La Mer
  staves fall to 0.62-0.70, on top of body text at 0.62-0.72.
- *Staff span vs the page median* (which this note previously recommended).
  Works only on mixed pages — on unbroken prose the median is itself
  text-derived and nothing is an outlier.

> **The related x-extent half is also fixed, twice over and on purpose.** This
> note used to pair the text-as-staves problem with `_staff_x_extent` returning
> the longest strictly-contiguous ink run, so the measure cell began past the
> clef. Both fixes are now in and they are complementary, not duplicates:
>
> - `staff_detector._staff_x_extent` now bridges breaks up to a staff space, so
>   Phase 1 returns the real extent and the cell contains the header again
>   (6/12 → 12/12 clefs on the Nottebohm ground-truth page).
> - `tools/omr/staff_header.py` measures each staff's header WINDOW beside
>   Phase 1 — left edge walked back to the system's initial rule, right edge at
>   the first barline. It was written when the Phase-1 fix looked too risky to
>   attempt without a regression baseline, and it stays because the CV readers
>   want a tight crop that Phase 1 has no reason to produce: the key-signature
>   locator reads that window, and the clef readers fall back to it only where
>   the measure cell still starts past the header, which the Phase-1 fix now
>   makes rare rather than routine.
>
> The regression baseline that blocked the Phase-1 change was itself built in
> the same round (`test_pipeline` expectations checked against the pages), so
> the reason for working around Phase 1 no longer applies to future work here.

Also: the first measurement pass labelled p.25 and p.29 as "text" when both
contain music examples, which made the separation look marginal. Check page
contents by eye before trusting a distribution built from them.

## Score library — eleven works still to find (2026-09-01)

The central library holds 235 editions and 1745 reference encodings, but eleven
works on the wantlist never resolved: `build_wishlist` guesses an IMSLP page
title and falls back to the search API, and for these neither matched. They are
not absent from IMSLP — they are filed under names the guess missed.

    Beethoven   Leonore Overture No.3        Ravel        Ma mere l'Oye
    Vivaldi     The Four Seasons             Boulanger    D'un matin de printemps
    Brahms      Double Concerto Op.102       Boulanger    D'un soir triste
    Rimsky      Russian Easter Overture      Coleridge-Taylor  Hiawatha's Wedding Feast
    Janacek     Sinfonietta                  Saint-Georges     Symphonie concertante
    R. Strauss  Sinfonia Domestica

Find each id by hand, then `python3 -m tools.library.ingest imslp <file>` — the
ingest does the rest. The full list, with what IS held, is
`data/score-library/wishlist.md`.

Four editions carry no publisher because they were imported from local files
rather than IMSLP (two Handel *Messiah*, Kirchhoff, the unidentified Mahler 5
scan); `ingest set` can correct them if the edition is ever identified.

---

## YOLO training via symphony MusicXML × multiple IMSLP editions (2026-05-23)

**OUTCOME (2026-05-25): EXECUTED AND CONCLUDED — training part failed.** This idea was carried out as Phases A–L on branch `claude/interesting-curran-3ca1b7` (43 commits, never merged). The catalog/label-generation half worked (65/65 IMSLP editions aligned, 154k labels across 26 movements), but every training attempt on those labels collapsed the model (Phases H, I, J, K, L — including after fixing a ~50px x-offset and remapping class IDs to DSv2-free slots). Verdict: catalog-augmented YOLO training is a dead end with this recipe; structure stays with classical CV, symbol improvement comes from hand-labeling. Full story: PROJECT_STATUS.md → "The catalog-training experiment". The publisher/era research question below remains open but is no longer hooked to an active pipeline.

**Original idea**: avoid hand-labeling ~500 cells for measure-line detection by using existing symphony MusicXML as ground truth, then pulling every available PDF edition of those same symphonies from IMSLP and training YOLO to detect structural elements (measure lines, stems, rhythms) by comparing detections against the XML.

**Why it works for structural elements**:
- MusicXML *is* authoritative for measure boundaries, stem direction, rhythm.
- Sean already has the MusicXML for the symphonies in question — no labeling cost.
- IMSLP has multiple engraved editions of the canonical symphonies (Beethoven, Brahms, etc.) — instant data multiplier per work.

**Limits to remember**:
- MusicXML will likely be missing dynamics, expression marks, articulations, technique markings, and other notation the original score has. This pipeline is **only** useful for the structural classes the XML can verify. Dynamics / expression / technique training still needs another approach.

**Publisher/era as a transfer-learning axis**:
- Track edition, publisher, and publication date metadata per training PDF.
- Hypothesis: a model trained on, e.g., all Beethoven symphonies engraved by Breitkopf & Härtel in 1862–1890 will generalize to *other* composers' symphonies engraved by the same publisher in the same window — engraving conventions track the publisher/era, not the composer.
- This implies the training pipeline should be sliceable by publisher × era, not just by composer.

**Action item (research, no code yet)**:
- Investigate the major score publishers across symphonic repertoire and their active windows. Goal is a categorization scheme: publisher → era → engraving style. Likely candidates to map: Breitkopf & Härtel, Peters, Schirmer, Eulenburg, Universal Edition, Bärenreiter, Henle. For each: when active, what they engraved, distinguishing visual conventions.

**Status**: parked. No action this session — Sean wants this brought up next time he's actively working on ReEngrave.

---

## Plans surfaced 2026-05-24 from past sessions

Sean asked to recover suggestions he'd made across past YOLO-era sessions that hadn't carried into the current plan. The seven below are the ones that were absent or under-documented. Quotes are verbatim from his sessions.

### 1. Maestro Analyzer as a theory-constraint layer over OMR (highest leverage)

**Status (2026-05-24): SHIPPED M0–M4.** See [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md) for the full picture. All five scholarly seed works curated. M4 in-pipeline pitch re-ranking with auto-correction is live (env-gated). Two follow-up bugs surfaced during the handel-leadsheet audit and are tracked below as separate items.

### Follow-up A — `tools/omr/export.to_musicxml` writes `<measure number="1">` for every measure

**Status: FIXED 2026-05-24.** Added "fragmented row" detection (system with >2 staves where each has exactly 1 measure) — those staves are now emitted as one part with sequential measure numbers. Piano grand-staff and orchestral systems unchanged (still share measure numbers across parallel staves). A page-global running counter ensures subsequent systems continue numbering correctly. handel-leadsheet now produces 32 distinct measure numbers; maestroAnalyst can do per-measure key resolution.

### Follow-up B — M4 candidate selection over-prefers enharmonic spellings

**Status: FIXED 2026-05-24.** Re-rank.ts now filters candidates by both pitch-class AND natural-spelling membership using maestroAnalyst's `preferredSpelling(pc, key)`. Wraps minor keys via `relativeKey()` first because maestroAnalyst's preferred-spelling tables only cover major keys (so D minor's pc 10 was returning "A#" instead of "Bb"). The bach-wtc F# → E# and G# → A# enharmonic mis-corrections are eliminated.


**Idea**: wire the existing `gradus-vercel/lib/maestroAnalyst/` TypeScript engine into ReEngrave as a *constraining* layer over YOLO output, not just as a post-hoc validator. Narrow ambiguous pitches by key + modulation + chromatic context; validate range; suggest enharmonic spellings. The MaestroAnalyst already covers cadence, enharmonicSpelling, keyDetection, modalAnalysis, pcSet, phraseSegmentation, pitch, pitchTendencyTags, rangeValidation, reduction, romanNumeral, scale, voiceLeading, xmlParser.

**Quotes**:
- "use a tool like maestro ananlyzer and determine what the potential notes couldbe based on key and even what chromatic notes would be more likely based on where the music is going by understanding modulations and the theory that is used to get there" (cool-kare)
- "I want to improve the maestroanalyzer to replace the music21 mcp by adding these functions: range validation, enharmonic spelling, xml parsing, basic pitch utilities" (jolly-noether)
- "Dose it make sense to add any access to the maestro analyzer or to the gradus vercel GKB for knowledge access to help" (hopeful-mayer)

**Current state**: not integrated. `grep maestro` in `backend/` and `tools/omr/` returns nothing. The only theory pass is reactive (`backend/modules/score_comparison.run_theory_checks`) and runs against the *final* MusicXML, not during OMR.

**What's needed to move**: decide on the integration shape — Python ↔ Node bridge vs. port the relevant analyst modules to Python vs. expose maestroAnalyst as an HTTP service. Then add a re-ranking step after `pitch_resolver` that takes the top-N candidates per notehead and asks maestroAnalyst to pick.

---

### 2. GKB (Gradus Knowledge Base) access for OMR context

**Idea**: let OMR query the GKB at gradus-vercel for context (composer/period/expected harmonic vocabulary) when transcribing.

**Quote**: "also use GKB at gradus vercel in any way that it is helpful" (jolly-noether)

**Current state**: Gradus *library* (reference MusicXMLs) is wired into ReEngrave for comparison; the GKB knowledge layer is not.

**What's needed**: bounded by item 1 — once the maestroAnalyst bridge exists, GKB access is the natural follow-on.

---

### 3. Expand training data: DoReMi + MUSCIMA++

**Idea**: don't stop at DeepScoresV2 — also train on Steinberg's DoReMi and MUSCIMA++ to broaden the model's exposure.

**Quotes**:
- "what about using a DOREMI baseline like steinberg's? https://github.com/steinbergmedia/DoReMi/releases/tag/v1.0" (objective-kare)
- "what other training can we do? more symbols from deepscore? DOREMI? MUSICIMA+++?" (objective-kare)

**Current state**: only DSv2 is in `tools/omr/training/`. DoReMi + MUSCIMA++ are not referenced anywhere.

**What's needed**: download + class-map both datasets, fold them into `prepare_yolo_data.py` and `build_catalog_yaml.py`. Re-train.

---

### 4. RTMDet / yolov8x@200ep escalation path

**Idea**: production weights are yolov8l@30ep — Sean approved the "all-the-way" run when ready.

**Quotes**:
- "I want to do this all the way full data set, yolov8x +200 epochs + the works. I can add more funds now or later but the rough estimates are ok with me" (cool-kare)
- "When we get to phase 3 should we use rtmdet instead of yolov8?" (cool-kare)
- "does our plan include using an anchor based object detector or checkpoints from github?" (objective-kare)

**Current state**: documented checkpoints stop at yolov8l-imgsz2048-ft-30ep. No RTMDet / yolov8x experiments are scheduled.

**What's needed**: define the comparison protocol (same verdict set, same imgsz) and budget a cloud run.

---

### 5. Multi-type barline classification

**Idea**: barlines aren't a single class — Sean explicitly wants single bar, double bar, final bar, and repeats distinguished. Currently classical CV detects "a barline" but not which kind.

**Quote**: "would it be bad to have a single bar line, double bar line, final bar line and repeats?" (objective-kare)

**Current state**: Phase 3.4 attempted barlines as a custom YOLO class and caused catastrophic forgetting. Currently: classical-CV barline detection, no type distinction. (See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.)

**What's needed**: either (a) post-process the classical-CV barline by inspecting pixel patterns to the left/right (double = two thin lines; final = thin + thick; repeat = thick + dots), or (b) re-introduce as YOLO classes once 200+ examples per type are labeled.

---

### 6. MusicXML repeat signs

**Idea**: MusicXML doesn't natively encode repeat marks the way humans see them — currently the export drops them.

**Quote**: "Mxl does not account for repeat signs - flag for follow up" (interesting-curran)

**Current state**: no handling in `tools/omr/export.to_musicxml()` or in the catalog labeler.

**What's needed**: detect repeats during OMR (tied to item 5) and emit `<barline location="left"><repeat direction="forward"/></barline>` etc. on export.

---

### 7. Confirm "just ink" as a label class

**Verified 2026-06-10: the annotate UI does NOT expose a noise/ink class** — the picker is the DSv2 208-class vocabulary only. The current doctrine covers most of the need by omission: dropped FPs / unboxed bleed become hard-negative background (see CLAUDE.md → "Ink-bleed / mostly-FP cells are GOOD"). Revisit an explicit "noise/ink" class only if hard-negative-by-omission proves insufficient after the v2/v3 retrain.

**Idea**: label noise/ink-artefacts explicitly during hand-labeling so the model learns to ignore them, instead of leaving them unclassified.

**Quote**: "It might be helpful also just to classify ink" (objective-kare)

**What's needed if revived**: add a "noise/ink" category and update `verdicts_to_yolo_labels.py` to either drop or remap those during YOLO label emission.
