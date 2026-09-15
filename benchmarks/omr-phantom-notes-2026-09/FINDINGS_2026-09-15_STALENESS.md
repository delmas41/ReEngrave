# The artefact is NOT stale for this population — and the brief's mechanism is wrong

2026-09-15, **no code outside `benchmarks/` and one new test file**. A
companion to [FINDINGS.md](FINDINGS.md), answering the question its §7 ranks
first. **Nothing was shipped into the reader, the adjudicators or the
exporter**, and §5 says why that is the result rather than a shortfall.

> §7.1: *"RE-EXPORT THE SHARED RECORD ON CURRENT MAIN AND RE-RUN
> `probe/silent_bars.py`. … The dedupe repair refuses 176 notes as
> `owned_by_another_staff`, and the 14 outside-the-staff phantoms are its
> target population. Until that runs, nobody knows how much of Sean's
> observation is already repaired."*

---

## 0. THE SHORT VERSION

⚠️⚠️ **THE STALENESS QUESTION IS ANSWERED WITHOUT THE RE-EXPORT, AND THE ANSWER
IS *NO*: 11 of the 13 offending bars — 20 of the 25 phantom notes — SIT IN BARS
THE DEDUPE REPAIR STRUCTURALLY CANNOT REACH.** They hold no cross-staff
notehead contest at all, not even in a loosened superset, so
`adjudicate_glyph_owner` has no domain there, files no verdict, and
`export._place_notes` refuses nothing. The artefact Sean read is stale for the
other 5 notes and for nothing else.

⚠️⚠️ **SO FINDINGS §4's ATTRIBUTION OF THE 14 OUTSIDE-THE-STAFF NOTES IS
REFUTED IN TWO SEPARATE WAYS.** It reads *"That ink entered through the measure
cell's 4-6-space PADDING from a neighbour"*, and §7.1 calls them *"exactly that
repair's target population"*. Measured:

* **11 of the 14 are in bars with no contest**, so they are not the repair's
  population at all — one cell detected that ink and the neighbour's did not,
  which is what makes them invisible to a rule whose domain is *contested*
  glyphs; and
* **5 of the 14 stand ABOVE THE TOP STAFF OF THEIR SYSTEM**, where there is no
  neighbour above to have supplied anything. Read off the exporter's own map.

⚠️ **THE THIRD REFUTATION IS THE BRIEF'S OWN, AND IT IS THE CHEAPEST TO STATE:
the brief said the question might not be answerable here.** It is, because the
join needs no box comparison — a contest's two members share a `(page, system,
staff, cell)` address, **857 of 857, none differing** — so the phantom bars and
the contest table meet on the subject address and the page-pixel frame error
never arises.

---

## 1. REACH, FIRST — AND THE RE-EXPORT REALLY IS IMPOSSIBLE HERE

Checked before anything else was attempted, exactly as the brief permits:

| what §7.1 needs | here |
|---|---|
| `library/_shared-records/beethoven5-p1-p4.record.json` | **absent** — `library/` does not exist |
| `omr-weights/` | **absent** |
| any staged record at all | **none on disk** |

So `python3 -m tools.omr.staged.export <record>` cannot run, and neither can a
`readjudicate` arm. What IS committed, and what this session used:

| artefact | what it gives |
|---|---|
| `benchmarks/omr-staged-dedupe-2026-09/out/pairs-p1-p4.json` | **1,418 overlapping detection pairs** at IoU 0.3 over 4,508 glyph subjects, each with both subject keys, family, scope, both classes and the IoU |
| `…/out/export-only-summary.json` | the dedupe A/B's own counts (1,793 → 1,618 notes; `owned_by_another_staff` 176) |
| `omr-cleanup-count-2026-09/out/system-map-p1-p4.json` | the exporter's own map, asserted measure-for-measure against the XML |
| this benchmark's `out/silent-p4s0.json`, `out/silent-p3s0.json` | the 18 print-silent bars and what we wrote in each |
| `…/out/side-by-side-p1-p4.html` | the seven printed-system PNGs |

```bash
python3 benchmarks/omr-phantom-notes-2026-09/probe/contest_join.py --check
python3 benchmarks/omr-phantom-notes-2026-09/probe/extract_crops.py --out /tmp/crops
python3 benchmarks/omr-phantom-notes-2026-09/probe/padding_ink.py \
    --crop /tmp/crops/crop00.png --page 4 --system 0 \
    --bars 0:3,0:6,0:7,0:9,0:10,1:2,1:8,1:10,5:1,5:6,5:10 --check
