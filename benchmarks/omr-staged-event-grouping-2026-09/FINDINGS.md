# The chord was grouped after the stage that needed it

`Q.EVENT`, `rhythm.adjudicate_event`, and `consequences._event_totals`.
No flag — this closes a defect rather than adding a behaviour.

Sean, 2026-09-09: *"I feel like determining when notes and voices and chords
line up should be very early in the process."*

He is right, and the record says so three ways.

---

## 1. THE DEFECT

`grep -rn chord tools/omr/staged/` outside `export.py` returned **nothing**,
and the record held **no chord, event, onset or voicing quantity at all**.
`group_chords_in_measure` was called from exactly one place —
`export._events`, at serialisation time.

So every stage before EXPORT counted each chord member as a separate
time-advancing event. That includes **`consequences.reconcile_duration`** —
the pipeline's own bar-sum check, which sums `Q.DURATION` over a cell and
compares the total to the meter.

⚠️ **And it failed SILENTLY, which is why it survived.** An inflated total
simply never equals the meter, so the rule did nothing and said nothing. There
was no warning to notice.

Measured on Beethoven 5 / Litolff `984073`, flag-OFF exports:

| | page 1 | page 17 |
|---|--:|--:|
| bars containing a chord | 11 of 83 (13.3%) | **50 of 131 (38.2%)** |
| bars exactly on the printed meter, **grouped** | 42 | **18** |
| bars exactly on the printed meter, **ungrouped** | 41 | **13** |

On page 17 the double-count destroyed **5 of the 18** correct bars — 28% of
the evidence — before any consumer saw it. ⚠️ The inflation is **not a
constant to subtract**: 13 distinct values from 0.125 to 6.0 quarter-lengths.

## 2. WHAT LANDED

* **`Q.EVENT`** — a CELL-scoped decision: which glyphs of this bar sound
  together. ⚠️ **A VERDICT, not a measurement**, and the distinction is the
  architecture's own: `Q.GLYPH_BOX` already carried every glyph's x — the
  ingredient was on the record all along and nothing read it — but *"these are
  simultaneous"* is an interpretation of those positions under a tolerance.
* **A rest is its own event.** Nothing sounds together with silence.
* **`reconcile_duration` sums EVENTS.** Where a chord's members disagree about
  their value the MODE is taken, which is `group_chords_in_measure`'s own
  definition of an event's duration.
* ⚠️ **No event verdict means NO repair**, rather than a fall back to the old
  per-notehead sum. A bar whose grouping is unknown is a bar whose sum is
  unknown, and repairing against a possibly-inflated total is exactly the
  laundered guess that rule's `bound` exists to prevent.
* **`EVENT_X_TOLERANCE_WIDTHS = 0.6` is not a new constant** — it is
  `voicing.group_chords_in_measure`'s own default, adaptive (0.6 of the mean
  notehead width in the bar) rather than a pixel count.

**Effect, measured, same tree, flag OFF:**

| | page 1 | page 17 |
|---|--:|--:|
| glyphs → events | 296 → 272 | 745 → **573** |
| chorded events | 20 | **114** |
| `reconcile_duration` fired | 13 → **16** | 0 → 0 |

Page 17 fires zero in both arms and that is not a failure: with the carry off
it has **no meter at all**, and `reconcile_duration` is keyed on one. Its
number here is the page-1 row.

## 3. ⚠️ THE TWO GROUPINGS DO NOT AGREE, AND I COULD NOT MAKE THEM

The control I wanted was *"the record's grouping and the exporter's are the
same"*. **They are not**, and reverse-engineering stopped rather than
continued.

| | page 1 | page 17 |
|---|--:|--:|
| chord members, this decision (every notehead READ) | 24 | 172 |
| chord members, restricted to WRITABLE noteheads | 15 | 95 |
| `<chord/>` the exporter actually wrote | **16** | **102** |

Most of the gap is a **population** difference — this decision groups every
notehead we read, the exporter groups only the ones it can write. A residual
of **1 and 7** survives that, and two candidate explanations were tested and
**refuted**:

