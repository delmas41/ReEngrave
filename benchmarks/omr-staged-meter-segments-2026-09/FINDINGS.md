# `Q.METER`'s segments reach the file — and the false positive they would have carried

2026-09-09. The top-ranked item of
[`docs/handoff-2026-09-09-the-boundary-measured.md`](../../docs/handoff-2026-09-09-the-boundary-measured.md)
§5 and of [`../omr-staged-meter-boundary-2026-09/FINDINGS.md`](../omr-staged-meter-boundary-2026-09/FINDINGS.md)
§5: three gaps the boundary session found by `grep` and deliberately left
unbuilt, because each needed its own measurement pass.

They are one fix — **carry, borrow from, and EXPORT the meter in force at each
bar, off the `segments` that already exist** — plus the false positive that
fix would otherwise have propagated.

---

## 1. What was wrong

| # | gap | where |
|---|---|---|
| 1 | the export took ONE meter per staff-run, so a mid-system change reached no file | `staged/export.py` |
| 2 | the carry took the source's OPENING and deleted its `segments` | `rhythm._carry_meter` |
| 3 | a system that READ a change could not be a carry or form source | `rhythm.py`, `reason == "voted"` |

`record.meter_at` — whose own docstring says it *is* how a bar's meter is
read — was called by nothing but its own tests.

---

## 2. What it is worth, on the ENGRAVED arm

Controlled A/B on the SAVED records, so no detector jitter enters: the old
behaviour is monkeypatched back in and the same record exported twice.

| fixture | before | after |
|---|---|---|
| Brahms 1 iv (`C` → `¢`) | `{4/4(common): 24}` | `{4/4(common): 24, **2/2(cut): 24}` |
| Brahms 1 i | `{6/8: 21, 9/8: 21}` | `{6/8: 42, 9/8: 42}` |
| Litolff p.61-62, `<time>` at | m1, m8 | m4, **m16** |

The cut-common — read on **24 staves of 24 at support 74.0** — reached no file
at all and now reaches every part. And Litolff's printed `3/4` moves to
measure 16, the **ninth bar of its system**, which is where the hand-read
truth puts it; it had been applied from that system's first bar, giving eight
bars a meter the page does not state there.

⚠️ **That last one is `meter_at` doing the thing it exists for.** A bar no
segment covers returns `None`, and the exporter already withholds
`measure="yes"` where the meter is unknown — so *"unknown until bar 9, 3/4
from there"* survives into the file instead of being flattened.

---

## 3. The false positive: a CAUTIONARY — built twice, and the other one is kept

⚠️⚠️ **A SIBLING SESSION REACHED THIS INDEPENDENTLY AND LANDED FIRST**
(`a54a6be6`, `TestACautionaryIsNotAChange`). Their rule discriminates on the
**LAST CELL** of each staff; this one on how much of the bar's own ink stands
to the LEFT of the glyph. **Theirs is kept, and it is the better rule on
reach**: it catches the Breitkopf scan's courtesy too, which this one
explicitly could not — that degenerate final cell holds five detections, so
nothing lies left of the glyph and the left-fraction reads 0.000 there. It
also carries an escape this one lacked: a last-cell candidate whose OWN BAR
FITS is still a change.

**What survives, and it is worth more than a second implementation would
be:** an independent second reading of the same engraving convention, from a
different quantity. Two sessions, two discriminators — ink-position and
cell-ordinal — one conclusion, on the same fixtures. The measurement below is
kept for that reason, not as a claim on the code.

### The convention, measured by ink position

`_meter_changes` had no notion of a courtesy signature — any glyph in a cell
after the first was a change — so the `9/8` Brahms 1 prints **after page 0's
final barline**, to announce the next system, became a segment re-sizing that
page's last bar.

The engraving fact: a change is printed immediately after the barline that
OPENS its bar, so the bar's music lies to its **right**; a courtesy stands
after the system's final barline, so the music lies to its **left**.