python3 benchmarks/omr-phantom-notes-2026-09/mutants.py
```

---

## 2. THE STRUCTURAL CLAIM, DERIVED FROM THE TWO FUNCTIONS

Both halves were read out of the tree rather than remembered.

**(a) `export._place_notes` (`tools/omr/staged/export.py:449`).** It writes a
note at the **subject's own** staff (`home = _staff_key(s["page"], s["system"],
s["staff"])`) and refuses it when `A.is_relocated_copy(sub, owner)` — i.e. when
`Q.GLYPH_OWNER` names a different staff. The pre-repair behaviour its own
docstring records is the mirror: the copy was *moved* to the owner. **Under
either, a note whose destination differs between the two arms is a glyph
carrying an ownership verdict.**

**(b) `gather.gather_ownership_evidence` (`tools/omr/staged/gather.py:524`).**
It files a `Q.GLYPH_BAND_DISTANCE` row only where two detections have

* `di.smufl_name == dj.smufl_name`,
* `gi.staff != gj.staff` inside one `(page, system)`, and
* `_iou(bi, bj) >= CONTEST_IOU` with `CONTEST_IOU = 0.5`.

`adjudicate_glyph_owner` declares `subjects_from=Q.GLYPH_BAND_DISTANCE`, so a
glyph outside that population gets **no verdict**, and `is_relocated_copy`
returns `False` on `None`.

> **=> A bar holding no member of such a contest is byte-identical between the
> two arms.**

⚠️ **It is ONE-SIDED and the probe says so on every row.** A bar that *does*
hold a contest may or may not have moved, because which copy is refused is the
owner's verdict and this container does not hold it. There are two such bars.

⚠️ **The claim is asserted against its source, not copied into prose.**
`tools/omr/tests/test_contest_join.py` reads `CONTEST_IOU` out of `gather.py`
**by AST** (importing the module would drag in the detector) and asserts all
three gate conditions still stand in `gather_ownership_evidence`'s source.
Mutating any of them turns the suite red.

---

## 3. THE MEASUREMENT

`probe/contest_join.py --check`, exit 0. Output committed at
`out/contest-join.log` / `out/contest-join.json`.

### The join

```
notehead CROSS-STAFF contests: 234 at IoU>=0.5  (286 in the 0.3 superset)
notehead SAME-CELL duplicates: 284   -- OUTSIDE the repair's domain by construction

THE ANSWER, over the 13 bars / 25 notes FINDINGS §4 counts:
   11 bars   20 notes   UNREACHABLE by the repair
    2 bars    5 notes   in the domain -- CANNOT TELL
```

The two reachable bars are **`P6 m88`** and **`P6 m92`** — the two FINDINGS §6
already names as the ones holding *both* a rest-slot note and an
outside-the-staff one.

### The cross-tab, which is the result

| | UNREACHABLE | in the domain | total |
|---|--:|--:|--:|
| at the WHOLE REST's own slot (step 5-6) | **6** | 2 | **8** |
| **OUTSIDE the staff (step < 0 or > 8)** | **11** | 3 | **14** |
| inside the staff, elsewhere | 3 | 0 | 3 |
| **TOTAL** | **20** | **5** | **25** |

⚠️ **The 8 / 14 / 3 column reproduces FINDINGS §4's partition exactly**, from a
step computed independently in this probe — so the two sessions' step
arithmetic agrees, and the cross-tab is a refinement of that table rather than
a second, differently-defined one.

### Is there even a neighbour on that side?

```
IS THERE A NEIGHBOUR ON THAT SIDE?  (outside-the-staff notes only)
    9  a neighbouring staff is on that side
    5  ABOVE the TOP staff -- no neighbour above
