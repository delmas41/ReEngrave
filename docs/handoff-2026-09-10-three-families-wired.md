# Handoff — three families wired, and a control that caught a real bug

⚠️⚠️ **READ [docs/plan-2026-09-10-wire-first-then-reconcile.md](plan-2026-09-10-wire-first-then-reconcile.md)
FIRST.** This session executed its **Phase 1** and changed none of its
targets. The three 2026-09-10 handoffs that precede it are still correct about
what they MEASURED and their rankings remain superseded.

---

## 1. WHAT LANDED — Phase 1 items 1, 2 and 4

| | family | reach it was measured on |
|---|---|---|
| `0982864e` | **fermata** | Litolff `984073` p1-3: **63** glyphs |
| `eb87d300` | **stem_direction + voices** | 1,189 CV stem rows |
| `830bfccb` | **ornament** | ⚠️ **0 and 7** — see §5 |

Each landed **all three legs at once** — adjudicator, emission, counter —
because the previous session established that a stub's "one repair" is three.
`grep -c articulations staged/export.py` was 0 the day `articulation_owner`'s
docstring called the repair *"write the adjudicator"*, and both
`adjudicate_dynamic` and `arc_kind` spent a day deciding into no file.

**`gather_coverage`'s `NO_VOCABULARY` went 7 → 2.** What remains is
`tied_to_next` / `tied_from_prev` — the tie CHAIN, which is Phase 1 item 5.
**No family in `FAMILIES` is quantity-less any more**, asserted derivedly.

Suite **3,63x passed** (run it; do not quote this line). `health --check`,
`inventory --check`, `gather_coverage` green, `unaccounted 0`.

---

## 2. ⚠️⚠️ THE ACCOUNTING CONTROL RAISED ON A REAL PAGE AND IT WAS RIGHT

The voices change died on its first real run:

```
Unbalanced: 1863 noteheads+rests in the log, 1616 written and
            264 accounted as dropped — the difference went nowhere.
```

17 over. Opened: **`Q.VOICES` partitions `Q.EVENT`'s groups — every notehead
the record READ — while `export._events` groups only the ones it can WRITE.**
The two groupings are not forced to agree, so a chord the exporter formed can
span two of the record's streams, and every one of its notes is written TWICE.
Measured: **7 such events**, three of three notes and four of two, which is
`3×3 + 4×2 = 17` — the control's number **to the unit**.

⚠️ **The repair is a REFUSAL, not a majority vote.** Assigning the chord to the
stream holding most of its notes would be the EXPORTER deciding a question the
record did not answer — the same overreach as collapsing a narrowed duration
by argmax, which that module refuses one screen up and says so.

⚠️⚠️ **AND IT IS AN ARGUMENT FOR KEEPING THE BALANCE AN EQUALITY.** The
rests-in-both-voices convention had just forced a subtraction into that
control, and the temptation at that moment was to relax it to `<=`. **Relaxing
it would have shipped this bug.** A control that cannot fail is worse than no
control, and the cheapest way to make one unable to fail is to widen it while
teaching it about a legitimate exception.

---

## 3. ⚠️ WHAT EACH FAMILY ACTUALLY DID — read the number beside the zero

### fermata — [benchmarks/omr-staged-fermata-2026-09/](../benchmarks/omr-staged-fermata-2026-09/)

63 marks → 51 decided → **37 `<fermata>`**, balance holding, and with the
fermata elements removed the two files are **byte-identical** with no other
counter moved. music21 reads back 37, **20 of them on a Rest**.

* ⚠️ **26 of 51 carriers are RESTS.** `fermataAbove` carries the detector's
  `ornament` CATEGORY, shared with all ten `artic*` classes — so a
  category-keyed router would have applied the articulation attach rule, which
  **structurally cannot reach more than half of this population**. Routing by
  CLASS is not a taxonomy preference.
* ⚠️ **The `nearest_in_bar` fallback fired ZERO times.** All 51 decisions are
  `contains_the_mark`, so that branch's correctness rests on its unit test
  alone and **the page does not exercise it**.
