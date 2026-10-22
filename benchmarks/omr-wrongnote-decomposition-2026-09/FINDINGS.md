# Decomposing `wrong note` — and the arm that contaminated itself

**2026-09-07.** Twenty scan-gate pairs, scored under three musicdiff detail
levels. The question was Sean's: **is the scan residual pitch or duration?** —
because `wrong note` is the largest named bucket and CLAUDE.md warns it does
**not** mean wrong pitches.

⚠️ **Every figure below is re-derived from the committed CSVs by summing the
`* OMR-ED` columns over the 20 data rows.** Nothing here is quoted from the
session that produced it. The scripts are committed beside the data.

---

## 1. ⚠️ The contamination, and why it was nearly reported as a result

Running two detail levels **in one interpreter** poisons the second:
`musicdiff` keeps a **process-global header cache**, and ops it cannot map are
filed under `directionins` → **`wrong direction`**.

| bucket | CONTAMINATED | CLEAN |
|---|--:|--:|
| `wrong direction` | **7975** | **744** |
| `wrong pitch` | **0** | **3159** |
| `pitch insert/delete` | **0** | **1636** |

**The contaminated arm reports ZERO wrong pitch.** Read naively that says *our
pitches are perfect* — the most flattering possible answer, arrived at by a
caching artefact. It was one step from being reported.

**Run each detail level in its own process.** `run_one_arm.py` exists for
exactly that; `run_detail_arms.py` drives it.

---

## 2. ⚠️ `wrong pitch` is structurally unreachable under `AllObjects`

Not empirically zero — **impossible**. `AllObjects` excludes `Voicing`
(`32767 & 131072 == 0`), and without it musicdiff pairs notes **by pitch**, so
every pitch error is *required* to become `noteins` + `notedel` and land in
`wrong note`.

| bucket | `AllObjects` | `AllObjects\|Voicing` (clean) |
|---|--:|--:|
| `wrong note` | 22174 | **10226** |
| `entire measure insert/delete` | 29655 | **7239** |
| `wrong pitch` | **0 (unreachable)** | 3159 |
| `pitch insert/delete` | 0 | 1636 |
| `wrong flag/beam` | 688 | **2535** |

⚠️ **A zero `wrong pitch` at any detail level excluding Voicing is a property
of the METRIC CONFIGURATION, not of our pitches.** This is the measured
confirmation of the warning already in CLAUDE.md.

⚠️ **And it is not only pitch.** `wrong flag/beam` is **688 → 2535**: the plain
arm hides duration evidence too, by charging whole measures instead. The two
large structural buckets absorb both.

---

## 3. The answer to the question, on the clean arm

Grouping the clean `AllObjects|Voicing` buckets by what they are *about*:

| family | buckets | edits |
|---|---|--:|
| **pitch** | `wrong pitch` + `pitch insert/delete` + `wrong accidental` | **5350** |
| **duration** | `wrong flag/beam` + `wrong dot` + `wrong tuplet` | **3184** |

**Pitch outweighs duration by roughly 1.7:1.** ⚠️ Sean's hypothesis — that the
scan residual is substantially pitch — **is supported**; the competing claim
that it is mostly duration **is not**.

⚠️ **Read this as a decomposition, not as a target.** The two largest buckets
in the clean arm are still **`entire staff insert/delete` 16777** and **`entire
measure insert/delete` 7239** — structure, not symbols. And `wrong note` at
10226 remains larger than either family above; it is what the aligner would not
pair at all.

⚠️ **The grouping is a judgment, and a different one moves the ratio.**
`wrong accidental` is arguably spelling rather than pitch; `wrong note head`
(3390) is hollow-vs-filled, which is a *duration* cue read off a *pitch*
glyph and is deliberately in neither column. Re-derive with the grouping you
mean rather than quoting 1.7 as a constant.

---

## 4. What NOT to conclude

- **Do not compare these totals to the pooled scan OMR-NED.** They are edit
  counts over 20 pairs at a non-default detail level.
- ⚠️ **Do not adopt `AllObjects|Voicing` as the benchmark's detail level on the
  strength of this.** It changes what every historical scan figure means. The
  era boundary rule applies: a figure under one detail level and a figure under
  another are measurements of different things.