```

**`P1 m91` (`A6 A6 G6`) and `P1 m92` (`A6 A6`) are on staff 0 of p4/s0 — the
top staff of its system.** Whatever ink is up there, it is not a neighbour's.

---

## 4. TWO CONTROLS, AND A THIRD FOUND BY THE BATTERY

The headline is a **zero**, and a zero from a dead instrument reads exactly
like a zero from a clean page. Both controls are in the probe and `--check`
exits non-zero on either.

1. **THE JOIN IS COMPLETE.** Indexing a contest at each member's own address is
   complete only if both members carry the same cell index — otherwise a
   relocation could land in a bar the probe never looks at. Measured:
   **857 cross-staff pairs share a cell index, 0 differ.** And every pair
   address lies inside its system's `(staves, bars)` from the exporter's own
   map, on all 7 systems, which is what licenses reading `Subject.cell` as the
   bar index at all.
2. **THE POSITIVE CONTROL LIGHTS UP.** The dedupe session named `cell/1/0/7/0`
   and `cell/1/0/8/0` by hand as the printed `ff` that reached the file as
   `ffff`. The same index re-finds them (**2 and 5 dynamic-letter contests**),
   so a lookup that silently returns nothing cannot pass.
3. ⚠️ **AND THE PRINT-SIDE PROBE HAD A FALSE ZERO THE BATTERY DID NOT FIND —
   THE CROP DID NOT HAVE THE PADDING.** `padding_ink.py`'s first run reported
   `above: nothing` for staff 0 at bars 3/6/7/10. Its band asks for 6 staff
   spaces and the crop supplies **3.2**, reaching only to **step 15.6** while
   the notes in question stand at **16-17**. It now prints
   `[have/want sp, reaches step N]` on every row and flags a band under half
   its request TRUNCATED. *A control that reports "the print holds nothing
   there" must first be able to say "I could not look there."*

---

## 5. WHAT WAS NOT SHIPPED, AND WHY THAT IS THE ANSWER

The brief's three branches were: ship the rest-slot rule if the 14 are already
refused; say so if they are not; ship nothing if it cannot be told. **The 14
are not refused, and the second branch is the one the evidence lands on.**

⚠️ **THE WIP BRANCH `claude/note-where-silence-is-printed` IS STILL NOT MERGED,
and the case for it is now DIFFERENT from what FINDINGS §6 left it.** It
reaches at most the 8 at the rest slot, and of those **6 sit in bars the dedupe
repair never touched** — so it is the only candidate for those 6 rather than a
top-up on a repair that had already run. But:

* it cannot be MEASURED in this container (its rule reads
  `Q.NOTEHEAD_IS_A_WHOLE_REST` off a staged record; there is none, and there
  are no weights to make one), and
* **its own reach has still never been joined to a BAR.** FINDINGS §6 says 20
  flagged glyphs over three pages; nothing says which bars.

Shipping an unmeasurable partial fix here would be exactly *"shipping the
smaller fix and calling the observation closed"*.

⚠️ **AND `Q.GLYPH_OWNER` IS NOT WHERE THE PADDING HALF LIVES**, which is the
brief's own supposition refuted. For 11 of 13 bars there is no contest, so that
decision is never asked. Three candidate repairs follow, and they are different
work:

1. **WIDEN THE CONTEST'S POPULATION** so this ink IS adjudicated. Two openings,
   both measured here:
   * the same-class gate refuses **37 cross-staff notehead pairs at IoU >= 0.5
     (47 at 0.3) that differ ONLY in the `InSpace`/`OnLine` suffix** — which is
     the one thing two staves' grids MUST disagree about for ink in the gap
     between them; and
   * `CONTEST_IOU = 0.5` against the legacy `_CROSS_STAFF_DUPLICATE_IOU = 0.3`,
     already recorded in CLAUDE.md as leaving **134 of 636 overlapping groups
     with no verdict**.

   ⚠️⚠️ **NEITHER IS SHIPPABLE FROM HERE AND NEITHER WOULD ADDRESS SEAN'S
   OBSERVATION**: both change the DETECTION SET filed in GATHER, so
   `readjudicate` and `reexport_arm` are structurally blind to them and only
   two full re-gathers can price one — and **the `sufx` column is 0 on all
   eighteen print-silent bars**, so a suffix-blind contest would reach none of
   them. It is a real finding about the gate and *not* a lead on this fault.

   ⚠️⚠️ **AND WIDENING `glyph_owner`'s DOMAIN MAKES `is_relocated_copy` UNSAFE**
   — that predicate is safe *only* because the domain guarantees a twin, which
   its own docstring states and `test_staged_dedupe.py` asserts off the
   registry. Any widening must land with a rule for the uncontested subset in
   the same change, or one printed note is deleted for every rescue.

2. **THE 5 ABOVE THE TOP STAFF ARE THEIR OWN QUESTION** and no ownership rule
   can answer it. The crop reaches step 15.6 and finds one blob at 14.8 on
   `P1 m91` and nothing on `P1 m92`; the notes read 16-17. **Unresolved here,
   and it needs a crop with more headroom than the side-by-side carries.**

3. **THE REST-SLOT RULE**, for the 6 unreachable rest-slot notes — the WIP,
   with §6's scoping, its reach joined to bars, and a machine that can run it.

---

## 6. WHAT IS NOT ESTABLISHED

* **The re-export was not run** and this does not replace it: what is shown is
  that **20 of 25 notes are outside the repair's reach**, not what the other 5
  did. `P6 m88` and `P6 m92` genuinely cannot be told from here.
* **n = 1 document, 1 publisher, 2 printed systems of 7** — inherited whole
  from FINDINGS §8, including that five crops are refused rather than measured.
* **Nothing was checked against the print beyond `padding_ink.py`'s ink
  census**, which reports blob geometry and deliberately names no glyph (the
  crop-side step drifts 1.4 steps across one system — FINDINGS §5.3).
* **The padding measurement is REACH-LIMITED on staff 0** (3.2 of 6 spaces),
  so `above: nothing` there is *could not look*, not *the print is empty*.
* **The 176 notes the dedupe repair refuses were still not inspected** — this
  says where they are NOT, not what they are.
* **No `Q.GLYPH_OWNER` verdict was read**, here or anywhere: the pairs table is
  the contest POPULATION, and the owner's choice is not in any committed file.
* **No OMR-NED figure**, no `readjudicate` arm, no re-gather.

---

## 7. THE INSTRUMENTS

| | what it does | control |
|---|---|---|
| `probe/contest_join.py` | joins the print-silent bars to the contest table on `(page, system, staff, cell)` | cell-index agreement + the hand-named `ffff` cells; `--check` |
| `probe/padding_ink.py` | what the PRINT holds in the cell's padding, which `print_ink.census` never looks at | prints available/requested band and the step it reaches; refuses a disagreeing grid |
| `mutants.py` | **9 arms, all red, 0 survived, 0 bad anchors**, positive control red | restores from its own in-memory snapshot and VERIFIES it |
| `tools/omr/tests/test_contest_join.py` | 8 tests pinning the restated constant and the three gate conditions to `gather.py`'s source | a reader that returns a fixed number is caught by a constant that is not that number |

⚠️ **THE BATTERY'S FIRST RUN REPORTED FOUR PROBLEMS AND ALL FOUR WERE ITS OWN —
the recorded pattern, again.** Two **BAD ANCHORS** (`CONTEST_IOU = 0.5` occurs
in the module docstring as well as the assignment — re-anchored on the
newline), and two **SURVIVORS**, both genuine test gaps rather than equivalent
mutants:

* **`the_test_stops_reading_the_source`**: replacing `_module_constant`'s body
  with `return 0.5` left the equality test GREEN, because **both sides returned
  the stub and the test agreed with itself**. Closed by asking the reader for
  constants whose values are *not* 0.5.
* **`same_class_gate_dropped`**: it moves 47 suffix-only pairs into the contest
  index and **changes no answer**, because no print-silent bar carries one —
  equivalent *for this page*, a real hole *for the mechanism*. Closed with unit
  tests on `index_pairs` itself, with a positive control in the same class so
  a function that files nothing anywhere cannot pass.

⚠️ **The battery restores from an in-memory snapshot and never from the version
control system**, and a checkpoint commit was taken before it ran — CLAUDE.md's
*a mutation battery must leave the tree as it FOUND it, which is not the same
as leaving it as the repository has it*. After the run the only tracked
difference is the intended test additions.
