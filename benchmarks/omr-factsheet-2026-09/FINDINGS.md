# The session-start FACT SHEET — what the machine knows, and what it needs you for

2026-09-21. `tools/omr/factsheet.py`, `tools/omr/tests/test_factsheet.py` (32
tests), `mutate.py` (17 arms, 17 RED, 0 survived). **Nothing consumes a sheet
and no pipeline behaviour changes** — `git diff` touches no reader, no
adjudicator and no exporter.

Sean, 2026-09-21: *"I want the reader and dossier process to work as well as
possible by itself but I can supply this info when necessary. The session
start fact sheet should auto populate what it can by itself. then I can do the
rest/double check."*

## 1. Why this is not the dossier, and not a bypass

**The dossier is not blocked on the staged path — it is unplumbed, for a
reason that is about MEASUREMENT and was applied to production.**
`gather_external(dossier=...)`, `gather_clef_seed` and `Q.DOSSIER_FACT` all
exist; what is missing is a `--dossier` flag, and `staged/__main__.py:231`
says why in terms: *"a dossier is generated from the same MusicXML the
benchmarks score against, so the scan gate is dossier-free BY PROTOCOL and a
`--dossier` flag would put a truth file inside a measurement path."* That is
correct for the gate and has nothing to say about reading a score. **This
module does not add that flag either** — it puts the dossier in a sheet a
human reads, which is a different act from feeding it to a benchmark.

⚠️⚠️ **AND THE DOSSIER STRUCTURALLY CANNOT SUPPLY THE FACT THAT MATTERS.**
`dossier.slot_facts_for_system` requires `len(parts) == n_staves` and abstains
otherwise (`dossier.py:581`). Beethoven 5 encodes **18 parts** and prints
**12 staves**, so on every condensed conductor's page the per-staff tier is
silent by design. *Which encoded part sits on which printed staff* is a
property of the ENGRAVING, absent from the MusicXML entirely. It is the one
fact a human reads off the top margin in seconds and no tier here can derive.

⚠️ **THE DISCIPLINE THAT KEEPS THIS AN INSTRUMENT RATHER THAN A CRUTCH.**
Every fact carries its `source`, and `merge` writes the reader's own answer
back as `reader_said` beside any value a human overrode — recovered from the
record on each re-draft, so the human never has to preserve anything.
`report()` is therefore a scorecard of the readers, on exactly the facts that
gate the pipeline, collected for free on whatever document is in front of you.

⚠️ **IT IS A DISAGREEMENT COUNT, NOT AN ERROR COUNT, and the first run proved
why**: a hand-typed publisher dropped an umlaut the catalog had right, and the
sheet filed the CATALOG as the thing that was wrong. Which side is correct is
a further act of adjudication that nothing here performs.

## 2. What it fills by itself — measured on both shared records

| | Litolff Beethoven 5 p1-4 | Breitkopf Brahms 1 p0-3 |
|---|--:|--:|
| facts on the sheet | 54 | 56 |
| **machine supplied** | **29** | **44** |
| still unknown | 25 | 12 |
| open checks | 10 | 8 |

