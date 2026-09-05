# One part per REFERENCE part, from a condensed printed staff

2026-09-04. Based on `a78c9454` (the slot-stitching merge on the integration
line). Branch `claude/condensed-parts-split`.

A conductor's page CONDENSES: Beethoven 5 is engraved on twelve staves and its
reference MusicXML holds eighteen parts, because `Flauti` share a staff and the
file does not. `benchmarks/omr-staff-structure-2026-09/FINDINGS.md` attributed
**87% of the scan benchmark's `entire staff insert/delete` bucket** to exactly
that, with our detection *correct* — musicdiff charges every unmatched
reference part as a whole staff.

Two things came out of this sitting, and they point opposite ways:

* **The split is the largest single lever measured on the scan corpus.** With
  the count supplied perfectly it is **−4,195 edits** (34,962 → 30,767, 12% of
  the pool) and takes `entire staff` from **8,453 to 2,775**. With slot
  stitching on as well, **−4,557 / ES 2,060**.
* **The count cannot be inferred from the page.** Whether a reference splits a
  condensed staff is a property of the ENCODING, and the same printed label
  `Flauti` is two parts in one reference and one in another. The label rule
  costs **+2,181 edits on Dvořák alone** — the corpus's only two structurally
  exact rows. Shipped default OFF for that reason.

---

## 0. The premise it was dispatched on is FALSE, and that changes the framing

`benchmarks/omr-vs-industry-2026-09/FINDINGS.md` Addendum 4 read Audiveris's
part counts off cost arithmetic and concluded it "emits exactly 22 parts from
Brahms p2's 14 printed staves — the reference's own count. **It splits condensed
staves into parts**; that, not stitching, is why its structural cost collapses
on multi-system pages. So condensed-staff part-splitting is *competitive
ground*."

The exports are on disk. `probe_audiveris_parts.py` opens them
(`audiveris-parts.json`) and adds the discriminator a part COUNT cannot carry —
how many measures each part spans:

| row | systems | printed staves | Audiveris parts | truth parts | measures/part |
|---|--:|--:|--:|--:|---|
| beethoven 984073 p1 | 1 | 12 | **12** | 18 | [15] |
| beethoven 575951 p1 | 1 | 12 | **12** | 18 | [15] |
| dvořák p5 | 1 | 15 | **15** | 15 | [8] |
| dvořák p6 | 1 | 15 | **15** | 15 | [7] |
| mahler p2 | 1 | 17 | **17** | 38 | [9] |
| mahler p3 | 1 | 13 | 12 | 38 | [8] |
| beethoven 984073 p2 | 2 | 11 | 15 | 18 | [29] |
| beethoven 575951 p2 | 2 | 11 | 16 | 18 | [31] |
| brahms p2 | 2 | 14+13 | 22 | 21 | [13, 14] |

**On five of the six single-system rows Audiveris emits exactly one part per
printed staff, and on the sixth it emits one FEWER.** It never splits a
condensed staff — on Mahler p2 it emits 17 against a truth of 38 and pays the
same floor we do, to the edit.

Its 22 on Brahms p2 are not a condensation split. Every one of those parts spans
13–14 measures on a page whose two systems hold ~15 measures between them, and
the part names repeat the wind section twice (`Fl. … Fag.` at P1–P8,
`F1. … Fag.` again at P9–P12) — it read the two systems as one tall system and
emitted a part per (system, staff). That is the SAME mechanism as our stitch
refusal, with luckier arithmetic: 22 fragments happen to pair against 21 truth
parts better than 14 continuous parts do.

⚠️ **So condensed-staff splitting is ACCURACY, not competitive ground.** Item 1
of the staff-structure session's own ranked reading said so ("Audiveris pays
this floor identically on every single-system row … closing it is worth
accuracy, not competitive ground"); the part-count reading in Addendum 4
overturned that, and the files overturn the part-count reading back. The work
below is still the biggest lever on this corpus, but it does not close the gap
against Audiveris, which sits on fragmentation.

---

## 1. The truth convention: a condensed staff DUPLICATES

Before designing a split, read what the reference actually holds.
`probe_truth_convention.py` (`truth-convention.json`) classifies every
(condensed staff × measure) in every row's window, over the parts `works.json`
hand-maps to that staff:

| | share | what the page prints | what a split must do |
|---|--:|---|---|
| **silent** | 51.5% | one staff of rests | rests in every part |
| **divisi** | 27.6% | a chord, or two stemmed voices | one voice per part |
| **unison** | 18.3% | one line of notes | the SAME notes in every part |
| solo | 2.6% | one line (`a 1`, `1.`) | notes in one, rests in the other |