* ⚠️ **The 13 "absorbed" marks are DUPLICATE DETECTIONS, not chords** — 13
  carriers named by exactly two marks each, overlapping boxes, one confident
  and one not. The hoist is doing dedupe work it was not designed for; that is
  named as a happy accident and is a **DETECTION** figure.

### stem_direction / voices — [benchmarks/omr-staged-voices-2026-09/](../benchmarks/omr-staged-voices-2026-09/)

**Three rules were present and none could fire**, which is worse than a
missing rule because an inert rule is indistinguishable from one that ran and
found nothing: the divisi guard (`divisi_guard: "not_implemented"`),
`_directions_conflict` in `export._events`, and `_paired_spans`'s one-voice
test, **handed an EMPTY `voice_of` map**.

Direction decided on **837 of 1,339 noteheads (62.5%)**; the guard RAN on 375
bars and **SEPARATED 4 chords** x alone would have merged; 19 bars read as two
streams → **11 written with a `<backup>`**, 5 refused (straddle), 1 refused
(empty stream), 2 exported as an empty measure. **11+5+1+2 = 19, exact.**

⚠️ **FOUR, NOT FOUR HUNDRED**, and what those four are worth against the print
is unmeasured. ⚠️ **One tie span is now refused** — the one-voice rule firing
for the first time on this path. Whether that tie is real needs a human; n = 1
and no claim is made either way.

---

## 4. ⚠️ THE MUTATION BATTERY'S FIRST RUN REPORTED FOUR SURVIVORS AND THREE WERE ITS OWN FAULTS

`benchmarks/omr-staged-fermata-2026-09/probe/battery.sh` — **20 arms, all RED**
after repair, positive control SURVIVED, harness control NOT APPLIED.

1. **Two GATHER arms SURVIVED because the test list did not include the gather
   tests.** *A battery whose tests do not reach the file it mutates measures
   its own scope, not the code.*
2. **One SURVIVED because `for h in heads` occurs three times in `rhythm.py`**
   and the first is in `adjudicate_tuplet` — it mutated a different function.
   Re-anchor on the whole expression, not on a fragment.
3. ✅ **One was a genuine test gap and is now closed** — *hoist reads only the
   chord's FIRST head*. `group_chords_in_measure` sorts a chord LOWEST NOTE
   FIRST and the adjudicator names whichever member its x test picked, so
   reading the hoist off the first head loses every fermata owned by another
   member — and every existing test happened to own the first.

---

## 5. ⚠️⚠️ ORNAMENT CLOSES A QUANTITY AND CLOSES NO DETECTION GAP

`export_coverage.KNOWN_GAPS` records the eleven-work engraved truth's only
ornaments as **twelve `<tremolo>`**, against a detector producing **ZERO**
`tremolo1`-`5` detections over a positive control of 34,115 detections on 11
committed transcriptions. Reach on the two documents in hand is **0** and
**7**. The RECORD can now name this family; the PAGE still supplies almost
none of it, and nothing here changes that.

⚠️ Its gather asks `transcribe._ORNAMENT_KINDS` rather than prefix-matching,
because **`tremolo1`-`5` ARE ornaments and their class names do not begin
`ornament`** — so `FAMILY_TO_Q` maps both `ornament` and `tremolo` to one
quantity. ⚠️ `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS` is imported and is declared
UNMEASURED by its own author; importing keeps ONE unmeasured number in the tree
rather than two that drift, and **does not make it measured.**

---

## 6. ⚠️ THE WEDGE SCOPING IN THE PREVIOUS HANDOFF IS WRONG IN OUR FAVOUR

Its §6 says a wedge *"has **no renderer to reuse** and needs the arc merge as
well"*. Checked against the tree rather than remembered:

* **A renderer exists.** `export._mxl_wedge` is a separate renderer from
  `_mxl_direction`, called by both legacy measure emitters. The premise —
  `_mxl_direction` emits only `<dynamics>` and `<words>` — is true and does not
  imply the conclusion.
