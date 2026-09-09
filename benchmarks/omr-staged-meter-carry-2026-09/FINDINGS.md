# The meter carry — measured on both sides, and OFF because of the second one

`OMR_METER_CARRY`, `tools/omr/staged/adjudicators/rhythm.py`. Default **`0`**.

A meter is a fact of the **MOVEMENT**: printed at its start and nowhere else.
Everything in the staged pipeline works a system at a time, so the second page
of a 2/4 movement has no meter at all — and the right answer is sitting in the
same log one page earlier, with nothing looking for it. `transcribe` carries it
(`source="carried_from_previous_page"`); the staged pipeline had no carry.

This adds one. It fires **only from an abstention branch**, so it can never
overturn a reading, and it records where the value came from and how far.

---

## 1. Both arms, one document, one call each

Beethoven 5 / Litolff `984073`, weights `hollow-graft-shift09`, `--pages 0-2`.

⚠️ **The control first, because it is what makes the rest attributable.**
Flag-OFF reproduces the pre-change run **exactly** — all 4,498 verdicts
identical in outcome, reason and value, and all 12,782 observations. So the
change is inert when off, *and* this document runs deterministically, which is
the only reason an ON/OFF delta on two separate runs can be read as the flag's.

### What the carry decided

| system | flag OFF | flag ON |
|---|---|---|
| `system/1/0` | **decided `2/4`**, `voted`, 12 of 12 staves | unchanged |
| `system/2/0` | abstained `no_evidence` | **decided `2/4`**, `carried` |
| `system/2/1` | abstained `too_few_staves_read_it` | **decided `2/4`**, `carried` |

Both carries record `carried_from: system/1/0`, `pages_since_read: 1`,
`source_share: 1.0`, `source_staves_spoke: 12`, and the abstention they
replaced.

### What that changed downstream

**Exactly two quantities move: `meter` (2) and `duration` (111).** Every one of
the 111 is on page 2. Nothing else in the log moves at all.

| durations that moved | OFF → ON | reason |
|--:|---|---|
| **77** | 4.0 → **2.0** | `rest_class` → `whole_rest_means_the_bar` |
| **20** | *none at all* → 0.5 | `beams_ambiguous` → `meter_reconciliation` |
| 5 | 2.0 → 1.0 | `head_and_marks` → `meter_reconciliation` |
| 4 | 0.5 → 1.0 | `head_and_marks` → `meter_reconciliation` |
| 2 | 0.25 → 0.5 | `head_and_marks` → `meter_reconciliation` |
| **2** | *none at all* → 1.0 | `beams_ambiguous` → `meter_reconciliation` |
| 1 | 1.0 → 2.0 | `head_and_marks` → `meter_reconciliation` |

⚠️ The predecessor handoff estimated **83** mis-sized lone whole rests on this
page. Measured, it is **77**. Quoted as measured.

### And in the file

`--musicxml`, same two arms:

| | OFF | ON |
|---|--:|--:|
| `<time>` elements | 12 | **25** |
| whole rests written `<type>whole</type>` at **4.0 ql** in a **2.0 ql** bar | **194** | **70** |
| `<rest measure="yes"/>` at 2.0 ql | 108 | **231** |
| `written.notes` | 646 | **664** |
| `notes_not_written_total` | 219 | **201** |
| `not_written.duration_narrowed` | 165 | **147** |
| `not_written.no_pitch` | 54 | 54 |
| `written.empty_bars_padded_without_meter` | **47** | *field gone* |
| `detected_and_unrepresented_total` | 659 | 659 |

**123 whole rests stop being 4.0 quarters of silence in a 2.0-quarter bar.**
The arithmetic is checked against each part's own `divisions` and not assumed:
`divisions=48`, `<duration>96` = 2.0 ql = one bar of 2/4, in both arms — what
changes is how many bars *reach* it. The ON file parses under music21, 12 parts.

⚠️ **Two of those rows are controls, and they are the ones that did NOT move.**
`no_pitch` is unchanged because a meter says nothing about pitch, and
`detected_and_unrepresented_total` is unchanged because the carry reads no new
ink. A carry that had moved either would have been doing something it has no
business doing.

⚠️ **A −1 was chased rather than rounded off.** Total rests went 433 → 432, so
one rest is *not* accounted for by the 123 conversions. It is P4 measure 44: in
the OFF arm a whole rest at 192 (4.0 ql), in the ON arm a **B3 quarter note**.
Nothing was lost — that bar had been *padded* because its only note had no
duration (`beams_ambiguous`), and `meter_reconciliation` gave the note a value,
so the pad is no longer needed. It is one of the 18 recovered notes, arriving
in the rest column.