Measured per READING over every segment the benchmark proposes:

| | left-fraction |
|---|--:|
| the one cautionary in the corpus (19 staves, 38 rows) | **1.000** (min = median = max) |
| every other segment, true or false | **≤ 0.118** |

The constant sits in an empty interval from 0.118 to 1.000; 0.5 is the middle
of it. The comparison is against the bar's **own ink**, not the cell's width,
so it needs no unit — the cell widths on these pages run 298 to 2048 px.

---

## 4. The tally

`report_boundary.py --tally`, counting SEGMENTS.

| fixture | printed | proposed | found | FALSE |
|---|--:|--:|--:|--:|
| Brahms 1 i ENGRAVED | 1 | 2 → **1** | 1 | 1 → **0** |
| Brahms 1 i BREITKOPF SCAN | 1 | 8 | 0 | 8 |
| Brahms 1 iv ENGRAVED (`C`→`¢`) | 1 | 1 | 1 | 0 |
| Beethoven 5 iv ENGRAVED (fwd) | 0 | 0 | 0 | 0 |
| Beethoven 5 iv ENGRAVED (rev) | 1 | 1 | 1 | 0 |
| Beethoven 5 LITOLFF SCAN | 1 | 2 | 1 | 1 |

**ENGRAVED 4 printed / 4 found / 1 → 0 false. SCANNED 2 / 1 / 9, unchanged.**

**1 of 9 false segments removed, 0 of 4 true positives lost.**

⚠️ **THE SCAN IS UNTOUCHED AND THAT IS THE EXPECTED RESULT, NOT A SHORTFALL.**
§4b already concluded that fixture's problem is the meter GLYPH readers rather
than the weighing, and the left-fractions confirm it from the other side:
every one of the scan's false segments reads **0.000** — at the head of its
bar, exactly where a real change stands. They are misreads, not misplacements,
and no placement rule can or should reach them.

---

## 5. ⚠️⚠️ THREE THINGS THIS SESSION GOT WRONG, AND HOW EACH WAS CAUGHT

Kept because the corrections are the finding.

### 5a. A fixture that does not match GATHER tests the test

The cautionary rule shipped, five unit tests passed, three went red under
mutation — and **the benchmark tally came back byte-identical to its
baseline**. `gather.gather_meter_glyphs` files `Q.METER_GLYPH` against the
**STAFF**, with the bar in `detail["cell"]`; the fixture filed it against a
**GLYPH**. `_looks_cautionary` derived its cell with `subject.at(Kind.CELL)`,
which returns `None` for a staff because a cell is *deeper*, so on every real
page it read no boxes and returned `False`.

The mutation tests were true and meaningless: they exercised a shape no
gather site emits. ⚠️ **The pre-existing `TestAMeterChangeIsReadFromTheInk`
fixture had the same mismatch**, which is why the bug had somewhere to hide.
Both fixed, and `TestTheFixturesFileMeterGlyphsWhereGATHERDoes` now asserts
the shape against the gather site **by AST** rather than against a remembered
string.

**What caught it was the number that did not move.**

### 5b. A cautionary belongs to a READING, not to a cell

The next arm removed the engraved false positive and left Litolff's. The rule
asked whether *every staff with a glyph at that bar* looked cautionary — but
p.61 cell 3 carries three staves reading three different things, and only one
of them wins. Asked per reading, it fires where it should.

### 5c. ⚠️ The claim that it caught TWO cautionaries was mine, and it was a
probe bug

An earlier draft of the constant's docstring — and of what I reported —
said *"both cautionaries read 1.000"*. That came from a probe that pooled
**every** staff with a glyph at the cell instead of the staves that READ the
segment, turning Litolff p.61's mixture of three readings into a single
1.000. Measured properly, that page's false `C` is one staff at **0.118**, at
the head of its bar: a misread, not a courtesy.

