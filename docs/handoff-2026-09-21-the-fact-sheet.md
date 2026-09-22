# Handoff, 2026-09-21 evening — the fact sheet, and a correction Sean made that changed the session

⚠️ **READ FIRST, BEFORE BUILDING ANYTHING:**
[docs/ask-first-conventions.md](ask-first-conventions.md) — say out loud how a
HUMAN reads the thing off the page, and what ENGRAVING CONVENTION governs it,
before the first line of code.

On `main` at **`64c9b200`**. Tree clean, suite **4,748 passed / 11 skipped /
0 failed** (baseline 4,716 + 32 new), all eight derived checks exit 0.

Predecessor: [docs/handoff-2026-09-21-connecting-the-sweep.md](handoff-2026-09-21-connecting-the-sweep.md)
(`effabd20`) — the four-lane integration. **Nothing in it is superseded.**

---

## 1. THE CORRECTION THAT STARTED THE SESSION, AND IT IS THE MOST REUSABLE THING HERE

Asked where the project stood, I said staff identity was the largest loss on
Litolff and framed it as an unsolved READING problem, quoting **41% of
noteheads reaching the file**.

**Sean: *"I thought we were good with staff identity if we used the dossier?"***

He was right and the framing was wrong, in two separate ways:

1. ⚠️⚠️ **41% IS NOT A READING SCORE.** The dominant loss is
   `staff_not_identified` (783 notes), which is `OMR_HOLD_OUT_UNIDENTIFIED`
   **working exactly as designed** — his own call, *"hold out — I want truth"*.
   Those notes were gathered, decided, pitched and arbitrated; they are absent
   because nobody could NAME THE STAFF, and the shortfall is *counted* rather
   than dressed as an orchestra. Quoting it as *how well the page was read* is
   reading the hold-out as a failure.
2. ⚠️⚠️ **THE DOSSIER IS NOT BLOCKED — IT IS UNPLUMBED, FOR A REASON ABOUT
   MEASUREMENT THAT GOT APPLIED TO PRODUCTION.** `gather_external(dossier=…)`,
   `gather_clef_seed` and `Q.DOSSIER_FACT` all exist. What is missing is a CLI
   rung, and `staged/__main__.py:231` says why: *"a dossier is generated from
   the same MusicXML the benchmarks score against … a `--dossier` flag would
   put a truth file inside a measurement path."* **Correct about the gate,
   silent about reading a score** — *A PREMISE ENCODED IN A REFUSAL OUTLIVES
   ITS REASON*, with the scope never having been stated.

⚠️ **AND THE DOSSIER WOULD NOT HAVE SETTLED IT ANYWAY**, which is the half
neither of us had in hand: `dossier.slot_facts_for_system` requires
`len(parts) == n_staves` and ABSTAINS otherwise (`dossier.py:581`). Beethoven 5
encodes **18 parts** and prints **12 staves**, so on every condensed
conductor's page the per-staff tier is silent by design. *Which encoded part
sits on which printed staff* is a property of the **ENGRAVING**, absent from
the MusicXML entirely.

**That is the gap the fact sheet is aimed at, and it is the one a musician
closes in five minutes.**

---

## 2. WHAT LANDED

`tools/omr/factsheet.py` (945 lines), 32 tests, a 17-arm battery.
**Nothing consumes a sheet and no pipeline behaviour changes** — no reader,
adjudicator or exporter is touched. Findings:
[benchmarks/omr-factsheet-2026-09/FINDINGS.md](../benchmarks/omr-factsheet-2026-09/FINDINGS.md).

```bash
python3 -m tools.omr.factsheet draft score.pdf --record rec.json -o sheet.json
python3 -m tools.omr.factsheet show  sheet.json
python3 -m tools.omr.factsheet check sheet.json --record rec.json --write
```

⚠️⚠️ **THE RULE THAT MAKES IT AN INSTRUMENT RATHER THAN A CRUTCH — and it is
the whole reason Sean asked for auto-population rather than a blank form:
every field a human corrects is a recorded DISAGREEMENT with a reader.**
`merge` writes the reader's own answer back as `reader_said`, recovered from
the record on each re-draft, so the human never has to preserve anything.
`report()` is a scorecard of the readers on exactly the facts that gate the
pipeline, collected for free, on whatever document is in front of you.
⚠️ **A DISAGREEMENT COUNT, NOT AN ERROR COUNT.** The first run filed the
CATALOG as wrong because a hand-typed publisher dropped an umlaut.

**PROVENANCE IS THE SHAPE OF THE LEAF.** `"Flute"` is a hand fact,
`{"value": …, "source": …}` a machine one, `null` nobody's answer — so
confirming is *replacing the dict with the bare value*, and you cannot
accidentally mark something confirmed.

| | Litolff Beethoven 5 p1-4 | Breitkopf Brahms 1 p0-3 |
|---|--:|--:|
| facts | 54 | 56 |
| **machine supplied** | **29** | **44** |
| still unknown | 25 | 12 |

One hand pass on the worst document in the corpus — **12 names, 1 bar number,
6 suppression lists** — takes `still unknown` **25 → 0**.

⚠️ **ONE BAR NUMBER PLACES EVERY SYSTEM AFTER IT** and reproduces this repo's
independently hand-verified figures to the bar (p4/s0 at **82**, p4/s1 at
**97**). It **BREAKS** the chain where the reader decided no bar count rather
than carrying a number across a gap it cannot measure.

---

## 3. WHAT IT FOUND IN TWO SECONDS THAT NOBODY HAD WRITTEN DOWN

