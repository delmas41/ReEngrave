# Precedence and ordering — one rule, and where it is missing

**Commissioned by Sean, 2026-09-07, twice. The second framing widened the first
and is the brief:**

> *"We were focused on structure because the assumption is that if there is
> general knowledge of what is happening it affects every measure — you are
> telling me we have not been using that information and trying to derive
> information from each bar in isolation, that will never work."*
>
> *"This all feels like precedence and ordering issues. We have way more
> information and are not using it well."*

⚠️ **No pipeline code changed.** Two read-only probes over committed artefacts,
in `benchmarks/omr-part-correspondence-2026-09/`. No `scan_eval`, no
`orchestral_eval`, no transcription run. Verified against **`origin/main`
(`8f209172`)**, which had moved past this branch's base — one seed item was
already closed there.

---

# THE ONE-PAGE ANSWER

## The rule the pipeline already follows in two places, and nowhere else

> **A fact has a SCOPE. A narrower read may FILL it. Overturning it requires a
> witness at its own scope.**

No probability is needed and none should be manufactured. The project has
shipped this rule twice, and each time the work was choosing the *right
witness*, not setting a threshold:

* **meter** is a fact of the SYSTEM → witnessed by other staves reading the same
  **value**. `rhythm.drop_uncorroborated_meter_changes`: **21 mid-staff changes
  reverted on scans, 0 survive.**
* **a key CHANGE** is an EVENT with a position and a value, and only the value is
  staff-scope → witnessed by other staves changing at the same **bar**.
  `key_signature_corroboration`, **default-ON on main since today**: the 7 flips
  it was built for are closed.

## The census, ranked by measured reach

11 stored scan transcriptions (193 staves, 5 publishers) and 11 engraved (224).
Every figure below is from a committed probe, named.

| what is overturned | by what | floor | contest recorded? | measured reach |
|---|---|---|---|--:|
| the three **carry dicts** — key, clef, meter, per staff across systems | **nothing: the carry never happens** | — | no | **every staff, every system** ⚠️ net effect **UNMEASURED** |
| **ownership** of a contested glyph | distance, a local geometric fact | — | yes (`OMR_CONTEST_DUMP`) | 4,255 of 4,521 (94.1%) — ⚠️ **82% in categories where no better tier exists**; confidence tested at P=0.545 |
| **part boundaries** (document) | the exporter's per-system ordinal | — | **no** | 2 of 11 rows; **2,238 of the 3,596** residual `entire staff` edits |
| a staff's **clef** | one cell's detector argmax | **none** | yes (new) | **11 of 193 scan staves; 0 of 224 engraved** |
| a staff's **key** (+ its cross-page vote) | one cell's marker count | none | yes | 7 of 193 — **CLOSED on main today** |
| a staff's **meter** | the header specialist, unconditionally | none | partial | 21 fired, **0 survive** — the guard holds |

⚠️ **The three carry dicts are dead, verified.** `active_key_sig_by_staff`,
`active_clef_by_staff` and `active_time_sig_by_staff` are read at
`transcribe.py:4851/4873/4885` and written at `:5232-5234` — **same key
`(p, sys_idx, staff_idx)`, same loop body, each staff visited once**, so the
lookup can never hit. This is Sean's sentence in code: the carry that would make
a fact global was written and never happens. ⚠️ It is partly compensated (the
cross-page vote seeds the key, `backfill_page_time_signatures` propagates the
meter, and `clef_continuity` escapes because it is keyed on **role**, not on
`(page, system, staff)`), so **do not assume reach equals damage** — measuring
it is the cheapest open item in this document.

## THE ONE RECOMMENDATION — unchanged, and now by elimination

> **Stop deciding part boundaries in the exporter. `apply_contextual_analysis`
> already decides them — `slot_index`, set on 193 of 193 staves — so make it
> write the decision out and have `export.to_musicxml` read it. The ordinal
> join survives only as the fallback for a result with no contextual block.**

The fault in one sentence: **the exporter already trusts contextual's identity
for what to CALL a part (`export.py:3465`) and refuses it for what a part IS
(`export.py:3218`).** That is the precedence rule violated at document scope,
and it is the only site on the census where applying the rule needs no new
evidence, no calibrated score, no refused edge and no held decision.

