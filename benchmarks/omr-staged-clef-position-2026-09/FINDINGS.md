# The clef that could not decide, and why the filed fix would not have reached it

Chosen because the record said it was the cheapest of the 595 events held back
— and the first thing checking it did was **falsify the fix that was filed.**

---

## 1. ⚠️ THE FILED FIX REACHES NONE OF THIS POPULATION

`adjudicate_clef`'s **own first `checked_by`** is *"implied pitches: this
staff's own measured positions under this candidate must fall in the
instrument's written range"*, and `inventory --check` has listed it as a
declared-and-never-read `wants` entry. It looked like the obvious fix for an
abstaining clef.

It needs the **instrument**. On the two scanned pages measured, `instrument`
abstains `no_evidence` on **22 of 22 and 27 of 27 staves** — no margin label is
read anywhere. So the range test would have fired **zero times** on exactly the
staves it was filed to fix. That matches the standing measurement that the
legacy written-range veto *has never fired on a scan*.

The `KNOWN_GAPS` entry now says so, so nobody reaches for it again.

## 2. What the population actually is: a NEIGHBOURING STAFF'S CLEF

Of the six staves whose clef did not decide across the two pages, **five are an
exact `{"treble": 3.0, "bass": 3.0}` tie** — one `clefG` *and* one `clefF`
detected on the same staff at nearly the same x and 250–350 canonical px apart
in y. A measure cell is the staff plus four staff spaces of air, so on a
conductor's page the neighbour's clef lands in this staff's cell. It is the
documented cross-staff padding problem, in the header.

The sixth is `no_candidates` — no clef glyph at all.

## 3. The discriminator needs no identity, and the gap is empty

`Q.CLEF_POSITION`: where each clef glyph stands on **this staff**, in
half-spaces down from the top line — the same measurement a notehead gets, from
the same grid. The grid was computed in `gather_notehead_positions` and thrown
away, so nothing could ask the question.

| staff | on the staff | standing off it |
|---|--:|---|
| beet5 `2/1/6` | `clefF` **+3.5** | `clefG` −5.8 |
| brahms `1/0/4` | `clefF` **+3.1** | `clefG` +13.6 |
| brahms `1/0/8` | `clefF` **+3.2** | `clefG` −4.8 |
| brahms `1/1/4` | `clefF` **+3.4** | `clefG` +13.3 |
| brahms `1/1/7` | `clefF` **+3.3** | `clefG` −6.9, `clefG` +14.8 |

**Nothing between +3.5 and +13.3; nothing between −4.8 and +3.1.** The band is
deliberately wide (−2 to +10) because the separation is 8 steps clear on the
near side — a tight band would start deciding cases the evidence does not
separate.

## 4. ⚠️⚠️ THE STRUCTURAL FINDING: A STAFF'S CLEF DETECTIONS ARE **ONE SIGNAL**

The first cut put the position in the glyph row's `detail` and added a term
citing that row. **It changed nothing**, and the reason is worth more than the
fix:

Every `CLEF_GLYPH` row on a staff shares a reader, a frame and a quantity, so
`Evidence.correlated_groups` calls them **one signal** and `tally` counts the
group once, taking its strongest term. A 1.5 added beside a 3.0 is 3.0. So:

> **No refinement of the DETECTOR's own evidence can ever break a clef
> contest.** A tie-breaker has to come from a different reader.

That is the correlation rule working exactly as designed — it exists to stop
one reader's output being counted twice — and it is invisible until you try.
`Q.CLEF_POSITION` is therefore a **`GEOMETRY` row**, and the term cites it
rather than the glyph.

## 5. Result, with both controls

| | beet5 p3 | brahms p2 |
|---|---|---|
| clef decided | 20 → **21** of 22 | 23 → **27 of 27** |
| pitches decided | 835 → **881** | 1,329 → **1,470** |
| `no_pitch` held back | 67 → **54** | 75 → **0** |
| notes reaching the file | 516 → **528** | 664 → **707** |

Beethoven's remaining abstention is the `no_candidates` staff — **nothing read
a clef there at all**, which is a different and honest gap.

⚠️ **CONTROL 1 — it cannot overturn anything.** Over the 19 staves that already
decided *and* hold more than one clef glyph, the on-staff glyph agrees with the
decided clef **19 of 19**; **0 would flip**, and none has no glyph inside the
staff. The rule is a no-op on everything that was working.

⚠️ **CONTROL 2 — an independent signal agrees.** All five ties resolved to
`bass`, which is the kind of uniformity that can mean a systematic error, so
the REGISTER of the resulting pitches was checked against staves decided
without the new term:

| | established bass | established treble | newly decided |
|---|--:|--:|---|
| beet5 p3, median MIDI | 50 | 71 | **48** |
| brahms p2, median MIDI | 52 | 69 | **52, 48, 59, 52** |

Every newly-decided staff lands in the bass band and none near the treble one.
That is `clef_register_warning`'s question asked from the outside, and it needs
no instrument either.

⚠️ **And the cross-system signal that seemed to CONTRADICT this was never
valid.** Two Brahms staves had a same-ordinal sibling that decided `treble`.
Brahms p2's two systems print **14 and 13 staves** — different lineups — so
slot *n* in one is not slot *n* in the other, which is exactly why
`groups._slot_fact` refuses to compare them. On Beethoven, where both systems
print 11, the sibling decided `bass` and **agrees**.

## 6. What is left on this axis

* **54 notes on one Beethoven staff** where no clef glyph was detected at all.
  Neither geometry nor identity helps; that is the CV locator's or the
  detector's question.
* **`duration_narrowed` is now the whole of the Brahms shortfall** (296 of
  309). See the beam-edge measurement in
  `benchmarks/omr-staged-gather-2026-09/FINDINGS.md` §7.
