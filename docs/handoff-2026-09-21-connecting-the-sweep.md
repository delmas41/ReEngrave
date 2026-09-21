# Handoff: the two bodies of work had DIVERGED, and three of four lanes landed

**START HERE.** One branch, **`claude/handoff-family-sweep-integration-d064d6`**,
pushed. It is `origin/main` + the family sweep + four overnight lanes + eight
documentation repairs.

⚠️⚠️ **THE FIRST THING THIS SESSION FOUND IS THAT THE HANDOFF IT STARTED FROM
WAS WRONG ABOUT WHERE THE WORK WAS.** `docs/RESUME-HERE-2026-09-21.md` says its
branch is *"`claude/integration-2026-09-18` **PLUS TWO THINGS**"*. It is not.
The two **DIVERGED at `b600964e` on 2026-09-20** — 27 commits on one side
carrying the **entire symbol-dossier family sweep** (13,066 lines, eleven
dossiers + INDEX), 18 on the other carrying the stem-notehead-gate merge and
the 09-21 part-instrument work. **Nobody had merged them.** A reader following
that handoff would have gone straight past the sweep.

**Section 5 is the part to read before quoting anything. Section 6 is the
manager's own failure and is the most reusable thing here.**

---

## 1. WHAT LANDED

| lane | outcome | the number |
|---|---|---|
| **A** the `<note>` element | **SHIPPED**, no flag | `<alter>` **0 → 221 / 0 → 489**; `<beam>` **0 → 679 / 0 → 1511**; Verovio flags **574 → 82** and **1156 → 277**, noteheads identical |
| **C** the dropped C clef | **SHIPPED**, no flag | 16 detections on 9 staves recovered — and **0 clef verdicts change** |
| **E** the class space | **SHIPPED**, no flag | audited **146 → 157** canonical names; 15 checked that cannot fire, 26 shipped never checked |
| **D** the stem attribution repair | ⚠️ **REFUSED**, no code changed | all **44** print-adjudicated heads are **unreachable** by it |
| manager | 8 documentation repairs, the merge, the integration | five claims of the sweep's §4 + three more found while checking |

**Baseline** (tip `28749347`, measured before dispatch): **4,657 passed / 11
skipped / 0 failed**, seven derived checks exit 0.

---

## 2. ⚠️⚠️ THE ONE THAT CHANGES A FILE'S MEANING: a SOUNDING fact was in a DRAWING slot

Lane A. `Q.ACCIDENTAL`'s **only** producer is `respell_accidental` — the row
means *this note is altered by the key*. `staged/export.py` handed it to
`_mxl_note(accidental=)`, which renders **the glyph the engraver DREW**.
**269 of 269 verdicts key-derived; the detector's 256 accidental GLYPHS reach
ZERO verdicts — disjoint populations.** One routing error, not two bugs.

⚠️ **The dossier's *"prints right, sounds wrong"* is half wrong and the truth is
worse**: the before-file carries **no sounding alteration** *and* **draws a
redundant flat**. Wrong in both directions — and **music21 and Verovio disagree
about what it sounds**, so the file's meaning depended on reader leniency.

⚠️⚠️ **THE STAGE QUESTION WAS SETTLED BY RULE ORDER AND THE TEXTBOOK ANSWER IS
A TRAP.** Revising `Q.PITCH` in EVALUATE is architecturally correct (key +
position ⇒ pitch is FORCED) and would have been silently undone: **`move_glyph`
runs AFTER `respell_accidental` and its effect is `pitch`**, so 8 subjects would
have lost their alteration. Verified at integration by printing the sorted rule
table: `restate_pitch` 7 → `respell_accidental` 8 → `move_glyph` 9.

---

## 3. ⚠️ TWO LANES CORROBORATED EACH OTHER WITHOUT KNOWING IT

**C** found `gather._CLEF_CLASSES` admits `clefC` — **the COARSE spelling that
fires zero times** — and misses the fine `clefCAlto` / `clefCTenor`.
**E** found `gather_coverage` was filing every clef under an **invented family**
`g`/`f`/`c`, because `_family` splits at the first camel hump and the snapshot
spells them `gClef`/`cClefAlto`. **So the coverage table LOOKED like it named
the clefs while the real `clef` family held only `clef8`/`clef15`.**