The rivals are eliminated, not ignored: two are closed, ownership is measured
near-vacuous (82% of contests have nothing above distance), the carry dicts are
unmeasured, and **the clef — the obvious next sibling — is retired below.**

**What must be true** — (1) `slot_index` complete: **MEASURED 193/193**;
(2) the slot join equals the ordinal join wherever ordinal succeeds:
**MEASURED, 3 rows of 3, identical partitions** ⚠️ n=3, load-bearing;
(3) a bad reference must not now corrupt part boundaries: **UNMEASURED**, and
the real risk — `slots.align` inherits `build_reference`'s single-system pick,
which once named 149 Brahms staves an instrument the work has not got.

**The falsifying experiment.** Replay both partitions over **every** stored
transcription in the tree — 11 scan rows, 11 engraved, the whole-work artefacts
— and count rows where they disagree *while the ordinal join succeeded*. Pure
read of committed JSON, minutes, no pipeline run. **Any disagreement kills the
inversion.** Then repeat under `OMR_SPAN_REFERENCE_FIT=off`, the arm known to
poison the reference: if the slot partition shatters there, the reference must
be hardened first and this must not ship until it is.

## ⚠️ The clef guard is RETIRED before anyone builds it — measured this session

The obvious move is to give the clef the guard its two siblings have. **The
corpus says no.** `key_signature_corroboration` could ship because the corpus
holds **zero** real mid-staff key changes, so only its benefit was measurable.
That asymmetry does not hold for clefs:

| | real mid-staff clef changes in the truth | spurious flips we produce |
|---|--:|--:|
| scan, 231 parts | **13** (tenor ×6, bass ×7) | 11 |
| engraved, 223 parts | 2 | 0 |

A blanket corroboration guard is **roughly break-even on real music** — it would
revert about as much as it saves. ⚠️ **And a confidence floor cannot separate
them either**: a floor at 0.3 blocks **0 of 11** flips and one at 0.8 blocks 10,
but the scan's legitimate clef winners sit at p25 = 0.792, so a 0.8 floor
discards a quarter of every real clef read. The flips are *inside* the
legitimate population — 0.32 to 0.82. **This is the constraint made concrete:
precedence is not confidence, and here neither one works.**

The discriminator that *would* work is the instrument (a Violin, Viola or
Clarinet does not go to bass clef mid-staff; a cello or bassoon does), and that
is a **refused edge** — `clef_correction.py:396`, measured to close the loop on
its own mistake — and coupled to the held `OMR_INSTRUMENT_CLEF_DEFAULT`
decision. Not proposed.

---
---

# THE WORKED EXAMPLE — part correspondence, in numbers


## Sean is right, and the arithmetic is already in the tree

`entire staff insert/delete` on the 20-row scan gate, **flags off, nothing in
the pipeline changed between these two rows** — measured 2026-09-07,
`benchmarks/omr-slot-stitch-reprice-2026-09/FINDINGS.md` lines 158/162:

| the truth we compare against | edits | `entire staff` | `entire measure` |
|---|--:|--:|--:|
| the encoding's parts (raw) | 74,913 | **17,520** | 29,633 |
| the page's staves (normalised) | 51,360 | **3,596** | 14,640 |

**79.5% of the part-correspondence charge is not a decision the pipeline made.**
It is the comparison lining up two lists of different kinds: our parts are the
**page's staves**, the reference's parts are the **encoding's parts**, and
musicdiff pairs them **by index with the surplus assumed to be at the end**
(`musicdiff/comparison.py:1596-1633`). One condensed staff and everything below
it pairs with the wrong part — which is why `entire measure` halves too.

Of the 3,596 that remain, **2,238 sit on the three rows where `OMR_SLOT_STITCH`
is consulted, and it takes them to zero** (FINDINGS:182). That flag reads a
number the pipeline had already computed and the exporter does not look at.

    17,520 raw
     −13,924  a valid comparison            (79.5%)  — no pipeline change
      −2,238  reading an answer we already have (12.8%)  — no new evidence
    ───────
       1,358  the pipeline actually getting correspondence wrong (7.7%)

**Fewer than one edit in twelve of this bucket is a recognition failure.**

## Why the answer was already there — measured this session

Over the 11 stored scan transcriptions (5 publishers, current stamped arm):

* **`slot_index` is set on 193 of 193 staves. Zero missing, every row.** The
  pipeline knows which staff is which part on every staff it found.