* *the tolerance is computed over a different set of widths* — recomputing it
  over the writable noteheads gives the **identical** 15 and 95;
* *the exporter also admits NARROWED durations* — that **overshoots**, 24 and
  115 against 16 and 102.

The exporter's population sits **between** the two, so its boundary is its own
filter chain (`_dotted_duration_for_beats` on the written value), not the
clustering rule. **What is pinned instead is RULE parity**: given the same
detections, this decision and `group_chords_in_measure` produce identical
groups (`TestTheClusteringRuleIsTheEXPORTERS`).

⚠️ **This argues FOR unification rather than for more reverse-engineering.**
Two groupings that answer the same question differently is the state this work
set out to remove, and the way to remove it is the exporter consuming this
verdict — which changes the file and therefore needs its own measurement. It
is the next step, now evidenced as necessary rather than merely tidy.

⚠️ **The reconcile fix does not depend on it.** A bar sum asks whether the
music we READ fits the meter; a note we read but cannot serialise is still time
in the bar. Summing over read events is the right semantics for that check
whatever the exporter can write.

## 4. ⚠️⚠️ A FIELD THAT CLAIMED A CHECK THAT NEVER RAN

The legacy rule carries a **divisi guard** (a 2026-07 audit follow-up): two
noteheads at the same x whose STEMS POINT OPPOSITE WAYS are two voices, not one
chord, and are not merged.

The first draft of this decision reported `divisi_guard: "ran"` wherever
`Q.STEM` rows merely EXISTED. **The guard is not built** — I only tested
whether its input was present — so the field asserted a check that never
happened, which is the exact failure this record exists to make impossible. It
was caught by reading the field's own output on a real page (`{'ran',
'unavailable:declined'}` — a guard that "ran" on a path where nothing
implements it).

Corrected to `divisi_guard: "not_implemented"` with `stem_evidence` reporting
the state of the input the guard would need. **Where chords were formed and
`stem_evidence` is not `read`, two divisi voices may have been merged into one
chord and nothing could have caught it** — that is now on the record per cell.

⚠️ The guard is already inert in `export._events` too, for the same reason:
the staged path never sets `stem_direction`, and `_directions_conflict`
documents that "unknown direction never blocks a merge". So this reproduces
what the exporter does TODAY, not what the legacy rule can do with stems.

## 5. The architecture caught one of my errors

`implicates` was first declared `(Q.DURATION, Q.METER)` and
`test_a_failed_check_implicates_the_decision_ITSELF` failed on it. It is right:
a bar that does not sum may hold a wrong duration, a wrong meter — **or two
notes I merged that are not simultaneous, or one chord I split in two.**
Declaring only the durations would have quietly decided the grouping was
innocent.

## 6. What this unlocks next

1. **Cross-staff corroboration of the meter** — the reason this matters most.
   Every staff of a system prints the SAME bar, so bars grouped by column
   become N staves witnessing ONE bar length, which is the
   `METER_COVERAGE_FLOOR` logic applied to rhythm instead of to the template
   reader. ⚠️ **Blocked on a coordinate frame**: every `glyph_box` is in CELL
   frame (`cell:0`, `cell:8`…) and cells are canonically rescaled, so
   cell-frame x is **not comparable across staves**. Page-frame x is what that
   needs — the same lesson already written down for slurs.
2. **Voices.** A staff carrying two rhythmic streams inflates its bar total the
   same way a chord did. ⚠️ **Not measured** — I have not separated voice
   inflation from ordinary reading error on page 17, so its share of that
   page's 13.7% is unknown.
3. **The divisi guard**, once `Q.STEM` carries a direction.

## Reproducing

```bash
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
python3 -m tools.omr.staged "$PDF" --pages 17 --weights "$W" \
    --out ev.json --musicxml ev.musicxml
python3 benchmarks/omr-staged-meter-carry-2026-09/probe_bar_sums.py p1.musicxml p17.musicxml
```
