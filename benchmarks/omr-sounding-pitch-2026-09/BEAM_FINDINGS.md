# The staged exporter wrote no `<beam>` — and in MusicXML that IS a flag

2026-09-21, no flag. Item 2 of the symbol-dossier sweep's ranked repair list.
Item 1 (the alter) is in [FINDINGS.md](FINDINGS.md); the two shipped as
separate commits.

---

## 1. The dossier's claim was a CLAIM. It is now measured, and it holds.

The repair list says *"in MusicXML no beam **is** a flag, so every beamed note
comes out flagged."* Many renderers infer beaming from `<type>` and the beat,
so this was worth checking rather than building to.

`probe/renderer_semantics.py` puts four eighths through Verovio with and
without the element:

| arm | MEI `<beam>` | flag glyphs DRAWN | music21 beams/note |
|---|--:|--:|--:|
| **WITH** `<beam>` | 1 | **0** | `[1,1,1,1]` |
| **NO** `<beam>` | 0 | **4** (`flag8thDown` ×4) | `[0,0,0,0]` |

**Confirmed.** Verovio does not infer beaming; an absent `<beam>` is rendered
as four separate flagged notes. The repair is a visible defect, not a fidelity
nicety.

⚠️ **And on the real file it is large.** Verovio, page 1 of the exported
artefact:

| | flags drawn | beams drawn | noteheads |
|---|--:|--:|--:|
| Litolff, before | **574** | 0 | 1618 |
| Litolff, after | **82** | 171 | 1618 |
| Breitkopf, before | **1156** | 0 | 2376 |
| Breitkopf, after | **277** | 278 | 2376 |

**492 and 879 flags stop being drawn.** The noteheads are identical, so
nothing was added or lost — the notes simply stopped being spelled wrong.

---

## 2. REACH, before anything was built

The beam level is **already on the record**: `adjudicate_duration` puts
`beam_levels` in the duration verdict's own VALUE, beside the beats it derived
FROM it. Nothing on the export path read it. So this is a wire, and the reach
is a property of the record rather than of a new reader:

| | pitched notes with a decided duration | `beam_levels >= 1` | cells carrying a beam stroke |
|---|--:|--:|--:|
| Litolff Beethoven 5 pp.1-4 | 2,000 | **900 (45.0%)** | 477 |
| Breitkopf Brahms 1 pp.0-3 | 2,828 | **1,751 (61.9%)** | 542 |

Levels run to 5 on Litolff and 7 on Breitkopf.

---

## 3. The frame was the whole risk, and it is the recorded one

`Q.BEAM_STROKE` is filed on the CELL in the cell's **canonical** frame —
`gather_cv_lines` reads an ERASED cell image and never converts — exactly as
`Q.STEM` is, and for the same reason. `annotate_beams` compares a beam box
against a notehead's centre and reads both out of **`bbox_page`**.

Handing the strokes over unconverted would compare two different rulers. **It
would not raise**; it would write a beam over the wrong notes. That is
`Q.ONSET_COLUMN`'s recorded fault.

`_beam_detections_page` converts **using the head as its own ruler** — the
method `_stem_probes` already established and measured (a per-cell affine fit
gives the identical answer at residual 0.00 px). A notehead carries both boxes,
so one head fixes the scale and the origin for every stroke in its cell.

⚠️ **It REFUSES rather than guesses.** A cell with no head carrying both boxes
has no ruler, yields nothing, and its notes stay flagged — which is what they
were. The refusal is **counted**: `beam_cells_without_a_frame_ruler` is **96**
on Litolff and **114** on Breitkopf. A wiring pass may connect a decision; it
may not let one guess, and a gap that is not counted is indistinguishable from
ink nobody read.

---

## 4. What changed, and what was deliberately NOT written

`tools/omr/staged/export.py` only.

- `_place_notes` carries `beam_levels` from the duration verdict onto the
  detection, under the name `annotate_beams` expects.
- `_beam_boxes_by_cell` / `_beam_detections_page` — read the strokes, convert
  the frame, refuse without a ruler.
- `_annotate_beams_for` calls **`_legacy.annotate_beams`, imported, never
  ported.** Its docstring records FOUR grouping rules, each paid for by a
  measured failure: the notehead-width pad, the same-stack collapse that took
  Mozart 41 from 7 to 145 beam edits, the box-containing-two-disjoint-boxes
  guard, and the divisi two-row case. Restating any of them would give this
  project two copies of numbers it paid to measure once.
- The call is **PER VOICE**, at the seam where the voice split already exists —
  `annotate_beams`' own docstring requires it.
