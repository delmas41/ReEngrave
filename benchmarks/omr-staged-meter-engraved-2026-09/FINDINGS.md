# The engraved render — and it settled the question by moving it upstream

⚠️ **No benchmark was run and nothing here is a score.** Every number is a
control or a diagnosis.

**Why an engraving.** Every measurement of the meter mechanisms until now is on
one scanned Litolff print, where a meter change is either a sparse texture or a
dense tutti and the bars cannot speak either way — so a failure could always be
blamed on the page. `benchmarks/omr-staged-meter-carry-2026-09/FINDINGS.md` §11
named the route and left it unspent: render the change through LilyPond, where
**the ink is perfect by construction, so a failure is a failure of the RULE.**

**The fixture.** `beethoven-sym5-mvt4` from the Gradus score library. Its meter
map, read off the file rather than quoted: **`{1: 4/4, 155: 3/4, 209: 4/4,
364: 2/2}`**, 23 parts, 446 measures.

```bash
python3 benchmarks/omr-staged-meter-engraved-2026-09/render_meter_change.py \
    --work beethoven-sym5-mvt4 --first 203 --last 218 --out-dir out/
python3 benchmarks/omr-staged-meter-engraved-2026-09/hide_change_signature.py \
    --ly out/beethoven-sym5-mvt4-m203-218.ly \
    --out-stem beethoven-sym5-mvt4-m203-218-hidechange --marker '\time 4/4'
```

---

## 1. ⚠️⚠️ THE HEADLINE — THE BAR SUMS ARE WRONG ON PERFECT INK

The whole bar-sum family — the carry's second witness, `OMR_METER_FROM_BARS`,
and Sean's per-bar model in `A-DUR-6` — rests on a page's own arithmetic being
readable. **It is not, and the scan was never the reason.**

Measured on the engraved bars 203-218, 23 staves, every part playing in every
bar (`playing parts per bar = 23` for all of 209-226):

| system | bars | truth | the bar sums we read |
|---|---|---|---|
| `0/0` | 203-205 | 3/4 | **3.0, 3.0, 3.0** ✅ at 5/8, 5/8, 5/9 |
| `1/0` | 206-214 | 3/4 then **4/4 from cell 3** | 3.0 ✅, then **4.0 at 20 of 23** ✅ on the change bar, then **3.5 (18/23)** ✗, **6.0 (20/23)** ✗ |
| `2/0` | 215-218 | 4/4 throughout | **5.0, 4.5, 5.0, 4.5** ✗ — not one bar right |

⚠️ **These are not noisy readings, they are CONFIDENT WRONG ones**: 18 of 23
staves agree on 3.5 where the truth is 4.0, and 20 of 23 agree on 6.0. The
cross-staff majority — the rule that is supposed to make a bar trustworthy —
passes them.

⚠️ **And the errors run LONG.** 3.5, 4.5, 5.0, 6.0 against a truth of 4.0.
A shortfall would suggest missed ink; an excess on a page with no missing ink
suggests the duration reader is composing something twice or reading a written
value too long. That is a diagnosis to open, not a conclusion.

**So the constraint on the bar-sum family is the DURATION READER, not page
quality.** Every previous conclusion of the form *"the bars cannot speak here
because the page is hard"* needs re-reading with that in mind — including this
session's own, which attributed the movement-start failures on Litolff p.17 /
p.32 / p.44 partly to sparse texture and dense tutti. The texture explanation
is still right about *how many staves* speak; it is not the reason the ones
that do speak are wrong.

---

## 2. ⚠️⚠️ AND A DETECTED-THEN-DROPPED BUG: A CHANGE TO COMMON TIME WAS INVISIBLE

The engraved fixture found this in its first arm, and only an engraving could
have: LilyPond spells 4/4 as a common-time **`C`**, so the change at bar 209 is
a letter, not two digits.

**The detector's own numbers, off the record:** on the change page,
`meter_glyph` = **23 rows, every one `timeSigCommon`, every one at cell 3** —
one per staff, at exactly the right bar. `meter_template` = 0 rows there,
correctly, since that reader only looks at the header window.

**And the system abstained `no_evidence`.**

`_meter_from_digits` required two stacked digits and skipped the letter with
the comment *"timeSigCommon and friends: no pair"* — true, and then the caller
counted it as a `loose` glyph, built no `readings` entry, and skipped the bar
entirely. **Perfect detection, dropped by the rule** — this project's signature
failure, inside the meter-change reader itself.

**Measured after the fix, same fixture, same command** — `system/1/0` goes
`no_evidence` → **`change_only` `C`**, and the segment is exact:

```
from_cell: 3   raw: "C"   4/4   support: 68.0
staves_reading_it: [0 … 22]      ← all 23
bars_fit: 1   bars_contradict: 2
```

Cell 3 of that system is excerpt bar 7 = **original bar 209**, the printed
change, to the bar.