Four tiers, cheapest first, **none of which needs weights or a raster**:
`catalog` (work id, publisher, plate, page count, `has_text_layer`, the IMSLP
roster) → `dossier` (meter, bar count, part count) → `reader` (a staged
record's own verdicts) → `derived`. The catalog tier costs a **filename**; the
whole draft over a 132 MB record runs in **0.67 s**.

⚠️ Re-measured against the SHIPPED code after the last change, rather than
quoted from the run that motivated it — the Brahms check count moved 3 → 8
when the widest-lineup caveat was added, and a figure that was true of an
earlier draft is exactly the kind this repo keeps finding stale.

**The structure it derives is right against the hand truth this repo already
holds**: 7 systems at 12/11/11/11/**8**/11/11 staves, and `p3/s1` at 8 is the
system CLAUDE.md records as suppressing Oboi/Trombe/Timpani.

## 3. What it found on its own, in two seconds, that nobody had written down

On Brahms the drafted lineup is **13 of 14 correct** and the fourteenth is a
live reader fault: the horn staff reads `'in C 1 2'` on p0/s0, `'(C)'` and
`'(Es)'` on p1/s0, and `'Hr.'`/`'Hr. (Es)'` on p1/s1 — **the instrument noun is
truncated away on some systems and not others**, which is the exact population
`OMR_ROSTER_LABELS` was built for and is here measured firing on the document
every other lane uses. It is also why "6 systems print 14 staves and they do
not agree about the order": the disagreement is the READER's, not the edition's.

## 4. One hand pass, measured

Filling the Litolff sheet with Sean's own committed hand-read lineup
(`printed-lineups.json`), one bar number, and six suppression lists:

| | before | after |
|---|--:|--:|
| machine supplied | 29 | **35** |
| you supplied | 0 | **19** |
| **still unknown** | **25** | **0** |
| open checks | 10 | **1** |

⚠️ **ONE BAR NUMBER PLACES EVERY SYSTEM AFTER IT.** `chain_windows` carries
`first_ref_measure` forward on the reader's own bar counts, so seven questions
are one. It reproduces this repo's independently hand-verified figures to the
bar — **p4/s0 opens at 82 and p4/s1 at 97**, which is exactly what
`omr-measure-numbering-2026-09` records. ⚠️ It rests entirely on those bar
counts and **a miscounted barline shifts every system below it**, so each
derived value says so and the chain **BREAKS** at the first system whose bar
count the reader did not decide rather than carrying a number across a gap it
cannot measure. A later hand value re-anchors it.

## 5. THREE BUGS IN MY OWN CODE, ALL FOUND BY RUNNING IT ON A REAL SHEET

None was caught by the tests that existed when it was written, and the third
was caught by a mutation arm.

1. ⚠️⚠️ **`source_of` answered `"hand"` for CONTAINERS, so `merge` bailed at
   the top level and merged nothing** — every re-draft silently returned the
   old sheet and the scorecard read a clean **zero**. *A believable zero from
   a merge that never ran.* Fixed by `is_leaf`; pinned by two arms.
2. ⚠️⚠️ **A hand-typed `suppressed: ["Timpani"]` was DISCARDED**, because a
   list-VALUED fact is indistinguishable from a list OF facts. Nothing about
   the two objects tells them apart, so the paths are now **declared**
   (`LIST_VALUED`) rather than sniffed. This is the failure the module exists
   to prevent, committed by the module itself, and it was invisible until a
   real sheet was filled in.
3. **Suppression was derived from a name the lexicon had REFUSED**, whenever
   the same raw string happened to appear on both systems — so the match was
   luck, not evidence. Found by a mutation arm surviving; the fixture that
   caught it had to be built for it.

⚠️ A fourth, in the checks themselves: a check label that is not a real dotted
path can never be retired by `_answered`, so the list keeps asking for what
you already gave it. Every label is now a path and a test asserts it.

## 6. What is NOT established

- ⚠️⚠️ **NOTHING CONSUMES A SHEET.** Deliberate — the `Q.INK` discipline: a
  producer and its first consumer landing together makes the reach measurement
  circular. **No pipeline behaviour changes and no file moves.**
- ⚠️⚠️ **NO PRINT WAS CONSULTED BY THIS WORK.** The Brahms lineup is checked
  against the reader's own output, not the plate; the Litolff fill uses Sean's
  previously committed hand reading. Whether a drafted name is *right* is
  exactly what the sheet exists to have a human answer.
- **The six suppression asks are irreducible from these inputs.** Knowing a
  system prints 11 of 12 staves does not say *which* is missing; that needs
  per-system margin evidence the record does not carry here.
- `lineup.full` **assumes the widest system prints the whole lineup**. If every
  system on the pages in hand suppresses something, the real lineup is longer
  and nothing here can tell. Flagged as a check.
- n = **2 documents, 2 publishers, 8 pages, both scans**; the ENGRAVED family
  is untouched. Both shared records predate fixes (`margin_label` reports
  `not_implemented` on 75 of 75 Litolff staves), so the Litolff draft measures
  a reader that **never ran**, not one that failed — the sheet says so rather
  than collapsing the two.
- No OMR-NED figure, deliberately: the sheet emits no music.

## 7. Controls

- 32 tests; **17 mutation arms, 17 RED, 0 survived**, with a byte snapshot, an
  in-flight sentinel, `PYTHONDONTWRITEBYTECODE=1` in every arm, each mutation
  verified by hash to have changed the file, and the restore verified by hash.
  ⚠️ The judge **strips pytest's elapsed time** — a judge comparing the summary
  line verbatim scores every arm RED for free, the shape that voided two
  published batteries here on 2026-09-20.
- The first re-anchor run reported **3 BAD ANCHORs** after an `is_leaf(f, path)`
  refactor moved the lines they named — reported as errors rather than passing
  silently.
- Every test fixture is **synthetic**: `library/` is gitignored, and a test that
  needed it would pass on one machine and skip everywhere else.
- All eight derived checks (`wiring`, `inventory`, `health`, `capture`,
  `gather_coverage`, `no_producer`, `conventions`, `trace`) exit **0**, with no
  stale gap entries introduced.
