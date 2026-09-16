# `OMR_METER_CARRY` on Breitkopf Brahms 1 — the COST side

**2026-09-15.** [docs/handoff-2026-09-11-phase-2-opened.md](../../docs/handoff-2026-09-11-phase-2-opened.md)
§5.1 / §8.7 — *"the cheapest thing that settles it: the same arm on Breitkopf
Brahms 1 p0-3."* Four arms (`OFF` / `CARRY` / `BARS` / `BOTH`) over ONE gather.

⚠️⚠️ **HEADLINE: the carry RAN on five of seven systems, the bars REFUSED it on
all five, and all four exports are BYTE-IDENTICAL. The misread `9/4` does not
propagate, because it structurally cannot.** The brief's premise is refuted by
the mechanism rather than by the number.

⚠️⚠️ **LANDING STAMP, 2026-09-16 — THIS ARM MEASURED A TREE THAT NO LONGER
EXISTS, AND THE RULES THAT SUPERSEDE IT ARE THE ONES IT IS ABOUT.** Merged to
main at `328c7ac0`. The gather provenance below names `ce7b8ba7`; verified at
landing time, that commit **does not carry `METER_CHANGE_MIN_STAVES`** and main
does (2 occurrences in `tools/omr/staged/adjudicators/rhythm.py`). `A-METER-6`
— *an uncorroborated change is not carried off its system* — landed in PR #35
(`000812bd`) **after this arm ran**, together with the default-ON flip of both
meter flags.

⚠️ **The direction is expected to be preserved and was NOT re-measured.**
`A-METER-6` only ever makes a carry MORE conservative, so *the bars refuse it*
and *the exports are byte-identical* should hold at least as strongly on
current main. **That is a prediction, not a measurement** — nothing here was
re-run, and if the byte-identity figure is ever load-bearing for a decision it
wants the arm re-running against `328c7ac0` or later. The record is on disk
(`library/_shared-records/brahms1-breitkopf-p0-p3.record.json`, md5 verified at
landing) and the arm is the scripts in this directory.

⚠️ Kept rather than dropped, per this repo's own rule: *a superseded
measurement with its correction beside it is worth more than a gap.*

---

## 1. Control, before any arm is read

`CONTROL: 4365 of 4365 duration verdicts reproduced exactly, 0 differ, +0 extra`
— matching to the unit the figure CLAUDE.md already records for this document.
Gather provenance `{commit: ce7b8ba7…, dirty: False}` — a clean tree.

## 2. ⚠️⚠️ REACH IS 5 OF 7, AND `summary.meter` MISLEADS ON EXACTLY THIS POINT

`summary.meter` reads `{"decided": 7}`. **That is rung 3's outcome, not the
READING's**, and taking it at face value gives the wrong answer — *the managing
session did exactly that and was corrected here.*

`_meter_fallbacks` (`staged/adjudicators/rhythm.py:1941`) orders the rungs by
what each KNOWS: **`_carry_meter` at 1970 (rung 1)**, `_meter_from_bars` at 1973
(rung 2), **`_change_only` at 1976 (rung 3)**. The five `change_only` verdicts
each carry **`opening_unknown_because`** (`no_evidence` ×2,
`too_few_staves_read_it` ×3) — that string IS the `why` argument to the chain.
**So those five systems' readings failed, they entered the chain, and the carry
was ASKED FIRST and REFUSED.**

⚠️ **The reach question for this family is *how many systems entered the
chain*, never *how many carry an abstained verdict*.** Only **2** systems
actually read a meter: `system/0/0` `voted 6/8` (correct) and `system/1/0`
`voted 9/4` (the misread).

## 3. The arms — byte-identical, and the positive controls that make that a result

Four arms, one md5: **`2ce02c810d9c74b3f29c4edd30ab58df` ×4.** Every counter
identical — notes 2444, rests 949, `measure_rests_read` 104,
`empty_bars_padded_without_meter` 14, rests at 4.0 **373**, at 9.0 **11**.

⚠️ **On Litolff, carry/bars/both were identical to EACH OTHER and DIFFERENT from
OFF**, with the carry's support exactly `W_METER_CARRIED = 1.0` higher. **Here
all four collapse together**, so that relation is not re-observed — there is no
support figure, because nothing carried.

**Three positive controls that this is a REFUSAL and not a dead flag:** each
arm's JSON records its own distinct `env`; the flag-on arms ran **LONGER** than
OFF (68 min vs 69-75) walking `_bar_lengths_for`; and decisively, the
`opening_unknown_because` details above.

## 4. WHY it was refused — the arithmetic, corroborated two ways

Voting bars per system: **2, 0, 2, 0, 2, 1, 1**. Against
`METER_CARRY_MIN_BARS = 2`, three of the five needing a carry are refused
outright (0, 1, 1 bars); the two with exactly two bars score
**`+1.0 − 2.0 = −1.0`** against `METER_CARRY_FLOOR = 2.0`.

Corroborated independently by the record: **every `4/4` segment carries
`bars_fit: 0`, six of six.** Not one bar on these pages fits 4/4.

⚠️⚠️ **THE `9/4` IS UNCARRYABLE.** `system/1/0` votes `9/4` at cell 0 *and*
prints a later `4/4` segment at cell 2, so `_meter_in_force_at_end` hands on
**4/4**. **The `OMR_METER_SEGMENTS` repair is what prevents the exact
propagation the brief feared.**

## 5. Blast radius — ZERO

