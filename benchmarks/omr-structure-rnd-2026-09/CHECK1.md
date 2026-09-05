# Check 1 — does the OUTPUT match the DETECTION?

**2026-09-05. MEASURED. No pipeline code touched.**
Probe: [`check1_output_matches_detection.py`](check1_output_matches_detection.py)
→ [`check1-output-vs-detection.json`](check1-output-vs-detection.json).

```bash
python3 benchmarks/omr-structure-rnd-2026-09/check1_output_matches_detection.py
```

⚠️ **THIS CHECK CONSUMES NO GROUND TRUTH.** It compares two stages of our own
pipeline — what phase 1 detected, and what the exporter emitted. No `works.json`,
no reference `.mxl`, no dossier, no human. **It therefore runs on any page anyone
ever hands the pipeline**, which is the property that makes it survive having no
MusicXML, and it is why this is check 1 of three rather than a supporting probe.

## The rule

A system may OMIT a part that is tacet through it; it can never invent one. So:

```
n_score_parts  ==  max(staves per system)          → OK
n_score_parts  >   max(staves per system)          → FRAGMENTED   (defect)
n_score_parts  <   max(staves per system)          → LOST
```

Plus a second, equally free conservation statement:

```
sum(measures over detected staves)  ==  sum(measures over emitted parts)
```

## Results — 20-row scan gate, 396 staves

| verdict | rows |
|---|--:|
| **OK** | **17 / 20** |
| **FRAGMENTED** | **3 / 20** |
| LOST | 0 / 20 |
| measure-conservation failures | **0 / 20** |

The three: `beethoven-sym5-mvt1-575951-p3` and `-984073-p3` (systems 11 and 8 →
**19 parts**), `brahms-sym1-mvt1-317803-p2` (14 and 13 → **27 parts**).

Cause is known and not re-derived: `export._stitch_slots` refuses the ordinal
join when systems disagree on staff count and falls back to one part per
(system, staff). Those same three rows are what the scan attribution flagged as
**16,769 edits, 22.4% of all scan error**.

⚠️ **Fixture provenance.** The 20-row gate is **only** in
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`, read read-only. The main checkout's
`fixtures/` is the stale 11-row `..graft09` set. The probe asserts 20 fixtures
and 396 staves and fails loudly otherwise.

---

## What check 1 found BEYOND the three known rows

### 1. Measure conservation is perfect, 20/20 — which narrows the defect

Every detected measure reaches the output on every row, including the three
fragmented ones. **Nothing is dropped or duplicated between detection and
export.** So fragmentation is purely a **grouping** failure: the same music, in
the wrong containers.

That places it squarely in class 2 of
[`docs/discussion-detector-right-output-wrong-2026-09-04.md`](../../docs/discussion-detector-right-output-wrong-2026-09-04.md)
— *emitted but degraded in translation*, "the count survives, the structure
didn't" — the class `export_coverage`'s presence test is structurally blind to,
and the class the beam bug lived in.

### 2. ⚠️ THE SYSTEM STRUCTURE IS NEVER EMITTED AT ALL — on any row, including the 17 that pass

**`<print new-system="yes">` count: 0, on all 20 rows.** MusicXML records a
system break that way, and the exporter emits none, ever.

Verified rather than inferred, three ways:

* `grep -n "new-system\|new_system\|<print" tools/omr/export.py` → **no matches**.
  The exporter has no code path that could emit one.
* **The pipeline knows exactly where they are.** `system_breaks` is computed and
  used at `export.py:2197–2231` and `:2409` — it is a documented parameter of
  the slur-pairing pass ("holds the indices of measures that OPEN a new
  system"). The fact is computed, consumed for one purpose, and never written
  out.
* It is **not** in `export_coverage.KNOWN_GAPS`, so it is not a recorded
  deliberate omission either.

**So the answer to "systems preserved?" is NO — and not only on the three
fragmented rows, but on every row in the corpus.** The 17 `OK` rows match on
part count while discarding the page's system structure entirely.

#### ⚠️ Why no MXL-based check could ever have caught this — measured

The 20 truth files carry **`<print new-system="yes">` × 0** as well. Neither
side records system structure, so:

* **musicdiff cannot see it** — it costs 0 edits and always has;
* **`export_coverage` cannot see it** — its rule is "the truth has N, we emit
  zero", and here the truth has zero too, so the guard is silent by
  construction rather than by oversight.

> **This is a defect that only the new benchmark can see.** It is a concrete,
> measured argument for the redirect rather than a rhetorical one: the reference
> encodings do not record system structure at all, so no amount of MusicXML
> scoring could have surfaced it. Check 1 found it on its first run, without
> truth.

⚠️ **What it costs TODAY is zero**, and saying so is part of the finding. Whether
it matters depends entirely on whether the output is meant to represent the
page's layout. Under the redirect — *"we just need to make sure the output
matches that"* — it is in scope. It is recorded here, not fixed, and it is a
**candidate for `KNOWN_GAPS` either way**: if we deliberately do not emit system
breaks, that belongs in the inventory with its reason.

---

## ⚠️ The blind spot, stated with the number

**`OK` is not a proof of correctness.** A page whose two systems print
*different* staves of *equal* count has a roster **larger** than its largest
system, so the correct part count exceeds `max(system_sizes)` and this rule
expects the smaller number.

**Beethoven 5 p.4 is exactly that page, in two editions**: both systems count
11, system 1 prints no Timpani, system 2 condenses `Violoncello`+`Basso` into
`Bassi`, and the true roster is **12**. Both rows score **`OK` here** — and both
are the documented silent mis-join, measured by H0's continuity score at
**6 of 9 links** on each twin.

So check 1's honest scope:

| | |
|---|---|
| catches | **fragmentation** — large, known, 22.4% of scan error, and free |
| blind to | **mis-joining** — cheap today (`staff["instrument"]` reaches only `<part-name>`), and the reason check 2 exists |

Check 2 (does the DETECTION match the PAGE) is what covers this, and it needs a
human — thinly, since H0 already measures page cardinality **exact at 20/20 rows
and 26/26 systems**.

---

## Three things to carry forward, loudly

⚠️ **1. If the exporter stops splitting condensed staves, OMR-NED gets WORSE on
those rows while the output gets BETTER.** The magnitude is already known — the
oracle arm's −7,118, run backwards. **State this in every summary that touches
it**, or a correct change will be read as a regression. Precedent runs both
ways: the articulation work shipped at **+97 pooled edits** because the marks
were right; the slur `drop` variant scored *better* by deleting 12 real slurs
and was refused.

**2. `named_parts`, not "players".** Right for winds (`Corni I.II.` ⇒ 2),
meaningless for a string *section*. The readable fact is **how many parts the
engraving NAMES** — and that distinction is what makes the truth answerable by a
human at all.

**3. `unreadable[]` must be a first-class field.** A Litolff continuation system
whose strings print no label and whose block is re-condensed **cannot be settled
by the human either**. Without somewhere to record that, the corpus silently
acquires guesses — and H2 caught the live version: `works.json`'s Dvořák p5/p6/p7
hand-read lists are **identical**, so an assumer and a checker produce the same
file.

## Status of `OMR_SLOT_STITCH`

**REOPENED, not decided.** Its recorded verdict — "flip it together with a real
count source, or not at all" — was reasoning about OMR-NED's part-pairing
charges. Under a page-truth model there is no count source to wait for, and
check 1 now shows the fragments it avoids are a **pure grouping error with
perfect measure conservation**. That is a reason to **re-measure it against
check 1 and the page-truth score**, and explicitly not a reason to flip it on
the old reasoning.
