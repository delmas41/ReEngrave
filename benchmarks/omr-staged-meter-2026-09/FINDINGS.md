# A meter is printed on EVERY staff — the half of the rule the staged vote dropped

Reached by following the record, not by picking a target. Two of my own
inferences were falsified on the way there and both are recorded in §5, because
each was one step from being reported as a result.

---

## 1. The fault: a wrong meter at FULL agreement

`adjudicate_meter` divides its agreement share by the staves that **spoke**, so
**three spurious readings that happen to agree score 3/3 = 1.0.**
`rhythm._dominant_detected_meter` says exactly this in its own docstring —
*"two spurious readings that happen to agree are unanimous among themselves"* —
and requires `_PROPAGATE_MIN_STAFF_FRACTION = 0.5` of the page's staves as
well. The staged vote kept the agreement half and dropped the coverage half.

Measured on **Beethoven 5 / Litolff p.2** (`--pages 2` of `984073`):

| | |
|---|---|
| what the page prints | **no time signature at all** — it opens at bar 17, a continuation page |
| the reference says | **2/4**, on all 18 parts |
| system 0 | abstains `no_evidence` — correct |
| system 1 | **decided 4/4** (`raw: "C"`) from **3 staves of 11**, share 1.0 |
| page 1 of the same run | **12 staves of 12** read the true **2/4** |

3/11 = 0.27 against 12/12 = 1.0. `METER_COVERAGE_FLOOR = 0.5` separates them
with room to spare, and it is the legacy constant, not a new one.

⚠️ **Coverage and agreement are reported APART**, with their own reasons
(`too_few_staves_read_it` vs `no_agreement`). *"Do the staves that spoke
agree?"* and *"did enough of them speak?"* are two facts, and a handful of
spurious readings passes the first trivially. A page that shipped a wrong meter
and a page whose staves disagreed must never be the same row.

⚠️ A system whose staff count never decided cannot be asked what share of it
spoke, so the floor **declines to judge** there rather than inventing a
denominator.

## 2. What the wrong meter was doing

**83 of the 94 bars that sum to 4.0 on that page are a lone whole rest valued
at 4.0** — in a 2/4 movement, where the bar is 2.0. Only 11 are notes summing
to 4.0, so the duration reading is largely sound and the meter was the fault.

⚠️ **And it bore directly on `size_measure_rest`, landed the same day.** That
consequence sizes a lone whole rest to the bar. With **no** meter it correctly
declines and the rest keeps its nominal 4.0; with a **wrong** 4/4 it fires and
produces 4.0 anyway. Either way the bar is twice too long — and on the
wrong-meter system the new consequence was *laundering* the error into a
`measure="yes"` assertion. After the fix that system abstains and
`measure_rests_read` goes 19 → 0: still 4.0 on the page, but no longer claimed
as a measured bar length. **An honest unknown in place of a confident wrong.**

## 3. ⚠️ A SECOND, DIFFERENT METER FAULT — filed, NOT fixed here

**Brahms 1 / Breitkopf p.2** reads **9/4** from **10 staves of 14**. That page
genuinely prints a meter change (works.json's own label says so), and the
reference holds **6/8 (42 parts) and 9/8 (21)**. So the numerator is right and
**the denominator `8` is being read as `4`.**

The coverage floor passes it, correctly — this is a real printed meter read by
most staves. It is a template-scoring fault, and the reader's own contest says
so:

| read | runner-up | n |
|---|---|--:|
| `9/4` | `6/4` | 8 |
| `9/4` | `C` | 2 |

**Neither `9/8` nor `6/8` is even the runner-up**, and `9/8` IS in
`DEFAULT_METERS` — so this is not a missing candidate. Winning NCC is
**0.42–0.53**, at or below the bottom of the documented scanned-digit band
(0.50–0.62), with margins of 0.04–0.09 over a runner-up that also has a `4`
denominator.

⚠️ **Not fixed here, deliberately.** It is a digit-template question and
CLAUDE.md's standing rule is that a threshold in this family must never be
tuned on one edition. It needs its own corpus.

## 4. What is left, honestly

The meter is still **unknown on both systems** of the Beethoven page, because
the page prints none and **the staged pipeline has no CARRY**. Measured
directly: pages 0–2 in ONE call read the true `2/4` on page 1 from 12 staves,
and page 2's systems still see nothing — the right answer is in the same log,
one page earlier, and nothing looks for it. The legacy pipeline carries it
(`source="carried_from_previous_page"`).

That is the next piece and it is bigger than this one: a meter is a fact of the
MOVEMENT, and carrying it means knowing where a movement starts.

## 5. ⚠️ TWO INFERENCES OF MINE THAT WERE WRONG, AND WHAT CAUGHT THEM

Both were one step from being reported.

1. **"The staff-line erasure is destroying the beam rung."** The CV reader
   found 98 strokes on the erased images against **609** on the originals, and
   `reader_declined` accounted for 230 of 247 black noteheads read as plain
   quarters. It looked decisive. **Rendering one cell killed it**: the five
   "beams" were the five staff lines. Measured properly, **557 of the 609
   (91%) sit within a third of a staff space of a staff line**, and exactly
   **one cell in 341** loses a genuine off-line stroke. The erasure is doing
   its job, and 91% of my evidence was staff lines counted as beams.
2. **"The durations are systematically doubled."** Bar sums peaked at 4.0
   against a true 2.0. **The sum counted every chord member separately.**
   Grouped into chords, 2.0 is a strong mode (81 bars) beside 4.0 (94) — and
   83 of those 94 turned out to be the lone whole rests of §2.

Sean read the crop independently and reported *"a treble clef, 3 flats and a
whole note rest"* — which is the finding, from the print, in one line.

**The pattern:** a number large enough to be convincing is not evidence about
its own cause. Both were settled by looking at the actual ink, and neither by
more counting.