`ELEMENTS 3546 → 3546, changed 0. NOTE <type> MOVES: 0. PITCH MOVES: 0.
REST MOVES: 0.` The Litolff arm moved **72** unchecked `<type>` values; here
`reconcile_duration` is never fed. **Zero things for a human to put back.**

## 6. Bar fill, as a PAIR (818 bars, identical in all arms)

| | truth-referenced (`--bar-beats 3.0`) | self-referenced (the file's own `<time>`) |
|---|--:|--:|
| exact | **101 (12.3%)** | **173 (21.1%)** |
| SHORT | 226 (27.6%) | 228 (27.9%) |
| OVERFULL | 491 (60.0%) | 169 (20.7%) |

⚠️ **The gap IS the misread**: the file agrees with its own declared meter nearly
twice as often as with the page. Both `--check` runs exit 0
(`instrument LIVE: 818 bars`); **neither gate is a threshold**, because a
bar-fill number used as a gate is gamed by emitting FEWER symbols.

Litolff's currency reproduced here: `empty_bars_padded_without_meter`
**14 → 14** (Litolff 168 → 0); bars that add up **12.3% → 12.3%** (Litolff
38.0% → 69.2%).

## 7. ⚠️⚠️ HOW FAR THE MISREAD TRAVELS — AND IT IS NOT EITHER FLAG UNDER TEST

`<time>` in the file: **`4/4` ×83, `6/8` ×14, `9/4` ×14**, on a movement printed
in **6/8 with one 9/8 bar**. Measures GOVERNED: `4/4` **430 of 818 (52.6%)**,
none 248, `6/8` 112, `9/4` 28.

**458 of 818 measures (56.0%) are governed by a meter the page does not print**
— showing in the rests as 11 measure rests at 9.0 ql and 108 at 4.0 in 3.0-ql
bars. ⚠️⚠️ **It arrives through `_change_only` under `OMR_METER_SEGMENTS`,
already DEFAULT ON — not through either flag under test.** Each spurious `4/4`
clears `METER_CHANGE_FLOOR = 3.0` on glyph evidence from **1-4 staves of 14**,
with `bars_fit: 0`.

## 8. `METER_CARRY_MIN_STAVES_PER_BAR = 3`, priced for the first time

CLAUDE.md records it as *"set by analogy to `METER_COVERAGE_FLOOR` and never
measured at all."* **It costs 2 bars of 360 (0.6%) — nearly inert.**

What actually silences the bars is the **fixpoint guard (301 of 360, 83.6%)**
and the **MAJORITY rule (49, 13.6%)**: ⚠️⚠️ **49 of 59 assessable bars have
staves contradicting EACH OTHER about their own length.** That is the sharpest
form yet of *"the bars are not an independent umpire over a bad reading"* —
here they do not merely fall silent, **they disagree among themselves on the
same ink the meter reader failed on.**

## 9. ⚠️ The fixpoint stays closed

`_bar_lengths_for` still excludes **ANY** bar holding a whole rest, verified in
the tree. **Nothing in this work widens the corroboration basis**, no constant
was tuned, and **no production file was touched** — every commit under
`benchmarks/`.

## 10. Is the objection RETIRED or CONFIRMED? **NEITHER.**

The weighing DID run; the candidate was **`4/4`, not `9/4`**; the bars refused it
everywhere. ⚠️ But that does **not** retire the objection: **this page refuses a
CORRECT candidate as readily as a wrong one**, so the protection observed is
*"when the page cannot speak, abstain"* — the *Andante* lesson, on a second
publisher.

⚠️⚠️ **THE COST SIDE REMAINS UNMEASURED, BECAUSE NO DOCUMENT IN HAND CAN EXPRESS
IT.** It needs **BOTH** (1) abstaining systems, so the carry has something to
serve, **AND** (2) a wrong meter standing in force to be carried. **Litolff has
(1) and not (2); Breitkopf has (2) and not (1).**

⚠️ **Two sessions have now selected on PRINT QUALITY and neither got both. Print
quality is the WRONG CRITERION**, because *a confidently wrong reader does not
abstain, and the carry only ever serves abstentions.* **That pair is the
selection criterion for a third document.**

## 11. Recommendation to Sean — the flip is yours

| | Litolff (benefit) | Breitkopf (this) |
|---|--:|--:|
| systems the carry serves | 6 of 7 | **0 of 5 that asked** |
| bars that add up | 38.0% → **69.2%** | 12.3% → **12.3%** |
| `empty_bars_padded_without_meter` | 168 → **0** | 14 → **14** |
| `<type>` values moved unchecked | **72** | **0** |
| file changed | yes | **byte-identical** |

**The measured cost of turning `OMR_METER_CARRY` on, on the document whose meter
reading is known bad, is ZERO in every currency the benefit was measured in.**

⚠️ **Read that as a BOUND, not a blessing: it is zero BECAUSE the mechanism was
refused**, for the same reason the document reads badly.

⚠️⚠️ **The larger finding on this page is not about either flag — 52.6% of
exported measures are governed by a `4/4` the page never prints, via a mechanism
that is ALREADY DEFAULT ON. If a meter default is worth revisiting, that is the
one.**

## 12. Not established

Safety of the carry (it fired on nothing); accuracy against the print beyond the
meter itself; that `METER_CARRY_MIN_STAVES_PER_BAR = 3` is *right* (only its
price); the LilyPond bar-check cost of the 458 measures (Beethoven 3's 390-vs-164
is quoted, not re-measured); the engraved family, untouched by construction.
**n = 1 document, 1 publisher, 4 pages, 7 systems, 818 exported measures.**