One lane found the gatherer accepting a name that never fires; the other found
that the instrument which should have caught it was looking at a family that
does not exist. **Neither knew about the other**, and only integration sees the
pair.

---

## 4. ⚠️⚠️ THE REFUSAL IS THE STRONGEST RESULT — and it is verifiable in six lines

Lane D refused the 09-18 handoff's ranked #1. `adjudicate_stem_direction`
reaches the beam-mate tier **only when `_stems_on` returns EMPTY**; the 26-head
standoff is built from heads that tier answered; an end constraint makes
`_stems_on` **strictly narrower**. Narrowing an empty set leaves it empty.
**All 44 heads the print has ever adjudicated carry the record's own verdict
`no_stem`.** So the 09-18 handoff's *"two lanes, two instruments, one
conclusion"* merges two populations **neither of which its repair can touch.**

⚠️ **It had already been refused on 2026-09-20** in the same benchmark
directory, which was **already in the tree at dispatch** — see §6.

⚠️ The safety argument was false too: **7.5% / 7.8% of solo pairs have a chord
partner the overlap test missed**, so the documented double-stop regression was
reachable. And the fault in `OMR_STEM_STROKE`'s strokes runs the **opposite**
way — that population is **93% chords whose members were never joined**, so
**`_stems_on` is too NARROW, not too wide.**

---

## 5. ⚠️ WHAT IS NOT ESTABLISHED — read before quoting anything

* **No print was consulted by any shipping lane.** Lane A's alterations are
  checked against **the key signature our own pipeline read** — and that reading
  is internally inconsistent: **5 of 12 parts carry more than one key signature
  within the part** (part 8 reads `-3` then `+1`). **The alterations are
  faithful to a reading that is itself wrong somewhere, and this change makes
  that audible where it used to be invisible.**
* **Lane C changes ZERO clef verdicts.** All 9 affected staves already decide,
  every one from the CV locator. It buys a second witness, not a rescue. Its
  own brief's premise — *a dropped clef costs a staff of music* — is **refuted**.
* **Lane E changes no pipeline output at all.** It repairs an instrument.
  Auditing `clefG` does not mean clefs are READ.
* **n = 2 documents, 2 publishers, 7-8 pages, BOTH SCANS.** The **engraved
  family is untouched** by all four lanes — and it is where the legacy beam work
  measured **430 of 449 edits as `editbeam`**, so it is the obvious next place.
* **No OMR-NED figure anywhere**, deliberately.
* **256 and 733 printed accidental glyphs still reach no quantity**; **210 cells
  carry a beam stroke and get no beam** for want of a frame ruler. Both counted,
  not guessed.
* ⚠️⚠️ **THE SHARED RECORDS CAN NO LONGER LICENSE A REBUILD.** A
  `readjudicate`-style CONTROL 1 **fails on today's tree — 2,760 of 2,993
  durations** — because **seven commits have touched `rhythm.py` since the
  record's tree `9d4ccc85`** (verified at integration; one is literally *"both
  flags default ON"*). **Any future A/B on `library/_shared-records/` must be
  base-vs-arm on ONE tree.** ⚠️ A third-route corroboration was still running at
  handoff; **if it returns 2,993 of 2,993 it CONTRADICTS this** and the lane
  said so itself.

---

## 6. ⚠️⚠️ PROCESS — and the manager's own failure is the most reusable item

**A lane was dispatched to build something its own benchmark directory had
already refuted the day before.** `benchmarks/omr-stem-attribution-2026-09/FINDINGS.md`
is dated 2026-09-20, records the print refuting the rule, and **was in the tree
at dispatch.** The brief was written from the 09-18 handoff without reading the
directory named after the thing. **~69 minutes and ~692k tokens to re-derive a
known answer.**

> ⚠️⚠️ **AND THE PRESCRIBED CHECK COULD NOT HAVE CAUGHT IT.** The brief said to
> run `git log --all --oneline -S "_stems_on" -- tools/`. **The 09-20 work
> changed no `tools/` file — because it was WITHDRAWN** — so an `-S` search over
> `tools/` returns nothing. **A withdrawn investigation is invisible to a code
> search by construction, and the most relevant prior art is exactly the work
> that concluded *do not build this*.**
>
> **New clause on this repo's `-S` rule: read the BENCHMARK DIRECTORY named
> after the thing, not just the code.**

