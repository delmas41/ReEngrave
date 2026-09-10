# The duration reader — a note is joined to its beam by its STEM

⚠️ **No benchmark was run and nothing here is a score.** Every number is a
control or a diagnosis. The change is **staged-pipeline only** — the legacy
`tools/omr/rhythm.py` is untouched, so no engraved or scan figure anywhere
moves.

Acts on
[`benchmarks/omr-staged-meter-engraved-2026-09/FINDINGS.md`](../omr-staged-meter-engraved-2026-09/FINDINGS.md)
§6, which separated **two independent faults** in the bar sums and asked for
them to be worked apart. **Fault 1 is FIXED here. Fault 2 is DIAGNOSED here to
a single cause, and is not fixed** — it is the next unit of work.

**The fixture.** `beethoven-sym5-mvt4` bars 203-218, rendered through LilyPond
at 23 parts with every part playing every bar (`render_meter_change.py`), so
the ink is perfect by construction and a bar that fails to sum is the reader's
fault. Truth `{203: 3/4, 209: 4/4}`. Engraved weights
(`imgsz2048-ft-30ep`), as `run_arms.py` records for this family of fixtures.

```bash
python3 benchmarks/omr-staged-meter-engraved-2026-09/render_meter_change.py \
    --work beethoven-sym5-mvt4 --first 203 --last 218 --out-dir out/
OMR_SURYA_KEEP_ALIVE=0 python3 -m tools.omr.staged out/<pdf> --pages 0-2 \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --out staged.json
python3 benchmarks/omr-staged-duration-beams-2026-09/barsum.py staged.json \
    "0:0-8=3.0,1:0-2=3.0,1:3-8=4.0,2:0-8=4.0"
```

---

## 1. THE RESULT — assessable bars 12 → 14, correct 7 → **10**

Off each record's **own** duration verdicts, under the **shipping** candidate
policy, every page of the fixture. A `*` marks a bar read wrong.

```
BEFORE  assessable 12  correct  7   p0c0=3.0 p0c1=3.0 p0c2=3.0 p1c0=3.0
                                    p1c1=2.0* p1c2=2.0* p1c3=4.0 p1c4=3.5*
                                    p1c5=6.0* p1c8=4.0 p2c2=4.0 p2c3=4.5*
AFTER   assessable 14  correct 10   … p2c0=4.0 p2c1=4.0 p2c2=4.0 p2c3=4.0
```

**No bar goes from right to wrong.** One wrong bar is repaired (`p2c3`
4.5 → 4.0) and two bars become assessable at all, both correct. `narrowed`
duration verdicts fall **147 → 29**.

⚠️ **The four bars that stay wrong are EXACTLY Fault 2 and they do not move** —
`p1c1`, `p1c2` at 2.0, `p1c4` at 3.5, `p1c5` at 6.0, reproducing §6's own
counts (17 of 23 and 20 of 23) to the staff. That the two faults are
independent is now a measurement, not a claim.

## 2. THE MECHANISM — a beam ends at a stem, and a stem is not a centre

A beam stroke runs from the **first stem it joins to the last**, and a stem
stands at the **side** of its notehead. So the outer note of every beamed group
has its centre roughly half a notehead width past the stroke's end, and
`_beam_levels` was testing exactly that centre.

Measured over the fixture's narrowed durations (`probe_stem.py`):

| | count |
|---|--:|
| the head's box overlaps a beam **and** a stem of that head meets it | **114** |
| no box overlap — genuinely not under a beam | 104 |
| no CV beam in the cell at all | 55 |
| no box overlap and no stem read | 8 |
| box overlap but no stem read | 4 |

and the overshoot of the centre past the stroke's end clusters at **0.35-0.47
notehead widths** — the stem offset and nothing else.

`BEAM_EDGE_TOLERANCE_WIDTHS` (1.0) then caught those 114 as **POSSIBLE**, so
the duration came out as a RANGE. `_bar_lengths_for` collapses a range to
`candidates[0]`, and `Ruling.narrow` orders by support, so the collapse always
took the **longer** note. ⚠️ **A verdict that says "it is one of these" was
consumed as if it had decided**, in the one direction that inflates a bar —
this project's own named anti-pattern, against `Evidence.admitted`'s explicit
*"THE POINT IS THAT A CONSUMER NEED NOT COLLAPSE THE SET EARLY"*.

⚠️⚠️ **`Q.STEM` WAS DECLARED IN `wants` AND `composed_from` AND READ BY
NOTHING**, with a `KNOWN_GAPS` entry saying so, inside the decision whose own
docstring calls the beam level its fragile input. 916 stem rows on this
three-page record. *The value existed and nothing read it*, again — and this
time it was not harmless.

## 3. WHY THIS AND NOT A CANDIDATE POLICY — the policy question DISSOLVES

§6 measured that "take the lowest candidate" fixes the dense page and breaks
the mixed one, and refused it as *a fudge that fits*. Simulated offline on ONE
saved record (`sim_beam_association.py`, no re-transcription, so no detector
jitter), rule A is the shipping centre test and rule B adds the stem tier:

| | assessable | correct | narrowed |
|---|--:|--:|--:|
| A, top candidate — **what shipped** | 10 | 7 | 149 |
| A, lowest candidate | 13 | 10 | 149 |
| **B, top candidate** | **13** | **10** | **16** |
| B, lowest candidate | 13 | 10 | 16 |

⚠️ **RULE B IS INSENSITIVE TO THE POLICY, AND THAT IS THE CLAIM.** Under it the
two policies give the same answer on every bar of all three pages, because the
ambiguity was an artefact of the association rather than a reading. Fixing the
association upstream is what §6 asked for, and it reaches rule A's *best* arm
without choosing a candidate at all.