- `_measure_events_xml` passes `beam_states` on the chord's **first note only**,
  the same rule the legacy call site follows.
- Counters `beams` / `beamed_events`, incremented **at the render** where the
  element is written — the rule the arc export learned by reporting 55 slurs
  into a file holding 23.

**No flag.** The rung is additive by construction: a cell with no stroke
produces no boxes, so nothing is annotated and the file does not move.

---

## 5. The numbers, and the controls

One record exported twice by two trees, both publishers:

| | Litolff | Breitkopf |
|---|--:|--:|
| **`<beam>` before → after** | **0 → 679** | **0 → 1511** |
| events carrying a beam | 495 | 886 |
| cells refused for want of a ruler | 96 | 114 |
| `<note>` / `<rest` | 2460 / 842 — unchanged | 3612 / 1099 — unchanged |
| `<slur` / `<tied` | 80 / 179 — unchanged | 490 / 700 — unchanged |

### Controls, and what each would have caught

| control | result | what it catches |
|---|---|---|
| **`begin` == `end` at EVERY level** | **holds, both documents, levels 1-5** | a wrong grouping — the invariant a beam must satisfy |
| byte-identical outside `<beam>`/`<alter>`/`<accidental>` | holds, both | any collateral change |
| …POSITIVE control (files *do* differ unstripped) | holds | a vacuous strip |
| Verovio flag count | 574→82 and 1156→277, noteheads identical | the defect as a human SEES it |
| music21 beam read-back (`probe/renderer_semantics.py`) | `[1,1,1,1]` vs `[0,0,0,0]` | the element being present but unreadable |
| accounting control (`Unbalanced`, an EQUALITY) | holds | notes written vs accounted |
| all seven derived checks | exit **0** | — |

Litolff by level: 1 → 171/171, 2 → 52/52, 3 → 15/15, 4 → 5/5, 5 → 1/1.
Breitkopf: 278/278, 108/108, 42/42, 11/11. Forward and backward hooks appear
(11 and 4 on Litolff), which is `annotate_beams` handling partial beams.

---

## 6. The battery, and the two gaps it found

**21 arms, 21 red, 0 survived, 0 bad anchors** (12 alter + 8 beam + a positive
control). Judge = exit code **plus the set of failing test ids**, against a
green baseline taken first.

⚠️⚠️ **BOTH BEAM SURVIVORS WERE EQUIVALENT MUTANTS ON MY FIXTURE AND REAL GAPS
ON A PAGE — the same shape as the alter half's, which is now three in one
session.**

- **`frame-scale-dropped` survived.** Setting `scale = 1.0` makes the converted
  stroke **twice as wide** — and my test asserted only that it *covers* the
  heads, which an over-wide box does. On a real page that box swallows the NEXT
  group, which is precisely the `box containing two disjoint boxes` failure
  `annotate_beams` documents paying for. The test now asserts the geometry
  **exactly** (x, y, w, h to six places) rather than containment.
- **`beams-computed-across-BOTH-voices` survived.** On a ONE-voice fixture
  `streams is None`, so `[events]` is what the loop already iterates — the
  mutation changes nothing. Only a two-voice bar separates them: four notes
  under one stroke split 0,2 / 1,3 give TWO runs per voice and ONE across both.
  `test_two_voices_get_their_OWN_runs` added.

⚠️ A third arm went **red via the wrong test**, which the judge reported rather
than passing: my `want` field named a stale test. Corrected.

---

## 7. WHAT IS NOT ESTABLISHED

- **No print was consulted.** The beams follow the CV's strokes and the
  record's levels; where the CV read a stroke that is not there, or missed one,
  this faithfully writes the consequence. The Verovio flag counts show the
  spelling changed, **not** that it is now right.
- **210 cells across the two documents carry a stroke and get no beam** for
  want of a frame ruler. Counted, not repaired — a head with no page box is an
  upstream gap.
- **`beam_levels` is trusted, not checked.** The record's own
  `beam_evidence` on Litolff reads `read` 1017 / `reader_declined` 998 /
  `none_over_this_note` 302 / `flag` 30, so a large minority of notes have a
  level nobody read off ink. This rung does not improve that and cannot.
- **No OMR-NED figure**, deliberately.
- n = 2 documents, 2 publishers, 7 pages, both SCANS. **The engraved family is
  untouched and unmeasured** — and it is where the legacy beam work measured
  430 of 449 edits as `editbeam`, so it is the obvious next place to look.
- The legacy exporter is **byte-identical**: `tools/omr/export.py` is not
  modified, so no legacy figure moves.