⚠️⚠️ **AND LOOK AT `bars_contradict: 2`.** The bar math *disagreed* with the
change — because of §1 — and 23 unanimous glyphs carried it anyway
(23 × 3.0 − 2 × 1.0 = 68.0). That is Sean's ordering behaving exactly as
specified: *"any time signature glyph should be the heaviest weight"*, and
arithmetic this unreliable cannot sink it. The same page is the argument for
the ordering and the argument for fixing §1.

⚠️ It is also why fixture **B** (built by mistake, see §4) produced *nothing at
all* on three pages: with the opening hidden, the only printed meter in the
whole document was that `C`, and it reached no decision.

**Fixed.** `_CHANGE_LETTERS` is derived from
`time_signature_locator.LETTER_METERS` rather than restated, so the two readers
cannot drift about which glyphs these are. Digits still win where both are
present, so the existing digit path is untouched — the letter is a fallback,
never an override. The letter reaches the segment's `raw`, because unlike a
BORROWED spelling it **is** evidence: the glyph was matched here.

---

## 3. WHAT THE MECHANISMS DID — the part that works

Fixture at bar **155** (the Scherzo recall), 5 pages, one system each:

| system | truth | flags OFF | CARRY | BARS | BOTH |
|---|---|---|---|---|---|
| `0/0` | 4/4 | `voted` **C** ✅ | same | same | same |
| `1/0` | 4/4 | `too_few_staves` | ⚠️ **refused, +1.0 (4 agree / 4 disagree)** | `too_few_staves` | refused |
| `2/0` | 4/4, one bar | `no_evidence` | `carry_not_corroborated` ✅ | — | same |
| `3/0` | **3/4** | `voted` **3/4** ✅ | same | same | same |
| `4/0` | 3/4 | `no_evidence` | **`carried` 3/4, +5.0 (4/0)** ✅ | **`derived_from_bars` 3/4, +4.0 (4/0)** ✅ | `carried` 3/4 |

✅ **Two independent mechanisms reach the same correct answer on `4/0`** — the
carry from the system that read it, and the bar reader deriving 3.0 and
borrowing the spelling from that same system. That is the layered model doing
exactly what it was built for.

✅ **A wrong carried meter IS refused on a well-read page.** On the
hidden-change fixture at bar 209, the carried `3/4` meets a system that is
half 3/4 and half 4/4 and scores **−1.0 (1 agree / 3 disagree)**.

⚠️⚠️ **AND A CORRECT CARRY IS ALSO REFUSED — the cost side, measured at last.**
`1/0` above is genuinely in 4/4, the carried `C` is genuinely right, and the
bars refuse it: **4 agree, 4 disagree, support +1.0 against a floor of 2.0**.
`A-DUR-2` says in its own words that *"only the BENEFIT is measured — the cost
of a wrong revert is not"*. It is now: **on perfect ink, one of the two
continuation systems available lost a correct carry.** That is a direct
consequence of §1 — the bars are wrong often enough to outvote a right answer.

---

## 4. ⚠️ TWO FIXTURE MISTAKES, BOTH CAUGHT BY LOOKING

1. **The hide script's `--marker` was a DEFAULT and the default was wrong for
   the second fixture.** `\time 3/4` is the CHANGE at bar 155 and the OPENING
   at bar 203 — so the 209 run hid the signature the carry needs as its
   **source** and left the change printed, inverting the experiment. The tell
   was `system/0/0` abstaining `no_evidence` where it had to read 3/4. The
   argument is now **required**, and the reason is in the code.
2. **A top-margin heuristic for finding movement starts missed p.17**, the one
   known boundary — that print does not indent a movement start. Discarded
   rather than trusted.

⚠️ **And the courtesy signature is a real structural case this fixture
surfaced.** At bar 155 the change falls on a system boundary, so LilyPond
prints `3/4` at the **end of the preceding system** as well as at the start of
the new one. A change reader that trusts the cell a glyph stands in would
propose a change one bar early, at the last bar of the old meter. It does not
fire here — but nothing in the rule prevents it, and no scanned page in the
corpus prints one.

---

## 5. WHAT THIS SETTLES, AND WHAT IT DOES NOT

**Settled.** The carry and the bar reader are correct mechanisms: given bars
that are read right, they name the right meter, agree with each other, and
refuse a wrong candidate. The engraving shows that where §1 does not bite.

**Moved upstream.** The reason they cannot be relied on is not the scan and not
the threshold — it is that **bar sums are wrong on clean ink**. No amount of
tuning `METER_CARRY_FLOOR` or `METER_FROM_BARS_FLOOR` reaches that, and a
sweep of either would be fitting constants to a broken input.

**Still open.** n = 2 changes in 1 movement of 1 work. The `2/2` change at bar
364 is rendered by the same tool in one command and is not yet run.
