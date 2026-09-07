# Review — `claude/reprice-slot-stitch` (`832b7582`), Fix Agent L

**Reviewer: Agent III, 2026-09-07.** Read-only; nothing edited, `scan_eval` not
run. The arm uses my page-normalised truth as its second column, which is why it
came here.

## VERDICT: **APPROVE WITH FIXES** (four, all in the writeup — none in the data)

## PRIORITY ONE — the misquote is confirmed, and it is worse than a paraphrase slip

**CLAUDE.md, verbatim:** *"⚠️ It is OFF because it still costs OMR-NED"*.

**The FINDINGS it cites (`omr-staff-structure-2026-09` §4), verbatim:**

| | pooled OMR-NED | edits | `entire staff` |
|---|--:|--:|--:|
| baseline (flag off) | 0.8283 | 34,962 | 8,453 |
| **slot stitch** | **0.8235** | **34,746** | **9,370** |
| | **−0.0048** | **−216** | **+917** |

and, in its own bold: *"**THE FIX IMPROVES THE POOL AND MAKES THE NAMED BUCKET
MORE THAN TWICE AS BAD.** That is not a contradiction, it is what the bucket
measures"*, then *"**Why it stays off.** … −216 edits from n=1, against +917 on
the bucket the work was scoped to reduce, **is not enough to change a default**."*

So the summary did not merely lose a nuance. **It took the one bucket the source
spends a paragraph explaining is *not* the cost, and reported it as the cost** —
inverting a documented warning written to prevent exactly that reading. "A real
gain on too little evidence" became "a cost", and the error runs in the direction
that suppresses a working mechanism.

**Reproduction:** `entire staff` 715 → 1,632 and parts 27 → 14 are **exact**.
⚠️ The net is **−214 against −216**, so *"reproduces the original to the edit"*
(§ summary, twice) is a slight overstatement — two edits, on a different tree,
comfortably immaterial, but this audit is about precise claims. **Fix 1: say
"reproduces the structural figures exactly and the net within two edits."**

## 1. Does the result depend on my reshaped truth? — **No. Verified per row.**

| reached row | RAW off → on | Δ | NORM off → on | Δ |
|---|--:|--:|--:|--:|
| beethoven-984073-p3 | 3034 → 3017 | **−17** | 1903 → 1315 | −588 |
| beethoven-575951-p3 | 3172 → 3163 | **−9** | 1763 → 1170 | −593 |
| brahms-317803-p2 | 6547 → 6333 | **−214** | 5506 → 4409 | −1097 |

**All three improve on the raw, unreshaped truth; no row is worse on either
column** (checked across all 20). Sean's standing rule — a better score on a
truth we reshaped does not vindicate a mechanism — is satisfied, because the
mechanism also improves on the truth we did not reshape. The normalised column
explains *why the raw gain is small*; it is not what makes it a gain. **This is
the verdict-deciding check and it holds.**

## 2. Transform artefact — counts reproduce **exactly**; two fixes

I recomputed from the committed per-row categories. The reported
**28,215 / 5,777** (OFF) and **32,080 / 7,604** (ON) reproduce **exactly** under
pool-level net accounting.

⚠️ **Fix 2 — the percentages are a different ratio than the sentence implies.**
`5,777 / 28,215 = 20.5%`, not 17.0%. The quoted 17.0% is
`added / (added + removed)` — a share of *total movement*. Both are defensible;
say which.

⚠️ **Fix 3 — the direction claim is accounting-dependent and should say so.**
"charges ON slightly more of its own noise" holds under pool-net (17.0 → 19.2,
or 20.5 → 23.7). Under **per-row gross** accounting it **reverses**: OFF 25.7%,
ON 24.2%. Pool-net is the right choice for a claim about a pooled figure, and
cancellation across rows understates the artefact — worth one sentence.

⚠️ **Fix 4, and the one that matters most: these figures are in the commit
message and the FINDINGS, but nowhere in `results-reprice.json`, and
`reprice_arm.py` does not compute them.** They are ad hoc and not reproducible
from the committed artefact. I could only check them by re-deriving. Put the
computation in the probe.

**Magnitude sanity:** consistent with what I measured for this transform in round
2 — residue 21.5% of the total structural floor, `wrong lyric` 30 → 231.

