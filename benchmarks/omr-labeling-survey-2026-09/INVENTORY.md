# Symbol inventory — every element, its owner, and its labeled evidence

**Generated — do not hand-edit.** Rebuild with `python3 benchmarks/omr-labeling-survey-2026-09/symbol_inventory.py` (last: 2026-09-03). Curated annotations live in the script; counts come from `data/user-labeled/v*/labels`. Rationale per owner bucket: `SURVEY_DESIGN.md` §1, CLAUDE.md "Hand-label cells", NOTES.md 🅿️ 2026-09-03.

Training space: **208 classes** — 67 carry any labeled box, 160 are detector-owned, and **109 detector-owned labeling targets have ZERO boxes** (the blind spots the survey works through).

## detector — LABELING TARGET (156)

| class | boxes | publisher columns covered | note |
|---|--:|---|---|
| `noteheadBlackOnLine` | 461 | Durand; Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Peters; Universal; clef cells (EXCLUDED from catalog); mixed (early orchestral) | well-covered baseline class |
| `noteheadBlackInSpace` | 424 | Durand; Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Novello; Peters; Universal; clef cells (EXCLUDED from catalog); mixed (early orchestral) | well-covered baseline class |
| `noteheadHalfOnLine` | 168 | Durand; Jurgenson (low-res); Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Novello; Peters; Universal; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R1 — SHIPPED 2026-09-03 (hollow-ft) |
| `noteheadHalfInSpace` | 163 | Durand; Jurgenson (low-res); Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Novello; Peters; Universal; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R1 — SHIPPED 2026-09-03 (hollow-ft) |
| `restQuarter` | 104 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | restQuarter well-covered; long rests interplay with MMR logic |
| `augmentationDot` | 93 | Durand; Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Novello; Peters; Universal; clef cells (EXCLUDED from catalog); mixed (early orchestral) | dot geometry fixed 2026-09-01 (asymmetric window) |
| `noteheadWholeOnLine` | 87 | Durand; Jurgenson (low-res); Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Peters; Universal; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R1 — shipped (the thin half of the row; Phase 2 fed it) |
| `accidentalFlat` | 81 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | inline accidentals; header ones are the template's |
| `restWhole` | 66 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | restQuarter well-covered; long rests interplay with MMR logic |
| `noteheadWholeInSpace` | 64 | Durand; Jurgenson (low-res); Litolff; Litolff+Breitkopf+Peters+Eulenburg+Simrock; Peters; Universal; mixed (early orchestral) | survey R1 — shipped (the thin half of the row; Phase 2 fed it) |
| `dynamicF` | 44 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `rest8th` | 41 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | restQuarter well-covered; long rests interplay with MMR logic |
| `articStaccatoAbove` | 40 | Durand; clef cells (EXCLUDED from catalog); mixed (early orchestral) | exported since 2026-09-01 |
| `accidentalSharp` | 39 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | inline accidentals; header ones are the template's |
| `flag8thDown` | 36 | Durand; clef cells (EXCLUDED from catalog); mixed (early orchestral) | duration evidence |
| `articTenutoAbove` | 30 | clef cells (EXCLUDED from catalog) | exported since 2026-09-01 |
| `accidentalNatural` | 29 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | inline accidentals; header ones are the template's |
| `flag8thUp` | 22 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | duration evidence |
| `dynamicLetterP` | 21 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `dynamicDiminuendoHairpin` | 18 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `articAccentAbove` | 16 | Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | exported since 2026-09-01 |
| `dynamicCrescendoHairpin` | 16 | Durand; Peters; mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `articStaccatoBelow` | 15 | Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | exported since 2026-09-01 |
| `tremolo2` | 15 | Litolff; clef cells (EXCLUDED from catalog); mixed (early orchestral) | scan behavior unmeasured |
| `dynamicLetterF` | 14 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `restHalf` | 14 | Durand; Litolff; Peters; mixed (early orchestral) | restQuarter well-covered; long rests interplay with MMR logic |
| `articAccentBelow` | 12 | clef cells (EXCLUDED from catalog) | exported since 2026-09-01 |
| `dynamicLetterS` | 8 | Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `noteheadBlackInSpaceSmall` | 5 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog) | well-covered baseline class |
| `tremolo3` | 5 | Durand; Peters; clef cells (EXCLUDED from catalog) | scan behavior unmeasured |
| `tuplet3` | 5 | Durand; Peters | tuplet family (catalog spelling) |
| `dynamicS` | 3 | mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `fermataAbove` | 3 | mixed (early orchestral) | exported (fermata gap closed) |
| `articulationAccent` | 2 | clef cells (EXCLUDED from catalog); mixed (early orchestral) | exported since 2026-09-01 |
| `dynamicLetterM` | 2 | Durand | survey R3 — small dynamics letters + hairpins |
| `dynamicM` | 2 | mixed (early orchestral) | survey R3 — small dynamics letters + hairpins |
| `noteheadHalfOnLineSmall` | 2 | Peters; mixed (early orchestral) | survey R1 — SHIPPED 2026-09-03 (hollow-ft) |
| `tuple` | 2 | Durand | tuplet family (catalog spelling) |
| `accidentalNaturalSmall` | 1 | mixed (early orchestral) | inline accidentals; header ones are the template's |
| `articulationMarcatoBelow` | 1 | Durand | exported since 2026-09-01 |
| `articulationTenuto` | 1 | Durand | exported since 2026-09-01 |
| `dynamicP` | 1 | Peters | survey R3 — small dynamics letters + hairpins |
| `flag16thUp` | 1 | mixed (early orchestral) | duration evidence |
| `flag8thUpSmall` | 1 | Durand | duration evidence |
| `noteheadBlackOnLineSmall` | 1 | clef cells (EXCLUDED from catalog) | well-covered baseline class |
| `noteheadWhole` | 1 | Peters | survey R1 — shipped (the thin half of the row; Phase 2 fed it) |
| `tuplet2` | 1 | Peters | tuplet family (catalog spelling) |
| `accidentalDoubleFlat` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalDoubleFlat` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalDoubleSharp` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalDoubleSharp` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalFlat` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalFlatSmall` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalNatural` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalSharp` | 0 | — | inline accidentals; header ones are the template's |
| `accidentalSharpSmall` | 0 | — | inline accidentals; header ones are the template's |
| `arpeggiato` | 0 | — | unmeasured |
| `arpeggio` | 0 | — | unmeasured |
| `articMarcatoAbove` | 0 | — | exported since 2026-09-01 |
| `articMarcatoBelow` | 0 | — | exported since 2026-09-01 |
| `articStaccatissimoAbove` | 0 | — | exported since 2026-09-01 |
| `articStaccatissimoBelow` | 0 | — | exported since 2026-09-01 |
| `articTenutoBelow` | 0 | — | exported since 2026-09-01 |
| `articulationMarcatoAbove` | 0 | — | exported since 2026-09-01 |
| `articulationStaccato` | 0 | — | exported since 2026-09-01 |
| `augmentationDot` | 0 | — | dot geometry fixed 2026-09-01 (asymmetric window) |
| `caesura` | 0 | — | unmeasured |
| `coda` | 0 | — | rare; unmeasured |
| `coda` | 0 | — | rare; unmeasured |
| `dynamicCrescendoHairpin` | 0 | — | survey R3 — small dynamics letters + hairpins |
| `dynamicDiminuendoHairpin` | 0 | — | survey R3 — small dynamics letters + hairpins |
| `dynamicLetterR` | 0 | — | survey R3 — small dynamics letters + hairpins |
| `dynamicLetterZ` | 0 | — | survey R3 — small dynamics letters + hairpins |
| `dynamicR` | 0 | — | survey R3 — small dynamics letters + hairpins |
| `dynamicZ` | 0 | — | survey R3 — small dynamics letters + hairpins |
| `fermataAbove` | 0 | — | exported (fermata gap closed) |
| `fermataBelow` | 0 | — | exported (fermata gap closed) |
| `fermataBelow` | 0 | — | exported (fermata gap closed) |
| `fingering0` | 0 | — | fingering3 doubles as a triplet digit (positional gate) |
| `fingering1` | 0 | — | fingering3 doubles as a triplet digit (positional gate) |
| `fingering2` | 0 | — | fingering3 doubles as a triplet digit (positional gate) |
| `fingering3` | 0 | — | fingering3 doubles as a triplet digit (positional gate) |
| `fingering4` | 0 | — | fingering3 doubles as a triplet digit (positional gate) |
| `fingering5` | 0 | — | fingering3 doubles as a triplet digit (positional gate) |
| `flag128thDown` | 0 | — | duration evidence |
| `flag128thUp` | 0 | — | duration evidence |
| `flag16thDown` | 0 | — | duration evidence |
| `flag16thDown` | 0 | — | duration evidence |
| `flag16thUp` | 0 | — | duration evidence |
| `flag32ndDown` | 0 | — | duration evidence |
| `flag32ndDown` | 0 | — | duration evidence |
| `flag32ndUp` | 0 | — | duration evidence |
| `flag32ndUp` | 0 | — | duration evidence |
| `flag64thDown` | 0 | — | duration evidence |
| `flag64thDown` | 0 | — | duration evidence |
| `flag64thUp` | 0 | — | duration evidence |
| `flag64thUp` | 0 | — | duration evidence |
| `flag8thDown` | 0 | — | duration evidence |
| `flag8thDownSmall` | 0 | — | duration evidence |
| `flag8thUp` | 0 | — | duration evidence |
| `graceNoteAcciaccatura` | 0 | — | survey R2 — NEXT; selector: grace_score.py |
| `graceNoteAcciaccaturaStemDown` | 0 | — | survey R2 — NEXT; selector: grace_score.py |
| `graceNoteAcciaccaturaStemUp` | 0 | — | survey R2 — NEXT; selector: grace_score.py |
| `graceNoteAppoggiaturaStemDown` | 0 | — | survey R2 — NEXT; selector: grace_score.py |
| `graceNoteAppoggiaturaStemUp` | 0 | — | survey R2 — NEXT; selector: grace_score.py |
| `keyboardPedalPed` | 0 | — | keyboard rep only |
| `keyboardPedalUp` | 0 | — | keyboard rep only |
| `noteheadDoubleWholeInSpace` | 0 | — | R1 family; rare on orchestral pages |
| `noteheadDoubleWholeInSpaceSmall` | 0 | — | R1 family; rare on orchestral pages |
| `noteheadDoubleWholeOnLine` | 0 | — | R1 family; rare on orchestral pages |
| `noteheadDoubleWholeOnLineSmall` | 0 | — | R1 family; rare on orchestral pages |
| `noteheadFullSmall` | 0 | — | catalog alias family for filled noteheads |
| `noteheadHalfInSpaceSmall` | 0 | — | survey R1 — SHIPPED 2026-09-03 (hollow-ft) |
| `noteheadHalfSmall` | 0 | — | survey R1 — SHIPPED 2026-09-03 (hollow-ft) |
| `noteheadWholeInSpaceSmall` | 0 | — | survey R1 — shipped (the thin half of the row; Phase 2 fed it) |
| `noteheadWholeOnLineSmall` | 0 | — | survey R1 — shipped (the thin half of the row; Phase 2 fed it) |
| `ornamentMordent` | 0 | — | survey R4 — deep scope |
| `ornamentTrill` | 0 | — | survey R4 — deep scope |
| `ornamentTrill` | 0 | — | survey R4 — deep scope |
| `ornamentTurn` | 0 | — | survey R4 — deep scope |
| `ornamentTurnInverted` | 0 | — | survey R4 — deep scope |
| `ottavaBracket` | 0 | — | 8va — not yet consumed downstream |
| `repeatDot` | 0 | — | repeat barlines are an export gap (NOTES item 6) |
| `repeatDot` | 0 | — | repeat barlines are an export gap (NOTES item 6) |
| `rest128th` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest16th` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest16th` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest32nd` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest32nd` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest64th` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest64th` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `rest8th` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restDoubleWhole` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restHBar` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restHBar` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restHNr` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restHalf` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restQuarter` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `restWhole` | 0 | — | restQuarter well-covered; long rests interplay with MMR logic |
| `segno` | 0 | — | rare; unmeasured |
| `segno` | 0 | — | rare; unmeasured |
| `stringsDownBow` | 0 | — | unmeasured |
| `stringsUpBow` | 0 | — | unmeasured |
| `tremolo1` | 0 | — | scan behavior unmeasured |
| `tremolo4` | 0 | — | scan behavior unmeasured |
| `tremolo5` | 0 | — | scan behavior unmeasured |
| `tremoloMark` | 0 | — | scan behavior unmeasured |
| `tupleBracket` | 0 | — | tuplet family (catalog spelling) |
| `tuplet1` | 0 | — | tuplet family (catalog spelling) |
| `tuplet4` | 0 | — | tuplet family (catalog spelling) |
| `tuplet5` | 0 | — | tuplet family (catalog spelling) |
| `tuplet6` | 0 | — | tuplet family (catalog spelling) |
| `tuplet7` | 0 | — | tuplet family (catalog spelling) |
| `tuplet8` | 0 | — | tuplet family (catalog spelling) |
| `tuplet9` | 0 | — | tuplet family (catalog spelling) |
| `tupletBracket` | 0 | — | tuplet family (catalog spelling) |

## detector — precision-capped, not a recall target (4)

| class | boxes | publisher columns covered | note |
|---|--:|---|---|
| `slur` | 65 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | over-fires on bled arcs; 2026-09 wins were pairing/export |
| `tie` | 51 | Durand; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | same as slur |
| `slur` | 0 | — | over-fires on bled arcs; 2026-09 wins were pairing/export |
| `tie` | 0 | — | same as slur |

## specialist slot ONLY (never the shared catalog) (10)

| class | boxes | publisher columns covered | note |
|---|--:|---|---|
| `clefG` | 35 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | same |
| `clefF` | 30 | Durand; Litolff; Peters; clef cells (EXCLUDED from catalog); mixed (early orchestral) | same |
| `clefCAlto` | 13 | clef cells (EXCLUDED from catalog) | same |
| `clefCTenor` | 12 | clef cells (EXCLUDED from catalog) | same |
| `clefC` | 8 | Durand; Litolff; mixed (early orchestral) | same |
| `clef8` | 1 | Durand | same |
| `clef15` | 0 | — | same |
| `clefF` | 0 | — | same |
| `clefG` | 0 | — | same |
| `clefUnpitchedPercussion` | 0 | — | same |

## CV template reader primary — detector secondary (REVISIT flag) (17)

| class | boxes | publisher columns covered | note |
|---|--:|---|---|
| `keySharp` | 66 | clef cells (EXCLUDED from catalog) | key_signature_template |
| `keyFlat` | 32 | clef cells (EXCLUDED from catalog); mixed (early orchestral) | key_signature_template reads 11/12 vs detector 2/12 |
| `timeSig2` | 22 | clef cells (EXCLUDED from catalog) | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSigCommon` | 8 | Litolff | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig6` | 1 | Durand | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig8` | 1 | Durand | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `keyNatural` | 0 | — | key_signature_template |
| `timeSig0` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig1` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig3` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig4` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig5` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig7` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSig9` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSigCommon` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSigCutCommon` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |
| `timeSigCutCommon` | 0 | — | time_signature_locator reads meters 12/0; REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean) |