**silent + unison = 69.8% is exact DUPLICATION** — copy the staff's content into
all N parts and the reference is reproduced note for note. That settles the
question of what to do with a single-voice condensed staff: duplicate, because
that is what a section staff MEANS and what the file records. It is not
intuition; it is the majority of the corpus.

The remaining 27.6% is where a chord we read whole goes into both parts. That
costs extra NOTES, not a missing PART — a far cheaper charge — and every number
below is measured with that approximation in place, so they are a floor for the
idea and not a ceiling. Splitting divisi by stem direction (`voicing.py` already
separates those voices) is the obvious next increment and is NOT built here.

---

## 2. The split, and where it may be made

`export.to_musicxml`, behind **`OMR_CONDENSED_PARTS`** (default off). A staff
carrying `condensed_parts: N > 1` is emitted as N `<part>`s named
`<instrument> 1 … N`, each a full re-serialization of that staff. A slot whose
systems disagree about N abstains.

⚠️ **A split may only be made where the part is CONTINUOUS, and that is not the
same as "the stitched path".** `_stitch_slots` returns None for a single-system
page on purpose (one system stitches to itself, and the per-system path keeps
richer part names), so the per-system path serves two different situations:

* a page with ONE system — a part is continuous by construction; split.
* several systems whose ordinal join REFUSED — the parts are already per-system
  fragments; **do not split**, because splitting each fragment multiplies the
  fragmentation instead of repairing it.

Gating on the path instead of on the fragmentation silently withheld the split
from seven of the eleven rows, including every row it gains most on. The bug was
caught by re-measuring, not by review. `_is_fragmented()` is the distinction;
`OMR_CONDENSED_PARTS=all` opts into splitting fragments and exists only to
reproduce the refusal: on Brahms 1 p.2, the corpus's only such page, it takes 27
fragments to **41** against a truth of 21 and costs **+904 edits** where every
other row gains.