* **The arc merge is NOT needed for the rows that matter.** Measured on the
  committed Brahms p0-3 record: of **47** `Q.WEDGE_BOX` rows, **46 are
  `cv_hairpins`** and every one carries `bbox_page_px`; the single `detector`
  row carries **no box at all**. `hairpin_detection` reads the WHOLE PAGE one
  staff-band at a time, so a CV hairpin is **never cut by a barline** — the
  merge exists for per-cell crops. And **12,932 of 12,932 `glyph_box` rows
  carry page pixels**, so both sides of the comparison are already in one
  frame.
* ⚠️ **What remains open is a STAGE-BOUNDARY question, not a plumbing one**,
  and it is why this was not rushed: `_legacy._wedge_anchors` wants the
  exporter's `measures` shims and three measured constants
  (`_WEDGE_ANCHOR_PAD_NOTEHEADS`, `_WEDGE_STOP_REACH_NOTEHEADS`,
  `_WEDGE_START_RULE`). Calling it from the exporter is the `_pair_arcs`
  precedent and would leave `adjudicate_wedge_anchor` with nothing to decide;
  doing it in the adjudicator restates three constants unless the legacy
  function is refactored to take page-pixel candidates. **Decide that before
  writing it.** ⚠️ The detector row also means `no_page_frame` is a real
  abstention branch, not a defensive one.

---

## 7. WHAT IS LEFT OF PHASE 1

In the plan's order, with what this session learned:

3. **`wedge_anchor`** — §6. Brahms is its ONLY fixture (47 there, **0** on
   Litolff), so measuring it on Litolff would produce a meaningless clean zero.
5. **`tied_to_next` / `tied_from_prev`** — the tie CHAIN, and the last two
   entries in `NO_VOCABULARY`. ⚠️ Note the exporter ALREADY sets both flags
   from `_pair_arcs`; what is missing is a quantity NAMING the chain, so this
   is *the record catching up with the exporter*, the opposite direction from
   every other item here.
6. **`direction`** — two jobs. `Q.DIRECTION_WORD` is the last input-starved
   quantity on the record (`gather_coverage` §3).

**Then STOP and take the first cleanup count** (plan §6, Phase 2). ⚠️ Fix the
categories — missing / wrong / spurious / would-not-notice — **before**
looking, or the count fits itself to what was found.

---

## 8. OPERATIONAL — one hazard measured the hard way

⚠️⚠️ **`staged/__main__.py` IMPORTS THE EXPORTER *AFTER* THE GATHER**
(`from . import export as staged_export`, inside the `--musicxml` branch). So a
run that started eight minutes ago picks up whatever `export.py` says when it
reaches EXPORT — **a gather finished cleanly and then died on a `NameError`
from an edit made four minutes into it.** The record was already written, so
nothing was lost, but the same shape could silently export under half-edited
code.

**The recipe: run a long gather WITHOUT `--musicxml` and export separately.**
Then the exporter is never imported late and edits during the run cannot reach
it.

⚠️ Editing anything — including an untracked file under `benchmarks/` —
makes `provenance.dirty` true, because `_provenance()` reads
`git status --porcelain` at the END of the run. A dirty stamp does not spoil a
SINGLE-record arm (one record exported twice); it does forbid comparing that
record to another.

* Timings, this session, under load ~5: Litolff 3-page gather **~8 min**;
  Brahms 4-page **~45 min**; the staged suite **~31 s**; the full suite
  **~9.5 min**.
* Four symlinks in a worktree: `library`, `tools/omr/training/data/weights`,
  `.venv-surya`, `.venv-omrned`. The staged pipeline needs only the weights;
  the music21 read-back needs `.venv-omrned`.
* ⚠️ Never `pkill -f` by name. Kill by PID from a file you wrote.

```bash
OMR_SURYA_KEEP_ALIVE=0 python3 -u -m tools.omr.staged <pdf> --pages 1-3 \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
    --out /tmp/x/staged.json          # ⚠️ no --musicxml
python3 -m tools.omr.staged.export /tmp/x/staged.json --out /tmp/x/out.musicxml
python3 benchmarks/omr-staged-fermata-2026-09/fermata_arm.py /tmp/x/staged.json
python3 benchmarks/omr-staged-voices-2026-09/voices_arm.py  /tmp/x/staged.json
zsh benchmarks/omr-staged-fermata-2026-09/probe/battery.sh
```