* Wherever the exporter's own ordinal join succeeds, the slot join produces the
  **identical partition — 3 rows of 3**. Where ordinal refuses (Brahms 1 p.2)
  the slot join expresses exactly the tacet case the page prints.
* Against the **page-normalised** truth the default exporter already emits the
  right number of parts in the right order on **5 of 8** rows with a hand-read
  staff map; **6 of 8** with slot stitch. The two misses are a staff-count
  error and two undetected one-line percussion staves — **neither is a
  correspondence fault.**

⚠️ **This corrects a premise of the commission.** The brief says slot stitch
"abstains on a single staff lacking a slot index, so its ceiling is set by slot
completeness". Slot completeness is **100%**. Its ceiling is set by *when it is
asked*: `_stitch_slots_by_slot` is consulted **only where a weaker rule already
failed**, and never at all on a one-system page.

## The same recommendation, stated at part-boundary scope

> **Stop deciding part boundaries in the exporter. `apply_contextual_analysis`
> already decides them; make it write the decision out, and let
> `export.to_musicxml` read it. The ordinal join survives only as the fallback
> for a result that carries no contextual block.**

The fault in one sentence: **the exporter already trusts contextual's identity
for what to CALL a part (`export.py:3465`, `:3657`) and refuses it for what a
part IS (`export.py:3218`).** Two joins exist, the weaker one is the default,
and the stronger one is reachable only as its fallback behind a default-off
flag. That is this project's recurring fault shape — *computed correctly, then
re-derived or dropped downstream* — arriving in the structural half rather than
the symbol half. (The numbered count of the export-gap instances lives in
`export_coverage.py`'s docstring; prose that restates an ordinal goes stale.)

This is a reordering, not an algorithm. No new evidence, no model, no corpus,
no rewrite. It subsumes `OMR_SLOT_STITCH`, whose separate existence is an
artefact of the decision sitting in the wrong place.

**What must be true**

1. `slot_index` is complete — **MEASURED, 193/193.**
2. The slot join equals the ordinal join wherever ordinal succeeds — **MEASURED,
   3 rows of 3, identical partitions.** ⚠️ n=3. This is the load-bearing one.
3. A bad reference must not now corrupt part boundaries — **UNMEASURED, and the
   real risk.** `slots.align` inherits `build_reference`'s single-system pick;
   the `Viol. Solo` span fault named 149 Brahms staves an instrument the work
   has not got. Today the ordinal join is immune because it reads nothing.

**The cheapest experiment that falsifies it, before anyone builds it**

Replay both partitions side by side over **every stored transcription in the
tree** — the 11 scan rows, the 11 engraved fixtures, the whole-work artefacts —
and count rows where they disagree *while the ordinal join succeeded*. Pure read
of committed JSON, no pipeline run, minutes. **Any disagreement kills the
inversion** and the slot join must stay a fallback. Then run the same replay
under `OMR_SPAN_REFERENCE_FIT=off`, the arm known to poison the reference: if
the slot partition shatters there, the reference must be hardened first and
this must not ship until it is. The 11-row version of the first half is the
probe committed with this document.


---
---

# THE EVIDENCE

## 1. WHERE a staff acquires an identity

Line numbers at `09384e50` (this branch merged with `origin/main` `8f209172`). ⚠️ `docs/architecture-decision-map.md` quotes
`transcribe.py` at `e1107b5b` and those numbers have drifted — identity is at
**5625**, not 4970.

| # | site | scope | what it knows when it decides | what it produces |
|---|---|---|---|---|
| 1 | `roster.acquire_roster` (`roster.py:261`) | document | the first labelled system's names | carried names |
| 2 | `slots.build_reference` (`slots.py:135`) | document | **one observed system** | the canonical part list |
| 3 | `slots.align` (`slots.py:492`) | system | labels + position + bracket group, against the reference | **`slot_index` — the answer** |
| 4 | `contextual` write-out (`contextual.py:1405`) | document | all of the above | `staff["slot_index"]`, `staff["instrument"]` |
| 5 | `export._stitch_slots` (`export.py:3218`) | document | **staff ORDINAL, and nothing else** | `<part>` boundaries |
| 6 | `export._stitch_slots_by_slot` (`export.py:3338`) | document | `slot_index` | `<part>` boundaries — **flag-gated, fallback-only** |
| 7 | musicdiff (`comparison.py:1596`) | document | **part INDEX, and nothing else** | the pairing that is scored |

Site 3 holds the evidence. Sites 5 and 7 each decide the same question again
with strictly less.

## 2. WHAT is in scope at each site, and what exists and is not visible

This is the heart of it.

| site | in scope | on the record, at that moment, and not read |
|---|---|---|
| `_stitch_slots` | staff ordinals, staff counts | `slot_index` (**set on 193/193 staves**), `staff["instrument"]` (read ~240 lines later, for the name), `staff_geometry`, clef, key signature, measure counts |
| `_stitch_slots_by_slot` | `slot_index` | is not consulted at all unless `_stitch_slots` has already refused |
| musicdiff part pairing | two part counts | every `<part-name>` we emit; any structure either file declares |
| `build_reference` | one system's staves and labels | the work's catalog roster (`work_roster.py`, `source_kind: "catalog"`, independent of the encoding) — reach is NIL because it needs `OMR_WORK_ID` and **nothing sets it** |

⚠️ **`_stitch_slots` is not blind by oversight. It is blind by era.**
`export.py` is a separate entry point over a stored JSON, so the exporter was
written as if the contextual pass might not have happened. It then reads
`staff["instrument"]` anyway, for naming — so the caution is already abandoned,
inconsistently, in the same function family.

## 3. WHEN each could be decided — three map claims, verified

| claim (`architecture-decision-map.md` §3.2) | verdict |
|---|---|
| (a) identity is the **last** substantive call | ✅ `transcribe.py:5625`; only the default-off range veto and runtime bookkeeping follow |
| (a) roughly half of identity needs no pitches | ✅ **`grep -c 'pitch\|midi' ` returns 0 for `slots.py`, `roster.py` and `score_layouts.py`.** The slot half is pitch-free by construction and is pinned at the end only by history |
| (b) the header clef is read twice and never compared | ✅ partially superseded — `transcribe.py:4677` still says *"it is not written to the output, and the measure pass below still reads the clef its own way"*, and the pre-pass trace is now **recorded** (`:4963`) but still **compared to nothing**. UNMEASURED how often they disagree |

Genuinely pinned late: the register fit and clef correction (they need resolved
pitches). Late only by history: label reading, bracket structure, staff counts,
score order, roster, **and the slot assignment those produce**.

## 4. Where Sean's hypothesis does NOT hold

Stated plainly, because a scoping document that only confirms its commission is
worth nothing.

* **`build_reference` is a real accuracy problem and no reordering fixes it.**
  The document's canonical part list is inferred from **one observed system**.
  When that pick is wrong every slot in the document is wrong — measured, 149
  staves. The independent source (the catalog roster) names *instruments*, and
  a printed score condenses, so it cannot supply a staff list; that the count
  cannot come from the page is already measured and refused
  (`OMR_CONDENSED_PARTS`). This is the one place where better evidence, not
  better sequencing, is what is missing.
* **The two residual rows are recognition, not correspondence.** Bach reads 12
  staves where the page prints 11; Mahler p3 reads 13 where it prints 15 (the
  one-line percussion staves a five-line detector cannot find).
* **The 7.7% residual is not obviously reachable.** Nothing here says the last
  1,358 edits are cheap.

## 4b. What already works, and WHY — the pattern to copy

Four sites get precedence right. In every one, the rule is the same and the
*work* was choosing a witness whose scope matches the fact's — never a number.

| site | the fact, and its true scope | the witness that matches it |
|---|---|---|
| `rhythm.drop_uncorroborated_meter_changes` | meter — a **system** fact, one value shared by every staff | other staves reading the **same value**. 21 reverted on scans, 0 survive |
| `key_signature_corroboration` (ON since today) | a key CHANGE — a **system event** whose VALUE is staff-scope (transposing instruments differ) but whose BAR is not | other staves changing at the **same bar**, never the same value. **Getting this distinction right is the whole module** |
| `clef_continuity` | a clef — a **role** fact: the third staff of a system is the same player on the next system | the same **position-in-system**, carried across systems. 48/52 → 49/52. ⚠️ It is the one carry that survives, and the reason is that it is keyed on the role and not on `(page, system, staff)` — which is exactly why its three siblings are dead |
| the **dossier override**, running LAST (`transcribe.py:2109`) | clef and key of a part — a **work** fact | none needed. Its own comment: *"unlike them it is not an opinion: it is what the page says, taken from the score"* — a work-scope fact outranks every reader, and the override is recorded rather than silent |
| `slots.align` → `slot_index` | which part a staff is — a **document** fact | the document's reference layout, with deletions allowed so a tacet staff is a MISSING slot rather than a shift. 193 of 193 |

**Three properties they share, and a fix should copy all three.** The witness is
at the fact's own scope, never a proxy for it. The rule is *fill freely, overturn
only with corroboration* — asymmetric on purpose. And the overturn is **recorded**
(`source="carried_from_previous_page"`, `clef_source`, the revert's own reason
string), so a wrong precedence decision is findable afterwards rather than
invisible.

⚠️ **Recording is not precedence, and the clef proves the difference.** The clef
argmax now writes a full contest — every candidate, the winner's confidence, and
`clef_in_effect_before` — which is why this document can count 11 flips at all.
It still has no floor and no authority over the staff. **Last night's work made
the contest visible; it did not make the global fact win.**

## 5. What I did NOT propose, and why

| not proposed | why |
|---|---|
| a learned identity model, a new corpus, a rewrite | ruled out by the commission, and unnecessary: the answer is already computed |
| clefs pinning the part↔staff join | **refused three times**, `dossier.py:434`, `score_layouts.py:682`, `clef_correction.py:396` |
| deduced identity feeding clef correction | same refusals |
| a confidence on the slot alignment | `align` returns no score (`slots.py:492`), and an **uncalibrated probability is worse than none** (P(name) ECE 0.1277). Adding one is a separate, measured-negative workstream |
| default-ON `OMR_SLOT_STITCH` on its own | it is the same fix expressed as a conditional patch on the weaker rule. Its reach is capped by *another rule failing first*; the recommendation removes the condition rather than widening the patch |
| widening `page_normalise` | already built and landing; ⚠️ a normalised figure is **a new benchmark era** and may not be differenced against any raw or historical figure, in either direction |

## 6. What is UNMEASURED here

* **n = 3** for the ordinal-vs-slot partition agreement. That is the claim the
  recommendation rests on, and it is the falsifying experiment's whole job.
* Whether a poisoned reference propagates into part boundaries under the
  inversion. Reasoned, not measured.
* **The net effect of the three dead carry dicts.** Reach is every staff; damage
  is unknown, because the cross-page key vote, `backfill_page_time_signatures`
  and `clef_continuity` each compensate for part of it. **This is the cheapest
  open item here** and it should be measured before it is described as a defect
  with a size.
* Whether the two header clef readings disagree, and how often
  (`architecture-decision-map.md` §3.2(b) — the pre-pass trace is now recorded
  at `transcribe.py:4963` and compared to nothing).
* Whether the 13 real scan clef changes and the 11 spurious flips are separable
  by anything admissible. This document shows two candidates that fail
  (corroboration, confidence) and one that is refused (instrument identity); it
  does not show that nothing works.
* Every figure in the census is quoted from a committed probe under
  `benchmarks/omr-pipeline-audit-2026-09/out/` or measured here; none was re-run
  end-to-end.

⚠️ One correction the widening surfaced: `benchmarks/omr-pipeline-audit-2026-09/
out/probe_stitch_refusal_reach.txt` reports the scan stitch REFUSING on 2 rows
including Bach at `[12, 3, 3, 3, 1, 2]`. On the **current stamped arm** Bach
reads `[12, 12]` and joins. The probes were run on different fixture arms; the
census above uses the current one, and the difference is the choir-grouping
default, not a disagreement about the rule.

## 7. Reproducing the two probes

```bash
python3 benchmarks/omr-part-correspondence-2026-09/probe_correspondence.py
python3 benchmarks/omr-part-correspondence-2026-09/probe_real_clef_changes.py
```

Both read-only; both exit non-zero on a missing or empty fixture set (verified
by running them against one). The fixtures are gitignored build products in the
main checkout, which the probes resolve the same way `library_root()` does.
⚠️ `probe_real_clef_changes` must never glob `*.omr.musicxml` in the engraved
fixture directory — that is our own export sitting beside the truth.