**Flag-off byte identity is proven, not asserted** (`probe_flag_off_identity.py`,
which re-imports the base commit's own `export.py` and compares digests): every
fixture of BOTH benchmarks — 11 scan rows and 11 engraved works — exports the
same bytes, **22/22**. And with the flag ON, a page carrying no
`condensed_parts` evidence is byte-identical too, **22/22** — abstention is the
fallback, measured rather than claimed.

⚠️ **The engraved benchmark cannot see this change at all.** All eleven works
are single-system excerpts with one part per staff, so it could not have caught
a regression here — the same shape as the direction-text finding.
`tools/omr/tests/test_condensed_parts.py` (27 tests) stands in its place, as
`test_export_slot_stitching.py` does for stitching.

---

## 3. What it is worth — measured

`run_arms.py` re-exports the transcriptions the scan benchmark already committed
and scores them with musicdiff; the arms differ in the exporter and nothing
else, so no detector time is spent and the A/B is exact. Baseline reproduces the
staff-structure session's own flag-off figure exactly (**34,962 / ES 8,453**),
which is the control saying the two trees agree.

| arm | edits | Δ edits | ES | Δ ES | EM | ES+EM |
|---|--:|--:|--:|--:|--:|--:|
| baseline | 34,962 | — | 8,453 | — | 12,434 | 20,887 |
| **oracle** (answer key) | **30,767** | **−4,195** | **2,775** | **−5,678** | 10,247 | 13,022 |
| label_ideal (rule, perfect reader) | 33,271 | −1,691 | 4,183 | −4,270 | 12,210 | 16,393 |
| baseline+stitch | 34,746 | −216 | 9,370 | +917 | 11,616 | 20,986 |
| **oracle+stitch** | **30,405** | **−4,557** | **2,060** | **−6,393** | 7,961 | 10,021 |
| label_ideal+stitch | 32,909 | −2,053 | 3,468 | −4,985 | 9,924 | 13,392 |

Per row, oracle against baseline (a row the arm does not touch is byte-identical
and is scored once):

| row | baseline | oracle | Δ | ES b → o | parts b → o (truth) |
|---|--:|--:|--:|---|---|
| beethoven 984073 p1 | 1,278 | **806** | −472 | 513 → **0** | 12 → 18 (18) |
| beethoven 984073 p2 | 4,341 | **3,582** | −759 | 1,551 → **0** | 11 → 18 (18) |
| beethoven 575951 p1 | 1,358 | **853** | −505 | 513 → **0** | 12 → 18 (18) |
| beethoven 575951 p2 | 4,405 | **2,932** | −1,473 | 1,551 → **0** | 11 → 18 (18) |
| brahms p1 | 3,431 | **2,485** | −946 | 1,001 → **0** | 14 → 21 (21) |
| mahler p2 | 1,119 | **1,079** | −40 | 649 → 100 | 17 → 34 (38) |
| dvořák p5 / p6 | 661 / 2,585 | unchanged | 0 | 0 → 0 | 15 → 15 (15) |
| brahms p2 | 6,562 | unchanged | 0 | 715 | 27 (fragments, gated off) |
| mahler p3, bach | unchanged | | 0 | | (no map — oracle abstains) |

Beethoven 984073 p1 goes **0.7108 → 0.3875** and Brahms p1 **0.9184 → 0.5510**.
Five rows land on the truth's part count EXACTLY and their `entire staff` goes
to zero — which is the check that the split is putting the right music in the
right parts rather than inflating a count: the count control and the content
score move together.

⚠️ **Mahler p2 is the honest small number, and it says what the metric does.**
ES falls 649 → 100 while EM RISES 199 → 415, netting only −40 edits. Its
condensation is 3- and 4-way (`Vier Flöten` → 3 parts, `Drei Klarinetten` → 4),
so duplication puts three copies of a divisi bar where the reference has three
different lines, and the bars stop pairing. **Duplication scales badly past two
players** — the divisi refinement is worth most exactly where this arm is worth
least.

### Slot stitching COMPOSES — and the split removes its documented downside

The staff-structure session withheld `OMR_SLOT_STITCH` partly because it
"improves the pool and makes the named bucket more than twice as bad"
(ES 8,453 → 9,370, +917). **That penalty is an artifact of not splitting.** On
Brahms 1 p.2, the only row either flag touches:

| | edits | ES | EM | parts |
|---|--:|--:|--:|--:|
| baseline (ordinal refuse) | 6,562 | 715 | 3,628 | 27 |
| slot stitch only | 6,346 | 1,632 | 2,810 | 14 |
| split only (gated off there) | 6,562 | 715 | 3,628 | 27 |
| **both** | **6,200** | **0** | **1,342** | **21** (truth 21) |

With both on, that row reaches the reference's own part count, its `entire
staff` goes to zero, and its `entire measure` falls by 2,286 against baseline.
Pool-wide the two compose to **−4,557 edits / ES 2,060**, better than either
alone on every axis. The stitch flag's cost was the fragments' *content* not
pairing; giving the stitched slots their players is what pays for it.

---

## 4. The rule cannot be inferred from the page — the Dvořák refusal

`tools/omr/condensed_parts.py` reads the printed margin label for evidence of
more than one player, in tiers: a printed enumeration (`Corni I.II.`,
`4 Hörner in C 1./2.`), a compound (`Violoncello e Basso`), a leading numeral
(`2 Flöten`, `Vier Flöten`), then a bare plural section noun (`Flauti`).
Scored against `works.json`'s hand-verified `staves[i].parts`, on the hand-read
strings so the READER's errors are excluded:

| rows | exact | over | under |
|---|--:|--:|--:|
| beethoven ×4, brahms ×2 | **74/74** | 0 | 0 |
| dvořák p5, p6 | 14/30 | **16** | 0 |
| mahler p2 | 8/17 | 7 | 2 |
| | 96/121 (79%) | 23 | 2 |

⚠️ **THE SAME PRINTED LABEL IS TWO PARTS IN ONE REFERENCE AND ONE IN ANOTHER.**
`Flauti`, `Oboi`, `Clarinetti in …`, `Fagotti`, `Corni …`, `Trombe in …` are
printed by both the Litolff Beethoven and the Simrock Dvořák. The Gradus
Beethoven 5 encodes each as two parts; the Gradus Dvořák 9 encodes each as one.
Nothing on the page distinguishes them, because the difference is not on the
page — the engraving says "two players share this staff" in both, and the two
encoders resolved that differently.

What that costs, in the `label_ideal` arm (the rule with a PERFECT reader, so
this is the rule's own error and not OCR's):

| row | baseline | oracle | label_ideal | parts (truth) |
|---|--:|--:|--:|---|
| dvořák p5 | 661 | 661 | **1,562** (+901) | 23 (15) |
| dvořák p6 | 2,585 | 2,585 | **3,865** (+1,280) | 23 (15) |
| mahler p2 | 1,119 | 1,079 | 1,402 (+323) | 48 (38) |
| beethoven ×4, brahms p1 | | identical to oracle | identical to oracle | exact |

**+2,181 edits on Dvořák alone**, which is 52% of the oracle's whole gain given
back on two rows of eleven — and those two are the corpus's ONLY rows whose
structure is currently exact (ES 0, tying Audiveris at zero). The rule is right
about the engraving and wrong about the file, and it converts our two perfect
structural rows into two of our worst.

So the label rule is **NOT shipped as the count's source.** It is committed,
tested and reachable so the finding is reproducible, exactly as
`OMR_SLOT_STITCH` is.

### The reader, measured separately, because a rule error and an OCR error want opposite fixes

`probe_real_labels.py` runs the pipeline's own free reader (Surya) on three
pages (`real-labels.json`):

* **Beethoven 984073 p1 — 12/12.** `Flauti.`, `Corni in Es.`, `Timpani in C.G.`
  read cleanly and the rule is exact on every one.
* **Dvořák p5 — the reader is CORRECT and the rule still wrong.**
  `Corni I. II. in E.` and `Tromboni I. II.` are transcribed faithfully; the
  rule reads 2 players from a printed enumeration, and the reference holds 1.
  This is the cleanest possible demonstration that the fault is not OCR.
* **Brahms p1 — 12/14, both losses in the safe direction.** Surya renders the
  stacked `4 Hörner in C 1./2.` as `in C \frac{1}{2}`, dropping the instrument
  and turning the enumeration into LaTeX, so the rule abstains (1) where the
  truth is 2. Stacked numerals arriving as `\frac{a}{b}` is a lead worth one
  line of normalisation, but it was NOT added here — fitting a rule to one
  reader's quirk on one page is how a corpus of two becomes a corpus of one.

### One rule bug WAS found and fixed

`4 Hörner in C 1./2.` was read as **four** players: the arabic-enumeration regex
used a single-character separator class, so `1./2.` did not match and the
leading numeral — which counts the SECTION, not the staff — won instead. Brahms
prints four horns across two staves of two. The enumeration now outranks the
numeral and the row scores 14/14. Pinned in `test_condensed_parts.py`.

---

## 5. Where the count should come from

Not the label. The honest sources, in the order they should be tried:

1. **A dossier.** Condensation is a fact about a (work, edition) pair, and
   `data/dossiers/` already exists to hold per-work facts generated from the
   work's own MusicXML — which is precisely the encoding whose convention the
   label cannot see. A dossier knows the part count and the part names; joining
   them to the printed staves is the same join `dossier.slot_facts_for_page`
   already makes, on the same terms (abstain unless the counts agree). This is
   the shape the oracle arm approximates, and it is NOT built here.
2. **Human confirmation**, which the annotate/assist path already has a channel
   for.
3. **The label, as a PROPOSAL only** — never as the decision.

⚠️ What a split must never do is chase the part COUNT. The metric is symmetric
and rewards it: `label_ideal` on Dvořák p6 emits 23 parts against 15 and still
scores better on `entire staff` than the correct 15 does, while the row's total
rises by 1,280. Every arm here is reported with its part count beside its edits
for that reason.

---

## Reproducing

```bash
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python

python3 benchmarks/omr-condensed-parts-2026-09/probe_truth_convention.py \
    --json truth-convention.json
python3 benchmarks/omr-condensed-parts-2026-09/probe_audiveris_parts.py \
    --out-dir <vs-industry>/out/audiveris-scan --json audiveris-parts.json
python3 benchmarks/omr-condensed-parts-2026-09/probe_flag_off_identity.py \
    --base a78c9454
python3 benchmarks/omr-condensed-parts-2026-09/probe_real_labels.py \
    --rows beethoven-sym5-mvt1-984073-p1 dvorak-sym9-mvt1-405834-p5 \
           brahms-sym1-mvt1-317803-p1 --json real-labels.json
python3 benchmarks/omr-condensed-parts-2026-09/run_arms.py \
    --arms baseline,oracle,label_ideal --stitch --json arms.json
```

`out/` is gitignored — every file in it is a re-export of a committed
transcription and is reproduced by `run_arms.py`. `arms-ceiling.json` is the
first run, taken BEFORE the fragment gate existed, and is kept because it is
where the +904 Brahms p2 refusal was measured.

The scan `fixtures/` are gitignored build products; `run_arms.py` records each
one's sha256 and the git HEAD in its output, because a parallel workstream can
re-export them under you — the discipline `condensation_arm.py` set after one
did exactly that on 2026-09-01.