## classical CV — NEVER label (trains as background) (10)

| class | boxes | publisher columns covered | note |
|---|--:|---|---|
| `legerLine` | 13 | Peters; mixed (early orchestral) | ledger-ladder evidence in transcribe (catalog spelling) |
| `ledgerLine` | 5 | Litolff; mixed (early orchestral) | ledger-ladder evidence in transcribe |
| `beam` | 0 | — | line_detection (Phase 4f) |
| `beam` | 0 | — | line_detection (Phase 4f) |
| `brace` | 0 | — | system grouping |
| `brace` | 0 | — | system grouping |
| `staff` | 0 | — | staff_detector |
| `staff` | 0 | — | staff_detector |
| `stem` | 0 | — | line_detection (Phase 4f) |
| `stem` | 0 | — | line_detection (Phase 4f) |

## UNASSESSED — needs an owner before any labeling (11)

| class | boxes | publisher columns covered | note |
|---|--:|---|---|
| `numeral6` | 2 | Durand |  |
| `numeral8` | 2 | Durand |  |
| `numeral` | 1 | Peters |  |
| `numeral3` | 1 | Peters |  |
| `numeral0` | 0 | — |  |
| `numeral1` | 0 | — |  |
| `numeral2` | 0 | — |  |
| `numeral4` | 0 | — |  |
| `numeral5` | 0 | — |  |
| `numeral7` | 0 | — |  |
| `numeral9` | 0 | — |  |

## Elements with no class at all

| element | owner |
|---|---|
| printed directions (legato, Allegro…) | OCR — direction-text reader (Surya+Tesseract union) |
| instrument margin labels | OCR — staff_labels / Surya / vision ladder |
| barline types (single/double/final/repeat) | classical CV (measure_extractor); repeat emission = export gap, NOTES item 6 |
| textDynamic words (cresc., dim.) | parked custom class (Phase-3.4 collapse); direction-text reads them meanwhile |
| lyrics | no path (export_coverage KNOWN_GAPS) |
| metronome marks | export gap, pinned by test (KNOWN_GAPS 'metronome') |
| trill extension wavy lines | nothing reads them |
| rehearsal letters/numbers | nothing reads them; margin-adjacent OCR candidate |

(Custom-class boxes beyond the nc=208 space, filtered by the catalog cap: id 208×74, id 209×2, id 211×1, id 212×5, id 213×2 — the parked barline/textDynamic collection.)

