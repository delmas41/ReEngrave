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

## 1. ⚠️⚠️ ON A DENSE PAGE, THE BARS THAT SURVIVE THE QUORUM ARE STILL WRONG

⚠️ **THIS TABLE WAS OVERSTATED IN A FIRST DRAFT AND THE CORRECTION IS THE
POINT.** It listed the modal length of EVERY cell as *"what we read"*. Most of
those cells never reached the quorum (≥3 staves, ≥50% agreeing), so the
mechanism correctly declined them and was never wrong about them. Only the
**assessable** bars are the mechanism's answers, and only they belong in a
claim about it. Caught by comparing against the sibling session's own table for
the same page.

Engraved `beethoven-sym5-mvt4` bars 203-218, 23 parts, every part playing in
every bar. **Assessable bars only:**

| system | bars | truth | assessable | what they read |
|---|---|---|--:|---|
| `0/0` | 203-205 | 3/4 | 3 of 3 | **3.0, 3.0, 3.0** — all ✅ |
| `1/0` | 206-214 | 3/4, then 4/4 from cell 3 | 4 of 9 | 3.0 ✅, **4.0 at 20/23** ✅ on the change bar, **3.5 (18/23)** ✗, **6.0 (20/23)** ✗ |
| `2/0` | 215-218 | 4/4 | **1 of 4** | **4.5 (12/23)** ✗ |

**Three of the five assessable bars on the two dense systems are wrong** — and
they are not near misses or ties. 18 of 23 staves agree on 3.5 where the truth
is 4.0; 20 of 23 agree on 6.0. **The cross-staff majority that is supposed to
make a bar trustworthy passes them.**

⚠️ **THIS IS THE PART THAT IS ADDITIONAL TO THE SIBLING SESSION'S RESULT.**
They measured that **assessability** falls with density — 100% of bars
assessable at 1.5 events per bar, 33% at 4.5 — which is about how MANY bars
speak. This is about whether the ones that do speak are RIGHT: on the dense
fixture, mostly not. Their own m215+ row (`{4.5: 1, 4.0: 1}`) is the same
finding at n=2 and agrees.

⚠️ **The errors run LONG** (3.5, 4.5, 6.0 against 4.0) on a page with no
missing ink. A shortfall would suggest missed ink; an excess suggests the
duration reader composing something twice or reading a written value too long.
**A diagnosis to open, not a conclusion.**

**So the constraint on the bar-sum family is the DURATION READER, not page
quality.** Every earlier conclusion of the form *"the bars cannot speak here
because the page is hard"* needs re-reading with that in mind — including this
session's own about Litolff p.17 / p.32 / p.44. ⚠️ And **the meter floors must
not be tuned against it**: that is fitting a constant to a broken input.

---

## 2. ⚠️ THE SAME `C` BUG, FOUND INDEPENDENTLY — and the sibling's fix is the one that shipped

This session reached the letter-meter hole from the same engraved bar 209,
wrote its own `_CHANGE_LETTERS` fix and five tests, and measured the repair on
the page (`no_evidence` → `change_only` **`C`** at `from_cell: 3` = original
bar **209**, all 23 staves, support 68.0).

⚠️ **A SIBLING SESSION DID IT IN PARALLEL AND LANDED FIRST**
(`benchmarks/omr-staged-meter-boundary-2026-09/`, `rhythm._meter_from_letter`).
**Theirs is better** — it abstains where one staff reads BOTH `timeSigCommon`
and `timeSigCutCommon`, which mine did not — so **mine was deleted**, along
with four of its five tests, on this repository's own precedent for a
duplicated hairpin export.

**What the duplication was worth, and it is not nothing:** the five tests were
written against one implementation and then run GREEN against the other. Two
independent readings of one hole, agreeing on the behaviour. The single test
they did not cover — a staff carrying a letter AND digits at the same bar,
where the digits must win — is kept as `TestDigitsWinOverALetterAtTheSameBar`.

**The measurement itself stands** and corroborates theirs from a second
fixture: `meter_glyph` = **23 rows, every one `timeSigCommon`, every one at
cell 3**, `meter_template` = 0 rows (correctly — that reader only sees the
header window), and the system abstained `no_evidence`. Perfect detection,
dropped by the rule.

⚠️ It is also why fixture **B** (built by mistake, see §4) produced *nothing at
all* on three pages: with the opening hidden, the only printed meter in the
whole document was that `C`.

⚠️⚠️ **AND THE REPAIRED SEGMENT CARRIES `bars_contradict: 2`.** The bar math
*disagreed* with the change — because of §1 — and 23 unanimous glyphs carried
it anyway (23 × 3.0 − 2 × 1.0 = 68.0). That is Sean's ordering behaving exactly
as specified: *"any time signature glyph should be the heaviest weight"*, and
arithmetic this unreliable cannot sink it. The same page is the argument for
the ordering and the argument for fixing §1.

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

**Still open.** n = 2 changes in 1 movement of 1 work here. The `2/2` change at
bar 364 renders from the same tool in one command and is not yet run.

⚠️ **Read this beside `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md`**,
which covers the boundary itself far more widely (two engraved fixtures, a
second document AND publisher, engraved 4 printed / 4 found / 1 false against
scanned 2 printed / 1 found / 9 false). **This file's contribution is the
DENSE-texture arm and the carry's measured cost**, not the boundary result.