Other process items, each paid for:

* ⚠️ **A brief is a ledger too.** My paraphrase of the dossier (*"misses the six
  that can"*) **inverted its source**, and following it would have aimed lane E
  at the raw 208 — the one wrong repair available. The lane caught it by reading
  the dossier instead of trusting me.
* ⚠️ **I merged into a tree while my own suite was running**, making that run
  void. A suite and a merge cannot share a tree.
* ⚠️ **The harness handed at least one lane the STALE `origin/main`** rather than
  the base the brief named; each lane caught it with `git log -1`. **Verify the
  base in the worktree, do not assume the harness honoured the brief.**
* ⚠️ **A test pinned `file:LINE` and went red for an unrelated change.** The line
  number was never part of the claim; what it bought was a red test on every
  edit above it, which trains the next reader to re-stamp the number rather than
  ask whether a real third caller appeared. Relaxed to the file set **plus an
  exact count**, and **proved still able to fail** in both directions.
* ⚠️ **Three EQUIVALENT-MUTANT test gaps in lane A alone**, all found by the
  battery and none by reading. **A test that names a hazard its inputs cannot
  reach is the commonest failure mode here.**
* ⚠️ Lanes were fenced **by file before dispatch**; four lanes, **zero
  conflicts**, one one-line out-of-fence edit which its lane flagged rather than
  hid. `CLAUDE.md` was held by the manager alone and each lane delivered a
  proposed paragraph.

---

## 7. THE DOCUMENTATION REPAIRS (manager, §4 of the sweep + three more)

All verified against the tree first; the sweep was a reading pass and fixed
none of them. **Corrected**: the F-clef dot veto (shipped setting is **13**, not
5 — and the paragraph **contradicted itself**); key-signature corroboration
(**legacy path only**; the staged path imports it nowhere, while
`staged/adjudicators/header.py:15` declares it *"CONSUMED, default-ON"*); the
direction lexicon (**156**, not 181); the confusables' *"stem vs barline —
already solved"* (gated on **`n_staves < 3`**, four braced piano systems — so on
a conductor's page it **never runs**); A-DUR-6's expired blocker (`stubs()` is
`()`). **Found while checking**: the stem spelling `record.py` records as
refuted still stood in `capture.py`; `Q.BARLINE_COLUMN` still declared *"a
fitted barline"* while its producer writes a cell count; and **the staged reader
runs NEITHER notehead-precision filter** — both are defined *and called* only in
`transcribe.py`, so §2a's *"'Shipped' means the legacy path"* is confirmed on
its own Tier-1 family.

⚠️ **ANNOTATED, NOT CHANGED**: `TRUTH_CHANGES ("litolff-984073", 62) = cell 8`.
The ink crops say cell 6, but those findings say the bar number **is not
settled**, and moving a truth table to a second unsettled number would silently
re-score every meter arm ever run on that fixture.

---

## 8. RANKED NEXT WORK

1. **Join a chord to its stroke** — `_stems_on` is too NARROW. Reach 115 of 124
   profile pairs. Three independent routes now point here (09-20's print
   adjudication, 09-21's structural reach, and the stroke lane's own crops).
2. **The ENGRAVED family**, for lane A's beams — 430 of 449 legacy edits were
   `editbeam`, and no lane touched an engraved page.
3. **The in-bar accidental needs a GATHER reader** before it can become a
   `Q.ACCIDENTAL`; until then `coverage()["accidental_reading"]` reports the gap
   (256 and 733 glyphs).
4. **The key signature disagreeing WITHIN a part** (5 of 12) — lane A's
   alterations are downstream of it.
5. Repair-list items **4 and 5** (grace notes; the tuplet whose positional gate
   is in its docstring and not its body) — both verified, both left because they
   sat inside a running lane's fence.

## 9. WHAT IS WAITING FOR SEAN

Unchanged and untaken: **`docs/symbol-dossiers/INDEX.md` §6**, eight decisions
that gate work. Nothing was flipped tonight; no default was changed; every
lane that could have proposed one either refused or shipped without a flag.
One cheap item would settle a convention in a single exchange: **on Brahms
p3/s1, are staves 11 and 12's C clefs the same glyph on different lines?**