On Brahms the drafted lineup is **13 of 14 correct**, and the fourteenth is a
live reader fault: the horn staff reads **`'in C 1 2'`** on p0/s0, **`'(C)'`**
and **`'(Es)'`** on p1/s0, and **`'Hr.'` / `'Hr. (Es)'`** on p1/s1 — the
instrument noun truncated away on some systems and not others. That is exactly
`OMR_ROSTER_LABELS`' population (measured at 1.4% of labels, default OFF),
firing on the document every other lane measures on. It is also why the systems
"disagree about the order": **the disagreement is the READER's, not the
edition's.**

---

## 4. WHAT IS NOT ESTABLISHED

- ⚠️⚠️ **NOTHING CONSUMES A SHEET**, deliberately — the `Q.INK` discipline: a
  producer and its first consumer landing together makes the reach measurement
  circular.
- ⚠️⚠️ **NO PRINT WAS CONSULTED BY THIS WORK.** The Brahms lineup is checked
  against the reader's own output; the Litolff fill uses Sean's previously
  committed hand reading. Whether a drafted name is RIGHT is exactly what the
  sheet exists to have a human answer.
- **The six suppression asks are irreducible** from these inputs: knowing a
  system prints 11 of 12 staves does not say WHICH is missing.
- `lineup.full` **assumes the widest system prints the whole lineup.** If every
  system on the pages in hand suppresses something, the real lineup is longer
  and nothing here can tell. Flagged as a check.
- n = **2 documents, 2 publishers, 8 pages, both scans**; the ENGRAVED family
  is untouched. Both shared records PREDATE fixes, so the Litolff draft
  measures a reader that **never ran** (`margin_label` reports
  `not_implemented` on 75 of 75 staves), not one that failed — the sheet says
  so rather than collapsing the two.
- No OMR-NED, because the sheet emits no music.

---

## 5. THE DECISION WAITING ON SEAN — and it is the only thing blocking the next step

**Wiring the sheet is not a pure wiring job, because a hand fact is a new kind
of evidence and the doctrine has to be settled before code.** Three questions:

1. **What tier is a hand fact?** The argument in the module is that reading the
   printed lineup off the plate is an observation of the PAGE by the best
   reader available — not a leak from the encoding — so it is **TRUTH for a
   measurement path (score against it) and INPUT for production**.
   `printed-lineups.json` is already used exactly that way. **Confirm or
   overrule.**
2. **Where does it enter?** As GATHER observations carrying `source: hand`, or
   as an override read at ADJUDICATE? GATHER is the honest home (it decides
   nothing), but it means a hand fact competes in `Evidence` alongside readers,
   and `correlated_groups` has opinions about that.
3. ⚠️ **Should the staged CLI get `--dossier` after all?** Its absence is now
   known to be measurement-scoped. **A cleaner answer may be that it should
   NOT**: let the dossier reach the pipeline *through a sheet a human has
   confirmed*, so a person has taken responsibility for it and the benchmark
   path stays structurally unable to consume one. That is a proposal, not a
   measurement.

⚠️ Also still open from the predecessor handoff: **the eight decisions in
[docs/symbol-dossiers/INDEX.md](symbol-dossiers/INDEX.md) §6.** Nothing has
been flipped; no default changed, no flag added, in either session.

---

## 6. RANKED NEXT WORK

1. **Wire the sheet** — blocked on §5, and worth little until unblocked.
2. **The truncated margin label.** The sheet found a second, independent
   instance on the primary Breitkopf document. `OMR_ROSTER_LABELS` is built,
   measured (28 firings, all hand-adjudicated correct) and **default OFF**.
   Re-pricing it now has a fresh population to price against.
3. **Join a chord to its stroke** — carried unchanged from the predecessor, and
   reached independently from three directions: `_stems_on` is too NARROW, not
   too wide (reach 115 of 124 profile pairs). **Not** a narrowing repair, which
   is refused twice with numbers.
4. **The ENGRAVED family for beams** — where the legacy work measured 430 of
   449 edits as `editbeam`, and the new `<beam>` emission has never been run.
5. **A GATHER reader for the in-bar accidental** — 256 and 733 printed glyphs
   reach no quantity at all.

---

## 7. THE MANAGER'S OWN FAILURES THIS SESSION

- **I gave Sean a wrong framing of where the project stood**, quoting 41% as a
  reading score when it is a hold-out count, and calling staff identity
  unsolved when the dossier tier exists and is merely unplumbed. **He corrected
  it in one sentence.** Same shape as the 09-20 stem lane: *three messages from
  a musician looking at the thing beat four probes and a battery.*
- ⚠️⚠️ **THREE BUGS IN THE NEW MODULE, ALL FOUND BY FILLING A REAL SHEET RATHER
  THAN BY READING IT**, and the tests that existed at the time caught none:
  (a) `source_of` answered `"hand"` for CONTAINERS, so `merge` bailed at the
  top level and merged nothing — **every re-draft silently returned the old
  sheet and the scorecard read a clean ZERO**; (b) a hand-typed
  `suppressed: ["Timpani"]` was **DISCARDED**, because a list-VALUED fact is
  indistinguishable from a list OF facts — the precise failure the module
  exists to prevent, committed by the module itself; (c) suppression was
  derived from a name the lexicon had **REFUSED**, wherever the same raw string
  happened to appear twice. Only (c) was caught by a mutation arm.
- **I ran a mutation battery and edited `tools/` while a full suite was
  running** — both hazards this file documents, in one go. That run was
  discarded and the suite re-run clean; the reported 4,748 is from the clean run.
- A documented figure went stale between measuring and writing (Brahms open
  checks 3 → 8). Caught by re-measuring against the shipped code before
  committing, which is the only reason it is right.