**The corpus contains exactly ONE cautionary this rule can see.** The
Breitkopf scan engraves the same courtesy and it reads 0.000, because that
degenerate final cell holds five detections and there is no music left of the
glyph to find.

### 5d. And a fourth, in the carry

Fixing the value `_carry_meter` RETURNS was half the bug: `_corroborate` was
still weighing the **opening**, so on a source that printed `3/4` and changed
to `2/4`, the next system's 2.0 bars were scored against `3/4` and a correct
carry was refused `carry_outweighed_by_the_bars` at **−2.0, 0 agreeing / 3
disagreeing**. Found by a test failing, not by reading the function.

---

## 6. The flag — ON by default

`OMR_METER_SEGMENTS`, **default ON since 2026-09-09 (Sean's call)**, gating
the export half only — findings 2 and 3 live inside `_carry_meter` /
`_meter_from_bars`, already gated by `OMR_METER_CARRY` and
`OMR_METER_FROM_BARS`. The cautionary rule is **unflagged**: it only ever
removes a false segment, and it is recorded (`cautionary_cells`, as
`(cell, raw)` pairs) rather than dropped, because a courtesy is this system's
statement about the NEXT one.

It shipped OFF, on **n** rather than on the mechanism, and was flipped the same
day. ⚠️⚠️ **THE FLIP OVERRIDES THE STANDING OBJECTION RATHER THAN RESOLVING
IT**, and the objection is now a number instead of a description.

| | `<time>` elements | |
|---|--:|---|
| Brahms 1 / Breitkopf p.1-2 (14 parts), `=0` | **41** | the per-run meter |
| the same page, default | **138** | `4/4` 13 → 96, plus 14 spurious `9/8` |

Those 83 extra `4/4` declarations are the five one-staff spurious changes at
support 3.5-4.0; the 14 `9/8` are the courtesy signature this rule cannot
reach on that degenerate final cell. **So a scan can now export a meter change
its page does not print.** Every ENGRAVED fixture gains only correct changes,
and **4 of the 9 committed boundary records are byte-identical either way** —
which is the blast radius: pages carrying a read change, and no others.

**The lever is the meter GLYPH readers** (`_meter_from_digits`,
`time_signature_locator`), not the weighing and not a placement rule. Until
that lands, `OMR_METER_SEGMENTS=0` restores the per-run meter exactly.

⚠️ **THE OFF TEST IS A DENY-LIST, AND THE DIRECTION FLIPPED WITH THE
DEFAULT.** `_carry_meter` reads *"anything but an explicit 1 is off"*, because
while a mechanism is off a typo must not switch a document ONTO it. On by
default the hazard runs the other way: with an allow-list — `in ("1", "true",
"yes", "on")`, which is what `OMR_SLOT_STITCH` and the other default-on flags
here use — an empty value or a misspelling silently RESTORES the bug. Only an
explicit off word turns this one off. ⚠️ **The allow-list default-on flags
carry that hazard today**; this one does not copy it. Caught by a test written
for the flip, which failed on the first attempt.

## 7. Reproducing

```bash
B=benchmarks/omr-staged-meter-boundary-2026-09
WS=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
python3 $B/run_arms.py --pdf $B/fixtures/brahms1-m1-22.pdf --pages 0-2 --tag m7brahms1eng --arms OFF
# ... the other six, see §7 of the boundary FINDINGS for the full set
PYTHONPATH=$PWD python3 $B/report_boundary.py --tally $B/out --prefix m7
```

⚠️ `--tally` reads the committed `out/*.meter.json` reduction when a full
record is absent, so the BASELINE is checkable on a fresh clone with no
weights and no re-transcription. It could not be before this session: the
reduction is what every figure is read off, and `meters()` accepted only the
gitignored full record's shape.

⚠️ `--prefix` scores a run GENERATION against truth tables keyed on the
FIXTURE. Baking a generation into `TALLY_SET` meant a re-run could only be
scored by editing the table it is scored against.