## 3. The hash-based execution proof — **sufficient, and stronger than timing**

`pred_off` ≠ `pred_on` on exactly the 3 reached rows; identical on the other 17;
`predictions_differ == reached` on **20/20**; all 17 unreached rows identical **to
the edit in both columns**.

Timing proves only that *something ran*. This proves **what ran differed exactly
where the flag can act and nowhere else** — a positive control and a negative
control in one artefact. For an export-only flag re-exporting in 1.3 s it is the
correct substitute, not a fallback. Sharing one transcription is right here (the
flag is export-only), and the `transcription` sha is recorded so the sharing is
visible rather than assumed.

## 4. Limits — **complete, and better reasoned than my objection**

I was going to file "two of the three raw gains (−17, −9) are near the ±6 noise
floor". **That objection is wrong and the design already answers it**: both arms
come from ONE stored transcription and differ only in the export, so the
detector's noise floor is removed from the comparison entirely — and export
determinism is separately controlled and measured **byte-identical**. I nearly
filed a limit the arm had already engineered away.

Also correct: the dilution guard is applied properly (pred symbols −35 = 0.09%
while edits fall 240 / 2,278 — ratio and count fall **together**, the opposite of
the symmetry artefact), fixtures-empty is checked, and the OFF/normalised cell
agrees with `scan_eval`'s own run exactly.

Verified the trade it volunteers, on the reached rows normalised:
`entire staff` **2,238 → 0**, `entire measure` 2,926 → 1,380, against
`wrong note` **+757** and `wrong note head` +306. Structural charge becoming
elementwise charge, stated honestly.

## 5. Reach — table exact; **heading over-asserts** (part of Fix 1)

The 9 / 8 / 3 table matches the data exactly. But **no row in the current 20 is
unreached for slot incompleteness**: the 17 split 9 "single system" and 8
"ordinal join succeeds". The slot-completeness evidence is a *historical*
graft09-era Bach transcription, and the FINDINGS **volunteers** that Bach's
ordinal join now succeeds so it is no longer an example.

That disclosure is exactly right. What over-asserts is the heading — *"Reach is
bounded by contextual slot COMPLETENESS, not by refusal rate"* — which the
current corpus does not show; the abstention rule is real code, but nothing in
these 20 rows exercises it. Qualify the heading and the body carries itself.

**The scheduling conclusion survives** in its weaker, correct form: the
abstention rule gates reach by construction, so identity work is upstream of any
future structural gain — established from the code and one historical page, not
from this corpus.

## Is it a legitimate default-ON candidate? — **Not yet, and not because of the score**

The score is fine: 3 of 3 reached rows improve on the unreshaped truth, no row
regresses, and the metric-artefact story is confirmed. What is missing is
**independent structural variety**. n=3 rows is **n=2 distinct pages**, and both
are the *same structural shape* — a multi-system scan with a suppressed tacet
staff. The twin is reproducibility across two rasters, not a second piece of
evidence.

**`OMR_MOVEMENT_REFERENCE` is the precedent and it is exactly on point**: shipped
default-ON on one work, made four times worse by the second. Backlog §B exists to
respect that.

⚠️ **But the documentation must be fixed now, independently of the flag.** The
recorded reason is false, and it has been suppressing a mechanism that has never
once measured worse. Those are separable decisions and only one of them needs
more evidence.

**What would settle it:** one multi-system scanned page, from a *different work
and publisher*, where the ordinal join refuses. ⚠️ The current 20-row gate cannot
supply one — its other 17 rows are single-system (9) or ordinal-succeeds (8) —
so this needs corpus widening, not a re-run. That is a concrete blocker with a
named cost, which is better than "needs more evidence".

## Registry consequence, flagged not applied

My structural floor (`ceiling.value` 0.2123 on the 15-row pool) is measured with
this flag **OFF**. On the reached rows the normalised `entire staff` charge goes
to **exactly 0** with it ON — so **the structural ceiling is flag-conditional**,
and nothing in the registry records that. If the flag ever defaults ON, the
ceiling must be re-measured before any `% of achievable` derived from it is
quoted.

The registry is frozen at **v0.6.0** and I have not touched it. This wants a
`ceiling.control` sentence on the two structural rows; say the word and I will
make it and re-freeze at v0.7.0.
