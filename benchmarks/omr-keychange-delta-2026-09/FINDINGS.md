# The shared-delta property at a key change — measured

**2026-09-07 · measurement + scoping only, no pipeline code.** Transcribed by the
coordinator: the agent was blocked from writing report files. Probes and full
records are in `probe/` and `out/`; every number below is reproducible from them.

## The answer, in one paragraph

**Sean's identity is correct as arithmetic and real in the music — and using it as a
second condition on the shipped key guard would have changed nothing while making
that guard strictly more aggressive, the one direction its own docstring names as
the risk.** Over all 1,745 reference encodings (197 works carry a mid-score key
change; 843 change bars; 6,266 changing staves; parser cross-checked against an
independent regex, 0 misses): at a bar where ≥2 staves change, **94.9% of changing
staves move by their bar's modal delta and 89.6% of bars have every changer agree.**
⚠️ **That pooled figure is diluted 3-to-1 and must not be quoted alone** — 225 of the
286 change-carrying encodings are 2–4-staff songs and piano music with no
transposing instruments, satisfying the property trivially. On the population the
pipeline actually reads — **≥10 staves — the strict bar-level rate is 0.640**, and
**every one of the 86 disagreeing bars in the whole corpus is orchestral.**

## The exceptions are named, not averaged

| mechanism | outlier staves | real ink? |
|---|--:|---|
| **UNSIGNATURED** — one side's signature is 0 while its `<transpose>` says otherwise | **115** | **yes** — the standard 19th-c. horn/trumpet/timpani convention |
| **ENHARMONIC** — delta differs by exactly ±12 | **83** | **yes** — 5 sharps chosen over 7 flats |
| before/after disagrees with the score's own key | 108 | mixed |
| **UNEXPLAINED** | **15** | 8 are one broken *Boléro* import declaring no `<transpose>` at all; 4 are Holst's genuine bitonality; 2 an undeclared Mahler crook |

⚠️ **Two escapes are identity-free — neither needs to know which staff is the
clarinet** (mod 12 is arithmetic on the two numbers read; "one side is 0" is on the
page). Together they take changing staves **0.9486 → 0.9867** and orchestral bars
**0.640 → 0.837**, leaving ~5 staves in 6,247 that are both real and unclassifiable.

## Against the shipped guard: refused, with a number

All seven spurious flips are **the only staff of their system to change at that
bar**, so they have no witness under either rule. `same bar AND same delta` is a
*conjunct* of the shipped condition, so it can only keep a subset of nothing:

- **benefit: 0 of 7 decisions change.**
- **cost: on ground truth it additionally reverts 1.0–1.4% of genuine staff key
  changes** (65 of 6,266; 42 of 3,050 deduped).

**Do not add the conjunct.**

## What the identity DOES contribute

**(1) A stronger justification for the guard that shipped — free, already true.**
The guard corroborates the *bar* on a scope argument. The identity gives a better
one: if every staff's Δ is shared, a system where every other staff has Δ = 0 at bar
B **positively contradicts** a staff claiming Δ ≠ 0 there — *refuted*, not merely
uncorroborated. ⚠️ Clean only where the others carry signatures: a system of
unsignatured brass reads Δ = 0 because it prints nothing, not because the key held.

**(2) Repair and propagation — identity-free, and that is the whole value.** Where a
bar is corroborated, the modal delta estimates the *value* with no instrument
identity: an outlier can be **corrected** to `before + modal Δ`, and a staff reading
no change can have one **inferred**. ⚠️⚠️ **Reach is ZERO today** — across 417 staves
of both families there are 7 mid-staff key changes and **not one bar carries two of
them.** The blocker is detection, not this property.

## Does it generalise?

**Meter — yes, and better.** No transposition, so the *value* is shared rather than
a delta: **970 of 972 meter-change bars state the same meter, 0.9979**, against the
key's 0.8956. The meter's premise is **45× stronger**, which is the quantitative
version of why its witness does not transplant to the key.

**Clefs — no.** A clef change is genuinely per-staff; there is no shared quantity.

## Side finding, free, and live

`TRANSPOSITION_FIFTHS_OFFSETS` is hand-written and covers **796 of 959 (83%)** of
the transpositions this corpus declares. Missing: **E (−4, 48 declarations — Brahms
1 mvt4 is in this corpus), D (−2, 83), G (−1, 17), B natural (−5, 8).** A correctly
read E horn departing from its system's mode is rejected. ⚠️ Reach, not cost — a
rejection means a fallback, not a wrong key. Unmeasured.

## Limits

⚠️ The scan corpus has **zero real mid-staff key changes**, so this says the property
is real *in the music* and cannot say what a delta rule would cost on our output.
⚠️ A reference encoding is a proxy for a page, not a page. ⚠️ Bars are matched by
measure ordinal, not printed bar number.

## ⚠️ And the probe hygiene note, because it happened again

An in-place `sed` edit deleted a probe from one anchor to end-of-file. It then ran
to completion, printed **nothing**, and **exited 0** — and the fail-loud guard caught
nothing, because the guard was in the deleted half. The tell was an empty `tee`
file. Every probe here was verified to exit 2 against a non-existent root by
*running it*, not by assertion.