⚠️ **The pipeline was then checked against the probe and the probe against the
pipeline.** A live `--pages 0-2` run reproduces the simulation in both
directions (narrowed 147 → 29 against a predicted 149 → 16; the residue is
`reconcile_duration`, which the offline simulation does not run).

⚠️ **AND IT WAS RE-MEASURED ON THE MERGED TREE.** `origin/main` moved under
this branch with the CAUTIONARY rule and the scan-side meter bookkeeping fix
(`_meter_changes`, `_last_cell_per_staff`), which the merge folded into the
same file. A live run after the merge is **identical bar for bar and count for
count** — 14 assessable, 10 correct, the same staff tallies. `out/barsums.txt`
carries all three arms.

## 4. THE RULE — box overlap, and NO CONSTANT

A stem is attached to a notehead, and joined to a beam, when their **boxes
overlap**. Both separations were measured before the rule was written, and
neither needs a tolerance:

* **stem ↔ beam**: of 707 pairs overlapping in x, **685 also overlap in y**;
  the 22 that do not are separated by **35 px or more**, with nothing in 1-34.
* **notehead ↔ stem**: 819 heads take **exactly one** stem; where none
  overlaps the nearest is **94 px** away but for three pairs at 1-2 px.

⚠️ **ADDITIVE, NEVER SUBTRACTIVE.** `_stem_joined` is a second tier beside the
centre test — the shape `_dedupe_cross_staff_detections`'s ledger ladder
already has. It can only turn a POSSIBLE into a CERTAIN, so a page whose stems
are not read behaves exactly as before, and stem-ONLY (dropping the centre
test) was measured and refused: same bars, but 60 narrowed against 16, because
a head whose stem the CV missed loses its beam entirely.

⚠️ **THE Y GUARD IS UNEXERCISED BY THIS FIXTURE AND IS TESTED DIRECTLY
INSTEAD.** Sweeping a y tolerance from 0 to 64 px changes no bar and moves
`narrowed` by one, because on a clean engraving every beam sits at its stems'
ends. It is kept because a stem in another octave crossing a beam's column is a
real case and the x test alone would join them —
`test_a_stem_that_misses_the_beam_in_Y_does_NOT_join` exercises it on
synthetic ink, **carrying its positive control inside the test**, and the
mutation arm that removes the y half of the overlap turns it red.

**Mutation arms, all red on the intended test** (`M1` x-only overlap, `M2`
every stem in the cell counts as attached, `M3` stem tier disabled, `M4`
joined ids ignored in `_beam_levels`): 1, 1, 4 and 4 failures of 7. The two
tests that survive M3/M4 are the two CONTROLS, which must pass on both trees.

## 5. ⚠️⚠️ FAULT 2 — DIAGNOSED, ONE CAUSE, AND IT IS THE SAME FAMILY

§6 said this one *"most needs a crop in front of a human"*. It did not need
one: the record answered it, and the encoding the page was **rendered from**
then confirmed it, which is stronger evidence than a crop.

**`Q.FLAG` and `Q.AUG_DOT` are gathered on the MARK's own glyph subject and
read on the NOTEHEAD's, so not one of them ever reaches a duration.**
`gather_rhythm_marks` writes them at `R.glyph(..., gi)` — the flag's or the
dot's own detection index — while `adjudicate_duration` does `ev.rows(Q.FLAG)`
and `ev.rows(Q.AUG_DOT)` on the notehead's subject. Measured on this record:

```
flag    (glyph-scoped): 134 rows, on a notehead subject: 0
aug_dot (glyph-scoped): 157 rows, on a notehead subject: 0
durations carrying a dot: 0        beam_evidence == "flag": 0
```

⚠️ It accounts for **both directions** of Fault 2, checked against the truth
encoding measure by measure:

| bar | we read | truth says |
|---|---|---|
| **m211** (4/4) | `quarter + 8th-rest` × 4 = **6.0** on 20 of 23 staves | **100 eighths** and 80 eighth rests — the missing FLAG |
| **m207/m208** (3/4) | a plain **half**, 2.0, on 7 of 13 | 8 parts play a **dotted half** — the missing DOT |

⚠️ And the two constants the adjudicator carries for exactly this —
`DOT_ABOVE_NOTE_MAX_SPACES` / `DOT_BELOW_NOTE_MAX_SPACES`, with a paragraph of
measured justification about Brahms's double stops — **are declared in the
staged module and used by nothing in it**; only the legacy `rhythm.py` reads
its own copies. The attachment the comment describes is never performed.

**So the repair is the same shape as this session's**: a mark that belongs to a
notehead must be ATTACHED to it, and the attachment is the adjudicator's job.
The dot's gate is already measured and written down; the flag's is not, and a
flag attaches at the STEM's far end, so it should be read through the stem tier
this session just built rather than by proximity to the head.

⚠️ **It is deliberately NOT done here.** It is a second fix, it changes
durations in the SHORTENING direction on a much larger population than 114
rows, and §6's instruction was to work the two faults separately.

## 6. WHAT THIS DOES NOT ESTABLISH

* **n = 1 document, 1 fixture, 3 pages, engraved.** A scan has fewer CV stems,
  so the tier reaches less there; it cannot reach less than zero, since it is
  additive, but the SIZE of the gain on a scan is unmeasured.
* **No scan arm was run**, and no OMR-NED figure was taken on either family —
  the legacy exporter does not use this code path at all.
* **The bar sums are still wrong on four bars** and will be until Fault 2 is
  fixed, so `OMR_METER_CARRY` / `OMR_METER_FROM_BARS` are **not** re-priced by
  this and neither floor should be touched. `A-DUR-8` stands, halved.
