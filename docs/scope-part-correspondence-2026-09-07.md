# Part correspondence — where, how and when we gather it

**Commissioned by Sean, 2026-09-07:**

> *"We keep coming back to this. It feels like there is a simple solution that
> has to do with **where, how and when we gather the info**, because I don't
> think getting the correct answer is the problem. It needs a big picture
> over-simplifying to make sure we are not too stuck in the weeds."*

⚠️ **No pipeline code was changed.** One read-only probe over committed
artefacts: `benchmarks/omr-part-correspondence-2026-09/probe_correspondence.py`.
No `scan_eval`, no `orchestral_eval`, no transcription run.

---

# THE ONE-PAGE ANSWER

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

## THE ONE RECOMMENDATION

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

Line numbers at `46bbfc09`. ⚠️ `docs/architecture-decision-map.md` quotes
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

* n = 3 for the ordinal-vs-slot partition agreement. That is the claim the
  recommendation rests on and it is the falsifying experiment's whole job.
* Whether a poisoned reference propagates into part boundaries under the
  inversion. Reasoned, not measured.
* Whether the two header clef readings disagree, and how often.
* Any effect on the engraved pool. The probe is scan-only; the engraved
  fixtures are 1:1 by construction and cannot express this fault.
* Every figure in §1 is quoted from committed FINDINGS, not re-run here.

## 7. Reproducing the probe

```bash
python3 benchmarks/omr-part-correspondence-2026-09/probe_correspondence.py \
    --json /tmp/correspondence.json
```

Read-only; exits non-zero if the fixture set or `works.json` is missing or
empty. The fixtures are gitignored build products in the main checkout, which
the probe resolves the same way `library_root()` does.