The three counts agree to the unit: **18 notes recovered = 18 fewer
`duration_narrowed` = +18 `written.notes`.**

---

## 2. ⚠️⚠️ THE HAZARD, ON THE SAME DOCUMENT — WHY THE FLAG IS OFF

Page 17 of `984073` is the ***Andante con moto***: a **new movement**, printing
`3/8` on every one of its staves. Run `--pages 1,17`:

| system | flag OFF | flag ON |
|---|---|---|
| `system/1/0` (mvt 1) | decided `2/4`, `voted` | unchanged |
| `system/17/0` (mvt 2) | abstained `no_evidence` | **decided `2/4`** ← **wrong, it is 3/8** |
| `system/17/1` | abstained `no_evidence` | **decided `2/4`** ← wrong |
| `system/17/2` | abstained `no_evidence` | **decided `2/4`** ← wrong |

Each carries `pages_since_read: 16`.

**The movement start reads nothing, and this is diagnosed, not guessed.** The
template reader **ran on all 20 staves of page 17** and declined
`below_threshold` on every one — the record says so, it is not silence. `3/8`
*is* in `DEFAULT_METERS`, so it is not a missing template. Rendering the ink
shows why: Litolff sets `3` over `8` as heavy, nearly-touching digits that do
not correlate with the Bravura templates. That is the digit-template family
CLAUDE.md's standing rule says is **never tuned on one edition**.

So an unconditional carry does not merely risk crossing a movement boundary on
this document — **it does cross it**, and then keeps the wrong meter for the
rest of the movement, since nothing later in the Andante reads one either.

### Four guards were looked for. All four are REFUTED by measurement.

1. **"A movement start reads SOME meter; a continuation reads none."**
   **Inverted.** The continuation systems on pages 14-16 read **1-4** spurious
   `C`/`4/4` each; the movement start reads **0**.
2. **The key signature changes at a movement boundary.** Unusable on a scan.
   Only a handful of staves per system decide a key and they disagree with each
   other — `p14/s1` reads `{-5, -3, -1, 2}` — and the Andante's true **−4** is
   never among the readings anywhere on page 17.
3. **The printed tempo heading.** Page 17 prints "Andante con moto." three
   times and this is the right signal *in principle* — the engraver's own mark
   for "a new movement starts here". `direction` yields **0 decided verdicts**
   in the staged record today, on both runs, so it cannot be asked.
4. **A distance bound.** Decisive, and it is arithmetic rather than a sweep:
   movement 1 occupies pages 1-16, so a meter read on page 1 legitimately
   governs **16 pages**. Any bound under 16 truncates a legitimate carry *in
   this document*; any bound of 16 or more reaches the Andante. **No reach
   constant separates benefit from hazard.**

**So the blocking input is named, and it is a MOVEMENT-START signal — not a
threshold.** Flip the flag the day one exists. The likeliest source is (3): the
tempo heading is genuinely printed and genuinely diagnostic, and it is blocked
on `direction` being a stub rather than on anything about movements.

---

## 3. Two design rules, and why each is in the code rather than here

**A carry NEVER chains onto a carry.** Only a `voted` verdict is a source, so
`pages_since_read` is the true distance back to *ink*. That is what makes the
number worth reading: a meter carried 16 pages is visibly suspect in the
record, where a chain of sixteen one-page hops would each have looked local.
Pinned by `test_a_carry_NEVER_chains_onto_a_carry`, which goes RED when the
`voted`-only line is removed.

**A carry never overturns a reading.** It is reached only from the three
abstention branches, so it is structurally incapable of overwriting a system
that read its own meter — which is also why the coverage floor (`9dec5cb6`)
had to land first: without it, the 3-of-11 spurious `C` on `system/2/1` would
have been a *decision*, and would then have been the thing that carried.

---

## 4. Reproducing

```bash
ln -sfn <main checkout>/library library        # the PDF; no venv needed
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

# benefit — the two arms of §1
OMR_METER_CARRY=0 python3 -m tools.omr.staged "$PDF" --pages 0-2 --weights "$W" \
    --out off.json --musicxml off.musicxml
OMR_METER_CARRY=1 python3 -m tools.omr.staged "$PDF" --pages 0-2 --weights "$W" \
    --out on.json  --musicxml on.musicxml

# hazard — §2
OMR_METER_CARRY=1 python3 -m tools.omr.staged "$PDF" --pages 1,17 --weights "$W" \
    --out hazard.json
```

`out/` holds the meter verdicts of all four runs and the two coverage reports.

⚠️ Measure a carry on a **multi-page run only**. The scan gate transcribes ONE
PAGE PER ROW, which silently disables every page-spanning mechanism — it would
report this change at exactly zero, twice.
