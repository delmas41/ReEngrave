# The cross-system key carry, measured — and it is NOT the fix

**2026-09-21.** No code under `tools/`. Asked because the 2026-09-11 key-signature
work ranked the cross-system vote as *"the big lever"* and recorded it as
**deliberately not built**, for a stated reason: keyed on a part join that was
grafting, it *"would carry the viola's 7 onto the timpani"*.

**That blocker HAS expired** — the join was repaired (**12 grafts → 0**,
verified). So the refusal was re-asked, exactly as *A PREMISE ENCODED IN A
REFUSAL OUTLIVES ITS REASON* prescribes.

⚠️⚠️ **AND THE ANSWER IS STILL NO, FOR A DIFFERENT REASON THAN THE ONE ON
RECORD. The premise fails: a part does not agree with itself.**

| | parts read on 2+ systems | **that DISAGREE with themselves** |
|---|--:|--:|
| Litolff Beethoven 5 pp.1-4 | 7 | **6** |
| Breitkopf Brahms 1 pp.0-3 | 14 | **11** |

`Flauti [-3,-3,-2,-2,-3,-3]`, `Fagotti [-3,-3,-1,-1,-1]`,
`Corni [0,0,-1]`, `slot 12 [-1,-4,-3,1,-3,-1]`. ⚠️ **This needs NO truth file**
and is the load-bearing measurement: the carry rests on *a part prints one
signature down the page*, and the READINGS do not.

---

## Ask-first block

**CONVENTION.** A part's written key signature is the same on every system of
a page — Sean's own framing, and the module's. **The convention is not in
doubt. What is measured here is that our READINGS are too noisy to use it.**

**NOT CONFIRMED WITH SEAN.** Whether +4 on one document is worth wiring a
legacy module into the staged path.

**WHAT WOULD FALSIFY §3.** A document whose parts agree with themselves on
most systems. Both available documents fail it, in the same direction.

---

## 1. The arms (Litolff, scored against the HAND-READ PRINT)

`reconcile_arm.py`, driving the SHIPPED `key_signature_vote.reconcile`.
⚠️ Scored **two ways**, because an abstention is not neutral in a file: a staff
with no `<key>` reads as *no accidentals*, so on the horns, trumpets and
timpani — which print none — **abstaining is accidentally right**, which this
file already records as 17 of 33 "right" rows.

| arm | reading | FILE | fixed | broken | carried |
|---|--:|--:|--:|--:|--:|
| **shipped** | 34 → 33 (**−1**) | 42 → 43 (+1) | 6 | 5 | 4 |
| all-carry (control) | 34 → 35 | 42 → 43 (+1) | 6 | 5 | 8 |
| **carry-only** | 34 → 38 (**+4**) | 42 → 46 (**+4**) | **4** | **0** | 4 |
| + the repaired part join | **identical** | identical | 4 | 0 | 4 |
| whole-document pooling | 34 → 30 (−4) | 42 → 40 (−2) | 2 | 4 | **0** |

**THE TWO HALVES OF THE MODULE PULL OPPOSITE WAYS.** Carrying is clean (4 of 4
right); REJECTING costs 5 and cancels it. ⚠️ **The rejections are systematic,
not noise: three of the five are the CLARINET, correctly reading 1 flat in
B-flat and rejected for departing from the page's 3-flat reference** — the
transposing hazard the module's own docstring warns of, observed.

⚠️ **Two upgrades REFUTED, so nobody re-tries them.** The repaired part join
changes **nothing** (on this document `slot_index` largely IS the ordinal).
Pooling the whole document into one vote carries **ZERO** and loses 2.

## 2. ⚠️⚠️ THE +4 DOES NOT BEAT A CONSTANT, AND THE NULL SAYS SO

Of 26 abstaining staves the truth is `{-3: 17, 0: 8, -1: 1}`. Writing **"3
flats" on every one of them** scores **17 right** against today's 8 — **+9,
more than double the carry** — and the 4 staves the carry actually reached are
**all truth −3**, so a constant would have scored **4 of 4 on exactly those
four.** *The carry did not out-predict a constant on the staves it reached.*

**Its merit is RESTRAINT, not accuracy**: it speaks for 4 and breaks 0, where
the constant speaks for 26 and writes **9 confidently wrong** signatures. Under
this project's own doctrine — *a fallback must never convert "cannot tell" into
a definite answer* — the constant is inadmissible. But the aggregate number is
reported because it is the honest comparison and it is larger.

## 3. The second publisher is harsher, and finds a WRONG carry

Breitkopf: **3 carries**, values `{-3: 2, -2: 1}`. The dossier's written keys
for this work are `{-3: 15, 0: 4, -1: 2}` — **−2 is not a key this work prints
on any part**, so that carry is wrong, caught without a print. **3 carries, at
least 1 wrong**, against Litolff's 4 of 4. n = 2 documents and the second one
already breaks it.

## 4. WHAT THIS CHANGES

**The recommendation made this morning is WITHDRAWN.** It read: *the blocker
expired, measure the carry, wire it if it holds.* It was measured and it does
not hold. The blocker really had expired — and it was not the binding
constraint. **The binding constraint is the per-staff READING**, and every
cross-system rule inherits it: 6 of 7 and 11 of 14 parts cannot agree with
themselves, so there is nothing stable to carry.

⚠️ That is *the bars are not an independent umpire over a bad reading*,
arriving in the key signature: **the page's redundancy cannot rescue a reading
this noisy, because the redundancy is made of the same readings.**

**The reading-side lever measured the same day is the one that survives**:
~43% of staves reporting *no evidence* carry key accidentals the detector found
and the fitter could not use.

## 5. What is NOT established

* **No code was changed and nothing is proposed for a default.**
* The Litolff truth is hand-read off the print and is the good kind; the
  **Breitkopf truth is the ENCODING** (a dossier), not the page — it is used
  only to show a carried value is impossible, never to score accuracy.
* `--carry-only` is **not a mode the module has** — it is this arm suppressing
  rejections to see the halves apart. Shipping it would be new code.
* n = **2 documents, 2 publishers, 8 pages, both scans**; no export, no file,
  **no OMR-NED figure**.
* Nothing here says the reconciler is wrong *on the pages it was built for* —
  it took a Bach page 6 of 10 → 10 of 10. It says this repertoire's readings
  are not good enough to feed it.

## 6. Running it

```bash
B=benchmarks/omr-keysig-carry-2026-09
python3 $B/carry_accuracy.py                              # the naive carry + the control
python3 $B/reconcile_arm.py                               # the shipped module
python3 $B/reconcile_arm.py --carry-only                  # the half that gains
python3 $B/reconcile_arm.py --carry-only --whole-document # refuted
```
