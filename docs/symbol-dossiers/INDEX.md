# Symbol dossiers — the index, and what falls out of them

**2026-09-20.** Eleven dossiers, one per family, one section per symbol, each
answering Sean's five questions. Written from the tree and committed records;
eleven small read-only probes, no transcribe run, no battery, no OMR-NED.
**Nothing was fixed.** This file is the cross-reading.

| dossier | symbols | lines |
|---|--:|--:|
| [noteheads](noteheads.md) | 7 | 1,239 |
| [stems-beams-flags](stems-beams-flags.md) | 6 | 1,131 |
| [rests](rests.md) | 9 | 1,146 |
| [accidentals-keys](accidentals-keys.md) | 8 | 897 |
| [clefs](clefs.md) | 6 | 845 |
| [meter](meter.md) | 6 | 1,028 |
| [arcs](arcs.md) | 6 | 927 |
| [dynamics](dynamics.md) | 12 | 1,345 |
| [articulations-ornaments](articulations-ornaments.md) | 13 | 1,224 |
| [structure](structure.md) | 13 | 1,644 |
| [text](text.md) | 10 | 1,254 |

## 0. This is the fourth time the question was asked — the other three

The dossiers cite these rather than restate them. Read them together.

| when | Sean's question | where the answer went | which of the five |
|---|---|---|---|
| 2026-09-04 | *"slurs and ties look exactly the same — what makes them different are the notes they connect"* | [`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md) — by **mark**: dot, arc, wedge, stroke, digit, blob | Q1 |
| 2026-09-17 | *"are we collecting both the ink shape and the location … before the staff is removed or after, or both?"* | `tools/omr/staged/capture.py` — per family: shape / position / raster | Q2, Q3 |
| 2026-09-17 | *"give the families real position information — or if it should be symbol specific then make it so"* | [`benchmarks/omr-family-positions-2026-09/`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md) + `staged/positions.py` — ten producers, no consumers | Q3 |
| 2026-09-20 | the five questions, per symbol | these dossiers | all five |

The confusables document is organised by mark and the dossiers by symbol, and
that is the point of having both: **the same fact read from the two ends
disagrees in six places** (§5), and each disagreement is a finding.

## 1. The order — what Q5 says, symbol by symbol

Sean's principle: *lean into what we know more to help us with what we know
less.* The dossiers answer Q5 for every symbol, so the order is derived, not
argued. Three tiers fall out.

**Tier 1 — things everything leans on.** In descending certainty:

| mark | what leans on it | how well it is read | the catch |
|---|---|---|---|
| the staff grid | every pitch, every bar | best-measured thing in the project (tilt trace priced on 20 rows) | `Q.SYSTEM_MEMBERSHIP` is decided and **read by nothing**; the per-gap evidence is computed and not recorded |
| noteheads | stems, arcs, dots, articulations, ownership | recall 0.98 on a scan; **precision is the fault** | a *missing* head is a counted gap; a *wrong* head recruits a stem, an arc end and a dot and nothing may doubt it. 459 of 576 wrong Breitkopf boxes are in ONE bucket — too tall — which the print reads 12 of 12 as a vertical stroke |
| the clef | every pitch, the key signature | 92% end to end, from the detector alone | its three declared second witnesses (label, range, implied pitches) are declared and not run; the staged path **drops every C clef** the detector reads |
| the measure partition | every bar sum, every measure number | 17 of 20 scan rows | the ordinary one-staff barline has **never been print-adjudicated** (Sean's test sampled the tall ones, ~8%) |

**Tier 2 — things that lean on Tier 1 and are leaned on in turn.**
Accidentals and keys (lean on the clef; feed pitch), stems and beams (lean on
noteheads; feed duration), rests (lean on the meter; feed the meter — the one
sanctioned loop, and the whole-rest exclusion that keeps it honest also blinds
the meter-change check).

**Tier 3 — leaves. Nothing downstream reads them.** Arcs, articulations and
ornaments, dynamics and hairpins, text. Confirmed by grep in each dossier: no
EVALUATE consequence, no INFER rule, no other adjudicator reads their verdicts.
They can be done in any order and nothing waits on them.

**Last — the meter.** Not because it is read badly, but because **no witness
on the staged path is independent of the raster**: the bars go silent where
they are needed (0 of 7 on the `9/4` system), cross-staff agreement is
unanimous on the wrong answer, the cautionary is independent but there are
three in the corpus, and the dossier — the only off-raster witness — has no
producer on the staged path.

### ⚠️ The thing four dossiers found independently

Noteheads, stems, structure and articulations each arrived at the same mark
from a different direction: **the vertical stroke** — stem, barline, an
accidental's upright, an arpeggiato, a clef fragment. It is the notehead
family's precision fault (the too-tall bucket), the stem family's largest
false population (476 barlines), the structure family's unadjudicated 92%, and
the articulation family's 377 `arpeggiato`. The confusables document files it
as *"already solved; the precedent"*. On this tree the mechanism it names runs
only on systems of fewer than three staves, on the evidence of four braced
piano systems.

**So the first thing to sweep is not a family. It is one mark, in the page
frame** — and the page-frame reader (`vertical_runs_page.py`) landed on 09-20
and names nothing. That is where "noteheads first" actually begins: the
noteheads we can trust are the ones whose vertical neighbour we have named.

## 2. What the dossiers found across families

**a. "Shipped" means the legacy path.** Five rules the documents describe as
shipped exist only in `transcribe.py`: the clipped-fragment filter, the
no-ledger-rung filter (noteheads); the phantom-stem-in-ornament filter
(articulations); key-signature corroboration (accidentals — CLAUDE.md calls it
default-ON; the staged path does not import it); the brace-centred margin block
(text — on one branch, 1,222 commits behind). **The staged reader is
systematically weaker than the documents say, by one or two filters per
family.**

**b. Producers with no consumers.** All ten family-position facts; `Q.INK`;
`Q.SYSTEM_MEMBERSHIP`; `Q.GROUP_SYMBOL`; `Q.REST_POSITION`; `Q.ARC_POSITION`;
`Q.METER_GLYPH_POSITION`; the meter template's `score` / `runner_up`; the
hairpin's direction evidence (computed, discarded); `Q.STAFF_SKEW.thickness_px`
(the tenuto/ledger discriminator, measured twice, compared by nothing);
`measure_ledger_rungs` (correct, detector-free, consumed by the labelling UI
only). *The value existed and nothing read it* — eleven more instances.

**c. Decisions that cannot say "I don't know".** The arc's kind (the detector's
class *is* the answer); the hairpin's direction (one comparison, no margin);
every rest's class and every notehead's class (observed as fact in GATHER);
the tuplet (its docstring states a positional gate, its body has none). Sean's
own ambiguity floor for arcs — *default to tie, the safer error* — is
unimplemented, and Mozart 41 says the safe direction is page-dependent.

**d. Contests decided by distance alone.** The cross-staff ownership contest
has a ledger-ladder tier for noteheads and nothing for anyone else. 198
accidental contests and every dynamic-letter contest are decided by distance
— the coin flip the project has measured four times. And the range veto has no
category guard: handed a dynamic letter it would turn the letter's height into
a pitch. Inert only because `Q.INSTRUMENT` abstains 75 of 75.

**e. Symbols with no route at all on the staged path.** Grace notes (a small
head becomes a full quarter and steals a beat); ledger lines and augmentation
dots (no quantity of their own); tuplets 1, 2, 4–9; tremolo; in-bar
accidentals (all five classes, and the scope span); `clef8` / `clef15`;
the mid-staff clef change; `brace`, `repeatDot`, `segno`, `coda`,
`ottavaBracket`; `arpeggiato`, `caesura`, bowings, pedal; the metronome mark,
measure number, rehearsal letter, lyric; fingerings 0/1/2/4/5.

## 3. Defects found and deliberately NOT fixed — the repair list, ranked by what a cleanup pass would feel

1. **Key-altered notes export as unaltered pitches wearing a printed
   accidental.** In the artefact Sean read: `<alter>` 0, `<accidental>` 334. An
   E♭ in three flats is written *E natural with a flat drawn on it* — prints
   right, sounds wrong. (accidentals-keys)
2. **The staged exporter writes no `<beam>`.** In MusicXML no beam *is* a flag,
   so every beamed note comes out flagged. Not on the known-gaps list. (stems)
3. **The staged gatherer drops every C clef** — it accepts the coarse name the
   detector never fires. 8 of 99 clef detections, 100% of the C clefs and octave
   marks. The coverage tool reports the family green. (clefs)
4. **A grace note is a full quarter** on both paths. Latent: the detector fires
   none today. (noteheads)
5. **The tuplet decision has no positional gate** in its body — members are
   every notehead in the cell. Zero firings in 286 runs. (stems)
6. **`gather_coverage`'s class list is a 146-name snapshot**, not the shipped
   208; it reports six dynamic classes that cannot fire and misses the six that
   can. (dynamics)
7. **`Q.BARLINE_COLUMN` is a count of cells**, not the fitted barline its own
   comment claims. (structure)
8. **`capture.py` still spells a stem `x, y0, y1`** — the convention `record.py`
   records as refuted on 400 of 400 rows. A comment, but the exact one that
   cost a lane a run. (stems)

Items 1–3 are wires, not rebuilds.

## 4. Documentation that is wrong, found by grep

| claim | where | the tree says |
|---|---|---|
| F-clef dot veto: 5 false positives, 20 declined | CLAUDE.md | reverted same day; shipped setting is **13** |
| key-signature corroboration is default-ON | CLAUDE.md knobs | legacy path only; staged imports it nowhere |
| direction lexicon is "181 musical terms" | three places | **156** strings; never was 181 |
| brace-centred margin block SHIPPED, +11 labels | its own FINDINGS | on one branch, not on integration or main |
| *"the bracket encloses exactly the system"* | CLAUDE.md | false on 2 of 5 held editions |
| stem vs barline *"already solved; the precedent"* | confusables doc | scoped to <3-staff systems; four piano systems of evidence |
| A-DUR-6: tempo word blocked on `direction` being a stub | ASSUMPTIONS.md | `stubs()` is `()` |
| Litolff p.62 meter change at cell 8 | `report_boundary.TRUTH_CHANGES` | the print changes at cell 6, where the detector fires nothing on 17 of 17 |

## 5. Where the dossiers disagree with the three prior documents

Against `position-grammar-confusables-2026-09-04.md`:
- **No REST entry**, though whole-vs-half (hangs vs sits) is the cleanest case
  of its own principle. (rests)
- **No BEAM, FLAG or TREMOLO entry.** (stems)
- **The clef body is only ever an anchor**, never a confusable — yet its
  fragments read as C clefs and its ink spells meters. A TALL GLYPH row is
  proposed. (clefs)
- **Accent vs hairpin is refuted on this corpus**: 1 of 96, and that one a
  crescendo. The shipped discriminator is isolation, not span. (dynamics)
- **Its DOT entry omits the after-a-rest role** the legacy pairing has always
  handled. (rests)
- **The ARC discriminator's two halves do not behave alike** — the provable
  different-pitch half is −4 edits, the inferred span half is edit-positive.
  (arcs)
- **Tenuto vs ledger: the alphabet says the rung *matches* staff-line
  thickness; the literature registry says 23% heavier.** The measurement that
  decides it is on the record, unread. (noteheads, structure)

Against `family-positions` and `capture.py`:
- The position sweep **never reached one structure symbol** and never reached
  stems, beams or flags — three of the six symbols in that family have no
  position quantity. (structure, stems)
- The HEIGHT half of a meter size gate is **refuted** by the position facts
  themselves (the Litolff fragments are 4.16 / 4.34 steps against a real
  digit's ~4); only WIDTH / ASPECT survives untried. (meter)

## 6. The decisions that gate work — consolidated from ~75 questions

The eleven files end with seventy-odd questions for Sean. These are the ones
whose answer changes what gets built; the rest are in their dossiers.

1. **The anchor with a declared domain.** Should the sweep anchor on noteheads
   as a whole, or only on heads that have a read stem? The second is
   measurable today; the first is not. (noteheads Q1)
2. **The vertical stroke as a decision.** *"Is this vertical mark a barline / a
   stem / an accidental's upright / something else?"* — built as one decision
   that can abstain, reading the page-frame runs. And the Friday question inside
   it: the accidental's stroke belongs in the domain of *what kind of vertical
   mark is this*, not in a rule whose only outcomes are *stem* and *deleted*.
   Agree? (stems Q2, structure Q7–8, noteheads Q7)
3. **The pair rule.** Its justification is a page total on a sheet that prints
   no accidentals; per bar it empties a bar of four chords. Retire, or
   re-justify on a page that prints accidentals? (stems Q1)
4. **Repair list items 1–3** — wires, not rebuilds. Now, or after the sweep?
5. **Arc kind: gap or wrong mark?** Should `arc_kind` be allowed to abstain,
   given a refused arc writes nothing? And is *default to tie* still the rule
   when Mozart 41 inverts it? (arcs Q1–2)
6. **`OMR_CV_HAIRPINS`**: 136 recovered : 53 invented, the two instruments
   disagreeing. (dynamics Q2)
7. **The one-line percussion staff**: +65 metric edits, and while it is off
   every staff below a percussion rule carries the wrong ordinal. (structure Q6)
8. **Which vocabulary does your repertoire actually print?** Half rests (4 in
   1,674), tuplet 6 (6-in-4 or 6-in-3?), cancellation naturals, multi-bar
   rests, ottava, repeats, rf/rfz and niente, grace notes, octave clefs. Each is
   one answer from you that closes or parks a class. (rests, stems, accidentals,
   structure, dynamics, noteheads, clefs)

## 7. What is not established

Every dossier says it in its own words. In one sentence: **almost every
figure here is the pipeline agreeing with itself.** Print-adjudicated: 255
notehead boxes, 126 arc cells, 19 barlines, the bracket blocks, the 75-staff
key page, the 158 label contradictions. Nothing else — no rest value, no
accidental, no dynamic, no hairpin, no articulation, no direction word, no
inferred note — has been checked against a print. n is 2 publishers and 8
scanned pages for nearly everything, one adjudicator, and on Litolff ~60% of
noteheads cannot be adjudicated by eye. No OMR-NED figure is claimed anywhere,
deliberately.
